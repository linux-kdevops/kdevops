output "instance_ids" {
  description = "The IDs of the Lambda Labs instances"
  value       = { for k, v in lambdalabs_instance.kdevops : k => v.id }
}

output "instance_ips" {
  description = "The IP addresses of the Lambda Labs instances"
  value       = { for k, v in lambdalabs_instance.kdevops : k => v.ip }
}

output "instance_names" {
  description = "The names of the Lambda Labs instances"
  value       = { for k, v in lambdalabs_instance.kdevops : k => v.name }
}

output "instance_regions" {
  description = "The regions of the Lambda Labs instances"
  value       = { for k, v in lambdalabs_instance.kdevops : k => v.region_name }
}

# Storage management is not supported by Lambda Labs provider
# output "storage_enabled" {
#   description = "Whether persistent storage is enabled"
#   value       = var.extra_storage_enable
# }

output "ssh_key_name" {
  description = "The name of the SSH key used"
  value       = var.lambdalabs_ssh_key_name
}

output "ssh_key_generated" {
  description = "Whether an SSH key was generated"
  value       = var.ssh_config_genkey
}

output "generated_private_key" {
  description = "The generated private SSH key (if created)"
  value       = var.ssh_config_genkey && length(lambdalabs_ssh_key.kdevops) > 0 ? lambdalabs_ssh_key.kdevops[0].private_key : null
  sensitive   = true
}

output "controller_ip_map" {
  description = "Map of instance names to IP addresses for Ansible"
  value       = { for k, v in lambdalabs_instance.kdevops : k => v.ip }
}

output "ssh_user" {
  description = "SSH user for connecting to instances based on OS image"
  value       = local.ssh_user
}
