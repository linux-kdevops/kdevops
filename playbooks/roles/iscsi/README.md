iscsi
=====

The iscsi role manages iSCSI targets, initiators, and LUNs.

Ansible runs the main.yml task set to provision a separate system
that will act as the iSCSI target.

The add_initiator.yml task set runs on a test node to enable that
node to access the iSCSI target.

The add_lun.yml task set runs on a test node or on a storage server
node (such as the kdevops NFS server) to provision a new LUN. The
node must already be set up as an iSCSI initiator.

Requirements
------------

None. This role installs any necessary administrative tools
automatically.

Role Variables
--------------

  * iscsi_target_wwn: the WWN of the iSCSI target
  * iscsi_target_hostname: the DNS hostname of the iSCSI target
  * iscsi_target_pv_prefix: the prefix of the name of the LVM
    physical volume group on the iSCSI target that contains LUN
    backing storage
  * iscsi_target_pv_count: the total number of physical devices
    to be added to the LVM physical volume group on the iSCSI
    target that contains LUN backing storage
  * iscsi_target_vg_name: the name of the LVM volume group on the
    iSCSI target that contains LUN backing storage

  * iscsi_add_devname: the unique name of the new LUN to be added
  * iscsi_add_size: the size of the new LUN to be added

Dependencies
------------

None.

Example Playbook
----------------

Below is an example playbook task:

```
- name: Create a new iSCSI LUN
  ansible.builtin.include_role:
    name: iscsi
    from_tasks: add_lun
  vars:
    iscsi_add_devname: "{{ export_volname }}"
    iscsi_add_size: "{{ export_size }}"
  tags: test_nfs_enable
```

For further examples refer to one of this role's users, the
[https://github.com/linux-kdevops/kdevops](kdevops) project.

License
-------

copyleft-next-0.3.1
