"""Pin the bounded A90 RTIC requirement recalibration and next gate."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "A90_RTIC_STOCK_EQUIVALENCE_REQUIREMENT_RECALIBRATION_H0_2026-08-22.md"
)
PREDECESSOR = ROOT / (
    "docs/reports/"
    "A90_STOCK_SHAPED_MPGEN_CATALOG_AND_DETERMINISTIC_REBUILD_H0_2026-08-22.md"
)


class A90RticStockEquivalenceRequirementRecalibrationDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = REPORT.read_text(encoding="utf-8")
        cls.flat = " ".join(cls.raw.split())

    def test_scope_is_host_only_and_non_authoritative(self) -> None:
        for token in (
            "Tier: H0 host-only evidence and sequencing decision",
            "Device contact: none",
            "no candidate, D0, D1, F1",
            "did not read `workspace/private`",
        ):
            self.assertIn(token, self.flat)

    def test_literal_stock_mp_equality_is_not_the_candidate_predicate(self) -> None:
        self.assertIn(
            "Literal byte equality with the stock 1,624-byte RTIC MP is **not** the correct next gate",
            self.flat,
        )
        self.assertIn("do not force stock equality", self.flat)
        self.assertIn("candidate-specific linked-layout measurement", self.flat)

    def test_task_offset_sentinels_remain_static_no_go(self) -> None:
        for token in (
            "four task-structure offsets are emitted as `0xffffffff`",
            "remains a static `NO_GO`",
            "`88`, `1704`, `1728`, and `2144`",
            "Hard-coding or post-editing the four offsets is forbidden",
        ):
            self.assertIn(token, self.flat)

    def test_complete_proprietary_acceptance_hazard_is_named(self) -> None:
        for token in (
            "remaining proprietary-acceptance uncertainty is an explicit hazard bundle",
            "non-stock MPGen content version, the candidate-derived extent/range",
            "proprietary RTIC/QHEE or whole-Image enforcement",
            "public tool/catalog provenance",
            "one attended boot canary",
        ):
            self.assertIn(token, self.flat)

    def test_next_build_requires_producer_and_rtic_binding_evidence(self) -> None:
        for token in (
            "keep the selected public MPGen Git tree byte-clean",
            "exact object-path mapping",
            "no `0xffffffff` sentinel",
            "one `rtic_mp` symbol, one RTIC DTB, one `MP_DATA`",
            "exact MP SHA-256 equality",
            "post-link build-ID or Image byte patching is forbidden",
            "two independent output trees",
        ):
            self.assertIn(token, self.flat)

    def test_independent_review_chronology_is_preserved(self) -> None:
        for token in (
            "initial adversarial review returned `NO_GO`",
            "one medium and one low finding",
            "bounded delta re-review then returned `PASS_H0_DESIGN`",
            "with no high, medium, or low finding",
            "not a candidate qualification, capability activation, or live review lease",
        ):
            self.assertIn(token, self.flat)

    def test_predecessor_links_without_rewriting_measured_deltas(self) -> None:
        predecessor = PREDECESSOR.read_text(encoding="utf-8")
        self.assertIn(REPORT.name, predecessor)
        self.assertIn(
            "does not rewrite this report's measured byte differences",
            " ".join(predecessor.split()),
        )


if __name__ == "__main__":
    unittest.main()
