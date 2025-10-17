resource "rcloud_vm" "kdevops_vm" {
  count        = local.kdevops_num_boxes
  name         = element(var.kdevops_nodes, count.index)
  vcpus        = 2
  memory_gb    = 4
  base_image   = var.rcloud_base_image
  root_disk_gb = 50
}
