import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_super_module_layout.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location("s22plus_fyg8_super_module_layout_tested", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class FakeReader:
    def __init__(self):
        self.entries = {
            3: (("lib", 4, 2), ("readme", 5, 1)),
            4: (("modules", 6, 2),),
            6: (("one.ko", 7, 1), ("metadata", 8, 1)),
        }

    def directory(self, inode):
        module = S22PlusFyg8SuperModuleLayoutTest.module
        return tuple(module.Dentry(child, file_type, name) for name, child, file_type in self.entries.get(inode, ()))


class S22PlusFyg8SuperModuleLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_walk_finds_module_directory_and_files(self):
        result = self.module.walk_filesystem(FakeReader())
        self.assertEqual(result["module_directories"], ["/lib/modules"])
        self.assertEqual(result["module_files"], ["/lib/modules/one.ko"])
        self.assertEqual(result["directory_count"], 3)

    def test_expected_partition_set_has_no_system_dlkm_partition(self):
        self.assertEqual(
            set(self.module.EXPECTED_PARTITIONS),
            {"system", "odm", "product", "system_ext", "vendor", "vendor_dlkm"},
        )
        self.assertEqual(self.module.EXPECTED_UNION_MODULES, 491)


if __name__ == "__main__":
    unittest.main()
