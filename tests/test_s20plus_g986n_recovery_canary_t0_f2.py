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
    "s20plus_g986n_recovery_canary_t0_f2.py"
)
SPEC = importlib.util.spec_from_file_location("s20plus_t0_f2_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
T0 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T0)

EXPECTED_SOURCE_SHA256 = "a91d45e14f4cb82f10a83a8c2bdc38126deb20b9b841918888ec45842ad51e75"
BOOT_A = "a" * 64
BOOT_B = "b" * 64
SERIAL = "c" * 64
TOPOLOGY = T0.b0.EXPECTED_ANDROID_TOPOLOGY_SHA256


def health(boot: str = BOOT_A) -> dict[str, object]:
    return {
        "target": dict(T0.h0.EXPECTED_TARGET),
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
            "size": T0.h0.ROLLBACK_RECOVERY_SIZE,
            "sha256": T0.h0.ROLLBACK_RECOVERY_SHA256,
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
        "topology_sha256": next(iter(T0.b0.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
        "usb": {**T0.b0.DOWNLOAD_USB, "serial_absent": True},
    }


def baseline() -> dict[str, object]:
    return {
        "schema": "s20plus_g986n_b0_download_baseline_v1",
        "endpoint_count": 0,
        "listing_sha256": "e" * 64,
        "at": "2026-08-31T00:00:00Z",
    }


def cage(kind: str, binding_sha256: str) -> dict[str, object]:
    parent = "/sys/fs/cgroup/user.slice"
    return {
        "schema": "s20plus_g986n_b0_process_cage_binding_v1",
        "version": T0.b0.VERSION,
        "kind": kind,
        "binding_sha256": binding_sha256,
        "parent": parent,
        "parent_identity": [1, 2, 3, 4, 5],
        "cage": f"{parent}/s20plus-b0-{kind}-{binding_sha256[:20]}",
        "host_boot_id_sha256": "7" * 64,
        "cage_identity": [6, 7, 8, 9, 10],
        "empty_before_backend": True,
        "at": "2026-08-31T00:00:00Z",
    }


def transfer_intent(
    value: dict[str, object], kind: str, ep: dict[str, object]
) -> dict[str, object]:
    binding = value["binding"]
    assert isinstance(binding, dict)
    ap = binding[kind]
    assert isinstance(ap, dict)
    return {
        "schema": "s20plus_g986n_recovery_canary_t0_transfer_intent_v1",
        "version": T0.VERSION,
        "kind": kind,
        "binding_sha256": value["binding_sha256"],
        "ap": {key: ap[key] for key in ("path", "size", "sha256")},
        "archive_member": T0.h0.AP_MEMBER_NAME,
        "endpoint": ep,
        "command_shape": [
            "odin4", *(["--reboot"] if kind == "rollback" else []),
            "-a", "AP.tar.md5", "-d", "USBFS",
        ],
        "process_cage": cage(kind, str(value["binding_sha256"])),
        "attempt": 1,
        "no_replay": True,
        "at": "2026-08-31T00:00:00Z",
    }


def quiescence(intent: dict[str, object], kind: str) -> dict[str, object]:
    return {
        "schema": "s20plus_g986n_b0_process_cage_quiescent_v1",
        "version": T0.b0.VERSION,
        "kind": kind,
        "binding_sha256": intent["binding_sha256"],
        "cage_binding_sha256": T0.b0.digest(intent["process_cage"]),
        "kill_requested": True,
        "cage_absent_before_check": False,
        "empty_and_removed": True,
        "at": "2026-08-31T00:00:00Z",
    }


def captured_stdout(run_dir: Path, name: str, payload: bytes):
    return T0.b0.raw_capture.acquire_command(
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
        "schema": "s20plus_g986n_recovery_canary_t0_binding_v1",
        "version": T0.VERSION,
        "run_id": run_dir.name,
        "target": dict(T0.h0.EXPECTED_TARGET),
        "preflight": health(),
        "initial_download_baseline": baseline(),
        "candidate": {
            "path": str(T0.h0.CANDIDATE_AP),
            "size": T0.h0.CANDIDATE_AP_SIZE,
            "sha256": T0.h0.CANDIDATE_AP_SHA256,
            "member": T0.h0.AP_MEMBER_NAME,
        },
        "rollback": {
            "path": str(T0.h0.ROLLBACK_AP),
            "size": T0.h0.ROLLBACK_AP_SIZE,
            "sha256": T0.h0.ROLLBACK_AP_SHA256,
            "member": T0.h0.AP_MEMBER_NAME,
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
    binding_sha = T0.digest(binding)
    return {
        "schema": "s20plus_g986n_recovery_canary_t0_prepared_v1",
        "version": T0.VERSION,
        "binding": binding,
        "binding_sha256": binding_sha,
        "approval_token": T0.APPROVAL_PREFIX + binding_sha,
        "at": "2026-08-31T00:00:00Z",
    }


class FakeHandle:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.producer_error_type = None
        self.timed_out = False
        self.output_exceeded = False


class S20PlusG986NRecoveryCanaryT0F2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="s20plus-t0-f2-")
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
            mock.patch.object(T0, "RUN_ROOT", self.run_root),
            mock.patch.object(T0, "CLAIM_ROOT", self.claim_root),
            mock.patch.object(T0, "SHARED_GUARD", self.guard),
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
        result = T0.validate_host_closure(enforce_self=False)
        self.assertEqual(result["host"]["verdict"], T0.h0.HOST_PASS_VERDICT)
        self.assertEqual(
            result["host"]["closure"]["candidate"]["members"][0]["name"],
            "recovery.img.lz4",
        )
        self.assertEqual(
            result["host"]["closure"]["rollback"]["members"][0]["name"],
            "recovery.img.lz4",
        )

    def test_plan_is_active_and_recovery_only(self) -> None:
        plan = T0.render_plan()
        self.assertTrue(plan["active"])
        self.assertTrue(plan["live_authority"])
        self.assertEqual(
            plan["status"], "BINDING_ATTENDED_RECOVERY_CANARY_T0_F2_ACTIVE"
        )
        self.assertEqual(plan["candidate"]["member"], "recovery.img.lz4")
        self.assertEqual(plan["rollback"]["member"], "recovery.img.lz4")
        self.assertEqual(plan["limits"]["all_other_partition_transfers"], 0)
        self.assertFalse(plan["limits"]["format"])
        self.assertFalse(plan["limits"]["vbmeta"])

    def test_direct_recovery_chord_is_fixed_and_keeps_usb_connected(self) -> None:
        instruction = T0.DIRECT_RECOVERY_INSTRUCTION
        self.assertIn("Keep USB connected", instruction)
        self.assertIn("Side/Power + Volume Down", instruction)
        self.assertIn("release Volume Down", instruction)
        self.assertIn("Volume Up", instruction)
        self.assertIn("Do not allow Android to boot", instruction)
        self.assertEqual(T0.render_plan()["direct_recovery_instruction"], instruction)

    def test_connected_cli_reaches_only_the_named_active_owner(self) -> None:
        output = io.StringIO()
        with mock.patch.object(
            T0, "prepare", return_value={"verdict": "FIXTURE_PREPARED"}
        ) as prepare_owner:
            with contextlib.redirect_stdout(output):
                rc = T0.main(["--prepare"])
        self.assertEqual(rc, 0)
        prepare_owner.assert_called_once_with()
        self.assertEqual(json.loads(output.getvalue())["verdict"], "FIXTURE_PREPARED")

    def test_cli_has_no_artifact_serial_endpoint_or_path_input(self) -> None:
        parser = T0.build_parser()
        destinations = {action.dest for action in parser._actions}
        for forbidden in ("artifact", "candidate", "rollback", "serial", "endpoint", "path", "command"):
            self.assertNotIn(forbidden, destinations)

    def test_guard_is_exact_and_exclusive(self) -> None:
        T0.acquire_guard(self.run_dir)
        T0.require_guard(self.run_dir)
        with self.assertRaises(T0.T0F2Error):
            T0.acquire_guard(self.run_dir)
        T0.release_guard(self.run_dir)
        self.assertFalse(self.guard.exists())

    def test_candidate_claim_is_global_and_no_replay(self) -> None:
        value = prepared(self.run_dir)
        T0._candidate_claim(self.run_dir, value)
        with self.assertRaisesRegex(T0.T0F2Error, "permanently consumed"):
            T0._candidate_claim(self.run_dir, value)

    def test_odin_classifier_requires_recovery_member_and_complete_markers(self) -> None:
        handle = FakeHandle()
        good = T0.b0.ODIN_CAGE_ENTRY_MARKER + (
            b"Setup Connection\ninitializeConnection\nReceive PIT Info\n"
            b"success getpit\nUpload Binaries\nrecovery.img.lz4\n"
            b"(100%)\nClose Connection\n"
        )
        self.assertEqual(T0._classify_odin(handle, good, b""), "odin_transfer_completed")
        bad = good.replace(b"recovery.img.lz4", b"boot.img.lz4")
        self.assertEqual(
            T0._classify_odin(handle, bad, b""),
            "odin_device_session_failure_or_unknown",
        )

    def test_odin_local_parse_is_not_a_transfer(self) -> None:
        handle = FakeHandle(returncode=1)
        stdout = T0.b0.ODIN_CAGE_ENTRY_MARKER + b"Fail parse archive\n"
        self.assertEqual(T0._classify_odin(handle, stdout, b""), "odin_local_parse_failure")

    def test_candidate_arrival_uses_wait_download_digest_domain(self) -> None:
        value = prepared(self.run_dir)
        arrival = {
            "endpoint": endpoint(),
            "baseline_sha256": T0.b0.digest(
                value["binding"]["initial_download_baseline"]
            ),
            "arrival_listing_sha256": "1" * 64,
            "at": "2026-08-31T00:00:01Z",
        }
        self.assertEqual(
            T0._validate_arrival(arrival, value, "candidate arrival"), arrival
        )
        arrival["baseline_sha256"] = T0.digest(
            value["binding"]["initial_download_baseline"]
        )
        with self.assertRaisesRegex(T0.T0F2Error, "prepared baseline"):
            T0._validate_arrival(arrival, value, "candidate arrival")

    def test_execute_records_download_intent_before_wait_and_no_candidate_on_miss(self) -> None:
        value = prepared(self.run_dir)
        T0.b0.durable_json(self.run_dir / "candidate-download-baseline.json", baseline())
        events: list[str] = []
        real_publish = T0.b0.durable_json

        def publish(path: Path, data: dict[str, object]) -> None:
            events.append(path.name)
            real_publish(path, data)

        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_host_closure", return_value={"frozen": True}),
            mock.patch.object(T0, "android_stock_recovery_health", return_value=(health(), "raw-serial")),
            mock.patch.object(T0, "_adb_reboot_download", return_value={"outcome": "dispatched"}),
            mock.patch.object(T0.b0, "wait_download", return_value=None),
            mock.patch.object(T0.b0, "durable_json", side_effect=publish),
            mock.patch.object(T0, "_candidate_claim", side_effect=AssertionError("candidate claimed")),
        ):
            value["binding"]["closure_sha256"] = T0.digest({"frozen": True})
            value["binding_sha256"] = T0.digest(value["binding"])
            value["approval_token"] = T0.APPROVAL_PREFIX + value["binding_sha256"]
            result = T0.execute(self.run_dir, value["approval_token"])
        self.assertEqual(result["candidate_attempts"], 0)
        self.assertLess(events.index("candidate-download-intent.json"), events.index("candidate-download-result.json"))
        self.assertFalse((self.run_dir / "candidate-intent.json").exists())

    def test_completed_candidate_publishes_recovery_boot_intent(self) -> None:
        value = prepared(self.run_dir)
        value["binding"]["closure_sha256"] = T0.digest({"frozen": True})
        value["binding_sha256"] = T0.digest(value["binding"])
        value["approval_token"] = T0.APPROVAL_PREFIX + value["binding_sha256"]
        T0.b0.durable_json(self.run_dir / "candidate-download-baseline.json", baseline())
        arrival = {"endpoint": endpoint(), "arrival_listing_sha256": "1" * 64}
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_host_closure", return_value={"frozen": True}),
            mock.patch.object(T0, "android_stock_recovery_health", return_value=(health(), "raw-serial")),
            mock.patch.object(T0, "_adb_reboot_download", return_value={"outcome": "dispatched"}),
            mock.patch.object(T0.b0, "wait_download", return_value=arrival),
            mock.patch.object(T0, "_candidate_claim"),
            mock.patch.object(T0, "_transfer", return_value={"classification": "odin_transfer_completed"}),
        ):
            result = T0.execute(self.run_dir, value["approval_token"])
        self.assertEqual(result["verdict"], "CANDIDATE_TRANSFERRED_AWAITING_DIRECT_RECOVERY_BOOT")
        self.assertTrue((self.run_dir / "recovery-boot-intent.json").is_file())

    def test_physical_rollback_cannot_arm_before_candidate_intent(self) -> None:
        value = prepared(self.run_dir)
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
        ):
            with self.assertRaisesRegex(T0.T0F2Error, "consumed candidate"):
                T0.arm_physical_rollback(self.run_dir)

    def test_physical_arm_is_one_shot_and_token_bound(self) -> None:
        value = prepared(self.run_dir)
        T0.b0.durable_json(self.run_dir / "candidate-intent.json", {"consumed": True})
        T0.b0.durable_json(self.run_dir / "candidate-result.json", {"classification": "unknown"})
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=set()),
            mock.patch.object(T0, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T0.b0, "download_baseline", return_value=baseline()),
        ):
            result = T0.arm_physical_rollback(self.run_dir)
            self.assertTrue(result["confirmation_token"].startswith(T0.PHYSICAL_PREFIX))
            with self.assertRaisesRegex(T0.T0F2Error, "already consumed"):
                T0.arm_physical_rollback(self.run_dir)

    def test_confirm_physical_rollback_rejects_wrong_token_before_endpoint(self) -> None:
        value = prepared(self.run_dir)
        arm = {
            "confirmation_token": T0.PHYSICAL_PREFIX + "1" * 64,
            "expires_unix": int(time.time()) + 60,
        }
        T0.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=set()),
            mock.patch.object(T0, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T0, "_validate_physical_arm", return_value=arm),
            mock.patch.object(T0.b0, "identify_download", side_effect=AssertionError("endpoint read")),
        ):
            with self.assertRaisesRegex(T0.T0F2Error, "differs or expired"):
                T0.confirm_physical_rollback(self.run_dir, T0.PHYSICAL_PREFIX + "2" * 64)

    def test_observe_recovery_auto_routes_to_stock_rollback(self) -> None:
        value = prepared(self.run_dir)
        T0.b0.durable_json(self.run_dir / "candidate-result.json", {"classification": "odin_transfer_completed"})
        T0.b0.durable_json(self.run_dir / "recovery-boot-intent.json", {"intent": True})
        observation = {"claim_verdict": "PROVED", "boot_id_sha256": BOOT_B}
        ep = endpoint()
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=set()),
            mock.patch.object(T0, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T0, "_validate_transfer_result_record", return_value={"classification": "odin_transfer_completed"}),
            mock.patch.object(T0, "_validate_observation", side_effect=lambda _run, item, _prepared: item),
            mock.patch.object(T0, "_recovery_observation", return_value=(observation, "raw-serial")),
            mock.patch.object(T0, "_automatic_rollback_download", return_value=ep),
            mock.patch.object(T0, "_rollback_from_download", return_value={"classification": "odin_transfer_completed"}),
        ):
            result = T0.observe_recovery(self.run_dir)
        self.assertEqual(result["claim_verdict"], "PROVED")
        self.assertTrue((self.run_dir / "candidate-observation.json").is_file())

    def test_abort_pre_candidate_requires_zero_transfer_intents(self) -> None:
        value = prepared(self.run_dir)
        T0.b0.durable_json(self.run_dir / "candidate-intent.json", {"consumed": True})
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=set()),
            mock.patch.object(T0, "require_all_transfer_processes_quiescent"),
        ):
            with self.assertRaisesRegex(T0.T0F2Error, "unavailable"):
                T0.abort_pre_candidate(self.run_dir)

    def test_abort_pre_candidate_closes_guard_after_stock_digest(self) -> None:
        value = prepared(self.run_dir)
        T0.acquire_guard(self.run_dir)
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=set()),
            mock.patch.object(T0, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T0, "android_stock_recovery_health", return_value=(health(BOOT_B), "raw-serial")),
        ):
            result = T0.abort_pre_candidate(self.run_dir)
        self.assertEqual(result["partition_transfer_attempts"], 0)
        self.assertFalse(self.guard.exists())

    def test_finalize_distinguishes_attempts_from_proved_transfers(self) -> None:
        value = prepared(self.run_dir)
        T0.acquire_guard(self.run_dir)
        T0.b0.durable_json(self.run_dir / "candidate-result.json", {"classification": "odin_transfer_completed"})
        T0.b0.durable_json(self.run_dir / "rollback-result.json", {"classification": "odin_device_session_failure_or_unknown"})
        T0.b0.durable_json(self.run_dir / "candidate-observation.json", {"claim_verdict": "PROVED"})
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=set()),
            mock.patch.object(T0, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T0, "_validate_transfer_result_record", side_effect=[{"classification": "odin_transfer_completed"}, {"classification": "odin_device_session_failure_or_unknown"}]),
            mock.patch.object(T0, "_validate_health", side_effect=lambda item, *_args: item),
            mock.patch.object(T0, "_validate_observation", side_effect=lambda _run, item, _prepared: item),
            mock.patch.object(T0, "_wait_android_health", return_value=health(BOOT_B)),
        ):
            result = T0.finalize(self.run_dir)
        self.assertEqual(result["partition_transfer_attempts"], 2)
        self.assertEqual(result["proved_recovery_partition_transfers"], 1)
        self.assertFalse(result["rollback_transfer_proved"])
        self.assertEqual(result["verdict"], "NO_PROOF_T0_STOCK_RECOVERY_HEALTHY_TRANSFER_UNPROVED")

    def test_namespace_rejects_unknown_and_duplicate_one_shot_nodes(self) -> None:
        (self.run_dir / "foreign.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(T0.T0F2Error, "unknown node"):
            T0.validate_namespace(self.run_dir)
        (self.run_dir / "foreign.json").unlink()
        for ordinal in (1, 2):
            (self.run_dir / f"candidate-transfer-{ordinal:04d}.stdout").write_bytes(b"")
        with self.assertRaisesRegex(T0.T0F2Error, "reuses one-shot"):
            T0.validate_namespace(self.run_dir)

    def test_api_substitution_is_rejected_before_closure_use(self) -> None:
        with mock.patch.object(T0.h0, "pin_regular_file", mock.Mock()):
            with self.assertRaisesRegex(T0.T0F2Error, "API was rebound"):
                T0.source_closure(enforce_self=False)

    def test_odin_classifier_rejects_out_of_order_and_conflicting_failure(self) -> None:
        handle = FakeHandle()
        ordered = T0.b0.ODIN_CAGE_ENTRY_MARKER + (
            b"Setup Connection\ninitializeConnection\nReceive PIT Info\n"
            b"success getpit\nUpload Binaries\nrecovery.img.lz4\n"
            b"(100%)\nClose Connection\n"
        )
        out_of_order = ordered.replace(
            b"Upload Binaries\nrecovery.img.lz4",
            b"recovery.img.lz4\nUpload Binaries",
        )
        self.assertEqual(
            T0._classify_odin(handle, out_of_order, b""),
            "odin_device_session_failure_or_unknown",
        )
        self.assertEqual(
            T0._classify_odin(handle, ordered + b"FAIL\n", b""),
            "odin_device_session_failure_or_unknown",
        )

    def test_transfer_result_cannot_claim_completion_without_raw_capture(self) -> None:
        value = prepared(self.run_dir)
        ep = endpoint()
        intent = transfer_intent(value, "candidate", ep)
        quiet = quiescence(intent, "candidate")
        T0.b0.durable_json(self.run_dir / "candidate-download-arrival.json", {"endpoint": ep})
        T0.b0.durable_json(self.run_dir / "candidate-intent.json", intent)
        T0.b0.durable_json(self.run_dir / "candidate-cage-quiescent.json", quiet)
        forged = {
            "schema": "s20plus_g986n_recovery_canary_t0_transfer_result_v1",
            "version": T0.VERSION,
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
            "process_quiescence_sha256": T0.digest(quiet),
            "replay_permitted": False,
            "at": "2026-08-31T00:00:00Z",
        }
        with self.assertRaisesRegex(T0.T0F2Error, "missing capture"):
            T0._validate_transfer_result_record(
                self.run_dir, forged, "candidate", value
            )

    def test_transfer_completion_is_rederived_from_raw_capture(self) -> None:
        value = prepared(self.run_dir)
        ep = endpoint()
        intent = transfer_intent(value, "candidate", ep)
        quiet = quiescence(intent, "candidate")
        T0.b0.durable_json(self.run_dir / "candidate-download-arrival.json", {"endpoint": ep})
        T0.b0.durable_json(self.run_dir / "candidate-intent.json", intent)
        T0.b0.durable_json(self.run_dir / "candidate-cage-quiescent.json", quiet)
        output = T0.b0.ODIN_CAGE_ENTRY_MARKER + (
            b"Setup Connection\ninitializeConnection\nReceive PIT Info\n"
            b"success getpit\nUpload Binaries\nrecovery.img.lz4\n"
            b"(100%)\nClose Connection\n"
        )
        handle = T0.b0.raw_capture.acquire_command(
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
            "schema": "s20plus_g986n_recovery_canary_t0_transfer_result_v1",
            "version": T0.VERSION,
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
            "process_quiescence_sha256": T0.digest(quiet),
            "replay_permitted": False,
            "at": "2026-08-31T00:00:00Z",
        }
        checked = T0._validate_transfer_result_record(
            self.run_dir, result, "candidate", value
        )
        self.assertEqual(checked["classification"], "odin_transfer_completed")

    def test_health_is_rederived_from_root_and_recovery_raw_captures(self) -> None:
        boot_id = "11111111-2222-3333-4444-555555555555"
        boot_sha256 = hashlib.sha256(boot_id.encode()).hexdigest()
        root_values = {"boot_id": boot_id, **T0.b0.EXPECTED_ROOT_OUTPUT}
        root_stdout = "".join(
            f"{key}={root_values[key]}\n" for key in T0.b0.ROOT_OUTPUT_KEYS
        ).encode()
        root_handle = captured_stdout(
            self.run_dir, "prepare-health-before", root_stdout
        )
        recovery_handle = captured_stdout(
            self.run_dir,
            "prepare-recovery-digest-0001",
            T0.recovery_digest.EXPECTED_ROOT_STDOUT,
        )
        read_intent = {
            "schema": "s20plus_g986n_recovery_canary_t0_recovery_read_intent_v1",
            "version": T0.VERSION,
            "phase": "prepare",
            "target": dict(T0.h0.EXPECTED_TARGET),
            "serial_sha256": SERIAL,
            "topology_sha256": TOPOLOGY,
            "boot_id_sha256": boot_sha256,
            "expected_size": T0.h0.ROLLBACK_RECOVERY_SIZE,
            "expected_sha256": T0.h0.ROLLBACK_RECOVERY_SHA256,
            "attempt": 1,
            "no_replay": True,
            "at": "2026-08-31T00:00:00Z",
        }
        T0.b0.durable_json(
            self.run_dir / "prepare-recovery-read-intent.json", read_intent
        )
        value = {
            "target": dict(T0.h0.EXPECTED_TARGET),
            "serial_sha256": SERIAL,
            "topology_sha256": TOPOLOGY,
            "boot_id_sha256": boot_sha256,
            "public_health": {
                "model": T0.h0.EXPECTED_TARGET["model"],
                "device": T0.h0.EXPECTED_TARGET["device"],
                "product_name": T0.h0.EXPECTED_TARGET["product"],
                "incremental": T0.h0.EXPECTED_TARGET["incremental"],
                "boot_completed": "1",
                "bootanim": "stopped",
                "selinux": "Enforcing",
            },
            "root_health": dict(T0.b0.EXPECTED_ROOT_OUTPUT),
            "inventory_sha256": "6" * 64,
            "root_health_capture": capture_receipt(root_handle),
            "recovery_digest": {
                "size": T0.h0.ROLLBACK_RECOVERY_SIZE,
                "sha256": T0.h0.ROLLBACK_RECOVERY_SHA256,
                "capture": capture_receipt(recovery_handle),
            },
        }
        checked = T0._validate_health(value, self.run_dir, "prepared health")
        self.assertEqual(checked["boot_id_sha256"], boot_sha256)
        forged = dict(value)
        forged["boot_id_sha256"] = "0" * 64
        with self.assertRaisesRegex(T0.T0F2Error, "root capture differs"):
            T0._validate_health(forged, self.run_dir, "forged health")

    def test_recover_transfer_result_never_dispatches_backend(self) -> None:
        value = prepared(self.run_dir)
        ep = endpoint()
        intent = transfer_intent(value, "candidate", ep)
        quiet = quiescence(intent, "candidate")
        T0.b0.durable_json(self.run_dir / "candidate-intent.json", intent)
        T0.b0.durable_json(self.run_dir / "candidate-cage-quiescent.json", quiet)
        with (
            mock.patch.object(T0, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T0, "_validate_transfer_intent_record", return_value=intent),
            mock.patch.object(T0, "_capture_paths", return_value=[]),
            mock.patch.object(T0.b0, "endpoint_stat", side_effect=FileNotFoundError),
            mock.patch.object(T0, "_capture", side_effect=AssertionError("backend replay")),
            mock.patch.object(T0, "_validate_transfer_result_record", side_effect=lambda _run, item, _kind, _prepared: item),
        ):
            result = T0.recover_transfer_result(
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
            mock.patch.object(T0, "_same_endpoint", side_effect=[ep, T0.T0F2Error("dispatch drift")]) as same,
            mock.patch.object(T0.h0, "validate_recovery_only_ap"),
            mock.patch.object(T0.b0, "prepare_process_cage", return_value=(Path("/sys/fs/cgroup/fake"), bound_cage)),
            mock.patch.object(T0.b0, "quiesce_process_cage", return_value=quiet),
            mock.patch.object(T0, "_capture", side_effect=AssertionError("backend dispatched")),
            mock.patch.object(T0, "_validate_transfer_result_record", side_effect=lambda _run, item, _kind, _prepared: item),
        ):
            result = T0._transfer(
                self.run_dir, value, "candidate", ep
            )
        self.assertEqual(same.call_count, 2)
        self.assertEqual(
            result["classification"], "odin_device_session_failure_or_unknown"
        )
        self.assertEqual(result["failure_class"], "T0F2Error")

    def test_recovery_observer_ambiguity_is_terminal_no_proof(self) -> None:
        value = prepared(self.run_dir)
        with (
            mock.patch.object(T0.b0, "adb_inventory", return_value=({"serial": "foreign"},)),
            mock.patch.object(T0.b0, "target_adb_rows", return_value=({"a": 1}, {"a": 2})),
            mock.patch.object(T0, "_capture", side_effect=AssertionError("observer command")),
        ):
            observation, serial = T0._recovery_observation(self.run_dir, value)
        self.assertEqual(observation["claim_verdict"], "NO_PROOF")
        self.assertEqual(observation["reason"], "exact-target-ambiguous")
        self.assertIsNone(serial)

    def test_recovery_digest_intent_without_receipt_never_replays(self) -> None:
        before = {
            "serial_sha256": SERIAL,
            "topology_sha256": TOPOLOGY,
            "boot_id_sha256": BOOT_A,
        }
        intent = {
            "schema": "s20plus_g986n_recovery_canary_t0_recovery_read_intent_v1",
            "version": T0.VERSION,
            "phase": "final",
            "target": dict(T0.h0.EXPECTED_TARGET),
            **before,
            "expected_size": T0.h0.ROLLBACK_RECOVERY_SIZE,
            "expected_sha256": T0.h0.ROLLBACK_RECOVERY_SHA256,
            "attempt": 1,
            "no_replay": True,
            "at": "2026-08-31T00:00:00Z",
        }
        T0.b0.durable_json(self.run_dir / "final-recovery-read-intent.json", intent)
        with (
            mock.patch.object(T0.b0, "resident_health_once", return_value=(before, "raw-serial")),
            mock.patch.object(T0, "_capture", side_effect=AssertionError("digest replay")),
        ):
            with self.assertRaisesRegex(T0.T0F2Error, "consumed without a receipt"):
                T0.android_stock_recovery_health(
                    self.run_dir, "final", SERIAL
                )

    def test_physical_confirmation_uses_armed_empty_baseline(self) -> None:
        value = prepared(self.run_dir)
        core = {
            "schema": "s20plus_g986n_recovery_canary_t0_physical_arm_v1",
            "version": T0.VERSION,
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
        token = T0.PHYSICAL_PREFIX + T0.digest(core)
        arm = {**core, "confirmation_token": token, "at": "2026-08-31T00:00:00Z"}
        T0.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        arrival = {"endpoint": endpoint(), "arrival_listing_sha256": "2" * 64}
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=set()),
            mock.patch.object(T0, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T0.b0, "wait_download", return_value=arrival) as waited,
            mock.patch.object(T0.b0, "enumerate_download", return_value=([endpoint()["device"]], "2" * 64)),
            mock.patch.object(T0.b0, "identify_download", return_value=endpoint()),
            mock.patch.object(T0, "_rollback_from_download", return_value={"classification": "odin_transfer_completed"}),
        ):
            result = T0.confirm_physical_rollback(self.run_dir, token)
        self.assertEqual(
            waited.call_args.args[0], core["baseline"]
        )
        self.assertEqual(result["rollback"], "odin_transfer_completed")

    def test_physical_confirmation_cut_resumes_without_second_confirmation(self) -> None:
        value = prepared(self.run_dir)
        core = {
            "schema": "s20plus_g986n_recovery_canary_t0_physical_arm_v1",
            "version": T0.VERSION,
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
        token = T0.PHYSICAL_PREFIX + T0.digest(core)
        arm = {**core, "confirmation_token": token, "at": "2026-08-31T00:00:00Z"}
        confirmation = {
            "schema": "s20plus_g986n_recovery_canary_t0_physical_confirmation_v1",
            "version": T0.VERSION,
            "binding_sha256": value["binding_sha256"],
            "confirmation_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "consumed": True,
            "at": "2026-08-31T00:00:01Z",
        }
        T0.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        T0.b0.durable_json(self.run_dir / "physical-rollback-confirmation.json", confirmation)
        with (
            mock.patch.object(T0.b0, "enumerate_download", return_value=([endpoint()["device"]], "2" * 64)),
            mock.patch.object(T0.b0, "identify_download", return_value=endpoint()),
        ):
            resumed = T0._resume_physical_confirmation(self.run_dir, value)
        self.assertEqual(resumed, endpoint())
        record = T0.b0.read_json(
            self.run_dir / "rollback-download-arrival.json", "arrival"
        )
        self.assertEqual(record["branch"], "empty-baseline-physical-entry")

    def test_expired_physical_resume_miss_cannot_bind_a_later_endpoint(self) -> None:
        value = prepared(self.run_dir)
        core = {
            "schema": "s20plus_g986n_recovery_canary_t0_physical_arm_v1",
            "version": T0.VERSION,
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
        token = T0.PHYSICAL_PREFIX + T0.digest(core)
        arm = {**core, "confirmation_token": token, "at": "2026-08-31T00:00:00Z"}
        confirmation = {
            "schema": "s20plus_g986n_recovery_canary_t0_physical_confirmation_v1",
            "version": T0.VERSION,
            "binding_sha256": value["binding_sha256"],
            "confirmation_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "consumed": True,
            "at": "2026-08-31T00:00:01Z",
        }
        T0.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        T0.b0.durable_json(self.run_dir / "physical-rollback-confirmation.json", confirmation)
        with mock.patch.object(
            T0.b0, "enumerate_download", side_effect=AssertionError("expired observation")
        ):
            self.assertIsNone(
                T0._resume_physical_confirmation(self.run_dir, value)
            )
        self.assertTrue(
            (self.run_dir / "physical-resume-observation-miss.json").is_file()
        )
        with mock.patch.object(
            T0.b0, "enumerate_download", side_effect=AssertionError("re-observation")
        ):
            self.assertIsNone(
                T0._resume_physical_confirmation(self.run_dir, value)
            )
        self.assertFalse(
            (self.run_dir / "rollback-download-arrival.json").exists()
        )

    def test_absent_physical_resume_is_consumed_before_later_arrival(self) -> None:
        value = prepared(self.run_dir)
        core = {
            "schema": "s20plus_g986n_recovery_canary_t0_physical_arm_v1",
            "version": T0.VERSION,
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
        token = T0.PHYSICAL_PREFIX + T0.digest(core)
        arm = {**core, "confirmation_token": token, "at": "2026-08-31T00:00:00Z"}
        confirmation = {
            "schema": "s20plus_g986n_recovery_canary_t0_physical_confirmation_v1",
            "version": T0.VERSION,
            "binding_sha256": value["binding_sha256"],
            "confirmation_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "consumed": True,
            "at": "2026-08-31T00:00:01Z",
        }
        T0.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        T0.b0.durable_json(self.run_dir / "physical-rollback-confirmation.json", confirmation)
        with mock.patch.object(
            T0.b0, "enumerate_download", return_value=([], "2" * 64)
        ):
            self.assertIsNone(
                T0._resume_physical_confirmation(self.run_dir, value)
            )
        with mock.patch.object(
            T0.b0, "enumerate_download", side_effect=AssertionError("late endpoint rebound")
        ):
            self.assertIsNone(
                T0._resume_physical_confirmation(self.run_dir, value)
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
            "schema": "s20plus_g986n_recovery_canary_t0_physical_arm_v1",
            "version": T0.VERSION,
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
        token = T0.PHYSICAL_PREFIX + T0.digest(core)
        arm = {**core, "confirmation_token": token, "at": "2026-08-31T00:00:00Z"}
        confirmation = {
            "schema": "s20plus_g986n_recovery_canary_t0_physical_confirmation_v1",
            "version": T0.VERSION,
            "binding_sha256": value["binding_sha256"],
            "confirmation_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "consumed": True,
            "at": "2026-08-31T00:00:01Z",
        }
        T0.b0.durable_json(self.run_dir / "physical-rollback-arm.json", arm)
        T0.b0.durable_json(self.run_dir / "physical-rollback-confirmation.json", confirmation)
        with (
            mock.patch.object(
                T0.b0,
                "wait_download",
                return_value={"endpoint": ep_a, "arrival_listing_sha256": "1" * 64},
            ),
            mock.patch.object(
                T0.b0,
                "enumerate_download",
                return_value=([ep_b["device"]], "2" * 64),
            ),
            mock.patch.object(T0.b0, "identify_download", return_value=ep_b),
        ):
            self.assertIsNone(
                T0._initial_physical_observation(self.run_dir, value, arm)
            )
        self.assertTrue(
            (self.run_dir / "physical-observation-miss.json").is_file()
        )
        with mock.patch.object(
            T0.b0, "enumerate_download", side_effect=AssertionError("B rebound")
        ):
            self.assertIsNone(
                T0._resume_physical_confirmation(self.run_dir, value)
            )
        self.assertFalse(
            (self.run_dir / "rollback-download-arrival.json").exists()
        )

    def test_final_health_wait_does_not_retry_target_ambiguity(self) -> None:
        value = prepared(self.run_dir)
        rows = ({"serial": "one"}, {"serial": "two"})
        with (
            mock.patch.object(T0.b0, "adb_inventory", return_value=rows) as inventory,
            mock.patch.object(T0.b0, "target_adb_rows", return_value=rows),
            mock.patch.object(T0, "android_stock_recovery_health", side_effect=AssertionError("health read")),
        ):
            with self.assertRaisesRegex(T0.T0F2Error, "ambiguous"):
                T0._wait_android_health(self.run_dir, value)
        self.assertEqual(inventory.call_count, 1)

    def test_prepare_global_claim_gate_precedes_device_health(self) -> None:
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "validate_host_closure", return_value={}),
            mock.patch.object(T0, "_ensure_private_roots"),
            mock.patch.object(T0, "require_fresh_candidate_unclaimed", side_effect=T0.T0F2Error("claimed")),
            mock.patch.object(T0, "android_stock_recovery_health", side_effect=AssertionError("device health")),
        ):
            with self.assertRaisesRegex(T0.T0F2Error, "claimed"):
                T0.prepare()

    def test_execute_global_claim_gate_precedes_approval_publication(self) -> None:
        value = prepared(self.run_dir)
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=set()),
            mock.patch.object(T0, "require_fresh_candidate_unclaimed", side_effect=T0.T0F2Error("claimed")),
        ):
            with self.assertRaisesRegex(T0.T0F2Error, "claimed"):
                T0.execute(self.run_dir, value["approval_token"])
        self.assertFalse((self.run_dir / "approval.json").exists())

    def test_execute_rechecks_global_claim_immediately_before_reboot_intent(self) -> None:
        value = prepared(self.run_dir)
        value["binding"]["closure_sha256"] = T0.digest({"frozen": True})
        value["binding_sha256"] = T0.digest(value["binding"])
        value["approval_token"] = T0.APPROVAL_PREFIX + value["binding_sha256"]
        T0.b0.durable_json(
            self.run_dir / "candidate-download-baseline.json", baseline()
        )
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=set()),
            mock.patch.object(T0, "validate_host_closure", return_value={"frozen": True}),
            mock.patch.object(T0, "android_stock_recovery_health", return_value=(health(), "raw-serial")),
            mock.patch.object(T0, "require_fresh_candidate_unclaimed", side_effect=[None, T0.T0F2Error("late claim")]),
            mock.patch.object(T0, "_adb_reboot_download", side_effect=AssertionError("reboot dispatched")),
        ):
            with self.assertRaisesRegex(T0.T0F2Error, "late claim"):
                T0.execute(self.run_dir, value["approval_token"])
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
            T0.b0.durable_json(self.run_dir / name, payload)
        T0._candidate_claim(self.run_dir, value)
        actual = {
            "approval.json", "candidate-download-intent.json",
            "candidate-download-result.json", "candidate-download-arrival.json",
            "candidate-intent.json", "candidate-result.json",
            "recovery-boot-intent.json", "candidate-observation-intent.json",
        }
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=actual),
            mock.patch.object(T0, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T0, "_validate_arrival", return_value={"endpoint": ep}),
            mock.patch.object(T0, "_validate_transfer_result_record", return_value={"classification": "odin_transfer_completed"}),
            mock.patch.object(T0, "_publish_recovery_boot_intent"),
            mock.patch.object(T0, "_validate_observation", side_effect=lambda _run, item, _prepared: item),
            mock.patch.object(T0, "_recovery_observation", side_effect=AssertionError("observer replay")),
        ):
            result = T0.resume_run(self.run_dir)
        self.assertEqual(result["verdict"], "NO_PROOF_T0_PHYSICAL_ROLLBACK_REQUIRED")
        observation = T0.b0.read_json(
            self.run_dir / "candidate-observation.json", "observation"
        )
        self.assertEqual(
            observation["reason"], "observation-intent-consumed-result-absent"
        )

    def test_terminal_proved_requires_three_distinct_boots(self) -> None:
        value = prepared(self.run_dir)
        T0.acquire_guard(self.run_dir)
        T0.b0.durable_json(self.run_dir / "candidate-result.json", {"classification": "placeholder"})
        T0.b0.durable_json(self.run_dir / "rollback-result.json", {"classification": "placeholder"})
        observation = {"claim_verdict": "PROVED", "boot_id_sha256": BOOT_B}
        T0.b0.durable_json(self.run_dir / "candidate-observation.json", observation)
        with (
            mock.patch.object(T0, "require_active"),
            mock.patch.object(T0, "read_prepared", return_value=value),
            mock.patch.object(T0, "validate_journal", return_value=set()),
            mock.patch.object(T0, "require_all_transfer_processes_quiescent"),
            mock.patch.object(T0, "_validate_transfer_result_record", side_effect=[{"classification": "odin_transfer_completed"}, {"classification": "odin_transfer_completed"}]),
            mock.patch.object(T0, "_validate_health", side_effect=lambda item, *_args: item),
            mock.patch.object(T0, "_validate_observation", return_value=observation),
            mock.patch.object(T0, "_wait_android_health", return_value=health(BOOT_B)),
        ):
            terminal = T0.finalize(self.run_dir)
        self.assertEqual(
            terminal["verdict"], "NO_PROOF_T0_RETURNED_STOCK_RECOVERY_HEALTHY"
        )

    def test_source_never_mentions_boot_partition_member(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("boot.img.lz4", source)
        self.assertNotIn("/dev/block/by-name/boot", source)

    def test_normalized_identity_changes_neither_for_boolean_nor_hash_literal(self) -> None:
        normalized = T0.normalized_self_sha256()
        source = SCRIPT.read_bytes().replace(b"T0_F2_ACTIVE = False", b"T0_F2_ACTIVE = True")
        source = source.replace(
            T0.EXPECTED_REVIEWED_NORMALIZED_SHA256.encode(), b"1" * 64
        )
        source, active_count = T0.re.subn(
            rb"^T0_F2_ACTIVE = (?:False|True)$",
            b"T0_F2_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
            source,
            flags=T0.re.MULTILINE,
        )
        source, hash_count = T0.re.subn(
            rb'^EXPECTED_REVIEWED_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
            b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
            source,
            flags=T0.re.MULTILINE,
        )
        self.assertEqual((active_count, hash_count), (1, 1))
        self.assertEqual(hashlib.sha256(source).hexdigest(), normalized)

    def test_common_and_target_contract_activate_only_exact_f2(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        tiers = (ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md").read_text(
            encoding="utf-8"
        )
        contract = (
            ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Contract-Revision: **5**", agents)
        self.assertIn("**F2:** the single-target S20+ recovery-canary T0", agents)
        self.assertIn("### F2 - Exact S20+ Recovery-Canary Bootstrap", tiers)
        self.assertIn(
            "Status: **BINDING - ATTENDED RECOVERY-CANARY T0 F2 ACTIVE**",
            contract,
        )
        self.assertIn(f"`{T0.EXPECTED_REVIEWED_NORMALIZED_SHA256}`", contract)
        registry_line = next(
            line
            for line in agents.splitlines()
            if line.startswith("| Samsung Galaxy S20+ 5G")
        )
        self.assertIn("recovery-canary T0 and TWRP T1 F2 candidates consumed", registry_line)


if __name__ == "__main__":
    unittest.main()
