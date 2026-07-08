import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/build_s22plus_m25_hs_only_usb2_acm.py")
TEMPLATE = Path("workspace/public/src/native-init/s22plus_init_usb_acm_m18_full_firststage_park.c")
DTBO = Path("workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/dtbo.img")
VENDOR_DTB = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/unpack-vendor-boot/dtb"
)
VENDOR_RAMDISK = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/"
    "unpack-vendor-boot/vendor_ramdisk00"
)
LZ4 = Path("workspace/private/tools/lz4-local/root/usr/bin/lz4")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("build_s22plus_m25_hs_only_usb2_acm", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusM25HsOnlyUsb2AcmBuildTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_generate_source_marks_hs_only_and_no_m18(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "m25.c"
            text = self.module.generate_m25_source(TEMPLATE, out, 40)

        self.assertIn("S22_NATIVE_INIT_USB_ACM_M25_HS_ONLY", text)
        self.assertIn("s22plus_m25_hs_only_usb2.modules", text)
        self.assertIn("module_group=hs_only_usb2", text)
        self.assertIn("hs_only=1 qmp_excluded=1 maximum_speed_dtbo=high-speed", text)
        self.assertIn('write_attr("/config/usb_gadget/g1/bcdUSB", "0x0200")', text)
        self.assertIn("S22M25HSONLY01", text)
        self.assertNotIn("S22_NATIVE_INIT_USB_ACM_M18_FULL", text)
        self.assertNotIn("full_firststage_usb", text)
        self.assertNotIn("0x0320", text)

    @unittest.skipUnless(DTBO.exists(), "private stock dtbo input missing")
    def test_dtbo_patch_is_equal_length_all_blobs(self):
        image = DTBO.read_bytes()
        summary = self.module.summarize_dtbo_max_speed(image)
        self.assertEqual(summary["blob_count"], 11)
        self.assertEqual(len(summary["patch_targets"]), 11)
        patched, applied = self.module.patch_dtbo_high_speed(image, summary)
        patched_summary = self.module.summarize_dtbo_max_speed(patched)
        self.assertEqual(len(applied), 11)
        self.assertEqual(len(image), len(patched))
        self.assertEqual(patched_summary["patch_targets"], [])
        self.assertNotIn(b"super-speed\0", patched)
        self.assertIn(b"high-speed\0\0", patched)

    @unittest.skipUnless(VENDOR_DTB.exists() and VENDOR_RAMDISK.exists() and LZ4.exists(), "private vendor inputs missing")
    def test_hs_only_closure_excludes_qmp(self):
        m23 = self.module.m23
        with tempfile.TemporaryDirectory() as tmp:
            metadata = m23.extract_vendor_metadata(VENDOR_RAMDISK.resolve(), LZ4.resolve(), Path(tmp))
        derived = self.module.derive_dts_hs_only(
            dtb_image=VENDOR_DTB.read_bytes(),
            compat_to_modules=metadata["compat_to_modules"],
            dep_map=metadata["dep_map"],
            recovery_lines=metadata["recovery_lines"],
        )
        subset = derived["dts_hs_only"]["subset"]
        self.assertEqual(len(subset), 40)
        self.assertIn("phy-msm-snps-hs.ko", subset)
        self.assertIn("phy-msm-snps-eusb2.ko", subset)
        self.assertIn("dwc3-msm.ko", subset)
        self.assertNotIn("phy-msm-ssusb-qmp.ko", subset)
        self.assertNotIn("eud.ko", subset)
        self.assertNotIn("ucsi_glink.ko", subset)

    def test_variant_constants(self):
        self.assertEqual(self.module.MODULES_RAMDISK, "s22plus_m25_hs_only_usb2.modules")
        self.assertEqual(self.module.USB_SERIAL, "S22M25HSONLY01")
        self.assertEqual(self.module.HIGH_SPEED_SAME_LEN_VALUE, b"high-speed\0\0")


if __name__ == "__main__":
    unittest.main()
