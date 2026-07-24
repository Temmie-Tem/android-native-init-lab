import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p234_build_repro_check as repro  # noqa: E402
import s22plus_fyg8_p234_userspace_build as userspace  # noqa: E402
import s22plus_fyg8_p253_e2_stock_closure as closure_selector  # noqa: E402
import s22plus_fyg8_p257_source_contract as p257  # noqa: E402
import s22plus_fyg8_p258_contract_spec as spec  # noqa: E402
import s22plus_fyg8_p258_e2_stock_closure as closure  # noqa: E402
import s22plus_fyg8_p258_linked_audit as linked  # noqa: E402
import s22plus_fyg8_p258_source_contract as p258  # noqa: E402
import s22plus_fyg8_source_contracts as contracts  # noqa: E402


class S22PlusFyg8P258SourceContractTest(unittest.TestCase):
    RUN_ID = bytes.fromhex("58" * 16)
    REPORT_PATH = ROOT / (
        "docs/reports/"
        "S22PLUS_FYG8_P258A_UDC_PREDICATE_IMPLEMENTATION_H0_2026-07-25.md"
    )

    @classmethod
    def setUpClass(cls):
        cls.implementation = p258.implementation_result(ROOT)
        cls.generated = p258.generate(ROOT)
        cls.historical = p257.generate(ROOT)
        cls.reachable = p258.validate_reachable_records(cls.RUN_ID)

    def test_known_good_stock_oracle_is_machine_readable(self):
        value = json.loads(
            (ROOT / spec.STOCK_TOPOLOGY_PATH).read_text(encoding="ascii")
        )
        self.assertEqual(
            value["sysfs"]["udc_entries"],
            [spec.UDC_TARGET_NAME, spec.UDC_STOCK_PEER],
        )
        oracle = self.implementation["semantic_oracle"]
        self.assertTrue(oracle["known_good_passed"])
        self.assertTrue(oracle["unrelated_peer_passed"])
        self.assertEqual(oracle["case_count"], 7)

    def test_semantic_oracle_covers_positive_negative_and_peer_states(self):
        actual = {
            case.name: spec.evaluate_udc_oracle(case)
            for case in spec.UDC_ORACLE_CASES
        }
        self.assertEqual(
            actual,
            {
                "target-absent": False,
                "real-only": True,
                "known-good-stock": True,
                "unrelated-peer": True,
                "wrong-target": False,
                "wrong-type": False,
                "duplicate-target": False,
            },
        )
        stock = next(
            case
            for case in spec.UDC_ORACLE_CASES
            if case.name == "known-good-stock"
        )
        old_singleton_predicate = (
            len(stock.entries) == 1
            and stock.entries.count(spec.UDC_TARGET_NAME) == 1
        )
        self.assertFalse(old_singleton_predicate)
        self.assertTrue(spec.evaluate_udc_oracle(stock))

    def test_oracle_inventory_and_expected_result_mutations_fail(self):
        with self.assertRaises(spec.SpecError):
            spec.validate_udc_oracle(spec.UDC_ORACLE_CASES[:-1])
        mutated = tuple(
            replace(case, expected=False)
            if case.name == "known-good-stock"
            else case
            for case in spec.UDC_ORACLE_CASES
        )
        with self.assertRaises(spec.SpecError):
            spec.validate_udc_oracle(mutated)
        with mock.patch.object(spec, "UDC_TARGET_NAME", "wrong-controller"):
            with self.assertRaises(spec.SpecError):
                spec.validate_udc_oracle()

    def test_canonical_topology_omission_or_peer_loss_fails_closed(self):
        for entries in (None, [spec.UDC_TARGET_NAME]):
            with self.subTest(entries=entries):
                with tempfile.TemporaryDirectory(
                    prefix="s22-p258-topology-"
                ) as name:
                    root = Path(name)
                    path = root / spec.STOCK_TOPOLOGY_PATH
                    path.parent.mkdir(parents=True)
                    value = {"sysfs": {}}
                    if entries is not None:
                        value["sysfs"]["udc_entries"] = entries
                    path.write_text(
                        json.dumps(value, sort_keys=True),
                        encoding="ascii",
                    )
                    with self.assertRaises(p258.SourceContractError):
                        p258._topology_oracle_audit(root)

    def test_only_runtime_differs_from_p257_generated_contract(self):
        self.assertEqual(self.generated["plan"], self.historical["plan"])
        self.assertEqual(
            self.generated["checkpoint"], self.historical["checkpoint"]
        )
        self.assertEqual(self.generated["patch"], self.historical["patch"])
        self.assertNotEqual(
            self.generated["runtime"], self.historical["runtime"]
        )
        semantics = self.implementation["generated_semantics"]
        self.assertTrue(semantics["kernel_patch_byte_identical_to_p257"])
        self.assertTrue(semantics["runtime_only_delta"])

    def test_generated_runtime_removes_singleton_and_resets_udc_dwell(self):
        runtime = self.generated["runtime"].decode("ascii")
        self.assertNotIn("entries == 1U", runtime)
        self.assertIn("if (exact == 0U) {", runtime)
        self.assertIn("if (exact != 1U) {", runtime)
        self.assertIn(
            "if (completed == S22_P258_UDC_GATE_INDEX) {", runtime
        )
        reset = runtime.index(
            "if (completed == S22_P258_UDC_GATE_INDEX) {"
        )
        clear = runtime.index("post_grace_drain = 0;", reset)
        advanced = runtime.index("advanced = 1;", clear)
        self.assertLess(reset, clear)
        self.assertLess(clear, advanced)

    def test_record_geometry_and_reachable_domain_are_unchanged(self):
        self.assertEqual(spec.STAGE_SEQUENCE, p257.spec.STAGE_SEQUENCE)
        self.assertEqual(spec.CLASSIFIER_VALUES, p257.spec.CLASSIFIER_VALUES)
        self.assertEqual(
            self.reachable["reachable_slot_variants"],
            p257.REACHABLE_VARIANTS,
        )
        self.assertEqual(
            self.reachable["decoder_policy_id"], p257.decoder.POLICY_ID
        )

    def test_selector_closure_and_linked_adapters_are_registered(self):
        selected = contracts.select(p258.CONTRACT_ID, "E2")
        self.assertIs(selected.module, p258)
        self.assertIs(selected.decoder, p257.decoder)
        self.assertIs(
            closure_selector.select(p258.CONTRACT_ID), closure
        )
        self.assertEqual(
            repro.LINKED_VALIDATOR_ADAPTERS[p258.CONTRACT_ID],
            "s22plus_fyg8_p258_linked_audit",
        )
        self.assertEqual(linked.EXPECTED_SOURCE_CONTRACT_ID, p258.CONTRACT_ID)
        source, _receipts = p258.source_receipts(ROOT)
        self.assertEqual(set(source), p258.SOURCE_KEYS)

    def test_materialized_userspace_plan_remains_60_modules(self):
        with tempfile.TemporaryDirectory(prefix="s22-p258-plan-") as name:
            directory = Path(name)
            path = directory / p258.MATERIALIZED_FILENAMES["plan_header"]
            path.write_bytes(self.generated["plan"])
            names = userspace._e2_module_files(
                ROOT, p258.CONTRACT_ID, directory
            )
        self.assertEqual(len(names), spec.MODULE_PLAN_COUNT)
        self.assertEqual(
            names[spec.DISPCC_INSERTION.index],
            spec.DISPCC_INSERTION.file,
        )

    def test_linked_tables_remain_exactly_p257(self):
        self.assertEqual(p258.linked_table_bytes(), p257.linked_table_bytes())
        self.assertTrue(
            p258.audit_linked_tables(p257.linked_table_bytes())["verified"]
        )

    def test_safety_result_is_host_only(self):
        self.assertEqual(
            self.implementation["verdict"],
            p258.IMPLEMENTATION_VERDICT,
        )
        self.assertEqual(
            self.implementation["linked_userspace"]["static_aarch64"], True
        )
        self.assertEqual(
            self.implementation["linked_userspace"][
                "two_link_reproducible"
            ],
            True,
        )
        self.assertEqual(
            self.implementation["safety"],
            {
                "host_only": True,
                "kernel_built": False,
                "image_built": False,
                "candidate_created": False,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "live_authorized": False,
            },
        )

    def test_report_receipts_match_generated_evidence(self):
        report = self.REPORT_PATH.read_text(encoding="ascii")
        for name, receipt in self.implementation["generated"].items():
            with self.subTest(name=name):
                self.assertIn(receipt["sha256"], report)
        self.assertIn(
            self.implementation["linked_userspace"]["sha256"],
            report,
        )


if __name__ == "__main__":
    unittest.main()
