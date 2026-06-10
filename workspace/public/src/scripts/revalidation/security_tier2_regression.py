#!/usr/bin/env python3
"""Focused regressions for Tier 2 security hardening."""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
HARNESS_PATH = REPO_ROOT / "workspace" / "public" / "src" / "harness"
if str(HARNESS_PATH) not in sys.path:
    sys.path.append(str(HARNESS_PATH))

from a90harness.evidence import read_bounded_text


class Tier2SecurityRegression(unittest.TestCase):
    def test_bounded_read_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a90-evidence-read-test-") as temp_dir:
            root = Path(temp_dir)
            target = root / "target.txt"
            link = root / "link.txt"
            target.write_text("ok\n", encoding="utf-8")
            link.symlink_to(target)

            with self.assertRaisesRegex(RuntimeError, "symlink"):
                read_bounded_text(link, max_bytes=16)

    def test_bounded_read_rejects_oversized_regular_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a90-evidence-read-test-") as temp_dir:
            path = Path(temp_dir) / "large.txt"
            path.write_bytes(b"x" * 17)

            with self.assertRaisesRegex(RuntimeError, "exceeds bounded read limit"):
                read_bounded_text(path, max_bytes=16)

    def test_bootstrap_archive_import_is_explicit_opt_in(self) -> None:
        bootstrap = importlib.import_module("_workspace_bootstrap")
        legacy_path = (
            REPO_ROOT
            / "workspace"
            / "public"
            / "archive"
            / "scripts"
            / "revalidation"
        )
        legacy_text = str(legacy_path)
        old_env = os.environ.pop("A90_INCLUDE_ARCHIVE_REVALIDATION", None)
        original_sys_path = list(sys.path)
        try:
            sys.path[:] = [entry for entry in sys.path if entry != legacy_text]
            returned = add_legacy_revalidation_path(REPO_ROOT)
            self.assertEqual(returned, legacy_path)
            self.assertNotIn(legacy_text, sys.path)

            bootstrap.add_legacy_revalidation_path(REPO_ROOT, include_archive=True)
            self.assertIn(legacy_text, sys.path)
        finally:
            sys.path[:] = original_sys_path
            if old_env is not None:
                os.environ["A90_INCLUDE_ARCHIVE_REVALIDATION"] = old_env


if __name__ == "__main__":
    unittest.main()
