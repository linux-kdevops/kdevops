variable "lambdalabs_api_key_file" {
  description = "Path to file containing Lambda Labs API key"
  type        = string
  default     = "~/.lambdalabs/credentials"
}

variable "lambdalabs_region" {
  description = "Lambda Labs region to deploy resources"
  type        = string
  default     = "us-tx-1"
}

variable "lambdalabs_instance_type" {
  description = "Lambda Labs instance type"
  type        = string
  default     = "gpu_1x_a10"
}

variable "lambdalabs_ssh_key_name" {
  description = "Name of the existing SSH key in Lambda Labs to use for instances"
  type        = string
}

# NOTE: Lambda Labs provider doesn't support OS image selection
# All instances use Ubuntu 22.04 by default
# This variable is kept for compatibility but has no effect
#variable "image_name" {
#  description = "OS image to use for instances"
#  type        = string
#  default     = "ubuntu-22.04"
#}


variable "ssh_config_name" {
  description = "The name of your ssh_config file"
  type        = string
  default     = "../.ssh/config"
}

variable "ssh_config_use" {
  description = "Set this to false to disable the use of the ssh config file"
  type        = bool
  default     = true
}

variable "ssh_config_genkey" {
  description = "Set this to true to enable regenerating an ssh key"
  type        = bool
  default     = false
}

# NOTE: Lambda Labs provider doesn't support storage volume management
# Instances come with their default storage only
# These variables are kept for compatibility but have no effect
#variable "extra_storage_size" {
#  description = "Size of extra storage volume in GB"
#  type        = number
#  default     = 0
#}
#
#variable "extra_storage_enable" {
#  description = "Enable extra storage volume"
#  type        = bool
#  default     = false
#}
