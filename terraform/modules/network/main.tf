### VPC
resource "aws_vpc" "vpc" {
  cidr_block       = var.vpc_ipv4_block
  instance_tenancy = var.vpc_instance_tenancy

  tags = {
    Name        = var.vpc_name
    Environment = var.environment
  }
}

### Subnets
resource "aws_subnet" "subnets" {
  for_each          = var.subnets
  vpc_id            = aws_vpc.vpc.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az

  tags = {
    Name        = each.key
    Environment = var.environment
  }
}

### INTERNET GATEWAY
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.vpc.id

  tags = {
    Name        = var.igw_name
    Environment = var.environment
  }
}

### ELASTIC IP FOR NAT GATEWAY
resource "aws_eip" "nat_eip" {
  count  = var.eip_enable_nat_gateway ? 1 : 0
  domain = "vpc"

  tags = {
    Name        = var.eip_name
    Environment = var.environment
  }
  depends_on = [aws_internet_gateway.igw]
}

### NAT GATEWAY (placed in public subnet)
resource "aws_nat_gateway" "nat_gw" {
  count         = var.eip_enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat_eip[0].id
  subnet_id     = aws_subnet.subnets["snet-dev-pub-1a"].id

  tags = {
    Name        = var.nat_gateway_name
    Environment = var.environment
  }

  depends_on = [aws_internet_gateway.igw]
}

### PUBLIC ROUTE TABLE
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name        = var.route_table_public_name
    Environment = var.environment
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.subnets["snet-dev-pub-1a"].id
  route_table_id = aws_route_table.public.id
}

### PRIVATE ROUTE TABLE
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.vpc.id

  # Only add NAT route if enabled, otherwise no default route
  dynamic "route" {
    for_each = var.eip_enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.nat_gw[0].id
    }
  }

  tags = {
    Name        = var.route_table_private_name
    Environment = var.environment
  }
}

### Associate all EXCEPT snet-dev-pub-1a with private route table
resource "aws_route_table_association" "private" {
  for_each = {
    for name, subnet in var.subnets : name => subnet
    if name != "snet-dev-pub-1a"
  }

  subnet_id      = aws_subnet.subnets[each.key].id
  route_table_id = aws_route_table.private.id
}

### SECURITY GROUP
resource "aws_security_group" "sg_private" {
  name        = var.security_group_priv_name
  description = var.security_group_priv_description
  vpc_id      = aws_vpc.vpc.id

  dynamic "ingress" {
    for_each = var.sg_priv_ingress_rules
    content {
      description     = ingress.value.description
      from_port       = ingress.value.from_port
      to_port         = ingress.value.to_port
      protocol        = ingress.value.protocol
      cidr_blocks     = ingress.value.cidr_blocks
      security_groups = ingress.value.is_sg_public ? [aws_security_group.sg_public.id] : ingress.value.security_groups
    }
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = var.security_group_priv_name
    Environment = var.environment
  }
}

resource "aws_security_group" "sg_public" {
  name        = var.security_group_pub_name
  description = var.security_group_pub_description
  vpc_id      = aws_vpc.vpc.id

  dynamic "ingress" {
    for_each = var.sg_pub_ingress_rules
    content {
      description     = ingress.value.description
      from_port       = ingress.value.from_port
      to_port         = ingress.value.to_port
      protocol        = ingress.value.protocol
      cidr_blocks     = ingress.value.cidr_blocks
      security_groups = ingress.value.security_groups
    }
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = var.security_group_pub_name
    Environment = var.environment
  }
}