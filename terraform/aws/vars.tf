# This is for North california, if you want another one:
# https://docs.aws.amazon.com/general/latest/gr/rande.html
variable "aws_region" {
  description = "Your preferred AWS region"
  type        = string
}

variable "aws_availability_zone" {
  description = "Your preferred AWS availability zone"
  type        = string
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

# AMI updates for debian:
# https://wiki.debian.org/Cloud/AmazonEC2Image/Stretch
#
# If you want to choose another distro:
# https://letslearndevops.com/2018/08/23/terraform-get-latest-centos-ami/
# To get filter values you can first setup aws cli:
# https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html#cli-quick-configuration
# Get your image ami id, for debian 9 amd64 on the us-west1 this is
# ami-0adbaf2e0ce044437 so you can run:
#
# aws ec2 describe-images --image-ids ami-0adbaf2e0ce044437
# For details:
#
# https://docs.aws.amazon.com/cli/latest/reference/ec2/describe-images.html
#
# Using this filter glob lets us get the latest ami for this owner / release.
variable "aws_name_search" {
  description = "Your AWS AMI search name filter"
  type        = string
}

variable "aws_ami_owner" {
  description = "An AWS AMI image owner or owner alias"
  type        = string
}

# https://aws.amazon.com/ec2/instance-types/
# Free trial limits you to 750 hours of only t2.micro
variable "aws_instance_type" {
  description = "Your AWS instance type"
  type        = string
}

variable "aws_ebs_volumes_per_instance" {
  description = "Number of EBS volumes to create per instance"
  type        = number
}

variable "aws_ebs_volume_size" {
  description = "Size in GiB for each of the volumes"
  type        = number
}

variable "aws_ebs_volume_type" {
  description = "Type of each of the EBS volumes"
  type        = string
}

variable "aws_ebs_volume_iops" {
  description = "IOPS reserved for each EBS volume"
  type        = number
  default     = null
}

# So far there hasn't been a need to configure this value
variable "aws_shared_config_file" {
  description = "Shared AWS configuration file"
  type        = string
  default     = "~/.aws/conf"
}

# So far there hasn't been a need to configure this value
variable "aws_shared_credentials_file" {
  description = "Shared AWS credentials file"
  type        = string
  default     = "~/.aws/credentials"
}

# We had to use this as aws terraform provider doesn't have a way to set
# the hostname. local-exec works too, but this is what we went with.
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

# Disable for non-systemd systems, you'll want to implement something that
# does all what systemd does for us then if you still want your hostname
# changed.
variable "user_data_admin_enable_hostnamectl" {
  description = "Should we use hostnamectl to change the target hostname?"
  type        = string
  default     = "yes"
}

# kdevops does want us to have the hostname there, yes... so this is required.
# I forget which tests requires this.
variable "user_data_admin_enable_host_file" {
  description = "Should /etc/hosts also be appended with the new hostname with the localhost address?"
  type        = string
  default     = "yes"
}

variable "aws_profile" {
  description = "Shared aws credentials file"
  type        = string
}
