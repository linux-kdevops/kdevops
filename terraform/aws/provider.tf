terraform {
  required_providers {
    template = {
      source = "hashicorp/template"
      # any non-beta version >= 2.1.0 and < 2.2, e.g. 2.1.2
      version = "~>2.1"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.93.0"
    }
  }
}

provider "aws" {
  profile                  = var.aws_profile
  region                   = var.aws_region
  shared_config_files      = [var.aws_shared_config_file]
  shared_credentials_files = [var.aws_shared_credentials_file]
}
