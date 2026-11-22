"""Host-only regressions for candidate-specific first-return stage evidence."""

import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0/mainline-handoff"


def local(name):
    spec = importlib.util.spec_from_file_location(name, MODULE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


record = local("return_stage")


class StageReturn(unittest.TestCase):
    nonce = "ab" * 16
    boot = "a1" * 32

    def probe(self, raw, expected=None, alter=None):
        frames = record.frames(self.nonce)
        hexdump = subprocess.check_output(["od", "-An", "-v", "-tx1"], input=raw)
        if alter:
            hexdump = alter(hexdump)
        run = subprocess.run(
            [
                "awk",
                "-v",
                f"expected={len(raw) if expected is None else expected}",
                "-v",
                "first=" + frames["fdt"].hex(),
                "-v",
                "second=" + frames["unflatten"].hex(),
                "-f",
                record.FILTER,
            ],
            input=hexdump,
            capture_output=True,
        )
        return record.parse(run.returncode, run.stdout, run.stderr)

    def test_stage_outcomes(self):
        a, b = record.frames(self.nonce).values()
        stale = record.frames("00" * 16)
        for pos in range(16):
            with self.subTest(offset=pos):
                self.assertEqual(self.probe(bytes(pos) + a + b)["state"], "paired")
        for raw, state in [
            (a, "fdt_only"),
            (b, "unflatten_only"),
            (a + a, "ambiguous"),
            (b + a, "ambiguous"),
            (a + b"x" + b, "ambiguous"),
            (b"\0" * 8 + a[8:], "no_record"),
            (b"", "no_record"),
            (stale["fdt"] + stale["unflatten"], "no_record"),
        ]:
            self.assertEqual(self.probe(raw)["state"], state)

    def test_complete_scan(self):
        f = record.frames(self.nonce)["fdt"]
        with self.assertRaises(ValueError):
            self.probe(f, expected=4096)
        with self.assertRaises(ValueError):
            self.probe(f, alter=lambda s: s + b" f fff\n")
        for rc, out, err in [
            (1, b"y2q_log_v1=128,1,0,0\n", b""),
            (0, b"y2q_log_v1=128,1,0,0\n", b"cut"),
            (0, b"y2q_log_v1=128,1,1,1\n", b""),
            (0, b"y2q_log_v1=0,0,0,1\n", b""),
        ]:
            with self.assertRaises(ValueError):
                record.parse(rc, out, err)

    def test_fixed_probe_binding(self):
        script = record.shell(self.nonce, self.boot)
        self.assertEqual(script.count(self.boot), 1)
        self.assertEqual(script.count("same_boot || exit 4"), 2)
        self.assertIn("set -o pipefail", script)
        self.assertIn("/proc/last_kmsg", script)
        self.assertIn(str(record.CAPACITY + 1), script)
        for frame in record.frames(self.nonce).values():
            self.assertEqual(len(frame), 128)
            self.assertIn(frame.hex(), script)
            self.assertNotIn(frame.decode(), script)
        with self.assertRaises(ValueError):
            record.shell("x" * 32, self.boot)
        with self.assertRaises(ValueError):
            record.shell(self.nonce, "bad boot")
        self.assertEqual(
            record.parse(0, b"y2q_log_missing\n", b""), {"state": "missing"}
        )
