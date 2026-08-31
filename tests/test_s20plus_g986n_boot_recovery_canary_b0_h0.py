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
    "build_s20plus_g986n_boot_recovery_canary_b0_h0.py"
)
SPEC = importlib.util.spec_from_file_location(
    "s20plus_g986n_boot_recovery_canary_b0_h0_tested", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

EXPECTED = {
    "builder": "3ef1eed83bf51e2725c0da62f31378d5505f89dc064fdd8e614bbfb02f7a131c",
    "candidate/AP.tar.md5": "a8ed52d314e3b0cf5820e99ecd55e97cacdbc8a943d2181886d52d42a1c177fa",
    "candidate/boot.img": "b42ba829a4a45728951f688b7b4ef07140686ce07f111a751bba948d1d934b4c",
    "candidate/boot.img.lz4": "d06b3175dff1ebb0d9f47cc5f4e4787b6a2ee27fe2f740e2c048b586063a7f84",
    "rollback/AP.tar.md5": BUILDER.RESIDENT_AP_SHA256,
    "rollback/boot.img": BUILDER.RESIDENT_BOOT_SHA256,
    "rollback/boot.img.lz4": BUILDER.RESIDENT_BOOT_LZ4_SHA256,
    "manifest.json": "a93b8175b1d20ab3ee53ec05420259e99d8434efd2ae8673fb635d928a9c1128",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_ap(path: Path) -> tuple[list[tarfile.TarInfo], str]:
    data = path.read_bytes()
    trailer_size = len(b"0" * 32 + b"  AP.tar\n")
    trailer = data[-trailer_size:].decode("ascii")
    if not trailer.endswith("  AP.tar\n"):
        raise AssertionError("Odin trailer is malformed")
    expected_md5 = trailer[:32]
    if hashlib.md5(data[:-trailer_size]).hexdigest() != expected_md5:
        raise AssertionError("Odin trailer does not bind the tar")
    with tarfile.open(path, "r:") as archive:
        members = archive.getmembers()
    return members, expected_md5


class S20PlusG986NBootRecoveryCanaryB0H0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(
            prefix="boot-recovery-canary-b0-tests-",
            dir=BUILDER.DEFAULT_OUTPUT.parent,
        )
        cls.output = Path(cls._temporary.name) / "build-a"
        BUILDER.build(cls.output)
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

    def test_manifest_is_h0_review_pending_and_boot_only(self) -> None:
        data = self.manifest
        self.assertEqual(data["schema"], BUILDER.SCHEMA)
        self.assertEqual(data["verdict"], BUILDER.VERDICT)
        self.assertEqual(data["target"], BUILDER.TARGET)
        self.assertEqual(data["tier"], "H0")
        self.assertEqual(data["review_state"], "REVIEW_PENDING")
        self.assertFalse(data["live_authority"])
        safety = data["safety"]
        self.assertTrue(safety["host_only"])
        self.assertTrue(safety["boot_only_candidate"])
        self.assertTrue(safety["boot_only_rollback"])
        for key in (
            "device_contact",
            "recovery_partition_read",
            "recovery_partition_write",
            "recovery_partition_transfer",
            "other_partition_transfer",
            "vbmeta_payload",
            "live_authority",
            "independent_review_complete",
        ):
            self.assertFalse(safety[key], key)
        for key in ("odin_commands", "adb_commands", "su_commands"):
            self.assertEqual(safety[key], 0, key)

    def test_candidate_and_rollback_aps_are_boot_only(self) -> None:
        for branch in ("candidate", "rollback"):
            members, md5 = parse_ap(self.output / branch / "AP.tar.md5")
            self.assertEqual(len(members), 1)
            member = members[0]
            self.assertEqual(member.name, "boot.img.lz4")
            self.assertTrue(member.isreg())
            self.assertEqual(member.mode, 0o644)
            self.assertEqual(member.uid, 0)
            self.assertEqual(member.gid, 0)
            self.assertEqual(member.mtime, 0)
            self.assertEqual(self.manifest[branch]["ap_tar_md5"]["tar_md5"], md5)
            self.assertEqual(
                self.manifest[branch]["ap_tar_md5"]["members"],
                ["boot.img.lz4"],
            )

    def test_boot_carrier_uses_exact_common_components_and_canary_ramdisk(self) -> None:
        components = self.manifest["components"]
        self.assertEqual(components["exact_common"], ["header", "kernel", "dtb"])
        for name in components["exact_common"]:
            self.assertEqual(
                components["stock_boot"][name], components["recovery_canary"][name]
            )
            self.assertEqual(
                components["stock_boot"][name], components["boot_carrier"][name]
            )
        self.assertEqual(
            components["boot_carrier"]["ramdisk.cpio"],
            self.manifest["boot_carrier_safety_delta"]["ramdisk_cpio"],
        )
        self.assertNotEqual(
            components["boot_carrier"]["ramdisk.cpio"],
            components["recovery_canary"]["ramdisk.cpio"],
        )
        self.assertNotEqual(
            components["boot_carrier"]["ramdisk.cpio"],
            components["stock_boot"]["ramdisk.cpio"],
        )
        self.assertFalse(components["recovery_dtbo_in_boot_carrier"])
        self.assertEqual(
            self.manifest["candidate"]["boot_img"]["size"], BUILDER.BASE_BOOT_SIZE
        )

    def test_recovery_init_and_adb_marker_closure_are_exact(self) -> None:
        source = self.manifest["source_recovery_init"]
        self.assertEqual(source["files"], BUILDER.RECOVERY_INIT_RECEIPTS)
        self.assertTrue(source["unconditional_boot_class_start"])
        self.assertTrue(source["default_class_recovery_service"])
        self.assertTrue(source["adb_boot_trigger"])
        self.assertEqual(source["recovery_adbd_banner"], "recovery")
        self.assertEqual(source["runtime_from_boot_partition"], "UNKNOWN")
        delta = self.manifest["boot_carrier_safety_delta"]
        self.assertEqual(delta["changed_entries"], [BUILDER.RECOVERY_INIT_RC])
        self.assertEqual(delta["added_entries"], [])
        self.assertEqual(delta["removed_entries"], [])
        self.assertEqual(delta["metadata_changes"], [])
        self.assertTrue(delta["recovery_service_disabled"])
        self.assertFalse(delta["automatic_recovery_service_started"])
        self.assertTrue(delta["adbd_trigger_unchanged"])
        self.assertTrue(delta["marker_unchanged"])
        self.assertEqual(
            self.manifest["marker"],
            {
                "path": BUILDER.MARKER_PATH,
                "size": BUILDER.MARKER_SIZE,
                "sha256": BUILDER.MARKER_SHA256,
                "mode": "0444",
            },
        )

    def test_stock_avb_passes_and_custom_boot_hash_fails_explicitly(self) -> None:
        avb = self.manifest["avb"]
        self.assertTrue(avb["stock_boot"]["embedded_vbmeta_signature_verified"])
        self.assertTrue(avb["stock_boot"]["boot_hash_descriptor_verified"])
        self.assertFalse(avb["stock_boot"]["boot_hash_descriptor_mismatch"])
        self.assertTrue(avb["boot_carrier"]["embedded_vbmeta_signature_verified"])
        self.assertFalse(avb["boot_carrier"]["boot_hash_descriptor_verified"])
        self.assertTrue(avb["boot_carrier"]["boot_hash_descriptor_mismatch"])
        self.assertEqual(
            avb["runtime_acceptance"],
            "UNKNOWN_REQUIRES_REVIEWED_ATTENDED_BOOT_ONLY_F1",
        )

    def test_rollback_is_the_exact_known_good_resident_boot(self) -> None:
        rollback = self.manifest["rollback"]
        self.assertEqual(rollback["role"], "known-good-resident-magisk-boot")
        self.assertTrue(rollback["previous_live_health_recorded"])
        self.assertEqual(rollback["boot_img"]["sha256"], BUILDER.RESIDENT_BOOT_SHA256)
        self.assertEqual(
            rollback["ap_tar_md5"]["sha256"], BUILDER.RESIDENT_AP_SHA256
        )

    def test_two_complete_builds_are_byte_identical(self) -> None:
        second = Path(self._temporary.name) / "build-b"
        BUILDER.build(second)
        for name in EXPECTED:
            if name == "builder":
                continue
            self.assertEqual(sha256(second / name), sha256(self.output / name), name)

    def test_output_reuse_and_hostile_replacement_stop(self) -> None:
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.build(self.output)
        with tempfile.TemporaryDirectory(
            prefix="boot-recovery-canary-hostile-",
            dir=BUILDER.DEFAULT_OUTPUT.parent,
        ) as temporary:
            root = Path(temporary)
            source = root / "source"
            destination = root / "destination"
            source.write_bytes(b"source")
            destination.write_bytes(b"destination")
            with self.assertRaises(BUILDER.BuildError):
                BUILDER.copy_file(source, destination)
            destination.unlink()
            destination.symlink_to(source)
            with self.assertRaises(BUILDER.BuildError):
                BUILDER.replace_file(source, destination)

    def test_builder_contains_no_device_or_partition_transport(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8").lower()
        for forbidden in (
            "import subprocess",
            "/usr/bin/odin4",
            "adb devices",
            "adb shell",
            "adb reboot",
            "/dev/bus/usb",
            "/dev/block/",
            "fastboot",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
