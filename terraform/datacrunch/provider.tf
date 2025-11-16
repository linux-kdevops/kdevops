terraform {
  required_version = ">= 1.0"
  required_providers {
    datacrunch = {
      source = "linux-kdevops/datacrunch"
      version = "~> 0.0.3"
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.3"
    }
  }
}

# Extract OAuth2 credentials from credentials file
data "external" "datacrunch_credentials" {
  program = ["python3", "${path.module}/extract_api_key.py", var.datacrunch_api_key_file]
}

provider "datacrunch" {
  # OAuth2 client credentials extracted from credentials file
  client_id     = data.external.datacrunch_credentials.result["client_id"]
  client_secret = data.external.datacrunch_credentials.result["client_secret"]
  server_url    = "https://api.datacrunch.io/v1"
}
