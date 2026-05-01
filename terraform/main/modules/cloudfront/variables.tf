variable "name" {
  type = string
}

variable "env" {
  type = string
}

variable "domain_name" {
  type        = string
  description = "Fully qualified domain name served by CloudFront (e.g. librarian.services.keyholding.com)"
}

variable "route53_zone_id" {
  type        = string
  description = "Route 53 hosted zone ID for the parent domain"
}

variable "price_class" {
  type    = string
  default = "PriceClass_100"
}

variable "alb_dns_name" {
  type        = string
  description = "DNS name of the ALB; the only origin for this distribution"
}
