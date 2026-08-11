#!/usr/bin/env python3
"""Tests for identity manifest naming rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


TESTS_DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIRECTORY))

from validate_identity_manifest import valid_group_name  # noqa: E402


class IdentityManifestTests(unittest.TestCase):
    def test_group_names_must_start_with_a_letter_or_underscore(self) -> None:
        for name in ("EPIC-RL", "CV3D", "MLLMs", "nue", "_internal"):
            self.assertTrue(valid_group_name(name), name)

        for name in ("3dv", "-invalid", "", "contains space"):
            self.assertFalse(valid_group_name(name), name)


if __name__ == "__main__":
    unittest.main()
