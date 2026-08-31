# Cluster Operator Permission Compatibility Fix

## Purpose

Repair administrator convergence on the controller while preserving the
previously agreed permission boundary:

- cluster operators may update any username in the fixed OOD htpasswd file;
- superadministrators have full Slurm administrative authority;
- cluster operators retain Slurm Operator authority;
- ordinary managed users have no Slurm administrative authority.

## Root Causes

The sudoers template currently uses a regular expression as the username
argument to `htpasswd`. The controller's `visudo` rejects that expression, so
Ansible cannot install the generated sudoers file. The username must not be
matched against `cluster_users`; the fixed htpasswd path is the security
boundary.

The Slurm convergence tasks grant `AdminLevel=Operator` only to
`epic_operators`, then set every other managed cluster user to
`AdminLevel=None`. A superadministrator who is not also listed as an operator
is therefore explicitly denied Slurm administrative authority.

## Sudoers Design

Keep the native interactive command and fixed password file. Replace the
username regular expression with the sudoers command-argument wildcard:

```sudoers
/usr/bin/htpasswd /etc/ood/auth/htpasswd *
```

This deliberately accepts any username argument and does not depend on the
Ansible user manifest. It does not permit the operator to select another
password file. Existing fixed Git and Ansible command aliases remain
unchanged.

## Slurm Authority Design

Converge the three authority sets independently with explicit precedence:

1. `epic_superadministrators` receive `AdminLevel=Administrator`.
2. Members of `epic_operators` who are not superadministrators receive
   `AdminLevel=Operator`.
3. Managed cluster users in neither administrator set receive
   `AdminLevel=None`.

If a username appears in both administrator lists, Administrator wins. This
prevents the later Operator or revocation loops from downgrading a
superadministrator.

## Validation

Contract tests will first reproduce both regressions: the sudoers command must
use the unrestricted username wildcard without the incompatible regular
expression, and the role must express all three Slurm authority sets with
Administrator precedence. After the tests fail for the expected reasons, the
minimal template and task changes will be applied.

Verification will include the focused cluster-operator test suite, the wider
repository test suite where practical, Ansible syntax checking, whitespace
checks, and `visudo` validation in an environment where `visudo` is available.
Documentation examples will be aligned with the final command and Slurm role
definitions.
