import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3437_ramoops_positive_control_live_gate.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_v3437_ramoops_positive_control_live_gate", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3437RamoopsPositiveControlLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.root = cls.module.repo_root()

    def test_offline_artifacts_and_policy_drafts_pass(self):
        contract = self.module.verify_artifacts(self.root)
        self.assertEqual(contract["verdict"], "HOST_DESIGN_PASS_NO_LIVE")
        drafts = self.module.verify_policy_drafts(self.root)
        self.assertEqual(
            set(drafts),
            {
                str(self.module.DTBO_POLICY_DRAFT),
                str(self.module.PANIC_POLICY_DRAFT),
            },
        )
        status = self.module.policy_status(self.root)
        self.assertEqual(set(status), {"dtbo_active", "panic_active"})
        self.assertTrue(all(isinstance(value, bool) for value in status.values()))

    def test_offline_check_never_calls_device_functions(self):
        with mock.patch.object(
            self.module, "require_current_android", side_effect=AssertionError("device")
        ):
            self.assertEqual(self.module.main(["--offline-check"]), 0)

    def test_print_plan_never_calls_device_functions(self):
        with mock.patch.object(
            self.module, "require_current_android", side_effect=AssertionError("device")
        ):
            self.assertEqual(self.module.main(["--print-plan"]), 0)

    def test_device_modes_fail_before_device_contact_while_policy_inactive(self):
        with mock.patch.object(
            self.module,
            "policy_status",
            return_value={"dtbo_active": False, "panic_active": False},
        ), mock.patch.object(
            self.module, "require_current_android", side_effect=AssertionError("device")
        ):
            with self.assertRaisesRegex(self.module.GateError, "policy is inactive"):
                self.module.main(
                    [
                        "--dry-run",
                        "--dtbo-ack",
                        self.module.DTBO_ACK_TOKEN,
                        "--panic-ack",
                        self.module.PANIC_ACK_TOKEN,
                    ]
                )

    def test_policy_status_requires_both_independent_marker_sets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dtbo_text = " ".join(
                (
                    self.module.DTBO_POLICY_MARKER,
                    self.module.DTBO_ACTIVE_SENTINEL,
                    self.module.HELPER_PATH,
                    self.module.DTBO_ACK_TOKEN,
                    self.module.RESTORE_ACK_TOKEN,
                    self.module.design.PINS[self.module.design.CANDIDATE_AP],
                    self.module.design.PINS[self.module.design.ROLLBACK_AP],
                )
            )
            (root / "AGENTS.md").write_text(dtbo_text, encoding="utf-8")
            self.assertEqual(
                self.module.policy_status(root),
                {"dtbo_active": True, "panic_active": False},
            )
            panic_text = " ".join(
                (
                    self.module.PANIC_POLICY_MARKER,
                    self.module.PANIC_ACTIVE_SENTINEL,
                    self.module.HELPER_PATH,
                    self.module.PANIC_ACK_TOKEN,
                    self.module.design.CONTRACT_SHA256,
                    "sysrq-trigger-c",
                )
            )
            (root / "AGENTS.md").write_text(
                dtbo_text + " " + panic_text, encoding="utf-8"
            )
            self.assertEqual(
                self.module.policy_status(root),
                {"dtbo_active": True, "panic_active": True},
            )

    def test_acknowledgements_are_independent(self):
        args = argparse.Namespace(
            dtbo_ack=self.module.DTBO_ACK_TOKEN,
            panic_ack=None,
            restore_ack=None,
        )
        with self.assertRaisesRegex(self.module.GateError, "panic action requires"):
            self.module.verify_acks(args, panic=True)
        args.panic_ack = self.module.PANIC_ACK_TOKEN
        self.module.verify_acks(args, panic=True)
        with self.assertRaisesRegex(self.module.GateError, "restore action requires"):
            self.module.verify_acks(args, panic=False, restore=True)

    def test_timeline_is_single_events_schema_and_durable(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "timeline.json"
            timeline = self.module.Timeline.create(path)
            timeline.append("live_session_start")
            timeline.append("candidate_flash_start")
            loaded = self.module.Timeline.load(path)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"events": loaded.events},
            )
            self.assertEqual([event["name"] for event in loaded.events], [
                "live_session_start",
                "candidate_flash_start",
            ])
            with self.assertRaisesRegex(self.module.GateError, "duplicate"):
                loaded.append("candidate_flash_start")
            with self.assertRaisesRegex(self.module.GateError, "unknown"):
                loaded.append("ad_hoc_phase")

    def test_timeline_rejects_ad_hoc_shape_and_reverse_order(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "timeline.json"
            path.write_text('{"steps": []}\n', encoding="utf-8")
            with self.assertRaisesRegex(self.module.GateError, "single events"):
                self.module.Timeline.load(path)
            path.write_text(
                json.dumps(
                    {
                        "events": [
                            {"name": "candidate_flash_start", "timestamp_utc": "x"},
                            {"name": "live_session_start", "timestamp_utc": "y"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(self.module.GateError, "order"):
                self.module.Timeline.load(path)

    def test_session_state_is_resumable_and_contract_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            session = self.module.Session.create(run_dir, "SERIAL")
            session.advance("CANDIDATE_TRANSFER")
            session.advance("PATCHED_BOOT_WAIT")
            loaded = self.module.Session.load(run_dir / "session.json")
            self.assertEqual(loaded.value["state"], "PATCHED_BOOT_WAIT")
            self.assertEqual(
                loaded.value["contract_sha256"], self.module.design.CONTRACT_SHA256
            )
            with self.assertRaisesRegex(self.module.GateError, "forbidden"):
                loaded.advance("CLASSIFIED")

    def test_evidence_abandonment_is_explicit_recovery_override(self):
        with tempfile.TemporaryDirectory() as temp:
            session = self.module.Session.create(Path(temp), "SERIAL")
            session.advance("CANDIDATE_TRANSFER")
            session.advance("PATCHED_BOOT_WAIT")
            session.advance("PATCHED_PREFLIGHT")
            session.advance("BACKEND_PROVEN")
            session.advance("MARKERS_WRITTEN")
            session.advance("PANIC_TRIGGERED")
            session.advance("RECOVERY_WAIT")
            session.abandon_evidence_for_recovery()
            self.assertEqual(session.value["state"], "EVIDENCE_COLLECTED")
            self.assertTrue(session.value["evidence_abandoned_for_recovery"])
            self.assertEqual(
                session.value["classification"]["result"],
                "NO_PROOF_EVIDENCE_ABANDONED_FOR_RECOVERY",
            )

    def test_prep_failure_uses_android_rollback_before_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            session = self.module.Session.create(run_dir, "SERIAL")
            for state in (
                "CANDIDATE_TRANSFER",
                "PATCHED_BOOT_WAIT",
                "PATCHED_PREFLIGHT",
            ):
                session.advance(state)
            timeline = self.module.Timeline.create(run_dir / "timeline.json")
            for event in (
                "live_session_start",
                "candidate_flash_start",
                "candidate_flash_done",
                "candidate_boot_ready",
            ):
                timeline.append(event)

            def fake_rollback(*_args):
                session.advance("ROLLBACK_TRANSFER")
                session.advance("ROLLBACK_BOOT_WAIT")
                session.advance("STOCK_RESTORED")

            with mock.patch.object(
                self.module,
                "adb_rows",
                return_value=[("SERIAL", "device", "")],
            ), mock.patch.object(
                self.module,
                "current_partition_hash",
                return_value=self.module.design.PINS[self.module.design.CANDIDATE_RAW],
            ), mock.patch.object(
                self.module, "rollback_from_android", side_effect=fake_rollback
            ) as rollback:
                restored = self.module.attempt_prep_failure_rollback(
                    self.root,
                    "SERIAL",
                    Path("/odin"),
                    run_dir / "log",
                    session,
                    timeline,
                    30,
                )
            self.assertTrue(restored)
            self.assertEqual(rollback.call_count, 1)
            self.assertEqual(session.value["state"], "CLASSIFIED")
            self.assertEqual(
                session.value["classification"]["result"],
                "FAIL_PREPANIC_GATE_ROLLBACK",
            )
            self.assertEqual(timeline.events[-1]["name"], "live_session_end")

    def test_transport_not_lost_rollback_keeps_specific_classification(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            session = self.module.Session.create(run_dir, "SERIAL")
            for state in (
                "CANDIDATE_TRANSFER",
                "PATCHED_BOOT_WAIT",
                "PATCHED_PREFLIGHT",
                "BACKEND_PROVEN",
                "MARKERS_WRITTEN",
                "PANIC_TRIGGERED",
            ):
                session.advance(state)
            timeline = self.module.Timeline.create(run_dir / "timeline.json")
            for event in (
                "live_session_start",
                "candidate_flash_start",
                "candidate_flash_done",
                "candidate_boot_ready",
                "backend_proven",
                "markers_written",
                "panic_trigger_start",
            ):
                timeline.append(event)

            def fake_rollback(*_args):
                session.advance("ROLLBACK_TRANSFER")
                session.advance("ROLLBACK_BOOT_WAIT")
                session.advance("STOCK_RESTORED")

            with mock.patch.object(
                self.module,
                "adb_rows",
                return_value=[("SERIAL", "device", "")],
            ), mock.patch.object(
                self.module,
                "current_partition_hash",
                return_value=self.module.design.PINS[self.module.design.CANDIDATE_RAW],
            ), mock.patch.object(
                self.module, "rollback_from_android", side_effect=fake_rollback
            ):
                restored = self.module.attempt_prep_failure_rollback(
                    self.root,
                    "SERIAL",
                    Path("/odin"),
                    run_dir / "log",
                    session,
                    timeline,
                    30,
                    "FAIL_PANIC_TRANSPORT_NOT_LOST",
                )
            self.assertTrue(restored)
            self.assertEqual(session.value["state"], "CLASSIFIED")
            self.assertEqual(
                session.value["classification"]["result"],
                "FAIL_PANIC_TRANSPORT_NOT_LOST",
            )

    def test_marker_arm_uses_kmsg_pmsg_and_one_sysrq_enable(self):
        captured = {}

        def fake_run(serial, script, timeout):
            captured.update(serial=serial, script=script, timeout=timeout)
            return subprocess.CompletedProcess([], 0, b"", b"")

        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            self.module, "direct_adb_su", side_effect=fake_run
        ):
            self.module.arm_markers(
                "SERIAL",
                "0123456789abcdef0123456789abcdef",
                Path(temp) / "log.txt",
            )
        self.assertEqual(captured["script"].count("/proc/sys/kernel/sysrq"), 1)
        self.assertIn("/dev/kmsg", captured["script"])
        self.assertIn("/dev/pmsg0", captured["script"])
        self.assertIn("PREPANIC_KMSG", captured["script"])
        self.assertIn("PREPANIC_PMSG", captured["script"])

    def test_panic_trigger_is_single_call_and_return_is_failure(self):
        run_id = "0123456789abcdef0123456789abcdef"
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            self.module,
            "direct_adb_su",
            return_value=subprocess.CompletedProcess([], 99, b"", b""),
        ) as mocked:
            with self.assertRaisesRegex(self.module.GateError, "returned"):
                self.module.trigger_panic_once("SERIAL", run_id, Path(temp) / "log")
            self.assertEqual(mocked.call_count, 1)
            script = mocked.call_args.args[1]
            self.assertEqual(script.count("/proc/sysrq-trigger"), 1)

    def test_duplicate_pstore_reads_must_match(self):
        calls = []

        def stable(_serial, output):
            calls.append(output)
            return {"console-ramoops-0": b"stable"}

        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            self.module, "collect_pstore_once", side_effect=stable
        ):
            result = self.module.collect_pstore_twice("SERIAL", Path(temp), 1)
            self.assertEqual(result, {"console-ramoops-0": b"stable"})
            self.assertEqual(len(calls), 2)

        responses = iter(
            [
                {"console-ramoops-0": b"one"},
                {"console-ramoops-0": b"two"},
            ]
        )
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            self.module, "collect_pstore_once", side_effect=lambda *_: next(responses)
        ):
            with self.assertRaisesRegex(self.module.GateError, "changed"):
                self.module.collect_pstore_twice("SERIAL", Path(temp), 1)

    def test_source_has_no_unguarded_default_live_mode(self):
        source = (self.root / SCRIPT).read_text(encoding="utf-8")
        self.assertIn("require_active_policies", source)
        self.assertIn("verify_acks", source)
        self.assertIn("verify_acks(args, panic=True, restore=True)", source)
        self.assertIn("--offline-check", source)
        self.assertIn("--resume-after-manual-recovery", source)
        self.assertNotIn("default=True", source)


if __name__ == "__main__":
    unittest.main()
