locals {
  device_name_suffixes = ["f", "g", "h", "i", "j", "k", "l", "m", "n", "o"]
}

resource "aws_ebs_volume" "kdevops_volume" {
  count                = var.vol_count
  availability_zone    = var.vol_availability_zone
  encrypted            = false
  iops                 = var.vol_iops
  multi_attach_enabled = false
  size                 = var.vol_size
  throughput           = var.vol_throughput
  type                 = var.vol_type

  tags = {
    FixedName = format("extra-volume-%02d", count.index)
  }
}

resource "aws_volume_attachment" "kdevops_attachment" {
  count       = var.vol_count
  device_name = format("/dev/sd%s", element(local.device_name_suffixes, count.index))
  instance_id = var.vol_instance_id
  volume_id   = element(aws_ebs_volume.kdevops_volume.*.id, count.index)
}
