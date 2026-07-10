import importlib.util
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3428_stock_transition_positive_control.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_v3428_stock_transition_positive_control", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3428StockTransitionPositiveControlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_offline_plan_is_not_live_authorization(self):
        plan = self.module.offline_plan(self.module.repo_root())
        self.assertFalse(plan["live_authorized"])
        self.assertFalse(plan["candidate_flash"])
        self.assertTrue(plan["boot_only_identity_rollback"])

    def test_expectation_binds_both_contracts(self):
        expectation = self.module.make_expectation("0" * 32)
        record = self.module.expected_marker_record(expectation)
        self.assertEqual(
            record["observer_contract_sha256"],
            self.module.observer.CONTRACT_SHA256,
        )
        self.assertEqual(
            record["transition_sha256"],
            self.module.transition.TRANSITION_SHA256,
        )

    def test_timeline_has_single_events_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "timeline.json"
            events = []
            for name in self.module.TIMELINE_NAMES:
                self.module.record_timeline_event(path, events, name)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(data), {"events"})
            self.assertEqual(
                [event["name"] for event in data["events"]],
                list(self.module.TIMELINE_NAMES),
            )
            self.assertTrue(self.module.timeline_complete(events))

    def test_timeline_rejects_unknown_and_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "timeline.json"
            events = []
            with self.assertRaises(self.module.PositiveControlError):
                self.module.record_timeline_event(path, events, "other")
            self.module.record_timeline_event(
                path, events, self.module.TIMELINE_NAMES[0]
            )
            with self.assertRaises(self.module.PositiveControlError):
                self.module.record_timeline_event(
                    path, events, self.module.TIMELINE_NAMES[0]
                )

    def test_policy_markers_pin_helper_contracts_and_rollback(self):
        markers = self.module.policy_markers(self.module.repo_root())
        self.assertIn(self.module.LIVE_ACK_TOKEN, markers)
        self.assertIn(self.module.observer.CONTRACT_SHA256, markers)
        self.assertIn(self.module.transition.TRANSITION_SHA256, markers)
        self.assertIn(self.module.transition.MAGISK_ROLLBACK_AP_SHA256, markers)
        self.assertIn(self.module.transition.STOCK_ROLLBACK_AP_SHA256, markers)

    def test_exception_verifier_rejects_missing_or_consumed(self):
        root = self.module.repo_root()
        with mock.patch.object(Path, "read_text", return_value=""):
            with self.assertRaises(self.module.PositiveControlError):
                self.module.verify_agents_exception(root)
        consumed = (
            "   "
            + self.module.ACTIVE_EXCEPTION_HEADING
            + "\n   Consumed exception\n"
        )
        with mock.patch.object(Path, "read_text", return_value=consumed):
            with self.assertRaises(self.module.PositiveControlError):
                self.module.verify_agents_exception(root)

    def test_marker_emit_command_is_bounded_dev_kmsg_write(self):
        expectation = self.module.make_expectation("1" * 32)
        frame = self.module.observer.encode_marker(
            expectation, self.module.observer.PHASE_PRECHECK
        )
        completed = self.module.subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        with mock.patch.object(
            self.module, "root_shell", return_value=completed
        ) as mocked:
            self.module.emit_marker("serial", frame)
        command = mocked.call_args.args[1]
        self.assertIn("> /dev/kmsg", command)
        self.assertNotIn("sysrq", command)
        self.assertNotIn("/dev/block", command)

    def test_connected_preflight_is_read_only_by_source_contract(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("adb reboot download", source)
        self.assertNotIn("/proc/sysrq-trigger", source)
        self.assertNotIn("fastboot", source)
        self.assertNotIn("vendor_boot", source)

    def test_connected_preflight_requires_exact_driver_bind(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("echo bind_ok=1", source)
        self.assertIn('"bind_ok=1",', source)

    def test_postrollback_health_is_fail_closed(self):
        good_props = (
            "model=SM-S906N\n"
            "device=g0q\n"
            "bootloader=S906NKSS7FYG8\n"
            "incremental=S906NKSS7FYG8\n"
            "boot_completed=1\n"
            "vbstate=orange\n"
        )
        root_state = f"uid=0(root)\n{self.module.EXPECTED_BOOT_SHA256}\n"
        good = self.module.evaluate_postrollback_health(good_props, root_state)
        self.assertTrue(good["pass"])
        bad = self.module.evaluate_postrollback_health(
            good_props.replace("boot_completed=1", "boot_completed=0"),
            root_state,
        )
        self.assertFalse(bad["pass"])

    def test_observer_stop_result_is_json_serializable(self):
        state = SimpleNamespace(
            name="udev_usb",
            argv=["udevadm"],
            log_path="log",
            started=True,
            returncode=-15,
            start_error=None,
        )
        observer = mock.Mock()
        observer.stop.return_value = state
        stopped = self.module.stop_observers([observer])
        json.dumps(stopped)
        self.assertEqual(stopped["udev_usb"]["returncode"], -15)

    def test_timeline_semantics_are_explicitly_no_candidate_flash(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"candidate_flash": False', source)
        self.assertIn("marker_arm_start_no_candidate_flash", source)
        self.assertIn("marker_pair_verified_no_candidate_flash", source)
        self.assertIn(
            "no_candidate_flash_marker_arm_start",
            self.module.TIMELINE_SEMANTIC_NAMES,
        )
        self.assertIn(
            "no_candidate_flash_marker_pair_verified",
            self.module.TIMELINE_SEMANTIC_NAMES,
        )

    def test_local_odin_log_path_redacts_serials(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("from s22plus_m3_observable_live_gate import (", source)
        self.assertIn("def wait_for_odin(", source)
        self.assertIn("def flash_ap(", source)

    def test_live_ack_mismatch_stops_before_preflight(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(self.module.PositiveControlError):
                self.module.live_run(
                    self.module.repo_root(), Path(temp), "wrong", 30
                )

    def test_redaction_removes_device_serial_shape(self):
        self.assertEqual(
            self.module.redact("device RFCT123ABC connected"),
            "device <S22_SERIAL_REDACTED> connected",
        )


if __name__ == "__main__":
    unittest.main()
