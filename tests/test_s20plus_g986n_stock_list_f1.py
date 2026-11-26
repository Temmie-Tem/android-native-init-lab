"""Host checks for the list-bearing S20+ stock handoff and one-grant profile."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
HERE = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0"
PAIR = ROOT / "workspace/private/analysis/s20plus-y2q-stock-list-20261127/packaged/pair.json"


class Builder(unittest.TestCase):
    def test_qualified_guard_and_fixed_build_inputs(self):
        guard = (HERE / "mainline-handoff/guard.c").read_bytes()
        builder = (HERE / "stock-direct/build_list_control.py").read_text()
        self.assertIn(hashlib.sha256(guard).hexdigest(), builder)
        self.assertIn('TAG = "codex,y2q-stock-list-v1"', builder)
        self.assertIn("base.package(args.candidate, args.packaged)", builder)


@unittest.skipUnless(PAIR.is_file(), "requires retained private S20+ qualification")
class ListProfile(unittest.TestCase):
    def setUp(self):
        import s20plus_g986n_stock_list_f1 as profile
        self.m = profile

    def test_selected_healthy_return_pair_and_fresh_marker(self):
        m = self.m
        pair = m.pair()
        old = m.direct.pair()
        self.assertEqual(pair["rollback"], old["rollback"])
        self.assertNotEqual(pair["nonce"], old["nonce"])
        self.assertNotEqual(pair["candidate"]["ap"]["sha256"], old["candidate"]["ap"]["sha256"])
        self.assertEqual(m.calibrated_identity()["boot_id_sha256"],
                         json.loads((m.LAST / "final-health.json").read_bytes())["health"]["boot_id_sha256"])
        for item in ("candidate", "rollback"):
            ap = pair[item]["ap"]
            self.assertEqual(hashlib.sha256(Path(ap["path"]).read_bytes()).hexdigest(), ap["sha256"])

    def test_wrong_or_expired_token_rejected_before_acceptance(self):
        m = self.m
        issue = {"issued": 100, "expires": 1000}
        code = "a"*64
        for now, token in [(200, m.direct.PREFIX + code), (1000, m.PREFIX + code)]:
            with self.subTest(now=now), patch.object(m.base, "subject", return_value=(issue, code)), \
                 patch.object(m.base, "PREFIX", m.PREFIX), patch.object(m.base.time, "time", return_value=now), \
                 patch.object(m.base, "put") as accept:
                with self.assertRaises(m.base.OWNER.Stop):
                    m.base.execute(m.LAST, token)
                accept.assert_not_called()

    def test_bound_entrypoint_in_fresh_process(self):
        # The retained byte-bound owner configures the actual callbacks in the child.
        cmd = """import s20plus_g986n_stock_list_f1 as m
m.bind()
s,b=m.direct,m.base
assert b.stage._configure_runtime.__code__.co_filename==str(m.SCRIPT)
assert b.OWNER.TEST_SOURCE==m.TEST and b.OWNER.RUN_ROOT.name==m.PROFILE
assert b.OWNER.ACTIVATION.parent==b.RUN_ROOT and b.READER==b.reader.FILTER.with_name('return_stage.py')
assert b.OWNER.read_pair()==m.pair()
v=b.OWNER.effect_profile()
assert v['stock_source']==m.calibrated_identity() and v['tag']==m.PROP
assert v['approval_seconds']==900 and v['candidate_attempt_maximum']==v['rollback_attempt_maximum']==1
assert v['physical_fallback'] and v['authenticated_adb_rollback'] and not v['candidate_and_rollback_replay']
cmd=s.command('candidate-tag',{'boot_id_sha256':'a'*64})
assert m.PROP in cmd and 'codex,y2q-stock-direct-v1' not in cmd
assert b.OWNER.checked_terminal is s.publish and b.OWNER.observe_candidate is s.observe
assert b.restore is s.restore and s.old_restore is not s.restore
assert b.OWNER.review_identity()['pair_sha256']==m.PAIR_SHA
"""
        subprocess.run([sys.executable,"-B","-c",cmd],cwd=SCRIPTS,check=True,timeout=30)


if __name__ == "__main__":
    unittest.main()
