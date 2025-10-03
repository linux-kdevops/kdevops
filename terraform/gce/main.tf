data "google_compute_image" "kdevops_image" {
  project = var.gce_image_project
  family  = var.gce_image_family
}

resource "google_compute_firewall" "kdevops_ssh" {
  name    = "kdevops-allow-ssh"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = [tostring(var.ssh_config_port)]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["kdevops-ssh"]
}

resource "google_compute_instance" "kdevops_instance" {
  count        = local.kdevops_num_boxes
  name         = element(var.kdevops_nodes, count.index)
  machine_type = var.gce_machine_type
  zone         = var.gce_zone

  boot_disk {
    initialize_params {
      image = data.google_compute_image.kdevops_image.self_link
      size  = var.gce_image_size
      type  = var.gce_image_type
    }
  }

  network_interface {
    network = "default"

    # Ephemeral IP
    access_config {
    }
  }

  lifecycle {
    ignore_changes = [attached_disk]
  }

  metadata = {
    ssh-keys = format("%s:%s", var.ssh_config_user, file(var.ssh_config_pubkey_file))
  }

  metadata_startup_script = templatefile("${path.module}/../scripts/cloud-init.sh", {
    user_data_log_dir = "/var/log/kdevops"
    user_data_enabled = "yes"
    ssh_config_user   = var.ssh_config_user
    ssh_config_port   = var.ssh_config_port
    new_hostname      = element(var.kdevops_nodes, count.index)
  })

  tags = ["kdevops-ssh"]
}

module "kdevops_compute_disks" {
  count              = local.kdevops_num_boxes
  cd_disk_count      = var.gce_disk_count
  cd_disk_iops       = var.gce_disk_iops
  cd_disk_size       = var.gce_disk_size
  cd_disk_throughput = var.gce_disk_throughput
  cd_disk_type       = var.gce_disk_type
  cd_instance_id     = google_compute_instance.kdevops_instance[count.index].id
  cd_instance_name   = element(var.kdevops_nodes, count.index)
  cd_zone            = var.gce_zone
  source             = "./kdevops_compute_disks"
}
