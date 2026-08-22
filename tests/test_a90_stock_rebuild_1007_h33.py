"""Public-first H33 identity-only flat-builder checks."""

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
H32 = VERSIONS / "phase3-minimal-h32/manifest.toml"
H33 = VERSIONS / "phase3-minimal-h33/manifest.toml"
REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H33_H0_2026-08-22.md"
INPUT = ROOT / "docs/reports/A90_H33_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-22.json"
REVIEW = ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H33_INDEPENDENT_REVIEW_2026-08-22.json"
AB = ROOT / "workspace/private/outputs/a90-h33-stock-rebuild-1007-cfp-ab-20260822-01"

BOOT_SHA256 = "bdbcfc5fb82150c2d508df1e4d7ae7b71f0659b7d6b02ddab506f263f6063e12"
H32_BOOT_SHA256 = "e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d"
RECEIPT_SHA256 = "edb7f6fcf2e8431995e459a68cf2f5c8274794fee40da114dce780ca11b9fd0e"
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


class A90StockRebuild1007H33Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.h32 = tomllib.loads(H32.read_text(encoding="utf-8"))
        cls.h33 = tomllib.loads(H33.read_text(encoding="utf-8"))

    def test_h33_is_fresh_identity_only_and_candidate_neutral(self) -> None:
        self.assertEqual(self.h33["profile"], "phase3-minimal-h33-stock-rebuild-1007-cfp")
        self.assertEqual(self.h33["cycle"], "H0-PHASE3H33")
        self.assertEqual(self.h33["decision"], "phase3-minimal-h33-exact-h32-functional-byte-reuse")
        self.assertEqual(self.h33["random_seed"], "a90-phase3-minimal-h33-stock-rebuild-1007-cfp")
        self.assertFalse(self.h33["candidate_authority"])
        self.assertIn('-DINIT_VERSION="0.11.200"', self.h33["init"]["cflags"])
        self.assertIn('-DINIT_BUILD="phase3-minimal-h33-stock-rebuild-1007-cfp"', self.h33["init"]["cflags"])
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h33.enable", H33.read_text(encoding="utf-8"))
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h33.done", H33.read_text(encoding="utf-8"))
        self.assertNotIn("0.11.199", self.h33["validation"]["init_strings"][0])

    def test_h33_matches_h32_on_every_functional_leaf(self) -> None:
        self.assertEqual(_functional(self.h33), _functional(self.h32))

    def test_report_and_input_bind_host_only_materialization(self) -> None:
        report = REPORT.read_text(encoding="utf-8")
        value = json.loads(INPUT.read_text(encoding="utf-8"))
        self.assertIn("Device contact: none", report)
        self.assertIn(BOOT_SHA256, report)
        self.assertIn(RECEIPT_SHA256, report)
        self.assertIn("candidate_authority = false", report)
        self.assertEqual(value["independentReview"]["status"], "PENDING_INDEPENDENT_REVIEW")
        self.assertIsNone(value["independentReview"]["verdict"])
        self.assertTrue(REVIEW.is_file())
        self.assertEqual(_sha(REVIEW.read_bytes()), "251235439de66b408397768201016c390bbf4d3d94bd73877117501b21294f77")
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertEqual(review["candidateSha256"], value["candidate"]["sha256"])
        self.assertFalse(review["liveAuthority"])
        self.assertEqual(value["candidate"]["sha256"], BOOT_SHA256)
        self.assertEqual(value["candidate"]["size"], 58_372_096)
        self.assertFalse(any(value["authority"].values()))

    def test_materialized_ab_kernel_and_receipt_are_exact_when_enabled(self) -> None:
        if os.environ.get("A90_H33_VERIFY_PRIVATE") != "1":
            self.skipTest("set A90_H33_VERIFY_PRIVATE=1 for private H33 verification")
        required = (AB / "A/boot.img", AB / "B/boot.img", AB / "ab-receipt.json")
        self.assertTrue(all(path.is_file() for path in required), "private H33 output is not staged")
        a = required[0].read_bytes()
        b = required[1].read_bytes()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 58_372_096)
        self.assertEqual(_sha(a), BOOT_SHA256)
        self.assertNotEqual(_sha(a), H32_BOOT_SHA256)
        page = struct.unpack_from("<I", a, 36)[0]
        kernel_size = struct.unpack_from("<I", a, 8)[0]
        ramdisk_size = struct.unpack_from("<I", a, 16)[0]
        kernel = a[page : page + kernel_size]
        offset = page + (kernel_size + page - 1) // page * page
        ramdisk = a[offset : offset + ramdisk_size]
        self.assertEqual(_sha(kernel), KERNEL_SHA256)
        self.assertEqual(_sha(kernel[20 : 20 + 48_830_480]), IMAGE_SHA256)
        self.assertIn(b"A90 Linux init 0.11.200 (phase3-minimal-h33-stock-rebuild-1007-cfp)", ramdisk)
        self.assertNotIn(b"0.11.199", ramdisk)
        receipt = json.loads(required[2].read_text(encoding="utf-8"))
        self.assertEqual(_sha(required[2].read_bytes()), RECEIPT_SHA256)
        self.assertTrue(receipt["byte_identical"])
        self.assertFalse(receipt["candidate_authority"])
        self.assertEqual(set(receipt["artifacts"]), {"boot", "helper", "init", "ramdisk"})


if __name__ == "__main__":
    unittest.main()
