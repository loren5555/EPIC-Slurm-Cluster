# SlurmDBD Manual Installation Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make MariaDB and SlurmDBD package installation an explicit manual controller operation while Ansible manages only configuration, database initialization, services, and verification.

**Architecture:** The deployment guide owns package-source inspection and manual APT installation. The existing `slurmdbd` role starts after packages exist and remains independent of host-specific repository or package decisions.

**Tech Stack:** Ansible, Ubuntu APT, MariaDB, SlurmDBD 25.11, Python unittest

---

### Task 1: Protect the manual-install boundary

**Files:**
- Modify: `tests/test_slurmdbd_role.py`

- [x] Add a contract test that reads every SlurmDBD role file and rejects `ansible.builtin.apt`, `ansible.builtin.package`, `apt-get`, and `apt install`.
- [x] Run `python -m unittest tests.test_slurmdbd_role -v` and confirm the new test fails because `tasks/main.yml` still contains `ansible.builtin.apt`.

### Task 2: Remove package management from the role

**Files:**
- Modify: `ansible/roles/slurmdbd/tasks/main.yml`

- [x] Delete the task named `Install MariaDB and the matching SlurmDBD package` without adding a replacement package check.
- [x] Keep the first configuration task as the MariaDB template deployment; missing manually installed packages may fail naturally at configuration or service activation.
- [x] Run `python -m unittest tests.test_slurmdbd_role -v` and confirm all SlurmDBD role tests pass.

### Task 3: Verify the complete work-package contract

**Files:**
- Verify: `docs/slurm-stack-deployment-guide.md`
- Verify: `ansible/roles/slurmdbd/`
- Verify: `tests/test_slurm_role.py`
- Verify: `tests/test_slurmdbd_role.py`

- [x] Run `python -m unittest tests.test_slurm_role tests.test_slurmdbd_role -v` and confirm all work-package tests pass.
- [x] Run `git diff --check` and confirm there are no whitespace errors.
- [x] Confirm the guide contains manual `apt-cache policy`, simulated installation, formal installation, and `slurmdbd -V`, while the Ansible role contains no package-management action.
