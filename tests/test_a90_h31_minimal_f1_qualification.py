"""Public H31 candidate-qualification checks; no device or private bytes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/reports/A90_H31_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-22.json"
REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H31_H0_2026-08-22.md"
MANIFEST = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h31/manifest.toml"
CONTINUATION_REVIEW = ROOT / "docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_CURRENT_REVIEW.json"
REVIEW = ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H31_INDEPENDENT_REVIEW_2026-08-22.json"
OWNER = ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
CONTINUATION = ROOT / "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class A90H31MinimalQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = json.loads(INPUT.read_text(encoding="utf-8"))

    def test_candidate_owner_and_rollback_are_exact(self) -> None:
        owner = _load("a90_h31_owner", OWNER)
        self.assertEqual(self.value["executionClosureSha256"], owner.execution_closure_sha256())
        self.assertEqual(self.value["candidate"], {
            "version": "0.11.198",
            "build": "phase3-minimal-h31-stock-rebuild-1007-cfp",
            "size": 58_372_096,
            "sha256": "5ad0fe043e39482163d10b1870f79c85780c12642bc04d9ee65d3eee8dd323f9",
        })
        self.assertEqual(self.value["rollback"]["sha256"], owner.V2321_ROLLBACK_SHA256)
        self.assertTrue(all(value is False for value in self.value["authority"].values()))

    def test_build_fresh_state_and_hazard_are_bound(self) -> None:
        build = self.value["build"]
        self.assertEqual(build["reportSha256"], _sha(REPORT))
        self.assertEqual(build["flatManifestSha256"], _sha(MANIFEST))
        self.assertEqual(build["abBootSha256"], self.value["candidate"]["sha256"])
        self.assertEqual(self.value["freshState"], {
            "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h31.enable",
            "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h31.done",
        })
        hazard = self.value["hazard"]
        self.assertEqual(hashlib.sha256(hazard["statement"].encode()).hexdigest(), hazard["statementSha256"])
        self.assertIn("H31 boot result remain unproved", hazard["statement"])
        self.assertIn("H29 and H30 are consumed", hazard["statement"])

    def test_current_continuation_lease_is_exact(self) -> None:
        continuation = _load("a90_h31_continuation", CONTINUATION)
        declared = self.value["continuationReview"]
        self.assertEqual(declared["sha256"], _sha(CONTINUATION_REVIEW))
        self.assertEqual(declared["size"], CONTINUATION_REVIEW.stat().st_size)
        self.assertEqual(declared["executionClosureSha256"], continuation.execution_closure_sha256())
        review = json.loads(CONTINUATION_REVIEW.read_text(encoding="utf-8"))
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertFalse(review["liveAuthority"])

    def test_recovery_identity_remains_private_and_unbound(self) -> None:
        identity = self.value["recoveryIdentity"]
        self.assertIsNone(identity["adbSerialSha256"])
        self.assertEqual(identity["binding"], "PRIVATE_MANIFEST_BOUND_AT_D0")
        self.assertFalse(identity["rawSerialTracked"])

    def test_independent_review_binds_exact_input(self) -> None:
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertEqual(review["executionClosureSha256"], self.value["executionClosureSha256"])
        self.assertEqual(review["candidateSha256"], self.value["candidate"]["sha256"])
        self.assertEqual(review["rollbackSha256"], self.value["rollback"]["sha256"])
        self.assertEqual(review["freshState"], self.value["freshState"])
        self.assertEqual(review["hazard"], {
            "accepted": True,
            "id": self.value["hazard"]["id"],
            "statementSha256": self.value["hazard"]["statementSha256"],
        })
        self.assertTrue(all(value == 0 for value in review["contacts"].values()))
        self.assertFalse(review["liveAuthority"])


if __name__ == "__main__":
    unittest.main()
