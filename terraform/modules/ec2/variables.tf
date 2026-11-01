variable "environment" {
  type = string
}

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

variable "ec2_subnet_id" {
  type = string
}

variable "ec2_associate_public_ip_address" {
  type = bool
}

variable "ec2_security_group_ids" {
  type = list(string)
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