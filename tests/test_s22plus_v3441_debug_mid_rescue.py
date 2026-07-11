import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "build_s22plus_v3441_debug_mid_rescue.py"
)
SOURCE = Path(
    "workspace/public/src/native-init/s22plus_init_raw_debug_mid_rescue_v3441.S"
)
MANIFEST = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "v3441_debug_mid_rescue_v0_1/manifest.json"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("build_s22plus_v3441", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class V3441DebugMidRescueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_source_has_one_reboot_syscall_and_mid_argument(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('.asciz "debug0x494d"', text)
        self.assertEqual(text.count("svc     #0"), 1)
        self.assertIn("mov     x8, #142", text)
        self.assertNotIn('.asciz "download"', text)

    def test_compiled_init_has_exact_first_action_shape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "init"
            info = self.module.compile_raw_init(SOURCE, output, root)
            disassembly = info["objdump"]
            instructions = [
                line.strip()
                for line in disassembly.splitlines()
                if line.strip().startswith("4000")
            ]
            self.assertTrue(any("mov" in line and "x8" in line and "#0x8e" in line for line in instructions))
            self.assertEqual(sum("svc" in line for line in instructions), 1)
            self.assertTrue(any("wfe" in line for line in instructions))
            binary = output.read_bytes()
            self.assertIn(b"debug0x494d\0", binary)
            self.assertNotIn(b"download\0", binary)

    def test_manifest_is_boot_only_and_live_inert(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        safety = data["safety"]
        self.assertTrue(safety["boot_only"])
        self.assertFalse(safety["live_flash_authorized"])
        self.assertEqual(safety["intended_syscalls"], ["reboot"])
        self.assertEqual(safety["intended_syscall_count"], 1)
        self.assertEqual(safety["reboot_request"], "debug0x494d")
        self.assertFalse(safety["block_write"])
        self.assertFalse(safety["marker_write"])
        self.assertEqual(data["tar_members"], ["boot.img.lz4"])

    def test_manifest_pins_known_kernel_and_magisk_base(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(
            data["hashes"]["base_boot"],
            "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e",
        )
        self.assertEqual(
            data["hashes"]["kernel"],
            "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff",
        )
        self.assertEqual(
            data["hashes"]["nochange_repack_boot"], data["hashes"]["base_boot"]
        )

    def test_ap_contains_only_boot_image(self):
        ap = MANIFEST.parent / "odin4/AP.tar.md5"
        result = subprocess.run(
            ["tar", "-tf", ap], check=True, text=True, capture_output=True
        )
        self.assertEqual(result.stdout.splitlines(), ["boot.img.lz4"])


if __name__ == "__main__":
    unittest.main()
