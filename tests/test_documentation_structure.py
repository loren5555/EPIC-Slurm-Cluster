#!/usr/bin/env python3
"""Contract tests for the published documentation structure."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = REPOSITORY_ROOT / "docs"


class DocumentationStructureTests(unittest.TestCase):
    def read_front_matter(self, relative_path: str) -> dict[str, str]:
        text = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"), relative_path)
        raw_front_matter = text.split("---", maxsplit=2)[1]
        return {
            key.strip(): value.strip()
            for line in raw_front_matter.strip().splitlines()
            for key, value in (line.split(":", maxsplit=1),)
        }

    def test_just_the_docs_theme_uses_builtin_github_pages(self) -> None:
        configuration = (REPOSITORY_ROOT / "_config.yml").read_text(
            encoding="utf-8"
        )

        for declaration in (
            "remote_theme: just-the-docs/just-the-docs@v0.12.0",
            "- jekyll-remote-theme",
            "search_enabled: true",
            "nav_enabled: true",
            "https://github.com/loren5555/EPIC-Slurm-Cluster",
            "- docs/superpowers",
        ):
            self.assertIn(declaration, configuration)

        self.assertNotIn("jekyll-theme-minimal", configuration)
        self.assertFalse((REPOSITORY_ROOT / ".github/workflows").exists())

    def test_just_the_docs_sidebar_hierarchy(self) -> None:
        expected_pages = {
            "README.md": ("EPIC 集群", "", "1", ""),
            "docs/index.md": ("文档导航", "", "2", ""),
            "docs/user/index.md": ("用户文档", "", "3", "true"),
            "docs/user/quick-start.md": ("快速开始", "用户文档", "1", ""),
            "docs/user/jobs.md": ("提交任务", "用户文档", "2", ""),
            "docs/user/queue.md": ("排队与优先级", "用户文档", "3", ""),
            "docs/user/storage.md": ("存储与运行环境", "用户文档", "4", ""),
            "docs/user/etc.md": ("其它功能", "用户文档", "5", ""),
            "docs/user/troubleshooting.md": ("用户排障", "用户文档", "6", ""),
            "docs/admin/index.md": ("管理员文档", "", "4", "true"),
            "docs/admin/users.md": ("用户管理", "管理员文档", "1", ""),
            "docs/admin/jobs.md": ("任务管理", "管理员文档", "2", ""),
            "docs/admin/commands.md": ("管理员可用命令", "管理员文档", "3", ""),
            "docs/developer/index.md": ("开发者文档", "", "5", "true"),
            "docs/developer/repository.md": ("仓库与变更规则", "开发者文档", "1", ""),
            "docs/developer/ansible.md": ("Ansible 架构", "开发者文档", "2", ""),
            "docs/developer/apps.md": ("IAPP 开发", "开发者文档", "3", ""),
            "docs/developer/documentation.md": ("文档维护", "开发者文档", "4", ""),
            "docs/developer/operations.md": ("系统运维", "开发者文档", "5", ""),
            "docs/developer/superadmin.md": ("超级管理员操作", "开发者文档", "6", ""),
        }

        for path, (title, parent, order, has_children) in expected_pages.items():
            with self.subTest(path=path):
                metadata = self.read_front_matter(path)
                self.assertEqual(metadata.get("layout"), "default")
                self.assertEqual(metadata.get("title"), title)
                self.assertEqual(metadata.get("nav_order"), order)
                self.assertEqual(metadata.get("parent", ""), parent)
                self.assertEqual(metadata.get("has_children", ""), has_children)

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
