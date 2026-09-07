"""Shared return-state names must not weaken candidate namespace isolation."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import device_action_f1_live_v2 as live

class ReturnStateNamespaceTests(unittest.TestCase):
    def validate(self,prefix,state):
        prepared=SimpleNamespace(bundle=SimpleNamespace(manifest={'observation':{}}))
        with mock.patch.object(live,'_userspace_overlay_contract_id',return_value='fixture'),mock.patch.object(live,'_host_first_prefix',return_value=prefix):
            live._validate_candidate_observer_state(prepared,state)

    def test_only_exact_shared_names_are_accepted_for_return_owner(self):
        for name in ('p363_control_intent','p363_return_window','p363_return_evidence_unavailable'):
            self.validate('p364',{name:None})
            self.validate('p363',{name:None})
            with self.assertRaisesRegex(live.F1LiveError,'foreign candidate namespace'):
                self.validate('p361',{name:None})

    def test_foreign_names_and_lookalikes_remain_rejected(self):
        for name in ('p363_stock','p363_closure_snapshot','p363_control_intent_extra','p363_return_window_extra','p363_return_evidence_unavailable_extra','p345_stock','p361_stock'):
            with self.subTest(name=name),self.assertRaisesRegex(live.F1LiveError,'foreign candidate namespace'):
                self.validate('p364',{name:None})

    def test_own_names_remain_local(self):
        self.validate('p364',{'p364_stock':None})
        with self.assertRaisesRegex(live.F1LiveError,'foreign candidate namespace'):
            self.validate('p363',{'p364_stock':None})

    def test_accepted_shared_name_still_reaches_durable_validator(self):
        prepared=SimpleNamespace(bundle=SimpleNamespace(manifest={'observation':{'candidate_observer':{}}}))
        with mock.patch.object(live,'_userspace_overlay_contract_id',return_value='fixture'),mock.patch.object(live,'_host_first_prefix',return_value='p364'),mock.patch.object(live,'_reopen_candidate_observation',side_effect=live.F1LiveError('durable receipt rejected')) as reopen:
            with self.assertRaisesRegex(live.F1LiveError,'durable receipt rejected'):
                live._validate_candidate_observer_state(prepared,{'p363_control_intent':None})
            reopen.assert_called_once_with(prepared)

if __name__=='__main__':unittest.main()
