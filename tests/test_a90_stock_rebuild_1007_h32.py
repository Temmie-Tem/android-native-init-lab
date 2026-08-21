"""Public-first H32 identity-only flat-builder checks."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions"
H31 = VERSIONS / "phase3-minimal-h31/manifest.toml"
H32 = VERSIONS / "phase3-minimal-h32/manifest.toml"
REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H32_H0_2026-08-22.md"
AB = ROOT / "workspace/private/outputs/a90-h32-stock-rebuild-1007-cfp-ab-20260822-01"

BOOT_SHA256 = "e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d"
RECEIPT_SHA256 = "5c075189edb5b2c48383aeb68a9f071c85cf031b6eedb5f9df08095825ff1dbc"

KERNEL_SHA256 = "59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac"
IMAGE_SHA256 = "6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557"
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


class A90StockRebuild1007H32Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.h31_text = H31.read_text(encoding="utf-8")
        cls.h32_text = H32.read_text(encoding="utf-8")
        cls.h31 = tomllib.loads(cls.h31_text)
        cls.h32 = tomllib.loads(cls.h32_text)

    def test_h32_is_fresh_identity_only_and_candidate_neutral(self) -> None:
        self.assertEqual(self.h32["profile"], "phase3-minimal-h32-stock-rebuild-1007-cfp")
        self.assertEqual(self.h32["cycle"], "H0-PHASE3H32")
        self.assertEqual(self.h32["decision"], "phase3-minimal-h32-exact-h31-functional-byte-reuse")
        self.assertEqual(self.h32["random_seed"], "a90-phase3-minimal-h32-stock-rebuild-1007-cfp")
        self.assertFalse(self.h32["candidate_authority"])
        self.assertIn('-DINIT_VERSION="0.11.199"', self.h32["init"]["cflags"])
        self.assertIn('-DINIT_BUILD="phase3-minimal-h32-stock-rebuild-1007-cfp"', self.h32["init"]["cflags"])
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h32.enable", self.h32_text)
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h32.done", self.h32_text)
        self.assertNotIn("0.11.198", self.h32["validation"]["init_strings"][0])

    def test_h32_matches_h31_on_every_functional_leaf(self) -> None:
        self.assertEqual(_functional(self.h32), _functional(self.h31))

    def test_report_binds_private_materialization(self) -> None:
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("Device contact: none", report)
        self.assertIn(BOOT_SHA256, report)
        self.assertIn(RECEIPT_SHA256, report)
        self.assertNotIn("ROOT_FILL_AFTER_PRIVATE_BUILD", report)
        self.assertIn("workspace/private/outputs/a90-h32-stock-rebuild-1007-cfp-ab-20260822-01", report)
        self.assertNotIn("candidate_authority = true", self.h32_text)
        self.assertNotIn("A90-F1", self.h32_text)

    def test_materialized_ab_kernel_and_receipt_are_exact_when_enabled(self) -> None:
        if os.environ.get("A90_H32_VERIFY_PRIVATE") != "1":
            self.skipTest("set A90_H32_VERIFY_PRIVATE=1 for private H32 verification")
        for value in (BOOT_SHA256, RECEIPT_SHA256):
            self.assertRegex(value, r"^[0-9a-f]{64}$", "fill H32 private-build hash placeholders first")
        required = (AB / "A/boot.img", AB / "B/boot.img", AB / "ab-receipt.json")
        self.assertTrue(all(path.is_file() for path in required), "private H32 output is not staged")
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
        self.assertIn(b"A90 Linux init 0.11.199 (phase3-minimal-h32-stock-rebuild-1007-cfp)", ramdisk)
        self.assertNotIn(b"0.11.198", ramdisk)
        receipt = json.loads(required[2].read_text(encoding="utf-8"))
        self.assertEqual(_sha(required[2].read_bytes()), RECEIPT_SHA256)
        self.assertTrue(receipt["byte_identical"])
        self.assertFalse(receipt["candidate_authority"])
        self.assertEqual(set(receipt["artifacts"]), {"boot", "helper", "init", "ramdisk"})


if __name__ == "__main__":
    unittest.main()
