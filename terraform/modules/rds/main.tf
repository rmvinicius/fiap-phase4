resource "aws_db_instance" "rds" {
  for_each = { for db in var.rds_database_instances : db.name => db }

  allocated_storage      = var.rds_allocated_storage
  db_name                = each.value.db_name
  db_subnet_group_name   = aws_db_subnet_group.rds-subnet.name
  engine                 = var.rds_engine
  engine_version         = var.rds_engine_version
  identifier             = each.value.name
  instance_class         = var.rds_instance_class
  username               = each.value.username
  password               = each.value.password
  parameter_group_name   = var.rds_parameter_group_name
  skip_final_snapshot    = var.rds_skip_final_snapshot
  vpc_security_group_ids = var.rds_vpc_security_group_ids
  apply_immediately      = var.rds_apply_immediately

  tags = {
    Name        = each.value.db_name
    Environment = var.environment
  }
}

resource "aws_db_subnet_group" "rds-subnet" {
  name       = var.rds_subnet_name
  subnet_ids = var.rds_subnet_ids

  tags = {
    Name        = var.rds_subnet_name
    Environment = var.environment
  }
}