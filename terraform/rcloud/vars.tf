variable "rcloud_api_url" {
  description = "rcloud REST API server URL"
  type        = string
}

variable "rcloud_base_image" {
  description = "Base image name to use for VMs (must exist in rcloud server's base images directory)"
  type        = string
}
