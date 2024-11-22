# kdevops's own CI

kdevops has its own CI to help allow testing of kdevops patches posted
to the kdevops@lists.linux.dev mailing list and also allow developers to
push development test branches to test. Two repositories are used for testing:

  * [kdevops](https://github.com/linux-kdevops/kdevops) - Main kdevops development tree
  * [kdevops-kpd](https://github.com/linux-kdevops/kdevops-kpd) - CI tree used by [kpd](https://github.com/facebookincubator/kernel-patches-daemon)

We also have a patchwork instance where run time test results are listed
as part of the column with "Success/Warning/Failures" "S/W/F":

  * [kdevops patchwork](https://patchwork.kernel.org/project/kdevops/list/)

Testing is done through both [kdevops](https://github.com/linux-kdevops/kdevops)
and [kdevops-kpd](https://github.com/linux-kdevops/kdevops-kpd) trees,
however the main purpose of the
[kdevops-kpd](https://github.com/linux-kdevops/kdevops-kpd) tree is to
proactively test mailing list patches and not pollute the
[kdevops](https://github.com/linux-kdevops/kdevops) with random test branches.

If you are a kdevops developers you can use either tree to also proactively
test a branch. Each tree uses its own self hosted server.

# kdevops CI testing

The [kdevops](https://github.com/linux-kdevops/kdevops) is where you get
the latest and greatest kdevops. To be sure we don't regress workloads
we proactively test the main tree. The work is defined on the directory
.github/workflows/ and we currently have two workloads:

 * docker-tests.yml - limited docker tests, there's only so much you can do with
   containers on kdevops so this is bare bones testing
 * fstests.yml: build Linus' tree, xfstests-dev, and runs generic/003, collects
   test results

With time this should be expanded to also run similar simple tests for each
supported workload with a limited test scope so to ensure testing will not
regress.

## kdevops CI testing results

You can see kdevops test results here:

  * [Ephemeral  interactive kdevops CI results](https://github.com/linux-kdevops/kdevops/actions)
  * [Persistent kdevops-results-archive kdevops test results](https://github.com/search?q=repo%3Alinux-kdevops%2Fkdevops-results-archive+is%3Acommit+%22kdevops%22+NOT+%22kdevops-kpd%3A%22&type=commits)

# kdevops-kpd CI testing

[kpd](https://github.com/facebookincubator/kernel-patches-daemon) requires
a tree to push branches with patches it gathers from series from patchwork.
To not pollute the branch space on the main development
[kdevops](https://github.com/linux-kdevops/kdevops) tree we use a separate
tree for testing branches which
[kpd](https://github.com/facebookincubator/kernel-patches-daemon) puts
together for us from patches posted to the kdevops@lists.linux.dev mailing list.

## kdevops-kpd CI testing results

You can see kdevops-kpd test results here:

  * [Ephemeral  interactive kdevops-kpd CI results](https://github.com/linux-kdevops/kdevops-kpd/actions)
  * [Persistent kdevops-results-archive kdevops-kpd test results](https://github.com/search?q=repo%3Alinux-kdevops%2Fkdevops-results-archive+is%3Acommit+%22kdevops-kpd%3A%22&type=commits)
