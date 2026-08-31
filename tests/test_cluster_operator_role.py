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

    def test_sudoers_accepts_any_ood_username_for_fixed_password_file(self) -> None:
        template = read_ansible_file(
            "roles/cluster_operator/templates/epic-operators.sudoers.j2"
        )

        self.assertIn("/usr/bin/ansible-playbook", template)
        self.assertIn("'users.yml'", template)
        self.assertIn("'ood.yml'", template)
        self.assertNotIn("'site.yml'", template)
        self.assertIn(
            "/usr/bin/htpasswd {{ ood_authentication_file }} *",
            template,
        )
        self.assertNotIn("^[a-z_][a-z0-9_.-]*$", template)
        self.assertNotIn("cluster_users | map(attribute='name')", template)
        self.assertIn("NOPASSWD: EPIC_GIT, EPIC_ANSIBLE, EPIC_OOD_PASSWORD", template)
        self.assertIn("%epic-superadmins ALL=(ALL:ALL) ALL", template)

    def test_user_onboarding_includes_all_noninteractive_user_configuration(
        self,
    ) -> None:
        playbook = read_ansible_file("playbooks/user_onboarding.yml")
        imports = (
            "users.yml",
            "ssh_access.yml",
            "slurm_associations.yml",
            "disk_quotas.yml",
            "ood.yml",
        )

        expected_sequence = "\n".join(
            f"- import_playbook: {playbook_name}" for playbook_name in imports
        )

        self.assertIn(expected_sequence, playbook)

    def test_role_converges_three_slurm_administration_levels(self) -> None:
        tasks = read_ansible_file("roles/cluster_operator/tasks/main.yml")
        normalized_tasks = " ".join(tasks.split())

        self.assertIn("/usr/bin/sacctmgr", tasks)
        self.assertIn("AdminLevel=Administrator", tasks)
        self.assertIn("AdminLevel=Operator", tasks)
        self.assertIn("AdminLevel=None", tasks)
        self.assertIn('loop: "{{ epic_superadministrators }}"', tasks)
        self.assertIn(
            'loop: "{{ epic_operators | difference(epic_superadministrators) | sort }}"',
            tasks,
        )
        self.assertIn(
            "difference(epic_operators) | difference(epic_superadministrators)",
            normalized_tasks,
        )
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
