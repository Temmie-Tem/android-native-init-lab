"""Tests for the V2596 ACDB direct pre-GET live runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2596 = load_revalidation("native_audio_acdb_direct_preget_live_handoff_v2596")


class AcdbDirectPregetLiveHandoffV2596(unittest.TestCase):
    def test_summarize_direct_preget_ret0_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_dir = Path(tmp)
            events = [
                {"event": "v2595_direct_preget", "stage": "entered_common_topology_hook", "code": 0},
                {"event": "v2595_direct_preget", "stage": "skip_real_common_topology", "code": 0},
                {"event": "v2595_direct_preget", "stage": "patch_initialized_flag_return", "code": 0},
                {"event": "v2595_direct_preget", "stage": "before_direct_preget", "code": 0},
                {
                    "event": "v2595_direct_preget",
                    "stage": "direct_preget_return",
                    "cmd": "0x0001122e",
                    "in_len": 4,
                    "out_len": 4,
                    "input_word": "0x00011135",
                    "ret": 0,
                    "out_word": "0x0000002a",
                    "out_nonzero": True,
                },
            ]
            (artifact_dir / "acdb-v2595-direct-preget-events.jsonl").write_text(
                "\n".join(json.dumps(item) for item in events) + "\n",
                encoding="utf-8",
            )

            summary = v2596.summarize_direct_preget_capture(artifact_dir)

        self.assertEqual(summary["classification"], "v2596-direct-preget-ret0-nonzero")
        self.assertTrue(summary["success"])
        self.assertEqual(summary["ret"], 0)
        self.assertEqual(summary["out_word"], "0x0000002a")
        self.assertTrue(summary["skip_real_common_topology_seen"])
        self.assertTrue(summary["patch_initialized_flag_ok"])
        self.assertTrue(summary["before_direct_preget_seen"])

    def test_summarize_direct_preget_ret0_zero_is_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact_dir = Path(tmp)
            rows = [
                {"event": "v2595_direct_preget", "stage": "before_direct_preget", "code": 0},
                {
                    "event": "v2595_direct_preget",
                    "stage": "direct_preget_return",
                    "ret": 0,
                    "out_word": "0x00000000",
                },
            ]
            (artifact_dir / "acdb-v2595-direct-preget-events.jsonl").write_text(
                "\n".join(json.dumps(item) for item in rows) + "\n",
                encoding="utf-8",
            )

            summary = v2596.summarize_direct_preget_capture(artifact_dir)

        self.assertEqual(summary["classification"], "v2596-direct-preget-ret0-zero")
        self.assertFalse(summary["success"])
        self.assertTrue(summary["partial_success"])

    def test_read_manifest_requires_direct_preget_contract(self) -> None:
        manifest = v2596.read_v2595_manifest(v2596.v2595.DEFAULT_MANIFEST)

        self.assertTrue(manifest["ok"])
        self.assertTrue(manifest["direct_preget_contract_ok"])
        self.assertTrue(manifest["skips_real_common_topology"])


if __name__ == "__main__":
    unittest.main()
