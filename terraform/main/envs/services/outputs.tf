output "ecr_api_repository_url" {
  value = module.app.ecr_api_repository_url
}

output "cloudfront_distribution_id" {
  value = module.app.cloudfront_distribution_id
}

output "alb_dns_name" {
  value = module.app.alb_dns_name
}

output "ecs_cluster_name" {
  value = module.app.ecs_cluster_name
}

output "ecs_service_name" {
  value = module.app.ecs_service_name
}
