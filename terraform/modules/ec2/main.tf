resource "aws_instance" "ec2" {
  ami                         = var.ec2_ami_id
  instance_type               = var.ec2_instance_type
  subnet_id                   = var.ec2_subnet_id
  associate_public_ip_address = var.ec2_associate_public_ip_address
  vpc_security_group_ids      = var.ec2_security_group_ids
  key_name                    = var.ec2_key_name
  monitoring                  = var.ec2_monitoring

  root_block_device {
    volume_size           = var.ec2_root_volume_size
    volume_type           = var.ec2_root_volume_type
    encrypted             = var.ec2_encrypted
    delete_on_termination = var.ec2_delete_on_termination
  }

  tags = {
    Name        = var.ec2_instance_name
    Environment = var.environment
  }
}