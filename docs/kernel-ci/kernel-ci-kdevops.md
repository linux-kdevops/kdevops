# The kdevops github CI

We define two tests:

  * docker-tests.yml: uses containers
  * fstests.yml: uses self-hosted runners to ensure the fstests workflow
    always works

In short, self-hosted runners

## kdevops docker-tests.yml

This just use the typical container matrix to ensure basic commands work
with kdevops. Nothing quite really useful can be done with these tests most
important kdevops functionality requires some level of provisioning, either
on the cloud or with virtualization.

## kdevops fstests.yml

This workflow is intended to ensure we can always bring up a guest, build
fstest, and fun fstests against at least one filesystem profile and one
single fstests test.
