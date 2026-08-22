"""Public-first H34 identity-only flat-builder checks."""

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
H33 = VERSIONS / "phase3-minimal-h33/manifest.toml"
H34 = VERSIONS / "phase3-minimal-h34/manifest.toml"
REPORT = ROOT / "docs/reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H34_H0_2026-08-22.md"
INPUT = ROOT / "docs/reports/A90_H34_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-22.json"
REVIEW = ROOT / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H34_INDEPENDENT_REVIEW_2026-08-22.json"
CONTINUATION_REVIEW = ROOT / "docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_CURRENT_REVIEW.json"
POSTROLLBACK_REVIEW = ROOT / "docs/reports/A90_F1_POSTROLLBACK_RECOVERY_CURRENT_REVIEW.json"
AB = ROOT / "workspace/private/outputs/a90-h34-stock-rebuild-1007-cfp-ab-20260822-01"

BOOT_SHA256 = "233bfdcac20d5fdc1184a907e8e8b5cd4d2c1286dc08a8f6028cfcf5c90ad4ee"
H33_BOOT_SHA256 = "bdbcfc5fb82150c2d508df1e4d7ae7b71f0659b7d6b02ddab506f263f6063e12"
RECEIPT_SHA256 = "606ff98cd06a4caa8f1f5e35bcc18dea85352ee0e458a0bf49b074fc2329eb3f"
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


class A90StockRebuild1007H34Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.h33 = tomllib.loads(H33.read_text(encoding="utf-8"))
        cls.h34 = tomllib.loads(H34.read_text(encoding="utf-8"))

    def test_h34_is_fresh_identity_only_and_candidate_neutral(self) -> None:
        text = H34.read_text(encoding="utf-8")
        self.assertEqual(self.h34["profile"], "phase3-minimal-h34-stock-rebuild-1007-cfp")
        self.assertEqual(self.h34["cycle"], "H0-PHASE3H34")
        self.assertEqual(self.h34["decision"], "phase3-minimal-h34-exact-h33-functional-byte-reuse")
        self.assertEqual(self.h34["random_seed"], "a90-phase3-minimal-h34-stock-rebuild-1007-cfp")
        self.assertFalse(self.h34["candidate_authority"])
        self.assertIn('-DINIT_VERSION="0.11.201"', self.h34["init"]["cflags"])
        self.assertIn('-DINIT_BUILD="phase3-minimal-h34-stock-rebuild-1007-cfp"', self.h34["init"]["cflags"])
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h34.enable", text)
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h34.done", text)
        self.assertNotIn("0.11.200", self.h34["validation"]["init_strings"][0])

    def test_h34_matches_h33_on_every_functional_leaf(self) -> None:
        self.assertEqual(_functional(self.h34), _functional(self.h33))

    def test_report_input_and_current_capability_reviews_bind_h0_only(self) -> None:
        report = REPORT.read_text(encoding="utf-8")
        value = json.loads(INPUT.read_text(encoding="utf-8"))
        self.assertIn("Device contact: none", report)
        self.assertIn(BOOT_SHA256, report)
        self.assertIn(RECEIPT_SHA256, report)
        self.assertEqual(value["candidate"]["sha256"], BOOT_SHA256)
        self.assertEqual(value["candidate"]["size"], 58_372_096)
        self.assertFalse(any(value["authority"].values()))
        self.assertEqual(value["independentReview"]["status"], "PENDING_INDEPENDENT_REVIEW")
        self.assertIsNone(value["independentReview"]["verdict"])
        self.assertTrue(REVIEW.is_file())
        self.assertEqual(_sha(REVIEW.read_bytes()), "9741aa0a5b9f0fdc93d5210e195fda5353270d6406713efa4d86ba3b720036d3")
        review = json.loads(REVIEW.read_text(encoding="utf-8"))
        self.assertEqual(review["verdict"], "PASS_GO")
        self.assertEqual(review["candidateSha256"], value["candidate"]["sha256"])
        self.assertFalse(review["liveAuthority"])
        self.assertEqual(_sha(CONTINUATION_REVIEW.read_bytes()), "22c0e6a60eb94dd5407d995c8e4b7e283bb149057e0ecbf8164dae5e613b49e9")
        self.assertEqual(_sha(POSTROLLBACK_REVIEW.read_bytes()), "429c84e57b873619fd840df7afa009d52a99560de6a4c461cf84da3c73aa5429")

    def test_materialized_ab_kernel_and_receipt_are_exact_when_enabled(self) -> None:
        if os.environ.get("A90_H34_VERIFY_PRIVATE") != "1":
            self.skipTest("set A90_H34_VERIFY_PRIVATE=1 for private H34 verification")
        required = (AB / "A/boot.img", AB / "B/boot.img", AB / "ab-receipt.json")
        self.assertTrue(all(path.is_file() for path in required), "private H34 output is not staged")
        a = required[0].read_bytes()
        b = required[1].read_bytes()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 58_372_096)
        self.assertEqual(_sha(a), BOOT_SHA256)
        self.assertNotEqual(_sha(a), H33_BOOT_SHA256)
        page = struct.unpack_from("<I", a, 36)[0]
        kernel_size = struct.unpack_from("<I", a, 8)[0]
        ramdisk_size = struct.unpack_from("<I", a, 16)[0]
        kernel = a[page : page + kernel_size]
        offset = page + (kernel_size + page - 1) // page * page
        ramdisk = a[offset : offset + ramdisk_size]
        self.assertEqual(_sha(kernel), KERNEL_SHA256)
        self.assertEqual(_sha(kernel[20 : 20 + 48_830_480]), IMAGE_SHA256)
        self.assertIn(b"A90 Linux init 0.11.201 (phase3-minimal-h34-stock-rebuild-1007-cfp)", ramdisk)
        self.assertNotIn(b"0.11.200", ramdisk)
        receipt = json.loads(required[2].read_text(encoding="utf-8"))
        self.assertEqual(_sha(required[2].read_bytes()), RECEIPT_SHA256)
        self.assertTrue(receipt["byte_identical"])
        self.assertFalse(receipt["candidate_authority"])
        self.assertEqual(set(receipt["artifacts"]), {"boot", "helper", "init", "ramdisk"})


if __name__ == "__main__":
    unittest.main()
