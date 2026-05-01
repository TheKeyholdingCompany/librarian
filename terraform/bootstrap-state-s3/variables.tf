variable "region" {
  type        = string
  default     = "eu-west-1"
  description = "AWS region for the state bucket"
}

variable "state_bucket_name" {
  type        = string
  default     = "tkc-librarian-terraform-state"
  description = "Name of the S3 bucket for Terraform state"
}
