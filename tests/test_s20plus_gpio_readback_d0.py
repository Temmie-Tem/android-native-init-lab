"""Check GPIO D0 bindings and the unchanged reader against retained qualified results."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_gpio_readback_d0 as m


class GPIOReadback(unittest.TestCase):
    @unittest.skipUnless(m.PAIR.exists(), "requires closed S20+ GPIO trial")
    def test_closed_boot_and_real_reader(self):
        restored, script, identity = m.inputs()
        self.assertEqual(restored, json.loads((m.RUN / "final-health.json").read_bytes())["health"])
        self.assertEqual(identity["shell"], m.prior.sha(script.encode()))
        q = m.EXP / "physical-preparation"
        for label, expected in json.loads((q / "stock-results.json").read_bytes()).items():
            out = (q / "runs" / label / "stdout.bin").read_bytes()
            self.assertEqual(m.reader.parse(0, out, b""), expected)
        with patch.object(m.session, "main") as entry, patch.multiple(
                m.session, inputs=None, classify=None, PARENT=None, LIMIT=None):
            m.main()
            entry.assert_called_once_with()
            self.assertIs(m.session.inputs, m.inputs)
            self.assertIs(m.session.classify, m.reader.parse)
            self.assertEqual((m.session.PARENT, m.session.LIMIT), (m.PARENT, 8288))

    def test_private_result_bound(self):
        values = "".join(f"{n:04x}" for n in range(32768, 33792))
        raw = f"GP2,61440,256,1024,0,33554431,33554431,1023,1,1,1,{values},{values}\n".encode()
        facts = m.reader.parse(0, raw, b"")
        result = dict(facts=facts, binding=dict.fromkeys(m.prior.IDENTITY, "f"*64), scope="current_boot_run_wide",
                      shell_sha256="f"*64, first_return_attributed=False)
        self.assertLessEqual(len(m.session.health._json_bytes(result)), m.session.RESULT_LIMIT)


if __name__ == "__main__":
    unittest.main()
