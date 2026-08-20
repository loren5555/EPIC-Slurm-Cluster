# User Onboarding Usability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let operators create any syntactically valid OOD username immediately and make the onboarding playbook complete all non-interactive user configuration.

**Architecture:** Keep native interactive `htpasswd`, but replace the rendered user-name list in sudoers with a generic single-username regular expression while retaining the fixed password-file path. Extend the existing composite playbook with `ood.yml`, then align administrator documentation and its copyable manifest example with the real workflow.

**Tech Stack:** Ansible YAML/Jinja, sudoers regular expressions, Markdown, Python `unittest` contract tests.

---

### Task 1: Define the new operator and onboarding contracts

**Files:**

- Modify: `tests/test_cluster_operator_role.py`

- [x] **Step 1: Replace the static-name expectation and add the complete onboarding expectation**

```python
def test_sudoers_accepts_any_valid_ood_username_for_the_fixed_password_file(self):
    template = read_ansible_file(
        "roles/cluster_operator/templates/epic-operators.sudoers.j2"
    )
    self.assertIn("^[a-z_][a-z0-9_.-]*$", template)
    self.assertNotIn("cluster_users | map(attribute='name')", template)

def test_user_onboarding_includes_all_noninteractive_user_configuration(self):
    playbook = read_ansible_file("playbooks/user_onboarding.yml")
    imports = [
        "users.yml",
        "ssh_access.yml",
        "slurm_associations.yml",
        "disk_quotas.yml",
        "ood.yml",
    ]
    positions = [playbook.index(f"import_playbook: {name}") for name in imports]
    self.assertEqual(positions, sorted(positions))
```

- [x] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest discover -s tests -p test_cluster_operator_role.py -v
```

Expected: both tests fail because sudoers still renders `cluster_users` and onboarding lacks `ood.yml`.

### Task 2: Implement the minimal Ansible behavior

**Files:**

- Modify: `ansible/roles/cluster_operator/templates/epic-operators.sudoers.j2`
- Modify: `ansible/playbooks/user_onboarding.yml`

- [x] **Step 1: Make the OOD username argument generic while keeping the password file fixed**

```jinja2
Cmnd_Alias EPIC_OOD_PASSWORD = /usr/bin/htpasswd {{ ood_authentication_file }} ^[a-z_][a-z0-9_.-]*$
```

- [x] **Step 2: Import OOD configuration last in onboarding**

```yaml
- import_playbook: users.yml
- import_playbook: ssh_access.yml
- import_playbook: slurm_associations.yml
- import_playbook: disk_quotas.yml
- import_playbook: ood.yml
```

- [x] **Step 3: Run the two focused tests and verify GREEN**

Run the Task 1 command again. Expected: both tests pass.

### Task 3: Align administrator documentation

**Files:**

- Modify: `docs/admin/users.md`
- Modify: `docs/admin/commands.md`

- [x] **Step 1: Add this complete copyable manifest entry to `users.md`**

```yaml
- name: exampleuser
  uid: 10000
  gid: 10000
  slurm_account: epic-rl
  home: /home/exampleuser
  shell: /bin/bash
  groups:
    - EPIC-RL
  ssh_access:
    - epic-cluster-compute-a100-01
```

- [x] **Step 2: State that partition policy is changed only when required**

Explain that an Account already present in `allowed_accounts` needs no partition edit, while explicit `allowed_users` authorization does.

- [x] **Step 3: Document the real onboarding sequence in both files**

Use exactly:

```text
users.yml → ssh_access.yml → slurm_associations.yml → disk_quotas.yml → ood.yml
```

State that OOD password creation remains the only separate interactive step and accepts any syntactically valid username.

- [x] **Step 4: Verify the documentation contract**

Run:

```powershell
rg -n "exampleuser|disk_quotas.yml|ood.yml|allowed_accounts|allowed_users|任意.*用户名" docs/admin/users.md docs/admin/commands.md
```

Expected: both workflow files and every template/policy term are present.

### Task 4: Minimal final verification

**Files:**

- Verify: all files above

- [x] **Step 1: Run only the focused cluster-operator test file**

```powershell
python -m unittest discover -s tests -p test_cluster_operator_role.py -v
```

Expected: all tests in that focused file pass.

- [x] **Step 2: Check the edited files for whitespace errors**

```powershell
git diff --check -- ansible/roles/cluster_operator/templates/epic-operators.sudoers.j2 ansible/playbooks/user_onboarding.yml tests/test_cluster_operator_role.py docs/admin/users.md docs/admin/commands.md
```

Expected: exit code 0. Leave all changes uncommitted in the current workspace.
