variable "aws_ami_arch" {
  description = "An AWS AMI image instruction set architecture"
  type        = string
}

variable "aws_ami_owner" {
  description = "An AWS AMI image owner or owner alias"
  type        = string
}

variable "aws_availability_zone" {
  description = "Your preferred AWS availability zone"
  type        = string
}

variable "aws_ebs_volumes_per_instance" {
  description = "Number of EBS volumes to create per instance"
  type        = number
}

variable "aws_ebs_volume_iops" {
  description = "IOPS reserved for each EBS volume"
  type        = number
  default     = null
}

variable "aws_ebs_volume_size" {
  description = "Size in GiB for each of the volumes"
  type        = number
}

variable "aws_ebs_volume_throughput" {
  description = "Throughput reserved for each EBS volume"
  type        = number
  default     = null
}

variable "aws_ebs_volume_type" {
  description = "Type of each of the EBS volumes"
  type        = string
}

variable "aws_instance_type" {
  description = "Your AWS instance type"
  type        = string
}

variable "aws_name_search" {
  description = "Your AWS AMI search name filter"
  type        = string
}

variable "aws_profile" {
  description = "Shared aws credentials file"
  type        = string
}

variable "aws_region" {
  description = "Your preferred AWS region"
  type        = string
}

# So far there hasn't been a need to configure this value
variable "aws_shared_config_file" {
  description = "Shared AWS configuration file"
  type        = string
  default     = "~/.aws/config"
}

# So far there hasn't been a need to configure this value
variable "aws_shared_credentials_file" {
  description = "Shared AWS credentials file"
  type        = string
  default     = "~/.aws/credentials"
}

variable "ssh_keyname" {
  default     = "kdevops_aws_key"
  description = "The name of your ssh key, this is just the name displayed and used on aws in the backend"
  type        = string
}

variable "ssh_pubkey_data" {
  default     = ""
  description = "The ssh public key data"
  type        = string
}

variable "user_data_admin_enable_hostnamectl" {
  description = "Should we use hostnamectl to change the target hostname?"
  type        = string
  default     = "yes"
}

variable "user_data_admin_enable_host_file" {
  description = "Should /etc/hosts also be appended with the new hostname with the localhost address?"
  type        = string
  default     = "yes"
}

variable "user_data_enabled" {
  description = "Do you want to enable cloud-init user data processing?"
  type        = string
  default     = "yes"
}

variable "user_data_log_dir" {
  description = "Where on the node you want user_data processing logs to go"
  type        = string
  default     = "/var/log/user_data"
}
