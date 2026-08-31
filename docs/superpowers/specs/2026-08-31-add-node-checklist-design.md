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

## Boundaries

This change updates published documentation, links, and documentation structure
tests only. It does not change inventory, Ansible behavior, Slurm configuration,
or any live node.
