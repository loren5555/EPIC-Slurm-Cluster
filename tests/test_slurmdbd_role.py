#!/usr/bin/env python3
"""Configuration contracts for the MariaDB and SlurmDBD work package."""

from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_DIRECTORY = REPOSITORY_ROOT / "ansible"


def read_ansible_file(relative_path: str) -> str:
    """Read one UTF-8 Ansible source file from the repository."""

    return (ANSIBLE_DIRECTORY / relative_path).read_text(encoding="utf-8")


class SlurmdbdRoleTests(unittest.TestCase):
    def test_work_package_files_exist(self) -> None:
        expected_files = (
            "inventory/group_vars/all/slurm_accounting.yml",
            "playbooks/slurmdbd.yml",
            "roles/slurmdbd/handlers/main.yml",
            "roles/slurmdbd/tasks/main.yml",
            "roles/slurmdbd/tasks/database.yml",
            "roles/slurmdbd/tasks/verify.yml",
            "roles/slurmdbd/templates/60-slurmdbd.cnf.j2",
            "roles/slurmdbd/templates/slurmdbd.conf.j2",
            "vars/secrets.example.yml",
        )

        missing = [
            path
            for path in expected_files
            if not (ANSIBLE_DIRECTORY / path).is_file()
        ]

        self.assertEqual(missing, [])

    def test_playbook_targets_only_controllers_and_loads_the_vault(self) -> None:
        playbook = read_ansible_file("playbooks/slurmdbd.yml")
        site_playbook = read_ansible_file("playbooks/site.yml")

        self.assertIn("hosts: controllers", playbook)
        self.assertIn("../vars/secrets.yml", playbook)
        self.assertIn("- slurmdbd", playbook)
        self.assertIn("import_playbook: slurmdbd.yml", site_playbook)

    def test_database_is_local_and_uses_conservative_settings(self) -> None:
        template = read_ansible_file(
            "roles/slurmdbd/templates/60-slurmdbd.cnf.j2"
        )

        self.assertIn("bind-address = 127.0.0.1", template)
        self.assertIn("innodb_buffer_pool_size = {{ mariadb_innodb_buffer_pool_size }}", template)
        self.assertIn("innodb_lock_wait_timeout = {{ mariadb_innodb_lock_wait_timeout }}", template)
        self.assertIn("max_allowed_packet = {{ mariadb_max_allowed_packet }}", template)

        variables = read_ansible_file(
            "inventory/group_vars/all/slurm_accounting.yml"
        )
        self.assertIn("mariadb_innodb_buffer_pool_size: 4G", variables)
        self.assertIn("mariadb_innodb_lock_wait_timeout: 900", variables)
        self.assertIn("mariadb_max_allowed_packet: 16M", variables)

    def test_slurmdbd_uses_munge_and_local_mariadb(self) -> None:
        template = read_ansible_file("roles/slurmdbd/templates/slurmdbd.conf.j2")

        expected_settings = (
            "AuthType=auth/munge",
            "DbdHost={{ slurmdbd_host }}",
            "SlurmUser=slurm",
            "StorageType=accounting_storage/mysql",
            "StorageHost=localhost",
            "StorageLoc={{ slurmdbd_database_name }}",
            "StorageUser={{ slurmdbd_database_user }}",
            "StoragePass={{ slurmdbd_storage_password }}",
            "LogFile=/var/log/slurm/slurmdbd.log",
            "PidFile=/run/slurmdbd/slurmdbd.pid",
        )

        for setting in expected_settings:
            self.assertIn(setting, template)

    def test_role_does_not_modify_controller_accounting_policy(self) -> None:
        role_files = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ANSIBLE_DIRECTORY / "roles" / "slurmdbd").rglob("*")
            if path.is_file()
        )

        self.assertNotIn("AccountingStorageType=", role_files)
        self.assertNotIn("AccountingStorageEnforce=", role_files)
        self.assertNotIn("sacctmgr add", role_files)

    def test_role_does_not_install_or_upgrade_packages(self) -> None:
        role_files = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ANSIBLE_DIRECTORY / "roles" / "slurmdbd").rglob("*")
            if path.is_file()
        )

        forbidden_package_actions = (
            "ansible.builtin.apt",
            "ansible.builtin.package",
            "apt-get",
            "apt install",
        )

        for package_action in forbidden_package_actions:
            self.assertNotIn(package_action, role_files)


if __name__ == "__main__":
    unittest.main()
