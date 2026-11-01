### TAGS
variable "environment" {
  type = string
}

### REGION
variable "aws_region" {
  type = string
}

### NETWORK
variable "vpc_name" {
  type = string
}

variable "vpc_ipv4_block" {
  type = string
}

variable "vpc_instance_tenancy" {
  type = string
}

variable "subnets" {
  type = map(object({
    cidr = string
    az   = string
  }))
  description = "Map with name, CIDR and AZ for each subnet"
}

variable "igw_name" {
  type = string
}
variable "eip_name" {
  type = string
}
variable "nat_gateway_name" {
  type = string
}
variable "route_table_public_name" {
  type = string
}
variable "route_table_private_name" {
  type = string
}

variable "eip_enable_nat_gateway" {
  type        = bool
  default     = true
  description = "Enable NAT Gateway for private subnets"
}

### SECURITY GROUP
variable "security_group_priv_name" {
  type        = string
  description = "Name of the private security group"
}

variable "security_group_priv_description" {
  type        = string
  description = "Name of the private security group"
}

variable "security_group_pub_name" {
  type        = string
  description = "Name of the public security group"
}

variable "security_group_pub_description" {
  type        = string
  description = "Name of the public security group"
}

variable "sg_priv_ingress_rules" {
  type = list(object({
    description     = string
    from_port       = number
    to_port         = number
    protocol        = string
    cidr_blocks     = optional(list(string), [])
    security_groups = optional(list(string), [])
    is_sg_public    = optional(bool, false)
  }))
  default     = []
  description = "Ingress rules for the private security group"
}

variable "sg_pub_ingress_rules" {
  type = list(object({
    description     = string
    from_port       = number
    to_port         = number
    protocol        = string
    cidr_blocks     = optional(list(string), [])
    security_groups = optional(list(string), [])
  }))
  default     = []
  description = "Ingress rules for the public security group"
}

### EC2
variable "ec2_instance_name" {
  type = string
}

variable "ec2_ami_id" {
  type        = string
  description = "AMI ID for the instance. When omitted, the latest Amazon Linux 2023 x86_64 AMI is selected."
}

variable "ec2_instance_type" {
  type = string
}

variable "ec2_associate_public_ip_address" {
  type = bool
}

variable "ec2_key_name" {
  type = string
}

variable "ec2_monitoring" {
  type = bool
}

variable "ec2_root_volume_size" {
  type = number
}

variable "ec2_root_volume_type" {
  type = string
}

variable "ec2_encrypted" {
  type = bool
}

variable "ec2_delete_on_termination" {
  type = bool
}

### SQS
variable "sqs_name" {
  type = string
}

variable "sqs_delay_seconds" {
  type = number
}

variable "sqs_max_message_size" {
  type = number
}

variable "sqs_message_retention_seconds" {
  type = number
}

variable "sqs_receive_wait_time_seconds" {
  type = number
}

variable "sqs_visibility_timeout_seconds" {
  type = number
}

variable "sqs_max_receive_count" {
  type = number
}

### RDS Postgres
variable "rds_database_instances" {
  type = list(object({
    name     = string
    db_name  = string
    username = string
    password = string
  }))
  description = "List of RDS instance definitions. The password field can be left empty and will be filled from the per-database password variables."
}

variable "rds_password_auth_db" {
  type        = string
  sensitive   = true
  description = "Master password for the auth_db RDS instance (set via TF_VAR_rds_password_auth_db)."
}

variable "rds_password_flags_db" {
  type        = string
  sensitive   = true
  description = "Master password for the flags_db RDS instance (set via TF_VAR_rds_password_flags_db)."
}

variable "rds_password_targeting_db" {
  type        = string
  sensitive   = true
  description = "Master password for the targeting_db RDS instance (set via TF_VAR_rds_password_targeting_db)."
}

variable "rds_allocated_storage" {
  type = number
}

variable "rds_instance_class" {
  type = string
}

variable "rds_engine" {
  type = string
}

variable "rds_engine_version" {
  type = string
}

variable "rds_parameter_group_name" {
  type = string
}

variable "rds_skip_final_snapshot" {
  type = bool
}

variable "rds_subnet_name" {
  type = string
}

variable "rds_apply_immediately" {
  type = bool
}

### EKS
variable "eks_cluster_name" {
  type = string
}

variable "eks_cluster_version" {
  type = string
}

variable "eks_node_groups" {
  type = list(object({
    name          = string
    instance_type = string
    desired_size  = number
    min_size      = number
    max_size      = number
  }))
}

variable "eks_role_arn" {
  type = string
}

variable "eks_capacity_type" {
  type = string
}

### DYNAMODB
variable "dynamodb_table_name" {
  type = string
}

variable "dynamodb_billing_mode" {
  type = string
}

variable "dynamodb_read_capacity" {
  type = number
}

variable "dynamodb_write_capacity" {
  type = number
}


variable "dynamodb_hash_key" {
  type = string
}

variable "dynamodb_range_key" {
  type = string
}

variable "dynamodb_attributes" {
  type = list(object({
    name = string
    type = string
  }))
}

### REDIS
variable "redis_cluster_id" {
  type = string
}

variable "redis_engine" {
  type = string
}

variable "redis_node_type" {
  type = string
}

variable "redis_num_cache_nodes" {
  type = number
}

variable "redis_parameter_group_name" {
  type = string
}

variable "redis_port" {
  type = number
}

variable "redis_subnet_group_name" {
  type = string
}

### ECR
variable "ecr_repositories" {
  type = list(string)
}