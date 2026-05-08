# Look up the Route 53 hosted zone
data "aws_route53_zone" "this" {
  name         = var.hosted_zone_domain
  private_zone = false
}

data "aws_region" "current" {}

locals {
  region = data.aws_region.current.id
}

# ── VPC ─────────────────────────────────────────────────────

module "vpc" {
  source = "./modules/vpc"
  name   = var.name
  env    = var.env
}

# ── ECR ─────────────────────────────────────────────────────

module "ecr" {
  source       = "./modules/ecr"
  name         = var.name
  env          = var.env
  force_delete = var.force_destroy
}

# ── Secrets ─────────────────────────────────────────────────

module "secrets" {
  source = "./modules/secrets"
  name   = var.name
  env    = var.env
}

# ── RDS ─────────────────────────────────────────────────────

module "rds" {
  source             = "./modules/rds"
  name               = var.name
  env                = var.env
  db_name            = var.db_name
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_id  = module.vpc.rds_security_group_id
  db_username        = module.secrets.rds_username
  db_password        = module.secrets.rds_password
}

# ── ALB ─────────────────────────────────────────────────────

module "alb" {
  source            = "./modules/alb"
  name              = var.name
  env               = var.env
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  security_group_id = module.vpc.alb_security_group_id
}

# ── S3 uploads ──────────────────────────────────────────────

module "s3_uploads" {
  source      = "./modules/s3_uploads"
  bucket_name = var.uploads_bucket_name
  name        = var.name
  env         = var.env
}

# ── ECS ─────────────────────────────────────────────────────

module "ecs" {
  source = "./modules/ecs"
  name   = var.name
  env    = var.env
  region = local.region

  api_image         = module.ecr.api_repository_url
  public_subnet_ids = module.vpc.public_subnet_ids

  ecs_security_group_id = module.vpc.ecs_security_group_id
  api_target_group_arn  = module.alb.api_target_group_arn

  secret_arns = [
    module.secrets.rds_secret_arn,
    module.secrets.flask_secret_arn,
    module.secrets.oidc_secret_arn,
  ]
  rds_secret_arn      = module.secrets.rds_secret_arn
  flask_secret_arn    = module.secrets.flask_secret_arn
  oidc_secret_arn     = module.secrets.oidc_secret_arn
  secrets_kms_key_arn = module.secrets.secrets_kms_key_arn

  oidc_issuer_url = var.oidc_issuer_url
  oidc_client_id  = var.oidc_client_id
  oidc_admin_role = var.oidc_admin_role

  db_address  = module.rds.address
  db_port     = module.rds.port
  db_username = module.secrets.rds_username
  db_name     = var.db_name

  s3_uploads_bucket          = module.s3_uploads.bucket_name
  s3_uploads_public_base_url = "https://${module.s3_uploads.bucket_regional_domain_name}"
}

# Grant the running container PutObject on the uploads prefix. The policy
# document lives in the s3_uploads module (it knows the bucket ARN); the
# attachment lives here because both modules' outputs are visible at root.
resource "aws_iam_role_policy_attachment" "ecs_task_s3_uploads" {
  role       = module.ecs.task_role_name
  policy_arn = module.s3_uploads.put_object_policy_arn
}

# ── CloudFront ──────────────────────────────────────────────
#
# Single origin: the ALB. CloudFront here is pure custom-domain TLS
# termination + edge layer. No `ordered_cache_behavior` because Flask static
# files (book covers, default SVG) don't have content hashes — we'd need to
# invalidate on every deploy. Default behaviour caches nothing.

module "cloudfront" {
  source = "./modules/cloudfront"
  name   = var.name
  env    = var.env

  domain_name     = var.domain_name
  route53_zone_id = data.aws_route53_zone.this.zone_id
  price_class     = var.price_class
  alb_dns_name    = module.alb.dns_name

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }
}
