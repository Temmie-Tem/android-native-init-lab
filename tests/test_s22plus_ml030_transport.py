"""Exercise the actual ML030 one-shot RSC writer with delayed posted writes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT/"workspace/public/src/mainline/s22plus_ufs_link_h0/transport"
CASES = ("success", "busy", "expired", "old-enable", "old-irq", "payload-expiry",
         "pretrigger-expiry", "posted-ctl", "posted-enable", "posted-addr",
         "posted-data", "posted-msgid")


def compile_fixture(out, compiler, flags, source="s22plus_ml030_rsc_fixture.c"):
    for name in ("linux/ktime.h", "linux/of_platform.h", "soc/qcom/g0q-ml030.h"):
        path = out/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    exe = out/Path(source).stem
    subprocess.run([compiler, "-std=gnu11", "-Wall", "-Wextra", "-Werror", "-O2",
                    *flags, "-I", out, "-I", SRC, ROOT/"tests"/source,
                    "-o", exe], check=True)
    return exe


class TransportTest(unittest.TestCase):
    def test_confirmed_usb_votes(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = compile_fixture(Path(temp), "cc", ["-Wno-sign-compare"], "s22plus_ml030_bcm_fixture.c")
            subprocess.run([exe], check=True, timeout=2)

    def test_resource_uniqueness_and_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = compile_fixture(Path(temp), "cc", [], "s22plus_ml030_cmd_db_fixture.c")
            subprocess.run([exe], check=True, timeout=2)

    def test_rsc_submission_and_slot_reuse(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = compile_fixture(Path(temp), "cc", [])
            for case in CASES:
                with self.subTest(case=case):
                    subprocess.run([exe, case], check=True, capture_output=True, timeout=2)


if __name__ == "__main__":
    unittest.main()
