# The Linux kernel ext4 kdevops CI

The ext4 kdevops CI is used to help proactively allow ext4 Linux kernel
developers test branches automatically through kdevops. Although
[kpd](https://github.com/facebookincubator/kernel-patches-daemon)
is not used we use the kpd prefix for the ext4 kdevops CI tree in case a
patchwork instance and
[kpd](https://github.com/facebookincubator/kernel-patches-daemon)
may be leveraged at later future time. The ext4 kdevops CI tree is:

  * [linux-ext4-kpd](https://github.com/linux-kdevops/linux-ext4-kpd)

## linux-ext4-kpd tests

Read [kdevops filesystem CI testing](linux-filesystems-kdevops-CI-testing.md)
first.

## linux-ext4-kpd CI testing results

You can see linux-ext4-kpd test results here:

  * [Ephemeral  interactive linux-ext4-kpd CI results](https://github.com/linux-kdevops/linux-ext4-kpd/actions)
  * [Persistent kdevops-results-archive linux-ext4-kpd test results](https://github.com/search?q=repo%3Alinux-kdevops%2Fkdevops-results-archive+is%3Acommit+%22linux-ext4-kpd%3A%22&type=commits)
