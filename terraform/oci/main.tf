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
    ocpus         = var.oci_instance_flex_ocpus
  }
  source_details {
    source_id   = var.oci_os_image_ocid
    source_type = "image"
  }

  display_name = element(var.kdevops_nodes, count.index)

  create_vnic_details {
    assign_public_ip = var.oci_assign_public_ip
    subnet_id        = var.oci_use_existing_vcn ? var.oci_subnet_ocid : one(oci_core_subnet.kdevops_subnet[*].id)
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_config_pubkey_file)
  }

  preemptible_instance_config {
    preemption_action {
      type                 = "TERMINATE"
      preserve_boot_volume = false
    }
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
  vol_vpus_per_gb         = var.oci_vpus_per_gb
}

resource "oci_core_vcn" "kdevops_vcn" {
  count = var.oci_use_existing_vcn ? 0 : 1

  cidr_blocks = [
    "10.0.0.0/16",
  ]
  compartment_id = data.oci_identity_compartments.kdevops_compartment.compartments[0].id
  display_name   = "kdevops VCN"
  dns_label      = "kdevops"
  is_ipv6enabled = false
}

resource "oci_core_internet_gateway" "kdevops_internet_gateway" {
  count = var.oci_use_existing_vcn ? 0 : 1

  compartment_id = data.oci_identity_compartments.kdevops_compartment.compartments[0].id
  display_name   = "kdevops internet gateway"
  vcn_id         = one(oci_core_vcn.kdevops_vcn[*].id)
}

resource "oci_core_dhcp_options" "kdevops_dhcp_options" {
  count = var.oci_use_existing_vcn ? 0 : 1

  compartment_id = data.oci_identity_compartments.kdevops_compartment.compartments[0].id
  display_name   = "kdevops dhcp options"
  vcn_id         = one(oci_core_vcn.kdevops_vcn[*].id)

  options {
    type        = "DomainNameServer"
    server_type = "VcnLocalPlusInternet"
  }
  options {
    type                = "SearchDomain"
    search_domain_names = ["kdevops.oraclevcn.com"]
  }
}

resource "oci_core_route_table" "kdevops_route_table" {
  count = var.oci_use_existing_vcn ? 0 : 1

  compartment_id = data.oci_identity_compartments.kdevops_compartment.compartments[0].id
  display_name   = "kdevops route table"
  vcn_id         = one(oci_core_vcn.kdevops_vcn[*].id)
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = one(oci_core_internet_gateway.kdevops_internet_gateway[*].id)
  }
}

resource "oci_core_security_list" "kdevops_security_list" {
  count = var.oci_use_existing_vcn ? 0 : 1

  compartment_id = data.oci_identity_compartments.kdevops_compartment.compartments[0].id
  display_name   = "kdevops security list"
  vcn_id         = one(oci_core_vcn.kdevops_vcn[*].id)

  egress_security_rules {
    description      = "Allow all outbound traffic"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    protocol         = "all"
    stateless        = false
  }

  ingress_security_rules {
    description = "Enable Path MTU Discovery to work"
    icmp_options {
      code = 4
      type = 3
    }
    protocol    = 1
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
  }
  ingress_security_rules {
    description = "Allow applications within VCN to fail fast"
    icmp_options {
      type = 3
    }
    protocol    = 1
    source      = "10.0.0.0/16"
    source_type = "CIDR_BLOCK"
    stateless   = false
  }
  ingress_security_rules {
    description = "Enable instance management via Ansible"
    protocol    = 6
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      min = 22
      max = 22
    }
  }
  ingress_security_rules {
    description = "Allow VCN-local TCP traffic for ports: all"
    protocol    = 6
    source      = "10.0.0.0/16"
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      min = 1
      max = 65535
    }
  }
}

resource "oci_core_subnet" "kdevops_subnet" {
  count = var.oci_use_existing_vcn ? 0 : 1

  availability_domain = data.oci_identity_availability_domain.kdevops_av_domain.name
  cidr_block          = "10.0.0.0/24"
  compartment_id      = data.oci_identity_compartments.kdevops_compartment.compartments[0].id
  dhcp_options_id     = one(oci_core_dhcp_options.kdevops_dhcp_options[*].id)
  dns_label           = "runners"
  display_name        = "kdevops subnet"
  route_table_id      = one(oci_core_route_table.kdevops_route_table[*].id)
  security_list_ids   = ["${one(oci_core_security_list.kdevops_security_list[*].id)}"]
  vcn_id              = one(oci_core_vcn.kdevops_vcn[*].id)
}
