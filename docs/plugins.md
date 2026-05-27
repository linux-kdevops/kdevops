# kdevops Plugin System

kdevops supports a versioned plugin system that allows workflows to be
distributed and installed from external sources. Plugins can be hosted in git
repositories, distributed as tarballs, or loaded from local directories.

## Overview

The plugin system extends the user-private workflows infrastructure with:

- **Versioned releases**: Plugins can specify versions via git tags or versioned tarballs
- **Manifest metadata**: Each plugin includes a `plugin.yaml` with metadata
- **Taint tracking**: Configurations using plugins are marked as "tainted"
- **Simple installation**: Install plugins with `make kdevops-plugin-add URL=<url>`

## Installing Plugins

### From a Git Repository

```bash
# Install the latest version
make kdevops-plugin-add URL=https://github.com/mcgrof/knlp

# Install a specific version (git tag or branch)
make kdevops-plugin-add URL=https://github.com/mcgrof/knlp REF=v1.0.0
```

For GitHub repositories, the plugin system downloads tarballs directly via
curl rather than git cloning, making installation fast and efficient.

### From a Local Directory

```bash
# Install from a project directory with .kdevops/
make kdevops-plugin-add URL=/path/to/project

# Install a specific version (if versioned tarballs exist)
make kdevops-plugin-add URL=/path/to/project REF=1.0.0
```

### From a Tarball

```bash
# Install from a tarball
make kdevops-plugin-add URL=/path/to/.kdevops-1.0.0.tar.xz
```

## Managing Plugins

### List Installed Plugins

```bash
make kdevops-plugin-list
```

Example output:
```
Installed plugins:

NAME                 VERSION      SOURCE
----                 -------      ------
knlp                 1.0.0        https://github.com/mcgrof/knlp
```

### Evaluate Available Versions

Before installing, you can see what versions are available:

```bash
make kdevops-plugin-evaluate URL=https://github.com/mcgrof/knlp
```

### Update a Plugin

```bash
make kdevops-plugin-update NAME=knlp
```

### Remove a Plugin

```bash
make kdevops-plugin-remove NAME=knlp
```

## Using Plugins

After installing a plugin, enable it in your configuration:

1. Run `make menuconfig`
2. Navigate to the plugin's configuration options
3. Enable the workflow and configure as needed

Alternatively, if the plugin provides a defconfig fragment:

```bash
# Combine base defconfig with plugin fragment
make defconfig-datacrunch-b200+knlp
```

## Creating Plugins

### Plugin Structure

Plugins are stored in a `.kdevops/` directory within your project:

```
your-project/
├── .kdevops/                    # Plugin directory
│   ├── plugin.yaml              # Required: Plugin manifest
│   ├── Kconfig                  # Root Kconfig
│   ├── Makefile                 # Root Makefile
│   ├── defconfigs/
│   │   └── configs/
│   │       └── yourplugin.config
│   ├── workflows/
│   │   └── yourplugin/
│   │       ├── Kconfig
│   │       └── Makefile
│   └── playbooks/
│       ├── yourplugin.yml
│       └── roles/
│           ├── devconfig/tasks/
│           │   ├── main.yml
│           │   └── yourplugin.yml
│           ├── gen_nodes/tasks/
│           │   └── main.yml
│           ├── gen_hosts/
│           │   ├── tasks/main.yml
│           │   └── templates/yourplugin.j2
│           └── yourplugin/
│               ├── defaults/main.yml
│               └── tasks/main.yml
├── src/                         # Your project source
└── README.md
```

### Plugin Manifest (plugin.yaml)

Every plugin must have a `plugin.yaml` in the `.kdevops/` directory:

```yaml
# plugin.yaml - kdevops plugin manifest
apiVersion: kdevops.io/v1
kind: Plugin

metadata:
  # Required: Unique plugin name (used for installation directory)
  name: knlp

  # Required: Semantic version
  version: 1.0.0

  # Required: Short description
  description: "Kernel Natural Language Processing workflow"

  # Optional: Author information
  author: "Your Name <email@example.com>"

  # Optional: License
  license: "copyleft-next-0.3.1"

  # Optional: Git repository URL
  repository: "https://github.com/mcgrof/knlp"

  # Optional: Project homepage
  homepage: "https://github.com/mcgrof/knlp"

spec:
  # Optional: kdevops version compatibility
  kdevops:
    minVersion: "5.0.0"
    maxVersion: ""  # Empty means no upper limit

  # Optional: Dependencies on other plugins
  dependencies: []

  # Optional: Workflow type (dedicated or multi-host)
  workflowType: dedicated

  # Optional: Tags for categorization
  tags:
    - ml
    - ai
    - research
```

### Root Kconfig

The root `Kconfig` should source workflow-specific Kconfigs:

```kconfig
# .kdevops/Kconfig
# SPDX-License-Identifier: copyleft-next-0.3.1

# Source the workflow Kconfig
# Note: Use absolute paths since this is sourced from ~/.config/kdevops/plugins/
source "$(shell, echo $HOME/.config/kdevops/plugins/knlp/workflows/knlp/Kconfig)"
```

### Root Makefile

The root `Makefile` should include workflow-specific Makefiles:

```makefile
# .kdevops/Makefile
# SPDX-License-Identifier: copyleft-next-0.3.1

PLUGIN_DIR := $(HOME)/.config/kdevops/plugins/knlp

ifeq (y,$(CONFIG_KDEVOPS_USER_WORKFLOW_KNLP))
include $(PLUGIN_DIR)/workflows/knlp/Makefile
endif
```

### Workflow Kconfig

Define configuration options for your workflow:

```kconfig
# .kdevops/workflows/knlp/Kconfig
# SPDX-License-Identifier: copyleft-next-0.3.1

config KDEVOPS_USER_WORKFLOW_KNLP
    bool "Enable the knlp workflow"
    default y
    output yaml
    help
      Enable the knlp workflow plugin.

if KDEVOPS_USER_WORKFLOW_KNLP

menu "knlp workflow configuration"

config WORKFLOW_KNLP_GIT_URL
    string "Git repository URL"
    default "https://github.com/mcgrof/knlp.git"
    output yaml

config WORKFLOW_KNLP_GIT_REF
    string "Git reference (branch, tag, or commit)"
    default "main"
    output yaml

endmenu

endif # KDEVOPS_USER_WORKFLOW_KNLP
```

### Workflow Makefile

Define make targets for your workflow:

```makefile
# .kdevops/workflows/knlp/Makefile
# SPDX-License-Identifier: copyleft-next-0.3.1

ifeq (y,$(CONFIG_KDEVOPS_USER_WORKFLOW_KNLP))
PLUGIN_DIR := $(HOME)/.config/kdevops/plugins/knlp

knlp:
    $(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
        -f 30 -i hosts -l all \
        $(PLUGIN_DIR)/playbooks/knlp.yml \
        --extra-vars=@./extra_vars.yaml

knlp-help-menu:
    @echo "knlp workflow targets:"
    @echo "  knlp - Setup and run knlp workflow"

HELP_TARGETS += knlp-help-menu
PHONY += knlp
endif
```

### Defconfig Fragment

Create a config fragment for easy enabling:

```
# .kdevops/defconfigs/configs/knlp.config
CONFIG_KDEVOPS_USER_CONFIG_ENABLE=y
CONFIG_KDEVOPS_USER_WORKFLOW_KNLP=y
```

## Distributing Plugins

### Via Git Repository

The simplest distribution method is a git repository with a `.kdevops/`
directory. Users install with:

```bash
make kdevops-plugin-add URL=https://github.com/youruser/yourproject
```

Version releases are managed via git tags (e.g., `v1.0.0`).

### Via Versioned Tarballs

For releases, you can create versioned tarballs:

```bash
# Create a versioned tarball
cd your-project
tar -cJf .kdevops-1.0.0.tar.xz .kdevops/

# Users can download and install
make kdevops-plugin-add URL=/path/to/.kdevops-1.0.0.tar.xz
```

Or host the tarballs alongside your project for version selection:

```
your-project/
├── .kdevops/                    # Latest version
├── .kdevops.tar.xz              # Latest as tarball
├── .kdevops-1.0.0.tar.xz        # Version 1.0.0
├── .kdevops-1.1.0.tar.xz        # Version 1.1.0
└── ...
```

Users can then evaluate available versions:

```bash
make kdevops-plugin-evaluate URL=/path/to/your-project
```

## Plugin Taint

When plugins are installed, kdevops marks the configuration as "tainted":

```
CONFIG_KDEVOPS_PLUGINS_INSTALLED=y
CONFIG_KDEVOPS_PLUGINS_TAINTED=y
```

This indicates the configuration includes externally-maintained plugins that
are not validated by kdevops maintainers. The taint is informational and
does not affect functionality.

## Plugin Installation Details

Plugins are installed to:

```
~/.config/kdevops/plugins/<plugin-name>/
```

The plugin registry is maintained in:

```
~/.config/kdevops/plugins.json
```

Generated configuration files:

```
~/.config/kdevops/Kconfig.plugins   # Sources all plugin Kconfigs
~/.config/kdevops/Makefile.plugins  # Includes all plugin Makefiles
```

## Example: Converting User Workflow to Plugin

If you have an existing user-private workflow, convert it to a plugin:

1. Create `.kdevops/` directory in your project
2. Move workflow files to `.kdevops/`
3. Create `plugin.yaml` with metadata
4. Update paths in Kconfig and Makefile to use absolute plugin paths
5. Test installation:
   ```bash
   make kdevops-plugin-add URL=/path/to/your-project
   ```

## Troubleshooting

### Plugin Not Found After Installation

Ensure the plugin script generated the Kconfig and Makefile:

```bash
ls -la ~/.config/kdevops/Kconfig.plugins
ls -la ~/.config/kdevops/Makefile.plugins
```

If missing, reinstall the plugin or run:

```bash
~/.config/kdevops/scripts/kdevops-plugin.sh list
```

### Configuration Options Not Appearing

Run `make menuconfig` after installing a plugin to refresh the configuration.

### Plugin Dependencies

If a plugin requires PyYAML or yq for manifest parsing, install them:

```bash
# Using pip
pip install pyyaml

# Or using package manager
sudo apt install python3-yaml  # Debian/Ubuntu
sudo dnf install python3-pyyaml  # Fedora
```
