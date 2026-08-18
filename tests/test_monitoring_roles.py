#!/usr/bin/env python3
"""Contract tests for the EPIC monitoring Ansible roles."""

from __future__ import annotations

import unittest
import runpy
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_DIRECTORY = REPOSITORY_ROOT / "ansible"


def read_ansible_file(relative_path: str) -> str:
    """Read one UTF-8 Ansible source file from the repository."""

    return (ANSIBLE_DIRECTORY / relative_path).read_text(encoding="utf-8")


class MonitoringRoleTests(unittest.TestCase):
    def test_work_package_files_exist(self) -> None:
        expected_files = (
            "inventory/group_vars/all/monitoring.yml",
            "playbooks/monitoring.yml",
            "roles/monitoring_node_exporter/tasks/main.yml",
            "roles/monitoring_node_exporter/handlers/main.yml",
            "roles/monitoring_node_exporter/templates/node_exporter.service.j2",
            "roles/monitoring_gpu_exporters/tasks/main.yml",
            "roles/monitoring_gpu_exporters/handlers/main.yml",
            "roles/monitoring_gpu_exporters/templates/nvitop-exporter.service.j2",
            "roles/monitoring_gpu_exporters/templates/dcgm-exporter-config.yaml.j2",
            "roles/monitoring_gpu_exporters/templates/nvidia-dcgm-exporter.service.j2",
            "roles/monitoring_prometheus/tasks/main.yml",
            "roles/monitoring_prometheus/handlers/main.yml",
            "roles/monitoring_prometheus/templates/prometheus.yml.j2",
            "roles/monitoring_prometheus/templates/prometheus.service.j2",
            "roles/monitoring_prometheus/templates/epic-slurm-usage-collector.py.j2",
            "roles/monitoring_prometheus/templates/epic-slurm-usage-collector.service.j2",
            "roles/monitoring_prometheus/templates/epic-slurm-usage-collector.timer.j2",
        )

        missing = [
            path
            for path in expected_files
            if not (ANSIBLE_DIRECTORY / path).is_file()
        ]

        self.assertEqual(missing, [])

    def test_inventory_explicitly_identifies_current_gpu_hosts(self) -> None:
        inventory = read_ansible_file("inventory/hosts.yml")
        gpu_group = inventory.split("gpu_nodes:", maxsplit=1)[1]

        self.assertIn("epic-cluster-compute-a100-01:", gpu_group)
        self.assertIn("epic-cluster-compute-rtx4070-01:", gpu_group)
        self.assertNotIn("children:", gpu_group)

    def test_monitoring_policy_uses_declared_sampling_and_retention(self) -> None:
        variables = read_ansible_file("inventory/group_vars/all/monitoring.yml")

        expected_policy = (
            'monitoring_fast_scrape_interval: "10s"',
            'monitoring_fast_scrape_timeout: "5s"',
            'monitoring_slurm_state_scrape_interval: "2m"',
            'monitoring_slurm_scheduler_scrape_interval: "5m"',
            'monitoring_slow_scrape_timeout: "10s"',
            'monitoring_prometheus_scrape_interval: "30s"',
            'monitoring_prometheus_retention_time: "90d"',
            'monitoring_prometheus_retention_size: "100GB"',
            "monitoring_dcgm_collection_interval_milliseconds: 10000",
        )

        for setting in expected_policy:
            self.assertIn(setting, variables)

    def test_node_exporter_is_configured_without_package_installation(self) -> None:
        tasks = read_ansible_file("roles/monitoring_node_exporter/tasks/main.yml")
        unit = read_ansible_file(
            "roles/monitoring_node_exporter/templates/node_exporter.service.j2"
        )

        self.assertIn("/usr/local/bin/node_exporter", tasks)
        self.assertIn("node_exporter.service", tasks)
        self.assertIn("http://127.0.0.1:{{ monitoring_node_exporter_port }}/metrics", tasks)
        self.assertIn("User=node_exporter", unit)
        self.assertIn("--collector.systemd", unit)
        self.assertIn("--collector.textfile.directory=", unit)

        for installer in ("ansible.builtin.apt", "ansible.builtin.get_url", "ansible.builtin.unarchive"):
            self.assertNotIn(installer, tasks)

    def test_gpu_exporters_use_rootful_docker_and_system_slice_nvitop(self) -> None:
        tasks = read_ansible_file("roles/monitoring_gpu_exporters/tasks/main.yml")
        nvitop_unit = read_ansible_file(
            "roles/monitoring_gpu_exporters/templates/nvitop-exporter.service.j2"
        )
        dcgm_config = read_ansible_file(
            "roles/monitoring_gpu_exporters/templates/dcgm-exporter-config.yaml.j2"
        )
        dcgm_unit = read_ansible_file(
            "roles/monitoring_gpu_exporters/templates/nvidia-dcgm-exporter.service.j2"
        )

        self.assertIn("/opt/nvitop-exporter/bin/nvitop-exporter", tasks)
        self.assertIn("User=root", nvitop_unit)
        self.assertIn("Slice=system.slice", nvitop_unit)
        self.assertIn("--port {{ monitoring_nvitop_exporter_port }}", nvitop_unit)
        self.assertIn("interval:", dcgm_config)
        self.assertIn("monitoring_dcgm_collection_interval_milliseconds", dcgm_config)
        self.assertIn("Requires=docker.service", dcgm_unit)
        self.assertIn("Slice=system.slice", dcgm_unit)
        self.assertIn("--gpus all", dcgm_unit)
        self.assertIn("--cap-add SYS_ADMIN", dcgm_unit)
        self.assertIn("monitoring_dcgm_configuration_file", dcgm_unit)
        self.assertIn("monitoring_dcgm_exporter_image", dcgm_unit)

        for installer in ("ansible.builtin.apt", "ansible.builtin.pip", "ansible.builtin.get_url"):
            self.assertNotIn(installer, tasks)

    def test_prometheus_scrapes_stable_inventory_names_at_declared_rates(self) -> None:
        template = read_ansible_file(
            "roles/monitoring_prometheus/templates/prometheus.yml.j2"
        )

        for job_name in (
            "prometheus",
            "node",
            "dcgm",
            "nvitop",
            "slurm-jobs",
            "slurm-nodes",
            "slurm-partitions",
            "slurm-scheduler",
        ):
            self.assertIn(f"job_name: {job_name}", template)

        self.assertIn("groups['all'] | sort", template)
        self.assertIn("groups['gpu_nodes'] | sort", template)
        self.assertIn("groups['controllers'] | sort", template)
        self.assertIn("monitoring_fast_scrape_interval", template)
        self.assertIn("monitoring_slurm_state_scrape_interval", template)
        self.assertIn("monitoring_slurm_scheduler_scrape_interval", template)
        self.assertIn("/metrics/jobs", template)
        self.assertIn("/metrics/nodes", template)
        self.assertIn("/metrics/partitions", template)
        self.assertIn("/metrics/scheduler", template)
        self.assertNotIn("jobs-users-accts", template)
        self.assertNotIn("ansible_host", template)

    def test_prometheus_uses_local_bounded_storage(self) -> None:
        tasks = read_ansible_file("roles/monitoring_prometheus/tasks/main.yml")
        unit = read_ansible_file(
            "roles/monitoring_prometheus/templates/prometheus.service.j2"
        )
        variables = read_ansible_file("inventory/group_vars/all/monitoring.yml")

        self.assertIn("/usr/local/bin/promtool", tasks)
        self.assertIn("check\n      - config", tasks)
        self.assertIn("--storage.tsdb.path={{ monitoring_prometheus_data_directory }}", unit)
        self.assertIn("monitoring_prometheus_data_directory: /var/lib/prometheus", variables)
        self.assertIn("--storage.tsdb.retention.time={{ monitoring_prometheus_retention_time }}", unit)
        self.assertIn("--storage.tsdb.retention.size={{ monitoring_prometheus_retention_size }}", unit)
        self.assertNotIn("ansible.builtin.get_url", tasks)
        self.assertNotIn("ansible.builtin.unarchive", tasks)

    def test_controller_collects_bounded_slurm_usage_metrics(self) -> None:
        tasks = read_ansible_file("roles/monitoring_prometheus/tasks/main.yml")
        service = read_ansible_file(
            "roles/monitoring_prometheus/templates/epic-slurm-usage-collector.service.j2"
        )
        timer = read_ansible_file(
            "roles/monitoring_prometheus/templates/epic-slurm-usage-collector.timer.j2"
        )
        collector = read_ansible_file(
            "roles/monitoring_prometheus/templates/epic-slurm-usage-collector.py.j2"
        )

        self.assertIn("epic-slurm-usage-collector.timer", tasks)
        self.assertIn("Type=oneshot", service)
        self.assertIn("--cluster {{ slurm_cluster_name }}", service)
        self.assertIn("OnUnitActiveSec={{ monitoring_slurm_usage_collection_interval }}", timer)
        self.assertIn("/usr/bin/scontrol", collector)
        self.assertIn("/usr/bin/sacct", collector)
        self.assertIn('"--clusters"', collector)
        self.assertIn('"--allusers"', collector)
        self.assertIn('"--truncate"', collector)
        self.assertIn("os.replace", collector)

        for metric in (
            "epic_slurm_jobs",
            "epic_slurm_pending_jobs",
            "epic_slurm_pending_oldest_age_seconds",
            "epic_slurm_gpus_allocated",
            "epic_slurm_gpus_requested_pending",
            "epic_slurm_node_gpus_configured",
            "epic_slurm_node_gpus_allocated",
            "epic_slurm_node_gpus_available",
            "epic_slurm_gpu_allocated_seconds",
            "epic_slurm_gpu_jobs",
            "epic_slurm_usage_collector_last_success_unixtime",
        ):
            self.assertIn(metric, collector)

        self.assertNotIn('"job_id"', collector)

    def test_slurm_usage_collector_parses_generic_and_typed_gpu_tres(self) -> None:
        collector_path = (
            ANSIBLE_DIRECTORY
            / "roles/monitoring_prometheus/templates/epic-slurm-usage-collector.py.j2"
        )
        collector = runpy.run_path(str(collector_path))

        gpu_count = collector["gpu_count_from_tres"]
        gres_count = collector["gpu_count_from_gres"]

        self.assertEqual(gpu_count("cpu=4,mem=8G,gres/gpu=2,gres/gpu:a100=2"), 2)
        self.assertEqual(gpu_count("cpu=4,gres/gpu:a100=2"), 2)
        self.assertEqual(gres_count("gpu:a100-sxm4:8(S:0-1)"), 8)
        self.assertEqual(gres_count("gpu:1(S:0)"), 1)

    def test_monitoring_playbook_orders_exporters_before_prometheus(self) -> None:
        playbook = read_ansible_file("playbooks/monitoring.yml")
        site = read_ansible_file("playbooks/site.yml")

        node_position = playbook.index("monitoring_node_exporter")
        gpu_position = playbook.index("monitoring_gpu_exporters")
        prometheus_position = playbook.index("monitoring_prometheus")

        self.assertLess(node_position, gpu_position)
        self.assertLess(gpu_position, prometheus_position)
        self.assertLess(
            site.index("import_playbook: slurm.yml"),
            site.index("import_playbook: monitoring.yml"),
        )


if __name__ == "__main__":
    unittest.main()
