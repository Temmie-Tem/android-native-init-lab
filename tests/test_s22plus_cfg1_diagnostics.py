"""V10 existing CFG1 accesses: actual C/ARM branches, formatter, guest and wire."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_s22plus_stage2_diagnostics import ROOT,SOURCE,HEADERS,function,compile_stage_fixture
from test_s22plus_pre_effect_return import compile_pre_effect,module_report
from test_s22plus_ml030_wire import KEY,ID,WIT,GOOD,record,w
from test_s22plus_hce_handoff import line

MODE=dict(handoff=True,reset_config=True,disabled_ucrdy=True,stale_uccs_ack=True,cfg1_diagnostics=True)

def compile_cfg1(out,compiler='cc',*,enabled=True,ordered_selection=False, link_irq_diagnostics=False):
 out.mkdir(parents=True,exist_ok=True)
 for header in HEADERS:
  p=out/header;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
 (out/'linux/errno.h').write_text('#include_next <linux/errno.h>\n')
 (out/'formatter.inc').write_text(function((SOURCE/'g0q_stage.c').read_text(),'static int report('))
 flags=['-DCFG1_FIXTURE','-DG0Q_PRE_EFFECT_RETURN','-DG0Q_HCE_HANDOFF','-DG0Q_RESET_CONFIG','-DG0Q_DISABLED_UCRDY','-DG0Q_STALE_UCCS_ACK']
 if enabled:flags.append('-DG0Q_CFG1_DIAGNOSTICS')
 if ordered_selection:flags.append('-DG0Q_CFG1_ORDERED_SELECTION')
 if link_irq_diagnostics:flags.append('-DG0Q_LINK_IRQ_DIAGNOSTICS')
 if compiler!='cc':flags.append('-static')
 exe=out/'cfg1'
 subprocess.run([compiler,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter',*flags,
                 '-I',out,'-I',SOURCE,ROOT/'tests/s22plus_hcs_ready_fixture.c','-o',exe],check=True)
 return exe

def decode(data):return w.result(record(raw_bytes=data),WIT,KEY,ID,report_version=10)

def good():return GOOD+[1<<16,0,0xa0000000,0xf20007ff]+[8191|(1<<13)|(2<<20),1,0x10f,0x400,0,0,0]+[3,0xffffffff,0xffffffff]

class Cfg1DiagnosticsTest(unittest.TestCase):
 def test_actual_access_clock_parity_and_branch_evidence(self):
  with tempfile.TemporaryDirectory() as tmp:
   for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
    out=Path(tmp)/compiler
    old=compile_cfg1(out/'v9',compiler,enabled=False);new=compile_cfg1(out/'v10',compiler)
    if runner:self.assertIn('ARM aarch64',subprocess.check_output(['file',new],text=True))
    for pre,post,expiry,hcs,hce in ((0,0,0,8,1),(0xffffffff,0xfffffffe,1,8,1),
             (0,1,1,8,1),(0x80000000,0x80000001,0,8,1),(1,1,0,0,1),(0,1,0,24,1),(0,1,0,8,2)):
     args=list(map(str,(8,8,hcs,0,0,hce,pre,post,expiry)))
     before=subprocess.run([*runner,old,*args],check=True,capture_output=True,timeout=5)
     after=subprocess.run([*runner,new,*args],check=True,capture_output=True,timeout=5)
     self.assertEqual(before.stderr,after.stderr) # includes every MMIO and clock
     v=list(map(int,after.stdout.split()));prior=list(map(int,before.stdout.split()))
     self.assertEqual(len(v),33);self.assertEqual(len(prior),30)
     self.assertEqual(v[:21]+v[22:30],prior[:21]+prior[22:])
     self.assertEqual(v[30:], [1 if not post&1 else 2 if expiry else 3,pre,post])
     f=decode(after.stdout)['cfg1'];self.assertEqual(f['budget_evaluated'],bool(post&1))
     rows=after.stderr.decode().splitlines();at=rows.index('write hci:dc='+format(pre|1,'x'))
     self.assertEqual(rows[at-1:at+2],['read hci:dc',rows[at],'read hci:dc'])
     self.assertEqual(sum('write hci:dc=' in r for r in rows),1)
     self.assertEqual(sum('read hci:dc'==r for r in rows),2)
     if not post&1:self.assertTrue(rows[at+2].startswith('STATS 0 0 2 1'))
     if expiry and post&1:self.assertEqual(rows[at+2:at+4],['clock','STATS 0 0 2 1'])
     if v[30] in (1,2):self.assertEqual(v[0],-5);self.assertEqual(v[4:10],[0]*6)
     self.assertFalse(decode(after.stdout)['normal_return']);self.assertTrue(decode(after.stdout)['recovery_return'])
     with self.assertRaises(ValueError):w.result(record(raw_bytes=after.stdout),WIT,KEY,ID,report_version=9)
     with self.assertRaises(ValueError):decode(before.stdout)
    # Existing early guard refuses before CFG1; all new fields stay unobserved.
    early=subprocess.check_output([*runner,new,*map(str,(1,0,8,0,0,1,0,1,0))],stderr=subprocess.DEVNULL)
    self.assertEqual(decode(early)['cfg1'],dict(outcome='UNREACHED',pre=None,post=None,budget_evaluated=False,budget_expired=None))

 def test_strict_outcomes_legacy_pairing_and_guest(self):
  with tempfile.TemporaryDirectory() as tmp:
   for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
    out=Path(tmp)/compiler;guest=compile_pre_effect(out/'guest',compiler=compiler,guest=True,**MODE)
    module=compile_pre_effect(out/'module',compiler=compiler,**MODE)
    def accepted(v):return int(subprocess.check_output([*runner,guest],input=line(v),timeout=5))==0
    success=good();self.assertTrue(decode(line(success))['normal_return']);self.assertTrue(accepted(success))
    for outcome in (0,1,2,4,0xffffffff):
     bad=success.copy();bad[30]=outcome
     with self.assertRaises(ValueError):decode(line(bad))
     self.assertFalse(accepted(bad))
    for index,value in ((31,-1),(32,-1),(31,2**32),(32,2**32),(32,0),(21,0x90000000)):
     bad=success.copy();bad[index]=value
     with self.assertRaises(ValueError):decode(line(bad))
     self.assertFalse(accepted(bad))
    for outcome in (1,2):
     failure=success.copy();failure[0]=-5;failure[4:10]=[0]*6;failure[30:]=[outcome,0,0 if outcome==1 else 1]
     f=decode(line(failure));self.assertFalse(f['normal_return']);self.assertTrue(f['recovery_return']);self.assertFalse(accepted(failure))
     for index,value in ((0,-110),(1,5),(3,0),(4,1),(5,1),(6,8),(7,0x400),(8,1),(9,9),(10,0),(22,0xf20007fe),(27,1),(28,1),(29,1),(32,outcome==1)):
      bad=failure.copy();bad[index]=int(value)
      with self.assertRaises(ValueError):decode(line(bad))
    unreachable=success.copy();unreachable[0]=-1;unreachable[4:11]=[0]*7;unreachable[30:]=[0,0,0]
    self.assertEqual(decode(line(unreachable))['cfg1']['outcome'],'UNREACHED')
    for index in (30,31,32):
     bad=unreachable.copy();bad[index]=1
     with self.assertRaises(ValueError):decode(line(bad))
    after=success.copy();after[4:10]=[0]*6
    for rc in (-110,-16):after[0]=rc;self.assertEqual(decode(line(after))['cfg1']['outcome'],'CHECK_PASSED')
    for rc in (-5,-1,0):
     after[0]=rc
     with self.assertRaises(ValueError):decode(line(after))
    cert=module_report(module,'refuse',runner);self.assertTrue(decode(cert)['normal_return'])
    for i in (30,31,32):
     bad=list(map(int,cert.split()));bad[i]=1
     with self.assertRaises(ValueError):decode(line(bad))
     self.assertFalse(accepted(bad))
    for data in (line(success[:-3]),line(success+[0]),line(success).replace(b'4294967295',b'+4294967295',1),line(success).replace(b'4294967295',b'04294967295',1)):
     with self.assertRaises(ValueError):decode(data)

 def test_actual_formatter_reader_maximum_and_all_early_paths(self):
  with tempfile.TemporaryDirectory() as tmp:
   for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
    out=Path(tmp)/compiler;stage=compile_stage_fixture(out/'stage',compiler,**MODE)
    guest=compile_pre_effect(out/'guest',compiler=compiler,guest=True,**MODE)
    maximum=subprocess.check_output([*runner,stage,*map(str,(0,0,-16,1,0,24))],stderr=subprocess.DEVNULL)
    self.assertEqual(len(maximum.split()),33);self.assertLessEqual(len(maximum),256)
    self.assertTrue(decode(maximum)['normal_return'])
    self.assertEqual(int(subprocess.check_output([*runner,guest],input=maximum)),0)
    for scenario in (1,2,6,7,8,9,10,11,12):
     data=subprocess.check_output([*runner,stage,*map(str,(0,0,-16,8,0,22,0,0,0,scenario))],stderr=subprocess.DEVNULL)
     self.assertEqual(decode(data)['cfg1']['outcome'],'UNREACHED')

if __name__=='__main__':unittest.main()
