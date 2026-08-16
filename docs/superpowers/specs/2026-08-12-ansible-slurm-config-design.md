# EPIC Cluster Ansible Slurm Configuration Design

Date: 2026-08-12  
Status: Superseded by the current stack deployment guide

> This document records the earlier two-partition design. The approved current
> design uses one partition per compute host, partition-specific SlurmDBD
> associations, and class-specific cgroup policy. Use
> [`docs/slurm-stack-deployment-guide.md`](../../slurm-stack-deployment-guide.md)
> for implementation. This file remains only as decision history.

## 1. Goal and Scope

Ansible will make the repository the source of truth for the currently working
Slurm configuration on the controller, A100 node, and RTX 4070 node.

This work manages only:

- `/etc/slurm/slurm.conf`
- `/etc/slurm/cgroup.conf`
- `/etc/slurm/gres.conf`
- Slurm configuration reloads caused by changes to those files

It does not install or upgrade Slurm packages, configure package repositories,
replace the MUNGE key, enable Slurm accounting, deploy Open OnDemand, or change
the existing SSH GPU-isolation policy.

## 2. Inventory Model

The existing inventory groups define partition membership:

- `controlled_compute_nodes` becomes the `controlled` Slurm partition.
- `free_compute_nodes` becomes the `free` Slurm partition.
- `compute_nodes` contains every `slurmd` host.
- `controllers` contains the active `slurmctld` host.

Host-specific Slurm hardware data lives in
`ansible/host_vars/<inventory-hostname>.yml`. Each compute-node record defines
its CPU topology, schedulable memory, feature, GPU type, GPU count, and device
range. This keeps hardware facts close to the inventory identity and avoids a
large conditional template.

Initial values preserve the running configuration:

| Host | Partition | CPUs | Sockets | Cores | Threads | Memory | GPU |
|---|---|---:|---:|---:|---:|---:|---|
| `epic-cluster-compute-a100-01` | `controlled` | 128 | 2 | 64 | 1 | 1030000 MiB | 8 × `a100-sxm4` |
| `epic-cluster-compute-rtx4070-01` | `free` | 32 | 1 | 16 | 2 | 126000 MiB | 1 × `rtx4070` |

`ansible/group_vars/all/slurm.yml` contains cluster-wide policy such as the
cluster name, ports, state paths, partition time limit, and default partition.

## 3. Generated Configuration

### 3.1 `slurm.conf`

The same `slurm.conf` is installed on every controller and compute node. It
contains:

- `ClusterName=epic`
- `SlurmctldHost=epic-cluster-controller-01` without a fixed address
- MUNGE authentication and the existing daemon users
- local state under `/var/lib/slurm`
- local logs under `/var/log/slurm`
- `sched/backfill` and `select/cons_tres`
- `SelectTypeParameters=CR_Core_Memory`
- `task/affinity,task/cgroup` and `proctrack/cgroup`
- `GresTypes=gpu`
- one generated `NodeName` record for every compute host
- `controlled` and `free` partitions generated from inventory groups

The controller address is deliberately not embedded in `SlurmctldHost`.
`epic-cluster-controller-01` already resolves to the controller address that is
reachable from each network: the A100 path uses `172.16.2.182`, while the RTX
4070 path uses `192.168.77.251`.

Each compute-node `NodeAddr` comes from its current `ansible_host`. A later IP
change therefore requires only an inventory update and another Slurm
configuration run.

`free` remains the default partition. Both partitions are available to all
cluster users, use `MaxTime=14-00:00:00`, and do not configure account, QoS,
quota, preemption, or forced oversubscription policy.

Accounting parameters are intentionally absent. In particular, the templates
must not add `AccountingStorageTRES=gres/gpu` before `slurmdbd` exists, because
Slurm 25.11 rejects that configuration.

### 3.2 `cgroup.conf`

The common cgroup-v2 policy is:

```ini
CgroupPlugin=autodetect
ConstrainCores=yes
ConstrainRAMSpace=yes
ConstrainDevices=yes
```

This preserves CPU, memory, and GPU-device enforcement for Slurm jobs. The
existing systemd `user.slice` policy that hides GPUs from ordinary A100 SSH
sessions remains separate and is not modified by this role.

### 3.3 `gres.conf`

Each compute node receives a short host-local `gres.conf` with explicit NVIDIA
device files:

- A100: `Name=gpu Type=nvidia_a100-sxm4-40gb File=/dev/nvidia[0-7]`
- RTX 4070: `Name=gpu Type=rtx4070 File=/dev/nvidia0`

The controller receives an empty, comment-only `gres.conf`. Explicit device
paths retain cgroup device enforcement and avoid depending on NVML plugin
package naming. Users and OOD may request an untyped resource such as
`--gres=gpu:1`; typed requests remain available when needed.

## 4. Safe Convergence

The Slurm playbook runs in four phases:

1. Preflight every host: verify required Slurm commands, expected daemon role,
   hostname, controller-name resolution, and current service availability.
2. Render and distribute all three configuration files with backups enabled.
3. On compute nodes, run `slurmd -G` against the installed configuration before
   activating a change. A failure stops activation and leaves diagnostic output.
4. If configuration changed, run `scontrol reconfigure` from the controller and
   restart only the affected `slurmd` services. Then verify controller health,
   node registration, partitions, and GPU counts.

All hosts use the same play with `any_errors_fatal: true`, so an unreachable or
incompatible node stops the run before configuration deployment. A
`--check --diff` run shows file changes but does not reload or restart services.

For Slurm 25.11, normal configuration updates use `scontrol reconfigure` rather
than restarting `slurmctld`. The controller state directory and queued jobs are
not replaced or cleared.

## 5. File Structure and Readability

```text
ansible/
├── group_vars/all/slurm.yml
├── host_vars/
│   ├── epic-cluster-compute-a100-01.yml
│   └── epic-cluster-compute-rtx4070-01.yml
├── playbooks/slurm.yml
└── roles/slurm/
    ├── handlers/main.yml
    ├── tasks/main.yml
    └── templates/
        ├── slurm.conf.j2
        ├── cgroup.conf.j2
        └── gres.conf.j2
```

Templates use English section comments and blank lines between logical groups.
Tasks describe deployment intent rather than restating module names.

## 6. Adding a Compute Node Later

A new server requires only:

1. Existing manual installation of the chosen Slurm version and the shared
   MUNGE key.
2. Addition to either `controlled_compute_nodes` or `free_compute_nodes`.
3. A host-vars file containing its hardware and GPU definition.
4. A check-mode run followed by the normal Slurm configuration playbook.

No template or partition definition changes are required.

## 7. Acceptance Criteria

- All three hosts have identical `slurm.conf` and `cgroup.conf` content.
- Each compute node has only its own GPU device definition in `gres.conf`.
- `scontrol ping` reports the primary controller as up.
- `sinfo` shows A100 in `controlled` and RTX 4070 in `free`.
- `free` is the default partition.
- Slurm reports eight A100 GPUs and one RTX 4070 GPU.
- A one-GPU test job runs successfully on each node and sees only its allocated
  GPU.
- Running the playbook again reports `changed=0` and does not restart services.
- No package, MUNGE, accounting, OOD, SSH key, or Linux identity file changes.
