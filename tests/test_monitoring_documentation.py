#!/usr/bin/env python3
"""Contract tests for the work-package 6 operator procedure."""

from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class MonitoringDocumentationTests(unittest.TestCase):
    def test_installation_uses_current_releases_without_legacy_backups(self) -> None:
        guide = (
            REPOSITORY_ROOT / "docs/slurm-stack-deployment-guide.md"
        ).read_text(encoding="utf-8")
        work_package = guide.split(
            "## 11. 工作包 6：部署 Prometheus 与采集端",
            maxsplit=1,
        )[1].split("## 12. 工作包 7", maxsplit=1)[0]

        self.assertIn("releases/latest", work_package)
        self.assertIn("pip install --upgrade nvitop-exporter", work_package)
        self.assertNotIn("/var/backups/epic-monitoring", work_package)
        self.assertNotIn("node_exporter-1.12.1", work_package)
        self.assertNotIn("prometheus-3.13.2", work_package)
        self.assertNotIn("nvitop-exporter==1.7.1", work_package)

    def test_legacy_monitoring_is_removed_before_new_installation(self) -> None:
        guide = (
            REPOSITORY_ROOT / "docs/slurm-stack-deployment-guide.md"
        ).read_text(encoding="utf-8")
        work_package = guide.split(
            "## 11. 工作包 6：部署 Prometheus 与采集端",
            maxsplit=1,
        )[1].split("## 12. 工作包 7", maxsplit=1)[0]

        for obsolete_item in (
            "slurm-job-exporter.service",
            "/opt/nvitop-exporter",
            "/usr/local/bin/node_exporter",
            "/usr/local/bin/prometheus",
        ):
            self.assertIn(obsolete_item, work_package)

    def test_dcgm_exporter_uses_the_preloaded_container_image(self) -> None:
        guide = (
            REPOSITORY_ROOT / "docs/slurm-stack-deployment-guide.md"
        ).read_text(encoding="utf-8")
        work_package = guide.split(
            "## 11. 工作包 6：部署 Prometheus 与采集端",
            maxsplit=1,
        )[1].split("## 12. 工作包 7", maxsplit=1)[0]

        self.assertIn("nvcr.io/nvidia/k8s/dcgm-exporter:latest", work_package)
        self.assertNotIn("datacenter-gpu-manager-exporter", work_package)


if __name__ == "__main__":
    unittest.main()
