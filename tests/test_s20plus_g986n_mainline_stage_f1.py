"""Host-only regressions for the attended S20+ Linux stage experiment."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import device_action_raw_capture_v1 as capture
import s20plus_g986n_mainline_stage_f1 as stage


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream)


class StageOwnerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.run_dir = Path(temp.name)
        self.serial = "fixture-endpoint"
        self.start = {
            "target": stage.owner.TARGET,
            "serial_sha256": hashlib.sha256(self.serial.encode()).hexdigest(),
            "topology_sha256": "c" * 64,
            "boot_id_sha256": "a" * 64,
        }
        self.returned = {**self.start, "boot_id_sha256": "b" * 64}
        self.prepared = {
            "binding_sha256": "d" * 64,
            "binding": {"preflight": self.start},
        }
        self.final = {
            "binding_sha256": "d" * 64,
            "health": self.returned,
            "rollback_transfer_completed": True,
            "rollback_outcome_proved": True,
            "resident_boot_healthy": True,
        }
        self.lease = {"run_dir": str(self.run_dir), "entrypoint": "prepare"}
        self.engine = SimpleNamespace(
            ADB=Path("/fixed/adb"),
            read_json=lambda path, _: json.loads(path.read_text()),
            durable_json=save,
            digest=digest,
            raw_capture=capture,
            RECOVERY_ARRIVAL_SECONDS=180,
            utc_now=lambda: "fixture-time",
        )
        self.runtime = SimpleNamespace(
            _require_live_transaction=lambda: self.lease,
            P0_PHYSICAL_REBIND_CONFIRM_NAME="rebind-confirmation.json",
        )
        for key, value in {
            "pair": {"nonce": "12" * 16},
            "engine": self.engine,
            "runtime": self.runtime,
            "validate_root": Mock(),
            "transfer_receipt": Mock(side_effect=lambda _, phase, __: digest(phase)),
            "require_active": Mock(),
            "original_publish": Mock(return_value="terminal"),
            "validated_current_serial": Mock(return_value=self.serial),
            "inherited_namespace": Mock(),
        }.items():
            self.enter_patch(stage.owner, key, value)
        self.enter_patch(stage, "fresh_return_run", None)
        for name, value in {
            "prepared.json": self.prepared,
            "final-health.json": self.final,
            "candidate-result.json": {"classification": "odin_transfer_completed"},
            "physical-confirmation-intent.json": {"binding_sha256": "d" * 64},
        }.items():
            save(self.run_dir / name, value)

    def enter_patch(self, obj, key, value):
        p = patch.object(obj, key, value, create=True)
        self.addCleanup(p.stop)
        return p.start()

    def intent(self, phase):
        health = self.start if phase == "baseline" else self.returned
        save(
            self.run_dir / stage.paths(phase)[0],
            stage.make_intent(self.run_dir, phase, health),
        )
        return health

    def test_preflight_and_return_have_disjoint_one_shot_leases(self):
        for phase in stage.PHASES:
            with self.subTest(phase=phase):
                health = self.intent(phase)
                name = stage.paths(phase)[1]
                argv = stage.command(self.serial, health["boot_id_sha256"])
                kw = stage.capture_options(name)
                self.lease["entrypoint"] = "execute"
                with self.assertRaises(stage.owner.Stop):
                    stage.allowed(argv, self.run_dir, name, kw)
                self.lease["entrypoint"] = (
                    "prepare" if phase == "baseline" else "confirm_physical_rollback"
                )
                if phase == "return":
                    with self.assertRaises(stage.owner.Stop):
                        stage.allowed(argv, self.run_dir, name, kw)
                    stage.fresh_return_run = self.run_dir
                self.assertTrue(stage.allowed(argv, self.run_dir, name, kw))
                with self.assertRaises(stage.owner.Stop):
                    stage.allowed(
                        stage.command("other-endpoint", health["boot_id_sha256"]),
                        self.run_dir,
                        name,
                        kw,
                    )
                with self.assertRaises(stage.owner.Stop):
                    stage.allowed(
                        stage.command(self.serial, "e" * 64), self.run_dir, name, kw
                    )
                with self.assertRaises(stage.owner.Stop):
                    stage.allowed(argv, self.run_dir, name, {**kw, "timeout": 121})
                (self.run_dir / (name + ".stdout")).touch()
                with self.assertRaises(stage.owner.Stop):
                    stage.allowed(argv, self.run_dir, name, kw)

    def test_possible_return_requires_proved_original_and_same_device(self):
        for delta in (
            {"rollback_transfer_completed": False},
            {"rollback_outcome_proved": False},
            {"resident_boot_healthy": False},
            {"binding_sha256": "e" * 64},
            {"health": self.start},
            {"health": {**self.returned, "topology_sha256": "f" * 64}},
        ):
            with self.subTest(delta=delta), self.assertRaises(stage.owner.Stop):
                stage.publish(self.run_dir, self.prepared, {**self.final, **delta})
        stage.owner.transfer_receipt.side_effect = stage.owner.Stop(
            "unproved raw rollback"
        )
        with self.assertRaisesRegex(stage.owner.Stop, "unproved raw rollback"):
            stage.publish(self.run_dir, self.prepared, self.final)
        stage.owner.original_publish.assert_not_called()
        self.assertFalse((self.run_dir / stage.paths("return")[2]).exists())

    def test_resume_never_samples_a_later_boot_or_retries_a_cut(self):
        with patch.object(stage, "acquire") as read:
            self.assertEqual(
                stage.publish(self.run_dir, self.prepared, self.final), "terminal"
            )
            read.assert_not_called()
        result_path = self.run_dir / stage.paths("return")[2]
        self.assertEqual(
            json.loads(result_path.read_text())["state"], "observation_gap"
        )
        result_path.unlink()
        self.intent("return")
        stage.fresh_return_run = self.run_dir
        with patch.object(stage, "acquire") as read:
            stage.publish(self.run_dir, self.prepared, self.final)
            read.assert_not_called()
        self.assertEqual(json.loads(result_path.read_text())["state"], "capture_cut")

    def test_real_capture_classifies_only_reached_stages(self):
        cases = [
            (b"y2q_log_v1=256,1,1,1\n", "paired", "POPULATED_ROOT", True),
            (b"y2q_log_v1=256,0,1,0\n", "unflatten_only", "POPULATED_ROOT", True),
            (b"y2q_log_v1=256,1,0,0\n", "fdt_only", "MAINLINE_FDT", True),
            (b"y2q_log_v1=256,0,0,0\n", "no_record", "NO_PROOF", False),
            (b"y2q_log_v1=256,1,1,0\n", "ambiguous", "NO_PROOF", False),
            (b"y2q_log_missing\n", "missing", "NO_PROOF", False),
            (b"malformed", "read_failed", "NO_PROOF", False),
        ]
        for output, state, label, proved in cases:
            with (
                self.subTest(state=state),
                tempfile.TemporaryDirectory(dir=self.run_dir) as directory,
            ):
                run = Path(directory)
                for item in self.run_dir.glob("*.json"):
                    (run / item.name).write_bytes(item.read_bytes())
                intent, raw, evidence = stage.paths("return")
                save(run / intent, stage.make_intent(run, "return", self.returned))
                capture.publish_captured_bytes(
                    run,
                    raw,
                    stdout=output,
                    argv0_name="adb",
                    stdout_name=raw + ".stdout",
                    stderr_name=raw + ".stderr",
                )
                value = stage.derive(run, "return", self.returned)
                self.assertEqual(value["state"], state)
                save(run / evidence, value)
                with stage.bound_run(run):
                    verdict, passed = stage.terminal_verdict(
                        "odin_transfer_completed", "NO_PROOF", True
                    )
                    self.assertIn(label, verdict)
                    self.assertEqual(passed, proved)
                    (run / evidence).write_text("{}")
                    with self.assertRaisesRegex(stage.owner.Stop, "evidence differs"):
                        stage.terminal_verdict(
                            "odin_transfer_completed", "NO_PROOF", True
                        )

    def test_candidate_dwell_uses_no_transport_and_no_control(self):
        with patch.object(stage.time, "sleep") as dwell:
            observation, serial = stage.observe(self.run_dir, self.prepared)
            dwell.assert_called_once_with(180)
            self.assertIsNone(serial)
            self.assertFalse(observation["transport_authorized"])
            self.assertEqual(observation["claim_verdict"], "NO_PROOF")
            (self.run_dir / "candidate-result.json").unlink()
            stage.observe(self.run_dir, self.prepared)
            dwell.assert_called_once()
        stage.owner.validated_current_serial.assert_not_called()

    def test_only_a_clean_baseline_allows_prepare_to_continue(self):
        self.enter_patch(
            stage.owner, "original_health", Mock(return_value=(self.start, self.serial))
        )
        self.enter_patch(stage.owner, "require_new_effect_owner_clear", Mock())
        self.enter_patch(stage, "recovery_matches", Mock())

        def read(run, phase, health, serial):
            self.intent(phase)
            raw = stage.paths(phase)[1]
            capture.publish_captured_bytes(
                run,
                raw,
                stdout=b"y2q_log_v1=256,1,0,0\n",
                argv0_name="adb",
                stdout_name=raw + ".stdout",
                stderr_name=raw + ".stderr",
            )

        with (
            patch.object(stage, "acquire", side_effect=read),
            self.assertRaisesRegex(stage.owner.Stop, "absence"),
        ):
            stage.preflight(self.run_dir, "preflight-root")
        self.assertFalse((self.run_dir / "initial-download-intent.json").exists())

    def test_extra_raw_stream_cannot_be_relabelled_as_the_return(self):
        self.intent("return")
        _, raw, _ = stage.paths("return")
        capture.publish_captured_bytes(
            self.run_dir,
            raw,
            stdout=b"y2q_log_v1=256,1,1,1\n",
            stdout_name="alien.stdout",
            argv0_name="adb",
        )
        with self.assertRaisesRegex(stage.owner.Stop, "stream identity differs"):
            stage.derive(self.run_dir, "return", self.returned)

    def test_before_download_cut_closes_only_this_guard_and_preserves_the_read(self):
        with tempfile.TemporaryDirectory(dir=self.run_dir) as path:
            run = Path(path)
            self.engine.validate_run_dir = lambda candidate: candidate
            self.engine.require_guard = Mock()
            self.engine.candidate_claim_present = Mock(return_value=False)

            def after_close(candidate):
                self.assertEqual(
                    json.loads((candidate / stage.PRECONTROL_CLOSE).read_text()),
                    stage.precontrol_result(candidate),
                )

            self.engine.release_guard = Mock(side_effect=after_close)
            self.lease.update(entrypoint="abort_pre_candidate", run_dir=str(run))
            raw = run / "mainline-baseline-scan.stdout"
            raw.write_bytes(b"partial")
            (run / "foreign-intent.json").touch()
            with self.assertRaisesRegex(stage.owner.Stop, "unexpected journal"):
                stage.abort_pre_candidate(run)
            self.engine.release_guard.assert_not_called()
            (run / "foreign-intent.json").unlink()
            self.assertEqual(stage.abort_pre_candidate(run)["device_controls"], 0)
            self.assertEqual(raw.read_bytes(), b"partial")
            self.engine.release_guard.assert_called_once_with(run)

    def test_after_download_intent_uses_existing_abort_without_releasing_guard(self):
        self.engine.validate_run_dir = lambda candidate: candidate
        self.engine.release_guard = Mock()
        abort = self.enter_patch(
            stage, "inherited_abort", Mock(return_value="existing-abort")
        )
        (self.run_dir / "initial-download-intent.json").touch()
        self.assertEqual(stage.abort_pre_candidate(self.run_dir), "existing-abort")
        abort.assert_called_once_with(self.run_dir)
        self.engine.release_guard.assert_not_called()

    def test_report_cut_after_precontrol_release_is_host_only(self):
        run = self.run_dir / ("run-" + "1" * 19)
        run.mkdir()
        self.enter_patch(stage, "RUN_ROOT", self.run_dir)
        guard = self.run_dir / "guard"
        self.enter_patch(stage.owner, "GUARD", guard)
        expected = stage.precontrol_result(run)
        sidecar = run / stage.PRECONTROL_CLOSE
        sidecar.write_text(
            json.dumps(expected, sort_keys=True, separators=(",", ":")) + "\n"
        )
        sidecar.chmod(0o400)
        self.assertEqual(stage.published_precontrol(run), expected)
        guard.touch()
        self.assertIsNone(stage.published_precontrol(run))
        self.assertTrue(guard.exists())
        guard.unlink()
        (run / "initial-download-intent.json").touch()
        with self.assertRaisesRegex(stage.owner.Stop, "unexpected journal"):
            stage.published_precontrol(run)

    def test_saved_baseline_and_first_return_must_belong_to_original_boots(self):
        self.intent("baseline")
        (self.run_dir / "initial-download-intent.json").touch()
        with self.assertRaisesRegex(stage.owner.Stop, "no qualified baseline"):
            stage.validate_namespace(self.run_dir)
        self.intent("return")
        with self.assertRaisesRegex(stage.owner.Stop, "unproved first return"):
            stage.derive(self.run_dir, "return", self.start)
        (self.run_dir / "physical-confirmation-intent.json").write_text(
            '{"binding_sha256":"wrong"}'
        )
        with self.assertRaisesRegex(stage.owner.Stop, "physical confirmation differs"):
            stage.derive(self.run_dir, "return", self.returned)

    def test_cut_without_candidate_result_never_gains_stage_proof(self):
        (self.run_dir / "candidate-result.json").unlink()
        stage.fresh_return_run = self.run_dir
        with patch.object(stage, "acquire") as read:
            stage.publish(self.run_dir, self.prepared, self.final)
            read.assert_not_called()
        self.assertEqual(
            stage.first_return(self.run_dir, self.prepared, self.final)["state"],
            "transfer_unproved",
        )


if __name__ == "__main__":
    unittest.main()
