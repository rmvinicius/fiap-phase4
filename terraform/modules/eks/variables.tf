variable "environment" {
  type = string
}

variable "eks_cluster_name" {
  type = string
}

variable "eks_cluster_version" {
  type = string
}

variable "eks_subnet_ids" {
  type = list(string)
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

variable "eks_security_group_ids" {
  type = list(string)
}

variable "eks_capacity_type" {
  type = string
}
