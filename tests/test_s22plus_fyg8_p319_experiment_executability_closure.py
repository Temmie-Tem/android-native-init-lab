from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_experiment_executability_closure.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p319_experiment_executability_closure", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P3.19 closure auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319ExperimentExecutabilityClosureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.authority = cls.module.load_exact_authority()
        cls.result = cls.module.build_result(cls.authority)

    def test_closure_is_h0_and_runtime_witnesses_are_not_preflight_facts(self):
        result = self.result
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertEqual(result["status"], "PASS_SOURCE_CLOSURE_RUNTIME_GATES_PENDING")
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["causal_result_allowed"])
        self.assertFalse(result["candidate_success"])
        self.assertFalse(result["runtime_gate_satisfied"])
        repin = result["authority"]["contracts"]["process_v2_repin"]
        self.assertEqual(repin["old"]["size"], 33498)
        self.assertEqual(repin["old"]["sha256"], "72f1eb6115872683af6a374b37267193c9c730a51698e5adf30b328b75b68d9b")
        self.assertEqual(repin["new"]["size"], 36163)
        self.assertEqual(repin["new"]["sha256"], "26d9c8110e19ca4dba09418d07350cd051167423387a684f8deebf76c0843af1")
        self.assertEqual(repin["delta"], {"added_lines": 41, "removed_lines": 0, "added_bytes": 2665})
        self.assertFalse(repin["authority_expanded"])
        process = self.module.stable_bytes(self.module.PROCESS_CONTRACT, "Process-v2 test contract", maximum=2 * 1024 * 1024)
        self.module.validate_process_contract_repin(process)
        mutated = copy.deepcopy(repin)
        mutated["old"]["sha256"] = "0" * 64
        with self.assertRaises(self.module.AuditError):
            self.module.validate_process_contract_repin(process, mutated)
        outside_mutation = process.replace(b"## Recovery", b"## Recovery-mutated", 1)
        with self.assertRaisesRegex(
            self.module.AuditError, "predecessor reconstruction differs"
        ):
            self.module.validate_process_contract_repin(outside_mutation)
        section_mutation = process.replace(
            b"never replays the candidate", b"may replay the candidate", 1
        )
        with self.assertRaisesRegex(
            self.module.AuditError, "reviewed successor"
        ):
            self.module.validate_process_contract_repin(section_mutation)
        self.assertEqual(
            set(result["runtime_evaluability_witnesses"]),
            {
                "module_results",
                "vbusdet_irq_tuple",
                "initial_status_classification_probe",
                "retained_carrier",
            },
        )
        for item in result["runtime_evaluability_witnesses"].values():
            self.assertTrue(item["required"])
            self.assertEqual(item["status"], "PENDING_FRESH_CANDIDATE_RUN")
            self.assertFalse(item["accepted_as_preflight_fact"])

    def test_stock_roots_and_chain_replace_p317_diagnostic_root(self):
        result = self.result
        self.assertEqual(tuple(result["fixed_point"]["roots"]), self.module.P319_ROOTS)
        self.assertNotIn(self.module.P317_DIAGNOSTIC_PARENT, result["fixed_point"]["roots"])
        self.assertTrue(result["excluded_p317_diagnostic_parent"]["excluded_from_roots_edges_and_providers"])
        edges = result["fixed_point"]["deduplicated_edges"]
        self.assertTrue(any(
            edge["consumer"] == self.module.P319_MFD
            and edge.get("instantiator") == self.module.P317_I2C
            and edge["mechanism"] == "i2c_add_adapter_then_of_i2c_register_devices"
            for edge in edges
        ))
        self.assertTrue(any(
            edge["consumer"] == self.module.P319_PDIC
            and edge.get("instantiator") == self.module.P319_MFD
            and edge["mechanism"] == "mfd_add_devices(max77705_devs)"
            for edge in edges
        ))
        self.assertFalse(any(
            self.module.P317_DIAGNOSTIC_PARENT in repr(edge)
            or "s22plus_max77705_mux_diag" in repr(edge)
            for edge in edges
        ))

    def test_plan_eud_and_module_roles_are_exact(self):
        plan = self.result["plan"]
        self.assertEqual(plan["module_count"], 73)
        self.assertEqual(plan["eud_index"], 38)
        self.assertEqual(plan["module_order"]["i2c-msm-geni.ko"], 69)
        self.assertEqual(plan["module_order"]["spu_verify.ko"], 70)
        self.assertEqual(plan["module_order"]["mfd_max77705.ko"], 71)
        self.assertEqual(plan["module_order"]["pdic_max77705.ko"], 72)
        self.assertEqual(plan["module_roles"]["spu_verify.ko"], "link_only_closure")
        self.assertEqual(plan["module_roles"]["mfd_max77705.ko"], "stock_mfd_parent")
        self.assertEqual(plan["module_roles"]["pdic_max77705.ko"], "stock_pdic_child")

    def test_all_three_families_reenter_each_frontier(self):
        fixed = self.result["fixed_point"]
        self.assertTrue(fixed["p317_upstream_reexecution"]["reexecuted_from_exact_receipt"])
        self.assertFalse(fixed["p317_upstream_reexecution"]["diagnostic_root_reused"])
        self.assertEqual(tuple(fixed["relationship_families"]), self.module.FAMILIES)
        self.assertTrue(fixed["converged"])
        self.assertTrue(fixed["family_outputs_reenter_all_families"])
        self.assertTrue(fixed["every_frontier_node_evaluated_by_every_family"])
        for iteration in fixed["iterations"]:
            pairs = {
                (row["node"], row["family"])
                for row in iteration["family_evaluations"]
            }
            self.assertEqual(
                len(pairs), len(iteration["frontier"]) * len(self.module.FAMILIES)
            )
            for node in iteration["frontier"]:
                for family in self.module.FAMILIES:
                    self.assertIn((node, family), pairs)

    def test_p317_diagnostic_root_leakage_is_fail_closed(self):
        mutated = copy.deepcopy(self.result["fixed_point"])
        mutated["roots"].append(self.module.P317_DIAGNOSTIC_PARENT)
        with self.assertRaises(self.module.AuditError):
            self.module.validate_fixed_point(mutated)

    def test_missing_family_evaluation_is_fail_closed(self):
        mutated = copy.deepcopy(self.result["fixed_point"])
        mutated["iterations"][0]["family_evaluations"] = [
            row for row in mutated["iterations"][0]["family_evaluations"]
            if row["family"] != self.module.FAMILY_DRIVER
        ]
        with self.assertRaises(self.module.AuditError):
            self.module.validate_fixed_point(mutated)

    def test_root_only_iteration_is_fail_closed(self):
        mutated = copy.deepcopy(self.result["fixed_point"])
        mutated["iterations"] = [mutated["iterations"][0]]
        mutated["iteration_count"] = 1
        mutated["nodes"] = list(mutated["roots"])
        mutated["node_count"] = len(mutated["nodes"])
        mutated["deduplicated_edges"] = []
        mutated["deduplicated_edge_count"] = 0
        with self.assertRaises(self.module.AuditError):
            self.module.validate_fixed_point(mutated)

    def test_missing_stock_child_edge_is_fail_closed(self):
        mutated = copy.deepcopy(self.authority["p319_irq"])
        mutated["conclusion"]["mfd_publishes_max77705_usbc_child"] = False
        with self.assertRaises(self.module.AuditError):
            self.module.validate_stock_evidence(
                mutated,
                self.authority["p319_pdic"],
                self.authority["p319_materialization"],
            )

    def test_plan_mutation_is_fail_closed(self):
        mutated = copy.deepcopy(self.authority["p319_plan"])
        mutated["successor_plan"]["successor_plan_rows"][38]["index"] = 37
        with self.assertRaises(self.module.AuditError):
            self.module.validate_plan(
                mutated,
                self.authority["p319_materialization"],
                self.authority["p319_intent"],
                self.authority["p319_qualification"],
            )

    def test_receipt_identity_mutation_is_fail_closed(self):
        expected = self.module.EXPECTED_IDS["p319_irq"]
        original = self.authority["_raw"]["p319_irq"]
        changed = bytearray(original)
        changed[-2] = ord("0") if changed[-2] != ord("0") else ord("1")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_bytes(changed)
            with self.assertRaises(self.module.AuditError):
                self.module.stable_bytes(path, "mutated receipt", expected=expected)

    def test_publication_is_complete_fsynced_and_verified(self):
        payload = b'{"schema":"p319-test"}\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            self.module.publish_exclusive(path, payload)
            self.assertEqual(path.read_bytes(), payload)
            info = path.stat()
            self.assertEqual(info.st_size, len(payload))
            self.assertEqual(info.st_nlink, 1)
            self.assertEqual(info.st_mode & 0o777, 0o400)
            with self.assertRaises(self.module.AuditError):
                self.module.publish_exclusive(path, payload)

    def test_mfd_driver_name_and_probe_source_mutations_are_rejected(self):
        mfd = self.module.stable_bytes(
            self.module.MFD_SOURCE,
            "MFD source",
            expected=self.authority["p319_irq"]["inputs"]["max77705_mfd_source"],
            maximum=128 * 1024,
        ).decode("utf-8")
        header = self.module.stable_bytes(
            self.module.MFD_HEADER,
            "MFD header",
            expected=self.authority["p319_irq"]["inputs"]["max77705_mfd_header"],
            maximum=32 * 1024,
        ).decode("utf-8")
        pdic = self.module.stable_bytes(
            self.module.PDIC_SOURCE,
            "PDIC source",
            expected=self.authority["p319_irq"]["inputs"]["max77705_usbc_source"],
            maximum=192 * 1024,
        ).decode("utf-8")
        with self.assertRaises(self.module.AuditError):
            self.module.validate_stock_source_texts(
                mfd.replace(".name\t= MFD_DEV_NAME", ".name\t= changed_driver", 1),
                header,
                pdic,
            )
        with self.assertRaises(self.module.AuditError):
            self.module.validate_stock_source_texts(
                mfd.replace(".probe\t\t= max77705_i2c_probe", ".probe\t\t= changed_probe", 1),
                header,
                pdic,
            )

    def test_stock_instantiation_source_mutation_is_rejected(self):
        mfd = self.module.stable_bytes(
            self.module.MFD_SOURCE,
            "MFD source",
            expected=self.authority["p319_irq"]["inputs"]["max77705_mfd_source"],
            maximum=128 * 1024,
        ).decode("utf-8")
        header = self.module.stable_bytes(
            self.module.MFD_HEADER,
            "MFD header",
            expected=self.authority["p319_irq"]["inputs"]["max77705_mfd_header"],
            maximum=32 * 1024,
        ).decode("utf-8")
        pdic = self.module.stable_bytes(
            self.module.PDIC_SOURCE,
            "PDIC source",
            expected=self.authority["p319_irq"]["inputs"]["max77705_usbc_source"],
            maximum=192 * 1024,
        ).decode("utf-8")
        with self.assertRaises(self.module.AuditError):
            self.module.validate_stock_source_texts(
                mfd.replace("mfd_add_devices(max77705->dev, -1, max77705_devs", "mfd_add_devices_removed(max77705->dev, -1, max77705_devs", 1),
                header,
                pdic,
            )


if __name__ == "__main__":
    unittest.main()
