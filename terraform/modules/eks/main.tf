resource "aws_eks_cluster" "main" {
  name     = var.eks_cluster_name
  role_arn = var.eks_role_arn
  version  = var.eks_cluster_version

  access_config {
    authentication_mode = "API"
  }

  vpc_config {
    subnet_ids              = var.eks_subnet_ids
    endpoint_public_access  = false
    endpoint_private_access = true
    security_group_ids      = var.eks_security_group_ids
  }

  tags = {
    Name        = var.eks_cluster_name
    Environment = var.environment
  }
}

# Node groups
resource "aws_eks_node_group" "nodes" {
  for_each = { for ng in var.eks_node_groups : ng.name => ng }

  cluster_name    = aws_eks_cluster.main.name
  node_group_name = each.value.name
  node_role_arn   = var.eks_role_arn
  subnet_ids      = var.eks_subnet_ids

  scaling_config {
    desired_size = each.value.desired_size
    min_size     = each.value.min_size
    max_size     = each.value.max_size
  }

  update_config {
    max_unavailable = 1
  }

  instance_types = [each.value.instance_type]
  capacity_type  = var.eks_capacity_type

  tags = {
    Name        = each.value.name
    Environment = var.environment
  }
}

resource "aws_eks_access_entry" "voclabs" {
  cluster_name  = aws_eks_cluster.main.name
  principal_arn = "arn:aws:iam::598450975126:role/voclabs"
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "voclabs_admin" {
  cluster_name  = aws_eks_cluster.main.name
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
  principal_arn = aws_eks_access_entry.voclabs.principal_arn

  access_scope {
    type = "cluster"
  }
}