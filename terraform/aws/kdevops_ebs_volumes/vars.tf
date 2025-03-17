variable "vol_availability_zone" {
  description = "AWS availability zone where each volume will reside"
  type        = string
}

variable "vol_count" {
  description = "Count of volumes to attach to the instance"
  type        = number
}

variable "vol_instance_id" {
  description = "Instance ID of the instance to which to attach each volume"
  type        = string
}

variable "vol_iops" {
  description = "Provisioned IOPS for each attached volume"
  type        = number
}

variable "vol_size" {
  description = "Size of each attached volume, in gibibytes"
  type        = number
}

variable "vol_type" {
  description = "Device type of each attached volume"
  type        = string
}
