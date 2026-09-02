# Unified Slurm Account Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one planner exclusively responsible for Slurm Account entities and cluster-level Account Associations.

**Architecture:** Extend the Account planner to compare both Account metadata and cluster-level Associations. Restrict the general Association planner to partition-scoped records, then make Ansible planning, convergence, and audit consume the separated plans directly.

**Tech Stack:** Python filter plugin, Ansible YAML, `sacctmgr`, Python `unittest`

---

### Task 1: Unify Account planning

**Files:**
- Modify: `tests/test_slurm_associations_role.py`
- Modify: `ansible/filter_plugins/slurm_associations.py`
- Modify: `ansible/roles/slurm_associations/tasks/plan.yml`
- Modify: `ansible/roles/slurm_associations/tasks/converge.yml`
- Modify: `ansible/roles/slurm_associations/tasks/audit.yml`

- [x] **Step 1: Write planner tests for all four Account states**

Add tests proving that a new Account produces only `add_accounts`, while an
existing Account without an `epic` Association produces only
`add_cluster_associations`. Also test the matching and Fairshare-update cases.

- [x] **Step 2: Run the focused tests and verify the new cases fail**

Run:

```powershell
python -m unittest tests.test_slurm_associations_role.SlurmAssociationPlannerTests -v
```

Expected: the new tests fail because the existing Account metadata planner
does not accept or classify Association rows.

- [x] **Step 3: Implement the unified Account plan**

Return four independent operation lists:

```python
{
    "add_accounts": [],
    "update_accounts": [],
    "add_cluster_associations": [],
    "update_cluster_associations": [],
}
```

Exclude global Account Associations from the partition Association planner.

- [x] **Step 4: Make Ansible consume the unified plan**

Pass current Association rows into the Account planner in `plan.yml` and
`audit.yml`. In `converge.yml`, loop directly over
`add_cluster_associations` and `update_cluster_associations`; remove the
cross-plan `when` condition.

- [x] **Step 5: Run focused and regression verification**

Run:

```powershell
python -m unittest tests.test_identity_conflicts tests.test_slurm_associations_role tests.test_slurm_role tests.test_slurmdbd_role -v
python -m py_compile ansible\filter_plugins\slurm_associations.py tests\test_slurm_associations_role.py
git diff --check
```

Expected: all tests pass, compilation succeeds, and the diff check reports no
whitespace errors.
