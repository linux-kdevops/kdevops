# DataCrunch main configuration

# Local variables for SSH user mapping based on OS
locals {
  # Map OS images to their default SSH users
  # DataCrunch uses root as the default user for all images
  ssh_user_map = {
    "ubuntu-24.04-cuda-12.8-open-docker" = "root"
    "ubuntu-22.04-pytorch"                = "root"
    "ubuntu-22.04"                        = "root"
    "ubuntu-20.04"                        = "root"
    "debian-11"                           = "root"
    "debian-12"                           = "root"
  }

  # Determine SSH user based on image
  ssh_user = lookup(local.ssh_user_map, var.datacrunch_image, "root")
}

# Create or reference SSH key
resource "datacrunch_ssh_key" "kdevops" {
  count      = var.datacrunch_ssh_key_id == "" ? 1 : 0
  name       = var.datacrunch_ssh_key_name
  public_key = file(pathexpand(var.ssh_config_pubkey_file))
}

# Create DataCrunch instances
resource "datacrunch_instance" "kdevops" {
  for_each      = toset(var.kdevops_nodes)
  hostname      = each.value
  description   = "kdevops node ${each.value}"
  location_code = var.datacrunch_location
  instance_type = var.datacrunch_instance_type
  image         = var.datacrunch_image
  ssh_key_ids   = var.datacrunch_ssh_key_id != "" ? [var.datacrunch_ssh_key_id] : [datacrunch_ssh_key.kdevops[0].id]
}
