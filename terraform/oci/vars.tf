variable "oci_ad_number" {
  description = "Suffix number of availability domain"
  type        = number
}

variable "oci_assign_public_ip" {
  description = "Assign public IP to the instance"
  type        = bool
}

variable "oci_compartment_name" {
  description = "Name of compartment in which to create resources"
  type        = string
}

variable "oci_config_file_profile" {
  description = "Entry in ~/.oci/config to use for API authentication"
  type        = string
}

variable "oci_data_volume_device_file_name" {
  description = "Data volume's device file name"
  type        = string
}

variable "oci_instance_flex_memory_in_gbs" {
  default     = null
  description = "The total amount of memory available to the instance, in gigabytes."
  type        = number
}

variable "oci_instance_flex_ocpus" {
  default     = null
  description = "The total number of OCPUs available to the instance."
  type        = number
}

variable "oci_os_image_ocid" {
  description = "OCID of OS image"
  type        = string
}

variable "oci_region" {
  description = "An OCI region"
  type        = string
}

variable "oci_shape" {
  description = "Shape name"
  type        = string
}

variable "oci_sparse_volume_device_file_name" {
  description = "Sparse volume's device file name"
  type        = string
}

variable "oci_subnet_ocid" {
  default     = null
  description = "Subnet OCID"
  type        = string
}

variable "oci_tenancy_ocid" {
  description = "OCID of your tenancy"
  type        = string
}

variable "oci_user_fingerprint" {
  default     = null
  description = "Fingerprint for the key pair being used"
  type        = string
}

variable "oci_user_ocid" {
  default     = null
  description = "OCID of the user calling the API"
  type        = string
}

variable "oci_user_private_key_path" {
  default     = null
  description = "The path of the private key stored on your computer"
  type        = string
}

variable "oci_use_existing_vcn" {
  description = "Use a pre-existing VCN"
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

variable "oci_vpus_per_gb" {
  description = "Volume performance units"
  type        = number
}
