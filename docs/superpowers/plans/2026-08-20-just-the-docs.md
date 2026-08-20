# Just the Docs Minimal Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current GitHub Pages minimal theme with Just the Docs and add a two-level sidebar without adding a custom Pages workflow.

**Architecture:** Continue using GitHub Pages' branch-based Jekyll build. Configure a pinned remote theme in `_config.yml`, then use YAML front matter on the existing Markdown files to define the three reader groups and their child pages.

**Tech Stack:** GitHub Pages, Jekyll, Just the Docs, Python `unittest`

---

### Task 1: Define and configure the theme

**Files:**
- Modify: `_config.yml`
- Modify: `tests/test_documentation_structure.py`

- [ ] **Step 1: Add a failing theme contract test**

Add `test_just_the_docs_theme_uses_builtin_github_pages` and assert that `_config.yml` contains the pinned `remote_theme`, `jekyll-remote-theme` plugin, enabled navigation and search, repository link, and `docs/superpowers` exclusion. Also assert that no workflow file is introduced.

- [ ] **Step 2: Run the focused test and confirm it fails**

```powershell
python -m unittest tests.test_documentation_structure.DocumentationStructureTests.test_just_the_docs_theme_uses_builtin_github_pages
```

Expected: failure because `_config.yml` still declares `jekyll-theme-minimal`.

- [ ] **Step 3: Replace the Jekyll configuration**

Use this configuration:

```yaml
title: EPIC 集群文档
description: EPIC Slurm Cluster 使用与维护文档
url: https://loren5555.github.io
baseurl: /EPIC-Slurm-Cluster
remote_theme: just-the-docs/just-the-docs@v0.12.0
plugins:
  - jekyll-remote-theme
color_scheme: light
search_enabled: true
nav_enabled: true
aux_links:
  GitHub 仓库:
    - https://github.com/loren5555/EPIC-Slurm-Cluster
exclude:
  - docs/superpowers
```

### Task 2: Define the sidebar hierarchy

**Files:**
- Modify: `README.md`
- Modify: `docs/index.md`
- Modify: `docs/user/*.md`
- Modify: `docs/admin/*.md`
- Modify: `docs/developer/*.md`
- Modify: `tests/test_documentation_structure.py`

- [ ] **Step 1: Add a failing navigation contract test**

Assert that the root pages have `title` and `nav_order`, the three section index pages have `has_children: true`, and every section child has the exact matching `parent` plus a unique `nav_order`.

- [ ] **Step 2: Run the focused test and confirm it fails**

```powershell
python -m unittest tests.test_documentation_structure.DocumentationStructureTests.test_just_the_docs_sidebar_hierarchy
```

Expected: failure because the Markdown files do not yet contain YAML front matter.

- [ ] **Step 3: Add navigation metadata without changing body text**

Add `layout`, `title`, `nav_order`, `has_children`, and `parent` fields as applicable. Use top-level order: home `1`, document navigation `2`, user `3`, administrator `4`, developer `5`. Order child pages in the same sequence currently shown by each section index.

- [ ] **Step 4: Run only the two focused tests**

```powershell
python -m unittest tests.test_documentation_structure.DocumentationStructureTests.test_just_the_docs_theme_uses_builtin_github_pages tests.test_documentation_structure.DocumentationStructureTests.test_just_the_docs_sidebar_hierarchy
```

Expected: two tests pass.

- [ ] **Step 5: Check the changed files and leave them uncommitted**

```powershell
git diff --check
```

Expected: no whitespace errors. Do not commit.
