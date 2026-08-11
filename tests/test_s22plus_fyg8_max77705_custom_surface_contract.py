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


def valid_diag_source():
    return r'''
#define S22PLUS_MAX77705_PARENT_COMPATIBLE "maxim,max77705"
#define S22PLUS_MAX77705_MUIC_ADDR 0x25
#define S22PLUS_MAX77705_UIC_INT 0x02
#define S22PLUS_MAX77705_AP_DATAOUT0 0x21
#define S22PLUS_MAX77705_AP_DATAOUT_END 0x41
#define S22PLUS_MAX77705_AP_DATAIN0 0x51
#define S22PLUS_MAX77705_AP_CMD_RESPONSE BIT(7)
#define S22PLUS_MAX77705_CONTROL1_READ 0x05
#define S22PLUS_MAX77705_CONTROL1_WRITE 0x06
#define S22PLUS_MAX77705_COM_USB 0x09
#define S22PLUS_MAX77705_POLL_LIMIT 100U
#define S22PLUS_MAX77705_RETENTION_MS 30000U

static int s22plus_max77705_read_pmic_identity(struct i2c_client *parent)
{
    return i2c_smbus_read_byte_data(parent, 0x00);
}

static int s22plus_max77705_clear_uic_latch_once(struct i2c_client *muic)
{
    int status = i2c_smbus_read_byte_data(muic, S22PLUS_MAX77705_UIC_INT);
    return status < 0 ? status : 0;
}

static int s22plus_max77705_wait_ap_response(struct i2c_client *muic)
{
    unsigned int attempt;
    int status;
    for (attempt = 0; attempt < S22PLUS_MAX77705_POLL_LIMIT; ++attempt) {
        status = i2c_smbus_read_byte_data(muic, S22PLUS_MAX77705_UIC_INT);
        if (status >= 0 && (status & S22PLUS_MAX77705_AP_CMD_RESPONSE))
            return 0;
        usleep_range(1000, 2000);
    }
    return -ETIMEDOUT;
}

static int s22plus_max77705_control1_read_once(struct i2c_client *muic, u8 *value)
{
    u8 command[1] = { S22PLUS_MAX77705_CONTROL1_READ };
    u8 response[2];
    int rc = i2c_smbus_write_i2c_block_data(muic,
        S22PLUS_MAX77705_AP_DATAOUT0, 1, command);
    if (rc < 0)
        return rc;
    rc = i2c_smbus_write_byte_data(muic,
        S22PLUS_MAX77705_AP_DATAOUT_END, 0);
    if (rc < 0)
        return rc;
    rc = s22plus_max77705_wait_ap_response(muic);
    if (rc < 0)
        return rc;
    rc = i2c_smbus_read_i2c_block_data(muic,
        S22PLUS_MAX77705_AP_DATAIN0, 2, response);
    if (rc < 0 || response[0] != S22PLUS_MAX77705_CONTROL1_READ)
        return -EPROTO;
    *value = response[1];
    return 0;
}

static int s22plus_max77705_control1_write_once(struct i2c_client *muic, u8 value)
{
    u8 command[2] = { S22PLUS_MAX77705_CONTROL1_WRITE, value };
    int response;
    int rc = i2c_smbus_write_i2c_block_data(muic,
        S22PLUS_MAX77705_AP_DATAOUT0, 2, command);
    if (rc < 0)
        return rc;
    rc = i2c_smbus_write_byte_data(muic,
        S22PLUS_MAX77705_AP_DATAOUT_END, 0);
    if (rc < 0)
        return rc;
    rc = s22plus_max77705_wait_ap_response(muic);
    if (rc < 0)
        return rc;
    response = i2c_smbus_read_byte_data(muic, S22PLUS_MAX77705_AP_DATAIN0);
    return response == S22PLUS_MAX77705_CONTROL1_WRITE ? 0 : -EPROTO;
}

static int s22plus_max77705_diag_run(struct i2c_client *parent,
                                      struct i2c_client *muic)
{
    u8 pre;
    u8 post1;
    u8 post2;
    int rc = s22plus_max77705_read_pmic_identity(parent);
    if (rc < 0)
        return rc;
    rc = s22plus_max77705_clear_uic_latch_once(muic);
    if (rc < 0)
        return rc;
    rc = s22plus_max77705_control1_read_once(muic, &pre);
    if (rc < 0)
        return rc;
    if (pre != S22PLUS_MAX77705_COM_USB) {
        rc = s22plus_max77705_control1_write_once(muic, S22PLUS_MAX77705_COM_USB);
        if (rc < 0)
            return rc;
    }
    rc = s22plus_max77705_control1_read_once(muic, &post1);
    if (rc < 0)
        return rc;
    msleep(S22PLUS_MAX77705_RETENTION_MS);
    rc = s22plus_max77705_control1_read_once(muic, &post2);
    if (rc < 0)
        return rc;
    return post1 == S22PLUS_MAX77705_COM_USB &&
           post2 == S22PLUS_MAX77705_COM_USB ? 0 : -EPROTO;
}

static int s22plus_max77705_diag_probe(struct i2c_client *parent)
{
    struct i2c_client *muic = devm_i2c_new_dummy_device(
        &parent->dev, parent->adapter, S22PLUS_MAX77705_MUIC_ADDR);
    return s22plus_max77705_diag_run(parent, muic);
}

static const struct of_device_id s22plus_max77705_diag_of_match[] = {
    { .compatible = S22PLUS_MAX77705_PARENT_COMPATIBLE },
    { }
};

static int s22plus_max77705_result_get(char *buffer, const void *arg)
{
    return scnprintf(buffer, PAGE_SIZE, "%s", cached_result);
}

static const struct kernel_param_ops s22plus_max77705_result_ops = {
    .set = NULL,
    .get = s22plus_max77705_result_get,
};
module_param_cb(result, &s22plus_max77705_result_ops, NULL, 0444);

static struct i2c_driver s22plus_max77705_diag_driver = {
    .driver = { .of_match_table = s22plus_max77705_diag_of_match },
    .probe = s22plus_max77705_diag_probe,
};
module_i2c_driver(s22plus_max77705_diag_driver);
'''


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

    def test_full_stack_surface_is_rejected(self):
        with self.assertRaisesRegex(self.module.SurfaceError, "broad effect"):
            self.module.validate_diag_source_text(
                valid_diag_source() + "\nmfd_add_devices(parent, 0, cells, 1, 0, 0, 0);"
            )

    def test_firmware_and_reset_surface_is_rejected(self):
        for token in ("BOOT_FLASH_FW_PASS2", "max77705_reset_ic"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(self.module.SurfaceError, "broad effect"):
                    self.module.validate_diag_source_text(valid_diag_source() + token)

    def test_irq_and_workqueue_surface_is_rejected(self):
        for token in ("request_threaded_irq(", "queue_work("):
            with self.subTest(token=token):
                with self.assertRaisesRegex(self.module.SurfaceError, "broad effect"):
                    self.module.validate_diag_source_text(valid_diag_source() + token)

    def test_notifier_power_and_protocol_surface_is_rejected(self):
        for token in (
            "blocking_notifier_call_chain(",
            "power_supply_",
            "max77705_alternate",
            "max77705_muic_afc",
            "DCD",
        ):
            with self.subTest(token=token):
                with self.assertRaisesRegex(self.module.SurfaceError, "broad effect"):
                    self.module.validate_diag_source_text(valid_diag_source() + token)

    def test_writable_export_surface_is_rejected(self):
        mutated = valid_diag_source().replace("0444", "0644", 1)
        with self.assertRaisesRegex(self.module.SurfaceError, "missing required"):
            self.module.validate_diag_source_text(mutated)

    def test_full_com_usb_byte_is_required(self):
        mutated = valid_diag_source().replace(
            "#define S22PLUS_MAX77705_COM_USB 0x09",
            "#define S22PLUS_MAX77705_COM_USB 0x01",
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "missing required"):
            self.module.validate_diag_source_text(mutated)

    def test_write_must_remain_conditional_on_pre_value(self):
        mutated = valid_diag_source().replace(
            "if (pre != S22PLUS_MAX77705_COM_USB)", "if (true)", 1
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "missing required"):
            self.module.validate_diag_source_text(mutated)

    def test_ambiguous_write_retry_is_rejected(self):
        mutated = valid_diag_source().replace(
            "u8 command[2] = { S22PLUS_MAX77705_CONTROL1_WRITE, value };",
            "u8 command[2] = { S22PLUS_MAX77705_CONTROL1_WRITE, value }; "
            "for (;;) { break; }",
            1,
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "loop|retry"):
            self.module.validate_diag_source_text(mutated)

    def test_second_write_call_site_is_rejected(self):
        needle = (
            "rc = s22plus_max77705_control1_write_once("
            "muic, S22PLUS_MAX77705_COM_USB);"
        )
        mutated = valid_diag_source().replace(needle, needle + "\n        " + needle, 1)
        with self.assertRaisesRegex(self.module.SurfaceError, "one call site"):
            self.module.validate_diag_source_text(mutated)

    def test_post1_read_cannot_be_synthesized_or_moved_inside_write_branch(self):
        source = valid_diag_source()
        post1 = (
            "    rc = s22plus_max77705_control1_read_once(muic, &post1);\n"
            "    if (rc < 0)\n"
            "        return rc;\n"
        )
        mutated = source.replace(
            "    }\n" + post1,
            post1 + "    } else {\n        post1 = pre;\n    }\n",
            1,
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "order|after|synthesized"):
            self.module.validate_diag_source_text(mutated)

    def test_post2_and_retention_window_are_mandatory(self):
        source = valid_diag_source()
        mutations = (
            (
                "#define S22PLUS_MAX77705_RETENTION_MS 30000U",
                "#define S22PLUS_MAX77705_RETENTION_MS 1U",
            ),
            ("msleep(S22PLUS_MAX77705_RETENTION_MS);", ""),
            (
                "s22plus_max77705_control1_read_once(muic, &post2)",
                "s22plus_max77705_control1_read_once(muic, &post1)",
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                mutated = source.replace(old, new, 1)
                with self.assertRaises(self.module.SurfaceError):
                    self.module.validate_diag_source_text(mutated)

    def test_extra_i2c_effect_is_rejected(self):
        mutated = valid_diag_source().replace(
            "return post1 == S22PLUS_MAX77705_COM_USB &&",
            "i2c_smbus_write_word_data(muic, 0x10, 0); "
            "return post1 == S22PLUS_MAX77705_COM_USB &&",
            1,
        )
        with self.assertRaisesRegex(self.module.SurfaceError, "I2C call surface"):
            self.module.validate_diag_source_text(mutated)

    def test_cached_result_getter_cannot_touch_i2c(self):
        mutated = valid_diag_source().replace(
            "return scnprintf(buffer, PAGE_SIZE, \"%s\", cached_result);",
            "i2c_smbus_read_byte_data(client, 0); "
            "return scnprintf(buffer, PAGE_SIZE, \"%s\", cached_result);",
            1,
        )
        with self.assertRaisesRegex(
            self.module.SurfaceError, "I2C call surface|external effect"
        ):
            self.module.validate_diag_source_text(mutated)

    def test_preferred_custom_shape_is_65_modules(self):
        result = self.module.validate_diag_source_text(valid_diag_source())
        self.assertEqual(result["preferred_total_module_count"], 65)
        self.assertEqual(result["control1_read_command_count"], 3)
        self.assertEqual(result["control1_write_maximum_count"], 1)
        self.assertEqual(result["stale_uic_latch_clear_count"], 1)
        self.assertTrue(result["post1_read_is_unconditional"])
        self.assertTrue(result["post2_read_is_after_retention_window"])
        self.assertEqual(result["retention_window_ms"], 30_000)
        self.assertTrue(result["ambiguous_write_retry_forbidden"])

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
        self.assertEqual(
            result["custom_contract"]["selected_design"],
            "POLLING_SINGLE_MODULE_MUX_DIAGNOSTIC",
        )
        self.assertEqual(result["custom_contract"]["preferred_total_module_count"], 65)
        self.assertEqual(
            result["custom_contract"]["rejected_full_pdic_custom_design"]["module_count"],
            66,
        )
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
            "BOUNDED_DIAGNOSTIC_EFFECT_SET_REGISTERED_NOT_IMPLEMENTED",
        )
        diagnostic = result["custom_contract"]["diagnostic"]
        self.assertEqual(
            diagnostic["load_timing"],
            "after gadget path activation and host sidecar arming; the probe "
            "then owns one bounded 30000-ms retention/correlation dwell",
        )
        self.assertTrue(
            diagnostic["initial_uic_read_scope"][
                "whole_register_read_to_clear_accepted"
            ]
        )
        self.assertTrue(
            diagnostic["initial_uic_read_scope"]["raw_initial_byte_must_be_retained"]
        )
        self.assertFalse(
            diagnostic["interpretation_ceiling"][
                "control1_readback_proves_physical_switch_contact"
            ]
        )
        self.assertFalse(
            diagnostic["interpretation_ceiling"][
                "silent_result_refutes_physical_mux_hypothesis"
            ]
        )
        self.assertTrue(
            diagnostic["interpretation_ceiling"][
                "host_attach_is_independent_physical_witness"
            ]
        )
        self.assertEqual(
            result["custom_contract"]["write_inventory"]["retention_window_ms"],
            30_000,
        )


if __name__ == "__main__":
    unittest.main()
