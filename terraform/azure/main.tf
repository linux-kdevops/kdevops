# Azure terraform provider main

resource "azurerm_resource_group" "kdevops_group" {
  name     = "kdevops_resource_group"
  location = var.azure_location
}

locals {
  kdevops_private_net = format("%s/%d", var.private_net_prefix, var.private_net_mask)
}

resource "azurerm_virtual_network" "kdevops_network" {
  name                = "kdevops_net"
  address_space       = [local.kdevops_private_net]
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.kdevops_group.name
}

resource "azurerm_subnet" "kdevops_subnet" {
  name                 = "kdevops_subnet"
  resource_group_name  = azurerm_resource_group.kdevops_group.name
  virtual_network_name = azurerm_virtual_network.kdevops_network.name
  address_prefixes     = [local.kdevops_private_net]
}

resource "azurerm_public_ip" "kdevops_publicip" {
  count               = local.kdevops_num_boxes
  name                = format("kdevops_pub_ip_%02d", count.index + 1)
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.kdevops_group.name
  allocation_method   = "Static"
}

resource "azurerm_network_security_group" "kdevops_sg" {
  name                = "kdevops_network_security_group"
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.kdevops_group.name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface_security_group_association" "kdevops_sg_assoc" {
  count                     = local.kdevops_num_boxes
  network_security_group_id = azurerm_network_security_group.kdevops_sg.id
  network_interface_id      = element(azurerm_network_interface.kdevops_nic.*.id, count.index)
}

resource "azurerm_network_interface" "kdevops_nic" {
  count                          = local.kdevops_num_boxes
  accelerated_networking_enabled = true
  name                           = format("kdevops_nic_%02d", count.index + 1)
  location                       = var.azure_location
  resource_group_name            = azurerm_resource_group.kdevops_group.name

  ip_configuration {
    name                          = "kdevops_nic_configuration"
    subnet_id                     = azurerm_subnet.kdevops_subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = element(azurerm_public_ip.kdevops_publicip.*.id, count.index)
  }
}

resource "azurerm_linux_virtual_machine" "kdevops_vm" {
  count = local.kdevops_num_boxes

  # As of terraform 0.11 there is no easy way to convert a list to a map
  # for the structure we have defined for the nodes. We can use
  # split to construct a subjset list though, and then key in with the
  # target left hand value name we want to look for. On the last split we
  # call always uses the second element given its a value: figure, we want
  # the right hand side of this.
  #
  # The "%7D" is the lingering nagging trailing "}" at the end of the string,
  # we just remove it.
  name                            = element(var.kdevops_nodes, count.index)
  location                        = var.azure_location
  resource_group_name             = azurerm_resource_group.kdevops_group.name
  network_interface_ids           = [element(azurerm_network_interface.kdevops_nic.*.id, count.index)]
  size                            = var.azure_vmsize
  admin_username                  = var.ssh_config_user
  disable_password_authentication = true

  os_disk {
    # Note: yes using the names like the ones below is better however it also
    # means propagating a hack *many* times. It would be better to instead
    # move this hack to a single place using local variables somehow so that
    # we can later adjust the hack *once* instead of many times.
    #name                 = "${format("kdevops-main-disk-%s", element(azurerm_virtual_machine.kdevops_vm.*.name, count.index))}"
    name                 = format("kdevops-main-disk-%02d", count.index + 1)
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    #disk_size_gb         = 64
  }

  source_image_reference {
    publisher = var.azure_image_publisher
    offer     = var.azure_image_offer
    sku       = var.azure_image_sku
    version   = "latest"
  }

  admin_ssh_key {
    username   = var.ssh_config_user
    public_key = var.ssh_config_pubkey_file != "" ? file(var.ssh_config_pubkey_file) : ""
  }
}

module "kdevops_managed_disks" {
  count                   = local.kdevops_num_boxes
  md_disk_size            = var.azure_managed_disks_size
  md_disk_count           = var.azure_managed_disks_per_instance
  md_location             = var.azure_location
  md_resource_group_name  = azurerm_resource_group.kdevops_group.name
  md_tier                 = var.azure_managed_disks_tier
  md_virtual_machine_id   = element(azurerm_linux_virtual_machine.kdevops_vm.*.id, count.index)
  md_virtual_machine_name = element(azurerm_linux_virtual_machine.kdevops_vm.*.name, count.index)
  source                  = "./kdevops_managed_disks"
}
