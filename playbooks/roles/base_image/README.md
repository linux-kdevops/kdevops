base_image
==========

The base_image role manages libvirt base OS images. These images
contain an installed operating system and are used to quickly
create new libvirt guests with virt-sysprep.

Requirements
------------

Network access to the public libvirt image repositories. The
virt-builder program must be installed.

Role Variables
--------------

  * base_image_os_version: OS to install on the image
  * base_image_pathname: pathname of local file to contain the image

Dependencies
------------

None.

Example Playbook
----------------

Below is an example playbook task:

```
- name: Create /test/nfs if needed
  ansible.builtin.import_role:
    name: base_image
  vars:
    base_image_os_version: "fedora-39"
    base_image_pathname: "/var/lib/libvirt/images/kdevops/base-images/fedora-39.raw"
```

For further examples refer to one of this role's users, the
[https://github.com/linux-kdevops/kdevops](kdevops) project.

License
-------

copyleft-next-0.3.1
