"""Host-only H30 identity-only flat-builder checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import tomllib
import unittest


REPO = Path(__file__).resolve().parents[1]
VERSIONS = REPO / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions"
MANIFEST = VERSIONS / "phase3-minimal-h30/manifest.toml"
H29_MANIFEST = VERSIONS / "phase3-minimal-h29/manifest.toml"
HANDOFF = REPO / "docs/plans/A90_H30_CURRENT_CLOSURE_REVIEW_HANDOFF_2026-08-21.md"
OWNER = REPO / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
CONTINUATION = REPO / "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py"
BASE = REPO / "workspace/private/inputs/boot_images/boot_a90_base_stock_rebuild_1007_20260821.img"
AB = REPO / "workspace/private/outputs/a90-h30-stock-rebuild-1007-cfp-ab-20260821-01"
H29_BOOT = REPO / "workspace/private/outputs/a90-h29-stock-rebuild-1007-cfp-ab-20260821-01/A/boot.img"

BASE_SIZE = 66_379_776
BASE_SHA256 = "5cf27a56b7887b3f766af3caa7c1441cac51d153faf4f64a771902ad7f0118f6"
CANDIDATE_SIZE = 58_372_096
CANDIDATE_SHA256 = "d28bd41434d252619dd95ecb352f55140d93889fd599784c0a7dbf491959c5fe"
H29_SHA256 = "c3d1b84eab65f387ce807cf9c355dc04dcc966cef15bf64e4fda901242907324"
KERNEL_SIZE = 49_827_613
KERNEL_SHA256 = "59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac"
IMAGE_SIZE = 48_830_480
IMAGE_SHA256 = "6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557"
MANIFEST_SHA256 = "cd067d0000c3f64d9367b5f5b0f6c29202829367a8dc9e4f81b886dfe8565ef5"
EFFECTIVE_MANIFEST_SHA256 = "b92a41aebeea2bbfdfd0b91fe708135ebcc124dafd00b5ef8c52c70b9744bb22"
RECEIPT_SHA256 = "88de4c342d66025bc49689a1c6b3c3d6fed86f418eb063010ce0dc06dea31f4f"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


class A90StockRebuild1007H30Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = MANIFEST.read_text(encoding="utf-8")
        cls.manifest = tomllib.loads(cls.text)
        cls.h29 = tomllib.loads(H29_MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_is_identity_only_and_candidate_neutral(self) -> None:
        self.assertEqual(self.manifest["profile"], "phase3-minimal-h30-stock-rebuild-1007-cfp")
        self.assertEqual(self.manifest["cycle"], "H0-PHASE3H30")
        self.assertEqual(self.manifest["decision"], "phase3-minimal-h30-exact-h29-functional-byte-reuse")
        self.assertEqual(self.manifest["random_seed"], "a90-phase3-minimal-h30-stock-rebuild-1007-cfp")
        self.assertFalse(self.manifest["candidate_authority"])
        self.assertIn('-DINIT_VERSION="0.11.197"', self.manifest["init"]["cflags"])
        self.assertIn('-DINIT_BUILD="phase3-minimal-h30-stock-rebuild-1007-cfp"', self.manifest["init"]["cflags"])
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h30.enable", self.text)
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h30.done", self.text)
        for stale in ("0.11.196", "phase3-minimal-h29-stock", "/cache/a90-auto-handoff-phase3-minimal-h29."):
            self.assertNotIn(stale, self.text)

    def test_h30_preserves_h29_functional_inputs(self) -> None:
        identity = ("-DINIT_VERSION=", "-DINIT_BUILD=", "-DA90_AUTO_HANDOFF_ENABLE_PATH=", "-DA90_AUTO_HANDOFF_LATCH_PATH=")
        self.assertEqual(self.manifest["inputs"], self.h29["inputs"])
        self.assertEqual(self.manifest["init"]["closure_globs"], self.h29["init"]["closure_globs"])
        self.assertEqual(self.manifest["init"]["closure_sha256"], self.h29["init"]["closure_sha256"])
        self.assertEqual(
            [flag for flag in self.manifest["init"]["cflags"] if not flag.startswith(identity)],
            [flag for flag in self.h29["init"]["cflags"] if not flag.startswith(identity)],
        )
        self.assertEqual(self.manifest["validation"]["init_strings"][1:], self.h29["validation"]["init_strings"][1:])

    def test_private_base_and_ab_outputs_are_exact_when_staged(self) -> None:
        if not BASE.is_file():
            self.skipTest("private base is not staged")
        required = (AB / "A/boot.img", AB / "B/boot.img", AB / "ab-receipt.json")
        if not all(path.is_file() for path in required):
            self.skipTest("private H30 output is not staged")
        self.assertEqual(BASE.stat().st_size, BASE_SIZE)
        self.assertEqual(sha256(BASE.read_bytes()), BASE_SHA256)
        a = required[0].read_bytes()
        b = required[1].read_bytes()
        self.assertEqual(a, b)
        self.assertEqual(len(a), CANDIDATE_SIZE)
        self.assertEqual(sha256(a), CANDIDATE_SHA256)
        self.assertNotEqual(CANDIDATE_SHA256, H29_SHA256)
        if H29_BOOT.is_file():
            self.assertEqual(sha256(H29_BOOT.read_bytes()), H29_SHA256)

    def test_boot_contains_exact_kernel_and_h30_identity(self) -> None:
        path = AB / "A/boot.img"
        if not path.is_file():
            self.skipTest("private H30 boot is not staged")
        data = path.read_bytes()
        page = struct.unpack_from("<I", data, 36)[0]
        kernel_size = struct.unpack_from("<I", data, 8)[0]
        ramdisk_size = struct.unpack_from("<I", data, 16)[0]
        kernel = data[page : page + kernel_size]
        offset = page + align(kernel_size, page)
        ramdisk = data[offset : offset + ramdisk_size]
        self.assertEqual(page, 4096)
        self.assertEqual(kernel_size, KERNEL_SIZE)
        self.assertEqual(sha256(kernel), KERNEL_SHA256)
        self.assertEqual(sha256(kernel[20 : 20 + IMAGE_SIZE]), IMAGE_SHA256)
        self.assertIn(b"A90 Linux init 0.11.197 (phase3-minimal-h30-stock-rebuild-1007-cfp)", ramdisk)
        self.assertNotIn(b"0.11.196", ramdisk)

    def test_receipt_binds_exact_manifest_and_boot_only_scope(self) -> None:
        receipt_path = AB / "ab-receipt.json"
        if not receipt_path.is_file():
            self.skipTest("private H30 receipt is not staged")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(sha256(MANIFEST.read_bytes()), MANIFEST_SHA256)
        self.assertEqual(sha256(receipt_path.read_bytes()), RECEIPT_SHA256)
        self.assertEqual(receipt["manifest_sha256"], MANIFEST_SHA256)
        self.assertEqual(receipt["effective_manifest_sha256"], EFFECTIVE_MANIFEST_SHA256)
        self.assertTrue(receipt["byte_identical"])
        self.assertTrue(receipt["accepted_boot_unchanged"])
        self.assertFalse(receipt["candidate_authority"])
        self.assertEqual(set(receipt["artifacts"]), {"boot", "helper", "init", "ramdisk"})

    def test_manifest_grants_no_execution_authority(self) -> None:
        self.assertIn("candidate_authority = false", self.text)
        self.assertNotIn("A90-F1", self.text)

    def test_review_handoff_binds_current_public_closures(self) -> None:
        import importlib.util
        import sys

        values = []
        for name, path in (("a90_h30_owner", OWNER), ("a90_h30_continuation", CONTINUATION)):
            spec = importlib.util.spec_from_file_location(name, path)
            self.assertIsNotNone(spec)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            assert spec.loader is not None
            spec.loader.exec_module(module)
            values.append(module.execution_closure_sha256())
        handoff = HANDOFF.read_text(encoding="utf-8")
        for value in values:
            self.assertIn(value, handoff)
        self.assertIn(CANDIDATE_SHA256, handoff)
        self.assertIn("Authority: none", handoff)


if __name__ == "__main__":
    unittest.main()
