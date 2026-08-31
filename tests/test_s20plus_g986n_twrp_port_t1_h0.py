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
    "build_s20plus_g986n_twrp_port_t1_h0.py"
)
SPEC = importlib.util.spec_from_file_location(
    "s20plus_g986n_twrp_port_t1_h0_tested", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

EXPECTED = {
    "builder": "300bd7f136dcb952db6ce7b1da2d4ce7ae382734b9f566f92e9ab6397f2aa3e7",
    "candidate/AP.tar.md5": "3ed8498243ff09399ffd93fa3b0e90044a3cfe1709b7204dac53fe190647260f",
    "candidate/recovery.img": "48406883b1f631c4dfa1b157708f2e320e70b744967024bad6cb50b08cd06cb2",
    "candidate/recovery.img.lz4": "f4ccd3fbcd683b5597cf20b028b1230cfb0dd8f4f3c93d3db27c5314834ace7a",
    "rollback/AP.tar.md5": "ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157",
    "rollback/recovery.img": BUILDER.t0.BASE_RECOVERY_SHA256,
    "rollback/recovery.img.lz4": BUILDER.t0.BASE_RECOVERY_LZ4_SHA256,
    "manifest.json": "c5901e75a81997c9ab7b7b964710c166c7a9650dfee8fcf92de637269ac19019",
}


def sha256(path: Path) -> str:
    return BUILDER.t0.sha256_file(path)


def parse_ap(path: Path) -> list[tarfile.TarInfo]:
    data = path.read_bytes()
    trailer_length = len(b"0" * 32 + b"  AP.tar\n")
    trailer = data[-trailer_length:]
    expected_md5 = trailer[:32].decode("ascii")
    if trailer[32:] != b"  AP.tar\n":
        raise AssertionError("invalid AP trailer")
    if hashlib.md5(data[:-trailer_length]).hexdigest() != expected_md5:
        raise AssertionError("AP MD5 mismatch")
    with tarfile.open(path, "r:") as archive:
        return archive.getmembers()


class S20PlusTwrpPortT1H0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        private_test_root = ROOT / "workspace/private/runs/tests"
        private_test_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        cls._temporary = tempfile.TemporaryDirectory(
            prefix="s20plus-twrp-port-t1-tests-", dir=private_test_root
        )
        cls.root = Path(cls._temporary.name)
        cls.output = cls.root / "build-a"
        cls.result = BUILDER.build(cls.output)
        cls.manifest = json.loads(
            (cls.output / "manifest.json").read_text(encoding="utf-8")
        )
        cls.unpack = cls.root / "candidate-unpack"
        BUILDER.t0.unpack_recovery(
            cls.output / "candidate/recovery.img", cls.unpack
        )
        cls.tree = cls.root / "candidate-tree"
        BUILDER.t0.extract_cpio_tree(cls.unpack / "ramdisk.cpio", cls.tree)

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
        self.assertEqual(data["twrp_version"], BUILDER.TWRP_VERSION)
        self.assertEqual(data["source_claim"], BUILDER.SOURCE_CLAIM)
        self.assertEqual(data["tier"], "H0")
        self.assertEqual(data["review_state"], "REVIEW_PENDING")
        self.assertFalse(data["live_authority"])
        for key in (
            "device_contact",
            "live_flash_authorized",
            "policy_amendment_complete",
            "independent_review_complete",
            "t0_runtime_passed",
            "vbmeta_payload",
            "vendor_write",
            "efs_write",
            "persist_write",
            "data_write",
            "misc_write_during_build",
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

    def test_port_uses_only_donor_ramdisk_on_exact_stock_substrate(self) -> None:
        data = self.manifest
        self.assertEqual(data["donor_components"], BUILDER.DONOR_COMPONENTS)
        self.assertEqual(
            data["substrate"]["donor_components_used"], ["ramdisk.cpio"]
        )
        for name in ("header", "kernel", "dtb", "recovery_dtbo"):
            self.assertEqual(
                data["port_components"][name],
                data["substrate"]["components"][name],
            )
            self.assertNotEqual(
                data["port_components"][name], data["donor_components"][name]
            )
        self.assertNotEqual(
            data["port_components"]["ramdisk.cpio"],
            data["substrate"]["components"]["ramdisk.cpio"],
        )
        self.assertEqual(
            data["candidate"]["recovery_img"]["size"],
            BUILDER.t0.BASE_RECOVERY_SIZE,
        )

    def test_ramdisk_delta_is_four_replacements_and_one_marker(self) -> None:
        ramdisk = self.manifest["ramdisk"]
        self.assertEqual(ramdisk["donor_entry_count"], 3_685)
        self.assertEqual(ramdisk["port_entry_count"], 3_686)
        self.assertEqual(ramdisk["added_entries"], [BUILDER.MARKER_ENTRY])
        self.assertEqual(ramdisk["removed_entries"], [])
        self.assertEqual(
            ramdisk["changed_entries"], sorted(BUILDER.CHANGED_ENTRIES)
        )
        self.assertTrue(ramdisk["all_other_entries_byte_and_mode_identical"])

    def test_automatic_persistent_mutations_are_neutralized(self) -> None:
        qcom = (self.tree / BUILDER.QCOM_RC).read_bytes()
        post = (self.tree / BUILDER.POST_HOOK).read_bytes()
        self.assertEqual(post, BUILDER.POST_HOOK_INERT)
        for forbidden in (
            b"/mnt/vendor/persist rw",
            b"/mnt/vendor/efs rw",
            b"mkdir /data/vendor/keymaster",
            b"start keymaster-sb-4-0",
            b"start spdaemon",
            b"start sec_nvm",
            b"recovery-from-boot.p",
            b"install-recovery.sh",
        ):
            self.assertNotIn(forbidden, qcom + post, forbidden)
        for required in (
            b"/mnt/vendor/persist ro nosuid nodev noexec noload",
            b"/mnt/vendor/efs ro nosuid nodev noexec noload",
            b"/vendor/firmware_mnt ro nosuid nodev noexec",
            b"start health-hal-2-1",
        ):
            self.assertIn(required, qcom)

    def test_first_boot_usb_is_adb_only(self) -> None:
        usb = (self.tree / BUILDER.USB_RC).read_bytes()
        BUILDER.validate_safe_usb_rc(usb)
        self.assertEqual(usb, BUILDER.SAFE_USB_RC)
        for forbidden in (
            b"functions/ffs.mtp",
            b"functions/ffs.fastboot",
            b"mount functionfs mtp",
            b"mount functionfs fastboot",
            b"start fastbootd",
        ):
            self.assertNotIn(forbidden, usb)
        self.assertEqual(self.manifest["ramdisk"]["usb_functions"], ["adb"])
        self.assertFalse(self.manifest["ramdisk"]["mtp_enabled"])
        self.assertFalse(self.manifest["ramdisk"]["fastbootd_enabled"])

    def test_twrp_ui_exposes_only_boot_image_flash(self) -> None:
        flags = (self.tree / BUILDER.TWRP_FLAGS).read_bytes()
        BUILDER.validate_safe_flags(flags)
        self.assertEqual(flags, BUILDER.SAFE_TWRP_FLAGS)
        self.assertEqual(flags.count(b"flashimg=1"), 1)
        self.assertIn(b"/boot ", flags)
        for token in BUILDER.FORBIDDEN_UI_TOKENS:
            self.assertNotIn(token, flags)

    def test_twrp_userland_and_a90_identical_reboot_hook_are_preserved(self) -> None:
        recovery = self.tree / BUILDER.RECOVERY_BINARY
        twrp = self.tree / BUILDER.TWRP_CLI
        reboot_hook = self.tree / BUILDER.REBOOT_HOOK
        self.assertEqual(
            sha256(recovery), BUILDER.DONOR_ENTRY_SHA256[BUILDER.RECOVERY_BINARY]
        )
        self.assertEqual(
            sha256(twrp), BUILDER.DONOR_ENTRY_SHA256[BUILDER.TWRP_CLI]
        )
        self.assertIn(BUILDER.TWRP_VERSION.encode("ascii"), recovery.read_bytes())
        self.assertEqual(reboot_hook.stat().st_size, 89)
        self.assertEqual(
            sha256(reboot_hook), BUILDER.DONOR_ENTRY_SHA256[BUILDER.REBOOT_HOOK]
        )
        self.assertFalse(
            self.manifest["ramdisk"]["rebootsystem_hook"][
                "s20plus_live_exception"
            ]
        )

    def test_marker_and_recovery_fstab_are_exact(self) -> None:
        self.assertEqual((self.tree / BUILDER.MARKER_ENTRY).read_bytes(), BUILDER.MARKER)
        self.assertEqual(
            sha256(self.tree / BUILDER.RECOVERY_FSTAB),
            BUILDER.DONOR_ENTRY_SHA256[BUILDER.RECOVERY_FSTAB],
        )
        fstab = (self.tree / BUILDER.RECOVERY_FSTAB).read_text(encoding="utf-8")
        for partition in ("system", "vendor", "product", "odm"):
            self.assertIn(f"{partition}", fstab)
        self.assertIn("/data", fstab)

    def test_candidate_and_rollback_ap_are_recovery_only(self) -> None:
        for branch in ("candidate", "rollback"):
            members = parse_ap(self.output / branch / "AP.tar.md5")
            self.assertEqual(len(members), 1)
            self.assertEqual(members[0].name, "recovery.img.lz4")
            self.assertTrue(members[0].isreg())
            self.assertEqual(
                self.manifest[branch]["ap_tar_md5"]["members"],
                ["recovery.img.lz4"],
            )

    def test_stock_avb_passes_and_port_hash_failure_is_explicit(self) -> None:
        avb = self.manifest["avb"]
        self.assertTrue(avb["stock"]["recovery_hash_descriptor_verified"])
        self.assertTrue(avb["candidate"]["embedded_vbmeta_signature_verified"])
        self.assertFalse(avb["candidate"]["recovery_hash_descriptor_verified"])
        self.assertTrue(avb["candidate"]["recovery_hash_descriptor_mismatch"])
        self.assertEqual(
            avb["candidate_runtime_acceptance"], "UNKNOWN_REQUIRES_T0_FIRST"
        )

    def test_two_complete_builds_are_byte_identical(self) -> None:
        second = self.root / "build-b"
        BUILDER.build(second)
        for name in EXPECTED:
            if name == "builder":
                continue
            self.assertEqual(sha256(second / name), sha256(self.output / name), name)

    def test_hostile_inputs_and_output_reuse_stop(self) -> None:
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.build(self.output)
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.sanitize_qcom_rc(b"on fs\n")
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.validate_safe_flags(BUILDER.SAFE_TWRP_FLAGS + b"/vbmeta\n")
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.validate_safe_usb_rc(BUILDER.SAFE_USB_RC + b"start fastbootd\n")

    def test_builder_has_no_connected_or_flash_invocation(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8").lower()
        for forbidden in (
            "/usr/bin/odin4",
            "/dev/bus/usb",
            "adb devices",
            "adb shell",
            "fastboot devices",
            "--reboot",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
