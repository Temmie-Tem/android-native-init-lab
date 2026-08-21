from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
HISTORICAL_READER = ROOT / "workspace/public/src/scripts/server-distro/a90_h28_physical_system_return_reconcile_v1.py"
INPUT = ROOT / "docs/reports/A90_H28_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-21.json"
HANDOFF = ROOT / "docs/plans/A90_H28_MINIMAL_F1_QUALIFICATION_HANDOFF_2026-08-21.md"
REVIEW = ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H28_INDEPENDENT_REVIEW_2026-08-21.json"
BUILD_REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H28_H0_2026-08-21.md"
FLAT_MANIFEST = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h28/manifest.toml"
H28_HISTORICAL_CLOSURE = (
    "0dca4f3ddc98eb4625411c93ad7c1748f3c016aab0075a570652ca946fc4eb1f"
)

SPEC = importlib.util.spec_from_file_location("a90_boot_only_f1_minimal_v1", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)
READER_SPEC = importlib.util.spec_from_file_location(
    "a90_h28_physical_system_return_reconcile_v1", HISTORICAL_READER
)
assert READER_SPEC and READER_SPEC.loader
R = importlib.util.module_from_spec(READER_SPEC)
sys.modules[READER_SPEC.name] = R
READER_SPEC.loader.exec_module(R)


class H28MinimalF1QualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = json.loads(INPUT.read_text())

    def test_input_is_h0_only_and_candidate_neutral(self):
        self.assertEqual(
            self.value["schema"], "a90-boot-only-f1-minimal-review-input-v1"
        )
        self.assertEqual(self.value["scope"], M.QUALIFICATION_REVIEW_SCOPE)
        self.assertEqual(self.value["targetProfile"], M.TARGET_PROFILE)
        self.assertEqual(
            self.value["authority"],
            {"candidate": False, "d0": False, "f1": False, "live": False},
        )

    def test_historical_execution_closure_is_pinned_and_stale_for_new_owner(self):
        self.assertEqual(
            self.value["executionClosureSha256"], H28_HISTORICAL_CLOSURE
        )
        review = json.loads(REVIEW.read_text())
        self.assertEqual(review["executionClosureSha256"], H28_HISTORICAL_CLOSURE)
        self.assertNotEqual(H28_HISTORICAL_CLOSURE, M.execution_closure_sha256())

    def test_independent_review_is_historical_and_rejected_for_new_owner_execution(self):
        raw = REVIEW.read_bytes()
        self.assertFalse(raw.endswith(b"\n"))
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "51474c2d323971c07ca1425be613ea48cdd6c13f870606b166fba76835e6a9b2",
        )
        review = M.parse_canonical(raw, "H28 independent review")
        manifest = {
            "candidate": {"sha256": self.value["candidate"]["sha256"]},
            "rollback": {"sha256": self.value["rollback"]["sha256"]},
            "qualification": {
                "recovery": self.value["recovery"],
                "hazard": {
                    key: self.value["hazard"][key]
                    for key in ("id", "statementSha256", "accepted")
                },
                "freshState": self.value["freshState"],
            },
        }
        self.assertEqual(review["executionClosureSha256"], H28_HISTORICAL_CLOSURE)
        with self.assertRaises(M.ContractError):
            M._validate_qualification_review(review, manifest)
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertFalse(review["liveAuthority"])
        self.assertTrue(all(value == 0 for value in review["contacts"].values()))

    def test_consumed_h28_reader_accepts_only_pinned_historical_review(self):
        historical_manifest = {
            "runId": R.RUN_ID,
            "capability": M.CAPABILITY,
            "targetProfile": M.TARGET_PROFILE,
            "candidate": {"sha256": self.value["candidate"]["sha256"]},
            "rollback": {"sha256": self.value["rollback"]["sha256"]},
            "qualification": {
                "review": {
                    "path": str(REVIEW),
                    "size": REVIEW.stat().st_size,
                    "sha256": hashlib.sha256(REVIEW.read_bytes()).hexdigest(),
                },
                "recovery": self.value["recovery"],
                "hazard": {
                    key: self.value["hazard"][key]
                    for key in ("id", "statementSha256", "accepted")
                },
                "freshState": self.value["freshState"],
            },
        }
        R._verify_historical_qualification_binding(historical_manifest)
        with self.assertRaises(M.ContractError):
            M._validate_qualification_review(
                json.loads(REVIEW.read_text()),
                {
                    "candidate": historical_manifest["candidate"],
                    "rollback": historical_manifest["rollback"],
                    "qualification": historical_manifest["qualification"],
                },
            )
        for field, bad in (
            ("path", str(ROOT / "docs/reports/foreign-review.json")),
            ("size", 1190),
            ("sha256", "0" * 64),
        ):
            with self.subTest(field=field):
                changed = json.loads(json.dumps(historical_manifest))
                changed["qualification"]["review"][field] = bad
                with self.assertRaises(R.ContractError):
                    R._verify_historical_qualification_binding(changed)

    def test_h28_and_v2321_identities_are_exact(self):
        candidate = self.value["candidate"]
        self.assertEqual(candidate, {
            "version": "0.11.195",
            "build": "phase3-minimal-h28-stock-rebuild-1007-cfp",
            "size": 58_372_096,
            "sha256": "aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b",
        })
        self.assertEqual(self.value["expectedStart"], {
            "version": M.V2321_ROLLBACK_VERSION,
            "build": M.V2321_ROLLBACK_BUILD,
        })
        self.assertEqual(self.value["rollback"]["sha256"], M.V2321_ROLLBACK_SHA256)
        for text in (BUILD_REPORT.read_text(), HANDOFF.read_text()):
            self.assertIn(candidate["sha256"], text)
            self.assertIn(candidate["build"], text)
        self.assertIn(candidate["build"], FLAT_MANIFEST.read_text())

    def test_hazard_statement_digest_and_limits_are_exact(self):
        hazard = self.value["hazard"]
        self.assertEqual(hazard["statementEncoding"], "UTF8_NO_TRAILING_NEWLINE")
        self.assertEqual(
            hashlib.sha256(hazard["statement"].encode("utf-8")).hexdigest(),
            hazard["statementSha256"],
        )
        self.assertTrue(hazard["accepted"])
        for phrase in (
            "non-stock build certificate",
            "Android/vendor external-module compatibility",
            "full build reproducibility",
            "H27 boot-loop cause remain unproved",
        ):
            self.assertIn(phrase, hazard["statement"])

    def test_h28_fresh_state_and_legacy_scope_do_not_alias(self):
        fresh = self.value["freshState"]
        self.assertEqual(fresh, {
            "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h28.enable",
            "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h28.done",
        })
        projected = {
            "candidate": {"sha256": self.value["candidate"]["sha256"]},
            "qualification": {
                "hazard": {
                    "id": self.value["hazard"]["id"],
                    "statementSha256": self.value["hazard"]["statementSha256"],
                    "accepted": self.value["hazard"]["accepted"],
                },
                "freshState": fresh,
            },
        }
        self.assertTrue(M._review_scope_is_allowed(
            {"scope": M.QUALIFICATION_REVIEW_SCOPE}, projected
        ))
        self.assertFalse(M._review_scope_is_allowed(
            {"scope": M.LEGACY_H27_REVIEW_SCOPE}, projected
        ))


if __name__ == "__main__":
    unittest.main()
