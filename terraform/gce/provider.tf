terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~>5"
    }
  }
}

provider "google" {
  credentials = file(var.credentials)
  project     = var.project
  region      = var.region
}
