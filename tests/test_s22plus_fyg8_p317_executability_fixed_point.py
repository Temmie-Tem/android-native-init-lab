import copy
import dataclasses
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p317_executability_fixed_point.py"
)
PRIVATE = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_p317/"
    "executability-fixed-point-20260812-01.json"
)


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("p317_fixed_point", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P317 = load_module()


class P317ExecutabilityFixedPointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_bytes = PRIVATE.read_bytes()
        cls.result = json.loads(cls.private_bytes)

    def test_exact_private_receipt_shape_and_delta(self):
        result = self.result
        self.assertEqual(result["schema"], P317.SCHEMA)
        self.assertEqual(result["verdict"], P317.VERDICT)
        self.assertEqual(result["status"], "CANDIDATE_NOT_READY")
        self.assertEqual(result["applicable_base_count"], 2)
        self.assertTrue(result["applicable_bases_static_closure_identical"])
        self.assertEqual(result["fixed_point"]["node_count"], 23)
        self.assertEqual(result["fixed_point"]["iteration_count"], 5)
        self.assertEqual(
            result["module_delta"]["added_early_modules"],
            list(P317.EXPECTED_NEW_MODULES),
        )
        self.assertEqual(result["module_delta"]["effective_count_delta"], "65->70")

    def test_all_three_families_receive_every_frontier_node(self):
        fixed = self.result["fixed_point"]
        self.assertEqual(fixed["relationship_families"], list(P317.FAMILIES))
        self.assertTrue(fixed["every_frontier_node_evaluated_by_every_family"])
        for iteration in fixed["iterations"]:
            seen = {
                (row["node"], row["family"])
                for row in iteration["family_evaluations"]
            }
            self.assertEqual(
                seen,
                {
                    (node, family)
                    for node in iteration["frontier"]
                    for family in P317.FAMILIES
                },
            )

    def test_instantiation_chain_is_recursive_on_supplier_outputs(self):
        nodes = set(self.result["fixed_point"]["nodes"])
        expected = {
            "/soc/qcom,spmi@c42d000",
            "/soc/qcom,spmi@c42d000/qcom,pm8350c@2",
            "/soc/qcom,spmi@c42d000/qcom,pm8350c@2/pinctrl@8800",
        }
        self.assertTrue(expected.issubset(nodes))
        edges = self.result["fixed_point"]["deduplicated_edges"]
        mechanisms = {row.get("mechanism") for row in edges}
        self.assertIn("qcom_spmi_pmic_devm_of_platform_populate", mechanisms)
        self.assertIn("spmi_controller_add_then_of_spmi_register_devices", mechanisms)

    def test_driver_consumed_wrapper_reference_is_not_parent_population(self):
        edges = self.result["fixed_point"]["deduplicated_edges"]
        rows = [
            row for row in edges
            if row["family"] == P317.FAMILY_DRIVER
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["consumer"], "/soc/i2c@994000")
        self.assertEqual(rows[0]["property"], "qcom,wrapper-core")
        self.assertEqual(rows[0]["dependency"], P317.ROOT_PATHS[0])

    def test_max77705_two_properties_deduplicate_to_one_supplier(self):
        rows = [
            row for row in self.result["fixed_point"]["deduplicated_edges"]
            if row["family"] == P317.FAMILY_FW
            and row["consumer"] == P317.ROOT_PATHS[2]
            and row.get("owner", "").endswith("/pinctrl@8800")
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["raw_evidence_count"], 2)
        self.assertEqual(
            set(rows[0]["raw_properties"]),
            {"pinctrl-0", "max77705,irq-gpio"},
        )

    def test_kernel_rejected_self_link_is_not_an_emitted_node(self):
        rows = [
            row for row in self.result["fixed_point"]["deduplicated_edges"]
            if row["consumer"] == "/soc/interrupt-controller@17100000"
            and row["family"] == P317.FAMILY_FW
        ]
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["kernel_link_created"])
        self.assertIn("consumer_self_or_descendant", rows[0]["kernel_link_rejection"])

    def test_predecessor_order_is_preserved_and_new_plan_is_dependency_valid(self):
        delta = self.result["module_delta"]
        predecessor = json.loads((ROOT / P317.DEFAULT_PREDECESSOR).read_bytes())
        old = predecessor["module_closure"]["files"]
        new = delta["successor_early_modules"]
        self.assertEqual([name for name in new if name in set(old)], old)
        positions = {name: index for index, name in enumerate(new)}
        for row in delta["dependency_constraints"]:
            self.assertLess(positions[row["before"]], positions[row["after"]])
        self.assertEqual(len(new), 69)
        self.assertEqual(delta["successor_effective_total_count"], 70)
        late = delta["early_vs_effective_contract"]
        self.assertEqual(late["early_module_count"], 69)
        self.assertEqual(late["early_loop_excludes"], "s22plus_max77705_mux_diag.ko")
        self.assertIn("gadget-path readiness", late["late_load_stage"])
        self.assertEqual(
            late["late_load_operation"],
            "one dedicated synchronous finit_module",
        )
        self.assertTrue(late["effective_count_includes_late_module"])

    def test_runtime_only_authorities_remain_pending(self):
        self.assertEqual(
            self.result["fw_devlink_policy"]["runtime_boot_mode_and_strict_witness"],
            "PENDING",
        )
        self.assertIn(
            "runtime_early_device_gate_witness",
            self.result["remaining_gates"],
        )
        self.assertEqual(
            self.result["must_bind"]["human_causal_review"],
            "SATISFIED_2026_08_12",
        )
        self.assertNotIn(
            "human_causal_review_of_corrected_claim_authority",
            self.result["remaining_gates"],
        )
        self.assertNotIn(
            "independent_review_of_changed_permanent_process_gate",
            self.result["remaining_gates"],
        )

    def test_missing_wrapper_reference_hard_fails(self):
        wrapper = P317.Node(
            path=P317.ROOT_PATHS[0],
            properties={
                "compatible": b"qcom,qupv3-geni-se\0",
                "phandle": (1).to_bytes(4, "big"),
            },
        )
        i2c = P317.Node(
            path=P317.ROOT_PATHS[1],
            properties={"compatible": b"qcom,i2c-geni\0"},
        )
        tree = P317.Tree(
            nodes={wrapper.path: wrapper, i2c.path: i2c},
            phandles={1: wrapper},
        )
        with self.assertRaisesRegex(P317.FixedPointError, "lacks qcom,wrapper-core"):
            P317.driver_reference_edges(tree, i2c)

    def test_spmi_instantiation_parent_mutation_hard_fails(self):
        parent = P317.Node(
            path="/soc/qcom,spmi@x/not-a-pmic",
            properties={"compatible": b"vendor,wrong\0"},
        )
        gpio = P317.Node(
            path=parent.path + "/pinctrl@8800",
            parent=parent,
            properties={"compatible": b"qcom,pm8350c-gpio\0"},
        )
        with self.assertRaisesRegex(P317.FixedPointError, "SPMI PMIC parent"):
            P317.instantiation_edges(P317.Tree({}, {}), gpio)

    def test_malformed_provider_cells_hard_fail(self):
        provider = P317.Node(
            path="/provider",
            properties={
                "compatible": b"vendor,provider\0",
                "#gpio-cells": b"\0\0\0\2",
            },
        )
        consumer = P317.Node(
            path="/consumer",
            properties={
                "compatible": b"vendor,consumer\0",
                "foo-gpio": b"\0\0\0\1\0\0\0\7",
            },
        )
        tree = P317.Tree(
            nodes={provider.path: provider, consumer.path: consumer},
            phandles={1: provider},
        )
        rule = {"cells_property": "#gpio-cells"}
        with self.assertRaisesRegex(P317.FixedPointError, "lacks 2 arguments"):
            P317._parse_generic_phandles(tree, consumer, "foo-gpio", rule)

    def test_alias_mutation_cannot_silently_drop_required_module(self):
        metadata = P317.module_plan.load_metadata(ROOT / P317.DEFAULT_METADATA)
        aliases = dict(metadata.aliases)
        aliases.pop("of:N*T*Cqcom,pm8350c-gpio")
        mutated = dataclasses.replace(metadata, aliases=aliases)
        node = P317.Node(
            path="/gpio",
            properties={"compatible": b"qcom,pm8350c-gpio\0"},
        )
        config = (ROOT / P317.DEFAULT_CONFIG).read_text()
        with self.assertRaisesRegex(P317.FixedPointError, "no exact built-in/module"):
            P317._module_for_node(node, mutated, config)

    def test_base_closure_mismatch_has_distinct_canonical_bytes(self):
        left = {
            "fixed_point": self.result["fixed_point"],
            "module_delta": self.result["module_delta"],
        }
        right = copy.deepcopy(left)
        right["fixed_point"]["nodes"].append("/synthetic-drift")
        self.assertNotEqual(
            P317._canonical_static_result(left),
            P317._canonical_static_result(right),
        )

    def test_exact_sources_regenerate_private_receipt(self):
        metadata = P317.module_plan.load_metadata(ROOT / P317.DEFAULT_METADATA)
        result = P317.build_contract(
            extractor_data=SCRIPT.read_bytes(),
            dtbo_data=(ROOT / P317.DEFAULT_DTBO).read_bytes(),
            vendor_dtb_data=(ROOT / P317.DEFAULT_VENDOR_DTB).read_bytes(),
            property_data=(ROOT / P317.DEFAULT_PROPERTY_SOURCE).read_bytes(),
            core_data=(ROOT / P317.DEFAULT_CORE_SOURCE).read_bytes(),
            of_base_data=(ROOT / P317.DEFAULT_OF_BASE_SOURCE).read_bytes(),
            irq_data=(ROOT / P317.DEFAULT_IRQ_SOURCE).read_bytes(),
            rpmh_data=(ROOT / P317.DEFAULT_RPMH_SOURCE).read_bytes(),
            rpmh_regulator_data=(
                ROOT / P317.DEFAULT_RPMH_REGULATOR_SOURCE
            ).read_bytes(),
            config_data=(ROOT / P317.DEFAULT_CONFIG).read_bytes(),
            predecessor_data=(ROOT / P317.DEFAULT_PREDECESSOR).read_bytes(),
            must_bind_data=(ROOT / P317.DEFAULT_MUST_BIND_RECEIPT).read_bytes(),
            metadata=metadata,
            fdtoverlay=ROOT / P317.DEFAULT_FDTOVERLAY,
            libfdt=ROOT / P317.DEFAULT_LIBFDT,
        )
        self.assertEqual(P317.encode_contract(result), self.private_bytes)


if __name__ == "__main__":
    unittest.main()
