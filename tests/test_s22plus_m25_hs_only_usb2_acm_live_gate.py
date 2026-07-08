import importlib.util
import sys
import unittest
from unittest.mock import patch
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py")
DRAFT = Path("docs/operations/S22PLUS_M25_HS_ONLY_USB2_ACM_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m25_hs_only_usb2_acm_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m25_hs_only_usb2_acm_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusM25HsOnlyUsb2AcmLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_draft_has_required_markers(self):
        text = DRAFT.read_text(encoding="utf-8")
        self.assertEqual(self.module.missing_policy_markers(text), [])

    def test_policy_marker_check_rejects_missing_ack_and_dtbo_scope(self):
        missing = self.module.missing_policy_markers("S22+ M25 HS-only USB2 ACM native-init boot+DTBO")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.RESTORE_DTBO_ACK_TOKEN, missing)
        self.assertIn("DTBO high-speed cap", missing)
        self.assertIn("phy-msm-ssusb-qmp.ko intentionally excluded", missing)
        self.assertIn("stock DTBO rollback", missing)
        self.assertIn("manual download-mode rollback", missing)

    def test_expected_candidate_hashes_are_pinned(self):
        self.assertEqual(
            self.module.EXPECTED_M25_BOOT_AP_SHA256,
            "7f89cfb8ff188190d1d161aee97e3edec2730bfc46efca9df37f2035f7206805",
        )
        self.assertEqual(
            self.module.EXPECTED_M25_BOOT_SHA256,
            "0ace02ff82be1cb7473879ff52f1c9e8d1491edaa3d9a88b829f901b2c86559f",
        )
        self.assertEqual(
            self.module.EXPECTED_M25_DTBO_AP_SHA256,
            "35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6",
        )
        self.assertEqual(
            self.module.EXPECTED_M25_PATCHED_DTBO_RAW_SHA256,
            "8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17",
        )

    def test_hs_only_module_policy_excludes_fault_path(self):
        modules = set(self.module.EXPECTED_M25_MODULES)
        self.assertEqual(len(modules), 40)
        self.assertIn("phy-msm-snps-hs.ko", modules)
        self.assertIn("phy-msm-snps-eusb2.ko", modules)
        self.assertIn("dwc3-msm.ko", modules)
        self.assertNotIn("phy-msm-ssusb-qmp.ko", modules)
        self.assertNotIn("eud.ko", modules)
        self.assertNotIn("ucsi_glink.ko", modules)
        self.assertNotIn("qcom_wdt_core.ko", modules)

    @unittest.skipUnless(MANIFEST.exists(), "private M25 manifest missing")
    def test_manifest_verifier_accepts_current_m25_build(self):
        with patch.object(self.module, "append_log", lambda *_args, **_kwargs: None):
            self.module.verify_m25_manifest(MANIFEST, Path("/tmp/unused-m25-live-gate-test.log"))


if __name__ == "__main__":
    unittest.main()
