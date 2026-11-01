resource "aws_elasticache_subnet_group" "redis" {
  name       = var.redis_subnet_group_name
  subnet_ids = var.redis_subnet_ids
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = var.redis_cluster_id
  engine               = var.redis_engine
  node_type            = var.redis_node_type
  num_cache_nodes      = var.redis_num_cache_nodes
  parameter_group_name = var.redis_parameter_group_name
  port                 = var.redis_port
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = var.redis_security_group_ids

  tags = {
    Name        = var.redis_cluster_id
    Environment = var.environment
  }
}