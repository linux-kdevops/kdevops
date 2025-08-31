# Create SSH key if configured to do so
resource "lambdalabs_ssh_key" "kdevops" {
  count = var.ssh_config_genkey ? 1 : 0
  name  = var.lambdalabs_ssh_key_name

  # If we have an existing public key file, use it (trimming whitespace)
  # Otherwise the provider will generate a new key pair
  public_key = fileexists(pathexpand(var.ssh_config_pubkey_file)) ? trimspace(file(pathexpand(var.ssh_config_pubkey_file))) : null

  lifecycle {
    # Ignore changes to public_key to work around provider bug with whitespace
    ignore_changes = [public_key]
  }
}

# Save the generated SSH key to files if it was created
resource "null_resource" "save_ssh_key" {
  count = var.ssh_config_genkey && !fileexists(pathexpand(var.ssh_config_pubkey_file)) ? 1 : 0

  provisioner "local-exec" {
    command = <<-EOT
      # Save private key
      echo "${lambdalabs_ssh_key.kdevops[0].private_key}" > ${pathexpand(var.ssh_config_privkey_file)}
      chmod 600 ${pathexpand(var.ssh_config_privkey_file)}

      # Extract and save public key
      ssh-keygen -y -f ${pathexpand(var.ssh_config_privkey_file)} > ${pathexpand(var.ssh_config_pubkey_file)}
      chmod 644 ${pathexpand(var.ssh_config_pubkey_file)}
    EOT
  }

  depends_on = [
    lambdalabs_ssh_key.kdevops
  ]
}

# Local variables for SSH user mapping based on OS
locals {
  # Map OS images to their default SSH users
  # Lambda Labs typically uses Ubuntu, but this allows for flexibility
  ssh_user_map = {
    "ubuntu-22.04" = "ubuntu"
    "ubuntu-20.04" = "ubuntu"
    "ubuntu-24.04" = "ubuntu"
    "ubuntu-18.04" = "ubuntu"
    "debian-11"    = "debian"
    "debian-12"    = "debian"
    "debian-10"    = "debian"
    "rocky-8"      = "rocky"
    "rocky-9"      = "rocky"
    "centos-7"     = "centos"
    "centos-8"     = "centos"
    "alma-8"       = "almalinux"
    "alma-9"       = "almalinux"
  }

  # Determine SSH user - Lambda Labs doesn't support OS selection
  # All instances use Ubuntu 22.04, so we always use "ubuntu" user
  # The ssh_user_map is kept for potential future provider updates
  ssh_user = "ubuntu"
}

# Create instances
resource "lambdalabs_instance" "kdevops" {
  for_each           = toset(var.kdevops_nodes)
  name               = each.value
  region_name        = var.lambdalabs_region
  instance_type_name = var.lambdalabs_instance_type
  ssh_key_names      = var.ssh_config_genkey ? [lambdalabs_ssh_key.kdevops[0].name] : [var.lambdalabs_ssh_key_name]
  # Note: Lambda Labs provider doesn't currently support specifying the OS image
  # The provider uses a default image (typically Ubuntu 22.04)

  lifecycle {
    ignore_changes = [ssh_key_names]
  }

  depends_on = [
    lambdalabs_ssh_key.kdevops
  ]
}

# Note: Lambda Labs provider doesn't currently support persistent storage resources
# This would need to be managed through the Lambda Labs console or API directly
# Keeping this comment for future implementation when the provider supports it

# SSH config update
resource "null_resource" "ansible_update_ssh_config_hosts" {
  for_each = var.ssh_config_update ? toset(var.kdevops_nodes) : []

  provisioner "local-exec" {
    command = "python3 ${path.module}/../../scripts/update_ssh_config_lambdalabs.py update ${each.key} ${lambdalabs_instance.kdevops[each.key].ip} ${local.ssh_user} ${var.ssh_config_name} ${var.ssh_config_privkey_file} 'Lambda Labs'"
  }

  triggers = {
    instance_id = lambdalabs_instance.kdevops[each.key].id
  }
}

# Remove SSH config entries on destroy
resource "null_resource" "remove_ssh_config" {
  for_each = var.ssh_config_update ? toset(var.kdevops_nodes) : []

  provisioner "local-exec" {
    when    = destroy
    command = "python3 ${self.triggers.ssh_config_script} remove ${self.triggers.hostname} '' '' ${self.triggers.ssh_config_name} '' 'Lambda Labs'"
  }

  triggers = {
    instance_id = lambdalabs_instance.kdevops[each.key].id
    ssh_config_script = "${path.module}/../../scripts/update_ssh_config_lambdalabs.py"
    ssh_config_name = var.ssh_config_name
    hostname = each.key
  }
}

# Ansible provisioning
resource "null_resource" "ansible_provision" {
  for_each = toset(var.kdevops_nodes)

  connection {
    type        = "ssh"
    host        = lambdalabs_instance.kdevops[each.key].ip
    user        = local.ssh_user
    private_key = file(pathexpand(var.ssh_config_privkey_file))
  }

  provisioner "remote-exec" {
    inline = [
      "echo 'Waiting for system to be ready...'",
      "sudo cloud-init status --wait || true",
      "echo 'System is ready for provisioning'"
    ]
  }

  provisioner "local-exec" {
    command = templatefile("${path.module}/ansible_provision_cmd.tpl", {
      inventory           = "../../hosts",
      limit              = each.key,
      extra_vars         = "../../extra_vars.yaml",
      playbook_dir       = "../../playbooks",
      provision_playbook = "devconfig.yml",
      extra_args         = "--limit ${each.key} --extra-vars @../../extra_vars.yaml"
    })
  }

  depends_on = [
    lambdalabs_instance.kdevops,
    null_resource.ansible_update_ssh_config_hosts
  ]

  triggers = {
    instance_id = lambdalabs_instance.kdevops[each.key].id
  }
}
