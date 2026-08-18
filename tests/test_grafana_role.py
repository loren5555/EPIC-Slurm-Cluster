#!/usr/bin/env python3
"""Contract tests for work-package 7 Grafana configuration."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_DIRECTORY = REPOSITORY_ROOT / "ansible"


def read_ansible_file(relative_path: str) -> str:
    """Read one UTF-8 Ansible source file from the repository."""

    return (ANSIBLE_DIRECTORY / relative_path).read_text(encoding="utf-8")


class GrafanaRoleTests(unittest.TestCase):
    def test_work_package_files_exist(self) -> None:
        expected_files = (
            "playbooks/grafana.yml",
            "roles/monitoring_grafana/tasks/main.yml",
            "roles/monitoring_grafana/handlers/main.yml",
            "roles/monitoring_grafana/templates/grafana.ini.j2",
            "roles/monitoring_grafana/templates/prometheus-datasource.yml.j2",
            "roles/monitoring_grafana/templates/dashboard-providers.yml.j2",
            "roles/monitoring_grafana/files/dashboards/epic-operations/cluster-administration.json",
            "roles/monitoring_grafana/files/dashboards/epic-operations/cluster-availability.json",
            "roles/monitoring_grafana/files/dashboards/epic-operations/cluster-overview.json",
        )

        missing = [
            path for path in expected_files if not (ANSIBLE_DIRECTORY / path).is_file()
        ]
        self.assertEqual(missing, [])

    def test_grafana_role_configures_but_does_not_install_software(self) -> None:
        tasks = read_ansible_file("roles/monitoring_grafana/tasks/main.yml")

        self.assertIn("/usr/sbin/grafana-server", tasks)
        self.assertIn("grafana-server.service", tasks)
        self.assertIn("prometheus-datasource.yml.j2", tasks)
        self.assertIn("dashboard-providers.yml.j2", tasks)
        self.assertIn("dashboards/upstream/", tasks)
        self.assertIn("dashboards/community-references/", tasks)

        for installer in (
            "ansible.builtin.apt",
            "ansible.builtin.apt_repository",
            "ansible.builtin.deb822_repository",
        ):
            self.assertNotIn(installer, tasks)

    def test_external_reference_dashboards_are_vendored_in_the_repository(self) -> None:
        tasks = read_ansible_file("roles/monitoring_grafana/tasks/main.yml")

        self.assertNotIn("ansible.builtin.get_url", tasks)
        self.assertNotIn("raw.githubusercontent.com", tasks)
        self.assertNotIn("grafana.com/api/dashboards", tasks)

        expected_dashboards = (
            "upstream/nvitop-exporter.json",
            "upstream/nvidia-dcgm-exporter.json",
            "upstream/prometheus-stats.json",
            "upstream/grafana-internal-metrics.json",
            "community-references/slurm-native-openmetrics.json",
            "community-references/node-exporter-full.json",
            "community-references/grafana-internal-stats.json",
        )
        dashboard_root = (
            ANSIBLE_DIRECTORY / "roles/monitoring_grafana/files/dashboards"
        )
        missing = [name for name in expected_dashboards if not (dashboard_root / name).is_file()]
        self.assertEqual(missing, [])

    def test_provisioning_separates_managed_and_experimental_dashboards(self) -> None:
        datasource = read_ansible_file(
            "roles/monitoring_grafana/templates/prometheus-datasource.yml.j2"
        )
        providers = read_ansible_file(
            "roles/monitoring_grafana/templates/dashboard-providers.yml.j2"
        )

        self.assertIn("uid: epic-prometheus", datasource)
        self.assertIn("url: http://127.0.0.1:{{ monitoring_prometheus_port }}", datasource)

        for folder in (
            "Upstream",
            "Community References",
            "EPIC Operations",
            "Experiments",
        ):
            self.assertIn(f"folder: {folder}", providers)

        managed_section = providers.split("folder: EPIC Operations", maxsplit=1)[1]
        experiments_section = providers.split("folder: Experiments", maxsplit=1)[1]
        self.assertIn("allowUiUpdates: false", managed_section)
        self.assertIn("allowUiUpdates: true", experiments_section)

    def test_custom_dashboards_are_valid_scenario_oriented_json(self) -> None:
        dashboard_directory = (
            ANSIBLE_DIRECTORY
            / "roles/monitoring_grafana/files/dashboards/epic-operations"
        )
        expected = {
            "cluster-administration.json": ("Cluster Administration", "now-30d"),
            "cluster-availability.json": ("Cluster Availability", "now-24h"),
            "cluster-overview.json": ("Cluster Overview", "now-7d"),
        }

        for filename, (title, default_from) in expected.items():
            dashboard = json.loads((dashboard_directory / filename).read_text(encoding="utf-8"))
            self.assertEqual(dashboard["title"], title)
            self.assertEqual(dashboard["time"]["from"], default_from)
            self.assertIn("epic", dashboard["tags"])
            self.assertIn("operations", dashboard["tags"])
            self.assertGreater(len(dashboard["panels"]), 4)

            serialized = json.dumps(dashboard)
            self.assertIn("epic-prometheus", serialized)
            self.assertNotIn("alert", dashboard)

    def test_dashboard_queries_cover_the_approved_reporting_scope(self) -> None:
        dashboard_directory = (
            ANSIBLE_DIRECTORY
            / "roles/monitoring_grafana/files/dashboards/epic-operations"
        )
        administration = (dashboard_directory / "cluster-administration.json").read_text(
            encoding="utf-8"
        )
        availability = (dashboard_directory / "cluster-availability.json").read_text(
            encoding="utf-8"
        )
        overview = (dashboard_directory / "cluster-overview.json").read_text(
            encoding="utf-8"
        )

        for metric in (
            "epic_slurm_accounting_jobs_total",
            "epic_slurm_accounting_gpu_allocated_seconds_total",
            "epic_slurm_fairshare",
            "epic_slurm_job_elapsed_seconds_bucket",
            "epic_slurm_job_queue_seconds_bucket",
        ):
            self.assertIn(metric, administration)

        for metric in (
            "slurm_nodes",
            "epic_slurm_node_gpus_available",
            "node_systemd_unit_state",
            "DCGM_FI_DEV_GPU_TEMP",
            "epic_slurm_usage_collector_last_success_unixtime",
        ):
            self.assertIn(metric, availability)

        for metric in (
            "slurm_jobs_running",
            "slurm_jobs_pending",
            "epic_slurm_gpu_allocated_seconds",
            "node_memory_MemAvailable_bytes",
            "DCGM_FI_DEV_GPU_UTIL",
        ):
            self.assertIn(metric, overview)


if __name__ == "__main__":
    unittest.main()
