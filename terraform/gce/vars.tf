variable "gce_project" {
  description = "Your project name"
  type        = string
}

variable "credentials" {
  description = "Path to the your service account json credentials file"
  type        = string
}

variable "gce_region" {
  description = "Geographic Region"
  type        = string
}

variable "gce_zone" {
  description = "Availability zone"
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
