"""Compare the device AWK against the independent host decoder, without USB."""
from contextlib import ExitStack
import json
import tempfile
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
from test_s20plus_deferred_presence_h0 import NONCE, h, window
import s20plus_g986n_presence_readback_d0 as m


class PresenceFilter(unittest.TestCase):
    def compare(self, snapshot, nonce=NONCE):
        binary = m.prior.PRIVATE / "analysis/s20plus-y2q-fdt-d0-20261123/busybox-host"
        if not binary.is_file() or not m.prior.QUAL.exists():
            self.skipTest("requires retained BusyBox and S20+ name dictionary")
        raw = subprocess.check_output(["od", "-An", "-v", "-tx1"], input=snapshot)
        command = [binary, "awk", "-v", f"expected={len(snapshot)}", "-v", "key="+nonce,
                   "-v", "legacy="+h.r4.legacy.frames(nonce)["basic_enter"].hex(), "-f", m.FILTER]
        cap = subprocess.run(command, input=raw, capture_output=True)
        got = m.classify(cap.returncode, cap.stdout, cap.stderr)
        try:
            expected = h.presence(snapshot, nonce)
        except ValueError:
            self.assertEqual(got, {"state": "invalid_snapshot"})
            return
        self.assertEqual(got["state"], "complete")
        self.assertEqual(got["size"], len(snapshot))
        for key in ("valid_windows", "unauthenticated_slots", "before_call_device_ids", "return_device_ids", "first_flush_return"):
            self.assertEqual(got[key], expected[key])

    def test_windows(self):
        worker = window([(2,1,0xcf89fca4,0,1),(3,2,0x12345678,0x12345678,2)])
        pid = window([(0,1,159,159,8)], epoch=b"x"*16)
        for padding in (0,3856,4089,4096):
            for slots in ((worker,pid),(pid,worker),(worker,window()),(pid,window()),(window(),window())):
                self.compare(bytes(padding)+b"".join(slots*4)+window())
        for bad in (worker+pid[:120], worker[:80]+pid, worker+b"Y2QSURV1",worker+window([(2,2,1,0,1)])):
            self.compare(bad)
        self.compare(pid[:160]+worker[160:])

    def test_qemu_snapshots(self):
        if not m.prior.PAIR.is_file():
            self.skipTest("requires retained QEMU snapshots")
        nonce = json.loads(m.prior.PAIR.read_bytes())["nonce"]
        for label in ("epoch-first","epoch-second","run-first","run-second"):
            self.compare((m.prior.EXP/"independent-h0/runs"/label/"fixture.bin").read_bytes(), nonce)

    def test_observe_dispatch_and_no_replay(self):
        for mismatch in ("before", "after", None):
            with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
                def mock(obj, name, **kwargs):
                    return stack.enter_context(patch.object(obj, name, **kwargs))
                dest = Path(tmp)
                identity = {"shell": m.prior.sha(b"fixed")}
                expected = dict.fromkeys(m.prior.IDENTITY, "1"*64)
                args = (expected, "fixed", identity)
                row = ("fixture-serial", "fixture-port", {})
                mock(m, "PARENT", new=dest)
                mock(m.stock, "admit")
                mock(m, "inputs", return_value=args)
                mock(m.health.base, "tool_receipt")
                mock(m.health, "_validate_adb_receipt", return_value={"path": "/fixture"})
                mock(m.stock, "bracket", side_effect=([ValueError("boot changed")] if mismatch=="before"
                                                       else [row, None if mismatch else row]))
                mock(m.health, "_ALLOWED_EVIDENCE_NAMES", new=m.health._ALLOWED_EVIDENCE_NAMES | {"intent.json"})
                mock(m.health, "_EVIDENCE_MAXIMUMS", new={**m.health._EVIDENCE_MAXIMUMS, "intent.json": 16384})
                def acquire(command, seconds, limit):
                    self.assertTrue((dest/"observation/intent.json").is_file())
                    self.assertEqual((seconds,limit),(120,4656))
                    self.assertEqual(command, ["/fixture","-s","fixture-serial","shell","-T","su","-c","fixed"])
                    return "completed",0,b"P1,invalid\n",b""
                capture = mock(m.io,"root_capture",side_effect=acquire)
                if mismatch:
                    with self.assertRaises(ValueError):
                        m.observe(*args)
                else:
                    m.observe(*args)
                self.assertEqual(capture.call_count, int(mismatch!="before"))
                self.assertEqual((dest/"observation/result.json").exists(), mismatch is None)
                if mismatch!="before":
                    with self.assertRaisesRegex(ValueError,"consumed"):
                        m.observe(*args)
                    capture.assert_called_once()

    def test_largest_result_fits_private_receipt(self):
        if not m.prior.QUAL.exists():
            self.skipTest("requires pinned S20+ dictionary")
        names = json.loads(m.prior.checked(m.prior.QUAL, m.prior.PINS[m.prior.QUAL]))["direct_soc_names"]
        ids = list(names)
        ids.extend(k for i in range(512) if (k := f"{i:08x}") not in names)
        raw = f"P1,2097136,256,0,1,{''.join(ids[:256])},{''.join(ids[256:512])}\n".encode()
        facts = m.classify(0,raw,b"")
        envelope = dict(facts=facts, binding=dict.fromkeys(m.prior.IDENTITY,"a"*64), scope="current_boot_run_wide",
                        shell_sha256="f"*64, first_return_attributed=False)
        self.assertLessEqual(len(m.health._json_bytes(envelope)),m.RESULT_LIMIT)

    def test_reject_bad_replies(self):
        for raw in (b"P1,240,0,0,1,,\n", b"P1,240,1,0,0,abcdef,\n", b"P1,240,1,5,0,,\n", b"P1,240,1,4,1,abcdef01,\n"):
            with self.assertRaises(ValueError):
                m.classify(0,raw,b"")

if __name__=="__main__":
    unittest.main()
