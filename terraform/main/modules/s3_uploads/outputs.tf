output "bucket_name" {
  value       = aws_s3_bucket.this.bucket
  description = "S3 bucket name"
}

output "bucket_regional_domain_name" {
  value       = aws_s3_bucket.this.bucket_regional_domain_name
  description = "Regional virtual-hosted-style hostname (e.g. <bucket>.s3.<region>.amazonaws.com). Use as the public base URL for serving images."
}

output "put_object_policy_arn" {
  value       = aws_iam_policy.put_object.arn
  description = "Attach this to the ECS task role to grant PutObject on the public prefix."
}
