import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p317_fw_devlink_contract.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p317_fw_devlink", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.17 fw_devlink contract")
    module = importlib.util.module_from_spec(spec)
    __import__("sys").modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P317 = load_module()


PARSERS = (
    "parse_clocks",
    "parse_interconnects",
    "parse_iommus",
    "parse_iommu_maps",
    "parse_mboxes",
    "parse_io_channels",
    "parse_interrupt_parent",
    "parse_dmas",
    "parse_power_domains",
    "parse_hwlocks",
    "parse_extcon",
    "parse_nvmem_cells",
    "parse_phys",
    "parse_wakeup_parent",
    "parse_pinctrl0",
    "parse_pinctrl1",
    "parse_pinctrl2",
    "parse_pinctrl3",
    "parse_pinctrl4",
    "parse_pinctrl5",
    "parse_pinctrl6",
    "parse_pinctrl7",
    "parse_pinctrl8",
    "parse_gpio_compat",
    "parse_interrupts",
    "parse_regulators",
    "parse_gpio",
    "parse_gpios",
)
OPTIONAL = {"parse_iommus", "parse_iommu_maps", "parse_dmas"}
MACRO_INVOCATIONS = (
    'DEFINE_SIMPLE_PROP(clocks, "clocks", "#clock-cells")',
    'DEFINE_SIMPLE_PROP(interconnects, "interconnects", "#interconnect-cells")',
    'DEFINE_SIMPLE_PROP(iommus, "iommus", "#iommu-cells")',
    'DEFINE_SIMPLE_PROP(mboxes, "mboxes", "#mbox-cells")',
    'DEFINE_SIMPLE_PROP(io_channels, "io-channels", "#io-channel-cells")',
    'DEFINE_SIMPLE_PROP(interrupt_parent, "interrupt-parent", NULL)',
    'DEFINE_SIMPLE_PROP(dmas, "dmas", "#dma-cells")',
    'DEFINE_SIMPLE_PROP(power_domains, "power-domains", "#power-domain-cells")',
    'DEFINE_SIMPLE_PROP(hwlocks, "hwlocks", "#hwlock-cells")',
    'DEFINE_SIMPLE_PROP(extcon, "extcon", NULL)',
    'DEFINE_SIMPLE_PROP(nvmem_cells, "nvmem-cells", NULL)',
    'DEFINE_SIMPLE_PROP(phys, "phys", "#phy-cells")',
    'DEFINE_SIMPLE_PROP(wakeup_parent, "wakeup-parent", NULL)',
    'DEFINE_SIMPLE_PROP(pinctrl0, "pinctrl-0", NULL)',
    'DEFINE_SIMPLE_PROP(pinctrl1, "pinctrl-1", NULL)',
    'DEFINE_SIMPLE_PROP(pinctrl2, "pinctrl-2", NULL)',
    'DEFINE_SIMPLE_PROP(pinctrl3, "pinctrl-3", NULL)',
    'DEFINE_SIMPLE_PROP(pinctrl4, "pinctrl-4", NULL)',
    'DEFINE_SIMPLE_PROP(pinctrl5, "pinctrl-5", NULL)',
    'DEFINE_SIMPLE_PROP(pinctrl6, "pinctrl-6", NULL)',
    'DEFINE_SIMPLE_PROP(pinctrl7, "pinctrl-7", NULL)',
    'DEFINE_SIMPLE_PROP(pinctrl8, "pinctrl-8", NULL)',
    'DEFINE_SUFFIX_PROP(regulators, "-supply", NULL)',
    'DEFINE_SUFFIX_PROP(gpio, "-gpio", "#gpio-cells")',
)


def property_source(parsers=PARSERS):
    rows = []
    for parser in parsers:
        optional = ", .optional = true" if parser in OPTIONAL else ""
        rows.append(f"    {{ .parse_prop = {parser}{optional}, }},")
    return "\n".join(
        (
            "static struct device_node *parse_prop_cells(",
            "if (strcmp(prop_name, list_name))",
            "of_parse_phandle_with_args(np, list_name, cells_name, index,",
            "#define DEFINE_SIMPLE_PROP(fname, name, cells)",
            "return parse_prop_cells(np, prop_name, index, name, cells);",
            "static int strcmp_suffix(const char *str, const char *suffix)",
            "if (len <= suffix_len)",
            "return strcmp(str + len - suffix_len, suffix);",
            "static struct device_node *parse_suffix_prop_cells(",
            "if (strcmp_suffix(prop_name, suffix))",
            "of_parse_phandle_with_args(np, prop_name, cells_name, index,",
            "#define DEFINE_SUFFIX_PROP(fname, suffix, cells)",
            "return parse_suffix_prop_cells(np, prop_name, index, suffix, cells);",
            'if (strcmp(prop_name, "iommu-map"))',
            'if (!strcmp_suffix(prop_name, ",nr-gpios"))',
            'return parse_suffix_prop_cells(np, prop_name, index, "-gpios",',
            'if (strcmp(prop_name, "gpio") && strcmp(prop_name, "gpios"))',
            'if (of_find_property(np, "gpio-hog", NULL))',
            'if (strcmp(prop_name, "interrupts") &&',
            'strcmp(prop_name, "interrupts-extended"))',
            *MACRO_INVOCATIONS,
            "static const struct supplier_bindings of_supplier_bindings[] = {",
            *rows,
            "    {}",
            "};",
            "if (s->optional && !fw_devlink_is_strict())",
            "if (!of_device_is_available(sup_np))",
            "if (of_is_ancestor_of(con_np, sup_np))",
            "of_node_check_flag(sup_np, OF_POPULATED)",
            "sup_np->fwnode.flags & FWNODE_FLAG_NOT_DEVICE",
            "fwnode_link_add(of_fwnode_handle(con_np), of_fwnode_handle(sup_np));",
        )
    )


CORE_SOURCE = """
static u32 fw_devlink_flags = FW_DEVLINK_FLAGS_ON;
static int __init fw_devlink_setup(char *arg)
{
    if (!arg)
        return -EINVAL;
    if (strcmp(arg, "off") == 0) {
        fw_devlink_flags = 0;
    } else if (strcmp(arg, "permissive") == 0) {
        fw_devlink_flags = FW_DEVLINK_FLAGS_PERMISSIVE;
    } else if (strcmp(arg, "on") == 0) {
        fw_devlink_flags = FW_DEVLINK_FLAGS_ON;
    } else if (strcmp(arg, "rpm") == 0) {
        fw_devlink_flags = FW_DEVLINK_FLAGS_RPM;
    }
    return 0;
}
early_param("fw_devlink", fw_devlink_setup);
static bool fw_devlink_strict = true;
static int __init fw_devlink_strict_setup(char *arg)
{
return strtobool(arg, &fw_devlink_strict);
}
early_param("fw_devlink.strict", fw_devlink_strict_setup);
return fw_devlink_strict && !fw_devlink_is_permissive();
static void fw_devlink_link_device(struct device *dev)
{
if (!fw_devlink_flags)
		return;
fw_devlink_parse_fwtree(fwnode);
}
static void fw_devlink_parse_fwtree(struct fwnode_handle *fwnode)
{
while ((child = fwnode_get_next_available_child_node(fwnode, child)))
fw_devlink_parse_fwtree(child);
}
val = !list_empty(&dev->fwnode->suppliers);
return sysfs_emit(buf, "%u\\n", val);
static DEVICE_ATTR_RO(waiting_for_supplier);
if (fw_devlink_flags && !fw_devlink_is_permissive() && dev->fwnode)
list_for_each_entry(link, &sup->consumers, s_hook)
if (link->consumer == con)
			goto out;
"""


OF_BASE_SOURCE = """
Return: True if the status property is absent or set to "okay" or "ok"
if (!strcmp(status, "okay") || !strcmp(status, "ok"))
"""


DTS_SOURCE = """
/dts-v1/;
/ {
    fragment@3 {
        __overlay__ {
            qcom,pm8350c@2 {
                pinctrl@8800 {
                    compatible = "qcom,pm8350c-gpio";
                    #gpio-cells = <0x02>;
                    phandle = <0x11>;
                    if_pmic_irq {
                        phandle = <0x7b>;
                    };
                };
            };
        };
    };
    fragment@63 {
        __overlay__ {
            max77705@66 {
                compatible = "maxim,max77705";
                reg = <0x66>;
                pinctrl-0 = <0x7b>;
                max77705,irq-gpio = <0x11 0x05 0x01>;
            };
        };
    };
};
"""


class P317FwDevlinkContractTest(unittest.TestCase):
    def rows_and_rules(self, source=None):
        source = property_source() if source is None else source
        return (
            P317.parse_supplier_bindings(source),
            P317.parse_macro_parser_rules(source),
        )

    def audit_edges(self, dts=DTS_SOURCE, source=None):
        rows, rules = self.rows_and_rules(source)
        core = P317.audit_core_semantics(CORE_SOURCE, OF_BASE_SOURCE)
        effective = P317.effective_parser_rows(
            rows,
            mode="on",
            strict=True,
            mode_assignments=core["mode_assignments"],
        )
        return P317.audit_max77705_edges(
            dts,
            rows=rows,
            parser_rules=rules,
            effective_parsers=effective,
        )

    def test_complete_table_and_optional_rows_are_extracted(self):
        rows = P317.parse_supplier_bindings(property_source())
        self.assertEqual(len(rows), 28)
        self.assertEqual(
            tuple(row["parse_prop"] for row in rows if row["optional"]),
            ("parse_iommus", "parse_iommu_maps", "parse_dmas"),
        )

    def test_mode_and_strict_are_evaluated_with_optional(self):
        rows = P317.parse_supplier_bindings(property_source())
        core = P317.audit_core_semantics(CORE_SOURCE, OF_BASE_SOURCE)
        kwargs = {"mode_assignments": core["mode_assignments"]}
        self.assertEqual(len(P317.effective_parser_rows(rows, mode="on", strict=True, **kwargs)), 28)
        self.assertEqual(len(P317.effective_parser_rows(rows, mode="on", strict=False, **kwargs)), 25)
        self.assertEqual(
            len(P317.effective_parser_rows(rows, mode="permissive", strict=True, **kwargs)),
            25,
        )
        self.assertEqual(P317.effective_parser_rows(rows, mode="off", strict=True, **kwargs), ())

    def test_missing_table_row_fails_loudly(self):
        with self.assertRaisesRegex(P317.ContractError, "count drift"):
            P317.parse_supplier_bindings(property_source(PARSERS[:-1]))

    def test_waiting_attribute_is_three_state_and_not_a_name_list(self):
        result = P317.audit_core_semantics(CORE_SOURCE, OF_BASE_SOURCE)
        self.assertEqual(
            result["waiting_for_supplier_states"],
            {
                "attribute_absent": "not_authoritatively_exposed",
                "attribute_present_0": "no_unresolved_fwnode_supplier",
                "attribute_present_1": "one_or_more_unresolved_fwnode_suppliers",
            },
        )
        self.assertFalse(result["waiting_for_supplier_names_suppliers"])

    def test_two_max77705_properties_resolve_to_one_owner_edge(self):
        result = self.audit_edges()
        self.assertEqual(result["raw_property_edge_count"], 2)
        self.assertEqual(result["deduplicated_consumer_supplier_edge_count"], 1)
        self.assertEqual(
            [row["parser"] for row in result["raw_property_edges"]],
            ["parse_pinctrl0", "parse_gpio"],
        )
        self.assertTrue(result["both_properties_resolve_to_same_owner"])

    def test_different_gpio_owner_is_not_silently_deduplicated(self):
        mutated = DTS_SOURCE.replace(
            "fragment@63 {",
            "fragment@4 { __overlay__ { pinctrl@9900 { "
            'compatible = "qcom,other-gpio"; #gpio-cells = <0x02>; '
            "phandle = <0x22>; }; }; }; "
            "fragment@63 {",
        ).replace(
            "max77705,irq-gpio = <0x11 0x05 0x01>",
            "max77705,irq-gpio = <0x22 0x05 0x01>",
        )
        with self.assertRaisesRegex(P317.ContractError, "different owner"):
            self.audit_edges(mutated)

    def test_same_count_parser_substitution_fails(self):
        mutated = property_source().replace(
            ".parse_prop = parse_pinctrl0",
            ".parse_prop = parse_unrelated0",
        )
        with self.assertRaisesRegex(P317.ContractError, "parser rule coverage drifted"):
            P317.build_contract(
                extractor_data=SCRIPT.read_bytes(),
                property_data=mutated.encode(),
                core_data=CORE_SOURCE.encode(),
                of_base_data=OF_BASE_SOURCE.encode(),
                dts_data=DTS_SOURCE.encode(),
            )

    def test_new_table_matched_consumer_property_changes_regression(self):
        mutated = DTS_SOURCE.replace(
            "pinctrl-0 = <0x7b>;",
            "pinctrl-0 = <0x7b>; interrupt-parent = <0x11>;",
        )
        with self.assertRaisesRegex(P317.ContractError, "exact Max77705 regression drifted"):
            P317.build_contract(
                extractor_data=SCRIPT.read_bytes(),
                property_data=property_source().encode(),
                core_data=CORE_SOURCE.encode(),
                of_base_data=OF_BASE_SOURCE.encode(),
                dts_data=mutated.encode(),
            )

    def test_parser_helper_semantics_mutation_fails(self):
        mutated = property_source().replace(
            "if (strcmp_suffix(prop_name, suffix))",
            "if (false)",
        )
        with self.assertRaisesRegex(P317.ContractError, "source contract missing"):
            P317.parse_macro_parser_rules(mutated)

    def test_disabled_supplier_fails_static_edge(self):
        mutated = DTS_SOURCE.replace(
            "if_pmic_irq {",
            'if_pmic_irq { status = "disabled";',
        )
        with self.assertRaisesRegex(P317.ContractError, "supplier path is unavailable"):
            self.audit_edges(mutated)

    def test_disabled_consumer_fails_fw_devlink_traversal(self):
        mutated = DTS_SOURCE.replace(
            'compatible = "maxim,max77705";',
            'compatible = "maxim,max77705"; status = "disabled";',
        )
        with self.assertRaisesRegex(P317.ContractError, "consumer path is unavailable"):
            self.audit_edges(mutated)

    def test_self_supplier_is_rejected(self):
        mutated = DTS_SOURCE.replace(
            "pinctrl-0 = <0x7b>",
            "phandle = <0x7b>; pinctrl-0 = <0x7b>",
        ).replace(
            "if_pmic_irq {\n                        phandle = <0x7b>;\n                    };",
            "if_pmic_irq { };",
        )
        with self.assertRaisesRegex(P317.ContractError, "descendant of consumer"):
            self.audit_edges(mutated)

    def test_descendant_supplier_is_rejected(self):
        mutated = DTS_SOURCE.replace(
            "pinctrl-0 = <0x7b>",
            "child-supplier { compatible = \"qcom,child\"; "
            "phandle = <0x7b>; }; pinctrl-0 = <0x7b>",
        ).replace(
            "if_pmic_irq {\n                        phandle = <0x7b>;\n                    };",
            "if_pmic_irq { };",
        )
        with self.assertRaisesRegex(P317.ContractError, "descendant of consumer"):
            self.audit_edges(mutated)

    def test_gpio_parser_requires_provider_argument_count(self):
        mutated = DTS_SOURCE.replace(
            "max77705,irq-gpio = <0x11 0x05 0x01>",
            "max77705,irq-gpio = <0x11>",
        )
        with self.assertRaisesRegex(P317.ContractError, "lacks 2 arguments"):
            self.audit_edges(mutated)

    def test_combined_contract_preserves_raw_and_deduplicated_edges(self):
        result = P317.build_contract(
            extractor_data=SCRIPT.read_bytes(),
            property_data=property_source().encode(),
            core_data=CORE_SOURCE.encode(),
            of_base_data=OF_BASE_SOURCE.encode(),
            dts_data=DTS_SOURCE.encode(),
        )
        self.assertEqual(result["verdict"], P317.VERDICT)
        self.assertEqual(
            result["supplier_parser_table"]["source_default_effective_parser_count"],
            28,
        )
        matrix = result["supplier_parser_table"]["mode_strict_matrix"]
        self.assertEqual(len(matrix), 8)
        counts = {
            (row["mode"], row["strict_argument"]): row["effective_parser_count"]
            for row in matrix
        }
        self.assertEqual(counts[("off", False)], 0)
        self.assertEqual(counts[("off", True)], 0)
        self.assertEqual(counts[("permissive", False)], 25)
        self.assertEqual(counts[("permissive", True)], 25)
        self.assertEqual(counts[("on", False)], 25)
        self.assertEqual(counts[("on", True)], 28)
        self.assertEqual(counts[("rpm", False)], 25)
        self.assertEqual(counts[("rpm", True)], 28)
        self.assertTrue(result["contract"]["must_bind_consumer_scope_is_independent"])
        self.assertTrue(result["contract"]["candidate_boot_arguments_must_reprove_effective_policy"])

    def test_core_mode_mapping_and_off_gate_mutations_fail(self):
        mutated_mapping = CORE_SOURCE.replace(
            "fw_devlink_flags = FW_DEVLINK_FLAGS_RPM;",
            "fw_devlink_flags = FW_DEVLINK_FLAGS_ON;",
        )
        with self.assertRaisesRegex(P317.ContractError, "mode mapping drifted"):
            P317.audit_core_semantics(mutated_mapping, OF_BASE_SOURCE)
        mutated_gate = CORE_SOURCE.replace(
            "if (!fw_devlink_flags)\n\t\treturn;",
            "if (false)\n\t\treturn;",
        )
        with self.assertRaisesRegex(P317.ContractError, "source contract missing"):
            P317.audit_core_semantics(mutated_gate, OF_BASE_SOURCE)
        mutated_strict = CORE_SOURCE.replace(
            "return strtobool(arg, &fw_devlink_strict);",
            "return 0;",
        )
        with self.assertRaisesRegex(P317.ContractError, "source contract missing"):
            P317.audit_core_semantics(mutated_strict, OF_BASE_SOURCE)

    def test_exact_sources_regenerate_pinned_private_receipt(self):
        root = ROOT
        result = P317.build_contract(
            extractor_data=P317.stable_read(
                SCRIPT, "extractor source", 2 * 1024 * 1024
            ),
            property_data=P317.stable_read(
                root / P317.DEFAULT_PROPERTY_SOURCE, "OF property source", 512 * 1024
            ),
            core_data=P317.stable_read(
                root / P317.DEFAULT_CORE_SOURCE, "driver-core source", 1024 * 1024
            ),
            of_base_data=P317.stable_read(
                root / P317.DEFAULT_OF_BASE_SOURCE, "OF base source", 512 * 1024
            ),
            dts_data=P317.stable_read(
                root / P317.DEFAULT_DTS, "exact g0q DTS", 8 * 1024 * 1024
            ),
        )
        encoded = P317.encode_contract(result)
        private = (
            root
            / "workspace/private/outputs/s22plus_fyg8_p317/"
            "fw-devlink-contract-20260812-01.json"
        ).read_bytes()
        self.assertEqual(encoded, private)
        self.assertEqual(
            result["authority"]["extractor_source"],
            P317.receipt(SCRIPT.read_bytes()),
        )
        self.assertEqual(result["max77705_regression"]["raw_property_edge_count"], 2)
        self.assertEqual(
            result["max77705_regression"]["deduplicated_consumer_supplier_edge_count"],
            1,
        )
        self.assertEqual(
            [row["phandle"] for row in result["max77705_regression"]["raw_property_edges"]],
            ["0x7b", "0x11"],
        )
        self.assertEqual(
            [row["parser"] for row in result["max77705_regression"]["raw_property_edges"]],
            ["parse_pinctrl0", "parse_gpio"],
        )


if __name__ == "__main__":
    unittest.main()
