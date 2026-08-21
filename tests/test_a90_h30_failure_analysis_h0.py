"""Host-only checks for the A90 H30 failure-analysis design."""

from __future__ import annotations

import unittest
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = (
    ROOT
    / "docs/plans/"
    "A90_H30_F1_FAILURE_ANALYSIS_RECONCILIATION_AND_LAST_KMSG_DESIGN_2026-08-21.md"
)
BACKEND = (
    ROOT
    / "workspace/public/src/scripts/server-distro/"
    "a90_f1_candidate_return_backend_v1.py"
)
ADAPTER = (
    ROOT
    / "workspace/public/src/scripts/server-distro/"
    "a90_boot_only_f1_adapter_v1.py"
)
MENU_HIDE = (
    ROOT
    / "workspace/public/src/scripts/server-distro/"
    "a90_h28_menu_hide_health_reconcile_v1.py"
)
RECONCILER = (
    ROOT
    / "workspace/public/src/scripts/server-distro/"
    "a90_h30_prewrite_reconcile_v1.py"
)


class A90H30FailureAnalysisDesignTest(unittest.TestCase):
    def test_design_declares_ordered_h0_boundary_and_source_contract(self):
        text = PLAN.read_text(encoding="utf-8")
        self.assertLess(text.index("## 1."), text.index("## 2."))
        self.assertLess(text.index("## 2."), text.index("## 3."))
        self.assertLess(text.index("## 3."), text.index("## 4."))
        for required in (
            "source | /proc/last_kmsg",
            "decoder | a90-proc-last-kmsg-raw-v1",
            "policy_id | A90_TWRP_FAILED_BOOT_LAST_KMSG_READONLY_V1",
            "source_contract_id | A90_PROC_LAST_KMSG_0444_NO_MOUNT_V1",
            "cat /proc/cmdline",
            "cat /proc/last_kmsg",
            "before any rollback write",
            "candidateReplay=false",
            "pstore entry count is diagnostic only",
        ):
            self.assertIn(required, text)

    def test_native_backend_has_no_adb_call_in_exact_native_usb_branch(self):
        text = BACKEND.read_text(encoding="utf-8")
        native_branch = text[
            text.index("if (", text.index("def _inventory"))
            : text.index("elif len(samsung_rows)", text.index("def _inventory"))
        ]
        self.assertIn("adb_raw = None", native_branch)
        self.assertNotIn('"adb-inventory"', native_branch)

    def test_active_health_consumers_do_not_use_entries_zero_as_predicate(self):
        adapter_text = ADAPTER.read_text(encoding="utf-8")
        menu_text = MENU_HIDE.read_text(encoding="utf-8")
        self.assertNotIn('count("entries=0")', adapter_text)
        self.assertNotIn('count("entries=0")', menu_text)
        self.assertIn("diagnostic receipt only", menu_text)

    def test_fixed_h30_reconciler_proves_no_write_without_guard_mutation(self):
        sys.path.insert(0, str(RECONCILER.parent))
        spec = importlib.util.spec_from_file_location(
            "a90_h30_prewrite_reconcile_v1", RECONCILER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        result = module.reconcile()
        self.assertEqual(result["decision"], "PREWRITE_ABORTED_NO_BOOT_WRITE")
        self.assertEqual(result["candidateWriteCount"], 0)
        self.assertEqual(result["rollbackWriteCount"], 0)
        self.assertFalse(result["deviceContact"])
        self.assertFalse(result["durableJournalPublication"])
        self.assertEqual(result["guards"], "retained")
        self.assertTrue(result["reviewRequiredBeforeClosure"])


if __name__ == "__main__":
    unittest.main()
