# kdevops libvirt storage pool considerations

Only read this page if you are using libvirt for virtualization.

kdevops uses libguestfs utilities to build images and relies on libvirt to
run the guests. Understanding how libvirt storage pools work is important if
you want to customize storage locations or scale your environment.

By default libvirt may create a "default" storage pool in the same directory
where you run libguestfs. On distributions where libvirt runs as root this can
lead to confusion if you later start guests manually and expect a different
default pool.

If you're not sure if you are using libvirt storage pool or have one defined:

```bash
virsh pool-list
```

To figure out the path an existing pool:

```bash
virsh pool-dumpxml | grep path
```

If you don't like this arrangement by all means first destroy guests, and
then kill the pool with

```bash
virsh pool-destroy <pool-name>
virsh pool-undefine <pool-name>
```

To destroy guests, you can use something like:

```bash
virsh dumpxml <guest-name> | grep desc
cd path-to-test
make destroy # if using kdevops
```

If the above failed you will have undefine the guest yourself manually:

```bash
virsh destroy <guest-name>
virsh undefine <guest-name>
rm -f path-to-all-its-files
```

# Proper storage pool usage for kdevops

We highly recommend a libvirt storage pool set up with kdevops
that meets your storage needs. That means think about what drives
you want to place your guests on and share data with. This typically
just means picking a partition that is fast and has a lot of space.

Then properly name it, something like:

/data1-btrfs/

To help you reflect that that partition was created with BTRFS. Then
when configuring kdevops for this setup you are recommended to set
two variables with something like the following:

CONFIG_LIBVIRT_STORAGE_POOL_CREATE=y
CONFIG_LIBVIRT_STORAGE_POOL_NAME="data1-btrfs"
CONFIG_LIBVIRT_STORAGE_POOL_PATH_CUSTOM="/data1-btrfs/libvirt/images"

With this, libvirt will create the storage pool for you with the
given name. And the nice thing is that *after* your first guests comes
up, all other further guests which you try to bring up using kdevops
on that path /data1-btrfs/ with a new clone of kdevops will *lookup*
your current working directory, and look at all the known libvirt
storage pools and paths, and if *any* storage pool has your base
first directory on it, it will be used as the default for the
new configuration. So you can be *very* lazy on bringup on secondary
kdevops instances on /data1-btrfs/ after your first full guest is up.

If you are a power user this is very convenient, as it means you can
have other partitions, say:

/data2-xfs/

and then create a guest there, use other options like this for its
first guest:

CONFIG_LIBVIRT_STORAGE_POOL_CREATE=y
CONFIG_LIBVIRT_STORAGE_POOL_NAME="data2-xfs"
CONFIG_LIBVIRT_STORAGE_POOL_PATH_CUSTOM="/data2-xfs/libvirt/images"

And then a *second* configuration of kdevops on any path under /data2-xfs/
will automatically *pick up* the fact that you *very likely* want to use
the data2-xfs storage pool.
