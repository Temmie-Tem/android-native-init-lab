"""Offline end-to-end binding and duplicate finalization regressions for y2q."""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
EXP = ROOT / "workspace/private/analysis/s20plus-y2q-mainline-list-20261127"


@unittest.skipUnless((EXP / "qualification.json").is_file(), "requires retained S20+ qualification")
class MainlineList(unittest.TestCase):
    def setUp(self):
        import s20plus_g986n_mainline_list_f1 as profile
        self.m = profile
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.run = self.root / "run-1234567890123456789"
        self.e = Mock()
        self.stack.enter_context(patch.object(profile.owner, "engine", self.e, create=True))
        self.guard = self.root / "guard.json"
        self.stack.enter_context(patch.object(profile.owner, "GUARD", self.guard))

    def mock(self, obj, key, **kwargs):
        return self.stack.enter_context(patch.object(obj, key, **kwargs))

    def test_fresh_image_and_exact_rollback(self):
        p = self.m.pair()
        self.assertNotEqual(p["nonce"], self.m.base.pair()["nonce"])
        self.assertEqual(p["rollback"], self.m.base.pair()["rollback"])
        for role in ("candidate", "rollback"):
            item = p[role]["ap"]
            self.assertEqual(hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest(), item["sha256"])
        self.assertEqual(self.m.calibrated_identity()["boot_id_sha256"],
                         json.loads((self.m.LAST / "final-health.json").read_bytes())["health"]["boot_id_sha256"])

    def test_runtime_bindings(self):
        child = """import s20plus_g986n_mainline_list_f1 as m
m.bind()
b,o,s=m.base,m.owner,m.stage
assert s._configure_runtime.__code__.co_filename==str(m.SCRIPT)
assert o.TEST_SOURCE==m.TEST and o.RUN_ROOT==b.RUN_ROOT==o.ACTIVATION.parent
assert o.read_pair()==m.pair() and b.execute is m.execute and b.restore is m.restore
assert o.observe_candidate is s.observe and o.checked_terminal is s.publish and s.make_intent is b.scan_intent
scope=o.effect_profile()
assert scope['sites']==['prebranch','primary_entry'] and scope['candidate_host_commands']==0
assert scope['physical_download_only_after_candidate'] and not scope['candidate_and_rollback_replay']
assert scope['approval_seconds']==900 and scope['scan_deadline_seconds']==120
assert scope['candidate_attempt_maximum']==scope['rollback_attempt_maximum']==1
assert o.review_identity()['pair_sha256']==m.PAIR_SHA
"""
        subprocess.run([sys.executable, "-B", "-c", child], cwd=SCRIPTS, check=True, timeout=30)

    def test_input_variants_and_separate_counters(self):
        m = self.m
        for values, state in [("0,0,0", "no_record"), ("1,0,0", "prebranch_only"),
                              ("0,1,0", "primary_entry_only"), ("1,1,1", "paired"),
                              ("1,1,0", "ambiguous"), ("2,0,0", "ambiguous")]:
            with self.subTest(values=values):
                result = m.base.reader.parse(0, ("y2q_early_v2=512,"+values+"\n").encode(), b"",
                                             m.base.reader.EARLY_STAGES)
                self.assertEqual(result["state"], state)
        self.mock(m.base, "old_make_intent", return_value={})
        self.mock(m.base, "accepted", return_value=({"health":{"boot_id_sha256":"old"}}, "grant"))
        self.mock(m.base, "ticket_dir", return_value=self.root)
        self.mock(m.base, "get", return_value={"binding_sha256":"grant", "boot_sha256":"first"})
        with self.assertRaises(m.owner.Stop):
            m.base.scan_intent(self.run, "return", {"boot_id_sha256":"later"})

    def test_wrong_and_expired_token_before_acceptance(self):
        m = self.m
        self.mock(m.base, "subject", return_value=({"issued":5, "expires":905}, "a"*64))
        accept = self.mock(m.base, "put")
        for now, prefix in [(6, m.base.PREFIX), (905, m.PREFIX)]:
            with self.subTest(now=now), patch.object(m.time, "time", return_value=now):
                with self.assertRaises(m.owner.Stop):
                    m.execute(self.run, prefix+"a"*64)
        accept.assert_not_called()
        self.e.prepare.assert_not_called()

    def test_execute_preserves_inner_terminal(self):
        m = self.m
        raw = (m.LAST / "terminal.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "9a0354400077f81dff308c60ec60bb027b9f1db583d31828d48b34cb9bfc63a4")
        terminal = json.loads(raw)
        self.mock(m.base, "subject", return_value=({"issued":1, "expires":901, "health":{}}, "key"))
        self.mock(m.time, "time", return_value=5)
        self.mock(m.base, "ticket_dir", return_value=self.root)
        self.mock(m.base, "put")
        self.mock(m.base, "accepted")
        self.mock(m.base, "source_fields", return_value={})
        runtime = self.mock(m.owner, "runtime", create=True)
        runtime._read_prepared_for_output.return_value = {"binding":{"expires_unix":900, "preflight":{}},
                                                         "approval_token":"inner"}
        saved = self.mock(m, "archived_terminal", return_value=terminal)
        recover = self.mock(m, "restore")
        self.e.execute.return_value = terminal
        self.assertEqual(m.execute(self.run, m.PREFIX+"key"), terminal)
        saved.assert_called_once_with(self.run)
        recover.assert_not_called()
        self.e.finalize_resident.assert_not_called()
        self.e.execute.return_value = {"status":"awaiting return"}
        self.assertIs(m.execute(self.run, m.PREFIX+"key"), recover.return_value)
        recover.assert_called_once_with(self.run)
        with self.assertRaises(m.owner.Stop):
            m.finish_step(self.run, {**terminal, "experiment_pass":False})
        self.run.mkdir()
        (self.run / "terminal.json").touch()
        with self.assertRaises(m.owner.Stop):
            m.finish_step(self.run, {})

    def test_recover_closed_or_cut_guard(self):
        m = self.m
        self.run.mkdir()
        (self.run / "terminal.json").touch()
        self.mock(m.base, "accepted")
        saved = self.mock(m, "archived_terminal", return_value={"verdict":"saved"})
        pending = self.mock(m, "recover_pending")
        self.assertEqual(m.restore(self.run), saved.return_value)
        self.e.finalize_resident.assert_not_called()
        self.guard.touch()
        self.e.guard_value.return_value = {"run_dir":str(self.run)}
        guard = self.mock(m.owner, "strict_private", return_value={"run_dir":"other"})
        with self.assertRaises(m.owner.Stop):
            m.restore(self.run)
        self.e.finalize_resident.assert_not_called()
        guard.return_value = self.e.guard_value.return_value
        self.assertIs(m.restore(self.run), self.e.finalize_resident.return_value)
        self.e.finalize_resident.assert_called_once_with(self.run)
        pending.assert_not_called()
        self.e.resume_run.assert_not_called()

    def test_cut_resume_must_publish_observation_before_recovery(self):
        m = self.m
        self.run.mkdir()
        (self.run / "candidate-claim-intent.json").touch()
        self.mock(m.base, "accepted")
        pending = self.mock(m, "recover_pending")
        self.e.resume_run.return_value = {}
        with self.assertRaises(m.owner.Stop):
            m.restore(self.run)
        pending.assert_not_called()
        def resume(run):
            (run / "candidate-observation.json").touch()
            return {}
        self.e.resume_run.side_effect = resume
        self.assertIs(m.restore(self.run), pending.return_value)
        pending.assert_called_once_with(self.run)
        self.e.execute.assert_not_called()


    def test_rederive_real_archive_without_usb_or_shared_guard(self):
        # Read the earlier admission under its retained historical identity.
        # The test namespace mounts each modified copy at its recorded path.
        b = self.m.base
        run = b.RUN_ROOT / "run-1795640333141198698"
        terminal = (run / "terminal.json").read_bytes()
        self.assertEqual(hashlib.sha256(terminal).hexdigest(),
                         "abea672783a967eda0fbc18a686eab7800d7efcce40d330ccd867527a72fbc8f")
        self.assertEqual(hashlib.sha256((b.RUN_ROOT / "activation.json").read_bytes()).hexdigest(),
                         "4a2af242ca2944e35b3387aff0a2a0a87863688a3fc058c7d45263da04f15feb")
        child = """import s20plus_g986n_mainline_list_f1 as m
b=m.base
b.bind()
b.cal.runtime()
b.OWNER.enter_runtime()
run=b.RUN_ROOT/'run-1795640333141198698'
saved=b.OWNER.strict_private(b.RUN_ROOT/'activation.json')['identity']
b.review=lambda:saved
m.PROFILE,m.CANDIDATE=b.PROFILE,b.CANDIDATE
assert m.archived_terminal(run)==b.OWNER.strict_private(run/'terminal.json',compact=True)
"""
        view = b.view.command(observe=False)
        view.insert(1, "--unshare-net")
        view[-1] = child
        for missing in (None, "saved-resume", "physical-rollback-arrival.json", "physical-confirmation-intent.json",
                        "candidate-claim-intent.json", "physical-observation-intent.json"):
            with self.subTest(missing=missing):
                cmd = view.copy()
                if missing:
                    copy = self.root / missing.removesuffix(".json")
                    shutil.copytree(run, copy)
                    if missing == "saved-resume":
                        def update(name, obj):
                            path = copy / (name+".json")
                            path.unlink(missing_ok=True)
                            path.write_text(json.dumps(obj, sort_keys=True, separators=(",", ":"))+"\n")
                            path.chmod(0o400)
                        def read(name):
                            return json.loads((copy / (name+".json")).read_bytes())
                        arm = read("physical-rollback-intent")
                        resume = dict(read("physical-observation-intent"),
                                      schema="s20plus_g986n_b0_physical_resume_observation_intent_v1",
                                      mode="one-current-read-after-reporting-cut", expires_unix=arm["expires_unix"])
                        update("physical-resume-observation-intent", resume)
                        update("physical-rollback-arrival", dict(read("physical-rollback-arrival"),
                                                               branch="reporting-cut-current-arrival"))
                        for path in copy.glob("mainline-return-*"):
                            path.unlink()
                        update("mainline-return-evidence", dict(phase="return", state="observation_gap",
                               binding_sha256=arm["binding_sha256"],
                               final_health_sha256=hashlib.sha256((copy/"final-health.json").read_bytes()).hexdigest()))
                    else:
                        (copy / missing).unlink()
                    i = cmd.index("--chdir")
                    cmd[i:i] = ["--ro-bind", str(copy), str(run)]
                result = subprocess.run(cmd, capture_output=True, env=b.view.clean_environment(), timeout=30)
                if missing and missing != "saved-resume":
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(missing.encode(), result.stderr)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
