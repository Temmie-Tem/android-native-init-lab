"""Public-first H35 identity-only flat-builder checks."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tomllib
import unittest

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions"
H34 = VERSIONS / "phase3-minimal-h34/manifest.toml"
H35 = VERSIONS / "phase3-minimal-h35/manifest.toml"
REVIEW = ROOT / (
    "docs/reports/"
    "A90_RTIC_PUBLIC_MPGEN_CANARY_HAZARD_INDEPENDENT_REVIEW_2026-08-23.json"
)
PACKAGE_REPORT = ROOT / (
    "docs/reports/"
    "A90_H35_PUBLIC_MPGEN_RTIC_CANARY_PACKAGE_H0_2026-08-23.md"
)
BUILDLIB = load_script(
    "workspace/public/src/scripts/revalidation/a90_flat_builder/buildlib.py"
)

EXPECTED_PROFILE = "phase3-minimal-h35-public-mpgen-rtic-canary"
EXPECTED_CYCLE = "H0-PHASE3H35"
EXPECTED_DECISION = (
    "phase3-minimal-h35-exact-h34-ramdisk-semantics-reviewed-rtic-carrier"
)
EXPECTED_SEED = "a90-phase3-minimal-h35-public-mpgen-rtic-canary"
EXPECTED_BASE_BOOT = (
    "workspace/private/inputs/boot_images/"
    "boot_a90_base_rtic_public_mpgen_canary_20260823.img"
)
EXPECTED_BASE_BOOT_SHA256 = (
    "5d681bbddf527fdacf1e433cdf30a0ca0b11d455c1b6e879c809418fd0d75484"
)
EXPECTED_BASE_BOOT_SIZE = 66_379_776
EXPECTED_CARRIER_SIZE = 49_827_613
EXPECTED_CARRIER_SHA256 = (
    "15b49a71aeb2342a5b5a7e24de27f78a4124bf877f6d8d8f28aaab928fa6bd71"
)
EXPECTED_IMAGE_SHA256 = (
    "1ddae56f8df97030794a590192e4a4162876736029b1a54fd26173c9287002b7"
)
EXPECTED_RTIC_DTB_SHA256 = (
    "68e6ab5bb2ccdde5e3d87086110257176c0fe55726d1d4f5db6eba3a4b6aca04"
)
PRIVATE_AB_ROOT = ROOT / (
    "workspace/private/outputs/"
    "a90-h35-public-mpgen-rtic-canary-ab-20260823-01"
)
EXPECTED_BOOT_SIZE = 58_372_096
EXPECTED_BOOT_SHA256 = (
    "5e2a44420195090e75f63e350cacdbcad88710e77cef9bcf29a6d3ee6f4ad759"
)
EXPECTED_RECEIPT_SIZE = 5_430
EXPECTED_RECEIPT_SHA256 = (
    "5c21ec82cee9cc9497867518d710c8374b54240bf115f3e2b9c3d0ed5b4216f9"
)
EXPECTED_INIT_SIZE = 1_723_376
EXPECTED_INIT_SHA256 = (
    "fbf330683ee08958379e0f69d2795d6dd26530b8cb1f6eb860e131fe959f4c00"
)
EXPECTED_HELPER_SIZE = 1_649_904
EXPECTED_HELPER_SHA256 = (
    "fcb005b0454aceb08aa6f8f81d83aa303e37199a56e018eb2501e4225f08e00e"
)
EXPECTED_RAMDISK_SIZE = 8_537_600
EXPECTED_RAMDISK_SHA256 = (
    "194a8797f59b7b0360845b6daa02d303bb2c09d2f6271116a10d9f1835feb824"
)
EXPECTED_MANIFEST_SHA256 = (
    "0b8ed49e5cb4ddc57fb73a1f43948d2c0c93829d7fb71a751f9badf75b52d89a"
)
EXPECTED_EFFECTIVE_MANIFEST_SHA256 = (
    "9fa94d1ad72c4891da036638a7ac43127a008cd45869df3b54f1fb0b8cf252b9"
)
IDENTITY_PREFIXES = (
    "-DINIT_VERSION=",
    "-DINIT_BUILD=",
    "-DA90_AUTO_HANDOFF_ENABLE_PATH=",
    "-DA90_AUTO_HANDOFF_LATCH_PATH=",
)


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def _functional(manifest: dict[str, object]) -> dict[str, object]:
    """Remove only H35 identity/input leaves before comparing to H34."""

    value = copy.deepcopy(manifest)
    for key in ("profile", "cycle", "decision", "random_seed"):
        value.pop(key)
    inputs = value["inputs"]
    assert isinstance(inputs, dict)
    for key in ("base_boot", "base_boot_sha256"):
        inputs.pop(key)
    init = value["init"]
    assert isinstance(init, dict)
    cflags = init["cflags"]
    assert isinstance(cflags, list)
    init["cflags"] = [
        flag for flag in cflags
        if not any(isinstance(flag, str) and flag.startswith(prefix) for prefix in IDENTITY_PREFIXES)
    ]
    validation = value["validation"]
    assert isinstance(validation, dict)
    init_strings = validation["init_strings"]
    assert isinstance(init_strings, list)
    validation["init_strings"] = init_strings[1:]
    return value


def _assert_review_binding(review: dict[str, object]) -> None:
    """Reject a review unless its H0 hazard binding is exact."""

    if review["schema"] != "a90-rtic-public-mpgen-canary-hazard-independent-review-v1":
        raise AssertionError("unexpected hazard-review schema")
    if review["verdict"] != "PASS_GO_H0_CANARY_HAZARD":
        raise AssertionError("hazard review is not the exact H0 canary verdict")
    if review["tier"] != "H0":
        raise AssertionError("hazard review is not H0")
    if review["candidateAllocated"] is not False:
        raise AssertionError("hazard review allocated a candidate")
    if review["liveAuthority"] is not False:
        raise AssertionError("hazard review grants live authority")
    artifact = review["artifact"]
    if not isinstance(artifact, dict):
        raise AssertionError("hazard artifact binding is not an object")
    expected = {
        "expectedCarrierSize": EXPECTED_CARRIER_SIZE,
        "expectedCarrierSha256": EXPECTED_CARRIER_SHA256,
        "imageSha256": EXPECTED_IMAGE_SHA256,
        "rticDtbSha256": EXPECTED_RTIC_DTB_SHA256,
    }
    for key, expected_value in expected.items():
        if artifact.get(key) != expected_value:
            raise AssertionError(f"hazard artifact binding mismatch: {key}")


def _assert_functional_reuse(
    h35: dict[str, object], h34: dict[str, object]
) -> None:
    if _functional(h35) != _functional(h34):
        raise AssertionError("H35 functional manifest leaves differ from H34")


class A90PublicMpgenRticH35Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.h34 = BUILDLIB.resolve_manifest(H34).data
        cls.h35_resolution = BUILDLIB.resolve_manifest(H35)
        cls.h35 = cls.h35_resolution.data
        cls.raw_h35 = H35.read_text(encoding="utf-8")
        cls.review = json.loads(
            REVIEW.read_text(encoding="utf-8"), object_pairs_hook=_strict_object
        )
        cls.package_report = PACKAGE_REPORT.read_text(encoding="utf-8")
        cls.package_report_flat = " ".join(cls.package_report.split())

    def test_h35_is_fresh_identity_only_and_candidate_neutral(self) -> None:
        self.assertEqual(self.h35["profile"], EXPECTED_PROFILE)
        self.assertEqual(self.h35["cycle"], EXPECTED_CYCLE)
        self.assertEqual(self.h35["decision"], EXPECTED_DECISION)
        self.assertEqual(self.h35["random_seed"], EXPECTED_SEED)
        self.assertFalse(self.h35["candidate_authority"])
        self.assertIn('-DINIT_VERSION="0.11.202"', self.h35["init"]["cflags"])
        self.assertIn('-DINIT_BUILD="phase3-minimal-h35-public-mpgen-rtic-canary"', self.h35["init"]["cflags"])
        self.assertIn(
            '-DA90_AUTO_HANDOFF_ENABLE_PATH="/cache/a90-auto-handoff-phase3-minimal-h35.enable"',
            self.h35["init"]["cflags"],
        )
        self.assertIn(
            '-DA90_AUTO_HANDOFF_LATCH_PATH="/cache/a90-auto-handoff-phase3-minimal-h35.done"',
            self.h35["init"]["cflags"],
        )
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h35.enable", self.raw_h35)
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h35.done", self.raw_h35)
        self.assertNotIn("phase3-minimal-h34-stock-rebuild-1007-cfp", self.raw_h35)
        self.assertNotIn("0.11.201", self.h35["validation"]["init_strings"][0])

    def test_h35_matches_h34_on_every_other_effective_leaf(self) -> None:
        self.assertEqual(_functional(self.h35), _functional(self.h34))
        self.assertEqual(
            self.h35["inputs"]["accepted_boot"], self.h34["inputs"]["accepted_boot"]
        )
        self.assertEqual(
            self.h35["inputs"]["accepted_boot_sha256"],
            self.h34["inputs"]["accepted_boot_sha256"],
        )
        self.assertEqual(_sha256(H35.read_bytes()), EXPECTED_MANIFEST_SHA256)
        self.assertEqual(
            self.h35_resolution.effective_sha256,
            EXPECTED_EFFECTIVE_MANIFEST_SHA256,
        )

    def test_h35_base_boot_is_the_exact_public_rtic_input_binding(self) -> None:
        self.assertEqual(self.h35["inputs"]["base_boot"], EXPECTED_BASE_BOOT)
        self.assertEqual(
            self.h35["inputs"]["base_boot_sha256"], EXPECTED_BASE_BOOT_SHA256
        )

    def test_review_is_exact_h0_hazard_go_without_authority(self) -> None:
        _assert_review_binding(self.review)
        self.assertIs(self.review["candidateAllocated"], False)
        self.assertIs(self.review["liveAuthority"], False)

    def test_unreviewed_carrier_hash_is_rejected(self) -> None:
        hostile = copy.deepcopy(self.review)
        hostile["artifact"]["expectedCarrierSha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            _assert_review_binding(hostile)

    def test_additional_functional_flag_is_rejected(self) -> None:
        hostile = copy.deepcopy(self.h35)
        hostile["init"]["cflags"].append("-DA90_H35_UNREVIEWED_FUNCTIONAL_FLAG=1")
        with self.assertRaises(AssertionError):
            _assert_functional_reuse(hostile, self.h34)

    def test_package_report_preserves_the_h0_boundary(self) -> None:
        for token in (
            "Tier: H0 private-host packaging and static validation",
            "Device, `/dev`, USB, ADB, and network contact: none",
            "Authority: none — no D0, D1, F1, approval, ordinal, journal, transfer, reboot, rollback, or replay is created here",
            "version `0.11.202`",
            "build `phase3-minimal-h35-public-mpgen-rtic-canary`",
            "5e2a44420195090e75f63e350cacdbcad88710e77cef9bcf29a6d3ee6f4ad759",
            "5c21ec82cee9cc9497867518d710c8374b54240bf115f3e2b9c3d0ed5b4216f9",
            EXPECTED_CARRIER_SHA256,
            EXPECTED_IMAGE_SHA256,
            EXPECTED_RTIC_DTB_SHA256,
            EXPECTED_BASE_BOOT_SHA256,
            "current V2321 health",
            "H29 through H34 remain consumed and non-replayable",
            "package-specific independent H0 review is still separate",
            "candidate-specific qualification",
            "fresh connected D0",
            "F1 authority",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.package_report_flat)

    def test_private_h35_materialization_is_exact_when_enabled(self) -> None:
        if os.environ.get("A90_H35_VERIFY_PRIVATE") != "1":
            self.skipTest("set A90_H35_VERIFY_PRIVATE=1 for private H35 verification")

        def read_regular(path: Path) -> bytes:
            self.assertTrue(path.is_file() and not path.is_symlink(), f"not a regular file: {path}")
            return path.read_bytes()

        self.assertTrue(
            PRIVATE_AB_ROOT.is_dir() and not PRIVATE_AB_ROOT.is_symlink(),
            f"private H35 AB root is not a directory: {PRIVATE_AB_ROOT}",
        )
        base = read_regular(ROOT / EXPECTED_BASE_BOOT)
        self.assertEqual(len(base), EXPECTED_BASE_BOOT_SIZE)
        self.assertEqual(_sha256(base), EXPECTED_BASE_BOOT_SHA256)

        expected_artifacts = {
            "boot.img": (EXPECTED_BOOT_SIZE, EXPECTED_BOOT_SHA256),
            "build/init": (EXPECTED_INIT_SIZE, EXPECTED_INIT_SHA256),
            "build/helper": (EXPECTED_HELPER_SIZE, EXPECTED_HELPER_SHA256),
            "build/ramdisk.cpio": (EXPECTED_RAMDISK_SIZE, EXPECTED_RAMDISK_SHA256),
        }
        artifact_bytes: dict[str, bytes] = {}
        for relative, (expected_size, expected_sha256) in expected_artifacts.items():
            a = read_regular(PRIVATE_AB_ROOT / "A" / relative)
            b = read_regular(PRIVATE_AB_ROOT / "B" / relative)
            self.assertEqual(a, b, relative)
            self.assertEqual(len(a), expected_size, relative)
            self.assertEqual(_sha256(a), expected_sha256, relative)
            artifact_bytes[relative] = a

        boot = artifact_bytes["boot.img"]
        page = struct.unpack_from("<I", boot, 36)[0]
        kernel_size = struct.unpack_from("<I", boot, 8)[0]
        ramdisk_size = struct.unpack_from("<I", boot, 16)[0]
        self.assertEqual(page, 4096)
        self.assertEqual(kernel_size, EXPECTED_CARRIER_SIZE)
        kernel = boot[page : page + kernel_size]
        self.assertEqual(len(kernel), EXPECTED_CARRIER_SIZE)
        self.assertEqual(_sha256(kernel), EXPECTED_CARRIER_SHA256)
        self.assertEqual(
            _sha256(kernel[20 : 20 + 48_830_480]), EXPECTED_IMAGE_SHA256
        )
        ramdisk_offset = page + _align(kernel_size, page)
        ramdisk = boot[ramdisk_offset : ramdisk_offset + ramdisk_size]
        self.assertEqual(_sha256(ramdisk), EXPECTED_RAMDISK_SHA256)
        h35_banner = (
            b"A90 Linux init 0.11.202 "
            b"(phase3-minimal-h35-public-mpgen-rtic-canary)"
        )
        h34_banner = (
            b"A90 Linux init 0.11.201 "
            b"(phase3-minimal-h34-stock-rebuild-1007-cfp)"
        )
        self.assertIn(h35_banner, ramdisk)
        self.assertNotIn(h34_banner, ramdisk)
        self.assertIn(h35_banner, artifact_bytes["build/init"])
        self.assertNotIn(h34_banner, artifact_bytes["build/init"])

        receipt_bytes = read_regular(PRIVATE_AB_ROOT / "ab-receipt.json")
        self.assertEqual(len(receipt_bytes), EXPECTED_RECEIPT_SIZE)
        self.assertEqual(_sha256(receipt_bytes), EXPECTED_RECEIPT_SHA256)
        receipt = json.loads(receipt_bytes, object_pairs_hook=_strict_object)
        self.assertIs(receipt["byte_identical"], True)
        self.assertIs(receipt["accepted_boot_unchanged"], True)
        self.assertIs(receipt["candidate_authority"], False)
        self.assertEqual(
            set(receipt["artifacts"]), {"boot", "helper", "init", "ramdisk"}
        )
        self.assertEqual(receipt["manifest_sha256"], EXPECTED_MANIFEST_SHA256)
        self.assertEqual(
            receipt["effective_manifest_sha256"],
            EXPECTED_EFFECTIVE_MANIFEST_SHA256,
        )
        self.assertEqual(_sha256(H35.read_bytes()), EXPECTED_MANIFEST_SHA256)
        self.assertEqual(
            self.h35_resolution.effective_sha256,
            EXPECTED_EFFECTIVE_MANIFEST_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
