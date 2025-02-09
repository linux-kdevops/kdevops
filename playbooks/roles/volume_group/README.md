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
```

For further examples refer to one of this role's users, the
[https://github.com/linux-kdevops/kdevops](kdevops) project.

License
-------

copyleft-next-0.3.1
