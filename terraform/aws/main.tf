data "aws_ami" "kdevops_ami" {
  most_recent = true
  owners      = [var.aws_ami_owner]

  filter {
    name   = "architecture"
    values = [var.aws_ami_arch]
  }
  filter {
    name   = "name"
    values = [var.aws_name_search]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Use the default VPC instead of creating a new one
data "aws_vpc" "default" {
  default = true
}

# Create a locals block for VPC reference
locals {
  vpc_id = data.aws_vpc.default.id
}

# Get all subnets in the default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }
}

# Use the first available subnet
data "aws_subnet" "default" {
  id = tolist(data.aws_subnets.default.ids)[0]
}

resource "aws_security_group" "kdevops_sec_group" {
  name   = "kdevops_sg_${var.ssh_keyname}"
  vpc_id = local.vpc_id
  ingress {
    cidr_blocks = [
      "0.0.0.0/0",
    ]
    from_port = var.ssh_config_port
    to_port   = var.ssh_config_port
    protocol  = "tcp"
  }

  # Terraform removes the default rule
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "kdevops_internal_group" {
  name   = "kdevops_isg_${var.ssh_keyname}"
  vpc_id = local.vpc_id

  # Allow all traffic between hosts in the security group
  ingress {
    self      = true
    from_port = 0
    to_port   = 0
    protocol  = "-1"
  }
}


resource "aws_key_pair" "kdevops_keypair" {
  key_name   = var.ssh_keyname
  public_key = var.ssh_config_pubkey_file != "" ? file(var.ssh_config_pubkey_file) : ""
}

data "template_file" "script_user_data" {
  count    = local.kdevops_num_boxes
  template = file("../scripts/cloud-init.sh")

  vars = {
    user_data_log_dir = var.user_data_log_dir
    user_data_enabled = var.user_data_enabled
    ssh_config_user   = var.ssh_config_user
    ssh_config_port   = var.ssh_config_port
    new_hostname      = element(var.kdevops_nodes, count.index),
  }
}

data "template_file" "cloud_init_user_data" {
  count    = local.kdevops_num_boxes
  template = file("templates/config.yaml")

  vars = {
    new_hostname    = element(var.kdevops_nodes, count.index),
    ssh_config_user = var.ssh_config_user
  }
}

data "template_cloudinit_config" "kdevops_config" {
  count         = local.kdevops_num_boxes
  gzip          = true
  base64_encode = true

  # Main cloud-config configuration file. I suppose other cloud providers
  # deal with this for us through cloud-init on the terraform provider.
  # Not sure why amazon's provider doesn not do it as well.
  part {
    filename     = "init.cfg"
    content_type = "text/cloud-config"
    content = element(
      data.template_file.cloud_init_user_data.*.rendered,
      count.index,
    )
  }

  # In case cloud-init modules don't support what we want to do for kdevops.
  # But note, we'll want to use ansible for most real provisioning.
  # Using this script fall into a small fine line in between what we cannot
  # accomplish with cloud-init for our initial bootstrap, and what ansible
  # provisioning can do.
  part {
    content_type = "text/x-shellscript"
    content      = element(data.template_file.script_user_data.*.rendered, count.index)
  }
}

resource "aws_instance" "kdevops_instance" {
  count         = local.kdevops_num_boxes
  ami           = data.aws_ami.kdevops_ami.id
  instance_type = var.aws_instance_type
  associate_public_ip_address = true  # Required for SSH access when using default VPC
  vpc_security_group_ids = [
    aws_security_group.kdevops_sec_group.id,
    aws_security_group.kdevops_internal_group.id
  ]
  key_name        = var.ssh_keyname
  subnet_id       = data.aws_subnet.default.id
  user_data_base64 = element(
    data.template_cloudinit_config.kdevops_config.*.rendered,
    count.index,
  )
}

module "kdevops_ebs_volumes" {
  count                 = var.aws_ebs_volumes_per_instance > 0 ? local.kdevops_num_boxes : 0
  source                = "./kdevops_ebs_volumes"
  # Use the same AZ as the instance (from default subnet)
  vol_availability_zone = data.aws_subnet.default.availability_zone
  vol_count             = var.aws_ebs_volumes_per_instance
  vol_instance_id       = element(aws_instance.kdevops_instance.*.id, count.index)
  vol_iops              = var.aws_ebs_volume_iops
  vol_size              = var.aws_ebs_volume_size
  vol_throughput        = var.aws_ebs_volume_throughput
  vol_type              = var.aws_ebs_volume_type
}

# Elastic IPs are optional when using default VPC with public IPs
# resource "aws_eip" "kdevops_eip" {
#   count    = local.kdevops_num_boxes
#   instance = element(aws_instance.kdevops_instance.*.id, count.index)
#   domain   = "vpc"
# }

# These resources are not needed when using default VPC
# as it already has internet gateway and route tables configured
#
# resource "aws_internet_gateway" "kdevops_gw" {
#   vpc_id = local.vpc_id
# }
#
# resource "aws_route_table" "kdevops_rt" {
#   vpc_id = local.vpc_id
#   route {
#     cidr_block = "0.0.0.0/0"
#     gateway_id = aws_internet_gateway.kdevops_gw.id
#   }
# }
#
# resource "aws_route_table_association" "kdevops_rt_assoc" {
#   subnet_id      = data.aws_subnet.default.id
#   route_table_id = aws_route_table.kdevops_rt.id
# }

