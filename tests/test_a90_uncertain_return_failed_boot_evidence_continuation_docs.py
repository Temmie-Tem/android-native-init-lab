"""Pin the bounded A90 uncertain-return evidence H0 result and limits."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "A90_UNCERTAIN_RETURN_FAILED_BOOT_EVIDENCE_CONTINUATION_H0_2026-08-22.md"
)
WIRING = ROOT / (
    "docs/reports/A90_TWRP_FAILED_BOOT_EVIDENCE_WIRING_H0_2026-08-22.md"
)
MPGEN = ROOT / (
    "docs/reports/"
    "A90_STOCK_SHAPED_MPGEN_CATALOG_AND_DETERMINISTIC_REBUILD_H0_2026-08-22.md"
)


def flatten(text: str) -> str:
    return " ".join(text.split())


class UncertainReturnFailedBootEvidenceContinuationDocsTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.raw = REPORT.read_text(encoding="utf-8")
        self.flat = flatten(self.raw)

    def test_scope_is_h0_and_grants_no_live_authority(self) -> None:
        for token in (
            "Tier: H0 host-only implementation and static review",
            "Device contact: none",
            "no candidate, D0, D1, F1",
            "does not authorize D0 or F1",
        ):
            self.assertIn(token, self.flat)

    def test_uncertain_evidence_cannot_promote_proof(self) -> None:
        for token in (
            "`UNCERTAIN`",
            "`EVIDENCE_ONLY_NO_DEVICE_REFUTATION`",
            "`deviceContradictionEligible` is always `false`",
            "cannot turn this branch into PASS or REFUTED",
        ):
            self.assertIn(token, self.flat)

    def test_one_intent_and_one_result_sidecar_are_bound(self) -> None:
        for token in (
            "`25-candidate-observation-intent.json`",
            "`O_EXCL|O_NOFOLLOW`",
            "`candidateReplay:false`",
            "`rollbackReplay:false`",
            "only new durable object",
        ):
            self.assertIn(token, self.flat)

    def test_crash_cut_repeats_neither_observation_nor_capture(self) -> None:
        for token in (
            "durable `25` with no result sidecar",
            "makes zero device contact",
            "repeats neither post-physical observation nor evidence capture",
            "may enter only the existing one-shot rollback",
        ):
            self.assertIn(token, self.flat)

    def test_owner_and_postrollback_remain_unchanged(self) -> None:
        self.assertIn("minimal F1 owner", self.flat)
        self.assertIn("postrollback recovery owner are unchanged", self.flat)
        self.assertIn(
            "c22b5a8ae6b630a178c31db22b6a9167ac6ed969b1d894a29c3399275db44c5e",
            self.raw,
        )
        self.assertIn(
            "a6bf12eef5a5c9514a2c8613cbfdcd4c4e0c8f5800f393b6b728b3048827af2c",
            self.raw,
        )

    def test_canonical_review_is_explicitly_stale(self) -> None:
        self.assertIn(
            "d8a50ee0ca7527d4a4a6b80e63ae1e2071b88c9917947ed8107a4aeedcaa955b",
            self.raw,
        )
        self.assertIn(
            "d053e137ca6d984709e53a1200d1e980f6d766ab4dd30cbb012cef2ddd3ee9e1",
            self.raw,
        )
        self.assertIn("live review gate fails closed", self.flat)

    def test_predecessor_reports_link_the_follow_up(self) -> None:
        for path in (WIRING, MPGEN):
            self.assertIn(
                REPORT.name,
                path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
