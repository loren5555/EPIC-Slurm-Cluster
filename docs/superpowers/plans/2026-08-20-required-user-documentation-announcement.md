# OOD Required User Documentation Announcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require each OOD user to accept a first-login announcement linking to the EPIC user documentation before using the portal.

**Architecture:** Add one native Open OnDemand 4.2 required-announcement template and install it through the existing `ood_controller` role. Extend the existing role contract test with only the fields that make the gate effective. Keep all changes uncommitted.

**Tech Stack:** Ansible, Jinja2/YAML, Python `unittest`

---

### Task 1: Define the required announcement contract

**Files:**
- Modify: `tests/test_ood_roles.py`
- Create: `ansible/roles/ood_controller/templates/announcement-required-docs.yml.j2`

- [ ] **Step 1: Extend the existing OOD role test**

Read `announcement-required-docs.yml.j2` alongside the other announcement templates and assert that it contains:

```python
self.assertIn("required: true", required_docs)
self.assertIn("dismissible: true", required_docs)
self.assertIn("button_text: 我已阅读，开始使用", required_docs)
self.assertIn("https://loren5555.github.io/EPIC-Slurm-Cluster/user/", required_docs)
```

Also include `required_docs` in the common announcement schema loop that checks `id:`, `type:`, `msg: |`, and absence of `content: |`.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```powershell
python -m unittest tests.test_ood_roles.OODRoleTests.test_controller_configuration
```

Expected: failure because `announcement-required-docs.yml.j2` does not exist.

- [ ] **Step 3: Add the announcement template**

Create the template with a stable acceptance identifier:

```yaml
---
id: epic-user-documentation-v1
type: info
required: true
dismissible: true
button_text: 我已阅读，开始使用
msg: |
  ### 使用 EPIC 集群前请先阅读用户文档

  请阅读 [EPIC 集群用户文档](https://loren5555.github.io/EPIC-Slurm-Cluster/user/)，了解登录、提交任务、资源申请、排队规则、存储与常见问题。

  确认已阅读后，才能继续使用 Open OnDemand。
```

Do not commit.

### Task 2: Deploy the required announcement

**Files:**
- Modify: `ansible/roles/ood_controller/tasks/main.yml`
- Modify: `tests/test_ood_roles.py`

- [ ] **Step 1: Add the deployment assertion**

Assert the role task content references both the template and destination:

```python
self.assertIn("src: announcement-required-docs.yml.j2", tasks)
self.assertIn("announcements.d/epic-user-documentation.yml", tasks)
```

- [ ] **Step 2: Install the template from the role**

Add a task next to the existing announcement tasks:

```yaml
- name: Install the required EPIC user documentation announcement
  ansible.builtin.template:
    src: announcement-required-docs.yml.j2
    dest: "{{ ood_configuration_directory }}/announcements.d/epic-user-documentation.yml"
    owner: root
    group: root
    mode: "0644"
  notify: Restart all user PUNs
```

- [ ] **Step 3: Run only the focused test**

Run:

```powershell
python -m unittest tests.test_ood_roles.OODRoleTests.test_controller_configuration
```

Expected: one test passes.

- [ ] **Step 4: Check the touched files**

Run:

```powershell
git diff --check -- ansible/roles/ood_controller/tasks/main.yml ansible/roles/ood_controller/templates/announcement-required-docs.yml.j2 tests/test_ood_roles.py docs/superpowers/specs/2026-08-20-required-user-documentation-announcement-design.md docs/superpowers/plans/2026-08-20-required-user-documentation-announcement.md
```

Expected: no output. Leave every change uncommitted.
