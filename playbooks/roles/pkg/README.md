pkg
===

Let's us keep package names for rolling distros, and if users are using
an older release, we provide a wrapper for them.

Requirements
------------

None.


Dependencies
------------

None.

Example Playbook
----------------

Below is an example playbook task:

```
---
- hosts: baseline:dev
  roles:
    - role: dpkg
```

License
-------

copyleft-next-0.3.1
