# OOD Help Menu Design

## Purpose

Restore stable support and documentation links in the Open OnDemand Help
drop-down menu. The menu is visible to every OOD user and provides one-click
access to EPIC documentation, upstream product documentation, the project
repository, and GitHub issue workflows.

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

Add two groups to the existing Help drop-down menu. All links open in a new
browser tab.

### EPIC 集群

- 集群文档: `https://loren5555.github.io/EPIC-Slurm-Cluster/`
- GitHub 仓库: `https://github.com/loren5555/EPIC-Slurm-Cluster`

The documentation link targets the documentation home page because that page
already routes users, administrators, and developers to their respective
sections.

### 参考与支持

- Slurm 官方文档: `https://slurm.schedmd.com/`
- Open OnDemand 官方文档:
  `https://osc.github.io/ood-documentation/latest`
- 查看 GitHub Issues:
  `https://github.com/loren5555/EPIC-Slurm-Cluster/issues`
- 提交问题:
  `https://github.com/loren5555/EPIC-Slurm-Cluster/issues/new/choose`

The custom links are appended to OOD's built-in Help items. The rest of the
left and right navigation bars remain unchanged.

## Validation

Extend the existing OOD controller contract test before changing the template.
The test will require the `help_menu` property, both group labels, all six link
titles and URLs, and `new_tab: true`. It must fail against the current template
and pass after the minimal template change.

Run the focused OOD controller test, parse the rendered YAML structure where
the local environment permits, and inspect the final diff for unrelated
changes. Deployment to the controller remains the operator's responsibility.
