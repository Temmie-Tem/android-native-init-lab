"""Regression tests for push_scope_check.py.

Exercises the review-trigger and empty-body-commit detectors against a
throwaway git repository so this never touches the real repo history.
"""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/security/push_scope_check.py"


def load_module():
    spec = importlib.util.spec_from_file_location("push_scope_check_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def commit(repo: Path, name: str, body: str = "") -> None:
    (repo / f"{name}.txt").write_text(name)
    run_git(repo, "add", f"{name}.txt")
    message = name if not body else f"{name}\n\n{body}"
    run_git(repo, "commit", "-m", message)


class PushScopeCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        run_git(self.repo, "init", "-q")
        run_git(self.repo, "config", "user.email", "test@example.invalid")
        run_git(self.repo, "config", "user.name", "Test")
        commit(self.repo, "base", body="root commit")

    def tearDown(self):
        self._tmp.cleanup()

    def test_commit_with_body_is_not_flagged(self):
        commit(self.repo, "with-body", body="attempt, result, and a Validation line")
        empty = self.module.empty_body_commits(self.repo, "HEAD~1..HEAD")
        self.assertEqual(empty, [])

    def test_commit_with_no_body_is_flagged(self):
        commit(self.repo, "no-body")
        empty = self.module.empty_body_commits(self.repo, "HEAD~1..HEAD")
        self.assertEqual(len(empty), 1)
        self.assertIn("no-body", empty[0])

    def test_commit_with_whitespace_only_body_is_flagged(self):
        run_git(self.repo, "commit", "--allow-empty", "-m", "whitespace-body\n\n   \n")
        empty = self.module.empty_body_commits(self.repo, "HEAD~1..HEAD")
        self.assertEqual(len(empty), 1)

    def test_mixed_range_counts_only_the_empty_ones(self):
        commit(self.repo, "first", body="has narrative")
        commit(self.repo, "second")
        commit(self.repo, "third", body="has narrative too")
        empty = self.module.empty_body_commits(self.repo, "HEAD~3..HEAD")
        self.assertEqual(len(empty), 1)
        self.assertIn("second", empty[0])

    def test_main_reports_empty_body_warning_without_blocking(self):
        # main() discovers the repo root from the script's own on-disk path,
        # so point it at the throwaway repo instead of the real one.
        commit(self.repo, "no-body")
        original_repo_root = self.module.repo_root
        self.module.repo_root = lambda: self.repo
        try:
            exit_code = self.module.main([str(SCRIPT), "HEAD~1..HEAD"])
        finally:
            self.module.repo_root = original_repo_root
        self.assertEqual(exit_code, 0)

    def test_main_clean_range_has_no_warning_section(self):
        (self.repo / "clean.txt").write_text("clean")
        run_git(self.repo, "add", "clean.txt")
        run_git(
            self.repo, "commit",
            "-m", "clean commit",
            "-m", "attempt, result, judgment, and a Validation line.",
        )
        original_repo_root = self.module.repo_root
        self.module.repo_root = lambda: self.repo
        try:
            exit_code = self.module.main([str(SCRIPT), "HEAD~1..HEAD"])
        finally:
            self.module.repo_root = original_repo_root
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
