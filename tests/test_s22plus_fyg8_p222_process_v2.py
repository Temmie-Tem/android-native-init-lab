import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
READY_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p221_process_v2_ready_1.json"
)


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8P222ProcessV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        cls.module = load(
            "s22plus_fyg8_p222_process_v2_tested",
            "prepare_s22plus_fyg8_p222_process_v2.py",
        )
        cls.core = load("s22plus_fyg8_p222_core_tested", "device_action_f1_v2.py")

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def fixture(self):
        module = self.module

        def record(label, size, digest):
            return {
                "label": label,
                "size": size,
                "sha256": digest,
                "entry_count": 1,
                "userspace_count": 1,
                "unsat_count": 1,
                "long_family_count": 2,
                "unsat_family_count": 1,
                "old_e0_entry_count": 0,
                "old_e0_userspace_count": 0,
                "verified": True,
            }

        image = {"size": 101, "sha256": "b" * 64}
        vmlinux = {"size": 202, "sha256": "c" * 64}
        boot = {"size": 303, "sha256": "d" * 64}
        closure = {
            "image": record("Image", image["size"], image["sha256"]),
            "vmlinux": record("vmlinux", vmlinux["size"], vmlinux["sha256"]),
            "boot_image": boot,
            "boot_kernel": {**image, "equals_image": True},
            "ap_members": [{"name": "boot.img.lz4", "type": "regular"}],
            "boot_only_ap": True,
            "verified": True,
        }
        candidate_ap = {
            "path": "workspace/private/test/AP.tar.md5",
            "size": 404,
            "sha256": "a" * 64,
        }
        p221 = {
            "schema": module.P221_SCHEMA,
            "target": module.contract.TARGET,
            "verdict": module.P221_VERDICT,
            "candidate": {
                "artifacts": {
                    "ap_tar_md5": {
                        "size": candidate_ap["size"],
                        "sha256": candidate_ap["sha256"],
                    }
                },
                "extracted_artifact_closure": closure,
                "writer_exclusion": {
                    "direct_ring_writer_present": False,
                    "sec_log_buf_loaded": False,
                    "verified": True,
                },
                "manifest_absent": True,
                "verified": True,
            },
            "safety": {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "flash": False,
                "partition_write": False,
                "manifest_created": False,
                "live_authorized": False,
            },
        }
        return p221, candidate_ap

    def acceptance(self, run_payload, static_payload):
        module = self.module
        return {
            "kind": module.evidence.SAME_RING_KIND,
            "source": module.evidence.CHECKPOINT_SOURCE,
            "decoder": module.evidence.SAME_RING_DECODER,
            "contract_id": module.evidence.SAME_RING_CONTRACT_ID,
            "records": {
                "entry_hex": module.contract.ENTRY_PROOF.hex(),
                "userspace_hex": module.contract.USERSPACE_PROOF.hex(),
                "unsat_hex": module.contract.UNSAT_PROOF.hex(),
            },
            "families": {
                "long_hex": module.evidence.same_ring.ENTRY_FAMILY.hex(),
                "unsat_hex": module.evidence.same_ring.UNSAT_FAMILY.hex(),
            },
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
            "exact_count": 1,
            "contract": {
                "run_manifest": {
                    "path": "workspace/private/run.json",
                    **module.receipt(run_payload),
                },
                "static_check": {
                    "path": "workspace/private/static.json",
                    **module.receipt(static_payload),
                },
            },
        }

    def test_derived_payloads_pass_common_offline_verifier(self):
        p221, candidate_ap = self.fixture()
        run_payload, static_payload = self.module.derive(p221, candidate_ap)
        self.assertEqual(run_payload, self.module.canonical(json.loads(run_payload)))
        self.assertEqual(
            static_payload, self.module.canonical(json.loads(static_payload))
        )
        verification = self.module.evidence.verify_offline_contract(
            self.acceptance(run_payload, static_payload),
            payloads={
                "run_manifest": run_payload,
                "static_check": static_payload,
            },
            receipts={
                "run_manifest": self.module.receipt(run_payload),
                "static_check": self.module.receipt(static_payload),
            },
            candidate_ap=candidate_ap,
        )
        self.assertEqual(
            verification["schema"],
            "device_action_f1_same_ring_offline_contract_v2",
        )
        self.assertTrue(verification["zero_is_ambiguous"])
        self.assertTrue(verification["verified"])

    def test_writer_or_manifest_presence_fails_closed(self):
        for key, value in (
            ("direct_ring_writer_present", True),
            ("sec_log_buf_loaded", True),
        ):
            p221, candidate_ap = self.fixture()
            p221["candidate"]["writer_exclusion"][key] = value
            with self.subTest(key=key):
                with self.assertRaisesRegex(
                    self.module.PromotionError, "ring-writer exclusion"
                ):
                    self.module.derive(p221, candidate_ap)
        p221, candidate_ap = self.fixture()
        p221["candidate"]["manifest_absent"] = False
        with self.assertRaisesRegex(self.module.PromotionError, "already carries"):
            self.module.derive(p221, candidate_ap)

    def test_candidate_ap_mismatch_fails_closed(self):
        p221, candidate_ap = self.fixture()
        candidate_ap["sha256"] = "f" * 64
        with self.assertRaisesRegex(self.module.PromotionError, "AP receipt mismatch"):
            self.module.derive(p221, candidate_ap)

    def test_stable_read_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "payload"
            payload.write_bytes(b"payload")
            indirect = root / "indirect"
            indirect.symlink_to(payload)
            with self.assertRaisesRegex(self.module.PromotionError, "indirect"):
                self.module.stable_read(indirect, 1024)

    def test_pinned_contract_constants_are_populated(self):
        self.assertEqual(self.module.P221_STATIC_SIZE, 8477)
        self.assertRegex(self.module.P221_STATIC_SHA256, r"^[0-9a-f]{64}$")
        self.assertEqual(self.module.CANDIDATE_AP["size"], 27064361)
        self.assertNotEqual(
            hashlib.sha256(b"not-the-candidate").hexdigest(),
            self.module.CANDIDATE_AP["sha256"],
        )

    def test_ready_manifest_passes_common_bundle_without_live_authority(self):
        bundle = self.core.verify_bundle(ROOT, READY_MANIFEST)
        self.assertEqual(
            bundle.manifest["manifest_id"],
            "s22plus-fyg8-p221-process-v2-ready-1",
        )
        self.assertEqual(
            bundle.manifest["observation"]["acceptance"]["kind"],
            self.module.evidence.SAME_RING_KIND,
        )
        self.assertEqual(
            bundle.receipt["candidate_ap"]["sha256"],
            self.module.CANDIDATE_AP["sha256"],
        )
        self.assertEqual(
            bundle.receipt["observation_contract"]["verification"]["schema"],
            "device_action_f1_same_ring_offline_contract_v2",
        )
        self.assertFalse(bundle.receipt["device_contact"])
        self.assertFalse(bundle.receipt["odin_invoked"])
        self.assertFalse(bundle.receipt["live_authorized"])
        self.assertEqual(
            bundle.sha256,
            "9f4540314e7dac0ae4801eef00af2c90884af57250eac23348cee4912bee9624",
        )


if __name__ == "__main__":
    unittest.main()
