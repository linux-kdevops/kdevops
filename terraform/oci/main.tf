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

module "volumes" {
  count  = var.oci_volumes_enable_extra == "true" ? local.kdevops_num_boxes : 0
  source = "./volumes"

  vol_availability_domain = var.oci_availablity_domain
  vol_compartment_ocid    = var.oci_compartment_ocid
  vol_instance_id         = element(oci_core_instance.kdevops_instance.*.id, count.index)
  vol_instance_name       = element(var.kdevops_nodes, count.index)
  vol_volume_count        = var.oci_volumes_per_instance
  vol_volume_size         = var.oci_volumes_size
}
