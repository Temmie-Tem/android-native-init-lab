"""Validate the public H35 RTIC package review without opening private bytes."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / (
    "docs/reports/"
    "A90_H35_PUBLIC_MPGEN_RTIC_CANARY_PACKAGE_INDEPENDENT_REVIEW_2026-08-23.json"
)
GOAL = ROOT / "GOAL_A90.md"

SOURCE_COMMIT = "d7245ab4b2106cba1ccb97825fff1053ab9252d7"
PACKAGE_COMMIT = "d7862a8cee0c3efe61d6a12c35bfb8d01fd4f25f"
EXPECTED_FILES = {
    "GOAL_A90.md": "c8e9d7e293b6c4689fc9c69da6814af191f96e39c82a7561488c699b6247b945",
    "docs/reports/A90_H35_PUBLIC_MPGEN_RTIC_CANARY_PACKAGE_H0_2026-08-23.md":
        "c5541efd3624bf2e147ededac0fe7d73756bb6d21ad119888a66d993d8665801",
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h35/manifest.toml":
        "0b8ed49e5cb4ddc57fb73a1f43948d2c0c93829d7fb71a751f9badf75b52d89a",
    "tests/test_a90_public_mpgen_rtic_h35.py":
        "bcce56c7544da036ed3d413445412d26a3d9c619e51bca88f52c1bd1492896d8",
    "docs/reports/A90_RTIC_PUBLIC_MPGEN_CANARY_HAZARD_INDEPENDENT_REVIEW_2026-08-23.json":
        "d180b3637bb36eefce7c28251a8c17ddb73393068135b4dff16972e5f86a8c94",
}


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate key: {key}")
        value[key] = item
    return value


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _commit_bytes(commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def _validate_authority(value: dict[str, object]) -> None:
    if value.get("tier") != "H0":
        raise AssertionError("review tier is not H0")
    if value.get("candidateAuthority") is not False:
        raise AssertionError("candidate authority is not exact false")
    if value.get("liveAuthority") is not False:
        raise AssertionError("live authority is not exact false")
    contacts = value.get("contacts")
    if not isinstance(contacts, dict) or not contacts:
        raise AssertionError("contacts are absent")
    if any(type(item) is not int or item != 0 for item in contacts.values()):
        raise AssertionError("review contact count is not exact integer zero")


class A90H35PublicMpgenRticPackageReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = REVIEW.read_bytes()
        cls.value = json.loads(cls.raw, object_pairs_hook=_strict_object)

    def test_verdict_and_source_commits_are_exact(self) -> None:
        self.assertEqual(
            self.value["schema"],
            "a90-h35-public-mpgen-rtic-package-independent-review-v1",
        )
        self.assertEqual(self.value["verdict"], "PASS_H0_PACKAGE_GATE")
        self.assertEqual(self.value["sourceCommit"], SOURCE_COMMIT)
        self.assertEqual(self.value["packageCommit"], PACKAGE_COMMIT)
        self.assertEqual(self.value["findings"], {"high": [], "medium": [], "low": []})

    def test_reviewed_public_files_match_the_source_commit(self) -> None:
        reviewed = {
            item["path"]: item["sha256"] for item in self.value["reviewedFiles"]
        }
        for path, digest in EXPECTED_FILES.items():
            with self.subTest(path=path):
                self.assertEqual(reviewed[path], digest)
                self.assertEqual(_sha(_commit_bytes(SOURCE_COMMIT, path)), digest)

    def test_exact_artifact_declarations_are_not_private_verification(self) -> None:
        self.assertEqual(
            self.value["artifacts"],
            {
                "carrier": {
                    "size": 49_827_613,
                    "sha256": "15b49a71aeb2342a5b5a7e24de27f78a4124bf877f6d8d8f28aaab928fa6bd71",
                    "verification": "declared_in_public_report_owner_host_bytes_not_directly_read",
                },
                "base": {
                    "size": 66_379_776,
                    "sha256": "5d681bbddf527fdacf1e433cdf30a0ca0b11d455c1b6e879c809418fd0d75484",
                    "verification": "declared_in_public_report_owner_host_bytes_not_directly_read",
                },
                "boot": {
                    "size": 58_372_096,
                    "sha256": "5e2a44420195090e75f63e350cacdbcad88710e77cef9bcf29a6d3ee6f4ad759",
                    "verification": "declared_in_public_report_owner_host_bytes_not_directly_read",
                },
            },
        )
        private = self.value["privateVerification"]
        self.assertIs(private["directPrivateByteVerification"], False)
        self.assertEqual(private["workspacePrivateReads"], 0)
        self.assertEqual(private["delegatedOwnerHostTest"]["environment"], "A90_H35_VERIFY_PRIVATE=1")
        self.assertEqual(private["delegatedOwnerHostTest"]["status"], "NOT_RUN_IN_PUBLIC_REVIEW")

    def test_authority_and_contacts_are_exact_zero(self) -> None:
        _validate_authority(self.value)
        self.assertEqual(self.value["workspacePrivate"], 0)

    def test_hostile_authority_and_bool_integer_alias_are_rejected(self) -> None:
        authority = copy.deepcopy(self.value)
        authority["candidateAuthority"] = True
        with self.assertRaises(AssertionError):
            _validate_authority(authority)
        alias = copy.deepcopy(self.value)
        alias["contacts"]["device"] = False
        with self.assertRaises(AssertionError):
            _validate_authority(alias)

    def test_remaining_live_prerequisites_are_not_promoted(self) -> None:
        remaining = set(self.value["remainingPrerequisites"])
        for token in (
            "CANDIDATE_SPECIFIC_QUALIFICATION_AND_MANIFEST",
            "CURRENT_OWNER_CONTINUATION_OBSERVER_ROLLBACK_POSTROLLBACK_BINDINGS",
            "FRESH_EXACT_V2321_HEALTH_AND_PHYSICAL_RECOVERY_D0",
            "FRESH_ATTENDED_EXACT_CANDIDATE_ROLLBACK_APPROVAL",
            "ONE_SHOT_F1_WITH_NO_CANDIDATE_REPLAY",
            "FIRST_OPPORTUNITY_EVIDENCE_THEN_JOURNAL_BOUND_ROLLBACK_RECOVERY",
        ):
            self.assertIn(token, remaining)

    def test_current_goal_records_review_without_authority(self) -> None:
        goal = GOAL.read_text(encoding="utf-8")
        flat = " ".join(goal.split())
        self.assertLessEqual(len(goal.splitlines()), 900)
        self.assertIn("`PASS_H0_PACKAGE_GATE`", goal)
        self.assertIn("candidate-specific `PASS_GO`", flat)
        self.assertIn("private H35 manifest passes owner validation", flat)
        self.assertIn("No D0, D1, approval, F1, or live authority exists", flat)
        self.assertNotIn("No qualification, manifest", flat)


if __name__ == "__main__":
    unittest.main()
