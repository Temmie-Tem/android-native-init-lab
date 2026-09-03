import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s20plus_g986n_fastboot_getvar_census.py"

import sys

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("s20plus_fastboot_census", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
REAL_REQUIRE_PREDECESSOR = MODULE.require_zero_query_predecessor


class S20PlusFastbootGetvarCensusTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(
            MODULE,
            "require_zero_query_predecessor",
            return_value={
                "ordinal": 1,
                "entry_sha256": MODULE.PREDECESSOR_ENTRY_SHA256,
                "terminal_sha256": MODULE.PREDECESSOR_FINAL_SHA256,
                "run_dir_sha256": "f" * 64,
                "verdict": MODULE.FINAL_NO_PROOF,
                "fastboot_query_intent_count": 0,
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def inventory(self, include_s20=True):
        rows = ["List of devices attached"]
        if include_s20:
            rows.append(
                "S20SERIAL device product:y2qksx model:SM_G986N "
                "device:y2q transport_id:1"
            )
        rows.extend(
            (
                "S22SERIAL device product:g0qksx model:SM_S906N "
                "device:g0q transport_id:2",
                "A90SERIAL device product:a90 model:SM_A908N "
                "device:a90q transport_id:3",
            )
        )
        return "\n".join(rows) + "\n"

    def snapshot(self, boot_id="11111111-1111-1111-1111-111111111111"):
        values = {key: "" for key in MODULE.base.PROPERTY_KEYS}
        values.update(
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product_name": "y2qksx",
                "build_product": "y2q",
                "fingerprint": (
                    "samsung/y2qksx/y2q:13/TP1A.220624.014/"
                    "G986NKSS8IYC2:user/release-keys"
                ),
                "incremental": "G986NKSS8IYC2",
                "boot_completed": "1",
                "bootanim": "stopped",
                "verified_boot_state": "orange",
                "flash_locked": "0",
                "vbmeta_device_state": "unlocked",
                "selinux": "Enforcing",
                "shell_identity": "uid=2000(shell) gid=2000(shell)",
                "boot_id": boot_id,
            }
        )
        return "".join(f"{key}={values[key]}\n" for key in MODULE.base.PROPERTY_KEYS)

    def android_usb(self):
        return (
            {
                "node": "3-2.1",
                "vid": "04e8",
                "pid": "6860",
                "bcd_device": "0c00",
                "manufacturer": "SAMSUNG",
                "product": "SAMSUNG_Android",
                "serial": "S20SERIAL",
                "interfaces": (
                    {
                        "class": "ff",
                        "subclass": "40",
                        "protocol": "02",
                        "endpoints": (),
                    },
                ),
            },
        )

    def fastboot_usb(self, node="3-2.1", serial="S20SERIAL"):
        return (
            {
                "node": node,
                "vid": "18d1",
                "pid": "d00d",
                "bcd_device": "0100",
                "manufacturer": "Google",
                "product": "Android",
                "serial": serial,
                "interfaces": (
                    {
                        "class": "ff",
                        "subclass": "42",
                        "protocol": "03",
                        "endpoints": MODULE.EXPECTED_ENDPOINTS,
                    },
                ),
            },
        )

    def receipts(self):
        adb = {
            "path": "/usr/lib/android-sdk/platform-tools/adb",
            "device": 1,
            "inode": 2,
            "mtime_ns": 3,
            "size": 4,
            "sha256": "a" * 64,
        }
        fastboot = {
            "path": "/private/fastboot",
            "size": MODULE.FASTBOOT_SIZE,
            "sha256": MODULE.FASTBOOT_SHA256,
            "version": MODULE.FASTBOOT_VERSION,
        }
        return adb, fastboot

    def command(
        self,
        calls,
        *,
        post_entry=True,
        unsupported=None,
        failure=None,
        unparsed=None,
        boot_id="11111111-1111-1111-1111-111111111111",
    ):
        inventory_count = 0

        def run(argv, _timeout, _maximum):
            nonlocal inventory_count
            calls.append(argv)
            if argv[-2:] == ["devices", "-l"]:
                inventory_count += 1
                include = not post_entry or inventory_count < 3
                return 0, self.inventory(include).encode(), b""
            if argv[-1] == "get-devpath":
                return 0, b"usb:3-2.1\n", b""
            if "exec-out" in argv:
                return 0, self.snapshot(boot_id).encode(), b""
            if "getvar" in argv:
                variable = argv[-1]
                if variable == unparsed:
                    return 0, b"", b"Finished. Total time: 0.001s\n"
                if variable == unsupported:
                    return (
                        1,
                        b"",
                        b"FAILED (remote: GetVar Variable Not found)\n",
                    )
                if variable == failure:
                    return 1, b"", b"FAILED (remote: device is locked)\n"
                values = {
                    "product": "kona",
                    "is-userspace": "no",
                    "version-bootloader": "",
                    "max-download-size": "0x10000000",
                }
                return (
                    0,
                    b"",
                    f"{variable}: {values[variable]}\nFinished. Total time: 0.001s\n".encode(),
                )
            raise AssertionError(argv)

        return run

    def connected(self, root, command, usb=None):
        run_dir = MODULE.allocate_run_dir(root)
        count = 0

        def default_usb():
            nonlocal count
            count += 1
            return self.android_usb() if count == 1 else self.fastboot_usb()

        adb, fastboot = self.receipts()
        with mock.patch.object(MODULE, "LIVE_ACTIVE", True), mock.patch.object(
            MODULE.base, "tool_receipt", return_value=adb
        ), mock.patch.object(MODULE, "require_fastboot", return_value=fastboot):
            result = MODULE.connected_census(
                root=root,
                run_dir=run_dir,
                command=command,
                usb_inventory=usb or default_usb,
                ready=lambda: None,
                timeout=1,
            )
        return run_dir, result

    def test_only_fixed_getvars_are_sent_and_intents_precede_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls = []
            run_dir, result = self.connected(root, self.command(calls))
            fastboot_calls = [argv for argv in calls if "getvar" in argv]
            self.assertEqual(
                [argv[-1] for argv in fastboot_calls], list(MODULE.GETVARS)
            )
            self.assertEqual(result["fastboot_command_count"], 4)
            self.assertTrue(MODULE.consumed_path(root).is_file())
            self.assertTrue(MODULE.guard_path(root).is_file())
            for ordinal in range(1, 5):
                self.assertTrue(
                    (run_dir / f"query-{ordinal:02d}-intent.json").is_file()
                )
                self.assertTrue(
                    (run_dir / f"query-{ordinal:02d}-result.json").is_file()
                )
            encoded = json.dumps(result, sort_keys=True)
            for private in ("S20SERIAL", "S22SERIAL", "A90SERIAL", "usb:3-2.1"):
                self.assertNotIn(private, encoded)
            self.assertFalse(result["payload_transfer"])
            self.assertFalse(result["boot_command_sent"])

    def test_recognized_remote_unsupported_continues(self):
        with tempfile.TemporaryDirectory() as temporary:
            calls = []
            _, result = self.connected(
                Path(temporary),
                self.command(calls, unsupported="is-userspace"),
            )
            statuses = {row["variable"]: row["status"] for row in result["getvars"]}
            self.assertEqual(statuses["is-userspace"], "UNSUPPORTED")
            self.assertEqual(
                [argv[-1] for argv in calls if "getvar" in argv],
                list(MODULE.GETVARS),
            )

    def test_other_nonzero_stops_all_later_queries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls = []
            run_dir = MODULE.allocate_run_dir(root)
            count = 0

            def usb():
                nonlocal count
                count += 1
                return self.android_usb() if count == 1 else self.fastboot_usb()

            adb, fastboot = self.receipts()
            with mock.patch.object(MODULE, "LIVE_ACTIVE", True), mock.patch.object(
                MODULE.base, "tool_receipt", return_value=adb
            ), mock.patch.object(MODULE, "require_fastboot", return_value=fastboot):
                with self.assertRaises(MODULE.ReturnRequiredError):
                    MODULE.connected_census(
                        root=root,
                        run_dir=run_dir,
                        command=self.command(calls, failure="version-bootloader"),
                        usb_inventory=usb,
                        ready=lambda: None,
                        timeout=1,
                    )
            self.assertEqual(
                [argv[-1] for argv in calls if "getvar" in argv],
                ["product", "is-userspace", "version-bootloader"],
            )
            self.assertFalse((run_dir / "query-04-intent.json").exists())
            with mock.patch.object(MODULE.base, "tool_receipt", return_value=adb):
                terminal = MODULE.finalize_return(
                    root=root,
                    run_dir=run_dir,
                    command=self.command(
                        [],
                        post_entry=False,
                        boot_id="22222222-2222-2222-2222-222222222222",
                    ),
                    usb_inventory=self.android_usb,
                )
            self.assertEqual(terminal["verdict"], MODULE.FINAL_NO_PROOF)

    def test_unparseable_zero_response_stops_later_queries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls = []
            run_dir = MODULE.allocate_run_dir(root)
            count = 0

            def usb():
                nonlocal count
                count += 1
                return self.android_usb() if count == 1 else self.fastboot_usb()

            adb, fastboot = self.receipts()
            with mock.patch.object(MODULE, "LIVE_ACTIVE", True), mock.patch.object(
                MODULE.base, "tool_receipt", return_value=adb
            ), mock.patch.object(MODULE, "require_fastboot", return_value=fastboot):
                with self.assertRaises(MODULE.ReturnRequiredError):
                    MODULE.connected_census(
                        root=root,
                        run_dir=run_dir,
                        command=self.command(calls, unparsed="is-userspace"),
                        usb_inventory=usb,
                        ready=lambda: None,
                        timeout=1,
                    )
            self.assertEqual(
                [argv[-1] for argv in calls if "getvar" in argv],
                ["product", "is-userspace"],
            )

    def test_foreign_fastboot_stops_before_query(self):
        for endpoint in (
            self.fastboot_usb(node="4-1"),
            self.fastboot_usb(serial="FOREIGN"),
        ):
            with self.subTest(endpoint=endpoint), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                calls = []
                sequence = iter((self.android_usb(), endpoint))
                adb, fastboot = self.receipts()
                with mock.patch.object(MODULE, "LIVE_ACTIVE", True), mock.patch.object(
                    MODULE.base, "tool_receipt", return_value=adb
                ), mock.patch.object(MODULE, "require_fastboot", return_value=fastboot):
                    with self.assertRaises(MODULE.FastbootCensusError):
                        MODULE.connected_census(
                            root=root,
                            run_dir=MODULE.allocate_run_dir(root),
                            command=self.command(calls),
                            usb_inventory=lambda: next(sequence),
                            ready=lambda: None,
                            timeout=1,
                        )
                self.assertFalse(any("getvar" in argv for argv in calls))

    def test_finalizer_requires_return_then_releases_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _ = self.connected(root, self.command([]))
            calls = []
            adb, _ = self.receipts()
            with mock.patch.object(MODULE.base, "tool_receipt", return_value=adb):
                terminal = MODULE.finalize_return(
                    root=root,
                    run_dir=run_dir,
                    command=self.command(
                        calls,
                        post_entry=False,
                        boot_id="22222222-2222-2222-2222-222222222222",
                    ),
                    usb_inventory=self.android_usb,
                )
            self.assertEqual(terminal["verdict"], MODULE.FINAL_PASS)
            self.assertFalse(MODULE.guard_path(root).exists())
            self.assertTrue(MODULE.consumed_path(root).exists())

            def forbidden(*_args):
                raise AssertionError("terminal re-emission must not contact the device")

            repeated = MODULE.finalize_return(
                root=root,
                run_dir=run_dir,
                command=forbidden,
                usb_inventory=forbidden,
            )
            self.assertEqual(repeated, terminal)

    def test_finalizer_sends_no_adb_while_fastboot_is_present(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _ = self.connected(root, self.command([]))

            def forbidden(*_args):
                raise AssertionError("ADB must not run before physical START")

            with self.assertRaises(MODULE.ReturnRequiredError):
                MODULE.finalize_return(
                    root=root,
                    run_dir=run_dir,
                    command=forbidden,
                    usb_inventory=self.fastboot_usb,
                )

    def test_consumed_entry_requires_a_fresh_returned_boot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _ = self.connected(root, self.command([]))
            adb, _ = self.receipts()
            with mock.patch.object(MODULE.base, "tool_receipt", return_value=adb):
                with self.assertRaisesRegex(
                    MODULE.FastbootCensusError, "no fresh returned boot"
                ):
                    MODULE.finalize_return(
                        root=root,
                        run_dir=run_dir,
                        command=self.command([], post_entry=False),
                        usb_inventory=self.android_usb,
                    )

    def test_raw_command_publishes_receipt_before_returning_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)

            def acquire(argv, capture_dir, name, **_kwargs):
                self.assertEqual(argv, ["/bin/fixture"])
                return MODULE.raw_capture.publish_captured_bytes(
                    capture_dir,
                    name,
                    stdout=b"fixture\n",
                    argv0_name="fixture",
                )

            command = MODULE.RawCommand(run_dir, "raw", acquire=acquire)
            result = command(["/bin/fixture"], 1, 32)
            self.assertEqual(result, (0, b"fixture\n", b""))
            self.assertTrue(
                (run_dir / "raw-captures/raw-01.capture.json").is_file()
            )

    def test_partial_finalize_raw_capture_does_not_block_safe_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _ = self.connected(root, self.command([]))
            adb, _ = self.receipts()

            def failed_acquire(_argv, capture_dir, name, **_kwargs):
                return MODULE.raw_capture.publish_captured_bytes(
                    capture_dir,
                    name,
                    stdout=b"",
                    stderr=b"fixture failure\n",
                    returncode=1,
                )

            first_dir = MODULE.allocate_finalize_capture_dir(run_dir)
            first = MODULE.RawCommand(
                run_dir,
                "read",
                acquire=failed_acquire,
                capture_dir=first_dir,
            )
            with mock.patch.object(MODULE.base, "tool_receipt", return_value=adb):
                with self.assertRaises(MODULE.base.InventoryError):
                    MODULE.finalize_return(
                        root=root,
                        run_dir=run_dir,
                        command=first,
                        usb_inventory=self.android_usb,
                    )

            fixture = self.command(
                [],
                post_entry=False,
                boot_id="22222222-2222-2222-2222-222222222222",
            )

            def successful_acquire(argv, capture_dir, name, **kwargs):
                rc, stdout, stderr = fixture(
                    argv,
                    kwargs["timeout"],
                    kwargs["stdout_maximum"],
                )
                return MODULE.raw_capture.publish_captured_bytes(
                    capture_dir,
                    name,
                    stdout=stdout,
                    stderr=stderr,
                    returncode=rc,
                )

            second_dir = MODULE.allocate_finalize_capture_dir(run_dir)
            second = MODULE.RawCommand(
                run_dir,
                "read",
                acquire=successful_acquire,
                capture_dir=second_dir,
            )
            with mock.patch.object(MODULE.base, "tool_receipt", return_value=adb):
                terminal = MODULE.finalize_return(
                    root=root,
                    run_dir=run_dir,
                    command=second,
                    usb_inventory=self.android_usb,
                )
            self.assertEqual(terminal["verdict"], MODULE.FINAL_PASS)
            self.assertNotEqual(first_dir, second_dir)
            self.assertTrue((first_dir / "read-01.capture.json").is_file())
            self.assertTrue((second_dir / "read-01.capture.json").is_file())

    def test_plan_and_contract_keep_the_surface_closed_and_inactive(self):
        plan = MODULE.dry_run_plan()
        self.assertEqual(plan["getvars"], list(MODULE.GETVARS))
        self.assertEqual(plan["capability_ordinal"], 2)
        self.assertTrue(plan["raw_capture_before_parse"])
        self.assertTrue(plan["live_active"])
        options = MODULE.build_parser()._option_string_actions
        for forbidden in ("--fastboot", "--serial", "--getvar", "--boot", "--flash"):
            self.assertNotIn(forbidden, options)
        self.assertNotIn("--run-dir", options)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        contract = (
            ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        self.assertIn("S20+ classic-fastboot census exception", agents)
        self.assertIn("Attended Classic-Fastboot Read-Only Census", contract)
        self.assertIn(
            "Status: **ORDINAL 1 CONSUMED ZERO-QUERY; ORDINAL 2 CONSUMED FOUR-QUERY PASS / HEALTHY RETURN**",
            contract,
        )
        self.assertIn(SCRIPT.name, contract)

    def test_replacement_requires_exact_zero_query_healthy_predecessor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = MODULE.run_root(root)
            parent.mkdir(parents=True)
            old_run = parent / "ordinal-1"
            old_run.mkdir()
            entry = {"run_dir": str(old_run), "consumed": True}
            terminal = {
                "verdict": MODULE.FINAL_NO_PROOF,
                "fastboot_query_intent_count": 0,
                "all_four_queries_completed": False,
                "fastboot_endpoint_absent_before_health": True,
                "replay_permitted": False,
            }
            MODULE.base.durable_write(parent / MODULE.PREDECESSOR_CONSUMED_NAME, entry)
            MODULE.base.durable_write(old_run / "final-result.json", terminal)
            entry_path = parent / MODULE.PREDECESSOR_CONSUMED_NAME
            terminal_path = old_run / "final-result.json"
            with mock.patch.object(
                MODULE, "PREDECESSOR_ENTRY_SIZE", entry_path.stat().st_size
            ), mock.patch.object(
                MODULE, "PREDECESSOR_ENTRY_SHA256", MODULE.sha256_file(entry_path)
            ), mock.patch.object(
                MODULE, "PREDECESSOR_FINAL_SIZE", terminal_path.stat().st_size
            ), mock.patch.object(
                MODULE, "PREDECESSOR_FINAL_SHA256", MODULE.sha256_file(terminal_path)
            ):
                result = REAL_REQUIRE_PREDECESSOR(root)
                self.assertEqual(result["fastboot_query_intent_count"], 0)
                MODULE.base.durable_write(
                    old_run / "entry-observed.json", {"unexpected": True}
                )
                with self.assertRaisesRegex(
                    MODULE.FastbootCensusError, "not the exact zero-query"
                ):
                    REAL_REQUIRE_PREDECESSOR(root)


if __name__ == "__main__":
    unittest.main()
