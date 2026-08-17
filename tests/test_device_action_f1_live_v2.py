import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import types
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


class FakeCandidateObserver:
    def __init__(self, module, prepared, classification):
        self.module = module
        self.prepared = prepared
        self.classification = classification

    def observe(self, *, timeout_sec, download_departure):
        if self.classification == "fault":
            raise self.module.cdc_acm_observer.ObserverError(
                "fixture observer fault"
            )
        spec = self.prepared.bundle.manifest["observation"][
            "candidate_observer"
        ]
        payload = (
            bytes.fromhex(spec["banner_hex"])
            if self.classification == "accepted"
            else b""
        )
        raw_handle = self.module.cdc_acm_observer.raw_capture.publish_captured_bytes(
            self.prepared.run_dir,
            "candidate-observer",
            stdout=payload,
            stdout_name="candidate-observer.raw",
            stderr_name="candidate-observer.raw.stderr",
        )
        raw = {
            "path": str(raw_handle.stdout_path),
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "capture_receipt": {
                "path": str(raw_handle.receipt_path),
                "size": raw_handle.receipt_path.stat().st_size,
                "sha256": hashlib.sha256(
                    raw_handle.receipt_path.read_bytes()
                ).hexdigest(),
            },
        }
        baseline = self.module.cdc_acm_observer.persist_json(
            self.prepared.run_dir / "candidate-observer-baseline.json",
            {
                "schema": self.module.cdc_acm_observer.BASELINE_SCHEMA,
                "spec_sha256": self.module.cdc_acm_observer.digest(spec),
                "topology_sha256": hashlib.sha256(b"1-1").hexdigest(),
                "identity_sha256": [],
                "exact_candidate_absent": True,
            },
        )
        download_departure = {
            "download_endpoint_absent": download_departure[
                "download_endpoint_absent"
            ],
            "absence_timed_out": False,
            "sequence": 1,
        }
        departure = self.module.cdc_acm_observer.persist_json(
            self.prepared.run_dir
            / "candidate-observer-download-departure.json",
            download_departure,
        )
        guard_dir = self.module.cdc_acm_observer.raw_capture.prepare_capture_dir(
            self.prepared.run_dir, "raw-cdc-guard"
        )
        guard_payload = b"fixture guard armed\n"
        guard_handle = self.module.cdc_acm_observer.raw_capture.publish_captured_bytes(
            guard_dir, "guard-arm", stdout=guard_payload
        )
        guard = self.module.cdc_acm_observer.persist_json(
            self.prepared.run_dir / "candidate-observer-guard.json",
            {
                "schema": self.module.cdc_acm_observer.GUARD_SCHEMA,
                "status": "armed",
                "spec_sha256": self.module.cdc_acm_observer.digest(spec),
                "topology_sha256": hashlib.sha256(b"1-1").hexdigest(),
                "rule_sha256": hashlib.sha256(
                    self.module.cdc_acm_observer._guard_rule(
                        spec, "usb:1-1"
                    )
                ).hexdigest(),
                "instance_sha256": "5" * 64,
                "output_sha256": hashlib.sha256(guard_payload).hexdigest(),
                "raw_capture_receipt": {
                    "path": str(guard_handle.receipt_path),
                    "size": guard_handle.receipt_path.stat().st_size,
                    "sha256": hashlib.sha256(
                        guard_handle.receipt_path.read_bytes()
                    ).hexdigest(),
                },
                "child_alive": True,
            },
        )
        value = {
            "schema": self.module.cdc_acm_observer.RECEIPT_SCHEMA,
            "kind": self.module.cdc_acm_observer.KIND,
            "binding": self.module._candidate_observer_binding(self.prepared),
            "spec_sha256": self.module.cdc_acm_observer.digest(spec),
            "baseline_sha256": baseline["sha256"],
            "download_departure_sha256": departure["sha256"],
            "download_endpoint_absent": (
                download_departure["download_endpoint_absent"] is True
            ),
            "topology_sha256": hashlib.sha256(b"1-1").hexdigest(),
            "endpoint_identity_sha256": (
                "3" * 64 if self.classification == "accepted" else None
            ),
            "guard_sha256": guard["sha256"],
            "raw": raw,
            "expected_size": len(bytes.fromhex(spec["banner_hex"])),
            "exact": self.classification == "accepted",
            "extra_byte": self.classification == "extra-byte",
            "classification": self.classification,
            "accepted": self.classification == "accepted",
            "bounded": True,
            "elapsed_sec": min(timeout_sec, 0.01),
        }
        self.module.cdc_acm_observer.persist_json(
            self.prepared.run_dir / "candidate-observer.json", value
        )
        return value


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
        acm=None,
        observer_arm_error=False,
        observer_release="released",
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
        self.acm = acm
        self.observer_arm_error = observer_arm_error
        self.observer_release = observer_release
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

    def candidate_observer_session(self, prepared):
        if self.observer_arm_error:
            @contextlib.contextmanager
            def failed():
                raise RuntimeError("fixture observer arm failure")
                yield

            return failed()
        spec = prepared.bundle.manifest["observation"].get(
            "candidate_observer"
        )
        if spec is None:
            return contextlib.nullcontext(None)
        @contextlib.contextmanager
        def observing():
            try:
                yield FakeCandidateObserver(
                    self.module, prepared, self.acm or "accepted"
                )
            finally:
                if self.observer_release == "released":
                    release = {
                        "schema": self.module.cdc_acm_observer.GUARD_SCHEMA,
                        "status": "released",
                        "instance_sha256": "5" * 64,
                        "returncode": 0,
                        "released": True,
                    }
                elif self.observer_release == "guard-expired":
                    release = {
                        "schema": self.module.cdc_acm_observer.GUARD_SCHEMA,
                        "status": "guard-expired",
                        "instance_sha256": "5" * 64,
                        "returncode": (
                            self.module.cdc_acm_observer.GUARD_EXPIRED_EXIT
                        ),
                        "released": False,
                    }
                elif self.observer_release == "guard-exited-uncommanded":
                    release = {
                        "schema": self.module.cdc_acm_observer.GUARD_SCHEMA,
                        "status": "guard-exited-uncommanded",
                        "instance_sha256": "5" * 64,
                        "returncode": 0,
                        "released": False,
                    }
                else:
                    release = {
                        "schema": self.module.cdc_acm_observer.GUARD_SCHEMA,
                        "status": "release-failed",
                        "instance_sha256": "5" * 64,
                        "returncode": 1,
                        "released": False,
                    }
                self.module.cdc_acm_observer.persist_json(
                    prepared.run_dir
                    / "candidate-observer-guard-release.json",
                    release,
                )

        return observing()

    def wait_download(self, _prepared, _run_dir, _lease, _timeout):
        self.calls.append("wait-download")
        return self.module.Endpoint("/dev/bus/usb/001/002", 1, "2" * 64)

    def _write_transfer(self, prepared, kind, classification, attempt, prefix):
        if classification == "odin_transfer_completed":
            stdout = (
                b"Setup Connection\nUpload Binaries\nboot.img.lz4\n"
                b"100%\nClose Connection\n"
            )
            returncode = 0
        elif classification == "odin_local_parse_failure":
            stdout = b"Fail parse\n"
            returncode = 1
        else:
            stdout = f"{kind}:device-session-unknown\n".encode()
            returncode = 1
        stderr = b""
        handle = self.module.raw_capture.publish_captured_bytes(
            prepared.run_dir,
            f"{prefix}-odin",
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
            argv0_name="odin4",
            stdout_name=f"{prefix}.stdout",
            stderr_name=f"{prefix}.stderr",
        )
        stdout_receipt = {
            "path": str(handle.stdout_path),
            "size": len(stdout),
            "sha256": hashlib.sha256(stdout).hexdigest(),
        }
        stderr_receipt = {
            "path": str(handle.stderr_path),
            "size": len(stderr),
            "sha256": hashlib.sha256(stderr).hexdigest(),
        }
        item = (
            prepared.bundle.manifest["candidate_ap"]
            if kind == "candidate"
            else prepared.bundle.manifest["rollback_ap"]
        )
        raw_payload = handle.receipt_path.read_bytes()
        value = {
            "schema": "device_action_f1_transfer_receipt_v2",
            "kind": kind,
            "attempt": attempt,
            "prefix": prefix,
            "classification": classification,
            "transport": {
                "label": kind,
                "returncode": handle.returncode,
                "timed_out": False,
                "output_exceeded": False,
                "producer_error_type": None,
                "command_shape": [
                    "odin4",
                    "--reboot",
                    "-a",
                    "AP.tar.md5",
                    "-d",
                    "USBFS",
                ],
                "regular_path_inputs": True,
                "anonymous_proc_fd_inputs": False,
                "odin": prepared.bundle.profile["transport"]["odin"],
                "ap": {
                    "path": str(
                        self.module.core._artifact_path(
                            prepared.root, item, f"{kind}_ap"
                        )
                    ),
                    "size": item["size"],
                    "sha256": item["sha256"],
                },
                "stdout_bytes": len(stdout),
                "stderr_bytes": len(stderr),
                "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                "raw_capture_receipt": {
                    "path": str(handle.receipt_path),
                    "size": len(raw_payload),
                    "sha256": hashlib.sha256(raw_payload).hexdigest(),
                },
            },
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

    def observe_candidate(
        self, prepared, _run_dir, _lease, observer_session
    ):
        self.calls.append("observe")
        if observer_session is not None:
            try:
                receipt = observer_session.observe(
                    timeout_sec=prepared.bundle.manifest["observation"][
                        "timeout_sec"
                    ],
                    download_departure={"download_endpoint_absent": True},
                )
            except self.module.cdc_acm_observer.ObserverError:
                receipt = {
                    "classification": "interrupted-before-receipt",
                    "accepted": False,
                }
            return {
                "bounded": True,
                "download_endpoint_absent": True,
                "candidate_execution_proven": receipt["accepted"],
                "candidate_observer_classification": receipt[
                    "classification"
                ],
                "candidate_observer_accepted": receipt["accepted"],
            }
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
            handle = self.module.raw_capture.publish_captured_bytes(
                destination,
                f"900{index}-observer-eof",
                stdout=payload,
                stdout_name=path.name,
                stderr_name=path.name + ".stderr",
            )
            reads.append(
                {
                    "path": str(path),
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "raw_capture": {
                        "path": str(handle.receipt_path),
                        "size": handle.receipt_path.stat().st_size,
                        "sha256": hashlib.sha256(
                            handle.receipt_path.read_bytes()
                        ).hexdigest(),
                    },
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

    def prepared(self, *, e3=False):
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
            "transport": {
                "odin": {
                    "path": "/fixture/odin4",
                    "size": 1,
                    "sha256": "8" * 64,
                }
            },
        }
        manifest = {
            "manifest_id": "fixture-manifest",
            "status": "ready-for-f1-approval",
            "candidate_ap": {
                "path": "fixture-candidate.tar.md5",
                "size": 1,
                "sha256": "9" * 64,
            },
            "rollback_ap": {
                "path": "fixture-rollback.tar.md5",
                "size": 1,
                "sha256": "7" * 64,
            },
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
        if e3:
            manifest["observation"]["candidate_observer"] = {
                "kind": "exact_cdc_acm_banner_v1",
                "usb_vendor_id": "04e8",
                "usb_product_id": "6861",
                "usb_serial": "S22E3" + "1" * 32,
                "usb_driver": "cdc_acm",
                "usb_interface_number": "00",
                "banner_hex": (
                    b"S22PLUS-FYG8-E3:" + b"1" * 32 + b"\n"
                ).hex(),
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
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = self.module.execute_prepared(
                prepared, prepared.approval_token, backend
            )
        self.assertEqual(
            result["verdict"], "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK"
        )
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Enter physical Download mode", stderr.getvalue())
        self.assertEqual(
            [event["name"] for event in result["timeline"]["events"]],
            list(self.module.core.TIMELINE),
        )
        self.assertEqual(
            [call for call in backend.calls if call.startswith("transfer-")],
            ["transfer-candidate", "transfer-rollback"],
        )

    def test_e3_all_of_verdict_matrix(self):
        cases = (
            (
                "accepted",
                True,
                "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK",
            ),
            (
                "read-timeout",
                True,
                "DIAGNOSTIC_F1_V2_RETAINED_ONLY_ROLLED_BACK",
            ),
            (
                "accepted",
                False,
                "DIAGNOSTIC_F1_V2_ACM_ONLY_ROLLED_BACK",
            ),
            (
                "read-timeout",
                False,
                "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
            ),
        )
        for acm, marker, verdict in cases:
            with self.subTest(acm=acm, marker=marker):
                temporary, prepared = self.prepared(e3=True)
                self.addCleanup(temporary.cleanup)
                result = self.module.execute_prepared(
                    prepared,
                    prepared.approval_token,
                    FakeBackend(self.module, acm=acm, marker=marker),
                )
                self.assertEqual(result["verdict"], verdict)

    def test_e3_acm_acceptance_cannot_outvote_failed_candidate_transfer(self):
        temporary, prepared = self.prepared(e3=True)
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(
            self.module.F1LiveError, "lacks transfer continuity"
        ):
            self.module.execute_prepared(
                prepared,
                prepared.approval_token,
                FakeBackend(
                    self.module,
                    candidate="odin_device_session_failure_or_unknown",
                    acm="accepted",
                ),
            )

    def test_e3_resume_reopens_durable_observer_without_reobservation(self):
        temporary, prepared = self.prepared(e3=True)
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(self.module, acm="accepted")
        original = self.module._save_state

        def interrupt_after_receipt(target, value):
            if "candidate_observer_classification" in value:
                raise KeyboardInterrupt("after observer receipt")
            return original(target, value)

        with mock.patch.object(
            self.module, "_save_state", new=interrupt_after_receipt
        ):
            with self.assertRaises(KeyboardInterrupt):
                self.module.execute_prepared(
                    prepared, prepared.approval_token, backend
                )
        recovery = FakeBackend(self.module, acm="read-timeout")
        result = self.module.recover_prepared(prepared, recovery)
        self.assertEqual(
            result["verdict"],
            "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK",
        )
        self.assertNotIn("observe", recovery.calls)
        self.assertNotIn("transfer-candidate", recovery.calls)

    def test_e3_candidate_flashed_recovery_keeps_acm_after_expiry(self):
        temporary, prepared = self.prepared(e3=True)
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(
            self.module,
            acm="accepted",
            marker=True,
            observer_release="guard-expired",
        )
        original = self.module._save_state

        def interrupt_before_observed(target, value):
            if (
                "candidate_observer_classification" in value
                and "candidate_observer_guard_release_status" not in value
            ):
                raise KeyboardInterrupt("before OBSERVED")
            return original(target, value)

        with mock.patch.object(
            self.module, "_save_state", new=interrupt_before_observed
        ):
            with self.assertRaises(KeyboardInterrupt):
                self.module.execute_prepared(
                    prepared, prepared.approval_token, backend
                )
        journal = self.module.core.Journal.reopen(
            prepared.run_dir / "transaction", prepared.binding_sha256
        )
        self.assertEqual(journal.state(), "CANDIDATE_FLASHED")
        self.assertTrue(
            (
                prepared.run_dir
                / "candidate-observer-guard-release.json"
            ).is_file()
        )

        recovery = FakeBackend(self.module, marker=True)
        result = self.module.recover_prepared(prepared, recovery)
        self.assertEqual(
            result["verdict"],
            "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK",
        )
        self.assertEqual(
            result["outcome_class"],
            "candidate_proven_rollback_verified",
        )
        self.assertEqual(
            result["live_state"][
                "candidate_observer_guard_release_status"
            ],
            "guard-expired",
        )
        self.assertFalse(
            result["live_state"]["candidate_observer_guard_released"]
        )
        self.assertEqual(
            result["live_state"]["candidate_observer_guard_warning"],
            "guard-expired",
        )
        self.assertNotIn("observe", recovery.calls)
        self.assertNotIn("transfer-candidate", recovery.calls)
        observed = next(
            item
            for item in self.module.core.Journal.reopen(
                prepared.run_dir / "transaction",
                prepared.binding_sha256,
            ).records()
            if item["kind"] == "transition"
            and item["state"] == "OBSERVED"
        )
        self.assertEqual(
            observed["details"][
                "candidate_observer_guard_release_status"
            ],
            "guard-expired",
        )
        self.assertTrue(observed["details"]["proof"])

    def test_e3_observer_fault_after_transfer_degrades_to_diagnostic(self):
        temporary, prepared = self.prepared(e3=True)
        self.addCleanup(temporary.cleanup)
        backend = object.__new__(self.module.SamsungOdinBackend)
        backend.odin = Path("/fixture/odin")
        failed = mock.Mock()
        failed.observe.side_effect = (
            self.module.cdc_acm_observer.ObserverError("fixture fault")
        )
        absence = types.SimpleNamespace(
            absent=True, timed_out=False, next_sequence=7
        )
        with (
            mock.patch.object(
                self.module.odin_core,
                "list_snapshot_receipts",
                return_value=[],
            ),
            mock.patch.object(
                self.module.odin_core,
                "wait_for_no_live_endpoint",
                return_value=absence,
            ),
        ):
            result = backend.observe_candidate(
                prepared, prepared.run_dir, object(), failed
            )
        self.assertEqual(
            result["candidate_observer_classification"],
            "interrupted-before-receipt",
        )
        self.assertFalse(result["candidate_observer_accepted"])

    def test_real_adb_client_recheck_and_final_observer_use_separate_raw_phases(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        adb = prepared.root / "fixture-adb"
        counter = prepared.root / "observer-count"
        marker = prepared.bundle.manifest["observation"]["acceptance"]["marker"]
        adb.write_text(
            f"""#!{sys.executable}
import pathlib
import sys

args = sys.argv[1:]
joined = " ".join(args)
counter = pathlib.Path({str(counter)!r})
if args == ["version"]:
    print("Android Debug Bridge version 1.0.41")
elif args == ["devices", "-l"]:
    print("List of devices attached")
    print("s device model:SM_S906N device:g0q transport_id:2")
elif args[-1:] == ["get-devpath"]:
    print("usb:1-1")
elif "getprop ro.product.model" in joined:
    print("model=SM-S906N")
    print("device=g0q")
    print("bootloader=S906NKSS7FYG8")
    print("incremental=S906NKSS7FYG8")
    print("boot_completed=1")
    print("bootanim=stopped")
    print("verified_boot_state=orange")
    print("boot_id=12345678-1234-1234-1234-123456789abc")
    print("kernel_release=fixture-kernel")
elif "sha256sum /dev/block/by-name/boot" in joined:
    print("root=uid=0(root) gid=0(root)")
    print("boot={'a' * 64}")
    print("vendor_boot={'b' * 64}")
    print("dtbo={'c' * 64}")
    print("recovery={'d' * 64}")
elif "exec-out" in args:
    count = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(count + 1))
    if count == 0:
        print("clean retained log")
    else:
        print("prefix")
        print({marker!r})
        print("suffix")
else:
    raise SystemExit(2)
""",
            encoding="utf-8",
        )
        adb.chmod(0o500)
        backend = object.__new__(self.module.SamsungOdinBackend)
        backend.root = prepared.root
        backend.bundle = prepared.bundle
        backend.adb = adb.resolve(strict=True)
        backend.client = self.module.d0.adb_client_for_bundle(
            backend.adb, prepared.bundle
        )
        backend.usb_root = prepared.root / "unused-usb"
        backend.odin = prepared.root / "unused-odin"
        properties = {
            "model": "SM-S906N",
            "device": "g0q",
            "incremental": "S906NKSS7FYG8",
        }
        target = self.module.d0._target_evidence(
            prepared.bundle, properties, "s", "usb:1-1"
        )
        prepared_preflight = prepared.run_dir / "preflight"
        prepared_preflight.mkdir()
        (prepared_preflight / "result.json").write_text(
            json.dumps({"target_evidence": target}), encoding="utf-8"
        )
        usb = {
            "enumerated_devices": 1,
            "download_endpoint_count": 0,
            "snapshot_sha256": "0" * 64,
        }
        absence = types.SimpleNamespace(absent=True, timed_out=False)
        with (
            mock.patch.object(self.module.d0, "usb_snapshot", return_value=usb),
            mock.patch.object(
                self.module.d0,
                "_inspect_clean_baseline",
                return_value=(
                    {
                        "baseline_clean": True,
                        "family_count": 0,
                        "exact_record_count": 0,
                        "integrity_issue": False,
                    },
                    None,
                ),
            ),
            mock.patch.object(
                self.module.odin_core, "list_snapshot_receipts", return_value=[]
            ),
            mock.patch.object(
                self.module.odin_core,
                "wait_for_no_live_endpoint",
                return_value=absence,
            ),
            mock.patch.object(self.module.time, "sleep", return_value=None),
        ):
            recheck = backend.recheck_android(
                prepared, prepared.run_dir / "execute-preflight-01"
            )
            final = backend.verify_final(
                prepared, prepared.run_dir / "odin-endpoints", object(), prepared.run_dir
            )
        self.assertTrue(recheck["healthy"])
        self.assertTrue(final["observer"]["accepted"], final)
        self.module._validate_final_observer(
            prepared,
            {
                "final_evidence": final,
                "marker_accepted": True,
            },
        )
        self.assertTrue(
            (prepared.run_dir / "execute-preflight-01/raw-adb").is_dir()
        )
        self.assertTrue((prepared.run_dir / "raw-adb").is_dir())
        for receipt in final["observer"]["reads"]:
            handle = self.module.raw_capture.load_handle(
                Path(receipt["raw_capture"]["path"])
            )
            self.assertEqual(handle.receipt_path.parent, prepared.run_dir)

    def test_e3_observer_fault_closes_after_verified_rollback(self):
        temporary, prepared = self.prepared(e3=True)
        self.addCleanup(temporary.cleanup)
        result = self.module.execute_prepared(
            prepared,
            prepared.approval_token,
            FakeBackend(self.module, acm="fault", marker=True),
        )
        self.assertEqual(
            result["verdict"], "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        )
        self.assertEqual(result["current_state"], "CLOSED")
        self.assertFalse(
            result["live_state"]["download_endpoint_absent"]
        )

    def test_e3_guard_release_failure_rolls_back_once_and_refuses_pass(self):
        temporary, prepared = self.prepared(e3=True)
        self.addCleanup(temporary.cleanup)
        backend = FakeBackend(
            self.module,
            acm="accepted",
            marker=True,
            observer_release="release-failed",
        )
        result = self.module.execute_prepared(
            prepared, prepared.approval_token, backend
        )
        self.assertEqual(
            result["verdict"], "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        )
        self.assertEqual(
            result["outcome_class"],
            "candidate_observer_guard_release_failed_rollback_verified",
        )
        self.assertFalse(
            result["live_state"]["candidate_observer_guard_released"]
        )
        self.assertEqual(
            [call for call in backend.calls if call.startswith("transfer-")],
            ["transfer-candidate", "transfer-rollback"],
        )

    def test_e3_exact_acm_survives_cleanup_confirmed_guard_loss(self):
        for release_status in (
            "guard-expired",
            "guard-exited-uncommanded",
        ):
            with self.subTest(release_status=release_status):
                temporary, prepared = self.prepared(e3=True)
                self.addCleanup(temporary.cleanup)
                result = self.module.execute_prepared(
                    prepared,
                    prepared.approval_token,
                    FakeBackend(
                        self.module,
                        acm="accepted",
                        marker=True,
                        observer_release=release_status,
                    ),
                )
                self.assertEqual(
                    result["verdict"],
                    "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK",
                )
                self.assertEqual(
                    result["outcome_class"],
                    "candidate_proven_rollback_verified",
                )
                self.assertEqual(
                    result["live_state"][
                        "candidate_observer_guard_release_status"
                    ],
                    release_status,
                )
                self.assertFalse(
                    result["live_state"][
                        "candidate_observer_guard_released"
                    ]
                )
                self.assertEqual(
                    result["live_state"][
                        "candidate_observer_guard_warning"
                    ],
                    release_status,
                )
                mutation = dict(result["live_state"])
                mutation["candidate_observer_guard_warning"] = None
                with self.assertRaisesRegex(
                    self.module.F1LiveError,
                    "candidate observer durable state mismatch",
                ):
                    self.module._validate_candidate_observer_state(
                        prepared, mutation
                    )

    def test_e3_absent_acm_with_guard_expiry_remains_indeterminate(self):
        temporary, prepared = self.prepared(e3=True)
        self.addCleanup(temporary.cleanup)
        result = self.module.execute_prepared(
            prepared,
            prepared.approval_token,
            FakeBackend(
                self.module,
                acm="read-timeout",
                marker=True,
                observer_release="guard-expired",
            ),
        )
        self.assertEqual(
            result["verdict"], "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        )
        self.assertEqual(
            result["outcome_class"],
            "candidate_observer_guard_expired_rollback_verified",
        )
        self.assertEqual(
            result["live_state"]["candidate_observer_guard_warning"],
            "guard-expired",
        )
        mutation = dict(result)
        mutation["outcome_class"] = (
            "candidate_observer_guard_release_failed_rollback_verified"
        )
        with self.assertRaisesRegex(
            self.module.F1LiveError, "guard failure outcome"
        ):
            self.module.validate_live_result(mutation, prepared)

    def test_e3_acm_only_survives_guard_expiry(self):
        temporary, prepared = self.prepared(e3=True)
        self.addCleanup(temporary.cleanup)
        result = self.module.execute_prepared(
            prepared,
            prepared.approval_token,
            FakeBackend(
                self.module,
                acm="accepted",
                marker=False,
                observer_release="guard-expired",
            ),
        )
        self.assertEqual(
            result["verdict"],
            "DIAGNOSTIC_F1_V2_ACM_ONLY_ROLLED_BACK",
        )

    def test_e3_resume_after_observed_rederives_asymmetric_guard_proof(self):
        cases = (
            (
                "release-failed",
                "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
                "candidate_observer_guard_release_failed_rollback_verified",
                False,
            ),
            (
                "guard-expired",
                "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK",
                "candidate_proven_rollback_verified",
                True,
            ),
        )
        for release_status, verdict, outcome, proof in cases:
            with self.subTest(release_status=release_status):
                temporary, prepared = self.prepared(e3=True)
                self.addCleanup(temporary.cleanup)
                backend = FakeBackend(
                    self.module,
                    acm="accepted",
                    marker=True,
                    observer_release=release_status,
                )
                original = self.module.core.Journal.event

                def interrupt_before_boot_ready(
                    journal, action, details, original_event=original
                ):
                    if action == "candidate_boot_ready":
                        raise KeyboardInterrupt("after OBSERVED")
                    return original_event(journal, action, details)

                with mock.patch.object(
                    self.module.core.Journal,
                    "event",
                    new=interrupt_before_boot_ready,
                ):
                    with self.assertRaises(KeyboardInterrupt):
                        self.module.execute_prepared(
                            prepared, prepared.approval_token, backend
                        )
                result = self.module.recover_prepared(
                    prepared, FakeBackend(self.module, marker=True)
                )
                self.assertEqual(
                    result["verdict"],
                    verdict,
                )
                self.assertEqual(result["outcome_class"], outcome)
                self.assertEqual(
                    result["live_state"][
                        "candidate_observer_guard_release_status"
                    ],
                    release_status,
                )
                boot_ready = next(
                    item
                    for item in self.module.core.Journal.reopen(
                        prepared.run_dir / "transaction",
                        prepared.binding_sha256,
                    ).records()
                    if item["kind"] == "event"
                    and item["action"] == "candidate_boot_ready"
                )
                self.assertIs(boot_ready["details"]["proof"], proof)

    def test_e3_pre_candidate_abort_and_local_parse_are_reportable(self):
        cases = (
            (
                {"observer_arm_error": True},
                "FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD",
            ),
            (
                {"request_error": True},
                "FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD",
            ),
            (
                {"candidate": "odin_local_parse_failure"},
                "FAIL_F1_V2_ODIN_LOCAL_PARSE_NO_DEVICE_SESSION",
            ),
        )
        for backend_args, verdict in cases:
            with self.subTest(verdict=verdict):
                temporary, prepared = self.prepared(e3=True)
                self.addCleanup(temporary.cleanup)
                result = self.module.execute_prepared(
                    prepared,
                    prepared.approval_token,
                    FakeBackend(self.module, **backend_args),
                )
                self.assertEqual(result["verdict"], verdict)
                self.assertEqual(result["current_state"], "ABORTED")

    def test_e3_malformed_receipt_is_fail_closed_without_parser_escape(self):
        temporary, prepared = self.prepared(e3=True)
        self.addCleanup(temporary.cleanup)
        observer = FakeCandidateObserver(
            self.module, prepared, "accepted"
        )
        observer.observe(
            timeout_sec=1,
            download_departure={"download_endpoint_absent": True},
        )
        path = prepared.run_dir / "candidate-observer.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["classification"] = []
        path.chmod(0o600)
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        reopened = self.module._reopen_candidate_observation(prepared)
        self.assertEqual(
            reopened["classification"], "interrupted-before-receipt"
        )
        self.assertFalse(reopened["accepted"])

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

    def test_same_ring_typed_observer_dispatches_without_generic_marker_fields(self):
        evidence = self.module.typed_evidence
        same_ring = evidence.same_ring
        acceptance = {
            "kind": evidence.SAME_RING_KIND,
            "source": evidence.CHECKPOINT_SOURCE,
            "decoder": evidence.SAME_RING_DECODER,
            "contract_id": evidence.SAME_RING_CONTRACT_ID,
            "records": {
                "entry_hex": same_ring.ENTRY_PROOF.hex(),
                "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
                "unsat_hex": same_ring.UNSAT_PROOF.hex(),
            },
            "families": {
                "long_hex": same_ring.ENTRY_FAMILY.hex(),
                "unsat_hex": same_ring.UNSAT_FAMILY.hex(),
            },
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
            "exact_count": 1,
            "contract": {
                "run_manifest": {
                    "path": "workspace/private/p219-run-manifest.json",
                    "size": 1,
                    "sha256": "1" * 64,
                },
                "static_check": {
                    "path": "workspace/private/p219-static-check.json",
                    "size": 1,
                    "sha256": "2" * 64,
                },
            },
        }
        accepted = self.module.classify_acceptance(
            b"prefix" + same_ring.USERSPACE_PROOF + b"suffix",
            acceptance,
        )
        diagnostic = self.module.classify_acceptance(
            same_ring.UNSAT_PROOF,
            acceptance,
        )
        self.assertTrue(accepted["accepted"])
        self.assertEqual(
            accepted["classification"], "USERSPACE_CALLBACK_REACHED"
        )
        self.assertFalse(diagnostic["accepted"])
        self.assertEqual(
            diagnostic["classification"],
            "UNSAT_VALID_MAGIC_ENTRY_DID_NOT_FIT",
        )

    def test_same_ring_multiboot_typed_observer_accepts_recovery_reboots(self):
        evidence = self.module.typed_evidence
        records = evidence.same_ring
        acceptance = {
            "kind": evidence.SAME_RING_MULTIBOOT_KIND,
            "source": evidence.CHECKPOINT_SOURCE,
            "decoder": evidence.SAME_RING_MULTIBOOT_DECODER,
            "contract_id": evidence.SAME_RING_CONTRACT_ID,
            "policy_id": evidence.SAME_RING_MULTIBOOT_POLICY_ID,
            "records": {
                "entry_hex": records.ENTRY_PROOF.hex(),
                "userspace_hex": records.USERSPACE_PROOF.hex(),
                "unsat_hex": records.UNSAT_PROOF.hex(),
            },
            "families": {
                "long_hex": records.ENTRY_FAMILY.hex(),
                "unsat_hex": records.UNSAT_FAMILY.hex(),
            },
            "accepted_identity": (
                "USERSPACE_CALLBACK_REACHED_ONE_OR_MORE_BOOTS"
            ),
            "minimum_exact_count": 1,
            "contract": {
                "run_manifest": {
                    "path": "workspace/private/p219-run-manifest.json",
                    "size": 1,
                    "sha256": "1" * 64,
                },
                "static_check": {
                    "path": "workspace/private/p219-static-check.json",
                    "size": 1,
                    "sha256": "2" * 64,
                },
            },
        }
        result = self.module.classify_acceptance(
            records.USERSPACE_PROOF * 2,
            acceptance,
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["exact_count"], 2)
        self.assertEqual(result["minimum_candidate_boots"], 2)
        self.assertEqual(
            result["classification"],
            "USERSPACE_CALLBACK_REACHED_ONE_OR_MORE_BOOTS",
        )

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

    def test_rollback_flashed_recovery_ignores_diagnostic_files(self):
        for diagnostic in ("absent", "present", "malformed"):
            with self.subTest(diagnostic=diagnostic):
                temporary, prepared = self.prepared()
                self.addCleanup(temporary.cleanup)
                backend = FakeBackend(self.module)
                original = self.module.core.Journal.event
                interrupted = False

                def interrupt_after_rollback_flashed(
                    journal, name, details=None
                ):
                    nonlocal interrupted
                    if name == "rollback_flash_done" and not interrupted:
                        interrupted = True
                        raise KeyboardInterrupt("at durable ROLLBACK_FLASHED")
                    return original(journal, name, details)

                with mock.patch.object(
                    self.module.core.Journal,
                    "event",
                    new=interrupt_after_rollback_flashed,
                ):
                    with self.assertRaises(KeyboardInterrupt):
                        self.module.execute_prepared(
                            prepared, prepared.approval_token, backend
                        )
                journal = self.module.core.Journal.reopen(
                    prepared.run_dir / "transaction",
                    prepared.binding_sha256,
                )
                self.assertEqual(journal.state(), "ROLLBACK_FLASHED")
                if diagnostic != "absent":
                    directory = (
                        prepared.run_dir / "odin-endpoints" / "diagnostics"
                    )
                    directory.mkdir(parents=True)
                    path = (
                        directory / "odin-diagnostic-failure-000000.json"
                    )
                    if diagnostic == "present":
                        self.module.odin_core._create_sealed_receipt(
                            path,
                            {
                                "schema": self.module.odin_core.DIAGNOSTIC_SCHEMA,
                                "ordinal": 0,
                                "timestamp_utc": "2026-07-24T00:00:00.000000Z",
                                "attempted_snapshot_sequence": 0,
                                "observation_stage": (
                                    self.module.odin_core
                                    .DIAGNOSTIC_OBSERVATION_STAGE
                                ),
                                "failure_kind": "usbfs-identity-failed",
                                "inner_exception_class": "UsbfsIdentityError",
                                "removed": [],
                                "added": [],
                                "snapshot_persisted": False,
                            },
                        )
                    else:
                        path.write_bytes(b"{malformed")
                        path.chmod(0o400)
                recovery = FakeBackend(self.module)
                result = self.module.recover_prepared(prepared, recovery)
                self.assertEqual(result["current_state"], "CLOSED")
                self.assertNotIn("transfer-candidate", recovery.calls)
                self.assertNotIn("transfer-rollback", recovery.calls)

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
        for invalid in (True, float("nan"), float("inf")):
            with self.subTest(elapsed_sec=invalid):
                changed = copy.deepcopy(result)
                changed["live_state"]["final_evidence"]["observer"][
                    "reads"
                ][0]["elapsed_sec"] = invalid
                with self.assertRaises(self.module.F1LiveError):
                    self.module.validate_live_result(changed, prepared)
        raw_path = prepared.run_dir / "rollback-observer-1.bin"
        raw_path.chmod(0o600)
        raw_path.write_bytes(b"tampered")
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

    def test_result_validator_requires_exact_raw_transport_binding(self):
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        result = self.module.execute_prepared(
            prepared, prepared.approval_token, FakeBackend(self.module)
        )
        path = prepared.run_dir / "candidate-attempt-01.result.json"
        path.chmod(0o600)
        value = json.loads(path.read_text(encoding="utf-8"))
        value["transport"]["raw_capture_receipt"]["sha256"] = "0" * 64
        path.write_text(json.dumps(value), encoding="utf-8")
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
        temporary, prepared = self.prepared()
        self.addCleanup(temporary.cleanup)
        prepared.bundle.manifest["status"] = "draft-host-only"
        plan = self.module.render_plan(ROOT, prepared.bundle)
        self.assertTrue(plan["prepare_is_d0_only"])
        self.assertTrue(plan["execute_requires_fresh_exact_approval"])
        self.assertFalse(plan["recover_can_transfer_candidate"])
        self.assertEqual(plan["manifest_status"], "draft-host-only")

    def test_historical_core1_canary_is_not_reusable_by_core2(self):
        manifest = (
            ROOT
            / "workspace/public/src/device-action/manifests/"
            "s22plus_fyg8_r4w1c_process_v2_canary_1.json"
        )
        with self.assertRaisesRegex(
            self.module.core.F1V2Error, "runner version mismatch"
        ):
            self.module.core.verify_bundle(ROOT, manifest)

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
