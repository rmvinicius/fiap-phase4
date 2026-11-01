# Bucket S3 com versionamento e criptografia
export BUCKET_NAME="tfstate-tech-challenge-lab-aws"

aws s3api create-bucket --bucket $BUCKET_NAME --region us-east-1
aws s3api put-bucket-versioning --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket $BUCKET_NAME \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  
# Build local terraform image
docker build -t terraform-local:1.0 .

# Export AWS Lab variables
export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""
export AWS_SESSION_TOKEN=""

# Run the container to execute terraform
docker run -it -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" -v ./:/workspace terraform-local:1.0 /bin/bash

# Export variables for postgres
export TF_VAR_rds_password_auth_db=""
export TF_VAR_rds_password_flags_db=""
export TF_VAR_rds_password_targeting_db=""

# terraform commands
terraform init -backend-config="bootstrap/remote/dev-backend.tfvars"
use --reconfigure ### Usar somente para alterar ambientes

terraform validate

terraform plan -var-file="environment/dev.tfvars"

terraform apply -var-file="environment/dev.tfvars"

terraform plan -destroy -var-file="environment/dev.tfvars"
terraform destroy -var-file="environment/dev.tfvars"
