import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_n3u0_attended_f1_execution_h0.py"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "s20plus_n3u0_attended_f1_execution_h0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


class FakeBackend:
    def __init__(self):
        self.calls = []
        self.operation = None
        self.captures = []
        self.full_receipt = None
        self.fail_operation = None
        self.capture_returncode = 0
        self.semantic_stdout = b"OK"

    def begin_operation_capture(self, operation):
        self.calls.append(("begin", operation))
        if self.operation is not None:
            raise AssertionError("nested capture")
        self.operation = operation
        self.full_receipt = None

    def consume_operation_capture(self, operation):
        self.calls.append(("consume", operation))
        if operation != self.operation:
            raise AssertionError("capture operation drift")
        self.operation = None
        result = {
            "commands": list(self.captures),
            "full_receipt": self.full_receipt,
        }
        self.captures.clear()
        self.full_receipt = None
        return result

    def command_return(self, argv=None, stdout=b"OK", stderr=b"", returncode=0):
        self.captures.append(
            {
                "argv": list(argv or ["fixed-command"]),
                "timeout_seconds": 20,
                "output_limit": 65536,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        )

    @staticmethod
    def raw(stdout=b"OK", stderr=b""):
        return {
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stdout_size": len(stdout),
            "stderr_size": len(stderr),
        }

    def reboot_download(self, phase, source_identity):
        operation = f"{phase}-download-reboot" if phase == "initial" else "rollback-download-reboot"
        if self.fail_operation == operation:
            self.command_return(returncode=1, stdout=b"", stderr=b"failed")
            raise OSError("injected command boundary")
        self.command_return(
            ["/fixed/adb", "-s", "PRIVATE_SERIAL", "reboot", "download"],
            returncode=self.capture_returncode,
        )
        value = {
            "phase": phase,
            "outcome": "dispatched",
            "raw_receipt": self.raw(self.semantic_stdout),
        }
        self.full_receipt = {
            "operation": f"{phase}-reboot-download",
            "source_identity": source_identity,
            **value,
        }
        return value

    def transfer_boot(self, kind, endpoint):
        operation = f"{kind}-transfer"
        if self.fail_operation == operation:
            self.command_return(returncode=1, stdout=b"", stderr=b"failed")
            raise OSError("injected transfer boundary")
        self.command_return(
            ["odin4", "--reboot", "-a", "AP.tar.md5"],
            returncode=self.capture_returncode,
        )
        value = {
            "kind": kind,
            "classification": "odin_transfer_completed",
            "raw_receipt": self.raw(self.semantic_stdout),
        }
        self.full_receipt = {
            "operation": f"{kind}-boot-transfer",
            "endpoint": endpoint,
            **value,
        }
        return value

    def observe_download(self, phase):
        self.command_return(["odin4", "-l"], stdout=b"USBFS\n")
        value = {
            "phase": phase,
            "endpoint": {
                "path_sha256": "c" * 64,
                "identity_sha256": "d" * 64,
                "topology_sha256": "e" * 64,
                "profile_sha256": "f" * 64,
            },
            "arrival_listing_sha256": "9" * 64,
        }
        self.full_receipt = dict(value)
        return value

    def observe_candidate(self):
        value = {
            "banner_accepted": True,
            "android_identity": {
                "serial_sha256": "a" * 64,
                "topology_sha256": "b" * 64,
                "boot_id_sha256": "3" * 64,
            },
        }
        self.full_receipt = {
            "usb_receipt": {"accepted": True, "exact": True},
            "android_identity": value["android_identity"],
            "android_health_sha256": "8" * 64,
        }
        return value

    def final_resident_health(self):
        value = {
            "identity": {
                "serial_sha256": "a" * 64,
                "topology_sha256": "b" * 64,
                "boot_id_sha256": "5" * 64,
            },
            "android_health_sha256": "6" * 64,
            "root_output_sha256": "7" * 64,
            "root_attempts": 1,
            "exact_target_healthy": True,
            "root_verified": True,
        }
        self.command_return(["/fixed/adb", "health"], stdout=b"HEALTHY")
        self.full_receipt = {
            "identity": value["identity"],
            "android_health_sha256": value["android_health_sha256"],
            "root": {
                "output_sha256": value["root_output_sha256"],
                "attempts": value["root_attempts"],
                "root_verified": True,
            },
        }
        return value


class S20PlusN3U0AttendedF1ExecutionH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.sources = cls.module.load_sources()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.runs = base / "runs"
        self.evidence_root = base / "evidence"
        self.runs.mkdir(mode=0o700)
        self.evidence_root.mkdir(mode=0o700)
        self.journal = self.sources["journal"]
        self.evidence = self.sources["evidence"]
        self.backend = FakeBackend()
        self.stack = ExitStack()
        self.stack.enter_context(
            mock.patch.object(self.module, "load_sources", return_value=self.sources)
        )
        self.stack.enter_context(mock.patch.object(self.module, "EXECUTION_ACTIVE", True))
        self.stack.enter_context(mock.patch.object(self.evidence, "EVIDENCE_ACTIVE", True))
        self.stack.enter_context(
            mock.patch.object(self.evidence, "EVIDENCE_ROOT", self.evidence_root)
        )
        self.stack.enter_context(
            mock.patch.object(self.evidence, "JOURNAL_RUNS_ROOT", self.runs)
        )
        self.stack.enter_context(
            mock.patch.object(
                self.sources["backend"], "FixedBackend", return_value=self.backend
            )
        )
        self.session = self.module.ExecutionSession()
        self.run = self.journal.create_prepared(
            self.runs,
            {
                "serial_sha256": "a" * 64,
                "topology_sha256": "b" * 64,
                "boot_id_sha256": "1" * 64,
            },
            "2" * 64,
        )

    def tearDown(self):
        self.stack.close()
        self.temporary.cleanup()

    @staticmethod
    def raw(stdout=b"OK", stderr=b""):
        return {
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stdout_size": len(stdout),
            "stderr_size": len(stderr),
        }

    def publish_initial_without_result(self):
        with mock.patch.object(
            self.module,
            "derive_initial_download_result",
            side_effect=RuntimeError("injected result cut"),
        ):
            with self.assertRaisesRegex(RuntimeError, "result cut"):
                self.session.enter_initial_download(self.run)

    def test_plan_is_dormant_and_render_only(self):
        with mock.patch.object(self.module, "EXECUTION_ACTIVE", False):
            plan = self.module.render_plan()
        self.assertFalse(plan["active"])
        self.assertEqual(
            plan["status"],
            "H0_EVIDENCE_EXECUTION_INTEGRATION_PASS_GO_NOT_ACTIVE",
        )
        self.assertFalse(plan["live_authority"])
        self.assertFalse(plan["integrated_live_consumer"])
        self.assertFalse(plan["physical_entry_bridge"])
        self.assertTrue(plan["result_derivation_without_replay"])
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["partition_transfers"], [])

    def test_dormant_gate_precedes_backend_capture(self):
        with mock.patch.object(self.module, "EXECUTION_ACTIVE", False):
            with self.assertRaisesRegex(self.module.ExecutionError, "not active"):
                self.session.enter_initial_download(self.run)
        self.assertEqual(self.backend.calls, [])
        self.assertFalse((self.run / "initial-download-intent.json").exists())

    def test_complete_return_is_durable_before_journal_result_derivation(self):
        self.publish_initial_without_result()
        self.assertFalse((self.run / "initial-download-result.json").exists())
        derived = self.module.derive_initial_download_result(self.run)
        self.assertEqual(derived["state"], "complete")
        self.assertEqual(
            derived["full_receipt"]["operation"], "initial-reboot-download"
        )
        result = self.journal.read_exact_json(
            self.run / "initial-download-result.json", "initial result"
        )
        self.assertEqual(result["outcome"], "dispatched")
        self.assertFalse(result["replay_permitted"])
        names = {path.name for path in (self.evidence_root / self.run.name).iterdir()}
        self.assertEqual(
            names,
            {
                "initial-download-reboot-01.stdout",
                "initial-download-reboot-01.stderr",
                "initial-download-reboot-01.result.json",
                "initial-download-reboot-90.stdout",
                "initial-download-reboot-90.stderr",
                "initial-download-reboot-90.result.json",
            },
        )

    def test_complete_evidence_resumes_result_with_zero_backend_calls(self):
        self.publish_initial_without_result()
        before = list(self.backend.calls)
        self.module.derive_initial_download_result(self.run)
        self.assertEqual(self.backend.calls, before)

    def test_partial_publication_is_uncertain_and_never_calls_backend_on_resume(self):
        original = self.evidence._durable_blob
        calls = 0

        def fail_second(path, payload):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected publication cut")
            return original(path, payload)

        with mock.patch.object(self.evidence, "_durable_blob", side_effect=fail_second):
            with self.assertRaises(OSError):
                self.session.enter_initial_download(self.run)
        before = list(self.backend.calls)
        derived = self.module.derive_backend_return(
            self.run, "initial-download-reboot"
        )
        self.assertEqual(derived["state"], "uncertain-consumed")
        self.assertFalse(derived["replay_permitted"])
        self.assertEqual(self.backend.calls, before)
        self.assertFalse((self.run / "initial-download-result.json").exists())

    def test_producer_exception_is_durably_consumed_without_retry(self):
        self.backend.fail_operation = "initial-download-reboot"
        with self.assertRaises(OSError):
            self.session.enter_initial_download(self.run)
        before = list(self.backend.calls)
        derived = self.module.derive_backend_return(
            self.run, "initial-download-reboot"
        )
        self.assertEqual(derived["state"], "producer-error-consumed")
        self.assertEqual(derived["error_class"], "OSError")
        self.assertEqual(self.backend.calls, before)

    def test_transfer_result_is_derived_only_from_complete_evidence(self):
        approval = self.session.enter_initial_download(self.run)
        with mock.patch.object(
            self.module,
            "derive_transfer_result",
            side_effect=RuntimeError("injected candidate result cut"),
        ):
            with self.assertRaisesRegex(RuntimeError, "candidate result cut"):
                self.session.transfer_candidate(self.run, approval)
        before = list(self.backend.calls)
        derived = self.module.derive_transfer_result(self.run, "candidate")
        self.assertEqual(derived["state"], "complete")
        self.assertEqual(self.backend.calls, before)
        result = self.journal.read_exact_json(
            self.run / "candidate-result.json", "candidate result"
        )
        self.assertEqual(result["classification"], "odin_transfer_completed")

    def test_complete_automatic_flow_has_one_effect_per_intent_and_terminal(self):
        approval = self.session.enter_initial_download(self.run)
        self.session.transfer_candidate(self.run, approval)
        rollback = self.session.automatic_rollback(self.run)
        terminal = self.session.finalize_resident(self.run)
        self.assertEqual(rollback["classification"], "odin_transfer_completed")
        self.assertEqual(
            terminal["verdict"], "PASS_S20PLUS_G986N_N3U0_RESIDENT_RESTORED"
        )
        for operation in (
            "initial-download-reboot",
            "initial-download-observation",
            "candidate-transfer",
            "candidate-observation",
            "rollback-download-reboot",
            "rollback-download-observation",
            "rollback-transfer",
            "final-resident-health",
        ):
            self.assertEqual(self.backend.calls.count(("begin", operation)), 1)
            self.assertEqual(self.backend.calls.count(("consume", operation)), 1)
        before = list(self.backend.calls)
        with self.assertRaisesRegex(Exception, "guard|replay forbidden"):
            self.session.automatic_rollback(self.run)
        self.assertEqual(self.backend.calls, before)

    def test_bool_returncode_and_typed_semantic_reject(self):
        self.backend.capture_returncode = True
        with self.assertRaisesRegex(Exception, "malformed"):
            self.session.enter_initial_download(self.run)

    def test_semantic_raw_must_equal_actual_captured_command(self):
        self.backend.semantic_stdout = b"FORGED"
        with self.assertRaisesRegex(
            self.module.ExecutionError, "differs from captured command"
        ):
            self.session.enter_initial_download(self.run)

    def test_existing_journal_result_must_equal_durable_backend_evidence(self):
        self.session.enter_initial_download(self.run)
        path = self.run / "initial-download-result.json"
        value = json.loads(path.read_text())
        value["raw_receipt"]["stdout_sha256"] = "f" * 64
        path.unlink()
        path.write_bytes(self.journal.canonical_bytes(value))
        path.chmod(0o400)
        with self.assertRaisesRegex(
            self.module.ExecutionError, "differs from durable backend evidence"
        ):
            self.module.derive_initial_download_result(self.run)

    def test_unknown_operation_rejects_before_backend_capture(self):
        before = list(self.backend.calls)
        with self.assertRaisesRegex(self.module.ExecutionError, "not created"):
            self.session._capture_fresh(self.run, "initial-download-reboot")
        self.assertEqual(self.backend.calls, before)
        self.assertFalse(hasattr(self.module, "publish_backend_return"))
        self.assertFalse(hasattr(self.module, "capture_operation"))
        self.assertFalse(hasattr(self.module, "_publish_captures"))
        self.assertFalse(hasattr(self.module, "_fixed_backend_call"))

    def test_intent_only_restart_cannot_reauthorize_or_replay_effect(self):
        self.journal.begin_initial_download(self.run)
        restarted = self.module.ExecutionSession()
        before = list(self.backend.calls)
        with self.assertRaisesRegex(Exception, "replay forbidden"):
            restarted.enter_initial_download(self.run)
        with self.assertRaisesRegex(self.module.ExecutionError, "not created"):
            restarted._capture_fresh(self.run, "initial-download-reboot")
        self.assertEqual(self.backend.calls, before)

    def test_source_drift_prevents_backend_call_and_evidence_write(self):
        changed = dict(self.module.SOURCES["backend"])
        changed["sha256"] = "0" * 64
        self.stack.close()
        self.stack = ExitStack()
        self.stack.enter_context(mock.patch.object(self.module, "EXECUTION_ACTIVE", True))
        with mock.patch.dict(self.module.SOURCES, {"backend": changed}, clear=False):
            with self.assertRaisesRegex(self.module.ExecutionError, "hash differs"):
                self.module.ExecutionSession()
        self.assertEqual(self.backend.calls, [])
        self.assertEqual(list(self.evidence_root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
