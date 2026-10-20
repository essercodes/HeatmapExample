# Public entry point for the web frontend: internet -> CloudFront (HTTPS) -> ALB (HTTP, public
# subnets) -> ECS tasks. Separate from API Gateway, which only fronts the backend APIs
# (api_gateway.tf). CloudFront gives an AWS-assigned *.cloudfront.net name with HTTPS, so no domain
# or certificate is needed; the ALB only accepts traffic from CloudFront (network.tf).

resource "aws_lb" "frontend" {
  name               = "${local.name}-frontend"
  load_balancer_type = "application"
  internal           = false
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]

  enable_deletion_protection = local.alb_deletion_protection
}

resource "aws_lb_target_group" "frontend" {
  name_prefix = "fe-"
  port        = var.frontend_port
  protocol    = "HTTP"
  target_type = "ip" # Fargate (awsvpc) registers task IPs
  vpc_id      = aws_vpc.main.id

  deregistration_delay = 30

  health_check {
    path    = "/"
    matcher = "200"
  }

  lifecycle { create_before_destroy = true }
}

resource "aws_lb_listener" "frontend_http" {
  load_balancer_arn = aws_lb.frontend.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# --- CloudFront --------------------------------------------------------------------------

# The app is server-rendered per request, so nothing is cached and every viewer header, cookie and
# query string reaches the origin.
data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer" {
  name = "Managed-AllViewer"
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled         = true
  comment         = "${local.name} frontend"
  price_class     = local.cloudfront_price_class
  is_ipv6_enabled = true

  origin {
    origin_id   = "alb"
    domain_name = aws_lb.frontend.dns_name

    # The ALB has no certificate (its AWS-assigned name can't get one), so CloudFront terminates
    # HTTPS and talks HTTP to the origin.
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id         = "alb"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = data.aws_cloudfront_cache_policy.caching_disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer.id
    compress                 = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
