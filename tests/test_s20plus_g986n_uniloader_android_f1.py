"""Tests for the S20+ UniLoader F1 additions; all device interfaces are fake."""

import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_uniloader_android_f1 as owner

MARKER_SPEC = importlib.util.spec_from_file_location("marker_fixture", owner.MARKER_SOURCE)
MARKER = importlib.util.module_from_spec(MARKER_SPEC)
MARKER_SPEC.loader.exec_module(MARKER)
BOOT = "12345678-1234-4123-8123-123456789abc"
BOOT_SHA = hashlib.sha256(BOOT.encode()).hexdigest()
MARKER_VALUE = "a" * 64
MATCH = (0, f"boot_id={BOOT}\n{MARKER_VALUE}\0".encode(), b"")
ABSENT = (44, f"boot_id={BOOT}\n".encode(), b"")
HEALTH = {"serial_sha256": "b" * 64, "topology_sha256": "c" * 64, "boot_id_sha256": BOOT_SHA}
PREFLIGHT = {**HEALTH, "boot_id_sha256": "d" * 64}
PREPARED = {"binding_sha256": "e" * 64, "binding": {"preflight": PREFLIGHT}}
PAIR = {"marker": {"sha256_with_nul": MARKER.marker_digest(MARKER_VALUE)}}


class UniLoaderOwnerTests(unittest.TestCase):
    def test_dormant_gate_precedes_effects(self):
        with patch.object(owner, "ACTIVE", False):
            with self.assertRaisesRegex(owner.Stop, "NOT_ACTIVE"):
                owner.require_active()

    def test_runtime_substitutes_owner_and_current_registry_only(self):
        original = owner.P0.read_bytes()
        transformed = owner.retained_runtime_source()
        self.assertEqual(hashlib.sha256(original).hexdigest(), owner.P0_SHA)
        self.assertIn(b'if __name__ == "_s20plus_g986n_uniloader_runtime":', transformed)
        self.assertIn(b"REGISTRY_SIZE = 60_232", transformed)
        self.assertEqual(original.count(b'if __name__ == "_s20plus_g986n_p1_pid1_runtime":'), 1)
        self.assertIn(b"\nP0_F1_ACTIVE = False\n", transformed)
        self.assertNotIn(b"\nP0_F1_ACTIVE = True\n", transformed)

    def test_recovery_authority_ignores_registry_lifecycle_only(self):
        before = b"Permanent rule\n| Samsung Galaxy X | goal | target | dormant |\n"
        self.assertEqual(owner.common_authority(before),
                         owner.common_authority(before.replace(b"dormant", b"active")))
        self.assertNotEqual(owner.common_authority(before),
                            owner.common_authority(before.replace(b"Permanent rule", b"Changed")))
        self.assertNotEqual(owner.common_authority(before),
                            owner.common_authority(before.replace(b" target ", b" other ")))

    def test_namespace_accepts_inherited_compact_guard_and_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            run = base / "run-1234567890123456789"
            run.mkdir()
            guard = base / "active-action.json"
            guard.write_bytes(
                ('{"candidate_sha256":"fixed","run_dir":"' + str(run) + '",'
                 '"schema":"s20plus_g986n_boot_recovery_canary_b0_guard_v1",'
                 '"unresolved":true,"version":"' + owner.PROFILE + '"}\n').encode())
            guard.chmod(0o400)
            intent = run / "p0-candidate-cage-0001-prepare.json"
            intent.write_bytes(
                b'{"generation":1,"host_boot_id_sha256":"other-boot","kind":"candidate",'
                b'"schema":"s20plus_g986n_p0_process_cage_prepare_v1","version":'
                + b'"' + owner.PROFILE.encode() + b'"}\n')
            intent.chmod(0o400)
            with (patch.object(owner, "GUARD", guard),
                  patch.object(owner, "RUN_ROOT", base),
                  patch.object(owner, "read_pair", return_value={"candidate": {"ap": {"sha256": "fixed"}}})):
                self.assertEqual(owner.recovery_cgroup_mounts(run), set())
            with self.assertRaisesRegex(owner.Stop, "not canonical"):
                owner.strict_private(guard)

    def test_marker_requires_clean_root_and_same_boot(self):
        run = Path("/fake-run")
        engine = Mock()
        engine.read_json.side_effect = lambda path, _label: (
            {} if path.name == "candidate-observation.json" else owner.phase_intent(
                run, "candidate", HEALTH, PREPARED))
        with (patch.object(owner, "engine", engine, create=True),
              patch.object(owner, "marker", MARKER, create=True),
              patch.object(owner, "pair", PAIR, create=True),
              patch.object(owner, "validate_root") as root,
              patch.object(owner, "transfer_receipt", return_value="transfer"),
              patch.object(owner, "before_candidate_boot", return_value=BOOT_SHA) as prior_boot,
              patch.object(owner, "marker_raw", return_value=(MATCH, "raw"))):
            result = owner.marker_result(run, "candidate", HEALTH, HEALTH, PREPARED)
            self.assertEqual(result["marker_status"], "MATCH")
            self.assertEqual(root.call_count, 2)
            prior_boot.assert_not_called()
            changed = {**HEALTH, "boot_id_sha256": "9" * 64}
            result = owner.marker_result(run, "candidate", HEALTH, changed, PREPARED)
            self.assertEqual(result["marker_status"], "HEALTH_BINDING_CHANGED")

    def test_root_with_returncode_zero_and_truncated_output_fails(self):
        engine = Mock()
        healthy = {"root_capture": {"path": "/fake-run/root.capture.json"}}
        with patch.object(owner, "engine", engine, create=True):
            for field, value in (("timed_out", True), ("output_exceeded", True),
                                 ("producer_error_type", "OSError")):
                flags = {"returncode": 0, "timed_out": False, "output_exceeded": False,
                         "producer_error_type": None}
                flags[field] = value
                engine.raw_capture.load_handle.return_value = SimpleNamespace(**flags)
                with self.assertRaisesRegex(owner.Stop, "root capture producer failed"):
                    owner.validate_root(Path("/fake-run"), healthy, "root")

    def test_interrupted_marker_is_never_dispatched_again(self):
        engine = Mock()
        with (tempfile.TemporaryDirectory() as directory,
              patch.object(owner, "engine", engine, create=True)):
            run = Path(directory)
            (run / owner.phase_files("final")[2]).touch()
            with self.assertRaisesRegex(owner.Stop, "interrupted"):
                owner.acquire_marker(run, "final", HEALTH, "exact-serial", PREPARED)
            engine.raw_capture.acquire_command.assert_not_called()

    def test_bad_root_capture_never_consumes_marker_intent(self):
        engine = Mock()
        with (tempfile.TemporaryDirectory() as directory,
              patch.object(owner, "engine", engine, create=True),
              patch.object(owner, "validate_root", side_effect=owner.Stop("root capture failed"))):
            with self.assertRaisesRegex(owner.Stop, "root capture failed"):
                owner.acquire_marker(Path(directory), "candidate", HEALTH, "exact", PREPARED)
            engine.durable_json.assert_not_called()
            engine.raw_capture.acquire_command.assert_not_called()

    def test_marker_raw_order_accepts_cut_but_rejects_unowned_evidence(self):
        name, after, intent, evidence = owner.phase_files("candidate")
        prior = {"candidate-observation-intent.json", intent}
        owner.require_marker_capture_order("candidate", prior | {name + ".stdout"})
        with self.assertRaisesRegex(owner.Stop, "escaped its phase"):
            owner.require_marker_capture_order("candidate", {intent})
        with self.assertRaisesRegex(owner.Stop, "lacks its durable intent"):
            owner.require_marker_capture_order("candidate", {after + ".stderr"})
        with self.assertRaisesRegex(owner.Stop, "lacks its raw inputs"):
            owner.require_marker_capture_order("candidate", prior | {evidence})

    def test_restore_transfer_and_absent_marker_gate_terminal(self):
        engine = Mock()
        final = {"rollback_transfer_completed": True, "health": HEALTH}
        with (tempfile.TemporaryDirectory() as directory,
              patch.object(owner, "engine", engine, create=True),
              patch.object(owner, "transfer_receipt") as transfer,
              patch.object(owner, "verified_marker") as verified,
              patch.object(owner, "original_publish", create=True) as publish):
            run = Path(directory)
            (run / owner.phase_files("final")[3]).touch()
            with self.assertRaisesRegex(owner.Stop, "rollback transfer unproved"):
                owner.checked_terminal(run, PREPARED, {**final, "rollback_transfer_completed": False})
            transfer.assert_not_called()
            for bad in ("MATCH", "UNAVAILABLE", "HEALTH_BINDING_CHANGED"):
                verified.return_value = {"marker_status": bad}
                with self.assertRaisesRegex(owner.Stop, "marker absence"):
                    owner.checked_terminal(run, PREPARED, final)
            publish.assert_not_called()
            verified.return_value = {"marker_status": "ABSENT"}
            owner.checked_terminal(run, PREPARED, final)
            publish.assert_called_once_with(run, PREPARED, final)

    def test_terminal_readback_rechecks_absence_before_guard_release(self):
        engine = Mock()
        engine.read_json.side_effect = [PREPARED, {"rollback_transfer_completed": True, "health": HEALTH}]
        with (tempfile.TemporaryDirectory() as directory,
              patch.object(owner, "engine", engine, create=True),
              patch.object(owner, "inherited_namespace", create=True),
              patch.object(owner, "verified_marker", return_value={"marker_status": "UNAVAILABLE"})):
            run = Path(directory)
            for name in ("candidate-intent.json", "terminal.json"):
                (run / name).touch()
            with self.assertRaisesRegex(owner.Stop, "terminal lacks proved"):
                owner.validate_namespace(run)

    def test_candidate_marker_failure_retains_observed_boot_for_recovery(self):
        with (patch.object(owner, "engine", Mock(), create=True),
              patch.object(owner, "transfer_receipt"),
              patch.object(owner, "candidate_health", return_value=(HEALTH, "exact-serial")),
              patch.object(owner, "acquire_marker", side_effect=OSError)):
            observed, serial = owner.observe_candidate(Path("/fake-run"), PREPARED)
        self.assertIsNone(serial)
        self.assertFalse(observed["transport_authorized"])
        self.assertEqual(observed["claim_verdict"], "NO_PROOF")
        self.assertEqual(observed["boot_id_sha256"], BOOT_SHA)


if __name__ == "__main__":
    unittest.main()
