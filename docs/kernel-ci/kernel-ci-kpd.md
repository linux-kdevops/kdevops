# kdevops kernel-patches-daemon integration

In order to leverage
[kernel-patches-daemon](https://github.com/facebookincubator/kernel-patches-daemon)
you will need an app on github which has permissions to push pull requests
onto a tree which will in turn leverage a self-hosted runner.

# Locking down your github organization

You should lock down your repo / organization so to ensure only privileged
developers can issue pull requests. In the future perhaps kpd can instead be
modified to only work with git pushes, as by default the security for pushes on
repos are locked down, whereas anyone can typically issue pull requests on most
open source projects.

## Modify organization base permissions

![0000a-org-security-member-privileges-base-permission-no-permission.png](/docs/kernel-ci/kpd-app/0000a-org-security-member-privileges-base-permission-no-permission.png)

## Make default no access

![0000b-no-access.png](/docs/kernel-ci/kpd-app/0000b-no-access.png)

# Prepare a base tree for Linux kernel development base for your organization

Uploading a full tree to github takes a long time. To reduce the amount of
time it makes sense to just fork Linus own github tree and use that as a base
for your organization to then use *this* tree to fork from. The reason we do
this is that kpd issues pull requests onto the original tree. This can also
be avoided perhaps in the future if kpd did not issue pull requests and instead
used only git pushes.

![0001-fork-linux-fork-for-kpd.png](/docs/kernel-ci/kpd-app/0001-fork-linux-fork-for-kpd.png)

# Create your custom subsystem topic kpd tree

Create a tree for your subsystem hacking.

![0002-create-custom-linux-kpd-tree.png](/docs/kernel-ci/kpd-app/0002-create-custom-linux-kpd-tree.png)

# Create an organization team

![0003-create-kpd-team-a.png](/docs/kernel-ci/kpd-app/0003-create-kpd-team-a.png)
![0003-create-kpd-team-b.png](/docs/kernel-ci/kpd-app/0003-create-kpd-team-b.png)

# Hunt for the new github app menu

![0004a-Developer-settings-GithubApps.png](/docs/kernel-ci/kpd-app/0004a-Developer-settings-GithubApps.png)

# Create a new github app

![0004b-github-create-kpd-app.png](/docs/kernel-ci/kpd-app/0004b-github-create-kpd-app.png)

# Give the app a name

![0005-github-app-name.png](/docs/kernel-ci/kpd-app/0005-github-app-name.png)

# Use sensible default permissions

![0006-app-repository-permissions.png](/docs/kernel-ci/kpd-app/0006-app-repository-permissions.png)

# Disable the webhook

![0007a-disable-web-hook.png](/docs/kernel-ci/kpd-app/0007a-disable-web-hook.png)

# Enable permissions for content, pull requests and workflow:

![0007b-content.png](/docs/kernel-ci/kpd-app/0007b-content.png)
![0007c-pull-request.png](/docs/kernel-ci/kpd-app/0007c-pull-request.png)
![0007d-workflow.png](/docs/kernel-ci/kpd-app/0007d-workflow.png)


# Create the app

![0008-create-Github-App.png](/docs/kernel-ci/kpd-app/0008-create-Github-App.png)

# How to get the app ID

![0009-app-id.png](/docs/kernel-ci/kpd-app/0009-app-id.png)

# Generate the app private key

This is the key which you will need for kpd to use.

![0010-generate-app-private-key.png](/docs/kernel-ci/kpd-app/0010-generate-app-private-key.png)

This will trigger a download of the key using your web browser.

![0011-downloads-generate-private-key.png](/docs/kernel-ci/kpd-app/0011-downloads-generate-private-key.png)

# Install the subsystem kpd app

![0012-install-app.png](/docs/kernel-ci/kpd-app/0012-install-app.png)

# Give subsystem kpd app permissions to your subsystem repo

![0013-only-select-repositories.png](/docs/kernel-ci/kpd-app/0013-only-select-repositories.png)

Be mindful and only select the specific repos you want the app to have
privileges to.

![0014-only-select-repos.png](/docs/kernel-ci/kpd-app/0014-only-select-repos.png)


# Install the kpd subsystem app

![0015-app-installation-id.png](/docs/kernel-ci/kpd-app/0015-app-installation-id.png)

# Edit subsystem repo secrets and variables

![0016-repo-kpd-settings-secrets-and-variables-click-actions.png](/docs/kernel-ci/kpd-app/0016-repo-kpd-settings-secrets-and-variables-click-actions.png)

You will want to add a secret, the private key which you will use to allow the
github actions from kdevops to upload to the kdevops-results-archive.

![0017-repository-secrets.png](/docs/kernel-ci/kpd-app/0017-repository-secrets.png)

You will want the key to be created with a command like this to be enable
the github webfactory ssh agent to know its associated to a specific repo.

![0018-ssh-genkey-kdevops-results-archive.png](/docs/kernel-ci/kpd-app/0018-ssh-genkey-kdevops-results-archive.png)

You will cat the private key.

![0019-cat-private-key.png](/docs/kernel-ci/kpd-app/0019-cat-private-key.png)

And add it to a secrete key.

![0019-private-key-listed-as-available-to-repo.png](/docs/kernel-ci/kpd-app/0019-private-key-listed-as-available-to-repo.png)

# Add a team for your subsystem

![0020-add-team.png](/docs/kernel-ci/kpd-app/0020-add-team.png)

# Grant team access

![0021-add-specific-team-admin-access.png](/docs/kernel-ci/kpd-app/0021-add-specific-team-admin-access.png)

# Add collaborators

![0022-collaborator-results-should-look-like.png](/docs/kernel-ci/kpd-app/0022-collaborator-results-should-look-like.png)

# Get kernel-patches-daemon

Now clone kpd on a system you have access to and which is private,
this is where kpd will run.

![0023-git-clone-kpd.png](/docs/kernel-ci/kpd-app/0023-git-clone-kpd.png)

# Create a private directory for your subsystem

![0024-create-private-dir-with-priv-key-and-new-kpd-json.png](/docs/kernel-ci/kpd-app/0024-create-private-dir-with-priv-key-and-new-kpd-json.png)

# How to get your API token number.

![0025-patchwork-user-api-token-number.png](/docs/kernel-ci/kpd-app/0025-patchwork-user-api-token-number.png)

# Get your patchwork project ID number

To find your project ID number use 
[the patchwork API page](https://patchwork.kernel.org/api/1.2/projects/) to look
for your respective project ID number. So for instance the linux-acpi patchwork
project has  project ID 2 while the inux-media patchwork project has project
ID 4.
