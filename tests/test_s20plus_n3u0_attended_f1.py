import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_n3u0_attended_f1.py"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "s20plus_n3u0_attended_f1_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


class S20PlusN3U0AttendedF1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.bound_closure = cls.module.current_binding()

    def setUp(self):
        self.binding_patch = mock.patch.object(
            self.module, "current_binding", return_value=self.bound_closure
        )
        self.binding_patch.start()
        self.temporary = tempfile.TemporaryDirectory()
        self.runs_root = Path(self.temporary.name) / "runs"
        self.runs_root.mkdir(mode=0o700)

    def tearDown(self):
        self.temporary.cleanup()
        self.binding_patch.stop()

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

    def health(self, identity=None):
        selected = self.identity(boot="5") if identity is None else identity
        return {
            "identity": selected,
            "android_health_sha256": "6" * 64,
            "root_output_sha256": "7" * 64,
            "root_attempts": 1,
            "exact_target_healthy": True,
            "root_verified": True,
        }

    def prepared(self):
        return self.module.create_prepared(
            self.runs_root,
            self.identity(),
            "2" * 64,
        )

    def candidate_observed(self):
        run = self.initial_arrived()
        self.module.begin_candidate(
            run, self.module.approval_token(run), self.endpoint()
        )
        self.module.record_transfer_result(
            run, "candidate", "odin_transfer_completed", self.raw()
        )
        self.module.record_candidate_observation(
            run,
            banner_accepted=True,
            android_identity=self.identity(boot="3"),
        )
        return run

    def initial_arrived(self):
        run = self.prepared()
        self.module.begin_initial_download(run)
        self.module.record_initial_download_result(run, "dispatched", self.raw())
        self.module.record_initial_download_observation(
            run, self.endpoint(), "9" * 64
        )
        return run

    def automatic_rollback_ready(self):
        run = self.candidate_observed()
        self.module.begin_rollback_mode(run)
        self.module.record_rollback_mode_result(run, "dispatched", self.raw())
        self.module.record_rollback_mode_observation(run, self.endpoint("4"))
        self.module.begin_rollback(run)
        return run

    def test_plan_is_dormant_and_pins_reviewed_h0_model(self):
        plan = self.module.render_plan()
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertEqual(plan["status"], "H0_EXECUTION_JOURNAL_PASS_GO_NOT_ACTIVE")
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["partition_transfers"], [])
        self.assertEqual(
            plan["binding"]["model_binding_sha256"],
            "860d7970b0b841d1fccdaa27c59ec0d56060294f566c0d4844f484593f5fffbc",
        )
        self.assertEqual(plan["binding"]["target"], self.module.TARGET)

    def test_prepared_record_and_guard_are_exact_and_resumable(self):
        run = self.prepared()
        prepared = self.module.read_prepared(run)
        self.assertEqual(prepared["run_id"], run.name)
        self.module.require_guard(run, prepared)
        self.assertEqual(self.module._run_files(run), {"prepared.json"})

    def test_candidate_intent_is_one_shot_and_result_never_reenables_it(self):
        run = self.initial_arrived()
        approval = self.module.approval_token(run)
        self.module.begin_candidate(run, approval, self.endpoint())
        with self.assertRaisesRegex(self.module.N3U0F1Error, "replay forbidden"):
            self.module.begin_candidate(run, approval, self.endpoint())
        self.module.record_transfer_result(
            run,
            "candidate",
            "odin_device_session_failure_or_unknown",
            self.raw(),
        )
        with self.assertRaisesRegex(self.module.N3U0F1Error, "replay forbidden"):
            self.module.begin_candidate(run, approval, self.endpoint())

    def test_initial_download_intent_is_one_shot_across_uncertain_result(self):
        run = self.prepared()
        self.module.begin_initial_download(run)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "replay forbidden"):
            self.module.begin_initial_download(run)
        self.module.record_initial_download_result(run, "uncertain", self.raw())
        with self.assertRaisesRegex(self.module.N3U0F1Error, "replay forbidden"):
            self.module.begin_initial_download(run)

    def test_candidate_requires_fresh_exact_arrival_approval_and_endpoint(self):
        run = self.initial_arrived()
        with self.assertRaisesRegex(self.module.N3U0F1Error, "approval"):
            self.module.begin_candidate(run, "stale", self.endpoint())
        with self.assertRaisesRegex(self.module.N3U0F1Error, "endpoint differs"):
            self.module.begin_candidate(
                run, self.module.approval_token(run), self.endpoint("8")
            )

    def test_candidate_intent_only_cut_can_enter_physical_recovery(self):
        run = self.initial_arrived()
        self.module.begin_candidate(
            run, self.module.approval_token(run), self.endpoint()
        )
        intent = self.module.begin_physical_rollback(run, "3" * 64)
        self.assertIs(intent["replay_permitted"], False)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "replay forbidden"):
            self.module.begin_physical_rollback(run, "3" * 64)

    def test_automatic_and_physical_recovery_are_mutually_exclusive(self):
        run = self.candidate_observed()
        self.module.begin_rollback_mode(run)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "already owns"):
            self.module.begin_physical_rollback(run, "4" * 64)

        second = self.prepared_after_removing_guard()
        self.module.begin_initial_download(second)
        self.module.record_initial_download_observation(
            second, self.endpoint(), "9" * 64
        )
        self.module.begin_candidate(
            second, self.module.approval_token(second), self.endpoint()
        )
        self.module.begin_physical_rollback(second, "4" * 64)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "already owns"):
            self.module.begin_rollback_mode(second)

    def test_rollback_intent_is_one_shot(self):
        run = self.automatic_rollback_ready()
        with self.assertRaisesRegex(self.module.N3U0F1Error, "replay forbidden"):
            self.module.begin_rollback(run)

    def test_uncertain_rollback_never_becomes_terminal(self):
        run = self.automatic_rollback_ready()
        self.module.record_transfer_result(
            run,
            "rollback",
            "odin_device_session_failure_or_unknown",
            self.raw(),
        )
        with self.assertRaisesRegex(self.module.N3U0F1Error, "completed"):
            self.module.record_final_health(run, self.health())
        with self.assertRaisesRegex(self.module.N3U0F1Error, "final health"):
            self.module.finalize(run)
        self.assertTrue((self.runs_root / "active.json").exists())

    def test_complete_automatic_path_releases_guard_after_terminal(self):
        run = self.automatic_rollback_ready()
        self.module.record_transfer_result(
            run, "rollback", "odin_transfer_completed", self.raw()
        )
        self.module.record_final_health(run, self.health())
        terminal = self.module.finalize(run)
        self.assertEqual(
            terminal["verdict"], "PASS_S20PLUS_G986N_N3U0_RESIDENT_RESTORED"
        )
        self.assertFalse((self.runs_root / "active.json").exists())
        self.assertEqual(self.module.finalize(run), terminal)

    def test_complete_physical_path_releases_guard_after_terminal(self):
        run = self.initial_arrived()
        self.module.begin_candidate(
            run, self.module.approval_token(run), self.endpoint()
        )
        self.module.begin_physical_rollback(run, "3" * 64)
        self.module.record_physical_arrival(run, self.endpoint("4"), "5" * 64)
        self.module.begin_rollback(run)
        self.module.record_transfer_result(
            run, "rollback", "odin_transfer_completed", self.raw()
        )
        self.module.record_final_health(
            run, self.health(self.identity(boot="6"))
        )
        self.assertEqual(
            self.module.finalize(run)["rollback_attempts"], 1
        )

    def test_final_health_rejects_foreign_or_reused_boot(self):
        run = self.automatic_rollback_ready()
        self.module.record_transfer_result(
            run, "rollback", "odin_transfer_completed", self.raw()
        )
        for identity in (
            self.identity(boot="1"),
            self.identity(boot="3"),
            self.identity(boot="5", serial="9"),
            self.identity(boot="5", topology="9"),
        ):
            with self.assertRaisesRegex(self.module.N3U0F1Error, "continuity"):
                self.module.record_final_health(run, self.health(identity))
        forged = self.health()
        forged["root_attempts"] = True
        with self.assertRaisesRegex(self.module.N3U0F1Error, "proof"):
            self.module.record_final_health(run, forged)

    def test_strict_json_rejects_duplicate_nonfinite_bool_and_indirect_nodes(self):
        run = self.prepared()
        prepared = run / "prepared.json"
        prepared.chmod(0o600)
        prepared.write_text('{"schema":"x","schema":"y"}\n', encoding="utf-8")
        prepared.chmod(0o400)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "malformed"):
            self.module.read_prepared(run)

        with tempfile.TemporaryDirectory() as other_temporary:
            path = Path(other_temporary) / "nan.json"
            path.write_text('{"value":Infinity}\n', encoding="utf-8")
            path.chmod(0o400)
            with self.assertRaisesRegex(self.module.N3U0F1Error, "malformed"):
                self.module.read_exact_json(path, "nonfinite")

        second = self.prepared_after_removing_guard()
        value = self.module.read_exact_json(second / "prepared.json", "prepared")
        value["candidate_attempts"] = True
        (second / "prepared.json").chmod(0o600)
        (second / "prepared.json").write_bytes(self.module.canonical_bytes(value))
        (second / "prepared.json").chmod(0o400)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "binding"):
            self.module.read_prepared(second)

    def prepared_after_removing_guard(self):
        guard = self.runs_root / "active.json"
        if guard.exists():
            guard.unlink()
        return self.prepared()

    def remove_guard(self):
        (self.runs_root / "active.json").unlink()

    def make_guard_foreign(self):
        guard = self.runs_root / "active.json"
        value = self.module.read_exact_json(guard, "guard")
        value["run_id"] = "f" * 32
        guard.chmod(0o600)
        guard.write_bytes(self.module.canonical_bytes(value))
        guard.chmod(0o400)

    def test_guard_written_prepared_missing_cut_resumes_without_new_run(self):
        run = self.prepared()
        prepared = self.module.read_prepared(run)
        (run / "prepared.json").unlink()
        resumed = self.module.resume_guard_prepared(self.runs_root, run.name)
        self.assertEqual(resumed, run)
        self.module.require_guard(run, prepared)
        self.assertEqual(self.module._run_files(run), {"prepared.json"})

    def test_old_prepared_orphan_cannot_reactivate_after_new_terminal(self):
        old = self.prepared()
        old_prepared = self.module.read_prepared(old)
        self.remove_guard()

        current = self.automatic_rollback_ready()
        self.module.record_transfer_result(
            current, "rollback", "odin_transfer_completed", self.raw()
        )
        self.module.record_final_health(current, self.health())
        self.module.finalize(current)

        with self.assertRaisesRegex(self.module.N3U0F1Error, "allocation guard"):
            self.module.resume_guard_prepared(self.runs_root, old.name)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "not empty"):
            self.module.acquire_guard(self.runs_root, old_prepared)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "guard"):
            self.module.begin_initial_download(old)

    def test_missing_guard_blocks_each_effect_phase(self):
        run = self.prepared()
        self.remove_guard()
        with self.assertRaisesRegex(self.module.N3U0F1Error, "guard"):
            self.module.begin_initial_download(run)

        self.tearDown()
        self.setUp()
        run = self.initial_arrived()
        approval = self.module.approval_token(run)
        self.remove_guard()
        with self.assertRaisesRegex(self.module.N3U0F1Error, "guard"):
            self.module.begin_candidate(run, approval, self.endpoint())

        self.tearDown()
        self.setUp()
        run = self.candidate_observed()
        self.remove_guard()
        with self.assertRaisesRegex(self.module.N3U0F1Error, "guard"):
            self.module.begin_rollback_mode(run)

        self.tearDown()
        self.setUp()
        run = self.initial_arrived()
        self.module.begin_candidate(
            run, self.module.approval_token(run), self.endpoint()
        )
        self.remove_guard()
        with self.assertRaisesRegex(self.module.N3U0F1Error, "guard"):
            self.module.begin_physical_rollback(run, "3" * 64)

        self.tearDown()
        self.setUp()
        run = self.candidate_observed()
        self.module.begin_rollback_mode(run)
        self.module.record_rollback_mode_observation(run, self.endpoint("4"))
        self.remove_guard()
        with self.assertRaisesRegex(self.module.N3U0F1Error, "guard"):
            self.module.begin_rollback(run)

        self.tearDown()
        self.setUp()
        run = self.automatic_rollback_ready()
        self.module.record_transfer_result(
            run, "rollback", "odin_transfer_completed", self.raw()
        )
        self.remove_guard()
        with self.assertRaisesRegex(self.module.N3U0F1Error, "guard"):
            self.module.record_final_health(run, self.health())

    def test_foreign_guard_blocks_initial_and_candidate_intents(self):
        run = self.prepared()
        self.make_guard_foreign()
        with self.assertRaisesRegex(self.module.N3U0F1Error, "guard"):
            self.module.begin_initial_download(run)

        self.tearDown()
        self.setUp()
        run = self.initial_arrived()
        approval = self.module.approval_token(run)
        self.make_guard_foreign()
        with self.assertRaisesRegex(self.module.N3U0F1Error, "guard"):
            self.module.begin_candidate(run, approval, self.endpoint())

    def test_runner_normalized_identity_is_bound_and_drift_rejects(self):
        receipt = self.module.self_receipt()
        self.assertEqual(
            receipt["normalized_sha256"],
            self.module.EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256,
        )
        self.assertEqual(
            self.bound_closure["runner"]["normalized_sha256"],
            receipt["normalized_sha256"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            drift = Path(temporary) / SCRIPT.name
            drift.write_bytes(SCRIPT.read_bytes() + b"\n")
            with mock.patch.object(self.module, "__file__", str(drift)):
                with self.assertRaisesRegex(
                    self.module.N3U0F1Error, "normalized identity"
                ):
                    self.module.self_receipt()

    def test_unknown_symlink_and_hardlink_nodes_fail_closed(self):
        run = self.prepared()
        unknown = run / "unknown.json"
        unknown.write_text("{}\n", encoding="utf-8")
        unknown.chmod(0o400)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "unknown"):
            self.module.validate_legal_prefix(run)
        unknown.unlink()
        (run / "candidate-result.json").symlink_to(run / "prepared.json")
        with self.assertRaisesRegex(self.module.N3U0F1Error, "indirect"):
            self.module.validate_legal_prefix(run)
        (run / "candidate-result.json").unlink()
        os.link(run / "prepared.json", run / "candidate-result.json")
        with self.assertRaisesRegex(self.module.N3U0F1Error, "hardlinked"):
            self.module.validate_legal_prefix(run)

    def test_prefix_graph_rejects_missing_predecessor_and_branch_conflict(self):
        run = self.prepared()
        prepared = self.module.read_prepared(run)
        bogus = {
            **self.module._base(
                "s20plus_g986n_n3u0_candidate_result_v1",
                prepared["run_id"],
                prepared["binding_sha256"],
            ),
            "kind": "candidate",
        }
        self.module.durable_create(run / "candidate-result.json", bogus)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "predecessor"):
            self.module.validate_legal_prefix(run)

    def test_foreign_guard_never_releases(self):
        run = self.prepared()
        guard = self.runs_root / "active.json"
        value = self.module.read_exact_json(guard, "guard")
        guard.chmod(0o600)
        value["run_id"] = "f" * 32
        guard.write_bytes(self.module.canonical_bytes(value))
        guard.chmod(0o400)
        with self.assertRaisesRegex(self.module.N3U0F1Error, "foreign"):
            self.module.release_guard(
                run,
                self.module.read_exact_json(run / "prepared.json", "prepared"),
            )
        self.assertTrue(guard.exists())

    def test_atomic_no_clobber_publication(self):
        path = self.runs_root / "receipt.json"
        self.module.durable_create(path, {"value": 1})
        with self.assertRaises(FileExistsError):
            self.module.durable_create(path, {"value": 2})
        self.assertEqual(self.module.read_exact_json(path, "receipt"), {"value": 1})

    def test_cli_exposes_no_live_action(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--render-plan"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
            timeout=10,
        )
        plan = json.loads(completed.stdout)
        self.assertFalse(plan["active"])
        self.assertEqual(plan["cli"], ["--render-plan"])
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "--prepare",
            "--execute",
            "--approval",
            "F1_ACTIVE = True",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
