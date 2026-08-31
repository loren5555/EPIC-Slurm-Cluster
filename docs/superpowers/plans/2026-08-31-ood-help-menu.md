# OOD Help Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add EPIC, upstream documentation, repository, and issue links to the native Open OnDemand Help drop-down menu.

**Architecture:** Extend the existing OOD 4.2 dashboard configuration template with a literal `help_menu` list. Keep the current deployment task and PUN restart handler unchanged because they already publish and activate `ondemand.d/epic.yml`.

**Tech Stack:** Ansible Jinja/YAML, Open OnDemand 4.2 dashboard configuration, Python `unittest`

---

### Task 1: Define the Help menu contract

**Files:**

- Modify: `tests/test_ood_roles.py:85-166`
- Test: `tests/test_ood_roles.py`

- [ ] **Step 1: Add a focused failing contract test**

Add this method to `OODRoleTests` after `test_controller_configuration`:

```python
def test_dashboard_help_menu_exposes_documentation_and_support_links(self) -> None:
    dashboard = read_ansible_file("roles/ood_controller/templates/ondemand.yml.j2")

    self.assertIn("help_menu:", dashboard)
    for group in ("EPIC 集群", "参考与支持"):
        self.assertIn(f'group: "{group}"', dashboard)

    links = {
        "集群文档": "https://loren5555.github.io/EPIC-Slurm-Cluster/",
        "GitHub 仓库": "https://github.com/loren5555/EPIC-Slurm-Cluster",
        "Slurm 官方文档": "https://slurm.schedmd.com/",
        "Open OnDemand 官方文档": "https://osc.github.io/ood-documentation/latest",
        "查看 GitHub Issues": "https://github.com/loren5555/EPIC-Slurm-Cluster/issues",
        "提交问题": "https://github.com/loren5555/EPIC-Slurm-Cluster/issues/new/choose",
    }
    for title, url in links.items():
        with self.subTest(title=title):
            self.assertIn(f'title: "{title}"', dashboard)
            self.assertIn(f'url: "{url}"', dashboard)

    self.assertEqual(dashboard.count("new_tab: true"), len(links))
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m unittest tests.test_ood_roles.OODRoleTests.test_dashboard_help_menu_exposes_documentation_and_support_links -v
```

Expected: FAIL because `ondemand.yml.j2` does not contain `help_menu`.

### Task 2: Add the native OOD Help menu configuration

**Files:**

- Modify: `ansible/roles/ood_controller/templates/ondemand.yml.j2:2-3`
- Test: `tests/test_ood_roles.py`

- [ ] **Step 1: Add the two Help menu groups and six links**

Insert after `dashboard_title`:

```yaml
help_menu:
  - group: "EPIC 集群"
  - title: "集群文档"
    icon: "fas://book"
    url: "https://loren5555.github.io/EPIC-Slurm-Cluster/"
    new_tab: true
  - title: "GitHub 仓库"
    icon: "fab://github"
    url: "https://github.com/loren5555/EPIC-Slurm-Cluster"
    new_tab: true
  - group: "参考与支持"
  - title: "Slurm 官方文档"
    icon: "fas://book"
    url: "https://slurm.schedmd.com/"
    new_tab: true
  - title: "Open OnDemand 官方文档"
    icon: "fas://book"
    url: "https://osc.github.io/ood-documentation/latest"
    new_tab: true
  - title: "查看 GitHub Issues"
    icon: "fab://github"
    url: "https://github.com/loren5555/EPIC-Slurm-Cluster/issues"
    new_tab: true
  - title: "提交问题"
    icon: "fas://bug"
    url: "https://github.com/loren5555/EPIC-Slurm-Cluster/issues/new/choose"
    new_tab: true
```

- [ ] **Step 2: Run the focused Help menu test and verify GREEN**

Run:

```powershell
python -m unittest tests.test_ood_roles.OODRoleTests.test_dashboard_help_menu_exposes_documentation_and_support_links -v
```

Expected: PASS.

- [ ] **Step 3: Run the existing OOD controller contract**

Run:

```powershell
python -m unittest tests.test_ood_roles.OODRoleTests.test_controller_configuration -v
```

Expected: PASS, confirming the new menu did not remove existing dashboard behavior.

### Task 3: Verify and hand off the local change

**Files:**

- Verify: `ansible/roles/ood_controller/templates/ondemand.yml.j2`
- Verify: `tests/test_ood_roles.py`
- Verify: `docs/superpowers/plans/2026-08-31-ood-help-menu.md`

- [ ] **Step 1: Run all OOD role tests**

Run:

```powershell
python -m unittest discover -s tests -p test_ood_roles.py -v
```

Expected: the new Help menu test and existing passing OOD contracts pass. Record any unrelated pre-existing failures without changing their files.

- [ ] **Step 2: Check whitespace and inspect the focused diff**

Run:

```powershell
git diff --check
git diff -- ansible/roles/ood_controller/templates/ondemand.yml.j2 tests/test_ood_roles.py
```

Expected: no whitespace errors, and the production diff contains only the native Help menu configuration.

- [ ] **Step 3: Leave implementation changes uncommitted for operator deployment**

Run:

```powershell
git status --short
```

Expected: the dashboard template, test, and this implementation plan remain available in the current workspace. Do not run Ansible or modify the controller.
