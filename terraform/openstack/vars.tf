# This is a relatively new feature, reading cloud.yaml and friends. Even
# though older openstack solutions don't support this, we keep things simple
# and ask you to use these files for now.
#
# If its a public cloud we may add support for extra processing / output
# for each one on its respective cloudname.tf file.
variable "openstack_cloud" {
  description = "Name of your cloud on clouds.yaml"
  default     = "minicloud"
}

variable "ssh_pubkey_name" {
  description = "Name of already existing pubkey or the new one you are about to upload, this must be set"
  default     = "kdevops-pubkey"
}

variable "ssh_pubkey_data" {
  description = "The ssh public key data"

  # for instance it coudl be "ssh-rsa AAetcccc"
  default = ""
}

variable "image_name" {
  description = "Type of image"
  default     = "Debian 10 ppc64le"
}

# Note: at least if using minicloud you're allowed 5 instances but only
# 8 cores and 10 GiB of RAM. If you use minicloud.max you max out all
# core limits right away. By default we use here the minicloud.tiny
# to let at you at least create a few instances.
variable "flavor_name" {
  description = "Flavor of image"
  default     = "minicloud.tiny"
}

variable "instance_prefix" {
  description = "The prefix of the VM instance name"
  default     = "my-fun"
}

variable "public_network_name" {
  description = "The name of the network"
  default     = "public"
}
