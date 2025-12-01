# Ansible Callback Plugins

kdevops supports multiple Ansible stdout callback plugins for controlling
playbook output. The callback plugin can be configured via Kconfig or
overridden from the command line.

## Supported Plugins

| Plugin | Description |
|--------|-------------|
| dense (default) | Compact output from community.general |
| debug | Ansible builtin debug callback |
| diy | Customizable output from community.general |
| lucid | Clean, minimal output with dynamic display (kdevops custom) |
| custom | Any Ansible callback plugin by name |

## Configuration

### Via Kconfig

Select the callback plugin in menuconfig:

```bash
make menuconfig
# Navigate to: Ansible Callback Plugin Configuration
```

### Via Command Line

Override the default at build time:

```bash
make ANSIBLE_CFG_CALLBACK_PLUGIN=lucid menuconfig
make
```

When `ANSIBLE_CFG_CALLBACK_PLUGIN` is set via environment, the custom plugin
option is automatically selected and populated with the specified value.

## Plugin Details

### dense (default)

The dense callback from community.general provides compact single-line output.

- Documentation: https://docs.ansible.com/ansible/latest/collections/community/general/dense_callback.html

### debug

The Ansible builtin debug callback shows detailed task information.

- Documentation: https://docs.ansible.com/ansible/latest/collections/ansible/builtin/debug_module.html

### diy

The DIY callback from community.general allows custom output formatting
via ansible.cfg configuration.

- Documentation: https://docs.ansible.com/ansible/latest/collections/community/general/diy_callback.html

### lucid

A custom callback plugin developed for kdevops providing clean, minimal
output with progressive verbosity levels and optional dynamic terminal
display.

#### Features

- Clean, minimal output by default (shows only changes and errors)
- Progressive verbosity with `-v`, `-vv`, `-vvv` flags
- Dynamic live display for interactive terminals (BitBake/Yocto style)
- Automatic static fallback for CI/CD and piped output
- Task-level output control via `output_verbosity` variable
- Comprehensive logging (always max verbosity, independent of display)
- Consistent time tracking shown for all tasks in both modes

#### Status Symbols

| Symbol | Status | Meaning |
|--------|--------|---------|
| ✓ | ok | Task succeeded, no changes made |
| * | changed | Task succeeded and made changes |
| ✗ | failed | Task failed |
| ⊘ | skipped | Task was skipped |
| ! | unreachable | Host was unreachable |

Example output (no flags):

```
TASK: Install packages
  * [host2] (2.3s)
TASK: Configure service
  ✗ [host2] (0.1s)
```

Example output with `-v`:

```
TASK: Install packages
  ✓ [host1] (0.6s)
  * [host2] (2.3s)
    $ apt-get install -y nginx
TASK: Configure service
  ⊘ [host1] (0.0s)
  ✗ [host2] (0.1s)
```

#### Verbosity Levels

Lucid uses Ansible's standard verbosity flags to control output detail:

| Flag | Level | Console Output |
|------|-------|----------------|
| (none) | 0 | Only changed, failed, unreachable tasks (with stdout/stderr) |
| `-v` | 1 | All tasks (ok, skipped) + executed commands + stdout/stderr |
| `-vv` | 2 | Above + tasks with `output_verbosity: 2` |
| `-vvv` | 3 | Above + tasks with `output_verbosity: 3` |

**Output display rules:**
- Changed, failed, unreachable: Always show stdout/stderr/msg
- OK tasks: Show stdout/stderr only with `-v` or higher
- Skipped tasks: Show only with `-v` or higher

**Log files always capture full output regardless of verbosity level.**

#### Enable lucid

```bash
./scripts/kconfig/merge_config.sh -n .config defconfigs/configs/lucid.config
make
```

Or via command line:

```bash
make ANSIBLE_CFG_CALLBACK_PLUGIN=lucid menuconfig
make
```

#### CI/CD Configuration

For CI/CD environments where you want full verbose output similar to log files,
use the lucid-ci configuration fragment:

```bash
./scripts/kconfig/merge_config.sh -n .config defconfigs/configs/lucid-ci.config
make
```

This enables lucid with static output mode and verbosity level 1, providing
comprehensive output including all task results, executed commands, and
stdout/stderr without requiring manual `-v` flags.

The verbosity level can be configured via Kconfig:

```bash
make menuconfig
# Navigate to: Ansible Configuration -> Ansible verbosity level
```

Or override at runtime using the native Ansible environment variable:

```bash
ANSIBLE_VERBOSITY=1 make target  # Force verbosity level 1 for this run
```

#### Parameters

| Parameter | Choices/Defaults | Configuration | Comments |
|-----------|------------------|---------------|----------|
| output_mode | Choices: auto/static/dynamic<br>Default: auto | ini: [callback_lucid] output_mode<br>env: ANSIBLE_LUCID_OUTPUT_MODE | Display mode: auto detects terminal, static for CI/CD, dynamic for live updates |

Log files are automatically created in `.ansible/logs/` with timestamped filenames.

#### Command Display

When running with `-v` or higher verbosity, lucid shows the executed command
for modules that expose their commands in task results:

- `ansible.builtin.shell`, `ansible.builtin.command`
- `ansible.builtin.pip`
- `community.general.make`
- `community.general.flatpak`, `community.general.flatpak_remote`
- `community.general.terraform`

Commands are always logged to the log file regardless of verbosity level.

#### Task-level Output Control

Control visibility of individual tasks using the `output_verbosity` variable.
Tasks are shown when the current verbosity level meets or exceeds the task's
`output_verbosity` setting:

```yaml
- name: Always visible task (shown even without -v)
  debug:
    msg: "Important status message"
  vars:
    output_verbosity: 0

- name: Normal task (shown with -v)
  debug:
    msg: "Standard task output"
  vars:
    output_verbosity: 1  # This is the default

- name: Debug task (shown with -vv)
  debug:
    msg: "Debugging information"
  vars:
    output_verbosity: 2

- name: Trace task (shown with -vvv)
  debug:
    msg: "Detailed trace output"
  vars:
    output_verbosity: 3
```

#### Force Static Mode

Use the environment variable to force static output mode:

```bash
ANSIBLE_LUCID_OUTPUT_MODE=static ansible-playbook playbooks/test.yml
```

Or via make:

```bash
ANSIBLE_LUCID_OUTPUT_MODE=static make bringup
```

The standard `TERM=dumb` convention is also respected for compatibility:

```bash
TERM=dumb make bringup
```

#### Dynamic Mode Display

In dynamic mode, the display shows all hosts participating in a task with a
stable layout that prevents flickering:

```
TASK: Install packages

Hosts: 1/2 running
  [⠦]    2.3s  host1 -> localhost
  [ ]          host2

Recent:
  * Install deps [host1] (1.2s)
```

Running hosts show a spinner and elapsed time. Non-running hosts show empty
brackets. The time column is fixed-width to prevent display jumping.

#### Delegation Display

Tasks using `delegate_to` show delegation info in the format `host -> delegate`,
matching Ansible's default callback behavior:

```
  * [host1 -> localhost] (2.3s)
```

This appears in static mode, dynamic mode, and log files.

#### Notes

- Dynamic mode provides live updates with spinner when running in interactive terminals
- Automatically detects CI/CD environments (GitHub Actions, Jenkins, GitLab CI) and uses static mode
- Logs are always full verbosity regardless of display verbosity
- Log files include playbook name and timestamp: `<playbook>-YYYY-MM-DD_HH-MM-SS.log`
- Compatible with ansible.posix.profile_tasks callback
- Failed tasks always freeze dynamic display and switch to static mode

### custom

Select any Ansible callback plugin by name. When selected, a text field
allows entering the full plugin name (e.g., `ansible.posix.json`).

## Timing Analysis

Enable `profile_tasks` for detailed timing analysis alongside any callback:

```bash
make menuconfig
# Enable: Ansible Callback Plugin Configuration -> Enable profile_tasks callback for timing analysis
```

This adds a `TASKS RECAP` section at the end showing execution times for
each task, similar to `systemd-analyze blame`.
