# kdevops nfstest suite

kdevops can run Jorge Mora's nfstest suite against an NFS server.

Run `make menuconfig` and select:

  Target workflows -> Dedicated target Linux test workflow ->nfstest

Then configure the test parameters by going to:

  Target workflows -> Configure and run the nfstest suite

Choose the location of the repo that contains the version of nfstest
you want to use for the test.

Then, run:

  * `make`
  * `make bringup`
  * `make nfstest`
  * `make nfstest-baseline`
