"""Pin the H0-only A90 public-MPGen canary hazard decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / (
    "docs/plans/"
    "A90_RTIC_PUBLIC_MPGEN_CANARY_HAZARD_REVIEW_HANDOFF_2026-08-23.md"
)
REVIEW = ROOT / (
    "docs/reports/"
    "A90_RTIC_PUBLIC_MPGEN_CANARY_HAZARD_INDEPENDENT_REVIEW_2026-08-23.json"
)
SOURCE_REPORT = ROOT / (
    "docs/reports/"
    "A90_RTIC_LOCATOR_REPAIRED_DETERMINISTIC_REBUILD_H0_2026-08-23.md"
)
GOAL = ROOT / "GOAL_A90.md"


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


class A90RticPublicMpgenCanaryHazardReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.handoff_raw = HANDOFF.read_text(encoding="utf-8")
        cls.handoff_flat = " ".join(cls.handoff_raw.split())
        cls.review = json.loads(
            REVIEW.read_text(encoding="utf-8"), object_pairs_hook=_strict_object
        )

    def test_exact_reviewed_sources_are_bound(self) -> None:
        self.assertEqual(
            hashlib.sha256(HANDOFF.read_bytes()).hexdigest(),
            self.review["handoff"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(SOURCE_REPORT.read_bytes()).hexdigest(),
            self.review["sourceReport"]["sha256"],
        )
        self.assertEqual(
            self.review["sourceCommit"],
            "1639f7c6a3e0c4d73ad036952fcbd4924c968816",
        )

    def test_exact_image_and_carrier_are_bound_without_candidate(self) -> None:
        artifact = self.review["artifact"]
        self.assertEqual(artifact["imageSize"], 48_830_480)
        self.assertEqual(
            artifact["imageSha256"],
            "1ddae56f8df97030794a590192e4a4162876736029b1a54fd26173c9287002b7",
        )
        self.assertEqual(artifact["expectedCarrierSize"], 49_827_613)
        self.assertEqual(
            artifact["expectedCarrierSha256"],
            "15b49a71aeb2342a5b5a7e24de27f78a4124bf877f6d8d8f28aaab928fa6bd71",
        )
        self.assertIs(self.review["candidateAllocated"], False)

    def test_whole_hazard_bundle_is_explicitly_limited(self) -> None:
        expected_ids = [
            "H1_NON_STOCK_MPGEN_CONTENT_VERSION",
            "H2_CANDIDATE_DERIVED_MEASURED_EXTENT",
            "H3_PUBLIC_CATALOG_AND_PRODUCER_PROVENANCE",
            "H4_PROPRIETARY_RTIC_QHEE_RESPONSE",
            "H5_POSSIBLE_PROPRIETARY_WHOLE_IMAGE_MEASUREMENT",
            "H6_STANDALONE_PRODUCT_SECONDARY_INPUT_GAPS",
        ]
        bundle = self.review["hazardBundle"]
        self.assertEqual([entry["id"] for entry in bundle], expected_ids)
        self.assertTrue(all(entry["accepted"] is True for entry in bundle))
        self.assertTrue(
            all(entry["scope"] == "ONE_FUTURE_ATTENDED_CANARY_ONLY" for entry in bundle)
        )

    def test_verdict_has_no_findings_and_grants_no_authority(self) -> None:
        self.assertEqual(self.review["verdict"], "PASS_GO_H0_CANARY_HAZARD")
        self.assertEqual(self.review["tier"], "H0")
        self.assertEqual(self.review["findings"], {"high": [], "low": [], "medium": []})
        self.assertIs(self.review["liveAuthority"], False)
        self.assertEqual(self.review["publicFocusedTests"], 50)
        self.assertTrue(all(value == 0 for value in self.review["contacts"].values()))

    def test_failure_evidence_never_authorizes_replay_or_rtic_attribution(self) -> None:
        attribution = self.review["failureAttribution"]
        self.assertEqual(attribution["evidenceAbsence"], "NO_PROOF_OBSERVER")
        self.assertIs(attribution["permitsCandidateReplay"], False)
        self.assertIs(attribution["rticSpecificAttributionFromBootFailure"], False)

    def test_all_future_prerequisites_remain_separate(self) -> None:
        self.assertEqual(len(self.review["futurePrerequisites"]), 8)
        for token in (
            "FRESH_SUCCESSOR_IDENTITY",
            "CANDIDATE_SPECIFIC_QUALIFICATION_AND_MANIFEST",
            "FRESH_EXACT_V2321_HEALTH_AND_PHYSICAL_RECOVERY_D0",
            "FRESH_ATTENDED_EXACT_CANDIDATE_ROLLBACK_APPROVAL",
            "ONE_SHOT_F1_WITH_NO_CANDIDATE_REPLAY",
        ):
            self.assertIn(token, self.review["futurePrerequisites"])

    def test_handoff_refuses_promotion_and_unbounded_review(self) -> None:
        for token in (
            "It is not `PASS`, production equivalence, a candidate qualification",
            "an unbounded demand for unavailable proprietary source is not by itself a falsifiable gate",
            "H34 and every earlier candidate remain consumed and non-replayable",
            "current tracked V2321 health is unproved",
        ):
            self.assertIn(token, self.handoff_flat)

    def test_goal_records_review_and_next_h0_without_exceeding_limit(self) -> None:
        goal = GOAL.read_text(encoding="utf-8")
        self.assertLessEqual(len(goal.splitlines()), 900)
        self.assertIn("`PASS_GO_H0_CANARY_HAZARD`", goal)
        self.assertIn(REVIEW.name, goal)
        self.assertIn("no successor/live authority exists", " ".join(goal.split()))


if __name__ == "__main__":
    unittest.main()
