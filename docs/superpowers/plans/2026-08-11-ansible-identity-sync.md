# EPIC Ansible Identity Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an idempotent Ansible identity source of truth from the A100 account table, converge the controller first, and safely onboard the RTX 4070 node without copying OOD passwords or A100 SSH keys.

**Architecture:** The controller runs Ansible against itself and compute nodes over the existing `administrator` SSH path. `ansible/vars/users.yml` becomes authoritative after migration; a preflight phase reads complete passwd/group databases and rejects every name/number conflict before any account task runs. The identity role creates groups, users, homes, locked passwords, and exact project-group membership; SSH key and OOD roles remain separate future modules.

**Tech Stack:** Ansible Core built-in modules, YAML, Python 3 validation script, OpenSSH, Ubuntu `addgroup` for the legacy `3dv` group name.

---

### Task 1: Validate the authoritative identity manifest

**Files:**
- Create: `tests/validate_identity_manifest.py`
- Create: `ansible/vars/users.yml`

- [ ] **Step 1: Write the failing manifest validation test**

Create a Python validator that loads `ansible/vars/users.yml`, rejects duplicate names/UIDs/GIDs, requires every user to have a matching private group, verifies project-group members exist, restricts `ssh_access` to `controller`, `a100`, and `rtx4070`, and checks the known migration anchors `liuhongbo=10000`, `huodongkun=10004`, `wanghao=13007`, and `3dv=20003`.

- [ ] **Step 2: Run the validator and confirm it fails**

Run:

```bash
python tests/validate_identity_manifest.py ansible/vars/users.yml
```

Expected: non-zero exit because the manifest does not exist.

- [ ] **Step 3: Add the complete A100-derived manifest**

Create `users.yml` with all UID 10000–19999 users from the captured A100 `getent passwd`, all same-name private groups, the five project groups with their exact captured members, original shells, and explicit SSH access. Grant controller access to every user; record A100 and RTX 4070 access separately without importing existing A100 `authorized_keys`.

- [ ] **Step 4: Run the validator and confirm it passes**

Run:

```bash
python tests/validate_identity_manifest.py ansible/vars/users.yml
```

Expected: `identity manifest valid` and exit 0.

- [ ] **Step 5: Commit the manifest and validator**

```bash
git add tests/validate_identity_manifest.py ansible/vars/users.yml
git commit -m "feat: add authoritative identity manifest"
```

### Task 2: Add inventory and Ansible runtime configuration

**Files:**
- Create: `ansible/ansible.cfg`
- Create: `ansible/inventory/hosts.yml`
- Create: `ansible/playbooks/users.yml`
- Create: `ansible/playbooks/site.yml`

- [ ] **Step 1: Add the three-host inventory**

Define `controllers`, `controlled_compute_nodes`, `free_compute_nodes`, and aggregate `compute_nodes`. Use local connection for `epic-cluster-controller-01`, `172.16.3.165` for A100, `192.168.77.11` for RTX 4070, and `administrator` with privilege escalation for all hosts.

- [ ] **Step 2: Add project-local Ansible defaults**

Point Ansible at `inventory/hosts.yml` and `roles`, retain host-key checking, disable retry files, and use automatic Python interpreter discovery.

- [ ] **Step 3: Add identity and site entry points**

`playbooks/users.yml` must load `../vars/users.yml` and apply only the `identity` role. `playbooks/site.yml` imports `users.yml` and contains comments reserving Slurm, SSH access, and OOD imports without invoking nonexistent roles.

- [ ] **Step 4: Run static Ansible checks**

Run on the controller after copying the repository:

```bash
cd /srv/epic/repos/EPIC-Slurm-Cluster/ansible
ansible-inventory --graph
ansible-playbook playbooks/users.yml --syntax-check
```

Expected: all three hosts appear and syntax check succeeds.

- [ ] **Step 5: Commit the runtime scaffold**

```bash
git add ansible/ansible.cfg ansible/inventory/hosts.yml ansible/playbooks
git commit -m "feat: scaffold ansible identity runtime"
```

### Task 3: Reject identity conflicts before mutation

**Files:**
- Create: `ansible/roles/identity/tasks/preflight.yml`
- Create: `ansible/roles/identity/tasks/main.yml`

- [ ] **Step 1: Gather complete passwd and group databases**

Use `ansible.builtin.getent` for `passwd` and `group`, then construct reverse UID and GID maps from returned facts.

- [ ] **Step 2: Assert all desired names and numbers are compatible**

Before importing convergence tasks, assert for every user and group that an existing name has the expected numeric ID and that an expected numeric ID is either unused or owned by the expected name. Assertion messages must include host, actual owner, expected owner, and numeric ID.

- [ ] **Step 3: Prove the RTX 4070 conflict is caught safely**

Run:

```bash
ansible-playbook playbooks/users.yml \
  --limit epic-cluster-compute-rtx4070-01 \
  --check --diff
```

Expected while `huodongkun` remains UID/GID 1011: play fails in preflight with expected UID/GID 10004, and no later identity task runs.

- [ ] **Step 4: Commit conflict preflight**

```bash
git add ansible/roles/identity/tasks
git commit -m "feat: reject ansible identity conflicts"
```

### Task 4: Converge users and groups idempotently

**Files:**
- Create: `ansible/roles/identity/tasks/converge.yml`
- Modify: `ansible/roles/identity/tasks/main.yml`

- [ ] **Step 1: Create private groups and regular project groups**

Use `ansible.builtin.group` for same-name private groups and project groups other than `3dv`. Preserve explicit GIDs from the manifest.

- [ ] **Step 2: Handle the legacy `3dv` group name explicitly**

After preflight, run Ubuntu `addgroup --gid 20003 --allow-bad-names 3dv` only when `3dv` is absent. Do not call unsupported `groupadd --force-badname`.

- [ ] **Step 3: Create or normalize ordinary users**

Use `ansible.builtin.user` with exact UID, primary group, home, shell, `create_home: true`, and `password_lock: true`. Do not delete users, recursively chown homes, copy shadow hashes, or manage administrator through this list.

- [ ] **Step 4: Converge only the five project-group member lists**

Compare sorted current and desired members and invoke `gpasswd --members` only when they differ. Do not replace unrelated supplementary groups such as `sudo` or `docker`.

- [ ] **Step 5: Verify controller convergence and idempotence**

Run:

```bash
ansible-playbook playbooks/users.yml \
  --limit epic-cluster-controller-01 \
  --check --diff
ansible-playbook playbooks/users.yml \
  --limit epic-cluster-controller-01
ansible-playbook playbooks/users.yml \
  --limit epic-cluster-controller-01
```

Expected: first real run succeeds; second real run reports `changed=0`.

- [ ] **Step 6: Commit convergence logic**

```bash
git add ansible/roles/identity/tasks
git commit -m "feat: converge cluster identities"
```

### Task 5: Onboard and verify the RTX 4070 as a new host

**Files:**
- Create: `ansible/playbooks/verify_identity.yml`

- [ ] **Step 1: Add read-only identity verification**

Create a playbook that reruns the same passwd/group facts and manifest comparisons without mutation and reports a clear success message per host.

- [ ] **Step 2: Complete the deferred live UID migration**

After `huodongkun` has no processes on RTX 4070, follow the already approved manual migration from UID/GID 1011 to 10004 and repair old numeric ownership on each local filesystem. This remains manual because the preflight role must never renumber a live account.

- [ ] **Step 3: Apply identity convergence to RTX 4070**

```bash
ansible epic-cluster-compute-rtx4070-01 -m ping
ansible-playbook playbooks/users.yml \
  --limit epic-cluster-compute-rtx4070-01 \
  --check --diff
ansible-playbook playbooks/users.yml \
  --limit epic-cluster-compute-rtx4070-01
ansible-playbook playbooks/users.yml \
  --limit epic-cluster-compute-rtx4070-01
```

Expected: ping succeeds; check mode reports only intended changes; first apply succeeds; second apply reports `changed=0`.

- [ ] **Step 4: Verify both managed targets**

```bash
ansible-playbook playbooks/verify_identity.yml \
  --limit epic-cluster-controller-01,epic-cluster-compute-rtx4070-01
```

Expected: both hosts report identity manifest consistency. No OOD password, `/etc/shadow` export, or A100 key archive is touched.

- [ ] **Step 5: Commit verification playbook**

```bash
git add ansible/playbooks/verify_identity.yml
git commit -m "test: verify synchronized identities"
```

### Task 6: Document routine operation and future modules

**Files:**
- Create: `docs/ansible_identity.md`
- Modify: `docs/admin_doc.md`

- [ ] **Step 1: Document installation and first run**

Record controller package installation, repository path `/srv/epic/repos/EPIC-Slurm-Cluster`, inventory ping, check-mode workflow, controller-first application, RTX 4070 onboarding, offline-node recovery with `--limit`, and conflict remediation boundaries.

- [ ] **Step 2: Document source-of-truth and manual-change rules**

State that A100 is only the migration source, `users.yml` is authoritative afterward, emergency manual edits must be reflected in Git, and OOD passwords plus A100 legacy keys are outside this role.

- [ ] **Step 3: Document extension points**

Explain that later `ssh_access`, `slurm`, `ood_controller`, `ood_compute`, and `ood_apps` roles plug into `site.yml` without changing identity convergence.

- [ ] **Step 4: Run final repository checks**

```bash
python tests/validate_identity_manifest.py ansible/vars/users.yml
git diff --check
git status --short
```

Expected: validator passes, diff check is clean, and only intended implementation files are modified.

- [ ] **Step 5: Commit operations documentation**

```bash
git add docs/ansible_identity.md docs/admin_doc.md
git commit -m "docs: explain ansible identity operations"
```
