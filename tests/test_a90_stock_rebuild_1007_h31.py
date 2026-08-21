"""Private-free H31 identity-only flat-builder checks."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions"
H30 = VERSIONS / "phase3-minimal-h30/manifest.toml"
H31 = VERSIONS / "phase3-minimal-h31/manifest.toml"
REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H31_H0_2026-08-22.md"
AB = ROOT / "workspace/private/outputs/a90-h31-stock-rebuild-1007-cfp-ab-20260822-01"
BOOT_SHA256 = "5ad0fe043e39482163d10b1870f79c85780c12642bc04d9ee65d3eee8dd323f9"
KERNEL_SHA256 = "59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac"
IMAGE_SHA256 = "6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557"
RECEIPT_SHA256 = "559e8f655f50e6d9b126dfd2beed6e9d6713ac4ca8ed743b5371d5e4f2fb073a"
IDENTITY_PREFIXES = (
    "-DINIT_VERSION=",
    "-DINIT_BUILD=",
    "-DA90_AUTO_HANDOFF_ENABLE_PATH=",
    "-DA90_AUTO_HANDOFF_LATCH_PATH=",
)


def _functional(manifest: dict) -> dict:
    value = copy.deepcopy(manifest)
    for key in ("profile", "cycle", "decision", "random_seed"):
        value.pop(key)
    value["init"]["cflags"] = [
        flag for flag in value["init"]["cflags"]
        if not flag.startswith(IDENTITY_PREFIXES)
    ]
    value["validation"]["init_strings"] = value["validation"]["init_strings"][1:]
    return value


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class A90StockRebuild1007H31Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.h30_text = H30.read_text(encoding="utf-8")
        cls.h31_text = H31.read_text(encoding="utf-8")
        cls.h30 = tomllib.loads(cls.h30_text)
        cls.h31 = tomllib.loads(cls.h31_text)

    def test_h31_is_fresh_identity_only_and_candidate_neutral(self) -> None:
        self.assertEqual(self.h31["profile"], "phase3-minimal-h31-stock-rebuild-1007-cfp")
        self.assertEqual(self.h31["cycle"], "H0-PHASE3H31")
        self.assertEqual(self.h31["decision"], "phase3-minimal-h31-exact-h30-functional-byte-reuse")
        self.assertEqual(self.h31["random_seed"], "a90-phase3-minimal-h31-stock-rebuild-1007-cfp")
        self.assertFalse(self.h31["candidate_authority"])
        self.assertIn('-DINIT_VERSION="0.11.198"', self.h31["init"]["cflags"])
        self.assertIn('-DINIT_BUILD="phase3-minimal-h31-stock-rebuild-1007-cfp"', self.h31["init"]["cflags"])
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h31.enable", self.h31_text)
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h31.done", self.h31_text)
        self.assertNotIn("0.11.197", self.h31["validation"]["init_strings"][0])

    def test_h31_matches_h30_on_every_functional_leaf(self) -> None:
        self.assertEqual(_functional(self.h31), _functional(self.h30))

    def test_public_scope_has_no_device_or_private_effect(self) -> None:
        self.assertNotIn("candidate_authority = true", self.h31_text)
        self.assertNotIn("A90-F1", self.h31_text)
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("Device contact: none", report)
        self.assertIn(BOOT_SHA256, report)
        self.assertIn("workspace/private/outputs/a90-h31-stock-rebuild-1007-cfp-ab-20260822-01", report)

    def test_materialized_ab_kernel_and_receipt_are_exact_when_staged(self) -> None:
        required = (AB / "A/boot.img", AB / "B/boot.img", AB / "ab-receipt.json")
        if not all(path.is_file() for path in required):
            self.skipTest("private H31 output is not staged")
        a = required[0].read_bytes()
        b = required[1].read_bytes()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 58_372_096)
        self.assertEqual(_sha(a), BOOT_SHA256)
        page = struct.unpack_from("<I", a, 36)[0]
        kernel_size = struct.unpack_from("<I", a, 8)[0]
        ramdisk_size = struct.unpack_from("<I", a, 16)[0]
        kernel = a[page : page + kernel_size]
        offset = page + (kernel_size + page - 1) // page * page
        ramdisk = a[offset : offset + ramdisk_size]
        self.assertEqual(_sha(kernel), KERNEL_SHA256)
        self.assertEqual(_sha(kernel[20 : 20 + 48_830_480]), IMAGE_SHA256)
        self.assertIn(b"A90 Linux init 0.11.198 (phase3-minimal-h31-stock-rebuild-1007-cfp)", ramdisk)
        self.assertNotIn(b"0.11.197", ramdisk)
        receipt = json.loads(required[2].read_text(encoding="utf-8"))
        self.assertEqual(_sha(required[2].read_bytes()), RECEIPT_SHA256)
        self.assertTrue(receipt["byte_identical"])
        self.assertFalse(receipt["candidate_authority"])
        self.assertEqual(set(receipt["artifacts"]), {"boot", "helper", "init", "ramdisk"})


if __name__ == "__main__":
    unittest.main()
