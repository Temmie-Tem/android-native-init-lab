#!/usr/bin/env python3
"""Focused regressions for 2026-06-10 Unit B security hardening."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

from _workspace_bootstrap import repo_root

REPO_ROOT = repo_root()

import native_wifi_supplicant_dependency_probe as probe
import native_wifi_v2178_autoconnect_phase_validation as phase


def minimal_v2178_manifest() -> dict[str, object]:
    return {
        "version": {"expected": True},
        "autoconnect_status": {"secret_values_logged": "0"},
        "connect": {
            "decision": "wifi-autoconnect-pass",
            "secret_values_logged": "0",
            "credentials_logged": "0",
        },
        "scope": {"credentials_logged": 0},
        "cleanup": {"decision": "wifi-cleanup-done"},
        "autoconnect_disable_restore": {"decision": "wifi-autoconnect-disabled"},
        "final_selftest": {"fail0": True},
    }


class UnitBRegressionTests(unittest.TestCase):
    def test_v2178_classify_fails_on_secret_leak_flag(self) -> None:
        manifest = minimal_v2178_manifest()
        manifest["connect"]["secret_values_logged"] = "1"  # type: ignore[index]

        classification = phase.classify(manifest)

        self.assertFalse(classification["pass"])
        self.assertEqual(classification["decision"], "v2180-wifi-phase-secret-hygiene-failed")

    def test_v2178_classify_passes_with_zero_secret_flags(self) -> None:
        classification = phase.classify(minimal_v2178_manifest())

        self.assertTrue(classification["pass"])
        self.assertEqual(classification["decision"], "v2180-wifi-phase-validation-pass")

    def test_supplicant_probe_transfer_requires_ok_and_matching_sha(self) -> None:
        self.assertTrue(probe.transfer_ok({"ok": True}))
        self.assertFalse(probe.transfer_ok({"ok": False}))
        self.assertFalse(probe.transfer_ok({"ok": True, "sha256_mismatch": True}))

    def test_public_v2172_report_has_no_full_mac_address(self) -> None:
        report_name = "NATIVE_INIT_V2172_WIFI_STATUS_SCAN_LIVE_VALIDATION_2026-06-08.md"
        report = REPO_ROOT / "docs/reports" / report_name
        if not report.exists():
            report = REPO_ROOT / "docs/archive/legacy/reports" / report_name
        text = report.read_text(encoding="utf-8")

        self.assertNotRegex(text, re.compile(r"\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b"))
        self.assertIn("mac_raw_redacted=1", text)


if __name__ == "__main__":
    unittest.main()
