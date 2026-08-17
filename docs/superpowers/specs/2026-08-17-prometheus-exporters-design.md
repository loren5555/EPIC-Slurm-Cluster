# EPIC Prometheus and Exporters Design

## 1. Goal

Work package 6 establishes local, real-time monitoring without making Slurm,
SSH, GPU access, or running jobs depend on the monitoring stack. Prometheus
runs on `epic-cluster-controller-01`; exporters run as ordinary systemd
services on the hosts whose state they observe.

The monitoring network is internal to the laboratory. GPU process metrics may
contain Linux usernames, process IDs, commands, and Slurm job identifiers.

## 2. Lifecycle boundary

Software installation remains a deliberate administrator operation because the
controller and compute nodes use different Ubuntu releases and GPU software
stacks. The deployment guide supplies complete commands to inspect, archive,
disable, and remove the legacy services before installing current software.

Ansible starts only after the required executables or NVIDIA packages exist. It
owns:

- systemd units and drop-ins that are not supplied by a package;
- exporter listen addresses and runtime options;
- the Prometheus configuration and generated inventory targets;
- Slurm OpenMetrics configuration;
- service validation, reload, and enablement.

Ansible does not download release archives, change NVIDIA drivers, select a
CUDA/DCGM package family, create containers, or remove unknown legacy files.

## 3. Components

| Component | Hosts | Port | Purpose | Installation owner |
|---|---|---:|---|---|
| Prometheus | controller | 9090 | Time-series storage, query, and target health | official release binary |
| node_exporter | all hosts | 9100 | CPU, memory, disk, filesystem, network, and systemd | official release binary |
| NVIDIA DCGM Exporter | GPU compute hosts | 9400 | GPU health, utilization, memory, temperature, power, and errors | NVIDIA APT packages |
| nvitop-exporter | GPU compute hosts | 5050 | GPU processes, usernames, PIDs, commands, and per-process use | isolated Python virtual environment |
| Slurm OpenMetrics | controller/slurmctld | 6817 | Jobs, nodes, partitions, and scheduler state | built into Slurm 25.11 |

The initial pinned upstream versions are Prometheus 3.12.0, node_exporter
1.11.1, and nvitop-exporter 1.7.1. The manual procedure verifies checksums and
records the installed versions. DCGM and DCGM Exporter are selected together
from NVIDIA's repository after inspecting the installed driver and CUDA
user-mode major version; their versions are not hard-coded across hosts.

The old `slurm-job-exporter.service` is retired because Slurm 25.11 exposes the
required OpenMetrics endpoints directly. Existing `node_exporter.service`,
`nvitop-exporter.service`, and non-vendor DCGM units are archived and disabled
before replacement. The package-owned `nvidia-dcgm-exporter.service` becomes
the only DCGM exporter unit.

## 4. Data flow and sampling

Prometheus uses inventory hostnames rather than temporary IP addresses. Every
scrape job declares its own interval and a 10-second timeout ceiling.

| Scrape job | Interval |
|---|---:|
| node_exporter | 10 seconds |
| DCGM Exporter | 10 seconds |
| nvitop-exporter | 10 seconds |
| Slurm jobs, nodes, and partitions | 2 minutes |
| Slurm scheduler | 5 minutes |
| Prometheus itself | 30 seconds |
| future OOD and Grafana endpoints | 1 minute |

DCGM's internal collection interval is also set to 10 seconds so a 10-second
Prometheus scrape does not repeatedly read a 30-second sample. Slurm's
`/metrics/jobs-users-accts` endpoint is not collected because its unbounded
user/account labels duplicate historical reporting already provided by
SlurmDBD.

The Slurm metrics plugin uses `MetricsParameters=ignore_private_data`. This
keeps the small internal deployment free from persistent JWT management. It is
acceptable because the controller and exporter ports are intended only for the
laboratory network.

## 5. Storage

Prometheus stores its TSDB on the controller's local filesystem at
`/var/lib/prometheus`. Network storage is not used. Retention is bounded by both:

- `--storage.tsdb.retention.time=90d`;
- `--storage.tsdb.retention.size=100GB`.

The first limit reached removes the oldest persistent blocks. The operating
system disk therefore retains substantial free space even if process-level
metrics create more series than expected.

## 6. Service model

Prometheus and node_exporter use dedicated unprivileged service accounts.
nvitop-exporter runs as root in `system.slice` because it must see every GPU and
attribute GPU processes to users across login and Slurm cgroups. It is started
in read-only exporter mode and receives no process-management interface.

DCGM Exporter uses NVIDIA's package-owned service and a systemd drop-in. The
drop-in changes only the collection interval and listen behavior; it does not
replace the vendor binary, driver, Fabric Manager, or GPU device policy.

Service failure has no reverse dependency on `slurmctld`, `slurmd`, MUNGE, SSH,
OOD, or NVIDIA Fabric Manager. Prometheus being unavailable only creates a gap
in monitoring data.

## 7. OOD, Grafana, and deferred exporters

Work package 6 does not install a speculative OOD exporter. OOD application
sessions are already represented by Slurm jobs, while its host processes are
visible through node_exporter. Work package 8 may add Apache/Passenger metrics
and HTTP availability probes after the actual OOD topology exists.

Grafana is deferred to work package 7. Its built-in `/metrics` endpoint will be
scraped at one minute after Grafana is installed.

MySQL/MariaDB exporter is omitted initially: SlurmDBD availability is already
verified operationally, and direct database performance tuning is not a work
package 6 requirement. Blackbox Exporter is deferred until OOD introduces
stable HTTP endpoints worth probing.

## 8. Configuration structure

The Ansible project adds one monitoring playbook and focused roles:

- `monitoring_common`: verifies installed executables and configures
  node_exporter on every host;
- `gpu_exporters`: configures nvitop-exporter and the NVIDIA DCGM service on GPU
  hosts;
- `prometheus`: renders inventory-based scrape targets, storage flags, and the
  controller service;
- the existing `slurm` role gains only the two Slurm metrics parameters.

Monitoring inventory data describes ports, intervals, retention, and which
hosts have GPUs. Package versions remain in the manual installation record,
not in host configuration templates.

## 9. Validation and stopping conditions

Before any service reload, Ansible validates Prometheus configuration with
`promtool check config`. Runtime verification confirms each local exporter
endpoint and uses the Prometheus HTTP API to ensure every declared target is
`UP`. A second playbook run must report no changes.

Deployment stops if:

- a required executable or vendor unit is absent;
- DCGM Exporter cannot see the same GPU count declared to Slurm;
- nvitop-exporter cannot expose process metrics from `system.slice`;
- Slurm metrics noticeably delay scheduling or fail at the selected intervals;
- any monitoring service changes GPU visibility, Fabric Manager, Slurm cgroups,
  SSH behavior, or existing jobs;
- Prometheus uses a temporary IP or non-local TSDB path.

GPU faults that appear as NVIDIA XID or driver events remain in journald. The
10-second Prometheus sampling captures time-series symptoms and persistent
counters, but it is not treated as an event-log replacement.
