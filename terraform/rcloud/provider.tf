terraform {
  required_providers {
    rcloud = {
      source  = "local/rcloud/rcloud"
      version = "~> 1.0"
    }
  }
}

provider "rcloud" {
  endpoint             = var.rcloud_api_url
  ssh_user             = var.ssh_config_user
  ssh_public_key_file  = var.ssh_config_pubkey_file
}
