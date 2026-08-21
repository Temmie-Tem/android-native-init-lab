"""Public H30 qualification-input checks; no private bytes or device."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/reports/A90_H30_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-21.json"
HANDOFF = ROOT / "docs/plans/A90_H30_MINIMAL_F1_QUALIFICATION_HANDOFF_2026-08-21.md"
BUILD_REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H30_H0_2026-08-21.md"
FLAT_MANIFEST = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h30/manifest.toml"
CONTINUATION_REVIEW = ROOT / "docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_CURRENT_REVIEW.json"
QUALIFICATION_REVIEW = ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H30_INDEPENDENT_REVIEW_2026-08-21.json"
OWNER_SOURCE = ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
CONTINUATION_SOURCE = ROOT / "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py"
H29_CANDIDATE = "c3d1b84eab65f387ce807cf9c355dc04dcc966cef15bf64e4fda901242907324"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(path: Path):
    def reject(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise AssertionError(f"duplicate JSON key: {key}")
            value[key] = item
        return value
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class A90H30QualificationInputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = strict_json(INPUT)

    def test_authority_is_fully_false(self):
        self.assertEqual(self.value["authority"], {
            "candidate": False, "candidateAuthority": False, "d0": False,
            "f1": False, "live": False, "liveAuthority": False,
        })
        self.assertTrue(all(type(value) is bool for value in self.value["authority"].values()))
        self.assertFalse(self.value["build"]["candidateAuthority"])

    def test_current_owner_and_candidate_are_exact(self):
        owner = load("a90_h30_qualification_owner", OWNER_SOURCE)
        self.assertEqual(self.value["executionClosureSha256"], owner.execution_closure_sha256())
        self.assertEqual(self.value["candidate"], {
            "version": "0.11.197",
            "build": "phase3-minimal-h30-stock-rebuild-1007-cfp",
            "size": 58_372_096,
            "sha256": "d28bd41434d252619dd95ecb352f55140d93889fd599784c0a7dbf491959c5fe",
        })
        self.assertNotEqual(self.value["candidate"]["sha256"], H29_CANDIDATE)
        self.assertEqual(self.value["rollback"], {
            "version": owner.V2321_ROLLBACK_VERSION,
            "build": owner.V2321_ROLLBACK_BUILD,
            "size": owner.V2321_ROLLBACK_SIZE,
            "sha256": owner.V2321_ROLLBACK_SHA256,
        })

    def test_current_continuation_review_is_exact(self):
        continuation = load("a90_h30_qualification_continuation", CONTINUATION_SOURCE)
        review = strict_json(CONTINUATION_REVIEW)
        declared = self.value["continuationReview"]
        self.assertEqual(declared["path"], str(CONTINUATION_REVIEW.relative_to(ROOT)))
        self.assertEqual(declared["sha256"], sha256(CONTINUATION_REVIEW))
        self.assertEqual(declared["size"], CONTINUATION_REVIEW.stat().st_size)
        self.assertEqual(declared["executionClosureSha256"], continuation.execution_closure_sha256())
        self.assertEqual(review["executionClosureSha256"], continuation.execution_closure_sha256())
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertFalse(review["liveAuthority"])
        self.assertTrue(all(value == 0 for value in review["contacts"].values()))

    def test_build_and_fresh_state_bindings_are_exact(self):
        build = self.value["build"]
        self.assertEqual(build["reportSha256"], sha256(BUILD_REPORT))
        self.assertEqual(build["flatManifestSha256"], sha256(FLAT_MANIFEST))
        self.assertEqual(build["abBootSha256"], self.value["candidate"]["sha256"])
        self.assertEqual(self.value["freshState"], {
            "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h30.enable",
            "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h30.done",
        })
        for path in (BUILD_REPORT, HANDOFF):
            self.assertIn(self.value["candidate"]["sha256"], path.read_text(encoding="utf-8"))
        self.assertIn(
            self.value["candidate"]["build"],
            FLAT_MANIFEST.read_text(encoding="utf-8"),
        )

    def test_hazard_digest_and_h29_no_replay_are_exact(self):
        hazard = self.value["hazard"]
        self.assertTrue(hazard["accepted"])
        self.assertEqual(hashlib.sha256(hazard["statement"].encode()).hexdigest(), hazard["statementSha256"])
        for phrase in (
            "Snapdragon LLVM 10.0.7", "non-stock build certificate",
            "H30 boot result remain unproved", "H29 is consumed",
            "cannot be replayed",
        ):
            self.assertIn(phrase, hazard["statement"])

    def test_recovery_identity_is_private_and_unbound(self):
        identity = self.value["recoveryIdentity"]
        self.assertIsNone(identity["adbSerialSha256"])
        self.assertEqual(identity["binding"], "PRIVATE_MANIFEST_BOUND_AT_D0")
        self.assertFalse(identity["rawSerialTracked"])
        self.assertEqual(identity["status"], "UNBOUND_PRIVATE_MANIFEST_REQUIRED")

    def test_independent_review_binds_exact_h30_input(self):
        review = strict_json(QUALIFICATION_REVIEW)
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertEqual(review["executionClosureSha256"], self.value["executionClosureSha256"])
        self.assertEqual(review["candidateSha256"], self.value["candidate"]["sha256"])
        self.assertEqual(review["rollbackSha256"], self.value["rollback"]["sha256"])
        self.assertEqual(review["freshState"], self.value["freshState"])
        self.assertEqual(review["recovery"], self.value["recovery"])
        self.assertEqual(review["hazard"], {
            "accepted": True,
            "id": self.value["hazard"]["id"],
            "statementSha256": self.value["hazard"]["statementSha256"],
        })
        self.assertEqual(review["findings"], {"high": [], "low": [], "medium": []})
        self.assertTrue(all(value == 0 for value in review["contacts"].values()))
        self.assertFalse(review["liveAuthority"])
        self.assertEqual(
            sha256(QUALIFICATION_REVIEW),
            "f23766ea52ec3c1d35b46013b21587fbbed243179a5e4afe1e008c9b61ed06d6",
        )


if __name__ == "__main__":
    unittest.main()
