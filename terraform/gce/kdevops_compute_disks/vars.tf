variable "cd_disk_count" {
  description = "Count of attached disks per instance"
  type        = number
}

variable "cd_disk_iops" {
  description = "Provisioned IOPS for each attached disk"
  type        = number
}

variable "cd_disk_size" {
  description = "Size of each attached disk, in GB"
  type        = number
}

variable "cd_disk_throughput" {
  description = "Provisioned throughput for each attached disk"
  type        = number
}

variable "cd_disk_type" {
  description = "Performance class of attached disks"
  type        = string
}

variable "cd_instance_id" {
  description = "Instance ID of instance to which to attach disks"
  type        = string
}

variable "cd_instance_name" {
  description = "Instance name of instance to which to attach disks"
  type        = string
}

variable "cd_zone" {
  description = "Availability zone in which disks are to reside"
  type        = string
}
