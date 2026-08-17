#!/usr/bin/env python3
"""Behavior and configuration contracts for Slurm associations."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_DIRECTORY = REPOSITORY_ROOT / "ansible"
sys.path.insert(0, str(ANSIBLE_DIRECTORY / "filter_plugins"))

from slurm_associations import (  # noqa: E402
    build_desired_state,
    find_jobs_blocking_removals,
    plan_account_metadata_changes,
    plan_association_changes,
    plan_user_default_changes,
    slurm_partition_argument,
)


USERS = [
    {"name": "liuhongbo", "slurm_account": "epic-rl"},
    {"name": "yinjiajie", "slurm_account": "epic-rl"},
    {"name": "wangjiaxiang", "slurm_account": "nue"},
]

ACCOUNTS = [
    {"name": "epic-rl", "description": "EPIC-RL members"},
    {"name": "nue", "description": "NUE members"},
]

PARTITIONS = [
    {
        "name": "epic-cluster-compute-a100-01",
        "host": "epic-cluster-compute-a100-01",
        "allowed_accounts": ["epic-rl", "nue"],
        "allowed_users": [],
        "denied_users": [],
        "account_limits": {"nue": {"group_tres": "gres/gpu=2"}},
    },
    {
        "name": "epic-cluster-compute-rtx4070-01",
        "host": "epic-cluster-compute-rtx4070-01",
        "allowed_accounts": [],
        "allowed_users": ["liuhongbo"],
        "denied_users": [],
        "account_limits": {},
    },
]


def read_ansible_file(relative_path: str) -> str:
    """Read one UTF-8 Ansible source file from the repository."""

    return (ANSIBLE_DIRECTORY / relative_path).read_text(encoding="utf-8")


class SlurmAssociationPlannerTests(unittest.TestCase):
    def test_blank_partition_selector_is_explicit(self) -> None:
        self.assertEqual(slurm_partition_argument(""), 'Partition=""')
        self.assertEqual(
            slurm_partition_argument("gpu-host"),
            "Partition=gpu-host",
        )

    def test_builds_explicit_partition_permissions_and_account_limit(self) -> None:
        state = build_desired_state(USERS, ACCOUNTS, PARTITIONS)

        self.assertEqual(
            state["authorization_matrix"]["epic-cluster-compute-a100-01"],
            ["liuhongbo", "wangjiaxiang", "yinjiajie"],
        )
        self.assertEqual(
            state["authorization_matrix"]["epic-cluster-compute-rtx4070-01"],
            ["liuhongbo"],
        )

        nue_a100 = next(
            association
            for association in state["associations"]
            if association["account"] == "nue"
            and association["user"] == ""
            and association["partition"] == "epic-cluster-compute-a100-01"
        )
        self.assertEqual(nue_a100["group_tres"], "gres/gpu=2")

        self.assertFalse(
            any(
                association["user"] and not association["partition"]
                for association in state["associations"]
            )
        )

    def test_account_shares_follow_effective_partition_membership(self) -> None:
        state = build_desired_state(USERS, ACCOUNTS, PARTITIONS)

        epic_a100 = next(
            association
            for association in state["associations"]
            if association["account"] == "epic-rl"
            and association["user"] == ""
            and association["partition"] == "epic-cluster-compute-a100-01"
        )
        epic_rtx4070 = next(
            association
            for association in state["associations"]
            if association["account"] == "epic-rl"
            and association["user"] == ""
            and association["partition"] == "epic-cluster-compute-rtx4070-01"
        )

        self.assertEqual(epic_a100["fairshare"], 2)
        self.assertEqual(epic_rtx4070["fairshare"], 1)

    def test_plan_adds_updates_and_removes_only_managed_associations(self) -> None:
        desired = build_desired_state(USERS, ACCOUNTS, PARTITIONS)
        current_rows = [
            "epic|epic-rl||epic-cluster-compute-a100-01|1|cpu=4|",
            "epic|epic-rl|liuhongbo|epic-cluster-compute-a100-01|1||",
            "epic|epic-rl|liuhongbo||1||",
            "epic|external|external-user||1||",
            (
                "epic|retired-account|retired-user|"
                "epic-cluster-compute-a100-01|1||"
            ),
            "epic|root||epic-cluster-compute-a100-01|1||",
        ]

        plan = plan_association_changes(
            desired,
            current_rows,
            cluster_name="epic",
        )

        self.assertIn(
            {
                "account": "epic-rl",
                "user": "liuhongbo",
                "partition": "",
                "fairshare": 1,
                "group_tres": "",
            },
            plan["remove_associations"],
        )
        self.assertFalse(
            any(item["account"] == "external" for item in plan["remove_associations"])
        )
        self.assertFalse(
            any(item["account"] == "root" for item in plan["remove_associations"])
        )
        self.assertTrue(
            any(
                item["user"] == "retired-user"
                for item in plan["remove_associations"]
            )
        )
        self.assertTrue(
            any(
                item["account"] == "epic-rl"
                and item["partition"] == "epic-cluster-compute-a100-01"
                and item["group_tres_update"] == "cpu=-1"
                for item in plan["update_associations"]
            )
        )

    def test_running_or_pending_jobs_block_association_removal(self) -> None:
        removals = [
            {
                "account": "epic-rl",
                "user": "liuhongbo",
                "partition": "epic-cluster-compute-rtx4070-01",
            }
        ]
        jobs = [
            "liuhongbo|epic-rl|epic-cluster-compute-rtx4070-01|42|RUNNING"
        ]

        blocked = find_jobs_blocking_removals(removals, jobs)

        self.assertEqual(blocked[0]["job_id"], "42")

    def test_plans_account_metadata_and_user_default_changes(self) -> None:
        desired = build_desired_state(USERS, ACCOUNTS, PARTITIONS)

        account_plan = plan_account_metadata_changes(
            desired,
            ["epic-rl|Old description|old-organization|"],
        )
        user_plan = plan_user_default_changes(
            desired,
            ["liuhongbo|wrong-account|", "yinjiajie|epic-rl|"],
        )

        self.assertEqual(account_plan["add_accounts"][0]["name"], "nue")
        self.assertEqual(account_plan["update_accounts"][0]["name"], "epic-rl")
        self.assertEqual(
            [item["name"] for item in user_plan],
            ["liuhongbo", "wangjiaxiang"],
        )


class SlurmAssociationRoleTests(unittest.TestCase):
    def test_work_package_files_exist(self) -> None:
        expected_files = (
            "vars/slurm_accounts.yml",
            "vars/slurm_partitions.yml",
            "playbooks/slurm_associations.yml",
            "roles/slurm_associations/tasks/main.yml",
            "roles/slurm_associations/tasks/preflight.yml",
            "roles/slurm_associations/tasks/plan.yml",
            "roles/slurm_associations/tasks/converge.yml",
            "roles/slurm_associations/tasks/audit.yml",
        )

        missing = [
            path for path in expected_files if not (ANSIBLE_DIRECTORY / path).is_file()
        ]

        self.assertEqual(missing, [])

    def test_playbook_loads_identity_and_authorization_manifests(self) -> None:
        playbook = read_ansible_file("playbooks/slurm_associations.yml")

        self.assertIn("hosts: controllers", playbook)
        self.assertIn("../vars/users.yml", playbook)
        self.assertIn("../vars/slurm_accounts.yml", playbook)
        self.assertIn("../vars/slurm_partitions.yml", playbook)
        self.assertNotIn("secrets.yml", playbook)

    def test_check_mode_never_writes_slurmdbd(self) -> None:
        converge = read_ansible_file("roles/slurm_associations/tasks/converge.yml")

        self.assertIn("when: not ansible_check_mode", converge)
        self.assertIn("/usr/bin/sacctmgr", converge)

    def test_association_reads_and_updates_use_explicit_limits(self) -> None:
        plan = read_ansible_file("roles/slurm_associations/tasks/plan.yml")
        audit = read_ansible_file("roles/slurm_associations/tasks/audit.yml")
        converge = read_ansible_file("roles/slurm_associations/tasks/converge.yml")

        self.assertIn("WOPLimits", plan)
        self.assertIn("WOPLimits", audit)
        self.assertGreaterEqual(converge.count("item.group_tres_update"), 2)
        self.assertIn("slurm_partition_argument", converge)

    def test_manifest_declares_confirmed_partition_policy(self) -> None:
        partitions = read_ansible_file("vars/slurm_partitions.yml")

        self.assertIn("allowed_users:\n      - liuhongbo", partitions)
        self.assertIn("group_tres: gres/gpu=2", partitions)

        users = read_ansible_file("vars/users.yml")
        cluster_user_section = users.split("access_groups:", maxsplit=1)[0]
        self.assertEqual(
            cluster_user_section.count("slurm_account:"),
            cluster_user_section.count("  - name:"),
        )

        declared_accounts = re.findall(
            r"^  - name: (\S+).*?^    slurm_account: (\S+)$",
            cluster_user_section,
            flags=re.MULTILINE | re.DOTALL,
        )
        account_counts = {}
        for _, account in declared_accounts:
            account_counts[account] = account_counts.get(account, 0) + 1

        self.assertEqual(
            account_counts,
            {
                "epic-rl": 9,
                "individual": 7,
                "cgcl": 3,
                "mllms": 17,
                "cv3d": 6,
                "nue": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
