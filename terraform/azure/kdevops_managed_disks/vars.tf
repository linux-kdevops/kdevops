variable "md_disk_count" {
  type        = number
  description = "Count of managed disks to attach to the virtual machine"
}

variable "md_disk_size" {
  type        = number
  description = "Size of each managed disk, in gibibytes"
}

variable "md_location" {
  type        = string
  description = "Azure resource location"
}

variable "md_resource_group_name" {
  type        = string
  description = "Azure resource group name"
}

variable "md_virtual_machine_id" {
  type        = string
  description = "Azure ID of the virtual machine to attach the disks to"
}

variable "md_virtual_machine_name" {
  type        = string
  description = "Name of the virtual machine to attach the disks to"
}
