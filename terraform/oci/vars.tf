variable "oci_config_file_profile" {
  description = "Entry in ~/.oci/config to use for API authentication"
  type        = string
}

variable "oci_region" {
  description = "An OCI region"
  type        = string
}

variable "oci_tenancy_ocid" {
  description = "OCID of your tenancy"
  type        = string
}

variable "oci_availablity_domain" {
  description = "Name of availability domain"
  type        = string
}

variable "oci_compartment_ocid" {
  description = "OCID of compartment"
  type        = string
}

variable "oci_shape" {
  description = "Shape name"
  type        = string
}

variable "oci_instance_flex_ocpus" {
  default     = null
  description = "The total number of OCPUs available to the instance."
  type        = number
}

variable "oci_instance_flex_memory_in_gbs" {
  default     = null
  description = "The total amount of memory available to the instance, in gigabytes."
  type        = number
}

variable "oci_os_image_ocid" {
  description = "OCID of OS image"
  type        = string
}

variable "oci_assign_public_ip" {
  description = "Assign public IP to the instance"
  type        = bool
}

variable "oci_subnet_ocid" {
  description = "Subnet OCID"
  type        = string
}

variable "oci_volumes_enable_extra" {
  description = "Create additional block volumes per instance"
  type        = bool
}

variable "oci_volumes_per_instance" {
  description = "The count of additional block volumes per instance"
  type        = number
}

variable "oci_volumes_size" {
  description = "The size of additional block volumes, in gibibytes"
  type        = number
}

variable "oci_data_volume_display_name" {
  description = "Display name to use for the data volume"
  type        = string
}

variable oci_data_volume_device_file_name {
  description = "Data volume's device file name"
  type        = string
}

variable "oci_sparse_volume_display_name" {
  description = "Display name to use for the sparse volume"
  type        = string
}

variable oci_sparse_volume_device_file_name {
  description = "Sparse volume's device file name"
  type        = string
}
