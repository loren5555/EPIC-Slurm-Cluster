#!/usr/bin/env python3
"""Basic syntax checks for repository-owned Grafana dashboards."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_ROOT = (
    REPOSITORY_ROOT / "ansible/roles/monitoring_grafana/files/dashboards"
)


class GrafanaDashboardTests(unittest.TestCase):
    def test_dashboard_json_can_be_loaded(self) -> None:
        dashboards = sorted(DASHBOARD_ROOT.rglob("*.json"))
        self.assertTrue(dashboards)

        for path in dashboards:
            with self.subTest(path=path.relative_to(DASHBOARD_ROOT)):
                dashboard = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(dashboard, dict)


if __name__ == "__main__":
    unittest.main()
