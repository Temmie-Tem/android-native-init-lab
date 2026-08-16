import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_postrollback_finalize.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p318_postrollback_finalize", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P318PostrollbackFinalizeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def _classified(self):
        return {
            "accepted": False,
            "classification": "E2_PROGRESS_OBSERVED",
            "exact_count": 0,
            "family_count": 1,
            "integrity_issue": False,
            "records": [
                {
                    "profile": "E2",
                    "fallback_used": True,
                    "header_crc_valid": True,
                    "terminal_success": False,
                    "slot_status": ["valid", "bad-body"],
                    "max77705": None,
                    "active": {
                        "generation": 46,
                        "stage": 101,
                        "outcome": 0,
                        "detail": 0,
                    },
                }
            ],
        }

    def _phase(self):
        return {
            "phase": "candidate_end",
            "authority_state": "candidate_approved_exact",
            "causal_terminal_ready": False,
            "observation_window_complete": True,
            "snapshot_capture_complete": True,
            "decision": {
                "proof_class": "NO_PROOF_OBSERVER",
                "effect": "NO_PROOF_OBSERVER_and_park",
                "relationship": "absent",
                "experiment_proof_reclassified_by_rollback": False,
            },
        }

    def test_authority_is_exact_deterministic_regeneration(self):
        authority = self.module.load_authority()
        regenerated = self.module.encode_authority(self.module.build_authority())
        self.assertEqual(regenerated, self.module.DEFAULT_AUTHORITY.read_bytes())
        self.assertEqual(
            authority["approval_token"],
            self.module.APPROVAL_PREFIX + authority["approval_binding_sha256"],
        )
        self.assertEqual(authority["binding"]["target"], self.module.TARGET)

    def test_current_incident_plan_is_host_only_and_one_shot(self):
        plan = self.module.render_plan()
        self.assertEqual(
            plan["verdict"],
            "PASS_P318_POSTROLLBACK_FINALIZE_HOST_READY_REVIEW_REQUIRED",
        )
        self.assertEqual(plan["journal_state"], "ROLLBACK_FLASHED")
        self.assertEqual(plan["candidate_transfers"], 1)
        self.assertEqual(plan["rollback_transfers"], 1)
        self.assertFalse(plan["candidate_transfer_allowed"])
        self.assertFalse(plan["rollback_transfer_allowed"])
        self.assertFalse(plan["device_contact"])
        self.assertFalse(plan["live_authorized"])
        run = self.module.DEFAULT_RUN_DIR
        self.assertFalse((run / "candidate-attempt-02.start.json").exists())
        self.assertFalse((run / "rollback-attempt-02.start.json").exists())

    def test_initial_mutable_identities_are_backed_by_immutable_snapshots(self):
        authority = self.module.load_authority()
        binding = authority["binding"]
        pairs = (
            ("live_state", "initial_live_state_snapshot"),
            ("journal_head", "initial_journal_head_snapshot"),
        )
        for mutable_name, snapshot_name in pairs:
            with self.subTest(snapshot=snapshot_name):
                snapshot = binding["immutable_inputs"][snapshot_name]
                mutable = binding["initial_mutable_inputs"][mutable_name]
                self.assertEqual(mutable["size"], snapshot["size"])
                self.assertEqual(mutable["sha256"], snapshot["sha256"])
                path = self.module._resolve(snapshot["path"], snapshot_name)
                self.assertEqual(path.stat().st_mode & 0o777, 0o400)

    def test_authority_token_and_adapter_mutations_fail_closed(self):
        authority = json.loads(self.module.DEFAULT_AUTHORITY.read_text())
        variants = []
        token = copy.deepcopy(authority)
        token["approval_token"] = self.module.APPROVAL_PREFIX + "0" * 64
        variants.append(token)
        adapter = copy.deepcopy(authority)
        adapter["binding"]["adapter"]["sha256"] = "0" * 64
        digest = self.module.live.core.json_sha256(adapter["binding"])
        adapter["approval_binding_sha256"] = digest
        adapter["approval_token"] = self.module.APPROVAL_PREFIX + digest
        variants.append(adapter)
        for value in variants:
            with self.subTest(value=value["approval_binding_sha256"]), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "authority.json"
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(self.module.FinalizeError):
                    self.module.load_authority(path)

    def test_live_rejects_noncanonical_authority_before_loading_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authority.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(
                self.module.FinalizeError, "canonical authority path"
            ):
                self.module.finalize(path, "wrong", Path("/usr/bin/adb"))

    def test_live_rejects_unbound_adb_before_incident_reopen(self):
        authority = self.module.load_authority()
        with tempfile.TemporaryDirectory() as temporary:
            fake = Path(temporary) / "adb"
            fake.write_bytes(b"not the bound adb")
            fake.chmod(0o700)
            with mock.patch.object(self.module, "verify_incident") as verify:
                with self.assertRaisesRegex(
                    self.module.FinalizeError, "ADB path differs"
                ):
                    self.module.finalize(
                        self.module.DEFAULT_AUTHORITY,
                        authority["approval_token"],
                        fake,
                    )
            verify.assert_not_called()

    def test_exact_stage101_patch_is_narrow_and_noncausal(self):
        patch = self.module.ProgressCorrelationPatch()
        result = patch.correlate(self._classified(), self._phase())
        self.assertEqual(result["host_correlation_proof_class"], "NO_PROOF_OBSERVER")
        self.assertFalse(result["causal_result_allowed"])
        self.assertFalse(
            result["p318_incomplete_terminal"]["terminal_record_present"]
        )
        mutations = []
        stage = self._classified()
        stage["records"][0]["active"]["stage"] = 100
        mutations.append((stage, self._phase()))
        causal = self._phase()
        causal["causal_terminal_ready"] = True
        mutations.append((self._classified(), causal))
        relationship = self._phase()
        relationship["decision"]["relationship"] = "same"
        mutations.append((self._classified(), relationship))
        for classified, phase in mutations:
            with self.subTest(classified=classified, phase=phase):
                with self.assertRaises(self.module.FinalizeError):
                    patch.correlate(classified, phase)

    def test_patch_installation_restores_the_exact_original(self):
        patch = self.module.ProgressCorrelationPatch()
        original = self.module.live.typed_evidence.correlate_p318_candidate_topology
        with patch.installed():
            installed = (
                self.module.live.typed_evidence.correlate_p318_candidate_topology
            )
            self.assertIs(installed.__self__, patch)
            self.assertIs(installed.__func__, patch.correlate.__func__)
        self.assertIs(
            self.module.live.typed_evidence.correlate_p318_candidate_topology,
            original,
        )

    def test_backend_has_no_download_or_transfer_path(self):
        backend = object.__new__(self.module.FinalHealthOnlyBackend)
        with self.assertRaisesRegex(self.module.FinalizeError, "cannot wait"):
            backend.wait_download()
        with self.assertRaisesRegex(self.module.FinalizeError, "cannot transfer"):
            backend.transfer()
        with backend.endpoint_session(Path("unused")) as lease:
            self.assertIsNone(lease)

    def test_arm_is_atomic_exclusive_and_idempotent(self):
        authority = self.module.load_authority()
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with mock.patch.object(self.module, "_initial_inputs_match"):
                first = self.module.arm_finalizer(authority, run)
                second = self.module.arm_finalizer(authority, run)
            self.assertEqual(first, second)
            self.assertFalse(first["candidate_transfer_allowed"])
            self.assertFalse(first["rollback_transfer_allowed"])
            arm = run / self.module.ARM_FILENAME
            value = json.loads(arm.read_text())
            value["device_writes"] = True
            arm.chmod(0o600)
            arm.write_text(json.dumps(value))
            with mock.patch.object(self.module, "_initial_inputs_match"):
                with self.assertRaisesRegex(
                    self.module.FinalizeError, "finalizer arm changed"
                ):
                    self.module.arm_finalizer(authority, run)

    def test_partial_arm_never_reaches_final_name(self):
        authority = self.module.load_authority()
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)

            def partial(path, _value, _label):
                path.write_bytes(b"partial")
                raise self.module.FinalizeError("fixture cut")

            with (
                mock.patch.object(self.module, "_initial_inputs_match"),
                mock.patch.object(
                    self.module, "_write_mode0400_exclusive", side_effect=partial
                ),
            ):
                with self.assertRaisesRegex(
                    self.module.FinalizeError, "could not be published"
                ):
                    self.module.arm_finalizer(authority, run)
            self.assertFalse((run / self.module.ARM_FILENAME).exists())
            self.assertEqual(list(run.iterdir()), [])

    def test_final_plus_temp_hardlink_cut_repairs_to_one_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            final = run / self.module.ARM_FILENAME
            temp = run / f".{final.name}.123.456.tmp"
            expected = {"schema": "fixture", "value": 1}
            self.module.live._write_exclusive(temp, expected)
            temp.chmod(0o400)
            os.link(temp, final)
            self.assertEqual(final.stat().st_nlink, 2)
            self.assertEqual(
                self.module._load_published_json(final, "fixture"), expected
            )
            self.assertFalse(temp.exists())
            self.assertEqual(final.stat().st_nlink, 1)

    def test_ambiguous_or_foreign_publication_cut_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            final = run / self.module.ARM_FILENAME
            first = run / f".{final.name}.123.456.tmp"
            second = run / f".{final.name}.124.457.tmp"
            self.module.live._write_exclusive(first, {"value": 1})
            os.link(first, final)
            second.write_text("foreign", encoding="utf-8")
            with self.assertRaisesRegex(
                self.module.FinalizeError, "publication cut is ambiguous"
            ):
                self.module._load_published_json(final, "fixture")

    def test_publication_normalizes_hostile_umask_to_owner_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            final = Path(temporary) / "fixture.json"
            previous = os.umask(0o777)
            try:
                self.assertTrue(
                    self.module._publish_exclusive(
                        final, {"schema": "fixture", "value": 1}, "fixture"
                    )
                )
            finally:
                os.umask(previous)
            self.assertEqual(final.stat().st_mode & 0o777, 0o400)
            self.assertEqual(final.stat().st_nlink, 1)
            self.assertEqual(
                self.module._load_published_json(final, "fixture"),
                {"schema": "fixture", "value": 1},
            )

    def test_adb_execution_input_requires_exact_mode0500_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "adb-snapshot"
            payload = b"#!/bin/sh\necho fixture-adb\n"
            source.write_bytes(payload)
            source.chmod(0o500)
            expected = {
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            self.assertEqual(
                self.module._verify_adb_execution_input(
                    source, expected, "fixture"
                ),
                source,
            )
            source.chmod(0o700)
            with self.assertRaisesRegex(
                self.module.FinalizeError, "identity differs"
            ):
                self.module._verify_adb_execution_input(source, expected, "fixture")
            source.chmod(0o700)
            source.write_bytes(b"#!/bin/sh\necho replaced-adb\n")
            source.chmod(0o500)
            with self.assertRaisesRegex(
                self.module.FinalizeError, "identity differs"
            ):
                self.module._verify_adb_execution_input(source, expected, "fixture")

    def test_authority_binds_reviewed_private_adb_not_system_path(self):
        authority = self.module.load_authority()
        adb = self.module._paths(authority)["adb"]
        self.assertEqual(adb, self.module.DEFAULT_ADB.resolve(strict=True))
        self.assertTrue(str(adb).startswith(str(self.module.ROOT / "workspace/private")))
        self.assertEqual(adb.stat().st_mode & 0o777, 0o500)
        self.assertEqual(adb.stat().st_nlink, 1)

    def test_closed_reemission_requires_existing_exact_arm(self):
        authority = {"fixture": True}
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            with self.assertRaisesRegex(
                self.module.FinalizeError, "finalizer arm is absent"
            ):
                self.module.verify_existing_arm(authority, run)

    def test_post_health_cut_never_creates_a_missing_arm(self):
        authority = self.module.load_authority()
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / self.module.HEALTH_FILENAME).write_text(
                "{}\n", encoding="utf-8"
            )
            with mock.patch.object(self.module, "_initial_inputs_match") as initial:
                with self.assertRaisesRegex(
                    self.module.FinalizeError, "post-health.*arm is absent"
                ):
                    self.module.arm_finalizer(authority, run)
            initial.assert_not_called()
            self.assertFalse((run / self.module.ARM_FILENAME).exists())

    def test_render_plan_rejects_post_health_missing_or_tampered_arm(self):
        authority = self.module.load_authority()
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            prepared = mock.Mock(run_dir=run, binding_sha256="fixture-binding")
            journal = mock.Mock()
            journal.state.return_value = "ROLLBACK_FLASHED"
            evidence = {"record": {"path": "fixture", "size": 1, "sha256": "0" * 64}}
            with (
                mock.patch.object(self.module, "load_authority", return_value=authority),
                mock.patch.object(
                    self.module,
                    "verify_incident",
                    return_value=(prepared, journal, evidence),
                ),
                mock.patch.object(self.module, "_initial_inputs_match") as initial,
            ):
                (run / self.module.HEALTH_FILENAME).write_text("{}\n", encoding="utf-8")
                with self.assertRaisesRegex(
                    self.module.FinalizeError, "post-health.*exact arm"
                ):
                    self.module.render_plan()
                initial.assert_not_called()

                (run / self.module.HEALTH_FILENAME).unlink()
                arm = run / self.module.ARM_FILENAME
                arm.write_text("{}\n", encoding="utf-8")
                arm.chmod(0o400)
                with self.assertRaisesRegex(
                    self.module.FinalizeError, "closed P3.18 finalizer arm changed"
                ):
                    self.module.render_plan()

    def test_health_boot_id_requires_a_string(self):
        authority = {"approval_binding_sha256": "a" * 64}
        expected = {
            "verified_boot_state": "green",
            "boot_sha256": "b" * 64,
            "supporting_partition_sha256": {"vendor_boot": "c" * 64},
        }
        prepared = mock.Mock(
            binding_sha256="d" * 64,
            private_target={"serial": "fixture", "topology": "usb:fixture"},
            bundle=mock.Mock(profile={"final_health": expected}),
        )
        health = {
            "android_boot_completed": True,
            "boot_animation_stopped": True,
            "verified_boot_state": "green",
            "root_verified": True,
            "boot_sha256": "b" * 64,
            "supporting_partition_sha256": {"vendor_boot": "c" * 64},
            "odin_endpoint_absent": True,
            "kernel_release": "fixture",
            "boot_id_sha256": "1" * 64,
        }
        value = self.module._health_value(authority, prepared, health)
        self.assertEqual(
            self.module._validate_health_value(authority, prepared, value), value
        )
        mutated = copy.deepcopy(value)
        mutated["health"]["boot_id_sha256"] = int("1" * 64)
        with self.assertRaisesRegex(
            self.module.FinalizeError, "final health semantics differ"
        ):
            self.module._validate_health_value(authority, prepared, mutated)

    def test_strict_json_rejects_duplicate_and_nonfinite_values(self):
        for payload in (
            b'{"x":1,"x":2}',
            b'{"x":NaN}',
            b'{"x":Infinity}',
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(self.module.FinalizeError):
                    self.module._strict_json_bytes(payload, "fixture")


if __name__ == "__main__":
    unittest.main()
