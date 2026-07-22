import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path("workspace/public/src/scripts/revalidation").resolve()
SCRIPT = SCRIPT_DIR / "s22plus_o2_module_plan.py"
FYG8_METADATA = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules"
)


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_o2_module_plan", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_metadata(root: Path, *, dep, softdep="", load="", recovery="", alias="", blocklist="", options=None):
    values = {
        "modules.dep": dep,
        "modules.softdep": softdep,
        "modules.load": load,
        "modules.load.recovery": recovery,
        "modules.alias": alias,
        "modules.blocklist": blocklist,
    }
    for name, text in values.items():
        (root / name).write_text(text, encoding="utf-8")
    if options is not None:
        (root / "modules.options").write_text(options, encoding="utf-8")


class S22PlusO2ModulePlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def fixture(self, root: Path, **overrides):
        values = {
            "dep": (
                "/lib/modules/root.ko: /lib/modules/hard-b.ko /lib/modules/hard-a.ko\n"
                "/lib/modules/hard-a.ko:\n"
                "/lib/modules/hard-b.ko:\n"
                "/lib/modules/pre-one.ko: /lib/modules/pre-dep.ko\n"
                "/lib/modules/pre-dep.ko:\n"
                "/lib/modules/post-one.ko: /lib/modules/post-dep.ko\n"
                "/lib/modules/post-dep.ko:\n"
            ),
            "softdep": "softdep root pre: pre_one post: post_one\n",
            "load": "hard-a.ko\npre-dep.ko\npre-one.ko\n",
            "recovery": "hard-b.ko\nroot.ko\npost-dep.ko\npost-one.ko\n",
            "alias": "alias exact:test root\n",
            "blocklist": "blocklist unrelated\n",
        }
        values.update(overrides)
        write_metadata(root, **values)
        return self.module.load_metadata(root)

    def test_hard_and_soft_dependencies_form_one_ordered_dag(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = self.fixture(Path(tmp))
            plan = self.module.build_plan(metadata, ["root.ko"])
        positions = {name: index for index, name in enumerate(plan.modules)}
        for before in ["hard-a.ko", "hard-b.ko", "pre-dep.ko", "pre-one.ko"]:
            self.assertLess(positions[before], positions["root.ko"])
        self.assertLess(positions["root.ko"], positions["post-one.ko"])
        self.assertLess(positions["post-dep.ko"], positions["post-one.ko"])

    def test_stock_order_breaks_ties_without_overriding_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = self.fixture(Path(tmp))
            plan = self.module.build_plan(metadata, ["root.ko"])
        self.assertLess(plan.modules.index("hard-a.ko"), plan.modules.index("hard-b.ko"))
        self.assertLess(plan.modules.index("post-dep.ko"), plan.modules.index("post-one.ko"))

    def test_exact_alias_root_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = self.fixture(Path(tmp))
            plan = self.module.build_plan(metadata, ["alias:exact:test"])
        self.assertEqual(plan.resolved_roots, ("root.ko",))

    def test_blocklisted_selected_module_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = self.fixture(Path(tmp), blocklist="blocklist hard_a\n")
            with self.assertRaisesRegex(self.module.PlanError, "intersects stock modules.blocklist"):
                self.module.build_plan(metadata, ["root.ko"])

    def test_options_are_carried_to_tsv_and_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = self.fixture(Path(tmp), options="options root answer=42 debug=0\n")
            plan = self.module.build_plan(metadata, ["root.ko"])
            tsv = self.module.render_plan_tsv(metadata, plan)
            header = self.module.render_plan_header(metadata, plan)
        self.assertIn("root.ko\troot\tanswer=42 debug=0\n", tsv)
        self.assertIn('"answer=42 debug=0"', header)

    def test_cycle_across_hard_and_soft_edges_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = self.fixture(
                Path(tmp),
                softdep="softdep root pre: pre_one\nsoftdep pre_one pre: root\n",
            )
            with self.assertRaisesRegex(self.module.PlanError, "dependency cycle"):
                self.module.build_plan(metadata, ["root.ko"])

    def test_unresolved_softdep_is_fatal_only_when_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = self.fixture(Path(tmp), softdep="softdep root pre: missing\n")
            with self.assertRaisesRegex(self.module.PlanError, "does not resolve"):
                metadata.resolve("missing")
            with self.assertRaisesRegex(self.module.PlanError, "unresolved softdep"):
                self.module.build_plan(metadata, ["root.ko"])

    def test_only_exact_pinned_unresolved_softdep_is_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata = self.fixture(
                Path(tmp),
                dep=(
                    "/lib/modules/pinctrl-waipio.ko:\n"
                    "/lib/modules/other.ko:\n"
                ),
                softdep=(
                    "softdep pinctrl_waipio pre: qcom_tlmm_vm_irqchip\n"
                    "softdep other pre: still_missing\n"
                ),
                load="pinctrl-waipio.ko\nother.ko\n",
                recovery="pinctrl-waipio.ko\nother.ko\n",
                alias="alias exact:pinctrl pinctrl_waipio\n",
            )
            plan = self.module.build_plan(metadata, ["pinctrl-waipio.ko"])
            self.assertEqual(
                plan.tolerated_unresolved_softdeps,
                {"pinctrl-waipio.ko": ("pre:qcom_tlmm_vm_irqchip",)},
            )
            with self.assertRaisesRegex(self.module.PlanError, "unresolved softdep"):
                self.module.build_plan(metadata, ["other.ko"])

    def test_duplicate_normalized_module_name_is_fatal(self):
        with self.assertRaisesRegex(self.module.PlanError, "ambiguous normalized module name"):
            self.module.parse_modules_dep(
                "/lib/modules/a-b.ko:\n/lib/modules/a_b.ko:\n"
            )

    def test_fixture_rendering_is_structured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata_dir = root / "metadata"
            metadata_dir.mkdir()
            metadata = self.fixture(metadata_dir)
            plan = self.module.build_plan(metadata, ["root.ko"])
            tsv = self.module.render_plan_tsv(metadata, plan)
            header = self.module.render_plan_header(metadata, plan)
        self.assertEqual(len(tsv.splitlines()), len(plan.modules))
        self.assertIn("S22PLUS_O2_MODULE_PLAN_COUNT", header)
        self.assertIn("S22PLUS_O2_BIND_GATE_COUNT", header)

    @unittest.skipUnless(FYG8_METADATA.is_dir(), "FYG8 module metadata is not present")
    def test_real_fyg8_metadata_and_default_plan(self):
        metadata = self.module.load_metadata(FYG8_METADATA.resolve())
        self.module.verify_fyg8_pins(metadata)
        plan = self.module.build_plan(metadata, self.module.DEFAULT_ROOTS)
        contract = self.module.validate_plan_contract(metadata, plan)
        self.module.verify_default_plan_identity(metadata, plan)
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.module.write_outputs(Path.cwd(), Path(tmp), metadata, plan)
            loaded = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
        positions = {name: index for index, name in enumerate(plan.modules)}
        self.assertEqual(len(metadata.files), 441)
        self.assertEqual(len(plan.modules), self.module.EXPECTED_DEFAULT_PLAN_COUNT)
        self.assertEqual(
            self.module.sha256_text(self.module.render_plan_tsv(metadata, plan)),
            self.module.EXPECTED_DEFAULT_PLAN_TSV_SHA256,
        )
        self.assertFalse(metadata.options_file_present)
        self.assertLess(positions["qcom_hwspinlock.ko"], positions["smem.ko"])
        self.assertLess(positions["qrtr.ko"], positions["qmi_helpers.ko"])
        self.assertLess(positions["dwc3-msm.ko"], positions["ucsi_glink.ko"])
        self.assertEqual([gate["order"] for gate in contract["functional_bind_gates"]], list(range(1, 9)))
        for name in ["cmd-db.ko", "qcom_rpmh.ko", "gcc-waipio.ko", "dwc3-msm.ko"]:
            self.assertIn(name, plan.modules)
        self.assertEqual(loaded["schema"], self.module.SCHEMA)
        self.assertEqual(loaded["plan"]["module_count"], len(plan.modules))
        self.assertTrue(manifest["safety"]["host_only"])
        self.assertFalse(manifest["safety"]["flash"])

    @unittest.skipUnless(FYG8_METADATA.is_dir(), "FYG8 module metadata is not present")
    def test_real_fyg8_o3_minimal_acm_plan_identity(self):
        metadata = self.module.load_metadata(FYG8_METADATA.resolve())
        self.module.verify_fyg8_pins(metadata)
        plan = self.module.build_plan(metadata, self.module.O3_MINIMAL_ACM_ROOTS)
        self.module.validate_plan_contract(metadata, plan)
        self.module.verify_o3_minimal_acm_plan_identity(metadata, plan)
        self.assertEqual(len(plan.modules), self.module.EXPECTED_O3_MINIMAL_ACM_PLAN_COUNT)
        self.assertEqual(
            self.module.sha256_text(self.module.render_plan_tsv(metadata, plan)),
            self.module.EXPECTED_O3_MINIMAL_ACM_PLAN_TSV_SHA256,
        )
        self.assertEqual(
            plan.tolerated_unresolved_softdeps,
            {"pinctrl-waipio.ko": ("pre:qcom_tlmm_vm_irqchip",)},
        )
        for name in [
            "pinctrl-waipio.ko",
            "qcom-pdc.ko",
            "qnoc-waipio.ko",
            "arm_smmu.ko",
            "qcom_wdt_core.ko",
            "gh_virt_wdt.ko",
            "dwc3-msm.ko",
        ]:
            self.assertIn(name, plan.modules)

    @unittest.skipUnless(FYG8_METADATA.is_dir(), "FYG8 module metadata is not present")
    def test_real_fyg8_e2_profile_identity_and_foundation(self):
        metadata = self.module.load_metadata(FYG8_METADATA.resolve())
        self.module.verify_fyg8_pins(metadata)
        plan = self.module.build_e2_profile_plan(metadata)
        self.module.validate_plan_contract(metadata, plan)
        self.module.verify_e2_profile_plan_identity(metadata, plan)
        self.assertEqual(
            plan.modules[: len(self.module.E2_PROVEN_E1B_FOUNDATION)],
            self.module.E2_PROVEN_E1B_FOUNDATION,
        )
        self.assertEqual(len(plan.modules), self.module.EXPECTED_E2_PROFILE_PLAN_COUNT)
        self.assertEqual(len(plan.constraints), 210)
        self.assertEqual(
            self.module.sha256_text(self.module.render_plan_tsv(metadata, plan)),
            self.module.EXPECTED_E2_PROFILE_PLAN_TSV_SHA256,
        )

    def test_source_has_no_device_or_flash_command(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ["adb reboot", "odin4 -a", "fastboot flash", "dd of=/dev/block"]:
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
