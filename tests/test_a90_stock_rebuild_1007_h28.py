"""Pin the A90 exact-10.0.7 rebuild report and H28 private artifact boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import tomllib
import unittest


REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / (
    "docs/reports/"
    "A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H28_H0_2026-08-21.md"
)
PRIOR = REPO / "docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md"
GOAL = REPO / "GOAL_A90.md"
MANIFEST = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h28/manifest.toml"
)
BASE = REPO / (
    "workspace/private/inputs/boot_images/"
    "boot_a90_base_stock_rebuild_1007_20260821.img"
)
AB = REPO / "workspace/private/outputs/a90-h28-stock-rebuild-1007-ab-20260821-01"

BASE_SIZE = 66_379_776
BASE_SHA256 = "5cf27a56b7887b3f766af3caa7c1441cac51d153faf4f64a771902ad7f0118f6"
CANDIDATE_SIZE = 58_372_096
CANDIDATE_SHA256 = "aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b"
KERNEL_SIZE = 49_827_613
KERNEL_SHA256 = "59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac"
IMAGE_SIZE = 48_830_480
IMAGE_SHA256 = "6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


class A90StockRebuild1007H28Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.prior = PRIOR.read_text(encoding="utf-8")
        cls.manifest = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_prior_keeps_history_and_links_the_explicit_correction(self) -> None:
        self.assertIn("Superseded compiler conclusion (2026-08-21)", self.prior)
        self.assertIn(REPORT.name, self.prior)
        self.assertIn("statement below that\n> the required CFP compiler was not published is false", self.prior)

    def test_goal_records_h27_consumption_and_h28_h0_only_status(self) -> None:
        goal = GOAL.read_text(encoding="utf-8")
        self.assertIn("H27 was written once, boot-looped, and was never replayed", goal)
        self.assertIn("terminal-only V2321 recovery receipt", goal)
        self.assertIn(CANDIDATE_SHA256, goal)
        self.assertIn("H28 remains H0-only", goal)

    def test_report_calibrates_build_success_separately_from_boot_proof(self) -> None:
        for claim in (
            "whether A90 boots this kernel remains **unproved**",
            "It is not byte-identical to stock and is not called stock",
            "full kernel bit reproducibility\nis **unproved**",
            "stock external-module trust equivalence is\nunproved",
            "No live authority is\ngranted",
        ):
            self.assertIn(claim, self.report)
        self.assertIn("CONFIG_RKP_CFP_JOPP=y", self.report)
        self.assertIn("CONFIG_RKP_CFP_ROPP=y", self.report)
        self.assertIn("453971166fa1b628df189e602f355cb2c58c12cd289515400ee6260c9a83459d", self.report)

    def test_manifest_is_fresh_h28_and_not_the_consumed_h27_generation(self) -> None:
        manifest_text = MANIFEST.read_text(encoding="utf-8")
        self.assertEqual(self.manifest["profile"], "phase3-minimal-h28-stock-rebuild-1007-cfp")
        self.assertEqual(self.manifest["cycle"], "H0-PHASE3H28")
        self.assertFalse(self.manifest["candidate_authority"])
        self.assertEqual(self.manifest["inputs"]["base_boot_sha256"], BASE_SHA256)
        self.assertIn('-DINIT_VERSION="0.11.195"', self.manifest["init"]["cflags"])
        self.assertIn(
            '-DINIT_BUILD="phase3-minimal-h28-stock-rebuild-1007-cfp"',
            self.manifest["init"]["cflags"],
        )
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h28.enable", manifest_text)
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h28.done", manifest_text)
        for stale in ("phase3-minimal-h27", "nocfp", "0.11.194", "cfp-disabled"):
            self.assertNotIn(stale, manifest_text)

    def test_private_base_matches_when_staged(self) -> None:
        if not BASE.is_file():
            self.skipTest(f"private base not staged: {BASE}")
        data = BASE.read_bytes()
        self.assertEqual(len(data), BASE_SIZE)
        self.assertEqual(sha256(data), BASE_SHA256)

    def test_private_ab_candidate_binds_exact_kernel_and_identity_when_staged(self) -> None:
        a = AB / "A/boot.img"
        b = AB / "B/boot.img"
        receipt_path = AB / "ab-receipt.json"
        if not all(path.is_file() for path in (a, b, receipt_path)):
            self.skipTest(f"private H28 A/B output not staged: {AB}")
        a_data = a.read_bytes()
        b_data = b.read_bytes()
        self.assertEqual(a_data, b_data)
        self.assertEqual(len(a_data), CANDIDATE_SIZE)
        self.assertEqual(sha256(a_data), CANDIDATE_SHA256)
        self.assertEqual(a_data[:8], b"ANDROID!")
        kernel_size, _kernel_addr, ramdisk_size = struct.unpack_from("<III", a_data, 8)
        page_size = struct.unpack_from("<I", a_data, 36)[0]
        self.assertEqual(page_size, 4096)
        self.assertEqual(kernel_size, KERNEL_SIZE)
        kernel = a_data[page_size : page_size + kernel_size]
        self.assertEqual(sha256(kernel), KERNEL_SHA256)
        self.assertEqual(kernel[:16], b"UNCOMPRESSED_IMG")
        image_size = struct.unpack_from("<I", kernel, 16)[0]
        self.assertEqual(image_size, IMAGE_SIZE)
        self.assertEqual(sha256(kernel[20 : 20 + image_size]), IMAGE_SHA256)
        ramdisk_offset = page_size + align(kernel_size, page_size)
        ramdisk = a_data[ramdisk_offset : ramdisk_offset + ramdisk_size]
        self.assertIn(
            b"A90 Linux init 0.11.195 (phase3-minimal-h28-stock-rebuild-1007-cfp)",
            ramdisk,
        )
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertTrue(receipt["byte_identical"])
        self.assertFalse(receipt["candidate_authority"])
        self.assertEqual(receipt["artifacts"]["boot"]["sha256"], CANDIDATE_SHA256)
        self.assertEqual(receipt["auto_handoff_binding"]["candidate_version"], "0.11.195")
        self.assertEqual(
            receipt["auto_handoff_binding"]["candidate_build"],
            "phase3-minimal-h28-stock-rebuild-1007-cfp",
        )


if __name__ == "__main__":
    unittest.main()
