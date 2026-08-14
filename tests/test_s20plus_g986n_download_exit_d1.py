import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_download_exit_d1.py"
SCRIPT_DIR = SCRIPT.parent
import sys
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("s20plus_g986n_download_exit_d1", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class S20PlusDownloadExitTests(unittest.TestCase):
    def setUp(self):
        self.identity = (1, 2, 3, 4)
        self.endpoint = {
            "device": "/dev/bus/usb/002/015",
            "endpoint_identity": list(self.identity),
            "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/002/015").hexdigest(),
            "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True},
        }

    def paths(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        run_root = root / "runs"
        guard = root / "routine" / "active-action.json"
        guard.parent.mkdir(parents=True)
        patches = mock.patch.multiple(MODULE, RUN_ROOT=run_root, SHARED_GUARD=guard)
        patches.start()
        self.addCleanup(patches.stop)
        self.addCleanup(temporary.cleanup)
        return temporary, root, run_root, guard

    def odin_receipt(self):
        return {"path": str(MODULE.ODIN), "size": MODULE.ODIN_SIZE, "sha256": MODULE.ODIN_SHA256}

    def test_arm_requires_empty_baseline_and_records_no_replay_binding(self):
        _temporary, _root, run_root, guard = self.paths()
        run = run_root / "run-arm"
        run.mkdir(parents=True)
        with mock.patch.object(MODULE, "tool_receipt", return_value=self.odin_receipt()):
            MODULE.arm(run, lambda argv, timeout, maximum: (0, b"", b""))
        self.assertTrue((run / "baseline.json").is_file())
        self.assertTrue((run / "arm-intent.json").is_file())
        self.assertTrue(guard.is_file())
        self.assertEqual(MODULE.read_json(run / "arm-intent.json", "arm")["operator_confirmation_required"], MODULE.CONFIRM_TOKEN)

    def test_arm_rejects_present_endpoint_and_closes_effect_free_guard(self):
        _temporary, _root, run_root, guard = self.paths()
        run = run_root / "run-arm"
        run.mkdir(parents=True)
        with mock.patch.object(MODULE, "tool_receipt", return_value=self.odin_receipt()), self.assertRaises(MODULE.ExitError):
            MODULE.arm(run, lambda argv, timeout, maximum: (0, b"/dev/bus/usb/002/015\n", b""))
        self.assertFalse(guard.exists())
        self.assertTrue((run / "failure.json").is_file())

    def test_confirm_dispatches_only_no_payload_odin_and_closes_after_android_health(self):
        _temporary, _root, run_root, guard = self.paths()
        run = run_root / "run-confirm"
        run.mkdir(parents=True)
        with mock.patch.object(MODULE, "tool_receipt", return_value=self.odin_receipt()):
            MODULE.arm(run, lambda argv, timeout, maximum: (0, b"", b""))
        calls = []

        def command(argv, timeout, maximum):
            calls.append(argv)
            return 0, b"", b""

        with mock.patch.object(MODULE, "identify_download", return_value=self.endpoint), mock.patch.object(MODULE, "endpoint_stat", side_effect=[self.identity, FileNotFoundError()]), mock.patch.object(MODULE, "android_health", return_value={"model": MODULE.EXPECTED_MODEL, "device": MODULE.EXPECTED_DEVICE, "product": MODULE.EXPECTED_PRODUCT, "incremental": MODULE.EXPECTED_INCREMENTAL, "serial_sha256": "a" * 64, "topology_sha256": MODULE.EXPECTED_ANDROID_TOPOLOGY_SHA256, "boot_id_sha256": "b" * 64}):
            result = MODULE.confirm(run, MODULE.CONFIRM_TOKEN, command)
        self.assertEqual(result["verdict"], "PASS_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTHY")
        self.assertFalse(guard.exists())
        self.assertEqual(calls, [[str(MODULE.ODIN), "--reboot", "-d", self.endpoint["device"]]])
        self.assertNotIn("-a", calls[0])
        self.assertNotIn("-b", calls[0])
        self.assertNotIn("-u", calls[0])

    def test_malformed_endpoint_after_arm_fails_before_odin_and_closes_effect_free(self):
        _temporary, _root, run_root, guard = self.paths()
        run = run_root / "run-drift"
        run.mkdir(parents=True)
        with mock.patch.object(MODULE, "tool_receipt", return_value=self.odin_receipt()):
            MODULE.arm(run, lambda argv, timeout, maximum: (0, b"", b""))
        calls = []

        def command(argv, timeout, maximum):
            calls.append(argv)
            return 0, b"", b""

        foreign = {**self.endpoint, "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": False}}
        with mock.patch.object(MODULE, "identify_download", return_value=foreign), self.assertRaises(MODULE.ExitError):
            MODULE.confirm(run, MODULE.CONFIRM_TOKEN, command)
        self.assertFalse(calls)
        self.assertFalse(guard.exists())
        self.assertFalse((run / "exit-intent.json").exists())

    def test_finalize_never_dispatches_or_replays(self):
        _temporary, _root, run_root, guard = self.paths()
        run = run_root / "run-finalize"
        run.mkdir(parents=True)
        with mock.patch.object(MODULE, "tool_receipt", return_value=self.odin_receipt()):
            MODULE.arm(run, lambda argv, timeout, maximum: (0, b"", b""))
        MODULE.durable_create(run / "exit-intent.json", {"schema": "s20plus_g986n_download_exit_intent_v1", "version": MODULE.VERSION, "binding_sha256": MODULE.read_json(run / "arm-intent.json", "arm")["binding_sha256"], "action": "exit-download", "endpoint": self.endpoint, "command_shape": ["odin4", "--reboot", "-d", "USBFS"], "attempt": 1, "no_payload": True, "no_replay": True, "at": MODULE.now()})
        MODULE.durable_bytes(run / "exit.stdout", b"")
        MODULE.durable_bytes(run / "exit.stderr", b"")
        MODULE.durable_create(run / "result.json", {"schema": "s20plus_g986n_download_exit_result_v1", "version": MODULE.VERSION, "binding_sha256": MODULE.read_json(run / "arm-intent.json", "arm")["binding_sha256"], "verdict": "RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTH", "returncode": 0, "post_state": "absent", "effect_command_count": 1, "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "no_replay": True, "replay_permitted": False, "at": MODULE.now()})
        with mock.patch.object(MODULE, "android_health", return_value={"model": MODULE.EXPECTED_MODEL, "device": MODULE.EXPECTED_DEVICE, "product": MODULE.EXPECTED_PRODUCT, "incremental": MODULE.EXPECTED_INCREMENTAL, "serial_sha256": "a" * 64, "topology_sha256": MODULE.EXPECTED_ANDROID_TOPOLOGY_SHA256, "boot_id_sha256": "b" * 64}):
            result = MODULE.finalize(run, lambda *_: (_ for _ in ()).throw(AssertionError("device command unexpectedly called")))
        self.assertEqual(result["verdict"], "PASS_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTHY")
        self.assertFalse(guard.exists())

    def test_confirm_without_matching_guard_stops_before_endpoint_or_odin(self):
        _temporary, _root, run_root, guard = self.paths()
        run = run_root / "run-no-guard"
        run.mkdir(parents=True)
        with mock.patch.object(MODULE, "tool_receipt", return_value=self.odin_receipt()):
            MODULE.arm(run, lambda argv, timeout, maximum: (0, b"", b""))
        guard.unlink()
        with mock.patch.object(MODULE, "identify_download", side_effect=AssertionError("endpoint must not be read")):
            with self.assertRaises(MODULE.ExitError):
                MODULE.confirm(run, MODULE.CONFIRM_TOKEN, lambda *_: (_ for _ in ()).throw(AssertionError("command")))

    def test_finalize_rejects_extra_journal_node_and_keeps_guard(self):
        _temporary, _root, run_root, guard = self.paths()
        run = run_root / "run-extra"
        run.mkdir(parents=True)
        with mock.patch.object(MODULE, "tool_receipt", return_value=self.odin_receipt()):
            MODULE.arm(run, lambda argv, timeout, maximum: (0, b"", b""))
        arm_value = MODULE.read_json(run / "arm-intent.json", "arm")
        binding_sha = arm_value["binding_sha256"]
        MODULE.durable_create(run / "exit-intent.json", {"schema": "s20plus_g986n_download_exit_intent_v1", "version": MODULE.VERSION, "binding_sha256": binding_sha, "action": "exit-download", "endpoint": self.endpoint, "command_shape": ["odin4", "--reboot", "-d", "USBFS"], "attempt": 1, "no_payload": True, "no_replay": True, "at": MODULE.now()})
        MODULE.durable_bytes(run / "exit.stdout", b"")
        MODULE.durable_bytes(run / "exit.stderr", b"")
        MODULE.durable_create(run / "result.json", {"schema": "s20plus_g986n_download_exit_result_v1", "version": MODULE.VERSION, "binding_sha256": binding_sha, "verdict": "RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTH", "returncode": 0, "post_state": "absent", "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "effect_command_count": 1, "no_replay": True, "replay_permitted": False, "at": MODULE.now()})
        MODULE.durable_bytes(run / "unexpected", b"x")
        with mock.patch.object(MODULE, "android_health", side_effect=AssertionError("health must not be read")):
            with self.assertRaises(MODULE.ExitError):
                MODULE.finalize(run)
        self.assertTrue(guard.exists())

    def test_source_has_no_partition_or_payload_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"--reboot", "-d"', source)
        self.assertNotIn('"--reboot", "-a"', source)
        self.assertNotIn('"--reboot", "-b"', source)
        self.assertNotIn('"--reboot", "-c"', source)
        self.assertNotIn('"--reboot", "-u"', source)
        self.assertNotIn("/dev/block", source)
        self.assertNotIn("su -c", source)

    def test_contract_and_report_bind_exact_exit_runner(self):
        contract = (ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md").read_text(encoding="utf-8")
        report = (ROOT / "docs/reports/S20PLUS_G986N_DOWNLOAD_EXIT_D1_H0_2026-08-13.md").read_text(encoding="utf-8")
        digest = MODULE.sha256_file(SCRIPT)
        self.assertIn("Status: **BINDING - ATTENDED PAYLOAD-FREE DOWNLOAD RETURN ACTIVE**", contract)
        self.assertIn("| `exit-download` |", contract)
        self.assertIn(digest, report)
        self.assertIn("--reboot -d", contract)


if __name__ == "__main__":
    unittest.main()
