### MODULE NETWORK
module "network" {
  source                          = "./modules/network"
  vpc_ipv4_block                  = var.vpc_ipv4_block
  vpc_instance_tenancy            = var.vpc_instance_tenancy
  subnets                         = var.subnets
  eip_enable_nat_gateway          = var.eip_enable_nat_gateway
  vpc_name                        = var.vpc_name
  environment                     = var.environment
  igw_name                        = var.igw_name
  eip_name                        = var.eip_name
  nat_gateway_name                = var.nat_gateway_name
  route_table_public_name         = var.route_table_public_name
  route_table_private_name        = var.route_table_private_name
  security_group_priv_name        = var.security_group_priv_name
  security_group_priv_description = var.security_group_priv_description
  security_group_pub_name         = var.security_group_pub_name
  security_group_pub_description  = var.security_group_pub_description
  sg_priv_ingress_rules           = var.sg_priv_ingress_rules
  sg_pub_ingress_rules            = var.sg_pub_ingress_rules
}

### MODULE EC2
module "ec2" {
  source                          = "./modules/ec2"
  environment                     = var.environment
  ec2_instance_name               = var.ec2_instance_name
  ec2_ami_id                      = var.ec2_ami_id
  ec2_instance_type               = var.ec2_instance_type
  ec2_subnet_id                   = module.network.public_subnet_ids[0]
  ec2_associate_public_ip_address = var.ec2_associate_public_ip_address
  ec2_security_group_ids          = [module.network.sg_public_id]
  ec2_key_name                    = var.ec2_key_name
  ec2_monitoring                  = var.ec2_monitoring
  ec2_root_volume_size            = var.ec2_root_volume_size
  ec2_root_volume_type            = var.ec2_root_volume_type
  ec2_encrypted                   = var.ec2_encrypted
  ec2_delete_on_termination       = var.ec2_delete_on_termination
}

### MODULE SQS
module "sqs" {
  source                         = "./modules/sqs"
  environment                    = var.environment
  sqs_name                       = var.sqs_name
  sqs_delay_seconds              = var.sqs_delay_seconds
  sqs_max_message_size           = var.sqs_max_message_size
  sqs_message_retention_seconds  = var.sqs_message_retention_seconds
  sqs_receive_wait_time_seconds  = var.sqs_receive_wait_time_seconds
  sqs_visibility_timeout_seconds = var.sqs_visibility_timeout_seconds
  sqs_max_receive_count          = var.sqs_max_receive_count
}

### MODULE RDS
locals {
  rds_db_passwords = {
    "auth_db"      = var.rds_password_auth_db
    "flags_db"     = var.rds_password_flags_db
    "targeting_db" = var.rds_password_targeting_db
  }

  rds_instances = [for db in var.rds_database_instances : {
    name     = db.name
    db_name  = db.db_name
    username = db.username
    password = db.password != "" ? db.password : lookup(local.rds_db_passwords, db.db_name, "")
  }]
}

module "rds" {
  source                     = "./modules/rds"
  environment                = var.environment
  rds_database_instances     = local.rds_instances
  rds_allocated_storage      = var.rds_allocated_storage
  rds_instance_class         = var.rds_instance_class
  rds_engine                 = var.rds_engine
  rds_engine_version         = var.rds_engine_version
  rds_parameter_group_name   = var.rds_parameter_group_name
  rds_skip_final_snapshot    = var.rds_skip_final_snapshot
  rds_subnet_name            = var.rds_subnet_name
  rds_subnet_ids             = module.network.rds_subnet_ids
  rds_vpc_security_group_ids = [module.network.sg_private_id]
  rds_apply_immediately      = var.rds_apply_immediately
}

### MODULE EKS
module "eks" {
  source                 = "./modules/eks"
  environment            = var.environment
  eks_cluster_name       = var.eks_cluster_name
  eks_cluster_version    = var.eks_cluster_version
  eks_subnet_ids         = module.network.eks_subnet_ids
  eks_node_groups        = var.eks_node_groups
  eks_role_arn           = var.eks_role_arn
  eks_security_group_ids = [module.network.sg_private_id]
  eks_capacity_type      = var.eks_capacity_type
}

### MODULE DYNAMODB
module "dynamodb" {
  source                  = "./modules/dynamodb"
  environment             = var.environment
  dynamodb_table_name     = var.dynamodb_table_name
  dynamodb_billing_mode   = var.dynamodb_billing_mode
  dynamodb_read_capacity  = var.dynamodb_read_capacity
  dynamodb_write_capacity = var.dynamodb_write_capacity
  dynamodb_hash_key       = var.dynamodb_hash_key
  dynamodb_range_key      = var.dynamodb_range_key
  dynamodb_attributes     = var.dynamodb_attributes
}

### MODULE REDIS
module "redis" {
  source                     = "./modules/redis"
  environment                = var.environment
  redis_cluster_id           = var.redis_cluster_id
  redis_engine               = var.redis_engine
  redis_node_type            = var.redis_node_type
  redis_num_cache_nodes      = var.redis_num_cache_nodes
  redis_parameter_group_name = var.redis_parameter_group_name
  redis_port                 = var.redis_port
  redis_subnet_group_name    = var.redis_subnet_group_name
  redis_security_group_ids   = [module.network.sg_private_id]
  redis_subnet_ids           = module.network.redis_subnet_ids
}

### MODULE ECR
module "ecr" {
  source           = "./modules/ecr"
  environment      = var.environment
  ecr_repositories = var.ecr_repositories
}