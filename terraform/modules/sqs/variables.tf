variable "environment" {
  type = string
}

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