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

## Port an external project into kdevops

The fio-tests was an older external project however its more suitably placed
into kdevops as jinja2 lets us easily scale this project. The projects also
were authored by the same person and the same license was used. The porting
took a few separate prompts as described below.

### Initial implementation of fio-tests workflow on kdevops

**Prompt:**
Now that we merged steady state to kdevops -- now let's add specific target
workflow support for different target different simple workflows. Learn from
how sysbench added two guests so we can do A/B testing in two separate guests.
The workflows you will focus on will be the workflows from
https://github.com/mcgrof/fio-tests. We already took steady state and
pre-conditioning from there so no need to do that. All we need to do is just
now target the different other workflows. Leverage the Kconfig documentation we
used on that project and adapt it to leverage output yaml on kdevops. Then also
to help test things we can simply add a basic test so that
.github/workflows/docker-tests.yml can run some tests using /dev/null as a
target block device for just one simple workflow.

**AI:** Claude Code
**Commit:** [`6d23d4bfbd2b`](https://github.com/linux-kdevops/kdevops/commit/6d23d4bfbd2b05e6ac122b059c9f6c9d9dac7161)
**Result:** Excellent implementation with comprehensive workflow structure.
**Grading:** 90%

**Notes:**

The implementation successfully:
- Added complete fio-tests workflow with A/B testing support following sysbench patterns
- Created comprehensive Kconfig structure with output yaml support for all options
- Implemented configurable test matrices (block sizes, IO depths, job counts, patterns)
- Added ansible role with template-based job generation
- Integrated with main kdevops workflow system and makefiles
- Created CI-optimized defconfig using /dev/null target device
- Updated GitHub Actions workflow for automated testing

Minor areas for improvement:
- Could have included more detailed help text in some Kconfig options
- Template generation could be more dynamic for complex configurations
- Didn't add documentation, which means we should extend CLAUDE.md to
  add documentation when adding a new workflow.
- Did not pick up on the trend to prefer to have 'make foo-results' to always
  copy results locally.

### Extend fio-tests with graphing support

**Prompt:**
The fio-tests project had support for graphing. Bring that over and add that to
kdevops. I am the author of fio-tests so I own all the code. Be sure to use
SPDX for my top header files with the copyleft-next license as is done with
tons of code on kdevops.

**AI:** Claude Code
**Commit:** [`6d23d4bfbd2b`](https://github.com/linux-kdevops/kdevops/commit/6d23d4bfbd2b05e6ac122b059c9f6c9d9dac7161)
**Result:** Comprehensive graphing implementation with proper licensing.
**Grading:** 95%

**Notes:**

Outstanding implementation that:
- Improved upon the graphs I had originally had on fio-tests and actually
  innovated on some! Also took the initiative to do A/B performance analysis!
- Created three comprehensive Python scripts with proper SPDX copyleft-next-0.3.1 headers
- Implemented advanced graphing: performance analysis, A/B comparison, trend analysis
- Added configurable graphing options through Kconfig (format, DPI, themes)
- Included conditional dependency installation across distributions
- Created ansible playbooks for automated graph generation
- Added make targets for different types of analysis
- Updated CI configuration with graphing support

The implementation perfectly followed kdevops patterns and demonstrated
excellent understanding of the codebase structure. The graphing capabilities
are comprehensive and production-ready.

### Add the fio-tests documentation

**Prompt:**
Now add documentation for fio-tests on kdevops. Extend README.md with a small
section and point to its own documentation file. You can use the upstream
fio-tests https://github.com/mcgrof/fio-tests page for inspiration, but
obviously we want to port this to how you've implemented support on kdevops.
You can point back to the old https://github.com/mcgrof/fio-tests page as an
origin story. Also extend PROMPTS.md with the few prompts I've given you to
help add support for fio-tests and graphing support.

**AI:** Claude Code
**Commit:** [`6d23d4bfbd2b`](https://github.com/linux-kdevops/kdevops/commit/6d23d4bfbd2b05e6ac122b059c9f6c9d9dac7161)
**Result:** Comprehensive documentation with examples and troubleshooting.
**Grading:** 90%

**Notes:**

The documentation implementation includes:
- Updated README.md with fio-tests section linking to detailed documentation
- Created comprehensive docs/fio-tests.md with full workflow coverage
- Included origin story referencing original fio-tests framework
- Added detailed configuration examples and troubleshooting guides
- Documented all graphing capabilities with usage examples
- Extended PROMPTS.md with the implementation prompts for future AI reference

This demonstrates the complete lifecycle of implementing a complex workflow in
kdevops from initial implementation through comprehensive documentation.

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
**Commit:** [`7f25db722a2b`](https://github.com/linux-kdevops/kdevops/commit/7f25db722a2ba80b052a463db7415fad6c0bf63f)
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

## Cloud provider integrations

### Adding Lambda Labs cloud provider support with dynamic Kconfig

**Prompt:**
The Lambda Labs company helps you use GPUs online, kind of like AWS, or OCI. Add
support for the terraform support for Lambda Labs. The best provider docs are at
https://registry.terraform.io/providers/elct9620/lambdalabs/latest/docs . Then
To create the kconfig values you will implement support to use the lambda cloud
API to let us query for what type of instances they have available and so forth.
Therefore the Kconfig stuff for Lambda labs will all be dynamic. So we'll want
to expand this as part of what make dynconfig does. However note that dynconfig
does *all* dynamically generated kconfig. We want to add support for make
cloud-config as a new target which is dynamic which is a subset of make
dynconfig ;  OK! good luck

**AI:** Claude Code (Opus 4.1)
**Commit:** [`3c4ba3293ba4`](https://github.com/linux-kdevops/kdevops/commit/3c4ba3293ba4316aaec7ad37f6fd7eda4b1d1720), [`535726de9d71`](https://github.com/linux-kdevops/kdevops/commit/535726de9d7114a4c3c348331dc638b91ff543a8)
**Result:** Complete Lambda Labs integration with dynamic Kconfig generation.
**Grading:** 75%

**Notes:**

The implementation successfully added:

1. **Terraform Provider Integration**: Created complete Terraform configuration
   for Lambda Labs including instance management, persistent storage, and SSH
   configuration management following existing cloud provider patterns.

2. **Dynamic Kconfig Generation**: Implemented Python script to query Lambda Labs
   API for available instance types, regions, and OS images. Generated dynamic
   Kconfig files with fallback defaults when API is unavailable.

3. **Build System Integration**: Added `make cloud-config` as a new target for
   cloud-specific dynamic configuration, properly integrated with `make dynconfig`.
   Created modular Makefile structure for cloud provider dynamic configuration.

4. **Kconfig Structure**: Properly integrated Lambda Labs into the provider
   selection system with modular Kconfig files for location, compute, storage,
   and identity management.

Biggest issues:

1. **SSH Management**: For this it failed to realize the provider
   didn't suport asking for a custom username, so we had to find out the
   hard way.

2. **Environment variables**: For some reason it wanted to define the
   credential API as an environment variable. This proved painful as some
   environment variables do not carry over for some ansible tasks. The
   best solution was to follow the strategy similar to what AWS supports
   with ~/.lambdalabs/credentials. This a more secure alternative.

Minor issues:
- Some whitespace formatting was automatically fixed by the linter
