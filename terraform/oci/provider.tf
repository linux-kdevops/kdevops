terraform {
}

provider "oci" {
  config_file_profile = var.oci_config_file_profile
  region              = var.oci_region
}
