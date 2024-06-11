# kdevops NFS support

kdevops has support for testing NFS. It can work with a kdevops-
provisioned NFS server or an NFS server that is remote to your
kdevops set up.

# kdevops NFSD setup
 
To enable the local NFS server, go to the "Bring up goals" menu, and
select "Set up the kernel nfs server" if it's not already enabled.
This will make the "Configure the kernel NFS server" menu visible.

In that menu, you can select the type of file system to be used
for NFS exports (such as "xfs" or "ext4"). By default, those
exported file systems reside on the NFS server itself.

You can also select the default export options and a few other
administrative options for the server.

The local NFS server is largely the same as the other target
nodes where the file system tests are run. For instance, the Linux
kernel options available under the "Target workflows" menu also
affect the kernel that is installed on the NFS server.

## NFS over RDMA

In the "Bring up goals" menu, you can enable the use of either
software-emulated iWARP or software-emulated RoCE on all of the
target nodes and the local NFS server (if it has been provisioned).
See the "Configure an RDMA device" submenu.

# kdevops NFS testing with pynfs

First, provision your NFS server (either the local NFS server, as
above; or a remote NFS server accessible from the kdevops test
network).

To test the kernel's NFS server with the pynfs testsuite, enable the
pynfs workflow under the "Target workflows" menu as you configure
kdevops.

Once you have made all your selections, use the usual make targets
to start your kdevops environment. For instance:

  * `make`
  * `make bringup`
  * `make linux`
  * `make pynfs`
  * `make pynfs-baseline`

# kdevops NFS testing with the fstests suite

First, provision your NFS server (either the local NFS server, as
above; or a remote NFS server accessible from the kdevops test
network).

To run the fstests suite using NFS, enable the fstests workflow
under the "Target workflows" menu. A "Configure and run fstests"
menu will appear.

Under this menu, select "nfs" as the "The target file system type to
be tested". The "Configure how to test nfs" submenu enables you to
select the NFS versions to be tested. Each NFS version is tested in
its own target node so that the tests can run in parallel. Then use:

  * `make`
  * `make bringup`
  * `make linux`
  * `make fstests`
  * `make fstests-baseline`

# kdevops NFS testing with the git regression suite

First, provision your NFS server (either the local NFS server, as
above; or a remote NFS server accessible from the kdevops test
network).

To run the git regression suite using NFS, enable the gitr workflow
under the "Target workflows" menu. A "Configure and run the git
regression suite" menu will appear.

Under this menu, select "nfs" as the "The target file system type to
be tested". The "Configure how to test nfs" submenu enables you to
select the NFS versions to be tested. Each NFS version is tested in
its own target node so that the tests can run in parallel. Then use:

  * `make`
  * `make bringup`
  * `make linux`
  * `make gitr`
  * `make gitr-baseline`

# kdevops NFS testing with the nfstest suite

The nfstest suite works only with the NFS file system.

You must first provision an NFS server, as explained above.

To run the nfstest suite, enable the nfstest workflow under the
"Target workflows" menu. A "Configure and run the nfstest suite"
menu will appear.

Under this menu, you can choose which test groups are to be run.
Each test group is run in its own target node so that the tests
can run in parallel. Then use:

  * `make`
  * `make bringup`
  * `make linux`
  * `make nfstest`
  * `make nfstest-baseline`

# kdevops NFS testing with the ltp suite

When running the NFS test group, the ltp suite uses loopback NFS.
Thus it does not need a separate NFS server.

To run the ltp suite, enable the ltp workflow under the "Target
workflows" menu. A "Configure and run the ltp suite" menu will
appear.

Under this menu, you can choose which test groups are to be run.
Each test group is run in its own target node so that the tests
can run in parallel. Then use:

  * `make`
  * `make bringup`
  * `make linux`
  * `make ltp`
  * `make ltp-baseline`

# Special testing modes for NFS

## NFS with TLS

When configuring kdevops, you can choose to provision a certificate
authority (CA) that can create x.509 certificates for the target
nodes and NFS server. The CA runs on the control node and the
certificates are distributed to each target node as it is
provisioned by libvirt.

To enable TLS, select the "Configure ktls on the hosts with self-
signed CA" option in the "Bring up goals" menu.

Some workflows enable you to adjust the mount options so that TLS
sessions are created between the NFS clients and server. Inspect the
workflow menus to see how those options are set.

## NFS with Kerberos

When configuring kdevops, you can choose to provision a Kerberos
Data Center (KDC). A keytab for each target node is then created
automatically and distributed to each target node as it is
provisioned by libvirt.

To enable NFS with Kerberos, select the "Set up KRB5" option in the
"Bring up goals" menu.

Some workflows enable you to adjust the mount options so that the
use of Kerberos is enabled between the NFS clients and server.
Inspect the workflow menus to see how those options are set.

## pNFS with block layouts

pNFS with block layouts requires special set up of the local NFS
server, as well as the installation of an iSCSI initiator on each
NFS client.

First, the local NFS server supports pNFS with block layouts only
with the XFS file system. Select xfs via the "Type of filesystem to
export" setting under the "Configure the kernel NFS server" menu.

Next, exported XFS file systems must reside on iSCSI LUNs so that
these devices can be visible to NFS clients as well. Select the
"Set up an iSCSI target host" in the "Bring up goals" menu, and
then go back to the "Configure the kernel NFS server" menu and
choose iSCSI for "Local or external physical storage".

The fstests, gitr, and pynfs workflows support pNFS with block
layouts, but the others do not. In the menu that controls the
workflow you wish to run, find the option that enables pNFS
with block". This provisions an iSCSI intiator on the NFS
client nodes.

Finally, for the fstests and gitr workflows, select the NFS version
4.1 or NFS version 4.2 options. Earlier NFS versions do not support
pNFS.
