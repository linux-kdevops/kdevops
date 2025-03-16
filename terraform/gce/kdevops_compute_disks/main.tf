resource "google_compute_disk" "kdevops_disk" {
  count                  = var.cd_disk_count
  name                   = format("disk-%s-%02d", var.cd_instance_name, count.index)
  provisioned_iops       = var.cd_disk_iops
  provisioned_throughput = var.cd_disk_throughput
  type                   = var.cd_disk_type
  size                   = var.cd_disk_size
  zone                   = var.cd_zone
}

resource "google_compute_attached_disk" "kdevops_attached_disk" {
  count    = var.cd_disk_count
  disk     = google_compute_disk.kdevops_disk[count.index].id
  instance = var.cd_instance_id
}
