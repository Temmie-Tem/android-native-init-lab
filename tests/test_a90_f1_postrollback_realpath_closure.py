"""Host-only tests for the A90 post-rollback tty-realpath closure helper."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "workspace/public/src/scripts/server-distro"
    / "a90_f1_postrollback_realpath_closure.py"
)
SPEC = importlib.util.spec_from_file_location("a90_postrollback_closure", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
closure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(closure)


class PostRollbackRealpathClosureTests(unittest.TestCase):
    def test_reviewed_helper_sha_is_an_external_execution_gate(self) -> None:
        with mock.patch.object(
            closure,
            "_helper_sha256",
            return_value="a" * 64,
        ):
            self.assertEqual(
                closure.require_reviewed_helper_sha256("a" * 64),
                "a" * 64,
            )
            with self.assertRaisesRegex(closure.ClosureError, "reviewed SHA256"):
                closure.require_reviewed_helper_sha256("b" * 64)
            with self.assertRaisesRegex(closure.ClosureError, "reviewed SHA256"):
                closure.require_reviewed_helper_sha256("not-a-sha")

    def test_open_action_contract_is_exact_and_has_one_rollback(self) -> None:
        self.assertEqual(closure.OPEN_ACTIONS.count("candidate-transfer-started"), 1)
        self.assertEqual(closure.OPEN_ACTIONS.count("candidate-flashed"), 1)
        self.assertEqual(closure.OPEN_ACTIONS.count("attended-handoff-started"), 1)
        self.assertEqual(closure.OPEN_ACTIONS.count("rollback-transfer-started"), 1)
        self.assertEqual(closure.OPEN_ACTIONS.count("rollback-flashed"), 1)
        self.assertNotIn("rollback-boot-ready", closure.OPEN_ACTIONS)
        self.assertNotIn("closed", closure.OPEN_ACTIONS)

    def test_expected_rollback_phases_require_write_and_readback_without_from_native(self) -> None:
        self.assertEqual(
            set(closure.EXPECTED_ROLLBACK_PHASES),
            closure.ROLLBACK_PHASE_KEYS,
        )
        self.assertFalse(
            closure.EXPECTED_ROLLBACK_PHASES["native_recovery_requested"]
        )
        for name in (
            "local_image_validated",
            "recovery_endpoint_selected",
            "payload_transfer_started",
            "boot_write_started",
            "boot_write_completed",
            "readback_completed",
        ):
            self.assertTrue(closure.EXPECTED_ROLLBACK_PHASES[name])

    def test_result_is_no_proof_one_candidate_one_rollback(self) -> None:
        spec = SimpleNamespace(
            stage=SimpleNamespace(
                run_id="a90-v3404-debian-f1-20260731-01",
                manifest_sha256="a" * 64,
            )
        )
        result = closure._result(spec)
        self.assertEqual(
            result["status"],
            "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
        )
        self.assertEqual(result["candidate_transfer_count"], 1)
        self.assertEqual(result["rollback_transfer_count"], 1)
        self.assertFalse(result["candidate_replay"])
        self.assertFalse(result["debian_pid1_proven"])
        self.assertTrue(result["final_health_restored"])
        self.assertEqual(
            result["timeline_events"],
            list(closure.orch.CANONICAL_EVENTS),
        )

    def test_existing_payload_refuses_duplicates_or_mismatch(self) -> None:
        expected = {"rollback_reinvoked": False}
        self.assertFalse(
            closure._validate_existing_payload([], "health-verified", expected)
        )
        record = {
            "schema": "journal",
            "sequence": 1,
            "timestamp_utc": "2026-01-01T00:00:00Z",
            "run_id": "run",
            "manifest_sha256": "a" * 64,
            "state": "HEALTH_VERIFIED",
            "action": "health-verified",
            **expected,
        }
        self.assertTrue(
            closure._validate_existing_payload(
                [record],
                "health-verified",
                expected,
            )
        )
        with self.assertRaisesRegex(closure.ClosureError, "not exact"):
            closure._validate_existing_payload(
                [record, dict(record)],
                "health-verified",
                expected,
            )
        with self.assertRaisesRegex(closure.ClosureError, "not exact"):
            closure._validate_existing_payload(
                [{**record, "rollback_reinvoked": True}],
                "health-verified",
                expected,
            )

    def test_current_target_requires_realpath_drift(self) -> None:
        spec = SimpleNamespace(
            stage=SimpleNamespace(
                bridge_device="/private/exact-by-id",
                bridge_realpath="/dev/ttyACM0",
            )
        )
        with mock.patch.object(closure.os.path, "realpath", return_value="/dev/ttyACM0"):
            with self.assertRaisesRegex(closure.ClosureError, "requires.*drift"):
                closure.validate_current_target(spec)

    def test_bridge_binding_requires_one_exact_managed_listener_pid(self) -> None:
        spec = SimpleNamespace(
            stage=SimpleNamespace(
                bridge_device="/private/exact-by-id",
                bridge_realpath="/dev/ttyACM1",
            )
        )
        command = [
            "/usr/bin/python3",
            str(closure.MANAGED_BRIDGE_SCRIPT),
            "--host",
            closure.LOOPBACK_HOST,
            "--port",
            str(closure.MANAGED_BRIDGE_PORT),
            "--device",
            spec.stage.bridge_device,
            "--device-glob",
            spec.stage.bridge_device,
            "--capture",
            str(ROOT / "workspace/private/test-a90-capture.raw.log"),
            "--expect-realpath",
            "/dev/ttyACM0",
        ]
        metadata = {
            "wrapper_contract": 1,
            "pid": 123,
            "host": closure.LOOPBACK_HOST,
            "port": closure.MANAGED_BRIDGE_PORT,
            "device": spec.stage.bridge_device,
            "pin_selected_realpath": False,
            "effective_expect_realpath": "/dev/ttyACM0",
            "capture_path": "workspace/private/test-a90-capture.raw.log",
            "command": command,
        }
        bridge = {
            "wrapper_contract": 1,
            "listen_host": closure.LOOPBACK_HOST,
            "listen_port": closure.MANAGED_BRIDGE_PORT,
            "ambiguous": False,
            "selected_device": spec.stage.bridge_device,
            "selected_realpath": "/dev/ttyACM0",
            "bridge_process": "running",
            "port_listening": True,
            "port_pid_source": "fd",
            "port_pids": [123],
            "port_sockets": [{
                "address": closure.LOOPBACK_HOST,
                "port": closure.MANAGED_BRIDGE_PORT,
                "inode": "456",
                "uid": 1000,
            }],
            "processes": [{
                "pid": 123,
                "managed": True,
                "port_match": True,
                "cmdline": "ignored",
            }],
        }
        closure.validate_exact_bridge_binding(
            bridge,
            metadata,
            command,
            spec,
            "/dev/ttyACM0",
        )
        for changed in (
            {**bridge, "port_pids": [999]},
            {
                **bridge,
                "port_sockets": [{
                    **bridge["port_sockets"][0],
                    "address": "0.0.0.0",
                }],
            },
            {
                **bridge,
                "processes": [{
                    **bridge["processes"][0],
                    "managed": False,
                }],
            },
        ):
            with self.assertRaisesRegex(closure.ClosureError, "exact managed"):
                closure.validate_exact_bridge_binding(
                    changed,
                    metadata,
                    command,
                    spec,
                    "/dev/ttyACM0",
                )
        wrong_command = [
            value if value != spec.stage.bridge_device else "/private/other"
            for value in command
        ]
        with self.assertRaisesRegex(closure.ClosureError, "exact managed"):
            closure.validate_exact_bridge_binding(
                bridge,
                {**metadata, "command": wrong_command},
                wrong_command,
                spec,
                "/dev/ttyACM0",
            )
        external_capture = [
            "/tmp/a90.raw.log" if value == command[11] else value
            for value in command
        ]
        with self.assertRaisesRegex(closure.ClosureError, "outside private"):
            closure.validate_exact_bridge_binding(
                bridge,
                {
                    **metadata,
                    "command": external_capture,
                    "capture_path": "/tmp/a90.raw.log",
                },
                external_capture,
                spec,
                "/dev/ttyACM0",
            )

    def test_bridge_private_runtime_files_require_exact_mode_0600(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = (Path(temp) / "capture.raw.log").resolve()
            path.write_bytes(b"private")
            with mock.patch.object(
                closure.staging,
                "PRIVATE_ROOT",
                Path(temp).resolve(),
            ):
                path.chmod(0o600)
                closure._require_private_regular(path, exact_mode=0o600)
                for mode in (0o700, 0o400):
                    path.chmod(mode)
                    with self.assertRaisesRegex(
                        closure.ClosureError,
                        "not exact",
                    ):
                        closure._require_private_regular(
                            path,
                            exact_mode=0o600,
                        )

    def test_health_read_is_read_only_and_requires_all_three_exact_markers(self) -> None:
        spec = SimpleNamespace(
            rollback_version="0.9.285",
            rollback_build="v2321-usb-clean-identity-rodata",
        )
        target = {
            "manifest_realpath": "/dev/ttyACM1",
            "current_realpath": "/dev/ttyACM0",
        }
        responses = {
            ("version",): {
                "rc": 0,
                "status": "ok",
                "text": "version: 0.9.285 build=v2321-usb-clean-identity-rodata\n",
            },
            ("status",): {
                "rc": 0,
                "status": "ok",
                "text": "pstore=ready entries=0\n",
            },
            ("selftest",): {
                "rc": 0,
                "status": "ok",
                "text": "selftest: pass=11 warn=1 fail=0\n",
            },
        }

        def fake_run(_host, _port, _timeout, argv, **_kwargs):
            return responses[tuple(argv)]

        with mock.patch.object(closure.d1, "run_cmd", side_effect=fake_run), \
                mock.patch.object(closure, "_helper_sha256", return_value="b" * 64):
            health = closure.read_exact_v2321_health(
                spec,
                target,
                timeout=30.0,
                reviewed_helper_sha256="b" * 64,
            )
        self.assertFalse(health["device_write"])
        self.assertFalse(health["flash"])
        self.assertFalse(health["payload_sent"])
        self.assertFalse(health["reboot_requested"])
        self.assertFalse(health["rollback_reinvoked"])
        self.assertFalse(health["candidate_replay"])
        self.assertEqual(set(health["framed_response_sha256"]), {
            "version",
            "status",
            "selftest",
        })

        responses[("status",)]["text"] = "pstore=ready entries=1\n"
        with mock.patch.object(closure.d1, "run_cmd", side_effect=fake_run):
            with self.assertRaisesRegex(closure.ClosureError, "not exact V2321"):
                closure.read_exact_v2321_health(
                    spec,
                    target,
                    timeout=30.0,
                    reviewed_helper_sha256="b" * 64,
                )

    def test_result_file_resume_refuses_changed_bytes(self) -> None:
        spec = SimpleNamespace(
            stage=SimpleNamespace(
                run_id="a90-v3404-debian-f1-20260731-01",
                manifest_sha256="a" * 64,
            ),
            rollback_version="0.9.285",
            rollback_build="v2321-usb-clean-identity-rodata",
        )
        health = {
            "manifest_realpath": "/dev/ttyACM1",
            "current_realpath": "/dev/ttyACM0",
            "closure_helper_sha256": "b" * 64,
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            path.write_text(json.dumps({"wrong": True}), encoding="utf-8")
            path.chmod(0o600)
            with mock.patch.object(
                closure,
                "_require_private_regular",
                return_value=path.stat(),
            ), mock.patch.object(
                closure.orch,
                "repair_timeline_from_journal",
                return_value=[
                    {"name": name, "timestamp_utc": "2026-01-01T00:00:00Z"}
                    for name in closure.orch.CANONICAL_EVENTS[:-1]
                ],
            ), mock.patch.object(
                closure.orch,
                "ensure_event",
                side_effect=lambda _td, events, name: events.append(
                    {"name": name, "timestamp_utc": "2026-01-01T00:00:00Z"}
                ),
            ), mock.patch.object(
                closure.orch,
                "read_journal",
                return_value=[],
            ), mock.patch.object(
                closure,
                "_validate_existing_payload",
                return_value=True,
            ), mock.patch.object(
                closure,
                "require_reviewed_helper_sha256",
                return_value="b" * 64,
            ):
                with self.assertRaisesRegex(closure.ClosureError, "result.json"):
                    closure.close_without_transfer(
                        spec,
                        Path(temp),
                        [],
                        health,
                        "b" * 64,
                    )

    def test_resume_artifacts_reject_result_before_health_and_bad_timeline(self) -> None:
        spec = SimpleNamespace(
            stage=SimpleNamespace(
                run_id="a90-v3404-debian-f1-20260731-01",
                manifest_sha256="a" * 64,
                bridge_device="/private/exact-by-id",
                bridge_realpath="/dev/ttyACM1",
            ),
            rollback_version="0.9.285",
            rollback_build="v2321-usb-clean-identity-rodata",
        )
        records = [{"action": action} for action in closure.OPEN_ACTIONS]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result_path = root / "result.json"
            result_path.write_text(
                json.dumps(closure._result(spec)),
                encoding="utf-8",
            )
            timeline_path = root / "timeline.json"
            timeline_path.write_text(
                json.dumps({
                    "events": [
                        {
                            "name": name,
                            "timestamp_utc": f"2026-01-01T00:00:0{index}Z",
                        }
                        for index, name in enumerate(
                            closure.orch.CANONICAL_EVENTS[:6]
                        )
                    ]
                }),
                encoding="utf-8",
            )
            result_path.chmod(0o600)
            timeline_path.chmod(0o600)
            with mock.patch.object(
                closure,
                "_require_private_regular",
                side_effect=lambda path, **_kwargs: path.stat(),
            ):
                with self.assertRaisesRegex(
                    closure.ClosureError,
                    "before health",
                ):
                    closure.validate_resume_artifacts(
                        spec,
                        root,
                        records,
                        "b" * 64,
                    )
                result_path.unlink()
                timeline_path.write_text(
                    json.dumps({
                        "events": [
                            {
                                "name": closure.orch.CANONICAL_EVENTS[0],
                                "timestamp_utc": "2026-01-01T00:00:00Z",
                            },
                            {
                                "name": closure.orch.CANONICAL_EVENTS[2],
                                "timestamp_utc": "2026-01-01T00:00:01Z",
                            },
                        ]
                    }),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    closure.ClosureError,
                    "resumable prefix",
                ):
                    closure.validate_resume_artifacts(
                        spec,
                        root,
                        records,
                        "b" * 64,
                    )
                timeline_path.write_text(
                    json.dumps({
                        "events": [
                            {
                                "name": name,
                                "timestamp_utc": f"2000-01-01T00:00:0{index}Z",
                            }
                            for index, name in enumerate(
                                closure.orch.CANONICAL_EVENTS[:6]
                            )
                        ]
                    }),
                    encoding="utf-8",
                )
                journal_records = [
                    {
                        "action": action,
                        "timestamp_utc": f"2026-01-01T00:00:{index:02d}Z",
                    }
                    for index, action in enumerate(closure.OPEN_ACTIONS)
                ]
                with self.assertRaisesRegex(
                    closure.ClosureError,
                    "journal source",
                ):
                    closure.validate_resume_artifacts(
                        spec,
                        root,
                        journal_records,
                        "b" * 64,
                    )

    def test_resume_artifacts_reject_malformed_partial_payload(self) -> None:
        spec = SimpleNamespace(
            stage=SimpleNamespace(
                run_id="run",
                manifest_sha256="a" * 64,
                bridge_device="/private/exact-by-id",
                bridge_realpath="/dev/ttyACM1",
            ),
            rollback_version="0.9.285",
            rollback_build="v2321-usb-clean-identity-rodata",
        )
        records = [
            *[{"action": action} for action in closure.OPEN_ACTIONS],
            {
                "action": "rollback-boot-ready",
                "closure_helper_sha256": "b" * 64,
            },
        ]
        with self.assertRaisesRegex(
            closure.ClosureError,
            "rollback-boot-ready payload",
        ):
            closure.validate_resume_artifacts(
                spec,
                Path("/not-reached"),
                records,
                "b" * 64,
            )

    def test_stored_health_requires_current_helper_and_all_false_mutations(self) -> None:
        spec = SimpleNamespace(
            stage=SimpleNamespace(
                bridge_device="/private/exact-by-id",
                bridge_realpath="/dev/ttyACM1",
            ),
            rollback_version="0.9.285",
            rollback_build="v2321-usb-clean-identity-rodata",
        )
        health = {
            "exact_bridge_device": "/private/exact-by-id",
            "manifest_realpath": "/dev/ttyACM1",
            "current_realpath": "/dev/ttyACM0",
            "usb_serial_sha256": "a" * 64,
            "realpath_drift_only": True,
            "version": "0.9.285",
            "build": "v2321-usb-clean-identity-rodata",
            "selftest_fail_zero": True,
            "pstore_entries_zero": True,
            "framed_response_sha256": {
                "version": "b" * 64,
                "status": "c" * 64,
                "selftest": "d" * 64,
            },
            "device_write": False,
            "flash": False,
            "payload_sent": False,
            "reboot_requested": False,
            "rollback_reinvoked": False,
            "candidate_replay": False,
            "closure_helper_sha256": "e" * 64,
        }
        with mock.patch.object(
            closure,
            "_connected_serial_digest",
            return_value="a" * 64,
        ):
            closure.validate_health_payload(spec, health, "e" * 64)
            for name in (
                "device_write",
                "flash",
                "payload_sent",
                "reboot_requested",
                "rollback_reinvoked",
                "candidate_replay",
            ):
                changed = {**health, name: True}
                with self.assertRaisesRegex(
                    closure.ClosureError,
                    "health-verified",
                ):
                    closure.validate_health_payload(spec, changed, "e" * 64)
            with self.assertRaisesRegex(
                closure.ClosureError,
                "health-verified",
            ):
                closure.validate_health_payload(
                    spec,
                    {**health, "closure_helper_sha256": "f" * 64},
                    "e" * 64,
                )

    def test_source_has_no_transfer_or_device_control_invocation(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn('parser.add_argument("--bridge-host"', source)
        self.assertNotIn('parser.add_argument("--bridge-port"', source)
        for forbidden in (
            "invoke_rollback(",
            "flash_command(",
            "native_init_flash.py",
            "reboot_native_to_recovery(",
            "adb -s",
            "dd if=",
            "--recover-approved-rollback",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
