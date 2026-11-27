"""Exercise the current-boot R4 acquisition with offline transport fixtures."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import ExitStack

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_deferred_readback_d0 as m


class R4Readback(unittest.TestCase):
    def exercise(self, changed):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            parent = Path(tmp)
            def stub(obj, name, **kw):
                return stack.enter_context(patch.object(obj, name, **kw))
            health = dict.fromkeys(m.IDENTITY, "0" * 64)
            subject = {"shell": m.sha(b"fixed")}
            stub(m, "PARENT", new=parent)
            stub(m.stock, "admit")
            before = ("fixture", "port", {})
            stub(m.stock, "bracket", side_effect=[before, None if changed else before])
            stub(m.health.base, "tool_receipt")
            stub(m.health, "_validate_adb_receipt", return_value={"path": "/fixture"})
            stub(m, "closure", return_value=(health, "fixed"))
            stub(m, "subject", return_value=subject)
            stub(m.health, "_ALLOWED_EVIDENCE_NAMES", new=m.health._ALLOWED_EVIDENCE_NAMES | {"intent.json"})
            stub(m.health, "_EVIDENCE_MAXIMUMS", new={**m.health._EVIDENCE_MAXIMUMS, "intent.json": 16384})
            capture = stub(m.io, "root_capture", return_value=("completed",0,b"R4,100,0,0,0,-,-\n",b""))
            if changed:
                with self.assertRaisesRegex(ValueError,"bracket"):
                    m.observe(subject,health,"fixed")
            else:
                m.observe(subject,health,"fixed")
            self.assertEqual((parent/"observation/result.json").exists(), not changed)
            with self.assertRaises(FileExistsError):
                m.observe(subject,health,"fixed")
            capture.assert_called_once()

    def test_current(self):
        self.exercise(False)

    def test_changed(self):
        self.exercise(True)

if __name__ == "__main__":
    unittest.main()
