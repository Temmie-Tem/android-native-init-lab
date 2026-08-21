"""Host-only H29 flat-builder materialization checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import tomllib
import unittest


REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h29/manifest.toml"
)
H28_MANIFEST = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h28/manifest.toml"
)
BASE = REPO / (
    "workspace/private/inputs/boot_images/"
    "boot_a90_base_stock_rebuild_1007_20260821.img"
)
AB = REPO / "workspace/private/outputs/a90-h29-stock-rebuild-1007-cfp-ab-20260821-01"
H28_BOOT = REPO / (
    "workspace/private/outputs/a90-h28-stock-rebuild-1007-ab-20260821-01/A/boot.img"
)
H27_BOOT = REPO / (
    "workspace/private/outputs/a90-h27-selfbuilt-kernel-ab-20260817-01/A/boot.img"
)

BASE_SIZE = 66_379_776
BASE_SHA256 = "5cf27a56b7887b3f766af3caa7c1441cac51d153faf4f64a771902ad7f0118f6"
CANDIDATE_SIZE = 58_372_096
CANDIDATE_SHA256 = "c3d1b84eab65f387ce807cf9c355dc04dcc966cef15bf64e4fda901242907324"
H28_SHA256 = "aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b"
H27_SHA256 = "fa7ab8af8cec027c433653da92eb6cb4ca6f3a02d7624a4f292f61906e8ce500"
KERNEL_SIZE = 49_827_613
KERNEL_SHA256 = "59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac"
IMAGE_SIZE = 48_830_480
IMAGE_SHA256 = "6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557"
MANIFEST_SHA256 = "faab594e46ca9cfaaa477b70ef55f4674b8aab9e95847a1db8e1871a62c6988a"
EFFECTIVE_MANIFEST_SHA256 = "ecefcf16abcd603c69c16900cc21f2c7f422ad3beda5c032c7bcea5245d77347"
RECEIPT_SHA256 = "8749cc6577089fc93166ffa17d1eeb491ce040b3871e1b16c1a9732fe5e5c4dc"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


class A90StockRebuild1007H29Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest_text = MANIFEST.read_text(encoding="utf-8")
        cls.manifest = tomllib.loads(cls.manifest_text)
        cls.h28_manifest = tomllib.loads(H28_MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_is_h29_identity_only_and_candidate_neutral(self) -> None:
        self.assertEqual(self.manifest["profile"], "phase3-minimal-h29-stock-rebuild-1007-cfp")
        self.assertEqual(self.manifest["cycle"], "H0-PHASE3H29")
        self.assertEqual(self.manifest["decision"], "phase3-minimal-h29-exact-h28-functional-byte-reuse")
        self.assertEqual(self.manifest["random_seed"], "a90-phase3-minimal-h29-stock-rebuild-1007-cfp")
        self.assertFalse(self.manifest["candidate_authority"])
        self.assertEqual(self.manifest["inputs"]["base_boot_sha256"], BASE_SHA256)
        self.assertIn('-DINIT_VERSION="0.11.196"', self.manifest["init"]["cflags"])
        self.assertIn('-DINIT_BUILD="phase3-minimal-h29-stock-rebuild-1007-cfp"', self.manifest["init"]["cflags"])
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h29.enable", self.manifest_text)
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h29.done", self.manifest_text)
        for stale in (
            "phase3-minimal-h28",
            "phase3-minimal-h27",
            "0.11.195",
            "0.11.194",
            "/cache/a90-auto-handoff-phase3-minimal-h28.",
        ):
            self.assertNotIn(stale, self.manifest_text)

    def test_h29_preserves_h28_functional_flags(self) -> None:
        identity = ("-DINIT_VERSION=", "-DINIT_BUILD=", "-DA90_AUTO_HANDOFF_ENABLE_PATH=", "-DA90_AUTO_HANDOFF_LATCH_PATH=")
        h28_flags = [flag for flag in self.h28_manifest["init"]["cflags"] if not flag.startswith(identity)]
        h29_flags = [flag for flag in self.manifest["init"]["cflags"] if not flag.startswith(identity)]
        self.assertEqual(h29_flags, h28_flags)
        self.assertEqual(self.manifest["init"]["closure_globs"], self.h28_manifest["init"]["closure_globs"])
        self.assertEqual(self.manifest["init"]["closure_sha256"], self.h28_manifest["init"]["closure_sha256"])
        self.assertEqual(self.manifest["inputs"], self.h28_manifest["inputs"])
        self.assertEqual(
            self.manifest["validation"]["init_strings"][1:],
            self.h28_manifest["validation"]["init_strings"][1:],
        )

    def test_private_base_and_ab_outputs_are_exact_when_staged(self) -> None:
        if not BASE.is_file():
            self.skipTest(f"private base not staged: {BASE}")
        if not all((AB / name).is_file() for name in ("A/boot.img", "B/boot.img", "ab-receipt.json")):
            self.skipTest(f"private H29 A/B output not staged: {AB}")
        self.assertEqual(BASE.stat().st_size, BASE_SIZE)
        self.assertEqual(sha256(BASE.read_bytes()), BASE_SHA256)
        a = (AB / "A/boot.img").read_bytes()
        b = (AB / "B/boot.img").read_bytes()
        self.assertEqual(a, b)
        self.assertEqual(len(a), CANDIDATE_SIZE)
        self.assertEqual(sha256(a), CANDIDATE_SHA256)
        if H28_BOOT.is_file():
            self.assertNotEqual(CANDIDATE_SHA256, sha256(H28_BOOT.read_bytes()))
        if H27_BOOT.is_file():
            self.assertNotEqual(CANDIDATE_SHA256, sha256(H27_BOOT.read_bytes()))

    def test_boot_contains_exact_kernel_and_h29_ramdisk_identity(self) -> None:
        path = AB / "A/boot.img"
        if not path.is_file():
            self.skipTest(f"private H29 boot not staged: {path}")
        data = path.read_bytes()
        page = struct.unpack_from("<I", data, 36)[0]
        kernel_size = struct.unpack_from("<I", data, 8)[0]
        ramdisk_size = struct.unpack_from("<I", data, 16)[0]
        kernel = data[page : page + kernel_size]
        ramdisk_offset = page + align(kernel_size, page)
        ramdisk = data[ramdisk_offset : ramdisk_offset + ramdisk_size]
        self.assertEqual(page, 4096)
        self.assertEqual(kernel_size, KERNEL_SIZE)
        self.assertEqual(sha256(kernel), KERNEL_SHA256)
        self.assertEqual(kernel[:16], b"UNCOMPRESSED_IMG")
        self.assertEqual(sha256(kernel[20 : 20 + IMAGE_SIZE]), IMAGE_SHA256)
        self.assertIn(b"A90 Linux init 0.11.196 (phase3-minimal-h29-stock-rebuild-1007-cfp)", ramdisk)
        self.assertNotIn(b"0.11.195", ramdisk)

    def test_receipt_binds_manifest_and_forbids_non_boot_payloads(self) -> None:
        receipt_path = AB / "ab-receipt.json"
        if not receipt_path.is_file():
            self.skipTest(f"private H29 receipt not staged: {receipt_path}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(sha256(MANIFEST.read_bytes()), MANIFEST_SHA256)
        self.assertEqual(sha256(receipt_path.read_bytes()), RECEIPT_SHA256)
        self.assertEqual(receipt["manifest_sha256"], MANIFEST_SHA256)
        self.assertEqual(receipt["effective_manifest_sha256"], EFFECTIVE_MANIFEST_SHA256)
        self.assertTrue(receipt["byte_identical"])
        self.assertTrue(receipt["accepted_boot_unchanged"])
        self.assertFalse(receipt["candidate_authority"])
        self.assertEqual(set(receipt["artifacts"]), {"boot", "helper", "init", "ramdisk"})
        forbidden = {"recovery", "vendor_boot", "dtbo", "vbmeta", "super", "userdata", "persist", "modem", "BL", "CP", "CSC"}
        self.assertTrue(forbidden.isdisjoint(receipt["artifacts"]))

    def test_report_and_manifest_grant_no_execution_authority(self) -> None:
        self.assertIn("candidate_authority = false", self.manifest_text)
        self.assertNotIn("A90-F1", self.manifest_text)


if __name__ == "__main__":
    unittest.main()
