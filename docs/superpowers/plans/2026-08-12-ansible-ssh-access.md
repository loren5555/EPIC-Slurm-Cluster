# Ansible SSH Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate one non-overwriting cluster SSH key per user on the controller and install its public key only on the controller and compute hosts authorized by `cluster_users[].ssh_access`.

**Architecture:** `playbooks/ssh_access.yml` runs three ordered plays: validate every target without changing it, create/read key sources on the controller, then converge one marked block in each applicable `authorized_keys`. A pure filter calculates authorized usernames for each inventory host. Existing unmarked keys and all private keys remain outside Ansible management.

**Tech Stack:** Ansible Core built-in modules, OpenSSH Ed25519 keys, YAML, Python unittest.

---

### Task 1: Host authorization calculation

**Files:**
- Modify: `ansible/filter_plugins/identity.py`
- Modify: `tests/test_identity_conflicts.py`

- [ ] Add a failing unit test proving that every user is authorized on a controller while compute hosts receive only users whose `ssh_access` contains that full inventory hostname.
- [ ] Run `python -m unittest tests.test_identity_conflicts` and confirm the missing filter fails the test.
- [ ] Add `ssh_authorized_users(cluster_users, host_name, controller_hosts)` and export it as `epic_ssh_authorized_users`.
- [ ] Re-run the unit tests and confirm they pass.

### Task 2: SSH access role

**Files:**
- Create: `ansible/roles/ssh_access/tasks/preflight.yml`
- Create: `ansible/roles/ssh_access/tasks/key_source.yml`
- Create: `ansible/roles/ssh_access/tasks/distribute.yml`

- [ ] In `preflight.yml`, read passwd data and assert every manifest user exists with the expected UID before any key is generated.
- [ ] In `key_source.yml`, inspect each controller key, generate missing `.ssh/epic_cluster_ed25519` Ed25519 keys without overwriting existing files, read public keys, and build an in-memory username-to-public-key mapping. In check mode, report missing key generation but do not attempt to read nonexistent files.
- [ ] In `distribute.yml`, calculate authorized users for the current host, create `.ssh` only for authorized users, and add one uniquely marked EPIC key block to `authorized_keys`. For unauthorized users, remove only that marked block when the file already exists; preserve all other lines and files.

### Task 3: Ordered playbook and site integration

**Files:**
- Create: `ansible/playbooks/ssh_access.yml`
- Modify: `ansible/playbooks/site.yml`

- [ ] Add the all-host read-only preflight play with `any_errors_fatal: true`.
- [ ] Add the controller key-source play after preflight.
- [ ] Add the all-host distribution play after key generation.
- [ ] Import `ssh_access.yml` from `site.yml` immediately after identity synchronization.

### Task 4: Verification and commit

**Files:**
- Verify all files above.

- [ ] Run all Python tests and the identity manifest validator.
- [ ] Parse every Ansible YAML file with PyYAML and run `git diff --check`.
- [ ] Review the diff against the approved single-key design: no private-key transfer, no replacement of unmarked authorized keys, and no authorization outside `ssh_access`.
- [ ] Commit only this plan and SSH implementation, leaving pre-existing user edits unstaged.
