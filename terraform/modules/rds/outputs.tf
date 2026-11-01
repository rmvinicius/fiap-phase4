output "database_endpoints" {
  value = { for k, v in aws_db_instance.rds : k => v.endpoint }
}

output "database_arns" {
  value = { for k, v in aws_db_instance.rds : k => v.arn }
}