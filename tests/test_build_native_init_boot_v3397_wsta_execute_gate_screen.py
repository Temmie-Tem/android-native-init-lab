"""Regression tests for V3397 WSTA execute-gate screen source build."""

from __future__ import annotations

import unittest

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3397_wsta_execute_gate_screen")


class BuildNativeInitBootV3397WstaExecuteGateScreenTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3397")
        self.assertEqual(builder.INIT_VERSION, "0.11.153")
        self.assertEqual(builder.INIT_BUILD, "v3397-wsta-execute-gate-screen")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3397-wsta-execute-gate-screen",
            b"0.11.153",
            b"screenapp.title=WSTA D-PUBLIC",
            b"WSTA D-PUBLIC",
            b"WSTA PUBLISH",
            b"STATE: PUBLIC_OFF EXEC-GATED",
            b"GATE: WSTA80 READY -> WSTA58",
            b"URL: REDACTED PRIVATE-RUN ONLY",
            b"NATIVE: DISPLAY-ONLY NO AUTOSTART",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_v3396_identity(self) -> None:
        text = builder._rewrite_v3397_text(
            "V3396 0.11.152 v3396-wsta-persistent-state-screen "
            "a90-doomgeneric-v3396"
        )
        self.assertIn("V3397", text)
        self.assertIn("0.11.153", text)
        self.assertIn("v3397-wsta-execute-gate-screen", text)
        self.assertIn("a90-doomgeneric-v3397", text)
        self.assertNotIn("v3396", text)
        self.assertNotIn("wsta-persistent-state-screen", text)

    def test_manifest_records_wsta_execute_gate_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        self.assertEqual(manifest["rung"], "wsta-execute-gate-screen")
        self.assertEqual(manifest["scope"], "native-wsta-redacted-execute-gate-screen")

        screenapp = manifest["wsta_operator_screenapp"]
        self.assertEqual(screenapp["surface"], "NETWORK menu + screenapp wsta/dpublic")
        self.assertEqual(screenapp["mode"], "read-only-display")
        self.assertEqual(screenapp["state"], "PUBLIC_OFF")
        self.assertEqual(screenapp["gate"], "WSTA80 ready status -> WSTA58 explicit live gate")
        self.assertEqual(screenapp["public_url_display"], "redacted-private-run-only")
        self.assertEqual(screenapp["native_public_action"], "none")
        self.assertEqual(screenapp["autostart"], "none")
        self.assertEqual(screenapp["redacted_result_source"], "WSTA48/WSTA80 public summaries")


if __name__ == "__main__":
    unittest.main()
