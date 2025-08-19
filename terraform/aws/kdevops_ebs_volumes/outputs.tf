output "ebs_volume_map" {
  description = "The block devices attached to the instance"
  value       = zipmap(aws_volume_attachment.kdevops_attachment[*].device_name,
                       aws_volume_attachment.kdevops_attachment[*].volume_id)
}

output "extra_volumes_tags" {
  description = "Tag to volume ID mappings for udev configuration"
  value       = zipmap(aws_ebs_volume.kdevops_volume[*].tags["FixedName"],
                       aws_volume_attachment.kdevops_attachment[*].volume_id)
}
