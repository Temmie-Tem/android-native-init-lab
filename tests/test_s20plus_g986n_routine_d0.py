import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s20plus_g986n_routine_d0.py"

import sys
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("s20plus_g986n_routine_d0", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class S20PlusG986NRoutineD0Tests(unittest.TestCase):
    def inventory(self, extra: str = "") -> str:
        return (
            "List of devices attached\n"
            "S20SERIAL device product:y2qksx model:SM_G986N device:y2q transport_id:1\n"
            "S22SERIAL device product:g0qksx model:SM_S906N device:g0q transport_id:2\n"
            "A90SERIAL device product:a90 model:SM_A908N device:a90q transport_id:3\n"
            + extra
        )

    def snapshot(self, **changes: str) -> str:
        values = {key: "" for key in MODULE.PROPERTY_KEYS}
        values.update(
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product_name": "y2qksx",
                "incremental": "G986NKSS8IYC2",
                "fingerprint": "samsung/y2qksx/y2q:13/TP1A/G986NKSS8IYC2:user/release-keys",
                "carrier_id": "KOO",
                "boot_sales_code": "KOO",
                "csc_sales_code": "KOO",
                "boot_completed": "1",
                "bootanim": "stopped",
                "verified_boot_state": "orange",
                "flash_locked": "0",
                "vbmeta_device_state": "unlocked",
            }
        )
        values.update(changes)
        return "".join(f"{key}={values[key]}\n" for key in MODULE.PROPERTY_KEYS)

    def command(self, calls: list[list[str]], snapshot: str | None = None):
        def run(argv, _timeout, _maximum):
            calls.append(argv)
            if argv[-2:] == ["devices", "-l"]:
                return 0, self.inventory().encode(), b""
            if argv[-1] == "get-devpath":
                return 0, b"usb:3-2.1\n", b""
            if "exec-out" in argv:
                return 0, (snapshot or self.snapshot()).encode(), b""
            raise AssertionError(argv)
        return run

    def test_collect_exact_target_only_and_redacts_serial_topology(self):
        calls: list[list[str]] = []
        result = MODULE.collect(self.command(calls))
        encoded = json.dumps(result, sort_keys=True)
        for raw in ("S20SERIAL", "S22SERIAL", "A90SERIAL", "usb:3-2.1"):
            self.assertNotIn(raw, encoded)
        target_calls = [argv for argv in calls if "-s" in argv]
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(target_calls), 2)
        self.assertTrue(all(argv[argv.index("-s") + 1] == "S20SERIAL" for argv in target_calls))
        self.assertEqual(result["csc_resolution"]["status"], "EXACT")
        self.assertEqual(result["csc_resolution"]["csc"], "KOO")
        self.assertEqual(result["s22plus_command_count"], 0)
        self.assertEqual(result["a90_command_count"], 0)
        self.assertFalse(result["device_writes"])

    def test_csc_resolution_maps_korean_carrier_aliases(self):
        for raw, expected in (("KOO", "KOO"), ("KTC", "KTC"), ("KTT", "KTC"), ("SKT", "SKC"), ("LGT", "LUC")):
            with self.subTest(raw=raw):
                values = MODULE.parse_snapshot(self.snapshot(carrier_id=raw, boot_sales_code="", csc_sales_code=""))
                result = MODULE.resolve_csc(values)
                self.assertEqual(result["status"], "EXACT")
                self.assertEqual(result["csc"], expected)

    def test_csc_resolution_preserves_no_proof_and_conflict(self):
        values = MODULE.parse_snapshot(self.snapshot(carrier_id="", boot_sales_code="", csc_sales_code=""))
        self.assertEqual(MODULE.resolve_csc(values)["status"], "NO_PROOF")
        values = MODULE.parse_snapshot(self.snapshot(carrier_id="KOO", boot_sales_code="SKC"))
        conflict = MODULE.resolve_csc(values)
        self.assertEqual(conflict["status"], "CONFLICT")
        self.assertEqual(conflict["candidates"], ["KOO", "SKC"])

    def test_snapshot_fails_closed_on_identity_health_or_schema(self):
        cases = (
            self.snapshot(model="SM-G986B"),
            self.snapshot(device="g0q"),
            self.snapshot(product_name="wrong"),
            self.snapshot(incremental="G986NKSS7IYA1"),
            self.snapshot(boot_completed="0"),
            self.snapshot(bootanim="running"),
            self.snapshot().replace("carrier_id=KOO\n", ""),
            self.snapshot() + "carrier_id=KOO\n",
        )
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(MODULE.RoutineD0Error):
                MODULE.parse_snapshot(payload)

    def test_ambiguous_replaced_or_changed_inventory_fails_before_cross_target_command(self):
        duplicate = self.inventory(
            "OTHER device product:y2qksx model:SM_G986N device:y2q transport_id:4\n"
        )
        with self.assertRaises(MODULE.base.InventoryError):
            MODULE.base.select_target(MODULE.base.parse_inventory(duplicate))

        calls: list[list[str]] = []
        inventories = iter((self.inventory(), self.inventory().replace("S20SERIAL", "REPLACED")))
        def changed(argv, _timeout, _maximum):
            calls.append(argv)
            if argv[-2:] == ["devices", "-l"]:
                return 0, next(inventories).encode(), b""
            if argv[-1] == "get-devpath":
                return 0, b"usb:3-2", b""
            return 0, self.snapshot().encode(), b""
        with self.assertRaisesRegex(MODULE.RoutineD0Error, "changed"):
            MODULE.collect(changed)
        self.assertTrue(all("S22SERIAL" not in argv and "A90SERIAL" not in argv for argv in calls))

    def test_wrong_or_partial_identity_is_rejected_before_target_command(self):
        bad_rows = (
            "WRONG device product:g0qksx model:SM_G986N device:g0q transport_id:1\n",
            "WRONG device product:wrong model:SM_G986N device:y2q transport_id:1\n",
            "WRONG device product:y2qksx model:SM_G986B device:y2q transport_id:1\n",
            "WRONG offline product:y2qksx model:SM_G986N device:y2q transport_id:1\n",
        )
        for row in bad_rows:
            with self.subTest(row=row):
                calls: list[list[str]] = []
                def command(argv, _timeout, _maximum):
                    calls.append(argv)
                    return 0, ("List of devices attached\n" + row).encode(), b""
                with self.assertRaises(MODULE.RoutineD0Error):
                    MODULE.collect(command)
                self.assertEqual(len(calls), 1)
                self.assertFalse(any("-s" in argv for argv in calls))

    def test_mixed_plausible_rows_rejected_and_final_identity_drift_closes(self):
        mixed = self.inventory(
            "PARTIAL device product:g0qksx model:SM_G986N device:g0q transport_id:4\n"
        )
        with self.assertRaises(MODULE.RoutineD0Error):
            MODULE.select_exact_target(MODULE.base.parse_inventory(mixed))

        calls: list[list[str]] = []
        final = self.inventory().replace(
            "product:y2qksx model:SM_G986N device:y2q",
            "product:g0qksx model:SM_G986N device:g0q",
        )
        inventories = iter((self.inventory(), final))
        def changed(argv, _timeout, _maximum):
            calls.append(argv)
            if argv[-2:] == ["devices", "-l"]:
                return 0, next(inventories).encode(), b""
            if argv[-1] == "get-devpath":
                return 0, b"usb:3-2", b""
            return 0, self.snapshot().encode(), b""
        with self.assertRaises(MODULE.RoutineD0Error):
            MODULE.collect(changed)
        self.assertEqual(sum("-s" in argv for argv in calls), 2)

    def test_duplicate_and_conflicting_metadata_fail_closed(self):
        duplicate = self.inventory(
            "S20SERIAL device product:y2qksx model:SM_G986N device:y2q transport_id:4\n"
        )
        conflicting = (
            "List of devices attached\n"
            "S20SERIAL device product:y2qksx product:g0qksx "
            "model:SM_G986N device:y2q transport_id:1\n"
        )
        for inventory in (duplicate, conflicting):
            with self.subTest(inventory=inventory), self.assertRaises(MODULE.base.InventoryError):
                MODULE.base.parse_inventory(inventory)

    def test_failure_receipt_records_counts_without_raw_error(self):
        recorder = MODULE.CommandRecorder(lambda _argv, _timeout, _maximum: (0, b"", b""))
        recorder.run(["adb", "devices", "-l"], 1, 1)
        recorder.run(["adb", "-s", "PRIVATE", "get-devpath"], 1, 1)
        failure = MODULE.failure_result(recorder, MODULE.RoutineD0Error("private-safe"))
        encoded = json.dumps(failure, sort_keys=True)
        self.assertNotIn("PRIVATE", encoded)
        self.assertNotIn("private-safe", encoded)
        self.assertEqual(failure["selected_target_command_count"], 1)
        self.assertEqual(failure["s22plus_command_count"], 0)
        self.assertFalse(failure["reboot_requested"])

    def test_cli_and_source_have_no_effect_surface_or_arbitrary_adb(self):
        options = MODULE.build_parser()._option_string_actions
        for forbidden in ("--adb", "--root", "--reboot", "--download", "--odin", "--flash"):
            self.assertNotIn(forbidden, options)
        source = SCRIPT.read_text(encoding="utf-8").lower()
        for forbidden in ("shell=true", "su -c", "setprop ", "settings put", "reboot download", "odin4", "/dev/block", "ro.serialno", "imei"):
            self.assertNotIn(forbidden, source)

    def test_dry_run_is_device_hidden_and_routine_not_one_shot(self):
        plan = MODULE.dry_run_plan()
        self.assertEqual(plan["mode"], "dry-run-device-hidden")
        self.assertFalse(plan["live_authorized"])
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("active-intent", source)
        self.assertNotIn("replay is refused", source)

    def test_private_run_directory_and_result_are_no_clobber(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = MODULE.allocate_run_dir(root, None)
            result = run_dir / "result.json"
            MODULE.base.durable_write(result, {"ok": True})
            self.assertEqual(result.stat().st_mode & 0o777, 0o400)
            with self.assertRaises(FileExistsError):
                MODULE.base.durable_write(result, {"ok": False})
            escaped = root / MODULE.DEFAULT_RUN_ROOT / "../../../../escape"
            with self.assertRaises(MODULE.RoutineD0Error):
                MODULE.allocate_run_dir(root, escaped)

    def test_documents_bind_exactly_one_active_routine_d0_row(self):
        contract = (
            ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        report = (
            ROOT
            / "docs/reports/S20PLUS_G986N_ROUTINE_D0_PUBLIC_PROPERTIES_H0_2026-08-12.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Status: **BINDING - ROUTINE D0 PUBLIC-PROPERTY READS ACTIVE**", contract)
        self.assertIn("s20plus_g986n_routine_d0.py", contract)
        self.assertIn("PASS_GO - ROUTINE D0 ACTIVATED", report)
        goal = (ROOT / "GOAL_S20PLUS.md").read_text(encoding="utf-8")
        self.assertIn("boot_sales_code=KTC", goal)
        self.assertIn("carrier_id` property is\n  `KOO`", goal)
        self.assertIn("5c1825b643f1745c6ed0c84b19cf4cce0246b20c4e3eb60cdb8e6047d03ba04f", goal)
        self.assertEqual(
            agents.count(
                "| Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `G986NKSS8IYC2`) "
                "| `GOAL_S20PLUS.md` | `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md` "
                "| Active exact-target routine D0/D1; bootstrap F1 endpoint-session correction under H0 review, no active F1 |"
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
