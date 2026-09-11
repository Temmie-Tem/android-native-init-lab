"""Ordinary installation/A recovery with actual resident C and retained readers.

Images, USB/Odin and Android are explicit existing H0 fixtures. Actual AP bytes
are independently reopened by the candidate-static build, without a device.
"""
from contextlib import ExitStack,contextmanager
import json
from unittest import mock

import test_s22plus_fyg8_p384_lifecycle as ordinary
import test_s22plus_native_resident_adoption_backend_v1 as backend_test
import s22plus_resident_adoption_h0_support as support

live=ordinary.live


class Backend(ordinary.Backend):
    def __init__(self,prepared,harness,case='normal',fault=None):
        super().__init__(prepared,harness.binary,case,2100)
        self.harness,self.case,self.fault=harness,case,fault

    @contextmanager
    def candidate_observer_session(self,prepared):
        with self.harness.owned_session(self.case,self.fault,prepared=prepared) as (fixture,session):
            self.fixture=fixture
            yield session


class Lifecycle(backend_test.BackendTests):
    test_actual_factory_four_opens_closes_and_retained_owner_replay=None
    test_middle_failure_closes_only_the_current_owned_descriptor=None

    def prepared(self):
        factory=ordinary.generic.DeviceActionF1LiveV2Test();factory.module=live
        temporary,prepared=factory.prepared();self.addCleanup(temporary.cleanup)
        variant=live.typed_evidence.SHELL_VARIANTS['p386']
        prepared.bundle.manifest['manifest_id']='p386-resident-ordinary-owner-fixture'
        prepared.bundle.manifest['observation']=dict(timeout_sec=2100,acceptance=variant.adapter.acceptance_fixture(),
            candidate_observer=live.typed_evidence._shell_observer_spec('p386'),
            **{live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY:live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE})
        prepared.private_target['topology']=live.p324_typec_lane.SOURCE_TOPOLOGY
        prepared.prepared.update(p328_auth_key_identity=dict(size=32,sha256=backend_test.KEY_SHA256),
            approval_binding=dict(p328_auth_key_identity=dict(size=32,sha256=backend_test.KEY_SHA256)))
        prepared.prepared['approval_binding']['resident_guard_lifetime']=live.native_resident.guard_derivation(live,prepared.bundle)
        return prepared

    def test_complete_partial_and_post_control_cut_return_once_to_android(self):
        for case,fault,cut in (('normal',None,False),('bad-health',None,False),
                               ('normal','final-close',False),('normal',None,True)):
            with self.subTest(case=case,fault=fault,cut=cut):
                prepared=self.prepared();backend=Backend(prepared,self,case,fault)
                transition=live.core.Journal.transition
                def interrupted(journal,state,action,details):
                    result=transition(journal,state,action,details)
                    if cut and state=='OBSERVED':raise KeyboardInterrupt('after resident CONTROL and durable observation')
                    return result
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.object(live,'_p300_bundle',return_value=False))
                    stack.enter_context(mock.patch.object(live,'_p328_read_auth_key',return_value=(backend_test.KEY,backend_test.KEY_SHA256)))
                    stack.enter_context(mock.patch.object(ordinary.departure,'_snapshot',
                        side_effect=ordinary.departure.usbfs.UsbfsEndpointDeparture('/dev/bus/usb/003/077')))
                    with mock.patch.object(live.core.Journal,'transition',new=interrupted):
                        if cut:
                            with self.assertRaises(KeyboardInterrupt):live.execute_prepared(prepared,prepared.approval_token,backend)
                        else:result=live.execute_prepared(prepared,prepared.approval_token,backend)
                    retained={p:p.read_bytes() for p in prepared.run_dir.glob('candidate-observer*') if p.is_file()}
                    if cut:
                        with (mock.patch.object(backend,'observe_candidate',side_effect=AssertionError('resident observation replay')),
                              mock.patch.object(backend,'candidate_observer_session',side_effect=AssertionError('resident authentication replay'))):
                            result=live.recover_prepared(prepared,backend)
                        for path,raw in retained.items():self.assertEqual(path.read_bytes(),raw)
                    live.validate_live_result(json.loads((prepared.run_dir/'live-result.json').read_text()),prepared)
                self.assertEqual(result['current_state'],'CLOSED');self.assertFalse(result['recovery_required'])
                self.assertTrue(result['live_state']['final_verified'])
                self.assertEqual([c for c in backend.calls if c.startswith('transfer-')],['transfer-candidate','transfer-rollback'])
                self.assertEqual(backend.calls.count('observe'),1)
                self.assertFalse((prepared.run_dir/'native-restore-intent.json').exists())
                self.assertEqual(result['verdict'],'PASS_F1_V2_P386_ROOT_CONSOLE_AND_ROLLED_BACK' if case=='normal' and fault is None
                    else 'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
