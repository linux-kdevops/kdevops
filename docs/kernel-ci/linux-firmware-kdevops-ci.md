# The Linux kernel firmware loader kdevops CI

The Linux kernel firmware loader CI is used to help proactively test patches for
the Linux kernel firmware loading and to ensure we do not regress. The
files in question are drivers/base/firmware_loader/ and related files.

Developers can also push test branches to automatically run tests. We rely
on [kpd](https://github.com/facebookincubator/kernel-patches-daemon)
to help us group up patches posted to the mailing list. The patchwork
instanced is the first one to rely on lei for custom filtering of emails
posted to the linux-fsdevel mailing list. The patchwork instance is:

 * [linux-firmware loader patchwork instance](https://patchwork.kernel.org/project/firmware/list/)

The Linux kernel tree which kdevops uses to run tests on is:

  * [linux-firmware-kpd](https://github.com/linux-kdevops/linux-firmware-kpd)

## linux-firmware-kpd tests

The Linux kernel firmware loading is tested today by using selftests. The kernel
is configured to enable the respective kernel firmware loader selftest and its
run. Since the tests are simple we rely on the main branch of the
[kdevops-ci tree](kdevops-ci-tree.md). All tests are assumed to pass,
if a failure is found a failure is annotated on the kdevops-results-archive
commit log.

## linux-firmware-kpd CI testing results

You can see linux-firmware-kpd test results here:

  * [Ephemeral  interactive linux-firmware-kpd CI results](https://github.com/linux-kdevops/linux-firmware-kpd/actions)
  * [Persistent kdevops-results-archive linux-firmware-kpd test results](https://github.com/search?q=repo%3Alinux-kdevops%2Fkdevops-results-archive+is%3Acommit+%22linux-firmware-kpd%3A%22&type=commits)

Right now we are having issues with this self-hosted server ... something
is off on 'make bringup' step.
