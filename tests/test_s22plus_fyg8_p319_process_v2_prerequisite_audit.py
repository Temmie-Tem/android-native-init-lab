from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_process_v2_prerequisite_audit.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p319_process_v2_prerequisite_audit_tested", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P3.19 prerequisite auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319ProcessV2PrerequisiteAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.receipt = cls.module.build_receipt()

    def test_registry_capability_and_runner_consumption_are_separate_from_readiness(self):
        self.assertEqual(self.receipt["verdict"], self.module.VERDICT)
        self.assertEqual(self.receipt["status"], self.module.VERDICT)
        admission = self.receipt["no_replay"]
        self.assertTrue(admission["new_live_run_id_absent"])
        self.assertTrue(admission["candidate_pair_absent"])
        self.assertTrue(admission["observation_and_consumption_namespaces_distinct"])
        self.assertEqual(
            admission["carrier_observation_run_id"],
            self.module.CARRIER_OBSERVATION_RUN_ID,
        )
        self.assertEqual(
            admission["process_live_run_id"], self.module.NEW_LIVE_RUN_ID
        )
        self.assertEqual(admission["candidate_ap"]["sha256"], self.module.CANDIDATE_AP_SHA256)
        self.assertEqual(admission["candidate_ap"]["single_member"], "boot.img.lz4")
        registry = admission["global_consumed_run_registry"]
        self.assertTrue(registry["capability_authoritative"])
        self.assertTrue(registry["runner_registry_consumption_proved"])
        self.assertFalse(registry["runner_recovery_closed"])
        self.assertFalse(registry["runner_ready"])
        self.assertIsNone(self.receipt["global_registry_blocker"])

    def test_recovery_provenance_is_distinct_from_reopening_ap(self):
        recovery = self.receipt["recovery_usability_provenance"]
        self.assertTrue(recovery["demonstrated_download_path"])
        self.assertTrue(recovery["rollback_bound_exact"])
        self.assertTrue(recovery["final_healthy_closed"])
        self.assertEqual(recovery["classification"], "odin_transfer_completed")
        self.assertEqual(recovery["transport"]["attempts"], 1)
        self.assertTrue(recovery["transport"]["attempt_2_absent"])
        self.assertEqual(
            recovery["artifact"]["sha256"],
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )
        self.assertEqual(recovery["artifact"]["single_member"], "boot.img.lz4")
        self.assertEqual(recovery["journal"]["record_count"], 19)
        self.assertEqual(recovery["journal"]["state"], "CLOSED")
        self.assertEqual(len(recovery["journal"]["records_0010_0018"]), 9)
        self.assertEqual(recovery["topology"]["authority_state"], "rollback_bound_exact")

    def test_restart_probe_uses_two_durable_attempts_then_rejects(self):
        restart = self.receipt["restart_durability"]
        self.assertEqual(restart["helper"]["size"], 2974)
        self.assertEqual(
            restart["helper"]["sha256"],
            "e24090b43d9a0b59f675f7a4c2bab8ee6343183dd34e3bdee9ff86f116dc1e7f",
        )
        self.assertTrue(restart["helper"]["fresh_python_command_only"])
        self.assertEqual(restart["attempts_after_reopen"], 2)
        self.assertTrue(restart["third_attempt_rejected"])
        self.assertEqual(restart["retained_checkpoint_count"], 2)
        self.assertEqual(restart["backend_transfer_calls"], 0)
        self.assertEqual(restart["device_function_calls"], 0)
        self.assertEqual(
            [item.get("attempt") for item in restart["process_restarts"][:2]],
            [1, 2],
        )
        self.assertTrue(restart["process_restarts"][2]["rejected"])

    def test_raw_first_projection_is_disk_population_probe(self):
        raw = self.receipt["raw_first_execution_closure"]
        self.assertEqual(raw["auditor"]["size"], 76359)
        self.assertEqual(
            raw["auditor"]["sha256"],
            "a15f805808f4cc6c97515dd08da9852c1ae91cc0c51be382061e98f6863752cb",
        )
        self.assertEqual(
            raw["receipt"]["sha256"],
            "0ffd630671974208eddd2ee4ea7d6037c1c9c667b501d4e342a03e1d3c46ca42",
        )
        self.assertEqual(raw["receipt"]["size"], 15075)
        self.assertEqual(raw["predecessor"], self.module.RAW_FIRST_PREDECESSOR)
        self.assertEqual(raw["receipt"]["mode"], "0400")
        self.assertEqual(raw["receipt"]["nlink"], 1)
        self.assertEqual(
            raw["baseline"],
            {
                "all_revalidation_python_files_scanned": 1747,
                "subprocess_modules_scanned": 412,
                "projection_sha256": "5a54a6da33c62edf90ffb63c534cb293d76933918b5ef42b95845093f3d06b04",
            },
        )
        self.assertEqual(
            raw["semantic_projection_omits_only"],
            [
                "all_revalidation_python_files_scanned",
                "subprocess_modules_scanned",
            ],
        )
        self.assertTrue(raw["inert_addition"]["full_census_changed"])
        self.assertTrue(raw["inert_addition"]["projection_unchanged"])
        self.assertTrue(raw["inert_addition"]["restored_exactly_after_deletion"])
        self.assertTrue(raw["neutral_host_process_addition"]["projection_unchanged"])
        self.assertTrue(raw["relevant_s22_mutation"]["failed_closed"])
        self.assertEqual(
            raw["override_vs_disk_population_mismatch"],
            "test-surface-only; this probe uses actual copied on-disk files and no overrides",
        )

    def test_all_authority_and_causal_fields_are_false(self):
        authority = self.receipt["authority"]
        for key in (
            "device_contact",
            "approval_created",
            "live_authorized",
            "candidate_success",
            "causal_result_allowed",
            "mux_result_claimable",
            "host_silent_claimable",
            "candidate_replay_authorized",
            "recovery_authorized",
            "transfer",
        ):
            with self.subTest(key=key):
                self.assertFalse(authority[key])
        self.assertEqual(authority["odin_invocations"], 0)
        self.assertEqual(authority["adb_commands"], 0)
        self.assertEqual(self.receipt["scope"]["tier"], "H0")
        self.assertTrue(self.receipt["scope"]["host_only"])
        self.assertFalse(self.receipt["scope"]["device_contact"])

    def test_raw_receipt_publication_is_complete_mode0400_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "prerequisite.json"
            identity = self.module.write_receipt(destination, self.receipt)
            self.assertEqual(destination.stat().st_mode & 0o777, 0o400)
            self.assertEqual(destination.stat().st_nlink, 1)
            self.assertEqual(identity["size"], destination.stat().st_size)
            self.assertEqual(
                json.loads(destination.read_text(encoding="utf-8"))["verdict"],
                self.module.VERDICT,
            )
            with self.assertRaises(self.module.AuditError):
                self.module.write_receipt(destination, self.receipt)
            sibling = Path(directory) / "prerequisite-copy.json"
            self.module.write_receipt(sibling, self.receipt)
            self.assertEqual(destination.read_bytes(), sibling.read_bytes())

    def test_strict_json_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_bytes(b'{"a":1,"a":2}\n')
            path.chmod(0o400)
            with self.assertRaises(self.module.AuditError):
                self.module._strict_json(path, "duplicate", mode=0o400)

    def test_new_auditor_has_no_device_command_import_or_live_authority(self):
        source = SCRIPT.read_text(encoding="utf-8")
        helper_path = (
            ROOT
            / "workspace/public/src/scripts/h0/"
            / "s22plus_fyg8_p319_restart_probe.py"
        )
        helper = helper_path.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "os.system(",
            "Popen(",
            "check_output(",
            "--adb",
            "--approval",
            "--finalize",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertNotIn("DEVICE-ACTION-F1-V2-APPROVE:", source)
        self.assertIn("subprocess.run", helper)
        self.assertNotIn("adb shell", helper)
        self.assertNotIn("odin4", helper)

    def test_restart_probe_byte_mutation_is_rejected(self):
        helper = (
            ROOT
            / "workspace/public/src/scripts/h0/"
            / "s22plus_fyg8_p319_restart_probe.py"
        )
        with tempfile.TemporaryDirectory() as directory:
            mutated = Path(directory) / helper.name
            mutated.write_bytes(helper.read_bytes() + b"\n# mutation\n")
            mutated.chmod(0o400)
            with self.assertRaises(self.module.AuditError):
                self.module._validate_restart_probe_source(mutated)


if __name__ == "__main__":
    unittest.main()
