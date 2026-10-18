# Heatmap example infrastructure on AWS: ECR repos, VPC, RDS PostGIS, and an HTTP API
# (API Gateway) in front of the ECS services. ECS cluster/services are added in a later step.
#
# Test/example by default. Set `environment = "production"` for production-grade settings
# (see locals.tf for exactly what changes).

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }

  assume_role {
    role_arn = "arn:aws:iam::${var.account_id}:role/${var.organization_account_access_role}"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}
