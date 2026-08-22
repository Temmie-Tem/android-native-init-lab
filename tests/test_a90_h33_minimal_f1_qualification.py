"""Public H33 qualification-input checks; no device or private bytes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/reports/A90_H33_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-22.json"
HANDOFF = ROOT / "docs/plans/A90_H33_MINIMAL_F1_QUALIFICATION_HANDOFF_2026-08-22.md"
REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H33_H0_2026-08-22.md"
MANIFEST = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h33/manifest.toml"
REVIEW = ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H33_INDEPENDENT_REVIEW_2026-08-22.json"
PRIVATE_MANIFEST = ROOT / "workspace/private/manifests/a90-h33-f1-20260822-01.json"
OWNER = ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
CONTINUATION = ROOT / "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py"
CURRENT_CONTINUATION_REVIEW = ROOT / "docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_CURRENT_REVIEW.json"


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


class A90H33MinimalQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = _strict_json(INPUT)

    def test_candidate_owner_and_rollback_are_fresh_and_exact(self) -> None:
        owner = _load("a90_h33_owner", OWNER)
        continuation = _load("a90_h33_continuation", CONTINUATION)
        self.assertEqual(
            self.value["executionClosureSha256"],
            "48cb09e35b25f02e15fde091c93f2755b366fcb561210df49ffbafea3d333854",
        )
        self.assertNotEqual(self.value["executionClosureSha256"], owner.execution_closure_sha256())
        self.assertEqual(self.value["candidate"], {
            "version": "0.11.200",
            "build": "phase3-minimal-h33-stock-rebuild-1007-cfp",
            "size": 58_372_096,
            "sha256": "bdbcfc5fb82150c2d508df1e4d7ae7b71f0659b7d6b02ddab506f263f6063e12",
        })
        self.assertEqual(self.value["rollback"], {
            "version": owner.V2321_ROLLBACK_VERSION,
            "build": owner.V2321_ROLLBACK_BUILD,
            "size": owner.V2321_ROLLBACK_SIZE,
            "sha256": owner.V2321_ROLLBACK_SHA256,
        })
        self.assertEqual(
            self.value["continuationReview"]["executionClosureSha256"],
            "a62318c74c334509560f7c84fead011eb0a0c7fa6d8a80a45b4d72539a97a4df",
        )
        self.assertNotEqual(
            self.value["continuationReview"]["executionClosureSha256"],
            continuation.execution_closure_sha256(),
        )
        self.assertTrue(all(value is False for value in self.value["authority"].values()))

    def test_build_fresh_state_and_pending_hazard_are_bound(self) -> None:
        build = self.value["build"]
        self.assertEqual(build["reportSha256"], "9f404ea0a0c599b54face948407fb82627a92bbdd1ad8859a4c6e7bda1b0d63d")
        self.assertNotEqual(build["reportSha256"], _sha(REPORT))
        self.assertEqual(build["flatManifestSha256"], _sha(MANIFEST))
        self.assertEqual(build["effectiveManifestSha256"], "591967b80e3b67ce01e1592819912e164cba3e58f6bbbcc10ca35e5a900a45a2")
        self.assertEqual(build["abBootSha256"], self.value["candidate"]["sha256"])
        self.assertEqual(build["abBootSize"], self.value["candidate"]["size"])
        self.assertEqual(self.value["freshState"], {
            "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h33.enable",
            "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h33.done",
        })
        hazard = self.value["hazard"]
        self.assertTrue(hazard["accepted"])
        self.assertEqual(hashlib.sha256(hazard["statement"].encode()).hexdigest(), hazard["statementSha256"])
        self.assertIn("H33 boot result remain unproved", hazard["statement"])
        self.assertIn("H29, H30, H31, and H32 are consumed", hazard["statement"])

    def test_current_continuation_review_is_the_only_review_lease(self) -> None:
        declared = self.value["continuationReview"]
        self.assertEqual(declared["size"], 547)
        self.assertEqual(declared["sha256"], "6bf984a2c5ff7ce3b7487b1af63073a88664c130f0137a9e2ab40104db47aac8")
        self.assertNotEqual(declared["sha256"], _sha(CURRENT_CONTINUATION_REVIEW))
        self.assertEqual(declared["executionClosureSha256"], "a62318c74c334509560f7c84fead011eb0a0c7fa6d8a80a45b4d72539a97a4df")
        current = _strict_json(CURRENT_CONTINUATION_REVIEW)
        self.assertEqual(_sha(CURRENT_CONTINUATION_REVIEW), "22fba68f002bf7e35b9e15d1b12cfed906e33de4bd1a0e56982bcc78f4acd120")
        self.assertEqual(current["executionClosureSha256"], "981a3f06ce38a288a8ab9c5ef76234bc38c97b51359fd2f46bfb4ed714d7ae3d")
        self.assertEqual(current["verdict"], "PASS_GO")
        self.assertFalse(declared["liveAuthority"])
        self.assertTrue(REVIEW.is_file())
        self.assertEqual(_sha(REVIEW), "251235439de66b408397768201016c390bbf4d3d94bd73877117501b21294f77")
        self.assertEqual(self.value["independentReview"]["status"], "PENDING_INDEPENDENT_REVIEW")
        self.assertIsNone(self.value["independentReview"]["verdict"])

    def test_current_h33_review_binds_exact_frozen_input(self) -> None:
        review = _strict_json(REVIEW)
        owner = _load("a90_h33_repaired_owner", OWNER)
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertEqual(review["executionClosureSha256"], self.value["executionClosureSha256"])
        self.assertNotEqual(review["executionClosureSha256"], owner.execution_closure_sha256())
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

    def test_recovery_identity_remains_private_and_unbound_in_public_input(self) -> None:
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
            "PENDING_INDEPENDENT_REVIEW at input freeze",
            "the current independent review is now `PASS_GO`",
            "251235439de66b408397768201016c390bbf4d3d94bd73877117501b21294f77",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("PASS_GO qualifies H33", text)
        self.assertNotIn("liveAuthority=true", text)

    def test_private_manifest_binds_historical_review_but_is_not_current_authority_when_enabled(self) -> None:
        if os.environ.get("A90_H33_VERIFY_PRIVATE") != "1":
            self.skipTest("set A90_H33_VERIFY_PRIVATE=1 for private H33 manifest verification")
        value = _strict_json(PRIVATE_MANIFEST)
        self.assertEqual(value["runId"], "a90-h33-f1-20260822-01")
        self.assertNotIn("preparationStatus", value)
        self.assertEqual(value["candidate"]["sha256"], self.value["candidate"]["sha256"])
        self.assertEqual(set(value["qualification"]["review"]), {"path", "size", "sha256"})
        self.assertEqual(value["qualification"]["review"]["size"], 1181)
        self.assertEqual(value["qualification"]["review"]["sha256"], "251235439de66b408397768201016c390bbf4d3d94bd73877117501b21294f77")
        owner = _load("a90_h33_private_repaired_owner", OWNER)
        self.assertNotEqual(
            self.value["executionClosureSha256"], owner.execution_closure_sha256()
        )
        self.assertTrue(value["qualification"]["hazard"]["accepted"])


if __name__ == "__main__":
    unittest.main()
