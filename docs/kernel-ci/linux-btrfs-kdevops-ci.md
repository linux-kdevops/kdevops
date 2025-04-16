# The Linux kernel btrfs kdevops CI

The btrfs kdevops CI is used to help proactively allow btrfs Linux kernel
developers test branches automatically through kdevops. Although
[kpd](https://github.com/facebookincubator/kernel-patches-daemon)
is not used we use the kpd prefix for the btrfs kdevops CI tree in case a
patchwork instance and
[kpd](https://github.com/facebookincubator/kernel-patches-daemon)
may be leveraged at later future time. The btrfs kdevops CI tree is:

  * [linux-btrfs-kpd](https://github.com/linux-kdevops/linux-btrfs-kpd)

## linux-btrfs-kpd tests

Read [kdevops filesystem CI testing](linux-filesystems-kdevops-CI-testing.md)
first.

## linux-btrfs-kpd CI testing results

You can see linux-btrfs-kpd test results here:

  * [Ephemeral  interactive linux-btrfs-kpd CI results](https://github.com/linux-kdevops/linux-btrfs-kpd/actions)
  * [Persistent kdevops-results-archive linux-btrfs-kpd test results](https://github.com/search?q=repo%3Alinux-kdevops%2Fkdevops-results-archive+is%3Acommit+%22linux-btrfs-kpd%3A%22&type=commits)
