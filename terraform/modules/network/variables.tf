variable "environment" {
  type = string
}
variable "vpc_name" {
  type = string
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

variable "eip_enable_nat_gateway" {
  type        = bool
  default     = true
  description = "Enable NAT Gateway for private subnets"
}

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