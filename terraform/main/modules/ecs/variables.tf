variable "name" { type = string }
variable "env" { type = string }
variable "region" { type = string }

variable "api_image" {
  type        = string
  description = "ECR repo URL (no tag) for the API container"
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "ecs_security_group_id" {
  type = string
}

variable "api_target_group_arn" {
  type = string
}

variable "secret_arns" {
  type        = list(string)
  description = "ARNs of every Secrets Manager secret the execution role may read"
}

variable "rds_secret_arn" {
  type        = string
  description = "Secrets Manager ARN for the RDS master credentials"
}

variable "flask_secret_arn" {
  type        = string
  description = "Secrets Manager ARN for the Flask SECRET_KEY"
}

variable "secrets_kms_key_arn" {
  type        = string
  description = "KMS key ARN that encrypts the Secrets Manager secrets"
}

variable "db_address" {
  type = string
}

variable "db_port" {
  type = number
}

variable "db_username" {
  type = string
}

variable "db_name" {
  type = string
}
