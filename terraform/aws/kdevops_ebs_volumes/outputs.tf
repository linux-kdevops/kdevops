output "ebs_volume_map" {
  description = "The block devices attached to the instance"
  value       = zipmap(aws_volume_attachment.kdevops_attachment[*].device_name,
                       aws_volume_attachment.kdevops_attachment[*].volume_id)
}
