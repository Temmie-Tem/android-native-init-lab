import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_custom_surface_contract.py"
)
FULL_STOCK_INPUTS = (
    ROOT
    / "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/vendor_ramdisk00"
)


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_max77705_custom_surface_contract_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT.parent))


class S22PlusFyg8Max77705CustomSurfaceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_parse_firmware_array(self):
        self.assertEqual(
            self.module.parse_firmware_array(
                "const uint8_t BOOT_FLASH_FW_PASS2[] = {0xc1, 0x6e, 0x40};"
            ),
            [0xC1, 0x6E, 0x40],
        )

    def test_stock_source_is_rejected_as_custom(self):
        with self.assertRaisesRegex(self.module.SurfaceError, "custom MFD"):
            self.module.validate_custom_source_texts(
                "max77705_usbc_fw_update BOOT_FLASH_FW_PASS2",
                "PDIC_SYSFS_PROP_CHIP_NAME",
                "",
            )

    def test_mfd_firmware_header_is_rejected_even_without_symbol_use(self):
        with self.assertRaisesRegex(self.module.SurfaceError, "custom MFD"):
            self.module.validate_custom_source_texts(
                "#include <linux/mfd/firmware/example.h> "
                "store_ccic_bin_version 0x6e 0x40 0x15 "
                "max77705_irq_init mfd_add_devices",
                "enum x { PDIC_SYSFS_PROP_CHIP_NAME }; "
                "static int max77705_sysfs_properties[] = {"
                "PDIC_SYSFS_PROP_CHIP_NAME}; "
                "pdic_core_register_chip max77705_muic_probe "
                "max77705_cc_init max77705_pd_init",
                "",
            )

    def test_debug_object_is_rejected(self):
        mfd = (
            "store_ccic_bin_version 0x6e 0x40 0x15 "
            "max77705_irq_init mfd_add_devices"
        )
        pdic = (
            "enum x { PDIC_SYSFS_PROP_CHIP_NAME }; "
            "static int max77705_sysfs_properties[] = {"
            "PDIC_SYSFS_PROP_CHIP_NAME}; "
            "pdic_core_register_chip max77705_muic_probe max77705_cc_init "
            "max77705_pd_init"
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "debug"):
            self.module.validate_custom_source_texts(
                mfd, pdic, "pdic_max77705-y += max77705_debug.o"
            )

    def test_pdic_firmware_payload_reference_is_rejected(self):
        mfd = (
            "store_ccic_bin_version 0x6e 0x40 0x15 "
            "max77705_irq_init mfd_add_devices"
        )
        pdic = (
            "enum x { PDIC_SYSFS_PROP_CHIP_NAME }; "
            "static int max77705_sysfs_properties[] = {"
            "PDIC_SYSFS_PROP_CHIP_NAME}; "
            "pdic_core_register_chip max77705_muic_probe max77705_cc_init "
            "max77705_pd_init BOOT_FLASH_FW_PASS2"
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "custom PDIC"):
            self.module.validate_custom_source_texts(mfd, pdic, "")

    def test_preferred_custom_shape_is_66_modules(self):
        mfd = (
            "store_ccic_bin_version 0x6e 0x40 0x15 "
            "max77705_irq_init mfd_add_devices"
        )
        pdic = (
            "enum x { PDIC_SYSFS_PROP_CHIP_NAME }; "
            "static int max77705_sysfs_properties[] = {"
            "PDIC_SYSFS_PROP_CHIP_NAME}; "
            "pdic_core_register_chip max77705_muic_probe max77705_cc_init "
            "max77705_pd_init"
        )
        result = self.module.validate_custom_source_texts(mfd, pdic, "")
        self.assertEqual(result["preferred_total_module_count"], 66)
        self.assertTrue(result["spu_verify_removed"])

    def test_atomic_json_replaces_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            self.module.atomic_json(output, {"value": 1})
            self.module.atomic_json(output, {"value": 2})
            self.assertEqual(output.read_text(encoding="utf-8"), '{\n  "value": 2\n}\n')

    def test_inventory_parser_rejects_duplicate_names(self):
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "inventory.tsv"
            inventory.write_text(
                "filename\tsize_bytes\tsha256\n"
                "one.ko\t1\ta\n"
                "one.ko\t1\ta\n",
                encoding="ascii",
            )
            digest = self.module.sha256_file(inventory)
            with self.assertRaisesRegex(self.module.SurfaceError, "duplicate"):
                self.module.parse_inventory(
                    inventory, expected_sha256=digest, expected_rows=2
                )

    @unittest.skipUnless(FULL_STOCK_INPUTS.is_file(), "private FYG8 corpus unavailable")
    def test_full_stock_union_and_exclusive_consumers(self):
        result = self.module.audit(ROOT)
        self.assertEqual(
            result["stock_module_union"]["union_unique_module_count"], 491
        )
        self.assertEqual(
            result["stock_module_union"]["vendor_dlkm_only"][
                "vendor_dlkm_only_count"
            ],
            50,
        )
        self.assertEqual(
            set(result["stock_surface"]["exclusive_consumers"]),
            set(self.module.MFD_EXPORTS_CONSUMED_ONLY_BY_PDIC),
        )
        self.assertTrue(
            all(
                consumers == ["pdic_max77705.ko"]
                for consumers in result["stock_surface"][
                    "exclusive_consumers"
                ].values()
            )
        )
        self.assertEqual(result["custom_contract"]["status"], "REGISTERED_NOT_SATISFIED")


if __name__ == "__main__":
    unittest.main()
