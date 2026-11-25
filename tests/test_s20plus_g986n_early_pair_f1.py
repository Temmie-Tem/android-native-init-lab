"""Offline checks for the integrated early-pair grant and recovery flow."""

import ast
from contextlib import ExitStack, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
# The reviewed runtime loads retained firmware qualification from private storage.
available = (
    ROOT
    / "workspace/private/analysis/s20plus-y2q-early-pair-20261126/retained-reader/return_stage.py"
).is_file()
if available:
    import s20plus_g986n_early_pair_f1 as m


class PublicContract(unittest.TestCase):
    def test_owner_literal_and_explicit_entrypoints(self):
        tree = ast.parse((SCRIPTS / "s20plus_g986n_early_pair_f1.py").read_bytes())
        names = {f.name for f in tree.body if isinstance(f, ast.FunctionDef)}
        self.assertTrue(
            {"prepare", "execute", "restore", "accepted", "exclusive", "scan_intent"}
            <= names
        )


@unittest.skipUnless(available, "retained private qualification required")
class EarlyPair(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.run = self.root / "run-1234567890123456789"
        self.ticket = self.root / "ticket-1234567890123456789"
        self.ticket.mkdir()
        self.patch(m, "RUN_ROOT", self.root)
        self.e = self.patch(m.OWNER, "engine", Mock(), create=True)
        self.c = self.patch(m.cal, "engine", Mock(), create=True)
        self.c.durable_json.side_effect = lambda path, v: self._write(path, v)
        self.c.read_json.side_effect = lambda path, label: json.loads(path.read_bytes())
        self.e.read_json.side_effect = self.c.read_json.side_effect
        self.e.digest.side_effect = lambda v: hashlib.sha256(
            json.dumps(v, sort_keys=True).encode()
        ).hexdigest()
        self.patch(m.stage, "fresh_return_run", None)
        self.clock = self.patch(m.time, "time", Mock(return_value=100))
        self.patch(m, "accepted", Mock(return_value=({}, "grant")))
        self.output = self.stack.enter_context(redirect_stdout(io.StringIO()))

    def patch(self, module, name, value, **kw):
        return self.stack.enter_context(patch.object(module, name, value, **kw))

    def _write(self, path, data):
        with path.open("x") as f:
            json.dump(data, f)

    def arm(self, branch="attended-entry-required"):
        self.run.mkdir()
        for name in ("candidate-intent", "candidate-observation"):
            self._write(self.run / (name + ".json"), {})
        data = dict(
            branch=branch,
            baseline={"endpoint_count": 0},
            expires_unix=480,
            confirmation_token="bound-machine-key",
        )
        self._write(self.run / "physical-rollback-intent.json", data)
        return data

    def test_ap_and_reader_bound(self):
        p = m.pair()
        self.assertEqual(p["candidate"]["ap"]["sha256"], m.CANDIDATE)
        self.assertEqual(p["rollback"]["ap"]["sha256"], m.ORIGINAL)
        self.assertEqual(m.reader.EARLY_STAGES, ("prebranch", "primary_entry"))

    def test_valid_arm_cues_once(self):
        self.arm()
        m.restore(self.run)
        self.assertEqual(
            json.loads(self.output.getvalue())["status"], "ENTER_PHYSICAL_DOWNLOAD_NOW"
        )
        self.e.confirm_physical_rollback.assert_called_once_with(
            self.run, "bound-machine-key"
        )
        self.assertEqual(m.stage.fresh_return_run, self.run)
        self._write(self.run / "physical-confirmation-intent.json", {})
        before = self.output.getvalue()
        m.restore(self.run)
        self.assertEqual(self.output.getvalue(), before)
        self.assertIsNone(m.stage.fresh_return_run)

    def test_expired_arrival_no_new_entry(self):
        self.arm()
        self.clock.return_value = 500
        with self.assertRaises(m.OWNER.Stop):
            m.restore(self.run)
        self.e.confirm_physical_rollback.assert_not_called()

    def test_already_download_no_cue(self):
        self.arm("already-download")
        with self.assertRaises(m.OWNER.Stop):
            m.restore(self.run)
        self.assertFalse(self.output.getvalue())
        self.e.confirm_physical_rollback.assert_not_called()

    def test_uncertain_transfer_never_replays(self):
        self.arm()
        self._write(self.run / "rollback-intent.json", {})
        m.restore(self.run)
        self.e.finalize_resident.assert_called_once_with(self.run)
        self.e.confirm_physical_rollback.assert_not_called()
        self.e.execute.assert_not_called()
        self.assertIsNone(m.stage.fresh_return_run)

    def test_old_or_wrong_approval_cannot_enter_download(self):
        self.patch(
            m, "subject", lambda run: ({"issued": 50, "expires": 150}, "expected")
        )
        with self.assertRaises(m.OWNER.Stop):
            m.execute(self.run, m.PREFIX + "other")
        self.clock.return_value = 150
        with self.assertRaises(m.OWNER.Stop):
            m.execute(self.run, m.PREFIX + "expected")
        self.e.prepare.assert_not_called()
        self.assertFalse((self.ticket / "accepted.json").exists())

    def test_admission_lock_excludes_second_owner(self):
        with m.exclusive(self.run):
            with self.assertRaises(BlockingIOError):
                with m.exclusive(self.run):
                    self.fail("second owner")

    def test_sibling_cut_record_rejected(self):
        self.arm()
        self._write(self.ticket / "physical-cue.json", {"run": "wrong"})
        with self.assertRaises(m.OWNER.Stop):
            m.restore(self.run)
        self.e.confirm_physical_rollback.assert_not_called()
