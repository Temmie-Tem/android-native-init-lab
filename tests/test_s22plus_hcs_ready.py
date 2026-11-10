"""V8 disabled-state UCRDY semantics through actual C and versioned wire."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import test_s22plus_hce_handoff as handoff
from test_s22plus_stage2_diagnostics import ROOT,SOURCE,HEADERS,compile_stage_fixture
from test_s22plus_ml030_wire import KEY,ID,WIT,GOOD,record,w
from test_s22plus_pre_effect_return import compile_pre_effect

class DisabledUcrdyHandoffTest(handoff.DedicatedResetHandoffTest):
    disabled_ucrdy=True
    report_version=8

    def test_post_stop_and_cold_hcs_bit_matrix(self):
        for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
            exe=compile_stage_fixture(self.out/(compiler+'-hcs'),compiler,handoff=True,reset_config=True,disabled_ucrdy=True)
            for case in (0,1):
                for hcs in (0,8,1,9,16,24,32,40,0x39,0xffffffff):
                    p=subprocess.run([*runner,exe,*map(str,(0,2,-16,hcs,0,case))],check=True,capture_output=True,timeout=5)
                    facts=self.decode(p.stdout);good=not hcs&0x31
                    self.assertEqual(facts['stage2_conditions']['HCS'],'PASS' if good else 'FAIL')
                    self.assertEqual(facts['hce_handoff']['refusal_condition'],'TRANSFER_DOORBELL' if good else 'HCS')
                    self.assertEqual(facts['stage2_hcs_masked'],hcs&0x39)
                    self.assertEqual(facts['stage2_observed'],7 if good else 3)
                    if not good:self.assertEqual(facts['hce_handoff']['refusal_raw'],hcs)
                    self.assertEqual(sum(' write ' in x for x in p.stderr.decode().splitlines()),case)
                    with self.assertRaises(ValueError):w.result(record(raw_bytes=p.stdout),WIT,KEY,ID,report_version=7)
            for case in (22,23):
                p=subprocess.run([*runner,exe,*map(str,(0,0,-16,1,0,case))],check=True,capture_output=True,timeout=5)
                facts=self.decode(p.stdout)
                self.assertEqual((facts['stage'],facts['stage2_observed'],facts['stage2_failed'],facts['stage2_hcs_masked']),(3,0x7ff,0,8))
                self.assertEqual(facts['hce_handoff']['status'],'STOP_COMPLETE' if case==22 else 'COLD_ENTRY')
            guest=compile_pre_effect(self.out/(compiler+'-v8-guest'),compiler=compiler,guest=True,handoff=True,reset_config=True,disabled_ucrdy=True)
            for hcs in (0,8):
                good=GOOD+[1<<16,0,0x80000000,0x7ff|(hcs<<22)]+[8191|(1<<13)|(2<<20),1,0x10f,0x400,0,0,0]
                data=(' '.join(map(str,good))+'\n').encode()
                self.assertTrue(self.decode(data)['normal_return'])
                self.assertEqual(int(subprocess.check_output([*runner,guest],input=data,timeout=5)),0)
                self.assertLessEqual(len(data),256)
            for badword in (0x040007ff,0x020007fe,0x0a0007ff):
                bad=good.copy();bad[22]=badword;data=(' '.join(map(str,bad))+'\n').encode()
                with self.assertRaises(ValueError):self.decode(data)
                self.assertNotEqual(int(subprocess.check_output([*runner,guest],input=data,timeout=5)),0)
            maximum=subprocess.check_output([*runner,exe,'0','0','-16','1','0','24'],stderr=subprocess.DEVNULL,timeout=5)
            self.assertTrue(self.decode(maximum)['normal_return'])
            self.assertEqual(int(subprocess.check_output([*runner,guest],input=maximum,timeout=5)),0)
            self.assertLessEqual(len(maximum),256)
            bad=good.copy();bad[21]=-2147483648
            data=(' '.join(map(str,bad))+'\n').encode()
            with self.assertRaises(ValueError):self.decode(data)
            self.assertNotEqual(int(subprocess.check_output([*runner,guest],input=data,timeout=5)),0)
            # A legacy semantic record cannot be relabeled: ready-only is no V8 failure.
            legacy=[-16,2,0x40040000]+[0]*14+[1,1,1<<16,0,0x80000104,3|(2<<11)|(8<<22)]+[8191|(1<<13)|(2<<20),1,0x10f,0x400,0,2,8]
            with self.assertRaises(ValueError):self.decode((' '.join(map(str,legacy))+'\n').encode())

class LaterDisabledUcrdyTest(unittest.TestCase):
    def test_actual_later_quiescence_pre_enable_and_enabled_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            for header in HEADERS:
                p=out/header;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
            (out/'linux/errno.h').write_text('#include_next <linux/errno.h>\n')
            for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
                baseline_trace=None
                for v8 in (False,True):
                    exe=out/(compiler+str(v8));flags=['-DG0Q_PRE_EFFECT_RETURN','-DG0Q_HCE_HANDOFF','-DG0Q_RESET_CONFIG']
                    if v8:flags.append('-DG0Q_DISABLED_UCRDY')
                    if runner:flags.append('-static')
                    subprocess.run([compiler,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,'-I',out,'-I',SOURCE,ROOT/'tests/s22plus_hcs_ready_fixture.c','-o',exe],check=True)
                    if runner:self.assertIn('ARM aarch64',subprocess.check_output(['file',exe],text=True))
                    def run(a,b,enabled=8,hce=0,final_hce=0,enabled_hce=1):
                        p=subprocess.run([*runner,exe,*map(str,(a,b,enabled,hce,final_hce,enabled_hce))],check=True,capture_output=True,timeout=5)
                        rc,reads,en,uic,writes,handoff=map(int,p.stdout.split());self.assertEqual(handoff,0)
                        return rc,reads,en,uic,writes,p.stderr.decode().splitlines()
                    for a in (0,8):
                        for b in (0,8):
                            rc,reads,en,uic,writes,trace=run(a,b)
                            admitted=v8 or not (a or b)
                            self.assertEqual((en,uic),(1,1) if admitted else (0,0))
                            self.assertEqual(rc,-11 if admitted else -16) # deliberate first DME value0
                            if admitted:
                                if not v8:baseline_trace=trace
                                else:self.assertEqual(trace,baseline_trace)
                                at=trace.index('write hci:dc=1');self.assertEqual(trace[:at].count('read hci:30'),2)
                    for bad in (1,9,16,24,32,40,0x39):
                        self.assertEqual(run(bad,0)[2:5],(0,0,0))
                    for bad in (1,9):self.assertEqual(run(0,bad)[2:5],(0,0,0))
                    self.assertEqual(run(0,0,hce=1)[2:5],(0,0,0))
                    for drift in (1,2):self.assertEqual(run(0,0,final_hce=drift)[2:5],(0,0,0))
                    for stuck in (0,2):
                        rc,_,en,uic,_,_=run(0,0,enabled_hce=stuck)
                        self.assertEqual((rc,en,uic),(-110,1,0))
                    rc,reads,en,uic,_,_=run(0,0,enabled=0)
                    self.assertEqual((rc,en,uic),(-110,1,0));self.assertGreater(reads,2)
                    self.assertEqual(run(0,0,enabled=24)[2:4],(1,0))

if __name__=='__main__':unittest.main()
