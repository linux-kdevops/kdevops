smbd_add_share
================

The smbd_add_share role lets you create an SMB share on the Samba
server set up by kdevops.  Basically a rip-off of nfsd_add_export.

Requirements
------------

None. SMB server and LVM administrative tools are installed on the
kdevops Samba server automatically.

Role Variables
--------------

  * server_host: the hostname or IP address of the SMB server where
    the new share is to be created
  * share_volname: the name of the new share, to be created under
    the /shares directory on the SMB server
  * share_options: the share options for the new share (currently not used)
  * share_fstype: the file system type of the new share
  * share_size: the maximum size of the new share
  * share_user: the owner of the new share
  * share_group: the owner group of the new share
  * share_mode: the mode bits for the new share's root directory

Dependencies
------------

None.

Example Playbook
----------------

Below is an example playbook task:

```
- name: Create SMB share for test vol
  include_role:
    name: smbd_add_share
  vars:
    server_host: "kdevops-smbd"
    share_volname: "test"
    share_fstype: "btrfs"
    share_size: 20g
  when:
    - test_fstype == "cifs"
    - test_cifs_use_kdevops_smbd|bool
```

For further examples refer to one of this role's users, the
[https://github.com/linux-kdevops/kdevops](kdevops) project.

License
-------

GPL-2.0+
