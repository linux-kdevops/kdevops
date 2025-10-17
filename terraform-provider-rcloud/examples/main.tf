terraform {
  required_providers {
    rcloud = {
      source = "kdevops/rcloud"
    }
  }
}

provider "rcloud" {
  endpoint = "http://localhost:8765"
  # token = "your-api-token" # Optional for MVP
}

resource "rcloud_vm" "example" {
  name         = "terraform-vm-01"
  vcpus        = 4
  memory_gb    = 8
  base_image   = "debian-13-generic-amd64.raw"
  root_disk_gb = 100
}

output "vm_id" {
  value = rcloud_vm.example.id
}

output "vm_state" {
  value = rcloud_vm.example.state
}
