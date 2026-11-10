"""V11: ordered CFG1 selection, real C/ARM reachability and strict report modes."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_s22plus_cfg1_diagnostics import compile_cfg1,MODE,good
from test_s22plus_stage2_diagnostics import ROOT,SOURCE,HEADERS,compile_stage_fixture
from test_s22plus_pre_effect_return import compile_pre_effect,module_report
from test_s22plus_ml030_wire import KEY,ID,WIT,record,w
from test_s22plus_hce_handoff import line

V11=dict(MODE,cfg1_ordered_selection=True)

def decode(data,version=11):return w.result(record(raw_bytes=data),WIT,KEY,ID,report_version=version)

def success(bit):
 v=good();v[21]=0xb0000000;v[30:]=[3 if bit else 1,0x1c00052c,0x1c00052d if bit else 0x1c00052c]
 return v

class Cfg1SelectionTest(unittest.TestCase):
 def test_actual_clock_hce_order_and_legacy_negative(self):
  with tempfile.TemporaryDirectory() as tmp:
   for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
    out=Path(tmp)/compiler;old=compile_cfg1(out/'v10',compiler);new=compile_cfg1(out/'v11',compiler,ordered_selection=True)
    if runner:self.assertIn('ARM aarch64',subprocess.check_output(['file',new],text=True))
    for bit in (0,1):
     for expiry in (0,1):
      for pre in (0,0x1c00052c,0xfffffffe):
       post=pre|bit;args=list(map(str,(8,8,8,0,0,1,pre,post,expiry)))
       prior=subprocess.run([*runner,old,*args],check=True,capture_output=True,timeout=5)
       actual=subprocess.run([*runner,new,*args],check=True,capture_output=True,timeout=5)
       v=list(map(int,actual.stdout.split()));f=decode(actual.stdout)['cfg1'];rows=actual.stderr.decode().splitlines()
       at=rows.index('write hci:dc='+format(pre|1,'x'))
       self.assertEqual(rows[at-1:at+3],['read hci:dc',rows[at],'read hci:dc','clock'])
       self.assertEqual(rows[:at+2],prior.stderr.decode().splitlines()[:at+2])
       self.assertEqual(v[30:],[2 if expiry else 3 if bit else 1,pre,post])
       self.assertTrue(f['budget_evaluated']);self.assertEqual(f['budget_expired'],bool(expiry))
       if expiry:self.assertEqual(v[0],-5);self.assertIn('STATS 0 0 2 1',rows)
       else:self.assertEqual(v[0],-11);self.assertEqual(v[4],1);self.assertIn('write hci:34=1',rows)
       if bit:self.assertEqual(rows,prior.stderr.decode().splitlines())
       else:
        before=list(map(int,prior.stdout.split()));self.assertEqual((before[0],before[4],before[30]),(-5,0,1))
        self.assertFalse(decode(prior.stdout,10)['cfg1']['budget_evaluated'])
       with self.assertRaises(ValueError):decode(actual.stdout,10)
       with self.assertRaises(ValueError):decode(prior.stdout,11)

 def test_actual_full_local_link_and_downstream_stops(self):
  with tempfile.TemporaryDirectory() as tmp:
   for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
    out=Path(tmp)/compiler;out.mkdir()
    for header in HEADERS:
     p=out/header;p.parent.mkdir(exist_ok=True);p.touch()
    (out/'linux/errno.h').write_text('#include_next <linux/errno.h>\n')
    flags=['-DG0Q_PRE_EFFECT_RETURN','-DG0Q_HCE_HANDOFF','-DG0Q_RESET_CONFIG','-DG0Q_DISABLED_UCRDY','-DG0Q_STALE_UCCS_ACK','-DG0Q_CFG1_DIAGNOSTICS','-DG0Q_CFG1_ORDERED_SELECTION']
    if runner:flags.append('-static')
    exe=out/'full';subprocess.run([compiler,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,'-I',out,'-I',SOURCE,ROOT/'tests/s22plus_ml030_hci_fixture.c','-o',exe],check=True)
    if runner:self.assertIn('ARM aarch64',subprocess.check_output(['file',exe],text=True))
    for suffix in ((),('cfg1-clear',)):
     for case in ('positive','active','device-before','old-completion','transfer-pending','task-running',
          'no-calibration','expired-at-link','timer-disagreement','no-device','bad-code','link-lost',
          'no-uccs','expired-cfg1','first-local-bad-state','pre-command-irq','bit31-clear','timer-set-bad-code','last-local-bad-code'):
      with self.subTest(compiler=compiler,bit_clear=bool(suffix),case=case):
       subprocess.run([*runner,exe,case,*suffix],check=True,capture_output=True,timeout=5)

 def test_typed_host_guest_outcomes_and_legacy_separation(self):
  with tempfile.TemporaryDirectory() as tmp:
   for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
    out=Path(tmp)/compiler;guest=compile_pre_effect(out/'v11',compiler=compiler,guest=True,**V11)
    old=compile_pre_effect(out/'v10',compiler=compiler,guest=True,**MODE)
    module=compile_pre_effect(out/'module',compiler=compiler,**V11)
    def accept(v,exe=guest):return int(subprocess.check_output([*runner,exe],input=line(v),timeout=5))==0
    for bit in (0,1):
     v=success(bit);self.assertTrue(decode(line(v))['normal_return']);self.assertTrue(accept(v));self.assertFalse(accept(v,old))
     self.assertEqual(decode(line(v))['cfg1']['outcome'],'BIT_SET_BUDGET_PASS' if bit else 'BIT_CLEAR_BUDGET_PASS')
     for rc,local in ((-110,0),(-16,0),(-5,1),(-11,1),(-5,5),(-5,6),(-95,2)):
      bad=v.copy();bad[0]=rc;bad[4:10]=[local,0,0,0,0,0]
      self.assertFalse(decode(line(bad))['normal_return']);self.assertTrue(decode(line(bad))['recovery_return'])
     for rc in (0,-5,-1):
      bad=v.copy();bad[0]=rc;bad[4:10]=[0]*6
      with self.assertRaises(ValueError):decode(line(bad))
     expired=v.copy();expired[0]=-5;expired[4:10]=[0]*6;expired[30]=2
     self.assertEqual(decode(line(expired))['cfg1']['outcome'],'BUDGET_EXPIRED');self.assertFalse(accept(expired))
     for index,value in ((0,-110),(1,5),(3,0),(4,1),(5,1),(6,8),(7,0x400),(8,1),(9,9),(10,0),(22,0xf20007fe),(27,1),(28,1),(29,1)):
      bad=expired.copy();bad[index]=value
      with self.assertRaises(ValueError):decode(line(bad))
     for index,value in ((30,0),(30,4),(31,-1),(32,2**32),(21,0xa0000000),(32,v[32]^1)):
      bad=v.copy();bad[index]=value
      with self.assertRaises(ValueError):decode(line(bad))
      self.assertFalse(accept(bad))
    cert=module_report(module,'refuse',runner);self.assertTrue(decode(cert)['normal_return'])
    for index in (30,31,32):
     v=list(map(int,cert.split()));v[index]=1
     with self.assertRaises(ValueError):decode(line(v))
     self.assertFalse(accept(v))
    # Tag swapping cannot convert V10's old bit-clear refusal into V11 evidence.
    v=success(0);v[0]=-5;v[4:10]=[0]*6
    with self.assertRaises(ValueError):decode(line(v))
    v[21]=0xa0000000;self.assertEqual(decode(line(v),10)['cfg1']['outcome'],'READBACK_BIT_CLEAR')
    stage=compile_stage_fixture(out/'stage',compiler,**V11)
    maximum=subprocess.check_output([*runner,stage,*map(str,(0,0,-16,1,0,24))],stderr=subprocess.DEVNULL)
    self.assertEqual(len(maximum.split()),33);self.assertLessEqual(len(maximum),256)
    self.assertTrue(decode(maximum)['normal_return']);self.assertEqual(int(subprocess.check_output([*runner,guest],input=maximum)),0)

if __name__=='__main__':unittest.main()
