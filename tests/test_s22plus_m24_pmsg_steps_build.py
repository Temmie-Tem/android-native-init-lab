import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/build_s22plus_inplace_m24_pmsg_steps_park.py")
TEMPLATE = Path("workspace/public/src/native-init/s22plus_init_usb_acm_m18_full_firststage_park.c")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("build_s22plus_inplace_m24_pmsg_steps_park", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusM24PmsgStepsBuildTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_generate_source_injects_pmsg_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "m24.c"
            text = self.module.generate_m24_source(TEMPLATE, out, 43)

        self.assertIn("S22_NATIVE_INIT_USB_ACM_M24_PMSG_STEPS", text)
        self.assertIn("A90_STEP:M24:", text)
        self.assertIn('ensure_chr_node("/dev/pmsg0", 0222, 507, 0);', text)
        self.assertIn('emit_pmsg_module(index, name, "module_prepare");', text)
        self.assertIn('emit_pmsg_module(index, name, "module_finit");', text)
        self.assertLess(text.index("setup_minimal_fs();"), text.index('emit_pmsg_phase("pid1_start");'))
        self.assertNotIn("S22_NATIVE_INIT_USB_ACM_M18_FULL", text)
        self.assertNotIn("full_firststage_usb", text)

    def test_variant_constants_are_distinct_from_m23(self):
        self.assertEqual(self.module.MODULES_RAMDISK, "s22plus_m24_pmsg_steps.modules")
        self.assertEqual(self.module.USB_SERIAL, "S22M24PMSG001")
        self.assertEqual(self.module.PMSG_STEP_PREFIX, "A90_STEP:M24:")


if __name__ == "__main__":
    unittest.main()
