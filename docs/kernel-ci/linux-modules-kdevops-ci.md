# The Linux kernel modules kdevops CI

The Linux kernel moduleus CI is used to help proactively test patches for
the Linux kernel module loading and to ensure we do not regress. The
files in question are kernel/module/* and related files.

Developers can also push test branches to automatically run tests. We rely
on [kpd](https://github.com/facebookincubator/kernel-patches-daemon)
to help us group up patches posted to the mailing list. The patchwork
instanced used is

 * [linux-modules patchwork instance](https://patchwork.kernel.org/project/linux-modules/list/)

The Linux kernel tree which kdevops uses to run tests on is:

  * [linux-modules-kpd](https://github.com/linux-kdevops/linux-modules-kpd)

## linux-modules-kpd tests

The Linux kernel module loading is tested today by using selftests. The kernel
is configured to enable the respective kernel module selftests and they are
run. Since the tests are simple we rely on the main branch of the
[kdevops-ci tree](kdevops-ci-tree.md). All tests are assumed to pass,
if a failure is found a failure is annotated on the kdevops-results-archive
commit log.

## linux-modules-kpd CI testing results

You can see linux-modules-kpd test results here:

  * [Ephemeral  interactive linux-modules-kpd CI results](https://github.com/linux-kdevops/linux-modules-kpd/actions)
  * [Persistent kdevops-results-archive linux-modules-kpd test results](https://github.com/search?q=repo%3Alinux-kdevops%2Fkdevops-results-archive+is%3Acommit+%22linux-modules-kpd%3A%22&type=commits)
