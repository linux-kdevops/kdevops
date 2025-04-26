terraform {
  required_version = ">= 0.12.6"
  required_providers {
    oci = {
      source = "oracle/oci"
      version = "~> 6"
    }
  }
}

provider "oci" {
  auth                = "APIKey"
  config_file_profile = var.oci_config_file_profile
  region              = var.oci_region
}
