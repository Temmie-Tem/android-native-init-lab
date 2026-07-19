import importlib.util
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "build_s22plus_fyg8_r4w1c_watchdog_carrier.py"
SOURCE = ROOT / "workspace/public/src/native-init/s22plus_init_r4w1c_wdt_carrier.c"
INVENTORY = ROOT / "docs/module-map/s22plus-fyg8/inventory.tsv"
MANIFEST = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/"
    "reproduction-h/manifest.json"
)


class S22PlusFyg8R4W1CWatchdogCarrierBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location("r4w1c_builder_tested", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def test_module_specs_match_exact_live_proven_closure(self):
        self.assertEqual(
            [spec["file"] for spec in self.module.MODULE_SPECS],
            self.module.m31b.EXPECTED_WDT_CLOSURE,
        )
        self.assertEqual(
            [spec["runtime"] for spec in self.module.MODULE_SPECS],
            ["smem", "minidump", "qcom_scm", "qcom_wdt_core", "gh_virt_wdt"],
        )

    def test_module_specs_match_static_inventory(self):
        expected = {spec["file"]: spec for spec in self.module.MODULE_SPECS}
        observed = {}
        with INVENTORY.open(encoding="utf-8") as handle:
            for line in handle:
                fields = line.rstrip("\n").split("\t")
                if fields[0] in expected:
                    observed[fields[0]] = {
                        "runtime": fields[1],
                        "sha256": fields[2],
                        "size": int(fields[3]),
                    }
        self.assertEqual(set(observed), set(expected))
        for file_name, spec in expected.items():
            self.assertEqual(observed[file_name]["runtime"], spec["runtime"])
            self.assertEqual(observed[file_name]["sha256"], spec["sha256"])
            self.assertEqual(observed[file_name]["size"], spec["size"])

    def test_source_loads_fixed_order_and_fails_closed(self):
        text = SOURCE.read_text(encoding="utf-8")
        positions = [
            text.index(f'{{"{spec["file"]}",')
            for spec in self.module.MODULE_SPECS
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("result != 0 ? result : closed", text)
        self.assertIn("result != 0)", text)
        self.assertIn("verify_exact_proc_modules", text)
        self.assertIn("line_count != MODULE_COUNT", text)
        self.assertIn("seen[index] != 0U", text)
        self.assertIn("phase=fail_closed reason=module_load", text)
        self.assertIn("phase=fail_closed reason=proc_modules", text)
        self.assertIn("if (emit(k_marker) != 0)", text)
        self.assertLess(
            text.index("if (verify_exact_proc_modules() != 0)"),
            text.index("module_closure_visible=1"),
        )
        self.assertIn("watchdog_ownership=not_directly_proven", text)
        self.assertIn("functional_proof=bounded_live_survival", text)
        self.assertNotIn("watchdog_closure_verified=1", text)

    def test_source_excludes_live_and_persistent_capabilities(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("NR_FINIT_MODULE 273", text)
        self.assertNotIn("NR_REBOOT", text)
        self.assertNotIn("/dev/block", text)
        self.assertNotIn("usb_gadget", text)
        self.assertNotIn("ttyGS0", text)
        self.assertNotIn("ss_acm.0", text)
        self.assertNotIn("/system/bin/init", text)
        self.assertNotIn("LINUX_REBOOT_CMD", text)

    def test_compile_init_produces_static_aarch64_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            receipt = self.module.compile_init(SOURCE, directory / "init", directory)
            self.assertGreater(receipt["size"], 0)
            self.assertEqual(len(receipt["sha256"]), 64)
            self.assertIn("ARM aarch64", receipt["file"])

    def test_exact_file_reader_rejects_size_hash_and_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            value = directory / "value"
            value.write_bytes(b"exact")
            digest = self.module.boot_slice.sha256_bytes(b"exact")
            self.assertEqual(
                self.module.read_exact_file(value, 5, digest, "value"), b"exact"
            )
            with self.assertRaises(self.module.BuildError):
                self.module.read_exact_file(value, 4, digest, "value")
            with self.assertRaises(self.module.BuildError):
                self.module.read_exact_file(value, 5, "0" * 64, "value")
            alias = directory / "alias"
            alias.symlink_to(value)
            with self.assertRaises(self.module.BuildError):
                self.module.read_exact_file(alias, 5, digest, "alias")

    def test_existing_output_fails_before_any_input_or_tool_action(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "exists"
            output.mkdir()
            missing = Path(temporary) / "missing"
            args = Namespace(
                out=output,
                base_boot=missing,
                source=missing,
                vendor_ramdisk=missing,
                image=missing,
                repro_result=missing,
                lz4=missing,
                magiskboot=missing,
            )
            with self.assertRaisesRegex(
                self.module.BuildError, "output path already exists"
            ):
                self.module.build(args)

    def test_builder_has_no_device_or_odin_execution_path(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("run_odin", text)
        self.assertNotIn("DEFAULT_ODIN", text)
        self.assertNotIn('"adb"', text.lower())
        self.assertNotIn("fastboot", text.lower())
        self.assertIn('"odin_invoked": False', text)
        self.assertIn('"device_contact": False', text)
        self.assertIn('"flash": False', text)
        self.assertIn('"live_authorized": False', text)

    @unittest.skipUnless(MANIFEST.exists(), "private R4W1-C manifest missing")
    def test_current_manifest_is_host_only_and_policy_inactive(self):
        manifest = json.loads(MANIFEST.read_text(encoding="ascii"))
        self.assertEqual(manifest["schema"], self.module.SCHEMA)
        self.assertEqual(
            manifest["module_closure"]["files"],
            [spec["file"] for spec in self.module.MODULE_SPECS],
        )
        self.assertEqual(manifest["safety"]["ap_members"], ["boot.img.lz4"])
        self.assertFalse(manifest["safety"]["device_contact"])
        self.assertFalse(manifest["safety"]["odin_invoked"])
        self.assertFalse(manifest["safety"]["flash"])
        self.assertFalse(manifest["safety"]["live_authorized"])
        self.assertTrue(
            manifest["runtime_contract"][
                "module_closure_load_and_visibility_only"
            ]
        )
        self.assertFalse(
            manifest["runtime_contract"][
                "watchdog_functional_ownership_directly_proven"
            ]
        )


if __name__ == "__main__":
    unittest.main()
