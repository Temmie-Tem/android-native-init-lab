import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1_build.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r4w1_build_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def make_outputs(self, image_size=1024, marker_count=1, config_count=1):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        dist = root / "out/msm-waipio-waipio-gki/gki_kernel/dist"
        config = root / "out/msm-waipio-waipio-gki/gki_kernel/common/.config"
        dist.mkdir(parents=True)
        config.parent.mkdir(parents=True)
        marker = self.module.patch_check.MARKER.encode("ascii")
        payload = marker * marker_count
        (dist / "Image").write_bytes(payload + bytes(max(0, image_size - len(payload))))
        (dist / "vmlinux").write_bytes(marker * marker_count)
        config.write_text(
            "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS=y\n" * config_count,
            encoding="ascii",
        )
        return temporary, root

    def test_witness_gate_accepts_exact_marker_and_config(self):
        temporary, root = self.make_outputs()
        self.addCleanup(temporary.cleanup)
        result = self.module.witness_output_gate(root)
        self.assertTrue(result["verified"])
        self.assertEqual(result["image_marker_count"], 1)

    def test_witness_gate_rejects_duplicate_marker(self):
        temporary, root = self.make_outputs(marker_count=2)
        self.addCleanup(temporary.cleanup)
        self.assertFalse(self.module.witness_output_gate(root)["verified"])

    def test_witness_gate_rejects_missing_config(self):
        temporary, root = self.make_outputs(config_count=0)
        self.addCleanup(temporary.cleanup)
        self.assertFalse(self.module.witness_output_gate(root)["verified"])

    def test_witness_gate_rejects_layout_overflow(self):
        temporary, root = self.make_outputs(
            image_size=self.module.FIXED_KERNEL_SLOT_CAPACITY + 1
        )
        self.addCleanup(temporary.cleanup)
        result = self.module.witness_output_gate(root)
        self.assertFalse(result["verified"])
        self.assertFalse(result["fits_fixed_ramdisk_layout"])


if __name__ == "__main__":
    unittest.main()
