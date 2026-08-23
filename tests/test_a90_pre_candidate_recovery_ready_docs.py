from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/A90_PRE_CANDIDATE_RECOVERY_READY_OWNER_H0_2026-08-23.md"
REVIEW = ROOT / "docs/reports/A90_PRE_CANDIDATE_RECOVERY_READY_OWNER_INDEPENDENT_REVIEW_2026-08-23.json"
INCIDENT = ROOT / "docs/reports/A90_H35_NATIVE_RECOVERY_COMMAND_PREWRITE_FAILURE_2026-08-23.md"
DESIGN = ROOT / "docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md"
CONTRACT = ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md"
GOAL = ROOT / "GOAL_A90.md"

OWNER_CLOSURE = "b7c6809cf0388da2a44f2aa9fbca99cc60e9e00d6fdddc32d39e91c70bc3ce6f"
CONTINUATION_CLOSURE = "603b5467efee0dabd84ea1fa463452a303cc8cf4bc4ae55e3bc2c45d25860c3e"
POSTROLLBACK_CLOSURE = "4e30bc7ac67bec18157cfafa0994fb28f0738957b7e02deb74787ec59f7835be"
REVIEW_SHA256 = "2c21f00057fa6bcf81b8fccb4ed1c5c566007bc5b670744f19833859d92e6cd9"


class A90PreCandidateRecoveryReadyDocsTest(unittest.TestCase):
    def test_report_freezes_the_narrow_sequence_and_zero_candidate_failure(self) -> None:
        text = REPORT.read_text(encoding="utf-8")
        flat = " ".join(text.split())
        for token in (
            "IMPLEMENTED_AND_INDEPENDENTLY_REVIEWED_PASS_GO",
            "11-recovery-transition-intent.json",
            "12-recovery-ready.json",
            "13-recovery-transition-parked.json",
            "only after exact single-Samsung `04e8:6860` appears does it open ADB",
            "`--reuse-bound-recovery-only`",
            "no candidate guard, candidate intent, candidate helper, boot write, or rollback",
            "does not recursively rewrite private inputs",
            REVIEW.name,
            REVIEW_SHA256,
            "no D0, D1, F1",
        ):
            self.assertIn(token, flat)

    def test_review_is_canonical_exact_h0_pass_go(self) -> None:
        raw = REVIEW.read_bytes()
        self.assertEqual(len(raw), 753)
        self.assertFalse(raw.endswith(b"\n"))
        self.assertEqual(hashlib.sha256(raw).hexdigest(), REVIEW_SHA256)
        value = json.loads(raw)
        self.assertEqual(
            raw,
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )
        self.assertEqual(
            value,
            {
                "capability": "A90_BOOT_ONLY_F1_PRE_CANDIDATE_RECOVERY_READY_V1",
                "contacts": {
                    "adb": 0,
                    "device": 0,
                    "network": 0,
                    "otherTargets": 0,
                    "usb": 0,
                    "workspacePrivate": 0,
                    "writes": 0,
                },
                "continuationClosureSha256": CONTINUATION_CLOSURE,
                "contractReviewed": True,
                "findings": {"high": [], "low": [], "medium": []},
                "liveAuthority": False,
                "ownerClosureSha256": OWNER_CLOSURE,
                "postrollbackClosureSha256": POSTROLLBACK_CLOSURE,
                "reviewDate": "2026-08-23",
                "reviewer": "LUNA_MAX_INDEPENDENT_REVIEW",
                "schema": "a90-pre-candidate-recovery-ready-owner-independent-review-v1",
                "scope": "A90_OWNER_CONTINUATION_POSTROLLBACK_BRIDGE_REPAIR",
                "verdict": "PASS_GO",
            },
        )

    def test_contract_and_design_bind_arrival_not_response(self) -> None:
        contract = CONTRACT.read_text(encoding="utf-8")
        design = DESIGN.read_text(encoding="utf-8")
        for text in (contract, design):
            self.assertIn("candidate guard", text)
            self.assertIn("Recovery", text)
        self.assertIn("Command-response text is diagnostic only", contract)
        self.assertIn("response is diagnostic", design)
        self.assertIn("Native and the zero-endpoint", contract)
        self.assertIn("sends no Native recovery command", contract)
        self.assertLessEqual(len(design.splitlines()), 250)

    def test_h35_links_followup_and_goal_stays_bounded(self) -> None:
        self.assertIn(REPORT.name, INCIDENT.read_text(encoding="utf-8"))
        goal = GOAL.read_text(encoding="utf-8")
        self.assertEqual(len(goal.splitlines()), 900)
        self.assertIn("H0 host repairs are independently `PASS_GO`-reviewed", goal)
        self.assertIn("No H36 identity or authority exists", goal)


if __name__ == "__main__":
    unittest.main()
