from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_twrp_fastbootd_census.py"
)
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("s20_twrp_fastbootd_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def endpoint(serial: str = "SERIAL") -> tuple[dict, ...]:
    return (
        {
            "node": "1-2.3",
            "vid": "18d1",
            "pid": "4ee0",
            "bcd_device": "0100",
            "manufacturer": "Samsung",
            "product": "SM-G986N",
            "serial": serial,
            "interfaces": (
                {
                    "class": "ff",
                    "subclass": "42",
                    "protocol": "03",
                    "endpoints": (
                        {"direction": "out", "type": "Bulk", "max_packet_size": "0400"},
                        {"direction": "in", "type": "Bulk", "max_packet_size": "0400"},
                    ),
                },
            ),
        },
    )


class FastbootdCensusTests(unittest.TestCase):
    def test_terminal_owner_is_active_and_has_only_four_fixed_reads(self) -> None:
        plan = MODULE.plan()
        self.assertTrue(plan["live_active"])
        self.assertEqual(
            MODULE.normalized_self_sha256(),
            MODULE.EXPECTED_REVIEWED_NORMALIZED_SHA256,
        )
        self.assertEqual(
            plan["getvars"],
            ["is-userspace", "product", "version-bootloader", "max-download-size"],
        )
        self.assertFalse(plan["getvar_all"])
        self.assertEqual(plan["fastboot_mutation_commands"], 0)
        self.assertEqual(plan["persistent_writes"], 0)
        self.assertEqual(plan["partition_operations"], 0)

    def test_exact_t2_builder_proves_current_recovery_is_adb_only(self) -> None:
        builder = (ROOT / (
            "workspace/public/src/scripts/revalidation/"
            "build_s20plus_g986n_twrp_port_t2_h0.py"
        )).read_text(encoding="utf-8")
        self.assertIn("on property:sys.usb.config=fastboot", builder)
        self.assertIn("setprop sys.usb.config adb", builder)
        validation = builder.split("def validate_safe_usb_rc", 1)[1].split("def ", 1)[0]
        self.assertIn('b"functions/ffs.fastboot"', validation)
        self.assertIn('b"start fastbootd"', validation)

    def test_preflight_parser_is_exact(self) -> None:
        payload = b"".join(
            f"{key}={value}\n".encode()
            for key, value in MODULE.PREFLIGHT_EXPECTED.items()
        )
        self.assertEqual(
            MODULE.parse_preflight((0, payload, b"")), MODULE.PREFLIGHT_EXPECTED
        )
        with self.assertRaises(MODULE.FastbootdCensusError):
            MODULE.parse_preflight((0, payload + b"extra=x\n", b""))
        with self.assertRaises(MODULE.FastbootdCensusError):
            MODULE.parse_preflight((1, payload, b""))
        self.assertIn('"bound_udc=$bound_udc"', MODULE.PREFLIGHT_SCRIPT)
        self.assertIn(
            '"fastboot_functionfs_dir=$fastboot_functionfs_dir"',
            MODULE.PREFLIGHT_SCRIPT,
        )
        self.assertIn('"secondary_function=$secondary_function"', MODULE.PREFLIGHT_SCRIPT)
        self.assertNotIn("|| exit", MODULE.PREFLIGHT_SCRIPT)

    def test_volatile_script_is_closed_and_partition_free(self) -> None:
        launch = MODULE.LAUNCH_SCRIPT
        inner = MODULE.INNER_ENABLE_SCRIPT
        self.assertIn("ctl.start fastbootd", inner)
        self.assertEqual(MODULE.PREFLIGHT_EXPECTED["ffs_fastboot"], "absent")
        self.assertIn('/system/bin/mkdir "$g/functions/ffs.fastboot"', inner)
        self.assertIn("0x18D1", inner)
        self.assertIn("0x4EE0", inner)
        self.assertIn("0x0320", inner)
        self.assertEqual(MODULE.PREFLIGHT_EXPECTED["usb_bcd_device"], "0419")
        self.assertIn("0x0419", inner)
        self.assertIn('SM-G986N > "$g/strings/0x409/product"', inner)
        self.assertEqual(inner.count("/system/bin/mount -t functionfs"), 1)
        self.assertIn(
            "rmode=0770,fmode=0660,uid=1000,gid=1000 fastboot "
            "/dev/usb-ffs/fastboot",
            inner,
        )
        self.assertIn(
            "! /system/bin/grep -q ' /dev/usb-ffs/fastboot ' /proc/mounts",
            inner,
        )
        self.assertIn("nohup", launch)
        self.assertIn(MODULE.t2_profile.MARKER_SHA256, launch)
        for forbidden in (
            "dd ",
            "blockdev",
            "flash",
            "erase",
            "set_active",
            "/dev/block",
            "/data/",
            "/efs/",
            "reboot",
        ):
            self.assertNotIn(forbidden, inner)

    def test_endpoint_requires_exact_profile_and_serial(self) -> None:
        self.assertIsNotNone(
            MODULE.validate_fastbootd_usb(endpoint(), "1-2.3", "SERIAL")
        )
        with self.assertRaises(MODULE.FastbootdCensusError):
            MODULE.validate_fastbootd_usb(endpoint(), "1-2.3", "OTHER")
        classic_row = list(endpoint())[0] | {"vid": "18d1", "pid": "d00d"}
        with self.assertRaises(MODULE.FastbootdCensusError):
            MODULE.validate_fastbootd_usb((classic_row,), "1-2.3", "SERIAL")
        wrong_bcd = list(endpoint())[0] | {"bcd_device": "0200"}
        with self.assertRaises(MODULE.FastbootdCensusError):
            MODULE.validate_fastbootd_usb((wrong_bcd,), "1-2.3", "SERIAL")
        foreign = endpoint() + endpoint("SECOND")
        with self.assertRaises(MODULE.FastbootdCensusError):
            MODULE.validate_fastbootd_usb(foreign, "1-2.3", "SERIAL")

    def _fixtures(self, root: Path) -> tuple[Path, dict, dict, dict]:
        run_dir = root / MODULE.RUN_ROOT_REL / "run-test"
        run_dir.mkdir(parents=True)
        predecessor = {
            "serial_sha256": MODULE.base.sha256_text("SERIAL"),
            "topology_sha256": MODULE.base.sha256_text("usb:1-2.3"),
        }
        recovery = {
            "serial": "SERIAL",
            "node": "1-2.3",
            "serial_sha256": predecessor["serial_sha256"],
            "topology_sha256": predecessor["topology_sha256"],
            "boot_id_sha256": MODULE.base.sha256_text("recovery-boot"),
            "other_serial_sha256": [],
            "identity": {"usb_config": "mtp,adb"},
            "preflight": dict(MODULE.PREFLIGHT_EXPECTED),
        }
        support = {
            "support": True,
            "fastboot": {"path": "/fixed/fastboot", "sha256": "f" * 64},
        }
        return run_dir, predecessor, recovery, support

    def _intent_only_journal(self, root: Path) -> tuple[Path, dict, dict, dict]:
        run_dir, _predecessor, recovery, support = self._fixtures(root)
        MODULE.acquire_guard(root, run_dir)
        prepared = {
            "schema": "s20plus_g986n_twrp_fastbootd_prepared_v1",
            "version": MODULE.VERSION,
            "run_dir": str(run_dir),
            "target": {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "incremental": "G986NKSS8IYC2",
                "serial_sha256": recovery["serial_sha256"],
                "topology_sha256": recovery["topology_sha256"],
                "recovery_boot_id_sha256": recovery["boot_id_sha256"],
                "other_serial_sha256": [],
            },
            "t2_predecessor": {"validated": True},
            "t2_identity": {"usb_config": "mtp,adb"},
            "volatile_preflight": dict(MODULE.PREFLIGHT_EXPECTED),
            "support_sha256": MODULE.classic.object_sha256(support),
            "fixed_getvars": list(MODULE.GETVARS),
            "fastboot_tool": support["fastboot"],
            "persistent_writes": 0,
            "partition_operations": 0,
            "at": "time",
        }
        MODULE.base.durable_write(run_dir / "prepared.json", prepared)
        MODULE.create_enable_intent(root, run_dir, prepared)
        return run_dir, prepared, recovery, support

    def _write_entry_and_queries(self, run_dir: Path, prepared: dict) -> list[dict]:
        MODULE.base.durable_write(
            run_dir / "enable-result.json",
            {
                "schema": "s20plus_g986n_twrp_fastbootd_enable_result_v1",
                "version": MODULE.VERSION,
                "armed": True,
                "returncode": 0,
                "stdout_sha256": MODULE.hashlib.sha256(b"armed\n").hexdigest(),
                "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(),
                "acquisition_error_sha256": None,
                "replay_permitted": False,
                "at": "time",
            },
        )
        MODULE.base.durable_write(
            run_dir / "entry-observed.json",
            {
                "schema": "s20plus_g986n_twrp_fastbootd_entry_observed_v1",
                "version": MODULE.VERSION,
                "serial_sha256": prepared["target"]["serial_sha256"],
                "topology_sha256": prepared["target"]["topology_sha256"],
                "vid": MODULE.EXPECTED_USB["vid"],
                "pid": MODULE.EXPECTED_USB["pid"],
                "bcd_device": MODULE.EXPECTED_USB["bcd_device"],
                "interface": dict(MODULE.EXPECTED_INTERFACE),
                "at": "time",
            },
        )
        observations = []
        values = ("yes", "y2q", "", "805306368")
        for ordinal, (variable, value) in enumerate(
            zip(MODULE.GETVARS, values), start=1
        ):
            intent = {
                "schema": "s20plus_g986n_twrp_fastbootd_getvar_intent_v1",
                "version": MODULE.VERSION,
                "ordinal": ordinal,
                "variable": variable,
                "attempt": 1,
                "replay_permitted": False,
                "at": "time",
            }
            result = MODULE.classic.classify_getvar(
                variable,
                (0, b"", f"{variable}: {value}\n".encode()),
                (),
            )
            result["intent_sha256"] = MODULE.classic.object_sha256(intent)
            result["ordinal"] = ordinal
            MODULE.base.durable_write(
                run_dir / f"query-{ordinal:02d}-intent.json", intent
            )
            MODULE.base.durable_write(
                run_dir / f"query-{ordinal:02d}-result.json", result
            )
            observations.append(result)
        return observations

    def _probe(self, prepared: dict, observations: list[dict]) -> dict:
        return {
            "schema": MODULE.SCHEMA,
            "version": MODULE.VERSION,
            "target": prepared["target"],
            "getvar_order": list(MODULE.GETVARS),
            "getvars": observations,
            "is_userspace_yes": True,
            "volatile_enable_attempts": 1,
            "recovery_adb_selected_command_count": 3,
            "fastboot_command_count": len(MODULE.GETVARS),
            "selected_s20plus_command_attempt_count": 4 + len(MODULE.GETVARS),
            "s22plus_command_count": 0,
            "a90_command_count": 0,
            "other_target_command_count": 0,
            "fastboot_download_phase": False,
            "getvar_all_sent": False,
            "boot_command_sent": False,
            "flash_command_sent": False,
            "erase_command_sent": False,
            "set_active_sent": False,
            "persistent_writes": 0,
            "partition_operations": 0,
            "return_health_pending": True,
            "replay_permitted": False,
            "verdict": MODULE.PENDING_VERDICT,
            "at": "time",
        }

    def test_execute_intents_precede_one_enable_and_fixed_getvars(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, predecessor, recovery, support = self._fixtures(root)
            calls: list[list[str]] = []

            def command(argv: list[str], _timeout: float, _maximum: int):
                calls.append(list(argv))
                if argv[-1] == MODULE.LAUNCH_SCRIPT:
                    self.assertTrue((run_dir / "enable-intent.json").exists())
                    self.assertTrue((root / MODULE.RUN_ROOT_REL / MODULE.CONSUMED_NAME).exists())
                    return 0, b"armed\n", b""
                if argv[1:] == ["devices", "-l"]:
                    return 0, b"List of devices attached\n\n", b""
                variable = argv[-1]
                ordinal = MODULE.GETVARS.index(variable) + 1
                self.assertTrue((run_dir / f"query-{ordinal:02d}-intent.json").exists())
                values = {
                    "is-userspace": "yes",
                    "product": "y2q",
                    "version-bootloader": "",
                    "max-download-size": "805306368",
                }
                return 0, b"", f"{variable}: {values[variable]}\nFinished. Total time: 0.001s\n".encode()

            with (
                mock.patch.object(MODULE, "LIVE_ACTIVE", True),
                mock.patch.object(MODULE, "require_support", return_value=support) as support_check,
                mock.patch.object(MODULE.twrp_d0, "validate_t2_predecessor", return_value=predecessor),
                mock.patch.object(MODULE, "recovery_snapshot", return_value=recovery),
                mock.patch.object(MODULE.classic, "require_fastboot", return_value=support["fastboot"]) as fastboot_check,
            ):
                result = MODULE.connected_census(root, run_dir, command, lambda: endpoint())
            self.assertEqual(support_check.call_count, 3)
            self.assertEqual(fastboot_check.call_count, 5)
            self.assertEqual(result["verdict"], MODULE.PENDING_VERDICT)
            self.assertTrue(result["is_userspace_yes"])
            fastboot_calls = [argv for argv in calls if argv[:3] == ["/fixed/fastboot", "-s", "SERIAL"]]
            self.assertEqual(
                [argv[3:] for argv in fastboot_calls],
                [["getvar", variable] for variable in MODULE.GETVARS],
            )
            flattened = "\n".join(" ".join(argv) for argv in fastboot_calls)
            for forbidden in ("getvar all", " boot ", " flash", " erase", "set_active", " oem"):
                self.assertNotIn(forbidden, flattened)
            returned = {
                "serial_sha256": recovery["serial_sha256"],
                "topology_sha256": recovery["topology_sha256"],
                "other_serial_sha256": [],
                "boot_id_sha256": MODULE.base.sha256_text("android-boot"),
                "health": {
                    "model": "SM-G986N",
                    "device": "y2q",
                    "product_name": "y2qksx",
                    "incremental": "G986NKSS8IYC2",
                    "boot_completed": "1",
                    "bootanim": "stopped",
                    "selinux": "Enforcing",
                },
            }
            with (
                mock.patch.object(MODULE, "require_support", return_value=support) as final_support,
                mock.patch.object(MODULE.classic, "collect_android_health", return_value=returned),
            ):
                final = MODULE.finalize(root, command, lambda: ())
            self.assertEqual(final_support.call_count, 2)
            self.assertEqual(final["verdict"], MODULE.FINAL_PASS)
            self.assertFalse((root / MODULE.SHARED_GUARD_REL).exists())

    def test_non_userspace_endpoint_stops_after_first_query(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, predecessor, recovery, support = self._fixtures(root)
            fastboot_calls = 0

            def command(argv: list[str], _timeout: float, _maximum: int):
                nonlocal fastboot_calls
                if argv[-1] == MODULE.LAUNCH_SCRIPT:
                    return 0, b"armed\n", b""
                if argv[1:] == ["devices", "-l"]:
                    return 0, b"List of devices attached\n\n", b""
                fastboot_calls += 1
                return 0, b"", b"is-userspace: no\nFinished. Total time: 0.001s\n"

            with (
                mock.patch.object(MODULE, "LIVE_ACTIVE", True),
                mock.patch.object(MODULE, "require_support", return_value=support),
                mock.patch.object(MODULE.twrp_d0, "validate_t2_predecessor", return_value=predecessor),
                mock.patch.object(MODULE, "recovery_snapshot", return_value=recovery),
                mock.patch.object(MODULE.classic, "require_fastboot", return_value=support["fastboot"]),
            ):
                with self.assertRaises(MODULE.ReturnRequiredError):
                    MODULE.connected_census(root, run_dir, command, lambda: endpoint())
            self.assertEqual(fastboot_calls, 1)

    def test_oversized_combined_output_stops_before_later_query(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, predecessor, recovery, support = self._fixtures(root)
            fastboot_calls = 0

            def command(argv: list[str], _timeout: float, _maximum: int):
                nonlocal fastboot_calls
                if argv[-1] == MODULE.LAUNCH_SCRIPT:
                    return 0, b"armed\n", b""
                if argv[1:] == ["devices", "-l"]:
                    return 0, b"List of devices attached\n\n", b""
                fastboot_calls += 1
                return (
                    0,
                    b"is-userspace: yes\n" + b"x" * MODULE.MAX_COMMAND_BYTES,
                    b"",
                )

            with (
                mock.patch.object(MODULE, "LIVE_ACTIVE", True),
                mock.patch.object(MODULE, "require_support", return_value=support),
                mock.patch.object(
                    MODULE.twrp_d0,
                    "validate_t2_predecessor",
                    return_value=predecessor,
                ),
                mock.patch.object(MODULE, "recovery_snapshot", return_value=recovery),
                mock.patch.object(
                    MODULE.classic,
                    "require_fastboot",
                    return_value=support["fastboot"],
                ),
            ):
                with self.assertRaises(MODULE.FastbootdCensusError):
                    MODULE.connected_census(root, run_dir, command, lambda: endpoint())
            self.assertEqual(fastboot_calls, 1)

    def test_finalizer_refuses_fastboot_before_android_contact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _run_dir, _prepared, _recovery, _support = self._intent_only_journal(root)
            with mock.patch.object(MODULE.classic, "collect_android_health") as health:
                with self.assertRaises(MODULE.ReturnRequiredError):
                    MODULE.finalize(root, lambda *_args: (_ for _ in ()).throw(AssertionError()), lambda: endpoint())
            health.assert_not_called()

    def test_minimal_forged_terminal_does_not_release_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _prepared, _recovery, _support = self._intent_only_journal(root)
            MODULE.base.durable_write(run_dir / "final-result.json", {"verdict": MODULE.FINAL_PASS})
            with self.assertRaises(MODULE.FastbootdCensusError):
                MODULE.finalize(root, lambda *_args: (_ for _ in ()).throw(AssertionError()), lambda: ())
            self.assertTrue((root / MODULE.SHARED_GUARD_REL).exists())

    def test_broken_entry_symlink_is_not_treated_as_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _prepared, _recovery, _support = self._intent_only_journal(root)
            (run_dir / "entry-observed.json").symlink_to(run_dir / "missing-entry")
            with self.assertRaises(
                (MODULE.FastbootdCensusError, MODULE.classic.FastbootCensusError)
            ):
                MODULE.finalize(
                    root,
                    lambda *_args: (_ for _ in ()).throw(AssertionError()),
                    lambda: (),
                )
            self.assertTrue((root / MODULE.SHARED_GUARD_REL).exists())

    def test_enable_intent_requires_exact_zero_effect_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _prepared, _recovery, _support = self._intent_only_journal(root)
            local_path = run_dir / "enable-intent.json"
            global_path = root / MODULE.RUN_ROOT_REL / MODULE.CONSUMED_NAME
            intent = MODULE.classic.load_json(local_path, "enable intent")
            local_path.unlink()
            global_path.unlink()
            intent["partition_operations"] = 1
            intent["unexpected"] = "field"
            MODULE.base.durable_write(local_path, intent)
            MODULE.base.durable_write(global_path, intent)
            with self.assertRaises(MODULE.FastbootdCensusError):
                MODULE.finalize(
                    root,
                    lambda *_args: (_ for _ in ()).throw(AssertionError()),
                    lambda: (),
                )
            self.assertTrue((root / MODULE.SHARED_GUARD_REL).exists())

    def test_minimal_query_receipts_cannot_form_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, prepared, _recovery, _support = self._intent_only_journal(root)
            observations = self._write_entry_and_queries(run_dir, prepared)
            for ordinal, result in enumerate(observations, start=1):
                path = run_dir / f"query-{ordinal:02d}-result.json"
                path.unlink()
                minimal = {
                    key: result[key]
                    for key in (
                        "schema",
                        "version",
                        "ordinal",
                        "variable",
                        "intent_sha256",
                        "status",
                        "value",
                    )
                }
                MODULE.base.durable_write(path, minimal)
                observations[ordinal - 1] = minimal
            MODULE.base.durable_write(
                run_dir / "probe-result.json", self._probe(prepared, observations)
            )
            with self.assertRaises(MODULE.FastbootdCensusError):
                MODULE.finalize(
                    root,
                    lambda *_args: (_ for _ in ()).throw(AssertionError()),
                    lambda: (),
                )
            self.assertTrue((root / MODULE.SHARED_GUARD_REL).exists())

    def test_probe_rejects_every_claimed_mutation_or_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, prepared, _recovery, _support = self._intent_only_journal(root)
            observations = self._write_entry_and_queries(run_dir, prepared)
            probe = self._probe(prepared, observations)
            for key in (
                "fastboot_download_phase",
                "getvar_all_sent",
                "boot_command_sent",
                "flash_command_sent",
                "erase_command_sent",
                "set_active_sent",
                "replay_permitted",
            ):
                probe[key] = True
            probe["persistent_writes"] = 99
            probe["partition_operations"] = 99
            MODULE.base.durable_write(run_dir / "probe-result.json", probe)
            with self.assertRaises(MODULE.FastbootdCensusError):
                MODULE.finalize(
                    root,
                    lambda *_args: (_ for _ in ()).throw(AssertionError()),
                    lambda: (),
                )
            self.assertTrue((root / MODULE.SHARED_GUARD_REL).exists())

    def test_result_without_intent_does_not_close_no_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _prepared, _recovery, _support = self._intent_only_journal(root)
            MODULE.base.durable_write(
                run_dir / "query-01-result.json",
                {"schema": "malformed-result-without-intent"},
            )
            with self.assertRaises(MODULE.FastbootdCensusError):
                MODULE.finalize(root, lambda *_args: (_ for _ in ()).throw(AssertionError()), lambda: ())
            self.assertTrue((root / MODULE.SHARED_GUARD_REL).exists())

    def test_probe_without_entry_observation_cannot_be_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, prepared, _recovery, _support = self._intent_only_journal(root)
            empty_sha = MODULE.hashlib.sha256(b"").hexdigest()
            MODULE.base.durable_write(
                run_dir / "enable-result.json",
                {
                    "schema": "s20plus_g986n_twrp_fastbootd_enable_result_v1",
                    "version": MODULE.VERSION,
                    "armed": True,
                    "returncode": 0,
                    "stdout_sha256": empty_sha,
                    "stderr_sha256": empty_sha,
                    "acquisition_error_sha256": None,
                    "replay_permitted": False,
                    "at": "time",
                },
            )
            observations = []
            values = ("yes", "y2q", "", "805306368")
            for ordinal, (variable, value) in enumerate(zip(MODULE.GETVARS, values), start=1):
                intent = {
                    "schema": "s20plus_g986n_twrp_fastbootd_getvar_intent_v1",
                    "version": MODULE.VERSION,
                    "ordinal": ordinal,
                    "variable": variable,
                    "attempt": 1,
                    "replay_permitted": False,
                    "at": "time",
                }
                result = MODULE.classic.classify_getvar(
                    variable,
                    (0, b"", f"{variable}: {value}\n".encode()),
                    (),
                )
                result["intent_sha256"] = MODULE.classic.object_sha256(intent)
                result["ordinal"] = ordinal
                MODULE.base.durable_write(run_dir / f"query-{ordinal:02d}-intent.json", intent)
                MODULE.base.durable_write(run_dir / f"query-{ordinal:02d}-result.json", result)
                observations.append(result)
            MODULE.base.durable_write(
                run_dir / "probe-result.json",
                {
                    "schema": MODULE.SCHEMA,
                    "version": MODULE.VERSION,
                    "target": prepared["target"],
                    "getvar_order": list(MODULE.GETVARS),
                    "getvars": observations,
                    "is_userspace_yes": True,
                    "volatile_enable_attempts": 1,
                    "recovery_adb_selected_command_count": 3,
                    "fastboot_command_count": len(MODULE.GETVARS),
                    "selected_s20plus_command_attempt_count": 4 + len(MODULE.GETVARS),
                    "s22plus_command_count": 0,
                    "a90_command_count": 0,
                    "other_target_command_count": 0,
                    "fastboot_download_phase": False,
                    "getvar_all_sent": False,
                    "boot_command_sent": False,
                    "flash_command_sent": False,
                    "erase_command_sent": False,
                    "set_active_sent": False,
                    "persistent_writes": 0,
                    "partition_operations": 0,
                    "return_health_pending": True,
                    "replay_permitted": False,
                    "verdict": MODULE.PENDING_VERDICT,
                    "at": "time",
                },
            )
            with self.assertRaises(MODULE.FastbootdCensusError):
                MODULE.finalize(root, lambda *_args: (_ for _ in ()).throw(AssertionError()), lambda: ())
            self.assertTrue((root / MODULE.SHARED_GUARD_REL).exists())

    def test_finalize_raw_capture_directories_are_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            run_dir.mkdir()
            first = MODULE.classic.allocate_finalize_capture_dir(run_dir)
            second = MODULE.classic.allocate_finalize_capture_dir(run_dir)
            self.assertNotEqual(first, second)
            source = SCRIPT.read_text(encoding="utf-8")
            self.assertIn("capture_dir=classic.allocate_finalize_capture_dir(run_dir)", source)

    def test_guard_only_cut_has_zero_device_pre_effect_abort(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _predecessor, _recovery, _support = self._fixtures(root)
            MODULE.acquire_guard(root, run_dir)
            result = MODULE.abort_pre_effect(root)
            self.assertNotIn("device_commands", result)
            self.assertEqual(result["device_effects"], 0)
            self.assertFalse((root / MODULE.SHARED_GUARD_REL).exists())

    def test_foreign_action_guard_is_never_released(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _predecessor, _recovery, _support = self._fixtures(root)
            MODULE.acquire_guard(root, run_dir)
            path = root / MODULE.SHARED_GUARD_REL
            value = MODULE.classic.load_json(path, "shared action guard")
            path.unlink()
            value["action"] = "foreign-action"
            value["extra"] = "foreign"
            MODULE.base.durable_write(path, value)
            with self.assertRaises(MODULE.FastbootdCensusError):
                MODULE.abort_pre_effect(root)
            self.assertTrue(MODULE.lexists(path))

    def test_pre_effect_abort_receipt_cut_resumes_guard_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _predecessor, _recovery, _support = self._fixtures(root)
            MODULE.acquire_guard(root, run_dir)
            receipt = {
                "schema": "s20plus_g986n_twrp_fastbootd_pre_effect_abort_v1",
                "version": MODULE.VERSION,
                "prepared_sha256": None,
                "device_effects": 0,
                "persistent_writes": 0,
                "partition_operations": 0,
                "verdict": "ABORTED_S20PLUS_G986N_TWRP_FASTBOOTD_BEFORE_EFFECT",
                "at": "time",
            }
            MODULE.base.durable_write(run_dir / "pre-effect-abort.json", receipt)
            self.assertEqual(MODULE.abort_pre_effect(root), receipt)
            self.assertFalse((root / MODULE.SHARED_GUARD_REL).exists())

    def test_local_intent_alone_is_consumed_for_exception_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _predecessor, _recovery, _support = self._fixtures(root)
            MODULE.base.durable_write(run_dir / "enable-intent.json", {"cut": True})
            self.assertTrue(MODULE.enable_is_consumed(root, run_dir))

    def test_local_intent_cut_reconstructs_only_consumed_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir, _prepared, _recovery, _support = self._intent_only_journal(root)
            intent = MODULE.classic.load_json(
                run_dir / "enable-intent.json", "local enable intent"
            )
            (root / MODULE.RUN_ROOT_REL / MODULE.CONSUMED_NAME).unlink()
            self.assertEqual(MODULE.resolve_consumed_run(root), run_dir)
            self.assertEqual(
                MODULE.classic.load_json(
                    root / MODULE.RUN_ROOT_REL / MODULE.CONSUMED_NAME,
                    "consumed",
                ),
                intent,
            )

    def test_contract_records_consumed_no_proof_terminal(self) -> None:
        contract = (ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md").read_text()
        agents = (ROOT / "AGENTS.md").read_text()
        self.assertIn("TWRP FASTBOOTD CENSUS CONSUMED", contract)
        self.assertIn("TWRP-fastbootd census consumed", agents)
        self.assertNotIn("TWRP-fastbootd census active", agents)


if __name__ == "__main__":
    unittest.main()
