# Terraform support

kdevops allows you to provide variability for Terraform using kconfig,
and uses Ansible to deploy the files needed to get you going with
a Terraform plan.

Terraform is used to deploy your development hosts on cloud virtual machines.
Below are the list of clouds providers currently supported:

**Traditional Cloud Providers:**
  * azure - Microsoft Azure
  * aws - Amazon Web Service
  * gce - Google Cloud Compute
  * oci - Oracle Cloud Infrastructure

**Neoclouds (GPU-optimized):**
  * datacrunch - DataCrunch GPU Cloud
  * lambdalabs - Lambda Labs GPU Cloud

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

## Neoclouds

A neocloud is a new type of specialized cloud provider that focuses on offering
high-performance computing, particularly GPU-as-a-Service, to handle demanding
AI and machine learning workloads. Unlike traditional, general-purpose cloud
providers like AWS or Azure, neoclouds are purpose-built for AI with
infrastructure optimized for raw speed, specialized hardware like dense GPU
clusters, and tailored services like fast deployment and simplified pricing.

kdevops supports the following neocloud providers:

### Custom AI Workflows on Neoclouds

Neoclouds are ideal for custom and proprietary AI workflows. kdevops makes it
easy to combine neocloud providers with user-private workflows, allowing you
to maintain custom AI/ML workflows outside the main kdevops repository.

**Quick Demo - Custom Workflow on GPU Cloud:**

```bash
# DataCrunch with custom knlp workflow on H100 or lower tier GPU
make defconfig-datacrunch-h100-pytorch-or-less+knlp KDEVOPS_HOSTS_PREFIX="1"
make bringup
# Creates host: 1-knlp with PyTorch environment and your custom workflow

# Lambda Labs with custom workflow on H100 or lower tier GPU
make defconfig-lambdalabs-h100-or-less+knlp KDEVOPS_HOSTS_PREFIX="ml"
make bringup
# Creates host: ml-knlp with your custom workflow
```

The `+<workflow>` suffix appends a defconfig fragment from your user-private
config directory (`~/.config/kdevops/defconfigs/configs/<workflow>.config`),
automatically enabling user-private workflows and your custom configuration.

For detailed instructions on creating your own custom AI workflows, see:
  * [User-Private Workflows Documentation](user-workflows/README.md)

### DataCrunch

kdevops supports DataCrunch, a cloud provider specialized in GPU computing
with competitive pricing for NVIDIA A100, H100, B200, and B300 instances.

#### Quick Start with DataCrunch

DataCrunch requires API key authentication. Create your credentials file:

```bash
mkdir -p ~/.datacrunch
cat > ~/.datacrunch/credentials << EOF
[default]
datacrunch_client_id=your-client-id-here
datacrunch_client_secret=your-client-secret-here
EOF
chmod 600 ~/.datacrunch/credentials
```

Get your API credentials from: https://cloud.datacrunch.io/

#### DataCrunch Defconfigs

kdevops provides several pre-configured defconfigs for DataCrunch:

**Single GPU Instances:**
```bash
make defconfig-datacrunch-a100        # Single A100 40GB SXM GPU
make defconfig-datacrunch-h100-pytorch # Single H100 80GB with PyTorch image
```

**Multi-GPU Instances:**
```bash
make defconfig-datacrunch-4x-h100-pytorch # 4x H100 80GB with PyTorch
make defconfig-datacrunch-4x-b200         # 4x B200 (Blackwell architecture)
make defconfig-datacrunch-4x-b300         # 4x B300 (Blackwell architecture)
```

#### Using Defconfigs with Workflows

DataCrunch defconfigs can be combined with user-private workflow fragments
using the `+<workflow>` syntax:

```bash
# Combine DataCrunch H100 with custom knlp workflow
make defconfig-datacrunch-h100-pytorch-or-less+knlp KDEVOPS_HOSTS_PREFIX="dev"
make bringup
```

This automatically configures a DataCrunch instance with your custom workflow
enabled, setting up the ML research environment. The tier-based selection
(`h100-pytorch-or-less`) automatically selects the best available GPU.

For creating your own custom AI workflows, see
[User-Private Workflows](user-workflows/README.md).

#### Instance Types

DataCrunch offers various GPU instance types:

**A100 Series (40GB SXM):**
- 1A100.40S.22V - Single GPU, 22 vCPUs, 80GB RAM (~$1.39/hr)
- 2A100.40S.44V - Dual GPU, 44 vCPUs, 160GB RAM (~$2.78/hr)
- 4A100.40S.88V - Quad GPU, 88 vCPUs, 320GB RAM (~$5.56/hr)
- 8A100.40S.176V - 8x GPU, 176 vCPUs, 640GB RAM (~$11.12/hr)

**H100 Series (80GB SXM):**
- 1H100.80S.30V - Single GPU, 30 vCPUs (~$1.99/hr)
- 1H100.80S.32V - Single GPU, 32 vCPUs (~$1.99/hr)
- 2H100.80S.80V - Dual GPU, 80 vCPUs (~$3.98/hr)
- 4H100.80S.176V - Quad GPU, 176 vCPUs (~$7.96/hr)
- 8H100.80S.176V - 8x GPU, 176 vCPUs (~$15.92/hr)

**Blackwell Series (Latest Architecture):**
- 4B200.120V - 4x B200 GPUs, 120 vCPUs
- 4B300.120V - 4x B300 GPUs, 120 vCPUs

#### Images

DataCrunch provides various OS images optimized for ML workloads:

- ubuntu-24.04-cuda-12.8-open-docker - Ubuntu 24.04 with CUDA 12.8 and Docker
- ubuntu-22.04-pytorch - Ubuntu 22.04 with PyTorch pre-installed
- ubuntu-22.04 - Ubuntu 22.04 base
- ubuntu-20.04 - Ubuntu 20.04 base
- debian-11 - Debian 11
- debian-12 - Debian 12

All images use `root` as the default SSH user.

#### Post-Provisioning Setup

kdevops automatically configures DataCrunch instances with:

1. System updates (apt-get dist-upgrade)
2. Development tools (git, make, flex, python3.12-venv, npm, etc.)
3. Python virtual environment at `~/.venv`
4. PyTorch installation
5. NVIDIA kernel module reload
6. Claude Code installation via npm

This happens automatically during `make bringup` via the datacrunch_ml_setup
Ansible role.

#### Capacity Checking

kdevops automatically checks instance availability before provisioning:

```bash
# Check capacity manually
./scripts/datacrunch_check_capacity.py

# Check specific instance type
./scripts/datacrunch_check_capacity.py --instance-type 1H100.80S.32V
```

The bringup process automatically selects an available location for your
chosen instance type.

#### SSH Configuration

DataCrunch instances are automatically added to your SSH config with
checksum-based filenames (e.g., `~/.ssh/config_kdevops_2df337e6`).
This allows multiple kdevops directories to coexist without conflicts.

The SSH config is automatically created during `make bringup` and removed
during `make destroy`.

#### Example: Complete Workflow

```bash
# Configure for DataCrunch with knlp workflow
make defconfig-datacrunch-a100 KNLP=1

# Review configuration (optional)
make menuconfig

# Provision instance and setup environment
make bringup

# The instance is now ready with:
# - Python venv with PyTorch and knlp dependencies
# - Claude Code installed
# - NVIDIA drivers loaded
# - SSH configured

# SSH into instance
ssh demo-knlp  # hostname from your configuration

# Destroy when done
make destroy
```

#### Troubleshooting

**API Authentication Issues:**
Check your credentials file exists and has correct permissions:
```bash
ls -l ~/.datacrunch/credentials
# Should show: -rw------- (600 permissions)
```

**Instance Type Not Available:**
If your desired instance type isn't available, kdevops will show
available alternatives. Use the capacity checker to see current
availability:
```bash
./scripts/datacrunch_check_capacity.py
```

**Provider Installation:**
If using a locally built DataCrunch provider (for development), ensure
you have the dev_overrides configured in `~/.terraformrc`:
```hcl
provider_installation {
  dev_overrides {
    "squat/datacrunch" = "/home/user/go/bin"
  }
  direct {}
}
```

For more information, visit: https://datacrunch.io/

### Lambda Labs

kdevops supports Lambda Labs, a cloud provider focused on GPU instances for
machine learning workloads with competitive pricing.

#### Using Lambda Labs with Custom Workflows

Lambda Labs defconfigs support user-private workflow fragments:

```bash
# Combine Lambda Labs H100 tier with custom knlp workflow
make defconfig-lambdalabs-h100-or-less+knlp KDEVOPS_HOSTS_PREFIX="ml"
make bringup
```

The tier-based selection (`h100-or-less`) automatically finds the cheapest
available GPU instance across all regions. For creating your own custom AI
workflows, see [User-Private Workflows](user-workflows/README.md).

#### Documentation

For detailed documentation on Lambda Labs integration, including tier-based
GPU selection, smart instance selection, and dynamic Kconfig generation, see:

  * [Lambda Labs Dynamic Cloud Kconfig](dynamic-cloud-kconfig.md) - Dynamic configuration generation
  * [Lambda Labs CLI Reference](lambda-cli.1) - Man page for the lambda-cli tool
  * [User-Private Workflows](user-workflows/README.md) - Creating custom AI workflows

Lambda Labs offers various GPU instance types including A10, A100, and H100
configurations. kdevops provides smart selection features that automatically
choose the cheapest available instance type and region.

For more information, visit: https://lambdalabs.com/
