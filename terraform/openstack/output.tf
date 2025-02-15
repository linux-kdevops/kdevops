data "null_data_source" "group_hostnames_and_ips" {
  count = local.kdevops_num_boxes
  inputs = {
    value = format(
      "%30s  :  %s",
      element(var.kdevops_nodes, count.index),
      element(
        openstack_compute_instance_v2.kdevops_instances.*.access_ip_v4,
        count.index,
      ),
    )
  }
}

output "kdevops_hosts_and_ipv4" {
  value = data.null_data_source.group_hostnames_and_ips.*.outputs
}

# Each provider's output.tf needs to define a public_ip_map. This
# map is used to build the Ansible controller's ssh configuration.
# Each map entry contains the node's hostname and public IP address.
output "public_ip_map" {
  description = "The public IP addresses assigned to each instance"
  value       = zipmap(var.kdevops_nodes[*], openstack_compute_instance_v2.kdevops_instances[*].access_ip_v4)
}
