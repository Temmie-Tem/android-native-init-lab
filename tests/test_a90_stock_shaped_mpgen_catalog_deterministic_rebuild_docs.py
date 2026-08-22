"""Pin the bounded A90 stock-shaped MPGen H0 result and its limits."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/reports/"
    "A90_STOCK_SHAPED_MPGEN_CATALOG_AND_DETERMINISTIC_REBUILD_H0_2026-08-22.md"
)
PREDECESSOR = ROOT / (
    "docs/reports/"
    "A90_PUBLIC_MPGEN27_SELF_CONSISTENT_RTIC_REBUILD_H0_2026-08-22.md"
)


def flatten(text: str) -> str:
    return " ".join(text.split())


class StockShapedMpgenCatalogDeterministicRebuildDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = REPORT.read_text(encoding="utf-8")
        self.flat = flatten(self.raw)

    def test_scope_is_h0_and_grants_no_device_authority(self) -> None:
        for token in (
            "Tier: H0 host-only public-source acquisition, build, and artifact analysis",
            "Device contact: none",
            "Authority: no candidate, D0, D1, F1, rollback, reboot, or live authority",
            "It does not qualify a kernel, manifest, D0, or F1",
        ):
            self.assertIn(token, self.flat)

    def test_historical_catalog_is_exactly_stock_shaped(self) -> None:
        for token in (
            "381c7b77b9e47d4cf81d9a9ac2b9e7597ec9b3e5",
            "1b75830441422a5bd2380b1b5871d6768f43ef20",
            "RO 3, WK 1, WU 2, AW 0",
            "`linux_banner`, `linux_proc_banner`, `selinux_hooks`",
            "`.head.text`, `selinux_enforcing`",
            "has no `selinux_state` record",
        ):
            self.assertIn(token, self.flat)

    def test_fixed_time_outputs_are_exact(self) -> None:
        for token in (
            "`2023-01-12 09:54:31`",
            "`1673517271`",
            "`2023-01-12T09:49:35Z`",
            "`Thu Jan 12 18:53:40 KST 2023`",
            "`1673517220`",
        ):
            self.assertIn(token, self.raw)

    def test_independent_mp_and_supporting_artifacts_are_identical(self) -> None:
        expected = (
            "66fc4f4db84abeeb0003caa6aa54ea60eadc6a0af09110b7f0130ae87a03c888",
            "6d050ebdcec3e6f92665c58d6828aac381e2bb94a6c097152baa439fee1e1289",
            "1a5e28c3cd22e9831d263c214293f05ca7c5a6ca6cb173ef154b6680866c587d",
            "1976d1b08244b857b62d4f7104201129344c53827a0637b7a964bda674cd98d1",
            "1a920d47b51f4a323bc1033b6aa630db5917421971dcaabf08b36e629afc23c7",
        )
        for digest in expected:
            self.assertIn(digest, self.raw)
        self.assertIn("expected and actual MP SHA-256", self.flat)
        self.assertIn(
            "2bcf7869f375a8f39178afa85c097f83c2e895b85bafc2adc64f0b21b48f95a7",
            self.raw,
        )

    def test_image_difference_is_not_misreported_as_full_reproducibility(self) -> None:
        self.assertIn("exactly two 20-byte ranges", self.flat)
        self.assertIn("embedded vDSO GNU build ID", self.flat)
        self.assertIn("full path-independent Image reproducibility is not claimed", self.flat)
        self.assertIn(
            "0f03a462f96b08b48c62e51a909fa748cffe0b925cb8f928f012865d865e4248",
            self.raw,
        )

    def test_exact_stock_mp_delta_remains_visible(self) -> None:
        for token in (
            "Exactly 22 bytes differ",
            "`2.7.e26468.30`, not stock `2.7.ef86a6.30`",
            "kernel size `0x03973000`",
            "`0x039d3000`",
            "`(88, 1704, 1728, 2144)`",
            "four `0xffffffff` values",
            "This unit does not silently inject those values",
        ):
            self.assertIn(token, self.raw)

    def test_follow_up_is_linked_without_rewriting_predecessor_result(self) -> None:
        predecessor = PREDECESSOR.read_text(encoding="utf-8")
        self.assertIn(REPORT.name, predecessor)
        self.assertIn("closes stock-time determinism", flatten(predecessor))


if __name__ == "__main__":
    unittest.main()
