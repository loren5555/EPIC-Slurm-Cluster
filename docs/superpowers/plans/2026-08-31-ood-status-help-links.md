# OOD Status Help Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add direct cluster health, resource overview, exporter target, and Slurm reason-code links to the existing OOD Help menu.

**Architecture:** Extend only the native `help_menu` list in the existing dashboard template. Reuse stable Grafana dashboard UIDs and link Prometheus directly to `/targets`; do not expose individual exporter metric endpoints.

**Tech Stack:** Open OnDemand 4.2 dashboard YAML, Ansible Jinja

---

### Task 1: Add live status and scheduler diagnosis links

**Files:**

- Modify: `ansible/roles/ood_controller/templates/ondemand.yml.j2:4-31`

- [ ] **Step 1: Insert the status group before the existing EPIC group**

Add these entries immediately below `help_menu:`:

```yaml
  - group: "集群状态"
  - title: "集群状态（Grafana）"
    icon: "fas://heartbeat"
    url: "http://epic-cluster-controller-01:3000/d/epic-cluster-availability"
    new_tab: true
  - title: "资源使用概览（Grafana）"
    icon: "fas://chart-line"
    url: "http://epic-cluster-controller-01:3000/d/epic-cluster-overview"
    new_tab: true
  - title: "Exporter 状态（Prometheus）"
    icon: "fas://signal"
    url: "http://epic-cluster-controller-01:9090/targets"
    new_tab: true
```

- [ ] **Step 2: Add the Slurm reason-code link after the general Slurm documentation**

Add:

```yaml
  - title: "Slurm 排队与失败原因"
    icon: "fas://info-circle"
    url: "https://slurm.schedmd.com/job_reason_codes.html"
    new_tab: true
```

- [ ] **Step 3: Parse the static Help menu portion as YAML**

Run:

```powershell
conda run -n marl_stable python -c "from pathlib import Path; import yaml; text=Path('ansible/roles/ood_controller/templates/ondemand.yml.j2').read_text(encoding='utf-8'); data=yaml.safe_load(text.split('# Keep every EPIC-managed application')[0]); links=[item for item in data['help_menu'] if 'url' in item]; assert len(data['help_menu'])==13; assert len(links)==10; assert all(item['new_tab'] is True for item in links); print('Help menu YAML parse OK: 3 groups, 10 links')"
```

Expected: `Help menu YAML parse OK: 3 groups, 10 links`.

- [ ] **Step 4: Inspect the focused diff and leave it uncommitted**

Run:

```powershell
git diff --check
git diff -- ansible/roles/ood_controller/templates/ondemand.yml.j2
git status --short
```

Expected: no whitespace errors; the template contains exactly the four approved links. Do not run tests, commit implementation changes, or deploy Ansible.
