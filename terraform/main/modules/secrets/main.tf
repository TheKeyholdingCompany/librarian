resource "random_password" "rds" {
  length  = 32
  special = false
}

# Flask uses SECRET_KEY for session cookie signing and CSRF tokens. Random,
# stable, and sourced from Secrets Manager — never written to git or
# baked into the container image.
resource "random_password" "flask_secret_key" {
  length  = 64
  special = true
}

# Customer-managed KMS key for Secrets Manager. Independent rotation and
# audit surface from the AWS-managed key.
resource "aws_kms_key" "secrets" {
  description             = "${var.name}-${var.env} Secrets Manager CMK"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.name}-${var.env}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# ── RDS master credentials ─────────────────────────────────

resource "aws_secretsmanager_secret" "rds" {
  name                    = "${var.name}-${var.env}/rds-master"
  recovery_window_in_days = 0
  kms_key_id              = aws_kms_key.secrets.arn
}

resource "aws_secretsmanager_secret_version" "rds" {
  secret_id = aws_secretsmanager_secret.rds.id
  secret_string = jsonencode({
    username = local.db_username
    password = random_password.rds.result
  })
}

# ── Flask SECRET_KEY ───────────────────────────────────────

resource "aws_secretsmanager_secret" "flask" {
  name                    = "${var.name}-${var.env}/flask"
  recovery_window_in_days = 0
  kms_key_id              = aws_kms_key.secrets.arn
}

resource "aws_secretsmanager_secret_version" "flask" {
  secret_id = aws_secretsmanager_secret.flask.id
  secret_string = jsonencode({
    secret_key = random_password.flask_secret_key.result
  })
}

locals {
  db_username = "librarian"
}

variable "name" { type = string }
variable "env" { type = string }

output "rds_secret_arn" {
  value = aws_secretsmanager_secret.rds.arn
}

output "rds_username" {
  value = local.db_username
}

output "rds_password" {
  value     = random_password.rds.result
  sensitive = true
}

output "flask_secret_arn" {
  value = aws_secretsmanager_secret.flask.arn
}

output "secrets_kms_key_arn" {
  value = aws_kms_key.secrets.arn
}
