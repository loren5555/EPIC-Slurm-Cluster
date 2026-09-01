#!/usr/bin/env python3
"""Contracts for onboarding the second free RTX 4070 compute node."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_DIRECTORY = REPOSITORY_ROOT / "ansible"
NODE_01 = "epic-cluster-compute-rtx4070-01"
NODE_02 = "epic-cluster-compute-rtx4070-02"


def read_yaml(relative_path: str) -> dict:
    return yaml.safe_load(
        (ANSIBLE_DIRECTORY / relative_path).read_text(encoding="utf-8")
    )


class Rtx407002NodeTests(unittest.TestCase):
    def test_inventory_declares_free_gpu_host_at_planned_address(self) -> None:
        children = read_yaml("inventory/hosts.yml")["all"]["children"]

        free_hosts = children["free_compute_nodes"]["hosts"]
        gpu_hosts = children["gpu_nodes"]["hosts"]
        self.assertEqual(free_hosts[NODE_02]["ansible_host"], "192.168.77.50")
        self.assertIn(NODE_02, gpu_hosts)

    def test_hardware_and_scheduling_policy_match_node_01(self) -> None:
        node_01 = read_yaml(f"inventory/host_vars/{NODE_01}.yml")
        node_02 = read_yaml(f"inventory/host_vars/{NODE_02}.yml")

        for key, value in node_01.items():
            if key != "ood_display_name":
                self.assertEqual(node_02[key], value, key)
        self.assertEqual(node_02["slurm_partition_state"], "DOWN")
        self.assertIn("Node 02", node_02["ood_display_name"])

    def test_partition_policy_matches_node_01_and_starts_closed(self) -> None:
        partitions = {
            item["name"]: item
            for item in read_yaml("vars/slurm_partitions.yml")["slurm_partitions"]
        }
        node_01 = partitions[NODE_01]
        node_02 = partitions[NODE_02]

        for key in (
            "management_class",
            "allowed_accounts",
            "allowed_users",
            "denied_users",
        ):
            self.assertEqual(node_02[key], node_01[key], key)
        self.assertEqual(node_02["host"], NODE_02)

        template = (
            ANSIBLE_DIRECTORY / "roles/slurm/templates/slurm.conf.j2"
        ).read_text(encoding="utf-8")
        self.assertIn("node.slurm_partition_state | default('UP')", template)

    def test_ssh_access_matches_node_01(self) -> None:
        users = read_yaml("vars/users.yml")["cluster_users"]
        node_01_users = {
            user["name"] for user in users if NODE_01 in user["ssh_access"]
        }
        node_02_users = {
            user["name"] for user in users if NODE_02 in user["ssh_access"]
        }
        self.assertEqual(node_02_users, node_01_users)


if __name__ == "__main__":
    unittest.main()
