# Replaces backend/api_gateway/nginx.conf: /<service>/... is routed to the matching
# service with the prefix stripped. Traffic goes API Gateway -> VPC link -> Cloud Map (SRV)
# -> ECS tasks. The ECS services (next step) must set `service_registries.registry_arn`
# to aws_service_discovery_service.api["<name>"].arn.
# Ref: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-private.html

resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "${local.name}.internal"
  vpc  = aws_vpc.main.id
}

# ECS-populated Cloud Map entries must use SRV records for API Gateway to find the port.
resource "aws_service_discovery_service" "api" {
  for_each = var.api_services
  name     = each.key

  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.main.id
    routing_policy = "MULTIVALUE"

    dns_records {
      ttl  = 10
      type = "SRV"
    }
  }
}

resource "aws_apigatewayv2_vpc_link" "main" {
  name               = local.name
  subnet_ids         = aws_subnet.private[*].id
  security_group_ids = [aws_security_group.vpc_link.id]
}

resource "aws_apigatewayv2_api" "main" {
  name          = local.name
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "api" {
  for_each = var.api_services

  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "HTTP_PROXY"
  integration_method = "ANY"
  integration_uri    = aws_service_discovery_service.api[each.key].arn
  connection_type    = "VPC_LINK"
  connection_id      = aws_apigatewayv2_vpc_link.main.id

  # Strip the /<service> prefix, as nginx did.
  request_parameters = {
    "overwrite:path" = "/$request.path.proxy"
  }
}

resource "aws_apigatewayv2_route" "api" {
  for_each = var.api_services

  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /${each.key}/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.api[each.key].id}"
}

# The $default stage keeps the stage name out of the URL and the backend request path.
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
}
