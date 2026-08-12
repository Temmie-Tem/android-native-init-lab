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

    def test_endpoint_session_revision_is_dormant_and_cli_surface_is_closed(self):
        plan = MODULE.render_plan()
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_flash_authorized"])
        self.assertFalse(plan["candidate_replay"])
        self.assertTrue(plan["rollback"]["mandatory"])
        options = MODULE.main.__code__.co_consts
        source = SCRIPT.read_text()
        for forbidden in ("--artifact", "--odin", "--device", "--adb", "--serial"):
            self.assertNotIn(forbidden, source)

    def test_exact_download_identity_and_topology(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE, "EXPECTED_DOWNLOAD_TOPOLOGY_SHA256", frozenset({MODULE.hashlib.sha256(b"usb:3-2.1").hexdigest()})
        ):
            root = Path(temporary)
            self.make_sysfs(root)
            command = lambda argv, timeout, maximum: (0, b"/dev/bus/usb/003/007\n", b"")
            result = MODULE.identify_download(command, sys_root=root, stat_reader=lambda path: (1, 2, 3, 4))
            self.assertEqual(result["usb"]["idProduct"], "685d")
            self.assertTrue(result["usb"]["serial_absent"])

    def test_download_profile_accepts_only_observed_paired_port_and_sm8250(self):
        self.assertEqual(MODULE.DOWNLOAD_USB["product"], "SM8250")
        self.assertEqual(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256, frozenset({
            "3279d577ef7a789f8aac93664e3b45543e10522b08d29ebabc99564ca86295f1",
            "ae90de878991480bf8aafc6e131953d185245aba4fa8d9cd8d0507810d2c96e1",
        }))

    def test_live_transition_records_exact_android_intent_before_one_reboot(self):
        selected = {"serial": "SERIAL"}
        identity = {
            "serial_sha256": MODULE.base.sha256_text("SERIAL"),
            "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": MODULE.base.sha256_text("boot-id"),
        }
        endpoint = {
            "device": "/dev/bus/usb/003/007",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(),
            "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True},
        }
        root_absence = {
            "returncode": 127,
            "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(),
            "stderr_sha256": MODULE.hashlib.sha256(b"su: not found").hexdigest(),
            "identity_confirmed": True,
        }
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            calls = []

            def command(argv, timeout, maximum):
                self.assertTrue((run / "initial-download-intent.json").exists())
                calls.append(argv)
                return 0, b"", b""

            with mock.patch.object(MODULE, "android_health_once", return_value=(selected, {}, identity)), mock.patch.object(MODULE, "exact_root_absence_once", return_value=root_absence), mock.patch.object(MODULE, "wait_download", return_value=endpoint):
                transition, observed = MODULE.transition_android_to_download(run, command, "/adb")
            self.assertEqual(calls, [["/adb", "-s", "SERIAL", "reboot", "download"]])
            self.assertEqual(observed, endpoint)
            MODULE.validate_live_transition_binding(run, transition, endpoint)

    def test_live_transition_never_issues_approval_without_download_observation(self):
        selected = {"serial": "SERIAL"}
        identity = {
            "serial_sha256": MODULE.base.sha256_text("SERIAL"),
            "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": MODULE.base.sha256_text("boot-id"),
        }
        root_absence = {
            "returncode": 127,
            "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(),
            "stderr_sha256": MODULE.hashlib.sha256(b"su: not found").hexdigest(),
            "identity_confirmed": True,
        }
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            command = lambda argv, timeout, maximum: (0, b"", b"")
            with mock.patch.object(MODULE, "android_health_once", return_value=(selected, {}, identity)), mock.patch.object(MODULE, "exact_root_absence_once", return_value=root_absence), mock.patch.object(MODULE, "wait_download", return_value=None):
                with self.assertRaisesRegex(MODULE.BootstrapError, "not observed"):
                    MODULE.transition_android_to_download(run, command, "/adb")
            self.assertTrue((run / "initial-download-intent.json").exists())
            self.assertTrue((run / "initial-download-result.json").exists())
            self.assertFalse((run / "initial-download-observation.json").exists())
            self.assertFalse((run / "prepared.json").exists())

    def test_initial_root_absence_rejects_root_marker_and_identity_drift(self):
        selected = {"serial": "SERIAL"}
        identity = {
            "serial_sha256": MODULE.base.sha256_text("SERIAL"),
            "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256,
            "boot_id_sha256": MODULE.base.sha256_text("boot-a"),
        }
        rooted = lambda argv, timeout, maximum: (
            127,
            b"uid=0(root) gid=0(root)\n",
            b"/system/bin/sh: su: not found\n",
        )
        with self.assertRaisesRegex(MODULE.BootstrapError, "not exact"):
            MODULE.exact_root_absence_once(rooted, "/adb", selected, identity)

        absent = lambda argv, timeout, maximum: (
            127,
            b"",
            b"/system/bin/sh: su: inaccessible or not found\n",
        )
        with mock.patch.object(MODULE, "android_health_once", return_value=(selected, {}, identity)):
            receipt = MODULE.exact_root_absence_once(absent, "/adb", selected, identity)
        self.assertTrue(receipt["identity_confirmed"])

        drift = {**identity, "boot_id_sha256": MODULE.base.sha256_text("boot-b")}
        with mock.patch.object(MODULE, "android_health_once", return_value=(selected, {}, drift)):
            with self.assertRaisesRegex(MODULE.BootstrapError, "identity changed"):
                MODULE.exact_root_absence_once(absent, "/adb", selected, identity)

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

    def test_dormant_execute_rejects_changed_ephemeral_endpoint_identity(self):
        endpoint = {"device": "/dev/bus/usb/003/009", "endpoint_identity": [9, 9, 9, 9], "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        prepared = {"approval_token": "approval", "binding_sha256": "binding", "binding": {"endpoint": {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4]}}}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_artifacts"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "identify_download", return_value=endpoint), mock.patch.object(MODULE, "transfer_once") as transfer:
            with self.assertRaisesRegex(MODULE.BootstrapError, "endpoint changed"):
                MODULE.execute(Path(temporary), "approval")
        transfer.assert_not_called()

    def test_pre_effect_abandon_requires_exact_empty_previous_run(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "ROOT", Path(temporary)):
            run = Path(temporary) / MODULE.RUN_ROOT / "run-old"
            (run / "events").mkdir(parents=True)
            MODULE.guard_path().parent.mkdir(parents=True)
            prepared = {"binding_sha256": "binding"}
            with mock.patch.object(MODULE, "read_prepared_for_pre_effect_abandon", return_value=prepared):
                MODULE.durable_create(MODULE.guard_path(), {"schema": "s20plus_g986n_magisk_bootstrap_guard_v1", "version": MODULE.VERSION, "run_dir": str(run), "unresolved": True})
                (run / "prepared.json").write_text("{}")
                (run / "events" / "00-prepared.json").write_text(json.dumps({"schema": "s20plus_g986n_f1_event_v1", "version": MODULE.VERSION, "ordinal": 0, "name": "prepared", "at": "fixed", "binding_sha256": "binding"}))
                result = MODULE.abandon_pre_effect(run)
                self.assertTrue(result.exists())
                self.assertFalse(MODULE.guard_path().exists())

            run2 = Path(temporary) / MODULE.RUN_ROOT / "run-bad"
            (run2 / "events").mkdir(parents=True)
            (run2 / "prepared.json").write_text("{}")
            (run2 / "events" / "00-prepared.json").write_text(json.dumps({"schema": "s20plus_g986n_f1_event_v1", "version": MODULE.VERSION, "ordinal": 0, "name": "prepared", "at": "fixed", "binding_sha256": "binding"}))
            (run2 / "candidate-intent.json").write_text("{}")
            MODULE.durable_create(MODULE.guard_path(), {"schema": "s20plus_g986n_magisk_bootstrap_guard_v1", "version": MODULE.VERSION, "run_dir": str(run2), "unresolved": True})
            with mock.patch.object(MODULE, "read_prepared_for_pre_effect_abandon", return_value=prepared):
                with self.assertRaisesRegex(MODULE.BootstrapError, "possible effect"):
                    MODULE.abandon_pre_effect(run2)
            self.assertTrue(MODULE.guard_path().exists())

    def test_pre_effect_abandon_rejects_dangling_symlink_and_wrong_binding_hash(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "ROOT", Path(temporary)):
            run = Path(temporary) / MODULE.RUN_ROOT / "run-special"
            (run / "events").mkdir(parents=True)
            (run / "prepared.json").write_text("{}")
            (run / "events" / "00-prepared.json").write_text("{}")
            (run / "dangling").symlink_to("missing")
            MODULE.guard_path().parent.mkdir(parents=True)
            MODULE.durable_create(MODULE.guard_path(), {"schema": "s20plus_g986n_magisk_bootstrap_guard_v1", "version": MODULE.VERSION, "run_dir": str(run), "unresolved": True})
            with mock.patch.object(MODULE, "read_prepared_for_pre_effect_abandon", return_value={"binding_sha256": "binding"}):
                with self.assertRaisesRegex(MODULE.BootstrapError, "unexpected evidence"):
                    MODULE.abandon_pre_effect(run)
            self.assertTrue(MODULE.guard_path().exists())

        self.assertEqual(MODULE.ABANDONABLE_PREVIOUS_BINDING_SHA256, "0e299f6f05c9846cb8584aef161c109a9bdf1007a5cf642a8c9589e46255c859")

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
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4]}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "ROOT", Path(temporary)), mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "validate_artifacts", return_value={"candidate": "exact"}), mock.patch.object(MODULE, "closure_receipts", return_value={"runner": "exact", "adb": {"path": "/adb"}}), mock.patch.object(MODULE, "transition_android_to_download", return_value=({"transition": "exact"}, endpoint)):
            (Path(temporary) / MODULE.RUN_ROOT).mkdir(parents=True)
            MODULE.guard_path().parent.mkdir(parents=True)
            run = MODULE.prepare(None)
            prepared = json.loads((run / "prepared.json").read_text())
            self.assertEqual(prepared["approval_token"], MODULE.APPROVAL_PREFIX + prepared["binding_sha256"])
            self.assertEqual(json.loads(MODULE.guard_path().read_text())["run_dir"], str(run))
            self.assertFalse((run / "candidate-intent.json").exists())
            with self.assertRaisesRegex(MODULE.BootstrapError, "remains unresolved"):
                MODULE.prepare(None)

    def test_prepare_retains_guard_after_initial_download_intent(self):
        def attempted_transition(run, command, adb):
            MODULE.durable_create(run / "initial-download-intent.json", {"no_replay": True})
            raise MODULE.BootstrapError("observer unavailable")

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "ROOT", Path(temporary)), mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "validate_artifacts", return_value={"candidate": "exact"}), mock.patch.object(MODULE, "closure_receipts", return_value={"runner": "exact", "adb": {"path": "/adb"}}), mock.patch.object(MODULE, "transition_android_to_download", side_effect=attempted_transition):
            (Path(temporary) / MODULE.RUN_ROOT).mkdir(parents=True)
            MODULE.guard_path().parent.mkdir(parents=True)
            with self.assertRaisesRegex(MODULE.BootstrapError, "observer unavailable"):
                MODULE.prepare(None)
            self.assertTrue(MODULE.guard_path().exists())
            guarded_run = Path(json.loads(MODULE.guard_path().read_text())["run_dir"])
            self.assertTrue((guarded_run / "initial-download-intent.json").exists())
            self.assertFalse((guarded_run / "prepared.json").exists())

    def test_recover_refuses_malformed_uncertain_rollback_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-intent.json").write_text("{}")
            (run / "rollback-intent.json").write_text("{}")
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value={"binding_sha256": "binding"}):
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

        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
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
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
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

    def test_documents_suspend_f1_for_endpoint_session_review(self):
        contract = (ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md").read_text()
        registry = (ROOT / "AGENTS.md").read_text()
        report = (ROOT / "docs/reports/S20PLUS_G986N_MAGISK_BOOTSTRAP_F1_H0_2026-08-13.md").read_text()
        self.assertIn("Status: **H0 REVIEW PENDING - ENDPOINT SESSION CORRECTION - NO LIVE F1**", contract)
        self.assertIn("Status: **PASS_GO - EXACT HOST-ONLY PRE-EFFECT ABANDON ACTIVE**", contract)
        self.assertIn("State: **H0 REVIEW PENDING - ENDPOINT SESSION CORRECTION - NO RUN APPROVAL**", report)
        row = "| Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `G986NKSS8IYC2`) | `GOAL_S20PLUS.md` | `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md` | Active exact-target routine D0/D1; bootstrap F1 endpoint-session correction under H0 review, no active F1 |"
        self.assertEqual(registry.count(row), 1)
        self.assertIn("S22+", contract)
        self.assertIn("A90", contract)
        self.assertIn("current dormant correction implements the required single-session design", report)
        self.assertIn(MODULE.sha256_file(SCRIPT), report)
        self.assertIn(MODULE.EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256, report)
        self.assertIn("`F1_ACTIVE` remains false", contract)


if __name__ == "__main__":
    unittest.main()
