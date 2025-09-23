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

resource "aws_vpc" "kdevops_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_subnet" "kdevops_subnet" {
  cidr_block        = cidrsubnet(aws_vpc.kdevops_vpc.cidr_block, 3, 1)
  vpc_id            = aws_vpc.kdevops_vpc.id
  availability_zone = var.aws_availability_zone
}

resource "aws_security_group" "kdevops_sec_group" {
  name   = "kdevops_sg"
  vpc_id = aws_vpc.kdevops_vpc.id
  ingress {
    cidr_blocks = [
      "0.0.0.0/0",
    ]
    from_port = 22
    to_port   = 22
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
  name   = "kdevops_isg"
  vpc_id = aws_vpc.kdevops_vpc.id

  # Allow all traffic between hosts in the security group
  ingress {
    cidr_blocks = [
      "10.0.0.0/16",
    ]
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
  template = file("templates/script.sh")

  vars = {
    user_data_log_dir = var.user_data_log_dir
    user_data_enabled = var.user_data_enabled
    ssh_config_user   = var.ssh_config_user
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
  vpc_security_group_ids = [
    aws_security_group.kdevops_sec_group.id,
    aws_security_group.kdevops_internal_group.id
  ]
  key_name        = var.ssh_keyname
  subnet_id       = aws_subnet.kdevops_subnet.id
  user_data_base64 = element(
    data.template_cloudinit_config.kdevops_config.*.rendered,
    count.index,
  )
}

module "kdevops_ebs_volumes" {
  count                 = var.aws_ebs_volumes_per_instance > 0 ? local.kdevops_num_boxes : 0
  source                = "./kdevops_ebs_volumes"
  vol_availability_zone = var.aws_availability_zone
  vol_count             = var.aws_ebs_volumes_per_instance
  vol_instance_id       = element(aws_instance.kdevops_instance.*.id, count.index)
  vol_iops              = var.aws_ebs_volume_iops
  vol_size              = var.aws_ebs_volume_size
  vol_throughput        = var.aws_ebs_volume_throughput
  vol_type              = var.aws_ebs_volume_type
}

resource "aws_eip" "kdevops_eip" {
  count    = local.kdevops_num_boxes
  instance = element(aws_instance.kdevops_instance.*.id, count.index)
  domain   = "vpc"
}

resource "aws_internet_gateway" "kdevops_gw" {
  vpc_id = aws_vpc.kdevops_vpc.id
}

resource "aws_route_table" "kdevops_rt" {
  vpc_id = aws_vpc.kdevops_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.kdevops_gw.id
  }
}

resource "aws_route_table_association" "kdevops_rt_assoc" {
  subnet_id      = aws_subnet.kdevops_subnet.id
  route_table_id = aws_route_table.kdevops_rt.id
}

