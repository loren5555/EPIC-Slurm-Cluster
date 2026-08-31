# Add Node Checklist Documentation Design

## Goal

Add a practical compute-node onboarding checklist for superadministrators and
number every developer document filename to match its sidebar `nav_order`.

## Documentation structure

The developer section uses the same filename convention as the user section:

1. `01-repository.md`
2. `02-ansible.md`
3. `03-apps.md`
4. `04-documentation.md`
5. `05-operations.md`
6. `06-superadmin.md`
7. `07-add-node-checklist.md`

The developer index follows this order. All internal links and documentation
structure contracts use the numbered paths.

## Checklist scope

`07-add-node-checklist.md` is an operational reference for members of
`epic-superadmins`. It covers readiness and rollback planning, base operating
system and cluster runtime preparation, inventory and host variables, Slurm
partition and association data, storage and identity access, monitoring and OOD,
staged convergence, workload acceptance, and handoff records.

The checklist points to repository-owned sources of truth instead of duplicating
their complete contents. The superadministrator and Ansible pages link directly
to it.

## Runbook expansion

The checklist is also the executable onboarding runbook. It remains a single
linear page so a superadministrator can follow it without switching between a
short checklist and a separate procedure.

The runbook begins with reusable placeholders for the node name, addresses,
controller, repository checkout, partition, and node class. Each phase contains:

- the purpose and completion condition;
- generic commands or configuration examples using explicit placeholders;
- the expected result that permits moving to the next phase;
- a stop or rollback instruction when the expected result is absent.

The phases are host identity and networking, time and administrator access,
base packages, MUNGE and Slurm, storage, optional GPU and monitoring runtimes,
hardware fact collection, repository declarations, repository checkout and
Vault access, `site.yml` convergence, service and workload acceptance, and
rollback and handoff.

Installation commands stay distribution- and version-neutral. They name the
required package or upstream component and use placeholders such as
`<package-manager>` where syntax is environment-specific. The runbook does not
pin an Ubuntu release, driver, exporter, or Slurm version. Hardware- and
version-sensitive installation steps must be completed using the approved
vendor or project instructions before Ansible convergence.

`site.yml` is the normal full-convergence entry point after the host runtime and
repository data are ready. Its syntax check and check-mode diff are documented
as mandatory review gates before the live run. Focused playbooks remain recovery
tools rather than the primary new-node workflow.

## Boundaries

This change updates published documentation, links, and documentation structure
tests only. It does not change inventory, Ansible behavior, Slurm configuration,
or any live node. The expansion changes only
`docs/developer/07-add-node-checklist.md` and this design record.
