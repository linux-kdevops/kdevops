variable "vol_availability_domain" {
  description = "Name of the vailability_domain in which to create the volumes"
  type        = string
}

variable "vol_compartment_ocid" {
  description = "OCID of the compartment in which to create the volumes"
  type        = string
}

variable "vol_instance_id" {
  description = "ID of the instance to which the volumes are to be attached"
  type        = string
}

variable "vol_instance_name" {
  description = "Name of the instance to which the volumes are to be attached"
  type        = string
}

variable "vol_volume_count" {
  description = "Count of volumes to attach to the instance "
  type        = number
}

variable "vol_volume_size" {
  description = "Size of each volume, in gibibytes"
  type        = number
}

variable "vol_vpus_per_gb" {
  description = "Volume performance units"
  type        = number
}
