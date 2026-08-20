import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_n3u0_attended_f1_integration_h0.py"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "s20plus_n3u0_attended_f1_integration_h0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


class FakeBackend:
    def __init__(self, module, runs_root):
        self.module = module
        self.journal = module.load_journal()
        self.runs_root = runs_root
        self.calls = []
        self.run = None
        self.transfer_classification = "odin_transfer_completed"
        self.transfer_endpoints = []
        self.reboot_outcome = {"initial": "dispatched", "rollback": "dispatched"}
        self.candidate_android = self.identity("3")
        self.endpoint_value = self.endpoint()

    @staticmethod
    def identity(boot="1", serial="a", topology="b"):
        return {
            "serial_sha256": serial * 64,
            "topology_sha256": topology * 64,
            "boot_id_sha256": boot * 64,
        }

    @staticmethod
    def endpoint(seed="c"):
        return {
            "path_sha256": seed * 64,
            "identity_sha256": "d" * 64,
            "topology_sha256": "e" * 64,
            "profile_sha256": "f" * 64,
        }

    @staticmethod
    def raw():
        return {
            "stdout_sha256": "0" * 64,
            "stderr_sha256": "1" * 64,
            "stdout_size": 0,
            "stderr_size": 0,
        }

    def count(self, name):
        return sum(call == name for call in self.calls)

    def preflight(self):
        self.calls.append("preflight")
        return {
            "identity": self.identity(),
            "empty_download_baseline_sha256": "2" * 64,
        }

    def download_baseline(self, phase):
        self.calls.append(f"{phase}-baseline")
        return "2" * 64

    def reboot_download(self, phase, source_identity):
        self.calls.append(f"{phase}-reboot")
        intent = (
            "initial-download-intent.json"
            if phase == "initial"
            else "rollback-mode-intent.json"
        )
        if self.run is None or not (self.run / intent).exists():
            raise AssertionError("effect happened before intent")
        intent_value = self.journal.read_exact_json(self.run / intent, intent)
        if intent_value["source_identity"] != source_identity:
            raise AssertionError("reboot source differs from intent")
        return {
            "phase": phase,
            "outcome": self.reboot_outcome[phase],
            "raw_receipt": self.raw(),
        }

    def observe_download(self, phase):
        self.calls.append(f"{phase}-download-observe")
        return {
            "phase": phase,
            "endpoint": self.endpoint_value,
            "arrival_listing_sha256": "9" * 64,
        }

    def transfer_boot(self, kind, endpoint):
        self.calls.append(f"{kind}-transfer")
        self.transfer_endpoints.append((kind, endpoint))
        if self.run is None or not (self.run / f"{kind}-intent.json").exists():
            raise AssertionError("transfer happened before intent")
        intent = self.journal.read_exact_json(
            self.run / f"{kind}-intent.json", f"{kind} intent"
        )
        if intent["endpoint"] != endpoint:
            raise AssertionError("transfer endpoint differs from intent")
        return {
            "kind": kind,
            "classification": self.transfer_classification,
            "raw_receipt": self.raw(),
        }

    def observe_candidate(self):
        self.calls.append("candidate-observe")
        return {
            "banner_accepted": True,
            "android_identity": self.candidate_android,
        }

    def physical_download_entry(self):
        self.calls.append("physical-entry")
        if self.run is None or not (self.run / "physical-rollback-intent.json").exists():
            raise AssertionError("physical effect happened before intent")

    def final_resident_health(self):
        self.calls.append("final-health")
        return {
            "identity": self.identity("5"),
            "android_health_sha256": "6" * 64,
            "root_output_sha256": "7" * 64,
            "root_attempts": 1,
            "exact_target_healthy": True,
            "root_verified": True,
        }


class S20PlusN3U0AttendedF1IntegrationH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.journal = cls.module.load_journal()
        cls.journal_binding = cls.journal.current_binding()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.runs_root = Path(self.temporary.name) / "runs"
        self.runs_root.mkdir(mode=0o700)
        self.journal_patch = mock.patch.object(
            self.module, "load_journal", return_value=self.journal
        )
        self.journal_patch.start()
        self.binding_patch = mock.patch.object(
            self.journal, "current_binding", return_value=self.journal_binding
        )
        self.binding_patch.start()
        self.backend = FakeBackend(self.module, self.runs_root)
        self.active = mock.patch.object(self.module, "INTEGRATION_ACTIVE", True)

    def tearDown(self):
        self.binding_patch.stop()
        self.journal_patch.stop()
        self.temporary.cleanup()

    def prepare_active(self):
        with self.active:
            run = self.module.prepare(self.runs_root, self.backend)
        self.backend.run = run
        return run

    def initial_active(self):
        run = self.prepare_active()
        with self.active:
            approval = self.module.enter_initial_download(run, self.backend)
        return run, approval

    def candidate_active(self):
        run, approval = self.initial_active()
        with self.active:
            self.module.transfer_candidate(run, approval, self.backend)
        return run

    def test_plan_is_dormant_and_binds_exact_consumers(self):
        plan = self.module.render_plan()
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertFalse(plan["backend_exposed"])
        self.assertEqual(
            plan["status"], "H0_CONSUMER_INTEGRATION_PASS_GO_NOT_ACTIVE"
        )
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["partition_transfers"], [])
        self.assertEqual(
            plan["binding"]["journal_binding_sha256"],
            self.module.JOURNAL_BINDING_SHA256,
        )

    def test_dormant_gate_precedes_every_backend_read(self):
        with self.assertRaisesRegex(self.module.IntegrationError, "not active"):
            self.module.prepare(self.runs_root, self.backend)
        self.assertEqual(self.backend.calls, [])

    def test_existing_guard_blocks_new_prepare_before_backend_read(self):
        self.prepare_active()
        before = list(self.backend.calls)
        with self.active, self.assertRaisesRegex(self.module.IntegrationError, "guard"):
            self.module.prepare(self.runs_root, self.backend)
        self.assertEqual(self.backend.calls, before)

    def test_initial_intent_precedes_one_reboot_and_retry_is_blocked(self):
        run, _approval = self.initial_active()
        self.assertEqual(self.backend.count("initial-reboot"), 1)
        with self.active, self.assertRaisesRegex(Exception, "replay forbidden"):
            self.module.enter_initial_download(run, self.backend)
        self.assertEqual(self.backend.count("initial-reboot"), 1)

    def test_candidate_intent_precedes_one_transfer_and_retry_is_blocked(self):
        run, approval = self.initial_active()
        with self.active:
            self.module.transfer_candidate(run, approval, self.backend)
        self.assertEqual(self.backend.count("candidate-transfer"), 1)
        with self.active, self.assertRaisesRegex(Exception, "replay forbidden"):
            self.module.transfer_candidate(run, approval, self.backend)
        self.assertEqual(self.backend.count("candidate-transfer"), 1)

    def test_foreign_download_endpoint_blocks_candidate_transfer(self):
        run, approval = self.initial_active()
        self.backend.endpoint_value = self.backend.endpoint("8")
        with self.active, self.assertRaisesRegex(Exception, "endpoint differs"):
            self.module.transfer_candidate(run, approval, self.backend)
        self.assertEqual(self.backend.count("candidate-transfer"), 0)

    def test_candidate_effect_exception_is_consumed_and_physical_only(self):
        run, approval = self.initial_active()

        def fail_after_intent(kind, endpoint):
            self.backend.calls.append(f"{kind}-transfer")
            self.assertTrue((run / "candidate-intent.json").exists())
            raise OSError("injected transfer cut")

        self.backend.transfer_boot = fail_after_intent
        with self.active, self.assertRaises(OSError):
            self.module.transfer_candidate(run, approval, self.backend)
        with self.active, self.assertRaisesRegex(Exception, "replay forbidden"):
            self.module.transfer_candidate(run, approval, self.backend)
        self.assertEqual(self.backend.count("candidate-transfer"), 1)

    def test_complete_automatic_path_has_exact_effect_counts(self):
        run = self.candidate_active()
        with self.active:
            rollback = self.module.automatic_rollback(run, self.backend)
            terminal = self.module.finalize_resident(run, self.backend)
        self.assertEqual(rollback["classification"], "odin_transfer_completed")
        self.assertEqual(
            terminal["verdict"], "PASS_S20PLUS_G986N_N3U0_RESIDENT_RESTORED"
        )
        self.assertEqual(self.backend.count("initial-reboot"), 1)
        self.assertEqual(self.backend.count("candidate-transfer"), 1)
        self.assertEqual(self.backend.count("rollback-reboot"), 1)
        self.assertEqual(self.backend.count("rollback-transfer"), 1)
        self.assertEqual(self.backend.count("physical-entry"), 0)
        self.assertEqual(self.backend.count("final-health"), 1)
        rollback_intent = self.journal.read_exact_json(
            run / "rollback-intent.json", "rollback intent"
        )
        self.assertEqual(
            self.backend.transfer_endpoints[-1],
            ("rollback", rollback_intent["endpoint"]),
        )

    def test_private_rollback_helper_is_dormant_before_any_backend_call(self):
        run = self.candidate_active()
        before = list(self.backend.calls)
        with self.assertRaisesRegex(self.module.IntegrationError, "not active"):
            self.module._transfer_rollback(run, self.backend)
        self.assertEqual(self.backend.calls, before)

    def test_complete_physical_path_has_exact_effect_counts(self):
        run, approval = self.initial_active()
        self.backend.candidate_android = None
        with self.active:
            self.module.transfer_candidate(run, approval, self.backend)
            rollback = self.module.physical_rollback(run, self.backend)
        before = list(self.backend.calls)
        with self.active, self.assertRaisesRegex(Exception, "replay forbidden"):
            self.module.physical_rollback(run, self.backend)
        self.assertEqual(self.backend.calls, before)
        with self.active:
            terminal = self.module.finalize_resident(run, self.backend)
        self.assertEqual(rollback["classification"], "odin_transfer_completed")
        self.assertEqual(
            terminal["verdict"], "PASS_S20PLUS_G986N_N3U0_RESIDENT_RESTORED"
        )
        self.assertEqual(self.backend.count("rollback-reboot"), 0)
        self.assertEqual(self.backend.count("physical-baseline"), 1)
        self.assertEqual(self.backend.count("physical-entry"), 1)
        self.assertEqual(self.backend.count("rollback-transfer"), 1)

    def test_uncertain_rollback_never_replays_or_reaches_health(self):
        run = self.candidate_active()
        self.backend.transfer_classification = "odin_device_session_failure_or_unknown"
        with self.active:
            self.module.automatic_rollback(run, self.backend)
        with self.active, self.assertRaisesRegex(Exception, "replay forbidden"):
            self.module.automatic_rollback(run, self.backend)
        with self.active, self.assertRaisesRegex(Exception, "completed resident rollback"):
            self.module.finalize_resident(run, self.backend)
        self.assertEqual(self.backend.count("rollback-transfer"), 1)
        self.assertEqual(self.backend.count("final-health"), 0)
        self.assertTrue((self.runs_root / "active.json").exists())

    def test_missing_guard_blocks_effect_before_backend_call(self):
        run, approval = self.initial_active()
        (self.runs_root / "active.json").unlink()
        before = list(self.backend.calls)
        with self.active, self.assertRaisesRegex(Exception, "guard"):
            self.module.transfer_candidate(run, approval, self.backend)
        self.assertEqual(self.backend.calls, before)
        self.assertEqual(self.backend.count("candidate-transfer"), 0)

    def test_terminal_resume_uses_zero_backend_calls(self):
        run = self.candidate_active()
        with self.active:
            self.module.automatic_rollback(run, self.backend)
            terminal = self.module.finalize_resident(run, self.backend)
        before = list(self.backend.calls)
        with self.active:
            repeated = self.module.finalize_resident(run, self.backend)
        self.assertEqual(repeated, terminal)
        self.assertEqual(self.backend.calls, before)

    def test_final_health_cut_and_missing_guard_use_zero_backend_calls(self):
        run = self.candidate_active()
        with self.active:
            self.module.automatic_rollback(run, self.backend)
        health = self.backend.final_resident_health()
        self.journal.record_final_health(run, health)
        before = list(self.backend.calls)
        with self.active:
            terminal = self.module.finalize_resident(run, self.backend)
        self.assertEqual(
            terminal["verdict"], "PASS_S20PLUS_G986N_N3U0_RESIDENT_RESTORED"
        )
        self.assertEqual(self.backend.calls, before)

        self.tearDown()
        self.setUp()
        run = self.candidate_active()
        with self.active:
            self.module.automatic_rollback(run, self.backend)
        (self.runs_root / "active.json").unlink()
        before = list(self.backend.calls)
        with self.active, self.assertRaisesRegex(Exception, "guard"):
            self.module.finalize_resident(run, self.backend)
        self.assertEqual(self.backend.calls, before)

    def test_consumer_source_drift_rejects_binding(self):
        changed = dict(self.module.CLOSURE["n3u0_usb_observer"])
        changed["sha256"] = "0" * 64
        with mock.patch.dict(
            self.module.CLOSURE, {"n3u0_usb_observer": changed}, clear=False
        ):
            with self.assertRaisesRegex(self.module.IntegrationError, "hash differs"):
                self.module.source_receipts()

    def test_typed_backend_receipts_fail_closed_after_consumed_intent(self):
        run = self.prepare_active()
        self.backend.reboot_outcome["initial"] = True
        with self.active, self.assertRaisesRegex(self.module.IntegrationError, "malformed"):
            self.module.enter_initial_download(run, self.backend)
        self.assertTrue((run / "initial-download-intent.json").exists())
        self.assertEqual(self.backend.count("initial-reboot"), 1)
        with self.active, self.assertRaisesRegex(Exception, "replay forbidden"):
            self.module.enter_initial_download(run, self.backend)
        self.assertEqual(self.backend.count("initial-reboot"), 1)


if __name__ == "__main__":
    unittest.main()
