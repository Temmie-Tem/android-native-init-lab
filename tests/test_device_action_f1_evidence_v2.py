import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "device_action_f1_evidence_v2.py"
RUN_ID = bytes.fromhex("395f27c3ac34ebe61395d7efd5a058e8")


def load_module():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(
            "device_action_f1_evidence_v2_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


class DeviceActionF1EvidenceV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.checkpoint = cls.module.checkpoint

    def acceptance(self):
        return {
            "kind": self.module.CHECKPOINT_KIND,
            "source": "/proc/last_kmsg",
            "marker": self.checkpoint.ENTRY_PROOF.decode("ascii"),
            "family": self.checkpoint.ENTRY_FAMILY.decode("ascii"),
            "exact_count": 1,
            "decoder": self.module.CHECKPOINT_DECODER,
            "profile": "E1",
            "run_id": RUN_ID.hex(),
            "terminal_stage": self.checkpoint.PROFILE_TERMINAL_STAGE["E1"],
            "terminal_outcome": "success",
            "require_two_valid_slots": True,
            "contract": {
                "run_manifest": {
                    "path": "workspace/private/run-manifest.json",
                    "size": 1,
                    "sha256": "1" * 64,
                },
                "static_check": {
                    "path": "workspace/private/static-check.json",
                    "size": 1,
                    "sha256": "2" * 64,
                },
            },
        }

    def same_ring_acceptance(self, run_payload=b"{}", static_payload=b"{}"):
        same_ring = self.module.same_ring
        return {
            "kind": self.module.SAME_RING_KIND,
            "source": "/proc/last_kmsg",
            "decoder": self.module.SAME_RING_DECODER,
            "contract_id": self.module.SAME_RING_CONTRACT_ID,
            "records": {
                "entry_hex": same_ring.ENTRY_PROOF.hex(),
                "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
                "unsat_hex": same_ring.UNSAT_PROOF.hex(),
            },
            "families": {
                "long_hex": same_ring.ENTRY_FAMILY.hex(),
                "unsat_hex": same_ring.UNSAT_FAMILY.hex(),
            },
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
            "exact_count": 1,
            "contract": {
                "run_manifest": {
                    "path": "workspace/private/p219-run-manifest.json",
                    "size": len(run_payload),
                    "sha256": hashlib.sha256(run_payload).hexdigest(),
                },
                "static_check": {
                    "path": "workspace/private/p219-static-check.json",
                    "size": len(static_payload),
                    "sha256": hashlib.sha256(static_payload).hexdigest(),
                },
            },
        }

    def same_ring_multiboot_acceptance(
        self, run_payload=b"{}", static_payload=b"{}"
    ):
        acceptance = self.same_ring_acceptance(run_payload, static_payload)
        acceptance["kind"] = self.module.SAME_RING_MULTIBOOT_KIND
        acceptance["decoder"] = self.module.SAME_RING_MULTIBOOT_DECODER
        acceptance["policy_id"] = self.module.SAME_RING_MULTIBOOT_POLICY_ID
        acceptance["accepted_identity"] = (
            "USERSPACE_CALLBACK_REACHED_ONE_OR_MORE_BOOTS"
        )
        acceptance["minimum_exact_count"] = acceptance.pop("exact_count")
        return acceptance

    def same_ring_offline_bundle(self):
        same_ring = self.module.same_ring
        candidate_ap = {
            "path": "/private/candidate.tar.md5",
            "size": 123,
            "sha256": "a" * 64,
        }
        records = {
            "entry_hex": same_ring.ENTRY_PROOF.hex(),
            "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
            "unsat_hex": same_ring.UNSAT_PROOF.hex(),
        }
        run_manifest = {
            "schema": self.module.SAME_RING_RUN_MANIFEST_SCHEMA,
            "target": same_ring.TARGET,
            "profile": "P219",
            "contract_id": self.module.SAME_RING_CONTRACT_ID,
            "contract_sha256": same_ring.CONTRACT_SHA256,
            "records": records,
            "observation_contract": {
                "accepted_identity": "USERSPACE_CALLBACK_REACHED",
                "zero_classification": "ZERO_AMBIGUOUS",
                "entry_threshold": same_ring.ENTRY_SIZE,
                "unsat_threshold": same_ring.UNSAT_SIZE,
                "clean_baseline_required": True,
            },
            "candidate_ap": candidate_ap,
        }
        run_payload = json.dumps(
            run_manifest, sort_keys=True, separators=(",", ":")
        ).encode("ascii")
        run_receipt = {
            "size": len(run_payload),
            "sha256": hashlib.sha256(run_payload).hexdigest(),
        }
        image_identity = {"size": 100, "sha256": "b" * 64}
        vmlinux_identity = {"size": 200, "sha256": "c" * 64}
        boot_image_identity = {"size": 300, "sha256": "d" * 64}

        def record_claim(label, identity):
            return {
                "label": label,
                **identity,
                "entry_count": 1,
                "userspace_count": 1,
                "unsat_count": 1,
                "long_family_count": 2,
                "unsat_family_count": 1,
                "old_e0_entry_count": 0,
                "old_e0_userspace_count": 0,
                "verified": True,
            }

        static_result = {
            "schema": self.module.SAME_RING_STATIC_SCHEMA,
            "target": same_ring.TARGET,
            "verdict": self.module.SAME_RING_STATIC_VERDICT,
            "contract_id": self.module.SAME_RING_CONTRACT_ID,
            "contract_sha256": same_ring.CONTRACT_SHA256,
            "records": records,
            "run_binding": {
                "canonical_manifest_size": len(run_payload),
                "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
                "verified": True,
            },
            "candidate": {
                "artifacts": {
                    "ap": {
                        "size": candidate_ap["size"],
                        "sha256": candidate_ap["sha256"],
                    },
                    "run_manifest": run_receipt,
                    "image": image_identity,
                    "vmlinux": vmlinux_identity,
                    "boot_image": boot_image_identity,
                },
                "record_verification": {
                    "image": record_claim("Image", image_identity),
                    "vmlinux": record_claim("vmlinux", vmlinux_identity),
                    "boot_image": boot_image_identity,
                    "boot_kernel": {
                        "size": image_identity["size"],
                        "sha256": image_identity["sha256"],
                        "equals_image": True,
                    },
                    "ap_members": [
                        {"name": "boot.img.lz4", "type": "regular"}
                    ],
                    "boot_only_ap": True,
                    "verified": True,
                },
            },
            "safety": {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "odin_transfer": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
            },
        }
        static_payload = json.dumps(
            static_result, sort_keys=True, separators=(",", ":")
        ).encode("ascii")
        acceptance = self.same_ring_acceptance(run_payload, static_payload)
        return {
            "acceptance": acceptance,
            "payloads": {
                "run_manifest": run_payload,
                "static_check": static_payload,
            },
            "receipts": {
                "run_manifest": run_receipt,
                "static_check": {
                    "size": len(static_payload),
                    "sha256": hashlib.sha256(static_payload).hexdigest(),
                },
            },
            "candidate_ap": candidate_ap,
        }

    def region_through(self, count, *, failure=False):
        region = self.checkpoint.initial_region(0x300000, 9)
        sequence = self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"]
        for index, stage in enumerate(sequence[:count]):
            is_last = index == count - 1
            if failure and is_last:
                outcome = self.checkpoint.OUTCOME_FAILURE
                detail = -5
            elif stage == self.checkpoint.PROFILE_TERMINAL_STAGE["E1"]:
                outcome = self.checkpoint.OUTCOME_SUCCESS
                detail = 0
            else:
                outcome = self.checkpoint.OUTCOME_PROGRESS
                detail = 0
            request = self.checkpoint.encode_request(
                "E1", stage, run_id=RUN_ID, outcome=outcome, detail=detail
            )
            region = self.checkpoint.apply_request(region, request)
        return region

    def classify(self, region):
        return self.module.classify_checkpoint(
            b"prefix" + region + b"suffix", self.acceptance()
        )

    def test_terminal_success_requires_exact_two_slot_checkpoint(self):
        result = self.classify(
            self.region_through(len(self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"]))
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["classification"], "CHECKPOINT_TERMINAL_SUCCESS")
        self.assertEqual(result["exact_count"], 1)
        self.assertTrue(result["checkpoint"]["two_valid_slots"])
        self.assertEqual(result["checkpoint"]["active"]["run_id"], RUN_ID.hex())

    def test_progress_and_failure_are_diagnostic_not_acceptance(self):
        progress = self.classify(self.region_through(3))
        failure = self.classify(self.region_through(3, failure=True))
        self.assertFalse(progress["accepted"])
        self.assertEqual(progress["classification"], "CHECKPOINT_PROGRESS_ONLY")
        self.assertFalse(failure["accepted"])
        self.assertEqual(failure["classification"], "CHECKPOINT_TERMINAL_FAILURE")
        self.assertEqual(failure["checkpoint"]["active"]["detail"], -5)

    def test_changed_run_id_is_decode_failure(self):
        acceptance = self.acceptance()
        acceptance["run_id"] = "4" * 32
        result = self.module.classify_checkpoint(
            self.region_through(len(self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"])),
            acceptance,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["classification"], "CHECKPOINT_DECODE_FAILURE")

    def test_duplicate_and_partial_family_are_integrity_failures(self):
        region = self.region_through(
            len(self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"])
        )
        duplicate = self.module.classify_checkpoint(
            region + region, self.acceptance()
        )
        partial = self.module.classify_checkpoint(
            b"prefix" + self.checkpoint.ENTRY_FAMILY[:8], self.acceptance()
        )
        self.assertEqual(
            duplicate["classification"], "CHECKPOINT_FAMILY_INTEGRITY_FAILURE"
        )
        self.assertEqual(
            partial["classification"], "CHECKPOINT_FAMILY_INTEGRITY_FAILURE"
        )
        self.assertFalse(duplicate["accepted"])
        self.assertFalse(partial["accepted"])

    def test_corrupt_new_slot_falls_back_without_pass(self):
        region = bytearray(
            self.region_through(len(self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"]))
        )
        active = self.checkpoint.decode_region(bytes(region))["active"]
        start = self.checkpoint.ENTRY_SIZE + active["slot_id"] * self.checkpoint.SLOT_SIZE
        region[start + 20] ^= 0x01
        result = self.classify(bytes(region))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["classification"], "CHECKPOINT_PROGRESS_ONLY")
        self.assertEqual(result["checkpoint"]["invalid_committed_slots"], [active["slot_id"]])

    def test_terminal_success_with_only_one_valid_slot_is_rejected(self):
        region = bytearray(
            self.region_through(len(self.checkpoint.PROFILE_STAGE_SEQUENCES["E1"]))
        )
        decoded = self.checkpoint.decode_region(bytes(region))
        active_slot = decoded["active"]["slot_id"]
        older_slot = active_slot ^ 1
        commit = (
            self.checkpoint.ENTRY_SIZE
            + older_slot * self.checkpoint.SLOT_SIZE
            + self.checkpoint.SLOT_SIZE
            - 1
        )
        region[commit] = 0
        result = self.classify(bytes(region))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["classification"], "CHECKPOINT_TERMINAL_MISMATCH")

    def test_marker_acceptance_shape_remains_supported(self):
        marker = {
            "kind": self.module.MARKER_KIND,
            "source": "/proc/last_kmsg",
            "marker": "legacy marker",
            "family": "legacy family",
            "exact_count": 1,
        }
        self.assertEqual(self.module.validate_acceptance(marker), marker)

    def test_same_ring_classifier_covers_all_bounded_states(self):
        acceptance = self.same_ring_acceptance()
        records = self.module.same_ring
        cases = (
            (b"ordinary", "ZERO_AMBIGUOUS", False),
            (records.ENTRY_PROOF, "ENTRY_ONLY", False),
            (records.USERSPACE_PROOF, "USERSPACE_CALLBACK_REACHED", True),
            (
                records.UNSAT_PROOF,
                "UNSAT_VALID_MAGIC_ENTRY_DID_NOT_FIT",
                False,
            ),
            (
                records.ENTRY_PROOF + records.UNSAT_PROOF,
                "AMBIGUOUS_INTEGRITY_FAILURE",
                False,
            ),
        )
        for payload, expected, accepted in cases:
            with self.subTest(expected=expected):
                result = self.module.classify_same_ring(payload, acceptance)
                self.assertEqual(result["classification"], expected)
                self.assertEqual(result["accepted"], accepted)
                self.assertEqual(
                    result["acceptance_present"], accepted
                )

    def test_same_ring_classifier_rejects_duplicate_foreign_and_partial(self):
        acceptance = self.same_ring_acceptance()
        records = self.module.same_ring
        payloads = (
            records.USERSPACE_PROOF * 2,
            records.ENTRY_FAMILY + b"0" * 32 + b"]]\n",
            b"prefix" + records.UNSAT_PROOF[:12],
        )
        for payload in payloads:
            with self.subTest(payload=payload.hex()):
                result = self.module.classify_same_ring(payload, acceptance)
                self.assertEqual(
                    result["classification"], "AMBIGUOUS_INTEGRITY_FAILURE"
                )
                self.assertTrue(result["integrity_issue"])
                self.assertFalse(result["accepted"])

    def test_same_ring_multiboot_accepts_only_pure_userspace_multiplicity(self):
        acceptance = self.same_ring_multiboot_acceptance()
        records = self.module.same_ring
        for count in (1, 2, 5):
            with self.subTest(count=count):
                result = self.module.classify_same_ring_multiboot(
                    records.USERSPACE_PROOF * count,
                    acceptance,
                )
                self.assertEqual(
                    result["classification"],
                    "USERSPACE_CALLBACK_REACHED_ONE_OR_MORE_BOOTS",
                )
                self.assertTrue(result["accepted"])
                self.assertEqual(result["exact_count"], count)
                self.assertEqual(result["minimum_candidate_boots"], count)

        for payload in (
            records.USERSPACE_PROOF + records.ENTRY_PROOF,
            records.USERSPACE_PROOF + records.UNSAT_PROOF,
            records.ENTRY_FAMILY + b"0" * 32 + b"]]\n",
            b"prefix" + records.UNSAT_PROOF[:12],
        ):
            with self.subTest(payload=payload.hex()):
                result = self.module.classify_same_ring_multiboot(
                    payload,
                    acceptance,
                )
                self.assertEqual(
                    result["classification"], "AMBIGUOUS_INTEGRITY_FAILURE"
                )
                self.assertFalse(result["accepted"])

    def test_same_ring_multiboot_clean_baseline_is_strict(self):
        acceptance = self.same_ring_multiboot_acceptance()
        records = self.module.same_ring
        cases = (
            (b"ordinary retained bytes", True),
            (records.ENTRY_PROOF, False),
            (records.USERSPACE_PROOF, False),
            (records.UNSAT_PROOF, False),
            (records.ENTRY_FAMILY + b"0" * 32 + b"]]\n", False),
            (records.UNSAT_FAMILY + b"\x00" * 16, False),
            (records.USERSPACE_PROOF[-12:] + b"suffix", False),
            (b"prefix" + records.USERSPACE_PROOF[:12], False),
        )
        for payload, expected_clean in cases:
            with self.subTest(payload=payload.hex()):
                result = self.module.classify_clean_baseline(
                    payload,
                    acceptance,
                )
                self.assertEqual(result["baseline_clean"], expected_clean)
                if not expected_clean:
                    self.assertTrue(
                        result["exact_record_count"] > 0
                        or result["family_count"] > 0
                        or result["integrity_issue"]
                    )

    def test_same_ring_multiboot_policy_is_not_manifest_selectable(self):
        acceptance = self.same_ring_multiboot_acceptance()
        mutations = (
            ("policy_id", "0" * 32),
            ("decoder", self.module.SAME_RING_DECODER),
            ("accepted_identity", "USERSPACE_CALLBACK_REACHED"),
            ("minimum_exact_count", 2),
        )
        for name, value in mutations:
            changed = copy.deepcopy(acceptance)
            changed[name] = value
            with self.subTest(name=name):
                with self.assertRaises(self.module.EvidenceError):
                    self.module.validate_acceptance(changed)

    def test_same_ring_multiboot_reuses_pinned_candidate_contract(self):
        bundle = self.same_ring_offline_bundle()
        bundle["acceptance"] = self.same_ring_multiboot_acceptance(
            bundle["payloads"]["run_manifest"],
            bundle["payloads"]["static_check"],
        )
        result = self.module.verify_offline_contract(**bundle)
        self.assertEqual(
            result["schema"],
            "device_action_f1_same_ring_multiboot_offline_contract_v1",
        )
        self.assertEqual(
            result["policy_id"], self.module.SAME_RING_MULTIBOOT_POLICY_ID
        )
        self.assertEqual(result["minimum_exact_count"], 1)
        self.assertTrue(result["verified"])

    def test_same_ring_acceptance_is_not_manifest_selectable(self):
        acceptance = self.same_ring_acceptance()
        mutations = (
            ("contract_id", "0" * 32),
            ("decoder", "another-decoder"),
            ("accepted_identity", "ENTRY_ONLY"),
        )
        for name, value in mutations:
            changed = copy.deepcopy(acceptance)
            changed[name] = value
            with self.subTest(name=name):
                with self.assertRaises(self.module.EvidenceError):
                    self.module.validate_acceptance(changed)
        changed = copy.deepcopy(acceptance)
        changed["records"]["userspace_hex"] = changed["records"]["entry_hex"]
        with self.assertRaises(self.module.EvidenceError):
            self.module.validate_acceptance(changed)

    def test_p260_acceptance_requires_versioned_terminal_stage(self):
        selected = self.module.source_contracts.p260
        decoder = self.module._latest_stage_decoder(selected.CONTRACT_ID, "E2")
        artifact = {
            "path": "workspace/private/contract.json",
            "size": 1,
            "sha256": "1" * 64,
        }
        acceptance = {
            "kind": self.module.E1_LATEST_STAGE_KIND,
            "source": self.module.CHECKPOINT_SOURCE,
            "decoder": decoder.DECODER_ID,
            "policy_id": decoder.POLICY_ID,
            "profile": "E2",
            "run_id": RUN_ID.hex(),
            "long_family_hex": decoder.model.LONG_FAMILY.hex(),
            "unsat_family_hex": decoder.model.UNSAT_FAMILY.hex(),
            "terminal_stage": 0x90,
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "source_contract_id": selected.CONTRACT_ID,
            "contract": {
                "candidate_static": artifact,
                "run_manifest": artifact,
                "static_check": artifact,
            },
        }
        result = self.module.validate_acceptance(acceptance)
        self.assertEqual(result["terminal_stage"], 0x90)

        stale = copy.deepcopy(acceptance)
        stale["terminal_stage"] = 0x8F
        with self.assertRaisesRegex(
            self.module.EvidenceError,
            "acceptance identity",
        ):
            self.module.validate_acceptance(stale)

    def test_same_ring_offline_contract_binds_candidate_and_records(self):
        bundle = self.same_ring_offline_bundle()
        result = self.module.verify_offline_contract(**bundle)
        self.assertEqual(
            result["schema"], "device_action_f1_same_ring_offline_contract_v2"
        )
        self.assertTrue(result["clean_baseline_required"])
        self.assertTrue(result["zero_is_ambiguous"])
        self.assertTrue(result["verified"])

    def test_same_ring_offline_contract_fails_closed_on_changed_static_claim(self):
        bundle = self.same_ring_offline_bundle()
        static_result = json.loads(bundle["payloads"]["static_check"])
        static_result["candidate"]["record_verification"]["image"][
            "unsat_count"
        ] = 0
        static_payload = json.dumps(
            static_result, sort_keys=True, separators=(",", ":")
        ).encode("ascii")
        bundle["payloads"]["static_check"] = static_payload
        bundle["receipts"]["static_check"] = {
            "size": len(static_payload),
            "sha256": hashlib.sha256(static_payload).hexdigest(),
        }
        bundle["acceptance"]["contract"]["static_check"] = {
            "path": "workspace/private/p219-static-check.json",
            **bundle["receipts"]["static_check"],
        }
        with self.assertRaisesRegex(
            self.module.EvidenceError,
            "Image record claim is invalid",
        ):
            self.module.verify_offline_contract(**bundle)


if __name__ == "__main__":
    unittest.main()
