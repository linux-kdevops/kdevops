# kdevops Git references generation TLDR

[Git References](https://git-scm.com/book/en/v2/Git-Internals-Git-References)
are names to commit IDs. To build and boot Linux on kdevops we need references
defined for target commits. Most users and developers care about three major
Linux trees: Linus' tree, linux-next and stable trees. We refer to these as
the Linux canon trees.

When you run `make menuconfig` the latest Linux releases from the Linux canon
trees are updated updated automatically to ensure you can always build and boot
the latest major Linux kernels. If [kernel.org](kernel.org) is unreachable
the existing static Kconfig files are used. By default, the files which define
the refs for the canon trees are not updated if they are they are less than
24 hours old.

To support more development trees kdevops supports static references defined in
yaml files, used to dynamically generate Kconfig files to support trees other
than the main cannon Linux trees and the main supported release listed on
kernel.org. These yaml file are static. The kdevops developers update these
inside the tree for you after we edit static yaml files under the directory
`workflows/linux/refs/static/`. The generated Kconfig file are under
`workflows/linux/refs/default/Kconfig*`. Developers should often run
the following command to ensure we have the latest default Kconfig files
from the static yaml reference files.

```bash
make refs-default
```

The above command can also be used to update the latest Linux canon tree refs.

Development however is not static, and so to provide even more flexibility
dynamically scraping git trees for refs is also supported using the target:

```bash
make refs-user
```

Don't use this unless you are a developer working on a supported user ref
and know that you always want to scrape for your custom latest tree refs
dynamically.

## How all this works

Most users should just use:

```bash
make menuconfig
```

If you have a tree you want to add options for outside of the canon Linux
trees you want to add a static yaml file and then run the following command
so that the Kconfig files are generated for your custom tree, you'd commit
these newly generated Kconfig files:

```bash
make refs-default
```

The Kconfig files under `workflows/linux/refs/default/Kconfig` are automatically
generated for you by kdevops developers using the command above. It is our
job to update these for you whenever we update the static refs defined in yaml
files under the directory `workflows/linux/refs/static/`.


Users of kdevops need to decide if the static refs suffice for their
needs and if not use user refs. Users of user refs are likely kernel
developers which want to use kdevops against bleeding edge refs they
may have just pushed onto their development trees and which there is
at least a respective user yaml defined for them in kdevops.

To use user refs you'd use:

```bash
make refs-user
```

This generates and switches to user references files (`refs/user/Kconfig.*`).
Using user refs are mutually exclusive with the default refs. You can switch
back to the default refs with:


```bash
make refs-user-clean` or
```

or

```bash
make refs-default
```

### Default References Mode

By default, references in `workflows/linux/refs/default/Kconfig.*` are used.


### User References Mode

References in `workflows/linux/refs/user/Kconfig.*` are only used when `make
refs-user` is run. Then, `workflows/linux/refs/default/Kconfig.*` are ignored.


### Switching back to Default References Mode (from User References Mode)

This can be accomplished by clearing the user generated references with `make
refs-user-clean` (target hidden from help) or by forcing the generation of
default references with `make refs-user`.


### Default References for Linus, Next and Stable trees: Updating Kconfig with Latest References

`make menuconfig` automatically creates
`workflows/linux/refs/default/Kconfig.{linus, stable, next}` files using
the latest releases from [kernel.org](kernel.org) and static references from
`workflows/linux/refs/default/{linux, next, stable}.yaml`. Subsequent `make
menuconfig` runs will not regenerate these files for 24 hours after the last
update.


### Default References for Linus, Next and Stable trees: Forced Update

Running `make refs-default` forces the update of `workflows/linux/refs/default/Kconfig.*`
files using their corresponding YAML files and [kernel.org](kernel.org) release
information.

### Default References for Development trees: Static References

Files like
`workflows/linux/refs/default/Kconfig.{btrfs-devel, cel-linux, jlayton-linux, kdevops-linux, mcgrof-linus, mcgrof-next}`
are auto-generated and maintained in kdevops tree. When adding new references,
update
`workflow/linux/refs/static/{btrfs-devel, cel-linux, jlayton-linux, kdevops-linus, mcgrof-linus, mcgrof-next}.yaml`
manually before running `make refs-default`. Send a patch with the changes
upstream.


### User References: Generating User Git References

Running `make refs-user` generates `workflows/linux/refs/user/Kconfig.*`
files including statically defined references and the last 15 references found
upstream. The Kconfig menu uses these new files until switching back to Default
References Mode.


## More elaborate details

kdevops facilitates the automatic generation of
[Git References](https://git-scm.com/book/en/v2/Git-Internals-Git-References)
(or refs), ensuring that repositories used for
[bootlinux](../playbooks/roles/bootlinux/README.md) are always up to date with the
latest refs available in Kconfig.

The automation of this process is integrated into Make through `menuconfig`, and
the following targets: `refs-default` and `refs-user`.

These targets ensure that the files `refs/default/Kconfig.*` and `refs/user/Kconfig.*`
are automatically generated using the
[`scripts/generate_refs.py`](../scripts/generate_refs.py) script file.

The `refs/default/Kconfig.*` files contain both statically defined references and
the latest release version references for the Linus, Next, and Stable trees.
Since these three trees are subject to change, their `refs/default/Kconfig.*`
files are not included in the repository and are generated every time `make
menuconfig` or `make refs-default` is run. Note that with `menuconfig`, files
are only generated if 24 hours have passed since last update.

Files that usually remain unchanged, such as the one for the Mcgrof Next tree
([`workflows/linux/Kconfig.kreleases-mcgrof-next`](../workflows/linux/Kconfig.kreleases-mcgrof-next)),
(or any other Development tree) are included in the kdevops tree as they only
contain statically defined references. To update these, the accompanying
YAML file is used as input. These files are generated automatically, enabling
kdevops to augment them when `make refs-user` is run (see more below in the
user paragraph).

For example, the
[`workflows/linux/Kconfig.kreleases-mcgrof-next`](../workflows/linux/Kconfig.kreleases-mcgrof-next)
autogenerated file uses
[`workflows/linux/mcgrof-next-refs.yaml`](../workflows/linux/mcgrof-next-refs.yaml)
as an input. Extending that file is encourage when including new static references
that kdevops needs to keep track, followed by running `make refs-default` for
the `refs/default/Kconfig.mcgrof-next` to be generated.

The `refs/user/Kconfig.*` files are user-generated files containing both
statically defined references and the last 15 references found upstream for
Linus, Stable, Next and Development trees. These files will be created empty
when `make` is invoked, as they are required for Kconfig to function. However,
when `make refs-user` is run, the Kconfig menu would use these instead of
the default ones until they are manually cleared with `make refs-user-clean`.
or `make refs-default` is run.

Finally, if [kernel.org](kernel.org) is unreachable, `make refs-default` will
use only static references and `make refs-user` will produce no output.
