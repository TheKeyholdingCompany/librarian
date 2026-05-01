locals {
  name = "librarian"
  env  = "services"

  hosted_zone_domain = "services.keyholding.com"
  domain_name        = "librarian.services.keyholding.com"
}

module "app" {
  source = "../../"

  name = local.name
  env  = local.env

  hosted_zone_domain = local.hosted_zone_domain
  domain_name        = local.domain_name

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }
}
