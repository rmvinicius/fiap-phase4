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
  principal_arn = var.eks_principal_arn
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

# OIDC provider required for IRSA. Without it the EBS CSI add-on
# cannot create its default service-account role.
data "aws_eks_cluster" "this" {
  name = aws_eks_cluster.main.name
}

resource "aws_iam_openid_connect_provider" "this" {
  url           = data.aws_eks_cluster.this.identity_oidc_config[0].issuer
  client_id_list = ["sts.amazonaws.com"]
  tags = {
    Name        = "${var.eks_cluster_name}-oidc"
    Environment = var.environment
  }
}

# IRSA role assumed by the CSI controller service account.
resource "aws_iam_role" "ebs_csi" {
  name = "${var.eks_cluster_name}-ebs-csi"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.this.arn
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = "${aws_iam_openid_connect_provider.this.url}:sub"
          = "system:serviceaccount:kube-system:ebs-csi-controller-sa"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ebs_csi" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEKS_EBS_CSI_DriverPolicy"
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = "v1.67.2-eksbuild.1"
  resolve_conflicts_on_update = "PRESERVE"
  service_account_role_arn    = aws_iam_role.ebs_csi.arn
}