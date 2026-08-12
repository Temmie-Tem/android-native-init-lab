import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py"
SPEC = importlib.util.spec_from_file_location("s20plus_g986n_d0_inventory", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class S20PlusG986ND0InventoryTests(unittest.TestCase):
    def inventory(self, extra: str = "") -> str:
        return (
            "List of devices attached\n"
            "S20SERIAL device product:y2qksx model:SM_G986N device:y2q transport_id:1\n"
            "S22SERIAL device product:g0qksx model:SM_S906N device:g0q transport_id:2\n"
            "A90SERIAL device product:a90qksx model:SM_A908N device:a90q transport_id:3\n"
            + extra
        )

    def snapshot(self, **changes: str) -> str:
        values = {key: "observed" for key in MODULE.PROPERTY_KEYS}
        values.update(
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product_name": "y2qksx",
                "fingerprint": "samsung/y2qksx/y2q:13/TP1A/G986NKSS8IYC2:user/release-keys",
                "incremental": "G986NKSS8IYC2",
                "boot_completed": "1",
                "bootanim": "stopped",
                "boot_id": "01234567-89ab-cdef-0123-456789abcdef",
            }
        )
        values.update(changes)
        return "".join(f"{key}={values[key]}\n" for key in MODULE.PROPERTY_KEYS)

    def test_selects_one_exact_model_and_hashes_all_serials(self):
        rows = MODULE.parse_inventory(self.inventory())
        selected = MODULE.select_target(rows)
        self.assertEqual(selected["serial"], "S20SERIAL")
        sanitized = MODULE.sanitized_inventory(rows)
        payload = json.dumps(sanitized, sort_keys=True)
        self.assertNotIn("S20SERIAL", payload)
        self.assertNotIn("S22SERIAL", payload)
        self.assertNotIn("A90SERIAL", payload)
        self.assertIn(hashlib.sha256(b"S20SERIAL").hexdigest(), payload)

    def test_rejects_missing_duplicate_unauthorized_and_wrong_model(self):
        cases = (
            "List of devices attached\n",
            self.inventory(
                "OTHER device product:y2qksx model:SM_G986N device:y2q transport_id:4\n"
            ),
            self.inventory(
                "OTHER offline product:y2qksx model:SM_G986N device:y2q transport_id:4\n"
            ),
            self.inventory().replace(
                "S22SERIAL device product:g0qksx model:SM_S906N device:g0q transport_id:2\n",
                "S20SERIAL unauthorized\n",
            ),
            self.inventory().replace(
                "model:SM_G986N",
                "model:SM_G986N model:SM_S906N",
            ),
            self.inventory().replace("device:y2q", "device:y2q device:g0q", 1),
            "List of devices attached\nS20SERIAL unauthorized model:SM_G986N\n",
            "List of devices attached\nS20SERIAL device model:SM_G985N device:x1s\n",
        )
        for text in cases:
            with self.subTest(text=text), self.assertRaises(MODULE.InventoryError):
                MODULE.select_target(MODULE.parse_inventory(text))

    def test_snapshot_requires_exact_schema_model_health_and_boot_id(self):
        parsed = MODULE.parse_snapshot(self.snapshot())
        self.assertEqual(parsed["device"], "y2q")
        for changed in (
            self.snapshot(model="SM-G986B"),
            self.snapshot(boot_completed="0"),
            self.snapshot(bootanim="running"),
            self.snapshot(boot_id="not-a-boot-id"),
            self.snapshot().replace("model=SM-G986N\n", ""),
            self.snapshot() + "model=SM-G986N\n",
        ):
            with self.subTest(changed=changed), self.assertRaises(MODULE.InventoryError):
                MODULE.parse_snapshot(changed)

    def test_collect_commands_only_selected_serial_and_redacts_private_values(self):
        calls = []

        def command(argv, _timeout, _maximum):
            calls.append(argv)
            if argv[-1] == "version":
                return 0, b"Android Debug Bridge version fixture\n", b""
            if argv[-2:] == ["devices", "-l"]:
                return 0, self.inventory().encode(), b""
            if argv[-1] == "get-devpath":
                return 0, b"usb:3-2.1\n", b""
            if "exec-out" in argv:
                return 0, self.snapshot().encode(), b""
            raise AssertionError(argv)

        result = MODULE.collect(command)
        encoded = json.dumps(result, sort_keys=True)
        for raw in ("S20SERIAL", "S22SERIAL", "A90SERIAL", "usb:3-2.1"):
            self.assertNotIn(raw, encoded)
        target_calls = [argv for argv in calls if "-s" in argv]
        self.assertEqual(len(target_calls), 3)
        self.assertTrue(all(argv[argv.index("-s") + 1] == "S20SERIAL" for argv in target_calls))
        self.assertEqual(result["host_command_count"], 6)
        self.assertEqual(result["inventory_command_count"], 2)
        self.assertEqual(result["selected_target_command_count"], 3)
        self.assertEqual(result["other_target_command_count"], 0)
        self.assertEqual(result["s22plus_command_count"], 0)
        self.assertEqual(result["a90_command_count"], 0)
        self.assertTrue(result["usb_debugging_verified"])

    def test_collect_rejects_target_replacement_and_snapshot_drift(self):
        inventories = iter(
            (
                self.inventory(),
                self.inventory().replace("S20SERIAL", "REPLACED"),
            )
        )

        def replaced(argv, _timeout, _maximum):
            if argv[-1] == "version":
                return 0, b"version", b""
            if argv[-2:] == ["devices", "-l"]:
                return 0, next(inventories).encode(), b""
            if argv[-1] == "get-devpath":
                return 0, b"usb:3-2", b""
            return 0, self.snapshot().encode(), b""

        with self.assertRaisesRegex(MODULE.InventoryError, "changed"):
            MODULE.collect(replaced)

        count = 0

        def drift(argv, _timeout, _maximum):
            nonlocal count
            if argv[-1] == "version":
                return 0, b"version", b""
            if argv[-2:] == ["devices", "-l"]:
                return 0, self.inventory().encode(), b""
            if argv[-1] == "get-devpath":
                return 0, b"usb:3-2", b""
            count += 1
            boot_id = (
                "01234567-89ab-cdef-0123-456789abcdef"
                if count == 1
                else "abcdefab-cdef-abcd-efab-cdefabcdefab"
            )
            return 0, self.snapshot(boot_id=boot_id).encode(), b""

        with self.assertRaisesRegex(MODULE.InventoryError, "snapshot changed"):
            MODULE.collect(drift)

    def test_snapshot_must_bind_adb_device_and_product_metadata(self):
        selected = MODULE.select_target(MODULE.parse_inventory(self.inventory()))
        MODULE.validate_snapshot_binding(MODULE.parse_snapshot(self.snapshot()), selected)
        for changed in (
            self.snapshot(device="g0q"),
            self.snapshot(product_name="wrong_product"),
        ):
            with self.assertRaisesRegex(MODULE.InventoryError, "conflicts"):
                MODULE.validate_snapshot_binding(MODULE.parse_snapshot(changed), selected)

    def test_dry_run_and_cli_expose_no_live_control_surface(self):
        plan = MODULE.dry_run_plan(Path("/usr/bin/adb"))
        self.assertEqual(plan["mode"], "dry-run-device-hidden")
        self.assertFalse(plan["live_authorized"])
        self.assertFalse(plan["device_writes"])
        options = MODULE.build_parser()._option_string_actions
        for forbidden in ("--adb", "--reboot", "--download", "--odin", "--root", "--flash"):
            self.assertNotIn(forbidden, options)

        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "shell=True",
            "su -c",
            "setprop ",
            "reboot download",
            "odin4",
            "/dev/block",
            "ro.serialno",
            "imei",
        ):
            self.assertNotIn(forbidden, source.lower())

    def test_tool_identity_is_fixed_to_reviewed_canonical_adb(self):
        receipt = MODULE.tool_receipt(MODULE.DEFAULT_ADB)
        self.assertEqual(receipt["path"], str(MODULE.EXPECTED_ADB_REALPATH))
        self.assertEqual(receipt["sha256"], MODULE.EXPECTED_ADB_SHA256)
        with tempfile.TemporaryDirectory() as temporary:
            replacement = Path(temporary) / "adb"
            replacement.write_bytes(b"not-reviewed")
            replacement.chmod(0o700)
            with self.assertRaisesRegex(MODULE.InventoryError, "reviewed canonical"):
                MODULE.tool_receipt(replacement)

    def test_host_command_output_and_time_are_bounded(self):
        with self.assertRaisesRegex(MODULE.InventoryError, "output exceeded"):
            MODULE.bounded_command(
                [sys.executable, "-c", "print('x' * 4096)"],
                5,
                64,
            )
        with self.assertRaisesRegex(MODULE.InventoryError, "timed out"):
            MODULE.bounded_command(
                [sys.executable, "-c", "import time; time.sleep(1)"],
                0.1,
                64,
            )

    def test_documents_bind_exactly_one_d0_only_target_row(self):
        contract = (
            ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        goal = (ROOT / "GOAL_S20PLUS.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Status: **BINDING - D0 ONBOARDING CONSUMED**", contract)
        self.assertIn("s20plus_g986n_d0_inventory.py", contract)
        self.assertIn("defines no S20+ D1, F1", contract)
        self.assertIn("terminal one-shot D0 PASS", goal)
        row = (
            "| Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `G986NKSS8IYC2`) "
            "| `GOAL_S20PLUS.md` | `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md` "
            "| Consumed one-shot D0 onboarding only; no active D1/F1 process |"
        )
        self.assertEqual(agents.count(row), 1)

    def test_durable_result_is_private_mode_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            MODULE.durable_write(path, {"ok": True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
            with self.assertRaises(FileExistsError):
                MODULE.durable_write(path, {"ok": False})

    def test_intent_guard_is_durable_and_refuses_reentry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_one = MODULE.allocate_run_dir(root, None)
            receipt = MODULE.tool_receipt(MODULE.DEFAULT_ADB)
            guard, intent_sha256 = MODULE.arm_intent(root, run_one, receipt)
            self.assertTrue(guard.is_file())
            self.assertTrue((run_one / "intent.json").is_file())
            self.assertRegex(intent_sha256, r"^[0-9a-f]{64}$")
            run_two = MODULE.allocate_run_dir(root, None)
            with self.assertRaisesRegex(MODULE.InventoryError, "replay is refused"):
                MODULE.arm_intent(root, run_two, receipt)

    def test_failure_receipt_retains_attempted_counts_and_zero_effects(self):
        recorder = MODULE.CommandRecorder(lambda _argv, _timeout, _maximum: (0, b"", b""))
        recorder.run(["adb", "devices", "-l"], 1, 1)
        recorder.run(["adb", "-s", "PRIVATE", "get-devpath"], 1, 1)
        failure = MODULE.failure_result(recorder, MODULE.InventoryError("private-safe"))
        encoded = json.dumps(failure, sort_keys=True)
        self.assertNotIn("PRIVATE", encoded)
        self.assertEqual(failure["inventory_command_count"], 1)
        self.assertEqual(failure["selected_target_command_count"], 1)
        self.assertEqual(failure["other_target_command_count"], 0)
        self.assertFalse(failure["device_writes"])
        self.assertEqual(failure["verdict"], "FAIL_S20PLUS_G986N_D0_STOP_NO_RETRY")

    def test_run_directory_cannot_escape_private_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            escaped = root / MODULE.DEFAULT_RUN_ROOT / "../../../../escape"
            with self.assertRaises(MODULE.InventoryError):
                MODULE.allocate_run_dir(root, escaped)

    def test_main_defaults_to_device_hidden_dry_run(self):
        with mock.patch("sys.argv", [str(SCRIPT)]), mock.patch("builtins.print") as output:
            self.assertEqual(MODULE.main(), 0)
        rendered = output.call_args.args[0]
        self.assertIn("dry-run-device-hidden", rendered)


if __name__ == "__main__":
    unittest.main()
