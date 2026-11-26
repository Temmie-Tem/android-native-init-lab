"""Host-only reducer, retained evidence and same-boot guard checks."""

from contextlib import ExitStack
import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
import s20plus_g986n_mainline_adjacency_d0 as m


class AdjacencyTest(unittest.TestCase):
    def setUp(self):
        self.frames = m.reader.frames("ab" * 16, m.reader.EARLY_STAGES)
        self.pre = self.frames["prebranch"]
        self.primary = self.frames["primary_entry"]

    def reduce(self, contents, *, expected=None):
        if expected is None:
            expected = len(contents)
        od = subprocess.run(["od", "-An", "-v", "-tx1"], input=contents,
                            capture_output=True, check=True, timeout=15)
        _, script = m.reducer()
        return subprocess.run(["awk", "-v", f"expected={expected}", "-v", f"first={self.pre.hex()}",
                               "-v", f"second={self.primary.hex()}", script],
                              input=od.stdout, capture_output=True, timeout=20)

    def counts(self, payload):
        reduced = self.reduce(payload)
        self.assertEqual(reduced.returncode, 0)
        self.assertEqual(reduced.stderr, b"")
        facts = m.parse(0, reduced.stdout.replace(b"y2q_log_v1=", b"y2q_early_adj_v1="), b"")
        self.assertEqual(facts["size"], len(payload))
        return tuple(facts[key] for key in ("prebranch_count", "primary_entry_count", "adjacent_pair_count"))

    def test_frame_boundaries_and_exact_order(self):
        for payload, expected in (
            (b"", (0, 0, 0)),
            (self.pre, (1, 0, 0)),
            (self.primary, (0, 1, 0)),
            (self.primary + self.pre, (1, 1, 0)),
            (self.pre + b"!" + self.primary, (1, 1, 0)),
            (b"!" * 15 + self.pre + self.primary, (1, 1, 1)),
            (b"!" * 255 + self.pre + self.primary, (1, 1, 1)),
            (self.pre + self.primary[:-1], (1, 0, 0)),
            (self.primary + b"!" * 128 + self.pre, (1, 1, 0)),
            (self.pre + b"!" * 256 + self.primary, (1, 1, 0)),
        ):
            with self.subTest(size=len(payload), expected=expected):
                self.assertEqual(self.counts(payload), expected)

    def test_four_hits_and_multiple_pairs(self):
        for payload, pairs in (
            ((b"!" * 17 + self.pre + self.primary) * 4, 4),
            (self.pre * 4 + self.primary * 4, 1),
            (self.pre * 4 + b"!" + self.primary * 4, 0),
            (self.pre * 2 + self.primary * 2 + b"!" + (self.pre + self.primary) * 2, 3),
        ):
            with self.subTest(pairs=pairs):
                self.assertEqual(self.counts(payload), (4, 4, pairs))

    def test_expected_length_oversize_and_inconsistent_outputs(self):
        for reduced in (self.reduce(self.pre, expected=129), self.reduce(b"!" * (m.CAPACITY + 1))):
            self.assertEqual(reduced.returncode, 3)
            self.assertEqual(reduced.stdout, b"")
        self.assertEqual(m.parse(0, b"y2q_log_missing\n", b""), {"state": "missing"})
        self.assertEqual(m.parse(0, b"y2q_log_unreadable\n", b""), {"state": "unreadable"})
        for response in (b"y2q_early_adj_v1=256,1,1,2\n", b"y2q_early_adj_v1=255,1,1,1\n",
                         b"y2q_early_adj_v1=2097137,0,0,0\n", b"y2q_early_adj_v1=256,1,1,1\nraw"):
            with self.assertRaises(ValueError):
                m.parse(0, response, b"")

    def test_exact_retained_chain_and_script(self):
        expected, script = m.closure()
        self.assertIn(expected["boot_id_sha256"], script)
        self.assertEqual(script.count("same_boot || exit 4"), 2)
        self.assertIn("-N 2097137", script)
        self.assertIn("first_slot[(at-128) % 256] == at-127", script)
        self.assertNotIn("print at", script)
        self.assertEqual(m.subject(script)["script"], m.sha(script.encode()))

    def test_transcript_publication_and_boot_change(self):
        expected, script = m.closure()
        identity = m.subject(script)
        original = ("selected", "first-port", {"boot_id": "first-boot"})
        changed = ("selected", "first-port", {"boot_id": "another-boot"})
        for mode in ("ok", "pre-boot", "post-boot", "counts", "overflow"):
            with self.subTest(mode=mode), ExitStack() as st:
                st.enter_context(patch.object(m, "admit"))
                st.enter_context(patch.object(m.health.base, "tool_receipt"))
                st.enter_context(patch.object(m.health, "_validate_adb_receipt", return_value={"path": "adb"}))
                evidence = Mock()
                def dispatch(argv, deadline, maximum):
                    self.assertEqual([call.args[0] for call in evidence.publish_json.call_args_list], ["intent.json"])
                    self.assertEqual(argv[:-1], ["adb", "-s", "selected", "shell", "-T", "su", "-c"])
                    self.assertEqual(shlex.split(argv[-1]), [script])
                    self.assertEqual((deadline, maximum), (120, 96))
                    data = b"y2q_early_adj_v1=2097136,4,4,3\n" if mode != "counts" else b"y2q_early_adj_v1=2097136,4,3,1\n"
                    return ("overflow" if mode == "overflow" else "completed", 0, data, b"")
                st.enter_context(patch.object(m.support, "bracket", side_effect=[
                    ValueError("first-return boot changed") if mode == "pre-boot" else original,
                    changed if mode == "post-boot" else original,
                ]))
                raw = st.enter_context(patch.object(m.io, "root_capture", side_effect=dispatch))
                if mode == "ok":
                    self.assertEqual(m.observe(identity, expected, script, evidence)["adjacent_pair_count"], 3)
                else:
                    with self.assertRaises(ValueError):
                        m.observe(identity, expected, script, evidence)
                names = [call.args[0] for call in evidence.publish_json.call_args_list]
                if mode == "pre-boot":
                    raw.assert_not_called()
                    self.assertEqual(names, [])
                else:
                    raw.assert_called_once()
                    self.assertEqual(names[:2], ["intent.json", "root-receipt.json"])
                    self.assertEqual(names[2:], ["result.json"] if mode == "ok" else [])
                    self.assertNotIn("y2q_early_adj_v1=", json.dumps(evidence.publish_json.call_args_list[1].args))


if __name__ == "__main__":
    unittest.main()
