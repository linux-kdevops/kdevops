variable "client_certificate_path" {
  description = "Path to the service principal PFX file for this application"
  type        = string
}

variable "client_certificate_password" {
  description = "The password to the service principal PFX file"
  type        = string
}

variable "application_id" {
  description = "The application ID"
  type        = string
}

variable "subscription_id" {
  description = "Your subscription ID"
  type        = string
}

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
}

variable "resource_location" {
  description = "Resource location"
  type        = string
}

variable "vmsize" {
  description = "VM size"
  type        = string
}

variable "image_publisher" {
  description = "Storage image publisher"
  type        = string
}

variable "image_offer" {
  description = "Storage image offer"
  type        = string
}

variable "image_sku" {
  description = "Storage image sku"
  type        = string
}

variable "image_version" {
  description = "Storage image version"
  type        = string
}

variable "managed_disks_per_instance" {
  description = "Count of managed disks per VM instance"
  type        = number
}

variable "managed_disks_size" {
  description = "Size of each managed disk, in gibibytes"
  type        = number
}
