# Cluster Operator Permission Compatibility Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the operator sudoers file valid on the controller while granting superadministrators full Slurm administration and preserving restricted Operator authority for business administrators.

**Architecture:** Keep the fixed native `htpasswd` command and replace its incompatible username regex with a sudoers argument wildcard. Converge Slurm authority in three disjoint sets, applying Administrator precedence over Operator and None. Update contract tests and operator documentation to encode the agreed boundary.

**Tech Stack:** Ansible YAML/Jinja, sudoers, Slurm `sacctmgr`, Python `unittest`, Markdown

---

### Task 1: Encode the two regressions as failing contract tests

**Files:**

- Modify: `tests/test_cluster_operator_role.py:29-73`
- Test: `tests/test_cluster_operator_role.py`

- [ ] **Step 1: Replace the username-regex contract with the unrestricted argument contract**

Replace the existing sudoers test with:

```python
def test_sudoers_accepts_any_ood_username_for_fixed_password_file(self) -> None:
    template = read_ansible_file(
        "roles/cluster_operator/templates/epic-operators.sudoers.j2"
    )

    self.assertIn("/usr/bin/ansible-playbook", template)
    self.assertIn("'users.yml'", template)
    self.assertIn("'ood.yml'", template)
    self.assertNotIn("'site.yml'", template)
    self.assertIn(
        "/usr/bin/htpasswd {{ ood_authentication_file }} *",
        template,
    )
    self.assertNotIn("^[a-z_][a-z0-9_.-]*$", template)
    self.assertNotIn("cluster_users | map(attribute='name')", template)
    self.assertIn("NOPASSWD: EPIC_GIT, EPIC_ANSIBLE, EPIC_OOD_PASSWORD", template)
    self.assertIn("%epic-superadmins ALL=(ALL:ALL) ALL", template)
```

- [ ] **Step 2: Replace the Slurm Operator-only contract with a three-level authority contract**

Replace `test_role_grants_declared_operators_slurm_operator_level` with:

```python
def test_role_converges_three_slurm_administration_levels(self) -> None:
    tasks = read_ansible_file("roles/cluster_operator/tasks/main.yml")

    self.assertIn("/usr/bin/sacctmgr", tasks)
    self.assertIn("AdminLevel=Administrator", tasks)
    self.assertIn("AdminLevel=Operator", tasks)
    self.assertIn("AdminLevel=None", tasks)
    self.assertIn('loop: "{{ epic_superadministrators }}"', tasks)
    self.assertIn(
        'loop: "{{ epic_operators | difference(epic_superadministrators) | sort }}"',
        tasks,
    )
    self.assertIn(
        "difference(epic_operators) | difference(epic_superadministrators)",
        tasks,
    )
    self.assertIn("gpasswd", tasks)
    self.assertNotIn("groups: epic-superadmins,sudo", tasks)
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```powershell
python -m unittest tests.test_cluster_operator_role -v
```

Expected: the two modified tests fail because the template still contains the regex and the role has no `AdminLevel=Administrator` task.

### Task 2: Make the OOD password sudoers rule controller-compatible

**Files:**

- Modify: `ansible/roles/cluster_operator/templates/epic-operators.sudoers.j2:16-18`
- Test: `tests/test_cluster_operator_role.py`

- [ ] **Step 1: Replace the regular expression with the agreed wildcard**

Use:

```jinja2
# Accept any OOD username while keeping the password file fixed.
# Password input remains interactive and is never committed to Git.
Cmnd_Alias EPIC_OOD_PASSWORD = /usr/bin/htpasswd {{ ood_authentication_file }} *
```

- [ ] **Step 2: Run the sudoers contract and verify GREEN**

Run:

```powershell
python -m unittest tests.test_cluster_operator_role.ClusterOperatorRoleTests.test_sudoers_accepts_any_ood_username_for_fixed_password_file -v
```

Expected: PASS.

### Task 3: Converge Slurm Administrator, Operator, and None without downgrades

**Files:**

- Modify: `ansible/roles/cluster_operator/tasks/main.yml:69-105`
- Test: `tests/test_cluster_operator_role.py`

- [ ] **Step 1: Add Administrator convergence before the Operator task**

Insert:

```yaml
- name: Grant declared superadministrators full Slurm authority
  ansible.builtin.command:
    argv:
      - /usr/bin/sacctmgr
      - --immediate
      - modify
      - user
      - where
      - "Name={{ item }}"
      - set
      - AdminLevel=Administrator
  loop: "{{ epic_superadministrators }}"
  loop_control:
    label: "{{ item }}"
  changed_when: false
  when: not ansible_check_mode
```

- [ ] **Step 2: Exclude superadministrators from Operator convergence**

Change the Operator loop to:

```yaml
loop: "{{ epic_operators | difference(epic_superadministrators) | sort }}"
```

- [ ] **Step 3: Exclude both active administrator sets from revocation**

Change the None loop to:

```yaml
loop: >-
  {{ cluster_operator_user_names | difference(epic_operators)
     | difference(epic_superadministrators) | sort }}
```

Update the adjacent comment to state that every managed user is explicitly an Administrator, Operator, or None and that Administrator takes precedence.

- [ ] **Step 4: Run the full focused test file and verify GREEN**

Run:

```powershell
python -m unittest tests.test_cluster_operator_role -v
```

Expected: all cluster-operator tests pass.

### Task 4: Align administrator documentation

**Files:**

- Modify: `docs/admin/commands.md:97-107`
- Modify: `docs/developer/superadmin.md:12-32`

- [ ] **Step 1: State the unrestricted OOD username boundary**

Change the OOD section in `docs/admin/commands.md` to say:

```markdown
管理员可以为任意 OOD 用户名创建或重置密码，不需要匹配 `users.yml` 或重新发布
sudoers 用户名单。密码文件路径仍固定为 `/etc/ood/auth/htpasswd`：
```

Keep the existing command and the explanation that OOD passwords are separate from Linux, SSH, and Slurm access.

- [ ] **Step 2: Document Slurm role precedence for superadministrators**

Add this paragraph after the administrator convergence procedure in `docs/developer/superadmin.md`:

```markdown
SlurmDB 权限由同一工作包收敛：`epic_superadministrators` 获得
`AdminLevel=Administrator`，`epic_operators` 获得 `AdminLevel=Operator`，其余受管
用户设为 `AdminLevel=None`。如果用户名同时出现在两个管理员名单中，超级管理员
权限优先。
```

- [ ] **Step 3: Verify the documentation terms**

Run:

```powershell
rg -n "任意 OOD 用户名|不需要匹配|AdminLevel=Administrator|AdminLevel=Operator|AdminLevel=None|权限优先" docs/admin/commands.md docs/developer/superadmin.md
```

Expected: every phrase is present in the intended document.

### Task 5: Verify the complete change

**Files:**

- Verify: `ansible/roles/cluster_operator/templates/epic-operators.sudoers.j2`
- Verify: `ansible/roles/cluster_operator/tasks/main.yml`
- Verify: `tests/test_cluster_operator_role.py`
- Verify: `docs/admin/commands.md`
- Verify: `docs/developer/superadmin.md`

- [ ] **Step 1: Run the repository test suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run Ansible syntax validation when Ansible is available**

Run on the repository's supported Linux/Ansible environment:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/administrators.yml --syntax-check
```

Expected: syntax check succeeds. If native Ansible is absent on Windows, record that limitation and rely on the focused contract plus controller deployment validation.

- [ ] **Step 3: Validate the rendered sudoers rule when visudo is available**

Render or deploy the template with the configured paths, then run:

```bash
visudo -cf /etc/sudoers.d/epic-operators
```

Expected: `parsed OK`. If `visudo` is unavailable locally, validate through the Ansible template task on the controller and record the local limitation.

- [ ] **Step 4: Check whitespace and inspect the final diff**

Run:

```powershell
git diff --check
git diff -- ansible/roles/cluster_operator/templates/epic-operators.sudoers.j2 ansible/roles/cluster_operator/tasks/main.yml tests/test_cluster_operator_role.py docs/admin/commands.md docs/developer/superadmin.md
```

Expected: no whitespace errors; every changed line maps to the approved design.

- [ ] **Step 5: Commit the implementation**

Run:

```powershell
git add ansible/roles/cluster_operator/templates/epic-operators.sudoers.j2 ansible/roles/cluster_operator/tasks/main.yml tests/test_cluster_operator_role.py docs/admin/commands.md docs/developer/superadmin.md docs/superpowers/plans/2026-08-31-cluster-operator-permissions-fix.md
git commit -m "fix: converge cluster administrator permissions"
```

Expected: one implementation commit containing the tested configuration, tests, documentation, and plan.
