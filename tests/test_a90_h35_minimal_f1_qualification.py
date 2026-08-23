"""Public H35 qualification-input checks; no private bytes or device contact."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/reports/A90_H35_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-23.json"
HANDOFF = ROOT / "docs/plans/A90_H35_MINIMAL_F1_QUALIFICATION_HANDOFF_2026-08-23.md"
PACKAGE_REPORT = ROOT / "docs/reports/A90_H35_PUBLIC_MPGEN_RTIC_CANARY_PACKAGE_H0_2026-08-23.md"
MANIFEST = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h35/manifest.toml"
CONTINUATION_REVIEW = ROOT / "docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_CURRENT_REVIEW.json"
POSTROLLBACK_REVIEW = ROOT / "docs/reports/A90_F1_POSTROLLBACK_RECOVERY_CURRENT_REVIEW.json"
HAZARD_REVIEW = ROOT / "docs/reports/A90_RTIC_PUBLIC_MPGEN_CANARY_HAZARD_INDEPENDENT_REVIEW_2026-08-23.json"
PACKAGE_REVIEW = ROOT / "docs/reports/A90_H35_PUBLIC_MPGEN_RTIC_CANARY_PACKAGE_INDEPENDENT_REVIEW_2026-08-23.json"
INDEPENDENT_REVIEW = ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H35_INDEPENDENT_REVIEW_2026-08-23.json"
PRIVATE_MANIFEST = ROOT / "workspace/private/manifests/a90-h35-f1-20260823-01.json"
OWNER = ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
CONTINUATION = ROOT / "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py"
POSTROLLBACK = ROOT / "workspace/public/src/scripts/server-distro/a90_f1_postrollback_recovery_v1.py"

EXPECTED_INPUT_SHA256 = (
    "1f70b880b482db50b3347102ad60f911bf9f28d07434db5adc06abf061dfff7a"
)
EXPECTED_OWNER_CLOSURE = (
    "455c486c3e4da2ec07b4ccf674c69625a4eb9661ae30c89924ab5f2c3363c0c8"
)
EXPECTED_CONTINUATION_CLOSURE = (
    "981a3f06ce38a288a8ab9c5ef76234bc38c97b51359fd2f46bfb4ed714d7ae3d"
)
EXPECTED_POSTROLLBACK_CLOSURE = (
    "148525430a5cd9f875df4cb39766c6c72a8093f2155ea1bc6e312aea8f45cf5d"
)
EXPECTED_CANDIDATE_SHA256 = (
    "5e2a44420195090e75f63e350cacdbcad88710e77cef9bcf29a6d3ee6f4ad759"
)
EXPECTED_ROLLBACK_SHA256 = (
    "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
)
EXPECTED_REVIEW_SHA256 = (
    "fa02661d1fbe1ef6e02c3692c1329f1db75b9855bc1365d08b694a49bac15fe1"
)
EXPECTED_PRIVATE_MANIFEST_SHA256 = (
    "d9cfa60c2b8cc306f96f506ca0fdb52d315b495531a55198c8d9afedc1b7ebaf"
)
EXPECTED_HAZARD_STATEMENT = (
    "Exact H35 0.11.202 / phase3-minimal-h35-public-mpgen-rtic-canary is the "
    "byte-identical A/B boot at SHA-256 "
    "5e2a44420195090e75f63e350cacdbcad88710e77cef9bcf29a6d3ee6f4ad759 and "
    "contains exact carrier "
    "15b49a71aeb2342a5b5a7e24de27f78a4124bf877f6d8d8f28aaab928fa6bd71 from "
    "reviewed Image "
    "1ddae56f8df97030794a590192e4a4162876736029b1a54fd26173c9287002b7 and "
    "RTIC DTB "
    "68e6ab5bb2ccdde5e3d87086110257176c0fe55726d1d4f5db6eba3a4b6aca04. "
    "Structural RTIC and packaging are proved, while H1-H6 remain: non-stock "
    "MPGen content version, candidate-derived measured extent, public producer "
    "provenance, proprietary RTIC/QHEE response, possible proprietary whole-Image "
    "measurement, and standalone-product secondary-input gaps. Hazard review "
    "d180b3637bb36eefce7c28251a8c17ddb73393068135b4dff16972e5f86a8c94 and "
    "package review "
    "843524b45415ef09d1c311ecf88bdb3243b32c65f01a781bb167cbd8a56ec397 accept "
    "only one future attended boot-only Native-health canary with exact V2321 "
    "rollback. H29-H34 are consumed and current V2321 health is unproved. "
    "Success proves only exact H35 Native health; a failure without "
    "device-attributable evidence is NO_PROOF_OBSERVER and cannot be attributed "
    "specifically to RTIC. Candidate replay is forbidden; first-opportunity "
    "failed-boot evidence precedes journal-bound rollback/recovery. No Debian, "
    "Wi-Fi, external-module, Android, stock-equivalence, or production-stability "
    "claim is included."
)


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


def _assert_all_false_authority(authority: dict[str, object]) -> None:
    expected = {"candidate", "candidateAuthority", "d0", "f1", "live", "liveAuthority"}
    if set(authority) != expected:
        raise AssertionError("authority keys are not exact")
    if any(type(value) is not bool or value is not False for value in authority.values()):
        raise AssertionError("authority is not exact boolean false")


def _assert_zero_contacts(contacts: dict[str, object]) -> None:
    expected = {"dev", "device", "network", "otherTargets", "usb", "workspacePrivate", "writes"}
    allowed = (expected, expected | {"adb"})
    if set(contacts) not in allowed:
        raise AssertionError("contact keys are not exact")
    if any(type(value) is not int or value != 0 for value in contacts.values()):
        raise AssertionError("contacts are not exact integer zero")


def _assert_hazard_statement(hazard: dict[str, object]) -> None:
    if hazard["statement"] != EXPECTED_HAZARD_STATEMENT:
        raise AssertionError("hazard statement changed")
    if hazard["statementEncoding"] != "UTF8_NO_TRAILING_NEWLINE":
        raise AssertionError("hazard statement encoding changed")
    if hashlib.sha256(hazard["statement"].encode("utf-8")).hexdigest() != hazard["statementSha256"]:
        raise AssertionError("hazard statement digest mismatch")


def _assert_evidence_review_binding(declared: dict[str, object], path: Path) -> None:
    if declared["size"] != path.stat().st_size or declared["sha256"] != _sha(path):
        raise AssertionError(f"evidence review bytes drifted: {path}")
    review = _strict_json(path)
    for key in ("schema", "verdict"):
        if review[key] != declared[key]:
            raise AssertionError(f"evidence review {key} drifted: {path}")
    if review.get("liveAuthority") is not False:
        raise AssertionError(f"evidence review authority drifted: {path}")


class A90H35MinimalQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = _strict_json(INPUT)

    def test_strict_json_and_historical_closures_are_frozen_but_stale(self) -> None:
        owner = _load("a90_h35_owner", OWNER)
        continuation = _load("a90_h35_continuation", CONTINUATION)
        postrollback = _load("a90_h35_postrollback", POSTROLLBACK)
        self.assertEqual(_sha(INPUT), EXPECTED_INPUT_SHA256)
        self.assertEqual(self.value["executionClosureSha256"], EXPECTED_OWNER_CLOSURE)
        self.assertNotEqual(owner.execution_closure_sha256(), EXPECTED_OWNER_CLOSURE)
        self.assertEqual(
            self.value["continuationReview"]["executionClosureSha256"],
            EXPECTED_CONTINUATION_CLOSURE,
        )
        self.assertNotEqual(continuation.execution_closure_sha256(), EXPECTED_CONTINUATION_CLOSURE)
        self.assertEqual(self.value["postrollbackReview"]["executionClosureSha256"], EXPECTED_POSTROLLBACK_CLOSURE)
        self.assertNotEqual(postrollback.execution_closure_sha256(), EXPECTED_POSTROLLBACK_CLOSURE)
        with self.assertRaises(AssertionError):
            json.loads('{"duplicate":1,"duplicate":2}', object_pairs_hook=lambda pairs: _strict_pairs(pairs))

    def test_exact_candidate_rollback_fresh_state_and_authority(self) -> None:
        owner = _load("a90_h35_owner_artifacts", OWNER)
        _assert_all_false_authority(self.value["authority"])
        self.assertEqual(self.value["capability"], "A90_BOOT_ONLY_F1_MINIMAL_V1")
        self.assertEqual(self.value["scope"], "A90_MINIMAL_BOOT_ONLY_F1_EXECUTION_AND_CANDIDATE_HAZARD")
        self.assertEqual(self.value["targetProfile"], "SAMSUNG_A90_5G")
        self.assertEqual(self.value["candidate"], {
            "version": "0.11.202",
            "build": "phase3-minimal-h35-public-mpgen-rtic-canary",
            "size": 58_372_096,
            "sha256": EXPECTED_CANDIDATE_SHA256,
        })
        self.assertEqual(self.value["expectedStart"], {
            "version": owner.V2321_ROLLBACK_VERSION,
            "build": owner.V2321_ROLLBACK_BUILD,
        })
        self.assertEqual(self.value["rollback"], {
            "version": owner.V2321_ROLLBACK_VERSION,
            "build": owner.V2321_ROLLBACK_BUILD,
            "size": owner.V2321_ROLLBACK_SIZE,
            "sha256": EXPECTED_ROLLBACK_SHA256,
        })
        self.assertEqual(self.value["freshState"], {
            "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h35.enable",
            "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h35.done",
        })
        self.assertEqual(self.value["recovery"], {
            "demonstrated": True,
            "method": "NATIVE_TO_STABLE_ADB_BASELINE_SINGLE_NEW_RECOVERY_ARRIVAL_BOOT_READBACK_V1",
            "profile": "A90_ATTENDED_PHYSICAL_RECOVERY_V1",
        })
        self.assertEqual(self.value["recoveryIdentity"], {
            "adbSerialSha256": None,
            "binding": "PRIVATE_MANIFEST_BOUND_AT_D0",
            "rawSerialTracked": False,
            "status": "UNBOUND_PRIVATE_MANIFEST_REQUIRED",
        })

    def test_h35_continuation_and_postrollback_review_bytes_are_frozen_and_stale(self) -> None:
        continuation = _load("a90_h35_stale_continuation", CONTINUATION)
        postrollback = _load("a90_h35_stale_postrollback", POSTROLLBACK)
        for declared, path, expected in (
            (self.value["continuationReview"], CONTINUATION_REVIEW, {
                "capability": "A90_F1_CANDIDATE_RETURN_CONTINUATION_V1",
                "schema": "a90-f1-candidate-return-continuation-independent-review-v1",
                "scope": "A90_F1_CANDIDATE_RETURN_CONTINUATION_AND_NO_REPLAY",
                "executionClosureSha256": EXPECTED_CONTINUATION_CLOSURE,
                "verdict": "PASS_GO",
                "liveAuthority": False,
            }),
            (self.value["postrollbackReview"], POSTROLLBACK_REVIEW, {
                "capability": "A90_F1_POSTROLLBACK_RECOVERY_V1",
                "schema": "a90-f1-postrollback-recovery-independent-review-v1",
                "executionClosureSha256": EXPECTED_POSTROLLBACK_CLOSURE,
                "verdict": "PASS_GO",
                "liveAuthority": False,
            }),
        ):
            self.assertEqual(declared["path"], str(path.relative_to(ROOT)))
            self.assertEqual(declared["size"], path.stat().st_size)
            self.assertEqual(declared["sha256"], _sha(path))
            current = _strict_json(path)
            for key, value in expected.items():
                self.assertEqual(current[key], value, (path, key))
                self.assertEqual(declared[key], value, (path, key, "declared"))
            self.assertEqual(current["findings"], {"high": [], "low": [], "medium": []})
            _assert_zero_contacts(current["contacts"])
        self.assertNotEqual(
            continuation.execution_closure_sha256(), EXPECTED_CONTINUATION_CLOSURE
        )
        self.assertNotEqual(
            postrollback.execution_closure_sha256(), EXPECTED_POSTROLLBACK_CLOSURE
        )

    def test_evidence_reviews_are_exact_public_h0_gates(self) -> None:
        evidence = self.value["evidenceReviews"]
        _assert_evidence_review_binding(evidence["hazard"], HAZARD_REVIEW)
        _assert_evidence_review_binding(evidence["package"], PACKAGE_REVIEW)
        self.assertEqual(evidence["hazard"], {
            "path": "docs/reports/A90_RTIC_PUBLIC_MPGEN_CANARY_HAZARD_INDEPENDENT_REVIEW_2026-08-23.json",
            "size": 3139,
            "sha256": "d180b3637bb36eefce7c28251a8c17ddb73393068135b4dff16972e5f86a8c94",
            "schema": "a90-rtic-public-mpgen-canary-hazard-independent-review-v1",
            "verdict": "PASS_GO_H0_CANARY_HAZARD",
            "liveAuthority": False,
        })
        self.assertEqual(evidence["package"], {
            "path": "docs/reports/A90_H35_PUBLIC_MPGEN_RTIC_CANARY_PACKAGE_INDEPENDENT_REVIEW_2026-08-23.json",
            "size": 5195,
            "sha256": "843524b45415ef09d1c311ecf88bdb3243b32c65f01a781bb167cbd8a56ec397",
            "schema": "a90-h35-public-mpgen-rtic-package-independent-review-v1",
            "verdict": "PASS_H0_PACKAGE_GATE",
            "liveAuthority": False,
        })
        hazard = _strict_json(HAZARD_REVIEW)
        package = _strict_json(PACKAGE_REVIEW)
        self.assertEqual(hazard["tier"], "H0")
        self.assertIs(hazard["candidateAllocated"], False)
        self.assertEqual(hazard["findings"], {"high": [], "low": [], "medium": []})
        _assert_zero_contacts(hazard["contacts"])
        self.assertEqual(package["tier"], "H0")
        self.assertIs(package["candidateAuthority"], False)
        self.assertEqual(package["findings"], {"high": [], "medium": [], "low": []})
        _assert_zero_contacts(package["contacts"])

    def test_hazard_statement_and_failed_boot_evidence_bind_to_owner(self) -> None:
        owner = _load("a90_h35_owner_evidence", OWNER)
        hazard = self.value["hazard"]
        self.assertTrue(hazard["accepted"] is True)
        self.assertEqual(hazard["id"], "A90_H35_PUBLIC_MPGEN_RTIC_CANARY_H1_H6")
        self.assertEqual(hazard["statementSha256"], "460afc03331024a79d051cb3a55ba878ae65f83610c1405d4a03671e4e3dd6c8")
        _assert_hazard_statement(hazard)
        for token in (
            "H1-H6 remain",
            "non-stock MPGen content version",
            "candidate-derived measured extent",
            "public producer provenance",
            "proprietary RTIC/QHEE response",
            "possible proprietary whole-Image measurement",
            "standalone-product secondary-input gaps",
            "NO_PROOF_OBSERVER",
            "Candidate replay is forbidden",
            "H29-H34 are consumed",
            "current V2321 health is unproved",
        ):
            self.assertIn(token, hazard["statement"])

        failed = self.value["failedBootEvidence"]
        self.assertTrue(failed["ownerClosureBound"] is True)
        self.assertEqual(failed["policyId"], owner.FAILED_BOOT_EVIDENCE_POLICY_ID)
        self.assertEqual(failed["sourceContractId"], owner.FAILED_BOOT_EVIDENCE_SOURCE_CONTRACT_ID)
        self.assertEqual(failed["decoder"], owner.FAILED_BOOT_EVIDENCE_DECODER)
        self.assertEqual(failed["source"], owner.FAILED_BOOT_EVIDENCE_SOURCE)
        self.assertEqual(failed["cmdlineSource"], owner.FAILED_BOOT_EVIDENCE_CMDLINE_SOURCE)
        self.assertEqual(failed["sourceMode"], "0444")
        self.assertEqual(failed["mount"], "none")
        self.assertEqual(failed["timeoutSec"], owner.FAILED_BOOT_EVIDENCE_TIMEOUT_SEC)
        self.assertEqual(failed["lastKmsgMaxBytes"], owner.FAILED_BOOT_LAST_KMSG_MAX_BYTES)
        self.assertTrue(type(failed["timeoutSec"]) is int)
        self.assertTrue(type(failed["lastKmsgMaxBytes"]) is int)
        self.assertTrue(failed["candidateReplay"] is False)
        self.assertEqual(failed["proofUse"], "FIRST_OPPORTUNITY_EVIDENCE_BEFORE_ROLLBACK_NO_RTIC_ATTRIBUTION")

    def test_build_bindings_and_pending_review_are_exact(self) -> None:
        build = self.value["build"]
        self.assertEqual(build["reportPath"], str(PACKAGE_REPORT.relative_to(ROOT)))
        self.assertEqual(build["reportSha256"], "c5541efd3624bf2e147ededac0fe7d73756bb6d21ad119888a66d993d8665801")
        self.assertEqual(build["reportSha256"], _sha(PACKAGE_REPORT))
        self.assertEqual(build["flatManifestPath"], str(MANIFEST.relative_to(ROOT)))
        self.assertEqual(build["flatManifestSha256"], "0b8ed49e5cb4ddc57fb73a1f43948d2c0c93829d7fb71a751f9badf75b52d89a")
        self.assertEqual(build["flatManifestSha256"], _sha(MANIFEST))
        self.assertEqual(build["effectiveManifestSha256"], "9fa94d1ad72c4891da036638a7ac43127a008cd45869df3b54f1fb0b8cf252b9")
        self.assertEqual(build["abBootSha256"], EXPECTED_CANDIDATE_SHA256)
        self.assertEqual(build["abBootSize"], self.value["candidate"]["size"])
        self.assertEqual(build["carrierSize"], 49_827_613)
        self.assertEqual(build["carrierSha256"], "15b49a71aeb2342a5b5a7e24de27f78a4124bf877f6d8d8f28aaab928fa6bd71")
        self.assertEqual(build["abReceiptSha256"], "5c21ec82cee9cc9497867518d710c8374b54240bf115f3e2b9c3d0ed5b4216f9")
        self.assertTrue(build["candidateAuthority"] is False)

        review = self.value["independentReview"]
        self.assertEqual(review, {
            "path": "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H35_INDEPENDENT_REVIEW_2026-08-23.json",
            "status": "PENDING_INDEPENDENT_REVIEW",
            "verdict": None,
            "liveAuthority": False,
        })

    def test_handoff_binds_input_review_schema_and_h0_boundaries(self) -> None:
        text = HANDOFF.read_text(encoding="utf-8")
        flat = " ".join(text.split())
        for expected in (
            EXPECTED_INPUT_SHA256,
            EXPECTED_OWNER_CLOSURE,
            EXPECTED_CONTINUATION_CLOSURE,
            EXPECTED_POSTROLLBACK_CLOSURE,
            EXPECTED_CANDIDATE_SHA256,
            EXPECTED_ROLLBACK_SHA256,
            "22fba68f002bf7e35b9e15d1b12cfed906e33de4bd1a0e56982bcc78f4acd120",
            "20aaed0b4e3d7aefb940c06db421a55b9113dcc7bf2cc9e074a36328ebf3e9a0",
            "d180b3637bb36eefce7c28251a8c17ddb73393068135b4dff16972e5f86a8c94",
            "843524b45415ef09d1c311ecf88bdb3243b32c65f01a781bb167cbd8a56ec397",
            "a90-boot-only-f1-minimal-independent-review-v1",
            "no trailing newline",
            "PENDING_INDEPENDENT_REVIEW",
            "current V2321 health is unproved",
            "private manifest, run ID, recovery serial",
            "H29-H34 are consumed and non-replayable",
            "NO_PROOF_OBSERVER",
            "candidate replay",
            "zero contacts/findings",
            "6,608 bytes",
        ):
            self.assertIn(expected, flat)
        self.assertIn("Authority: none", text)
        self.assertIn("no D0, approval, F1", text)
        self.assertNotIn("liveAuthority=true", text)
        self.assertNotIn("candidateAuthority=true", text)

    def test_independent_review_is_canonical_historical_and_current_owner_rejects_it(self) -> None:
        owner = _load("a90_h35_review_owner", OWNER)
        raw = INDEPENDENT_REVIEW.read_bytes()
        review = _strict_json(INDEPENDENT_REVIEW)
        self.assertEqual(len(raw), 1_192)
        self.assertEqual(_sha(INDEPENDENT_REVIEW), EXPECTED_REVIEW_SHA256)
        self.assertFalse(raw.endswith(b"\n"))
        self.assertEqual(owner.canonical_json(review), raw)
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertEqual(review["executionClosureSha256"], EXPECTED_OWNER_CLOSURE)
        self.assertEqual(review["candidateSha256"], EXPECTED_CANDIDATE_SHA256)
        self.assertEqual(review["rollbackSha256"], EXPECTED_ROLLBACK_SHA256)
        self.assertEqual(review["findings"], {"high": [], "low": [], "medium": []})
        _assert_zero_contacts(review["contacts"])
        self.assertIs(review["liveAuthority"], False)
        synthetic_manifest = {
            "candidate": {"sha256": EXPECTED_CANDIDATE_SHA256},
            "rollback": {"sha256": EXPECTED_ROLLBACK_SHA256},
            "qualification": {
                "recovery": self.value["recovery"],
                "hazard": {
                    key: self.value["hazard"][key]
                    for key in ("id", "statementSha256", "accepted")
                },
                "freshState": self.value["freshState"],
            },
        }
        with self.assertRaises(owner.ContractError):
            owner._validate_qualification_review(review, synthetic_manifest)

    def test_private_manifest_binds_h35_review_when_explicitly_enabled(self) -> None:
        if os.environ.get("A90_H35_VERIFY_PRIVATE") != "1":
            self.skipTest("set A90_H35_VERIFY_PRIVATE=1 for private H35 manifest verification")
        owner = _load("a90_h35_private_owner", OWNER)
        raw, value = owner.load_manifest(PRIVATE_MANIFEST.resolve())
        with self.assertRaises(owner.ContractError):
            owner._verify_qualification_inputs(value)
        self.assertEqual(value["runId"], "a90-h35-f1-20260823-01")
        self.assertEqual(value["candidate"]["sha256"], EXPECTED_CANDIDATE_SHA256)
        self.assertEqual(value["rollback"]["sha256"], EXPECTED_ROLLBACK_SHA256)
        self.assertEqual(value["qualification"]["review"]["size"], 1_192)
        self.assertEqual(
            value["qualification"]["review"]["sha256"], EXPECTED_REVIEW_SHA256
        )
        self.assertEqual(len(raw), 1_955)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED_PRIVATE_MANIFEST_SHA256)
        self.assertTrue(value["qualification"]["hazard"]["accepted"] is True)

    def test_hostile_stale_closure_evidence_sha_statement_and_bool_aliases_reject(self) -> None:
        stale = copy.deepcopy(self.value)
        stale["executionClosureSha256"] = "1c31fb97e8f181e63bd71949b020f647aa8dab45c63d13bd089f6be2659da8a8"
        with self.assertRaises(AssertionError):
            self.assertEqual(stale["executionClosureSha256"], EXPECTED_OWNER_CLOSURE)

        mutated_evidence = copy.deepcopy(self.value)
        mutated_evidence["evidenceReviews"]["hazard"]["sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            _assert_evidence_review_binding(mutated_evidence["evidenceReviews"]["hazard"], HAZARD_REVIEW)

        mutated_statement = copy.deepcopy(self.value)
        mutated_statement["hazard"]["statement"] += " mutation"
        with self.assertRaises(AssertionError):
            _assert_hazard_statement(mutated_statement["hazard"])

        authority_alias = copy.deepcopy(self.value)
        authority_alias["authority"]["d0"] = 0
        with self.assertRaises(AssertionError):
            _assert_all_false_authority(authority_alias["authority"])

        contacts_alias = _strict_json(CONTINUATION_REVIEW)
        contacts_alias["contacts"]["device"] = False
        with self.assertRaises(AssertionError):
            _assert_zero_contacts(contacts_alias["contacts"])


def _strict_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise AssertionError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


if __name__ == "__main__":
    unittest.main()
