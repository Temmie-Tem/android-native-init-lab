import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p317_must_bind_claim_contract.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p317_must_bind", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.17 must-bind claim contract")
    module = importlib.util.module_from_spec(spec)
    __import__("sys").modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P317 = load_module()


RUNTIME = """
#define P316_TARGET_I2C_DEVICE "994000.i2c"
{"9c0000.qcom,qupv3_0_geni_se", "qupv3_geni_se", 1U}
{"994000.i2c", "i2c_geni", 1U}
rc = p260_bind_udc();
p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_CLOSED, 0U);
p282_copy_path_part(
            topology->adapter_path
entry->d_name, length, value.adapter_name, "0066"
static const char exact[] = "maxim,max77705";
p316_observe_diagnostic(tty_fd, &topology, &observation)
"""


LIVE = """
trace_session = _P300UsbTraceSession(prepared, journal)
trace_session.start()
backend.request_download(prepared)
"""


QUP = """
static const struct of_device_id geni_se_dt_match[] = {
    { .compatible = "qcom,qupv3-geni-se", },
};
geni_se_dev = dev_get_drvdata(rsc->wrapper_dev);
if (unlikely(!geni_se_dev))
    return -EPROBE_DEFER;
.name = "qupv3_geni_se"
.probe = geni_se_probe
"""


I2C_DRIVER = """
wrapper_ph_node = of_parse_phandle(pdev->dev.of_node,
                "qcom,wrapper-core", 0);
wrapper_pdev = of_find_device_by_node(wrapper_ph_node);
gi2c->i2c_rsc.wrapper_dev = &wrapper_pdev->dev;
ret = geni_se_resources_init(&gi2c->i2c_rsc, I2C_CORE2X_VOTE,
gi2c->adap.dev.of_node = pdev->dev.of_node;
ret = i2c_add_adapter(&gi2c->adap);
.name = "i2c_geni"
.probe  = geni_i2c_probe
"""


I2C_CORE = """
static int i2c_register_adapter(struct i2c_adapter *adap)
of_i2c_register_devices(adap);
"""


I2C_OF = """
client = i2c_new_client_device(adap, &info);
void of_i2c_register_devices(struct i2c_adapter *adap)
for_each_available_child_of_node(bus, node)
client = of_i2c_register_device(adap, node);
"""


OF_PLATFORM = """
static int __init of_platform_default_populate_init(void)
of_platform_default_populate(NULL, NULL, NULL);
arch_initcall_sync(of_platform_default_populate_init);
"""


QUP_DTS = """
qupv3_0: qcom,qupv3_0_geni_se@9c0000 {
compatible = "qcom,qupv3-geni-se";
};
qupv3_se5_i2c: i2c@994000 {
compatible = "qcom,i2c-geni";
qcom,wrapper-core = <&qupv3_0>;
};
"""


SPMI_ARB = """
static int spmi_pmic_arb_probe(struct platform_device *pdev)
ctrl = spmi_controller_alloc(&pdev->dev, sizeof(*pmic_arb));
err = spmi_controller_add(ctrl);
{ .compatible = "qcom,spmi-pmic-arb", }
.probe\t\t= spmi_pmic_arb_probe
"""


SPMI_CORE = """
static void of_spmi_register_devices(struct spmi_controller *ctrl)
for_each_available_child_of_node(ctrl->dev.of_node, node)
sdev = spmi_device_alloc(ctrl);
err = spmi_device_add(sdev);
of_spmi_register_devices(ctrl);
"""


SPMI_PMIC = """
{ .compatible = "qcom,spmi-pmic", .data = (void *)COMMON_SUBTYPE }
static int pmic_spmi_probe(struct spmi_device *sdev)
return devm_of_platform_populate(&sdev->dev);
.probe = pmic_spmi_probe
"""


PM8350C_DTS = """
&spmi_bus {
qcom,pm8350c@2 {
compatible = "qcom,spmi-pmic";
pm8350c_gpios: pinctrl@8800 {
compatible = "qcom,pm8350c-gpio";
"""


DIAGNOSTIC = """
if (parent->addr != S22PLUS_MAX77705_PARENT_ADDR)
devm_i2c_new_dummy_device(&parent->dev, parent->adapter,
rc = s22plus_max77705_diag_run(parent, muic,
.compatible = S22PLUS_MAX77705_PARENT_COMPATIBLE
.name = "s22plus_max77705_mux_diag"
.probe_type = PROBE_FORCE_SYNCHRONOUS
"""


SURFACE = """
"pre_non_0x09_post1_post2_0x09_attach": "strong MUX-causal support"
"pre_non_0x09_post1_post2_0x09_silent"
"pre_0x09_post1_post2_0x09_attach"
"post1_0x09_post2_non_0x09"
"host_fact_without_complete_device_result"
"control1_readback_proves_physical_switch_contact": False
"msm-geni-se.ko"
"gpi.ko"
"i2c-msm-geni.ko"
"""


class P317MustBindClaimContractTest(unittest.TestCase):
    def build(
        self, *, authority=None, runtime=RUNTIME, live=LIVE, qup=QUP,
        i2c_driver=I2C_DRIVER, i2c_core=I2C_CORE, i2c_of=I2C_OF,
        of_platform=OF_PLATFORM,
        qup_dts=QUP_DTS, spmi_arb=SPMI_ARB, spmi_core=SPMI_CORE,
        spmi_pmic=SPMI_PMIC, pm8350c_dts=PM8350C_DTS,
    ):
        return P317.build_contract(
            extractor_data=SCRIPT.read_bytes(),
            runtime_data=runtime.encode(),
            diagnostic_data=DIAGNOSTIC.encode(),
            surface_data=SURFACE.encode(),
            live_data=live.encode(),
            qup_data=qup.encode(),
            i2c_driver_data=i2c_driver.encode(),
            i2c_core_data=i2c_core.encode(),
            i2c_of_data=i2c_of.encode(),
            of_platform_data=of_platform.encode(),
            qup_dts_data=qup_dts.encode(),
            spmi_arb_data=spmi_arb.encode(),
            spmi_core_data=spmi_core.encode(),
            spmi_pmic_data=spmi_pmic.encode(),
            pm8350c_dts_data=pm8350c_dts.encode(),
            authority=authority,
        )

    def test_proposed_authority_has_complete_small_root_coverage(self):
        result = self.build()
        self.assertEqual(
            result["counts"],
            {
                "claims": 3,
                "evaluability_preconditions": 4,
                "must_bind_consumers": 3,
                "claim_consumer_edges": 9,
                "excluded_adjacent_consumers": 5,
                "review_triggers": 5,
            },
        )
        self.assertEqual(
            {
                row["device_identity"]
                for row in result["claim_authority"]["must_bind_consumers"]
            },
            {
                "platform:9c0000.qcom,qupv3_0_geni_se",
                "platform:994000.i2c",
                (
                    "i2c:<adapter-under-platform-994000.i2c>-0066; "
                    "compatible=maxim,max77705"
                ),
            },
        )

    def test_relationship_families_iterate_over_every_emitted_node(self):
        result = self.build()
        fixed = result["claim_authority"]["relationship_fixed_point"]
        self.assertEqual(fixed["algorithm"], "least_fixed_point")
        self.assertTrue(
            fixed["family_outputs_reenter_all_registered_families"]
        )
        self.assertTrue(fixed["root_only_instantiation_is_forbidden"])
        self.assertEqual(
            fixed["registered_families"],
            [
                "FW_DEVLINK_DT_SUPPLIER_CLOSURE",
                "DEVICE_INSTANTIATION_CLOSURE",
                "DRIVER_CONSUMED_DT_REFERENCE_CLOSURE",
            ],
        )
        self.assertTrue(
            result["contract"]["all_registered_families_iterate_to_fixed_point"]
        )

    def test_root_only_instantiation_semantics_fail(self):
        authority = P317.proposed_authority()
        authority["relationship_fixed_point"][
            "family_input_domain"
        ] = "reviewed must-bind roots only"
        with self.assertRaisesRegex(
            P317.ClaimContractError, "fixed-point semantics differ"
        ):
            self.build(authority=authority)

    def test_json_roundtrip_preserves_fixed_point_authority(self):
        result = self.build()
        decoded = json.loads(P317.encode_contract(result))
        validated = P317.validate_authority(decoded["claim_authority"])
        self.assertEqual(
            P317.authority_sha256(validated), result["claim_authority_sha256"]
        )

    def test_machine_scope_is_coverage_not_causal_truth(self):
        result = self.build()
        self.assertEqual(
            result["human_causal_review"],
            "REQUIRED_NOT_YET_SATISFIED",
        )
        self.assertEqual(
            result["human_review_binding"]["pending_claim_authority_sha256"],
            result["claim_authority_sha256"],
        )
        self.assertFalse(result["human_review_binding"]["candidate_authority"])
        self.assertTrue(result["contract"]["machine_enforces_coverage_not_truth"])
        self.assertFalse(result["contract"]["p317_candidate_ready"])
        self.assertTrue(result["contract"]["arming_precondition_is_not_expanded"])
        self.assertTrue(
            result["contract"][
                "evaluability_precondition_presence_is_machine_checked"
            ]
        )
        self.assertTrue(
            result["contract"][
                "evaluability_precondition_truth_requires_separate_qualification"
            ]
        )

    def test_claim_without_consumer_analysis_fails(self):
        authority = P317.proposed_authority()
        authority["claim_consumer_edges"] = [
            row
            for row in authority["claim_consumer_edges"]
            if row["claim"] != "P317_CLAIM_MUX_CAUSAL_ATTACH_SUPPORT"
        ]
        with self.assertRaisesRegex(P317.ClaimContractError, "lack a consumer"):
            self.build(authority=authority)

    def test_consumer_without_causal_claim_fails(self):
        authority = P317.proposed_authority()
        authority["must_bind_consumers"].append(
            {
                "id": "P317_CONSUMER_ORPHAN",
                "device_identity": "platform:orphan",
                "expected_driver": "orphan",
                "root_kind": "experiment_endpoint",
                "root_reason": "synthetic orphan",
            }
        )
        with self.assertRaisesRegex(P317.ClaimContractError, "lack a causal claim"):
            self.build(authority=authority)

    def test_empty_failure_consequence_fails(self):
        authority = P317.proposed_authority()
        authority["claim_consumer_edges"][0]["failure_consequence"] = ""
        with self.assertRaisesRegex(P317.ClaimContractError, "consequence is empty"):
            self.build(authority=authority)

    def test_missing_claim_evaluability_precondition_fails(self):
        authority = P317.proposed_authority()
        authority["claims"][2]["evaluability_preconditions"] = []
        with self.assertRaisesRegex(
            P317.ClaimContractError, "evaluability-precondition coverage"
        ):
            self.build(authority=authority)

    def test_orphan_evaluability_precondition_fails(self):
        authority = P317.proposed_authority()
        authority["evaluability_preconditions"].append(
            {
                "id": "P317_EVAL_ORPHAN",
                "statement": "synthetic orphan",
                "current_status": "PENDING",
            }
        )
        with self.assertRaisesRegex(P317.ClaimContractError, "orphaned"):
            self.build(authority=authority)

    def test_excluded_adjacent_consumer_requires_reason(self):
        authority = P317.proposed_authority()
        authority["excluded_adjacent_consumers"][0]["reason"] = ""
        with self.assertRaisesRegex(P317.ClaimContractError, "reason is empty"):
            self.build(authority=authority)

    def test_claim_text_change_changes_root_authority_hash(self):
        original = P317.proposed_authority()
        changed = copy.deepcopy(original)
        changed["claims"][0]["statement"] += " changed"
        self.assertNotEqual(
            P317.authority_sha256(original), P317.authority_sha256(changed)
        )

    def test_runtime_exact_transport_seam_is_source_bound(self):
        mutated = RUNTIME.replace('"994000.i2c", "i2c_geni", 1U',
                                  '"994000.i2c", "i2c_geni", 0U')
        with self.assertRaisesRegex(P317.ClaimContractError, "source contract missing"):
            self.build(runtime=mutated)

    def test_wrapper_direct_dependency_seam_is_source_bound(self):
        mutated = QUP.replace("return -EPROBE_DEFER", "return -ENOENT")
        with self.assertRaisesRegex(P317.ClaimContractError, "source contract missing"):
            self.build(qup=mutated)

        mutated_i2c = I2C_DRIVER.replace(
            '"qcom,wrapper-core", 0);', '"qcom,unrelated-core", 0);'
        )
        with self.assertRaisesRegex(P317.ClaimContractError, "source contract missing"):
            self.build(i2c_driver=mutated_i2c)

    def test_wrapper_and_controller_must_be_dt_siblings(self):
        nested = QUP_DTS.replace(
            'compatible = "qcom,qupv3-geni-se";\n};\n',
            'compatible = "qcom,qupv3-geni-se";\n',
        )
        with self.assertRaisesRegex(P317.ClaimContractError, "siblings"):
            self.build(qup_dts=nested)

    def test_i2c_client_instantiation_seam_is_source_bound(self):
        mutated = I2C_CORE.replace(
            "of_i2c_register_devices(adap);", "of_i2c_register_none(adap);"
        )
        with self.assertRaisesRegex(P317.ClaimContractError, "source contract missing"):
            self.build(i2c_core=mutated)

    def test_spmi_supplier_instantiation_seams_are_source_bound(self):
        mutations = (
            {"spmi_arb": SPMI_ARB.replace(
                "spmi_controller_add(ctrl)", "spmi_controller_skip(ctrl)"
            )},
            {"spmi_core": SPMI_CORE.replace(
                "spmi_device_add(sdev)", "spmi_device_skip(sdev)"
            )},
            {"spmi_pmic": SPMI_PMIC.replace(
                "devm_of_platform_populate", "devm_of_platform_skip"
            )},
            {"pm8350c_dts": PM8350C_DTS.replace(
                "qcom,pm8350c-gpio", "qcom,pm8350c-missing"
            )},
        )
        for kwargs in mutations:
            with self.subTest(kwargs=tuple(kwargs)):
                with self.assertRaisesRegex(
                    P317.ClaimContractError, "source contract missing"
                ):
                    self.build(**kwargs)

    def test_sidecar_arm_must_precede_candidate_request(self):
        mutated = """
trace_session = _P300UsbTraceSession(prepared, journal)
backend.request_download(prepared)
trace_session.start()
"""
        with self.assertRaisesRegex(P317.ClaimContractError, "not before"):
            self.build(live=mutated)

    def test_gadget_path_gate_must_precede_diagnostic_dispatch(self):
        mutated = RUNTIME.replace(
            "rc = p260_bind_udc();\n"
            "p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_CLOSED, 0U);\n",
            "p316_observe_diagnostic(tty_fd, &topology, &observation)\n"
            "rc = p260_bind_udc();\n"
            "p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_CLOSED, 0U);\n",
        )
        with self.assertRaisesRegex(P317.ClaimContractError, "not before"):
            self.build(runtime=mutated)

    def test_exact_sources_regenerate_pinned_private_receipt(self):
        result = P317.build_contract(
            extractor_data=P317.stable_read(
                SCRIPT, "claim-contract source", 2 * 1024 * 1024
            ),
            runtime_data=P317.stable_read(
                ROOT / P317.DEFAULT_RUNTIME_SOURCE,
                "P3.16 runtime",
                2 * 1024 * 1024,
            ),
            diagnostic_data=P317.stable_read(
                ROOT / P317.DEFAULT_DIAGNOSTIC_SOURCE,
                "Max77705 diagnostic",
                2 * 1024 * 1024,
            ),
            surface_data=P317.stable_read(
                ROOT / P317.DEFAULT_SURFACE_SOURCE,
                "Max77705 surface contract",
                4 * 1024 * 1024,
            ),
            live_data=P317.stable_read(
                ROOT / P317.DEFAULT_LIVE_SOURCE,
                "Process-v2 live runner",
                4 * 1024 * 1024,
            ),
            qup_data=P317.stable_read(
                ROOT / P317.DEFAULT_QUP_SOURCE,
                "QUPv3 wrapper driver",
                4 * 1024 * 1024,
            ),
            i2c_driver_data=P317.stable_read(
                ROOT / P317.DEFAULT_I2C_DRIVER_SOURCE,
                "GENI I2C driver",
                4 * 1024 * 1024,
            ),
            i2c_core_data=P317.stable_read(
                ROOT / P317.DEFAULT_I2C_CORE_SOURCE,
                "I2C core",
                4 * 1024 * 1024,
            ),
            i2c_of_data=P317.stable_read(
                ROOT / P317.DEFAULT_I2C_OF_SOURCE,
                "I2C OF core",
                2 * 1024 * 1024,
            ),
            of_platform_data=P317.stable_read(
                ROOT / P317.DEFAULT_OF_PLATFORM_SOURCE,
                "OF platform core",
                2 * 1024 * 1024,
            ),
            qup_dts_data=P317.stable_read(
                ROOT / P317.DEFAULT_QUP_DTS_SOURCE,
                "Waipio QUPv3 DT",
                4 * 1024 * 1024,
            ),
            spmi_arb_data=P317.stable_read(
                ROOT / P317.DEFAULT_SPMI_ARB_SOURCE,
                "SPMI PMIC arbiter driver",
                4 * 1024 * 1024,
            ),
            spmi_core_data=P317.stable_read(
                ROOT / P317.DEFAULT_SPMI_CORE_SOURCE,
                "SPMI core",
                2 * 1024 * 1024,
            ),
            spmi_pmic_data=P317.stable_read(
                ROOT / P317.DEFAULT_SPMI_PMIC_SOURCE,
                "SPMI PMIC MFD driver",
                2 * 1024 * 1024,
            ),
            pm8350c_dts_data=P317.stable_read(
                ROOT / P317.DEFAULT_PM8350C_DTS_SOURCE,
                "PM8350C DT",
                4 * 1024 * 1024,
            ),
        )
        encoded = P317.encode_contract(result)
        private = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p317/"
            "must-bind-claim-contract-20260812-01.json"
        ).read_bytes()
        self.assertEqual(encoded, private)
        self.assertEqual(
            result["claim_authority_sha256"],
            "49859c0957a15ef25cdad98137c5f178eb790f4689ddeb74553971d1a9ce3070",
        )


if __name__ == "__main__":
    unittest.main()
