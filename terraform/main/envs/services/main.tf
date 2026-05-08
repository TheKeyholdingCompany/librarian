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

  uploads_bucket_name = "tkc-librarian-uploads-services"

  # Keycloak realm name needs to match the realm provisioned by the
  # keycloak-config repo. `oidc_client_id` and the Keycloak-side client
  # registration must agree.
  oidc_issuer_url = "https://login.keyholding.com/realms/keyholding"
  oidc_client_id  = "tkc-library"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }
}
