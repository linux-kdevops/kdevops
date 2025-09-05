variable "azure_location" {
  description = "Azure resource location"
  type        = string
}

variable "azure_image_offer" {
  description = "OS image offer"
  type        = string
}

variable "azure_image_publisher" {
  description = "OS image publisher"
  type        = string
}

variable "azure_image_sku" {
  description = "OS image SKU"
  type        = string
}

variable "azure_managed_disks_per_instance" {
  description = "Count of managed disks per VM instance"
  type        = number
}

variable "azure_managed_disks_size" {
  description = "Size of each managed disk, in gibibytes"
  type        = number
}

variable "azure_managed_disks_tier" {
  description = "Performance tier of managed disks"
  type        = string
}

variable "azure_resource_group_name" {
  description = "Name of the set of resources for this run"
  type        = string
}

variable "azure_subscription_id" {
  description = "Your Azure subscription ID"
  type        = string
}

variable "azure_vmsize" {
  description = "VM size"
  type        = string
}
