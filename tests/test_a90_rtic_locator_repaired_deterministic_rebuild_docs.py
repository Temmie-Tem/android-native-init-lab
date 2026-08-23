"""Pin the A90 RTIC locator repair and deterministic rebuild result."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "A90_RTIC_LOCATOR_REPAIRED_DETERMINISTIC_REBUILD_H0_2026-08-23.md"
)
PREDECESSOR = ROOT / (
    "docs/reports/"
    "A90_RTIC_STOCK_EQUIVALENCE_REQUIREMENT_RECALIBRATION_H0_2026-08-22.md"
)
GOAL = ROOT / "GOAL_A90.md"


class A90RticLocatorRepairedDeterministicRebuildDocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = REPORT.read_text(encoding="utf-8")
        cls.flat = " ".join(cls.raw.split())

    def test_scope_is_h0_and_non_authoritative(self) -> None:
        for token in (
            "Tier: H0 private-host deterministic rebuild and artifact analysis",
            "Device contact: none",
            "no candidate identity, boot image, manifest, D0, D1, F1",
            "current tracked resident-health state after H34 remains unproved",
        ):
            self.assertIn(token, self.flat)

    def test_repair_is_pre_link_and_does_not_modify_mpgen(self) -> None:
        for token in (
            "`-fdebug-compilation-dir=<fixed-object-map>/source`",
            "`-Wa,--debug-prefix-map,<real-output>=<fixed-object-map>/source`",
            "MPGen Git subtree was clean before and after",
            "No MPGen, catalog, kernel source, generated MP, `vmlinux`, build ID, or Image byte was hard-coded or patched after linking",
        ):
            self.assertIn(token, self.flat)

    def test_diagnostic_build_is_not_hidden_or_promoted(self) -> None:
        self.assertIn("first diagnostic build proved the C-side locator repair", self.flat)
        self.assertIn("external assembler still retained its real vDSO output path", self.flat)
        self.assertIn("rejected before a comparison partner was built", self.flat)

    def test_exact_objects_and_offsets_are_pinned(self) -> None:
        expected = (
            "69cc2ab41e6f91ca10c0cf7fc090914b62fd5b652d3a235a5d3fa2b5dfa12aad",
            "9484a1133fc8048a588940096e31e9201dee7164671790715dfc447f840a1a80",
            "8a14c7826f0e8f94c836e5d6ec999505612163db6711718670c82edc15b77757",
            "`state=88, pid=1704, parent=1728, comm=2144`",
            "No `0xffffffff` sentinel remains",
        )
        for token in expected:
            self.assertIn(token, self.raw)

    def test_complete_selected_outputs_are_pairwise_identical(self) -> None:
        expected = (
            "1ddae56f8df97030794a590192e4a4162876736029b1a54fd26173c9287002b7",
            "46d92aca9526ff7851d4fc6f4a3a962e36aac4672196e271869d8d68c6581135",
            "01df7d8ad1915ef64a48916dd3fee19aadf57005777fb73ad6ebad8e15ff31db",
            "40ce65d99bc380a5ea607cff064813c6211474e4ae7077bf06cff70e448b7ad2",
            "6d050ebdcec3e6f92665c58d6828aac381e2bb94a6c097152baa439fee1e1289",
            "fc760b76a13e7580219c67a690b9b8eb7515834dd382d7cab4fa6f09722a9b29",
            "68e6ab5bb2ccdde5e3d87086110257176c0fe55726d1d4f5db6eba3a4b6aca04",
            "1a920d47b51f4a323bc1033b6aa630db5917421971dcaabf08b36e629afc23c7",
            "all_selected_outputs_byte_identical=true",
        )
        for token in expected:
            self.assertIn(token, self.raw)

    def test_rtic_binding_is_exact_but_not_a_boot_result(self) -> None:
        for token in (
            "MP VA `0xffffff8009f00000`",
            "raw-Image offset `0x01e80000`",
            "size 1,624",
            "interface `30.3`",
            "d95fd9710dd019c5f2e0a273669bcb9b96f81dfdf994afd940b9abb4ff04ec69",
            "This is not a boot result",
        ):
            self.assertIn(token, self.flat)

    def test_prior_delta_is_exactly_bounded(self) -> None:
        for token in (
            "differ in exactly 56 bytes across only three ranges",
            "`0x019862c8..0x019862db`",
            "`0x01e80648..0x01e80657`",
            "`0x0256a5a8..0x0256a5bb`",
            "There is no other Image delta",
            "path repair did not alter CFP code or configuration",
        ):
            self.assertIn(token, self.flat)

    def test_residual_hazard_and_next_sequence_remain_separate(self) -> None:
        for token in (
            "`2.7.e26468.30`, not stock `2.7.ef86a6.30`",
            "candidate-derived extent `0x039d3000`, not stock `0x03973000`",
            "proprietary RTIC/QHEE",
            "next unit is one independent H0 review",
        ):
            self.assertIn(token, self.flat + " " + GOAL.read_text(encoding="utf-8"))
        self.assertIn("no candidate identity, boot image, manifest, D0, D1, F1", self.flat)
        goal = " ".join(GOAL.read_text(encoding="utf-8").split())
        self.assertIn("H35 is consumed and never replayed", goal)
        self.assertIn("H35 never booted and remains unproved", goal)
        self.assertIn("No H36 identity or authority exists", goal)

    def test_predecessor_links_without_rewriting_the_design_decision(self) -> None:
        predecessor = " ".join(PREDECESSOR.read_text(encoding="utf-8").split())
        self.assertIn(REPORT.name, predecessor)
        self.assertIn("proprietary-acceptance hazard", predecessor)
        self.assertIn("every candidate/live prerequisite unproved", predecessor)

    def test_independent_review_preserves_evidence_boundaries(self) -> None:
        for token in (
            "returned `PASS_H0_BUILD_GATE` with no high, medium, or low finding",
            "33 focused public RTIC documentation tests",
            "did not open private build inputs or evidence",
            "does not decode task offsets or prove the symbol",
            "qualifies only this host build gate and grants no candidate or live authority",
        ):
            self.assertIn(token, self.flat)


if __name__ == "__main__":
    unittest.main()
