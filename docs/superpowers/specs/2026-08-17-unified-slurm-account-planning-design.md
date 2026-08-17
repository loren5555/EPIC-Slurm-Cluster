# Unified Slurm Account Planning Design

## Goal

Keep every rule about Slurm Account entities and their cluster-level
Associations in one planner. Ansible execution tasks should apply an explicit
plan without comparing one plan with another.

## Ownership

The Account planner owns:

- creation and metadata repair of Account entities;
- creation of a cluster-level Association for an existing Account;
- repair of cluster-level Fairshare and explicit TRES limits.

The Association planner owns only partition-scoped Account and user
Associations. It does not plan global Account Associations.

## Required states

| Current database state | Planned operation |
| --- | --- |
| Account and cluster Association absent | Create the Account once |
| Account exists; cluster Association absent | Add the cluster Association |
| Both exist and match | No operation |
| Cluster Association differs | Update the cluster Association |

`sacctmgr add account Cluster=<cluster>` creates both the Account and its
cluster-level Association. Therefore the first state must never also produce
an Association-add operation.

## Execution and audit

`converge.yml` consumes independent lists produced by the Account planner. It
contains no cross-plan exclusion condition. `audit.yml` invokes the same
planner after convergence, so all Account and cluster Association states are
verified through the same rules used during planning.

The declared users, Accounts, partition permissions, limits, and Fairshare
policy are unchanged.
