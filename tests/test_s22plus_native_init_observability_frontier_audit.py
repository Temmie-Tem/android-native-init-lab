import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_native_init_observability_frontier_audit.py")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_native_init_observability_frontier_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusNativeInitObservabilityFrontierAuditTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_uart_classifier_rejects_samsung_android_acm(self):
        result = self.module.classify_tty_candidate(
            "/dev/ttyACM0",
            "ID_VENDOR=SAMSUNG\nID_MODEL=SAMSUNG_Android\nID_SERIAL=usb-SAMSUNG_SAMSUNG_Android_RFCT0000-if01\n",
        )
        self.assertTrue(result["android_serial_hint"])
        self.assertFalse(result["usable_uart_candidate"])

    def test_uart_classifier_accepts_common_usb_uart(self):
        result = self.module.classify_tty_candidate(
            "/dev/ttyUSB0",
            "ID_VENDOR=FTDI\nID_MODEL=FT232R_USB_UART\nID_USB_DRIVER=ftdi_sio\n",
        )
        self.assertTrue(result["uart_adapter_hint"])
        self.assertTrue(result["usable_uart_candidate"])

    def test_decision_prefers_eud_when_ready(self):
        decision = self.module.choose_next(
            {"ready": True},
            {"external_uart_ready": True},
            {"ready": True},
        )
        self.assertEqual(decision["recommended_next"], "promote-eud-openocd-init-probe-live-gate")

    def test_decision_uses_uart_before_m18_fallback(self):
        decision = self.module.choose_next(
            {"ready": False},
            {"external_uart_ready": True},
            {"ready": True},
        )
        self.assertEqual(decision["recommended_next"], "run-uart-console-capture-readiness")

    def test_decision_uses_m18_prefix_when_eud_and_uart_not_ready(self):
        decision = self.module.choose_next(
            {"ready": False},
            {"external_uart_ready": False},
            {"ready": True},
        )
        self.assertEqual(decision["recommended_next"], "prepare-m18-prefix-p00-live-gate-source")


if __name__ == "__main__":
    unittest.main()
