import importlib.util
import contextlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s20plus_g986n_magisk_bootstrap_f1.py"
import sys
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("s20_f1", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class S20BootstrapF1Tests(unittest.TestCase):
    def make_sysfs(self, root: Path, name: str = "3-2.1", bus: str = "3", dev: str = "7") -> Path:
        node = root / name
        node.mkdir(parents=True)
        values = {"busnum": bus, "devnum": dev, **MODULE.DOWNLOAD_USB, "serial": ""}
        for key, value in values.items():
            (node / key).write_text(value + "\n")
        return node

    def test_active_plan_and_cli_surface_are_closed(self):
        plan = MODULE.render_plan()
        self.assertTrue(plan["active"])
        self.assertFalse(plan["live_flash_authorized"])
        self.assertFalse(plan["candidate_replay"])
        self.assertTrue(plan["rollback"]["mandatory"])
        options = MODULE.main.__code__.co_consts
        source = SCRIPT.read_text()
        for forbidden in ("--artifact", "--odin", "--device", "--adb", "--serial"):
            self.assertNotIn(forbidden, source)

    def test_exact_download_identity_and_topology(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE, "EXPECTED_TOPOLOGY_SHA256", MODULE.hashlib.sha256(b"usb:3-2.1").hexdigest()
        ):
            root = Path(temporary)
            self.make_sysfs(root)
            command = lambda argv, timeout, maximum: (0, b"/dev/bus/usb/003/007\n", b"")
            result = MODULE.identify_download(command, sys_root=root, stat_reader=lambda path: (1, 2, 3, 4))
            self.assertEqual(result["usb"]["idProduct"], "685d")
            self.assertTrue(result["usb"]["serial_absent"])

    def test_transition_evidence_uses_exact_public_schema_and_topology_key(self):
        dispatch = {
            "schema": "s20plus_g986n_routine_action_result_v1",
            "version": "s20plus-g986n-routine-actions-v1",
            "action": "enter-download",
            "verdict": "DISPATCHED_S20PLUS_G986N_DOWNLOAD_ENTRY_PENDING",
            "effect_command_count": 1,
            "other_target_command_count": 0,
            "s22plus_command_count": 0,
            "a90_command_count": 0,
            "target": {"model": MODULE.EXPECTED_MODEL, "device": MODULE.EXPECTED_DEVICE, "product": MODULE.EXPECTED_PRODUCT, "incremental": MODULE.EXPECTED_INCREMENTAL, "usb_topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256},
            "verification": {"replay_permitted": False},
        }
        resolution = {"schema": "s20plus_g986n_control_resolution_v1", "version": "s20plus-g986n-routine-actions-v1", "action": "enter-download", "resolution": "download-observed"}
        with tempfile.TemporaryDirectory() as temporary:
            result_path = Path(temporary) / "result.json"
            resolution_path = Path(temporary) / "resolution.json"
            result_path.write_text(json.dumps(dispatch))
            resolution_path.write_text(json.dumps(resolution))
            patches = (
                mock.patch.object(MODULE, "TRANSITION_RESULT", result_path),
                mock.patch.object(MODULE, "TRANSITION_RESULT_SIZE", result_path.stat().st_size),
                mock.patch.object(MODULE, "TRANSITION_RESULT_SHA256", MODULE.sha256_file(result_path)),
                mock.patch.object(MODULE, "TRANSITION_RESOLUTION", resolution_path),
                mock.patch.object(MODULE, "TRANSITION_RESOLUTION_SIZE", resolution_path.stat().st_size),
                mock.patch.object(MODULE, "TRANSITION_RESOLUTION_SHA256", MODULE.sha256_file(resolution_path)),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
                MODULE.validate_transition_evidence()
                dispatch["target"]["topology_sha256"] = dispatch["target"].pop("usb_topology_sha256")
                result_path.write_text(json.dumps(dispatch))
                with mock.patch.object(MODULE, "TRANSITION_RESULT_SIZE", result_path.stat().st_size), mock.patch.object(MODULE, "TRANSITION_RESULT_SHA256", MODULE.sha256_file(result_path)):
                    with self.assertRaisesRegex(MODULE.BootstrapError, "not exact"):
                        MODULE.validate_transition_evidence()

    def test_download_rejects_wrong_topology_usb_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            node = self.make_sysfs(root)
            (node / "idProduct").write_text("6860\n")
            command = lambda argv, timeout, maximum: (0, b"/dev/bus/usb/003/007\n", b"")
            with self.assertRaises(MODULE.BootstrapError):
                MODULE.identify_download(command, sys_root=root, stat_reader=lambda path: (1, 2, 3, 4))
            ambiguous = lambda argv, timeout, maximum: (0, b"/dev/bus/usb/003/007\n/dev/bus/usb/003/008\n", b"")
            with self.assertRaises(MODULE.BootstrapError):
                MODULE.identify_download(ambiguous, sys_root=root, stat_reader=lambda path: (1, 2, 3, 4))

    def test_transfer_intent_blocks_candidate_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            MODULE.durable_create(run / "candidate-intent.json", {"attempt": 1})
            prepared = {"approval_token": "token"}
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared):
                with self.assertRaisesRegex(MODULE.BootstrapError, "replay"):
                    MODULE.execute(run, "token", lambda argv, timeout, maximum: (0, b"", b""))

    def test_raw_transfer_evidence_is_exclusive_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "raw"
            MODULE.durable_bytes(path, b"evidence")
            self.assertEqual(path.read_bytes(), b"evidence")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
            with self.assertRaises(FileExistsError):
                MODULE.durable_bytes(path, b"replacement")
            with self.assertRaises(MODULE.BootstrapError):
                MODULE.durable_bytes(Path(temporary) / "large", b"x" * (MODULE.MAX_OUTPUT + 1))

    def test_guard_is_exact_and_cannot_clear_another_run(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "ROOT", Path(temporary)):
            run = Path(temporary) / MODULE.RUN_ROOT / "run-a"
            run.mkdir(parents=True)
            MODULE.guard_path().parent.mkdir(parents=True)
            MODULE.durable_create(MODULE.guard_path(), {
                "schema": "s20plus_g986n_magisk_bootstrap_guard_v1",
                "version": MODULE.VERSION,
                "run_dir": str(run),
                "unresolved": True,
            })
            MODULE.read_guard(run)
            with self.assertRaisesRegex(MODULE.BootstrapError, "does not match"):
                MODULE.release_guard(run.parent / "run-b")
            self.assertTrue(MODULE.guard_path().exists())

    def test_prepare_is_host_bound_and_creates_exact_shared_guard(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "ROOT", Path(temporary)), mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "validate_artifacts", return_value={"candidate": "exact"}), mock.patch.object(MODULE, "validate_transition_evidence", return_value={"transition": "exact"}), mock.patch.object(MODULE, "closure_receipts", return_value={"runner": "exact"}), mock.patch.object(MODULE, "identify_download", return_value={"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4]}):
            (Path(temporary) / MODULE.RUN_ROOT).mkdir(parents=True)
            MODULE.guard_path().parent.mkdir(parents=True)
            run = MODULE.prepare(None)
            prepared = json.loads((run / "prepared.json").read_text())
            self.assertEqual(prepared["approval_token"], MODULE.APPROVAL_PREFIX + prepared["binding_sha256"])
            self.assertEqual(json.loads(MODULE.guard_path().read_text())["run_dir"], str(run))
            self.assertFalse((run / "candidate-intent.json").exists())
            with self.assertRaisesRegex(MODULE.BootstrapError, "remains unresolved"):
                MODULE.prepare(None)

    def test_recover_refuses_malformed_uncertain_rollback_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-intent.json").write_text("{}")
            (run / "rollback-intent.json").write_text("{}")
            with mock.patch.object(MODULE, "read_prepared", return_value={"binding_sha256": "binding"}):
                with self.assertRaisesRegex(MODULE.BootstrapError, "malformed or mismatched"):
                    MODULE.recover(run)

    def test_forged_rollback_completion_cannot_clear_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "rollback-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_intent_v1",
                "version": MODULE.VERSION,
                "kind": "rollback",
                "binding_sha256": "binding",
                "ap_sha256": MODULE.ROLLBACK_SHA256,
                "endpoint": {"device": "/dev/bus/usb/003/007", "identity": [1, 2, 3, 4]},
                "attempt": 1,
                "no_replay": True,
                "at": "fixed",
            }))
            (run / "rollback-result.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_v1",
                "version": MODULE.VERSION,
                "kind": "rollback",
                "classification": "odin_transfer_completed",
                "receipt": {"label": "candidate", "returncode": 0},
            }))
            with self.assertRaisesRegex(MODULE.BootstrapError, "raw transfer evidence is missing"):
                MODULE.completed_transfer_result(run, "rollback", "binding")

    def test_streaming_output_bound_is_enforced_during_execution(self):
        with self.assertRaisesRegex(MODULE.BootstrapError, "while running"):
            MODULE.streaming_command(["/usr/bin/python3", "-c", "import sys; sys.stdout.buffer.write(b'x'*2000000)"], 10, 1024)

    def test_reviewed_normalized_runner_identity_is_enforced(self):
        receipts = MODULE.closure_receipts()
        self.assertEqual(receipts["runner"]["normalized_sha256"], MODULE.EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256)
        with mock.patch.object(MODULE, "EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256", "0" * 64):
            with self.assertRaisesRegex(MODULE.BootstrapError, "reviewed normalized identity"):
                MODULE.closure_receipts()

    def test_odin_dispatch_checks_endpoint_pre_and_marks_post_change_unknown(self):
        class Pinned:
            def __init__(self, path, sha):
                self.path = path
                self.sha = sha
            def receipt(self):
                return {"path": str(self.path), "size": 1, "sha256": self.sha}

        @contextlib.contextmanager
        def pinned_regular(*args, **kwargs):
            yield Pinned(MODULE.ODIN, MODULE.ODIN_SHA256)

        @contextlib.contextmanager
        def pinned_ap(*args, **kwargs):
            yield Pinned(MODULE.CANDIDATE, MODULE.CANDIDATE_SHA256)

        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4]}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE.transport, "pin_regular_file", pinned_regular), mock.patch.object(MODULE.transport, "pin_boot_only_ap", pinned_ap), mock.patch.object(MODULE.transport, "revalidate_pinned_path"), mock.patch.object(MODULE, "streaming_command", return_value=(0, b"Setup Connection Upload Binaries boot.img.lz4 100% Close Connection", b"")), mock.patch.object(MODULE, "endpoint_stat", side_effect=[(1, 2, 3, 4), (9, 9, 9, 9)]):
            receipt, stdout, stderr = MODULE.execute_odin_exact(MODULE.CANDIDATE, MODULE.CANDIDATE_SIZE, MODULE.CANDIDATE_SHA256, "candidate", endpoint)
            classification = MODULE.persist_transfer(Path(temporary), "candidate", "binding", endpoint, (receipt, stdout, stderr))
            self.assertEqual(receipt["endpoint_post_state"], "changed")
            self.assertEqual(classification, "odin_device_session_failure_or_unknown")

    def test_rollback_mode_intent_is_bound_to_fresh_android_identity(self):
        source = SCRIPT.read_text()
        for required in ("binding_sha256", "serial_sha256", "topology_sha256", "boot_id_sha256", "enter-download-for-stock-rollback"):
            self.assertIn(required, source)

    def test_final_health_rejects_offline_malformed_and_identity_drift(self):
        selected = {"serial": "SERIAL"}
        values = {"boot_id": "boot-b"}
        identity = {"serial_sha256": "s", "topology_sha256": "t", "boot_id_sha256": MODULE.base.sha256_text("boot-b")}
        with mock.patch.object(MODULE, "wait_android", return_value=(selected, values, identity)):
            offline = MODULE.final_stock_health(lambda argv, timeout, maximum: (1, b"", b"error: device offline"), "/adb", MODULE.base.sha256_text("boot-a"))
            malformed = MODULE.final_stock_health(lambda argv, timeout, maximum: (127, b"\xff", b""), "/adb", MODULE.base.sha256_text("boot-a"))
        self.assertFalse(offline["healthy"])
        self.assertIsNone(offline["root_absent"])
        self.assertFalse(malformed["healthy"])
        with mock.patch.object(MODULE, "wait_android", return_value=(selected, values, identity)), mock.patch.object(MODULE, "android_health_once", return_value=(selected, values, {**identity, "boot_id_sha256": "changed"})):
            drift = MODULE.final_stock_health(lambda argv, timeout, maximum: (127, b"", b"/system/bin/sh: su: not found\n"), "/adb", MODULE.base.sha256_text("boot-a"))
        self.assertFalse(drift["healthy"])
        self.assertEqual(drift["reason"], "post-root-probe-identity-drift")

    def test_final_health_accepts_only_exact_root_absence_and_stable_identity(self):
        selected = {"serial": "SERIAL"}
        values = {"boot_id": "boot-b"}
        identity = {"serial_sha256": "s", "topology_sha256": "t", "boot_id_sha256": MODULE.base.sha256_text("boot-b")}
        with mock.patch.object(MODULE, "wait_android", return_value=(selected, values, identity)), mock.patch.object(MODULE, "android_health_once", return_value=(selected, values, identity)):
            health = MODULE.final_stock_health(lambda argv, timeout, maximum: (127, b"", b"/system/bin/sh: su: not found\n"), "/adb", MODULE.base.sha256_text("boot-a"))
        self.assertTrue(health["healthy"])
        self.assertTrue(health["root_absent"])

    def test_final_health_rejects_contradictory_and_trailing_absence_output(self):
        selected = {"serial": "SERIAL"}
        values = {"boot_id": "boot-b"}
        identity = {"serial_sha256": "s", "topology_sha256": "t", "boot_id_sha256": MODULE.base.sha256_text("boot-b")}
        cases = [
            (127, b"uid=0(root) gid=0(root)\n", b"/system/bin/sh: su: not found\n"),
            (127, b"", b"/system/bin/sh: su: not found\ntrailing\n"),
            (126, b"", b"/system/bin/sh: su: permission denied\n"),
        ]
        for response in cases:
            with self.subTest(response=response), mock.patch.object(MODULE, "wait_android", return_value=(selected, values, identity)):
                health = MODULE.final_stock_health(lambda argv, timeout, maximum, value=response: value, "/adb", MODULE.base.sha256_text("boot-a"))
                self.assertFalse(health["healthy"])

    def test_root_observer_timeout_closes_as_no_proof(self):
        identity = {"serial_sha256": "s", "topology_sha256": "t", "boot_id_sha256": "b"}
        with mock.patch.object(MODULE, "android_health_once", return_value=({"serial": "SERIAL"}, {}, identity)):
            result = MODULE.root_observation(lambda argv, timeout, maximum: (_ for _ in ()).throw(TimeoutError("timeout")), "/adb", identity)
        self.assertFalse(result["root_verified"])
        self.assertTrue(result["observer_uncertain"])

    def test_rollback_mode_dispatch_exception_is_durable_and_passive_observation_can_continue(self):
        identity = {"serial_sha256": "s", "topology_sha256": "t", "boot_id_sha256": "b"}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "android_health_once", return_value=({"serial": "SERIAL"}, {}, identity)):
            run = Path(temporary)
            outcome = MODULE.request_rollback_download(run, lambda argv, timeout, maximum: (_ for _ in ()).throw(TimeoutError("timeout")), "/adb", "binding", identity)
            self.assertFalse(outcome)
            result = json.loads((run / "rollback-mode-result.json").read_text())
            self.assertEqual(result["outcome"], "uncertain")
            self.assertFalse(result["replay_permitted"])
            self.assertTrue((run / "rollback-mode-intent.json").exists())

    def test_execute_observer_uncertainty_still_reaches_one_mandatory_rollback(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4]}
        candidate_android = ({"serial": "SERIAL"}, {"boot_id": "boot-b"}, {"serial_sha256": "s", "topology_sha256": "t", "boot_id_sha256": MODULE.base.sha256_text("boot-b")})
        prepared = {"approval_token": "approval", "binding_sha256": "binding", "binding": {"endpoint": endpoint}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_artifacts"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "identify_download", return_value=endpoint), mock.patch.object(MODULE, "transfer_once", side_effect=["odin_transfer_completed", "odin_transfer_completed"]) as transfers, mock.patch.object(MODULE, "wait_android", return_value=candidate_android), mock.patch.object(MODULE, "root_observation", return_value={"root_verified": False, "observer_uncertain": True, "attempts": 1}), mock.patch.object(MODULE, "request_rollback_download", return_value=False) as dispatch, mock.patch.object(MODULE, "wait_download", return_value=endpoint) as download, mock.patch.object(MODULE, "completed_transfer_result"), mock.patch.object(MODULE, "final_stock_health", return_value={"healthy": True, "root_absent": True}), mock.patch.object(MODULE, "release_guard"):
                result = MODULE.execute(run, "approval")
            self.assertEqual(result["verdict"], "NO_PROOF_S20PLUS_G986N_CANDIDATE_STOCK_ROLLBACK_HEALTHY")
            self.assertEqual(transfers.call_count, 2)
            self.assertEqual(transfers.call_args_list[0].args[1], "candidate")
            self.assertEqual(transfers.call_args_list[1].args[1], "rollback")
            dispatch.assert_called_once()
            download.assert_called_once()

    def test_source_is_boot_only_one_attempt_and_stock_terminal(self):
        source = SCRIPT.read_text()
        self.assertIn(MODULE.CANDIDATE_SHA256, source)
        self.assertIn(MODULE.ROLLBACK_SHA256, source)
        self.assertIn("candidate_attempts\": 1", source)
        self.assertIn("rollback_attempts\": 1", source)
        for forbidden in ("recovery.img", "dtbo.img", "vbmeta.img", "super.img", "persist.img", "fastboot", "/dev/block"):
            self.assertNotIn(forbidden, source)

    def test_documents_bind_exact_active_f1_and_one_registry_row(self):
        contract = (ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md").read_text()
        registry = (ROOT / "AGENTS.md").read_text()
        report = (ROOT / "docs/reports/S20PLUS_G986N_MAGISK_BOOTSTRAP_F1_H0_2026-08-13.md").read_text()
        self.assertIn("Status: **BINDING - ATTENDED ONE-SHOT BOOT-ONLY F1 ACTIVE**", contract)
        self.assertIn("State: **PASS_GO - EXACT CAPABILITY ACTIVE - NO RUN APPROVAL**", report)
        row = "| Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `G986NKSS8IYC2`) | `GOAL_S20PLUS.md` | `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md` | Active exact-target routine D0/D1 plus attended one-shot boot-only Magisk candidate and mandatory stock rollback F1; no resident-root authority |"
        self.assertEqual(registry.count(row), 1)
        for document in (contract, report):
            self.assertIn("211e001c492930c4490405ace09a6203980bf4092d276dcd018171624a16e887", document)
        self.assertIn("S22+", contract)
        self.assertIn("A90", contract)


if __name__ == "__main__":
    unittest.main()
