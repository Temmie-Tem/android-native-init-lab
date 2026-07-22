import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
DRAFT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_r4w1e0_process_v2_draft.json"
)
READY_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_r4w1e0_process_v2_ready_1.json"
)


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1E0ProcessV2ManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        cls.core = load("r4w1e0_process_core_tested", "device_action_f1_v2.py")
        cls.live = load("r4w1e0_process_live_tested", "device_action_f1_live_v2.py")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def acceptance(self):
        return self.core.verify_bundle(ROOT, DRAFT_MANIFEST).manifest[
            "observation"
        ]["acceptance"]

    def test_exact_draft_bundle_pins_e0_offline_contract(self):
        bundle = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        self.assertEqual(bundle.manifest["status"], "draft-host-only")
        self.assertEqual(
            bundle.receipt["candidate_ap"]["sha256"],
            "9b5ed2295ef9217746ba5e422acd54d13cfbc2daddcf35804ebaa08b9303ac08",
        )
        verification = bundle.receipt["observation_contract"]["verification"]
        self.assertEqual(
            verification["schema"],
            "device_action_f1_pid1_userspace_offline_contract_v2",
        )
        self.assertEqual(
            verification["probe_id"], "64554e8469385878c5bf8d57c44edeea"
        )
        self.assertTrue(verification["clean_baseline_required"])
        self.assertTrue(verification["verified"])
        self.assertEqual(
            bundle.sha256,
            "8cd229d61d698305e45cb48fe4ff965b6aed3157bc5601801c99f6bcfa603782",
        )

    def test_draft_cannot_allocate_connected_prepare(self):
        bundle = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "must-not-exist"
            with self.assertRaisesRegex(
                self.live.F1LiveError, "manifest is not ready for F1 approval"
            ):
                self.live.prepare_connected(ROOT, bundle, run_dir, object())
            self.assertFalse(run_dir.exists())

    def test_classifier_distinguishes_absent_entry_and_userspace(self):
        acceptance = self.acceptance()
        evidence = self.live.typed_evidence
        absent = self.live.classify_acceptance(b"clean retained log", acceptance)
        entry = self.live.classify_acceptance(
            b"prefix" + evidence.PID1_USERSPACE_ENTRY + b"suffix", acceptance
        )
        userspace = self.live.classify_acceptance(
            b"prefix" + evidence.PID1_USERSPACE_PROOF + b"suffix", acceptance
        )
        self.assertEqual(absent["classification"], "PID1_USERSPACE_ABSENT")
        self.assertFalse(absent["accepted"])
        self.assertEqual(entry["classification"], "PID1_ENTRY_ONLY")
        self.assertEqual(entry["entry_count"], 1)
        self.assertFalse(entry["accepted"])
        self.assertEqual(
            userspace["classification"], "PID1_USERSPACE_CALLBACK_REACHED"
        )
        self.assertEqual(userspace["userspace_count"], 1)
        self.assertTrue(userspace["accepted"])

    def test_classifier_rejects_duplicate_mixed_and_partial_family(self):
        acceptance = self.acceptance()
        evidence = self.live.typed_evidence
        payloads = (
            evidence.PID1_USERSPACE_PROOF * 2,
            evidence.PID1_USERSPACE_ENTRY + evidence.PID1_USERSPACE_PROOF,
            evidence.PID1_USERSPACE_PROOF[:24],
        )
        for payload in payloads:
            with self.subTest(payload=payload.hex()):
                result = self.live.classify_acceptance(payload, acceptance)
                self.assertTrue(result["integrity_issue"])
                self.assertFalse(result["accepted"])

    def test_acceptance_identity_is_not_manifest_selectable(self):
        acceptance = self.acceptance()
        for name, value in (
            ("probe_id", "1" * 32),
            ("marker", acceptance["entry_marker"]),
            ("entry_marker", acceptance["marker"]),
            ("decoder", "another-decoder"),
        ):
            changed = copy.deepcopy(acceptance)
            changed[name] = value
            with self.subTest(name=name):
                with self.assertRaises(self.core.typed_evidence.EvidenceError):
                    self.core.typed_evidence.validate_acceptance(changed)

    def test_execution_source_closure_is_kind_specific(self):
        e0_sources = self.core.execution_critical_source_receipts(
            self.acceptance()
        )
        self.assertEqual(
            set(e0_sources),
            {
                "runner",
                "typed_evidence",
                "checkpoint_decoder",
                "regular_path_transport",
            },
        )
        evidence = self.core.typed_evidence
        decoder = evidence.same_ring
        same_ring_acceptance = {
            "kind": evidence.SAME_RING_KIND,
            "source": evidence.CHECKPOINT_SOURCE,
            "decoder": evidence.SAME_RING_DECODER,
            "contract_id": evidence.SAME_RING_CONTRACT_ID,
            "records": {
                "entry_hex": decoder.ENTRY_PROOF.hex(),
                "userspace_hex": decoder.USERSPACE_PROOF.hex(),
                "unsat_hex": decoder.UNSAT_PROOF.hex(),
            },
            "families": {
                "long_hex": decoder.ENTRY_FAMILY.hex(),
                "unsat_hex": decoder.UNSAT_FAMILY.hex(),
            },
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
            "exact_count": 1,
            "contract": {
                "run_manifest": {
                    "path": "workspace/private/run.json",
                    "size": 1,
                    "sha256": "1" * 64,
                },
                "static_check": {
                    "path": "workspace/private/static.json",
                    "size": 1,
                    "sha256": "2" * 64,
                },
            },
        }
        sources = self.core.execution_critical_source_receipts(
            same_ring_acceptance
        )
        self.assertTrue(
            {
                "same_ring_decoder",
                "same_ring_static_checker",
                "same_ring_design_model",
                "same_ring_base_checker",
            }.issubset(sources)
        )

    def test_malformed_static_artifact_shape_fails_closed(self):
        bundle = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        acceptance = copy.deepcopy(bundle.manifest["observation"]["acceptance"])
        run_manifest = (
            ROOT / acceptance["contract"]["run_manifest"]["path"]
        ).read_bytes()
        static_result = json.loads(
            (ROOT / acceptance["contract"]["static_check"]["path"]).read_text()
        )
        static_result["candidate"]["artifacts"]["ap"] = []
        malformed = (
            json.dumps(static_result, indent=2, sort_keys=True, allow_nan=False)
            + "\n"
        ).encode("ascii")
        acceptance["contract"]["static_check"] = {
            "path": "unused",
            "size": len(malformed),
            "sha256": hashlib.sha256(malformed).hexdigest(),
        }
        payloads = {"run_manifest": run_manifest, "static_check": malformed}
        receipts = {
            name: {
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for name, payload in payloads.items()
        }
        with self.assertRaisesRegex(
            self.core.typed_evidence.EvidenceError,
            "static checker result does not bind E0 candidate",
        ):
            self.core.typed_evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=bundle.receipt["candidate_ap"],
            )

    def test_ready_manifest_is_data_only_promotion_without_live_authority(self):
        draft = self.core.verify_bundle(ROOT, DRAFT_MANIFEST)
        ready = self.core.verify_bundle(ROOT, READY_MANIFEST)
        mutable = {"manifest_id", "run_id", "status"}
        self.assertEqual(
            {
                key
                for key in draft.manifest
                if draft.manifest[key] != ready.manifest[key]
            },
            mutable,
        )
        self.assertEqual(ready.manifest["status"], "ready-for-f1-approval")
        self.assertEqual(
            ready.manifest["observation"]["acceptance"]["kind"],
            "retained_pid1_userspace_after_rollback",
        )
        self.assertEqual(
            ready.sha256,
            "3c4c5086e8706a9c811a1c4335b4ef79b97be7113bb4ce3bf3ddd640c1d1d0b1",
        )
        self.assertFalse(ready.receipt["device_contact"])
        self.assertFalse(ready.receipt["odin_invoked"])
        self.assertFalse(ready.receipt["live_authorized"])


if __name__ == "__main__":
    unittest.main()
