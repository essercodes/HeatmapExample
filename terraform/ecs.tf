locals {
  # Task definition family => the ECR repository (and image_tags key) its image comes from.
  ecs_task_families = merge(
    { for name in var.api_services : name => name },
    { "booking-migrate" = "booking", "booking-sync" = "booking" },
    { "frontend" = "frontend" },
  )

  # Task families that get no database environment or credentials.
  db_free_families = toset(["frontend"])

  # RDS keeps the generated credentials as JSON in Secrets Manager; libpq reads PG* variables
  # natively, so the apps need no URL. DATABASE_URL is a keyword/value conninfo string that
  # only names the database, the rest comes from the PG* variables. RDS (PostgreSQL 15+)
  # requires TLS.
  db_environment = [
    { name = "DATABASE_URL", value = "dbname=heatmap" },
    { name = "PGHOST", value = aws_db_instance.main.address },
    { name = "PGPORT", value = tostring(aws_db_instance.main.port) },
    { name = "PGSSLMODE", value = "require" },
  ]
  # For one-shot jobs: healthy while the container can reach the database.
  db_health_check = {
    command  = ["CMD", "python", "healthcheck.py", "db"]
    interval = 5
    timeout  = 4
    retries  = 3
  }
  container_extras = merge(
    {
      for name in var.api_services : name => {
        portMappings = [{ name = name, containerPort = var.service_port, protocol = "tcp" }]
        healthCheck = {
          command     = ["CMD", "python", "healthcheck.py"]
          interval    = 15
          timeout     = 5
          retries     = 3
          startPeriod = 30
        }
      }
    },
    {
      # Applies pending booking migrations and exits; CI runs it before each booking deploy.
      "booking-migrate" = {
        command     = ["python", "migrate.py"]
        healthCheck = local.db_health_check
      }
      # One sync per run, started by the schedule below.
      "booking-sync" = {
        command     = ["python", "sync.py"]
        healthCheck = local.db_health_check
      }
      "frontend" = {
        portMappings = [{ name = "frontend", containerPort = var.frontend_port, protocol = "tcp" }]
        environment = [
          { name = "POLL_TIME_MIN", value = tostring(var.poll_time_min) },
          { name = "API_URL", value = aws_apigatewayv2_api.main.api_endpoint },
        ]
        healthCheck = {
          command     = ["CMD", "node", "healthcheck.js"]
          interval    = 15
          timeout     = 5
          retries     = 3
          startPeriod = 30
        }
      }
    },
  )
  db_secrets = [
    { name = "PGUSER", valueFrom = "${aws_db_instance.main.master_user_secret[0].secret_arn}:username::" },
    { name = "PGPASSWORD", valueFrom = "${aws_db_instance.main.master_user_secret[0].secret_arn}:password::" },
  ]
}

resource "aws_ecs_cluster" "main" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = local.is_production ? "enabled" : "disabled"
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  for_each = local.ecs_task_families

  name              = "/ecs/${local.name}/${each.key}"
  retention_in_days = local.ecs_log_retention_days
}

# --- IAM -------------------------------------------------------------------------------

# Pulls images, writes logs and reads the database secret on behalf of the task.
resource "aws_iam_role" "ecs_execution" {
  name = "${local.name}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_db_secret" {
  name = "read-db-secret"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = aws_db_instance.main.master_user_secret[0].secret_arn
    }]
  })
}

# --- Task definitions ------------------------------------------------------------------

resource "aws_ecs_task_definition" "service" {
  for_each = local.ecs_task_families

  family                   = "${local.name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = local.ecs_task_cpu
  memory                   = local.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([merge(
    {
      name      = each.key
      image     = "${aws_ecr_repository.this[each.value].repository_url}:${lookup(var.image_tags, each.value, "unset")}"
      essential = true
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs[each.key].name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = each.key
        }
      }
    },
    contains(local.db_free_families, each.key) ? {} : {
      environment = local.db_environment
      secrets     = local.db_secrets
    },
    try(local.container_extras[each.key], {}),
  )])

  lifecycle {
    ignore_changes = [container_definitions]
  }
}

# --- Services --------------------------------------------------------------------------

resource "aws_ecs_service" "api" {
  for_each = var.api_services

  name            = each.key
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.service[each.key].arn
  desired_count   = local.ecs_desired_count
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = local.ecs_subnet_ids
    security_groups  = [aws_security_group.services.id]
    assign_public_ip = !local.enable_nat_gateway
  }

  # API Gateway finds the tasks through this Cloud Map SRV registration (see api_gateway.tf).
  service_registries {
    registry_arn   = aws_service_discovery_service.api[each.key].arn
    container_name = each.key
    container_port = var.service_port
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# Public web frontend, served through its own load balancer (frontend.tf), not API Gateway.
resource "aws_ecs_service" "frontend" {
  name                              = "frontend"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.service["frontend"].arn
  desired_count                     = local.ecs_desired_count
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = local.ecs_subnet_ids
    security_groups  = [aws_security_group.frontend.id]
    assign_public_ip = !local.enable_nat_gateway
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = var.frontend_port
  }

  depends_on = [aws_lb_listener.frontend_http]

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# --- Scheduled booking sync ------------------------------------------------------------

# Runs the booking-sync task definition on a schedule. The revision-less ARN makes EventBridge
# use the latest revision, which the CI deploy job registers alongside each booking deploy.
resource "aws_iam_role" "booking_sync_events" {
  name = "${local.name}-booking-sync-events"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "booking_sync_events" {
  name = "run-booking-sync"
  role = aws_iam_role.booking_sync_events.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Action    = "ecs:RunTask"
        Resource  = "${aws_ecs_task_definition.service["booking-sync"].arn_without_revision}:*"
        Condition = { ArnEquals = { "ecs:cluster" = aws_ecs_cluster.main.arn } }
      },
      {
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = aws_iam_role.ecs_execution.arn
      },
    ]
  })
}

resource "aws_cloudwatch_event_rule" "booking_sync" {
  name                = "${local.name}-booking-sync"
  description         = "Syncs active bookings from the upstream API into the database."
  schedule_expression = var.booking_sync_schedule
}

resource "aws_cloudwatch_event_target" "booking_sync" {
  rule     = aws_cloudwatch_event_rule.booking_sync.name
  arn      = aws_ecs_cluster.main.arn
  role_arn = aws_iam_role.booking_sync_events.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.service["booking-sync"].arn_without_revision
    launch_type         = "FARGATE"

    network_configuration {
      subnets          = local.ecs_subnet_ids
      security_groups  = [aws_security_group.services.id]
      assign_public_ip = !local.enable_nat_gateway
    }
  }
}
