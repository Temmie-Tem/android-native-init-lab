"""Public H34 qualification-input checks; no device or H34 review verdict."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/reports/A90_H34_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-22.json"
HANDOFF = ROOT / "docs/plans/A90_H34_MINIMAL_F1_QUALIFICATION_HANDOFF_2026-08-22.md"
REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H34_H0_2026-08-22.md"
MANIFEST = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h34/manifest.toml"
REVIEW = ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H34_INDEPENDENT_REVIEW_2026-08-22.json"
CONTINUATION_REVIEW = ROOT / "docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_CURRENT_REVIEW.json"
POSTROLLBACK_REVIEW = ROOT / "docs/reports/A90_F1_POSTROLLBACK_RECOVERY_CURRENT_REVIEW.json"
PRIVATE_MANIFEST = ROOT / "workspace/private/manifests/a90-h34-f1-20260822-01.json"
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


class A90H34MinimalQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = _strict_json(INPUT)

    def test_candidate_owner_rollback_and_current_capabilities_are_exact(self) -> None:
        owner = _load("a90_h34_owner", OWNER)
        continuation = _load("a90_h34_continuation", CONTINUATION)
        self.assertNotEqual(self.value["executionClosureSha256"], owner.execution_closure_sha256())
        self.assertEqual(self.value["executionClosureSha256"], "1c31fb97e8f181e63bd71949b020f647aa8dab45c63d13bd089f6be2659da8a8")
        self.assertEqual(self.value["candidate"], {
            "version": "0.11.201",
            "build": "phase3-minimal-h34-stock-rebuild-1007-cfp",
            "size": 58_372_096,
            "sha256": "233bfdcac20d5fdc1184a907e8e8b5cd4d2c1286dc08a8f6028cfcf5c90ad4ee",
        })
        self.assertEqual(self.value["rollback"], {
            "version": owner.V2321_ROLLBACK_VERSION,
            "build": owner.V2321_ROLLBACK_BUILD,
            "size": owner.V2321_ROLLBACK_SIZE,
            "sha256": owner.V2321_ROLLBACK_SHA256,
        })
        self.assertEqual(self.value["continuationReview"]["executionClosureSha256"], "d053e137ca6d984709e53a1200d1e980f6d766ab4dd30cbb012cef2ddd3ee9e1")
        self.assertNotEqual(self.value["continuationReview"]["executionClosureSha256"], continuation.execution_closure_sha256())
        self.assertNotEqual(self.value["continuationReview"]["sha256"], _sha(CONTINUATION_REVIEW))
        self.assertNotEqual(self.value["postrollbackReview"]["sha256"], _sha(POSTROLLBACK_REVIEW))
        self.assertTrue(all(value is False for value in self.value["authority"].values()))

    def test_build_fresh_state_and_pending_hazard_are_bound(self) -> None:
        build = self.value["build"]
        self.assertEqual(build["reportSha256"], "d4dc538fce7c80504bd3ce8c804d7a95a70d31f84d7cc35249fcd411fd72d08d")
        self.assertNotEqual(build["reportSha256"], _sha(REPORT))
        self.assertEqual(build["flatManifestSha256"], "d2f27becfe42491519dd82defafaa82bb974e125dfc937b38f44b62370c5014d")
        self.assertNotEqual(build["flatManifestSha256"], _sha(MANIFEST))
        self.assertEqual(build["effectiveManifestSha256"], "77de213ddbb02a2e4c5abec91e1f0b454717c1c62dd0cbf2504f4c225336cd19")
        self.assertEqual(build["abBootSha256"], self.value["candidate"]["sha256"])
        self.assertEqual(build["abBootSize"], self.value["candidate"]["size"])
        self.assertEqual(self.value["freshState"], {
            "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h34.enable",
            "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h34.done",
        })
        hazard = self.value["hazard"]
        self.assertTrue(hazard["accepted"])
        self.assertEqual(hashlib.sha256(hazard["statement"].encode()).hexdigest(), hazard["statementSha256"])
        self.assertIn("H34 boot result remain unproved", hazard["statement"])
        self.assertIn("H29, H30, H31, H32, and H33 are consumed", hazard["statement"])
        self.assertEqual(self.value["independentReview"]["status"], "PENDING_INDEPENDENT_REVIEW")
        self.assertIsNone(self.value["independentReview"]["verdict"])

    def test_current_capability_leases_and_h34_review_are_exact(self) -> None:
        continuation = _strict_json(CONTINUATION_REVIEW)
        postrollback = _strict_json(POSTROLLBACK_REVIEW)
        self.assertEqual(continuation["verdict"], "PASS_GO")
        self.assertEqual(continuation["executionClosureSha256"], "981a3f06ce38a288a8ab9c5ef76234bc38c97b51359fd2f46bfb4ed714d7ae3d")
        self.assertEqual(postrollback["verdict"], "PASS_GO")
        self.assertEqual(postrollback["executionClosureSha256"], "148525430a5cd9f875df4cb39766c6c72a8093f2155ea1bc6e312aea8f45cf5d")
        self.assertTrue(all(value == 0 for value in continuation["contacts"].values()))
        self.assertTrue(all(value == 0 for value in postrollback["contacts"].values()))
        self.assertFalse(continuation["liveAuthority"])
        self.assertFalse(postrollback["liveAuthority"])
        self.assertTrue(REVIEW.is_file())
        review = _strict_json(REVIEW)
        self.assertEqual(_sha(REVIEW), "9741aa0a5b9f0fdc93d5210e195fda5353270d6406713efa4d86ba3b720036d3")
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

    def test_handoff_binds_current_subject_without_authority(self) -> None:
        text = HANDOFF.read_text(encoding="utf-8")
        for expected in (
            self.value["executionClosureSha256"],
            self.value["continuationReview"]["executionClosureSha256"],
            self.value["continuationReview"]["sha256"],
            self.value["postrollbackReview"]["sha256"],
            self.value["candidate"]["sha256"],
            self.value["hazard"]["statementSha256"],
            "Authority: none",
            "`PENDING_INDEPENDENT_REVIEW` and a null verdict",
            "current H34 independent\nreview is now `PASS_GO`",
            "9741aa0a5b9f0fdc93d5210e195fda5353270d6406713efa4d86ba3b720036d3",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("liveAuthority=true", text)

    def test_private_manifest_binds_current_review_and_schema_when_enabled(self) -> None:
        if os.environ.get("A90_H34_VERIFY_PRIVATE") != "1":
            self.skipTest("set A90_H34_VERIFY_PRIVATE=1 for private H34 manifest verification")
        owner = _load("a90_h34_private_owner", OWNER)
        raw, value = owner.load_manifest(PRIVATE_MANIFEST.resolve())
        self.assertEqual(value["runId"], "a90-h34-f1-20260822-01")
        self.assertEqual(value["candidate"]["sha256"], self.value["candidate"]["sha256"])
        self.assertEqual(value["qualification"]["review"]["size"], 1181)
        self.assertEqual(value["qualification"]["review"]["sha256"], "9741aa0a5b9f0fdc93d5210e195fda5353270d6406713efa4d86ba3b720036d3")
        self.assertEqual(len(raw), 1970)
        self.assertTrue(value["qualification"]["hazard"]["accepted"])


if __name__ == "__main__":
    unittest.main()
