### NETWORK Output
output "vpc_id" {
  value = module.network.vpc_id
}

output "subnet_ids" {
  value = module.network.subnet_ids
}

output "igw_id" {
  value = module.network.igw_id
}

output "nat_gateway_id" {
  value = module.network.nat_gateway_id
}

output "public_route_table_id" {
  value = module.network.public_route_table_id
}

output "private_route_table_id" {
  value = module.network.private_route_table_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "sg_private_id" {
  value = module.network.sg_private_id
}

output "sg_public_id" {
  value = module.network.sg_public_id
}

### EC2
output "ec2_instance_id" {
  value = module.ec2.instance_id
}

### SQS Output
output "sqs_id" {
  value = module.sqs.sqs_id
}

### DYNAMODB Output
output "table_name" {
  value = module.dynamodb.table_name
}

output "table_arn" {
  value = module.dynamodb.table_arn
}

output "table_id" {
  value = module.dynamodb.table_id
}

### EKS Output
output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "cluster_certificate_authority" {
  value = module.eks.cluster_certificate_authority
}

output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_arn" {
  value = module.eks.cluster_arn
}

### RDS Output
output "database_endpoints" {
  value = module.rds.database_endpoints
}

output "database_arns" {
  value = module.rds.database_arns
}

### RDS Output
output "redis_endpoint" {
  value = module.redis.redis_endpoint
}

### ECR Output
output "ecr_repository_urls" {
  value = module.ecr.repository_urls
}