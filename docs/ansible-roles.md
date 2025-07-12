# Local ansible role documentation

The following local ansible roles are used:

  * [devconfig](./playbooks/roles/devconfig/README.md)
  * [create_partition](./playbooks/roles/create_partition/README.md)
  * create_data_partition: creates the data partition, uses the `create_partition` role
  * [install_terraform/](./playbooks/roles/install_terraform/README.md)
  * [libvirt_user](./playbooks/roles/libvirt_user/README.md)
  * update_ssh_config_guestfs: updates your ssh config for guestfs deployments

The following are ansible roles dedicated towards supported workflows:

  * [bootlinux](./playbooks/roles/bootlinux/README.md): used to support hacking
    on Linux. Kernel configuration files are also tracked in the bootlinux role.
  * fstests_prep_localhost: used to install command and control dependencies
  * fstests: used to run the fstests workflow
  * blktests: used to run the blktests workflow
  * reboot-limit: used to run the reboot-limit test workflow

