#!/usr/bin/env python3
"""Tests for read-only identity conflict detection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "ansible" / "filter_plugins"))

from identity import identity_conflicts  # noqa: E402


class IdentityConflictTests(unittest.TestCase):
    def setUp(self) -> None:
        self.users = [
            {"name": "liuhongbo", "uid": 10000, "gid": 10000},
            {"name": "huodongkun", "uid": 10004, "gid": 10004},
        ]
        self.access_groups = [{"name": "EPIC-RL", "gid": 20000}]
        self.passwd = {
            "administrator": ["x", "1000", "1000", "", "/home/administrator", "/bin/bash"],
            "liuhongbo": ["x", "10000", "10000", "", "/home/liuhongbo", "/bin/bash"],
        }
        self.groups = {
            "administrator": ["x", "1000", ""],
            "liuhongbo": ["x", "10000", ""],
            "EPIC-RL": ["x", "20000", "liuhongbo"],
        }

    def test_accepts_missing_identities_and_exact_existing_identities(self) -> None:
        conflicts = identity_conflicts(
            self.users,
            self.access_groups,
            self.passwd,
            self.groups,
        )

        self.assertEqual(conflicts, [])

    def test_accepts_duplicate_nss_records_with_the_same_numeric_id(self) -> None:
        self.groups["gdm"] = [
            ["x", "975", ""],
            ["x", "975", "gdm-greeter"],
        ]

        conflicts = identity_conflicts(
            self.users,
            self.access_groups,
            self.passwd,
            self.groups,
        )

        self.assertEqual(conflicts, [])

    def test_reports_name_and_numeric_conflicts_together(self) -> None:
        self.passwd["huodongkun"] = [
            "x",
            "1011",
            "1011",
            "",
            "/home/huodongkun",
            "/bin/bash",
        ]
        self.passwd["unexpected-user"] = [
            "x",
            "10004",
            "10004",
            "",
            "/home/unexpected-user",
            "/bin/bash",
        ]
        self.groups["huodongkun"] = ["x", "1011", ""]
        self.groups["unexpected-group"] = ["x", "10004", ""]

        conflicts = identity_conflicts(
            self.users,
            self.access_groups,
            self.passwd,
            self.groups,
        )

        self.assertEqual(len(conflicts), 4)
        self.assertTrue(any("user huodongkun" in conflict and "1011:1011" in conflict for conflict in conflicts))
        self.assertTrue(any("UID 10004" in conflict and "unexpected-user" in conflict for conflict in conflicts))
        self.assertTrue(any("group huodongkun" in conflict and "GID 1011" in conflict for conflict in conflicts))
        self.assertTrue(any("GID 10004" in conflict and "unexpected-group" in conflict for conflict in conflicts))

    def test_reports_access_group_conflicts(self) -> None:
        self.groups["EPIC-RL"] = ["x", "22222", ""]
        self.groups["other-laboratory"] = ["x", "20000", ""]

        conflicts = identity_conflicts(
            self.users,
            self.access_groups,
            self.passwd,
            self.groups,
        )

        self.assertEqual(len(conflicts), 2)
        self.assertTrue(any("group EPIC-RL" in conflict and "GID 22222" in conflict for conflict in conflicts))
        self.assertTrue(any("GID 20000" in conflict and "other-laboratory" in conflict for conflict in conflicts))


if __name__ == "__main__":
    unittest.main()
