import importlib.util
from pathlib import Path
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_boot_only_odin_prep.py"
SPEC = importlib.util.spec_from_file_location("s20_boot_only_prep", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class S20BootOnlyPrepTests(unittest.TestCase):
    def test_boot_ap_is_exactly_one_member_and_md5_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frame = root / "boot.img.lz4"
            frame.write_bytes(b"frame")
            output = root / "AP.tar.md5"
            result = MODULE.write_boot_ap(frame, output)
            self.assertEqual(result["members"], ["boot.img.lz4"])
            with tarfile.open(output, "r:") as archive:
                self.assertEqual([item.name for item in archive.getmembers()], ["boot.img.lz4"])

    def test_exact_inputs_and_live_exclusions_are_closed(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(MODULE.PATCHED_AP_SHA256, source)
        self.assertIn(MODULE.STOCK_BOOT_SHA256, source)
        self.assertIn(MODULE.ODIN4_SHA256, source)
        self.assertIn('"live_flash_authorized": False', source)
        for forbidden in ("adb ", "odin4 -", "fastboot", "/dev/block", "--reboot"):
            self.assertNotIn(forbidden, source.lower())


if __name__ == "__main__":
    unittest.main()
