data "null_data_source" "host_names" {
  count = local.kdevops_num_boxes
  inputs = {
    value = element(var.kdevops_nodes, count.index),
  }
}

output "kdevops_hosts" {
  value = data.null_data_source.host_names.*.outputs.value
}

data "azurerm_public_ip" "public_ips" {
  count               = local.kdevops_num_boxes
  name                = element(azurerm_public_ip.kdevops_publicip.*.name, count.index)
  resource_group_name = azurerm_resource_group.kdevops_group.name
  depends_on          = [azurerm_linux_virtual_machine.kdevops_vm]
}

output "kdevops_public_ip_addresses" {
  value = data.azurerm_public_ip.public_ips.*.ip_address
}

# Each provider's output.tf needs to define a public_ip_map. This
# map is used to build the Ansible controller's ssh configuration.
# Each map entry contains the node's hostname and public IP address.
output "public_ip_map" {
  description = "The public IP addresses assigned to each instance"
  value       = zipmap(var.kdevops_nodes[*], azurerm_public_ip.kdevops_publicip[*].ip_address)
}
