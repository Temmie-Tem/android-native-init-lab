"""Fixed signed progress grammar and partial-capture adversarial cases."""
import copy,hashlib,hmac,struct,types,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_fyg8_p364_progress as progress
import s22plus_fyg8_p364_research_shell_runtime as runtime
import s22plus_fyg8_p364_research_shell_observer as observer
import device_action_f1_live_v2 as live
spec=progress.spec
KEY=b'k'*32;NONCE=b'n'*32

def frame(stage=1,event=0,code=0,ordinal=0,*,reserved=0,run=progress.RUN_ID,nonce=NONCE):
    body=struct.pack('<HBBi',stage,event,reserved,code);seq=spec.DIAGNOSTIC_SEQUENCE_BASE+ordinal
    tag=hmac.new(KEY,spec.DIAGNOSTIC_DOMAIN+run+nonce+struct.pack('<I',seq)+body,hashlib.sha256).digest()
    return types.SimpleNamespace(frame_type=spec.FRAME_DIAGNOSTIC,sequence=seq,payload=body+tag)

class GrammarTests(unittest.TestCase):
    def test_fixed_stage_plan_matches_native_cap(self):
        self.assertEqual(spec.MAX_DIAGNOSTIC_FRAMES,48)
        self.assertIn(b'#define P364_DIAG_MAX_FRAMES 48U',runtime.DIAGNOSTIC_SOURCE.read_bytes())
        p=progress.Progress()
        for i,(stage,event) in enumerate(spec.SUCCESS_EVENTS):p.accept(frame(stage,event,ordinal=i),KEY,NONCE)
        self.assertTrue(p.ready_for_control())
        a=types.SimpleNamespace(native_progress=p,authenticated=True,boot_id=b'b'*32,parent_identity_verified=True,display_frame_fully_written=True)
        value=progress.projection(a);self.assertEqual(progress.validate_projection(value),value)
    def test_invalid_frame_never_advances_prefix(self):
        bad=[frame(reserved=1),frame(run=b'x'*16),frame(nonce=b'x'*32),frame(ordinal=1),frame(stage=99),frame(event=1),frame(code=-1)]
        f=frame();f.payload=f.payload[:-1];bad.append(f)
        f=frame();f.payload=f.payload[:-1]+bytes((f.payload[-1]^1,));bad.append(f)
        for f in bad:
            with self.subTest(payload=f.payload.hex()[:12]):
                p=progress.Progress()
                with self.assertRaises(progress.ProgressError):p.accept(f,KEY,NONCE)
                self.assertEqual(p.records,[])
    def test_failure_forbids_next_operation_and_duplicate(self):
        p=progress.Progress();p.accept(frame(),KEY,NONCE);p.accept(frame(10,0,ordinal=1),KEY,NONCE)
        p.accept(frame(10,1,-2,ordinal=2),KEY,NONCE)
        with self.assertRaises(progress.ProgressError):p.accept(frame(11,0,ordinal=3),KEY,NONCE)
        with self.assertRaises(progress.TerminalReported):p.accept(frame(255,4,-2,ordinal=3),KEY,NONCE)
        with self.assertRaises(progress.ProgressError):p.accept(frame(255,4,-2,ordinal=4),KEY,NONCE)
        self.assertFalse(p.ready_for_control())
    def test_terminal_must_preserve_reported_original_error(self):
        p=progress.Progress();p.accept(frame(),KEY,NONCE);p.accept(frame(10,0,ordinal=1),KEY,NONCE);p.accept(frame(10,1,-2,ordinal=2),KEY,NONCE)
        with self.assertRaises(progress.ProgressError):p.accept(frame(255,4,-5,ordinal=3),KEY,NONCE)
    def test_cached_projection_cannot_change_code_or_meaning(self):
        p=progress.Progress();p.accept(frame(),KEY,NONCE)
        a=types.SimpleNamespace(native_progress=p,authenticated=True,boot_id=b'b'*32,parent_identity_verified=True,display_frame_fully_written=True)
        d=progress.projection(a)
        for key,value in [('unreturned_stage',10),('authority_granted',True),('full_candidate_qualification',True),('authenticated',False),('preparation_and_clone_returned',True)]:
            x=copy.deepcopy(d);x[key]=value
            with self.assertRaises(progress.ProgressError):progress.validate_projection(x)
    def test_empty_or_partial_open_keeps_no_progress(self):
        codec=live._open_header_initial_observer_module(runtime,observer,'p364-partial-prefix')
        blank=observer.replay_progress(codec,b'',b'',KEY)
        self.assertFalse(blank['authenticated']);self.assertEqual(blank['records'],[])
        wire=codec._CODEC.encode_frame(runtime.FRAME_OPEN,0,runtime.P364_RUN_ID)
        value=observer.replay_progress(codec,b'',wire[:7],KEY)
        self.assertFalse(value['display_frame_fully_written']);self.assertEqual(value['records'],[])
    def test_malformed_qualification_is_bounded_failure(self):
        for v in (None,[],{},dict(sessions=[]),dict(sessions=[None])):
            with self.assertRaises(observer.QualificationError):observer.validate_qualification(v)

if __name__=='__main__':unittest.main()
