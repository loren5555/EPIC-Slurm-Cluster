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
            "roles/slurm/tasks/accounting.yml",
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

    def test_accounting_enforces_declared_associations_and_limits(self) -> None:
        template = read_ansible_file("roles/slurm/templates/slurm.conf.j2")

        expected_settings = (
            "AccountingStorageType=accounting_storage/slurmdbd",
            "AccountingStorageHost={{ slurmdbd_host }}",
            "AccountingStorageTRES=gres/gpu",
            "AccountingStorageEnforce={{ slurm_accounting_storage_enforce }}",
            "JobAcctGatherType=jobacct_gather/cgroup",
            "JobAcctGatherFrequency=30",
        )

        for setting in expected_settings:
            self.assertIn(setting, template)

        forbidden_settings = ("gres/gpu:a100", "gres/gpu:rtx4070")

        for setting in forbidden_settings:
            self.assertNotIn(setting, template)

    def test_multifactor_priority_uses_fairshare_without_preemption(self) -> None:
        template = read_ansible_file("roles/slurm/templates/slurm.conf.j2")
        variables = read_ansible_file("inventory/group_vars/all/slurm.yml")

        for setting in (
            "PriorityType=priority/multifactor",
            "PriorityDecayHalfLife={{ slurm_priority_decay_half_life }}",
            "PriorityCalcPeriod={{ slurm_priority_calculation_period }}",
            "PriorityMaxAge={{ slurm_priority_max_age }}",
            "PriorityWeightFairshare={{ slurm_priority_weight_fairshare }}",
            "PriorityWeightAge={{ slurm_priority_weight_age }}",
            "PriorityWeightJobSize=0",
            "PriorityWeightPartition=0",
            "PriorityWeightQOS={{ slurm_priority_weight_qos }}",
            "PreemptType=preempt/none",
            "PreemptMode=OFF",
        ):
            self.assertIn(setting, template)

        for policy in (
            "slurm_accounting_storage_enforce: limits,qos",
            'slurm_priority_decay_half_life: "14-0"',
            "slurm_priority_calculation_period: 5",
            'slurm_priority_max_age: "7-0"',
            "slurm_priority_weight_fairshare: 10000",
            "slurm_priority_weight_age: 3000",
            "slurm_priority_weight_qos: 30000",
        ):
            self.assertIn(policy, variables)

        self.assertNotIn("preempt/qos", template)

    def test_gpu_partitions_bill_one_gpu_and_negligible_cpu(self) -> None:
        template = read_ansible_file("roles/slurm/templates/slurm.conf.j2")
        a100 = read_ansible_file(
            "inventory/host_vars/epic-cluster-compute-a100-01.yml"
        )
        rtx4070 = read_ansible_file(
            "inventory/host_vars/epic-cluster-compute-rtx4070-01.yml"
        )

        self.assertIn(
            'TRESBillingWeights="{{ node.slurm_tres_billing_weights }}"',
            template,
        )
        self.assertIn('slurm_tres_billing_weights: "CPU=0.01,GRES/gpu=1"', a100)
        self.assertIn(
            'slurm_tres_billing_weights: "CPU=0.01,GRES/gpu=1"',
            rtx4070,
        )

    def test_cluster_record_is_created_before_slurm_reconfiguration(self) -> None:
        main_tasks = read_ansible_file("roles/slurm/tasks/main.yml")
        accounting_path = ANSIBLE_DIRECTORY / "roles/slurm/tasks/accounting.yml"

        self.assertTrue(accounting_path.is_file())
        accounting_tasks = accounting_path.read_text(encoding="utf-8")

        self.assertLess(
            main_tasks.index("import_tasks: accounting.yml"),
            main_tasks.index("import_tasks: verify.yml"),
        )
        self.assertIn("/usr/bin/sacctmgr", accounting_tasks)
        self.assertIn("list\n      - cluster", accounting_tasks)
        self.assertIn("--immediate", accounting_tasks)
        self.assertIn("add\n      - cluster", accounting_tasks)
        self.assertIn("slurm_cluster_name", accounting_tasks)
        self.assertNotIn("add\n      - account", accounting_tasks)
        self.assertNotIn("add\n      - user", accounting_tasks)

    def test_site_bootstraps_accounting_before_enabling_enforcement(self) -> None:
        site = read_ansible_file("playbooks/site.yml")

        bootstrap = site.index("slurm_accounting_storage_enforce: none")
        associations = site.index("import_playbook: slurm_associations.yml")
        final_slurm = site.rindex("import_playbook: slurm.yml")

        self.assertLess(bootstrap, associations)
        self.assertLess(associations, final_slurm)

    def test_runtime_verification_pings_slurmdbd(self) -> None:
        verification_tasks = read_ansible_file("roles/slurm/tasks/verify.yml")

        self.assertIn("/usr/bin/sacctmgr", verification_tasks)
        self.assertIn("- ping", verification_tasks)
        self.assertIn("is UP", verification_tasks)

    def test_shared_slurm_configuration_is_reloaded_without_daemon_restart(self) -> None:
        configuration_tasks = read_ansible_file("roles/slurm/tasks/configure.yml")
        shared_configuration_task = configuration_tasks.split(
            "- name: Install the shared cluster and partition configuration",
            maxsplit=1,
        )[1].split(
            "- name: Install the shared Slurm job cgroup policy",
            maxsplit=1,
        )[0]

        self.assertIn("Reconfigure Slurm daemons", shared_configuration_task)
        self.assertNotIn("Restart slurmd", shared_configuration_task)

    def test_all_slurm_jobs_use_the_same_cgroup_constraints(self) -> None:
        template = read_ansible_file("roles/slurm/templates/cgroup.conf.j2")

        self.assertIn("ConstrainCores=yes", template)
        self.assertIn("ConstrainRAMSpace=yes", template)
        self.assertIn("ConstrainDevices=yes", template)
        self.assertNotIn("controlled_compute_nodes", template)
        self.assertNotIn("free_compute_nodes", template)
        self.assertNotIn("ConstrainCores=no", template)
        self.assertNotIn("ConstrainRAMSpace=no", template)
        self.assertNotIn("ConstrainDevices=no", template)

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
