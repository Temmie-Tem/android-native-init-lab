from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "build_s20plus_n3u0_magisk_overlay.py"
)
SOURCE = ROOT / "workspace/public/src/native-init/s20plus_n3u0_acm_witness.c"
RC = ROOT / "workspace/public/src/android/s20plus_n3u0_acm.rc"
REPORT = ROOT / "docs/reports/S20PLUS_G986N_N3U0_ACM_HOST_BUILD_H0_2026-08-16.md"
DESIGN = ROOT / "docs/plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md"
GOAL = ROOT / "GOAL_S20PLUS.md"
SCRIPT_DIR = SCRIPT.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("s20plus_n3u0_builder_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

EXPECTED = {
    "source": "cb6b71b08575658edc22bb00472ee13eaa8198543ad393ef6e4ad6efb22ef2f1",
    "rc": "bbaab9cc2829119d5a90775456eb0935b0890b1a3ce0e418afc847cc346385ad",
    "builder": "93af2c760acd7d4f33a992fe68cb0346485aa675490aed6c43b993f1f09dcce2",
    "s20plus_n3u0_acm": "a0d90dbba2fe6f85af2421f888ecdfd76ecf22420b03846260ecab708de4810d",
    "boot.img": "7024d206453dbd82f04187b7a3ccb6042aef7e2e20ed9660a67b47ecf19206eb",
    "boot.img.lz4": "ee57ba63c557bca651fd633f77d6f006585ec0d5b22bb18418a6fade3590809d",
    "AP.tar.md5": "3aad497979cfa0f247aef68f50ea792f40127afa037c134eeb0d2e96798ca7af",
    "manifest.json": "594b83dfc52f37e1db21ab5f240b804ad10a8eb1d0642719aef0ecd5ddfc619f",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class S20PlusN3U0MagiskOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory(prefix="s20plus-n3u0-tests-")
        cls.root = Path(cls._temp.name)
        cls.output = cls.root / "output"
        cls.result = BUILDER.build(cls.output)
        cls.manifest = json.loads(
            (cls.output / "manifest.json").read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def test_frozen_sources_and_outputs_match(self) -> None:
        self.assertEqual(sha256(SOURCE), EXPECTED["source"])
        self.assertEqual(sha256(RC), EXPECTED["rc"])
        self.assertEqual(sha256(SCRIPT), EXPECTED["builder"])
        for name in (
            "s20plus_n3u0_acm",
            "boot.img",
            "boot.img.lz4",
            "AP.tar.md5",
            "manifest.json",
        ):
            self.assertEqual(sha256(self.output / name), EXPECTED[name], name)

    def test_manifest_is_h0_review_pending_and_reproducible(self) -> None:
        data = self.manifest
        self.assertEqual(data["schema"], BUILDER.SCHEMA)
        self.assertEqual(data["verdict"], BUILDER.VERDICT)
        self.assertEqual(data["tier"], "H0")
        self.assertEqual(data["review_state"], "REVIEW_PENDING")
        self.assertFalse(data["live_authority"])
        self.assertEqual(data["target"], BUILDER.TARGET)
        self.assertEqual(
            data["ramdisk"]["added_entries"], list(BUILDER.ADDED_ENTRIES)
        )
        self.assertEqual(data["ramdisk"]["replaced_entries"], [])
        self.assertTrue(data["reproducibility"]["two_witness_builds_byte_identical"])
        self.assertTrue(
            data["reproducibility"]["two_complete_artifact_builds_byte_identical"]
        )
        self.assertTrue(data["safety"]["base_nochange_repack_byte_identical"])
        self.assertTrue(data["safety"]["one_rc_plus_one_binary"])
        for key in (
            "live_authority",
            "adb_commands",
            "su_commands",
            "reboot_commands",
            "odin_commands",
            "partition_transfers",
        ):
            self.assertIn(key, data)
            self.assertIn(data[key], (False, 0))
        for key in (
            "mode_peripheral_write",
            "module_insertions",
            "network_functions",
            "storage_functions",
            "pid1_replacement",
            "persistent_promotion",
            "odin_invoked",
            "device_contact",
        ):
            self.assertFalse(data["safety"][key], key)

    def test_boot_only_ap_has_one_regular_member_and_valid_md5(self) -> None:
        path = self.output / "AP.tar.md5"
        data = path.read_bytes()
        trailer_start = len(data) - len(b"0" * 32 + b"  AP.tar\n")
        trailer = data[trailer_start:]
        self.assertRegex(trailer.decode("ascii"), r"^[0-9a-f]{32}  AP\.tar\n$")
        expected_md5 = trailer.split(b" ", 1)[0].decode("ascii")
        self.assertEqual(hashlib.md5(data[:trailer_start]).hexdigest(), expected_md5)
        with tarfile.open(path, "r:") as archive:
            members = archive.getmembers()
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].name, "boot.img.lz4")
        self.assertTrue(members[0].isreg())

    def test_repacked_boot_preserves_base_and_adds_only_two_entries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-n3u0-unpack-") as temp:
            work = Path(temp)
            subprocess.run(
                [str(BUILDER.MAGISKBOOT), "unpack", "-h", str(self.output / "boot.img")],
                cwd=work,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=30,
            )
            listing = subprocess.run(
                [
                    str(BUILDER.MAGISKBOOT),
                    "cpio",
                    "ramdisk.cpio",
                    "ls -r /",
                ],
                cwd=work,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=30,
            ).stdout
            parsed = BUILDER.parse_cpio_listing(listing)
            for entry, mode in BUILDER.ENTRY_MODES.items():
                self.assertEqual(parsed[entry], mode)
            subprocess.run(
                [
                    str(BUILDER.MAGISKBOOT),
                    "cpio",
                    "ramdisk.cpio",
                    "extract init init.extracted",
                ],
                cwd=work,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=30,
            )
            self.assertEqual(sha256(work / "init.extracted"), BUILDER.BASE_INIT_SHA256)
            self.assertEqual(sha256(work / "kernel"), BUILDER.BASE_KERNEL_SHA256)
            self.assertEqual(sha256(work / "dtb"), BUILDER.BASE_DTB_SHA256)

    def test_witness_is_static_closed_and_uses_owned_dynamic_port(self) -> None:
        binary = self.output / "s20plus_n3u0_acm"
        described = subprocess.run(
            ["file", str(binary)], text=True, capture_output=True, check=True
        ).stdout
        readelf = subprocess.run(
            ["aarch64-linux-gnu-readelf", "-W", "-l", "-d", str(binary)],
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        undefined = subprocess.run(
            ["aarch64-linux-gnu-nm", "-u", str(binary)],
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        strings = subprocess.run(
            ["strings", "-a", str(binary)], text=True, capture_output=True, check=True
        ).stdout
        self.assertIn("ARM aarch64", described)
        self.assertIn("statically linked", described)
        self.assertNotIn("INTERP", readelf)
        self.assertNotIn("NEEDED", readelf)
        self.assertIn(undefined.strip(), ("", f"{binary}: no symbols"))
        for token in (
            "S20PLUS_N3U0_ACM_WITNESS_V1",
            "S20PLUS_N3U0_ACM_V1",
            "a600000.dwc3",
            "/config/usb_gadget/s20plus_n3u0",
            "/functions/acm.usb0/port_num",
            "/dev/ttyGS%d",
        ):
            self.assertIn(token, strings)
        for token in (
            "/dev/ttyGS0",
            "/dev/block",
            "/data/adb",
            "mass_storage",
            "rndis",
            "ffs.adb",
            "peripheral",
        ):
            self.assertNotIn(token, strings)

    def test_all_fault_routes_cleanup_and_restore_after_unbind(self) -> None:
        state = BUILDER.host_selftest()
        self.assertEqual(state["fault_routes"], 7)
        self.assertTrue(state["cleanup_after_owned_touch"])
        self.assertTrue(state["stock_restore_after_unbind"])

    def test_rc_is_late_one_shot_magisk_service(self) -> None:
        text = RC.read_text(encoding="ascii")
        for token in (
            "on property:sys.boot_completed=1",
            "service s20plus_n3u0_acm ${MAGISKTMP}/s20plus_n3u0_acm",
            "class late_start",
            "disabled",
            "oneshot",
            "seclabel u:r:magisk:s0",
        ):
            self.assertIn(token, text)
        for token in ("early-init", "critical", "setprop", "write /", "reboot"):
            self.assertNotIn(token, text)

    def test_hostile_contract_mutations_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-n3u0-hostile-") as temp:
            root = Path(temp)
            bad_rc = root / "bad.rc"
            bad_rc.write_text(
                RC.read_text(encoding="ascii").replace("    seclabel u:r:magisk:s0\n", ""),
                encoding="ascii",
            )
            bad_source = root / "bad.c"
            bad_source.write_text(
                SOURCE.read_text(encoding="ascii") + '\nconst char *bad = "/mode";\n',
                encoding="ascii",
            )
            with mock.patch.object(BUILDER, "RC_SOURCE", bad_rc):
                with self.assertRaises(BUILDER.BuildError):
                    BUILDER.source_contract()
            with mock.patch.object(BUILDER, "SOURCE", bad_source):
                with self.assertRaises(BUILDER.BuildError):
                    BUILDER.source_contract()

    def test_wrong_base_and_existing_output_fail_before_materialization(self) -> None:
        with tempfile.TemporaryDirectory(prefix="s20plus-n3u0-wrong-base-") as temp:
            root = Path(temp)
            wrong = root / "boot.img"
            wrong.write_bytes(b"ANDROID!wrong")
            with mock.patch.object(BUILDER, "BASE_BOOT", wrong):
                with self.assertRaises(BUILDER.BuildError):
                    BUILDER.build(root / "output")
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.build(self.output)

    def test_builder_has_no_device_or_live_execution_surface(self) -> None:
        text = SCRIPT.read_text(encoding="ascii")
        for token in (
            '"review_state": "REVIEW_PENDING"',
            '"live_authority": False',
            '"device_contact": False',
            '"odin_invoked": False',
            '"device_commands": 0',
            '"adb_commands": 0',
            '"su_commands": 0',
        ):
            self.assertIn(token, text)
        for token in (
            'subprocess.run(["adb"',
            'subprocess.run(["odin4"',
            "fastboot flash",
            "heimdall flash",
            "dd of=/dev/block",
        ):
            self.assertNotIn(token, text)

    def test_public_docs_keep_the_build_review_pending_and_port_dynamic(self) -> None:
        report = REPORT.read_text(encoding="utf-8")
        design = DESIGN.read_text(encoding="utf-8")
        goal = GOAL.read_text(encoding="utf-8")
        for text in (report, design, goal):
            self.assertIn("REVIEW_PENDING", text)
            self.assertIn("port_num", text)
            self.assertNotIn("N3-U0 ACTIVE", text)
        for text in (design, goal):
            self.assertIn("S20PLUS_G986N_N3U0_ACM_HOST_BUILD_H0_2026-08-16.md", text)
        self.assertIn(EXPECTED["source"], report)
        self.assertIn(EXPECTED["builder"], report)
        self.assertIn(EXPECTED["boot.img"], report)
        self.assertIn(sha256(Path(__file__)), report)
        self.assertIn("no connected run or live boot authority", design)
        self.assertIn("no connected observer", goal)


if __name__ == "__main__":
    unittest.main()
