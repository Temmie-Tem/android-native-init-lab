from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "build_s20plus_g986n_p0_pid1_acm_h0.py"
)
SOURCE = ROOT / "workspace/public/src/native-init/s20plus_p0_pid1_acm_init.c"
SCRIPT_DIR = SCRIPT.parent
PRIVATE_TMP = ROOT / "workspace/private/tmp"
PRIVATE_TMP.mkdir(parents=True, exist_ok=True)
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("s20plus_p0_builder_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class S20PlusP0Pid1AcmH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp = tempfile.TemporaryDirectory(
            prefix="s20plus-p0-tests-", dir=PRIVATE_TMP
        )
        cls.root = Path(cls._temp.name)
        cls.output = cls.root / "output"
        cls.result = BUILDER.build(cls.output)
        cls.manifest = json.loads(
            (cls.output / "manifest.json").read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls):
        cls._temp.cleanup()

    def test_manifest_is_h0_review_pending_and_not_live(self):
        data = self.manifest
        self.assertEqual(data["schema"], BUILDER.SCHEMA)
        self.assertEqual(data["verdict"], BUILDER.VERDICT)
        self.assertEqual(data["tier"], "H0")
        self.assertEqual(data["review_state"], "REVIEW_PENDING")
        self.assertFalse(data["live_authority"])
        self.assertEqual(data["target"], BUILDER.TARGET)
        self.assertEqual(data["ramdisk"]["replaced_entries"], ["init"])
        self.assertEqual(data["ramdisk"]["added_entries"], [])
        self.assertEqual(data["ramdisk"]["removed_entries"], [])
        self.assertTrue(data["ramdisk"]["logical_regular_entries_exact"])
        self.assertNotIn("init", data["ramdisk"]["retained_regular_entries"])
        self.assertTrue(data["reproducibility"]["two_init_builds_byte_identical"])
        self.assertTrue(
            data["reproducibility"]["two_complete_artifact_builds_byte_identical"]
        )
        self.assertIn("objdump", data["tools"])
        for key in (
            "device_commands",
            "adb_commands",
            "su_commands",
            "reboot_commands",
            "odin_commands",
            "partition_transfers",
        ):
            self.assertEqual(data[key], 0, key)
        for key in (
            "android_started",
            "magisk_started",
            "persistent_partition_mount",
            "persistent_write",
            "block_device_access",
            "module_insertion",
            "network_function",
            "storage_function",
            "mode_peripheral_write",
            "reboot_syscall",
            "odin_invoked",
            "device_contact",
        ):
            self.assertFalse(data["safety"][key], key)

    def test_result_receipts_match_all_published_bytes(self):
        for name in BUILDER.PUBLISHED_FILES:
            expected = self.manifest["outputs"][name]
            path = self.output / name
            self.assertEqual(path.stat().st_size, expected["size"])
            self.assertEqual(sha256(path), expected["sha256"])
        self.assertEqual(
            self.result["manifest"]["sha256"], sha256(self.output / "manifest.json")
        )
        self.assertEqual(
            self.manifest["sources"]["init"]["sha256"], sha256(SOURCE)
        )
        self.assertEqual(
            self.manifest["sources"]["builder"]["sha256"], sha256(SCRIPT)
        )

    def test_boot_only_ap_has_one_regular_member_and_valid_md5(self):
        path = self.output / "AP.tar.md5"
        data = path.read_bytes()
        trailer_size = len(b"0" * 32 + b"  AP.tar\n")
        tar_bytes = data[:-trailer_size]
        trailer = data[-trailer_size:]
        self.assertRegex(trailer.decode("ascii"), r"^[0-9a-f]{32}  AP\.tar\n$")
        self.assertEqual(
            hashlib.md5(tar_bytes).hexdigest(),
            trailer.split(b" ", 1)[0].decode("ascii"),
        )
        with tarfile.open(path, "r:") as archive:
            members = archive.getmembers()
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].name, "boot.img.lz4")
        self.assertTrue(members[0].isreg())

    def test_repacked_boot_preserves_substrate_and_replaces_only_init(self):
        with tempfile.TemporaryDirectory(
            prefix="s20plus-p0-unpack-", dir=PRIVATE_TMP
        ) as temporary:
            root = Path(temporary)
            candidate = root / "candidate"
            base = root / "base"
            candidate.mkdir()
            base.mkdir()
            for directory, image in (
                (candidate, self.output / "boot.img"),
                (base, BUILDER.BASE_BOOT),
            ):
                subprocess.run(
                    [str(BUILDER.MAGISKBOOT), "unpack", "-h", str(image)],
                    cwd=directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=True,
                    timeout=30,
                )
            listings = []
            for directory in (candidate, base):
                listing = subprocess.run(
                    [str(BUILDER.MAGISKBOOT), "cpio", "ramdisk.cpio", "ls -r /"],
                    cwd=directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=True,
                    timeout=30,
                ).stdout
                listings.append(BUILDER.n3.parse_cpio_listing(listing))
            self.assertEqual(listings[0], listings[1])
            for index, (entry, mode) in enumerate(sorted(listings[0].items())):
                if not mode.startswith("-") or entry == "init":
                    continue
                extracted = []
                for label, directory in (("candidate", candidate), ("base", base)):
                    destination = root / f"logical-{label}-{index:03d}"
                    subprocess.run(
                        [
                            str(BUILDER.MAGISKBOOT),
                            "cpio",
                            "ramdisk.cpio",
                            f"extract {entry} {destination}",
                        ],
                        cwd=directory,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        check=True,
                        timeout=30,
                    )
                    os.chmod(destination, 0o600, follow_symlinks=False)
                    extracted.append(destination.read_bytes())
                self.assertEqual(extracted[0], extracted[1], entry)
            for directory, destination in (
                (candidate, "init.candidate"),
                (base, "init.base"),
            ):
                subprocess.run(
                    [
                        str(BUILDER.MAGISKBOOT),
                        "cpio",
                        "ramdisk.cpio",
                        f"extract init {root / destination}",
                    ],
                    cwd=directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=True,
                    timeout=30,
                )
            self.assertEqual(
                (root / "init.candidate").read_bytes(),
                (self.output / "s20plus_p0_pid1_init").read_bytes(),
            )
            self.assertEqual(sha256(root / "init.base"), BUILDER.BASE_INIT_SHA256)
            for name in ("kernel", "dtb", "header"):
                self.assertEqual(
                    (candidate / name).read_bytes(),
                    (base / name).read_bytes(),
                    name,
                )

    def test_init_is_static_small_closed_and_first_syscall_is_getpid(self):
        binary = self.output / "s20plus_p0_pid1_init"
        described = subprocess.run(
            ["file", str(binary)], text=True, capture_output=True, check=True
        ).stdout
        readelf = subprocess.run(
            ["aarch64-linux-gnu-readelf", "-W", "-l", "-d", str(binary)],
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        elf_header = subprocess.run(
            ["aarch64-linux-gnu-readelf", "-h", str(binary)],
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
        disassembly = subprocess.run(
            [str(BUILDER.OBJDUMP), "-d", str(binary)],
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        strings = subprocess.run(
            ["strings", "-a", str(binary)],
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        self.assertIn("ARM aarch64", described)
        self.assertIn("statically linked", described)
        self.assertNotIn("INTERP", readelf)
        self.assertNotIn("NEEDED", readelf)
        self.assertIn(undefined.strip(), ("", f"{binary}: no symbols"))
        entry_match = re.search(
            r"Entry point address:\s+0x([0-9a-f]+)", elf_header
        )
        self.assertIsNotNone(entry_match)
        entry = int(entry_match.group(1), 16)
        entry_disassembly = subprocess.run(
            [
                str(BUILDER.OBJDUMP),
                "-d",
                f"--start-address={entry}",
                f"--stop-address={entry + 64}",
                str(binary),
            ],
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        first_svc = entry_disassembly.find("svc")
        self.assertGreater(first_svc, 0)
        self.assertIn("x8, #0xac", entry_disassembly[:first_svc])
        self.assertNotIn("svc", entry_disassembly[:first_svc])
        self.assertLessEqual(binary.stat().st_size, 16 * 1024)
        for token in (
            "S20PLUS_P0_PID1_ACM_V1;pid=00000001;stage=ACM_READY",
            "S20Plus-P0-PID1",
            "a600000.dwc3",
            "/config/usb_gadget/s20plus_p0",
            "/functions/acm.usb0/port_num",
        ):
            self.assertIn(token, strings)
        for token in (
            "/data/",
            "/metadata",
            "/dev/block",
            "/system/",
            "peripheral",
            "mass_storage",
            "ffs.adb",
        ):
            self.assertNotIn(token, strings)

    def test_source_contract_rejects_persistent_or_wrong_pid1_flow(self):
        with tempfile.TemporaryDirectory(
            prefix="s20plus-p0-hostile-", dir=PRIVATE_TMP
        ) as temporary:
            root = Path(temporary)
            for name, mutation in (
                ("persistent", '\nconst char *bad = "/data/bad";\n'),
                (
                    "pid-gate",
                    SOURCE.read_text(encoding="ascii").replace(
                        "if (pid != 1)", "if (pid != 2)"
                    ),
                ),
            ):
                bad = root / f"{name}.c"
                if name == "persistent":
                    bad.write_text(
                        SOURCE.read_text(encoding="ascii") + mutation,
                        encoding="ascii",
                    )
                else:
                    bad.write_text(mutation, encoding="ascii")
                with mock.patch.object(BUILDER, "SOURCE", bad):
                    with self.assertRaises(BUILDER.BuildError):
                        BUILDER.source_contract()

    def test_wrong_base_existing_output_and_indirect_output_reject(self):
        with tempfile.TemporaryDirectory(
            prefix="s20plus-p0-wrong-", dir=PRIVATE_TMP
        ) as temporary:
            root = Path(temporary)
            wrong = root / "boot.img"
            wrong.write_bytes(b"ANDROID!wrong")
            with mock.patch.object(BUILDER, "BASE_BOOT", wrong):
                with self.assertRaises((BUILDER.BuildError, BUILDER.n3.BuildError)):
                    BUILDER.build(root / "output")
            link = root / "link"
            link.symlink_to(root / "missing")
            with self.assertRaises(BUILDER.BuildError):
                BUILDER.build(link)
        with self.assertRaises(BUILDER.BuildError):
            BUILDER.build(self.output)

    def test_builder_has_no_connected_execution_surface(self):
        text = SCRIPT.read_text(encoding="ascii")
        for token in (
            '"review_state": "REVIEW_PENDING"',
            '"live_authority": False',
            '"device_contact": False',
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


if __name__ == "__main__":
    unittest.main()
