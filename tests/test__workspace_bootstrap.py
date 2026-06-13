from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import REPO_ROOT, load_revalidation


bootstrap = load_revalidation("_workspace_bootstrap")


class WorkspaceBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_sys_path = list(sys.path)
        self._orig_env = dict(os.environ)
        self.addCleanup(self._restore_process_state)

    def _restore_process_state(self) -> None:
        sys.path[:] = self._orig_sys_path
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_repo_root_finds_checkout_from_script_location(self) -> None:
        self.assertEqual(bootstrap.repo_root(), REPO_ROOT)

    def test_repo_root_raises_when_no_git_ancestor_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            orphan = Path(tmp) / "workspace" / "public" / "src" / "scripts" / "revalidation" / "helper.py"
            orphan.parent.mkdir(parents=True)
            orphan.write_text("", encoding="utf-8")
            with mock.patch.object(bootstrap, "__file__", str(orphan)):
                with self.assertRaisesRegex(RuntimeError, "could not locate repo root"):
                    bootstrap.repo_root()

    def test_add_legacy_revalidation_path_adds_harness_but_not_archive_by_default(self) -> None:
        root = Path("/repo")
        harness = str(root / "workspace" / "public" / "src" / "harness")
        legacy = root / "workspace" / "public" / "archive" / "scripts" / "revalidation"
        sys.path[:] = ["/already"]
        os.environ.pop("A90_INCLUDE_ARCHIVE_REVALIDATION", None)

        returned = bootstrap.add_legacy_revalidation_path(root)

        self.assertEqual(returned, legacy)
        self.assertEqual(sys.path, ["/already", harness])

    def test_add_legacy_revalidation_path_can_include_archive_once(self) -> None:
        root = Path("/repo")
        harness = str(root / "workspace" / "public" / "src" / "harness")
        legacy = str(root / "workspace" / "public" / "archive" / "scripts" / "revalidation")
        sys.path[:] = [harness, legacy]

        returned = bootstrap.add_legacy_revalidation_path(root, include_archive=True)

        self.assertEqual(returned, Path(legacy))
        self.assertEqual(sys.path.count(harness), 1)
        self.assertEqual(sys.path.count(legacy), 1)
        self.assertEqual(sys.path, [harness, legacy])

    def test_env_flag_controls_archive_inclusion_when_argument_omitted(self) -> None:
        root = Path("/repo")
        harness = str(root / "workspace" / "public" / "src" / "harness")
        legacy = str(root / "workspace" / "public" / "archive" / "scripts" / "revalidation")
        sys.path[:] = []
        os.environ["A90_INCLUDE_ARCHIVE_REVALIDATION"] = "yes"

        bootstrap.add_legacy_revalidation_path(root)

        self.assertEqual(sys.path, [harness, legacy])

    def test_explicit_include_archive_false_overrides_truthy_env_flag(self) -> None:
        root = Path("/repo")
        harness = str(root / "workspace" / "public" / "src" / "harness")
        legacy = str(root / "workspace" / "public" / "archive" / "scripts" / "revalidation")
        sys.path[:] = []
        os.environ["A90_INCLUDE_ARCHIVE_REVALIDATION"] = "true"

        bootstrap.add_legacy_revalidation_path(root, include_archive=False)

        self.assertEqual(sys.path, [harness])
        self.assertNotIn(legacy, sys.path)


if __name__ == "__main__":
    unittest.main()
