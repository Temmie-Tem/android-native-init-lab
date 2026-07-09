import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT_DIR = Path("workspace/public/src/scripts/revalidation").resolve()
SCRIPT = SCRIPT_DIR / "s22plus_o11_stock_first_stage_control_live_gate.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_o11_stock_first_stage_control_live_gate", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusO11StockFirstStageControlLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_active_exception_contains_every_live_marker(self):
        text = Path("AGENTS.md").read_text(encoding="utf-8")
        segment = self.module.active_exception_segment(text)
        self.assertTrue(segment)
        self.assertNotIn("Consumed exception", segment)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(text, encoding="utf-8")
            self.module.verify_agents_exception(root, root / "gate.log")

    def test_consumed_exception_is_not_live_authorization(self):
        text = Path("AGENTS.md").read_text(encoding="utf-8")
        text = text.replace(
            self.module.ACTIVE_EXCEPTION_HEADING,
            "**Consumed exception (2026-07-10, S22+ O1.1 SELinux-domain USB control boot-only live gate):**",
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "absent or consumed"):
                self.module.verify_agents_exception(root, root / "gate.log")

    def test_live_requires_both_new_ack_tokens(self):
        args = argparse.Namespace(live=True, ack=None, rollback_ack=None)
        with self.assertRaisesRegex(SystemExit, "--ack"):
            self.module.validate_live_authorization(args)
        args.ack = self.module.LIVE_ACK_TOKEN
        with self.assertRaisesRegex(SystemExit, "--rollback-ack"):
            self.module.validate_live_authorization(args)
        args.rollback_ack = self.module.ROLLBACK_ACK_TOKEN
        self.module.validate_live_authorization(args)

    def test_download_retry_waits_for_reconnect_then_succeeds(self):
        responses = iter(
            [
                SimpleNamespace(returncode=1, stdout="", stderr="error: closed"),
                SimpleNamespace(returncode=0, stdout="", stderr=""),
            ]
        )
        calls = []

        def runner(argv, timeout):
            calls.append((argv, timeout))
            return next(responses)

        with tempfile.TemporaryDirectory() as tmp:
            result = self.module.request_download_with_retry(
                "SERIAL",
                Path(tmp) / "gate.log",
                Path("/usr/bin/odin4"),
                run_command=runner,
                transition_probe=lambda odin, serial, log, timeout: "adb",
            )
        self.assertTrue(result["success"])
        self.assertEqual(len(result["attempts"]), 2)
        self.assertEqual(len(calls), 2)

    def test_download_retry_stops_without_reconnect(self):
        calls = []

        def runner(argv, timeout):
            calls.append((argv, timeout))
            return SimpleNamespace(returncode=1, stdout="", stderr="error: closed")

        with tempfile.TemporaryDirectory() as tmp:
            result = self.module.request_download_with_retry(
                "SERIAL",
                Path(tmp) / "gate.log",
                Path("/usr/bin/odin4"),
                run_command=runner,
                transition_probe=lambda odin, serial, log, timeout: "none",
            )
        self.assertFalse(result["success"])
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(len(calls), 1)

    def test_download_error_with_odin_is_success_without_retry(self):
        calls = []

        def runner(argv, timeout):
            calls.append((argv, timeout))
            return SimpleNamespace(returncode=1, stdout="", stderr="error: closed")

        with tempfile.TemporaryDirectory() as tmp:
            result = self.module.request_download_with_retry(
                "SERIAL",
                Path(tmp) / "gate.log",
                Path("/usr/bin/odin4"),
                run_command=runner,
                transition_probe=lambda odin, serial, log, timeout: "odin",
            )
        self.assertTrue(result["success"])
        self.assertEqual(result["transition"], "odin-after-adb-error")
        self.assertEqual(len(calls), 1)

    def test_readiness_requires_daemon_phase_and_stock_handoff(self):
        evidence = {
            "rc": 0,
            "values": {
                "marker": "1",
                "phase": "daemon-running",
                "o1_service_state": "running",
            },
        }
        stock = {"rc": 0, "state": "stopped", "pid_present": False, "tty_owner_count": 0}
        self.assertEqual(self.module.readiness_reasons(evidence, stock), [])
        stock["state"] = "running"
        self.assertEqual(
            self.module.readiness_reasons(evidence, stock),
            ["stock-service-not-handed-off"],
        )

    def test_candidate_snapshot_is_pinned_to_o11_boot(self):
        snapshot = {
            "model": "SM-S906N",
            "device": "g0q",
            "incremental": "S906NKSS7FYG8",
            "boot_completed": "1",
            "boot_recovery": "0",
            "vbstate": "orange",
            "ttyGS0_char": "1",
            "boot_sha256": self.module.EXPECTED_O11_BOOT_SHA256,
            "uid": "0",
            "udc": "a600000.dwc3",
            "usb_config": "mtp,conn_gadget,adb",
        }
        self.assertEqual(self.module.candidate_snapshot_reasons(snapshot), [])
        snapshot["boot_sha256"] = self.module.EXPECTED_BASE_BOOT_SHA256
        self.assertEqual(self.module.candidate_snapshot_reasons(snapshot), ["boot_sha256-mismatch"])

    def test_offline_contract_keeps_single_behavior_delta(self):
        contract = self.module.offline_contract()
        self.assertEqual(contract["service_seclabel"], "u:r:magisk:s0")
        self.assertEqual(contract["download_retry_max_attempts"], 2)
        self.assertTrue(contract["automatic_retained_log_collection"])
        self.assertTrue(contract["mandatory_rollback"])
        self.assertFalse(contract["selinux_policy_file_change"])
        self.assertFalse(contract["configfs_write"])
        self.assertFalse(contract["module_insertion"])

    def test_source_contains_standard_timeline_and_retained_collection(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for phase in self.module.REQUIRED_LIVE_TIMELINE_PHASES:
            self.assertIn(phase, source)
        self.assertIn("collect_retained_after_rollback", source)
        self.assertIn("request_download_with_retry", source)

    def test_candidate_boot_ready_follows_snapshot_hash_gate(self):
        source = SCRIPT.read_text(encoding="utf-8")
        snapshot_gate = source.index("snapshot_reasons = candidate_snapshot_reasons")
        boot_ready = source.index('record_timeline_event(run_dir, "candidate_boot_ready")')
        runtime_gate = source.index("readiness, ready_stock, ready_reasons = wait_runtime_ready")
        self.assertLess(snapshot_gate, boot_ready)
        self.assertLess(boot_ready, runtime_gate)


if __name__ == "__main__":
    unittest.main()
