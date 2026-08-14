from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P317_CDC_ACM_ENDPOINT_SELECTOR_CORRECTION_H0_2026-08-14.md"
)
INCIDENT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P317_HISTORICAL_ENDPOINT_REPLAY_RECOVERY_INCIDENT_2026-08-14.md"
)
GOAL = ROOT / "GOAL.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
PRIVATE = ROOT / "workspace/private/outputs/s22plus_fyg8_p318_endpoint_selector"
PREPARED = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-2026-08-12T165954582328Z-1786553994582372233/prepared.json"
)


class P318DocumentationTest(unittest.TestCase):
    def test_report_binds_current_private_receipts(self):
        report = REPORT.read_text(encoding="utf-8")
        expected = {
            "endpoint-transition-20260814-01.json": (
                "PASS_P318_P317_ENDPOINT_SELECTOR_LOCALIZATION_H0"
            ),
            "cdc-acm-positive-control-20260814-01.json": (
                "PASS_P318_CDC_ACM_TWO_SEAM_POSITIVE_CONTROL_H0"
            ),
            "banner-result-contract-20260814-01.json": (
                "PASS_P318_BANNER_RESULT_DESIGN_H0_IMPLEMENTATION_REQUIRED"
            ),
        }
        for name, verdict in expected.items():
            payload = (PRIVATE / name).read_bytes()
            value = json.loads(payload)
            self.assertEqual(value["verdict"], verdict)
            self.assertIn(name, report)
            self.assertIn(f"size    {len(payload)}", report)
            self.assertIn(f"sha256  {hashlib.sha256(payload).hexdigest()}", report)

    def test_scope_is_p317_only_and_not_live_ready(self):
        combined = REPORT.read_text(encoding="utf-8") + GOAL.read_text(
            encoding="utf-8"
        )
        required = (
            "For P3.17 only",
            "does not reclassify earlier campaigns",
            "not yet wired into the live observer",
            "P3.18 is not candidate-ready",
            "grants no D0, D1, F1, recovery, or live authority",
        )
        for clause in required:
            self.assertIn(clause, combined)

    def test_ledger_correction_is_append_only_after_original_close(self):
        ledger = LEDGER.read_text(encoding="utf-8")
        original = (
            "2026-08-13T17:42:07Z | s22plus-fyg8-p317 | 1-recovery-close | "
            "F1 | CAMPAIGN_CLOSED | HEALTHY | NO_PROOF_OBSERVER | 1/1 |"
        )
        correction = (
            "s22plus-fyg8-p317 | h0-endpoint-selector-correction-1 | H0 | "
            "P317_CDC_ACM_ENDPOINT_SELECTOR_POSTCLOSE_CORRECTION_AND_P318_H0_DESIGN"
        )
        self.assertEqual(ledger.count(original), 1)
        self.assertEqual(ledger.count(correction), 1)
        self.assertLess(ledger.index(original), ledger.index(correction))

    def test_incident_report_carries_explicit_post_close_correction(self):
        incident = INCIDENT.read_text(encoding="utf-8")
        self.assertIn("## Post-close endpoint-observer correction", incident)
        self.assertIn("selected no\nendpoint and never opened the TTY", incident)
        self.assertIn("campaign-level multiplicity result", incident)

    def test_tracked_unit_does_not_export_raw_candidate_serial(self):
        prepared = json.loads(PREPARED.read_text(encoding="utf-8"))
        serial = prepared["approval_binding"]["base_binding"]["observation"][
            "candidate_observer"
        ]["usb_serial"]
        tracked = [
            REPORT,
            INCIDENT,
            GOAL,
            LEDGER,
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_cdc_acm_endpoint_transition.py",
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_cdc_acm_positive_control.py",
            ROOT
            / "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p318_banner_result_contract.py",
        ]
        for path in tracked:
            self.assertNotIn(serial, path.read_text(encoding="utf-8"), path)


if __name__ == "__main__":
    unittest.main()
