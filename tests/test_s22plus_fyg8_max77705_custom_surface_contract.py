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


def valid_custom_sources():
    mfd = (
        "store_ccic_bin_version 0x6e 0x40 0x15 "
        "max77705_irq_init mfd_add_devices"
    )
    pdic = (
        "enum x { PDIC_SYSFS_PROP_CHIP_NAME }; "
        "static int max77705_sysfs_properties[] = {"
        "PDIC_SYSFS_PROP_CHIP_NAME}; "
        "pdic_core_register_chip max77705_muic_probe max77705_cc_init "
        "max77705_pd_init usbc_data->typec_cap.ops = NULL; "
        "typec_register_port "
        "static void max77705_usbpd_set_host_on(void *data, int mode) { "
        "struct max77705_usbc_platform_data *usbpd_data = data; "
        "if (mode) { usbpd_data->device_add = 0; "
        "usbpd_data->detach_done_wait = 0; "
        "usbpd_data->host_turn_on_event = 1; "
        "wake_up_interruptible(&usbpd_data->host_turn_on_wait_q); } "
        "else { usbpd_data->device_add = 0; "
        "usbpd_data->detach_done_wait = 0; "
        "usbpd_data->host_turn_on_event = 0; } } "
        "struct usbpd_ops ops_usbpd = { "
        ".usbpd_sbu_test_read = NULL, "
        ".usbpd_set_host_on = max77705_usbpd_set_host_on, "
        ".usbpd_cc_control_command = NULL, "
        ".usbpd_wait_entermode = NULL, }; "
        "usbpd_d->ops = &ops_usbpd; register_usbpd(usbpd_d) "
        "pdic_manual_ccopen_request(0);"
    )
    muic = (
        "max77705_muic_probe max77705_muic_init_regs "
        "max77705_muic_init_detect com_to_usb_ap "
        "muic_data->muic_d.ops = NULL; "
        "register_muic(&(muic_data->muic_d))"
    )
    pd = (
        "max77705_pd_init "
        "max77705_set_fw_noautoibus(MAX77705_AUTOIBUS_AT_OFF); "
        "fp_sec_pd_select_pdo = NULL; fp_sec_pd_select_pps = NULL; "
        "fp_sec_pd_vpdo_auth = NULL; "
        "fp_sec_pd_manual_ccopen_req = NULL; "
        "fp_sec_pd_change_src = NULL;"
    )
    return mfd, pdic, muic, pd, ""


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
        _mfd, pdic, muic, pd, makefile = valid_custom_sources()
        with self.assertRaisesRegex(self.module.SurfaceError, "custom MFD"):
            self.module.validate_custom_source_texts(
                "max77705_usbc_fw_update BOOT_FLASH_FW_PASS2",
                pdic,
                muic,
                pd,
                makefile,
            )

    def test_mfd_firmware_header_is_rejected_even_without_symbol_use(self):
        _mfd, pdic, muic, pd, makefile = valid_custom_sources()
        with self.assertRaisesRegex(self.module.SurfaceError, "custom MFD"):
            self.module.validate_custom_source_texts(
                "#include <linux/mfd/firmware/example.h> "
                "store_ccic_bin_version 0x6e 0x40 0x15 "
                "max77705_irq_init mfd_add_devices",
                pdic,
                muic,
                pd,
                makefile,
            )

    def test_debug_object_is_rejected(self):
        mfd, pdic, muic, pd, _makefile = valid_custom_sources()
        with self.assertRaisesRegex(self.module.SurfaceError, "debug"):
            self.module.validate_custom_source_texts(
                mfd,
                pdic,
                muic,
                pd,
                "pdic_max77705-y += max77705_debug.o",
            )

    def test_pdic_firmware_payload_reference_is_rejected(self):
        mfd, pdic, muic, pd, makefile = valid_custom_sources()
        with self.assertRaisesRegex(self.module.SurfaceError, "custom PDIC"):
            self.module.validate_custom_source_texts(
                mfd, pdic + " BOOT_FLASH_FW_PASS2", muic, pd, makefile
            )

    def test_muic_attribute_group_is_rejected(self):
        mfd, pdic, muic, pd, makefile = valid_custom_sources()
        with self.assertRaisesRegex(self.module.SurfaceError, "custom MUIC"):
            self.module.validate_custom_source_texts(
                mfd, pdic, muic + " max77705_muic_group", pd, makefile
            )

    def test_typec_role_mutation_ops_are_rejected(self):
        mfd, pdic, muic, pd, makefile = valid_custom_sources()
        with self.assertRaisesRegex(self.module.SurfaceError, "custom PDIC"):
            self.module.validate_custom_source_texts(
                mfd, pdic + " max77705_ops", muic, pd, makefile
            )

    def test_if_cb_wait_callback_is_rejected(self):
        mfd, pdic, muic, pd, makefile = valid_custom_sources()
        with self.assertRaisesRegex(self.module.SurfaceError, "custom PDIC"):
            self.module.validate_custom_source_texts(
                mfd,
                pdic + " static void max77705_usbpd_wait_entermode(",
                muic,
                pd,
                makefile,
            )

    def test_if_cb_host_callback_cannot_gain_hardware_effect(self):
        mfd, pdic, muic, pd, makefile = valid_custom_sources()
        mutated = pdic.replace(
            "if (mode) {",
            "max77705_write_reg(client, reg, value); if (mode) {",
            1,
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "gains a hardware"):
            self.module.validate_custom_source_texts(
                mfd, mutated, muic, pd, makefile
            )

    def test_sec_pd_mutation_callback_is_rejected(self):
        mfd, pdic, muic, pd, makefile = valid_custom_sources()
        with self.assertRaisesRegex(self.module.SurfaceError, "custom PD"):
            self.module.validate_custom_source_texts(
                mfd,
                pdic,
                muic,
                pd.replace(
                    "fp_sec_pd_manual_ccopen_req = NULL;",
                    "fp_sec_pd_manual_ccopen_req = pdic_manual_ccopen_request;",
                ),
                makefile,
            )

    def test_preferred_custom_shape_is_66_modules(self):
        result = self.module.validate_custom_source_texts(*valid_custom_sources())
        self.assertEqual(result["preferred_total_module_count"], 66)
        self.assertTrue(result["spu_verify_removed"])
        self.assertTrue(result["max77705_muic_attribute_group_removed"])
        self.assertTrue(result["typec_role_mutation_ops_removed"])

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
        self.assertEqual(result["p315_plan"]["module_count"], 61)
        self.assertEqual(
            result["stock_surface"]["pdic_control_export_consumers"],
            self.module.PDIC_CONTROL_EXPORT_CONSUMERS,
        )
        self.assertEqual(
            result["stock_surface"]["if_cb_export_consumers"],
            self.module.IF_CB_EXPORT_CONSUMERS,
        )
        self.assertEqual(
            result["stock_surface"]["common_muic_sysfs"][
                "tree_wide_driver_c_definition_only"
            ],
            ["drivers/muic/common/muic_sysfs.c"],
        )
        self.assertEqual(
            result["custom_contract"]["write_inventory"]["status"],
            "SOURCE_DERIVED_PARTIAL_NOT_COMPLETE",
        )


if __name__ == "__main__":
    unittest.main()
