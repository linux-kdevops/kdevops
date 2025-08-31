terraform {
  required_version = ">= 1.0"
  required_providers {
    lambdalabs = {
      source  = "elct9620/lambdalabs"
      version = "~> 0.3.0"
    }
  }
}

# Extract API key from credentials file
data "external" "lambdalabs_api_key" {
  program = ["python3", "${path.module}/extract_api_key.py", var.lambdalabs_api_key_file]
}

provider "lambdalabs" {
  # API key extracted from credentials file
  api_key = data.external.lambdalabs_api_key.result["api_key"]
}
