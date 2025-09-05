terraform {
  required_version = ">= 0.12.6"
  required_providers {
    oci = {
      source = "hashicorp/oci"
      version = "> 7"
    }
  }
}

provider "oci" {
  auth                = "APIKey"
  config_file_profile = var.oci_config_file_profile
  region              = var.oci_region
}
