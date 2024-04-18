# Running kdevops for the first time

See [kdevops requirements](docs/requirements.md) first and install that.

If you're using virtualization with guestfs we just need to verify your user can
run guests, and setting this up varies distro-by-distro.

# Manual check

If you know what you are are doing you can do the setup yourself. Here is a
checklist of things you need to do:

  * your user is part of groups libvirt-qemu (if it exists), libvirt, kvm
  * disable selinux or apparmor
  * reboot

## Dedicated storage pool

You can use an existing storage pool, create one, or let kdevops create it
for you. Let's say you want to be lazy and let kdevops create it for you,
just empty out enough disk space on and let kdevops know you want it to create
your storage pool for with by setting CONFIG_LIBVIRT_STORAGE_POOL_PATH_CUSTOM_MANUAL
to a new directory under it. For example say /xfs1/ is a new partition create
/xfs1/libvirt and ensure the appropriate libvirt group owns it and use that for
this custom path. The benefit of this setup is that you can use the same
dedicated partition for work with kdevops. After you do a first bringup with
this storage pool, if you run 'make menuconfig' under any directory under
/xfs1/ then kdevops will detect your existing storage pool and use that, so
sensible defaults are used.

### Mirror setup

Consider enabling the local [kdevops mirror](docs/kdevops-mirror.md) if you
think you're going to be using kdevops a bit.

### First manual check

To be sure things will work right, use the default after 'make menuconfig'
and run 'make; make bringup'; if that fails consider reading below as you may
have missed something.

## Getting help with kdevops

kdevops can help you verify your user can use virtualization correctly.

# Enabling CONFIG_KDEVOPS_FIRST_RUN

kdevops can help you verify virtualization will work correctly for your user. To
help with this we have an option on Kconfig which you should enable if it is
your first time running kdevops, the prompt is for CONFIG_KDEVOPS_FIRST_RUN:

```
"Is this your first time running kdevops on this system?"
```

This will enable a set of sensible defaults to help with your first run. The
requirements will be installed for you when you call 'make', after
'make menuconfig'.

The way to use this 'first run' feature is to just enable the option, and
keep running `make` until it stops telling you to fix things. The first run
stuff verifies and ensures your user can bring up a virtualization guest as a
regular user without needing root. This is typically done by having your
username be part of a few special groups, depending on your Linux distribution.
Other than that, the other amount of work the `first run` stuff does is nags /
complains are about disabling AppArmor / SELinux, and maybe needing to reboot.

You should just disable the `CONFIG_KDEVOPS_FIRST_RUN` once kdevops stops
complaining about things, and then just run `make mrproper` and never, *ever*
enable it again. The reason you want to get to disable `CONFIG_KDEVOPS_FIRST_RUN`
is that leaving the enabled does a bit of sanity checks which are not needed
after your first run, and simply slow down your user experience.

If you want to set up a git mirror for Linux for personal use read
[kdevops mirror support](docs/kdevops-mirror.md). You may want to set up this
mirror if you are going to deploy multiple instances of kdevops on a same
system or network. If you are using a cloud environment you could still use
kdevops to set up a mirror but you'd run kdevops on an already instantiated
node on the cloud. kdevops could even bring those nodes up for you, but
setting this up for the cloud is a bit beyond the scope of this guide.

So let's re-iterate a few goals of the first run stuff:

  * Ensuring your user can run libvirt commands as a regular user without
    a password
  * Disabling SELinux / AppArmor
  * Optionally install a git mirror for a few git trees you may use often

Disable `CONFIG_KDEVOPS_FIRST_RUN` after you have verified you can kdevops
works to bring up systems for you.
