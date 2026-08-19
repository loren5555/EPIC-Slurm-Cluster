#!/usr/bin/env python3
"""Contract tests for the EPIC Open OnDemand deployment."""

from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_DIRECTORY = REPOSITORY_ROOT / "ansible"
APPS_DIRECTORY = REPOSITORY_ROOT / "apps"


def read_repository_file(relative_path: str) -> str:
    """Read one UTF-8 source file from the repository."""

    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def read_ansible_file(relative_path: str) -> str:
    """Read one UTF-8 Ansible source file from the repository."""

    return (ANSIBLE_DIRECTORY / relative_path).read_text(encoding="utf-8")


class OODRoleTests(unittest.TestCase):
    def test_work_package_files_exist(self) -> None:
        expected_files = (
            "inventory/group_vars/all/ood.yml",
            "playbooks/ood.yml",
            "roles/ood_controller/tasks/main.yml",
            "roles/ood_controller/handlers/main.yml",
            "roles/ood_controller/templates/ood_portal.yml.j2",
            "roles/ood_controller/templates/epic.yml.j2",
            "roles/ood_controller/templates/ondemand.yml.j2",
            "roles/ood_controller/templates/dashboard.env.j2",
            "roles/ood_controller/templates/myjobs.env.j2",
            "roles/ood_controller/templates/epic-ood.exports.j2",
            "roles/ood_controller/templates/openssl.cnf.j2",
            "roles/ood_controller/templates/ondemand_exporter.service.j2",
            "roles/ood_compute/tasks/main.yml",
            "roles/ood_compute/templates/srv-epic-ood.mount.j2",
            "roles/ood_compute/templates/srv-epic-ood.automount.j2",
            "roles/ood_apps/tasks/main.yml",
            "roles/ood_apps/templates/partitions.yml.j2",
            "roles/ood_apps/templates/rclone-remotes.ini.j2",
        )

        missing = [
            path for path in expected_files if not (ANSIBLE_DIRECTORY / path).is_file()
        ]
        self.assertEqual(missing, [])

    def test_ood_policy_is_explicit_and_uses_manual_installation(self) -> None:
        variables = read_ansible_file("inventory/group_vars/all/ood.yml")
        playbook = read_ansible_file("playbooks/ood.yml")
        site = read_ansible_file("playbooks/site.yml")

        for policy in (
            "ood_server_address: epic-cluster-controller-01",
            "ood_shared_root: /srv/epic/ood",
            "ood_interactive_maximum_hours: 32",
            "ood_session_retention_days: 30",
            "ood_exporter_port: 9301",
        ):
            self.assertIn(policy, variables)

        self.assertLess(playbook.index("role: ood_controller"), playbook.index("role: ood_compute"))
        self.assertIn("role: ood_apps", playbook)
        self.assertIn("import_playbook: ood.yml", site)

        combined_roles = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ANSIBLE_DIRECTORY / "roles").rglob("*.yml")
            if "ood_" in str(path)
        )
        self.assertNotIn("ansible.builtin.apt", combined_roles)
        self.assertNotIn("ansible.builtin.package", combined_roles)

    def test_controller_configuration(self) -> None:
        tasks = read_ansible_file("roles/ood_controller/tasks/main.yml")
        handlers = read_ansible_file("roles/ood_controller/handlers/main.yml")
        portal = read_ansible_file("roles/ood_controller/templates/ood_portal.yml.j2")
        cluster = read_ansible_file("roles/ood_controller/templates/epic.yml.j2")
        dashboard = read_ansible_file("roles/ood_controller/templates/ondemand.yml.j2")
        dashboard_env = read_ansible_file("roles/ood_controller/templates/dashboard.env.j2")
        myjobs_env = read_ansible_file("roles/ood_controller/templates/myjobs.env.j2")
        tls = read_ansible_file("roles/ood_controller/templates/openssl.cnf.j2")
        exports = read_ansible_file("roles/ood_controller/templates/epic-ood.exports.j2")
        exporter = read_ansible_file("roles/ood_controller/templates/ondemand_exporter.service.j2")

        self.assertIn('/etc/ood/auth/htpasswd', portal)
        self.assertIn("AuthType Basic", portal)
        self.assertIn('AuthName "EPIC Open OnDemand"', portal)
        self.assertIn("servername: \"{{ ood_server_address }}\"", portal)
        self.assertIn("host_regex:", portal)
        self.assertIn("subjectAltName", tls)
        self.assertIn("DNS.1 = {{ ood_server_address }}", tls)

        self.assertIn('adapter: "slurm"', cluster)
        self.assertIn('submit_host: "{{ slurm_controller_host }}"', cluster)
        self.assertIn('conf: "/etc/slurm/slurm.conf"', cluster)
        self.assertIn("ssh_allow: false", cluster)

        self.assertIn("remote_files_enabled: true", dashboard)
        self.assertIn("remote_files_validation: false", dashboard)
        self.assertIn("files_enable_shell_button: false", dashboard)
        self.assertIn("disable_bc_shell: true", dashboard)
        self.assertIn("bc_clean_old_dirs: true", dashboard)

        self.assertIn("{{ ood_dashboard_dataroot }}", dashboard_env)
        self.assertIn("{{ ood_myjobs_dataroot }}", myjobs_env)
        self.assertIn("{{ ood_shared_root }}", exports)
        self.assertIn("ondemand_exporter", exporter)
        self.assertIn("{{ ood_exporter_port }}", exporter)

        self.assertIn("update_ood_portal", handlers)
        self.assertIn("force: false", tasks)
        self.assertIn("cluster_users", tasks)

    def test_quota_reports_are_independent_per_compute_host(self) -> None:
        variables = read_ansible_file("inventory/group_vars/all/ood.yml")
        collector = read_ansible_file(
            "roles/disk_quota/templates/epic-disk-quota-collector.py.j2"
        )
        dashboard_env = read_ansible_file(
            "roles/ood_controller/templates/dashboard.env.j2"
        )

        self.assertIn("ood_quota_directory:", variables)
        self.assertIn("inventory_hostname", collector)
        self.assertIn('"host": HOST', collector)
        self.assertIn("OOD_QUOTA_DIRECTORY", dashboard_env)

    def test_quota_preflight_uses_user_quota_state_not_aggregate_exit_code(self) -> None:
        tasks = read_ansible_file("roles/disk_quota/tasks/main.yml")

        self.assertNotIn("disk_quota_status.rc != 0", tasks)
        self.assertIn("select('match', '^user quota on .* is on$')", tasks)

    def test_quota_widget_aggregates_hosts_and_marks_stale_reports(self) -> None:
        widget = read_ansible_file(
            "roles/ood_controller/templates/epic_disk_quota_status.html.erb.j2"
        )

        self.assertIn('Dir.glob(File.join(ENV.fetch("OOD_QUOTA_DIRECTORY"), "*.json"))', widget)
        self.assertIn('quota["host"]', widget)
        self.assertIn("OOD_QUOTA_STALE_SECONDS", widget)
        self.assertIn("数据已过期", widget)

    def test_compute_context_uses_automount(self) -> None:
        tasks = read_ansible_file("roles/ood_compute/tasks/main.yml")
        mount = read_ansible_file("roles/ood_compute/templates/srv-epic-ood.mount.j2")
        automount = read_ansible_file("roles/ood_compute/templates/srv-epic-ood.automount.j2")

        self.assertIn("groups['ood_servers'][0]", mount)
        self.assertIn("_netdev", mount)
        self.assertIn("nofail", mount)
        self.assertNotIn("soft", mount)
        self.assertIn("TimeoutIdleSec", automount)
        self.assertIn("srv-epic-ood.automount", tasks)
        self.assertNotIn("ansible.builtin.apt", tasks)

    def test_generated_user_interfaces_follow_authoritative_manifests(self) -> None:
        tasks = read_ansible_file("roles/ood_apps/tasks/main.yml")
        partitions = read_ansible_file("roles/ood_apps/templates/partitions.yml.j2")
        rclone = read_ansible_file("roles/ood_apps/templates/rclone-remotes.ini.j2")
        grafana = read_repository_file("apps/LINK_grafana/manifest.yml")
        a100 = read_ansible_file("inventory/host_vars/epic-cluster-compute-a100-01.yml")
        rtx4070 = read_ansible_file("inventory/host_vars/epic-cluster-compute-rtx4070-01.yml")

        for source in ("slurm_partitions", "cluster_users", "hostvars"):
            self.assertIn(source, partitions)
        self.assertIn("allowed_users:", partitions)
        self.assertIn("slurm_cpus", partitions)
        self.assertIn("slurm_real_memory", partitions)
        self.assertIn("slurm_gpu_count", partitions)

        self.assertIn("ssh_access", rclone)
        self.assertIn("blockinfile", tasks)
        self.assertIn("type = sftp", rclone)
        self.assertIn("epic_cluster_ed25519", rclone)
        self.assertIn("ood_display_name", a100)
        self.assertIn("ood_display_name", rtx4070)

        self.assertNotIn("ansible.builtin.lineinfile", tasks)
        self.assertNotIn("item != 'LINK_grafana'", tasks)
        self.assertIn("url: http://epic-cluster-controller-01:3000", grafana)

    def test_prometheus_collects_the_ood_exporter_at_the_slow_interval(self) -> None:
        variables = read_ansible_file("inventory/group_vars/all/monitoring.yml")
        prometheus = read_ansible_file(
            "roles/monitoring_prometheus/templates/prometheus.yml.j2"
        )

        self.assertIn("monitoring_ood_exporter_port: 9301", variables)
        self.assertIn("job_name: open-ondemand", prometheus)
        self.assertIn("monitoring_slurm_state_scrape_interval", prometheus)
        self.assertIn("monitoring_ood_exporter_port", prometheus)


class OODApplicationTests(unittest.TestCase):
    APPLICATIONS = (
        "IAPP_jupyter",
        "IAPP_codeserver",
        "IAPP_ttyd",
        "IAPP_tensorboard",
        "IAPP_script",
    )

    def test_forms_use_the_shared_host_resource_contract(self) -> None:
        for application in self.APPLICATIONS:
            form = (APPS_DIRECTORY / application / "form.yml.erb").read_text(encoding="utf-8")
            submit = (APPS_DIRECTORY / application / "submit.yml.erb").read_text(encoding="utf-8")

            with self.subTest(application=application):
                self.assertIn("/etc/ood/config/site.d/partitions.yml", form)
                self.assertIn("allowed_users", form)
                self.assertIn("resource_partition", form)
                self.assertIn("extra_sbatch", form)
                self.assertIn("memory", form)
                self.assertIn("max: 32", form)
                self.assertNotIn("mail_user", form)
                self.assertNotIn("mail_type", form)
                self.assertNotIn("@hust.edu.cn", form)
                self.assertIn("queue_name", submit)
                self.assertIn("--time=", submit)
                self.assertIn("--mem=", submit)
                self.assertIn("extra_sbatch", submit)

    def test_forms_adjust_resource_fields_for_the_selected_host(self) -> None:
        for application in self.APPLICATIONS:
            form = (APPS_DIRECTORY / application / "form.yml.erb").read_text(
                encoding="utf-8"
            )

            cpu_field = "cpus-per-task" if application == "IAPP_script" else "cpus"
            gpu_field = "gpus-per-task" if application == "IAPP_script" else "gpus"

            with self.subTest(application=application):
                self.assertIn("config['cpu_max']", form)
                self.assertIn("config['gpu_max']", form)
                self.assertIn("config['mem_max_gb']", form)
                self.assertIn(f"data-max-{cpu_field}", form)
                self.assertIn(f"data-hide-{gpu_field}", form)
                self.assertIn(f"data-max-{gpu_field}", form)
                self.assertIn(f"data-set-{gpu_field}", form)
                self.assertIn("data-max-memory", form)
                self.assertIn("data-set-gpus", form.replace("-per-task", ""))
                self.assertNotIn("data-max-bc-num-hours", form)

    def test_apps_do_not_reference_the_old_controller_or_fixed_runtime_versions(self) -> None:
        all_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in APPS_DIRECTORY.rglob("*")
            if path.is_file() and path.suffix in {".erb", ".yml", ".md", ".sh"}
        )

        self.assertNotIn("epic-control-node", all_text)
        self.assertNotIn("code-server-4.104.2", all_text)
        self.assertNotIn("@hust.edu.cn", all_text)

    def test_job_composer_templates_cover_basic_gpu_and_array_jobs(self) -> None:
        template_root = ANSIBLE_DIRECTORY / "roles/ood_apps/files/job_templates"
        for name in ("basic", "gpu", "array"):
            with self.subTest(name=name):
                self.assertTrue((template_root / name / "manifest.yml").is_file())
                self.assertTrue((template_root / name / "job.sh").is_file())


class OODDocumentationTests(unittest.TestCase):
    def test_work_package_contains_the_complete_operator_procedure(self) -> None:
        guide = read_repository_file("docs/slurm-stack-deployment-guide.md")
        work_package = guide.split("## 13. 工作包 8：接入 OOD", maxsplit=1)[1].split(
            "## 14. 新增计算节点流程", maxsplit=1
        )[0]

        for required in (
            "Open OnDemand 4.2",
            "Ubuntu 26.04",
            "ondemand_exporter",
            "rclone",
            "/srv/epic/ood",
            "htpasswd",
            "ansible-vault",
            "ansible-playbook playbooks/ood.yml",
            "32 小时",
            "Remote Files",
        ):
            self.assertIn(required, work_package)

        self.assertTrue((REPOSITORY_ROOT / "docs/ood-compute-runtime.md").is_file())


if __name__ == "__main__":
    unittest.main()
