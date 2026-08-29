from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import stat
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_process_v2_candidate_static.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p319_process_v2_candidate_static", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.19 candidate-static source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P319ProcessV2CandidateStaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.output = cls.module.DEFAULT_OUTPUT
        cls.payload = cls.output.read_bytes()
        cls.value = json.loads(cls.payload.decode("ascii"))

    def mutated(self):
        return copy.deepcopy(self.value)

    def test_private_result_is_exact_and_host_only(self):
        info = self.output.lstat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertFalse(self.output.is_symlink())
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        self.assertEqual(len(self.payload), 35_309)
        self.assertEqual(
            hashlib.sha256(self.payload).hexdigest(),
            "d00f422e46c55c15795c171ef893d8d6a01e441e00adebbaae2d7316af859fab",
        )
        self.assertEqual(self.module.canonical(self.value), self.payload)
        self.module.validate_result(self.value)
        self.assertEqual(self.value["schema"], self.module.SCHEMA)
        self.assertEqual(self.value["verdict"], self.module.VERDICT)
        self.assertFalse(self.value["ready_manifest_created"])
        self.assertFalse(self.value["run_manifest_created"])
        self.assertFalse(self.value["approval_created"])
        self.assertIs(self.value["safety"]["host_only"], True)
        for name in (
            "device_contact",
            "device_write",
            "odin_invoked",
            "odin_transfer",
            "flash",
            "partition_write",
            "live_authorized",
            "d0_authorized",
            "d1_authorized",
            "f1_authorized",
            "replay_authorized",
            "causal_result_allowed",
            "candidate_success",
        ):
            self.assertIs(self.value["safety"][name], False)

    def test_integration_loader_executes_stable_source_not_cached_bytecode(self):
        source = inspect.getsource(self.module.load_local)
        self.assertIn("stable_bytes(", source)
        self.assertIn("_StableSourceFinder", source)
        self.assertIn("importlib.import_module", source)
        self.assertNotIn("spec_from_file_location", source)

    def test_candidate_static_self_binds_its_exact_validator_source(self):
        authority = self.value["authority_source"]
        source = ROOT / authority["path"]
        payload = source.read_bytes()
        self.assertEqual(authority["size"], len(payload))
        self.assertEqual(authority["sha256"], hashlib.sha256(payload).hexdigest())

    def test_exact_regeneration_is_byte_identical(self):
        regenerated = self.module.canonical(self.module.build_result())
        self.assertEqual(regenerated, self.payload)

    def test_validation_rebuilds_the_bound_integration_receipt(self):
        original_load = self.module.load_local

        class DriftedIntegration:
            def __init__(self, wrapped):
                self.wrapped = wrapped

            def __getattr__(self, name):
                return getattr(self.wrapped, name)

            def build_result(self):
                result = self.wrapped.build_result()
                result["decision"] = "FORGED"
                return result

        def drifted_load(path, name):
            loaded = original_load(path, name)
            if path == self.module.INTEGRATION_SOURCE:
                return DriftedIntegration(loaded)
            return loaded

        with mock.patch.object(self.module, "load_local", side_effect=drifted_load):
            with self.assertRaisesRegex(
                self.module.StaticContractError, "not byte-reproducible"
            ):
                self.module.validate_result(self.value)

    def test_three_real_terminal_paths_are_armed_without_causal_promotion(self):
        rows = self.value["result_contract_arming"]["admitted_terminals"]
        self.assertEqual(
            [(row["state"], row["proof_class"], row["accepted"]) for row in rows],
            [
                ("COMPLETE", "NONCAUSAL_SUCCESS_PATH", True),
                ("INCOMPLETE", "NO_PROOF_EXPERIMENT_PRECONDITION", False),
                ("AMBIGUOUS", "NO_PROOF_OBSERVER", False),
            ],
        )
        runtime = self.value["runtime_observation_contract"]
        self.assertFalse(runtime["runtime_values_observed"])
        self.assertFalse(runtime["causal_result_allowed"])
        self.assertFalse(runtime["candidate_success"])
        self.assertFalse(runtime["mux_result_claimable"])
        self.assertFalse(runtime["host_silent_claimable"])

    def test_future_runtime_witnesses_are_required_but_not_preflight_facts(self):
        witnesses = self.value["runtime_observation_contract"]["witnesses"]
        self.assertEqual(tuple(sorted(witnesses)), self.module.RUNTIME_WITNESSES)
        for item in witnesses.values():
            self.assertIs(item["required"], True)
            self.assertEqual(item["status"], "PENDING_FRESH_CANDIDATE_RUN")
            self.assertIs(item["accepted_as_preflight_fact"], False)

    def test_current_candidate_and_preflight_authorities_are_bound(self):
        self.assertEqual(
            self.value["candidate"]["plan"],
            {
                "count": 73,
                "eud_index": 38,
                "overlay_delta": ["s22plus_dwc3_event_latch.ko"],
            },
        )
        self.assertEqual(
            self.value["candidate"]["artifacts"]["candidate"]["ap_tar_md5"]["sha256"],
            "db5666ac794dfbf6f64192d7ea341ed79ff330f03db74c57da5ef61f659032f6",
        )
        self.assertTrue(self.value["preflight"]["fresh_baseline"]["authoritative"])
        self.assertEqual(
            self.value["preflight"]["consumed_candidate_registry"]["status"],
            "PRESENT",
        )
        self.assertEqual(
            self.value["preflight"]["download_request_recovery"]["status"],
            "PASS_HOST_ONLY_RUNNER_FIXTURES",
        )

    def test_boolean_integer_substitution_is_rejected(self):
        value = self.mutated()
        value["runtime_observation_contract"]["witnesses"]["module_results"][
            "accepted_as_preflight_fact"
        ] = 0
        with self.assertRaisesRegex(self.module.StaticContractError, "differs"):
            self.module.validate_result(value)

    def test_terminal_proof_class_relabel_is_rejected(self):
        value = self.mutated()
        value["result_contract_arming"]["admitted_terminals"][0][
            "proof_class"
        ] = "PROVED"
        with self.assertRaisesRegex(self.module.StaticContractError, "differs"):
            self.module.validate_result(value)

    def test_candidate_plan_drift_is_rejected(self):
        value = self.mutated()
        value["candidate"]["plan"]["eud_index"] = 37
        with self.assertRaisesRegex(self.module.StaticContractError, "differs"):
            self.module.validate_result(value)

    def test_candidate_plan_float_substitution_is_rejected(self):
        mutations = (
            ("plan_count", ("candidate", "plan", "count"), 73.0),
            ("plan_eud", ("candidate", "plan", "eud_index"), 38.0),
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
                value = self.mutated()
                target = value
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = replacement
                with self.assertRaisesRegex(self.module.StaticContractError, "differs"):
                    self.module.validate_result(value)

    def test_candidate_artifact_drift_is_rejected(self):
        value = self.mutated()
        value["candidate"]["artifacts"]["candidate"]["ap_tar_md5"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(self.module.StaticContractError, "differs"):
            self.module.validate_result(value)

    def test_integration_identity_and_adapter_sources_are_exact(self):
        self.assertEqual(
            self.value["integration"]["receipt"],
            {
                "path": (
                    "workspace/private/outputs/s22plus_fyg8_p319/"
                    "process-v2-integration-qualification-v2-20260830-16/result.json"
                ),
                **self.module.INTEGRATION_IDENTITY,
            },
        )
        self.assertEqual(
            set(self.value["adapter_source_receipts"]),
            {"stock_process_v2_adapter", "p310_carrier_model", "p308_telemetry_spec"},
        )


if __name__ == "__main__":
    unittest.main()
