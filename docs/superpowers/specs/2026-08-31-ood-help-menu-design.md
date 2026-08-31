# OOD Help Menu Design

## Purpose

Restore stable support and documentation links in the Open OnDemand Help
drop-down menu. The menu is visible to every OOD user and provides one-click
access to EPIC documentation, upstream product documentation, the project
repository, GitHub issue workflows, and live cluster health information.

## Configuration Location

Use Open OnDemand 4.2's native `help_menu` property in the existing
`ansible/roles/ood_controller/templates/ondemand.yml.j2` template. The
`ood_controller` role already installs this template as
`/etc/ood/config/ondemand.d/epic.yml` and restarts all user PUNs when it
changes, so no new deployment task or handler is required.

The links remain literal site-level configuration in the template. They are
not inventory variables because they are stable project identities rather
than host-specific values.

## Menu Structure

Add three groups to the existing Help drop-down menu. All links open in a new
browser tab.

### 集群状态

- 集群状态（Grafana）:
  `http://epic-cluster-controller-01:3000/d/epic-cluster-availability`
- 资源使用概览（Grafana）:
  `http://epic-cluster-controller-01:3000/d/epic-cluster-overview`
- Exporter 状态（Prometheus）:
  `http://epic-cluster-controller-01:9090/targets`

These links answer whether the cluster is currently usable before a user
starts troubleshooting their own job. Prometheus links directly to the target
health page rather than its general query interface.

### EPIC 集群

- 集群文档: `https://loren5555.github.io/EPIC-Slurm-Cluster/`
- GitHub 仓库: `https://github.com/loren5555/EPIC-Slurm-Cluster`

The documentation link targets the documentation home page because that page
already routes users, administrators, and developers to their respective
sections.

### 参考与支持

- Slurm 官方文档: `https://slurm.schedmd.com/`
- Slurm 排队与失败原因:
  `https://slurm.schedmd.com/job_reason_codes.html`
- Open OnDemand 官方文档:
  `https://osc.github.io/ood-documentation/latest`
- 查看 GitHub Issues:
  `https://github.com/loren5555/EPIC-Slurm-Cluster/issues`
- 提交问题:
  `https://github.com/loren5555/EPIC-Slurm-Cluster/issues/new/choose`

The custom links are appended to OOD's built-in Help items. The rest of the
left and right navigation bars remain unchanged.

## Validation

The user explicitly authorized a configuration-only follow-up without adding
or changing tests. Inspect the final template diff for unrelated changes and
leave deployment to the controller to the operator.
