resource "azurerm_managed_disk" "kdevops_managed_disk" {
  count                         = var.md_disk_count
  create_option                 = "Empty"
  disk_size_gb                  = var.md_disk_size
  location                      = var.md_location
  name                          = format("kdevops_%s_disk%02d", var.md_virtual_machine_name, count.index + 1)
  public_network_access_enabled = false
  resource_group_name           = var.md_resource_group_name
  storage_account_type          = "Premium_LRS"
  tier                          = var.md_tier
}

resource "azurerm_virtual_machine_data_disk_attachment" "kdevops_disk_attachment" {
  count                     = var.md_disk_count
  caching                   = "ReadWrite"
  lun                       = count.index
  managed_disk_id           = azurerm_managed_disk.kdevops_managed_disk[count.index].id
  virtual_machine_id        = var.md_virtual_machine_id
  write_accelerator_enabled = false
}
