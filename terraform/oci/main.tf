data "oci_identity_compartments" "kdevops_compartment" {
  access_level              = "ANY"
  compartment_id            = var.oci_tenancy_ocid
  compartment_id_in_subtree = true
  name                      = var.oci_compartment_name
  state                     = "ACTIVE"
}

data "oci_identity_availability_domain" "kdevops_av_domain" {
  ad_number      = var.oci_ad_number
  compartment_id = var.oci_tenancy_ocid
}

resource "oci_core_instance" "kdevops_instance" {
  count = local.kdevops_num_boxes

  availability_domain = data.oci_identity_availability_domain.kdevops_av_domain.name
  compartment_id      = data.oci_identity_compartments.kdevops_compartment.compartments[0].id
  shape               = var.oci_shape
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

module "volumes" {
  count  = local.kdevops_num_boxes
  source = "./volumes"

  vol_availability_domain = data.oci_identity_availability_domain.kdevops_av_domain.name
  vol_compartment_ocid    = data.oci_identity_compartments.kdevops_compartment.compartments[0].id
  vol_instance_id         = element(oci_core_instance.kdevops_instance.*.id, count.index)
  vol_instance_name       = element(var.kdevops_nodes, count.index)
  vol_volume_count        = var.oci_volumes_per_instance
  vol_volume_size         = var.oci_volumes_size
}
