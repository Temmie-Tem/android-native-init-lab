#!/usr/bin/env python3
"""Focused tests for the FYD9-to-FYG8 USB delta H0 audit."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_fyd9_fyg8_usb_delta_audit.py"
)
REPORT = (
    ROOT
    / "docs/reports/"
    "S22PLUS_FYG8_P319_FYD9_FYG8_USB_DELTA_CLOSURE_H0_2026-08-23.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"


def load_module():
    spec = importlib.util.spec_from_file_location("p319_fyd9_fyg8_usb_delta", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319Fyd9Fyg8UsbDeltaAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.closure = cls.module.load_overlay_closure()
        cls.auxiliary = cls.module.load_auxiliary_sources()
        cls.result = cls.module.build_result(cls.closure, cls.auxiliary)

    def test_exact_overlay_census_and_changed_path_partition(self):
        census = self.result["overlay_census"]
        self.assertEqual(census["base_members"], 166_037)
        self.assertEqual(census["delta_members"], 51)
        self.assertEqual(census["changed_regular_files"], 22)
        self.assertEqual(census["identical_directories"], 29)
        self.assertEqual(census["added_members"], 0)
        self.assertEqual(census["p290_applied_matches"], 22)
        self.assertEqual(
            census["changed_categories"],
            {
                "defex": 2,
                "dts_thermal": 11,
                "nfc_snvm": 5,
                "usb_notify": 2,
                "venus_media": 2,
            },
        )
        self.assertEqual(
            tuple(row["path"] for row in census["changed_files"]),
            self.module.EXPECTED_CHANGED_PATHS,
        )
        self.assertTrue(all(row["p290_applied_match"] for row in census["changed_files"]))

    def test_all_eleven_dts_revisions_have_only_the_thermal_substitution(self):
        dts = self.result["dts_delta"]
        self.assertEqual(dts["revision_count"], 11)
        self.assertEqual(dts["usb_related_change_count"], 0)
        self.assertTrue(dts["r12_is_not_unique"])
        self.assertEqual(
            [row["revision"] for row in dts["revisions"]],
            list(self.module.DTS_REVISIONS),
        )
        for row in dts["revisions"]:
            with self.subTest(revision=row["revision"]):
                self.assertEqual(row["old_decimal_value"], 85_000)
                self.assertEqual(row["new_decimal_value"], 80_000)
                self.assertEqual(row["replacement_count"], 13)
                self.assertEqual(row["other_changed_lines"], 0)
                self.assertFalse(row["usb_token_in_changed_lines"])

    def test_usb_delta_records_exact_patches_and_narrow_effect(self):
        usb = self.result["usb_delta"]
        self.assertEqual(tuple(usb["changed_paths"]), self.module.USB_PATHS)
        self.assertEqual(
            [(row["added_lines"], row["removed_lines"]) for row in usb["rows"]],
            [(8, 1), (27, 3)],
        )
        self.assertEqual(
            usb["reserve_state_check"]["still_init_effects"],
            [
                "first_restrict=true",
                "set_notify_disable(NOTIFY_BLOCK_TYPE_HOST)",
                "skip_possible_usb=1",
            ],
        )
        self.assertTrue(
            usb["reserve_state_check"]["possible_usb_event_suppressed_when_skip_is_set"]
        )
        self.assertEqual(
            usb["reserve_state_check"]["host_disable_transition"],
            {
                "emitted_event": "NOTIFY_EVENT_HOST_DISABLE",
                "client_bit_cleared": True,
                "host_bit_set": True,
                "widens_to_all": False,
            },
        )
        self.assertFalse(
            usb["usb_sl_store"]["release_requires_previous_restrict_state"]
        )
        conclusion = self.result["conclusion"]
        self.assertTrue(conclusion["host_restriction_is_not_client_restriction"])
        self.assertFalse(conclusion["direct_gadget_silence_cause_proved"])
        self.assertFalse(conclusion["candidate_bytes_changed"])
        self.assertFalse(conclusion["p319_integration_blockers_changed"])

    def test_source_configuration_keeps_host_and_client_boundaries_distinct(self):
        source = self.result["source_configuration_and_downstream"]
        config = source["configuration"]
        self.assertEqual(config["waipio_gki"], {"USB_NOTIFY_LAYER": "m", "USB_NOTIFIER": "m"})
        self.assertEqual(config["waipio_sec"], {"USB_NOTIFY_LAYER": "m", "USB_NOTIFIER": "m"})
        self.assertFalse(config["DISABLE_LOCKSCREEN_USB_RESTRICTION_explicit"])
        self.assertFalse(config["DISABLE_LOCKSCREEN_USB_RESTRICTION_default"])
        self.assertFalse(config["shipped_binary_reachability_proved_here"])
        downstream = source["downstream"]
        self.assertTrue(downstream["host_and_client_block_bits_are_distinct"])
        self.assertTrue(downstream["possible_usb_maps_to_pdic_delay_done"])
        self.assertFalse(downstream["USB_NOTIFIER_module_value_satisfies_that_ifdef"])

    def test_mutated_reserve_hook_is_rejected(self):
        changed = dict(self.closure.delta_files)
        original = changed[self.module.USB_NOTIFY]
        changed[self.module.USB_NOTIFY] = original.replace(
            b"set_notify_disable(&u_noti->udev, NOTIFY_BLOCK_TYPE_HOST);",
            b"set_notify_disable(&u_noti->udev, NOTIFY_BLOCK_TYPE_ALL);",
            1,
        )
        self.assertNotEqual(changed[self.module.USB_NOTIFY], original)
        with self.assertRaisesRegex(self.module.AuditError, "FYG8 USB source identity differs"):
            self.module.audit_usb_delta(self.closure.base_files, changed)

    def test_mutated_dts_value_is_rejected(self):
        changed = dict(self.closure.delta_files)
        path = self.module.DTS_PATHS[-1]
        original = changed[path]
        changed[path] = original.replace(b"0x13880", b"0x13881", 1)
        self.assertNotEqual(changed[path], original)
        with self.assertRaisesRegex(
            self.module.AuditError, "DTS (change count|added values) differs"
        ):
            self.module.audit_dts_delta(self.closure.base_files, changed)

    def test_mutated_dwc3_gate_is_rejected(self):
        changed = dict(self.auxiliary)
        original = changed["dwc3_core"]
        needle = (
            b"#ifdef CONFIG_USB_NOTIFIER\n"
            b"\tif (role == USB_ROLE_DEVICE) {\n"
            b"\t\tif (is_blocked(get_otg_notify(), NOTIFY_BLOCK_TYPE_CLIENT)) {"
        )
        changed["dwc3_core"] = original.replace(needle, needle.replace(b"#ifdef", b"#if 1  "), 1)
        self.assertNotEqual(changed["dwc3_core"], original)
        with self.assertRaisesRegex(self.module.AuditError, "DWC3 module-value-inactive client gate"):
            self.module.audit_auxiliary_sources(changed)

    def test_download_positive_control_was_already_present(self):
        documents = self.result["document_crosscheck"]
        self.assertTrue(documents["download_positive_control_already_documented"])
        self.assertTrue(documents["normal_boot_com_open_and_download_com_usb_are_distinct"])
        self.assertTrue(documents["predecessor_role_report_omits_fyg8_post_wait_hook"])
        self.assertIn("reserved VBUS", documents["correction_required"])
        self.assertTrue(self.result["conclusion"]["download_positive_control_was_not_missing"])
        self.assertFalse(
            self.result["conclusion"]["max77705_reset_default_required_for_this_conclusion"]
        )

    def test_private_receipt_is_exact_byte_regeneration(self):
        expected = self.module.encode(self.result)
        actual = self.module.OUTPUT.read_bytes()
        info = self.module.OUTPUT.stat()
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 24_861)
        self.assertEqual(
            hashlib.sha256(actual).hexdigest(),
            "3590ab4076df73762edc699dadcadf888b7f6a3e7cc0ab0072a01406a281e82c",
        )
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
        self.assertEqual(info.st_nlink, 1)
        self.assertEqual(stat.S_IMODE(self.module.OUTPUT_ROOT.stat().st_mode), 0o700)
        self.assertEqual(
            self.result["auditor"],
            {
                "path": (
                    "workspace/public/src/scripts/analysis/"
                    "s22plus_fyg8_p319_fyd9_fyg8_usb_delta_audit.py"
                ),
                "size": 35_966,
                "sha256": "d11ccaae3c5cffe7b195325028f53285ba9ae9ead897436910fb6e91fa8ff4a1",
            },
        )

    def test_predecessor_development_receipts_are_preserved(self):
        expected = {
            "fyd9-fyg8-usb-delta-audit-20260823-01": (
                24_617,
                "457d5fafa05dcfa2537f5e14eefa708928483cd7e8b5b9eda8efce7064052b70",
            ),
            "fyd9-fyg8-usb-delta-audit-20260823-02": (
                24_666,
                "244a85f78a77dc91e890fd9be36506cb867f52d5b94ffcf1e2cff06709b58e25",
            ),
        }
        for name, (size, digest) in expected.items():
            with self.subTest(name=name):
                predecessor = self.module.OUTPUT_ROOT.with_name(name) / "result.json"
                data = predecessor.read_bytes()
                info = predecessor.stat()
                self.assertEqual(len(data), size)
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
                self.assertEqual(info.st_nlink, 1)

    def test_report_goal_and_append_only_ledger_are_scoped(self):
        report = REPORT.read_text(encoding="utf-8")
        for token in (
            "P319_FYD9_FYG8_USB_DELTA_CLOSURE_IMPLEMENTED_REVIEW_PENDING",
            "22 changed regular files",
            "11 DTS revisions",
            "`NOTIFY_BLOCK_TYPE_HOST`",
            "does not prove gadget silence",
            "Download positive control was already present",
            "24,861B",
            "3590ab4076df",
            "545 methods",
            "544 passed",
        ):
            with self.subTest(token=token):
                self.assertIn(token, report)
        rows = [
            line
            for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if "| h0-fyd9-fyg8-usb-delta-33 |" in line
        ]
        self.assertEqual(len(rows), 1)
        self.assertIn("P319_FYD9_FYG8_USB_DELTA_CLOSURE_IMPLEMENTED_REVIEW_PENDING", rows[0])
        self.assertNotIn("PASS_GO_", rows[0])
        goal = GOAL.read_text(encoding="utf-8")
        self.assertIn("topic 33", goal)
        self.assertIn("FYD9-to-FYG8 22-file delta", goal)

    def test_authority_axes_are_all_false(self):
        authority = dict(self.result["authority"])
        self.assertTrue(authority.pop("host_only"))
        self.assertFalse(any(authority.values()))


if __name__ == "__main__":
    unittest.main()
