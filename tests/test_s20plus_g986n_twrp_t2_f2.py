from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_twrp_t2_f2.py"
)
SPEC = importlib.util.spec_from_file_location("s20plus_t2_f2_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
T2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T2)

EXPECTED_SOURCE_SHA256 = "7f5519ef76091f491165a0be5ce81733f0343318057d02f7577954db1d1a0d11"
BOOT_A = "a" * 64
BOOT_B = "b" * 64
SERIAL = "c" * 64
TOPOLOGY = T2.b0.EXPECTED_ANDROID_TOPOLOGY_SHA256


def health(boot: str = BOOT_A) -> dict[str, object]:
    return {
        "target": dict(T2.h0.EXPECTED_TARGET),
        "serial_sha256": SERIAL,
        "topology_sha256": TOPOLOGY,
        "boot_id_sha256": boot,
        "public_health": {"boot_completed": "1"},
        "root_health": {"uid": "0"},
        "inventory_sha256": "9" * 64,
        "root_health_capture": {
            "path": "private-root", "size": 1, "sha256": "8" * 64
        },
        "recovery_digest": {
            "size": T2.h0.ROLLBACK_RECOVERY_SIZE,
            "sha256": T2.h0.ROLLBACK_RECOVERY_SHA256,
            "capture": {"path": "private", "size": 1, "sha256": "d" * 64},
        },
    }


def endpoint() -> dict[str, object]:
    return {
        "device": "/dev/bus/usb/001/002",
        "endpoint_identity": [1, 2, 3, 4],
        "endpoint_sha256": hashlib.sha256(
            b"/dev/bus/usb/001/002"
        ).hexdigest(),
        "topology_sha256": next(iter(T2.b0.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
        "usb": {**T2.b0.DOWNLOAD_USB, "serial_absent": True},
    }


def baseline() -> dict[str, object]:
    return {
        "schema": "s20plus_g986n_b0_download_baseline_v1",
        "endpoint_count": 0,
        "listing_sha256": "e" * 64,
        "at": "2026-08-31T20:00:00Z",
    }


def cage(kind: str, binding_sha256: str) -> dict[str, object]:
    parent = "/sys/fs/cgroup/user.slice"
    return {
        "schema": "s20plus_g986n_b0_process_cage_binding_v1",
        "version": T2.b0.VERSION,
        "kind": kind,
        "binding_sha256": binding_sha256,
        "parent": parent,
        "parent_identity": [1, 2, 3, 4, 5],
        "cage": f"{parent}/s20plus-b0-{kind}-{binding_sha256[:20]}",
        "host_boot_id_sha256": "7" * 64,
        "cage_identity": [6, 7, 8, 9, 10],
        "empty_before_backend": True,
        "at": "2026-08-31T20:00:00Z",
    }


def transfer_intent(
    value: dict[str, object], kind: str, ep: dict[str, object]
) -> dict[str, object]:
    binding = value["binding"]
    assert isinstance(binding, dict)
    ap = binding[kind]
    assert isinstance(ap, dict)
    return {
        "schema": "s20plus_g986n_twrp_t2_transfer_intent_v1",
        "version": T2.VERSION,
        "kind": kind,
        "binding_sha256": value["binding_sha256"],
        "ap": {key: ap[key] for key in ("path", "size", "sha256")},
        "archive_member": T2.h0.AP_MEMBER_NAME,
        "endpoint": ep,
        "command_shape": [
            "odin4", *(["--reboot"] if kind == "rollback" else []),
            "-a", "AP.tar.md5", "-d", "USBFS",
        ],
        "process_cage": cage(kind, str(value["binding_sha256"])),
        "attempt": 1,
        "no_replay": True,
        "at": "2026-08-31T20:00:00Z",
    }


def quiescence(intent: dict[str, object], kind: str) -> dict[str, object]:
    return {
        "schema": "s20plus_g986n_b0_process_cage_quiescent_v1",
        "version": T2.b0.VERSION,
        "kind": kind,
        "binding_sha256": intent["binding_sha256"],
        "cage_binding_sha256": T2.b0.digest(intent["process_cage"]),
        "kill_requested": True,
        "cage_absent_before_check": False,
        "empty_and_removed": True,
        "at": "2026-08-31T20:00:00Z",
    }


def captured_stdout(run_dir: Path, name: str, payload: bytes):
    return T2.b0.raw_capture.acquire_command(
        ["/usr/bin/printf", "%s", payload.decode("ascii")],
        run_dir,
        name,
        timeout=5,
        stdout_maximum=max(4096, len(payload) + 1),
        stderr_maximum=4096,
        stdout_name=f"{name}.stdout",
        stderr_name=f"{name}.stderr",
    )


def capture_receipt(handle) -> dict[str, object]:
    payload = handle.receipt_path.read_bytes()
    return {
        "path": str(handle.receipt_path),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def prepared(run_dir: Path) -> dict[str, object]:
    binding = {
        "schema": "s20plus_g986n_twrp_t2_binding_v1",
        "version": T2.VERSION,
        "run_id": run_dir.name,
        "target": dict(T2.h0.EXPECTED_TARGET),
        "preflight": health(),
        "initial_download_baseline": baseline(),
        "candidate": {
            "path": str(T2.h0.CANDIDATE_AP),
            "size": T2.h0.CANDIDATE_AP_SIZE,
            "sha256": T2.h0.CANDIDATE_AP_SHA256,
            "member": T2.h0.AP_MEMBER_NAME,
        },
        "rollback": {
            "path": str(T2.h0.ROLLBACK_AP),
            "size": T2.h0.ROLLBACK_AP_SIZE,
            "sha256": T2.h0.ROLLBACK_AP_SHA256,
            "member": T2.h0.AP_MEMBER_NAME,
        },
        "closure_sha256": "f" * 64,
        "candidate_attempt_maximum": 1,
        "rollback_attempt_maximum": 1,
        "candidate_replay": False,
        "rollback_replay": False,
        "recovery_partition_only": True,
        "all_other_partition_transfers": 0,
        "expires_unix": int(time.time()) + 900,
    }
    binding_sha = T2.digest(binding)
    return {
        "schema": "s20plus_g986n_twrp_t2_prepared_v1",
        "version": T2.VERSION,
        "binding": binding,
        "binding_sha256": binding_sha,
        "approval_token": T2.APPROVAL_PREFIX + binding_sha,
        "at": "2026-08-31T20:00:00Z",
    }


class FakeHandle:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.producer_error_type = None
        self.timed_out = False
        self.output_exceeded = False


class S20PlusG986NRecoveryCanaryT2F2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="s20plus-t2-f2-")
        self.root = Path(self.temporary.name)
        self.run_root = self.root / "runs"
        self.run_root.mkdir()
        self.claim_root = self.run_root / "consumed-candidates"
        self.claim_root.mkdir()
        self.guard_parent = self.root / "shared"
        self.guard_parent.mkdir()
        self.guard = self.guard_parent / "active-action.json"
        self.run_dir = self.run_root / "run-1234567890123456789"
        self.run_dir.mkdir()
        self.patchers = (
            mock.patch.object(T2, "RUN_ROOT", self.run_root),
            mock.patch.object(T2, "CLAIM_ROOT", self.claim_root),
            mock.patch.object(T2, "SHARED_GUARD", self.guard),
        )
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temporary.cleanup()

    def test_source_is_frozen(self) -> None:
        self.assertEqual(hashlib.sha256(SCRIPT.read_bytes()).hexdigest(), EXPECTED_SOURCE_SHA256)

    def test_host_closure_and_artifacts_remain_exact(self) -> None:
        result = T2.validate_host_closure(enforce_self=False)
        self.assertEqual(result["host"]["verdict"], T2.h0.HOST_PASS_VERDICT)
        self.assertEqual(
            result["host"]["closure"]["candidate"]["members"][0]["name"],
            "recovery.img.lz4",
        )
        self.assertEqual(
            result["host"]["closure"]["rollback"]["members"][0]["name"],
            "recovery.img.lz4",
        )

    def test_host_closure_pins_base_and_exact_t1_predecessor(self) -> None:
        result = T2.validate_host_closure(enforce_self=False)
        self.assertEqual(
            result["sources"]["t0_h0_base"]["sha256"],
            T2.h0.BASE_SOURCE_SHA256,
        )
        self.assertEqual(
            result["t1_predecessor"]["terminal"]["sha256"],
            T2.T1_PREDECESSOR_TERMINAL_SHA256,
        )
        self.assertEqual(
            result["t1_predecessor"]["observer_stdout"]["sha256"],
            T2.T1_PREDECESSOR_OBSERVER_STDOUT_SHA256,
        )
        self.assertEqual(result["t1_predecessor"]["observed_usb_config"], "mtp,adb")
        self.assertTrue(result["t1_predecessor"]["rollback_transfer_proved"])

    def test_t1_predecessor_rejects_current_serial_mismatch(self) -> None:
        with self.assertRaisesRegex(T2.T2F2Error, "T1-qualified device"):
            T2.validate_t1_predecessor(expected_serial_sha256="0" * 64)

    def test_t1_predecessor_parser_accepts_only_the_retained_exact_difference(self) -> None:
        payload = T2.T1_PREDECESSOR_OBSERVER_STDOUT.read_bytes()
        values = T2._parse_t1_predecessor_observation(payload)
        self.assertEqual(values["usb_config"], "mtp,adb")
        self.assertEqual(values["marker_sha256"], T2.t1_predecessor.h0.MARKER_SHA256)
        for changed in (
            payload.replace(b"usb_config=mtp,adb", b"usb_config=adb"),
            payload.replace(
                T2.t1_predecessor.h0.MARKER_SHA256.encode(), b"0" * 64
            ),
        ):
            with self.assertRaises(T2.T2F2Error):
                T2._parse_t1_predecessor_observation(changed)

    def test_plan_is_active_and_recovery_only(self) -> None:
        plan = T2.render_plan()
        self.assertTrue(plan["active"])
        self.assertTrue(plan["live_authority"])
        self.assertEqual(plan["status"], "BINDING_ATTENDED_TWRP_T2_F2_ACTIVE")
        self.assertEqual(plan["candidate"]["member"], "recovery.img.lz4")
        self.assertEqual(plan["rollback"]["member"], "recovery.img.lz4")
        self.assertEqual(plan["limits"]["all_other_partition_transfers"], 0)
        self.assertFalse(plan["limits"]["format"])
        self.assertFalse(plan["limits"]["vbmeta"])

    def test_direct_recovery_chord_is_fixed_and_keeps_usb_connected(self) -> None:
        instruction = T2.DIRECT_RECOVERY_INSTRUCTION
        self.assertIn("Keep USB connected", instruction)
        self.assertIn("Side/Power + Volume Down", instruction)
        self.assertIn("release Volume Down", instruction)
        self.assertIn("Volume Up", instruction)
        self.assertIn("Do not allow Android to boot", instruction)
        self.assertEqual(T2.render_plan()["direct_recovery_instruction"], instruction)

    def test_connected_cli_reaches_only_the_named_active_owner(self) -> None:
        output = io.StringIO()
        with mock.patch.object(
            T2, "prepare", return_value={"verdict": "FIXTURE_PREPARED"}
        ) as prepare_owner:
            with contextlib.redirect_stdout(output):
                rc = T2.main(["--prepare"])
        self.assertEqual(rc, 0)
        prepare_owner.assert_called_once_with()
        self.assertEqual(json.loads(output.getvalue())["verdict"], "FIXTURE_PREPARED")

    def test_cli_has_no_artifact_serial_endpoint_or_path_input(self) -> None:
        parser = T2.build_parser()
        destinations = {action.dest for action in parser._actions}
        for forbidden in ("artifact", "candidate", "rollback", "serial", "endpoint", "path", "command"):
            self.assertNotIn(forbidden, destinations)

    def test_guard_is_exact_and_exclusive(self) -> None:
        T2.acquire_guard(self.run_dir)
        T2.require_guard(self.run_dir)
        with self.assertRaises(T2.T2F2Error):
            T2.acquire_guard(self.run_dir)
        T2.release_guard(self.run_dir)
        self.assertFalse(self.guard.exists())

    def test_candidate_claim_is_global_and_no_replay(self) -> None:
        value = prepared(self.run_dir)
        T2._candidate_claim(self.run_dir, value)
        with self.assertRaisesRegex(T2.T2F2Error, "permanently consumed"):
            T2._candidate_claim(self.run_dir, value)

    def test_odin_classifier_requires_recovery_member_and_complete_markers(self) -> None:
        handle = FakeHandle()
        good = T2.b0.ODIN_CAGE_ENTRY_MARKER + (
            b"Setup Connection\ninitializeConnection\nReceive PIT Info\n"
            b"success getpit\nUpload Binaries\nrecovery.img.lz4\n"
            b"(100%)\nClose Connection\n"
        )
        self.assertEqual(T2._classify_odin(handle, good, b""), "odin_transfer_completed")
        bad = good.replace(b"recovery.img.lz4", b"boot.img.lz4")
        self.assertEqual(
            T2._classify_odin(handle, bad, b""),
            "odin_device_session_failure_or_unknown",
        )

    def test_odin_local_parse_is_not_a_transfer(self) -> None:
        handle = FakeHandle(returncode=1)
        stdout = T2.b0.ODIN_CAGE_ENTRY_MARKER + b"Fail parse archive\n"
        self.assertEqual(T2._classify_odin(handle, stdout, b""), "odin_local_parse_failure")

    def test_twrp_observer_profile_accepts_only_exact_marker_and_version(self) -> None:
        values = {
            **T2.h0.EXPECTED_RECOVERY_FIXED_OUTPUT,
            "boot_id": "123e4567-e89b-12d3-a456-426614174000",
        }
        stdout = "".join(
            f"{key}={values[key]}\n" for key in T2.h0.RECOVERY_OUTPUT_KEYS
        ).encode()
        parsed = T2.h0.parse_recovery_observation((0, stdout, b""))
        self.assertEqual(parsed["twrp_version"], T2.h0.TWRP_VERSION)
        self.assertEqual(parsed["usb_config"], "mtp,adb")
        bad = stdout.replace(T2.h0.TWRP_VERSION.encode(), b"3.7.1-wrong")
        with self.assertRaises(T2.h0.TWRPT2ProfileError):
            T2.h0.parse_recovery_observation((0, bad, b""))
        bad_usb = stdout.replace(b"usb_config=mtp,adb", b"usb_config=adb")
        with self.assertRaises(T2.h0.TWRPT2ProfileError):
            T2.h0.parse_recovery_observation((0, bad_usb, b""))

    def test_retain_terminal_is_one_transfer_and_no_rollback(self) -> None:
        value = prepared(self.run_dir)
        observation = {"claim_verdict": "PROVED", "boot_id_sha256": BOOT_B}
        T2.b0.durable_json(
            self.run_dir / "candidate-result.json",
            {"classification": "odin_transfer_completed"},
        )
        with (
            mock.patch.object(
                T2,
                "_validate_transfer_result_record",
                return_value={"classification": "odin_transfer_completed"},
            ),
            mock.patch.object(T2, "validate_journal", return_value=set()) as journal,
            mock.patch.object(T2, "release_guard") as release,
        ):
            result = T2.retain_proved_twrp(self.run_dir, value, observation)
        self.assertEqual(result["verdict"], "PROVED_T2_RECOVERY_RETAINED")
        self.assertEqual(result["candidate_attempts"], 1)
        self.assertEqual(result["rollback_attempts"], 0)
        self.assertEqual(result["partition_transfer_attempts"], 1)
        self.assertTrue(result["candidate_retained"])
        self.assertTrue((self.run_dir / "terminal.json").is_file())
        journal.assert_called_once_with(self.run_dir, value)
        release.assert_called_once_with(self.run_dir)

    def test_retain_terminal_rejects_an_armed_physical_rollback(self) -> None:
        value = prepared(self.run_dir)
        observation = {"claim_verdict": "PROVED", "boot_id_sha256": BOOT_B}
        T2.b0.durable_json(
            self.run_dir / "candidate-result.json",
            {"classification": "odin_transfer_completed"},
        )
        T2.b0.durable_json(
            self.run_dir / "physical-rollback-arm.json", {"armed": True}
        )
        with self.assertRaisesRegex(T2.T2F2Error, "armed physical rollback"):
            T2.retain_proved_twrp(self.run_dir, value, observation)

    def test_proved_observation_blocks_physical_rollback_before_endpoint_read(self) -> None:
        value = prepared(self.run_dir)
        T2.b0.durable_json(self.run_dir / "candidate-intent.json", {"intent": True})
        T2.b0.durable_json(
            self.run_dir / "candidate-result.json",
            {"classification": "odin_transfer_completed"},
        )
        T2.b0.durable_json(
            self.run_dir / "candidate-observation.json",
            {"claim_verdict": "PROVED", "boot_id_sha256": BOOT_B},
        )
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
            mock.patch.object(
                T2,
                "_validate_observation",
                side_effect=lambda _run, item, _prepared: item,
            ),
            mock.patch.object(
                T2.b0, "enumerate_download", side_effect=AssertionError("endpoint read")
            ),
        ):
            with self.assertRaisesRegex(T2.T2F2Error, "competing physical rollback"):
                T2.arm_physical_rollback(self.run_dir)

    def test_candidate_arrival_uses_wait_download_digest_domain(self) -> None:
        value = prepared(self.run_dir)
        arrival = {
            "endpoint": endpoint(),
            "baseline_sha256": T2.b0.digest(
                value["binding"]["initial_download_baseline"]
            ),
            "arrival_listing_sha256": "1" * 64,
            "at": "2026-08-31T20:00:01Z",
        }
        self.assertEqual(
            T2._validate_arrival(arrival, value, "candidate arrival"), arrival
        )
        arrival["baseline_sha256"] = T2.digest(
            value["binding"]["initial_download_baseline"]
        )
        with self.assertRaisesRegex(T2.T2F2Error, "prepared baseline"):
            T2._validate_arrival(arrival, value, "candidate arrival")

    def test_resume_candidate_arrival_uses_wait_download_digest_domain(self) -> None:
        value = prepared(self.run_dir)
        ep = endpoint()
        with (
            mock.patch.object(
                T2.b0,
                "enumerate_download",
                return_value=([ep["device"]], "1" * 64),
            ),
            mock.patch.object(T2.b0, "identify_download", return_value=ep),
        ):
            bound = T2._bind_current_candidate_download(self.run_dir, value)
        self.assertEqual(bound, ep)
        arrival = T2.b0.read_json(
            self.run_dir / "candidate-download-arrival.json", "arrival"
        )
        self.assertEqual(
            arrival["baseline_sha256"],
            T2.b0.digest(value["binding"]["initial_download_baseline"]),
        )

    def test_execute_records_download_intent_before_wait_and_no_candidate_on_miss(self) -> None:
        value = prepared(self.run_dir)
        T2.b0.durable_json(self.run_dir / "candidate-download-baseline.json", baseline())
        events: list[str] = []
        real_publish = T2.b0.durable_json

        def publish(path: Path, data: dict[str, object]) -> None:
            events.append(path.name)
            real_publish(path, data)

        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_host_closure", return_value={"frozen": True}),
            mock.patch.object(T2, "android_stock_recovery_health", return_value=(health(), "raw-serial")),
            mock.patch.object(T2, "_adb_reboot_download", return_value={"outcome": "dispatched"}),
            mock.patch.object(T2.b0, "wait_download", return_value=None),
            mock.patch.object(T2.b0, "durable_json", side_effect=publish),
            mock.patch.object(T2, "_candidate_claim", side_effect=AssertionError("candidate claimed")),
        ):
            value["binding"]["closure_sha256"] = T2.digest({"frozen": True})
            value["binding_sha256"] = T2.digest(value["binding"])
            value["approval_token"] = T2.APPROVAL_PREFIX + value["binding_sha256"]
            result = T2.execute(self.run_dir, value["approval_token"])
        self.assertEqual(result["candidate_attempts"], 0)
        self.assertLess(events.index("candidate-download-intent.json"), events.index("candidate-download-result.json"))
        self.assertFalse((self.run_dir / "candidate-intent.json").exists())

    def test_completed_candidate_publishes_recovery_boot_intent(self) -> None:
        value = prepared(self.run_dir)
        value["binding"]["closure_sha256"] = T2.digest({"frozen": True})
        value["binding_sha256"] = T2.digest(value["binding"])
        value["approval_token"] = T2.APPROVAL_PREFIX + value["binding_sha256"]
        T2.b0.durable_json(self.run_dir / "candidate-download-baseline.json", baseline())
        arrival = {"endpoint": endpoint(), "arrival_listing_sha256": "1" * 64}
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_host_closure", return_value={"frozen": True}),
            mock.patch.object(T2, "android_stock_recovery_health", return_value=(health(), "raw-serial")),
            mock.patch.object(T2, "_adb_reboot_download", return_value={"outcome": "dispatched"}),
            mock.patch.object(T2.b0, "wait_download", return_value=arrival),
            mock.patch.object(T2, "_candidate_claim"),
            mock.patch.object(T2, "_transfer", return_value={"classification": "odin_transfer_completed"}),
        ):
            result = T2.execute(self.run_dir, value["approval_token"])
        self.assertEqual(result["verdict"], "CANDIDATE_TRANSFERRED_AWAITING_DIRECT_RECOVERY_BOOT")
        self.assertTrue((self.run_dir / "recovery-boot-intent.json").is_file())

    def test_physical_rollback_cannot_arm_before_candidate_intent(self) -> None:
        value = prepared(self.run_dir)
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
        ):
            with self.assertRaisesRegex(T2.T2F2Error, "consumed candidate"):
                T2.arm_physical_rollback(self.run_dir)

    def test_physical_arm_is_one_shot_and_token_bound(self) -> None:
        value = prepared(self.run_dir)
        T2.b0.durable_json(self.run_dir / "candidate-intent.json", {"consumed": True})
        T2.b0.durable_json(self.run_dir / "candidate-result.json", {"classification": "unknown"})
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T2.b0, "download_baseline", return_value=baseline()),
        ):
            result = T2.arm_physical_rollback(self.run_dir)
            self.assertTrue(result["confirmation_token"].startswith(T2.PHYSICAL_PREFIX))
            with self.assertRaisesRegex(T2.T2F2Error, "already consumed"):
                T2.arm_physical_rollback(self.run_dir)

    def test_confirm_physical_rollback_rejects_wrong_token_before_endpoint(self) -> None:
        value = prepared(self.run_dir)
        arm = {
            "confirmation_token": T2.PHYSICAL_PREFIX + "1" * 64,
            "expires_unix": int(time.time()) + 60,
        }
        T2.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T2, "_validate_physical_arm", return_value=arm),
            mock.patch.object(T2.b0, "identify_download", side_effect=AssertionError("endpoint read")),
        ):
            with self.assertRaisesRegex(T2.T2F2Error, "differs or expired"):
                T2.confirm_physical_rollback(self.run_dir, T2.PHYSICAL_PREFIX + "2" * 64)

    def test_observe_recovery_routes_proof_to_retained_terminal(self) -> None:
        value = prepared(self.run_dir)
        T2.b0.durable_json(self.run_dir / "candidate-result.json", {"classification": "odin_transfer_completed"})
        T2.b0.durable_json(self.run_dir / "recovery-boot-intent.json", {"intent": True})
        observation = {"claim_verdict": "PROVED", "boot_id_sha256": BOOT_B}
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T2, "_validate_transfer_result_record", return_value={"classification": "odin_transfer_completed"}),
            mock.patch.object(T2, "_validate_observation", side_effect=lambda _run, item, _prepared: item),
            mock.patch.object(T2, "_recovery_observation", return_value=(observation, "raw-serial")),
            mock.patch.object(
                T2,
                "retain_proved_twrp",
                return_value={"verdict": "PROVED_T2_RECOVERY_RETAINED"},
            ) as retained,
        ):
            result = T2.observe_recovery(self.run_dir)
        self.assertEqual(result["verdict"], "PROVED_T2_RECOVERY_RETAINED")
        retained.assert_called_once_with(self.run_dir, value, observation)
        self.assertTrue((self.run_dir / "candidate-observation.json").is_file())

    def test_abort_pre_candidate_requires_zero_transfer_intents(self) -> None:
        value = prepared(self.run_dir)
        value["binding"]["closure_sha256"] = T2.PRE_REPAIR_ACTIVE_CLOSURE_SHA256
        T2.b0.durable_json(self.run_dir / "candidate-intent.json", {"consumed": True})
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
        ):
            with self.assertRaisesRegex(T2.T2F2Error, "unavailable"):
                T2.abort_pre_candidate(self.run_dir)

    def test_abort_pre_candidate_closes_same_boot_guard_after_stock_digest(self) -> None:
        value = prepared(self.run_dir)
        value["binding"]["closure_sha256"] = T2.PRE_REPAIR_ACTIVE_CLOSURE_SHA256
        T2.acquire_guard(self.run_dir)
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T2, "android_stock_recovery_health", return_value=(health(BOOT_A), "raw-serial")),
        ):
            result = T2.abort_pre_candidate(self.run_dir)
        self.assertEqual(result["partition_transfer_attempts"], 0)
        self.assertEqual(
            result["final_health"]["boot_id_sha256"],
            value["binding"]["preflight"]["boot_id_sha256"],
        )
        self.assertFalse(self.guard.exists())

    def test_abort_accepts_only_pre_repair_or_current_source_closure(self) -> None:
        value = prepared(self.run_dir)
        with mock.patch.object(
            T2, "validate_host_closure", side_effect=AssertionError("old closure reopened")
        ):
            value["binding"]["closure_sha256"] = T2.PRE_REPAIR_ACTIVE_CLOSURE_SHA256
            T2._require_pre_candidate_abort_closure(value)

        current = {"schema": "fixture-current-reviewed-closure"}
        with mock.patch.object(T2, "validate_host_closure", return_value=current):
            value["binding"]["closure_sha256"] = T2.digest(current)
            T2._require_pre_candidate_abort_closure(value)

    def test_forged_abort_closure_stops_before_health_or_guard_release(self) -> None:
        value = prepared(self.run_dir)
        value["binding"]["closure_sha256"] = "0" * 64
        T2.acquire_guard(self.run_dir)
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(
                T2,
                "validate_host_closure",
                return_value={"schema": "fixture-current-reviewed-closure"},
            ),
            mock.patch.object(T2, "android_stock_recovery_health") as health_owner,
        ):
            with self.assertRaisesRegex(T2.T2F2Error, "source closure is unrecognized"):
                T2.abort_pre_candidate(self.run_dir)
        health_owner.assert_not_called()
        self.assertTrue(self.guard.is_file())

    def test_same_boot_abort_terminal_still_requires_zero_transfer_graph(self) -> None:
        value = prepared(self.run_dir)
        terminal = {
            "schema": "s20plus_g986n_twrp_t2_pre_candidate_abort_v1",
            "version": T2.VERSION,
            "binding_sha256": value["binding_sha256"],
            "verdict": "ABORTED_PRE_CANDIDATE_STOCK_RECOVERY_HEALTHY",
            "global_candidate_claim_consumed": False,
            "candidate_attempts": 0,
            "rollback_attempts": 0,
            "partition_transfer_attempts": 0,
            "candidate_replay_permitted": False,
            "final_health": health(BOOT_A),
            "at": "2026-09-01T00:00:00Z",
        }
        T2.b0.durable_json(self.run_dir / "terminal.json", terminal)
        with mock.patch.object(T2, "_validate_health", return_value=health(BOOT_A)):
            accepted = T2._validate_terminal(
                self.run_dir,
                value,
                {"pre-candidate-abort-recovery-read-intent.json", "terminal.json"},
            )
            self.assertEqual(accepted, terminal)
            with self.assertRaisesRegex(T2.T2F2Error, "pre-candidate terminal differs"):
                T2._validate_terminal(
                    self.run_dir,
                    value,
                    {
                        "pre-candidate-abort-recovery-read-intent.json",
                        "candidate-intent.json",
                        "terminal.json",
                    },
                )

    def test_finalize_distinguishes_attempts_from_proved_transfers(self) -> None:
        value = prepared(self.run_dir)
        T2.acquire_guard(self.run_dir)
        T2.b0.durable_json(self.run_dir / "candidate-result.json", {"classification": "odin_transfer_completed"})
        T2.b0.durable_json(self.run_dir / "rollback-result.json", {"classification": "odin_device_session_failure_or_unknown"})
        T2.b0.durable_json(self.run_dir / "candidate-observation.json", {"claim_verdict": "PROVED"})
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T2, "_validate_transfer_result_record", side_effect=[{"classification": "odin_transfer_completed"}, {"classification": "odin_device_session_failure_or_unknown"}]),
            mock.patch.object(T2, "_validate_health", side_effect=lambda item, *_args: item),
            mock.patch.object(T2, "_validate_observation", side_effect=lambda _run, item, _prepared: item),
            mock.patch.object(T2, "_wait_android_health", return_value=health(BOOT_B)),
        ):
            result = T2.finalize(self.run_dir)
        self.assertEqual(result["partition_transfer_attempts"], 2)
        self.assertEqual(result["proved_recovery_partition_transfers"], 1)
        self.assertFalse(result["rollback_transfer_proved"])
        self.assertEqual(result["verdict"], "NO_PROOF_T2_STOCK_RECOVERY_HEALTHY_TRANSFER_UNPROVED")

    def test_namespace_rejects_unknown_and_duplicate_one_shot_nodes(self) -> None:
        (self.run_dir / "foreign.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(T2.T2F2Error, "unknown node"):
            T2.validate_namespace(self.run_dir)
        (self.run_dir / "foreign.json").unlink()
        for ordinal in (1, 2):
            (self.run_dir / f"candidate-transfer-{ordinal:04d}.stdout").write_bytes(b"")
        with self.assertRaisesRegex(T2.T2F2Error, "reuses one-shot"):
            T2.validate_namespace(self.run_dir)

    def test_api_substitution_is_rejected_before_closure_use(self) -> None:
        with mock.patch.object(T2.h0, "pin_regular_file", mock.Mock()):
            with self.assertRaisesRegex(T2.T2F2Error, "API was rebound"):
                T2.source_closure(enforce_self=False)

    def test_odin_classifier_rejects_out_of_order_and_conflicting_failure(self) -> None:
        handle = FakeHandle()
        ordered = T2.b0.ODIN_CAGE_ENTRY_MARKER + (
            b"Setup Connection\ninitializeConnection\nReceive PIT Info\n"
            b"success getpit\nUpload Binaries\nrecovery.img.lz4\n"
            b"(100%)\nClose Connection\n"
        )
        out_of_order = ordered.replace(
            b"Upload Binaries\nrecovery.img.lz4",
            b"recovery.img.lz4\nUpload Binaries",
        )
        self.assertEqual(
            T2._classify_odin(handle, out_of_order, b""),
            "odin_device_session_failure_or_unknown",
        )
        self.assertEqual(
            T2._classify_odin(handle, ordered + b"FAIL\n", b""),
            "odin_device_session_failure_or_unknown",
        )

    def test_transfer_result_cannot_claim_completion_without_raw_capture(self) -> None:
        value = prepared(self.run_dir)
        ep = endpoint()
        intent = transfer_intent(value, "candidate", ep)
        quiet = quiescence(intent, "candidate")
        T2.b0.durable_json(self.run_dir / "candidate-download-arrival.json", {"endpoint": ep})
        T2.b0.durable_json(self.run_dir / "candidate-intent.json", intent)
        T2.b0.durable_json(self.run_dir / "candidate-cage-quiescent.json", quiet)
        forged = {
            "schema": "s20plus_g986n_twrp_t2_transfer_result_v1",
            "version": T2.VERSION,
            "kind": "candidate",
            "binding_sha256": value["binding_sha256"],
            "classification": "odin_transfer_completed",
            "failure_class": "ReportingCut",
            "stdout_sha256": hashlib.sha256(b"").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "raw_capture": None,
            "endpoint_pre_identity": ep["endpoint_identity"],
            "endpoint_post_identity": None,
            "endpoint_post_state": "unread",
            "process_quiescence_sha256": T2.digest(quiet),
            "replay_permitted": False,
            "at": "2026-08-31T20:00:00Z",
        }
        with self.assertRaisesRegex(T2.T2F2Error, "missing capture"):
            T2._validate_transfer_result_record(
                self.run_dir, forged, "candidate", value
            )

    def test_transfer_completion_is_rederived_from_raw_capture(self) -> None:
        value = prepared(self.run_dir)
        ep = endpoint()
        intent = transfer_intent(value, "candidate", ep)
        quiet = quiescence(intent, "candidate")
        T2.b0.durable_json(self.run_dir / "candidate-download-arrival.json", {"endpoint": ep})
        T2.b0.durable_json(self.run_dir / "candidate-intent.json", intent)
        T2.b0.durable_json(self.run_dir / "candidate-cage-quiescent.json", quiet)
        output = T2.b0.ODIN_CAGE_ENTRY_MARKER + (
            b"Setup Connection\ninitializeConnection\nReceive PIT Info\n"
            b"success getpit\nUpload Binaries\nrecovery.img.lz4\n"
            b"(100%)\nClose Connection\n"
        )
        handle = T2.b0.raw_capture.acquire_command(
            ["/usr/bin/printf", "%s", output.decode("ascii")],
            self.run_dir,
            "candidate-transfer-0001",
            timeout=5,
            stdout_maximum=4096,
            stderr_maximum=4096,
            stdout_name="candidate-transfer-0001.stdout",
            stderr_name="candidate-transfer-0001.stderr",
        )
        receipt_bytes = handle.receipt_path.read_bytes()
        result = {
            "schema": "s20plus_g986n_twrp_t2_transfer_result_v1",
            "version": T2.VERSION,
            "kind": "candidate",
            "binding_sha256": value["binding_sha256"],
            "classification": "odin_transfer_completed",
            "failure_class": None,
            "stdout_sha256": hashlib.sha256(output).hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "raw_capture": {
                "path": str(handle.receipt_path),
                "size": len(receipt_bytes),
                "sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            },
            "endpoint_pre_identity": ep["endpoint_identity"],
            "endpoint_post_identity": ep["endpoint_identity"],
            "endpoint_post_state": "same",
            "process_quiescence_sha256": T2.digest(quiet),
            "replay_permitted": False,
            "at": "2026-08-31T20:00:00Z",
        }
        checked = T2._validate_transfer_result_record(
            self.run_dir, result, "candidate", value
        )
        self.assertEqual(checked["classification"], "odin_transfer_completed")

    def test_health_is_rederived_from_root_and_recovery_raw_captures(self) -> None:
        boot_id = "11111111-2222-3333-4444-555555555555"
        boot_sha256 = hashlib.sha256(boot_id.encode()).hexdigest()
        root_values = {"boot_id": boot_id, **T2.b0.EXPECTED_ROOT_OUTPUT}
        root_stdout = "".join(
            f"{key}={root_values[key]}\n" for key in T2.b0.ROOT_OUTPUT_KEYS
        ).encode()
        root_handle = captured_stdout(
            self.run_dir, "prepare-health-before", root_stdout
        )
        recovery_handle = captured_stdout(
            self.run_dir,
            "prepare-recovery-digest-0001",
            T2.recovery_digest.EXPECTED_ROOT_STDOUT,
        )
        read_intent = {
            "schema": "s20plus_g986n_twrp_t2_recovery_read_intent_v1",
            "version": T2.VERSION,
            "phase": "prepare",
            "target": dict(T2.h0.EXPECTED_TARGET),
            "serial_sha256": SERIAL,
            "topology_sha256": TOPOLOGY,
            "boot_id_sha256": boot_sha256,
            "expected_size": T2.h0.ROLLBACK_RECOVERY_SIZE,
            "expected_sha256": T2.h0.ROLLBACK_RECOVERY_SHA256,
            "attempt": 1,
            "no_replay": True,
            "at": "2026-08-31T20:00:00Z",
        }
        T2.b0.durable_json(
            self.run_dir / "prepare-recovery-read-intent.json", read_intent
        )
        value = {
            "target": dict(T2.h0.EXPECTED_TARGET),
            "serial_sha256": SERIAL,
            "topology_sha256": TOPOLOGY,
            "boot_id_sha256": boot_sha256,
            "public_health": {
                "model": T2.h0.EXPECTED_TARGET["model"],
                "device": T2.h0.EXPECTED_TARGET["device"],
                "product_name": T2.h0.EXPECTED_TARGET["product"],
                "incremental": T2.h0.EXPECTED_TARGET["incremental"],
                "boot_completed": "1",
                "bootanim": "stopped",
                "selinux": "Enforcing",
            },
            "root_health": dict(T2.b0.EXPECTED_ROOT_OUTPUT),
            "inventory_sha256": "6" * 64,
            "root_health_capture": capture_receipt(root_handle),
            "recovery_digest": {
                "size": T2.h0.ROLLBACK_RECOVERY_SIZE,
                "sha256": T2.h0.ROLLBACK_RECOVERY_SHA256,
                "capture": capture_receipt(recovery_handle),
            },
        }
        checked = T2._validate_health(value, self.run_dir, "prepared health")
        self.assertEqual(checked["boot_id_sha256"], boot_sha256)
        forged = dict(value)
        forged["boot_id_sha256"] = "0" * 64
        with self.assertRaisesRegex(T2.T2F2Error, "root capture differs"):
            T2._validate_health(forged, self.run_dir, "forged health")

    def test_recover_transfer_result_never_dispatches_backend(self) -> None:
        value = prepared(self.run_dir)
        ep = endpoint()
        intent = transfer_intent(value, "candidate", ep)
        quiet = quiescence(intent, "candidate")
        T2.b0.durable_json(self.run_dir / "candidate-intent.json", intent)
        T2.b0.durable_json(self.run_dir / "candidate-cage-quiescent.json", quiet)
        with (
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T2, "_validate_transfer_intent_record", return_value=intent),
            mock.patch.object(T2, "_capture_paths", return_value=[]),
            mock.patch.object(T2.b0, "endpoint_stat", side_effect=FileNotFoundError),
            mock.patch.object(T2, "_capture", side_effect=AssertionError("backend replay")),
            mock.patch.object(T2, "_validate_transfer_result_record", side_effect=lambda _run, item, _kind, _prepared: item),
        ):
            result = T2.recover_transfer_result(
                self.run_dir, value, "candidate"
            )
        self.assertEqual(
            result["classification"], "odin_device_session_failure_or_unknown"
        )
        self.assertIsNone(result["raw_capture"])
        self.assertFalse(result["replay_permitted"])

    def test_transfer_rechecks_endpoint_immediately_before_backend(self) -> None:
        value = prepared(self.run_dir)
        ep = endpoint()
        bound_cage = cage("candidate", str(value["binding_sha256"]))
        quiet = quiescence(
            transfer_intent(value, "candidate", ep), "candidate"
        )
        with (
            mock.patch.object(T2, "_same_endpoint", side_effect=[ep, T2.T2F2Error("dispatch drift")]) as same,
            mock.patch.object(T2.h0, "validate_recovery_only_ap"),
            mock.patch.object(T2.b0, "prepare_process_cage", return_value=(Path("/sys/fs/cgroup/fake"), bound_cage)),
            mock.patch.object(T2.b0, "quiesce_process_cage", return_value=quiet),
            mock.patch.object(T2, "_capture", side_effect=AssertionError("backend dispatched")),
            mock.patch.object(T2, "_validate_transfer_result_record", side_effect=lambda _run, item, _kind, _prepared: item),
        ):
            result = T2._transfer(
                self.run_dir, value, "candidate", ep
            )
        self.assertEqual(same.call_count, 2)
        self.assertEqual(
            result["classification"], "odin_device_session_failure_or_unknown"
        )
        self.assertEqual(result["failure_class"], "T2F2Error")

    def test_recovery_observer_ambiguity_is_terminal_no_proof(self) -> None:
        value = prepared(self.run_dir)
        value["binding"]["preflight"]["serial_sha256"] = hashlib.sha256(
            b"same-serial"
        ).hexdigest()
        rows = (
            {"serial": "same-serial", "state": "recovery", "metadata": frozenset()},
            {"serial": "same-serial", "state": "recovery", "metadata": frozenset()},
        )
        with (
            mock.patch.object(T2.b0, "adb_inventory", return_value=rows),
            mock.patch.object(T2, "_capture", side_effect=AssertionError("observer command")),
        ):
            observation, serial = T2._recovery_observation(self.run_dir, value)
        self.assertEqual(observation["claim_verdict"], "NO_PROOF")
        self.assertEqual(observation["reason"], "prepared-serial-ambiguous")
        self.assertIsNone(serial)

    def test_recovery_digest_intent_without_receipt_never_replays(self) -> None:
        before = {
            "serial_sha256": SERIAL,
            "topology_sha256": TOPOLOGY,
            "boot_id_sha256": BOOT_A,
        }
        intent = {
            "schema": "s20plus_g986n_twrp_t2_recovery_read_intent_v1",
            "version": T2.VERSION,
            "phase": "final",
            "target": dict(T2.h0.EXPECTED_TARGET),
            **before,
            "expected_size": T2.h0.ROLLBACK_RECOVERY_SIZE,
            "expected_sha256": T2.h0.ROLLBACK_RECOVERY_SHA256,
            "attempt": 1,
            "no_replay": True,
            "at": "2026-08-31T20:00:00Z",
        }
        T2.b0.durable_json(self.run_dir / "final-recovery-read-intent.json", intent)
        with (
            mock.patch.object(T2.b0, "resident_health_once", return_value=(before, "raw-serial")),
            mock.patch.object(T2, "_capture", side_effect=AssertionError("digest replay")),
        ):
            with self.assertRaisesRegex(T2.T2F2Error, "consumed without a receipt"):
                T2.android_stock_recovery_health(
                    self.run_dir, "final", SERIAL
                )

    def test_physical_confirmation_uses_armed_empty_baseline(self) -> None:
        value = prepared(self.run_dir)
        core = {
            "schema": "s20plus_g986n_twrp_t2_physical_arm_v1",
            "version": T2.VERSION,
            "binding_sha256": value["binding_sha256"],
            "mode": "empty-baseline-physical-entry",
            "baseline": baseline(),
            "existing_endpoint": None,
            "initial_listing_sha256": baseline()["listing_sha256"],
            "expires_unix": int(time.time()) + 60,
            "action": "attended-physical-entry-to-download-for-stock-recovery-only",
            "attempt": 1,
            "no_replay": True,
        }
        token = T2.PHYSICAL_PREFIX + T2.digest(core)
        arm = {**core, "confirmation_token": token, "at": "2026-08-31T20:00:00Z"}
        T2.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        arrival = {"endpoint": endpoint(), "arrival_listing_sha256": "2" * 64}
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T2.b0, "wait_download", return_value=arrival) as waited,
            mock.patch.object(T2.b0, "enumerate_download", return_value=([endpoint()["device"]], "2" * 64)),
            mock.patch.object(T2.b0, "identify_download", return_value=endpoint()),
            mock.patch.object(T2, "_rollback_from_download", return_value={"classification": "odin_transfer_completed"}),
        ):
            result = T2.confirm_physical_rollback(self.run_dir, token)
        self.assertEqual(
            waited.call_args.args[0], core["baseline"]
        )
        self.assertEqual(result["rollback"], "odin_transfer_completed")

    def test_physical_confirmation_cut_resumes_without_second_confirmation(self) -> None:
        value = prepared(self.run_dir)
        core = {
            "schema": "s20plus_g986n_twrp_t2_physical_arm_v1",
            "version": T2.VERSION,
            "binding_sha256": value["binding_sha256"],
            "mode": "empty-baseline-physical-entry",
            "baseline": baseline(),
            "existing_endpoint": None,
            "initial_listing_sha256": baseline()["listing_sha256"],
            "expires_unix": int(time.time()) + 60,
            "action": "attended-physical-entry-to-download-for-stock-recovery-only",
            "attempt": 1,
            "no_replay": True,
        }
        token = T2.PHYSICAL_PREFIX + T2.digest(core)
        arm = {**core, "confirmation_token": token, "at": "2026-08-31T20:00:00Z"}
        confirmation = {
            "schema": "s20plus_g986n_twrp_t2_physical_confirmation_v1",
            "version": T2.VERSION,
            "binding_sha256": value["binding_sha256"],
            "confirmation_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "consumed": True,
            "at": "2026-08-31T20:00:01Z",
        }
        T2.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        T2.b0.durable_json(self.run_dir / "physical-rollback-confirmation.json", confirmation)
        with (
            mock.patch.object(T2.b0, "enumerate_download", return_value=([endpoint()["device"]], "2" * 64)),
            mock.patch.object(T2.b0, "identify_download", return_value=endpoint()),
        ):
            resumed = T2._resume_physical_confirmation(self.run_dir, value)
        self.assertEqual(resumed, endpoint())
        record = T2.b0.read_json(
            self.run_dir / "rollback-download-arrival.json", "arrival"
        )
        self.assertEqual(record["branch"], "empty-baseline-physical-entry")

    def test_expired_physical_resume_miss_cannot_bind_a_later_endpoint(self) -> None:
        value = prepared(self.run_dir)
        core = {
            "schema": "s20plus_g986n_twrp_t2_physical_arm_v1",
            "version": T2.VERSION,
            "binding_sha256": value["binding_sha256"],
            "mode": "empty-baseline-physical-entry",
            "baseline": baseline(),
            "existing_endpoint": None,
            "initial_listing_sha256": baseline()["listing_sha256"],
            "expires_unix": int(time.time()) - 1,
            "action": "attended-physical-entry-to-download-for-stock-recovery-only",
            "attempt": 1,
            "no_replay": True,
        }
        token = T2.PHYSICAL_PREFIX + T2.digest(core)
        arm = {**core, "confirmation_token": token, "at": "2026-08-31T20:00:00Z"}
        confirmation = {
            "schema": "s20plus_g986n_twrp_t2_physical_confirmation_v1",
            "version": T2.VERSION,
            "binding_sha256": value["binding_sha256"],
            "confirmation_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "consumed": True,
            "at": "2026-08-31T20:00:01Z",
        }
        T2.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        T2.b0.durable_json(self.run_dir / "physical-rollback-confirmation.json", confirmation)
        with mock.patch.object(
            T2.b0, "enumerate_download", side_effect=AssertionError("expired observation")
        ):
            self.assertIsNone(
                T2._resume_physical_confirmation(self.run_dir, value)
            )
        self.assertTrue(
            (self.run_dir / "physical-resume-observation-miss.json").is_file()
        )
        with mock.patch.object(
            T2.b0, "enumerate_download", side_effect=AssertionError("re-observation")
        ):
            self.assertIsNone(
                T2._resume_physical_confirmation(self.run_dir, value)
            )
        self.assertFalse(
            (self.run_dir / "rollback-download-arrival.json").exists()
        )

    def test_absent_physical_resume_is_consumed_before_later_arrival(self) -> None:
        value = prepared(self.run_dir)
        core = {
            "schema": "s20plus_g986n_twrp_t2_physical_arm_v1",
            "version": T2.VERSION,
            "binding_sha256": value["binding_sha256"],
            "mode": "empty-baseline-physical-entry",
            "baseline": baseline(),
            "existing_endpoint": None,
            "initial_listing_sha256": baseline()["listing_sha256"],
            "expires_unix": int(time.time()) + 60,
            "action": "attended-physical-entry-to-download-for-stock-recovery-only",
            "attempt": 1,
            "no_replay": True,
        }
        token = T2.PHYSICAL_PREFIX + T2.digest(core)
        arm = {**core, "confirmation_token": token, "at": "2026-08-31T20:00:00Z"}
        confirmation = {
            "schema": "s20plus_g986n_twrp_t2_physical_confirmation_v1",
            "version": T2.VERSION,
            "binding_sha256": value["binding_sha256"],
            "confirmation_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "consumed": True,
            "at": "2026-08-31T20:00:01Z",
        }
        T2.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        T2.b0.durable_json(self.run_dir / "physical-rollback-confirmation.json", confirmation)
        with mock.patch.object(
            T2.b0, "enumerate_download", return_value=([], "2" * 64)
        ):
            self.assertIsNone(
                T2._resume_physical_confirmation(self.run_dir, value)
            )
        with mock.patch.object(
            T2.b0, "enumerate_download", side_effect=AssertionError("late endpoint rebound")
        ):
            self.assertIsNone(
                T2._resume_physical_confirmation(self.run_dir, value)
            )
        self.assertFalse(
            (self.run_dir / "rollback-download-arrival.json").exists()
        )

    def test_initial_arrival_a_to_endpoint_b_mismatch_consumes_resume(self) -> None:
        value = prepared(self.run_dir)
        ep_a = endpoint()
        ep_b = endpoint()
        ep_b["device"] = "/dev/bus/usb/001/003"
        ep_b["endpoint_identity"] = [1, 3, 5, 7]
        ep_b["endpoint_sha256"] = hashlib.sha256(
            str(ep_b["device"]).encode()
        ).hexdigest()
        core = {
            "schema": "s20plus_g986n_twrp_t2_physical_arm_v1",
            "version": T2.VERSION,
            "binding_sha256": value["binding_sha256"],
            "mode": "empty-baseline-physical-entry",
            "baseline": baseline(),
            "existing_endpoint": None,
            "initial_listing_sha256": baseline()["listing_sha256"],
            "expires_unix": int(time.time()) + 60,
            "action": "attended-physical-entry-to-download-for-stock-recovery-only",
            "attempt": 1,
            "no_replay": True,
        }
        token = T2.PHYSICAL_PREFIX + T2.digest(core)
        arm = {**core, "confirmation_token": token, "at": "2026-08-31T20:00:00Z"}
        confirmation = {
            "schema": "s20plus_g986n_twrp_t2_physical_confirmation_v1",
            "version": T2.VERSION,
            "binding_sha256": value["binding_sha256"],
            "confirmation_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "consumed": True,
            "at": "2026-08-31T20:00:01Z",
        }
        T2.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        T2.b0.durable_json(self.run_dir / "physical-rollback-confirmation.json", confirmation)
        with (
            mock.patch.object(
                T2.b0,
                "wait_download",
                return_value={"endpoint": ep_a, "arrival_listing_sha256": "1" * 64},
            ),
            mock.patch.object(
                T2.b0,
                "enumerate_download",
                return_value=([ep_b["device"]], "2" * 64),
            ),
            mock.patch.object(T2.b0, "identify_download", return_value=ep_b),
        ):
            self.assertIsNone(
                T2._initial_physical_observation(self.run_dir, value, arm)
            )
        self.assertTrue(
            (self.run_dir / "physical-observation-miss.json").is_file()
        )
        with mock.patch.object(
            T2.b0, "enumerate_download", side_effect=AssertionError("B rebound")
        ):
            self.assertIsNone(
                T2._resume_physical_confirmation(self.run_dir, value)
            )
        self.assertFalse(
            (self.run_dir / "rollback-download-arrival.json").exists()
        )

    def test_final_health_wait_does_not_retry_target_ambiguity(self) -> None:
        value = prepared(self.run_dir)
        rows = ({"serial": "one"}, {"serial": "two"})
        with (
            mock.patch.object(T2.b0, "adb_inventory", return_value=rows) as inventory,
            mock.patch.object(T2.b0, "target_adb_rows", return_value=rows),
            mock.patch.object(T2, "android_stock_recovery_health", side_effect=AssertionError("health read")),
        ):
            with self.assertRaisesRegex(T2.T2F2Error, "ambiguous"):
                T2._wait_android_health(self.run_dir, value)
        self.assertEqual(inventory.call_count, 1)

    def test_prepare_global_claim_gate_precedes_device_health(self) -> None:
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "validate_host_closure", return_value={}),
            mock.patch.object(T2, "_ensure_private_roots"),
            mock.patch.object(T2, "require_fresh_candidate_unclaimed", side_effect=T2.T2F2Error("claimed")),
            mock.patch.object(T2, "android_stock_recovery_health", side_effect=AssertionError("device health")),
        ):
            with self.assertRaisesRegex(T2.T2F2Error, "claimed"):
                T2.prepare()

    def test_execute_global_claim_gate_precedes_approval_publication(self) -> None:
        value = prepared(self.run_dir)
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "require_fresh_candidate_unclaimed", side_effect=T2.T2F2Error("claimed")),
        ):
            with self.assertRaisesRegex(T2.T2F2Error, "claimed"):
                T2.execute(self.run_dir, value["approval_token"])
        self.assertFalse((self.run_dir / "approval.json").exists())

    def test_execute_rechecks_global_claim_immediately_before_reboot_intent(self) -> None:
        value = prepared(self.run_dir)
        value["binding"]["closure_sha256"] = T2.digest({"frozen": True})
        value["binding_sha256"] = T2.digest(value["binding"])
        value["approval_token"] = T2.APPROVAL_PREFIX + value["binding_sha256"]
        T2.b0.durable_json(
            self.run_dir / "candidate-download-baseline.json", baseline()
        )
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "validate_host_closure", return_value={"frozen": True}),
            mock.patch.object(T2, "android_stock_recovery_health", return_value=(health(), "raw-serial")),
            mock.patch.object(T2, "require_fresh_candidate_unclaimed", side_effect=[None, T2.T2F2Error("late claim")]),
            mock.patch.object(T2, "_adb_reboot_download", side_effect=AssertionError("reboot dispatched")),
        ):
            with self.assertRaisesRegex(T2.T2F2Error, "late claim"):
                T2.execute(self.run_dir, value["approval_token"])
        self.assertFalse(
            (self.run_dir / "candidate-download-intent.json").exists()
        )

    def test_resume_converts_observation_reporting_cut_to_no_proof(self) -> None:
        value = prepared(self.run_dir)
        ep = endpoint()
        for name, payload in {
            "candidate-download-intent.json": {"intent": True},
            "candidate-download-result.json": {"result": True},
            "candidate-download-arrival.json": {"endpoint": ep},
            "candidate-intent.json": {"intent": True},
            "candidate-result.json": {"classification": "placeholder"},
            "recovery-boot-intent.json": {"intent": True},
            "candidate-observation-intent.json": {"intent": True},
        }.items():
            T2.b0.durable_json(self.run_dir / name, payload)
        T2._candidate_claim(self.run_dir, value)
        actual = {
            "approval.json", "candidate-download-intent.json",
            "candidate-download-result.json", "candidate-download-arrival.json",
            "candidate-intent.json", "candidate-result.json",
            "recovery-boot-intent.json", "candidate-observation-intent.json",
        }
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=actual),
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T2, "_validate_arrival", return_value={"endpoint": ep}),
            mock.patch.object(T2, "_validate_transfer_result_record", return_value={"classification": "odin_transfer_completed"}),
            mock.patch.object(T2, "_publish_recovery_boot_intent"),
            mock.patch.object(T2, "_validate_observation", side_effect=lambda _run, item, _prepared: item),
            mock.patch.object(T2, "_recovery_observation", side_effect=AssertionError("observer replay")),
        ):
            result = T2.resume_run(self.run_dir)
        self.assertEqual(result["verdict"], "NO_PROOF_T2_PHYSICAL_ROLLBACK_REQUIRED")
        observation = T2.b0.read_json(
            self.run_dir / "candidate-observation.json", "observation"
        )
        self.assertEqual(
            observation["reason"], "observation-intent-consumed-result-absent"
        )

    def test_terminal_proved_requires_three_distinct_boots(self) -> None:
        value = prepared(self.run_dir)
        T2.acquire_guard(self.run_dir)
        T2.b0.durable_json(self.run_dir / "candidate-result.json", {"classification": "placeholder"})
        T2.b0.durable_json(self.run_dir / "rollback-result.json", {"classification": "placeholder"})
        observation = {"claim_verdict": "PROVED", "boot_id_sha256": BOOT_B}
        T2.b0.durable_json(self.run_dir / "candidate-observation.json", observation)
        with (
            mock.patch.object(T2, "require_active"),
            mock.patch.object(T2, "read_prepared", return_value=value),
            mock.patch.object(T2, "validate_journal", return_value=set()),
            mock.patch.object(T2, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T2, "_validate_transfer_result_record", side_effect=[{"classification": "odin_transfer_completed"}, {"classification": "odin_transfer_completed"}]),
            mock.patch.object(T2, "_validate_health", side_effect=lambda item, *_args: item),
            mock.patch.object(T2, "_validate_observation", return_value=observation),
            mock.patch.object(T2, "_wait_android_health", return_value=health(BOOT_B)),
        ):
            terminal = T2.finalize(self.run_dir)
        self.assertEqual(
            terminal["verdict"], "NO_PROOF_T2_RETURNED_STOCK_RECOVERY_HEALTHY"
        )

    def test_source_never_mentions_boot_partition_member(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("boot.img.lz4", source)
        self.assertNotIn("/dev/block/by-name/boot", source)

    def test_normalized_identity_changes_neither_for_boolean_nor_hash_literal(self) -> None:
        normalized = T2.normalized_self_sha256()
        source = SCRIPT.read_bytes().replace(b"T2_F2_ACTIVE = False", b"T2_F2_ACTIVE = True")
        source = source.replace(
            T2.EXPECTED_REVIEWED_NORMALIZED_SHA256.encode(), b"1" * 64
        )
        source, active_count = T2.re.subn(
            rb"^T2_F2_ACTIVE = (?:False|True)$",
            b"T2_F2_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
            source,
            flags=T2.re.MULTILINE,
        )
        source, hash_count = T2.re.subn(
            rb'^EXPECTED_REVIEWED_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
            b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
            source,
            flags=T2.re.MULTILINE,
        )
        self.assertEqual((active_count, hash_count), (1, 1))
        self.assertEqual(hashlib.sha256(source).hexdigest(), normalized)

    def test_common_and_target_contract_activate_exact_t2_only(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        tiers = (ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md").read_text(
            encoding="utf-8"
        )
        contract = (
            ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Contract-Revision: **5**", agents)
        self.assertIn("TWRP T2 F2 active", agents)
        self.assertIn("### F2-T2 - Exact S20+ TWRP Corrected Retained Recovery", tiers)
        self.assertIn(
            "Status: **BINDING - ATTENDED TWRP T2 F2 ACTIVE**",
            contract,
        )
        self.assertIn(f"`{T2.EXPECTED_REVIEWED_NORMALIZED_SHA256}`", contract)
        registry_line = next(
            line
            for line in agents.splitlines()
            if line.startswith("| Samsung Galaxy S20+ 5G")
        )
        self.assertIn("TWRP T2 F2 active", registry_line)


if __name__ == "__main__":
    unittest.main()
