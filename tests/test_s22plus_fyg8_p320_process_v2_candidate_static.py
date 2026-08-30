from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p320_process_v2_candidate_static.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p320_candidate_static", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("P3.20 candidate-static source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P320CandidateStaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.output = cls.module.DEFAULT_OUTPUT
        cls.payload = cls.output.read_bytes()
        cls.value = json.loads(cls.payload.decode("ascii"))

    def test_private_result_is_exact_h0_and_noncausal(self):
        info = self.output.lstat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertFalse(self.output.is_symlink())
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        self.assertEqual(self.module.canonical(self.value), self.payload)
        self.module.validate_result(self.value)
        self.assertEqual(self.value["run_id"], "c320f1e0a90b5e6d7c8a9b0c1d2e3f40")
        self.assertNotEqual(
            self.value["candidate"]["a"]["ap_tar_md5"]["sha256"],
            "db5666ac794dfbf6f64192d7ea341ed79ff330f03db74c57da5ef61f659032f6",
        )
        self.assertTrue(self.value["safety"]["host_only"])
        self.assertFalse(self.value["safety"]["candidate_success"])

    def test_delta_binds_final_builder_and_consumed_p319_predecessor(self):
        builder, _ = self.module._load_source(
            self.module.BUILDER_SOURCE, "P320 builder test"
        )
        builder_result_path = Path(builder.DEFAULT_OUTPUT_ROOT) / "result.json"
        adapter, _ = self.module._load_source(
            self.module.ADAPTER_SOURCE, "P320 adapter test"
        )
        observer_payload = Path(adapter.P320_OBSERVER_SOURCE).read_bytes()
        self.assertEqual(
            self.value["builder_result"]["sha256"],
            hashlib.sha256(
                builder_result_path.read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(self.value["predecessor"]["run_id"], self.module.P319_RUN_ID)
        self.assertEqual(
            self.value["predecessor"]["userspace_overlay_contract_id"],
            self.module.P319_OVERLAY,
        )
        self.assertEqual(
            self.value["source_closure"]["p320_observer_contract"]["sha256"],
            hashlib.sha256(observer_payload).hexdigest(),
        )
        self.assertTrue(self.value["candidate"]["byte_identical"])
        self.assertTrue(self.value["candidate"]["static_aarch64"])
        self.assertTrue(self.value["candidate"]["one_boot_img_lz4_member"])

    def test_observer_terminal_contract_is_explicit(self):
        self.assertEqual(
            self.value["result_contract_arming"],
            {
                "COMPLETE": {
                    "accepted": True,
                    "proof_class": "NONCAUSAL_SUCCESS_PATH",
                    "detail": 0x6724,
                    "receipt_zero": True,
                },
                "INCOMPLETE": {
                    "accepted": False,
                    "proof_class": "NO_PROOF_EXPERIMENT_PRECONDITION",
                    "detail": 0x6725,
                    "receipt_zero": True,
                },
                "AMBIGUOUS": {
                    "accepted": False,
                    "proof_class": "NO_PROOF_OBSERVER",
                    "detail": 0x6726,
                    "receipt_zero": False,
                },
            },
        )
        self.assertFalse(self.value["runtime_observation_contract"]["runtime_values_observed"])
        self.assertTrue(self.value["runtime_observation_contract"]["receipt_implies_ambiguous"])

    def test_mutated_builder_or_run_identity_is_rejected(self):
        for key, replacement in (
            ("run_id", self.module.P319_RUN_ID),
            ("builder_result", {"path": "foreign", "size": 1, "sha256": "0" * 64}),
        ):
            with self.subTest(key=key):
                value = copy.deepcopy(self.value)
                value[key] = replacement
                with self.assertRaises(self.module.StaticContractError):
                    self.module.validate_result(value)


if __name__ == "__main__":
    unittest.main()
