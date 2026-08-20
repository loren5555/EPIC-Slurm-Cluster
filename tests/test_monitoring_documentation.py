#!/usr/bin/env python3
"""Contract tests for the work-package 6 operator procedure."""

from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class MonitoringDocumentationTests(unittest.TestCase):
    def test_monitoring_document_describes_manual_install_boundary(self) -> None:
        guide = (REPOSITORY_ROOT / "docs/admin/monitoring.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("手工准备", guide)
        self.assertIn("Ansible 管理配置", guide)
        self.assertIn("180 天", guide)
        self.assertIn("100GB", guide)

    def test_legacy_monitoring_is_removed_before_new_installation(self) -> None:
        guide = (REPOSITORY_ROOT / "docs/admin/monitoring.md").read_text(
            encoding="utf-8"
        )

        for component in ("node_exporter", "DCGM Exporter", "nvitop-exporter"):
            self.assertIn(component, guide)

    def test_dcgm_exporter_uses_the_preloaded_container_image(self) -> None:
        guide = (REPOSITORY_ROOT / "docs/admin/monitoring.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("DCGM Exporter", guide)
        self.assertNotIn("datacenter-gpu-manager-exporter", guide)


if __name__ == "__main__":
    unittest.main()
