volume_group
============

The volume_group playbook creates a logical volume group
on a target node using unused block devices.

Requirements
------------

The ansible community.general collection must be installed on the
control host.

Role Variables
--------------

  * volume_group_name: The name for new volume group (string)
  * volume_device_prefix: The pathname prefix for block devices to
    consider for the new volume group (string)
  * volume_device_count: The number of block devices to include in
    the new volume group (int)

Dependencies
------------

None.

Example Playbook
----------------

Below is an example playbook task:

```
- name: Create a volume group for NFSD exports
  ansible.builtin.include_role:
    name: volume_group
  vars:
    volume_group_name: "exports"
    volume_device_prefix: "/dev/disk/by-id/virtio*"
    volume_count: 3
```

For further examples refer to one of this role's users, the
[https://github.com/linux-kdevops/kdevops](kdevops) project.

License
-------

copyleft-next-0.3.1
