# Linux filesystem kdevops CI testing

kdevops has long supported Linux kernel filesystems testing, and has aimed
to automate all this for years now. The CI infrastructure is new, it started
in 2024 Q4 and is in a state of functional use now by at least one filesystem
maintainer.

The goal behind filesystem CI testing is to make filesystem testing as easy
as a git push onto a tree, or to post a patch onto a mailing list and optionally
allow filesystem maintainers to enable automation of testing for patches posted.
Developers should be able to follow testing progress in realtime for both
patches posted (if this is enabled) and for branch git pushes.

We collectively refer to both github actions and gitlab pipelines as
``git CI solutions``. Although both ``git CI solutions`` are supported we
are starting out with CI filesystem testing on kdevops using github actions
first. Once we have confidence in the github actions workflow files, we can
easily just port these over to gitlab pipelines allowing developers to choose
either ``git CI solution``.

Both self-hosted runners and cloud infrastructure is supported, since kdevops
supports both for filesystems testing already. Currently self-hosted runner
are being used to take advantage of kdevops' mirroring setup, allowing
CIs to quickly clone kernel repositories from the community. This saves both
bandwidth and reduces total test time. If cloud solutions are to be used
federated cloud arrangements are recommended so to also be able to use cloud
mirrors for trees used for filesystem testing.

# kdevops-ci fstests branch

As documented in the [kdevops-ci](docs/kernel-ci/kdevops-ci-tree.md)
documentation, each subsystem has a different branch which can be used
to help test each subsystem. The
[kdevops-ci fstests branch](https://github.com/linux-kdevops/kdevops-ci/tree/fstests)
is the base branch you should use to start doing initial support for your
filesystem. You should create a filesystem specific branch to help carry
any deltas you might have. Ideally we should merge into the
[kdevops-ci fstests branch](https://github.com/linux-kdevops/kdevops-ci/tree/fstests)
everything but its not clear if we want to have the variability to test for
example tmpfs on the xfs ci, and its also not clear if there is a way to only
dynamically enable the variability for each filesystem dynamically through
github actions yet. For now, to make things easier we use the main branch
to track generalities and each filesystem can have its own branch for its
own customizations for variability.

# kdevops fstests CI github actions files

  * [.github/workflows/kdevops-init.yml](https://github.com/linux-kdevops/kdevops-ci/blob/fstests/.github/workflows/kdevops-init.yml)
  * [.github/workflows/kdevops-cleanup.yml](https://github.com/linux-kdevops/kdevops-ci/blob/fstests/.github/workflows/kdevops-generic.yml)
  * [.github/workflows/kdevops-fstests.yml](https://github.com/linux-kdevops/kdevops-ci/blob/fstests/.github/workflows/kdevops-fstests.yml)

If you are going to create your own filesystem CI, you will likely only
have to modify the kdevops-fstests.yml file.

# Test variability

Running a full set of fstests for a filesystem can take a while, 4-8 hours.
For this reason by default we disable pushes of a new branches to trigger
a test. Refer to [kdevops-ci tree documentation](kdevops-ci-tree.md) for
guidelines on how to enable automatic push triggers for tests.

By default then pushing a branch does not trigger anything for filesystem
testing, but it is very easy to enable.

# Filesystem test variability support

The variability that kdevops supports through the adoption of Linux kconfig
enables us to also provide the same variability in the CI testing reflected
through a github custom action workflow.

Support for enabling custom github actions, visible when you see the
``Run workflow`` option on a github actions page, requires the default
branch used for the repository to have in place an existing `.github/*/*.yml`
with the `workflow_dispatch` enabled. Only privileged users of the repository
will be able to trigger manual workflows.

<img src="/docs/kernel-ci/fstests-workflow/0001-fstests-run-workflow.png" width=1024 align=center alt="001-fstests-run-workflow.png">


<table>
  <tr>
    <th>Description</th>
    <th>Options</th>
  </tr>
  <tr>
    <td>
      Here is the first drop down menu once you click on "Run workflow" button.
      With it you can now see different test variability options. Most
      of the test variability options you've defined through Kconfig on kdevops
      can become live realtime test variability options you can now configure from your CI.
    </td>
    <td>
      <img src="/docs/kernel-ci/fstests-workflow/0002-drop-down-menu.png" alt="First drop down menu">
    </td>
  </tr>
  <tr>
    <td>
      You can pick the branch which you want the test to run. Each branch in turn can
       have custom input options of its own. So for example a tree which lacks LBS can
       support can avoid having the options to test 16k, 32k and 64k block size filesystems.
    </td>
    <td>
      <img src="/docs/kernel-ci/fstests-workflow/0003-pick-branch.png" alt="0003-pick-branch.png">
    </td>
  </tr>
  <tr>
    <td>
      You can configure a custom soak duration, by default no soak duration is used.
      If enabled kdevops manages to enable soak duraiton by setting an environment variable
      which will be read at `make defconfig` time. Support for this was added to kdevops
      through commit
      <a href="https://github.com/linux-kdevops/kdevops/commit/e6294385d2b3b6">
        commit e6294385d2b3b6 ("fstests: add support for overriding soak duration through CLI")
      </a>.
      See also related fix
      <a href="https://github.com/linux-kdevops/kdevops/commit/59aee5697ea0">
      commit 59aee5697ea0 ("fstests/Kconfig: use int-specific default for CLI SOAK_DURATION")
      </a>.
    </td>
    <td>
     <img src="/docs/kernel-ci/fstests-workflow/0004-pick-soak.png" alt="Pick soak duration">
    </td>
  </tr>
  <tr>
    <td>
      You can pick the specific test group you want to test, as well, the default in kdevops is to
      test the group "auto".
    </td>
    <td>
      <img src="/docs/kernel-ci/fstests-workflow/0005-pick-group.png" alt="Pick test group">
    </td>
  </tr>
  <tr>
    <td>
      You can select one of all suported tests to run as well, when you do this only that specific
      test will run, that's it. By default all test are run which are part of the "auto" group as
      that is the default test group kdevops uses.
    </td>
    <td>
      <img src="/docs/kernel-ci/fstests-workflow/0006-pick-test.png" alt="Pick your test">
    </td>
  </tr>
  <tr>
    <td>
      If you are working on something specific, you may know you want to only test
      a few select tests, but you may not want to run a full test group or only
      pick one test. From the drop down menu on "Select additional test coverage" pick
      "custom". In the field "Enter custom test" put the list of tests you want to test
      each test separated by a space. In this example we'll run a test with only
      generic/003 and generic/750.
    </td>
    <td>
      <img src="/docs/kernel-ci/fstests-workflow/0007-custom-tests.png" alt="Custom tests">
    </td>
  </tr>
</table>

Then just click on the green button which says `Run workflow`. You can either just
wait for the test to complete or you can also access the console of the runner
and watch live with a status of each machine being tested, a different target
node will run each test filesystem profile.

![0008-run-tests-wait.png](/docs/kernel-ci/fstests-workflow/0008-run-tests-wait.png)

Below is a real example of an interaction with an existing ongoing fstests test
for XFS development. kdevops leverages a custom test specific watchdog in
kdevops for fstests the
[fstests_watchdog.py](https://github.com/linux-kdevops/kdevops/blob/main/scripts/workflows/fstests/fstests_watchdog.py).
For documentation refer to the
[fstests Kconfig](https://github.com/linux-kdevops/kdevops/blob/main/workflows/fstests/Kconfig)
on the related `FSTESTS_WATCHDOG` options and `SOAK_DURATION`. Live monitoring
is only useful for tests which take a long time, like fstests, or blktests.
Each test which takes a long time to run should consider implementing its own
watchdog to allow test progress monitoring.

![example kdevops fstests CI watchdog live run](/docs/kernel-ci/fstests-workflow/0009-watchdog-example-2024-11-12.png)
