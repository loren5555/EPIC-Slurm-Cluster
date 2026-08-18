# EPIC Open OnDemand Deployment Design

## Purpose

Open OnDemand (OOD) is the browser entry point for convenient Slurm use. It
runs only on `epic-cluster-controller-01`; compute workloads always run as
Slurm jobs. OOD improves usability but does not replace Slurm Associations,
QoS, cgroups, SSH access policy, or command-line administration.

The previous deployment records are historical references. This design follows
the current one-partition-per-host Slurm model, independent host storage, and
Ansible-managed configuration.

## Deployment boundary

Software installation remains manual:

- the controller receives OOD 4.2, Apache, rclone, the NFS server, and
  `ondemand_exporter`;
- compute nodes receive the NFS client and the runtime programs used by the
  published interactive applications;
- Ansible configures installed software, publishes applications, and manages
  services, but does not install or upgrade the packages.

The OOD playbook has three roles:

- `ood_controller` owns the portal, HTTPS, authentication path, cluster
  adapter, shared context export, dashboard settings, Remote Files settings,
  and exporter service;
- `ood_compute` mounts the shared context without making boot, SSH, local Home,
  or Slurm depend on NFS;
- `ood_apps` publishes the repository applications, Grafana link, Job Composer
  templates, partition menu, and per-user rclone remotes.

## Authentication and network entry

Users access OOD through the controller's current campus-network IP. There is
no DNS name or external identity provider. Apache serves HTTPS with a locally
generated certificate whose subject alternative name contains that IP.

OOD uses HTTP Basic authentication. Usernames are identical to the Linux names
in `users.yml`, but OOD passwords are independent of Linux passwords and SSH
keys. `/etc/ood/auth/htpasswd` is the live source of truth and administrators
modify it locally with `htpasswd`. Ordinary Ansible convergence never replaces
the file. Administrators periodically store an explicit Ansible-Vault-encrypted
snapshot in the repository for disaster recovery; restore is a separate manual
operation.

## Slurm integration and authorization

The controller uses the local Slurm adapter and the stable cluster name `epic`.
No SSH hop is used for `sbatch`, `squeue`, `scontrol`, or `scancel`.

Ansible renders `/etc/ood/config/site.d/partitions.yml` from:

- `ansible/vars/slurm_partitions.yml` for partition authorization;
- `ansible/vars/users.yml` for usernames and Slurm Accounts;
- inventory host variables for CPU, memory, GPU count, and display labels.

Forms show only partitions authorized for the current user. This filtering is a
user-interface convenience; Slurm Associations remain the authoritative access
control. Partition labels are friendly descriptions, while submitted values are
the complete host-specific partition names.

Every IAPP exposes only the basic resource fields: target host, CPU count, GPU
count, memory, duration, working directory, application-specific settings, and
an advanced `extra_sbatch` field. The advanced field remains intentionally
available for QoS, binding, and other Slurm options. Mail fields are removed.
Interactive jobs are limited to 32 hours. Ordinary Slurm jobs retain the
partition's 14-day limit.

## Shared OOD context

Batch Connect and Job Composer require the controller and execution node to see
the same session files. The controller exports only:

```text
/srv/epic/ood
```

Compute nodes mount it at the same absolute path through systemd automount with
`_netdev` and `nofail`. The default hard NFS behavior is retained to avoid
silent session-file corruption. An outage may stall or fail an OOD session that
is using this path, but does not block system boot, SSH, Slurm, local Home, or
ordinary local jobs.

OOD uses explicit dataroots rather than per-user Home symlinks:

```text
/srv/epic/ood/users/$USER/ondemand/data/sys/dashboard
/srv/epic/ood/users/$USER/ondemand/data/sys/myjobs
```

Ansible creates the per-user roots with the user's synchronized UID/GID and
mode `0700`. The dashboard cleans stopped Batch Connect directories older than
30 days. SlurmDBD remains the job-history source; the shared context is not an
archive or general-purpose network filesystem.

## Independent Home and Remote Files

The controller and every compute host retain independent Home directories.
OOD 4.2 Remote Files is enabled through rclone. On the controller, Ansible adds
one SFTP remote per host in each user's `ssh_access` list. The remote uses that
user's existing unencrypted cluster key at
`~/.ssh/epic_cluster_ed25519` and the stable inventory hostname.

The Files application therefore exposes the controller-local Home and the
authorized compute-node Homes without mounting them. Connections are created on
demand; an offline compute node affects only its own remote. The Files shell
button and the built-in Shell application are disabled. Large transfers should
still use `rsync`; browser transfers target code and small files.

## Published applications

The initial system applications are:

- JupyterLab;
- Code Server;
- scheduled Web Shell through ttyd;
- TensorBoard;
- Script, retained as a form-based shortcut for users who do not want to write
  an sbatch script;
- a Grafana link.

Prometheus is not linked for ordinary users. The repository also supplies Job
Composer templates for an ordinary job, a GPU job, and a Job Array. These
templates complement rather than replace the Script IAPP.

All IAPPs use the same host/resource menu, preserve `extra_sbatch`, use PATH to
find runtime programs, keep connection state in the shared dataroot, and keep
user work in the selected compute-node path. The first deployment assumes the
documented runtime set is installed on every compute node; per-host capability
declarations are deferred until a real incompatibility appears.

## Monitoring and operations

`ondemand_exporter` runs on the controller at port `9301`. Prometheus scrapes it
every two minutes. Grafana remains the reporting interface; OOD exports only its
own portal/PUN/application metrics.

The role manages the exporter service and portal/PUN restarts after
configuration changes. Verification is limited to
configuration generation, service state, the exporter endpoint, and one
end-to-end IAPP launch during deployment. OOD failure must not affect Slurm,
SSH, accounting, monitoring storage, or already running compute processes.

## New-node workflow

For a new compute node, administrators install the standard IAPP runtime set,
add the host to inventory and Slurm declarations, synchronize identities and
SSH access, converge Slurm Associations, then run the OOD playbook. The host is
automatically added to authorized users' menus, rclone remotes, Prometheus
context, and the shared-context mount.
