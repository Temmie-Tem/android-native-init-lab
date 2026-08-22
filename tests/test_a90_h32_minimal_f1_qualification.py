"""Public H32 candidate-qualification checks; no device or private bytes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/reports/A90_H32_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-22.json"
HANDOFF = ROOT / "docs/plans/A90_H32_MINIMAL_F1_QUALIFICATION_HANDOFF_2026-08-22.md"
REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H32_H0_2026-08-22.md"
MANIFEST = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h32/manifest.toml"
REVIEW = ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H32_INDEPENDENT_REVIEW_2026-08-22.json"
SUPERSESSION = ROOT / "docs/reports/A90_H32_MINIMAL_F1_QUALIFICATION_SUPERSEDED_2026-08-22.md"
OWNER = ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
CONTINUATION = ROOT / "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strict_json(path: Path):
    def reject_duplicates(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise AssertionError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class A90H32MinimalQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = _strict_json(INPUT)

    def test_historical_candidate_owner_and_rollback_are_exact(self) -> None:
        owner = _load("a90_h32_owner", OWNER)
        self.assertEqual(
            self.value["executionClosureSha256"],
            "0a6122d2902d9f72b8e4d1e1f9d23cbcc3767d48be50a01e052ba81a1c41745e",
        )
        self.assertNotEqual(self.value["executionClosureSha256"], owner.execution_closure_sha256())
        self.assertEqual(self.value["candidate"], {
            "version": "0.11.199",
            "build": "phase3-minimal-h32-stock-rebuild-1007-cfp",
            "size": 58_372_096,
            "sha256": "e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d",
        })
        self.assertEqual(self.value["rollback"], {
            "version": owner.V2321_ROLLBACK_VERSION,
            "build": owner.V2321_ROLLBACK_BUILD,
            "size": owner.V2321_ROLLBACK_SIZE,
            "sha256": owner.V2321_ROLLBACK_SHA256,
        })
        self.assertTrue(all(value is False for value in self.value["authority"].values()))

    def test_build_fresh_state_and_hazard_are_bound(self) -> None:
        build = self.value["build"]
        self.assertEqual(build["reportSha256"], _sha(REPORT))
        self.assertEqual(build["flatManifestSha256"], _sha(MANIFEST))
        self.assertEqual(build["effectiveManifestSha256"], "543d97a79db6ab0136ba6ef823ecc49b8f3558e98ace6ba37043c989ace74292")
        self.assertEqual(build["abBootSha256"], self.value["candidate"]["sha256"])
        self.assertEqual(build["abBootSize"], self.value["candidate"]["size"])
        self.assertEqual(self.value["freshState"], {
            "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h32.enable",
            "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h32.done",
        })
        hazard = self.value["hazard"]
        self.assertEqual(hashlib.sha256(hazard["statement"].encode()).hexdigest(), hazard["statementSha256"])
        self.assertEqual(hazard["statementSha256"], "cd8d868ac3b7fd5f5a934955a50ff2f32c228ab8b2e52e061d9f0ad90d73ca69")
        self.assertIn("H32 boot result remain unproved", hazard["statement"])
        self.assertIn("H29, H30, and H31 are consumed", hazard["statement"])

    def test_historical_continuation_lease_is_explicitly_superseded(self) -> None:
        continuation = _load("a90_h32_continuation", CONTINUATION)
        declared = self.value["continuationReview"]
        self.assertEqual(declared["sha256"], "7688558ec7a0b592053e04408d4a3863ae8a8ecc389c542d17ca906137c5d606")
        self.assertEqual(declared["size"], 547)
        self.assertEqual(declared["executionClosureSha256"], "585869c5c4eb843b165afea4ba1e5d10f228cda84dd1b924936e0ea0c369921f")
        self.assertNotEqual(declared["executionClosureSha256"], continuation.execution_closure_sha256())
        text = SUPERSESSION.read_text(encoding="utf-8")
        self.assertIn("SUPERSEDED_CONSUMED_CANDIDATE_AND_STALE_CLOSURE", text)
        self.assertIn("H33", text)
        self.assertIn("No H32 effect may replay", text)

    def test_recovery_identity_remains_private_and_unbound(self) -> None:
        identity = self.value["recoveryIdentity"]
        self.assertIsNone(identity["adbSerialSha256"])
        self.assertEqual(identity["binding"], "PRIVATE_MANIFEST_BOUND_AT_D0")
        self.assertFalse(identity["rawSerialTracked"])

    def test_handoff_binds_current_public_subject_without_authority(self) -> None:
        text = HANDOFF.read_text(encoding="utf-8")
        for expected in (
            self.value["executionClosureSha256"],
            self.value["continuationReview"]["executionClosureSha256"],
            self.value["continuationReview"]["sha256"],
            self.value["candidate"]["sha256"],
            self.value["hazard"]["statementSha256"],
            "Authority: none",
            "liveAuthority=false",
        ):
            self.assertIn(expected, text)

    def test_independent_review_binds_exact_input(self) -> None:
        self.assertEqual(_sha(INPUT), "9da1d3c29fbc36616e68b9c983e6fdc3386fd57a0345e764c8e6aabc6cf470d6")
        self.assertEqual(_sha(REVIEW), "c7454db67c768a68b661bec230d3206a2817558d7dc55634d9e062d0854dc49f")
        review = _strict_json(REVIEW)
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
