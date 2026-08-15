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

    def test_endpoint_session_revision_is_active_and_cli_surface_is_closed(self):
        plan = MODULE.render_plan()
        self.assertTrue(plan["active"])
        self.assertTrue(plan["pre_candidate_abort_active"])
        self.assertFalse(plan["live_flash_authorized"])
        self.assertFalse(plan["candidate_replay"])
        self.assertTrue(plan["rollback"]["mandatory"])
        options = MODULE.main.__code__.co_consts
        source = SCRIPT.read_text()
        for forbidden in ("--artifact", "--odin", "--device", "--adb", "--serial"):
            self.assertNotIn(forbidden, source)
        self.assertIn("--confirm-rollback-mode", source)
        self.assertIn("--confirm-candidate-endpoint", source)
        self.assertIn("--abort-pre-candidate", source)
        self.assertIn("--close-pre-candidate", source)
        self.assertIn("--close-endpoint-uncertain", source)
        self.assertIn(MODULE.PHYSICAL_ROLLBACK_ARM, source)
        self.assertIn(MODULE.PHYSICAL_ROLLBACK_CONFIRM, source)
        self.assertIn(MODULE.CANDIDATE_ENDPOINT_CONFIRM, source)

    def test_pre_candidate_abort_closes_healthy_android_without_odin(self):
        prepared_identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "b" * 64}
        current_identity = {**prepared_identity, "boot_id_sha256": "c" * 64}
        prepared = {"binding_sha256": "binding", "binding": {"transition": {"android_identity": prepared_identity}}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            android = ({"serial": "SERIAL"}, {}, current_identity)
            with mock.patch.object(MODULE, "PRE_CANDIDATE_ABORT_ACTIVE", True), mock.patch.object(MODULE, "read_prepared_for_pre_candidate_abort", return_value=prepared), mock.patch.object(MODULE, "validate_pre_candidate_abort_state"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "android_health_once", return_value=android), mock.patch.object(MODULE, "wait_android", return_value=android), mock.patch.object(MODULE, "identify_download") as identify, mock.patch.object(MODULE, "release_guard") as release:
                result = MODULE.abort_pre_candidate(run, lambda *_: (_ for _ in ()).throw(AssertionError("Odin must not run")))
            self.assertEqual(result["verdict"], "PASS_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTHY")
            self.assertEqual(result["partition_transfer_count"], 0)
            self.assertFalse(result["payload_free_reboot_dispatched"])
            self.assertFalse(result["candidate_replay_permitted"])
            self.assertFalse(result["rollback_replay_permitted"])
            self.assertEqual(set(result), {"schema", "version", "binding_sha256", "verdict", "pre_candidate", "candidate_intent_absent", "rollback_intent_absent", "partition_transfer_count", "payload_free_reboot_dispatched", "android_identity", "candidate_replay_permitted", "rollback_replay_permitted", "at"})
            identify.assert_not_called()
            release.assert_called_once_with(run)

    def test_pre_candidate_abort_download_dispatch_is_payload_free_once(self):
        prepared_identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "b" * 64}
        current_identity = {**prepared_identity, "boot_id_sha256": "c" * 64}
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        prepared = {"binding_sha256": "binding", "binding": {"transition": {"android_identity": prepared_identity}, "endpoint": endpoint}}
        calls = []

        def command(argv, timeout, maximum):
            calls.append(argv)
            return 0, b"", b""

        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with mock.patch.object(MODULE, "PRE_CANDIDATE_ABORT_ACTIVE", True), mock.patch.object(MODULE, "read_prepared_for_pre_candidate_abort", return_value=prepared), mock.patch.object(MODULE, "validate_pre_candidate_abort_state"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "android_health_once", side_effect=MODULE.BootstrapError("not Android")), mock.patch.object(MODULE, "adb_rows", return_value=[]), mock.patch.object(MODULE, "require_file"), mock.patch.object(MODULE, "identify_download", return_value=endpoint), mock.patch.object(MODULE, "read_guard"), mock.patch.object(MODULE, "endpoint_stat", side_effect=[tuple(endpoint["endpoint_identity"]), FileNotFoundError()]), mock.patch.object(MODULE, "wait_android", return_value=({"serial": "SERIAL"}, {}, current_identity)), mock.patch.object(MODULE, "release_guard") as release:
                result = MODULE.abort_pre_candidate(run, command)
            self.assertEqual(calls, [[str(MODULE.ODIN), "--reboot", "-d", endpoint["device"]]])
            self.assertNotIn("-a", calls[0])
            self.assertEqual(result["partition_transfer_count"], 0)
            self.assertTrue(result["payload_free_reboot_dispatched"])
            release.assert_called_once_with(run)

    def test_pre_candidate_abort_rejects_candidate_evidence_before_device_contact(self):
        prepared = {"binding_sha256": "binding", "binding": {"transition": {"android_identity": {}}, "endpoint": {}}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "events").mkdir()
            for name in ("prepared.json", "initial-download-baseline.json", "initial-download-intent.json", "initial-download-observation.json", "initial-download-result.json", "candidate-intent.json"):
                (run / name).write_text("{}")
            (run / "events" / "00-prepared.json").write_text("{}")
            with self.assertRaisesRegex(MODULE.BootstrapError, "possible-effect"):
                MODULE.validate_pre_candidate_abort_state(run, prepared)

    def test_pre_candidate_abort_rejects_forged_prepared_event(self):
        prepared = {"binding_sha256": "binding"}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "events").mkdir()
            for name in ("prepared.json", "initial-download-baseline.json", "initial-download-intent.json", "initial-download-observation.json", "initial-download-result.json"):
                (run / name).write_text("{}")
            (run / "events" / "00-prepared.json").write_text(json.dumps({"forged": True}))
            with self.assertRaisesRegex(MODULE.BootstrapError, "prepared event"):
                MODULE.validate_pre_candidate_abort_state(run, prepared)

    def test_pre_candidate_abort_rejects_foreign_download_endpoint_without_dispatch(self):
        prepared_identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "b" * 64}
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        foreign_device = "/dev/bus/usb/003/009"
        foreign = {**endpoint, "device": foreign_device, "endpoint_identity": [9, 10, 11, 12], "endpoint_sha256": MODULE.hashlib.sha256(foreign_device.encode()).hexdigest()}
        prepared = {"binding_sha256": "binding", "binding": {"transition": {"android_identity": prepared_identity}, "endpoint": endpoint}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with mock.patch.object(MODULE, "PRE_CANDIDATE_ABORT_ACTIVE", True), mock.patch.object(MODULE, "read_prepared_for_pre_candidate_abort", return_value=prepared), mock.patch.object(MODULE, "validate_pre_candidate_abort_state"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "android_health_once", side_effect=MODULE.BootstrapError("not Android")), mock.patch.object(MODULE, "adb_rows", return_value=[]), mock.patch.object(MODULE, "require_file"), mock.patch.object(MODULE, "identify_download", return_value=foreign):
                with self.assertRaisesRegex(MODULE.BootstrapError, "continuity"):
                    MODULE.abort_pre_candidate(run, lambda *_: (_ for _ in ()).throw(AssertionError("dispatch must not run")))
            self.assertFalse((run / "pre-candidate-abort-intent.json").exists())

    def test_pre_candidate_abort_does_not_fallback_to_download_with_adb_rows(self):
        prepared = {"binding_sha256": "binding", "binding": {"transition": {"android_identity": {}}, "endpoint": {}}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with mock.patch.object(MODULE, "PRE_CANDIDATE_ABORT_ACTIVE", True), mock.patch.object(MODULE, "read_prepared_for_pre_candidate_abort", return_value=prepared), mock.patch.object(MODULE, "validate_pre_candidate_abort_state"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "android_health_once", side_effect=MODULE.BootstrapError("ambiguous Android")), mock.patch.object(MODULE, "adb_rows", return_value=[{"serial": "OTHER"}]), mock.patch.object(MODULE, "identify_download") as identify:
                with self.assertRaisesRegex(MODULE.BootstrapError, "ADB rows remain"):
                    MODULE.abort_pre_candidate(run)
            identify.assert_not_called()

    def test_pre_candidate_abort_never_dispatches_to_reenumerated_endpoint(self):
        prepared = {"binding_sha256": "binding", "binding": {"endpoint": {}}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-endpoint-reenumeration.json").write_text("{}")
            with mock.patch.object(MODULE, "validate_candidate_endpoint_reenumeration", return_value={"device": "/dev/bus/usb/003/009"}):
                with self.assertRaisesRegex(MODULE.BootstrapError, "not eligible"):
                    MODULE.expected_pre_candidate_abort_endpoint(run, prepared)

    def test_pre_candidate_abort_resume_observes_health_without_replay(self):
        prepared_identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "b" * 64}
        current_identity = {**prepared_identity, "boot_id_sha256": "c" * 64}
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        prepared = {"binding_sha256": "binding", "binding": {"transition": {"android_identity": prepared_identity}, "endpoint": endpoint}}
        intent = {"schema": "s20plus_g986n_f1_pre_candidate_abort_intent_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "action": "payload-free-normal-return", "endpoint": endpoint, "command_shape": ["odin4", "--reboot", "-d", "USBFS"], "attempt": 1, "partition_payload": False, "no_replay": True, "at": "fixed"}
        result = {"schema": "s20plus_g986n_f1_pre_candidate_abort_result_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "action": "payload-free-normal-return", "verdict": "RECOVERY_PENDING_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTH", "returncode": 0, "post_state": "absent", "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "effect_command_count": 1, "partition_transfer_count": 0, "no_replay": True, "replay_permitted": False, "at": "fixed"}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "pre-candidate-abort-intent.json").write_text(json.dumps(intent))
            (run / "pre-candidate-abort-result.json").write_text(json.dumps(result))
            (run / "pre-candidate-abort.stdout").write_bytes(b"")
            (run / "pre-candidate-abort.stderr").write_bytes(b"")
            with mock.patch.object(MODULE, "PRE_CANDIDATE_ABORT_ACTIVE", True), mock.patch.object(MODULE, "read_prepared_for_pre_candidate_abort", return_value=prepared), mock.patch.object(MODULE, "validate_pre_candidate_abort_state"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "wait_android", return_value=({"serial": "SERIAL"}, {}, current_identity)), mock.patch.object(MODULE, "identify_download") as identify, mock.patch.object(MODULE, "release_guard"):
                closed = MODULE.abort_pre_candidate(run, lambda *_: (_ for _ in ()).throw(AssertionError("dispatch must not replay")))
            self.assertEqual(closed["verdict"], "PASS_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTHY")
            identify.assert_not_called()

    def test_pre_candidate_abort_resume_rejects_forged_intent_result_binding(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        prepared = {"binding_sha256": "binding", "binding": {"transition": {"android_identity": {}}, "endpoint": endpoint}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "pre-candidate-abort-intent.json").write_text(json.dumps({"schema": "forged", "binding_sha256": "binding"}))
            (run / "pre-candidate-abort-result.json").write_text(json.dumps({"schema": "s20plus_g986n_f1_pre_candidate_abort_result_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "action": "payload-free-normal-return", "verdict": "RECOVERY_PENDING_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTH", "returncode": 0, "post_state": "absent", "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "effect_command_count": 1, "partition_transfer_count": 0, "no_replay": True, "replay_permitted": False, "at": "fixed"}))
            (run / "pre-candidate-abort.stdout").write_bytes(b"")
            (run / "pre-candidate-abort.stderr").write_bytes(b"")
            with self.assertRaisesRegex(MODULE.BootstrapError, "intent is malformed"):
                MODULE.validate_pre_candidate_abort_dispatch(run, prepared)

    def test_pre_candidate_abort_resume_rejects_success_with_zero_effect_count(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        prepared = {"binding_sha256": "binding", "binding": {"endpoint": endpoint}}
        intent = {"schema": "s20plus_g986n_f1_pre_candidate_abort_intent_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "action": "payload-free-normal-return", "endpoint": endpoint, "command_shape": ["odin4", "--reboot", "-d", "USBFS"], "attempt": 1, "partition_payload": False, "no_replay": True, "at": "fixed"}
        result = {"schema": "s20plus_g986n_f1_pre_candidate_abort_result_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "action": "payload-free-normal-return", "verdict": "RECOVERY_PENDING_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTH", "returncode": 0, "post_state": "absent", "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "effect_command_count": 0, "partition_transfer_count": 0, "no_replay": True, "replay_permitted": False, "at": "fixed"}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "pre-candidate-abort-intent.json").write_text(json.dumps(intent))
            (run / "pre-candidate-abort-result.json").write_text(json.dumps(result))
            (run / "pre-candidate-abort.stdout").write_bytes(b"")
            (run / "pre-candidate-abort.stderr").write_bytes(b"")
            with self.assertRaisesRegex(MODULE.BootstrapError, "not successful"):
                MODULE.validate_pre_candidate_abort_dispatch(run, prepared)

    def test_pre_candidate_abort_resume_rejects_boolean_numeric_fields(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        prepared = {"binding_sha256": "binding", "binding": {"endpoint": endpoint}}
        intent = {"schema": "s20plus_g986n_f1_pre_candidate_abort_intent_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "action": "payload-free-normal-return", "endpoint": endpoint, "command_shape": ["odin4", "--reboot", "-d", "USBFS"], "attempt": 1, "partition_payload": False, "no_replay": True, "at": "fixed"}
        result = {"schema": "s20plus_g986n_f1_pre_candidate_abort_result_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "action": "payload-free-normal-return", "verdict": "RECOVERY_PENDING_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTH", "returncode": False, "post_state": "absent", "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "effect_command_count": True, "partition_transfer_count": False, "no_replay": True, "replay_permitted": False, "at": "fixed"}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "pre-candidate-abort-intent.json").write_text(json.dumps(intent))
            (run / "pre-candidate-abort-result.json").write_text(json.dumps(result))
            (run / "pre-candidate-abort.stdout").write_bytes(b"")
            (run / "pre-candidate-abort.stderr").write_bytes(b"")
            with self.assertRaisesRegex(MODULE.BootstrapError, "result is malformed"):
                MODULE.validate_pre_candidate_abort_dispatch(run, prepared)

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

    def test_download_baseline_is_empty_and_listing_parser_rejects_foreign_nodes(self):
        self.assertEqual(MODULE.parse_download_listing(""), [])
        with self.assertRaisesRegex(MODULE.BootstrapError, "malformed"):
            MODULE.parse_download_listing("/dev/bus/usb/003/007 extra")
        with self.assertRaisesRegex(MODULE.BootstrapError, "not empty"):
            MODULE.download_baseline(lambda argv, timeout, maximum: (0, b"/dev/bus/usb/003/007\n", b""))

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
                if argv[-2:] == ["reboot", "download"]:
                    self.assertTrue((run / "initial-download-intent.json").exists())
                calls.append(argv)
                return 0, b"", b""

            arrival = {"baseline_listing_sha256": "0" * 64, "arrival_listing_sha256": "1" * 64, "arrival_endpoint": endpoint["device"]}
            with mock.patch.object(MODULE, "android_health_once", return_value=(selected, {}, identity)), mock.patch.object(MODULE, "exact_root_absence_once", return_value=root_absence), mock.patch.object(MODULE, "download_baseline", return_value={"schema": "s20plus_g986n_f1_download_baseline_v1", "version": MODULE.VERSION, "endpoint_count": 0, "listing_sha256": "0" * 64, "at": "fixed"}), mock.patch.object(MODULE, "wait_download_after_baseline", return_value=(endpoint, arrival)):
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
            with mock.patch.object(MODULE, "android_health_once", return_value=(selected, {}, identity)), mock.patch.object(MODULE, "exact_root_absence_once", return_value=root_absence), mock.patch.object(MODULE, "download_baseline", return_value={"schema": "s20plus_g986n_f1_download_baseline_v1", "version": MODULE.VERSION, "endpoint_count": 0, "listing_sha256": "0" * 64, "at": "fixed"}), mock.patch.object(MODULE, "wait_download_after_baseline", return_value=None):
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
        topology_sha256 = next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256))
        endpoint = {"device": "/dev/bus/usb/003/009", "endpoint_identity": [9, 9, 9, 9], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/009").hexdigest(), "topology_sha256": topology_sha256, "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        prepared_endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": topology_sha256, "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        prepared = {"approval_token": "approval", "binding_sha256": "binding", "binding": {"endpoint": prepared_endpoint}}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_artifacts"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "identify_download", return_value=endpoint), mock.patch.object(MODULE, "transfer_once") as transfer:
            result = MODULE.execute(Path(temporary), "approval")
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_S20PLUS_G986N_CANDIDATE_ENDPOINT_CONFIRMATION_REQUIRED")
        transfer.assert_not_called()

    def test_pre_candidate_close_requires_exact_named_run_and_closes_after_health(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "ROOT", Path(temporary)):
            root = Path(temporary) / MODULE.RUN_ROOT
            run = root / "run-close"
            (run / "events").mkdir(parents=True)
            for name in ("prepared.json", "initial-download-baseline.json", "initial-download-intent.json", "initial-download-observation.json", "initial-download-result.json"):
                (run / name).write_text("{}")
            (run / "events" / "00-prepared.json").write_text("{}")
            target = {"model": MODULE.EXPECTED_MODEL, "device": MODULE.EXPECTED_DEVICE, "product": MODULE.EXPECTED_PRODUCT, "incremental": MODULE.EXPECTED_INCREMENTAL, "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256}
            binding = {
                "schema": "s20plus_g986n_magisk_bootstrap_binding_v1", "version": MODULE.VERSION, "run_dir": str(run),
                "target": target, "closure": {"runner": {"sha256": MODULE.PRE_CANDIDATE_CLOSE_RUNNER_SHA256, "normalized_sha256": MODULE.PRE_CANDIDATE_CLOSE_NORMALIZED_SHA256}},
                "transition": {"android_identity": {"serial_sha256": "a", "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "b"}},
                "endpoint": {}, "candidate_attempts": 1, "rollback_attempts": 1, "rollback_mandatory": True, "candidate_replay": False,
            }
            binding_sha = MODULE.canonical_sha(binding)
            prepared = {"schema": "s20plus_g986n_magisk_bootstrap_prepared_v1", "version": MODULE.VERSION, "binding": binding, "binding_sha256": binding_sha, "approval_token": MODULE.APPROVAL_PREFIX + binding_sha, "prepared_at": "fixed"}
            prepared_path = run / "prepared.json"
            prepared_path.write_text(json.dumps(prepared))
            MODULE.guard_path().parent.mkdir(parents=True)
            MODULE.durable_create(MODULE.guard_path(), {"schema": "s20plus_g986n_magisk_bootstrap_guard_v1", "version": MODULE.VERSION, "run_dir": str(run), "unresolved": True})
            identity = {**binding["transition"]["android_identity"], "boot_id_sha256": "c" * 64}
            with mock.patch.object(MODULE, "PRE_CANDIDATE_CLOSE_BINDING_SHA256", binding_sha), mock.patch.object(MODULE, "validate_live_transition_binding"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "android_health_once", return_value=({"serial": "SERIAL"}, {}, identity)), mock.patch.object(MODULE, "exact_root_absence_once", return_value={"returncode": 127, "stdout_sha256": "a", "stderr_sha256": "b", "identity_confirmed": True}):
                path = MODULE.close_pre_candidate_transition(run, lambda argv, timeout, maximum: (0, b"", b""))
            self.assertTrue(path.exists())
            self.assertFalse(MODULE.guard_path().exists())

    def test_pre_candidate_close_rejects_any_candidate_evidence(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "ROOT", Path(temporary)):
            root = Path(temporary) / MODULE.RUN_ROOT
            run = root / "run-close"
            (run / "events").mkdir(parents=True)
            (run / "prepared.json").write_text("{}")
            (run / "candidate-intent.json").write_text("{}")
            MODULE.guard_path().parent.mkdir(parents=True)
            MODULE.durable_create(MODULE.guard_path(), {"schema": "s20plus_g986n_magisk_bootstrap_guard_v1", "version": MODULE.VERSION, "run_dir": str(run), "unresolved": True})
            with self.assertRaisesRegex(MODULE.BootstrapError, "named pre-candidate"):
                MODULE.close_pre_candidate_transition(run)
            self.assertTrue(MODULE.guard_path().exists())

    def test_endpoint_uncertain_close_requires_exact_result_and_health(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "ROOT", Path(temporary)):
            root = Path(temporary) / MODULE.RUN_ROOT
            run = root / "run-endpoint-uncertain"
            (run / "events").mkdir(parents=True)
            for name in ("initial-download-baseline.json", "initial-download-intent.json", "initial-download-observation.json", "initial-download-result.json"):
                (run / name).write_text("{}")
            (run / "events" / "00-prepared.json").write_text("{}")
            target = {"model": MODULE.EXPECTED_MODEL, "device": MODULE.EXPECTED_DEVICE, "product": MODULE.EXPECTED_PRODUCT, "incremental": MODULE.EXPECTED_INCREMENTAL, "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256}
            prepared_identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "b" * 64}
            binding = {
                "run_dir": str(run),
                "target": target,
                "closure": {"runner": {"sha256": MODULE.ENDPOINT_UNCERTAIN_CLOSE_RUNNER_SHA256, "normalized_sha256": MODULE.ENDPOINT_UNCERTAIN_CLOSE_NORMALIZED_SHA256}},
                "transition": {"android_identity": prepared_identity},
                "endpoint": {},
                "candidate_attempts": 1,
                "rollback_attempts": 1,
                "rollback_mandatory": True,
                "candidate_replay": False,
            }
            binding_sha = MODULE.canonical_sha(binding)
            prepared = {"schema": "s20plus_g986n_magisk_bootstrap_prepared_v1", "version": MODULE.VERSION, "binding": binding, "binding_sha256": binding_sha, "approval_token": MODULE.APPROVAL_PREFIX + binding_sha, "prepared_at": "fixed"}
            (run / "prepared.json").write_text(json.dumps(prepared))
            (run / "result.json").write_text(json.dumps({"schema": "s20plus_g986n_magisk_bootstrap_f1_result_v1", "version": MODULE.VERSION, "verdict": "RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_ENDPOINT_UNCERTAIN", "failure_class": "BootstrapError", "candidate_replay_permitted": False, "rollback_replay_permitted": False}))
            MODULE.guard_path().parent.mkdir(parents=True)
            MODULE.durable_create(MODULE.guard_path(), {"schema": "s20plus_g986n_magisk_bootstrap_guard_v1", "version": MODULE.VERSION, "run_dir": str(run), "unresolved": True})
            current_identity = {**prepared_identity, "boot_id_sha256": "c" * 64}
            with mock.patch.object(MODULE, "ENDPOINT_UNCERTAIN_CLOSE_BINDING_SHA256", binding_sha), mock.patch.object(MODULE, "validate_live_transition_binding"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "android_health_once", return_value=({"serial": "SERIAL"}, {}, current_identity)), mock.patch.object(MODULE, "exact_root_absence_once", return_value={"returncode": 127, "stdout_sha256": "a", "stderr_sha256": "b", "identity_confirmed": True}):
                path = MODULE.close_endpoint_uncertain_transition(run, lambda argv, timeout, maximum: (0, b"", b""))
            self.assertTrue(path.exists())
            self.assertFalse(MODULE.guard_path().exists())
            receipt = json.loads(path.read_text())
            self.assertTrue(receipt["endpoint_observation_uncertain"])
            self.assertTrue(receipt["candidate_intent_absent"])

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
        baseline = {"schema": "s20plus_g986n_f1_download_baseline_v1", "version": MODULE.VERSION, "endpoint_count": 0, "listing_sha256": "0" * 64, "at": "fixed"}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "android_health_once", return_value=({"serial": "SERIAL"}, {}, identity)), mock.patch.object(MODULE, "download_baseline", return_value=baseline):
            run = Path(temporary)
            outcome = MODULE.request_rollback_download(run, lambda argv, timeout, maximum: (_ for _ in ()).throw(TimeoutError("timeout")), "/adb", "binding", identity)
            self.assertFalse(outcome)
            result = json.loads((run / "rollback-mode-result.json").read_text())
            self.assertEqual(result["outcome"], "uncertain")
            self.assertFalse(result["replay_permitted"])
            self.assertTrue((run / "rollback-mode-intent.json").exists())

    def test_execute_observer_uncertainty_does_not_use_unbound_rollback_endpoint(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        candidate_android = ({"serial": "SERIAL"}, {"boot_id": "boot-b"}, {"serial_sha256": "s", "topology_sha256": "t", "boot_id_sha256": MODULE.base.sha256_text("boot-b")})
        prepared = {"approval_token": "approval", "binding_sha256": "binding", "binding": {"endpoint": endpoint}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_artifacts"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "identify_download", return_value=endpoint), mock.patch.object(MODULE, "transfer_once", side_effect=["odin_transfer_completed", "odin_transfer_completed"]) as transfers, mock.patch.object(MODULE, "wait_android", return_value=candidate_android), mock.patch.object(MODULE, "root_observation", return_value={"root_verified": False, "observer_uncertain": True, "attempts": 1}), mock.patch.object(MODULE, "request_rollback_download", return_value=False) as dispatch, mock.patch.object(MODULE, "wait_download", return_value=endpoint) as download, mock.patch.object(MODULE, "completed_transfer_result"), mock.patch.object(MODULE, "final_stock_health", return_value={"healthy": True, "root_absent": True}), mock.patch.object(MODULE, "release_guard"):
                result = MODULE.execute(run, "approval")
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_MODE_UNCERTAIN")
            self.assertEqual(transfers.call_count, 1)
            self.assertEqual(transfers.call_args_list[0].args[1], "candidate")
            dispatch.assert_called_once()
            download.assert_not_called()

    def test_execute_records_endpoint_reenumeration_before_candidate_transfer(self):
        endpoint_a = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        endpoint_b = {"device": "/dev/bus/usb/003/008", "endpoint_identity": [5, 6, 7, 8], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/008").hexdigest(), "topology_sha256": endpoint_a["topology_sha256"], "usb": endpoint_a["usb"]}
        prepared = {"approval_token": "approval", "binding_sha256": "binding", "binding": {"endpoint": endpoint_a}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_artifacts"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "identify_download", return_value=endpoint_b), mock.patch.object(MODULE, "transfer_once") as transfer:
                result = MODULE.execute(run, "approval")
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_S20PLUS_G986N_CANDIDATE_ENDPOINT_CONFIRMATION_REQUIRED")
            self.assertFalse(transfer.called)
            evidence = json.loads((run / "candidate-endpoint-reenumeration.json").read_text())
            self.assertTrue(evidence["topology_continuity"])
            self.assertTrue(evidence["usb_profile_continuity"])
            self.assertFalse((run / "candidate-intent.json").exists())

    def test_execute_absorbs_ctime_only_endpoint_refresh_without_second_confirmation(self):
        endpoint_a = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        endpoint_b = {**endpoint_a, "endpoint_identity": [1, 2, 3, 999]}
        prepared = {"approval_token": "approval", "binding_sha256": "binding", "binding": {"endpoint": endpoint_a}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_artifacts"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "identify_download", return_value=endpoint_b), mock.patch.object(MODULE, "transfer_once", return_value="odin_device_session_failure_or_unknown") as transfer:
                result = MODULE.execute(run, "approval")
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_S20PLUS_G986N_PHYSICAL_DOWNLOAD_REQUIRED")
            transfer.assert_called_once_with(run, "candidate", endpoint_b, 1, "binding")
            self.assertFalse((run / "candidate-endpoint-reenumeration.json").exists())

    def test_endpoint_session_equivalence_rejects_every_stable_field_drift(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        self.assertTrue(MODULE.endpoint_session_equivalent(endpoint, {**endpoint, "endpoint_identity": [1, 2, 3, 999]}))
        cases = [
            {**endpoint, "device": "/dev/bus/usb/003/008", "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/008").hexdigest()},
            {**endpoint, "endpoint_identity": [9, 2, 3, 4]},
            {**endpoint, "endpoint_identity": [1, 9, 3, 4]},
            {**endpoint, "endpoint_identity": [1, 2, 9, 4]},
            {**endpoint, "topology_sha256": next(value for value in MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256 if value != endpoint["topology_sha256"])},
            {**endpoint, "usb": {**endpoint["usb"], "product": "WRONG"}},
        ]
        for changed in cases:
            with self.subTest(changed=changed):
                if changed["usb"].get("product") == "WRONG":
                    with self.assertRaises(MODULE.BootstrapError):
                        MODULE.endpoint_session_equivalent(endpoint, changed)
                else:
                    self.assertFalse(MODULE.endpoint_session_equivalent(endpoint, changed))

    def test_candidate_endpoint_confirmation_requires_same_observed_endpoint_and_dispatches_once(self):
        endpoint_a = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        endpoint_b = {"device": "/dev/bus/usb/003/008", "endpoint_identity": [5, 6, 7, 8], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/008").hexdigest(), "topology_sha256": endpoint_a["topology_sha256"], "usb": endpoint_a["usb"]}
        prepared = {"approval_token": "approval", "binding_sha256": "binding", "binding": {"endpoint": endpoint_a}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            MODULE.record_candidate_endpoint_reenumeration(run, "binding", endpoint_a, endpoint_b)
            live_endpoint = {**endpoint_b, "endpoint_identity": [5, 6, 7, 999]}
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "identify_download", return_value=live_endpoint), mock.patch.object(MODULE, "ensure_pre_candidate_continuation"), mock.patch.object(MODULE, "validate_artifacts"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "transfer_once", return_value="odin_device_session_failure_or_unknown") as transfer:
                result = MODULE.confirm_candidate_endpoint_reenumeration(run, MODULE.CANDIDATE_ENDPOINT_CONFIRM)
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_S20PLUS_G986N_PHYSICAL_DOWNLOAD_REQUIRED")
            transfer.assert_called_once()
            self.assertTrue((run / "candidate-endpoint-confirmation.json").exists())

    def test_candidate_endpoint_confirmation_rejects_foreign_endpoint_without_transfer(self):
        endpoint_a = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        endpoint_b = {"device": "/dev/bus/usb/003/008", "endpoint_identity": [5, 6, 7, 8], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/008").hexdigest(), "topology_sha256": endpoint_a["topology_sha256"], "usb": endpoint_a["usb"]}
        endpoint_c = {"device": "/dev/bus/usb/003/009", "endpoint_identity": [9, 10, 11, 12], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/009").hexdigest(), "topology_sha256": endpoint_a["topology_sha256"], "usb": endpoint_a["usb"]}
        prepared = {"approval_token": "approval", "binding_sha256": "binding", "binding": {"endpoint": endpoint_a}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            MODULE.record_candidate_endpoint_reenumeration(run, "binding", endpoint_a, endpoint_b)
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "identify_download", return_value=endpoint_c), mock.patch.object(MODULE, "ensure_pre_candidate_continuation"), mock.patch.object(MODULE, "transfer_once") as transfer:
                with self.assertRaisesRegex(MODULE.BootstrapError, "changed after candidate confirmation"):
                    MODULE.confirm_candidate_endpoint_reenumeration(run, MODULE.CANDIDATE_ENDPOINT_CONFIRM)
            transfer.assert_not_called()
            self.assertFalse((run / "candidate-endpoint-confirmation.json").exists())

    def test_internal_confirmed_endpoint_argument_cannot_bypass_durable_confirmation(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        prepared = {"approval_token": "approval", "binding_sha256": "binding", "binding": {"endpoint": endpoint}}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "transfer_once") as transfer:
            with self.assertRaisesRegex(MODULE.BootstrapError, "confirmation"):
                MODULE.execute(Path(temporary), "approval", confirmed_endpoint=endpoint)
            transfer.assert_not_called()

    def test_compatible_continuation_rejects_followup_evidence_without_intent(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            for name in ("candidate-result.json", "candidate.stdout", "candidate-observation.json", "rollback-mode-intent.json", "rollback-result.json"):
                path = run / name
                path.write_bytes(b"{}")
                self.assertFalse(MODULE.compatible_continuation_journal_consistent(run), name)
                path.unlink()
            (run / "candidate-intent.json").write_bytes(b"{}")
            self.assertTrue(MODULE.compatible_continuation_journal_consistent(run))
            (run / "rollback-result.json").write_bytes(b"{}")
            self.assertFalse(MODULE.compatible_continuation_journal_consistent(run))
            (run / "rollback-intent.json").write_bytes(b"{}")
            self.assertTrue(MODULE.compatible_continuation_journal_consistent(run))

    def test_persisted_transfer_classifier_replays_post_state_rule_for_recovery(self):
        receipt = {"returncode": 0, "endpoint_post_state": "changed"}
        with mock.patch.object(MODULE.f1_core, "classify_odin_output", return_value="odin_transfer_completed"):
            self.assertEqual(
                MODULE.persisted_transfer_classification(receipt, b"ok", b""),
                "odin_device_session_failure_or_unknown",
            )
        receipt["endpoint_post_state"] = "absent"
        with mock.patch.object(MODULE.f1_core, "classify_odin_output", return_value="odin_transfer_completed"):
            self.assertEqual(MODULE.persisted_transfer_classification(receipt, b"ok", b""), "odin_transfer_completed")

    def test_persisted_transfer_classifier_accepts_only_ctime_identity_change(self):
        receipt = {
            "returncode": 0,
            "endpoint_post_state": "changed",
            "endpoint_pre_identity": [7, 1857, 48535, 100],
            "endpoint_post_identity": [7, 1857, 48535, 200],
        }
        with mock.patch.object(MODULE.f1_core, "classify_odin_output", return_value="odin_transfer_completed"):
            self.assertEqual(MODULE.persisted_transfer_classification(receipt, b"ok", b""), "odin_transfer_completed")
        receipt["endpoint_post_identity"][2] = 999
        with mock.patch.object(MODULE.f1_core, "classify_odin_output", return_value="odin_transfer_completed"):
            self.assertEqual(MODULE.persisted_transfer_classification(receipt, b"ok", b""), "odin_device_session_failure_or_unknown")

    def test_transfer_intent_rejects_boolean_attempt_and_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            value = {
                "schema": "s20plus_g986n_f1_transfer_intent_v1", "version": MODULE.VERSION,
                "kind": "candidate", "binding_sha256": "binding", "ap_sha256": MODULE.CANDIDATE_SHA256,
                "endpoint": {"device": "/dev/bus/usb/003/007", "identity": [1, 2, 3, 4]},
                "attempt": True, "no_replay": True, "at": "fixed",
            }
            (run / "candidate-intent.json").write_text(json.dumps(value))
            with self.assertRaisesRegex(MODULE.BootstrapError, "intent is malformed"):
                MODULE.read_transfer_intent(run, "candidate", "binding")
            value["attempt"] = 1
            value["endpoint"]["identity"][0] = True
            (run / "candidate-intent.json").write_text(json.dumps(value))
            with self.assertRaisesRegex(MODULE.BootstrapError, "intent is malformed"):
                MODULE.read_transfer_intent(run, "candidate", "binding")

    def test_completed_transfer_rejects_boolean_returncode(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "identity": [1, 2, 3, 4]}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_intent_v1", "version": MODULE.VERSION,
                "kind": "candidate", "binding_sha256": "binding", "ap_sha256": MODULE.CANDIDATE_SHA256,
                "endpoint": endpoint, "attempt": 1, "no_replay": True, "at": "fixed",
            }))
            (run / "candidate.stdout").write_bytes(b"")
            (run / "candidate.stderr").write_bytes(b"")
            receipt = {
                "label": "candidate", "returncode": False,
                "command_shape": ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"],
                "regular_path_inputs": True, "anonymous_proc_fd_inputs": False,
                "odin": {"path": str(MODULE.ODIN), "size": MODULE.ODIN_SIZE, "sha256": MODULE.ODIN_SHA256},
                "ap": {"path": str(MODULE.CANDIDATE), "size": MODULE.CANDIDATE_SIZE, "sha256": MODULE.CANDIDATE_SHA256},
                "endpoint_path_sha256": MODULE.hashlib.sha256(endpoint["device"].encode()).hexdigest(),
                "endpoint_pre_identity": endpoint["identity"], "endpoint_post_identity": endpoint["identity"],
                "endpoint_post_state": "same", "stdout_bytes": 0, "stderr_bytes": 0,
            }
            (run / "candidate-result.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_v1", "version": MODULE.VERSION,
                "kind": "candidate", "binding_sha256": "binding", "endpoint": endpoint,
                "classification": "odin_transfer_completed", "receipt": receipt,
                "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(),
                "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(),
            }))
            with mock.patch.object(MODULE.f1_core, "classify_odin_output", return_value="odin_transfer_completed"):
                with self.assertRaisesRegex(MODULE.BootstrapError, "completion evidence is malformed"):
                    MODULE.completed_transfer_result(run, "candidate", "binding")

    def test_candidate_observation_rejects_boolean_attempts(self):
        value = {
            "schema": "s20plus_g986n_f1_candidate_observation_v1", "version": MODULE.VERSION,
            "classification": "odin_transfer_completed", "android_returned": True,
            "boot_id_sha256": "a" * 64, "root_verified": True, "attempts": True,
        }
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-observation.json").write_text(json.dumps(value))
            with self.assertRaisesRegex(MODULE.BootstrapError, "observation is malformed"):
                MODULE.validate_candidate_observation_for_physical_handoff(run, {"classification": "odin_transfer_completed"})

    def test_candidate_observation_rejects_android_return_for_unknown_transfer(self):
        value = {
            "schema": "s20plus_g986n_f1_candidate_observation_v1", "version": MODULE.VERSION,
            "classification": "odin_device_session_failure_or_unknown", "android_returned": True,
            "boot_id_sha256": "a" * 64, "root_verified": True, "attempts": 1,
            "output_sha256": "b" * 64,
        }
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-observation.json").write_text(json.dumps(value))
            with self.assertRaisesRegex(MODULE.BootstrapError, "observation is malformed"):
                MODULE.validate_candidate_observation_for_physical_handoff(run, {"classification": "odin_device_session_failure_or_unknown"})

    def test_candidate_observation_requires_exact_root_proof_shape(self):
        base = {
            "schema": "s20plus_g986n_f1_candidate_observation_v1", "version": MODULE.VERSION,
            "classification": "odin_transfer_completed", "android_returned": True,
            "boot_id_sha256": "a" * 64, "root_verified": True, "attempts": 1,
        }
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-observation.json").write_text(json.dumps(base))
            with self.assertRaisesRegex(MODULE.BootstrapError, "observation is malformed"):
                MODULE.validate_candidate_observation_for_physical_handoff(run, {"classification": "odin_transfer_completed"})
            base["root_verified"] = False
            base["attempts"] = 0
            (run / "candidate-observation.json").write_text(json.dumps(base))
            with self.assertRaisesRegex(MODULE.BootstrapError, "observation is malformed"):
                MODULE.validate_candidate_observation_for_physical_handoff(run, {"classification": "odin_transfer_completed"})

    def test_rollback_mode_transition_rejects_boolean_returncode(self):
        identity = {"serial_sha256": "a" * 64, "topology_sha256": "b" * 64, "boot_id_sha256": "c" * 64}
        baseline = {"schema": "s20plus_g986n_f1_download_baseline_v1", "version": MODULE.VERSION, "endpoint_count": 0, "listing_sha256": "d" * 64, "at": "fixed"}
        intent = {"schema": "s20plus_g986n_f1_rollback_mode_intent_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "action": "enter-download-for-stock-rollback", "ordinal": 1, **identity, "baseline_sha256": MODULE.canonical_sha(baseline), "no_replay": True, "at": "fixed"}
        result = {"schema": "s20plus_g986n_f1_rollback_mode_result_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "returncode": False, "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "outcome": "dispatched", "replay_permitted": False}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "rollback-mode-baseline.json").write_text(json.dumps(baseline))
            (run / "rollback-mode-intent.json").write_text(json.dumps(intent))
            (run / "rollback-mode-result.json").write_text(json.dumps(result))
            with self.assertRaisesRegex(MODULE.BootstrapError, "transition evidence is malformed"):
                MODULE.validate_rollback_mode_transition(run, "binding", identity)

    def test_recover_late_root_proof_reaches_one_stock_rollback_without_candidate_replay(self):
        prepared_identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "b" * 64}
        candidate_identity = {**prepared_identity, "boot_id_sha256": "c" * 64}
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4]}
        prepared = {"binding_sha256": "binding", "binding": {"endpoint": endpoint, "transition": {"android_identity": prepared_identity}}}
        observation = {"schema": "s20plus_g986n_f1_candidate_observation_v1", "version": MODULE.VERSION, "classification": "odin_device_session_failure_or_unknown", "android_returned": False, "boot_id_sha256": None, "root_verified": False, "attempts": 0}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "d" * 64}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_intent_v1", "version": MODULE.VERSION,
                "kind": "candidate", "binding_sha256": "binding", "ap_sha256": MODULE.CANDIDATE_SHA256,
                "endpoint": {"device": endpoint["device"], "identity": endpoint["endpoint_identity"]},
                "attempt": 1, "no_replay": True, "at": "fixed",
            }))
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_candidate_for_physical_handoff", return_value={"classification": "odin_device_session_failure_or_unknown"}) as validate_candidate, mock.patch.object(MODULE, "validate_candidate_observation_for_physical_handoff", return_value=observation), mock.patch.object(MODULE, "validate_late_candidate_completion") as validate_late, mock.patch.object(MODULE, "observe_late_candidate_android", return_value=(candidate_identity, root)), mock.patch.object(MODULE, "ensure_recovery_continuation") as continuation, mock.patch.object(MODULE, "recover_stock_after_candidate_android", return_value={"verdict": "PASS"}) as rollback, mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}):
                result = MODULE.recover(run)
            self.assertEqual(result["verdict"], "PASS")
            validate_candidate.assert_called_once()
            validate_late.assert_called_once()
            continuation.assert_called_once_with(run, prepared)
            rollback.assert_called_once_with(run, prepared, mock.ANY, "/adb", candidate_identity, root, "odin_device_session_failure_or_unknown")

    def test_recovery_continuation_rejects_symlinked_candidate_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            target = run / "target.json"
            target.write_text("{}")
            (run / "candidate-intent.json").symlink_to(target)
            (run / "candidate-result.json").write_text("{}")
            (run / "candidate-observation.json").write_text("{}")
            prepared = {"binding_sha256": "binding", "binding": {"run_dir": str(run)}}
            closure = {"runner": {"path": str(SCRIPT), "size": 1, "sha256": "a" * 64, "normalized_sha256": "b" * 64}}
            with self.assertRaisesRegex(MODULE.BootstrapError, "candidate intent is not an exact regular file"):
                MODULE.recovery_continuation_value(prepared, closure)

    def test_late_candidate_observation_rejects_root_without_output_hash(self):
        identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "c" * 64}
        prepared = {"binding_sha256": "binding", "binding": {"transition": {"android_identity": {**identity, "boot_id_sha256": "b" * 64}}}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-result.json").write_text("{}")
            (run / "candidate-observation.json").write_text("{}")
            (run / "candidate-late-observation.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_candidate_late_observation_v1", "version": MODULE.VERSION,
                "binding_sha256": "binding",
                "candidate_result_sha256": MODULE.sha256_file(run / "candidate-result.json"),
                "candidate_observation_sha256": MODULE.sha256_file(run / "candidate-observation.json"),
                "android_identity": identity, "root_observation": {"root_verified": True, "attempts": 1},
                "candidate_replay_permitted": False, "at": "fixed",
            }))
            with self.assertRaisesRegex(MODULE.BootstrapError, "late observation is malformed"):
                MODULE.observe_late_candidate_android(run, prepared, mock.Mock(), "/adb")

    def test_late_candidate_recovery_sends_only_one_stock_transfer(self):
        identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "c" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "d" * 64}
        prepared = {"binding_sha256": "binding"}
        baseline = {"schema": "s20plus_g986n_f1_download_baseline_v1", "version": MODULE.VERSION, "endpoint_count": 0, "listing_sha256": "0" * 64, "at": "fixed"}
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with mock.patch.object(MODULE, "request_rollback_download", return_value=True) as dispatch, mock.patch.object(MODULE, "validate_rollback_mode_transition", return_value=baseline), mock.patch.object(MODULE, "wait_download_after_baseline", return_value=(endpoint, {"baseline_listing_sha256": baseline["listing_sha256"], "arrival_listing_sha256": "e" * 64, "arrival_endpoint": endpoint["device"]})), mock.patch.object(MODULE, "transfer_once", return_value="odin_transfer_completed") as transfer, mock.patch.object(MODULE, "completed_transfer_result", return_value={"classification": "odin_transfer_completed"}), mock.patch.object(MODULE, "final_stock_health", return_value={"healthy": True}), mock.patch.object(MODULE, "release_guard") as release:
                result = MODULE.recover_stock_after_candidate_android(run, prepared, mock.Mock(), "/adb", identity, root, "odin_device_session_failure_or_unknown")
            dispatch.assert_called_once()
            transfer.assert_called_once_with(run, "rollback", endpoint, 4, "binding")
            self.assertEqual(result["verdict"], "PASS_S20PLUS_G986N_MAGISK_ROOT_PROVEN_STOCK_ROLLBACK_HEALTHY")
            release.assert_called_once_with(run)

    def test_recover_does_not_transfer_to_unbound_fresh_download_endpoint(self):
        endpoint_a = {"device": "/dev/bus/usb/003/007", "identity": [1, 2, 3, 4]}
        endpoint_b = {"device": "/dev/bus/usb/003/008", "identity": [9, 8, 7, 6]}
        prepared = {"binding_sha256": "binding", "binding": {"endpoint": {"device": endpoint_a["device"], "endpoint_identity": endpoint_a["identity"]}}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_intent_v1",
                "version": MODULE.VERSION,
                "kind": "candidate",
                "binding_sha256": "binding",
                "ap_sha256": MODULE.CANDIDATE_SHA256,
                "endpoint": endpoint_a,
                "attempt": 1,
                "no_replay": True,
                "at": "fixed",
            }))
            (run / "candidate-result.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_v1",
                "version": MODULE.VERSION,
                "kind": "candidate",
                "classification": "odin_device_session_failure_or_unknown",
            }))
            (run / "candidate-observation.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_candidate_observation_v1",
                "version": MODULE.VERSION,
                "classification": "odin_device_session_failure_or_unknown",
                "android_returned": False,
                "boot_id_sha256": None,
                "root_verified": False,
                "attempts": 0,
            }))
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_candidate_for_physical_handoff", return_value={"classification": "odin_device_session_failure_or_unknown"}), mock.patch.object(MODULE, "validate_late_candidate_completion"), mock.patch.object(MODULE, "observe_late_candidate_android", side_effect=MODULE.BootstrapError("not Android")), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "wait_download", return_value={"device": endpoint_b["device"], "endpoint_identity": endpoint_b["identity"], "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}) as download, mock.patch.object(MODULE, "transfer_once") as transfer:
                result = MODULE.recover(run)
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_MODE_CONFIRMATION_REQUIRED")
            download.assert_not_called()
            transfer.assert_not_called()

    def test_recover_rejects_minimal_forged_candidate_result(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "identity": [1, 2, 3, 4]}
        prepared = {"binding_sha256": "binding", "binding": {"endpoint": {"device": endpoint["device"], "endpoint_identity": endpoint["identity"]}}}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_intent_v1", "version": MODULE.VERSION,
                "kind": "candidate", "binding_sha256": "binding", "ap_sha256": MODULE.CANDIDATE_SHA256,
                "endpoint": endpoint, "attempt": 1, "no_replay": True, "at": "fixed",
            }))
            (run / "candidate-result.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_v1", "version": MODULE.VERSION,
                "kind": "candidate", "classification": "odin_transfer_completed",
            }))
            with mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared):
                with self.assertRaisesRegex(MODULE.BootstrapError, "candidate transfer evidence is malformed"):
                    MODULE.recover(run)

    def test_unknown_candidate_result_rejects_minimal_receipt(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "identity": [1, 2, 3, 4]}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-intent.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_intent_v1", "version": MODULE.VERSION,
                "kind": "candidate", "binding_sha256": "binding", "ap_sha256": MODULE.CANDIDATE_SHA256,
                "endpoint": endpoint, "attempt": 1, "no_replay": True, "at": "fixed",
            }))
            (run / "candidate.stdout").write_bytes(b"")
            (run / "candidate.stderr").write_bytes(b"")
            (run / "candidate-result.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_transfer_v1", "version": MODULE.VERSION,
                "kind": "candidate", "binding_sha256": "binding", "endpoint": endpoint,
                "classification": "odin_device_session_failure_or_unknown",
                "receipt": {"returncode": 1, "endpoint_post_state": "same", "stdout_bytes": 0, "stderr_bytes": 0},
                "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(),
                "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(),
            }))
            with self.assertRaisesRegex(MODULE.BootstrapError, "receipt is malformed"):
                MODULE.validate_candidate_for_physical_handoff(run, "binding")

    def test_physical_rollback_handoff_requires_arm_then_confirm(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        baseline = {"schema": "s20plus_g986n_f1_download_baseline_v1", "version": MODULE.VERSION, "endpoint_count": 0, "listing_sha256": "0" * 64, "at": "fixed"}
        prepared = {"binding_sha256": "binding"}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_candidate_for_physical_handoff", return_value={"classification": "odin_device_session_failure_or_unknown"}), mock.patch.object(MODULE, "ensure_recovery_continuation"), mock.patch.object(MODULE, "download_baseline", return_value=baseline), mock.patch.object(MODULE, "identify_download", return_value=endpoint), mock.patch.object(MODULE, "transfer_once", return_value="odin_transfer_completed"), mock.patch.object(MODULE, "completed_transfer_result"), mock.patch.object(MODULE.base, "tool_receipt", return_value={"path": "/adb"}), mock.patch.object(MODULE, "final_stock_health", return_value={"healthy": True}), mock.patch.object(MODULE, "release_guard"):
            run = Path(temporary)
            (run / "candidate-observation.json").write_text(json.dumps({
                "schema": "s20plus_g986n_f1_candidate_observation_v1",
                "version": MODULE.VERSION,
                "classification": "odin_device_session_failure_or_unknown",
                "android_returned": False,
                "boot_id_sha256": None,
                "root_verified": False,
                "attempts": 0,
            }))
            first = MODULE.confirm_rollback_mode(run, MODULE.PHYSICAL_ROLLBACK_ARM)
            self.assertEqual(first["verdict"], "RECOVERY_PENDING_S20PLUS_G986N_PHYSICAL_DOWNLOAD_CONFIRMATION_REQUIRED")
            second = MODULE.confirm_rollback_mode(run, MODULE.PHYSICAL_ROLLBACK_CONFIRM)
            self.assertEqual(second["verdict"], "RECOVERED_S20PLUS_G986N_STOCK_ROLLBACK_HEALTHY")
            self.assertTrue((run / "rollback-handoff-confirmation.json").exists())

    def test_physical_handoff_rejects_symlinked_handoff_evidence(self):
        endpoint = {"device": "/dev/bus/usb/003/007", "endpoint_identity": [1, 2, 3, 4], "endpoint_sha256": MODULE.hashlib.sha256(b"/dev/bus/usb/003/007").hexdigest(), "topology_sha256": next(iter(MODULE.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)), "usb": {**MODULE.DOWNLOAD_USB, "serial_absent": True}}
        baseline = {"schema": "s20plus_g986n_f1_download_baseline_v1", "version": MODULE.VERSION, "endpoint_count": 0, "listing_sha256": "0" * 64, "at": "fixed"}
        prepared = {"binding_sha256": "binding"}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_candidate_for_physical_handoff", return_value={"classification": "odin_device_session_failure_or_unknown"}), mock.patch.object(MODULE, "ensure_recovery_continuation"), mock.patch.object(MODULE, "download_baseline", return_value=baseline), mock.patch.object(MODULE, "identify_download", return_value=endpoint) as identify:
            run = Path(temporary)
            (run / "candidate-observation.json").write_text(json.dumps({"schema": "s20plus_g986n_f1_candidate_observation_v1", "version": MODULE.VERSION, "classification": "odin_device_session_failure_or_unknown", "android_returned": False, "boot_id_sha256": None, "root_verified": False, "attempts": 0}))
            MODULE.confirm_rollback_mode(run, MODULE.PHYSICAL_ROLLBACK_ARM)
            for name in ("rollback-handoff-intent.json", "rollback-handoff-baseline.json"):
                source = run / (name + ".source")
                source.write_bytes((run / name).read_bytes())
                (run / name).unlink()
                (run / name).symlink_to(source.name)
                with self.assertRaisesRegex(MODULE.BootstrapError, "exact regular file"):
                    MODULE.confirm_rollback_mode(run, MODULE.PHYSICAL_ROLLBACK_CONFIRM)
                (run / name).unlink()
                (run / name).write_bytes(source.read_bytes())
            identify.assert_not_called()

    def test_physical_handoff_rejects_dispatched_rollback_mode_race(self):
        prepared = {"binding_sha256": "binding"}
        baseline = {"schema": "s20plus_g986n_f1_download_baseline_v1", "version": MODULE.VERSION, "endpoint_count": 0, "listing_sha256": "0" * 64, "at": "fixed"}
        intent = {"schema": "s20plus_g986n_f1_rollback_mode_intent_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "action": "enter-download-for-stock-rollback", "ordinal": 1, "serial_sha256": "a" * 64, "topology_sha256": "b" * 64, "boot_id_sha256": "c" * 64, "baseline_sha256": MODULE.canonical_sha(baseline), "no_replay": True, "at": "fixed"}
        result = {"schema": "s20plus_g986n_f1_rollback_mode_result_v1", "version": MODULE.VERSION, "binding_sha256": "binding", "returncode": 0, "stdout_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "stderr_sha256": MODULE.hashlib.sha256(b"").hexdigest(), "outcome": "dispatched", "replay_permitted": False}
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "validate_candidate_for_physical_handoff", return_value={"classification": "odin_transfer_completed"}), mock.patch.object(MODULE, "ensure_recovery_continuation"), mock.patch.object(MODULE, "identify_download") as identify:
            run = Path(temporary)
            (run / "candidate-observation.json").write_text(json.dumps({"schema": "s20plus_g986n_f1_candidate_observation_v1", "version": MODULE.VERSION, "classification": "odin_transfer_completed", "android_returned": True, "boot_id_sha256": "d" * 64, "root_verified": False, "attempts": 1}))
            (run / "rollback-mode-intent.json").write_text(json.dumps(intent))
            (run / "rollback-mode-result.json").write_text(json.dumps(result))
            (run / "rollback-mode-baseline.json").write_text(json.dumps(baseline))
            with self.assertRaisesRegex(MODULE.BootstrapError, "already dispatched"):
                MODULE.confirm_rollback_mode(run, MODULE.PHYSICAL_ROLLBACK_CONFIRM)
            identify.assert_not_called()

    def test_physical_handoff_rejects_returned_android_without_boot_identity(self):
        value = {
            "schema": "s20plus_g986n_f1_candidate_observation_v1",
            "version": MODULE.VERSION,
            "classification": "odin_transfer_completed",
            "android_returned": True,
            "boot_id_sha256": None,
            "root_verified": False,
            "attempts": 1,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "candidate-observation.json"
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(MODULE.BootstrapError, "candidate observation"):
                MODULE.validate_candidate_observation_for_physical_handoff(Path(temporary), {"classification": value["classification"]})

    def test_source_is_boot_only_one_attempt_and_stock_terminal(self):
        source = SCRIPT.read_text()
        self.assertIn(MODULE.CANDIDATE_SHA256, source)
        self.assertIn(MODULE.ROLLBACK_SHA256, source)
        self.assertIn("candidate_attempts\": 1", source)
        self.assertIn("rollback_attempts\": 1", source)
        for forbidden in ("recovery.img", "dtbo.img", "vbmeta.img", "super.img", "persist.img", "fastboot", "/dev/block"):
            self.assertNotIn(forbidden, source)

    def test_documents_activate_f1_after_endpoint_session_review(self):
        contract = (ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md").read_text()
        registry = (ROOT / "AGENTS.md").read_text()
        report = (ROOT / "docs/reports/S20PLUS_G986N_MAGISK_BOOTSTRAP_F1_H0_2026-08-13.md").read_text()
        self.assertIn("Status: **BINDING - ATTENDED BOOT-ONLY F1 ACTIVE**", contract)
        self.assertIn("Status: **PASS_GO - EXACT HOST-ONLY PRE-EFFECT ABANDON ACTIVE**", contract)
        self.assertIn("State: **PASS_GO - FIRST MAGISK ROOT PROVEN; STOCK ROLLBACK HEALTHY**", report)
        self.assertIn("Status: **BINDING - ACTIVE**", contract)
        row = "| Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `G986NKSS8IYC2`) | `GOAL_S20PLUS.md` | `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md` | Active exact-target routine D0/D1 including payload-free Download return; attended boot-only bootstrap and resident Magisk F1 active; reviewed attended native-canary R1 active |"
        self.assertEqual(registry.count(row), 1)
        self.assertIn("S22+", contract)
        self.assertIn("A90", contract)
        self.assertIn("current active correction implements the required single-session design", report)
        self.assertIn(MODULE.sha256_file(SCRIPT), report)
        self.assertIn(MODULE.EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256, report)
        self.assertIn("`F1_ACTIVE` is true", contract)


if __name__ == "__main__":
    unittest.main()
