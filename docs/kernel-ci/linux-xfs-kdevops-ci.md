# The Linux kernel XFS kdevops CI

The XFS kdevops CI is used to help proactively allow XFS Linux kernel
developers test branches automatically through kdevops. Although
[kpd](https://github.com/facebookincubator/kernel-patches-daemon)
is not used we use the kpd prefix for the XFS kdevops CI tree in case a
patchwork instance and
[kpd](https://github.com/facebookincubator/kernel-patches-daemon)
may be leveraged at later future time. The XFS kdevops CI tree is:

  * [linux-xfs-kpd](https://github.com/linux-kdevops/linux-xfs-kpd)

## linux-xfs-kpd tests

Read [kdevops filesystem CI testing](linux-filesystems-kdevops-CI-testing.md)
first.

## linux-xfs-kpd CI testing results

You can see linux-xfs-kpd test results here:

  * [Ephemeral  interactive linux-xfs-kpd CI results](https://github.com/linux-kdevops/linux-xfs-kpd/actions)
  * [Persistent kdevops-results-archive linux-xfs-kpd test results](https://github.com/search?q=repo%3Alinux-kdevops%2Fkdevops-results-archive+is%3Acommit+%22linux-xfs-kpd%3A%22&type=commits)
