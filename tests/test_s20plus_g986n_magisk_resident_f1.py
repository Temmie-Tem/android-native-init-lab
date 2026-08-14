import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s20plus_g986n_magisk_resident_f1.py"
import sys
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("s20_resident", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def endpoint() -> dict:
    device = "/dev/bus/usb/003/007"
    return {
        "device": device,
        "endpoint_identity": [1, 2, 3, 4],
        "endpoint_sha256": MODULE.hashlib.sha256(device.encode()).hexdigest(),
        "topology_sha256": next(iter(MODULE.bootstrap.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
        "usb": {**MODULE.bootstrap.DOWNLOAD_USB, "serial_absent": True},
    }


class S20ResidentF1Tests(unittest.TestCase):
    def prepared(self) -> dict:
        return {
            "approval_token": "approval",
            "binding_sha256": "binding",
            "binding": {
                "endpoint": endpoint(),
                "closure": {"bootstrap": {"adb": {"path": "/adb"}}},
                "transition": {"android_identity": {
                    "serial_sha256": "a" * 64,
                    "topology_sha256": MODULE.bootstrap.EXPECTED_TOPOLOGY_SHA256,
                    "boot_id_sha256": "b" * 64,
                }},
            },
        }

    def test_plan_is_active_and_closed(self):
        plan = MODULE.render_plan()
        self.assertTrue(plan["active"])
        self.assertTrue(plan["resident_root_authorized"])
        self.assertTrue(plan["factory_reset_data_loss_accepted_by_approval"])
        self.assertEqual(plan["candidate_attempts"], 1)
        self.assertEqual(plan["rollback_attempts"], 1)
        self.assertFalse(plan["candidate_replay"])
        self.assertFalse(plan["non_boot_partitions"])
        source = SCRIPT.read_text()
        for forbidden in ("--artifact", "--odin", "--adb", "--device", "--serial", "fastboot", "/dev/block", "recovery.img", "vbmeta.img"):
            self.assertNotIn(forbidden, source)

    def test_execute_sends_one_candidate_and_parks_for_factory_reset(self):
        prepared = self.prepared()
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "events").mkdir()
            observation = {"schema": "s20plus_g986n_f1_candidate_observation_v1", "version": MODULE.bootstrap.VERSION, "classification": "odin_transfer_completed", "android_returned": False, "boot_id_sha256": None, "root_verified": False, "attempts": 0}
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE, "candidate_manifest_files", return_value=set()), mock.patch.object(MODULE.bootstrap, "identify_download", return_value=endpoint()), mock.patch.object(MODULE.bootstrap, "transfer_once", return_value="odin_transfer_completed") as transfer, mock.patch.object(MODULE.bootstrap, "wait_android", return_value=None), mock.patch.object(MODULE, "validated_candidate_observation", return_value=({"classification": "odin_transfer_completed"}, observation)):
                result = MODULE.execute(run, "approval")
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_FACTORY_RESET_REQUIRED")
            transfer.assert_called_once_with(run, "candidate", endpoint(), 1, "binding")
            self.assertFalse((run / "rollback-intent.json").exists())
            self.assertFalse(result["candidate_replay_permitted"])

    def test_execute_rejects_wrong_approval_and_changed_endpoint(self):
        prepared = self.prepared()
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE.bootstrap, "transfer_once") as transfer:
            run = Path(temporary)
            with self.assertRaisesRegex(MODULE.ResidentError, "approval"):
                MODULE.execute(run, "wrong")
            changed = {**endpoint(), "endpoint_identity": [1, 9, 3, 4]}
            with mock.patch.object(MODULE.bootstrap, "identify_download", return_value=changed):
                with self.assertRaisesRegex(MODULE.ResidentError, "endpoint changed"):
                    MODULE.execute(run, "approval")
            transfer.assert_not_called()

    def test_uncertain_candidate_writes_observation_and_allows_only_stock_recovery(self):
        prepared = self.prepared()
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "events").mkdir()
            observation = {"schema": "s20plus_g986n_f1_candidate_observation_v1", "version": MODULE.bootstrap.VERSION, "classification": "odin_device_session_failure_or_unknown", "android_returned": False, "boot_id_sha256": None, "root_verified": False, "attempts": 0}
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE, "candidate_manifest_files", return_value=set()), mock.patch.object(MODULE.bootstrap, "identify_download", return_value=endpoint()), mock.patch.object(MODULE.bootstrap, "transfer_once", return_value="odin_device_session_failure_or_unknown"), mock.patch.object(MODULE.bootstrap, "wait_android") as wait, mock.patch.object(MODULE, "validated_candidate_observation", return_value=({"classification": "odin_device_session_failure_or_unknown"}, observation)):
                result = MODULE.execute(run, "approval")
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_CANDIDATE_UNCERTAIN")
            observation = json.loads((run / "candidate-observation.json").read_text())
            self.assertFalse(observation["android_returned"])
            self.assertFalse(observation["root_verified"])
            wait.assert_not_called()

    def test_exact_transport_exception_evidence_remains_stock_recoverable(self):
        prepared = self.prepared()
        failure = {
            "schema": "s20plus_g986n_f1_transfer_failure_v1",
            "kind": "candidate",
            "classification": "odin_device_session_failure_or_unknown",
            "error_class": "TimeoutError",
            "possible_partition_effect": True,
        }
        observation = {
            "schema": "s20plus_g986n_f1_candidate_observation_v1",
            "version": MODULE.bootstrap.VERSION,
            "classification": "odin_device_session_failure_or_unknown",
            "android_returned": False,
            "boot_id_sha256": None,
            "root_verified": False,
            "attempts": 0,
        }
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-result.json").write_text(json.dumps(failure))
            with mock.patch.object(MODULE.bootstrap, "validate_candidate_for_physical_handoff", side_effect=MODULE.bootstrap.BootstrapError("transport")), mock.patch.object(MODULE.bootstrap, "read_transfer_intent"), mock.patch.object(MODULE.bootstrap, "validate_candidate_observation_for_physical_handoff", return_value=observation):
                candidate, observed = MODULE.validated_candidate_observation(run, prepared)
            self.assertEqual(candidate, failure)
            self.assertEqual(observed, observation)

    def test_execute_rejects_candidate_replay_before_contact(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "candidate-intent.json").write_text("{}")
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=self.prepared()), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE.bootstrap, "identify_download") as identify:
                with self.assertRaisesRegex(MODULE.ResidentError, "replay forbidden"):
                    MODULE.execute(run, "approval")
            identify.assert_not_called()

    def test_immediate_root_never_releases_on_malformed_candidate_journal(self):
        identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.bootstrap.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "c" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "d" * 64}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "events").mkdir()
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=self.prepared()), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE, "candidate_manifest_files", return_value=set()), mock.patch.object(MODULE.bootstrap, "identify_download", return_value=endpoint()), mock.patch.object(MODULE.bootstrap, "transfer_once", return_value="odin_transfer_completed"), mock.patch.object(MODULE.bootstrap, "wait_android", return_value=({"serial": "SERIAL"}, {}, identity)), mock.patch.object(MODULE.bootstrap, "root_observation", return_value=root), mock.patch.object(MODULE, "validated_candidate_observation", side_effect=MODULE.ResidentError("malformed journal")), mock.patch.object(MODULE, "release_guard") as release:
                with self.assertRaisesRegex(MODULE.ResidentError, "malformed journal"):
                    MODULE.execute(run, "approval")
            release.assert_not_called()

    def test_finalize_resident_proves_root_and_releases_without_transfer(self):
        prepared = self.prepared()
        identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.bootstrap.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "c" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "d" * 64}
        pending = {
            "schema": "s20plus_g986n_magisk_resident_pending_v1",
            "version": MODULE.VERSION,
            "binding_sha256": "binding",
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_FACTORY_RESET_REQUIRED",
            "factory_reset_data_loss_accepted": True,
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "resident-pending.json").write_text(json.dumps(pending))
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "candidate_observation", return_value={"android_returned": False, "root_verified": False}), mock.patch.object(MODULE, "candidate_manifest_files", return_value=set()), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE.bootstrap, "android_health_once", return_value=({"serial": "SERIAL"}, {}, identity)), mock.patch.object(MODULE.bootstrap, "root_observation", return_value=root), mock.patch.object(MODULE, "release_guard") as release, mock.patch.object(MODULE.bootstrap, "transfer_once") as transfer:
                result = MODULE.finalize_resident(run)
            self.assertEqual(result["verdict"], "PASS_S20PLUS_G986N_MAGISK_RESIDENT_ROOT_HEALTHY")
            self.assertTrue(result["resident_root"])
            self.assertTrue(result["late_boot_finalization"])
            transfer.assert_not_called()
            release.assert_called_once_with(run)

    def test_finalize_resident_allows_pre_reset_android_without_root(self):
        prepared = self.prepared()
        identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.bootstrap.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "c" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "d" * 64}
        pending = {
            "schema": "s20plus_g986n_magisk_resident_pending_v1",
            "version": MODULE.VERSION,
            "binding_sha256": "binding",
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_FACTORY_RESET_REQUIRED",
            "factory_reset_data_loss_accepted": True,
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "resident-pending.json").write_text(json.dumps(pending))
            old_observation = {"android_returned": True, "root_verified": False, "attempts": 1, "boot_id_sha256": "e" * 64}
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "candidate_observation", return_value=old_observation), mock.patch.object(MODULE, "candidate_manifest_files", return_value=set()), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE.bootstrap, "android_health_once", return_value=({"serial": "SERIAL"}, {}, identity)), mock.patch.object(MODULE.bootstrap, "root_observation", return_value=root), mock.patch.object(MODULE, "release_guard") as release:
                result = MODULE.finalize_resident(run)
            self.assertEqual(result["verdict"], "PASS_S20PLUS_G986N_MAGISK_RESIDENT_ROOT_HEALTHY")
            release.assert_called_once_with(run)

    def test_finalize_resident_rejects_wrong_identity_or_missing_root(self):
        prepared = self.prepared()
        for identity, root in (
            ({"serial_sha256": "e" * 64, "topology_sha256": MODULE.bootstrap.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "c" * 64}, {"root_verified": True, "attempts": 1, "output_sha256": "d" * 64}),
            ({"serial_sha256": "a" * 64, "topology_sha256": MODULE.bootstrap.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "c" * 64}, {"root_verified": False, "attempts": 1}),
        ):
            with tempfile.TemporaryDirectory() as temporary:
                run = Path(temporary)
                (run / "resident-pending.json").write_text(json.dumps({
                    "schema": "s20plus_g986n_magisk_resident_pending_v1",
                    "version": MODULE.VERSION,
                    "binding_sha256": "binding",
                    "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_FACTORY_RESET_REQUIRED",
                    "factory_reset_data_loss_accepted": True,
                    "candidate_replay_permitted": False,
                    "rollback_replay_permitted": False,
                }))
                with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "candidate_observation", return_value={"android_returned": False, "root_verified": False}), mock.patch.object(MODULE, "candidate_manifest_files", return_value=set()), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE.bootstrap, "android_health_once", return_value=({"serial": "SERIAL"}, {}, identity)), mock.patch.object(MODULE.bootstrap, "root_observation", return_value=root), mock.patch.object(MODULE, "release_guard") as release:
                    with self.assertRaisesRegex(MODULE.ResidentError, "root health"):
                        MODULE.finalize_resident(run)
                release.assert_not_called()

    def test_resident_success_rejects_any_rollback_evidence(self):
        identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.bootstrap.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "c" * 64}
        root = {"root_verified": True, "attempts": 1, "output_sha256": "d" * 64}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "rollback-intent.json").write_text("{}")
            with mock.patch.object(MODULE, "candidate_manifest_files", return_value=set()), mock.patch.object(MODULE, "require_exact_run_nodes", side_effect=MODULE.ResidentError("extra terminal evidence")), mock.patch.object(MODULE, "release_guard") as release:
                with self.assertRaisesRegex(MODULE.ResidentError, "extra terminal"):
                    MODULE.write_resident_success(run, self.prepared(), identity, root, late_boot_finalization=True)
            release.assert_not_called()

    def test_pre_candidate_abort_is_android_read_only(self):
        prepared = self.prepared()
        identity = {"serial_sha256": "a" * 64, "topology_sha256": MODULE.bootstrap.EXPECTED_TOPOLOGY_SHA256, "boot_id_sha256": "c" * 64}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=prepared), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE.bootstrap, "android_health_once", return_value=({"serial": "SERIAL"}, {}, identity)), mock.patch.object(MODULE.bootstrap, "exact_root_absence_once", return_value={"returncode": 127}), mock.patch.object(MODULE, "release_guard") as release, mock.patch.object(MODULE.bootstrap, "transfer_once") as transfer:
                result = MODULE.abort_pre_candidate(run)
            self.assertEqual(result["candidate_transfer_count"], 0)
            self.assertEqual(result["rollback_transfer_count"], 0)
            transfer.assert_not_called()
            release.assert_called_once_with(run)

    def test_exact_pre_candidate_manifest_rejects_extra_or_indirect_nodes(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            for name in MODULE.PRE_CANDIDATE_FILES:
                path = run / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}")
            MODULE.require_exact_run_nodes(run, MODULE.PRE_CANDIDATE_FILES)
            (run / "candidate-endpoint-reenumeration.json").write_text("{}")
            with self.assertRaisesRegex(MODULE.ResidentError, "extra"):
                MODULE.require_exact_run_nodes(run, MODULE.PRE_CANDIDATE_FILES)

    def test_physical_recovery_arms_then_sends_only_stock_once(self):
        baseline = {"schema": "s20plus_g986n_f1_download_baseline_v1", "version": MODULE.bootstrap.VERSION, "endpoint_count": 0, "listing_sha256": "0" * 64, "at": "fixed"}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "resident-pending.json").write_text(json.dumps({
                "schema": "s20plus_g986n_magisk_resident_pending_v1",
                "version": MODULE.VERSION,
                "binding_sha256": "binding",
                "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_FACTORY_RESET_REQUIRED",
                "factory_reset_data_loss_accepted": True,
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
            }))
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=self.prepared()), mock.patch.object(MODULE, "validated_candidate_observation", return_value=({"classification": "odin_transfer_completed"}, {"android_returned": False})), mock.patch.object(MODULE, "candidate_manifest_files", return_value=set()), mock.patch.object(MODULE, "rollback_manifest_files", return_value=set()), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE.bootstrap, "download_baseline", return_value=baseline), mock.patch.object(MODULE.bootstrap, "identify_download", return_value=endpoint()), mock.patch.object(MODULE.bootstrap, "transfer_once", return_value="odin_transfer_completed") as transfer, mock.patch.object(MODULE.bootstrap, "completed_transfer_result"), mock.patch.object(MODULE.bootstrap, "final_stock_health", return_value={"healthy": True}), mock.patch.object(MODULE, "release_guard") as release:
                first = MODULE.physical_stock_rollback(run, MODULE.PHYSICAL_ROLLBACK_ARM)
                second = MODULE.physical_stock_rollback(run, MODULE.PHYSICAL_ROLLBACK_CONFIRM)
            self.assertIn("CONFIRMATION", first["verdict"])
            self.assertEqual(second["verdict"], "RECOVERED_S20PLUS_G986N_RESIDENT_TO_STOCK_HEALTHY")
            transfer.assert_called_once_with(run, "rollback", endpoint(), 4, "binding")
            release.assert_called_once_with(run)

    def test_full_unknown_rollback_result_is_durably_parked_without_replay(self):
        baseline = {"schema": "s20plus_g986n_f1_download_baseline_v1", "version": MODULE.bootstrap.VERSION, "endpoint_count": 0, "listing_sha256": "0" * 64, "at": "fixed"}
        pending = {
            "schema": "s20plus_g986n_magisk_resident_pending_v1",
            "version": MODULE.VERSION,
            "binding_sha256": "binding",
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_CANDIDATE_UNCERTAIN",
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "resident-pending.json").write_text(json.dumps(pending))
            def transfer(run_dir, kind, endpoint_value, ordinal, binding):
                (run_dir / "rollback-result.json").write_text(json.dumps({"schema": "s20plus_g986n_f1_transfer_v1"}))
                return "odin_device_session_failure_or_unknown"
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=self.prepared()), mock.patch.object(MODULE, "validated_candidate_observation", return_value=({"classification": "odin_device_session_failure_or_unknown"}, {"android_returned": False})), mock.patch.object(MODULE, "candidate_manifest_files", return_value=set()), mock.patch.object(MODULE, "rollback_manifest_files", return_value=set()), mock.patch.object(MODULE, "require_exact_run_nodes"), mock.patch.object(MODULE.bootstrap, "download_baseline", return_value=baseline), mock.patch.object(MODULE.bootstrap, "identify_download", return_value=endpoint()), mock.patch.object(MODULE.bootstrap, "transfer_once", side_effect=transfer), mock.patch.object(MODULE, "validate_full_transfer_result", return_value={"classification": "odin_device_session_failure_or_unknown"}), mock.patch.object(MODULE, "release_guard") as release:
                MODULE.physical_stock_rollback(run, MODULE.PHYSICAL_ROLLBACK_ARM)
                result = MODULE.physical_stock_rollback(run, MODULE.PHYSICAL_ROLLBACK_CONFIRM)
            self.assertEqual(result["verdict"], "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_STOCK_ROLLBACK_UNCERTAIN")
            self.assertFalse(result["rollback_replay_permitted"])
            release.assert_not_called()

    def test_forged_rollback_confirmation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "resident-rollback-confirmation.json").write_text(json.dumps({
                "schema": "s20plus_g986n_magisk_resident_rollback_confirmation_v1",
                "version": MODULE.VERSION,
                "binding_sha256": "wrong",
                "endpoint": endpoint(),
                "operator_confirmed": True,
                "no_replay": True,
                "at": "fixed",
            }))
            with self.assertRaisesRegex(MODULE.ResidentError, "malformed or mismatched"):
                MODULE.validate_rollback_confirmation(run, self.prepared(), endpoint())

    def test_finalize_stock_rejects_forged_pending_recovery_before_device_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "resident-recovery-result.json").write_text(json.dumps({
                "verdict": "RECOVERY_PENDING_S20PLUS_G986N_RESIDENT_STOCK_FACTORY_RESET_REQUIRED"
            }))
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", True), mock.patch.object(MODULE, "read_prepared", return_value=self.prepared()), mock.patch.object(MODULE, "validated_candidate_observation"), mock.patch.object(MODULE.bootstrap, "completed_transfer_result"), mock.patch.object(MODULE.bootstrap, "final_stock_health") as health, mock.patch.object(MODULE, "release_guard") as release:
                with self.assertRaisesRegex(MODULE.ResidentError, "malformed or mismatched"):
                    MODULE.finalize_stock(run)
            health.assert_not_called()
            release.assert_not_called()

    def test_fixed_artifacts_are_boot_only(self):
        self.assertEqual(MODULE.bootstrap.CANDIDATE_SHA256, "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2")
        self.assertEqual(MODULE.bootstrap.ROLLBACK_SHA256, "48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b")
        source = SCRIPT.read_text()
        self.assertEqual(source.count('bootstrap.transfer_once(run_dir, "candidate"'), 1)
        self.assertEqual(source.count('bootstrap.transfer_once(run_dir, "rollback"'), 1)

    def test_reviewed_dormant_identity_and_documents_match(self):
        receipt = MODULE.self_receipt()
        self.assertEqual(receipt["sha256"], "226842be1c5a32dd72e4af3f5d4e9936a2d389489ce09f1d904b56e955b99a22")
        self.assertEqual(receipt["normalized_sha256"], "d9a47bbc6627fbfc2f57ee18952c5d9524527c23978873ea541e04c7617c8fdc")
        self.assertTrue(MODULE.RESIDENT_F1_ACTIVE)
        contract = (ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md").read_text()
        goal = (ROOT / "GOAL_S20PLUS.md").read_text()
        report = (ROOT / "docs/reports/S20PLUS_G986N_MAGISK_RESIDENT_F1_H0_2026-08-15.md").read_text()
        for document in (contract, goal, report):
            self.assertIn(receipt["sha256"], document)
            self.assertIn(receipt["normalized_sha256"], document)
            self.assertIn("BINDING - ACTIVE", document)

    def test_dormant_state_blocks_every_state_changing_or_closing_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            actions = (
                lambda: MODULE.prepare(None),
                lambda: MODULE.execute(run, "approval"),
                lambda: MODULE.finalize_resident(run),
                lambda: MODULE.abort_pre_candidate(run),
                lambda: MODULE.physical_stock_rollback(run, MODULE.PHYSICAL_ROLLBACK_ARM),
                lambda: MODULE.finalize_stock(run),
            )
            with mock.patch.object(MODULE, "RESIDENT_F1_ACTIVE", False):
                for action in actions:
                    with self.assertRaisesRegex(MODULE.ResidentError, "not active"):
                        action()


if __name__ == "__main__":
    unittest.main()
