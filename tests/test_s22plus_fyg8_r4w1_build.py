import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
        with mock.patch.object(self.module, "FIXED_KERNEL_SLOT_CAPACITY", 4096):
            result = self.module.witness_output_gate(root)
        self.assertTrue(result["verified"])
        self.assertEqual(result["image_marker_count"], 1)
        self.assertTrue(result["preserves_fixed_ramdisk_start"])

    def test_witness_gate_rejects_duplicate_marker(self):
        temporary, root = self.make_outputs(marker_count=2)
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(self.module, "FIXED_KERNEL_SLOT_CAPACITY", 4096):
            self.assertFalse(self.module.witness_output_gate(root)["verified"])

    def test_witness_gate_rejects_missing_config(self):
        temporary, root = self.make_outputs(config_count=0)
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(self.module, "FIXED_KERNEL_SLOT_CAPACITY", 4096):
            self.assertFalse(self.module.witness_output_gate(root)["verified"])

    def test_witness_gate_rejects_layout_overflow(self):
        temporary, root = self.make_outputs(image_size=4097)
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(self.module, "FIXED_KERNEL_SLOT_CAPACITY", 4096):
            result = self.module.witness_output_gate(root)
        self.assertFalse(result["verified"])
        self.assertFalse(result["fits_fixed_ramdisk_layout"])

    def test_witness_gate_rejects_smaller_alignment_bucket(self):
        temporary, root = self.make_outputs(image_size=4096)
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(self.module, "FIXED_KERNEL_SLOT_CAPACITY", 8192):
            result = self.module.witness_output_gate(root)
        self.assertFalse(result["verified"])
        self.assertFalse(result["preserves_fixed_ramdisk_start"])

    def test_kmi_path_control_is_exact_and_restored(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            path = root / self.module.BUILD_SH_PATH
            path.parent.mkdir(parents=True)
            content = (
                "prefix\n" + self.module.KMI_PATH_ORIGINAL + "suffix\n"
            ).encode("ascii")
            path.write_bytes(content)
            expected_sha256 = self.module.base.sha256_file(path)
            with mock.patch.object(self.module, "BUILD_SH_SHA256", expected_sha256):
                control = self.module.inspect_kmi_path_control(root)
                self.assertTrue(control["verified"])
                with self.module.apply_kmi_path_control(root, control) as runtime:
                    self.assertIn(
                        self.module.KMI_PATH_REPRODUCIBLE,
                        path.read_text(encoding="ascii"),
                    )
            self.assertEqual(path.read_bytes(), content)
            self.assertTrue(runtime["restored"])

    def test_vdso_debug_control_is_exact_and_restored(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            controls = []
            originals = {}
            for index, spec in enumerate(self.module.VDSO_DEBUG_CONTROLS):
                path = root / spec["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                content = (f"prefix-{index}\n" + spec["original"] + "suffix\n").encode(
                    "ascii"
                )
                path.write_bytes(content)
                originals[path] = content
                controls.append({**spec, "sha256": self.module.base.sha256_file(path)})
            with mock.patch.object(
                self.module, "VDSO_DEBUG_CONTROLS", tuple(controls)
            ):
                control = self.module.inspect_vdso_debug_control(root)
                self.assertTrue(control["verified"])
                with self.module.apply_vdso_debug_control(root, control) as runtime:
                    for spec in controls:
                        self.assertIn(
                            spec["reproducible"],
                            (root / spec["path"]).read_text(encoding="ascii"),
                        )
            self.assertTrue(runtime["restored"])
            self.assertTrue(runtime["patched_content_unchanged"])
            for path, content in originals.items():
                self.assertEqual(path.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
