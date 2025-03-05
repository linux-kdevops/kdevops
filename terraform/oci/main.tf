resource "oci_core_instance" "kdevops_instance" {
  count = local.kdevops_num_boxes

  availability_domain = var.oci_availablity_domain
  compartment_id = var.oci_compartment_ocid
  shape = var.oci_shape
  shape_config {
    memory_in_gbs = var.oci_instance_flex_memory_in_gbs
    ocpus = var.oci_instance_flex_ocpus
  }
  source_details {
    source_id = var.oci_os_image_ocid
    source_type = "image"
  }

  display_name = element(var.kdevops_nodes, count.index)

  create_vnic_details {
    assign_public_ip = var.oci_assign_public_ip
    subnet_id = var.oci_subnet_ocid
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_config_pubkey_file)
  }

  preserve_boot_volume = false
}

resource "oci_core_volume" "kdevops_data_disk" {
  count = var.oci_volumes_enable_extra == "true" ? 0 : local.kdevops_num_boxes

  compartment_id = var.oci_compartment_ocid

  availability_domain = var.oci_availablity_domain
  display_name = var.oci_data_volume_display_name
  size_in_gbs = 50
}

resource "oci_core_volume" "kdevops_sparse_disk" {
  count = var.oci_volumes_enable_extra == "true" ? 0 : local.kdevops_num_boxes

  compartment_id = var.oci_compartment_ocid

  availability_domain = var.oci_availablity_domain
  display_name = var.oci_sparse_volume_display_name
  size_in_gbs = 120
}

resource "oci_core_volume_attachment" "kdevops_data_volume_attachment" {
  count = var.oci_volumes_enable_extra == "true" ? 0 : local.kdevops_num_boxes

  attachment_type = "paravirtualized"
  instance_id = element(oci_core_instance.kdevops_instance.*.id, count.index)
  volume_id = element(oci_core_volume.kdevops_data_disk.*.id, count.index)

  device = var.oci_data_volume_device_file_name
}

resource "oci_core_volume_attachment" "kdevops_sparse_disk_attachment" {
  count = var.oci_volumes_enable_extra == "true" ? 0 : local.kdevops_num_boxes

  attachment_type = "paravirtualized"
  instance_id = element(oci_core_instance.kdevops_instance.*.id, count.index)
  volume_id = element(oci_core_volume.kdevops_sparse_disk.*.id, count.index)

  device = var.oci_sparse_volume_device_file_name
}

resource "oci_core_volume" "kdevops_volume_extra" {
  count               = var.oci_volumes_enable_extra == "false" ? 0 : local.kdevops_num_boxes * var.oci_volumes_per_instance
  availability_domain = var.oci_availablity_domain
  display_name        = format("kdevops_volume%02d", count.index + 1)
  compartment_id      = var.oci_compartment_ocid
  size_in_gbs         = var.oci_volumes_size
}

locals {
  volume_name_suffixes = [ "b", "c", "d", "e", "f", "g", "h", "i", "j", "k" ]
}

resource "oci_core_volume_attachment" "kdevops_volume_extra_att" {
  count           = var.oci_volumes_enable_extra == "false" ? 0 : local.kdevops_num_boxes * var.oci_volumes_per_instance
  attachment_type = "paravirtualized"
  instance_id     = element(oci_core_instance.kdevops_instance.*.id, count.index)
  volume_id       = element(oci_core_volume.kdevops_volume_extra.*.id, count.index)
  device          = format("/dev/oracleoci/oraclevd%s", element(local.volume_name_suffixes, count.index))
}
