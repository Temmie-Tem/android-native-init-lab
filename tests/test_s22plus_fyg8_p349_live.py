"""P349 raw replay and retained owner isolation, without device contact."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256
from test_s22plus_fyg8_p348_live import P348ReceiptFixture
import device_action_f1_live_v2 as live


class P349ReceiptFixture(P348ReceiptFixture):
    def __init__(self, run_dir):
        _ReceiptFixture.__init__(self,run_dir,variant='p349')

    def _receipt_value(self):
        value=super()._receipt_value()
        value[self.variant.proof_key]=value.pop('p349_readonly_research_shell_qualification')
        return value


class P349LiveTests(unittest.TestCase):
    def test_exact_owner_and_raw_reopening(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=P349ReceiptFixture(Path(directory)/'run')
            self.assertTrue(live._p349_bundle(fixture.prepared.bundle))
            self.assertFalse(live._p348_bundle(fixture.prepared.bundle))
            self.assertIs(live._exploration_owner(fixture.prepared.bundle),live.p349_shell_session)
            with mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,KEY_SHA256)):
                durable=live._reopen_candidate_observation(fixture.prepared)
            self.assertTrue(live._p349_proof_ok(durable))
            self.assertFalse(live._p348_proof_ok(durable))
            self.assertEqual(fixture.spec['read_only_child_required'],False)
            self.assertTrue(fixture.spec['ram_workspace_child_required'])

    def test_old_namespace_never_selects_new_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture=P348ReceiptFixture(Path(directory)/'run')
            self.assertFalse(live._p349_bundle(fixture.prepared.bundle))
            self.assertIs(live._exploration_owner(fixture.prepared.bundle),live.p348_shell_session)

if __name__=='__main__': unittest.main()
