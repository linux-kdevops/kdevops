# kdevops filesystem testing support

kdevops has support testing Linux filesystems using the fstests test suite.
This documents support for that.

Bugs found are tracked on each filesystem:

  * [xfs reported bugs](xfs-bugs.md)

# kdevops fstests configuration

Other than using Kconfig to let you configure your bring up environment and
requirements kdevops also brings the options that fstests offers into Kconfig,
and so enables an easy way to configure you fstests test environment.

# kdevops fstests dedicated workflow

If you are going to test a filesystem you really want to enable a dedicated
workflow (`CONFIG_KDEVOPS_WORKFLOW_DEDICATE_FSTESTS=y`) as that allows kdevops
to let you pick and choose the different target filesystem configuration options
you can test. Some Linux distributions may have older kernels, for instance,
which may not have support for new features which cannot be tested. kdevops uses
Kconfig to allow developers to `select` which target filesystem configuration
options are supported by a distro kernel or not. This avoids having users
testing incorrect or unsupported filesystem configurations.

A dedicated workflow also let's us build target host nodes either for a cloud
deployment or a local virtualization setup which is built off of each target
supported filesystem configuration we support.

# Target devices to use to test

fstest requires at least one drive to test a filesystem, however, there are
cheap ways for us to create multiple drives to support more advanced tests.
Since there are different ways to to create multiple devices this is a
configurable option for kdevops. A dedicated kdevops fstsets workflow has the
option to either use use real NVMe drives to test filesystems or we can build
sparse files for you. The NVMe drives may exist already or if you are using
virtualization, they may be pass onto the guest with PCIe passthrough support.
More details for each of these follow.

# kdevops sparse file testing

kdevops supports testing using sparse or
[truncated files with loopback block devices](docs/testing-with-loopback.md)
so to minimize disk usage and requirements. With this mechanism you only use
disk space for the actual required test, nothing more.

# Testing with real NVMe drives

kdevops supports using real NVMe drives for filesystem testing when used in
a kdevops dedicated fstests workflow.

NVMe drive support relies on the symlinks:

  * `/dev/disk/by-id/nvme`
  * `/dev/disk/by-id/nvme`$model-$serial as an optional fallback

For more details refer to [test using real NVMe drives](docs/testing-with-nvme.md).
The symlinks are used to ensure the same drives are used upon reboot.

You can use real NVMe drives on nodes which are on baremetal, the cloud,
or virtualization using [PCIe passthrough](docs/libvirt-pcie-passthrough.md).
kdevops supports all these and automates it setup for you.

# Running fstests

Just run:

  * `make fstests`
  * `make fstests-baseline`
  * `make fstests-results`

# Running fstests against only a set of tests

You can run tests only against a smaller subset of tests with something like;

```bash
make fstests-baseline TESTS="generic/531 xfs/008 xfs/013"
```

The expunge will will *not* be used if the TESTS argument is used and so
running the above will *ensure* the tests are run even if they are known to
crash on a system for a target section.

# A/B Testing with Different Kernels

kdevops supports advanced A/B testing workflows that allow you to compare test
results between different kernel versions, branches, or configurations. This is
particularly useful for validating patches, comparing stable releases, or
detecting performance regressions across kernel versions.

## CLI Environment Variables

You can use environment variables to configure kdevops without modifying your
.config file. This is especially useful for automated testing and quick
configuration changes. The following variables are supported:

### A/B Testing Variables

- `TEST_AB=y` - Enables baseline and development nodes
  (sets `CONFIG_KDEVOPS_BASELINE_AND_DEV=y`)

### Host Configuration

- `KDEVOPS_HOSTS_PREFIX="name"` - Sets the hostname prefix for all nodes
  (sets `CONFIG_KDEVOPS_HOSTS_PREFIX`)

### Baseline Kernel Configuration

- `LINUX_TREE=/path/to/tree.git` - Git repository URL or local path for baseline kernel
  (sets `CONFIG_BOOTLINUX_TREE`)
- `LINUX_TREE_REF=v6.16` - Git reference (tag, branch, or commit) for baseline
  (sets `CONFIG_BOOTLINUX_TREE_REF`)

### Development Kernel Configuration (A/B Testing)

- `LINUX_DEV_TREE=/path/to/tree.git` - Git repository for development kernel
  (sets `CONFIG_BOOTLINUX_DEV_TREE`)
- `LINUX_DEV_TREE_REF=branch-name` - Git reference for development kernel
  (sets `CONFIG_TARGET_LINUX_DEV_REF`)

### Testing Configuration

- `SOAK_DURATION=432000` - Duration in seconds for soak testing (432000 = 5 days)
  (sets `CONFIG_FSTESTS_SOAK_DURATION`)

## A/B Testing Workflow Example

Here's a complete example that tests XFS reflink functionality comparing a
stable kernel (v6.16) against a development branch with new patches:

```bash
# Configure kdevops with A/B testing enabled
make defconfig-xfs_reflink \
    TEST_AB=y \
    KDEVOPS_HOSTS_PREFIX="parallewb" \
    LINUX_TREE=/mirror/mcgrof-linus.git/ \
    LINUX_TREE_REF=v6.16 \
    LINUX_DEV_TREE=/mirror/mcgrof-linus.git/ \
    LINUX_DEV_TREE_REF="20250807-migrate-folios-stats-pw" \
    SOAK_DURATION=432000 -j128

# Build the configuration
make -j$(nproc)

# Provision baseline and dev nodes
make bringup

# Build and install kernels (baseline on baseline node, dev on dev node)
make linux

# Run fstests on baseline and dev
make fstests-tests
```

### Understanding the Configuration

This example creates two test nodes:

1. **Baseline node** (`parallewb-xfs-reflink`):
   - Runs kernel v6.16 from `/mirror/mcgrof-linus.git/`
   - Provides the reference test results, ie, this is our baseline

2. **Development node** (`parallewb-xfs-reflink-dev`):
   - Runs kernel from branch `20250807-migrate-folios-stats-pw`
   - Tests new patches against the baseline

Both nodes run the same XFS reflink test configuration, allowing direct
comparison of test results between kernel versions.

### Long-term Soak Testing

The `SOAK_DURATION=432000` (5 days) enables extended stress testing:

- Tests designed for soak testing will run for the specified duration
- Helps catch rare race conditions and memory leaks
- More effective than simple test loops for long-term stability validation
- Results are tracked separately for baseline and dev nodes
- This is an insane amount of time as it will take 5 days *per* test
  which supports to run with soak duration. So this is just an example.

### Comparing Results

After tests complete, you can compare results between baseline and dev nodes.
For detailed information on comparing fstests results, including automated
regression detection and side-by-side comparisons, see the
[Comparing fstests results](https://github.com/linux-kdevops/kdevops-results-archive#comparing-fstests-results)
section in the kdevops-results-archive documentation.

The results archive provides the `bin/compare-results-fstests.py` script which:
- Automatically detects regressions and fixes between test runs
- Provides verbose side-by-side test comparison
- Handles multiple filesystem test profiles
- Extracts kernel versions from commit messages

Quick example:
```bash
# View test results summary
make fstests-results

# For automated comparison using the results archive
cd ../kdevops-results-archive
./bin/compare-results-fstests.py <baseline-commit> <test-commit>

# Detailed verbose comparison
./bin/compare-results-fstests.py <baseline-commit> <test-commit> --verbose
```

### Using Local Git Mirrors

The example uses local git mirrors (`/mirror/mcgrof-linus.git/`) for faster
kernel builds and reduced network usage. Local mirrors are particularly useful
for:

- **Repeated testing**: Avoid re-cloning repositories
- **Offline development**: Work without network access
- **Custom branches**: Test local development branches
- **CI/CD environments**: Faster pipeline execution

You can create a local mirror with:

```bash
git clone --mirror \
    git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git \
    /mirror/mcgrof-linus.git
```

### Parallel Builds

The `-j128` flag enables parallel processing:

- Applied to both configuration (`make defconfig-xfs_reflink -j128`)
- And to the build process (`make -j128`)
- Significantly reduces setup and build time
- Adjust based on your system's CPU core count

## Review regressions

To see regressions:

  * `git diff`

## Commit new expunges

If you know these failures are real, you can commit them:

  * `git add workflows/fstests/expunges/<path-to-kernel>`

It would be nice for you to commit back over results to our archive, specially
if you are adding expunges for a kernel.

## Submitting results to the community archive

kdevops maintains a community results archive at
[kdevops-results-archive](https://github.com/linux-kdevops/kdevops-results-archive)
to help track test baselines across different kernels, configurations, and
environments. You can contribute your test results to help the community build
confidence in kernel baselines.

### Prerequisites

1. Clone the results archive repository in the same parent directory as kdevops:

```bash
cd ..  # Go to parent directory of kdevops
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/linux-kdevops/kdevops-results-archive.git
cd kdevops  # Return to kdevops directory
```

The `GIT_LFS_SKIP_SMUDGE=1` flag prevents downloading all result tarballs,
saving significant bandwidth (results in a ~2.5M directory instead of 218M+).

2. Ensure you have run fstests and have results available:

```bash
make fstests-baseline
# or
make fstests
```

### Using copy-results.sh

The script automates copying your results to the archive with proper organization:

```bash
scripts/workflows/fstests/copy-results.sh
```

The script will:

1. **Detect your environment**: Automatically determines if you're using
   libvirt-qemu, cloud, or custom infrastructure

2. **Organize results**: Creates a directory structure following the pattern:
   ```
   workflows/fstests/results/archive/$USER/$FSTYP/$TYPE/YYYYMMDD-NNNN/
   ```
   Where:
   - `$USER`: Your username
   - `$FSTYP`: Filesystem type (xfs, ext4, btrfs, etc.)
   - `$TYPE`: Infrastructure type (libvirt-qemu, cloud, custom)
   - `YYYYMMDD`: Current date
   - `NNNN`: Sequential counter (0001, 0002, etc.) for multiple runs per day

3. **Copy files**: Places the following files in the archive:
   - `<kernel-version>.xz`: Compressed test results tarball
   - `kdevops.config`: Your kdevops configuration for reproducibility

4. **Stage for commit**: Automatically runs `git add` on the new files

### Example workflow

```bash
# Run your fstests
make fstests-baseline

# Copy results to archive
scripts/workflows/fstests/copy-results.sh

# The script will output the commands it ran and show:
# Filesystem:     xfs
# Kernel tested:  6.9.0-rc6
#
# Running:
#
# mkdir -p workflows/fstests/results/archive/jdoe/xfs/libvirt-qemu/20240505-0001
# cp workflows/fstests/results/6.9.0-rc6.xz workflows/fstests/results/archive/...
# cp .config workflows/fstests/results/archive/.../kdevops.config

# Now commit and push to the archive
cd ../kdevops-results-archive
git commit -a -s
git push
```

### Multiple runs per day

The script supports running multiple tests per day with different configurations
(e.g., XFS with quota enabled vs disabled). Each run gets a unique counter:

```
workflows/fstests/results/archive/jdoe/xfs/libvirt-qemu/20240505-0001/
workflows/fstests/results/archive/jdoe/xfs/libvirt-qemu/20240505-0002/
workflows/fstests/results/archive/jdoe/xfs/libvirt-qemu/20240505-0003/
```

The script automatically increments the counter to avoid conflicts.

### Archive benefits

Results submitted to the archive:

- **Build community baselines**: Help establish known-good test results
- **Track regressions**: Enable comparison across kernel versions
- **Support CI/CD**: Automated dashboard generation at [kdevops.org](https://kdevops.org)
- **Provide reproducibility**: Include configuration files for test recreation
- **Use Git LFS**: Efficient storage and selective download of result tarballs

### Troubleshooting

If the script reports errors:

- **Missing archive**: Ensure `kdevops-results-archive` is cloned in the parent directory
- **No results**: Run `make fstests` or `make fstests-baseline` first
- **Missing files**: Verify `workflows/fstests/results/last-kernel.txt` exists and
  the corresponding `.xz` tarball is present

## Augment expunges for a kernel

If you know this is a real failure which we need to expunge the test so to
help reduce the amount of time to test *by default*. Although it is important
to verify if a test is still occurring, that is a secondary step we can work
on. Developers and users are encouraged to augment the shared expunge list to
help with our known test baseline.

Baselines are available for upstream all Linux kernel releases, linux-next,
development kernel branches, custom R&D branches, and standard Linux
distributions.

If you are not a developer, you can still use kdevops to help test your
distribution kernel baseline, and track the known failures. If some of these
failures are crashes, and you've already updated your latest kernel for that
release, you may want to report the kernel failing to the Linux distribution.

If you are not a developer, you can also help track baselines for the latest
Linux kernels, or stable kernels, and linux-next. If testing Linus' kernel
be sure to use the latest tip tree from Linus' tree. If using stable kernels
make sure they are still listed as supported on kernel.org first, and then
use the latest point release. If using linux-next, be sure to use the
latest linux-next tag.

## Confidence in a baseline

A baseline consists of a set of known failures being expunged. Failure rates may
vary on tests and so to help with this we strive by default to build confidence
of a baseline by running fstests in a loop 100 times.  If no new failures have
been found we consider that we have a high confidence in a baseline and then
it can be used to verify if new development changes are not causing a regression.

The preferred method for long-term testing with fstests is to use the
SOAK_DURATION feature, which allows specific tests designed for soak
testing to run for extended periods. This provides a more targeted approach
to stress testing compared to simply running all tests in a loop.

The value originally comes from kdevops use at SUSE Linux enterprise
distributions, as a litmus test to validate kernel releases, so to ensure
there are no filesystem regressions. Eventually it has also now been adopted
for Linux kernel XFS stable backporting efforts.

You may want to increase or reduce this value depending on your criteria for
testing, but for upstream kdevops testing we want to upkeep at least 100 minimum.

We currently expunge known failures so to reduce time to test. And so any known
test failure is important to expunge, even if the failure rate is one out of
10,000. If a test has a failure rate of 1/10,000, that is one out of 10,000
times running the test, it is still an issue we want to document. We strive
to document failure rates with a comment.

Regardless of how low a failure rate is, we must expunge the test. Eventually
we should verify failures are still occurring and remove tests from expunges
if patches merged fix issues. We should strive to automate this too in the
future.

## Lazy baseline

Since we test different filesystem configurations often, when working on a new
baseline what will happen is a low failure rate test starts to be observed only
in a few target filesystem configuration sections. Eventually, these tests start
failing on other configurations. And so to help reduce the amount of time to
test, after a test fails in at least two test sections (filesystem
configurations) you can use a lazy baseline consideration and just expunge
the test on all sections by using the `all.txt` file.

To do this we a script which will look for common failures, and if found
add them to all.txt, it will then also remove tests found on all.txt but
still present on individual test sections. To process a lazy baseline,
just run:

```bash
./scripts/workflows/fstests/lazy-baseline.sh
```

If you want a high confidence in a baseline you want to avoid the lazy-baseline
as much as possible.

# Initial baseline help

When you work on a new baseline often you are running into crashes and want
to pick up testing after the last test you know that crashed. To help with this
you can use:

```bash
make fstests-baseline START_AFTER=generic/451
```

This will skip testing until *after* generic/451, and so it assumes you are
not using  random order.

This makes use of a patch merged on kdevops's version of fstests which is
not yet merged on upstream fstests, which adds support for the
[fstests check --start-after](https://lore.kernel.org/all/20230907221030.3037715-1-mcgrof@kernel.org/).

# Seeing kdevops community fstests results

See [viewing kdevops archived results](viewing-fstests-results.md) to see
how you can look at existing results file inside kdevops.

# How to add a new filesystem test profile

kdevops strives to supports making make adding new test profiles as easy as
just adding  Kconfig option for it and the respective fstests configuration
entry. The fact that you have to do more work today is a limitation of kconfig
we plan to expand on.

Adding a new target test profile for a filesystem is super easy. All you have
to do is add a test profile, so for example, the tmpfs filesystem has:

```
playbooks/roles/fstests/templates/tmpfs/tmpfs.config
```

In it you will see a `[default]` section, this section is special, it allows
kdevops's wrapper script oscheck.sh to read all variables in it, so it can
share them all for all sections. Each of kdevop's scripts ensures to process
these variables before proceeding.

To add a new section just add the name so for example [tmpfs_huge_always]
was added, and then a respective Kconfig entry for it with the name
matching name FSTESTS_TMPFS_SECTION_HUGE_ALWAYS was added under:

```
playbooks/roles/fstests/templates/tmpfs/tmpfs.config
```

The templates directory is used as that is the default place ansible lets
us stuff in template files we can use with the ansible template task so we
can use jinja2 to parse variables you may have set up.

That's it! Well, due to limitations you will also want to add respective
ansible default variables for the filesystem, and a respective Makefile
entry which switches the default to True when the Makefile detects it is
enabled. For tmpfs that is:

```
workflows/fstests/tmpfs/Makefile
```

Each test section will create a new node / guest / cloud node to test.

Once we extend kconfig to support an extra_vars.yaml output and
we can also select which kconfig entries we want to be output, then these
Makefile hacks are no longer needed.

# How to verify if a filesystem test configuration looks OK

You you are expanding a filesystem configuration file you can test and verify
if your changes make sense with:

```bash
make fstests-config-debug
```

This will allow you to edit just the template file, Kconfig file, the
ansible defaults file, the respective Makefile for the filesystem and see
immediately (without bringup) if the changes look OK.

# How kdevops verifies filesystem test sections

It is painful to spawn nodes up only to realize you messed things up in
your configuration. Because of this kdevops does a bit of sanity checking
to verify that if you enabled a target section we will first ensure it is
a valid test section.

The ansible role gen_nodes is used for this, see:

```
playbooks/roles/gen_nodes/tasks/main.yml
```

The task to review are:

  * "Check which fstests test types are enabled"

This will look do first a;

```
"{{ lookup('file', fs_config_path) }}"
```

This looks for the filesystem configuration, in the case of tmpfs this is:

```
playbooks/roles/fstests/templates/tmpfs/tmpfs.config
```

It will try to look for all '`CONFIG_FSTESTS_`' + fs + '`_SECTION_`' entries in
your `.config` file. It will ignore the `[default]` section as it is shared.
Then it looks for all filesystem configurations enabled with `=y`.

TODO:
  * provide a python script to query all results for a specific test or filesystem.
  * this should assume your current configured kernel first and optionally
    let you override that
