terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "eu-west-1"
  default_tags {
    tags = {
      Project     = local.name
      Environment = local.env
      Area        = "Internal"
      SubArea     = "Tech Enablers"
      Team        = "Application Development"
      ManagedBy   = "terraform"
    }
  }
}

# Aliased provider for CloudFront ACM certs (must be in us-east-1).
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
  default_tags {
    tags = {
      Project     = local.name
      Environment = local.env
      Area        = "Internal"
      SubArea     = "Tech Enablers"
      Team        = "Application Development"
      ManagedBy   = "terraform"
    }
  }
}
