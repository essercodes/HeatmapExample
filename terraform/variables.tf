variable "account_id" {
  description = "AWS Organization Account ID"
  type        = string
  default     = "285861554180"
}

variable "organization_account_access_role" {
  description = "AWS Organization Account Access Role"
  type        = string
  default     = "OrganizationAccountAccessRole"
}

variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Name prefix for all resources."
  type        = string
  default     = "heatmap"
}

variable "environment" {
  description = "\"test\" is cheap and disposable; \"production\" enables deletion protection, Multi-AZ, NAT, and backups."
  type        = string
  default     = "test"

  validation {
    condition     = contains(["test", "production"], var.environment)
    error_message = "environment must be \"test\" or \"production\"."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to spread subnets across (RDS subnet groups need at least 2)."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2
    error_message = "az_count must be at least 2."
  }
}

variable "db_instance_class" {
  description = "RDS instance class. Defaults to db.t4g.micro (test) or db.m7g.large (production) when null."
  type        = string
  default     = null
}

variable "db_allocated_storage" {
  description = "Initial RDS storage in GiB."
  type        = number
  default     = 20
}

variable "db_engine_version" {
  description = "RDS PostgreSQL version. Major version 18 matches the local postgis/postgis:18-3.6 image."
  type        = string
  default     = "18"
}

variable "service_port" {
  description = "Port the backend containers listen on."
  type        = number
  default     = 8000
}

variable "api_services" {
  description = "Backend services exposed through API Gateway at /<name>/..., mirroring containers/api_gateway/nginx.conf."
  type        = set(string)
  default     = ["booking", "vehicle"]
}

variable "booking_sync_schedule" {
  description = "EventBridge schedule expression for the booking sync task (`python sync.py` in the booking image)."
  type        = string
  default     = "rate(5 minutes)"
}

variable "image_tags" {
  description = "Image tag (the git SHA CI pushed) per image repository: booking, vehicle (booking-migrate and booking-sync use the booking tag). Only read when Terraform creates a task definition; after that CI deploys new tags (see ecs.tf), so later applies can leave this unset."
  type        = map(string)
  default     = {}
}
