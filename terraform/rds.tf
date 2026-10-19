resource "aws_db_subnet_group" "main" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier = local.name

  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = local.db_instance_class

  allocated_storage = var.db_allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  # Matches POSTGRES_DB / POSTGRES_USER in containers/database/Dockerfile.
  db_name  = "heatmap"
  username = "heatmap"

  # RDS generates the password and stores it in Secrets Manager (no password in state).
  # Container tasks read it from output db_master_secret_arn.
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = local.db_multi_az

  backup_retention_period    = local.db_backup_retention
  deletion_protection        = local.db_deletion_protection
  skip_final_snapshot        = local.db_skip_final_snapshot
  final_snapshot_identifier  = local.db_skip_final_snapshot ? null : "${local.name}-final"
  apply_immediately          = !local.is_production
  auto_minor_version_upgrade = true
}
