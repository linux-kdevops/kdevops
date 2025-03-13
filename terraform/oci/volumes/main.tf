resource "oci_core_volume" "kdevops_volume_extra" {
  count               = var.vol_volume_count
  availability_domain = var.vol_availability_domain
  display_name        = format("kdevops_%s_volume%02d", var.vol_instance_name, count.index + 1)
  compartment_id      = var.vol_compartment_ocid
  size_in_gbs         = var.vol_volume_size
}

locals {
  vol_name_suffixes = ["b", "c", "d", "e", "f", "g", "h", "i", "j", "k"]
}

resource "oci_core_volume_attachment" "kdevops_volume_extra_att" {
  count           = var.vol_volume_count
  attachment_type = "paravirtualized"
  instance_id     = var.vol_instance_id
  volume_id       = oci_core_volume.kdevops_volume_extra[count.index].id
  device          = format("/dev/oracleoci/oraclevd%s", element(local.vol_name_suffixes, count.index))
}
