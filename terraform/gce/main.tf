resource "google_compute_instance" "kdevops_instance" {
  count        = local.kdevops_num_boxes
  name         = element(var.kdevops_nodes, count.index)
  machine_type = var.gce_machine_type
  zone         = var.gce_zone

  tags = ["kdevops"]

  boot_disk {
    initialize_params {
      image = var.image_name
      type  = var.gce_image_type
    }
  }

  scratch_disk {
    interface = var.scratch_disk_interface
  }

  scratch_disk {
    interface = var.scratch_disk_interface
  }

  network_interface {
    network = "default"

    # Ephemeral IP
    access_config {
    }
  }

  metadata = {
    ssh-keys = format("%s:%s", var.ssh_config_user, file(var.ssh_config_pubkey_file))
  }

  metadata_startup_script = "echo hi > /test.txt"
}
