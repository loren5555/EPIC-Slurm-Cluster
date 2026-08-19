#!/usr/bin/env python3
"""Contract tests for the managed EPIC SSH client configuration."""

from __future__ import annotations

import unittest
from pathlib import Path


ANSIBLE_ROOT = Path(__file__).resolve().parents[1] / "ansible"


class SSHAccessRoleTests(unittest.TestCase):
    def test_managed_client_config_is_present_and_uses_cluster_key(self) -> None:
        distribute = (ANSIBLE_ROOT / "roles/ssh_access/tasks/distribute.yml").read_text(
            encoding="utf-8"
        )
        template = (
            ANSIBLE_ROOT / "roles/ssh_access/templates/client_config.j2"
        ).read_text(encoding="utf-8")

        self.assertIn("blockinfile", distribute)
        self.assertIn(".ssh/config", distribute)
        self.assertIn('mode: "0600"', distribute)
        self.assertIn("groups['controllers']", template)
        self.assertIn("ssh_access", template)
        self.assertIn("IdentityFile ~/.ssh/epic_cluster_ed25519", template)
        self.assertIn("IdentitiesOnly yes", template)
        self.assertIn("StrictHostKeyChecking accept-new", template)


if __name__ == "__main__":
    unittest.main()
