# ECS Fargate: one service per api_service (booking, vehicle) behind API Gateway via Cloud Map,
# plus a task definition for the one-shot schema-migrations job.
#
# Terraform bootstraps the task definitions using var.image_tags (pass it on the first apply
# only; an "unset" tag just means the service can't start until the first CI deploy) and then
# stops managing the image: the CI deploy job registers a new revision with the freshly pushed tag and updates the
# service (and runs migrations first), so both the task definitions' container_definitions and
# the services' task_definition are ignored here. To change env/secrets/sizing, replace the
# task definition and pass the tags currently running:
#   terraform apply -replace='aws_ecs_task_definition.service["booking"]' -var 'image_tags={...}'
# Then run the deploy workflow (or `aws ecs update-service`) to roll it out.
# Images are built on GitHub's x86_64 runners, hence the X86_64 platform.

locals {
  ecs_task_families = toset(concat(tolist(var.api_services), ["schema-migrations"]))

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
  service_container_extras = {
    for name in var.api_services : name => {
      portMappings = [{ name = name, containerPort = var.service_port, protocol = "tcp" }]
      healthCheck = {
        command     = ["CMD", "python", "-c", "import urllib.request as u; u.urlopen('http://localhost:${var.service_port}/health', timeout=3)"]
        interval    = 15
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
    }
  }
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
      name        = each.key
      image       = "${aws_ecr_repository.this[each.key].repository_url}:${lookup(var.image_tags, each.key, "unset")}"
      essential   = true
      environment = local.db_environment
      secrets     = local.db_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs[each.key].name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = each.key
        }
      }
    },
    # The migration job runs once and exits, so only the HTTP services have a port and health check.
    try(local.service_container_extras[each.key], {}),
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
