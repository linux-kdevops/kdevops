# All generic output goes here

# Each provider's output.tf needs to define a public_ip_map. This
# map is used to build the Ansible controller's ssh configuration.
# Each map entry contains the node's hostname and public IP address.
output "public_ip_map" {
  description = "The public IP addresses assigned to each instance"
  value       = zipmap(var.kdevops_nodes[*], oci_core_instance.kdevops_instance.*.public_ip)
}
