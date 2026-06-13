"""Regression tests for cleanup_tmp_classified_artifacts safety behavior."""

from __future__ import annotations

import gzip
import io
import os
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from _loader import load_revalidation


cleanup = load_revalidation("cleanup_tmp_classified_artifacts")


def args(**overrides):
    values = {
        "execute": False,
        "ncm_benchmark_payloads": False,
        "kernel_build_out": False,
        "root_build_products": False,
        "compress_bridge_logs": False,
        "bridge_min_mib": 1.0,
        "all_safe": False,
    }
    values.update(overrides)
    return types.SimpleNamespace(**values)


def write_file(path: Path, data: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class CleanupTmpClassifiedArtifactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.old_values = {
            "REPO_ROOT": cleanup.REPO_ROOT,
            "TMP_ROOT": cleanup.TMP_ROOT,
            "WIFI_TMP_ROOT": cleanup.WIFI_TMP_ROOT,
            "ARCHIVE_ROOT": cleanup.ARCHIVE_ROOT,
            "V766_KERNEL_OUT": cleanup.V766_KERNEL_OUT,
        }
        self.addCleanup(self.restore_constants)
        cleanup.REPO_ROOT = self.root
        cleanup.TMP_ROOT = self.root / "tmp"
        cleanup.WIFI_TMP_ROOT = cleanup.TMP_ROOT / "wifi"
        cleanup.ARCHIVE_ROOT = cleanup.WIFI_TMP_ROOT / "archive"
        cleanup.V766_KERNEL_OUT = (
            cleanup.WIFI_TMP_ROOT / "v766-icnss-qcacld-patch-apply-build" / "source" / "out"
        )

    def restore_constants(self) -> None:
        for name, value in self.old_values.items():
            setattr(cleanup, name, value)

    def test_build_plan_all_safe_collects_only_classified_generated_artifacts(self) -> None:
        ncm_payload = write_file(cleanup.WIFI_TMP_ROOT / "a90-ncm-transport-smoke-run" / "payload.bin", b"payload")
        write_file(cleanup.WIFI_TMP_ROOT / "a90-ncm-transport-smoke-run" / "keep.txt", b"log")
        kernel_obj = write_file(cleanup.V766_KERNEL_OUT / "drivers" / "built-in.o", b"obj")
        root_elf = write_file(cleanup.TMP_ROOT / "a90_helper_v2300", cleanup.ELF_MAGIC + b"binary")
        write_file(cleanup.TMP_ROOT / "a90_helper_v2300.txt", cleanup.ELF_MAGIC + b"text")
        bridge_log = write_file(cleanup.TMP_ROOT / "bridge-large.log", b"a" * (2 * 1024 * 1024))
        write_file(cleanup.TMP_ROOT / "bridge-large.log.gz", b"already")

        plan = cleanup.build_plan(args(all_safe=True, bridge_min_mib=1.0))

        actions_by_path = {item["path"]: item for item in plan["actions"]}
        self.assertEqual(plan["mode"], "dry-run")
        self.assertIn(cleanup.rel(ncm_payload), actions_by_path)
        self.assertIn(cleanup.rel(cleanup.V766_KERNEL_OUT), actions_by_path)
        self.assertIn(cleanup.rel(root_elf), actions_by_path)
        self.assertNotIn(cleanup.rel(kernel_obj), actions_by_path)
        self.assertNotIn(cleanup.rel(bridge_log), actions_by_path)
        self.assertEqual(actions_by_path[cleanup.rel(ncm_payload)]["category"], "wifi-benchmark-payload")
        self.assertEqual(actions_by_path[cleanup.rel(root_elf)]["category"], "root-helper-build-product")
        self.assertGreater(plan["planned_remove_bytes"], 0)

    def test_bridge_log_plan_skips_small_or_already_compressed_logs(self) -> None:
        large = write_file(cleanup.TMP_ROOT / "bridge-large.log", b"a" * 2048)
        small = write_file(cleanup.TMP_ROOT / "bridge-small.log", b"a" * 16)
        already = write_file(cleanup.TMP_ROOT / "bridge-existing.log", b"a" * 2048)
        write_file(cleanup.TMP_ROOT / "bridge-existing.log.gz", b"gz")

        plan = cleanup.build_plan(args(compress_bridge_logs=True, bridge_min_mib=0.001))

        paths = {item["path"] for item in plan["actions"]}
        self.assertIn(cleanup.rel(large), paths)
        self.assertNotIn(cleanup.rel(small), paths)
        self.assertNotIn(cleanup.rel(already), paths)
        self.assertEqual(plan["actions"][0]["action"], "compress-gzip-remove-original")
        self.assertEqual(plan["actions"][0]["gzip_path"], cleanup.rel(large.with_suffix(".log.gz")))
        self.assertGreater(plan["planned_compress_input_bytes"], 0)

    def test_execute_plan_removes_files_and_compresses_logs_reproducibly(self) -> None:
        remove_me = write_file(cleanup.TMP_ROOT / "a90_remove_v1", cleanup.ELF_MAGIC + b"remove")
        log = write_file(cleanup.TMP_ROOT / "bridge-test.log", b"line\n" * 100)
        plan = {
            "mode": "dry-run",
            "actions": [
                cleanup.removal(remove_me, "root-helper-build-product", "test remove"),
                cleanup.compression(log, "root-bridge-log", "test compress"),
            ],
        }

        result = cleanup.execute_plan(plan)

        gzip_path = log.with_suffix(".log.gz")
        self.assertFalse(remove_me.exists())
        self.assertFalse(log.exists())
        self.assertTrue(gzip_path.is_file())
        with gzip.open(gzip_path, "rb") as file_obj:
            self.assertEqual(file_obj.read(), b"line\n" * 100)
        self.assertEqual(result["executed_count"], 2)
        self.assertGreater(result["executed_freed_bytes_estimate"], 0)
        self.assertEqual(result["results"][0]["after_bytes"], 0)
        self.assertIn("gzip_bytes", result["results"][1])

    def test_execute_plan_refuses_symlink_escape_and_preserves_target(self) -> None:
        outside = write_file(self.root / "outside.bin", b"outside")
        escape = cleanup.TMP_ROOT / "escape-link"
        escape.parent.mkdir(parents=True, exist_ok=True)
        escape.symlink_to(outside)
        plan = {"actions": [{"action": "remove", "path": cleanup.rel(escape), "bytes": 0}]}

        with self.assertRaisesRegex(RuntimeError, "refusing path outside tmp"):
            cleanup.execute_plan(plan)

        self.assertTrue(escape.is_symlink())
        self.assertEqual(outside.read_bytes(), b"outside")

    def test_main_execute_writes_manifest_before_and_after_actions(self) -> None:
        payload = write_file(cleanup.WIFI_TMP_ROOT / "a90-ncm-transport-smoke-run" / "payload.bin", b"payload")
        manifest = cleanup.ARCHIVE_ROOT / "manifest.json"
        parsed_args = args(execute=True, ncm_benchmark_payloads=True, manifest=manifest, json=False)
        parsed_args.kernel_build_out = False
        parsed_args.root_build_products = False
        parsed_args.compress_bridge_logs = False
        parsed_args.all_safe = False

        old_parse_args = cleanup.parse_args
        try:
            cleanup.parse_args = lambda: parsed_args
            with redirect_stdout(io.StringIO()):
                rc = cleanup.main()
        finally:
            cleanup.parse_args = old_parse_args

        self.assertEqual(rc, 0)
        self.assertFalse(payload.exists())
        manifest_data = cleanup.json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(manifest_data["mode"], "execute")
        self.assertEqual(manifest_data["manifest"], cleanup.rel(manifest))
        self.assertEqual(manifest_data["executed_count"], 1)


if __name__ == "__main__":
    unittest.main()
