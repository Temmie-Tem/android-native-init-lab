import importlib.util
import json
import struct
import sys
import unittest
from pathlib import Path


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "build_s22plus_v3435_ramoops_console_dtbo.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "build_s22plus_v3435_ramoops_console_dtbo", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3435RamoopsConsoleDtboTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.root = cls.module.repo_root()
        cls.contract_path = cls.root / cls.module.DEFAULT_CONTRACT_OUT
        cls.contract = json.loads(cls.contract_path.read_text(encoding="utf-8"))
        cls.stock_path = cls.root / cls.module.DEFAULT_DTBO
        cls.vendor_path = cls.root / cls.module.DEFAULT_VENDOR_DTB
        cls.candidate_path = (
            cls.root / cls.module.DEFAULT_OUT / "build" / "dtbo.img"
        )
        cls.private_manifest_path = cls.root / cls.module.DEFAULT_OUT / "manifest.json"

    def test_host_only_contract_and_final_objective(self):
        self.assertEqual(self.contract["verdict"], "HOST_BUILD_PASS_NO_LIVE")
        self.assertEqual(
            self.contract["safety"],
            {
                "host_only": True,
                "device_contact": False,
                "reboot": False,
                "flash": False,
                "live_authorized": False,
                "future_partition_scope": "dtbo only after a fresh exception",
                "future_positive_control_first": True,
                "direct_pid1_candidate_authorized": False,
            },
        )
        self.assertIn(
            "without Android userspace", self.contract["objective"]["final_state"]
        )
        self.assertIn(
            "interim", self.contract["objective"]["stock_pid1_supervisor"]
        )

    def test_stock_root_cause_is_all_pmsg_no_console_or_dmesg(self):
        stock = self.contract["stock_ramoops"]
        self.assertEqual(stock["region_size"], 0x200000)
        self.assertEqual(stock["pmsg_size"], 0x200000)
        self.assertEqual(stock["console_size"], 0)
        self.assertEqual(stock["record_size"], 0)
        self.assertEqual(stock["dmesg_size"], 0)
        self.assertEqual(len(stock["vendor_dtb_variants"]), 4)
        for variant in stock["vendor_dtb_variants"]:
            self.assertFalse(variant["has_reg"])
            self.assertEqual(variant["size"], 0x200000)
            self.assertEqual(variant["pmsg_size"], 0x200000)

    def test_kernel_source_contract_makes_console_null_irrelevant(self):
        source = self.contract["source_contract"]
        self.assertEqual(
            source["kernel_config"],
            {
                "CONFIG_PSTORE": "y",
                "CONFIG_PSTORE_CONSOLE": "y",
                "CONFIG_PSTORE_PMSG": "y",
                "CONFIG_PSTORE_RAM": "y",
            },
        )
        self.assertIn("CON_ENABLED", source["console_null_effect"])
        self.assertEqual(
            source["dmesg_space_formula"], "region - console - ftrace - pmsg"
        )

    def test_candidate_layout_is_exact_and_power_of_two(self):
        layout = self.contract["candidate_layout"]
        self.assertEqual(layout["region_size"], 0x200000)
        self.assertEqual(layout["pmsg_size"], 0x100000)
        self.assertEqual(layout["console_size"], 0x80000)
        self.assertEqual(layout["record_size"], 0x40000)
        self.assertEqual(layout["dmesg_size"], 0x80000)
        self.assertEqual(layout["dmesg_record_count"], 2)
        self.assertTrue(layout["sum_exact"])
        self.assertTrue(layout["all_nonzero_sizes_power_of_two"])
        self.assertFalse(layout["new_reserved_region"])
        self.assertFalse(layout["cmdline_change"])

    def test_dt_table_signer_trailer_and_entry_sizes_are_preserved(self):
        container = self.contract["candidate"]["container"]
        self.assertEqual(container["stock_header"], container["candidate_header"])
        self.assertEqual(container["patched_entry_indices"], [9, 10])
        self.assertTrue(container["dt_table_header_and_entries_preserved"])
        self.assertTrue(container["all_fdt_entry_sizes_preserved"])
        self.assertTrue(container["samsung_signer_trailer_preserved"])
        self.assertEqual(container["samsung_signer_trailer_size"], 512)
        for patch in container["patches"]:
            self.assertEqual(patch["growth"], 0)
            self.assertTrue(patch["semantic_diff_allowlist_only"])
            self.assertGreaterEqual(
                patch["string_compaction"]["string_bytes_reclaimed"], 79
            )
            self.assertGreater(patch["string_compaction"]["trailing_padding"], 0)

    def test_candidate_binary_changes_only_target_overlay_semantics(self):
        stock = self.stock_path.read_bytes()
        candidate = self.candidate_path.read_bytes()
        self.assertEqual(len(stock), len(candidate))
        stock_header, stock_entries = self.module.parse_dt_table(stock)
        candidate_header, candidate_entries = self.module.parse_dt_table(candidate)
        self.assertEqual(stock_header, candidate_header)
        self.assertEqual(stock_entries, candidate_entries)
        self.assertEqual(
            stock[stock_header.total_size :], candidate[stock_header.total_size :]
        )

        allowed = {
            (self.module.OVERLAY_NODE, "status"),
            (self.module.OVERLAY_NODE, "pmsg-size"),
            (self.module.OVERLAY_NODE, "console-size"),
            (self.module.OVERLAY_NODE, "record-size"),
        }
        for entry in stock_entries:
            before_blob = self.module.entry_blob(stock, entry)
            after_blob = self.module.entry_blob(candidate, entry)
            if entry.index not in (9, 10):
                self.assertEqual(before_blob, after_blob)
                continue
            before = self.module.property_map(before_blob)
            after = self.module.property_map(after_blob)
            self.assertEqual(
                {key: value for key, value in before.items() if key not in allowed},
                {key: value for key, value in after.items() if key not in allowed},
            )
            self.assertEqual(after[(self.module.OVERLAY_NODE, "status")], b"okay\0")
            self.assertEqual(
                after[(self.module.OVERLAY_NODE, "pmsg-size")],
                struct.pack(">I", 0x100000),
            )
            self.assertEqual(
                after[(self.module.OVERLAY_NODE, "console-size")],
                struct.pack(">I", 0x80000),
            )
            self.assertEqual(
                after[(self.module.OVERLAY_NODE, "record-size")],
                struct.pack(">I", 0x40000),
            )

    def test_every_target_overlay_applies_to_every_vendor_root(self):
        matrix = self.contract["candidate"]["overlay_application_matrix"]
        self.assertEqual(len(matrix), 8)
        self.assertEqual(
            {(row["vendor_root_index"], row["overlay_entry_index"]) for row in matrix},
            {(root, overlay) for root in range(4) for overlay in (9, 10)},
        )
        for row in matrix:
            self.assertTrue(row["pass"])
            self.assertEqual(row["status"], ["okay"])
            self.assertEqual(row["size"], 0x200000)
            self.assertEqual(row["pmsg_size"], 0x100000)
            self.assertEqual(row["console_size"], 0x80000)
            self.assertEqual(row["record_size"], 0x40000)
            self.assertFalse(row["has_reg"])

    def test_artifacts_are_dtbo_only_and_hash_pinned(self):
        candidate = self.contract["candidate"]
        self.assertEqual(self.module.sha256_file(self.candidate_path), candidate["raw_sha256"])
        self.assertEqual(candidate["ap_members"], ["dtbo.img.lz4"])
        ap = self.root / candidate["paths"]["ap_tar_md5"]
        rollback = self.root / candidate["paths"]["rollback_ap_tar_md5"]
        self.assertEqual(self.module.tar_members(ap), ["dtbo.img.lz4"])
        self.assertEqual(self.module.tar_members(rollback), ["dtbo.img.lz4"])
        self.assertEqual(self.module.sha256_file(ap), candidate["ap_tar_md5_sha256"])
        for result in candidate["odin_parse_gate"].values():
            self.assertTrue(result["executed"])
            self.assertTrue(result["archive_check_reached"])
            self.assertTrue(result["invalid_device_boundary_reached"])

    def test_avb_mismatch_is_explicit_and_live_is_blocked(self):
        avb = self.contract["candidate"]["avb_hash_descriptor"]
        self.assertFalse(avb["candidate_matches_stock_descriptor"])
        self.assertTrue(avb["metadata_tail_preserved"])
        self.assertTrue(avb["future_live_requires_verified_boot_disabled_or_resigning"])
        future = self.contract["future_live_gate"]
        self.assertFalse(future["authorized"])
        self.assertIn("Android positive control", future["first_action"])
        self.assertIn("fresh SHA-pinned DTBO exception", future["requires"])
        self.assertIn("intentional-panic", " ".join(future["requires"]))

    def test_private_manifest_and_public_contract_match(self):
        private = json.loads(self.private_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(private["contract"], self.contract)

    def test_builder_contains_no_live_action_path(self):
        source = (self.root / SCRIPT).read_text(encoding="utf-8")
        self.assertNotIn("--live", source)
        self.assertNotIn("adb ", source)
        self.assertNotIn("reboot(", source)
        self.assertNotIn("sysrq-trigger", source)


if __name__ == "__main__":
    unittest.main()
