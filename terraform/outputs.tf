output "api_url" {
  description = "Base URL of the API Gateway HTTP API."
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "ecr_repository_urls" {
  description = "Repository URL per image (booking, vehicle, schema-migrations)."
  value       = { for k, r in aws_ecr_repository.this : k => r.repository_url }
}

output "db_endpoint" {
  description = "RDS endpoint (host:port)."
  value       = aws_db_instance.main.endpoint
}

output "db_master_secret_arn" {
  description = "Secrets Manager secret holding the generated master user credentials."
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "ecs_subnet_ids" {
  description = "Subnets for ECS tasks: private in production (NAT), public in test."
  value       = local.enable_nat_gateway ? aws_subnet.private[*].id : aws_subnet.public[*].id
}

output "ecs_assign_public_ip" {
  description = "Whether ECS tasks need a public IP (test only, no NAT)."
  value       = !local.enable_nat_gateway
}

output "services_security_group_id" {
  value = aws_security_group.services.id
}

output "service_discovery_arns" {
  description = "Cloud Map service ARNs to use as ECS service_registries."
  value       = { for k, s in aws_service_discovery_service.api : k => s.arn }
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}
