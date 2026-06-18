"""Tests for V2733 atomic App Type Config writer build unit."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2733 = load_revalidation("build_audio_app_type_config_writer_v2733")


class BuildAudioAppTypeConfigWriterV2733(unittest.TestCase):
    def test_source_guard_is_ready(self) -> None:
        state = v2733.source_state()

        self.assertTrue(state["exists"])
        self.assertTrue(state["ready"])
        self.assertTrue(all(state["required_tokens"].values()))
        self.assertFalse(any(state["prohibited_tokens"].values()))

    def test_parse_args_defaults_to_private_manifest(self) -> None:
        args = v2733.parse_args([])

        self.assertEqual(args.manifest_path, v2733.DEFAULT_MANIFEST)
        self.assertEqual(args.report, v2733.DEFAULT_REPORT)
        self.assertEqual(args.cc, "aarch64-linux-gnu-gcc")

    def test_write_report_redacts_private_details(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2733-"))
        report = root / "report.md"
        manifest = {
            "decision": "v2733-app-type-config-atomic-writer-built",
            "source_state": {"ready": True},
            "build": {
                "tools": {
                    v2733.TOOL_NAME: {
                        "path": "workspace/private/builds/audio/v2733/bin/tool",
                        "sha256": "0" * 64,
                        "file": "ELF 64-bit LSB executable, ARM aarch64, statically linked",
                    }
                }
            },
        }

        v2733.write_report(report, manifest)
        text = report.read_text(encoding="utf-8")

        self.assertIn("atomic ALSA", text)
        self.assertIn("SNDRV_CTL_IOCTL_ELEM_WRITE", text)
        self.assertIn(v2733.TOOL_NAME, text)
        self.assertNotIn("local_path_private", text)

    def test_manifest_writer_uses_json(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2733-"))
        path = root / "manifest.json"
        payload = {"ok": True}

        v2733.write_json(path, payload)

        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)


if __name__ == "__main__":
    unittest.main()
