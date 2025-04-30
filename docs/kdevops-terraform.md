# Terraform support

kdevops allows you to provide variability for Terraform using kconfig,
and uses Ansible to deploy the files needed to get you going with
a Terraform plan.

Terraform is used to deploy your development hosts on cloud virtual machines.
Below are the list of clouds providers currently supported:

  * azure - Microsoft Azure
  * aws - Amazon Web Service
  * gce - Google Cloud Compute
  * oci - Oracle Cloud Infrastructure
  * openstack (special minicloud support added)

You configure which cloud provider you want to use, what feature from that
cloud provider you want to use, and then you can use kdevops to select which
workflows you want to enable on that configuration.

## Configuring your cloud options

To configure which cloud provider you will use you will use the same
mechanism to configure anything in kdevops:

```bash
make menuconfig
```

Under "Bring up methods" you will see the option for
"Node bring up method (Vagrant for local virtualization (KVM / VirtualBox))".
Click on that and then change the option to "Terraform for cloud environments".
That should let you start configuring your cloud provider options. You can
use the same main menu to configure specific workflows supported by kdevops,
by defaults no workflows are enabled, and so all you get is the bringup.

## Installing dependencies

To install the dependencies of everything which you just enabled just run:

```bash
make
```

## Provisioning (bringup) with Terraform

You can just use:

```bash
make bringup
```

Or if you want to do this manually:

```bash
make deps
cd terraform/you_provider
make deps
# Make sure you then add the variables to let you log in to your cloud provider
terraform init
terraform plan
terraform apply
```
### Terraform SSH config update - The add-host-ssh-config Terraform module

We provide support for updating your configured SSH configuration file
(typically `~/.ssh/config`) automatically for you, however each cloud provider
requires support to be added in order for this to work. At the time of this
writing we support this for all cloud providers we support.

After `make bringup` you should have had your SSH configuration file updated
automatically with the provisioned hosts. The Terraform module
`add-host-ssh-config` is used to do the work of updating your SSH configuration,
a module is used to share the code with provisioning with vagrant.

The Terraform module on the registry:

  * https://registry.terraform.io/modules/mcgrof/add-host-ssh-config/kdevops/latest

The Terraform source code:

  * https://github.com/mcgrof/terraform-kdevops-add-host-ssh-config

Because the same code is shared between the vagrant Ansible role and the
Terraform module, a git subtree is used to maintain the shared code. The
Terraform code downloads the module on its own, while the code for
the Vagrant Ansible role has the code present on the kdevops tree as
part of its local directories in under:

  * `playbooks/roles/update_ssh_config_vagrant/update_ssh_config/`

Patches for code for in `update_ssh_config` can go against
the `playbooks/roles/update_ssh_config_vagrant/update_ssh_config/`
directory, but should be made atomic so that these changes can
be pushed onto the standalone git tree for update_ssh_config on
a regular basis. For details on the development workflow for it,
read the documentation on:

 * [update_ssh_config documentation](playbooks/roles/update_ssh_config_vagrant/update_ssh_config/README.md)

## Destroying nodes with Terraform

Just run:

```bash
make destroy
```

Or if you are doing things manually:

```bash
cd terraform/you_provider
terraform destroy
```

# If provisioning failed

We run the devconfig Ansible role after we update your SSH configuration,
as part of the bring up process. If can happen that this can fail due to
connectivity issues. In such cases, you can run the Ansible role yourself
manually:

```bash
ansible-playbook -l kdevops playbooks/devconfig.yml
```

Note that there a few configuration items you may have enabled, for things
which we are aware of that we need to pass in as extra arguments to
the roles we support we automatically build an `extra_vars.yaml` with all
known extra arguments. We do use this for one argument for the devconfig
role, and a series of these for the bootlinux role. The `extra_args.yaml`
file is read by all kdevops Ansible roles, it does this on each role with
a task, so that users do not have to specify the
`--extra-args=@extra_args.yaml` argument themselves. We however strive to
make inferences for sensible defaults for most things.

## Running Ansible for workflows

Before running Ansible make sure you can SSH into the hosts listed on
ansible/hosts.

```bash
make uname
```

There is documentation about different workflows supported on the top level
documentation.

## Getting set up with cloud providers

To get set up with cloud providers with Terraform we provide some more
references below which are specific to each cloud provider.


### Azure

Read these pages:

https://www.terraform.io/docs/providers/azurerm/auth/service_principal_client_certificate.html
https://github.com/terraform-providers/terraform-provider-azurerm.git
https://docs.microsoft.com/en-us/azure/virtual-machines/linux/terraform-create-complete-vm
https://wiki.debian.org/Cloud/MicrosoftAzure

But the skinny of it:

```
$ openssl req -newkey rsa:4096 -nodes -keyout "service-principal.key" -out "service-principal.csr"
$ openssl x509 -signkey "service-principal.key" -in "service-principal.csr" -req -days 365 -out "service-principal.crt"
$ openssl pkcs12 -export -out "service-principal.pfx" -inkey "service-principal.key" -in "service-principal.crt"
```

Use the documentation to get your subscription ID, tenant ID, and
application id. Set these values via "make menuconfig" in the
Terraform Providers submenu.


### Openstack

Openstack is supported. This solution relies on the clouds.yaml file for
openstack configuration. This simplifies setting up authentication
considerably.

#### Minicloud Openstack support

minicloud has a custom setup where the you have to SSH with a special port
depending on the IP address you get, if you enable minicloud we do this
computation for you and tell you where to SSH to, but we also have support
to update your ~/ssh/config for you.

Please note that minicloud takes a while to update its ports / mac address
tables, and so you may not be able to log in until after about 5 minutes after
you are able to create the nodes. Have patience.

Your terraform.tfvars may look something like:

```
instance_prefix = "my-random-project"

image_name = "Debian 10 ppc64le"
flavor_name = "minicloud.tiny"

ssh_config_pubkey_file = "~/.ssh/minicloud.pub"
ssh_config = "~/.ssh/config"
ssh_config_user = "debian"
ssh_config_update = "true"
ssh_config_use_strict_settings = "true"
ssh_config_backup = "true"

```

### AWS - Amazon Web Services

AWS is supported. For authentication, kdevops relies on a shared
credentials file, separate from kdevops' .config:

```
~/.aws/credentials
```

This file is rather simple with a structure as follows:

```
[default]
aws_access_key_id = SOME_ACCESS_KEY
aws_secret_access_key = SECRET_KEY
```

This file may contain authentication secrets for more than one
user. The TERRAFORM_AWS_PROFILE setting enables you to select which
entry in this file kdevops will use to authenticate.

To read more about shared credentials refer to:

  * https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html
  * https://docs.aws.amazon.com/powershell/latest/userguide/shared-credentials-in-aws-powershell.html

If you run kdevops on CodeBuild (or ECS), configure an IAM Task Role
for the build container so that kdevops can create AWS resources.
For more information, see:

https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html
https://docs.aws.amazon.com/prescriptive-guidance/latest/terraform-aws-provider-best-practices/security.html

### GCE - Google Compute Engine

kdevops can provision Google Compute Engine resources. If you are
new to GCE, review this article:

https://cloud.google.com/docs/overview

to understand the concepts and requirements for setting up and
using GCE resources.

Once your project is created, the administrator must create a
service account key and provide it to you in a file. The
pathname to that file is specified in the "Identity & Access"
submenu. See:

https://cloud.google.com/iam/docs/creating-managing-service-account-keys

Further, the service account must be granted access to allow
it to create instances and other resources. See:

https://cloud.google.com/iam/docs/granting-roles-to-service-accounts#granting_access_to_a_service_account_for_a_resource

### OCI - Oracle Cloud Infrastructure

kdevops supports using the OCI Public Cloud (OCI).

#### New To OCI?

You can find a generic tutorial guide at the following link. You'll
need many (but not all) of these steps to bring up kdevops with OCI.

https://docs.oracle.com/en-us/iaas/Content/dev/terraform/tutorials/tf-provider.htm

This explains what an "OCID" is:

https://docs.oracle.com/en-us/iaas/Content/General/Concepts/identifiers.htm

#### Quick Start

To authenticate to the Oracle cloud, kdevops uses the API Key
authentication method, described here:

 https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm

To generate a signing key, follow these instructions:

https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm#apisigningkey_topic_How_to_Generate_an_API_Signing_Key_Console

By default, kdevops picks up the "DEFAULT" entry in the config file.
You can add more entries and use Kconfig to have kdevops use one
of the non-default entries in that file.

OCI pre-configures an admin ssh user on each instance. Under the
CONFIG_TERRAFORM_SSH_CONFIG_USER option, you need to explicitly set
kconfig's ssh login name depending on which OS image you have
selected:

   - `opc` for Oracle Linux.
   - `ubuntu` for Ubuntu Linux

If your Ansible controller (where you run "make bringup") and your
test instances operate inside the same subnet, you can disable the
TERRAFORM_OCI_ASSIGN_PUBLIC_IP option for better network security.
