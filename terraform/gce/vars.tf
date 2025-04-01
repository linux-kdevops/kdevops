variable "project" {
  description = "Your project name"
  type        = string
}

variable "credentials" {
  description = "Path to the your service account json credentials file"
  type        = string
}

# https://cloud.google.com/compute/docs/regions-zones/
# This is LA, California
variable "region" {
  description = "Region location"
  type        = string
}

# https://cloud.google.com/compute/docs/machine-types
variable "machine_type" {
  description = "Machine type"
  type        = string
}

variable "image_name" {
  description = "Name of image to use"
  type        = string
}

variable "scratch_disk_interface" {
  description = "The type of interface for the scratch disk, SCSI, or NVME"
  type        = string
}
