#!/usr/bin/env python3
"""Behavior tests for monitoring data parsing."""

from __future__ import annotations

import runpy
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class MonitoringCollectorTests(unittest.TestCase):
    def test_slurm_usage_collector_parses_generic_and_typed_gpu_tres(self) -> None:
        collector_path = (
            REPOSITORY_ROOT
            / "ansible/roles/monitoring_prometheus/templates"
            / "epic-slurm-usage-collector.py.j2"
        )
        collector = runpy.run_path(str(collector_path))

        gpu_count = collector["gpu_count_from_tres"]
        gres_count = collector["gpu_count_from_gres"]

        self.assertEqual(gpu_count("cpu=4,mem=8G,gres/gpu=2,gres/gpu:a100=2"), 2)
        self.assertEqual(gpu_count("cpu=4,gres/gpu:a100=2"), 2)
        self.assertEqual(gres_count("gpu:a100-sxm4:8(S:0-1)"), 8)
        self.assertEqual(gres_count("gpu:1(S:0)"), 1)


if __name__ == "__main__":
    unittest.main()
