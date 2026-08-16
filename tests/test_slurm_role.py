#!/usr/bin/env python3
"""Contract tests for the declarative Slurm Ansible role.

These tests intentionally inspect the configuration source rather than a live
cluster. Live syntax checks and convergence checks run later on the controller,
where Ansible and Slurm 25.11 are installed.
"""

from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_DIRECTORY = REPOSITORY_ROOT / "ansible"


def read_ansible_file(relative_path: str) -> str:
    """Read one UTF-8 Ansible source file from the repository."""

    return (ANSIBLE_DIRECTORY / relative_path).read_text(encoding="utf-8")


class SlurmRoleTests(unittest.TestCase):
    def test_work_package_files_exist(self) -> None:
        expected_files = (
            "inventory/group_vars/all/slurm.yml",
            "inventory/host_vars/epic-cluster-compute-a100-01.yml",
            "inventory/host_vars/epic-cluster-compute-rtx4070-01.yml",
            "playbooks/slurm.yml",
            "roles/slurm/handlers/main.yml",
            "roles/slurm/tasks/main.yml",
            "roles/slurm/tasks/configure.yml",
            "roles/slurm/tasks/verify.yml",
            "roles/slurm/templates/slurm.conf.j2",
            "roles/slurm/templates/cgroup.conf.j2",
            "roles/slurm/templates/gres.conf.j2",
        )

        missing = [
            path
            for path in expected_files
            if not (ANSIBLE_DIRECTORY / path).is_file()
        ]

        self.assertEqual(missing, [])

    def test_slurm_configuration_uses_names_and_default_ports(self) -> None:
        template = read_ansible_file("roles/slurm/templates/slurm.conf.j2")

        self.assertIn("SlurmctldHost={{ slurm_controller_host }}", template)
        self.assertNotIn("SlurmctldHost={{ slurm_controller_host }}(", template)
        self.assertNotIn("NodeAddr=", template)
        self.assertNotIn("SlurmctldPort=", template)
        self.assertNotIn("SlurmdPort=", template)
        self.assertIn("PartitionName={{ node_name }}", template)
        self.assertIn("Default=NO", template)
        self.assertNotIn("PartitionName=controlled", template)
        self.assertNotIn("PartitionName=free", template)

    def test_slurm_configuration_declares_only_generic_gpu_resources(self) -> None:
        template = read_ansible_file("roles/slurm/templates/slurm.conf.j2")

        self.assertIn("Gres=gpu:{{ node.slurm_gpu_count }}", template)
        self.assertNotIn("slurm_gpu_type", template)
        self.assertNotIn("Feature=", template)
        self.assertNotIn("slurm_feature", template)

    def test_work_package_one_does_not_enable_accounting_or_fair_share(self) -> None:
        template = read_ansible_file("roles/slurm/templates/slurm.conf.j2")

        forbidden_settings = (
            "AccountingStorageType",
            "AccountingStorageTRES",
            "AccountingStorageEnforce",
            "PriorityType=priority/multifactor",
        )

        for setting in forbidden_settings:
            self.assertNotIn(setting, template)

    def test_cgroup_policy_is_selected_by_management_class(self) -> None:
        template = read_ansible_file("roles/slurm/templates/cgroup.conf.j2")

        self.assertIn("inventory_hostname in groups['controlled_compute_nodes']", template)
        self.assertIn("inventory_hostname in groups['free_compute_nodes']", template)
        self.assertNotIn("slurm_management_class", template)
        self.assertIn("ConstrainCores=yes", template)
        self.assertIn("ConstrainRAMSpace=yes", template)
        self.assertIn("ConstrainDevices=yes", template)
        self.assertIn("ConstrainCores=no", template)
        self.assertIn("ConstrainRAMSpace=no", template)
        self.assertIn("ConstrainDevices=no", template)

    def test_gres_configuration_uses_nvidia_autodetection(self) -> None:
        template = read_ansible_file("roles/slurm/templates/gres.conf.j2")

        self.assertIn("AutoDetect=nvidia", template)
        self.assertNotIn("slurm_gpu_type", template)
        self.assertNotIn("slurm_gpu_devices", template)
        self.assertNotIn("File=", template)

    def test_host_variables_preserve_validated_hardware(self) -> None:
        a100 = read_ansible_file(
            "inventory/host_vars/epic-cluster-compute-a100-01.yml"
        )
        rtx4070 = read_ansible_file(
            "inventory/host_vars/epic-cluster-compute-rtx4070-01.yml"
        )

        for expected in (
            "slurm_cpus: 128",
            "slurm_real_memory: 1024000",
            "slurm_gpu_count: 8",
        ):
            self.assertIn(expected, a100)

        for expected in (
            "slurm_cpus: 32",
            "slurm_real_memory: 126000",
            "slurm_gpu_count: 1",
        ):
            self.assertIn(expected, rtx4070)

        for obsolete_variable in (
            "slurm_feature",
            "slurm_gpu_type",
            "slurm_gpu_devices",
        ):
            self.assertNotIn(obsolete_variable, a100)
            self.assertNotIn(obsolete_variable, rtx4070)


if __name__ == "__main__":
    unittest.main()
