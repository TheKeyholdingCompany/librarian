variable "name" {
  type        = string
  description = "Service name (used for resource naming and tagging)"
}

variable "env" {
  type        = string
  description = "Deployment environment (e.g., services)"
}

# --- DNS / TLS ---

variable "domain_name" {
  type        = string
  description = "Fully qualified domain name for the app (e.g. librarian.services.keyholding.com)"
}

variable "hosted_zone_domain" {
  type        = string
  description = "Route 53 hosted zone domain (e.g. services.keyholding.com)"
}

# --- Database ---

variable "db_name" {
  type        = string
  default     = "librarian"
  description = "Postgres database name on the RDS instance"
}

# --- S3 uploads ---

variable "uploads_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for image uploads (e.g. tkc-librarian-uploads-services)"
}

# --- Lifecycle ---

variable "force_destroy" {
  type        = bool
  default     = false
  description = "Allow destroying ECR repositories even when they contain images. Set true only for ad-hoc teardown."
}

# --- CloudFront ---

variable "price_class" {
  type        = string
  default     = "PriceClass_100"
  description = "CloudFront price class (PriceClass_100 = US/EU, PriceClass_200 = US/EU/Asia, PriceClass_All = all)"
}
