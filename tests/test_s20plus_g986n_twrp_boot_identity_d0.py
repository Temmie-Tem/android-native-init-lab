from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_twrp_boot_identity_d0.py"
)
CONTRACT = ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
SCRIPT_DIR = SCRIPT.parent
PRIVATE_TMP = ROOT / "workspace/private/tmp"
PRIVATE_TMP.mkdir(parents=True, exist_ok=True)
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s20plus_g986n_twrp_boot_identity_d0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S20PlusTwrpBootIdentityD0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.serial = "SYNTHETIC-S20-D0"
        cls.devpath = "usb:1-2"
        cls.current_boot_id = "12345678-1234-4123-8123-123456789abc"
        cls.predecessor = {
            "terminal": {
                "path": "private-terminal",
                "size": cls.module.T2_TERMINAL_SIZE,
                "sha256": cls.module.T2_TERMINAL_SHA256,
            },
            "serial_sha256": hashlib.sha256(cls.serial.encode()).hexdigest(),
            "topology_sha256": hashlib.sha256(cls.devpath.encode()).hexdigest(),
            "boot_id_sha256": "a" * 64,
            "journal_node_count": 43,
            "host_closure_sha256": "b" * 64,
            "candidate_consumed": True,
            "t2_transfer_authority_inherited": False,
        }

    def identity_output(self, boot_id=None):
        boot_id = boot_id or self.current_boot_id
        values = {
            "boot_id": boot_id,
            **self.module.t2.h0.EXPECTED_RECOVERY_FIXED_OUTPUT,
        }
        return (
            "".join(
                f"{key}={values[key]}\n"
                for key in self.module.t2.h0.RECOVERY_OUTPUT_KEYS
            ).encode()
        )

    def metadata_output(self, **changes):
        values = {
            "boot_link": self.module.BOOT_LINK,
            "direct_path": "/dev/block/sda24",
            "rdev_major": "259",
            "rdev_minor": "8",
            "sysfs_dev": "259:8",
            "devname": "sda24",
            "devtype": "partition",
            "partname": "boot",
            "partition_number": "24",
            "sectors_512": "131072",
            "size_bytes": "67108864",
            "node_is_block": "1",
            "block_device_open_count": "0",
            "partition_content_bytes_read": "0",
        }
        values.update(changes)
        return "".join(
            f"{key}={values[key]}\n" for key in self.module.BOOT_METADATA_KEYS
        ).encode()

    def inventory_output(self, *, state="recovery", suffix=b""):
        return (
            b"List of devices attached\n"
            b"FOREIGN-DEVICE\tdevice usb:9-9 model:OTHER device:other product:other\n"
            + self.serial.encode()
            + b"\t"
            + state.encode()
            + b" usb:1-2\n"
            + suffix
        )

    def fake_command(self, *, second_identity=None, final_inventory=None):
        calls = []

        def command(argv, timeout, maximum):
            calls.append(list(argv))
            self.assertLessEqual(timeout, self.module.COMMAND_TIMEOUT_SECONDS)
            self.assertEqual(maximum, self.module.MAX_COMMAND_BYTES)
            ordinal = len(calls)
            if ordinal in (1, 7):
                return (
                    0,
                    final_inventory
                    if ordinal == 7 and final_inventory is not None
                    else self.inventory_output(),
                    b"",
                )
            if ordinal in (2, 6):
                return 0, (self.devpath + "\n").encode(), b""
            if ordinal == 3:
                return 0, self.identity_output(), b""
            if ordinal == 4:
                return 0, self.metadata_output(), b""
            if ordinal == 5:
                return 0, second_identity or self.identity_output(), b""
            raise AssertionError(f"unexpected command ordinal {ordinal}")

        return command, calls

    def test_plan_is_dormant_and_has_zero_effect_limits(self):
        plan = self.module.render_plan()
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertEqual(plan["status"], "H0_REVIEW_PENDING_NOT_ACTIVE")
        self.assertEqual(plan["target"], self.module.TARGET)
        self.assertEqual(len(plan["connected_commands"]), 7)
        self.assertFalse(plan["grants_f1"])
        self.assertFalse(plan["grants_direct_block_write"])
        for key in (
            "other_target_commands",
            "block_device_opens",
            "partition_content_bytes_read",
            "device_writes",
            "reboots",
            "mode_transitions",
            "odin_invocations",
            "partition_transfers",
        ):
            self.assertEqual(plan["limits"][key], 0, key)

    def test_dormant_connected_gate_stops_before_closure_or_command(self):
        with mock.patch.object(
            self.module,
            "validate_host_closure",
            side_effect=AssertionError("dormant gate must stop first"),
        ), mock.patch.object(
            self.module.base,
            "bounded_command",
            side_effect=AssertionError("no device command permitted"),
        ):
            with self.assertRaisesRegex(self.module.AuditError, "dormant"):
                self.module.run_connected()

    def test_activation_normalization_is_boolean_and_expected_hash_independent(self):
        baseline = self.module.normalized_self_sha256()
        source = SCRIPT.read_text(encoding="utf-8")
        mutated = source.replace(
            "ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE = False",
            "ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE = True",
        ).replace(
            self.module.EXPECTED_REVIEWED_NORMALIZED_SHA256,
            "f" * 64,
            1,
        )
        with tempfile.TemporaryDirectory(
            prefix="s20plus-boot-d0-normalized-", dir=PRIVATE_TMP
        ) as temporary:
            path = Path(temporary) / SCRIPT.name
            path.write_text(mutated, encoding="utf-8")
            with mock.patch.object(self.module, "SCRIPT", path):
                self.assertEqual(self.module.normalized_self_sha256(), baseline)

    def test_current_retained_t2_full_journal_is_revalidated(self):
        predecessor = self.module.validate_t2_predecessor()
        self.assertEqual(
            predecessor["terminal"]["sha256"], self.module.T2_TERMINAL_SHA256
        )
        self.assertEqual(predecessor["journal_node_count"], 43)
        self.assertTrue(predecessor["candidate_consumed"])
        self.assertFalse(predecessor["t2_transfer_authority_inherited"])
        for key in ("serial_sha256", "topology_sha256", "boot_id_sha256"):
            self.assertRegex(predecessor[key], r"^[0-9a-f]{64}$")

    def test_exact_boot_metadata_parses_and_binds_cross_checks(self):
        parsed = self.module.parse_boot_metadata(
            (0, self.metadata_output(), b"")
        )
        self.assertEqual(
            parsed,
            {
                "boot_link": self.module.BOOT_LINK,
                "direct_path": "/dev/block/sda24",
                "rdev_major": 259,
                "rdev_minor": 8,
                "sysfs_dev": "259:8",
                "devname": "sda24",
                "devtype": "partition",
                "partname": "boot",
                "partition_number": 24,
                "sectors_512": 131072,
                "size_bytes": 67108864,
                "node_is_block": True,
                "block_device_open_count": 0,
                "partition_content_bytes_read": 0,
            },
        )

    def test_metadata_mutations_fail_closed(self):
        mutations = {
            "link": {"boot_link": "/dev/block/by-name/recovery"},
            "path": {"direct_path": "/dev/block/../sda24"},
            "basename": {"devname": "sda25"},
            "major": {"rdev_major": "260"},
            "minor": {"rdev_minor": "9"},
            "sysfs": {"sysfs_dev": "259:9"},
            "type": {"devtype": "disk"},
            "partname": {"partname": "recovery"},
            "partition": {"partition_number": "0"},
            "sectors": {"sectors_512": "131071"},
            "size": {"size_bytes": "67108863"},
            "not-block": {"node_is_block": "0"},
            "block-open": {"block_device_open_count": "1"},
            "content": {"partition_content_bytes_read": "1"},
        }
        for name, changes in mutations.items():
            with self.subTest(name=name):
                with self.assertRaises(self.module.AuditError):
                    self.module.parse_boot_metadata(
                        (0, self.metadata_output(**changes), b"")
                    )
        with self.assertRaises(self.module.AuditError):
            self.module.parse_boot_metadata(
                (0, self.metadata_output().replace(b"partname=boot\n", b""), b"")
            )
        with self.assertRaises(self.module.AuditError):
            self.module.parse_boot_metadata(
                (0, self.metadata_output() + b"extra=value\n", b"")
            )

    def test_complete_fake_collection_targets_only_retained_serial(self):
        command, calls = self.fake_command()
        result = self.module.collect(command, predecessor=self.predecessor)
        self.assertEqual(
            result["verdict"],
            "PROVED_S20PLUS_G986N_TWRP_BOOT_IDENTITY_METADATA",
        )
        self.assertEqual(result["boot_partition"]["rdev_major"], 259)
        self.assertEqual(result["boot_partition"]["rdev_minor"], 8)
        self.assertEqual(result["partition_content_bytes_read"], 0)
        self.assertEqual(result["block_device_open_count"], 0)
        self.assertEqual(result["device_writes"], 0)
        self.assertEqual(result["selected_target_command_count"], 5)
        selected = [argv[2] for argv in calls if len(argv) >= 3 and argv[1] == "-s"]
        self.assertEqual(selected, [self.serial] * 5)
        self.assertNotIn("FOREIGN-DEVICE", " ".join(" ".join(argv) for argv in calls))

    def test_state_topology_identity_and_inventory_drift_reject(self):
        state_command, _ = self.fake_command()

        def wrong_state(argv, timeout, maximum):
            if argv[1:] == ["devices", "-l"]:
                return 0, self.inventory_output(state="device"), b""
            return state_command(argv, timeout, maximum)

        with self.assertRaisesRegex(self.module.AuditError, "recovery state"):
            self.module.collect(wrong_state, predecessor=self.predecessor)

        topology_command, _ = self.fake_command()

        def wrong_topology(argv, timeout, maximum):
            if "get-devpath" in argv:
                return 0, b"usb:1-3\n", b""
            return topology_command(argv, timeout, maximum)

        with self.assertRaisesRegex(self.module.AuditError, "retained T2"):
            self.module.collect(wrong_topology, predecessor=self.predecessor)

        changed_identity = self.identity_output(
            "22345678-1234-4123-8123-123456789abc"
        )
        identity_command, _ = self.fake_command(second_identity=changed_identity)
        with self.assertRaisesRegex(self.module.AuditError, "identity changed"):
            self.module.collect(identity_command, predecessor=self.predecessor)

        inventory_command, _ = self.fake_command(
            final_inventory=self.inventory_output(
                suffix=b"NEW-FOREIGN\tdevice usb:8-8\n"
            )
        )
        with self.assertRaisesRegex(self.module.AuditError, "inventory changed"):
            self.module.collect(inventory_command, predecessor=self.predecessor)

    def test_stderr_nonzero_oversize_and_framing_reject(self):
        exact = self.metadata_output()
        for result in (
            (1, exact, b""),
            (0, exact, b"warning"),
            (0, exact.replace(b"\n", b"\r\n"), b""),
            (0, exact + b"\n", b""),
            (True, exact, b""),
            (0, b"x" * (self.module.MAX_COMMAND_BYTES + 1), b""),
        ):
            with self.subTest(result=result[0:1]):
                with self.assertRaises(self.module.AuditError):
                    self.module.parse_boot_metadata(result)

    def test_remote_script_is_fixed_metadata_only_and_shell_parses(self):
        script = self.module.BOOT_METADATA_SCRIPT
        completed = subprocess.run(
            ["/usr/bin/dash", "-n"],
            input=script,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for required in (
            "[ -L \"$boot_link\" ]",
            "[ -b \"$direct_path\" ]",
            "/sys/dev/block/$major:$minor",
            "PARTNAME",
            '"partname=$partname"',
            '"block_device_open_count=0"',
            '"partition_content_bytes_read=0"',
        ):
            self.assertIn(required, script)
        for forbidden in (
            "dd ",
            "blockdev",
            "sha256sum",
            "cat \"$direct_path\"",
            "head ",
            "tail ",
            "> $direct_path",
            "mount ",
            "reboot",
            "twrp ",
        ):
            self.assertNotIn(forbidden, script)

    def test_exact_t2_ramdisk_contains_only_needed_command_and_boot_flag_surface(self):
        recovery = self.module.t2.h0.CANDIDATE_AP.parent / "recovery.img"
        self.assertEqual(recovery.stat().st_size, self.module.t2.h0.CANDIDATE_RECOVERY_SIZE)
        self.assertEqual(
            hashlib.sha256(recovery.read_bytes()).hexdigest(),
            self.module.t2.h0.CANDIDATE_RECOVERY_SHA256,
        )
        magiskboot = ROOT / "workspace/private/tools/magisk-v30.7/magiskboot"
        with tempfile.TemporaryDirectory(
            prefix="s20plus-t2-command-surface-", dir=PRIVATE_TMP
        ) as temporary:
            work = Path(temporary)
            subprocess.run(
                [str(magiskboot), "unpack", "-h", str(recovery)],
                cwd=work,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=30,
            )
            expected = {
                "system/bin/sh": ("regular", None),
                "system/bin/toybox": ("regular", None),
                "system/bin/cat": ("symlink", "toybox"),
                "system/bin/readlink": ("symlink", "toybox"),
                "system/bin/stat": ("symlink", "toybox"),
                "system/bin/awk": ("regular", None),
                "system/etc/twrp.flags": ("regular", None),
            }
            extracted = {}
            for index, (entry, identity) in enumerate(expected.items()):
                destination = work / f"entry-{index:02d}"
                subprocess.run(
                    [
                        str(magiskboot),
                        "cpio",
                        "ramdisk.cpio",
                        f"extract {entry} {destination}",
                    ],
                    cwd=work,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    check=True,
                    timeout=30,
                )
                extracted[entry] = destination
                if identity[0] == "regular":
                    self.assertTrue(destination.is_file(), entry)
                    self.assertFalse(destination.is_symlink(), entry)
                else:
                    self.assertTrue(destination.is_symlink(), entry)
                    self.assertEqual(os.readlink(destination), identity[1])
            flags = extracted["system/etc/twrp.flags"].read_bytes()
            self.assertEqual(flags.count(b"flashimg=1"), 1)
            self.assertIn(
                b"/boot               emmc         "
                b"/dev/block/bootdevice/by-name/boot",
                flags,
            )

    def test_indirect_or_hardlinked_host_closure_rejects(self):
        with tempfile.TemporaryDirectory(
            prefix="s20plus-boot-d0-files-", dir=PRIVATE_TMP
        ) as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"
            link = root / "link"
            first.write_bytes(b"x")
            os.link(first, second)
            link.symlink_to(first)
            for path in (first, link):
                with self.assertRaises(self.module.AuditError):
                    self.module.read_exact_regular(
                        path,
                        expected_size=1,
                        expected_sha256=hashlib.sha256(b"x").hexdigest(),
                        maximum=1,
                        label="hostile",
                    )

    def test_private_publication_is_no_clobber_and_failure_is_zero_effect(self):
        with tempfile.TemporaryDirectory(
            prefix="s20plus-boot-d0-run-", dir=PRIVATE_TMP
        ) as temporary:
            root = Path(temporary)
            path = root / "result.json"
            value = {"schema": "test", "exact": True}
            self.module.durable_json(path, value)
            self.assertEqual(json.loads(path.read_text()), value)
            with self.assertRaises(FileExistsError):
                self.module.durable_json(path, value)
        failure = self.module.failure_result(None, self.module.AuditError("fixed"))
        for key in (
            "host_command_count",
            "device_writes",
            "block_device_open_count",
            "partition_content_bytes_read",
            "reboots",
            "odin_invocations",
            "partition_transfers",
        ):
            self.assertEqual(failure[key], 0, key)

    def test_cli_has_no_caller_target_or_command_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            'add_argument("--serial"',
            'add_argument("--path"',
            'add_argument("--command"',
            'add_argument("--shell"',
            'add_argument("--output"',
            'add_argument("--run-id"',
            'add_argument("--approval"',
        ):
            self.assertNotIn(forbidden, source)
        with mock.patch.object(
            self.module,
            "run_connected",
            side_effect=AssertionError("invalid CLI must not run"),
        ):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.module.main([])

    def test_target_contract_matches_the_exact_d0_activation_state(self):
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("## TWRP boot-identity metadata D0", contract)
        self.assertIn(SCRIPT.name, contract)
        self.assertIn(self.module.EXPECTED_REVIEWED_NORMALIZED_SHA256, contract)
        self.assertIn(
            "block-device opens, partition-content bytes, writes, reboots, "
            "mode transitions, Odin invocations, and transfers are all zero",
            contract,
        )
        section = contract.split(
            "## TWRP boot-identity metadata D0", 1
        )[1].split("\n## ", 1)[0]
        if self.module.ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE:
            self.assertIn(
                "Status: **BINDING - ATTENDED TWRP BOOT-IDENTITY D0 ACTIVE**",
                section,
            )
            self.assertNotIn("Status: **DEFINED - NOT ACTIVE**", section)
        else:
            self.assertIn("Status: **DEFINED - NOT ACTIVE**", section)
            self.assertNotIn(
                "BINDING - ATTENDED TWRP BOOT-IDENTITY D0 ACTIVE", section
            )


if __name__ == "__main__":
    unittest.main()
