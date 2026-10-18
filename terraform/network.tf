resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = local.name }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = { Name = local.name }
}

# Public subnets: /24s from the first half of the VPC range.
resource "aws_subnet" "public" {
  count = var.az_count

  vpc_id                  = aws_vpc.main.id
  availability_zone       = local.azs[count.index]
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  map_public_ip_on_launch = false

  tags = { Name = "${local.name}-public-${local.azs[count.index]}" }
}

# Private subnets: RDS, the API Gateway VPC link, and (in production) ECS tasks.
resource "aws_subnet" "private" {
  count = var.az_count

  vpc_id            = aws_vpc.main.id
  availability_zone = local.azs[count.index]
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 100)

  tags = { Name = "${local.name}-private-${local.azs[count.index]}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${local.name}-public" }
}

resource "aws_route_table_association" "public" {
  count = var.az_count

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# NAT is production-only: it costs money per hour. In test, ECS tasks run in the public
# subnets with a public IP so they can pull from ECR (see output ecs_subnet_ids).
resource "aws_eip" "nat" {
  count  = local.enable_nat_gateway ? var.az_count : 0
  domain = "vpc"

  tags = { Name = "${local.name}-nat-${local.azs[count.index]}" }
}

resource "aws_nat_gateway" "main" {
  count = local.enable_nat_gateway ? var.az_count : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = { Name = "${local.name}-${local.azs[count.index]}" }

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "private" {
  count  = var.az_count
  vpc_id = aws_vpc.main.id

  dynamic "route" {
    for_each = local.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.main[count.index].id
    }
  }

  tags = { Name = "${local.name}-private-${local.azs[count.index]}" }
}

resource "aws_route_table_association" "private" {
  count = var.az_count

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# --- Security groups -------------------------------------------------------------------

# Attach to the ECS services and the migration task.
resource "aws_security_group" "services" {
  name_prefix = "${local.name}-services-"
  description = "Backend containers (booking, vehicle, migrations)"
  vpc_id      = aws_vpc.main.id

  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "vpc_link" {
  name_prefix = "${local.name}-vpc-link-"
  description = "API Gateway VPC link"
  vpc_id      = aws_vpc.main.id

  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "db" {
  name_prefix = "${local.name}-db-"
  description = "RDS PostGIS"
  vpc_id      = aws_vpc.main.id

  lifecycle { create_before_destroy = true }
}

resource "aws_vpc_security_group_ingress_rule" "services_from_vpc_link" {
  security_group_id            = aws_security_group.services.id
  referenced_security_group_id = aws_security_group.vpc_link.id
  ip_protocol                  = "tcp"
  from_port                    = var.service_port
  to_port                      = var.service_port
  description                  = "API Gateway to containers"
}

resource "aws_vpc_security_group_egress_rule" "services_all" {
  security_group_id = aws_security_group.services.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "ECR pulls, CloudWatch Logs, database"
}

resource "aws_vpc_security_group_egress_rule" "vpc_link_to_services" {
  security_group_id            = aws_security_group.vpc_link.id
  referenced_security_group_id = aws_security_group.services.id
  ip_protocol                  = "tcp"
  from_port                    = var.service_port
  to_port                      = var.service_port
  description                  = "VPC link to containers"
}

resource "aws_vpc_security_group_ingress_rule" "db_from_services" {
  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = aws_security_group.services.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  description                  = "Containers to PostgreSQL"
}
