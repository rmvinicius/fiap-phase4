output "repository_urls" {
  value = {
    for repo in aws_ecr_repository.repositories :
    repo.name => repo.repository_url
  }
}