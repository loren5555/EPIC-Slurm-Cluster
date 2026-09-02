# Cluster Operator Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give declared EPIC operators Git-driven deployment, limited controller privileges, Slurm Operator authority, and direct restricted OOD password resets without granting unrestricted sudo.

**Architecture:** `administrators.yml` declares the owner, future superadministrators, and equal business operators. A controller-only Ansible role creates the administrator groups, renders exact sudoers permissions from the trusted deployment checkout, and grants declared operators SlurmDB `AdminLevel=Operator`. OOD password reset remains a native `htpasswd` invocation; its sudoers regular expression is generated from the authoritative cluster-user list.

**Tech Stack:** Ansible built-ins, sudoers regular expressions, OpenSSH/Linux groups, SlurmDB `sacctmgr`, Apache `htpasswd`, Python unittest.

---

### Task 1: Declare and validate administrator membership

**Files:**
- Create: `ansible/vars/administrators.yml`
- Modify: `tests/test_cluster_operator_role.py`

- [ ] **Step 1: Write a failing contract test**

```python
def test_operator_manifest_and_playbook_are_declared(self) -> None:
    manifest = read_ansible_file("vars/administrators.yml")
    playbook = read_ansible_file("playbooks/administrators.yml")

    self.assertIn("epic_superadministrators:", manifest)
    self.assertIn("epic_operators:", manifest)
    self.assertIn("liuhongbo", manifest)
    self.assertIn("cluster_operator", playbook)
```

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m unittest tests.test_cluster_operator_role.ClusterOperatorRoleTests.test_operator_manifest_and_playbook_are_declared`

Expected: failure because the administrator manifest and playbook do not exist.

- [ ] **Step 3: Add the manifest and controller playbook**

Use `epic_superadministrators` and `epic_operators` lists. Load both the user manifest and administrator manifest in a controller-only playbook.

- [ ] **Step 4: Run the test and verify success**

Run: `python -m unittest tests.test_cluster_operator_role.ClusterOperatorRoleTests.test_operator_manifest_and_playbook_are_declared`

Expected: `OK`.

### Task 2: Install controller groups and exact sudoers rules

**Files:**
- Create: `ansible/roles/cluster_operator/tasks/main.yml`
- Create: `ansible/roles/cluster_operator/templates/epic-operators.sudoers.j2`
- Modify: `tests/test_cluster_operator_role.py`

- [ ] **Step 1: Write failing contracts for the command boundary**

```python
def test_sudoers_uses_fixed_playbooks_and_managed_ood_users(self) -> None:
    template = read_ansible_file(
        "roles/cluster_operator/templates/epic-operators.sudoers.j2"
    )

    self.assertIn("/usr/bin/ansible-playbook", template)
    self.assertIn("playbooks/users.yml", template)
    self.assertIn("playbooks/ood.yml", template)
    self.assertNotIn("playbooks/site.yml", template)
    self.assertIn("/usr/bin/htpasswd", template)
    self.assertIn("cluster_users", template)
```

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m unittest tests.test_cluster_operator_role.ClusterOperatorRoleTests.test_sudoers_uses_fixed_playbooks_and_managed_ood_users`

Expected: failure because the template does not exist.

- [ ] **Step 3: Implement the controller-only role**

Create `epic-superadmins` and `epic-operators`, append declared users to their intended groups, append superadministrators to the system `sudo` group, and render `/etc/sudoers.d/epic-operators` with mode `0440` plus `visudo -cf %s` validation. Allow exact Git update/status/log commands, exact check/deploy invocations for each approved playbook, and one `htpasswd` command whose username is matched against declared `cluster_users` only.

- [ ] **Step 4: Run the contract test and syntax check**

Run: `python -m unittest tests.test_cluster_operator_role.ClusterOperatorRoleTests.test_sudoers_uses_fixed_playbooks_and_managed_ood_users && git diff --check`

Expected: `OK` and no whitespace errors.

### Task 3: Grant Slurm business authority declaratively

**Files:**
- Modify: `ansible/roles/cluster_operator/tasks/main.yml`
- Modify: `tests/test_cluster_operator_role.py`

- [ ] **Step 1: Write a failing contract test**

```python
def test_role_grants_declared_operators_slurm_operator_level(self) -> None:
    tasks = read_ansible_file("roles/cluster_operator/tasks/main.yml")

    self.assertIn("/usr/bin/sacctmgr", tasks)
    self.assertIn("AdminLevel=Operator", tasks)
    self.assertIn("epic_operators", tasks)
```

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m unittest tests.test_cluster_operator_role.ClusterOperatorRoleTests.test_role_grants_declared_operators_slurm_operator_level`

Expected: failure because the role has no Slurm authority task.

- [ ] **Step 3: Add the idempotent Slurm authority task**

Run `sacctmgr --immediate modify user where Name=<operator> set AdminLevel=Operator` for declared operators only outside check mode. Do not grant `Administrator`, MariaDB access, or arbitrary `sacctmgr` sudo access.

- [ ] **Step 4: Run the contract test**

Run: `python -m unittest tests.test_cluster_operator_role.ClusterOperatorRoleTests.test_role_grants_declared_operators_slurm_operator_level`

Expected: `OK`.

### Task 4: Integrate and document operations

**Files:**
- Modify: `ansible/playbooks/site.yml`
- Modify: `docs/admin_doc.md`
- Modify: `docs/superpowers/specs/2026-08-19-cluster-operator-access-design.md`

- [ ] **Step 1: Add a failing integration contract**

```python
def test_full_site_imports_administrator_convergence_after_slurm_policy(self) -> None:
    site = read_ansible_file("playbooks/site.yml")

    self.assertIn("import_playbook: administrators.yml", site)
    self.assertGreater(
        site.index("import_playbook: administrators.yml"),
        site.index("import_playbook: slurm_associations.yml"),
    )
```

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m unittest tests.test_cluster_operator_role.ClusterOperatorRoleTests.test_full_site_imports_administrator_convergence_after_slurm_policy`

Expected: failure because the full site does not import administrator convergence.

- [ ] **Step 3: Add the full-site import and operating procedure**

Import `administrators.yml` after `slurm_associations.yml`. Document GitHub merge, exact `sudo git pull`, check-mode then deployment commands, OOD password reset syntax, and the excluded `site.yml` boundary for operators.

- [ ] **Step 4: Run targeted tests and static checks**

Run: `python -m unittest tests.test_cluster_operator_role tests.test_slurm_associations_role && git diff --check`

Expected: all tests pass and no whitespace errors.
