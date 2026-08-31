from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "build_s20plus_g986n_recovery_adb_canary_h0.py"
)
SPEC = importlib.util.spec_from_file_location(
    "s20plus_g986n_recovery_adb_canary_h0_tested", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

EXPECTED = {
    "builder": "811b2f80db822689d716c0de400cea22440af3069d7ea20945ddf0b36908c118",
    "candidate/AP.tar.md5": "30227458889f1fa99eca192c9b7f8747f168d9e33cc1f407b52ae2b4d298559a",
    "candidate/recovery.img": "e1297613df576d25cc9391df97dac7cf316fee545f56111e6bc5340cb8ce659b",
    "candidate/recovery.img.lz4": "7f0e6b53a1036904fd02c5e8c2c014d3112ffb58fc33f9aa9a26c0962af45928",
    "rollback/AP.tar.md5": "ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157",
    "rollback/recovery.img": BUILDER.BASE_RECOVERY_SHA256,
    "rollback/recovery.img.lz4": BUILDER.BASE_RECOVERY_LZ4_SHA256,
    "manifest.json": "7c693b4e2e13efa912b5de00a95bbd41bb1651913427461e756225243381e1e3",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_ap(path: Path) -> tuple[list[tarfile.TarInfo], str]:
    data = path.read_bytes()
    trailer_length = len(b"0" * 32 + b"  AP.tar\n")
    trailer = data[-trailer_length:]
    text = trailer.decode("ascii")
    if len(text) != trailer_length or not text.endswith("  AP.tar\n"):
        raise AssertionError("invalid AP trailer")
    expected_md5 = text[:32]
    if hashlib.md5(data[:-trailer_length]).hexdigest() != expected_md5:
        raise AssertionError("AP trailer mismatch")
    with tarfile.open(path, "r:") as archive:
        members = archive.getmembers()
    return members, expected_md5


class S20PlusRecoveryAdbCanaryH0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(
            prefix="s20plus-recovery-adb-canary-tests-"
        )
        cls.root = Path(cls._temporary.name)
        cls.output = cls.root / "build-a"
        cls.result = BUILDER.build(cls.output)
        cls.manifest = json.loads(
            (cls.output / "manifest.json").read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary.cleanup()

    def test_frozen_builder_and_outputs_match(self) -> None:
        self.assertEqual(sha256(SCRIPT), EXPECTED["builder"])
        for name, expected in EXPECTED.items():
            if name == "builder":
                continue
            self.assertEqual(sha256(self.output / name), expected, name)

    def test_manifest_is_h0_review_pending_without_live_authority(self) -> None:
        data = self.manifest
        self.assertEqual(data["schema"], BUILDER.SCHEMA)
        self.assertEqual(data["verdict"], BUILDER.VERDICT)
        self.assertEqual(data["target"], BUILDER.TARGET)
        self.assertEqual(data["tier"], "H0")
        self.assertEqual(data["review_state"], "REVIEW_PENDING")
        self.assertFalse(data["live_authority"])
        for key in (
            "device_contact",
            "live_flash_authorized",
            "policy_amendment_complete",
            "independent_review_complete",
            "vbmeta_payload",
            "vendor_mutation",
            "misc_write",
            "data_format",
        ):
            self.assertFalse(data["safety"][key], key)
        for key in (
            "adb_commands",
            "su_commands",
            "reboot_commands",
            "odin_commands",
            "partition_transfers",
        ):
            self.assertEqual(data["safety"][key], 0, key)

    def test_only_three_ramdisk_entries_change(self) -> None:
        ramdisk = self.manifest["ramdisk"]
        self.assertEqual(ramdisk["added_entries"], [BUILDER.MARKER_ENTRY])
        self.assertEqual(ramdisk["removed_entries"], [])
        self.assertEqual(
            ramdisk["changed_entries"], sorted(BUILDER.CHANGED_ENTRIES)
        )
        self.assertTrue(ramdisk["all_other_entries_byte_and_mode_identical"])
        self.assertEqual(
            ramdisk["candidate_entry_count"], ramdisk["base_entry_count"] + 1
        )
        self.assertEqual(
            ramdisk["marker"]["sha256"], hashlib.sha256(BUILDER.MARKER).hexdigest()
        )
        self.assertEqual(ramdisk["marker"]["mode"], "0444")

    def test_non_ramdisk_components_and_partition_size_are_exact(self) -> None:
        components = self.manifest["components"]
        for name in ("header", "kernel", "dtb", "recovery_dtbo"):
            self.assertEqual(components["candidate"][name], components["stock"][name])
        self.assertNotEqual(
            components["candidate"]["ramdisk.cpio"],
            components["stock"]["ramdisk.cpio"],
        )
        self.assertEqual(
            self.manifest["candidate"]["recovery_img"]["size"],
            BUILDER.BASE_RECOVERY_SIZE,
        )

    def test_candidate_and_rollback_ap_are_recovery_only(self) -> None:
        for branch in ("candidate", "rollback"):
            members, md5 = parse_ap(self.output / branch / "AP.tar.md5")
            self.assertEqual(len(members), 1)
            self.assertEqual(members[0].name, "recovery.img.lz4")
            self.assertTrue(members[0].isreg())
            self.assertEqual(
                self.manifest[branch]["ap_tar_md5"]["tar_md5"], md5
            )
            self.assertEqual(
                self.manifest[branch]["ap_tar_md5"]["members"],
                ["recovery.img.lz4"],
            )

    def test_stock_avb_passes_and_custom_hash_failure_is_explicit(self) -> None:
        avb = self.manifest["avb"]
        self.assertTrue(avb["stock"]["embedded_vbmeta_signature_verified"])
        self.assertTrue(avb["stock"]["recovery_hash_descriptor_verified"])
        self.assertTrue(avb["candidate"]["embedded_vbmeta_signature_verified"])
        self.assertFalse(avb["candidate"]["recovery_hash_descriptor_verified"])
        self.assertTrue(avb["candidate"]["recovery_hash_descriptor_mismatch"])
        self.assertEqual(
            avb["candidate_runtime_acceptance"],
            "UNKNOWN_REQUIRES_REVIEWED_ATTENDED_T0",
        )

    def test_build_is_reproducible(self) -> None:
        second = self.root / "build-b"
        BUILDER.build(second)
        for name in EXPECTED:
            if name == "builder":
                continue
            self.assertEqual(sha256(second / name), sha256(self.output / name), name)

    def test_existing_output_and_hostile_base_mutations_stop(self) -> None:
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.build(self.output)
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.patch_prop_default(b"ro.secure=1\n")
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.patch_samsung_rc(b"on init\n")

    def test_builder_contains_no_connected_or_flash_command(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8").lower()
        for forbidden in (
            "/usr/bin/odin4",
            "/dev/bus/usb",
            "adb devices",
            "adb shell",
            "fastboot",
            "--reboot",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
