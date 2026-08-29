from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import py_compile
import stat
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
REPORT = ROOT / (
    "docs/reports/"
    "S22PLUS_FYG8_P319_PROCESS_V2_OFFLINE_READY_H0_2026-08-30.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import prepare_s22plus_fyg8_p319_process_v2 as promotion  # noqa: E402
import prepare_s22plus_fyg8_p319_ready_manifest as ready  # noqa: E402


class P319ProcessV2ReadyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.static_payload = promotion.stable_bytes(
            promotion.DEFAULT_CANDIDATE_STATIC,
            "P3.19 candidate-static",
            2 * 1024 * 1024,
        )
        cls.static_value = json.loads(cls.static_payload.decode("ascii"))
        cls.payloads, cls.verification = promotion.build()
        parent = ROOT / "workspace/private/outputs/s22plus_fyg8_p319"
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="p319-ready-test-", dir=parent
        )
        cls.promotion_root = Path(cls.temporary.name) / "promotion"
        promotion.publish(cls.promotion_root, cls.payloads)
        cls.manifest, cls.manifest_payload = ready.build(
            ready.DEFAULT_PROMOTION,
            ready.DEFAULT_CANDIDATE_AP,
            ready.DEFAULT_ROLLBACK_AP,
            ready.DEFAULT_TARGET_PROFILE,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_candidate_static_registration_is_exact_and_noncausal(self):
        checked = evidence._validate_p319_candidate_static(  # noqa: SLF001
            self.static_value
        )
        self.assertEqual(checked["schema"], evidence.P319_CANDIDATE_STATIC_SCHEMA)
        self.assertEqual(
            checked["verdict"], evidence.P319_CANDIDATE_STATIC_VERDICT
        )
        self.assertFalse(
            checked["runtime_observation_contract"]["causal_result_allowed"]
        )
        self.assertFalse(
            checked["runtime_observation_contract"]["candidate_success"]
        )

    def test_offline_contract_binds_exact_three_artifacts(self):
        self.assertEqual(
            self.verification["schema"],
            "device_action_f1_p319_stock_offline_contract_v1",
        )
        self.assertTrue(self.verification["verified"])
        self.assertFalse(self.verification["runtime_values_observed"])
        self.assertTrue(self.verification["complete_is_noncausal"])
        self.assertFalse(self.verification["causal_result_allowed"])
        self.assertFalse(self.verification["candidate_success"])
        self.assertEqual(
            self.verification["candidate_static_sha256"],
            hashlib.sha256(self.static_payload).hexdigest(),
        )

    def test_promotion_artifacts_are_canonical_and_exact(self):
        self.assertEqual(set(self.payloads), {
            "candidate_static", "run_manifest", "static_check"
        })
        run_manifest = json.loads(self.payloads["run_manifest"])
        static_check = json.loads(self.payloads["static_check"])
        self.assertEqual(promotion.canonical(run_manifest), self.payloads["run_manifest"])
        self.assertEqual(promotion.canonical(static_check), self.payloads["static_check"])
        self.assertFalse(
            run_manifest["observation_contract"]["runtime_values_preflighted"]
        )
        self.assertTrue(
            run_manifest["observation_contract"]["complete_is_noncausal"]
        )
        self.assertFalse(static_check["candidate"]["runtime_values_observed"])
        self.assertFalse(static_check["safety"]["candidate_success"])

    def test_published_promotion_is_exact_regeneration(self):
        filenames = {
            "candidate_static": "candidate-static.json",
            "run_manifest": "run-manifest.json",
            "static_check": "static-check-result.json",
        }
        reopened = {
            name: promotion.stable_bytes(
                promotion.DEFAULT_OUTPUT / filename,
                f"published P3.19 {name}",
                2 * 1024 * 1024,
            )
            for name, filename in filenames.items()
        }
        self.assertEqual(reopened, self.payloads)

    def test_exact_ap_is_independently_decoded(self):
        ap = promotion.stable_bytes(
            promotion.DEFAULT_CANDIDATE_AP, "candidate AP", 64 * 1024 * 1024
        )
        _info, frame = promotion.boot_verify.parse_ap_tar_md5(ap)
        result = evidence.validate_e2_ap_payload(
            frame, self.verification["ap_payload_closure"]
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["rootfs_entry_count"], 23)

    def test_ap_mutation_is_rejected(self):
        ap = promotion.stable_bytes(
            promotion.DEFAULT_CANDIDATE_AP, "candidate AP", 64 * 1024 * 1024
        )
        _info, frame = promotion.boot_verify.parse_ap_tar_md5(ap)
        changed = bytearray(frame)
        changed[-1] ^= 1
        with self.assertRaisesRegex(evidence.EvidenceError, "boot member differs"):
            evidence.validate_e2_ap_payload(
                bytes(changed), self.verification["ap_payload_closure"]
            )

    def test_bool_integer_runtime_substitution_is_rejected(self):
        value = copy.deepcopy(self.static_value)
        value["runtime_observation_contract"]["witnesses"]["module_results"][
            "accepted_as_preflight_fact"
        ] = 0
        with self.assertRaises(evidence.EvidenceError):
            evidence._validate_p319_candidate_static(value)  # noqa: SLF001

    def test_forged_candidate_static_provenance_is_rederived_and_rejected(self):
        mutations = {
            "integration": lambda value: value["integration"]["receipt"].__setitem__(
                "sha256", "0" * 64
            ),
            "target": lambda value: value["candidate"]["identity"]["target"].__setitem__(
                "model", "foreign"
            ),
            "source_keys": lambda value: value["candidate"]["identity"]["closure"][
                "source_keys"
            ].__setitem__("sha256", "0" * 64),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                value = copy.deepcopy(self.static_value)
                mutate(value)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "authority rejected"
                ):
                    evidence._validate_p319_candidate_static(value)  # noqa: SLF001

    def test_terminal_relabel_is_rejected(self):
        value = copy.deepcopy(self.static_value)
        value["result_contract_arming"]["admitted_terminals"][0][
            "proof_class"
        ] = "PROVED"
        with self.assertRaisesRegex(evidence.EvidenceError, "arming differs"):
            evidence._validate_p319_candidate_static(value)  # noqa: SLF001

    def test_plan_and_artifact_drift_are_rejected(self):
        value = copy.deepcopy(self.static_value)
        value["candidate"]["plan"]["eud_index"] = 37
        with self.assertRaisesRegex(evidence.EvidenceError, "plan differs"):
            evidence._validate_p319_candidate_static(value)  # noqa: SLF001
        value = copy.deepcopy(self.static_value)
        value["candidate"]["artifacts"]["candidate"]["ap_tar_md5"][
            "sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(evidence.EvidenceError, "artifact identity differs"):
            evidence._validate_p319_candidate_static(value)  # noqa: SLF001

    def test_ready_manifest_is_verified_but_grants_no_f1_authority(self):
        self.assertEqual(self.manifest["status"], "ready-for-f1-approval")
        self.assertNotIn("candidate_observer", self.manifest["observation"])
        self.assertEqual(
            self.manifest["observation"]["acceptance"][
                "userspace_overlay_contract_id"
            ],
            evidence.P319_STOCK_OVERLAY_CONTRACT_ID,
        )
        self.assertEqual(
            self.manifest["observation"]["acceptance"]["contract"].keys(),
            {"candidate_static", "run_manifest", "static_check"},
        )
        self.assertEqual(
            json.loads(self.manifest_payload)["manifest_id"],
            ready.DEFAULT_MANIFEST_ID,
        )

    def test_ready_manifest_rejects_boolean_minimum_success_count(self):
        mutations = {
            "minimum_bool": ("minimum_success_count", True),
            "minimum_float": ("minimum_success_count", 1.0),
            "terminal_float": ("terminal_stage", 147.0),
        }
        for label, (field, replacement) in mutations.items():
            with self.subTest(label=label):
                value = copy.deepcopy(self.manifest)
                value["observation"]["acceptance"][field] = replacement
                with self.assertRaises(ready.ReadyManifestError):
                    ready.verify_bundle(value)

    def test_shared_verifier_rejects_float_module_plan_substitution(self):
        mutations = (
            ("candidate_count", ("candidate", "plan", "count"), 73.0),
            ("candidate_eud", ("candidate", "plan", "eud_index"), 38.0),
            (
                "closure_count",
                ("candidate", "identity", "closure", "module_plan", "count"),
                73.0,
            ),
            (
                "closure_eud",
                ("candidate", "identity", "closure", "module_plan", "eud_index"),
                38.0,
            ),
        )
        for label, keys, replacement in mutations:
            with self.subTest(label=label):
                value = copy.deepcopy(self.static_value)
                target = value
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = replacement
                with self.assertRaises(evidence.EvidenceError):
                    evidence._validate_p319_candidate_static(value)  # noqa: SLF001

    def test_shared_verifier_rejects_integer_boolean_substitution(self):
        mutations = (
            ("safety_host", ("safety", "host_only"), 1),
            ("safety_device", ("safety", "device_contact"), 0),
            (
                "runtime_post_run",
                ("runtime_observation_contract", "post_run_classification_only"),
                1,
            ),
            (
                "runtime_candidate",
                ("runtime_observation_contract", "candidate_success"),
                0,
            ),
        )
        for label, keys, replacement in mutations:
            with self.subTest(label=label):
                value = copy.deepcopy(self.static_value)
                target = value
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = replacement
                with self.assertRaises(evidence.EvidenceError):
                    evidence._validate_p319_candidate_static(value)  # noqa: SLF001

    def test_p319_adapter_dependency_loader_ignores_same_stamp_stale_pyc(self):
        module_name = "s22plus_fyg8_p319_stock_process_v2_adapter"
        payloads = evidence._stable_local_import_closure(  # noqa: SLF001
            module_name, REVALIDATION
        )
        with tempfile.TemporaryDirectory(prefix="p319-stale-pyc-") as name:
            root = Path(name) / "workspace/public/src/scripts/revalidation"
            root.mkdir(parents=True)
            for dependency, payload in payloads.items():
                (root / f"{dependency}.py").write_bytes(payload)
            carrier = root / "s22plus_fyg8_p310_carrier_model.py"
            fixed_ns = 1_700_000_000_000_000_000
            os.utime(carrier, ns=(fixed_ns, fixed_ns))
            py_compile.compile(str(carrier), doraise=True)
            original = carrier.read_bytes()
            mutated = original.replace(b'b"S22E1L2|"', b'b"F0RE1L2|"')
            self.assertEqual(len(mutated), len(original))
            self.assertNotEqual(mutated, original)
            carrier.write_bytes(mutated)
            os.utime(carrier, ns=(fixed_ns, fixed_ns))
            loaded = evidence._load_stable_local_module(  # noqa: SLF001
                module_name, root
            )
            self.assertEqual(loaded.LONG_FAMILY, b"F0RE1L2|")

    def test_published_ready_manifest_is_exact_regeneration(self):
        info = ready.DEFAULT_OUTPUT.lstat()
        observed_mode = stat.S_IMODE(info.st_mode)
        self.assertIn(observed_mode, {0o644, 0o664})
        payload = ready.stable_bytes(
            ready.DEFAULT_OUTPUT,
            "published P3.19 ready manifest",
            1024 * 1024,
            mode=observed_mode,
        )
        self.assertEqual(payload, self.manifest_payload)
        self.assertEqual(info.st_nlink, 1)

    def test_report_goal_and_ledger_keep_ready_non_authoritative(self):
        report = REPORT.read_text(encoding="utf-8")
        goal = GOAL.read_text(encoding="utf-8")
        ledger = LEDGER.read_text(encoding="utf-8")
        for token in (
            "15,075 bytes / `608799f12b16aab5",
            "13,190 bytes / `4a18cf1148a7c8bd",
            "126,135 bytes / `1506e8988dfe2c9",
            "35,309 bytes / `d00f422e46c55c15",
            "2,432 bytes / `e6c758460f45e52b",
            "PASS_GO_P319_PROCESS_V2_OFFLINE_READY_CENSUS_DECOUPLE_H0_CAPABILITY_V1",
            "creates no approval",
        ):
            self.assertIn(token, report)
        self.assertIn("`ready-for-f1-approval`", goal)
        self.assertIn("h0-process-v2-offline-ready-51", ledger)
        self.assertIn("h0-process-v2-offline-ready-census-decouple-review-52", ledger)
        self.assertIn("75/58/17 across 425 rows", ledger)

    def test_temporary_outputs_are_private_and_no_clobber(self):
        for path in self.promotion_root.iterdir():
            info = path.lstat()
            self.assertTrue(stat.S_ISREG(info.st_mode))
            self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
            self.assertEqual(info.st_nlink, 1)
        with self.assertRaisesRegex(promotion.PromotionError, "already exists"):
            promotion.publish(self.promotion_root, self.payloads)


if __name__ == "__main__":
    unittest.main()
