"""P371 real generated native protocol with the established PTY fixture."""
from pathlib import Path
import sys,types,unittest
from unittest import mock
base=types.ModuleType('_p371_handoff_fixture');base.__file__=str(Path('tests/test_s22plus_fyg8_p370_handoff.py').resolve());sys.modules[base.__name__]=base
raw=Path(base.__file__).read_text().replace('p370','p371').replace('P370','P371')
exec(compile(raw,base.__file__+'#p371','exec'),base.__dict__)
original_source=base.source
runtime=base.runtime;observer=base.observer;KEY=base.KEY

def source():
    value=original_source().replace('state->status_count++; /* Consume before the response;', 'state->status_count++;fx_mark("status",state->status_count); /* Consume before the response;')
    return value.replace('if(size>100U)return -P260_EOVERFLOW;', 'if(size>100U)return -P260_EOVERFLOW;\n    if(kind==0x8fU && fx_case("status-write-failure")){fx_mark("status-write-failure",0);(void)sys_write(fd,"partial",7);return -EIO;}')
base.source=source

class StatusProtocol(base.HandoffTests):
    def run_case(self,*args,**kwargs):
        with mock.patch.object(observer.control,'STATUS_INTERVAL_SEC',.1):
            return super().run_case(*args,**kwargs)
    def test_two_signed_status_samples(self):
        value,error,events,marks,audits=self.run_case()
        self.assertIsNone(error)
        samples=value.receipt['status_samples'];self.assertEqual(len(samples),2)
        self.assertEqual(samples[0]['elapsed_since_first_ms'],0)
        self.assertGreaterEqual(samples[1]['elapsed_since_first_ms'],2000)
        self.assertTrue(all(s['child_unreaped'] and s['submitted_swaps']==3 for s in samples))
        self.assertEqual(value.receipt['total_command_count'],6)
        self.assertEqual(marks.count('child 0'),1);self.assertEqual(marks.count('download 0'),1)

    def test_early_second_sample_and_child_exit_still_allow_control(self):
        for case in ('wait-good','wait-exit'):
            with self.subTest(case=case),mock.patch.object(observer.control,'STATUS_INTERVAL_SEC',0):
                # Call the parent directly so run_case does not restore the normal interval.
                value,error,events,marks,audits=base.HandoffTests.run_case(self,case)
                self.assertIsNone(value);self.assertIsNotNone(error)
                self.assertEqual(marks.count('download 0'),1)
                self.assertEqual(marks.count('status 1'),1);self.assertEqual(marks.count('status 2'),1)

    def test_native_control_before_or_between_status(self):
        def one(io,audit):
            body=observer.control.STATUS_BODY
            io.write(observer.control.FRAME_STATUS,8,body+observer._handoff_tag(io.key,observer.control.STATUS_REQUEST_DOMAIN,audit.nonce,8,body))
            io.frame(observer.control.FRAME_STATUS_REPLY,8,diagnostics=True)
        for count in (0,1):
            with self.subTest(status_count=count),mock.patch.object(observer,'_query_statuses',side_effect=(one if count else lambda *_:None)),mock.patch.object(observer,'replay_progress',return_value={}):
                # Deliberately outside the normal two-STATUS host grammar: test native availability only.
                value,error,events,marks,audits=self.run_case()
                self.assertIsNone(value);self.assertIsNotNone(error)
                self.assertEqual(marks.count('download 0'),1)
                self.assertEqual(marks.count('status 1'),count);self.assertNotIn('status 2',marks)

    def test_duplicate_or_reordered_status_stops_without_control(self):
        for sequences in ((8,8),(9,)):
            def wrong(io,audit):
                for seq in sequences:
                    body=observer.control.STATUS_BODY
                    io.write(observer.control.FRAME_STATUS,seq,body+observer._handoff_tag(io.key,observer.control.STATUS_REQUEST_DOMAIN,audit.nonce,seq,body))
                    io.frame(observer.control.FRAME_STATUS_REPLY,seq,diagnostics=True)
            with self.subTest(sequences=sequences),mock.patch.object(observer,'_query_statuses',side_effect=wrong),mock.patch.object(observer,'replay_progress',return_value={}):
                value,error,events,marks,audits=self.run_case()
                self.assertIsNone(value);self.assertIsNotNone(error);self.assertNotIn('download 0',marks)
                self.assertEqual(marks.count('status 1'),1 if sequences[0]==8 else 0)

    def test_partial_status_response_consumed_once_without_control(self):
        with mock.patch.object(observer,'replay_progress',return_value={}):
            value,error,events,marks,audits=self.run_case('status-write-failure')
        self.assertIsNone(value);self.assertIsNotNone(error)
        self.assertEqual(marks.count('status 1'),1);self.assertNotIn('status 2',marks)
        self.assertEqual(marks.count('status-write-failure 0'),1);self.assertNotIn('download 0',marks)

if __name__=='__main__':unittest.main()
