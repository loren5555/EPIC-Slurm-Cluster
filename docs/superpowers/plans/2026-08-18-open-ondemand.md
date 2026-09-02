# EPIC Open OnDemand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy Open OnDemand 4.2 on the controller with Ansible-managed configuration, shared Batch Connect context, SFTP Remote Files, the existing EPIC applications, Job Composer templates, and OOD Prometheus metrics.

**Architecture:** Software is installed manually and configured by three focused Ansible roles. The controller exports only `/srv/epic/ood`; compute nodes mount it on demand, while rclone/SFTP exposes their otherwise independent Home directories. Existing Slurm and identity manifests generate OOD host menus and per-user remote access.

**Tech Stack:** Open OnDemand 4.2, Apache, Slurm 25.11, Ansible, NFS, rclone/SFTP, systemd, ondemand_exporter, ERB/YAML, Python unittest contract tests.

---

### Task 1: Define the OOD configuration contract

**Files:**
- Create: `tests/test_ood_roles.py`
- Create: `ansible/inventory/group_vars/all/ood.yml`
- Create: `ansible/playbooks/ood.yml`
- Modify: `ansible/playbooks/site.yml`

- [ ] **Step 1: Write failing tests for the declared files and policy**

Test that the three roles, controller IP variable, 32-hour limit, shared root,
exporter port, manual-install boundary, and final `site.yml` import exist.

- [ ] **Step 2: Run the focused test and observe the missing-file failure**

Run: `python -m unittest tests.test_ood_roles -v`
Expected: FAIL because the OOD variables, playbook, and roles do not exist.

- [ ] **Step 3: Add the variables and ordered playbook**

Declare `ood_server_address: 10.17.207.105`, `/srv/epic/ood`, 32 hours, 30-day
cleanup, port 9301, application names, and stable paths. Run controller roles
before compute mounts, and import `ood.yml` after monitoring in `site.yml`.

- [ ] **Step 4: Re-run the focused tests**

Run: `python -m unittest tests.test_ood_roles -v`
Expected: remaining failures move to the not-yet-created role files.

### Task 2: Configure the OOD controller and shared context

**Files:**
- Create: `ansible/roles/ood_controller/tasks/main.yml`
- Create: `ansible/roles/ood_controller/handlers/main.yml`
- Create: `ansible/roles/ood_controller/templates/ood_portal.yml.j2`
- Create: `ansible/roles/ood_controller/templates/epic.yml.j2`
- Create: `ansible/roles/ood_controller/templates/ondemand.yml.j2`
- Create: `ansible/roles/ood_controller/templates/dashboard.env.j2`
- Create: `ansible/roles/ood_controller/templates/myjobs.env.j2`
- Create: `ansible/roles/ood_controller/templates/epic-ood.exports.j2`
- Create: `ansible/roles/ood_controller/templates/openssl.cnf.j2`
- Create: `ansible/roles/ood_controller/templates/ondemand_exporter.service.j2`

- [ ] **Step 1: Extend the failing tests with controller invariants**

Require Basic Auth at `/etc/ood/auth/htpasswd`, IP-SAN TLS, local Slurm adapter,
restricted reverse-proxy host regex, explicit `$USER` dataroots, Remote Files,
disabled shell entry points, NFS export, and the exporter service.

- [ ] **Step 2: Observe the controller tests fail**

Run: `python -m unittest tests.test_ood_roles.OODRoleTests.test_controller_configuration -v`
Expected: FAIL because controller templates are absent.

- [ ] **Step 3: Implement the minimal controller role**

The role creates the
shared per-user roots, creates an empty htpasswd file only when missing,
generates the self-signed certificate when its IP configuration changes,
installs OOD/Apache/NFS/exporter configuration, runs `update_ood_portal`, and
restarts only the affected services through handlers.

- [ ] **Step 4: Re-run the controller tests**

Run: `python -m unittest tests.test_ood_roles.OODRoleTests.test_controller_configuration -v`
Expected: PASS.

### Task 3: Configure compute-node context mounts

**Files:**
- Create: `ansible/roles/ood_compute/tasks/main.yml`
- Create: `ansible/roles/ood_compute/templates/srv-epic-ood.automount.j2`
- Create: `ansible/roles/ood_compute/templates/srv-epic-ood.mount.j2`

- [ ] **Step 1: Add a failing automount contract test**

Require a systemd automount, `nofail`, `_netdev`, the stable controller
hostname, and no package-install tasks or `soft` NFS option.

- [ ] **Step 2: Observe the missing templates fail the test**

Run: `python -m unittest tests.test_ood_roles.OODRoleTests.test_compute_context_uses_automount -v`
Expected: FAIL.

- [ ] **Step 3: Implement the mount role**

Create `/srv/epic/ood`, install the `.mount` and `.automount` units, reload
systemd, and enable/start only the automount unit.

- [ ] **Step 4: Re-run the automount test**

Run: `python -m unittest tests.test_ood_roles.OODRoleTests.test_compute_context_uses_automount -v`
Expected: PASS.

### Task 4: Generate partition menus and Remote Files configuration

**Files:**
- Create: `ansible/roles/ood_apps/tasks/main.yml`
- Create: `ansible/roles/ood_apps/templates/partitions.yml.j2`
- Create: `ansible/roles/ood_apps/templates/rclone-remotes.ini.j2`
- Modify: `ansible/inventory/host_vars/epic-cluster-compute-a100-01.yml`
- Modify: `ansible/inventory/host_vars/epic-cluster-compute-rtx4070-01.yml`

- [ ] **Step 1: Add failing generation tests**

Require friendly labels, hardware-derived maxima, complete partition names,
per-user authorization derived from Account/user declarations, and rclone SFTP
sections derived only from `ssh_access` using the existing cluster key.

- [ ] **Step 2: Observe the generation tests fail**

Run: `python -m unittest tests.test_ood_roles.OODRoleTests.test_generated_user_interfaces_follow_authoritative_manifests -v`
Expected: FAIL.

- [ ] **Step 3: Implement the templates and deployment tasks**

Render the site partition file on the controller. Create each user's rclone
configuration directory and maintain one marked block containing only that
user's authorized compute hosts. Preserve unrelated rclone remotes.

- [ ] **Step 4: Re-run the generation test**

Run: `python -m unittest tests.test_ood_roles.OODRoleTests.test_generated_user_interfaces_follow_authoritative_manifests -v`
Expected: PASS.

### Task 5: Normalize and publish the EPIC applications

**Files:**
- Modify: `apps/IAPP_jupyter/**`
- Modify: `apps/IAPP_codeserver/**`
- Modify: `apps/IAPP_ttyd/**`
- Modify: `apps/IAPP_tensorboard/**`
- Modify: `apps/IAPP_script/**`
- Modify: `apps/LINK_grafana/manifest.yml`
- Create: `ansible/roles/ood_apps/files/job_templates/basic/manifest.yml`
- Create: `ansible/roles/ood_apps/files/job_templates/basic/job.sh`
- Create: `ansible/roles/ood_apps/files/job_templates/gpu/manifest.yml`
- Create: `ansible/roles/ood_apps/files/job_templates/gpu/job.sh`
- Create: `ansible/roles/ood_apps/files/job_templates/array/manifest.yml`
- Create: `ansible/roles/ood_apps/files/job_templates/array/job.sh`

- [ ] **Step 1: Add failing application contract tests**

Require a consistent host menu, CPU/GPU/memory/time/work-directory fields,
32-hour maximum, retained `extra_sbatch`, no mail field, no old host names or
school-domain defaults, PATH-based executables, and valid script-variable names.

- [ ] **Step 2: Observe existing applications fail the contract**

Run: `python -m unittest tests.test_ood_roles.OODApplicationTests -v`
Expected: FAIL on old fields, old addresses, and inconsistent applications.

- [ ] **Step 3: Make the smallest application changes that satisfy the contract**

Preserve the previously working connection implementations. Normalize forms and
submission resources, fix Script's GPU variable, add memory and 32-hour wall
time, remove mail, and retain the warning on advanced arguments. Publish copies
under `/opt/ood_apps/epic` with system-app symlinks and install the three Job
Composer templates.

- [ ] **Step 4: Re-run application tests**

Run: `python -m unittest tests.test_ood_roles.OODApplicationTests -v`
Expected: PASS.

### Task 6: Add OOD metrics to Prometheus

**Files:**
- Modify: `ansible/inventory/group_vars/all/monitoring.yml`
- Modify: `ansible/roles/monitoring_prometheus/templates/prometheus.yml.j2`
- Modify: `tests/test_monitoring_roles.py`

- [ ] **Step 1: Add a failing scrape-job test**

Require controller port 9301 and a two-minute `ondemand` scrape job.

- [ ] **Step 2: Observe the monitoring test fail**

Run: `python -m unittest tests.test_monitoring_roles -v`
Expected: FAIL because the scrape job is absent.

- [ ] **Step 3: Add the OOD exporter target**

Use the controller inventory hostname and the existing slow scrape timeout.

- [ ] **Step 4: Re-run monitoring tests**

Run: `python -m unittest tests.test_monitoring_roles -v`
Expected: PASS.

### Task 7: Write the complete operator procedure

**Files:**
- Modify: `docs/slurm-stack-deployment-guide.md`
- Create: `docs/ood-compute-runtime.md`

- [ ] **Step 1: Add a failing documentation contract**

Require OOD 4.2 Ubuntu 26.04 installation, rclone/NFS/exporter installation,
password backup/restore, compute runtime prerequisites, Ansible commands,
expected outcomes, and one IAPP launch.

- [ ] **Step 2: Observe the documentation test fail**

Run: `python -m unittest tests.test_ood_roles.OODDocumentationTests -v`
Expected: FAIL.

- [ ] **Step 3: Replace the Work Package 8 placeholder with the full procedure**

Keep installation manual, explain each deployment step and expected result,
and avoid redundant low-value validation.

- [ ] **Step 4: Re-run the documentation and focused OOD tests**

Run: `python -m unittest tests.test_ood_roles -v`
Expected: PASS.

### Task 8: Proportionate local review

**Files:**
- Review: all files changed above

- [ ] **Step 1: Run the focused contract suite**

Run: `python -m unittest tests.test_ood_roles tests.test_monitoring_roles -v`
Expected: PASS.

- [ ] **Step 2: Run YAML parsing where static YAML is available**

Run: `python -c "import pathlib,yaml; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in pathlib.Path('ansible').rglob('*.yml') if '.j2' not in p.name]; print('yaml ok')"`
Expected: `yaml ok`.

- [ ] **Step 3: Review the final diff for scope**

Confirm that no package-install module was introduced, live htpasswd contents
are absent, existing Slurm policy is unchanged, and only OOD's Prometheus target
was added to monitoring.
