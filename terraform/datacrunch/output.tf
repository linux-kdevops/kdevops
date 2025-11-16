# DataCrunch outputs

# Controller IP map for SSH configuration
output "controller_ip_map" {
  value = {
    for node_name, instance in datacrunch_instance.kdevops :
    node_name => instance.ip
  }
  description = "Map of instance hostnames to IP addresses"
}

# Instance details
output "instance_details" {
  value = {
    for node_name, instance in datacrunch_instance.kdevops :
    node_name => {
      id           = instance.id
      ip           = instance.ip
      status       = instance.status
      os_volume_id = instance.os_volume_id
    }
  }
  description = "Detailed information about all instances"
}

# Configuration summary
output "datacrunch_info" {
  value = {
    location      = var.datacrunch_location
    instance_type = var.datacrunch_instance_type
    image         = var.datacrunch_image
    ssh_user      = local.ssh_user
  }
  description = "DataCrunch configuration information"
}
