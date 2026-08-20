#!/usr/bin/env python3
"""Contract tests for the published documentation structure."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = REPOSITORY_ROOT / "docs"


class DocumentationStructureTests(unittest.TestCase):
    def test_public_entry_points_link_to_the_three_reader_groups(self) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
        index = (DOCUMENT_ROOT / "index.md").read_text(encoding="utf-8")

        for path in (
            "docs/user/index.md",
            "docs/admin/index.md",
            "docs/developer/index.md",
        ):
            self.assertIn(path, readme)

        for path in ("user/index.md", "admin/index.md", "developer/index.md"):
            self.assertIn(path, index)

    def test_reader_pages_exist(self) -> None:
        expected_pages = (
            "user/index.md",
            "user/quick-start.md",
            "user/jobs.md",
            "user/storage.md",
            "user/etc.md",
            "user/troubleshooting.md",
            "admin/index.md",
            "admin/operations.md",
            "admin/deployment.md",
            "admin/access.md",
            "admin/monitoring.md",
            "admin/ood.md",
            "developer/index.md",
            "developer/repository.md",
            "developer/ansible.md",
            "developer/apps.md",
            "developer/documentation.md",
        )

        for relative_path in expected_pages:
            with self.subTest(path=relative_path):
                self.assertTrue((DOCUMENT_ROOT / relative_path).is_file())

    def test_process_plans_and_removed_entries_are_not_published(self) -> None:
        self.assertFalse(any((DOCUMENT_ROOT / "superpowers/plans").glob("*.md")))
        for removed in (
            "deployment.md",
            "quick_start.md",
            "sbatch.md",
            "developer_doc.md",
            "ood-compute-runtime.md",
            "slurm-stack-deployment-guide.md",
        ):
            self.assertFalse((DOCUMENT_ROOT / removed).exists())

    def test_markdown_does_not_reference_removed_assets_or_external_notes(self) -> None:
        markdown = "\n".join(
            path.read_text(encoding="utf-8")
            for path in DOCUMENT_ROOT.rglob("*.md")
        )

        self.assertNotRegex(markdown, re.compile(r"notion\.[a-z.]+", re.IGNORECASE))
        self.assertNotRegex(markdown, re.compile(r"!\[[^]]*\]\([^)]*image(?:-1)?\.png\)"))


if __name__ == "__main__":
    unittest.main()
