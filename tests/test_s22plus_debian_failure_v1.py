"""Diagnostic authentication, incomplete evidence and distinct proof meanings."""
import hashlib
import struct
import unittest

import s22plus_debian_failure_protocol_v1 as protocol


class Diagnostics(unittest.TestCase):
    key=bytes(range(32));run_id=bytes(range(16))
    boot=b'12345678-1234-1234-1234-123456789abc'

    def record(self,*,sequence=2,outcome=1,status=0,error=0,stable=1,helper=1,**fields):
        values={name:0 for name in protocol.FIELDS}
        values.update(phase=12,semantic_done=1,initial_pid1_measured=1)
        values.update(fields)
        if not stable:values={name:0 for name in values}
        body=struct.pack('<27I',outcome,status,error,stable,300000,
            *(values[name]&0xffffffff for name in protocol.FIELDS))
        nonce=hashlib.sha256(self.boot).digest()
        tag=protocol.tag(self.key,self.run_id,nonce,250+helper,sequence,body,domain=protocol.DOMAIN)
        return b'S22DIAG1 run='+self.run_id.hex().encode()+b' boot='+self.boot+f' helper={helper} seq={sequence} mac='.encode()+\
            tag.hex().encode()+b' data='+body.hex().encode()+b'\n'

    def decode(self,raw,**kwargs):return protocol.decode(raw,key=self.key,run=self.run_id,**kwargs)

    def test_terminal_authenticates_with_missing_start(self):
        result=self.decode(self.record())
        self.assertTrue(result['records'][0]['semantic_success'])
        self.assertEqual(result['helper_status'],{'1':'WORKER_EXIT','2':'UNKNOWN'})
        for name in ('worker_collection_proved','descendant_settlement_proved','unmount_proved',
                'retention_proved','nonexecution_proved','replay_authorized'):
            self.assertFalse(result[name])

    def test_module_success_and_evidence_failure_are_separate(self):
        row=self.decode(self.record(status=256,result=1,call_returned=1,call_rc=0,call_errno=0,
            first_log_failure_stage=3,first_log_failure_errno=110,first_failure_phase=7,
            first_failure_errno=110))['records'][0]
        self.assertEqual(row['fields']['call_errno'],0)
        self.assertEqual(row['fields']['first_log_failure_errno'],110)
        self.assertFalse(row['semantic_success'])

    def test_abnormal_exit_signal_pending_and_clock_error(self):
        cases=[(dict(status=77<<8,semantic_done=0),'WORKER_EXIT'),
            (dict(outcome=2,status=15,semantic_done=0),'WORKER_SIGNAL'),
            (dict(outcome=3,phase=3,semantic_done=0),'WORKER_NOT_COLLECTED_AT_DEADLINE'),
            (dict(outcome=4,error=5,semantic_done=0),'OBSERVER_ERROR')]
        for args,expected in cases:
            row=self.decode(self.record(**args))['records'][0]
            self.assertEqual(row['observation'],expected);self.assertFalse(row['semantic_success'])

    def test_unstable_snapshot_cannot_assert_fields(self):
        row=self.decode(self.record(outcome=2,status=15,stable=0))['records'][0]
        self.assertIsNone(row['fields']);self.assertFalse(row['semantic_success'])

    def test_absent_torn_foreign_or_corrupted_terminal_is_unknown(self):
        raw=self.record()
        cases=(b'',raw[:-10],raw.replace(b'mac=',b'bad='),raw.replace(self.run_id.hex().encode(),b'f'*32),
            raw[:-3]+b'ff\n')
        for value in cases:self.assertEqual(self.decode(value)['status'],'UNKNOWN')
        self.assertEqual(self.decode(raw,expected_boot='00'*32)['status'],'UNKNOWN')

    def test_duplicate_authenticated_record_is_not_another_event(self):
        raw=self.record()
        with self.assertRaisesRegex(ValueError,'duplicate'):self.decode(raw+raw)

    def test_unreturned_operation_cannot_assert_success_or_errno(self):
        with self.assertRaisesRegex(ValueError,'unreturned'):
            self.decode(self.record(call_returned=0,call_rc=-1,call_errno=5))

    def test_late_collected_worker_and_unmeasured_ancestor_cannot_succeed(self):
        for args in (dict(error=110),dict(initial_pid1_measured=0)):
            self.assertFalse(self.decode(self.record(**args))['records'][0]['semantic_success'])


if __name__=='__main__':unittest.main()
