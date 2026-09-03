import contextlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s20plus_g986n_fastboot_boot_support_f1.py"

import sys

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("s20_fastboot_boot_support", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class S20FastbootBootSupportF1Tests(unittest.TestCase):
    def health(self, boot="a" * 64):
        return {
            "serial": "S20SERIAL",
            "devpath": "usb:3-2.1",
            "node": "3-2.1",
            "serial_sha256": MODULE.census.base.sha256_text("S20SERIAL"),
            "topology_sha256": MODULE.census.base.sha256_text("usb:3-2.1"),
            "boot_id_sha256": boot,
            "other_serial_sha256": [],
            "health": {
                "model": "SM-G986N",
                "device": "y2q",
                "product_name": "y2qksx",
                "incremental": "G986NKSS8IYC2",
                "boot_completed": "1",
                "bootanim": "stopped",
                "selinux": "Enforcing",
            },
            "adb": {"path": "/private/adb", "sha256": "1" * 64},
        }

    def closure(self):
        return {
            "census_source": {
                "path": str(MODULE.CENSUS_SOURCE),
                "size": MODULE.CENSUS_SOURCE_SIZE,
                "sha256": MODULE.CENSUS_SOURCE_SHA256,
            },
            "raw_capture_source": {
                "path": str(MODULE.RAW_CAPTURE_SOURCE),
                "size": MODULE.RAW_CAPTURE_SOURCE_SIZE,
                "sha256": MODULE.RAW_CAPTURE_SOURCE_SHA256,
            },
            "d0_inventory_source": {
                "path": str(MODULE.D0_INVENTORY_SOURCE),
                "size": MODULE.D0_INVENTORY_SOURCE_SIZE,
                "sha256": MODULE.D0_INVENTORY_SOURCE_SHA256,
            },
            "routine_d0_source": {
                "path": str(MODULE.ROUTINE_D0_SOURCE),
                "size": MODULE.ROUTINE_D0_SOURCE_SIZE,
                "sha256": MODULE.ROUTINE_D0_SOURCE_SHA256,
            },
            "boot_image": {
                "path": str(MODULE.BOOT_IMAGE),
                "size": MODULE.BOOT_IMAGE_SIZE,
                "sha256": MODULE.BOOT_IMAGE_SHA256,
            },
            "p0_terminal": {"sha256": "2" * 64},
            "p0_final_health": {"sha256": "3" * 64},
            "p0_rollback_result": {"sha256": "4" * 64},
            "fastboot_census_probe": {"sha256": "5" * 64},
            "fastboot_census_terminal": {"sha256": "6" * 64},
        }

    def fastboot(self):
        return {
            "path": "/private/fastboot",
            "size": MODULE.census.FASTBOOT_SIZE,
            "sha256": MODULE.census.FASTBOOT_SHA256,
            "version": MODULE.census.FASTBOOT_VERSION,
        }

    @contextlib.contextmanager
    def private_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_root = root / "runs"
            guard = root / "shared/active-action.json"
            consumed = run_root / "consumed-boot-intent.json"
            with mock.patch.object(MODULE, "RUN_ROOT", run_root), mock.patch.object(
                MODULE, "SHARED_GUARD", guard
            ), mock.patch.object(MODULE, "CONSUMED", consumed):
                yield root

    def seed_prepared(self):
        run_dir = MODULE.allocate_run_dir()
        MODULE.acquire_guard(run_dir)
        health = self.health()
        binding = {
            "schema": "s20plus_g986n_fastboot_boot_support_binding_v1",
            "version": MODULE.VERSION,
            "run_dir_sha256": MODULE.census.base.sha256_text(str(run_dir)),
            "target": {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "incremental": "G986NKSS8IYC2",
                "serial_sha256": health["serial_sha256"],
                "topology_sha256": health["topology_sha256"],
                "boot_id_sha256": health["boot_id_sha256"],
                "other_serial_sha256": [],
            },
            "boot_image": self.closure()["boot_image"],
            "adb": health["adb"],
            "fastboot": self.fastboot(),
            "predecessors": self.closure(),
            "command_shape": [
                "fastboot",
                "-s",
                "BOUND_SERIAL",
                "boot",
                "BOUND_BOOT_IMAGE",
            ],
            "physical_recovery": "power-cycle-or-START-to-persistent-resident-boot",
            "attempt": 1,
            "no_replay": True,
        }
        prepared = {
            "schema": "s20plus_g986n_fastboot_boot_support_prepared_v1",
            "version": MODULE.VERSION,
            "binding": binding,
            "binding_sha256": MODULE.census.object_sha256(binding),
            "approval": MODULE.APPROVAL_PREFIX
            + MODULE.census.object_sha256(binding),
            "health": health["health"],
            "persistent_device_writes": False,
            "partition_writes": 0,
            "persistent_mutation": False,
            "partition_access": False,
            "at": MODULE.now(),
        }
        MODULE.census.base.durable_write(run_dir / "prepared.json", prepared)
        return run_dir, prepared

    def write_entry(self, run_dir, prepared):
        target = prepared["binding"]["target"]
        MODULE.census.base.durable_write(
            run_dir / "entry-observed.json",
            {
                "schema": "s20plus_g986n_fastboot_boot_support_entry_v1",
                "version": MODULE.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "serial_sha256": target["serial_sha256"],
                "topology_sha256": target["topology_sha256"],
                "at": MODULE.now(),
            },
        )

    def test_real_static_closure_binds_known_good_resident_boot(self):
        result = MODULE.static_closure()
        self.assertEqual(
            result["boot_image"]["sha256"], MODULE.BOOT_IMAGE_SHA256
        )
        self.assertEqual(result["boot_image"]["size"], 67_108_864)
        self.assertEqual(
            result["fastboot_census_terminal"]["sha256"],
            MODULE.CENSUS_FINAL_SHA256,
        )
        self.assertEqual(
            result["raw_capture_source"]["sha256"],
            MODULE.RAW_CAPTURE_SOURCE_SHA256,
        )

    def test_plan_is_active_and_has_only_one_boot_command(self):
        plan = MODULE.plan()
        self.assertTrue(plan["live_active"])
        self.assertEqual(plan["fastboot_commands"], [["boot", "BOUND_BOOT_IMAGE"]])
        self.assertEqual(plan["command_count"], 1)
        self.assertEqual(plan["ram_payload_transfer_attempts"], 1)
        self.assertEqual(plan["partition_writes"], 0)
        options = MODULE.parser()._option_string_actions
        for forbidden in (
            "--serial",
            "--image",
            "--artifact",
            "--flash",
            "--erase",
            "--reboot",
            "--run-dir",
        ):
            self.assertNotIn(forbidden, options)

    def test_prepare_emits_exact_approval_without_fastboot_contact(self):
        with self.private_paths():
            health = self.health()
            command = mock.Mock()
            with mock.patch.object(MODULE, "LIVE_ACTIVE", True), mock.patch.object(
                MODULE, "static_closure", return_value=self.closure()
            ), mock.patch.object(
                MODULE.census, "RawCommand", return_value=command
            ), mock.patch.object(
                MODULE.census, "collect_android_health", return_value=health
            ), mock.patch.object(
                MODULE.census, "require_fastboot", return_value=self.fastboot()
            ):
                run_dir, approval = MODULE.prepare()
            self.assertTrue(approval.startswith(MODULE.APPROVAL_PREFIX))
            self.assertTrue((run_dir / "prepared.json").is_file())
            self.assertTrue(MODULE.SHARED_GUARD.is_file())
            self.assertFalse(MODULE.CONSUMED.exists())
            command.assert_not_called()

            first_approval = approval
            MODULE.abort_pre_entry()
            with mock.patch.object(MODULE, "LIVE_ACTIVE", True), mock.patch.object(
                MODULE, "static_closure", return_value=self.closure()
            ), mock.patch.object(
                MODULE.census, "RawCommand", return_value=command
            ), mock.patch.object(
                MODULE.census, "collect_android_health", return_value=health
            ), mock.patch.object(
                MODULE.census, "require_fastboot", return_value=self.fastboot()
            ):
                _second_run, second_approval = MODULE.prepare()
                self.assertNotEqual(first_approval, second_approval)
                with self.assertRaisesRegex(MODULE.SupportProbeError, "approval"):
                    MODULE.execute(first_approval)

    def test_execute_sends_exactly_one_boot_after_durable_intent(self):
        with self.private_paths():
            run_dir, prepared = self.seed_prepared()
            calls = []

            def command(argv, _timeout, _maximum):
                calls.append(argv)
                if argv[-2:] == ["devices", "-l"]:
                    return 0, b"List of devices attached\n", b""
                if "boot" in argv:
                    self.assertTrue((run_dir / "boot-intent.json").is_file())
                    return (
                        0,
                        b"",
                        b"Sending 'boot.img' OKAY [  1.000s]\n"
                        b"Booting             OKAY [  0.100s]\n",
                    )
                raise AssertionError(argv)

            endpoint = {"serial": "S20SERIAL"}
            with mock.patch.object(MODULE, "LIVE_ACTIVE", True), mock.patch.object(
                MODULE, "static_closure", return_value=self.closure()
            ), mock.patch.object(
                MODULE.census, "RawCommand", return_value=command
            ), mock.patch.object(
                MODULE.census,
                "collect_android_health",
                return_value=self.health(),
            ), mock.patch.object(
                MODULE.census, "wait_for_fastboot", return_value=endpoint
            ), mock.patch.object(
                MODULE.census, "validate_fastboot_usb", return_value=endpoint
            ), mock.patch.object(
                MODULE.census, "require_fastboot", return_value=self.fastboot()
            ):
                result = MODULE.execute(prepared["approval"], ready=lambda: None)
            boot_calls = [argv for argv in calls if "boot" in argv]
            self.assertEqual(
                boot_calls,
                [
                    [
                        "/private/fastboot",
                        "-s",
                        "S20SERIAL",
                        "boot",
                        str(MODULE.BOOT_IMAGE),
                    ]
                ],
            )
            self.assertEqual(result["status"], "COMMAND_ACCEPTED")
            self.assertTrue(MODULE.CONSUMED.is_file())
            encoded = json.dumps(result)
            self.assertNotIn("S20SERIAL", encoded)
            self.assertNotIn(str(MODULE.BOOT_IMAGE), encoded)
            with mock.patch.object(MODULE, "LIVE_ACTIVE", True), mock.patch.object(
                MODULE.census, "RawCommand"
            ) as constructor:
                with self.assertRaisesRegex(MODULE.SupportProbeError, "already consumed"):
                    MODULE.execute(prepared["approval"])
                constructor.assert_not_called()

    def test_classification_does_not_upgrade_partial_or_unknown_output(self):
        accepted = MODULE.classify_boot(
            (
                0,
                b"",
                b"Sending 'boot.img' OKAY\nBooting OKAY\n",
            ),
            (),
        )
        unsupported = MODULE.classify_boot(
            (
                1,
                b"",
                b"FAILED (remote: unknown command)\n",
            ),
            (),
        )
        actual_unsupported = MODULE.classify_boot(
            (
                1,
                b"",
                b"Booting             FAILED (remote: 'unknown command')\n"
                b"fastboot: error: Command failed\n",
            ),
            (),
        )
        uncertain = MODULE.classify_boot(
            (
                0,
                b"",
                b"Sending 'boot.img' OKAY\nBooting FAILED\n",
            ),
            (),
        )
        contradictory = MODULE.classify_boot(
            (
                0,
                b"",
                b"Booting OKAY\nFAILED remote contradiction\n",
            ),
            (),
        )
        split_marker = MODULE.classify_boot(
            (
                1,
                b"",
                b"FAILED (remote: permission denied)\nnot supported by wrapper\n",
            ),
            (),
        )
        sending_failed = MODULE.classify_boot(
            (
                0,
                b"",
                b"Sending 'boot.img' FAILED (remote: denied)\nBooting OKAY\n",
            ),
            (),
        )
        conflicting_unsupported = MODULE.classify_boot(
            (
                1,
                b"",
                b"Booting OKAY\nBooting FAILED (remote: unknown command)\n",
            ),
            (),
        )
        multiple_remote = MODULE.classify_boot(
            (
                1,
                b"",
                b"Booting FAILED (remote: unknown command)\n"
                b"FAILED (remote: not supported)\n",
            ),
            (),
        )
        self.assertEqual(accepted["status"], "COMMAND_ACCEPTED")
        self.assertEqual(unsupported["status"], "UNSUPPORTED")
        self.assertEqual(actual_unsupported["status"], "UNSUPPORTED")
        self.assertEqual(uncertain["status"], "UNCERTAIN")
        self.assertEqual(contradictory["status"], "UNCERTAIN")
        self.assertEqual(split_marker["status"], "UNCERTAIN")
        self.assertEqual(sending_failed["status"], "UNCERTAIN")
        self.assertEqual(conflicting_unsupported["status"], "UNCERTAIN")
        self.assertEqual(multiple_remote["status"], "UNCERTAIN")
        with self.assertRaisesRegex(MODULE.SupportProbeError, "combined bound"):
            MODULE.classify_boot((0, b"a" * 20_000, b"b" * 20_000), ())
        with self.assertRaisesRegex(MODULE.SupportProbeError, "redacted.*bound"):
            MODULE.classify_boot((1, b"x" * 2_000, b""), ("x",))

    def test_post_tool_closure_runs_before_parser_error_or_command_raise(self):
        for mode in ("invalid-utf8", "command-raise"):
            with self.subTest(mode=mode), self.private_paths():
                _run_dir, prepared = self.seed_prepared()

                def command(argv, _timeout, _maximum):
                    if argv[-2:] == ["devices", "-l"]:
                        return 0, b"List of devices attached\n", b""
                    if "boot" in argv:
                        if mode == "command-raise":
                            raise RuntimeError("raw acquisition failure")
                        return 0, b"\xff", b""
                    raise AssertionError(argv)

                closure_check = mock.Mock(return_value=self.closure())
                endpoint = {"serial": "S20SERIAL"}
                patches = (
                    mock.patch.object(MODULE, "LIVE_ACTIVE", True),
                    mock.patch.object(MODULE, "static_closure", closure_check),
                    mock.patch.object(MODULE.census, "RawCommand", return_value=command),
                    mock.patch.object(
                        MODULE.census,
                        "collect_android_health",
                        return_value=self.health(),
                    ),
                    mock.patch.object(
                        MODULE.census, "wait_for_fastboot", return_value=endpoint
                    ),
                    mock.patch.object(
                        MODULE.census, "validate_fastboot_usb", return_value=endpoint
                    ),
                    mock.patch.object(
                        MODULE.census, "require_fastboot", return_value=self.fastboot()
                    ),
                )
                with contextlib.ExitStack() as stack:
                    for patcher in patches:
                        stack.enter_context(patcher)
                    expected = RuntimeError if mode == "command-raise" else MODULE.SupportProbeError
                    with self.assertRaises(expected):
                        MODULE.execute(prepared["approval"], ready=lambda: None)
                self.assertEqual(closure_check.call_count, 3)

    def test_wrong_approval_stops_before_entry_or_command(self):
        with self.private_paths():
            run_dir, _prepared = self.seed_prepared()
            command = mock.Mock()
            with mock.patch.object(MODULE, "LIVE_ACTIVE", True), mock.patch.object(
                MODULE.census, "RawCommand", return_value=command
            ):
                with self.assertRaisesRegex(MODULE.SupportProbeError, "approval"):
                    MODULE.execute("wrong")
            command.assert_not_called()
            self.assertFalse(MODULE.CONSUMED.exists())
            self.assertFalse((run_dir / "boot-intent.json").exists())

    def test_adb_tool_drift_stops_before_entry(self):
        with self.private_paths():
            _run_dir, prepared = self.seed_prepared()
            drifted = self.health()
            drifted["adb"] = {"path": "/changed/adb", "sha256": "9" * 64}
            with mock.patch.object(MODULE, "LIVE_ACTIVE", True), mock.patch.object(
                MODULE, "static_closure", return_value=self.closure()
            ), mock.patch.object(
                MODULE.census, "RawCommand", return_value=mock.Mock()
            ), mock.patch.object(
                MODULE.census, "collect_android_health", return_value=drifted
            ):
                with self.assertRaisesRegex(MODULE.SupportProbeError, "target or boot"):
                    MODULE.execute(prepared["approval"])
            self.assertFalse(MODULE.CONSUMED.exists())

    def test_pre_entry_abort_releases_only_zero_effect_guard(self):
        with self.private_paths():
            run_dir, _prepared = self.seed_prepared()
            result = MODULE.abort_pre_entry()
            self.assertEqual(result, run_dir / "pre-entry-abort.json")
            self.assertFalse(MODULE.SHARED_GUARD.exists())
            self.assertFalse(MODULE.CONSUMED.exists())
            value = json.loads(result.read_text())
            self.assertEqual(value["fastboot_boot_attempts"], 0)
            self.assertEqual(value["device_effects"], 0)

    def test_guard_only_cut_aborts_without_prepared_or_device_contact(self):
        with self.private_paths():
            run_dir = MODULE.allocate_run_dir()
            MODULE.acquire_guard(run_dir)
            result = MODULE.abort_pre_entry()
            value = json.loads(result.read_text())
            self.assertFalse(value["prepared_present"])
            self.assertIsNone(value["binding_sha256"])
            self.assertFalse(MODULE.SHARED_GUARD.exists())

    def test_malformed_foreign_guard_is_never_released(self):
        with self.private_paths():
            MODULE.SHARED_GUARD.parent.mkdir(parents=True)
            MODULE.census.base.durable_write(
                MODULE.SHARED_GUARD, {"schema": "foreign"}
            )
            with self.assertRaises(MODULE.SupportProbeError):
                MODULE.abort_pre_entry()
            self.assertTrue(MODULE.SHARED_GUARD.exists())

    def test_pre_entry_abort_resumes_after_receipt_before_guard_release_cut(self):
        with self.private_paths():
            run_dir, _prepared = self.seed_prepared()
            with mock.patch.object(
                MODULE, "release_guard", side_effect=OSError("cut")
            ):
                with self.assertRaises(OSError):
                    MODULE.abort_pre_entry()
            self.assertTrue((run_dir / "pre-entry-abort.json").is_file())
            self.assertTrue(MODULE.SHARED_GUARD.is_file())
            result = MODULE.abort_pre_entry()
            self.assertEqual(result, run_dir / "pre-entry-abort.json")
            self.assertFalse(MODULE.SHARED_GUARD.exists())

    def test_pre_entry_abort_treats_broken_effect_symlink_as_present(self):
        with self.private_paths():
            run_dir, _prepared = self.seed_prepared()
            (run_dir / "boot-intent.json").symlink_to(run_dir / "missing")
            with self.assertRaisesRegex(MODULE.SupportProbeError, "effect evidence"):
                MODULE.abort_pre_entry()
            self.assertTrue(MODULE.SHARED_GUARD.exists())

    def test_finalizer_maps_accepted_result_and_releases_guard(self):
        with self.private_paths():
            run_dir, prepared = self.seed_prepared()
            MODULE.create_entry_intent(run_dir, prepared)
            self.write_entry(run_dir, prepared)
            intent = {
                "schema": "s20plus_g986n_fastboot_boot_support_command_intent_v1",
                "version": MODULE.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "command_shape": prepared["binding"]["command_shape"],
                "boot_image_sha256": MODULE.BOOT_IMAGE_SHA256,
                "attempt": 1,
                "no_replay": True,
                "at": MODULE.now(),
            }
            MODULE.census.base.durable_write(run_dir / "boot-intent.json", intent)
            output = "Booting OKAY"
            result = {
                "schema": "s20plus_g986n_fastboot_boot_support_command_result_v1",
                "version": MODULE.VERSION,
                "status": "COMMAND_ACCEPTED",
                "returncode": 0,
                "output": output,
                "output_sha256": MODULE.hashlib.sha256(output.encode()).hexdigest(),
                "replay_permitted": False,
                "at": MODULE.now(),
                "intent_sha256": MODULE.census.object_sha256(intent),
            }
            MODULE.census.base.durable_write(run_dir / "boot-result.json", result)
            returned = self.health(boot="b" * 64)
            with mock.patch.object(
                MODULE.census, "collect_android_health", return_value=returned
            ):
                terminal = MODULE.finalize(
                    mock.Mock(),
                    usb_inventory=lambda: (),
                )
            self.assertEqual(terminal["verdict"], MODULE.PASS_SUPPORTED)
            self.assertFalse(MODULE.SHARED_GUARD.exists())
            self.assertTrue(MODULE.CONSUMED.exists())

    def test_valid_intent_without_result_closes_no_proof_after_fresh_return(self):
        with self.private_paths():
            run_dir, prepared = self.seed_prepared()
            MODULE.create_entry_intent(run_dir, prepared)
            self.write_entry(run_dir, prepared)
            MODULE.census.base.durable_write(
                run_dir / "boot-intent.json",
                {
                    "schema": "s20plus_g986n_fastboot_boot_support_command_intent_v1",
                    "version": MODULE.VERSION,
                    "binding_sha256": prepared["binding_sha256"],
                    "command_shape": prepared["binding"]["command_shape"],
                    "boot_image_sha256": MODULE.BOOT_IMAGE_SHA256,
                    "attempt": 1,
                    "no_replay": True,
                    "at": MODULE.now(),
                },
            )
            with mock.patch.object(
                MODULE.census,
                "collect_android_health",
                return_value=self.health(boot="b" * 64),
            ):
                terminal = MODULE.finalize(mock.Mock(), usb_inventory=lambda: ())
            self.assertEqual(terminal["verdict"], MODULE.NO_PROOF)
            self.assertEqual(terminal["command_status"], "NO_RESULT")
            self.assertFalse(MODULE.SHARED_GUARD.exists())

    def test_terminal_cut_reemits_and_releases_without_device_contact(self):
        with self.private_paths():
            run_dir, prepared = self.seed_prepared()
            MODULE.create_entry_intent(run_dir, prepared)
            self.write_entry(run_dir, prepared)
            intent = {
                "schema": "s20plus_g986n_fastboot_boot_support_command_intent_v1",
                "version": MODULE.VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "command_shape": prepared["binding"]["command_shape"],
                "boot_image_sha256": MODULE.BOOT_IMAGE_SHA256,
                "attempt": 1,
                "no_replay": True,
                "at": MODULE.now(),
            }
            MODULE.census.base.durable_write(run_dir / "boot-intent.json", intent)
            output = "Booting OKAY"
            MODULE.census.base.durable_write(
                run_dir / "boot-result.json",
                {
                    "schema": "s20plus_g986n_fastboot_boot_support_command_result_v1",
                    "version": MODULE.VERSION,
                    "status": "COMMAND_ACCEPTED",
                    "returncode": 0,
                    "output": output,
                    "output_sha256": MODULE.hashlib.sha256(output.encode()).hexdigest(),
                    "replay_permitted": False,
                    "at": MODULE.now(),
                    "intent_sha256": MODULE.census.object_sha256(intent),
                },
            )
            with mock.patch.object(
                MODULE.census,
                "collect_android_health",
                return_value=self.health(boot="b" * 64),
            ), mock.patch.object(
                MODULE, "release_guard", side_effect=OSError("cut")
            ):
                with self.assertRaises(OSError):
                    MODULE.finalize(mock.Mock(), usb_inventory=lambda: ())
            self.assertTrue((run_dir / "final-result.json").is_file())
            self.assertTrue(MODULE.SHARED_GUARD.is_file())

            def forbidden(*_args):
                raise AssertionError("terminal re-emission contacted device")

            terminal = MODULE.finalize(forbidden, usb_inventory=forbidden)
            self.assertEqual(terminal["verdict"], MODULE.PASS_SUPPORTED)
            self.assertFalse(MODULE.SHARED_GUARD.exists())

    def test_partial_terminal_cannot_release_guard(self):
        with self.private_paths():
            run_dir, prepared = self.seed_prepared()
            MODULE.create_entry_intent(run_dir, prepared)
            MODULE.census.base.durable_write(
                run_dir / "final-result.json",
                {"verdict": MODULE.PASS_SUPPORTED},
            )
            with self.assertRaises(MODULE.SupportProbeError):
                MODULE.finalize(mock.Mock(), usb_inventory=lambda: ())
            self.assertTrue(MODULE.SHARED_GUARD.exists())

    def test_malformed_intent_only_cannot_close_as_no_proof(self):
        with self.private_paths():
            run_dir, prepared = self.seed_prepared()
            MODULE.create_entry_intent(run_dir, prepared)
            self.write_entry(run_dir, prepared)
            MODULE.census.base.durable_write(
                run_dir / "boot-intent.json", {"malformed": True}
            )
            with mock.patch.object(
                MODULE.census,
                "collect_android_health",
                return_value=self.health(boot="b" * 64),
            ):
                with self.assertRaisesRegex(MODULE.SupportProbeError, "intent differs"):
                    MODULE.finalize(mock.Mock(), usb_inventory=lambda: ())
            self.assertTrue(MODULE.SHARED_GUARD.exists())

    def test_boot_intent_without_entry_observation_cannot_finalize(self):
        with self.private_paths():
            run_dir, prepared = self.seed_prepared()
            MODULE.create_entry_intent(run_dir, prepared)
            MODULE.census.base.durable_write(
                run_dir / "boot-intent.json",
                {
                    "schema": "s20plus_g986n_fastboot_boot_support_command_intent_v1",
                    "version": MODULE.VERSION,
                    "binding_sha256": prepared["binding_sha256"],
                    "command_shape": prepared["binding"]["command_shape"],
                    "boot_image_sha256": MODULE.BOOT_IMAGE_SHA256,
                    "attempt": 1,
                    "no_replay": True,
                    "at": MODULE.now(),
                },
            )
            with mock.patch.object(
                MODULE.census,
                "collect_android_health",
                return_value=self.health(boot="b" * 64),
            ):
                with self.assertRaisesRegex(
                    MODULE.SupportProbeError, "no valid entry observation"
                ):
                    MODULE.finalize(mock.Mock(), usb_inventory=lambda: ())
            self.assertTrue(MODULE.SHARED_GUARD.exists())

    def test_contract_names_only_exact_support_probe(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        contract = (
            ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        self.assertIn("fastboot-boot support", agents)
        self.assertIn("Fastboot Boot Support Probe", contract)
        self.assertIn(SCRIPT.name, contract)
        self.assertIn(
            "Status: **CONSUMED - NO_PROOF - HEALTHY RETURN; TERMINAL OWNER ONLY**",
            contract,
        )


if __name__ == "__main__":
    unittest.main()
