resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-${var.env}"
  subnet_ids = var.private_subnet_ids
  tags       = { Name = "${var.name}-${var.env}-db-subnet-group" }
}

# Customer-managed KMS key for storage encryption. Independent rotation and
# audit surface from the AWS-managed key. Setting `storage_encrypted = true`
# from day 1 avoids the snapshot → encrypted-copy → restore migration that
# the coralboards stack had to do retroactively (`storage_encrypted` is
# ForceNew on aws_db_instance).
resource "aws_kms_key" "rds" {
  description             = "${var.name}-${var.env} RDS storage CMK"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${var.name}-${var.env}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

resource "aws_db_instance" "this" {
  identifier = "${var.name}-${var.env}"

  engine         = "postgres"
  engine_version = "16"
  instance_class = var.instance_class

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.security_group_id]

  multi_az                  = false
  publicly_accessible       = false
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.name}-${var.env}-final"

  backup_retention_period = 7
  deletion_protection     = true

  tags = { Name = "${var.name}-${var.env}-db" }
}

variable "name" { type = string }
variable "env" { type = string }

variable "db_name" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  type = string
}

variable "db_username" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "instance_class" {
  type    = string
  default = "db.t4g.micro"
}

output "endpoint" {
  value = aws_db_instance.this.endpoint
}

output "address" {
  value = aws_db_instance.this.address
}

output "port" {
  value = aws_db_instance.this.port
}

output "kms_key_arn" {
  value = aws_kms_key.rds.arn
}

output "kms_key_id" {
  value = aws_kms_key.rds.key_id
}
