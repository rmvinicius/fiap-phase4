variable "environment" {
  type = string
}

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

variable "redis_subnet_ids" {
  type = list(string)
}

variable "redis_subnet_group_name" {
  type = string
}

variable "redis_security_group_ids" {
  type = list(string)
}