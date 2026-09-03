#!/usr/bin/env python3
"""Contract tests for Open OnDemand portal IP access."""

from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class OodIpAccessTests(unittest.TestCase):
    def test_campus_ip_is_declared_once_and_consumed_by_portal_and_tls(self) -> None:
        inventory = (
            REPOSITORY_ROOT / "ansible/inventory/group_vars/all/ood.yml"
        ).read_text(encoding="utf-8")
        portal = (
            REPOSITORY_ROOT
            / "ansible/roles/ood_controller/templates/ood_portal.yml.j2"
        ).read_text(encoding="utf-8")
        openssl = (
            REPOSITORY_ROOT
            / "ansible/roles/ood_controller/templates/openssl.cnf.j2"
        ).read_text(encoding="utf-8")

        self.assertIn("ood_server_address: epic-cluster-controller-01", inventory)
        self.assertIn("ood_server_ip_addresses:", inventory)
        self.assertIn('  - "222.20.99.125"', inventory)
        self.assertIn("server_aliases:", portal)
        self.assertIn("for address in ood_server_ip_addresses", portal)
        self.assertIn("for address in ood_server_ip_addresses", openssl)
        self.assertIn("IP.{{ loop.index }} = {{ address }}", openssl)
        self.assertIn(
            'host_regex: "epic-cluster-(controller|compute)-[a-z0-9-]+"',
            portal,
        )


if __name__ == "__main__":
    unittest.main()
