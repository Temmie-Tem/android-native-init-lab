"""Exercise the actual g0q command code with a deterministic register model."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workspace/public/src/mainline/s22plus_ufs_link_h0"


class ColdHciTest(unittest.TestCase):
    def test_cold_link_and_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            for header in ("linux/types.h", "linux/bitfield.h", "linux/delay.h", "linux/io.h",
                           "linux/ktime.h", "ufs/ufshci.h", "ufs/unipro.h"):
                dest = output / header
                dest.parent.mkdir(exist_ok=True)
                dest.touch()
            (output/"linux/errno.h").write_text("#include_next <linux/errno.h>\n")
            exe = output/"cold-hci"
            subprocess.run(["cc", "-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-I", output, "-I", SOURCE, ROOT/"tests/s22plus_ml030_hci_fixture.c",
                            "-o", exe], check=True)
            for case in ("positive", "active", "device-before", "old-completion",
                         "transfer-pending", "task-running", "no-calibration", "expired-at-link",
                         "timer-disagreement", "no-device", "bad-code", "link-lost", "no-uccs"):
                with self.subTest(case=case):
                    subprocess.run([exe, case], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
