# The Linux kernel memory management kdevops CI

The Linux kernel memory management CI is used to help proactively test patches
for the Linux kernel memory management to ensure we do not regress. For now
we are limiting the scope to xarray tree and maple tree modifications. Note
that these are not selftests, you can also either run these tests in kernel
space or in userpsace. We test both.

Developers can also push test branches to automatically run tests. We rely
on [kpd](https://github.com/facebookincubator/kernel-patches-daemon)
to help us group up patches posted to the mailing list. The patchwork
instanced will be the first one to rely on lei for custom filtering of emails
posted to the linux-mm mailing list, we are however waiting on the firmware
loader lei setup to complete assessment as its the first patchwork instance
to leverage lei. The patchwork instance will eventually be created.

The Linux kernel tree which kdevops uses to run tests on is:

  * [linux-mm-kpd](https://github.com/linux-kdevops/linux-mm-kpd)

## linux-mm-kpd tests

The test are simple for now:

 * radix tree testsj
 * maple tree tests

We run both in first kernel space and then userspace.

Since the tests are simple but customized (not selftests) we rely on the
the topic mm branch of the [kdevops-ci tree](kdevops-ci-tree.md).

## linux-mm-kpd CI testing results

You can see linux-mm-kpd test results here:

  * [Ephemeral  interactive linux-mm-kpd CI results](https://github.com/linux-kdevops/linux-mm-kpd/actions)
  * [Persistent kdevops-results-archive linux-mm-kpd test results](https://github.com/search?q=repo%3Alinux-kdevops%2Fkdevops-results-archive+is%3Acommit+%22linux-mm-kpd%3A%22&type=commits)

These tests are running smoothly, we are just waiting for the patchwork
instance to be created, and that will depend on the results of the lei
patchwork instance for the firmware loader, as that's the first lei based
patchwork instance created.
