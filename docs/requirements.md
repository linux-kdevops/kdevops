# Requirements for kdevops

You must be on a recent Linux distribution, we highly recommend a rolling
Linux distribution or OS X. You must have installed:

  * Ansible
  * GNU Make
  * guestfs-tools

Then just run:

  * `make menuconfig-deps`

Then you can now run:

  * `make menuconfig`

# Supported base distributions for command and control

Examples of well tested rolling distributions recommended if using vagrant:

  * Debian testing
  * OpenSUSE Tumbleweed
  * Fedora
  * Latest Ubuntu

If using Terraform just ensure you can upgrade Terraform to the latest release
regularly.
