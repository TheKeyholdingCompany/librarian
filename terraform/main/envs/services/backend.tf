terraform {
  backend "s3" {
    bucket       = "tkc-librarian-terraform-state"
    key          = "librarian/terraform.tfstate"
    region       = "eu-west-1"
    encrypt      = true
    use_lockfile = true
  }
}
