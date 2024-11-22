# kdevops-ci tree

The different ``git CI solutions`` supported (github actions and gitlab
pipelines) are supported to enable Linux kernel testing using kdevops
through a specific git tree:

  * [kdevops-ci](https://github.com/linux-kdevops/kdevops-ci)

The main branch is intended to be generic enough for all simple Linux
kernel tests which don't have complex tests and which also use and leverage
the Linux kernel selftests. Topic branches allow further subsystem CI test
customizations which we don't yet generalize. Topic branches may also be
inevitable since since each CI may have custom test variability options. It
might be possible to address the variability for each test in one main tree in
the future, however this would require a bit more R&D to investigate if this
is possible.

Test results are pushed onto the
[kdevops-results-archive](https://github.com/linux-kdevops/kdevops-results-archive)
and each results has a commit log intended to be descriptive enough to help
developers easily understand the final status of a test. Topic branches also
allow each subsystem developer to fine to results status messaging for tests.

## kdevops-ci branches

The following branches track different subsystems:

  * [main](https://github.com/linux-kdevops/kdevops-ci/tree/main): tracks simple Linux kernel tests and [Linux kernel selftests](https://www.kernel.org/doc/html/latest/dev-tools/kselftest.html)
  * [fstests](https://github.com/linux-kdevops/kdevops-ci/tree/fstests): example branch you should use to start your filesystem specific support
  * [xfs](https://github.com/linux-kdevops/kdevops-ci/tree/xfs): the latest XFS CI
  * [mm](https://github.com/linux-kdevops/kdevops-ci/tree/mm): CI for Linux kernel memory management

# kdevops-ci file

We try to break down work into different files. This allows us to share as much
code as possible on the main branch. The main branch has these files for
instance:

  * [.github/workflows/kdevops-init.yml](https://github.com/linux-kdevops/kdevops-ci/blob/main/.github/workflows/kdevops-init.yml)
  * [.github/workflows/kdevops-cleanup.yml](https://github.com/linux-kdevops/kdevops-ci/blob/main/.github/workflows/kdevops-generic.yml)
  * [.github/workflows/kdevops-generic.yml](https://github.com/linux-kdevops/kdevops-ci/blob/main/.github/workflows/kdevops-generic.yml)

However a filesystem would replace the kdevops-generic.yml file with:

  * [.github/workflows/kdevops-fstests.yml](https://github.com/linux-kdevops/kdevops-ci/blob/fstests/.github/workflows/kdevops-fstests.yml)

And the mm subsystem CI would replace the same kdevops-generic.yml file with:

  * [.github/workflows/kdevops-mm.yml](https://github.com/linux-kdevops/kdevops-ci/blob/mm/.github/workflows/kdevops-mm.yml)

The delta between the main subsystem worker file is pretty minor to the
[kdevops-fstests.yml](https://github.com/linux-kdevops/kdevops-ci/blob/fstests/.github/workflows/kdevops-fstests.yml) file,
mostly test results parsing modifications for the
[kdevops-results-archive](https://github.com/linux-kdevops/kdevops-results-archive)
and CI variability on the web graphical user interface when you are customizing
a test. It may be possible in the future to completely avoid all this delta,
that however will require more CI R&D.

# Consideration of long running tests

github actions lets you customize when you should run tests. These can be
triggered by pull requests, pushes, or manual runs. The main branch of
kdevops-ci by default enables all methods to trigger tests. But for some
subsystems, running a full test can take 4-8 hours. For this reason some
topic branches on kdevops-ci may disable automatic test runs on git pushes.

For example, the fstests branch for kdevops-ci disables running tests on
git push. You can however force to enable this in your CI workflow easily,
with just three lines of github action code:

```
diff --git a/.github/workflows/kdevops-fstests.yml b/.github/workflows/kdevops-fstests.yml
index b2da84e96f42..eafc9c59b394 100644
--- a/.github/workflows/kdevops-fstests.yml
+++ b/.github/workflows/kdevops-fstests.yml
@@ -14,9 +14,9 @@ name: Run fstests
 #
 
 on:
-#  push:
-#    branches:
-#      - '**'
+  push:
+    branches:
+      - '**'
   pull_request:
     branches:
       - '**'
```

You should consider how long tests take before enabling automatic tests
to run on all git pushes.

# Merging kdevops-ci into Linux kernel trees

To leverage kdevops for a CI all you need to do merge the kdevops-ci topic
branch for your subsystem into your Linux kernel tree and git push the branch
to a kdevops CI tree dedicated for your subsystem. The only thing special
about the kdevops CI tree you push your changes onto is that it has a github
self-hosted runner which is capable of running kdevops.

For example if working on XFS testing, you would use the xfs branch of
kdevops-ci, and so you would just do something like this:

```
# Merge the kdevops-ci xfs branch
git remote add kdevops-ci https://github.com/linux-kdevops/kdevops-ci.git
git merge kdevops-ci/xfs --allow-unrelated-histories --squash
git commit -a -s -m "CI: add kdevops actions from $(date -I)" 

# Push onto linux-kdevops-xfs
git remote add linux-xfs-kpd git@github.com:linux-kdevops/linux-xfs-kpd.git
git push -u linux-xfs-kpd example-xfs:example-xfs
```

For most subsystem, git pushes of new branches trigger automatic test runs.
However, since filesystems take long, by default you'd have to go and trigger
the run manually after a git push. You can view live tests running in realtime
and you can also trigger test runs by going to the respective subsystem
github actions page. For example to view existing test runs for XFS or to
trigger a new custom XFS test you can go to
[linux-xfs-kpd actions page](https://github.com/linux-kdevops/linux-xfs-kpd/actions).
