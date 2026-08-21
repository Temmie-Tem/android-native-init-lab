"""Host-only public H29 qualification-input checks; no private bytes or device."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/reports/A90_H29_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-21.json"
HANDOFF = ROOT / "docs/plans/A90_H29_MINIMAL_F1_QUALIFICATION_HANDOFF_2026-08-21.md"
BUILD_REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H29_H0_2026-08-21.md"
FLAT_MANIFEST = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h29/manifest.toml"
CONTINUATION_REVIEW = ROOT / "docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_INDEPENDENT_REVIEW_2026-08-21.json"
OWNER_SOURCE = ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
CONTINUATION_SOURCE = ROOT / "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py"
H28_CANDIDATE = "aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b"
H27_CANDIDATE = "fa7ab8af8cec027c433653da92eb6cb4ca6f3a02d7624a4f292f61906e8ce500"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


class A90H29QualificationInputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = json.loads(
            INPUT.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )

    def test_h0_authority_is_explicitly_false(self):
        self.assertEqual(
            self.value["authority"],
            {
                "candidate": False,
                "candidateAuthority": False,
                "d0": False,
                "f1": False,
                "live": False,
                "liveAuthority": False,
            },
        )
        self.assertEqual(
            set(self.value),
            {
                "schema", "capability", "scope", "targetProfile", "authority",
                "executionClosureSha256", "candidate", "expectedStart", "rollback",
                "freshState", "recovery", "recoveryIdentity", "continuationReview",
                "hazard", "build",
            },
        )
        self.assertTrue(all(type(value) is bool for value in self.value["authority"].values()))
        self.assertFalse(self.value["build"]["candidateAuthority"])
        self.assertEqual(self.value["schema"], "a90-boot-only-f1-minimal-review-input-v1")

    def test_current_owner_closure_and_exact_h29_identity(self):
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("a90_h29_owner", OWNER_SOURCE)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(self.value["executionClosureSha256"], module.execution_closure_sha256())
        self.assertEqual(self.value["candidate"], {
            "version": "0.11.196",
            "build": "phase3-minimal-h29-stock-rebuild-1007-cfp",
            "size": 58372096,
            "sha256": "c3d1b84eab65f387ce807cf9c355dc04dcc966cef15bf64e4fda901242907324",
        })
        self.assertNotIn(self.value["candidate"]["sha256"], {H27_CANDIDATE, H28_CANDIDATE})
        self.assertEqual(self.value["rollback"], {
            "version": module.V2321_ROLLBACK_VERSION,
            "build": module.V2321_ROLLBACK_BUILD,
            "size": module.V2321_ROLLBACK_SIZE,
            "sha256": module.V2321_ROLLBACK_SHA256,
        })

    def test_current_continuation_review_is_exact_public_pass_go(self):
        review = json.loads(CONTINUATION_REVIEW.read_text(encoding="utf-8"))
        declared = self.value["continuationReview"]
        self.assertEqual(declared["sha256"], sha256(CONTINUATION_REVIEW))
        self.assertEqual(declared["size"], CONTINUATION_REVIEW.stat().st_size)
        self.assertEqual(declared["executionClosureSha256"], review["executionClosureSha256"])
        self.assertEqual(review["executionClosureSha256"], "9b17904db2374664d91af10e98b8c8f9d4e1cdee5e8ac9514018838d4dfafeb5")
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertFalse(review["liveAuthority"])
        self.assertEqual(review["findings"], {"high": [], "low": [], "medium": []})
        self.assertTrue(all(value == 0 for value in review["contacts"].values()))
        self.assertEqual(review["scope"], "A90_F1_CANDIDATE_RETURN_CONTINUATION_AND_NO_REPLAY")

    def test_h29_public_artifact_digests_and_paths_are_bound(self):
        build = self.value["build"]
        self.assertEqual(build["reportSha256"], sha256(BUILD_REPORT))
        self.assertEqual(build["flatManifestSha256"], sha256(FLAT_MANIFEST))
        report = BUILD_REPORT.read_text(encoding="utf-8")
        manifest = FLAT_MANIFEST.read_text(encoding="utf-8")
        for text in (report, HANDOFF.read_text(encoding="utf-8")):
            self.assertIn(self.value["candidate"]["sha256"], text)
            self.assertIn(self.value["candidate"]["build"], text)
        self.assertIn(self.value["candidate"]["build"], manifest)
        self.assertIn("candidate_authority = false", manifest)
        self.assertEqual(self.value["freshState"], {
            "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h29.enable",
            "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h29.done",
        })

    def test_recovery_hash_is_private_unbound_not_fabricated(self):
        identity = self.value["recoveryIdentity"]
        self.assertIsNone(identity["adbSerialSha256"])
        self.assertEqual(identity["binding"], "PRIVATE_MANIFEST_BOUND_AT_D0")
        self.assertFalse(identity["rawSerialTracked"])
        self.assertEqual(identity["status"], "UNBOUND_PRIVATE_MANIFEST_REQUIRED")
        self.assertIn("UNBOUND_PRIVATE_MANIFEST_REQUIRED", HANDOFF.read_text(encoding="utf-8"))
        self.assertNotRegex(INPUT.read_text(encoding="utf-8"), r"(?:[A-Za-z0-9_-]{8,})\s+(?:device|recovery)\b")

    def test_hazard_digest_and_limits_are_exact(self):
        hazard = self.value["hazard"]
        self.assertTrue(hazard["accepted"])
        self.assertEqual(hazard["id"], "A90_SELF_BUILT_KERNEL_BOOT_ACCEPTANCE_WITH_NEW_BUILD_CERT")
        self.assertEqual(hazard["statementEncoding"], "UTF8_NO_TRAILING_NEWLINE")
        self.assertEqual(hashlib.sha256(hazard["statement"].encode()).hexdigest(), hazard["statementSha256"])
        for phrase in (
            "Snapdragon LLVM 10.0.7",
            "non-stock build certificate",
            "Android/vendor external-module compatibility",
            "H29 boot result remain unproved",
        ):
            self.assertIn(phrase, hazard["statement"])
        self.assertIn("no D0, approval, ordinal, F1", HANDOFF.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
