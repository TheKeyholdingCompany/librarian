output "ecr_api_repository_url" {
  value       = module.ecr.api_repository_url
  description = "ECR repo URL for the API container; used by the deploy workflow to push and tag images."
}

output "cloudfront_distribution_id" {
  value       = module.cloudfront.distribution_id
  description = "CloudFront distribution ID; used by the deploy workflow to issue invalidations."
}

output "alb_dns_name" {
  value       = module.alb.dns_name
  description = "Internal ALB DNS name; CloudFront's only origin."
}

output "ecs_cluster_name" {
  value       = module.ecs.cluster_name
  description = "ECS cluster name; used by the deploy workflow for force-new-deployment."
}

output "ecs_service_name" {
  value       = module.ecs.service_name
  description = "ECS service name; used by the deploy workflow for force-new-deployment."
}
