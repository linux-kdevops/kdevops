variable "datacrunch_api_key_file" {
  description = "Path to file containing DataCrunch API key (client secret)"
  type        = string
  default     = "~/.datacrunch/credentials"
}

variable "datacrunch_location" {
  description = "DataCrunch datacenter location code"
  type        = string
  default     = "FIN-01"
}

variable "datacrunch_instance_type" {
  description = "DataCrunch instance type"
  type        = string
  default     = "1x.h100.pcie"
}

variable "datacrunch_image" {
  description = "DataCrunch OS image ID"
  type        = string
  default     = "ubuntu-22.04-pytorch"
}

variable "datacrunch_ssh_key_name" {
  description = "Name for the SSH key in DataCrunch"
  type        = string
}

variable "datacrunch_ssh_key_id" {
  description = "ID of existing SSH key in DataCrunch (if empty, a new key will be created)"
  type        = string
  default     = ""
}

variable "ssh_config_name" {
  description = "The name of your ssh_config file"
  type        = string
  default     = "~/.ssh/config"
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
