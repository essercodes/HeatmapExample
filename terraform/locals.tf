locals {
  is_production = var.environment == "production"
  name          = "${var.project}-${var.environment}"
  azs           = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  # Container images: one repo per image built from containers/<dir>.
  ecr_repositories = toset(["booking", "vehicle"])

  # Settings that differ between test and production.
  db_instance_class       = coalesce(var.db_instance_class, local.is_production ? "db.m7g.large" : "db.t4g.micro")
  db_multi_az             = local.is_production
  db_deletion_protection  = local.is_production
  db_skip_final_snapshot  = !local.is_production
  db_backup_retention     = local.is_production ? 14 : 1
  ecr_tag_mutability      = "IMMUTABLE"
  ecr_force_delete        = !local.is_production
  enable_nat_gateway      = local.is_production
  ecr_untagged_expiry_day = 7
  ecs_task_cpu            = local.is_production ? 512 : 256
  ecs_task_memory         = local.is_production ? 1024 : 512
  ecs_desired_count       = local.is_production ? 2 : 1
  ecs_log_retention_days  = local.is_production ? 90 : 14
  ecs_subnet_ids          = local.enable_nat_gateway ? aws_subnet.private[*].id : aws_subnet.public[*].id
}
