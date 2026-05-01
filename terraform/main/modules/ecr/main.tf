resource "aws_ecr_repository" "api" {
  name                 = "${var.name}-${var.env}-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = var.force_delete

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Keep the last 10 images. ECS pulls by `:latest`, so anything older is
# only useful for rollback — and 10 covers a couple of weeks of deploys.
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

variable "name" { type = string }
variable "env" { type = string }
variable "force_delete" {
  type    = bool
  default = false
}

output "api_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "api_repository_arn" {
  value = aws_ecr_repository.api.arn
}
