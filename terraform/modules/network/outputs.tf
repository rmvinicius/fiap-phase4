output "vpc_id" {
  value = aws_vpc.vpc.id
}

output "subnet_ids" {
  value = values(aws_subnet.subnets)[*].id
}

output "igw_id" {
  value = aws_internet_gateway.igw.id
}

output "nat_gateway_id" {
  value = var.eip_enable_nat_gateway ? aws_nat_gateway.nat_gw[0].id : null
}

output "public_route_table_id" {
  value = aws_route_table.public.id
}

output "private_route_table_id" {
  value = aws_route_table.private.id
}

output "public_subnet_ids" {
  value = [aws_subnet.subnets["snet-dev-pub-1a"].id]
}

output "private_subnet_ids" {
  value = [
    for name, subnet in aws_subnet.subnets : subnet.id
    if name != "snet-dev-pub-1a"
  ]
}

output "sg_private_id" {
  value = aws_security_group.sg_private.id
}

output "sg_public_id" {
  value = aws_security_group.sg_public.id
}

output "eks_subnet_ids" {
  value = [
    aws_subnet.subnets["snet-dev-aks-1a"].id,
    aws_subnet.subnets["snet-dev-aks-1b"].id,
  ]
}

output "rds_subnet_ids" {
  value = [
    aws_subnet.subnets["snet-dev-rds-1a"].id,
    aws_subnet.subnets["snet-dev-rds-1b"].id,
  ]
}

output "redis_subnet_ids" {
  value = [
    aws_subnet.subnets["snet-dev-pve-1a"].id,
    aws_subnet.subnets["snet-dev-pve-1b"].id,
  ]
}