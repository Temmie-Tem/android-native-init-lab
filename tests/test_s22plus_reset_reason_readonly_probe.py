import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_reset_reason_readonly_probe.py")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_reset_reason_readonly_probe", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusResetReasonReadonlyProbeTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_remote_file_payload_strips_ls_header(self):
        text = "-r--r----- 1 system system 0 2025-08-04 03:48 /proc/reset_reason\nMPON\n"
        self.assertEqual(self.module.remote_file_payload(text), "MPON")
        self.assertEqual(self.module.first_payload_line(text), "MPON")

    def test_parse_reset_context_structures_pmic_abnormal_summary(self):
        reset_history = """-r-------- 1 system system 0 2025-08-04 03:48 /proc/reset_history
@ Ramdump Auto Summary
@ General Info (RWC=41)
@ Upload Cause = 0x0 / PMIC abnormal reset
@ TZ Reset Info
OEM_RESET_REASON: check rpm or kernel (magic_val:0x910d00f8)
@ Upload Cause = 0x0 / PMIC abnormal reset
OEM_RESET_REASON: check rpm or kernel (magic_val:0x915500f8)
"""
        reset_summary = "<html>PMIC abnormal reset</html>"
        parsed = self.module.parse_reset_context(
            reset_reason_text="-r--r----- 1 system system 0 2025-08-04 03:48 /proc/reset_reason\nMPON\n",
            reset_rwc_text="-r--r----- 1 system system 0 2025-08-04 03:48 /proc/reset_rwc\n41",
            store_lastkmsg_text="-r--r----- 1 system system 0 2025-08-04 03:48 /proc/store_lastkmsg\n1",
            reset_history_text=reset_history,
            reset_summary_text=reset_summary,
        )
        self.assertEqual(parsed["proc_reset_reason_value"], "MPON")
        self.assertEqual(parsed["proc_reset_rwc_value"], "41")
        self.assertEqual(parsed["proc_store_lastkmsg_value"], "1")
        self.assertEqual(parsed["reset_history_upload_cause_count"], 2)
        self.assertEqual(parsed["reset_history_pmic_abnormal_count"], 2)
        self.assertEqual(parsed["reset_summary_pmic_abnormal_count"], 1)
        self.assertEqual(
            parsed["reset_history_upload_causes"],
            ["0x0 / PMIC abnormal reset", "0x0 / PMIC abnormal reset"],
        )
        self.assertEqual(
            parsed["reset_history_oem_reset_magic_values"],
            ["0x910d00f8", "0x915500f8"],
        )


if __name__ == "__main__":
    unittest.main()
