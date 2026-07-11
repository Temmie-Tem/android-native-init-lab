import gzip
import importlib.util
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_stock_kernel_baseline.py"


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_stock_kernel_baseline_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8StockKernelBaselineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_extract_ikconfig(self):
        config = b"#\n# Automatically generated file; DO NOT EDIT.\nCONFIG_TEST=y\n"
        image = b"prefix" + self.module.IKCONFIG_START + gzip.compress(config) + self.module.IKCONFIG_END
        self.assertEqual(self.module.extract_ikconfig(image), config)

    def test_parse_arm64_image_header(self):
        image = bytearray(64)
        struct.pack_into("<3Q", image, 8, 0x80000, 0x1234000, 0xA)
        struct.pack_into("<I", image, 56, self.module.ARM64_IMAGE_MAGIC)
        parsed = self.module.parse_arm64_image(bytes(image))
        self.assertEqual(parsed["text_offset"], 0x80000)
        self.assertEqual(parsed["image_size"], 0x1234000)

    def test_decode_os_version(self):
        encoded = (12 << 25) | ((2025 - 2000) << 4) | 8
        parsed = self.module.decode_os_version(encoded)
        self.assertEqual(parsed["os_version"], "12.0.0")
        self.assertEqual(parsed["os_patch_level"], "2025-08")


if __name__ == "__main__":
    unittest.main()
