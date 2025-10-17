# Generic import of data.
#
# Terraform will process all *.tf files in alphabetical order, but the
# order does not matter as terraform is declarative.

variable "ssh_config" {
  description = "Path to SSH config update script"
  default     = "../scripts/update_ssh_config_lambdalabs.py"
}

variable "ssh_config_update" {
  description = "Set this to true if you want terraform to update your ssh_config with the provisioned set of hosts"
  type        = bool
}

variable "ssh_config_user" {
  description = "If ssh_config_update is true, and this is set, it will be the user set for each host on your ssh config"
  default     = "ubuntu"
}

variable "ssh_config_pubkey_file" {
  description = "Path to the ssh public key file"
  default     = "~/.ssh/kdevops_terraform.pub"
}

variable "ssh_config_privkey_file" {
  description = "Path to the ssh private key file for authentication"
  default     = "~/.ssh/kdevops_terraform"
}

variable "ssh_config_use_strict_settings" {
  description = "Whether or not to use strict settings on ssh_config"
  type        = bool
}

variable "ssh_config_backup" {
  description = "Set this to true if you want to backup your ssh_config per update"
  type        = bool
}

variable "ssh_config_kexalgorithms" {
  description = "If set, this sets a custom ssh kexalgorithms"
  default     = ""
}

variable "ssh_config_port" {
  description = "SSH port to use for remote connections"
  type        = number
  default     = 22
}

variable "ssh_config_name" {
  description = "SSH config file to update (allows per-directory configs)"
  type        = string
  default     = "~/.ssh/config"
}

locals {
  kdevops_num_boxes = length(var.kdevops_nodes)
}
