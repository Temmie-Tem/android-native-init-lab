"""Pin the A90 continuation/postrollback H0 repair and review boundaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "A90_CONTINUATION_POSTROLLBACK_REVIEW_BLOCKER_REPAIR_H0_2026-08-22.md"
)
PREDECESSOR = ROOT / (
    "docs/reports/"
    "A90_UNCERTAIN_RETURN_FAILED_BOOT_EVIDENCE_CONTINUATION_H0_2026-08-22.md"
)
CONTINUATION_REVIEW = ROOT / (
    "docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_CURRENT_REVIEW.json"
)
POSTROLLBACK_REVIEW = ROOT / (
    "docs/reports/A90_F1_POSTROLLBACK_RECOVERY_CURRENT_REVIEW.json"
)
H34_INPUT = ROOT / (
    "docs/reports/A90_H34_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-22.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(path: Path):
    def reject_duplicates(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise AssertionError(f"duplicate JSON key: {key}")
            value[key] = item
        return value

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)


class ContinuationPostrollbackReviewBlockerRepairDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = REPORT.read_text(encoding="utf-8")
        cls.flat = " ".join(cls.raw.split())
        cls.continuation = strict_json(CONTINUATION_REVIEW)
        cls.postrollback = strict_json(POSTROLLBACK_REVIEW)

    def test_scope_is_host_only_and_non_authoritative(self) -> None:
        for token in (
            "Tier: H0 host-only repair and independent review",
            "Device contact: none",
            "capability review creates no candidate, D0, D1, F1",
            "No device, USB, ADB, network endpoint",
        ):
            self.assertIn(token, self.flat)

    def test_full_review_findings_and_second_branch_no_go_are_preserved(self) -> None:
        for token in (
            "HIGH — bridge raw capture was not private-bound",
            "exact normal ADB daemon-start banner",
            "postrollback recovery did not consume continuation rollback prefixes",
            "physical record-`25` branch",
            "absence means the attributable-failure branch",
        ):
            self.assertIn(token, self.flat)

    def test_current_continuation_review_is_exact_pass_go(self) -> None:
        self.assertEqual(
            self.continuation["executionClosureSha256"],
            "981a3f06ce38a288a8ab9c5ef76234bc38c97b51359fd2f46bfb4ed714d7ae3d",
        )
        self.assertEqual(sha256(CONTINUATION_REVIEW), "22fba68f002bf7e35b9e15d1b12cfed906e33de4bd1a0e56982bcc78f4acd120")
        self.assertEqual(self.continuation["verdict"], "PASS_GO")
        self.assertFalse(self.continuation["liveAuthority"])
        self.assertTrue(all(value == 0 for value in self.continuation["contacts"].values()))

    def test_current_postrollback_review_is_exact_pass_go(self) -> None:
        self.assertEqual(
            self.postrollback["executionClosureSha256"],
            "148525430a5cd9f875df4cb39766c6c72a8093f2155ea1bc6e312aea8f45cf5d",
        )
        self.assertEqual(sha256(POSTROLLBACK_REVIEW), "20aaed0b4e3d7aefb940c06db421a55b9113dcc7bf2cc9e074a36328ebf3e9a0")
        self.assertEqual(self.postrollback["verdict"], "PASS_GO")
        self.assertFalse(self.postrollback["liveAuthority"])
        self.assertTrue(all(value == 0 for value in self.postrollback["contacts"].values()))

    def test_h34_frozen_input_does_not_match_current_capabilities(self) -> None:
        h34 = strict_json(H34_INPUT)
        self.assertNotEqual(
            h34["continuationReview"]["sha256"], sha256(CONTINUATION_REVIEW)
        )
        self.assertNotEqual(
            h34["postrollbackReview"]["sha256"], sha256(POSTROLLBACK_REVIEW)
        )
        self.assertIn("H34 remains consumed and non-replayable", self.flat)

    def test_predecessor_links_this_review_closure(self) -> None:
        self.assertIn(REPORT.name, PREDECESSOR.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
