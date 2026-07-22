import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"


def load_module(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_tested", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P234ProcessV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        cls.module = load_module("prepare_s22plus_fyg8_p234_process_v2")
        cls.evidence = cls.module.evidence
        cls.core = load_module("device_action_f1_v2")

    @staticmethod
    def identity(seed, size=123):
        return {"size": size, "sha256": hashlib.sha256(seed).hexdigest()}

    def fixture(self):
        run_id = hashlib.sha256(b"P234-PROCESS-V2-TEST").hexdigest()[:32]
        ap = self.identity(b"ap", 456)
        identities = {
            "artifact_result": self.identity(b"artifact-result"),
            "boot_img": self.identity(b"boot"),
            "boot_img_lz4": self.identity(b"lz4"),
            "ap_tar_md5": ap,
        }
        userspace = {
            "result": self.identity(b"userspace-result"),
            "init": self.identity(b"init"),
            "child": self.identity(b"child"),
            "two_build_byte_identical": True,
            "verified": True,
        }
        static_result = {
            "schema": self.module.static_checker.SCHEMA,
            "target": self.module.TARGET,
            "verdict": self.module.static_checker.VERDICT,
            "candidate_contract": {
                "schema": self.evidence.E1_LATEST_STAGE_CANDIDATE_CONTRACT_SCHEMA,
                "target": self.module.TARGET,
                "verdict": self.evidence.E1_LATEST_STAGE_CANDIDATE_CONTRACT_VERDICT,
                "profile": "E1A",
                "profile_number": 1,
                "run_id": run_id,
                "unsat_record_hex": self.evidence.e1_latest_stage.model.unsat_record(
                    "E1A", bytes.fromhex(run_id)
                ).hex(),
                "unsat_tag_hex": self.evidence.e1_latest_stage.model.unsat_record(
                    "E1A", bytes.fromhex(run_id)
                )[len(self.evidence.e1_latest_stage.model.UNSAT_FAMILY) :].hex(),
                "decoder_id": self.evidence.E1_LATEST_STAGE_DECODER,
                "decoder_policy_id": self.evidence.e1_latest_stage.POLICY_ID,
                "intent": self.identity(b"candidate-intent"),
                "patch": {
                    **self.identity(b"candidate-patch"),
                    "targets": sorted(self.evidence.E1_LATEST_STAGE_BASE_FILES),
                    "base_files": self.evidence.E1_LATEST_STAGE_BASE_FILES,
                    "patched_files": {
                        name: hashlib.sha256(name.encode("ascii")).hexdigest()
                        for name in self.evidence.E1_LATEST_STAGE_BASE_FILES
                    },
                    "config_lines": [
                        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
                        "CONFIG_S22PLUS_FYG8_E1_PROFILE=1",
                        f'CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{run_id}"',
                        "CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX=\""
                        + self.evidence.e1_latest_stage.model.unsat_record(
                            "E1A", bytes.fromhex(run_id)
                        )[len(self.evidence.e1_latest_stage.model.UNSAT_FAMILY) :].hex()
                        + "\"",
                    ],
                    "clean_apply": True,
                    "verified": True,
                },
                "base_files": self.evidence.E1_LATEST_STAGE_BASE_FILES,
                "patched_files": {
                    name: hashlib.sha256(name.encode("ascii")).hexdigest()
                    for name in self.evidence.E1_LATEST_STAGE_BASE_FILES
                },
                "config_lines": [
                    "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
                    "CONFIG_S22PLUS_FYG8_E1_PROFILE=1",
                    f'CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{run_id}"',
                    "CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX=\""
                    + self.evidence.e1_latest_stage.model.unsat_record(
                        "E1A", bytes.fromhex(run_id)
                    )[len(self.evidence.e1_latest_stage.model.UNSAT_FAMILY) :].hex()
                    + "\"",
                ],
                "reachable_record_contract": {
                    "reachable_slot_variants": 32769,
                    "profiles": ["E1A"],
                    "checked_run_ids": {"E1A": run_id},
                    "adjacent_slot_combinations_verified": True,
                    "zero_crc_count": 0,
                    "family_collision_count": 0,
                    "decoder_policy_id": self.evidence.e1_latest_stage.POLICY_ID,
                    "verified": True,
                },
                "verified": True,
                "safety": {
                    "host_only": True,
                    "device_contact": False,
                    "device_write": False,
                    "odin_invoked": False,
                    "live_authorized": False,
                },
            },
            "build_repro": {
                "result": self.identity(b"build-repro-result"),
                "image": self.identity(b"Image"),
                "fresh_reverification": True,
                "two_clean_builds_byte_identical": True,
                "linked_audit_verified": True,
            },
            "candidate": {
                "artifacts": identities,
                "candidate_b_artifacts": copy.deepcopy(identities),
                "base_boot": self.identity(b"base-boot"),
                "ap": {
                    "tar_md5": "a" * 32,
                    "member": {
                        "name": "boot.img.lz4",
                        "size": identities["boot_img_lz4"]["size"],
                        "mode": 0o644,
                        "uid": 0,
                        "gid": 0,
                        "mtime": 0,
                        "uname": "",
                        "gname": "",
                    },
                },
                "fixed_interval": {
                    "kernel_start": self.evidence.E1_LATEST_STAGE_KERNEL_INTERVAL[0],
                    "kernel_end_exclusive": self.evidence.E1_LATEST_STAGE_KERNEL_INTERVAL[1],
                    "header_preserved": True,
                    "ramdisk_preserved": True,
                    "outside_interval_changed_byte_count": 0,
                    "verified": True,
                },
                "userspace": userspace,
                "verified": True,
                "boot_only_ap": True,
                "independent_reconstruction": True,
                "independent_lz4_roundtrip": True,
                "independent_magiskboot_unpack": True,
                "writer_exclusion_verified": True,
                "two_package_builds_byte_identical": True,
                "manifest_absent": True,
            },
            "tools": {
                "lz4": self.identity(b"lz4"),
                "magiskboot": self.identity(b"magiskboot"),
                "qemu_aarch64": self.identity(b"qemu-aarch64"),
            },
            "limits": [
                "host-only artifact qualification grants no D0, D1, F1, or live authority",
                "candidate execution and retained observation remain unproved",
            ],
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
        candidate_static_payload = (
            json.dumps(static_result, indent=2, sort_keys=True).encode("ascii") + b"\n"
        )
        candidate_static = self.module.receipt(candidate_static_payload)
        run_payload, process_static = self.module.derive(
            static_result, candidate_static, ap
        )
        payloads = {
            "candidate_static": candidate_static_payload,
            "run_manifest": run_payload,
            "static_check": process_static,
        }
        receipts = {
            name: self.module.receipt(payload) for name, payload in payloads.items()
        }
        acceptance = {
            "kind": self.evidence.E1_LATEST_STAGE_KIND,
            "source": self.evidence.CHECKPOINT_SOURCE,
            "decoder": self.evidence.E1_LATEST_STAGE_DECODER,
            "policy_id": self.evidence.e1_latest_stage.POLICY_ID,
            "profile": "E1A",
            "run_id": run_id,
            "long_family_hex": self.evidence.e1_latest_stage.model.LONG_FAMILY.hex(),
            "unsat_family_hex": self.evidence.e1_latest_stage.model.UNSAT_FAMILY.hex(),
            "terminal_stage": self.evidence.e1_latest_stage.model.PROFILE_TERMINALS[
                "E1A"
            ],
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "contract": {
                name: {"path": f"contracts/{name}.json", **value}
                for name, value in receipts.items()
            },
        }
        return static_result, candidate_static, ap, payloads, receipts, acceptance

    def coherently_repin_candidate_static(self, static_result, payloads, acceptance):
        forged_payload = (
            json.dumps(static_result, indent=2, sort_keys=True).encode("ascii") + b"\n"
        )
        forged_receipt = self.module.receipt(forged_payload)
        run_manifest = json.loads(payloads["run_manifest"])
        run_manifest["candidate_static"] = forged_receipt
        run_payload = self.module.canonical(run_manifest)
        process_static = json.loads(payloads["static_check"])
        process_static["candidate"]["artifacts"]["candidate_static"] = forged_receipt
        process_static["run_binding"] = {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        }
        repinned_payloads = {
            "candidate_static": forged_payload,
            "run_manifest": run_payload,
            "static_check": self.module.canonical(process_static),
        }
        receipts = {
            name: self.module.receipt(payload)
            for name, payload in repinned_payloads.items()
        }
        acceptance["contract"] = {
            name: {"path": f"contracts/{name}.json", **value}
            for name, value in receipts.items()
        }
        return repinned_payloads, receipts

    def test_promotion_and_offline_verifier_bind_exact_candidate(self):
        _static, candidate_static, ap, payloads, receipts, acceptance = self.fixture()
        result = self.evidence.verify_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=ap,
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["profile"], "E1A")
        self.assertEqual(result["candidate_ap_sha256"], ap["sha256"])
        self.assertEqual(
            result["candidate_static_sha256"], candidate_static["sha256"]
        )

    def test_offline_verifier_rejects_changed_candidate_ap(self):
        _static, _candidate_static, ap, payloads, receipts, acceptance = self.fixture()
        changed = copy.deepcopy(ap)
        changed["sha256"] = "f" * 64
        with self.assertRaises(self.evidence.EvidenceError):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=changed,
            )

    def test_offline_verifier_rejects_missing_candidate_static(self):
        _static, _candidate_static, ap, payloads, receipts, acceptance = self.fixture()
        payloads.pop("candidate_static")
        receipts.pop("candidate_static")
        acceptance["contract"].pop("candidate_static")
        with self.assertRaisesRegex(self.evidence.EvidenceError, "contract"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_coherently_forged_candidate_static(self):
        static, _candidate_static, ap, payloads, _receipts, acceptance = self.fixture()
        forged = copy.deepcopy(static)
        forged["build_repro"]["linked_audit_verified"] = False
        forged_payload = (
            json.dumps(forged, indent=2, sort_keys=True).encode("ascii") + b"\n"
        )
        forged_receipt = self.module.receipt(forged_payload)

        run_manifest = json.loads(payloads["run_manifest"])
        run_manifest["candidate_static"] = forged_receipt
        run_payload = self.module.canonical(run_manifest)
        process_static = json.loads(payloads["static_check"])
        process_static["candidate"]["artifacts"]["candidate_static"] = forged_receipt
        process_static["run_binding"] = {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        }
        payloads = {
            "candidate_static": forged_payload,
            "run_manifest": run_payload,
            "static_check": self.module.canonical(process_static),
        }
        receipts = {
            name: self.module.receipt(payload) for name, payload in payloads.items()
        }
        acceptance["contract"] = {
            name: {"path": f"contracts/{name}.json", **value}
            for name, value in receipts.items()
        }
        with self.assertRaisesRegex(self.evidence.EvidenceError, "build closure"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_false_reconstruction_proofs(self):
        for name in (
            "independent_reconstruction",
            "independent_lz4_roundtrip",
            "independent_magiskboot_unpack",
        ):
            with self.subTest(name=name):
                static, _candidate_static, ap, payloads, _receipts, acceptance = (
                    self.fixture()
                )
                static["candidate"][name] = False
                payloads, receipts = self.coherently_repin_candidate_static(
                    static, payloads, acceptance
                )
                with self.assertRaisesRegex(
                    self.evidence.EvidenceError, "artifact closure"
                ):
                    self.evidence.verify_offline_contract(
                        acceptance,
                        payloads=payloads,
                        receipts=receipts,
                        candidate_ap=ap,
                    )

    def test_offline_verifier_rejects_candidate_contract_shape_changes(self):
        for operation in ("omit", "extra"):
            with self.subTest(operation=operation):
                static, _candidate_static, ap, payloads, _receipts, acceptance = (
                    self.fixture()
                )
                if operation == "omit":
                    static["candidate_contract"].pop("base_files")
                else:
                    static["candidate_contract"]["unexpected"] = True
                payloads, receipts = self.coherently_repin_candidate_static(
                    static, payloads, acceptance
                )
                with self.assertRaisesRegex(self.evidence.EvidenceError, "keys"):
                    self.evidence.verify_offline_contract(
                        acceptance,
                        payloads=payloads,
                        receipts=receipts,
                        candidate_ap=ap,
                    )

    def test_offline_verifier_rejects_candidate_contract_value_change(self):
        static, _candidate_static, ap, payloads, _receipts, acceptance = self.fixture()
        static["candidate_contract"]["profile_number"] = 2
        payloads, receipts = self.coherently_repin_candidate_static(
            static, payloads, acceptance
        )
        with self.assertRaisesRegex(self.evidence.EvidenceError, "E1A-bound"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_candidate_contract_type_aliases(self):
        cases = (
            ("profile_number", True),
            ("zero_crc_count", False),
            ("family_collision_count", False),
            ("safety_host_only", 1),
            ("safety_device_contact", 0),
        )
        for name, value in cases:
            with self.subTest(name=name):
                static, _candidate_static, ap, payloads, _receipts, acceptance = (
                    self.fixture()
                )
                contract = static["candidate_contract"]
                if name == "profile_number":
                    contract[name] = value
                elif name.startswith("safety_"):
                    contract["safety"][name.removeprefix("safety_")] = value
                else:
                    contract["reachable_record_contract"][name] = value
                payloads, receipts = self.coherently_repin_candidate_static(
                    static, payloads, acceptance
                )
                with self.assertRaisesRegex(self.evidence.EvidenceError, "E1A-bound"):
                    self.evidence.verify_offline_contract(
                        acceptance,
                        payloads=payloads,
                        receipts=receipts,
                        candidate_ap=ap,
                    )

    def test_offline_verifier_rejects_cross_payload_identity_substitution(self):
        for name in ("image", "boot_image", "init", "child"):
            with self.subTest(name=name):
                _static, _candidate_static, ap, payloads, _receipts, acceptance = (
                    self.fixture()
                )
                process_static = json.loads(payloads["static_check"])
                process_static["candidate"]["artifacts"][name] = self.identity(
                    f"forged-{name}".encode("ascii"), 999
                )
                payloads["static_check"] = self.module.canonical(process_static)
                receipts = {
                    item: self.module.receipt(payload)
                    for item, payload in payloads.items()
                }
                acceptance["contract"] = {
                    item: {"path": f"contracts/{item}.json", **value}
                    for item, value in receipts.items()
                }
                with self.assertRaisesRegex(
                    self.evidence.EvidenceError, "does not bind"
                ):
                    self.evidence.verify_offline_contract(
                        acceptance,
                        payloads=payloads,
                        receipts=receipts,
                        candidate_ap=ap,
                    )

    def test_offline_verifier_rejects_omitted_candidate_static_structure(self):
        static, _candidate_static, ap, payloads, _receipts, acceptance = self.fixture()
        forged = copy.deepcopy(static)
        forged["candidate"].pop("candidate_b_artifacts")
        forged_payload = (
            json.dumps(forged, indent=2, sort_keys=True).encode("ascii") + b"\n"
        )
        forged_receipt = self.module.receipt(forged_payload)
        run_manifest = json.loads(payloads["run_manifest"])
        run_manifest["candidate_static"] = forged_receipt
        payloads["run_manifest"] = self.module.canonical(run_manifest)
        process_static = json.loads(payloads["static_check"])
        process_static["candidate"]["artifacts"]["candidate_static"] = forged_receipt
        process_static["run_binding"] = {
            "canonical_manifest_size": len(payloads["run_manifest"]),
            "canonical_manifest_sha256": hashlib.sha256(
                payloads["run_manifest"]
            ).hexdigest(),
            "verified": True,
        }
        payloads["candidate_static"] = forged_payload
        payloads["static_check"] = self.module.canonical(process_static)
        receipts = {
            item: self.module.receipt(payload) for item, payload in payloads.items()
        }
        acceptance["contract"] = {
            item: {"path": f"contracts/{item}.json", **value}
            for item, value in receipts.items()
        }
        with self.assertRaisesRegex(self.evidence.EvidenceError, "keys"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_noncanonical_manifest(self):
        _static, _candidate_static, ap, payloads, _receipts, acceptance = self.fixture()
        parsed = json.loads(payloads["run_manifest"])
        payloads["run_manifest"] = json.dumps(parsed, indent=2).encode("ascii")
        receipts = {
            name: self.module.receipt(payload) for name, payload in payloads.items()
        }
        acceptance["contract"] = {
            name: {"path": f"contracts/{name}.json", **value}
            for name, value in receipts.items()
        }
        with self.assertRaisesRegex(self.evidence.EvidenceError, "run manifest"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_offline_verifier_rejects_e1b_profile(self):
        _static, _candidate_static, ap, payloads, receipts, acceptance = self.fixture()
        acceptance["profile"] = "E1B"
        acceptance["terminal_stage"] = (
            self.evidence.e1_latest_stage.model.PROFILE_TERMINALS["E1B"]
        )
        with self.assertRaisesRegex(self.evidence.EvidenceError, "restricted to E1A"):
            self.evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=ap,
            )

    def test_promotion_rejects_unverified_writer_exclusion(self):
        static_result, candidate_static, ap, _payloads, _receipts, _acceptance = (
            self.fixture()
        )
        static_result["candidate"]["writer_exclusion_verified"] = False
        with self.assertRaisesRegex(self.module.PromotionError, "independently closed"):
            self.module.derive(static_result, candidate_static, ap)

    def test_approval_binding_excludes_unreachable_p234_build_tools(self):
        _static, _candidate_static, _ap, _payloads, _receipts, acceptance = (
            self.fixture()
        )
        sources = self.core.execution_critical_source_receipts(acceptance)
        self.assertIn("e1_latest_stage_decoder", sources)
        self.assertIn("e1_latest_stage_design_model", sources)
        self.assertNotIn("e1_latest_stage_static_checker", sources)
        self.assertNotIn("e1_candidate_static_checker", sources)
        self.assertNotIn("e1_process_v2_promotion", sources)


if __name__ == "__main__":
    unittest.main()
