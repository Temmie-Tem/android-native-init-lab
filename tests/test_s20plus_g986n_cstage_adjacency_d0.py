"""Host-only tests of the adapted C-stage return frame reader."""

from contextlib import ExitStack
import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_cstage_adjacency_d0 as owner

m = owner.profile


class CStageAdjacency(unittest.TestCase):
    def test_retained_chain_and_real_reducer_shape(self):
        restored, script = m.closure()
        nonce = json.loads(owner.PAIR.read_bytes())["nonce"]
        frames = m.reader.frames(nonce)
        self.assertEqual(list(frames), ["fdt", "unflatten"])
        _, reducer = m.reducer()
        self.assertIn(shlex.quote(reducer.replace('"y2q_log_v1=', '"y2q_cstage_adj_v1=')), script)
        self.assertIn(frames["fdt"].hex(), script)
        self.assertIn(frames["unflatten"].hex(), script)
        self.assertNotIn("prebranch", script)
        self.assertIn(restored["boot_id_sha256"], script)
        self.assertEqual(script.count("same_boot || exit 4"), 2)
        identity = m.subject(script)
        self.assertEqual(identity["owner"], m.sha(owner.SCRIPT.read_bytes()))
        for path, digest in ((owner.SOURCE, owner.SOURCE_SHA), (owner.READER, owner.READER_SHA)):
            self.assertEqual(identity["helpers"][str(path.relative_to(ROOT))], digest)
        self.assertEqual(identity["script"], m.sha(script.encode()))

    def test_exact_fdt_to_unflatten_adjacency(self):
        nonce = "ab" * 16
        frames = m.reader.frames(nonce)
        first, second = frames["fdt"], frames["unflatten"]
        _, script = m.reducer()
        script = script.replace('"y2q_log_v1=', '"y2q_cstage_adj_v1=')
        for payload, pairs in (
            ((b"!" * 15 + first + second) * 4, 4),
            (first * 4 + second * 4, 1),
            (first * 4 + b"!" + second * 4, 0),
            ((second + b"!" + first + b"!") * 4, 0),
        ):
            with self.subTest(pairs=pairs):
                od = subprocess.run(["od", "-An", "-v", "-tx1"], input=payload,
                                    capture_output=True, check=True, timeout=5)
                result = subprocess.run(["awk", "-v", f"expected={len(payload)}", "-v", f"first={first.hex()}",
                                         "-v", f"second={second.hex()}", script],
                                        input=od.stdout, capture_output=True, check=True, timeout=5)
                self.assertEqual(m.parse(result.returncode, result.stdout, result.stderr),
                                 dict(state="complete", size=len(payload), fdt_count=4,
                                      unflatten_count=4, adjacent_pair_count=pairs))
        with self.assertRaises(ValueError):
            m.parse(0, b"y2q_early_adj_v1=2097136,4,4,4\n", b"")

    def test_bound_first_boot_and_capture_failure(self):
        expected, script = m.closure()
        identity = m.subject(script)
        same = ("selected", "same-port", {"boot_id": "correct"})
        other = ("selected", "same-port", {"boot_id": "different"})
        for scenario in ("accepted", "wrong-boot", "wrong-counts"):
            with self.subTest(scenario=scenario), ExitStack() as stack:
                out = b"y2q_cstage_adj_v1=2097136,4,4,4\n"
                if scenario == "wrong-counts":
                    out = b"y2q_cstage_adj_v1=2097136,4,3,3\n"
                stack.enter_context(patch.object(m, "admit"))
                stack.enter_context(patch.object(m.health.base, "tool_receipt"))
                stack.enter_context(patch.object(m.health, "_validate_adb_receipt", return_value={"path": "adb"}))
                stack.enter_context(patch.object(m.support, "bracket", side_effect=[same, other if scenario == "wrong-boot" else same]))
                capture = stack.enter_context(patch.object(m.io, "root_capture", return_value=("completed", 0, out, b"")))
                evidence = Mock()
                if scenario == "accepted":
                    self.assertEqual(m.observe(identity, expected, script, evidence)["adjacent_pair_count"], 4)
                else:
                    with self.assertRaises(ValueError):
                        m.observe(identity, expected, script, evidence)
                capture.assert_called_once_with(["adb", "-s", "selected", "shell", "-T", "su", "-c", shlex.quote(script)], 120, 96)
                records = evidence.publish_json.call_args_list
                self.assertEqual([r.args[0] for r in records], ["intent.json", "root-receipt.json"] +
                                 (["result.json"] if scenario == "accepted" else []))
                self.assertNotIn(out.decode().strip(), json.dumps(records[1].args))


if __name__ == "__main__":
    unittest.main()
