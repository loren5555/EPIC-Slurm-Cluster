#!/usr/bin/env python3
"""Contract tests for EPIC cluster operator administration."""

from __future__ import annotations

import unittest
from pathlib import Path


ANSIBLE_DIRECTORY = Path(__file__).resolve().parents[1] / "ansible"


def read_ansible_file(relative_path: str) -> str:
    """Read one Ansible source file as UTF-8."""

    return (ANSIBLE_DIRECTORY / relative_path).read_text(encoding="utf-8")


class ClusterOperatorRoleTests(unittest.TestCase):
    def test_operator_manifest_and_playbook_are_declared(self) -> None:
        manifest = read_ansible_file("vars/administrators.yml")
        playbook = read_ansible_file("playbooks/administrators.yml")

        self.assertIn("epic_superadministrators:", manifest)
        self.assertIn("epic_operators:", manifest)
        self.assertIn("liuhongbo", manifest)
        self.assertIn("cluster_operator", playbook)

    def test_sudoers_uses_fixed_playbooks_and_managed_ood_users(self) -> None:
        template = read_ansible_file(
            "roles/cluster_operator/templates/epic-operators.sudoers.j2"
        )

        self.assertIn("/usr/bin/ansible-playbook", template)
        self.assertIn("'users.yml'", template)
        self.assertIn("'ood.yml'", template)
        self.assertNotIn("'site.yml'", template)
        self.assertIn("/usr/bin/htpasswd", template)
        self.assertIn("cluster_users", template)
        self.assertIn("NOPASSWD: EPIC_GIT, EPIC_ANSIBLE, EPIC_OOD_PASSWORD", template)
        self.assertIn("%epic-superadmins ALL=(ALL:ALL) ALL", template)

    def test_role_grants_declared_operators_slurm_operator_level(self) -> None:
        tasks = read_ansible_file("roles/cluster_operator/tasks/main.yml")

        self.assertIn("/usr/bin/sacctmgr", tasks)
        self.assertIn("AdminLevel=Operator", tasks)
        self.assertIn("AdminLevel=None", tasks)
        self.assertIn("epic_operators", tasks)
        self.assertIn("difference(epic_operators)", tasks)
        self.assertIn("gpasswd", tasks)
        self.assertNotIn("groups: epic-superadmins,sudo", tasks)

    def test_full_site_imports_administrator_convergence_after_slurm_policy(self) -> None:
        site = read_ansible_file("playbooks/site.yml")

        self.assertIn("import_playbook: administrators.yml", site)
        self.assertGreater(
            site.index("import_playbook: administrators.yml"),
            site.index("import_playbook: slurm_associations.yml"),
        )


if __name__ == "__main__":
    unittest.main()
