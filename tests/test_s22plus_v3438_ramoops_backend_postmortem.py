import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3438_ramoops_backend_postmortem.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_v3438_ramoops_backend_postmortem", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3438RamoopsBackendPostmortemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.root = cls.module.repo_root()
        cls.result = cls.module.build_analysis(cls.root)

    def test_host_only_verdict(self):
        self.assertEqual(
            self.result["verdict"],
            "HOST_POSTMORTEM_PASS_V3437_BACKEND_GATE_FALSE_NEGATIVE",
        )
        self.assertEqual(
            self.result["safety"],
            {
                "host_only": True,
                "device_contact": False,
                "image_build": False,
                "flash": False,
                "panic": False,
                "live_authorized": False,
            },
        )

    def test_committed_output_is_current(self):
        committed = (self.root / self.module.OUTPUT).read_text(encoding="utf-8")
        expected = json.dumps(self.result, indent=2, sort_keys=True) + "\n"
        self.assertEqual(committed, expected)

    def test_platform_creation_path_explicitly_allows_ramoops(self):
        proof = self.result["source_proof"]["platform_device_creation"]
        self.assertTrue(proof["reserved_memory_allowlist_contains_ramoops"])
        self.assertTrue(proof["available_matching_nodes_are_created"])
        self.assertEqual(proof["initcall"], "arch_initcall_sync")

    def test_parameter_update_is_after_successful_registration(self):
        proof = self.result["source_proof"]["ramoops_probe_success_order"]
        self.assertTrue(proof["module_parameters_update_only_after_pstore_register_success"])
        self.assertEqual(proof["source_lines"], sorted(proof["source_lines"]))
        self.assertEqual(
            self.result["v3437_observation"]["candidate_parameters"],
            self.module.EXPECTED_PARAMETERS,
        )

    def test_running_kernel_contains_exact_success_and_failure_strings(self):
        strings = self.result["source_proof"]["running_kernel_strings"]
        self.assertTrue(all(strings.values()))

    def test_early_log_was_outside_retained_ring(self):
        evidence = self.result["v3437_observation"]["last_kmsg"]
        self.assertTrue(evidence["duplicate_reads_match"])
        self.assertEqual(evidence["size"], 2097136)
        self.assertGreater(evidence["first_retained_timestamp_seconds"], 3.0)
        self.assertFalse(evidence["registration_log_retained"])
        self.assertFalse(evidence["using_log_retained"])

    def test_helper_gate_is_a_false_negative(self):
        postmortem = self.result["gate_postmortem"]
        self.assertTrue(postmortem["capture_regex_accepts_registered_or_using"])
        self.assertTrue(postmortem["final_predicate_requires_registered_only"])
        self.assertTrue(postmortem["early_success_logs_absent_after_ring_wrap"])
        self.assertTrue(postmortem["post_register_side_effect_observed"])
        self.assertEqual(
            postmortem["backend_registration_conclusion"],
            "PROVEN_BY_POST_REGISTER_PARAMETER_UPDATE",
        )
        self.assertEqual(
            postmortem["technical_interpretation"],
            "FALSE_NEGATIVE_LOG_ONLY_BACKEND_GATE",
        )

    def test_contract_result_remains_historical(self):
        observation = self.result["v3437_observation"]
        self.assertEqual(observation["contract_result"], "FAIL_PREPANIC_GATE_ROLLBACK")
        self.assertFalse(observation["panic_attempted"])
        self.assertEqual(observation["final_state"], "CLASSIFIED")

    def test_stock_backend_competes_later_from_module_109(self):
        backend = self.result["stock_competing_backend"]
        self.assertEqual(
            backend["live_readonly_snapshot"]["pstore_backend"],
            "samsung,pstore_pmsg",
        )
        self.assertEqual(backend["live_readonly_snapshot"]["mem_size"], "0")
        self.assertEqual(backend["modules_load_positions"]["sec_pmsg.ko"], 109)
        self.assertTrue(all(backend["sec_pmsg_module"].values()))
        self.assertIn("precedes", backend["ordering_inference"])

    def test_next_unit_requires_fresh_policy(self):
        next_unit = self.result["next_unit"]
        self.assertEqual(next_unit["live_status"], "NOT_AUTHORIZED")
        self.assertFalse(next_unit["candidate_rebuild"])
        self.assertTrue(next_unit["same_dtbo_reuse_requires_fresh_exception"])

    def test_source_has_no_live_transport(self):
        source = (self.root / SCRIPT).read_text(encoding="utf-8")
        self.assertNotIn("adb ", source)
        self.assertNotIn("odin4 ", source)
        self.assertNotIn("--live", source)
        self.assertNotIn("reboot(", source)


if __name__ == "__main__":
    unittest.main()
