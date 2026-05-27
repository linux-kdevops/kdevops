qemu
====

The Ansible qemu role lets you get and build QEMU from source.
This may be desirable if QEMU offers a feature which is not yet upstream,
which is typically the case for new hardware features.

Requirements
------------

Run a supported OS/distribution:

  * SUSE SLE / OpenSUSE
  * Red Hat / Fedora
  * Debian / Ubuntu

Dependencies
------------

None.

Example Playbook
----------------

Below is an example playbook, say a bootlinux.yml file:

```
---
- hosts: localhost
  roles:
    - role: qemu
```

License
-------

copyleft-next-0.3.1
