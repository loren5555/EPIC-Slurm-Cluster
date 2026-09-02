# Prometheus and Exporters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure Prometheus, node_exporter, DCGM Exporter, nvitop-exporter, and Slurm OpenMetrics for the current EPIC cluster while keeping software installation manual.

**Architecture:** Ansible configures only software that an administrator has already installed. Exporters are configured before the controller Prometheus service; Prometheus targets are generated from stable inventory hostnames, and monitoring has no reverse dependency into Slurm or GPU services.

**Tech Stack:** Ansible, systemd, current stable Prometheus, node_exporter and nvitop-exporter releases, NVIDIA DCGM Exporter, Slurm 25.11 OpenMetrics, Python `unittest` contract tests.

---

### Task 1: Define the monitoring contract

**Files:**
- Create: `tests/test_monitoring_roles.py`
- Modify: `tests/test_slurm_role.py`

- [x] **Step 1: Write failing tests**

Add contract tests for the explicit `gpu_nodes` inventory group, scrape intervals, retention limits, systemd units, inventory-derived targets, absence of package installation, playbook ordering, and Slurm OpenMetrics settings.

- [x] **Step 2: Confirm the tests fail for missing work-package files**

Run: `python -m unittest tests.test_monitoring_roles tests.test_slurm_role -v`

Expected: monitoring tests fail because the monitoring variables, roles, templates, and playbook do not yet exist.

### Task 2: Enable Slurm OpenMetrics

**Files:**
- Modify: `ansible/roles/slurm/templates/slurm.conf.j2`

- [x] **Step 1: Add the bounded internal metrics configuration**

Add:

```ini
MetricsType=metrics/openmetrics
```

- [x] **Step 2: Run the Slurm role tests**

Run: `python -m unittest tests.test_slurm_role -v`

Expected: all Slurm role tests pass.

### Task 3: Configure exporters on managed hosts

**Files:**
- Modify: `ansible/inventory/hosts.yml`
- Create: `ansible/inventory/group_vars/all/monitoring.yml`
- Create: `ansible/roles/monitoring_node_exporter/tasks/main.yml`
- Create: `ansible/roles/monitoring_node_exporter/handlers/main.yml`
- Create: `ansible/roles/monitoring_node_exporter/templates/node_exporter.service.j2`
- Create: `ansible/roles/monitoring_gpu_exporters/tasks/main.yml`
- Create: `ansible/roles/monitoring_gpu_exporters/handlers/main.yml`
- Create: `ansible/roles/monitoring_gpu_exporters/templates/nvitop-exporter.service.j2`
- Create: `ansible/roles/monitoring_gpu_exporters/templates/dcgm-exporter-config.yaml.j2`
- Create: `ansible/roles/monitoring_gpu_exporters/templates/nvidia-dcgm-exporter.service.j2`

- [x] **Step 1: Declare stable hosts and sampling policy**

Declare the two present GPU hosts explicitly and set fast scrapes to `10s`, Slurm state scrapes to `2m`, scheduler scrapes to `5m`, self-scrapes to `30s`, retention to `90d`, and size retention to `100GB`.

- [x] **Step 2: Configure node_exporter without installing it**

Require `/usr/local/bin/node_exporter`, create its service account and textfile directory, install a readable systemd unit, enable it, and verify its local endpoint.

- [x] **Step 3: Configure GPU exporters without changing drivers**

Require `/opt/nvitop-exporter/bin/nvitop-exporter`. Run nvitop-exporter as root and use an Ansible-owned systemd service to launch the manually loaded DCGM Exporter image through rootful Docker. Mount the `10000` millisecond collection policy, enable both services, and verify both local endpoints.

- [x] **Step 4: Run exporter contract tests**

Run: `python -m unittest tests.test_monitoring_roles -v`

Expected: exporter-related tests pass; Prometheus-related tests still fail until Task 4.

### Task 4: Configure Prometheus and orchestration

**Files:**
- Create: `ansible/roles/monitoring_prometheus/tasks/main.yml`
- Create: `ansible/roles/monitoring_prometheus/handlers/main.yml`
- Create: `ansible/roles/monitoring_prometheus/templates/prometheus.yml.j2`
- Create: `ansible/roles/monitoring_prometheus/templates/prometheus.service.j2`
- Create: `ansible/playbooks/monitoring.yml`
- Modify: `ansible/playbooks/site.yml`

- [x] **Step 1: Render inventory-based scrape targets**

Generate separate jobs for Prometheus, node_exporter, DCGM, nvitop, Slurm jobs, nodes, partitions, and scheduler. Do not collect `/metrics/jobs-users-accts`.

- [x] **Step 2: Configure the local TSDB service**

Require the two installed binaries, create the service account and standard directories, validate the rendered configuration with `promtool`, and start Prometheus with `90d` and `100GB` retention.

- [x] **Step 3: Add the monitoring playbook after Slurm in the full entry point**

Order the plays as all-host node exporter, GPU exporters, then controller Prometheus. Add `monitoring.yml` after `slurm.yml` in `site.yml`.

- [x] **Step 4: Run all contract tests**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass.

### Task 5: Write the complete operator procedure

**Files:**
- Modify: `docs/superpowers/specs/2026-08-17-prometheus-exporters-design.md`
- Modify: `docs/slurm-stack-deployment-guide.md`

- [x] **Step 1: Define the clean-install release policy**

Delete obsolete monitoring software and data, then resolve current stable releases at installation time instead of retaining version pins.

- [x] **Step 2: Replace work package 6 with an executable procedure**

Document legacy-service removal, manual binary and container-image preparation per host class, Ansible preview and apply, endpoint checks, Prometheus target checks, idempotence, expected results, and stopping conditions. Explain the purpose and expected outcome of each deployment phase.

- [x] **Step 3: Verify documentation and repository state**

Run:

```bash
python -m unittest discover -s tests -v
git diff --check
```

Expected: all tests pass and `git diff --check` prints no errors.
