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
TARGET_CONTRACT = ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
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
                "PASS_P318_P317_PHYSICAL_TOPOLOGY_DRIFT_LOCALIZATION_H0"
            ),
            "cdc-acm-positive-control-20260814-01.json": (
                "PASS_P318_CDC_ACM_TWO_SEAM_POSITIVE_CONTROL_H0"
            ),
            "banner-result-contract-20260814-01.json": (
                "PASS_P318_ENVELOPE_V4_TIMING_BANNER_BUDGET_DESIGN_H0_"
                "IMPLEMENTATION_REQUIRED"
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
        combined = " ".join(
            (
                REPORT.read_text(encoding="utf-8")
                + GOAL.read_text(encoding="utf-8")
            ).split()
        )
        required = (
            "For P3.17 only",
            "does not reclassify earlier campaigns",
            "No live selector transition is authorized",
            "P3.18 is not candidate-ready",
            "grants no D0, D1, F1, recovery, or live authority",
            "NO_PROOF_EXPERIMENT_PRECONDITION",
            "first actual host-caused device event",
            "lossless PackBits poll capacity falls from 76 to 55 bytes",
            "PASS_GO — S22PLUS_FYG8_P318_TOPOLOGY_TIMING_DESIGN_H0_CAPABILITY_V1",
            "P3.18 is not candidate-ready",
        )
        for clause in required:
            self.assertIn(clause, combined)

    def test_ledger_correction_is_append_only_after_original_close(self):
        ledger = LEDGER.read_text(encoding="utf-8")
        original = (
            "2026-08-13T17:42:07Z | s22plus-fyg8-p317 | 1-recovery-close | "
            "F1 | CAMPAIGN_CLOSED | HEALTHY | NO_PROOF_OBSERVER | 1/1 |"
        )
        superseded_correction = (
            "s22plus-fyg8-p317 | h0-endpoint-selector-correction-1 | H0 | "
            "P317_CDC_ACM_ENDPOINT_SELECTOR_POSTCLOSE_CORRECTION_AND_P318_H0_DESIGN"
        )
        correction = (
            "s22plus-fyg8-p317 | h0-endpoint-topology-correction-2 | H0 | "
            "P317_PHYSICAL_TOPOLOGY_PRECONDITION_POSTCLOSE_CORRECTION | "
            "HEALTHY | NO_PROOF_EXPERIMENT_PRECONDITION | 0/0 |"
        )
        self.assertEqual(ledger.count(original), 1)
        self.assertEqual(ledger.count(superseded_correction), 1)
        self.assertEqual(ledger.count(correction), 1)
        self.assertLess(ledger.index(original), ledger.index(superseded_correction))
        self.assertLess(ledger.index(superseded_correction), ledger.index(correction))

    def test_incident_report_carries_explicit_post_close_correction(self):
        incident = INCIDENT.read_text(encoding="utf-8")
        normalized = " ".join(incident.split())
        self.assertIn("## Post-close endpoint/topology correction", incident)
        self.assertIn("selected no endpoint and never opened the TTY", normalized)
        self.assertIn("campaign-level multiplicity result", incident)
        self.assertIn("cable/dock connection was physically moved", incident)

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

    def test_target_contract_closes_physical_drift_and_rollback_rebinding(self):
        contract = " ".join(TARGET_CONTRACT.read_text(encoding="utf-8").split())
        required = (
            "through rollback transfer and verified final-health close",
            "The observer must never widen its selector or open an unapproved endpoint",
            "permanent `S22PLUS_F1_PHYSICAL_TOPOLOGY_CONTINUITY` boundary",
            "and has no expiry",
            "requires a new independent boundary review",
            "Process-v2 evidence must retain the exact endpoint identity, topology, host "
            "controller/device path, and immutable raw-snapshot receipt",
            "A missing, truncated, or unreadable snapshot is an observer failure",
            "Classification is phase-specific",
            "pre-session stop and has no consumed-run proof class",
            "host-silent device-result classification",
            "never changes an already retained experiment result",
            "A drifted topology does not authorize rollback against the new path",
            "the run parks without new device effects until "
            "a bounded, independently reviewed recovery-only path re-establishes one exact "
            "current rollback endpoint under a new immutable recovery binding ID",
            "the predeclared exact rollback resume",
            "does not retroactively validate candidate attribution",
            "Candidate replay remains forbidden",
        )
        for clause in required:
            self.assertIn(clause, contract)


if __name__ == "__main__":
    unittest.main()
