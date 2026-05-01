variable "bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name (e.g. tkc-librarian-uploads-services)"
}

variable "name" {
  type        = string
  description = "Service name (used for tagging)"
}

variable "env" {
  type        = string
  description = "Deployment environment (used for tagging)"
}

variable "public_read_prefix" {
  type        = string
  default     = "books/"
  description = "Key prefix that is readable anonymously over HTTPS. Other prefixes stay private."
}

variable "cors_allowed_origins" {
  type        = list(string)
  default     = ["*"]
  description = "Origins allowed to PUT directly via presigned URLs. '*' is acceptable because the presigned URL itself is the access control."
}
