import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import test_device_action_f1_v2 as f1_core_tests


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py"
)
REVALIDATION = SCRIPT.parent


def load_module():
    sys.path.insert(0, str(REVALIDATION))
    try:
        spec = importlib.util.spec_from_file_location(
            "device_action_f1_live_v2_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(REVALIDATION))


class FakeBackend:
    def __init__(
        self,
        module,
        *,
        candidate="odin_transfer_completed",
        rollback=None,
        marker=True,
        request_error=False,
        final_failures=0,
        crash_candidate=False,
        crash_rollback_attempt=None,
        recheck_failures=0,
    ):
        self.module = module
        self.candidate = candidate
        self.rollback = list(rollback or ["odin_transfer_completed"])
        self.marker = marker
        self.request_error = request_error
        self.final_failures = final_failures
        self.crash_candidate = crash_candidate
        self.crash_rollback_attempt = crash_rollback_attempt
        self.recheck_failures = recheck_failures
        self.calls = []

    def recheck_android(self, _prepared, destination):
        self.calls.append("recheck")
        destination.mkdir()
        if self.recheck_failures:
            self.recheck_failures -= 1
            raise RuntimeError("simulated preflight interruption")
        return {"healthy": True, "target_evidence_sha256": "1" * 64}

    def request_download(self, _prepared):
        self.calls.append("request-download")
        if self.request_error:
            raise RuntimeError("request failed")

    def endpoint_session(self, _run_dir):
        return contextlib.nullcontext(object())

    def wait_download(self, _prepared, _run_dir, _lease, _timeout):
        self.calls.append("wait-download")
        return self.module.Endpoint("/dev/bus/usb/001/002", 1, "2" * 64)

    def _write_transfer(self, prepared, kind, classification, attempt, prefix):
        stdout = f"{kind}:{classification}:stdout".encode()
        stderr = b""
        stdout_receipt = self.module._persist_bytes(
            prepared.run_dir / f"{prefix}.stdout", stdout
        )
        stderr_receipt = self.module._persist_bytes(
            prepared.run_dir / f"{prefix}.stderr", stderr
        )
        value = {
            "schema": "device_action_f1_transfer_receipt_v2",
            "kind": kind,
            "attempt": attempt,
            "prefix": prefix,
            "classification": classification,
            "transport": {"returncode": 0 if classification.endswith("completed") else 1},
            "stdout": stdout_receipt,
            "stderr": stderr_receipt,
        }
        self.module._write_exclusive(
            prepared.run_dir / f"{prefix}.result.json", value
        )
        return value

    def transfer(
        self, prepared, _endpoint, kind, _destination, attempt, prefix
    ):
        self.calls.append(f"transfer-{kind}")
        if kind == "candidate" and self.crash_candidate:
            raise KeyboardInterrupt("simulated host interruption")
        if kind == "rollback" and attempt == self.crash_rollback_attempt:
            raise KeyboardInterrupt("simulated rollback interruption")
        classification = (
            self.candidate if kind == "candidate" else self.rollback.pop(0)
        )
        receipt = self._write_transfer(
            prepared, kind, classification, attempt, prefix
        )
        return self.module.TransferOutcome(
            classification,
            classification == "odin_transfer_completed",
            classification != "odin_local_parse_failure",
            receipt,
        )

    def observe_candidate(self, _prepared, _run_dir, _lease):
        self.calls.append("observe")
        return {
            "bounded": True,
            "download_endpoint_absent": True,
            "candidate_execution_proven": False,
        }

    def verify_final(self, prepared, _run_dir, _lease, destination):
        self.calls.append("verify-final")
        if self.final_failures:
            self.final_failures -= 1
            raise RuntimeError("final health unavailable")
        acceptance = prepared.bundle.manifest["observation"]["acceptance"]
        if self.marker is True:
            payload = ("prefix\n" + acceptance["marker"] + "\nsuffix\n").encode()
        elif self.marker is False:
            payload = b"clean retained log\n"
        elif self.marker == "foreign":
            payload = ("prefix\n" + acceptance["family"] + "foreign]]\nsuffix\n").encode()
        elif self.marker == "partial":
            payload = ("prefix\n" + acceptance["marker"][:16]).encode()
        else:
            raise AssertionError("unknown marker fixture")
        reads = []
        for index in (1, 2):
            path = destination / f"rollback-observer-{index}.bin"
            path.write_bytes(payload)
            path.with_suffix(path.suffix + ".stderr").write_bytes(b"")
            reads.append(
                {
                    "path": str(path),
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "read_to_eof": True,
                    "stderr_bytes": 0,
                    "elapsed_sec": 0.01,
                }
            )
        classification = self.module.classify_acceptance(payload, acceptance)
        exact = classification["exact_count"]
        family = classification["family_count"]
        accepted = classification["accepted"]
        health = {
            "android_boot_completed": True,
            "boot_animation_stopped": True,
            "verified_boot_state": "orange",
            "root_verified": True,
            "boot_sha256": prepared.bundle.profile["final_health"]["boot_sha256"],
            "supporting_partition_sha256": prepared.bundle.profile["final_health"][
                "supporting_partition_sha256"
            ],
            "odin_endpoint_absent": True,
            "kernel_release": "fixture-kernel",
            "boot_id_sha256": "3" * 64,
        }
        return {
            "health": health,
            "target_evidence_sha256": self.module.core.json_sha256(
                {
                    "serial": hashlib.sha256(
                        prepared.private_target["serial"].encode()
                    ).hexdigest(),
                    "topology": hashlib.sha256(
                        prepared.private_target["topology"].encode()
                    ).hexdigest(),
                }
            ),
            "observer": {
                "reads": reads,
                "byte_identical": True,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "exact_marker_count": exact,
                "marker_family_count": family,
                "classification": classification,
                "accepted": accepted,
            },
            "rollback_verified": True,
        }


class DeviceActionF1LiveV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def prepared(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        run_dir = root / "run"
        run_dir.mkdir()
        health = {
            "android_boot_completed": True,
            "boot_animation_stopped": True,
            "verified_boot_state": "orange",
            "root_required": True,
            "boot_sha256": "a" * 64,
            "supporting_partition_sha256": {
                "vendor_boot": "b" * 64,
                "dtbo": "c" * 64,
                "recovery": "d" * 64,
            },
            "odin_endpoint_absent": True,
        }
        profile = {
            "profile_id": "fixture-profile",
            "target": {
                "model": "SM-S906N",
                "device": "g0q",
                "firmware_incremental": "S906NKSS7FYG8",
                "android_transport": "adb",
                "download": {
                    "usb_vendor_id": "04e8",
                    "usb_product_id": "685d",
                    "product": "SAMSUNG USB",
                    "manufacturer": "Samsung",
                    "serial_policy": "absent",
                },
            },
            "start_health": health,
            "final_health": health,
        }
        manifest = {
            "manifest_id": "fixture-manifest",
            "status": "ready-for-f1-approval",
            "observation": {
                "timeout_sec": 1,
                "acceptance": {
                    "source": "/proc/last_kmsg",
                    "marker": "[[FIXTURE|phase=PID1]]",
                    "family": "[[FIXTURE|",
                    "exact_count": 1,
                },
            },
        }
        bundle = self.module.core.Bundle(profile, manifest, {}, "e" * 64)
        prepared_dict = {"approval_binding_sha256": "f" * 64}
        prepared = self.module.PreparedRun(
            root,
            run_dir,
            bundle,
            prepared_dict,
            {"schema": self.module.PRIVATE_TARGET_SCHEMA, "serial": "s", "topology": "usb:1-1"},
        )
        return temporary, prepared

    def test_success_closes_exact_timeline_and_rollback(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(self.module)
        result = self.module.execute_prepared(
            prepared, prepared.approval_token, backend
        )
        self.assertEqual(
            result["verdict"], "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK"
        )
        self.assertEqual(
            [event["name"] for event in result["timeline"]["events"]],
            list(self.module.core.TIMELINE),
        )
        self.assertEqual(
            [call for call in backend.calls if call.startswith("transfer-")],
            ["transfer-candidate", "transfer-rollback"],
        )

    def test_approval_mismatch_stops_before_backend(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(self.module)
        with self.assertRaises(self.module.F1LiveError):
            self.module.execute_prepared(prepared, "wrong", backend)
        self.assertEqual(backend.calls, [])
        self.assertFalse((prepared.run_dir / "transaction").exists())

    def test_local_parse_failure_aborts_without_rollback(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(self.module, candidate="odin_local_parse_failure")
        result = self.module.execute_prepared(
            prepared, prepared.approval_token, backend
        )
        self.assertEqual(result["current_state"], "ABORTED")
        self.assertEqual(
            result["verdict"], "FAIL_F1_V2_ODIN_LOCAL_PARSE_NO_DEVICE_SESSION"
        )
        self.assertNotIn("transfer-rollback", backend.calls)

    def test_unknown_candidate_session_still_rolls_back_as_no_proof(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(
            self.module, candidate="odin_device_session_failure_or_unknown"
        )
        result = self.module.execute_prepared(
            prepared, prepared.approval_token, backend
        )
        self.assertEqual(
            result["verdict"], "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        )
        self.assertIn("transfer-rollback", backend.calls)

    def test_marker_absence_is_no_proof_after_verified_rollback(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        result = self.module.execute_prepared(
            prepared,
            prepared.approval_token,
            FakeBackend(self.module, marker=False),
        )
        self.assertEqual(
            result["verdict"], "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        )

    def test_foreign_and_partial_markers_are_integrity_failures(self):
        for marker in ("foreign", "partial"):
            with self.subTest(marker=marker):
                temporary, prepared = self.prepared()
                self.addCleanup(temporary.cleanup)
                result = self.module.execute_prepared(
                    prepared,
                    prepared.approval_token,
                    FakeBackend(self.module, marker=marker),
                )
                self.assertEqual(
                    result["verdict"], "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
                )
                classification = result["live_state"]["final_evidence"][
                    "observer"
                ]["classification"]
                self.assertTrue(classification["integrity_issue"])

    def test_compact_proof_is_data_only(self):
        marker = "[[S22P1D|0e13f28e8558dde01ce3345f16408673]]"
        family = "[[S22P1D|"
        acceptance = {
            "marker": marker,
            "family": family,
            "exact_count": 1,
        }
        accepted = self.module.classify_acceptance(
            f"prefix\n{marker}\nsuffix".encode(),
            acceptance,
        )
        self.assertTrue(accepted["accepted"])
        self.assertEqual(accepted["exact_count"], 1)
        self.assertEqual(accepted["family_count"], 1)

        historical = self.module.classify_acceptance(
            ("[[S22R4W1B|id=historical-partial\n" f"{marker}\n").encode(),
            acceptance,
        )
        self.assertTrue(historical["accepted"])

        partial_proof = self.module.classify_acceptance(
            f"prefix\n{marker[:24]}".encode(), acceptance
        )
        self.assertFalse(partial_proof["accepted"])
        self.assertTrue(partial_proof["integrity_issue"])

        duplicate = self.module.classify_acceptance(
            f"\n{marker}\n\n{marker}\n".encode(), acceptance
        )
        self.assertFalse(duplicate["accepted"])
        self.assertEqual(duplicate["exact_count"], 2)

        foreign = self.module.classify_acceptance(
            f"\n{family}foreign]]\n".encode(), acceptance
        )
        self.assertFalse(foreign["accepted"])
        self.assertEqual(foreign["foreign_count"], 1)

    def test_rollback_failure_remains_recoverable_without_candidate_replay(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(
            self.module,
            rollback=[
                "odin_device_session_failure_or_unknown",
                "odin_transfer_completed",
            ],
        )
        first = self.module.execute_prepared(
            prepared, prepared.approval_token, backend
        )
        self.assertTrue(first["recovery_required"])
        result = self.module.recover_prepared(prepared, backend)
        self.assertEqual(result["current_state"], "CLOSED")
        self.assertEqual(backend.calls.count("transfer-candidate"), 1)
        self.assertEqual(backend.calls.count("transfer-rollback"), 2)

    def test_second_rollback_interruption_consumes_attempt_and_stops(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(
            self.module,
            rollback=["odin_device_session_failure_or_unknown"],
            crash_rollback_attempt=2,
        )
        first = self.module.execute_prepared(
            prepared, prepared.approval_token, backend
        )
        self.assertTrue(first["recovery_required"])
        with self.assertRaises(KeyboardInterrupt):
            self.module.recover_prepared(prepared, backend)
        with self.assertRaises(self.module.F1LiveError):
            self.module.recover_prepared(prepared, backend)
        self.assertEqual(backend.calls.count("transfer-candidate"), 1)
        self.assertEqual(backend.calls.count("transfer-rollback"), 2)
        journal = self.module.core.Journal.reopen(
            prepared.run_dir / "transaction", prepared.binding_sha256
        )
        checkpoints = [
            record
            for record in journal.records()
            if record["kind"] == "checkpoint"
            and record["action"] == "rollback_transfer_attempt"
        ]
        self.assertEqual(len(checkpoints), 2)

    def test_missing_start_with_durable_checkpoint_stops_before_retry(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        first = FakeBackend(
            self.module,
            rollback=["odin_device_session_failure_or_unknown"],
        )
        result = self.module.execute_prepared(
            prepared, prepared.approval_token, first
        )
        self.assertTrue(result["recovery_required"])
        (prepared.run_dir / "rollback-attempt-01.start.json").unlink()
        recovery = FakeBackend(self.module)
        with self.assertRaises(self.module.F1LiveError):
            self.module.recover_prepared(prepared, recovery)
        self.assertNotIn("transfer-rollback", recovery.calls)

    def test_interruption_before_candidate_start_closes_without_rollback(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(self.module)
        with mock.patch.object(
            self.module,
            "_begin_transfer_attempt",
            side_effect=KeyboardInterrupt("before durable candidate start"),
        ):
            with self.assertRaises(KeyboardInterrupt):
                self.module.execute_prepared(
                    prepared, prepared.approval_token, backend
                )
        recovery = FakeBackend(self.module)
        result = self.module.recover_prepared(prepared, recovery)
        self.assertEqual(result["current_state"], "ABORTED")
        self.assertEqual(
            result["outcome_class"], "interrupted_before_candidate_attempt"
        )
        self.assertNotIn("transfer-candidate", recovery.calls)
        self.assertNotIn("transfer-rollback", recovery.calls)

    def test_orphan_candidate_start_is_consumed_before_rollback(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(self.module)
        original = self.module.core.Journal.checkpoint

        def interrupt_candidate_checkpoint(journal, name, outcome, details=None):
            if name == "candidate_transfer_attempt":
                raise KeyboardInterrupt("after start before checkpoint")
            return original(journal, name, outcome, details)

        with mock.patch.object(
            self.module.core.Journal,
            "checkpoint",
            new=interrupt_candidate_checkpoint,
        ):
            with self.assertRaises(KeyboardInterrupt):
                self.module.execute_prepared(
                    prepared, prepared.approval_token, backend
                )
        recovery = FakeBackend(self.module)
        result = self.module.recover_prepared(prepared, recovery)
        self.assertEqual(
            result["verdict"], "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        )
        self.assertNotIn("transfer-candidate", recovery.calls)
        self.assertEqual(recovery.calls.count("transfer-rollback"), 1)

    def test_interruption_after_candidate_start_recovers_rollback_only(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        crashing = FakeBackend(self.module, crash_candidate=True)
        with self.assertRaises(KeyboardInterrupt):
            self.module.execute_prepared(
                prepared, prepared.approval_token, crashing
            )
        recovery = FakeBackend(
            self.module, candidate="odin_device_session_failure_or_unknown"
        )
        result = self.module.recover_prepared(prepared, recovery)
        self.assertEqual(
            result["verdict"], "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        )
        self.assertNotIn("transfer-candidate", recovery.calls)
        self.assertEqual(recovery.calls.count("transfer-rollback"), 1)

    def test_final_health_retry_does_not_reflash_rollback(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(self.module, final_failures=1)
        with self.assertRaises(RuntimeError):
            self.module.execute_prepared(
                prepared, prepared.approval_token, backend
            )
        result = self.module.recover_prepared(prepared, backend)
        self.assertEqual(result["current_state"], "CLOSED")
        self.assertEqual(backend.calls.count("transfer-rollback"), 1)

    def test_durable_rollback_success_resumes_without_reflash(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(self.module)
        original = self.module._save_state
        interrupted = False

        def interrupt_after_rollback_result(target, value):
            nonlocal interrupted
            if value.get("rollback_completed") is True and not interrupted:
                interrupted = True
                raise KeyboardInterrupt("after durable rollback result")
            return original(target, value)

        with mock.patch.object(
            self.module, "_save_state", new=interrupt_after_rollback_result
        ):
            with self.assertRaises(KeyboardInterrupt):
                self.module.execute_prepared(
                    prepared, prepared.approval_token, backend
                )
        result = self.module.recover_prepared(prepared, backend)
        self.assertEqual(result["current_state"], "CLOSED")
        self.assertEqual(backend.calls.count("transfer-rollback"), 1)

    def test_rollback_event_gaps_resume_without_reflash(self):
        for event_name in (
            "rollback_flash_start",
            "rollback_flash_done",
            "rollback_boot_ready",
            "live_session_end",
        ):
            with self.subTest(event_name=event_name):
                temporary, prepared = self.prepared()
                self.addCleanup(temporary.cleanup)
                backend = FakeBackend(self.module)
                original = self.module.core.Journal.event
                interrupted = False

                def interrupt_event(journal, name, details=None):
                    nonlocal interrupted
                    if name == event_name and not interrupted:
                        interrupted = True
                        raise KeyboardInterrupt(f"before {event_name}")
                    return original(journal, name, details)

                with mock.patch.object(
                    self.module.core.Journal, "event", new=interrupt_event
                ):
                    with self.assertRaises(KeyboardInterrupt):
                        self.module.execute_prepared(
                            prepared, prepared.approval_token, backend
                        )
                result = self.module.recover_prepared(prepared, backend)
                self.assertEqual(result["current_state"], "CLOSED")
                self.assertEqual(backend.calls.count("transfer-rollback"), 1)

    def test_pre_candidate_download_failure_aborts_without_transfer(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(self.module, request_error=True)
        result = self.module.execute_prepared(
            prepared, prepared.approval_token, backend
        )
        self.assertEqual(result["current_state"], "ABORTED")
        self.assertEqual(result["verdict"], "FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD")
        self.assertFalse(any(call.startswith("transfer-") for call in backend.calls))

    def test_pre_journal_preflight_interruption_resumes_append_only(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(self.module, recheck_failures=1)
        with self.assertRaises(RuntimeError):
            self.module.execute_prepared(
                prepared, prepared.approval_token, backend
            )
        result = self.module.execute_prepared(
            prepared, prepared.approval_token, backend
        )
        self.assertEqual(result["current_state"], "CLOSED")
        self.assertTrue((prepared.run_dir / "execute-preflight-01").is_dir())
        self.assertTrue((prepared.run_dir / "execute-preflight-02").is_dir())

    def test_fails_twice_attempt_bound_is_enforced(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        journal = self.module.core.Journal.create(
            prepared.run_dir / "transaction", prepared.binding_sha256
        )
        for state in (
            "APPROVED",
            "DOWNLOAD_IDENTIFIED",
            "CANDIDATE_FLASHED",
            "OBSERVED",
            "RECOVERY_DOWNLOAD",
        ):
            journal.transition(state, "test", {})
        self.module._begin_transfer_attempt(prepared, journal, "rollback")
        self.module._begin_transfer_attempt(prepared, journal, "rollback")
        with self.assertRaises(self.module.F1LiveError):
            self.module._begin_transfer_attempt(prepared, journal, "rollback")

    def test_fails_twice_preflight_bound_is_enforced(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        for attempt in (1, 2):
            (prepared.run_dir / f"execute-preflight-{attempt:02d}").mkdir()
        with self.assertRaises(self.module.F1LiveError):
            self.module._next_execute_preflight(prepared.run_dir)

    def test_result_validator_reopens_raw_observer(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        result = self.module.execute_prepared(
            prepared, prepared.approval_token, FakeBackend(self.module)
        )
        self.module.validate_live_result(result, prepared)
        (prepared.run_dir / "rollback-observer-1.bin").write_bytes(b"tampered")
        with self.assertRaises(self.module.F1LiveError):
            self.module.validate_live_result(result, prepared)

    def test_result_validator_reopens_transfer_attempt_start(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        result = self.module.execute_prepared(
            prepared, prepared.approval_token, FakeBackend(self.module)
        )
        start = prepared.run_dir / "candidate-attempt-01.start.json"
        start.chmod(0o600)
        value = json.loads(start.read_text(encoding="utf-8"))
        value["attempt"] = 2
        start.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(self.module.F1LiveError):
            self.module.validate_live_result(result, prepared)

    def test_download_identity_requires_same_topology_and_no_serial(self):
        with tempfile.TemporaryDirectory() as temporary:
            usb = Path(temporary)
            node = usb / "1-2"
            node.mkdir()
            values = {
                "busnum": "1",
                "devnum": "5",
                "idVendor": "04e8",
                "idProduct": "685d",
                "product": "SAMSUNG USB",
                "manufacturer": "Samsung",
            }
            for name, value in values.items():
                (node / name).write_text(value, encoding="utf-8")
            fixture, prepared = self.prepared()
            self.addCleanup(fixture.cleanup)
            profile = prepared.bundle.profile
            evidence = self.module.validate_download_endpoint(
                "/dev/bus/usb/001/005", "usb:1-2", profile, usb
            )
            self.assertTrue(evidence["identity"]["serial_absent"])
            (node / "serial").write_text("unexpected", encoding="utf-8")
            with self.assertRaises(self.module.F1LiveError):
                self.module.validate_download_endpoint(
                    "/dev/bus/usb/001/005", "usb:1-2", profile, usb
                )

    def test_prepare_and_reopen_bind_private_target_and_source_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "workspace/private").mkdir(parents=True)
            fixture = f1_core_tests.DeviceActionF1V2Test()
            fixture.module = self.module.core
            _profile, manifest, _profile_path, manifest_path = fixture.fixture(root)
            manifest["status"] = "ready-for-f1-approval"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            bundle = self.module.core.verify_bundle(root, manifest_path)
            run_dir = self.module.allocate_run_dir(root, None)
            serial = "fixture-serial"
            topology = "usb:1-2"
            target_evidence = {
                "schema": self.module.core.TARGET_EVIDENCE_SCHEMA,
                "targets": [
                    {
                        "model": "SM-S906N",
                        "device": "g0q",
                        "firmware_incremental": "S906NKSS7FYG8",
                        "android_transport": "adb",
                        "adb_serial_sha256": hashlib.sha256(
                            serial.encode()
                        ).hexdigest(),
                        "usb_topology_sha256": hashlib.sha256(
                            topology.encode()
                        ).hexdigest(),
                    }
                ],
                "odin_endpoint_absent": True,
            }
            d0_result = {"target_evidence": target_evidence}

            class Client:
                @staticmethod
                def one_serial():
                    return serial

                @staticmethod
                def topology(_serial):
                    return topology

            def collect(_bundle, destination, _client, _usb_root):
                self.module._write_exclusive(destination / "result.json", d0_result)
                return d0_result

            with mock.patch.object(self.module.d0, "collect_connected", collect), mock.patch.object(
                self.module.d0, "validate_result", return_value=d0_result
            ):
                prepared_record = self.module.prepare_connected(
                    root, bundle, run_dir, Client()
                )
                reopened = self.module.load_prepared(root, manifest_path, run_dir)
            self.assertEqual(reopened.approval_token, prepared_record["approval_token"])
            manifest["status"] = "draft-host-only"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with mock.patch.object(
                self.module.d0, "validate_result", return_value=d0_result
            ), self.assertRaises(self.module.F1LiveError):
                self.module.load_prepared(root, manifest_path, run_dir)
            manifest["status"] = "ready-for-f1-approval"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            target_path = run_dir / "target-private.json"
            changed = json.loads(target_path.read_text(encoding="utf-8"))
            changed["serial"] = "tampered"
            target_path.chmod(0o600)
            target_path.write_text(json.dumps(changed), encoding="utf-8")
            with mock.patch.object(
                self.module.d0, "validate_result", return_value=d0_result
            ), self.assertRaises(self.module.F1LiveError):
                self.module.load_prepared(root, manifest_path, run_dir)

    def test_run_directory_must_be_direct_private_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "workspace/private").mkdir(parents=True)
            nested = root / self.module.DEFAULT_RUN_ROOT / "nested/run"
            with self.assertRaises(self.module.F1LiveError):
                self.module.allocate_run_dir(root, nested)

    def test_cli_separates_prepare_execute_and_recovery(self):
        options = self.module.build_parser()._option_string_actions
        for expected in ("--prepare", "--execute", "--recover", "--approval"):
            self.assertIn(expected, options)
        plan = self.module.render_plan(ROOT, self.module.core.verify_bundle(ROOT, self.module.core.DEFAULT_MANIFEST))
        self.assertTrue(plan["prepare_is_d0_only"])
        self.assertTrue(plan["execute_requires_fresh_exact_approval"])
        self.assertFalse(plan["recover_can_transfer_candidate"])
        self.assertEqual(plan["manifest_status"], "draft-host-only")

    def test_data_only_canary_manifest_is_explicitly_ready(self):
        manifest = (
            ROOT
            / "workspace/public/src/device-action/manifests/"
            "s22plus_fyg8_r4w1c_process_v2_canary_1.json"
        )
        bundle = self.module.core.verify_bundle(ROOT, manifest)
        plan = self.module.render_plan(ROOT, bundle)
        self.assertEqual(plan["manifest_status"], "ready-for-f1-approval")
        self.assertEqual(
            plan["manifest_id"], "s22plus-fyg8-r4w1c-process-v2-canary-1"
        )
        self.assertFalse(plan["f1_authorized"])
        self.assertFalse(plan["live_authorized"])

    def test_cli_refuses_draft_prepare_before_run_allocation(self):
        with mock.patch.object(
            self.module, "allocate_run_dir", side_effect=AssertionError("must not allocate")
        ) as allocate, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.module.main(["--prepare"]), 2)
        allocate.assert_not_called()

    def test_cli_recovery_rejects_approval_before_prepared_load(self):
        with mock.patch.object(
            self.module, "load_prepared", side_effect=AssertionError("must not load")
        ) as load, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                self.module.main(
                    [
                        "--recover",
                        "--run-dir",
                        "workspace/private/runs/device-action-f1-live-v2/missing",
                        "--approval",
                        "forbidden",
                    ]
                ),
                2,
            )
        load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
