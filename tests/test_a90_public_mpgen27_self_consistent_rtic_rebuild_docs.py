"""Pin the limits and exact result of the A90 public-MPGen H0 control."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "A90_PUBLIC_MPGEN27_SELF_CONSISTENT_RTIC_REBUILD_H0_2026-08-22.md"
)
PREDECESSOR = ROOT / (
    "docs/reports/"
    "A90_PUBLIC_R3Q_REBUILT_KERNEL_ARTIFACT_COMPARISON_H0_2026-08-22.md"
)


def flatten(text: str) -> str:
    return " ".join(text.split())


class PublicMpgen27SelfConsistentRticRebuildDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = REPORT.read_text(encoding="utf-8")
        self.flat = flatten(self.raw)

    def test_scope_is_host_only_and_grants_no_live_authority(self) -> None:
        for token in (
            "Tier: H0 host-only acquisition, build, and artifact analysis",
            "Device contact: none",
            "Authority: no candidate, D0, D1, F1, rollback, reboot, or live authority",
            "H34 remains consumed and non-replayable",
        ):
            self.assertIn(token, self.flat)

    def test_structural_pass_is_not_stock_security_equivalence(self) -> None:
        self.assertIn("**RTIC structural consistency is proved.**", self.raw)
        self.assertIn("**Stock security equivalence is not proved.**", self.raw)
        self.assertIn("The current validator proves byte binding only", self.flat)
        self.assertIn("whether QHEE will accept", self.flat)
        self.assertIn("or whether the device will boot it", self.flat)

    def test_final_artifacts_are_frozen_exactly(self) -> None:
        expected = {
            "raw `Image`": (
                "48,830,480",
                "94767a8233173ea3a5f1875822373f92084a90483b9ec5d0cf84a6135207b962",
            ),
            "`System.map`": (
                "6,363,557",
                "01df7d8ad1915ef64a48916dd3fee19aadf57005777fb73ad6ebad8e15ff31db",
            ),
            "generated `rtic_mp.dtb`": (
                "173",
                "3434b434da95108252a74133c4cc39c7ffef48bf04fb781d52a1d23f8f66c874",
            ),
            "H0 comparison wrapper": (
                "49,827,613",
                "36ef56c07a9b8a8d8e8fffb56609e617846a5705cbf0e86adeb71f446112430e",
            ),
        }
        for label, (size, digest) in expected.items():
            with self.subTest(label=label):
                self.assertIn(label, self.raw)
                self.assertIn(size, self.raw)
                self.assertIn(digest, self.raw)

    def test_rtic_binding_values_are_exact(self) -> None:
        for token in (
            "`0xffffff8009f00000`",
            "`0x01e80000`",
            "`30.3`",
            "`2.7.48ef28.30`",
            "`8bb97ebc…` / equal",
            "RO 3 / WK 1 / WU 3 / AW 0",
        ):
            self.assertIn(token, self.raw)

    def test_public_catalog_is_not_misrepresented_as_production(self) -> None:
        self.assertIn("# TEST CATALOG", self.raw)
        self.assertIn(
            "# For production catalog contact Qualcomm Technologies, Inc.",
            self.raw,
        )
        self.assertIn("The stock MP contains", self.raw)
        self.assertIn("The public control contains the same named set plus WU", self.flat)
        self.assertIn("Whether that is stricter, harmless, or rejected is **unproved**", self.raw)

    def test_selinux_state_warning_and_writer_gap_are_preserved(self) -> None:
        self.assertIn("`selinux_state`", self.raw)
        self.assertIn("`after kernel 4.19`", self.raw)
        self.assertIn("`selinux_state`(no selinux_init)", self.raw)
        self.assertIn("empty writer list", self.flat)

    def test_public_mpgen_build_is_not_reproducible_yet(self) -> None:
        self.assertIn("does not consume `SOURCE_DATE_EPOCH`", self.flat)
        self.assertIn("`2026-08-22T09:43:54Z`", self.raw)
        self.assertIn("`2023-01-12T09:54:31Z`", self.raw)
        self.assertIn("build reproducibility is not yet closed", self.flat)

    def test_layout_repair_is_bounded_to_host_evidence(self) -> None:
        self.assertIn("adds exactly one symbol relative to H34, `rtic_mp`", self.flat)
        self.assertIn("H34 MPGen-free rebuild | 142,719 | 54,709", self.raw)
        self.assertIn("public-MPGen rebuild | 142,720 | 80,997", self.raw)
        self.assertIn("26,286-symbol mode shifted by `-0xd4000`", self.flat)
        self.assertIn("It is not a boot result", self.flat)

    def test_public_rom_exact_source_closure_remains_unproved(self) -> None:
        self.assertIn("| [`d6ddde5205b0`]", self.raw)
        self.assertIn("| 5,402 | 115 |", self.raw)
        self.assertIn("| [`e1d271581eff`]", self.raw)
        self.assertIn("| 5,405 | 120 |", self.raw)
        self.assertIn(
            "the exact source commit and build closure are **unproved**", self.flat
        )
        self.assertIn("No unpublished working tree", self.flat)

    def test_predecessor_links_the_follow_up_without_promoting_it(self) -> None:
        predecessor = flatten(PREDECESSOR.read_text(encoding="utf-8"))
        self.assertIn(REPORT.name, predecessor)
        self.assertIn("RTIC byte consistency now passes", predecessor)
        self.assertIn("no candidate or live authority was created", predecessor)


if __name__ == "__main__":
    unittest.main()
