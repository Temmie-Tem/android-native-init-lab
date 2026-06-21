from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/revalidation/native_doomgeneric_runtime_wad_preflight_v3027.py")


class NativeDoomgenericRuntimeWadPreflightV3027Tests(unittest.TestCase):
    def test_collect_state_reports_asset_needed_without_private_wad(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_root = root / "private-wads"
            public_root = root / "public"
            public_root.mkdir()

            with mock.patch.object(runner, "PRIVATE_WAD_ROOT", private_root), \
                    mock.patch.object(runner, "PUBLIC_ROOT", public_root):
                state = runner.collect_state()

        self.assertEqual(state["run_id"], "V3027")
        self.assertEqual(state["decision"], runner.DECISION_ASSET_NEEDED)
        self.assertTrue(state["preflight_ok"])
        self.assertFalse(state["live_asset_ready"])
        self.assertEqual(state["public_wads"]["count"], 0)
        self.assertEqual(state["private_wads"]["count"], 0)
        self.assertEqual(state["next_unit"]["type"], "operator-private-asset-needed")
        self.assertFalse(state["runtime_contract"]["commit_wad"])
        self.assertFalse(state["runtime_contract"]["embed_wad_in_ramdisk"])
        self.assertFalse(state["runtime_contract"]["embed_wad_in_boot"])

    def test_collect_private_wad_candidates_selects_single_valid_wad_without_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SECRET.WAD").write_bytes(b"IWAD" + b"\0" * 128)

            result = runner.collect_private_wad_candidates(root)

        self.assertTrue(result["exists"])
        self.assertEqual(result["count"], 1)
        self.assertIsNotNone(result["selected"])
        self.assertEqual(result["selected"]["bytes"], 132)
        self.assertEqual(result["selected"]["magic"], "IWAD")
        self.assertTrue(result["selected"]["magic_ok"])
        self.assertNotIn("SECRET.WAD", str(result))
        self.assertNotIn("path", str(result).lower())

    def test_collect_private_wad_candidates_rejects_multiple_wads_as_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "A.WAD").write_bytes(b"IWAD" + b"\0")
            (root / "B.IWAD").write_bytes(b"PWAD" + b"\0")

            result = runner.collect_private_wad_candidates(root)

        self.assertEqual(result["count"], 2)
        self.assertTrue(result["ambiguous"])
        self.assertIsNone(result["selected"])
        self.assertNotIn("A.WAD", str(result))
        self.assertNotIn("B.IWAD", str(result))

    def test_collect_private_wad_candidates_requires_iwad_or_pwad_magic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "BAD.WAD").write_bytes(b"NOPE" + b"\0")

            result = runner.collect_private_wad_candidates(root)

        self.assertEqual(result["count"], 1)
        self.assertFalse(result["all_magic_ok"])
        self.assertIsNone(result["selected"])

    def test_render_report_omits_private_wad_names_and_records_asset_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_root = root / "private-wads"
            public_root = root / "public"
            public_root.mkdir()

            with mock.patch.object(runner, "PRIVATE_WAD_ROOT", private_root), \
                    mock.patch.object(runner, "PUBLIC_ROOT", public_root):
                report = runner.render_report(runner.collect_state())

        self.assertIn("Native Init V3027 DOOMGENERIC Runtime WAD Preflight", report)
        self.assertIn(runner.DECISION_ASSET_NEEDED, report)
        self.assertIn("Private WAD/IWAD candidate count: `0`", report)
        self.assertIn("Live asset ready: `0`", report)
        self.assertIn("Selected WAD SHA256: `not-recorded-asset-absent`", report)
        self.assertIn("operator-private-asset-needed", report)
        self.assertIn("remains asset-gated", report)
        self.assertNotIn("SECRET.WAD", report)
        self.assertNotIn("BAD.WAD", report)

    def test_collect_state_can_be_ready_with_single_private_wad(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_root = root / "private-wads"
            public_root = root / "public"
            private_root.mkdir()
            public_root.mkdir()
            (private_root / "SECRET.WAD").write_bytes(b"IWAD" + b"\0" * 128)

            with mock.patch.object(runner, "PRIVATE_WAD_ROOT", private_root), \
                    mock.patch.object(runner, "PUBLIC_ROOT", public_root):
                state = runner.collect_state()

        self.assertEqual(state["decision"], runner.DECISION_READY)
        self.assertTrue(state["live_asset_ready"])
        self.assertEqual(state["next_unit"]["run_id"], "V3028")
        self.assertEqual(
            state["next_unit"]["type"],
            "host-only WAD-backed doomgeneric command implementation",
        )
        self.assertNotIn("SECRET.WAD", str(state))

    def test_render_report_records_ready_state_without_private_wad_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_root = root / "private-wads"
            public_root = root / "public"
            private_root.mkdir()
            public_root.mkdir()
            (private_root / "SECRET.WAD").write_bytes(b"IWAD" + b"\0" * 128)

            with mock.patch.object(runner, "PRIVATE_WAD_ROOT", private_root), \
                    mock.patch.object(runner, "PUBLIC_ROOT", public_root):
                report = runner.render_report(runner.collect_state())

        self.assertIn(runner.DECISION_READY, report)
        self.assertIn("Live asset ready: `1`", report)
        self.assertIn("Private WAD/IWAD candidate count: `1`", report)
        self.assertIn("exactly one private WAD/IWAD candidate", report)
        self.assertIn("V3028", report)
        self.assertNotIn("SECRET.WAD", report)


if __name__ == "__main__":
    unittest.main()
