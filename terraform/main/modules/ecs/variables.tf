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

variable "oidc_secret_arn" {
  type        = string
  description = "Secrets Manager ARN for the Keycloak OIDC client_secret"
}

variable "oidc_issuer_url" {
  type        = string
  description = "OIDC issuer URL (Keycloak realm root, e.g. https://login.keyholding.com/realms/<realm>)"
}

variable "oidc_client_id" {
  type        = string
  description = "OIDC client_id registered in Keycloak for this app"
}

variable "oidc_admin_role" {
  type        = string
  default     = "library-admin"
  description = "Keycloak realm role name that grants admin in this app"
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

variable "s3_uploads_bucket" {
  type        = string
  description = "Name of the S3 bucket the API uses for image uploads (passed in as S3_BUCKET env var)"
}

variable "s3_uploads_public_base_url" {
  type        = string
  description = "Public HTTPS base URL for serving uploaded images (passed in as S3_PUBLIC_BASE_URL env var). Trailing slash optional."
}
