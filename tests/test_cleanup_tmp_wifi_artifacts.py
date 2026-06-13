"""Regression tests for cleanup_tmp_wifi_artifacts safety planning."""

from __future__ import annotations

import os
import tempfile
import time
import types
import unittest
from pathlib import Path

from _loader import load_revalidation


cleanup = load_revalidation("cleanup_tmp_wifi_artifacts")


def args(**overrides):
    values = {
        "execute": False,
        "scratch_days": 0.0,
        "builds_days": 14.0,
        "bench_days": 14.0,
        "cache_days": None,
        "archive_days": None,
        "include_legacy_flat": False,
        "legacy_days": None,
        "legacy_build_products_only": False,
        "legacy_build_product_days": 0.0,
        "keep_prefix": list(cleanup.DEFAULT_KEEP_PREFIXES),
        "top": 30,
    }
    values.update(overrides)
    return types.SimpleNamespace(**values)


def write_file(path: Path, text: str = "x", *, age_days: float = 0.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    when = time.time() - age_days * 86400.0
    os.utime(path, (when, when))
    os.utime(path.parent, (when, when))
    return path


class CleanupTmpWifiArtifactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.old_values = {
            "WIFI_TMP_ROOT": cleanup.WIFI_TMP_ROOT,
            "TMP_LOG_ROOT": cleanup.TMP_LOG_ROOT,
            "DOC_ARTIFACT_ROOT": cleanup.DOC_ARTIFACT_ROOT,
        }
        self.addCleanup(self.restore_constants)
        cleanup.WIFI_TMP_ROOT = self.root / "tmp" / "wifi"
        cleanup.TMP_LOG_ROOT = self.root / "tmp" / "logs"
        cleanup.DOC_ARTIFACT_ROOT = self.root / "docs" / "artifacts"

    def restore_constants(self) -> None:
        for name, value in self.old_values.items():
            setattr(cleanup, name, value)

    def test_build_plan_prunes_structured_thresholds_and_keeps_configured_prefixes(self) -> None:
        old_scratch = write_file(cleanup.WIFI_TMP_ROOT / "scratch" / "old" / "log.txt", age_days=3)
        kept = write_file(
            cleanup.WIFI_TMP_ROOT / "scratch" / "v725-fasttransport-baseline-validation-run" / "log.txt",
            age_days=3,
        )
        fresh_build = write_file(cleanup.WIFI_TMP_ROOT / "builds" / "fresh" / "boot_linux.img", age_days=1)
        old_build = write_file(cleanup.WIFI_TMP_ROOT / "builds" / "old" / "boot_linux.img", age_days=20)

        plan = cleanup.build_plan(args(scratch_days=1.0, builds_days=14.0))

        removal_paths = {item["path"] for item in plan["removals"]}
        self.assertIn(str(old_scratch.parent.relative_to(self.root)), removal_paths)
        self.assertIn(str(old_build.parent.relative_to(self.root)), removal_paths)
        self.assertNotIn(str(kept.parent.relative_to(self.root)), removal_paths)
        self.assertNotIn(str(fresh_build.parent.relative_to(self.root)), removal_paths)
        self.assertEqual(plan["mode"], "dry-run")
        self.assertGreaterEqual(plan["remove_bytes"], old_scratch.stat().st_size + old_build.stat().st_size)

    def test_legacy_flat_entries_are_protected_unless_legacy_days_is_explicit(self) -> None:
        legacy = write_file(cleanup.WIFI_TMP_ROOT / "v100-old-run" / "log.txt", age_days=60)

        protected_plan = cleanup.build_plan(args(include_legacy_flat=False))
        self.assertEqual(protected_plan["remove_count"], 0)
        self.assertEqual(protected_plan["protected_legacy_count"], 1)
        self.assertEqual(protected_plan["protected_legacy_top"][0]["path"], str(legacy.parent.relative_to(self.root)))

        with self.assertRaises(SystemExit):
            cleanup.build_plan(args(include_legacy_flat=True, legacy_days=None))

        removal_plan = cleanup.build_plan(args(include_legacy_flat=True, legacy_days=30.0))
        self.assertEqual(removal_plan["remove_count"], 1)
        self.assertEqual(removal_plan["removals"][0]["reason"], "legacy-flat-older-than-30d")

    def test_legacy_build_products_only_selects_generated_files_not_log_dirs(self) -> None:
        legacy_root = cleanup.WIFI_TMP_ROOT / "v999-source-build"
        boot = write_file(legacy_root / "boot_linux_v999.img", age_days=7)
        ramdisk = write_file(legacy_root / "nested" / "ramdisk_v999.cpio", age_days=7)
        log = write_file(legacy_root / "native.log", age_days=7)

        plan = cleanup.build_plan(
            args(
                legacy_build_products_only=True,
                legacy_build_product_days=2.0,
                scratch_days=None,
                builds_days=None,
                bench_days=None,
            )
        )

        removal_paths = {item["path"] for item in plan["removals"]}
        self.assertIn(str(boot.relative_to(self.root)), removal_paths)
        self.assertIn(str(ramdisk.relative_to(self.root)), removal_paths)
        self.assertNotIn(str(log.relative_to(self.root)), removal_paths)
        self.assertTrue(plan["legacy_build_products_only"])
        self.assertEqual(plan["legacy_build_product_days"], 2.0)

    def test_execute_plan_deletes_inside_tmp_wifi_and_refuses_symlink_escape(self) -> None:
        inside = write_file(cleanup.WIFI_TMP_ROOT / "scratch" / "remove-me.txt")
        outside = write_file(self.root / "outside.txt")
        escape = cleanup.WIFI_TMP_ROOT / "scratch" / "escape-link"
        escape.symlink_to(outside)

        cleanup.execute_plan({"removals": [{"path": str(inside.relative_to(self.root))}]})
        self.assertFalse(inside.exists())

        with self.assertRaisesRegex(RuntimeError, "refusing path outside tmp/wifi"):
            cleanup.execute_plan({"removals": [{"path": str(escape.relative_to(self.root))}]})
        self.assertTrue(escape.is_symlink())
        self.assertTrue(outside.exists())

    def test_render_text_summarizes_removals_and_protected_legacy(self) -> None:
        plan = {
            "mode": "dry-run",
            "root": str(cleanup.WIFI_TMP_ROOT),
            "remove_count": 1,
            "remove_bytes": 5,
            "protected_legacy_count": 1,
            "protected_legacy_bytes": 7,
            "removals": [
                {
                    "bytes": 5,
                    "age_days": 3.5,
                    "path": "tmp/wifi/scratch/old",
                    "reason": "scratch-older-than-1d",
                }
            ],
            "protected_legacy_top": [
                {
                    "bytes": 7,
                    "age_days": 9.0,
                    "path": "tmp/wifi/v1-run",
                    "kind": "legacy-run",
                }
            ],
        }

        text = cleanup.render_text(plan)

        self.assertIn("mode: dry-run", text)
        self.assertIn("remove 5B age=3.5d tmp/wifi/scratch/old", text)
        self.assertIn("protected_legacy_top:", text)
        self.assertIn("keep 7B age=9.0d tmp/wifi/v1-run", text)


if __name__ == "__main__":
    unittest.main()
