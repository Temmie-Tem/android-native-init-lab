"""Regression tests for evidence bundle helpers."""

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_harness

bundle = load_harness("bundle")


class FakeStore:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.json_payloads = {}
        self.text_payloads = {}

    def write_json(self, name, payload):
        self.json_payloads[name] = payload
        path = self.run_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_text(self, name, text):
        self.text_payloads[name] = text
        path = self.run_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class BundleFileSchema(unittest.TestCase):
    def test_bundle_file_to_dict_serializes_fields(self):
        item = bundle.BundleFile("a.txt", 3, "0o600", 12.5)

        self.assertEqual(
            item.to_dict(),
            {"path": "a.txt", "size": 3, "mode": "0o600", "mtime": 12.5},
        )


class CollectBundleFiles(unittest.TestCase):
    def test_collect_bundle_files_returns_sorted_regular_file_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "nested").mkdir()
            (run_dir / "z.txt").write_text("z", encoding="utf-8")
            (run_dir / "nested" / "a.txt").write_text("abc", encoding="utf-8")
            (run_dir / "z.txt").chmod(0o600)

            files = bundle.collect_bundle_files(FakeStore(run_dir))

            self.assertEqual([item.path for item in files], ["nested/a.txt", "z.txt"])
            self.assertEqual([item.size for item in files], [3, 1])
            self.assertEqual(files[1].mode, "0o600")
            self.assertIsInstance(files[0].mtime, float)

    def test_collect_bundle_files_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "target.txt").write_text("target", encoding="utf-8")
            (run_dir / "link.txt").symlink_to(run_dir / "target.txt")

            with self.assertRaisesRegex(RuntimeError, "refusing symlink"):
                bundle.collect_bundle_files(FakeStore(run_dir))


class RenderReadme(unittest.TestCase):
    def test_render_bundle_readme_formats_manifest_fields_and_layout(self):
        text = bundle.render_bundle_readme(
            {
                "label": "run-label",
                "pass": True,
                "created_utc": "2026-06-13T00:00:00Z",
                "expect_version": "A90 Linux init test",
                "policy": "read-only",
            }
        )

        self.assertIn("# A90 Native Init Evidence Bundle", text)
        self.assertIn("- label: `run-label`", text)
        self.assertIn("- result: `PASS`", text)
        self.assertIn("- policy: `read-only`", text)
        self.assertIn("- `observer.jsonl`: read-only observer stream when present", text)

    def test_render_bundle_readme_treats_falsey_pass_as_fail(self):
        self.assertIn("- result: `FAIL`", bundle.render_bundle_readme({"pass": False}))
        self.assertIn("- result: `FAIL`", bundle.render_bundle_readme({}))


class FinalizeBundle(unittest.TestCase):
    def test_finalize_bundle_writes_manifest_summary_readme_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "commands").mkdir()
            (run_dir / "commands" / "status.txt").write_text("status", encoding="utf-8")
            store = FakeStore(run_dir)
            original_time = bundle.time.time
            bundle.time.time = lambda: 123.456
            try:
                bundle.finalize_bundle(
                    store,
                    {
                        "label": "bundle-test",
                        "pass": True,
                        "created_utc": "2026-06-13T00:00:00Z",
                        "expect_version": "A90 test",
                        "policy": "private",
                    },
                    "summary text\n",
                )
            finally:
                bundle.time.time = original_time

            manifest = store.json_payloads["manifest.json"]
            self.assertEqual(manifest["bundle_schema"], "a90-harness-v175")
            self.assertEqual(manifest["bundle_finalized_host_ts"], 123.456)
            self.assertEqual(store.text_payloads["summary.md"], "summary text\n")
            self.assertIn("- result: `PASS`", store.text_payloads["README.md"])
            index = store.json_payloads["bundle-index.json"]
            self.assertEqual(index["schema"], "a90-harness-v175")
            self.assertEqual(index["run_dir"], str(run_dir))
            self.assertEqual(
                sorted(item["path"] for item in index["files"]),
                ["README.md", "commands/status.txt", "manifest.json", "summary.md"],
            )
            self.assertEqual(index["file_count"], 4)
            self.assertIn("symlink destinations refused", index["policy"])
            self.assertTrue((run_dir / "bundle-index.json").is_file())


if __name__ == "__main__":
    unittest.main()
