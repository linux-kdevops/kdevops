# Monitoring Services in kdevops

## Overview

kdevops provides a flexible monitoring framework that allows you to collect system metrics and statistics during workflow execution. This is particularly useful for:

- Performance analysis during testing
- Debugging kernel behavior
- Understanding system resource usage patterns
- Validating new kernel features with custom metrics

The monitoring framework runs services in the background during workflow execution and automatically collects results afterward.

## Configuration

### Enabling Monitoring

Monitoring services are configured through the kdevops menuconfig system:

```bash
make menuconfig
# Navigate to: Monitors
# Enable: "Enable monitoring services during workflow execution"
```

### Available Monitors

#### Folio Migration Statistics (Developmental)

This monitor tracks page/folio migration statistics in the Linux kernel. It's marked as "developmental" because it requires kernel patches that are not yet upstream.

**Requirements:**
- Kernel with folio migration debugfs stats patch applied
- Debugfs mounted at `/sys/kernel/debug`
- File exists: `/sys/kernel/debug/mm/migrate/stats`

**Configuration:**
```bash
make menuconfig
# Navigate to: Monitors
# Enable: "Enable monitoring services during workflow execution"
# Enable: "Enable developmental statistics (not yet upstream)"
# Enable: "Monitor folio migration statistics"
# Set: "Folio migration monitoring interval" (default: 60 seconds)
```

## Integration with Workflows

### Currently Supported Workflows

- **fstests**: Filesystem testing framework
- **blktests**: Block layer testing framework
- **sysbench**: Database performance testing framework

### How Workflows Integrate Monitoring

Workflows integrate monitoring by including the monitoring role at appropriate points. Here's the pattern used in fstests:

```yaml
# Start monitoring before tests
- name: Start monitoring services
  include_role:
    name: monitoring
    tasks_from: monitor_run
  when:
    - kdevops_run_fstests|bool
    - enable_monitoring|default(false)|bool
  tags: [ 'oscheck', 'fstests', 'run_tests', 'monitoring', 'monitor_run' ]

# ... workflow tasks run here ...

# Stop monitoring and collect data after tests
- name: Stop monitoring services and collect data
  include_role:
    name: monitoring
    tasks_from: monitor_collect
  when:
    - kdevops_run_fstests|bool
    - enable_monitoring|default(false)|bool
  tags: [ 'oscheck', 'fstests', 'run_tests', 'monitoring', 'monitor_collect' ]
```

### Adding Monitoring to Your Workflow

To add monitoring support to a new workflow:

1. **Identify the execution boundaries**: Determine where your workflow starts and completes its main work.

2. **Include the monitoring role**: Add the monitoring role calls before and after your main tasks:

```yaml
# In your workflow's main task file (e.g., playbooks/roles/YOUR_WORKFLOW/tasks/main.yml)

# Set custom monitoring results path (optional)
- name: Set monitoring results path for this workflow
  set_fact:
    monitoring_results_base_path: "{{ topdir_path }}/workflows/YOUR_WORKFLOW/results/monitoring"
  when:
    - enable_monitoring|default(false)|bool

# Start monitoring
- name: Start monitoring services
  include_role:
    name: monitoring
    tasks_from: monitor_run
  when:
    - your_workflow_condition|bool
    - enable_monitoring|default(false)|bool
  tags: [ 'your_workflow', 'monitoring', 'monitor_run' ]

# Your workflow tasks here...

# Stop monitoring
- name: Stop monitoring services and collect data
  include_role:
    name: monitoring
    tasks_from: monitor_collect
  when:
    - your_workflow_condition|bool
    - enable_monitoring|default(false)|bool
  tags: [ 'your_workflow', 'monitoring', 'monitor_collect' ]
```

3. **Test the integration**: Run your workflow with monitoring enabled to verify data collection.

## Output and Results

### Result Location

Monitoring results are stored in workflow-specific directories:

- **fstests**: `workflows/fstests/results/monitoring/`
- **Other workflows**: `workflows/YOUR_WORKFLOW/results/monitoring/`

Workflows can customize the results path by setting the `monitoring_results_base_path` variable in their playbook.

### Result Files

For folio migration monitoring:
- `<hostname>_folio_migration_stats.txt`: Raw statistics with timestamps
- `<hostname>_folio_migration_plot.png`: Visualization plot (if generation succeeds)

### Example Output

Raw statistics file format:
```
2024-01-15 10:30:00
success: 12345
fail: 67
total: 12412

2024-01-15 10:31:00
success: 12456
fail: 68
total: 12524
```

## Running Workflows with Monitoring

### Example: fstests with Folio Migration Monitoring

1. **Configure monitoring**:
```bash
make menuconfig
# Enable monitoring options as described above
make
```

2. **Provision systems**:
```bash
make bringup
```

3. **Run tests with monitoring**:
```bash
# Run on both baseline and dev groups
make fstests-tests TESTS=generic/003

# Or run on specific group
make fstests-baseline TESTS=generic/003
```

4. **Check results**:
```bash
ls -la workflows/fstests/results/monitoring/
```

## Advanced Usage

### Custom Monitoring Intervals

You can override the monitoring interval at runtime:

```bash
make fstests-tests EXTRA_VARS="monitor_folio_migration_interval=30"
```

### Selective Monitoring

You can enable/disable specific monitors at runtime:

```bash
# Enable only folio migration monitoring
make fstests-tests EXTRA_VARS="enable_monitoring=true monitor_folio_migration=true"
```

## Troubleshooting

### Monitor Not Starting

1. **Check kernel support**:
```bash
ansible all -m shell -a "ls -la /sys/kernel/debug/mm/migrate/stats"
```

2. **Verify debugfs is mounted**:
```bash
ansible all -m shell -a "mount | grep debugfs"
```

3. **Check monitoring process**:
```bash
ansible all -m shell -a "ps aux | grep monitoring"
```

### No Data Collected

1. **Verify monitoring was enabled**:
```bash
grep -E "enable_monitoring|monitor_" .config
```

2. **Check ansible output for monitoring tasks**:
```bash
make fstests-tests AV=2 | grep -A5 -B5 monitoring
```

3. **Look for error messages**:
```bash
ansible all -m shell -a "cat /root/monitoring/folio_migration.log"
```

## Adding New Monitors

To add a new monitor to the framework:

1. **Add Kconfig option** in `kconfigs/monitors/Kconfig`:
```kconfig
config MONITOR_YOUR_METRIC
	bool "Monitor your metric description"
	output yaml
	default n
	help
	  Detailed description of what this monitors...
```

2. **Extend monitoring role**:
   - Add collection logic in `playbooks/roles/monitoring/tasks/monitor_run.yml`
   - Add termination and data collection in `playbooks/roles/monitoring/tasks/monitor_collect.yml`

3. **Add visualization** (optional):
   - Place scripts in `playbooks/roles/monitoring/files/`
   - Call them from `monitor_collect.yml`

4. **Update documentation**: Add your monitor to this documentation file.

## Performance Considerations

- **Monitoring overhead**: Each monitor adds some system overhead. Consider the trade-off between data granularity and performance impact.
- **Storage requirements**: Long-running tests with frequent monitoring can generate large data files.
- **Concurrent monitors**: Running multiple monitors simultaneously increases overhead.

## Future Enhancements

Planned monitoring additions:
- Memory pressure statistics
- CPU utilization tracking
- I/O statistics collection
- Network traffic monitoring
- Custom perf event monitoring
- Integration with Grafana/Prometheus for real-time visualization
