resource "azurerm_managed_disk" "kdevops_managed_disk" {
  count                = var.md_disk_count

  name                 = format("kdevops_%s_disk%02d", var.md_virtual_machine_name, count.index + 1)
  location             = var.md_location
  resource_group_name  = var.md_resource_group_name
  create_option        = "Empty"
  storage_account_type = "Premium_LRS"
  disk_size_gb         = var.md_disk_size
}

resource "azurerm_virtual_machine_data_disk_attachment" "kdevops_disk_attachment" {
  count                     = var.md_disk_count
  caching                   = "ReadWrite"
  lun                       = count.index
  managed_disk_id           = azurerm_managed_disk.kdevops_managed_disk[count.index].id
  virtual_machine_id        = var.md_virtual_machine_id
  write_accelerator_enabled = false
}
