# Identity Manifest Conflicts Implementation Plan

> **For agentic workers:** Execute inline in the current workspace. Do not create commits. Use one targeted red-green test; deployment feedback drives later iterations.

**Goal:** Make the existing Ansible identity preflight report every duplicate UID and GID declared inside `users.yml` before convergence starts.

**Architecture:** Extend `identity_conflicts()` without changing its interface or the Ansible task chain. Build reverse indexes from desired users and desired private/access groups, append one stable aggregate message for each duplicate numeric ID, then retain the existing target-host NSS conflict checks.

**Tech Stack:** Python 3, Ansible filter plugin, `unittest`

---

### Task 1: Add manifest-internal conflict detection

**Files:**
- Modify: `tests/test_identity_conflicts.py`
- Modify: `ansible/filter_plugins/identity.py`

- [ ] **Step 1: Write the failing regression test**

Add a test that calls the real `identity_conflicts()` with empty NSS mappings and a manifest containing a duplicate UID, duplicate private-group GID, duplicate access-group GID, and a private/access cross-GID collision. Assert the exact ordered aggregate messages:

```python
def test_reports_all_manifest_numeric_id_conflicts(self) -> None:
    users = [
        {"name": "alice", "uid": 10000, "gid": 10000},
        {"name": "bob", "uid": 10000, "gid": 10001},
        {"name": "carol", "uid": 10002, "gid": 10001},
    ]
    access_groups = [
        {"name": "EPIC-RL", "gid": 20000},
        {"name": "CGCL", "gid": 20000},
        {"name": "shared-private", "gid": 10000},
    ]

    conflicts = identity_conflicts(users, access_groups, {}, {})

    self.assertEqual(
        conflicts,
        [
            "UID 10000 is assigned to multiple manifest users: alice, bob",
            "GID 10000 is assigned to multiple manifest groups: alice, shared-private",
            "GID 10001 is assigned to multiple manifest groups: bob, carol",
            "GID 20000 is assigned to multiple manifest groups: CGCL, EPIC-RL",
        ],
    )
```

- [ ] **Step 2: Run the single regression test and verify RED**

Run:

```text
conda run -n marl_stable python -m unittest discover -s tests -p test_identity_conflicts.py -k test_reports_all_manifest_numeric_id_conflicts -v
```

Expected: one failure because the current function returns `[]`.

- [ ] **Step 3: Implement the minimum filter change**

At the start of `identity_conflicts()`, build `desired_users_by_uid` from `cluster_users`. Build `desired_groups` once by combining user private groups with `access_groups`, then build `desired_groups_by_gid`. Iterate sorted numeric IDs, append one message only when the sorted set of names has length greater than one. Reuse `desired_groups` in the existing host-group loop and leave the remaining NSS checks unchanged.

- [ ] **Step 4: Run the single regression test and verify GREEN**

Run the command from Step 2.

Expected: one passing test.

- [ ] **Step 5: Inspect the final workspace diff**

Inspect the diff for the design document, plan, regression test, and filter change. Do not run broader tests. Leave every change uncommitted and unstaged.
