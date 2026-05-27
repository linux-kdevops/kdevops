# User-Private Workflows

kdevops supports user-private workflows that are stored outside the main
kdevops repository. This allows users to maintain custom workflows without
modifying the kdevops codebase.

## Overview

User-private workflows are stored in `~/.config/kdevops/` (or a custom
directory configured via `KDEVOPS_USER_CONFIG_DIR`). When enabled, kdevops
will:

- Source user Kconfig files for additional configuration options
- Include user Makefiles for custom make targets
- Load user Ansible roles and tasks for node/host generation

## Enabling User-Private Workflows

1. Run `make menuconfig` and navigate to:
   - User-private workflows (top-level menu)
2. Enable "Enable user-private workflows"
3. Optionally customize the user configuration directory

## Directory Structure

```
~/.config/kdevops/
├── Kconfig                    # User Kconfig (sourced by kdevops)
├── Makefile                   # User Makefile (included by kdevops)
├── defconfigs/
│   └── configs/
│       └── <workflow>.config  # Config fragment for make defconfig-base+<workflow>
├── workflows/
│   └── <workflow>/
│       ├── Kconfig            # Workflow-specific Kconfig
│       └── Makefile           # Workflow-specific Makefile
└── playbooks/
    ├── <workflow>.yml         # Workflow playbook (for make <workflow>)
    └── roles/
        ├── devconfig/tasks/
        │   ├── main.yml       # User devconfig tasks (runs on bringup)
        │   └── <workflow>.yml # Workflow setup tasks
        ├── gen_nodes/tasks/
        │   └── main.yml       # Node generation tasks
        ├── gen_hosts/
        │   ├── tasks/
        │   │   └── main.yml   # Host generation tasks
        │   └── templates/
        │       └── <workflow>.j2  # Hosts template
        └── <workflow>/
            ├── defaults/
            │   └── main.yml   # Role defaults
            └── tasks/
                └── main.yml   # Role tasks
```

## Automatic Workflow Setup on Bringup

User workflows can run automatically during `make bringup` by adding tasks to
the devconfig role. The kdevops devconfig role includes user tasks from
`~/.config/kdevops/playbooks/roles/devconfig/tasks/main.yml` if user-private
workflows are enabled.

Example devconfig/tasks/main.yml:
```yaml
- name: Setup my workflow
  ansible.builtin.include_tasks: myworkflow.yml
  when:
    - my_workflow_config_var is defined
    - my_workflow_config_var|bool
  tags: ["myworkflow"]
```

This allows your workflow setup to run automatically when systems are
provisioned, without requiring a separate `make <workflow>` step.

## Example: KNLP Workflow

The `example-knlp/` directory contains a complete example of the KNLP
(Kernel Natural Language Processing) workflow configured as a user-private
workflow. To use it:

1. Copy the example files to your user config directory:

```bash
mkdir -p ~/.config/kdevops
cp -r docs/user-workflows/example-knlp/* ~/.config/kdevops/
```

2. Use the defconfig fragment to enable KNLP with any base configuration:

```bash
make defconfig-datacrunch-b200-or-less+knlp
make
make bringup
```

The `+knlp` fragment (from `~/.config/kdevops/defconfigs/configs/knlp.config`)
enables user-private workflows, which sources your user Kconfig and enables
the KNLP workflow automatically.

Alternatively, you can enable user-private workflows manually via menuconfig:

```bash
make defconfig-datacrunch-b200-or-less
make menuconfig
# Navigate to: User-private workflows → Enable user-private workflows
```

## Creating Your Own Workflow

1. Create the directory structure under `~/.config/kdevops/`
2. Define your workflow Kconfig with configuration options
3. Create a Makefile with your workflow targets
4. Add gen_nodes tasks to create the nodes file
5. Add gen_hosts tasks and template to create the hosts file
6. Create your workflow playbook and roles

### Kconfig Guidelines

Your user Kconfig should source workflow-specific Kconfigs using shell expansion:

```kconfig
source "$(shell, echo $HOME/.config/kdevops/workflows/myworkflow/Kconfig)"
```

Note: Kconfig variables like `$(KDEVOPS_USER_CONFIG_DIR_EXPANDED)` are not
available at parse time. Use `$(shell, ...)` for path expansion.

Use `output yaml` on config options that need to be available to Ansible.

### Makefile Guidelines

Your user Makefile should include workflow-specific Makefiles:

```makefile
ifeq (y,$(CONFIG_MY_WORKFLOW))
include $(CONFIG_KDEVOPS_USER_CONFIG_DIR_EXPANDED)/workflows/myworkflow/Makefile
endif
```

### Ansible Guidelines

- Use `kdevops_user_config_dir_expanded` variable to reference files in your
  private config directory
- Your gen_nodes/gen_hosts tasks are included after the built-in workflow tasks
- Use conditional logic (`when:`) to ensure your tasks only run when your
  workflow is enabled
