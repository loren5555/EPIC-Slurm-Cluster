# EPIC Cluster Operator Access Design

> 当前架构决策记录，不是部署操作手册。实际操作请阅读 `docs/admin/access.md`。

## Purpose

Define a practical, auditable administrator model for the EPIC cluster. The
cluster has one owner now and will add one superadministrator later. Seven
business administrators perform ordinary user, Slurm, monitoring, and OOD
operations without receiving unrestricted root access.

All persistent cluster configuration is changed through GitHub and Ansible.
Administrators do not edit the deployed controller checkout by hand.

## Roles

| Role | Linux group | Intended members | Authority |
| --- | --- | --- | --- |
| Superadministrator | `epic-superadmins` | Owner and one future deputy | Full system administration through the existing `sudo` group. |
| Cluster operator | `epic-operators` | Seven designated administrators | Fixed Git, Ansible, Slurm, monitoring, and OOD operations only. |
| Cluster user | none | All other users | Ordinary OOD, SSH, Slurm, and filesystem access. |

`epic-superadmins` is an Ansible-managed dedicated sudoers group. It grants
full sudo without changing the shared system `sudo` group, so membership can
be synchronized and revoked safely. `epic-operators` is not a member of
`sudo`, `adm`, `docker`, or any group granting broad system control.

## Configuration Workflow

The controller checkout is `/srv/epic/repos/EPIC-Slurm-Cluster`. It is owned by
the existing `administrator` deployment account and is not writable by cluster
operators.

1. An operator changes the repository through GitHub and merges the protected
   `main` branch.
2. The operator logs in to the controller with their own account.
3. The operator uses the exact permitted `sudo git pull --ff-only origin main`
   command to update the controller checkout.
4. The operator runs the relevant fixed Ansible playbook in check mode.
5. The operator runs the same fixed playbook for deployment.

GitHub commit history identifies the author and reviewer of every persistent
configuration change. The local deployment checkout must remain clean; a dirty
checkout is an operational failure requiring a superadministrator to inspect
and repair it.

The repository's platform code (`ansible/roles`, `ansible/playbooks`, and
templates) and its site configuration are deliberately both visible to
operators. This is a laboratory trust model, not a hostile multi-tenant model:
an operator able to merge arbitrary Ansible code and deploy it could obtain
root-equivalent control. GitHub branch protection, review, and accountability
are the safeguards for that authority.

## Sudo Policy

Operators receive only explicit commands from `/etc/sudoers.d/epic-operators`.
Every Ansible playbook has one exact check command and one exact deployment
command. The initial permitted playbooks are:

- `users.yml`
- `ssh_access.yml`
- `slurm.yml`
- `slurm_associations.yml`
- `disk_quotas.yml`
- `monitoring.yml`
- `grafana.yml`
- `ood.yml`

`site.yml` is intentionally excluded from operator sudoers permissions. It
changes multiple subsystems in one invocation and remains restricted to
superadministrators.

Sudo rules must not use broad patterns such as `ansible-playbook *`, accept
arbitrary inventory paths, arbitrary `--extra-vars`, arbitrary configuration
files, or arbitrary playbook arguments. These would defeat the command
boundary. Additional operational commands are added individually when a real
need exists.

Operators may inspect the deployment revision with a fixed Git status/log
command and update it only through a fixed fast-forward pull of `origin/main`.
They must not be able to run arbitrary Git subcommands as root.

## Slurm Administration

Every cluster operator receives SlurmDB `AdminLevel=Operator`; every other
managed `cluster_users` account is converged to `AdminLevel=None`. This grants
ordinary scheduling authority without exposing database credentials or
configuration files, and revokes it when an operator is removed from the
administrator manifest.

Operators use native Slurm commands to inspect jobs and nodes, cancel broken
jobs, requeue jobs, and drain or resume nodes. Changes to Accounts,
Associations, QoS, fair-share, partition access, or database configuration are
persistent policy changes and must be declared in the repository then applied
through `slurm_associations.yml` or `slurm.yml`.

`AdminLevel=Administrator`, MariaDB access, SlurmDBD secrets, and unrestricted
`sacctmgr` write access remain superadministrator-only.

## Monitoring and Grafana

Cluster operators receive Grafana `Editor`. They can create and edit dashboards
and investigate metrics. The owner and future superadministrator receive
Grafana `Admin`; this small group manages Grafana users, organizations, and
data sources.

Prometheus configuration, exporter configuration, retention, and service units
remain repository-managed. Operators can inspect the status and logs of the
declared monitoring services. Restart permissions, if required later, are
granted only for individually named service units; arbitrary `systemctl`
control is excluded.

## OOD and User Administration

OOD portal configuration, applications, announcements, and Remote Files are
repository-managed and deployed through `ood.yml`.

Linux identity fields (name, UID, GID, Home, shell, Unix group membership, SSH
access, Slurm account) are immutable at the command line for operators. They
are changed only through `ansible/vars/users.yml` and the relevant declared
policy files, then synchronized by Ansible.

Linux passwords remain locked. OOD passwords are independent credentials and
are not committed to Git. Operators reset them with the native interactive
command `sudo htpasswd /etc/ood/auth/htpasswd <username>`. Ansible renders a
sudoers regular expression from `cluster_users`, so the command accepts only
an existing declared cluster username and that one fixed password file.
Operators must not receive generic `passwd`, `usermod`, `useradd`, `userdel`,
`gpasswd`, or generic `htpasswd` sudo permissions.

## Audit and Boundaries

- GitHub is the record of persistent policy changes.
- Slurm accounting records job and scheduling actions.
- Grafana records dashboard changes in its own database.
- Sudo logs record controller-side deployments and privileged diagnostics.
- Administrators use personal Linux and GitHub identities; no shared operator
  account is used.

Operators do not receive root shells, unrestricted sudo, access to `/etc/shadow`,
TLS private keys, Ansible Vault secrets, MariaDB credentials, driver control,
network administration, or arbitrary service control. Emergency system repair
is escalated to a superadministrator.

## Initial Scope

The first implementation creates the two administrator groups, declares their
membership in the Ansible manifest, installs fixed sudoers rules, grants Slurm
Operator authority, enables restricted native OOD password resets, and
documents the Git-plus-Ansible workflow.
