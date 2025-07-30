# kdevops PROMPTS.md

This file can be used by generative AI agents to learn previous prompts
and example commits and their outcomes, and notes by users of the AI agent
grading. It is also instructive for humans to learn how to use generative
AI to easily extend kdevops for their own needs.

## Extending existing Linux kernel selftests

Below are a set of example prompts / result commits of extending existing
kdevops selftests support to add new selftests. We bundle together "selftests"
with a few custom tests which don't fit into the "selftetsts" category but
due to efficiency we simply augment its support to cover them. The special
unicorn workloads are:

  - xarray - has kernel module and userspace tests
  - maple tree - has kernel module and userspace tests
  - vma - only has userspace tests

### Adding a new custom Linux kernel userspace test under kdevops selftests

**Prompt:**
We already support testing the Linux kernel maple tree and radix tree on the
selftests workflow. These are custom tests and each of these are tested on
kdevops in-kernel and then in userspace. The in-kernel testing done requires
using a loadable kernel module for each.

We have support for bundling these two tests under the
defconfigs/seltests-radix-tree defconfig and we use the
SELFTESTS_TEST_BUNDLE_RADIX_TREE to help us bundle all radix-tree related tests.
We want to extend this with a new userspace only test. Its the vma tests on the
Linux kernel. So it won't have a corresponding Linux kernel module load,
contrary to test_xarray and test_maple_tree. The only thing that needs to be
done to test it is to change directory on the linux kernel directory sources
into tools/testing/vma and as a user run make -j$(nproc) and then just run
sudo ./vma. So add support for this and augment SELFTESTS_TEST_BUNDLE_RADIX_TREE
to select this.

**AI:** Claude Code
**Commit:** [`191ae5678688`](https://github.com/linux-kdevops/kdevops/commit/191ae5678688)
**Result:** Almost perfect.
**Grading:** 95%

**Notes:**

The only issue caught was a complex bug which any human would have also run
into. It created a separate task for running the userspace tests and registered
the output to the same variable name as the task which runs the userspace
tests on the maple tree and xarray. This confuses ansible. And so the
selftests task "Run userspace selftests" needed to be manually fixed to
check if the test was either xarray or maple tree or vma, and use that same
task with variables for the directory where we change into and the command
we run.


## Adding completely new workflows to kdevops

Below are a list of successful prompts used with Claude Code to generate
commits for kdevops. They range from fixing bugs, to adding new workflows
to extending existing selftests support. These are intended to be useful
for humans and Claude Code. Please extend them with more examples. You
can add new types of fields. It just needs to make coherent sense.

### mmtests integration

**Prompt:**
mmtests by Mel Gorman is used to help force memory fragmentation. I had
extended mmtests so to ensure it works with debian-testing. And so given
kdevops default are to work with debian-testing adding support for mmtests to
kdevops should be straight forward, it should consist of just looking at its
README and for each distribution adding requirements on dependencies just as we
do for the sysbench workflow on kdevops. The kdevops sysbench workflow also
intelligently used intelligently the kconfig KDEVOPS_BASELINE_AND_DEV option so
to enable A/B testing.  So extend kdevops to add support for mmtests. Add
mirror support so that we have it as one of the mirrored git trees we take.
Then add a new mmtests workflow with support for it, and only initially focus
on thpchallenge-fio and thpcompact as possible mmtests workflow targets we can
work. Ensure to use the new output yaml feature so to enable ansible tasks for
mmtests to leverage the kconfig logic passed down automatically.

**AI:** Claude Code
**Commit:** [`0b829e6a1fb8`](https://github.com/linux-kdevops/kdevops/commit/0b829e6a1fb8)
**Result:** Comprehensive tests generated, with minor manual fixups.
**Grading:** 70%

**Notes:**
Most of the nuggets were properly implemented except it lacked insight to
review the build component and that:

a) Upon build the script called may expect user input. This required us to
   modify the call to use 'yes yes | ./run-mmtests.sh -b' and that meant
   also using and leveraging the ansible shell module. The ansible shell
   module is not ideal and not recommended due to the fact that pipes can
   easily lead to non deteriministic behaviour. We prefer long term to
   use the ansible command module and split task as needed. In this case
   in the future to enhance determinism we want to instead add an option
   upstream mmtest to the ./run-mmtests.sh command line options to let us
   not have to enter any input from users and let it just install depdenencies
   for us.

b) The script ./run-mmtests.sh asks us for user input to install dependencies.
   The lack of insight was to realize that other than the README it should have
   looked at the script ./run-mmtests.sh to help review if it did try to
   install dependencies on its own. What we can do later is instead as a
   secondary step use Caude Code to later ask it to analyze the latest
   upstream mmtests run-mmtests.sh script and ask it to install augment
   the dependency list we have on kdevops for each distribution.

c) The prompt the user gave lacked sufficient hints to help it understand
   where to get more sensible configurations from to be used as templates
   for ninja2 conversion. So for example ./bin/autogen-configs generates
   configurations for us and these should have been used for the base
   templates.

d) I manually had to enhance styling for variables for the different mmtests
   test types. This consisted of for example using variable names like
   MMTESTS_THPCOMPACT_THREADS_MIN for thpcompact related knobs. Likewise I
   preferred to split configurations for the different mmtests test types
   into their own kconfig file. So for example we ended up with:

source "workflows/mmtests/Kconfig.thpcompact"
source "workflows/mmtests/Kconfig.thpchallenge"
source "workflows/mmtests/Kconfig.fs"

   This separation is preferred as it helps us scale.

## Kernel development and A/B testing support

### Adding A/B kernel testing support for different kernel versions

**Prompt:**
We want to add support for when users enable KDEVOPS_BASELINE_AND_DEV we want
to extend workflows/linux/Kconfig with the a choise set of options to either a)
use the same kernel ref or b) allow the user to specify a different ref tag.
This will enable A/B testing with different kernel versions. When a different
kernel refs are desirable we will want to extend the compilation step and
installation of the Linux kernel in two steps. The first will be for the ref
and target of A (baseline tag) and the second will be for the target ref of B
(dev tag). However we want to fold these two steps in one for when
KDEVOPS_BASELINE_AND_DEV is used and make install is used, it would happen
transparently for us. The resulting linux kernel directory would end up with
the "dev" ref at the end. In case a user wants to re-compile a target ref for
baseline or dev we want to add (if we don't have already) a make linux-baseline
and make linux-dev so that we can build and install the target ref tag on the
baseline (A) or dev (B). The make linux target then would serially do make
linux-baseline and make linux-dev. Extend documentation for all this and also
add the respective prompt to PROMPTS.md once done. Avoid adding extra spaces to
code or documentation at the end of each line. These end up in red color on
diffs and hurt my eyes. Extend CLAUDE.md to understand styling for these rules
about not wanting lines ending in white space for styling.

**AI:** Claude Code
**Commit:** [To be determined]
**Result:** Complete A/B kernel testing implementation with comprehensive configuration options.
**Grading:** 70%

**Notes:**

The implementation successfully added:

1. **Makefile Implementation**: the AI failed to grasp the value of
   output yaml, and made ugly Makefile changes to extract variables.

2. **Ansible Integration**: The AI failed to write the required changes on
   the ansible playbook at first. A secondary prompt made it just move the
   definitions to the ansible playbook but failed to address serially compiling
   linux for the baseline group first followed by the dev group after.

3. **Documentation**: The AI is not grasping the preference to respect 80
   character lengths.

4. **Issues**: The AI failed to understand a really obscure lesson which even
   humans have issues in understanding in ansible, you can't override a fact
   and later use it specially if being used on multple hosts. The best thing
   to do is to use a separate fact if you want a true dynamic variable. This
   is why we switched to an active ref prefix for the baseline and dev group
   ref tags.
