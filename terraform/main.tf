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
