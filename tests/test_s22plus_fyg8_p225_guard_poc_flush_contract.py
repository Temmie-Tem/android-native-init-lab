import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "s22plus_fyg8_p225_guard_poc_flush_contract.py"


def load_module():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_p225_guard_poc_flush_contract_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


class S22PlusFyg8P225GuardPocFlushContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_current_node_and_parent_bus_decoders_diverge_exactly(self):
        result = self.module.check_reg_semantics(self.module.REG_CELLS)
        self.assertEqual(
            result["current_node_2_2"],
            {"base": 0x800200000, "size": 0x200000},
        )
        self.assertEqual(
            result["parent_node_1_1_resource_zero"],
            {"base": 0x8, "size": 0x200000},
        )
        self.assertTrue(result["semantic_mismatch_proven"])

    def test_reg_decoder_rejects_short_invalid_and_drifted_shapes(self):
        invalid = (
            ((0x8,), 1, 1),
            ((0x8, 0x200000), 2, 2),
            ((-1, 0x200000), 1, 1),
            ((0x1_0000_0000, 0x200000), 1, 1),
        )
        for cells, address_cells, size_cells in invalid:
            with self.subTest(cells=cells):
                with self.assertRaises(self.module.CheckError):
                    self.module.decode_reg_cells(
                        cells, address_cells, size_cells
                    )
        with self.assertRaisesRegex(self.module.CheckError, "changed"):
            self.module.check_reg_semantics((0x8, 0x200000, 0, 0x100000))

    def test_patch_applies_with_guard_and_flush_order(self):
        source = ROOT / self.module.DEFAULT_SOURCE
        if not source.is_dir():
            self.skipTest("private FYG8 source is not present")
        patch = ROOT / self.module.DEFAULT_PATCH
        patch_result = self.module.check_patch(patch)
        source_result = self.module.apply_and_check(source, patch)
        self.assertTrue(patch_result["record_bytes_unchanged_from_p219"])
        self.assertTrue(source_result["current_node_reg_parser"])
        self.assertTrue(source_result["generic_resource_helper_absent"])
        self.assertTrue(source_result["copy_poc_flush_readback_order"])
        self.assertFalse(source_result["reset_retention_proven"])
        self.assertTrue(source_result["pre_post_header_checks"])

    def test_exact_stock_rev12_overlay_on_both_waipio_bases(self):
        paths = (
            self.module.DEFAULT_DTBO,
            self.module.DEFAULT_VENDOR_DTB,
            self.module.DEFAULT_FDTOVERLAY,
            self.module.DEFAULT_LIBFDT,
        )
        if not all((ROOT / path).is_file() for path in paths):
            self.skipTest("private FYG8 DT inputs or tools are not present")
        result = self.module.check_stock_dtb(
            ROOT,
            ROOT / self.module.DEFAULT_DTBO,
            ROOT / self.module.DEFAULT_VENDOR_DTB,
            ROOT / self.module.DEFAULT_FDTOVERLAY,
            ROOT / self.module.DEFAULT_LIBFDT,
        )
        self.assertEqual(result["active_overlay_index"], 10)
        self.assertEqual(result["applicable_base_indices"], [0, 1])
        self.assertEqual(len(result["merged_bases"]), 2)
        self.assertTrue(result["generic_parser_regression_proven"])
        self.assertTrue(result["samsung_parser_target_proven"])
        self.assertTrue(result["direct_map_prerequisites_proven"])
        for merged in result["merged_bases"]:
            self.assertEqual(
                merged["direct_map"]["memory_node"],
                "/reserved-memory/sec_debug_region_log@8001FF000",
            )
            self.assertTrue(merged["direct_map"]["contains_log_range"])
            self.assertFalse(merged["direct_map"]["no_map"])

    def test_record_and_observer_wire_bytes_remain_p219(self):
        result = self.module.check_record_derivation()
        self.assertEqual(
            result["contract_sha256"],
            "a01800f437cf129e693f32b7199ea6a613dd2366fff82ca45083f2098fd13bae",
        )
        blob = (
            b"prefix"
            + self.module.ENTRY_PROOF
            + self.module.USERSPACE_PROOF
            + self.module.UNSAT_PROOF
            + b"suffix"
        )
        compiled = self.module.classify_compiled_blob(blob, "synthetic")
        self.assertEqual(compiled["entry_count"], 1)
        self.assertEqual(compiled["userspace_count"], 1)
        self.assertEqual(compiled["unsat_count"], 1)


if __name__ == "__main__":
    unittest.main()
