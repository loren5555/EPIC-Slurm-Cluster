# Add Node Checklist Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a superadministrator add-node checklist and number developer document filenames in sidebar order.

**Architecture:** Keep the checklist as a focused developer child page and link to repository sources of truth for detailed configuration. Rename the existing child pages without changing their titles or `nav_order`, then update every live link and documentation structure contract to the numbered paths.

**Tech Stack:** Markdown, Just the Docs front matter, Python `unittest` documentation contracts

---

### Task 1: Number the existing developer documents

**Files:**
- Rename: `docs/developer/repository.md` to `docs/developer/01-repository.md`
- Rename: `docs/developer/ansible.md` to `docs/developer/02-ansible.md`
- Rename: `docs/developer/apps.md` to `docs/developer/03-apps.md`
- Rename: `docs/developer/documentation.md` to `docs/developer/04-documentation.md`
- Rename: `docs/developer/operations.md` to `docs/developer/05-operations.md`
- Rename: `docs/developer/superadmin.md` to `docs/developer/06-superadmin.md`

- [x] **Step 1: Rename the six pages in `nav_order` order**

Preserve each page's front matter, title, body, and `nav_order`; only its path changes.

- [x] **Step 2: Keep the numbered path-to-order mapping explicit**

The filename prefix and `nav_order` must match for all six pages.

### Task 2: Add the superadministrator checklist

**Files:**
- Create: `docs/developer/07-add-node-checklist.md`
- Modify: `docs/developer/02-ansible.md`
- Modify: `docs/developer/06-superadmin.md`

- [x] **Step 1: Create the checklist page**

Use front matter title `新增节点 Checklist`, parent `开发者文档`, and `nav_order: 7`.
Include checkboxes for change planning, host preparation, inventory and host vars,
Slurm data, identity/storage, monitoring/OOD, staged deployment, CPU/GPU acceptance,
rollback, and handoff.

- [x] **Step 2: Link the checklist from the superadministrator page**

Add a short `新增节点` section that identifies the checklist as the required
operational reference before a host is admitted to the cluster.

- [x] **Step 3: Replace the Ansible page's one-line onboarding summary**

Keep the architectural summary concise and link to `07-add-node-checklist.md` for
the executable procedure and to `06-superadmin.md` for installation boundaries.

### Task 3: Update navigation and all live references

**Files:**
- Modify: `docs/developer/index.md`
- Modify: `docs/developer/05-operations.md`
- Modify: `docs/index.md`

- [x] **Step 1: List all seven developer pages in numbered sidebar order**

Use `01-` through `07-` paths and keep descriptions brief.

- [x] **Step 2: Update cross-page links**

Replace old developer filenames with their numbered equivalents, including links
from the operations page and the public documentation index.

### Task 4: Update documentation contracts

**Files:**
- Modify: `tests/test_documentation_structure.py`

- [x] **Step 1: Replace old developer paths with numbered paths**

Update `expected_pages` and `test_reader_pages_exist` to use the six renamed paths.

- [x] **Step 2: Add the checklist contract**

Require `docs/developer/07-add-node-checklist.md` with title `新增节点 Checklist`,
parent `开发者文档`, and `nav_order` `7`.

- [x] **Step 3: Respect the requested verification boundary**

Do not run tests or a site build. Report that verification was intentionally not
run at the user's request.
