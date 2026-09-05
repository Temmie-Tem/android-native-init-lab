import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "workspace/public/src/scripts/revalidation"),
               str(ROOT / "workspace/public/src/scripts/analysis")]
import device_action_f1_evidence_v2 as evidence
import device_action_f1_v2 as core
import s22plus_fyg8_p345_process_v2_candidate_static as static

class P345ProcessTests(unittest.TestCase):
    def test_exact_manifest_role_and_no_lease(self):
        path = ROOT / "workspace/public/src/device-action/manifests/s22plus_fyg8_p344_process_v2_ready_1.json"
        manifest = json.loads(path.read_bytes())
        profile = json.loads((ROOT / manifest["target_profile"]).read_bytes())
        manifest["observation"]["acceptance"] = evidence.p345_stock_adapter.acceptance_fixture()
        spec = evidence.p345_research_shell_observer_spec()
        manifest["observation"]["candidate_observer"] = spec
        core.validate_manifest(manifest, profile)
        self.assertEqual(spec["same_fd_session_count"], 5)
        self.assertEqual(spec["physical_reopen_count"], 0)
        self.assertFalse(spec["later_action_lease_active"])
        self.assertNotIn("resident_lease_schema", spec)
        for key, changed in (("caller_selected_command", True), ("idle_seconds", 120),
                             ("usb_serial", "S22E3" + evidence.P344_RUN_ID)):
            bad = copy.deepcopy(spec); bad[key] = changed
            with self.assertRaises(evidence.EvidenceError):
                evidence.validate_candidate_arrival_proof_role(
                    evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE, bad,
                    expected_run_id=evidence.P345_RUN_ID)

    def test_real_carrier_classification_and_clean_baseline(self):
        adapter = evidence.p345_stock_adapter
        acceptance = adapter.acceptance_fixture()
        record = adapter.encode_fixture()
        raw = bytes(adapter.RAW_SIZE - len(record)) + record
        result = evidence.classify_e1_latest_stage(raw, acceptance)
        self.assertEqual(result["exact_record_count"], 1)
        self.assertFalse(result["candidate_success"])
        self.assertTrue(result["carrier_supplemental"])
        self.assertTrue(evidence.classify_clean_baseline(bytes(adapter.RAW_SIZE), acceptance)["baseline_clean"])
        with self.assertRaises(ValueError):
            evidence.classify_clean_baseline(raw, acceptance)

    def test_execution_closure_and_foreign_source_reject(self):
        acceptance = evidence.p345_stock_adapter.acceptance_fixture()
        sources = core.execution_critical_source_receipts(acceptance,
            candidate_arrival_proof_role=evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE)
        verified = {"source_closure": static.source_receipts()}
        core.verify_candidate_source_binding(acceptance, verified, sources)
        bad = copy.deepcopy(sources)
        bad["p345_research_shell_runtime"]["sha256"] = "0" * 64
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_source_binding(acceptance, verified, bad)

    def test_predecessor_and_extra_authority_rejected(self):
        value = evidence.p345_stock_adapter.acceptance_fixture()
        for key, changed in (("run_id", evidence.P344_RUN_ID), ("resident_lease_schema", "anything")):
            bad = copy.deepcopy(value); bad[key] = changed
            with self.assertRaises(evidence.EvidenceError):
                evidence.validate_acceptance(bad)

    def test_compact_promotion_has_no_old_claims(self):
        fixture = {"candidate": {"a": {"ap_tar_md5": {"size": 1, "sha256": "1" * 64}}},
                   "qualification": evidence.p345_stock_adapter.acceptance_fixture()["qualification_commands"]}
        pin = {"path": "private/static", "size": 1, "sha256": "2" * 64}
        run, check = static.promotion_payloads(fixture, pin, run_id="h0-fixture")
        self.assertEqual(run["schema"], evidence.P345_RUN_MANIFEST_SCHEMA)
        self.assertEqual(check["schema"], evidence.P345_STATIC_RESULT_SCHEMA)
        self.assertNotIn("runtime_behavior_unchanged", run)
        self.assertNotIn("idle_reuse", run)
        self.assertFalse(run["later_action_lease_active"])

    def test_p344_image_cannot_be_promoted_by_header_relabel(self):
        closure = {"kind": "p345_exact_readonly_research_shell_ap_v1",
            "run_id": evidence.P345_RUN_ID,
            "userspace_overlay_contract_id": evidence.P345_STOCK_OVERLAY_CONTRACT_ID,
            "source_contract_id": evidence.p345_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "auth_key": evidence.P345_AUTH_EXEC_AUTH_KEY_IDENTITY,
            "image": evidence.p345_artifact_identity.P344_IMAGE_IDENTITY,
            **{key: {} for key in ("boot_img_lz4", "boot_image", "init", "child", "busybox", "latch")}}
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_e2_ap_payload(b"", closure)

if __name__ == "__main__":
    unittest.main()
