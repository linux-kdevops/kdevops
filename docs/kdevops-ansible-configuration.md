# kdevops Ansible Configuration

The Ansible Configuration module in kdevops allows the user to configure the
[Ansible configuration file](https://docs.ansible.com/ansible/latest/reference_appendices/config.html#the-configuration-file)
, typically `ansible.cfg` (in kdevops `$TOPDIR_PATH` directory). This file
includes some Ansible settings such as the callback plugin and the Ansible
inventory file configuration (a comma-separated list).


## Ansible Configuration File (`ANSIBLE_CFG_FILE`)

This setting allows the user to define a path and filename to the Ansible
configuration file.

If the specified file already exists, it will not be overwritten. Otherwise,
kdevops will generate one using the Kconfig settings.

Default: `$(TOPDIR_PATH)/ansible.cfg`

See: [Ansible config file](https://docs.ansible.com/ansible/latest/reference_appendices/config.html#the-configuration-file)


## Ansible Inventory File (`ANSIBLE_CFG_INVENTORY`)

Comma-separated list of Ansible inventory source paths. Each entry can be a path
to a file or directory.

Example: `/path/to/hosts,/path/to/inventory_dir`

This is written to the `[defaults]` section of the generated `ansible.cfg`:

```ini
[defaults]
inventory = /path/to/hosts,/path/to/inventory_dir
```

Default: `$(TOPDIR_PATH)/hosts`

See: [Ansible inventory sources](https://docs.ansible.com/ansible/latest/reference_appendices/config.html#default-host-list)


## Callback Plugin Configuration (`ANSIBLE_CFG_CALLBACK_PLUGIN*`)

The callback plugin determines how Ansible output is displayed. You may select one of:

- [debug](https://docs.ansible.com/ansible/latest/collections/ansible/posix/debug_callback.html): formatted stdout/stderr display
- [dense](https://docs.ansible.com/ansible/latest/collections/community/general/dense_callback.html): minimal stdout output
- custom: this allows defining the plugin name manually

See more plugins:
[Ansible callback plugins list](https://docs.ansible.com/ansible/latest/collections/index_callback.html)

Also, see the Parameters section in the debug/dense for a description of the
callback plugin options.


## Python Interpreter Configuration (`ANSIBLE_CFG_INTERPRETER_PYTHON`)

This allows selecting how Ansible discovers or uses a Python interpreter on target systems.

Options include:

- auto
- auto_legacy
- auto_legacy_client
- auto_silent
- custom: this allows defining the path manually

See:
- [Interpreter Discovery](https://docs.ansible.com/ansible/latest/reference_appendices/interpreter_discovery.html#interpreter-discovery)
- [Using Python 3](https://docs.ansible.com/ansible/latest/reference_appendices/python_3_support.html#using-python-3-on-the-managed-machines-with-commands-and-playbooks)

This option can be controlled via command line Makefile parameter `ANSIBLE_CFG_INTERPRETER_PYTHON`.


## Forks Configuration (`ANSIBLE_CFG_FORKS`)

Control the number of parallel forks (concurrent tasks) Ansible may use.

Default: 10

See: [Forks](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_strategies.html#setting-the-number-of-forks)

This option can be controlled via command line Makefile parameter `ANSIBLE_CFG_FORKS`.


## Ansible Deprecation Warnings (`ANSIBLE_CFG_DEPRECATION_WARNINGS`)

Toggle whether Ansible displays deprecation warnings.

Default: Enabled

See: [Deprecation warnings](https://docs.ansible.com/ansible/latest/reference_appendices/config.html#deprecation-warnings)


## Ansible Reconnection Retries (`ANSIBLE_CFG_RECONNECTION_RETRIES`, OpenSUSE only)

Number of SSH reconnection attempts. Ansible retries connections only on SSH return code 255.

Default: 2000

See: [Reconnection retries](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/ssh_connection.html#parameter-reconnection_retries)
