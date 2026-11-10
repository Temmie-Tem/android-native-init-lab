"""V9 one-shot initial UCCS acknowledgement: actual C/ARM producer and wire."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_s22plus_stage2_diagnostics import compile_stage_fixture
from test_s22plus_pre_effect_return import compile_pre_effect, module_report
from test_s22plus_ml030_wire import KEY, ID, WIT, GOOD, record, w
from test_s22plus_hce_handoff import line

MODE=dict(handoff=True,reset_config=True,disabled_ucrdy=True,stale_uccs_ack=True)
def decode(data):return w.result(record(raw_bytes=data),WIT,KEY,ID,report_version=9)

class InitialCompletionTest(unittest.TestCase):
 def test_actual_c_arm_effect_order_and_faults(self):
  with tempfile.TemporaryDirectory() as tmp:
   for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
    out=Path(tmp)/compiler;exe=compile_stage_fixture(out/'stage',compiler,**MODE)
    if runner:self.assertIn('ARM aarch64',subprocess.check_output(['file',exe],text=True))
    def run(case=1,guard=0,expiry=0,entry=22,fault=0):
     p=subprocess.run([*runner,exe,*map(str,(fault,guard,-16,0xffffffff,0,entry,expiry,0,0,case))],check=True,capture_output=True,timeout=5)
     facts=decode(p.stdout);rows=p.stderr.decode().splitlines();rows=rows[:rows.index('REPORT_DONE')]
     self.assertLessEqual(len(p.stdout),256)
     return p.stdout,facts,rows
    data,facts,rows=run();ack=facts['initial_uccs_ack']
    self.assertEqual((facts['stage'],facts['stage2_observed'],facts['stage2_failed'],facts['stage2_hcs_masked']),(3,0x7ff,0,8))
    self.assertEqual((ack['flags'],ack['status'],ack['readback_raw']),(15,'ZERO_OBSERVED_IN_TIME',0))
    self.assertFalse(facts['normal_return']);self.assertTrue(facts['recovery_return'])
    store=next(i for i,r in enumerate(rows) if 'write hci:20=400' in r)
    opens=next(i for i,r in enumerate(rows) if 'open rails' in r)
    self.assertLess(store,opens)
    self.assertEqual([r.split()[-1] for r in rows[store-6:store+4]],['pin:1','hci','hci:34','hci','hci:20','hci','hci:20=400','hci','hci:20','hci'])
    self.assertEqual(sum('write hci:20=' in r for r in rows),1)
    # Zero path retains the old read sequence and no acknowledgement access.
    zero,z,zr=run(2);self.assertEqual(z['initial_uccs_ack']['flags'],0)
    self.assertFalse(any('write hci:20' in r for r in zr));self.assertEqual(sum('read hci:20' in r for r in zr),2)
    for case,entry in ((3,0),(4,19),(5,22)):
     _,f,tr=run(case,entry=entry);self.assertEqual(f['initial_uccs_ack']['flags'],0)
     self.assertEqual(f['hce_handoff']['refusal_condition'],'IRQ_STATUS')
     self.assertFalse(any('write hci:20' in r or 'open rails' in r for r in tr))
    # The pending bit is admission only; later AHIT/pin failures never write.
    for guard in range(2,12):
     _,f,tr=run(guard=guard);self.assertEqual(f['stage2_failed'],1<<(guard-1))
     self.assertEqual(f['initial_uccs_ack']['flags'],1 if guard>=9 else 0)
     self.assertFalse(any('write hci:20' in r or 'open rails' in r for r in tr))
    for case,status,prefix,index,raw in ((6,'DRIFT',1,1,1),(7,'DRIFT',1,8,0),(8,'DRIFT',1,8,0x800),
          (9,'NONZERO_READBACK',7,8,0x400),(10,'NONZERO_READBACK',7,8,0x800),
          (11,'DEADLINE',15,8,0),(12,'DEADLINE',7,8,0x400)):
     d,f,tr=run(case);v=list(map(int,d.split()));a=f['initial_uccs_ack']
     self.assertEqual((a['status'],a['flags'],v[28],v[29]),(status,prefix,index,raw))
     self.assertFalse(a['completed_in_time']);self.assertFalse(any('open rails' in r for r in tr))
     self.assertEqual(sum('write hci:20' in r for r in tr),int(prefix>=3))
    # Every new budget boundary, including an issued store with no readback.
    ack_clocks=[];clock=0
    for r in rows:
     if 'clock hci' in r:
      clock+=1
      if int(r.split()[0]) in (37,39,41,43,45):ack_clocks.append(clock)
    self.assertEqual(len(ack_clocks),5)
    for n,prefix,index in zip(ack_clocks,(1,1,1,3,15),(0,0,0,0,8)):
     d,f,tr=run(expiry=n);v=list(map(int,d.split()));a=f['initial_uccs_ack']
     self.assertEqual((a['status'],a['flags'],v[28]),('DEADLINE',prefix,index))
     self.assertEqual(sum('write hci:20' in r for r in tr),int(prefix>=3))
     self.assertFalse(any('open rails' in r for r in tr))
    # A later rate/supply failure keeps the completed acknowledgement history.
    for row in rows[opens+1:]:
     event,kind,_=row.split()
     if kind in ('remaining','rate-set','rate-get','supply-get','load','voltage-set','enable','voltage-get'):
      _,f,_=run(fault=int(event));self.assertEqual(f['initial_uccs_ack']['status'],'ZERO_OBSERVED_IN_TIME')

 def test_strict_prefix_provenance_guest_and_versions(self):
  with tempfile.TemporaryDirectory() as tmp:
   for compiler,runner in (('cc',()),('aarch64-linux-gnu-gcc',('qemu-aarch64',))):
    out=Path(tmp)/compiler
    guest=compile_pre_effect(out/'guest',compiler=compiler,guest=True,**MODE)
    module=compile_pre_effect(out/'module',compiler=compiler,**MODE)
    stage=compile_stage_fixture(out/'stage',compiler,**MODE)
    def accept(data):return int(subprocess.check_output([*runner,guest],input=data,timeout=5))==0
    good=GOOD+[1<<16,0,0x90000000,0xf20007ff]+[8191|(1<<13)|(2<<20),1,0x10f,0x400,0,0,0]
    self.assertTrue(decode(line(good))['normal_return']);self.assertTrue(accept(line(good)))
    # Completed ack plus later strict IS/command refusal is not ack failure.
    later=good.copy();later[0]=-16;later[4:11]=[0]*7
    f=decode(line(later));self.assertFalse(f['normal_return']);self.assertTrue(f['initial_uccs_ack']['completed_in_time'])
    for prefix in range(16):
     for pre in (0,0x400):
      for ho in (1,8191|(1<<13)|(2<<20)):
       v=good.copy();v[22]=0x020007ff|(prefix<<28);v[23]=ho;v[26]=pre
       if ho==1:v[24]=v[25]=0
       valid=prefix in (0,15) and (prefix==0 or ho!=1 and pre==0x400) and (ho!=1 or pre==0)
       if valid:self.assertTrue(decode(line(v))['normal_return'])
       else:
        with self.assertRaises(ValueError):decode(line(v))
       self.assertEqual(accept(line(v)),valid)
    # Every nonzero legacy high nibble must remain rejected.
    for version in (6,7,8):
     for prefix in range(1,16):
      v=good.copy();v[21]=version<<28;v[22]=0x7ff|(prefix<<28)
      with self.assertRaises(ValueError):w.result(record(v),WIT,KEY,ID,report_version=version)
    certificate=module_report(module,'refuse',runner)
    self.assertTrue(decode(certificate)['normal_return']);self.assertTrue(accept(certificate))
    v=list(map(int,certificate.split()));v[22]=1<<28
    with self.assertRaises(ValueError):decode(line(v))
    self.assertFalse(accept(line(v)))
    maximum=subprocess.check_output([*runner,stage,*map(str,(0,0,-16,1,0,24))],stderr=subprocess.DEVNULL,timeout=5)
    self.assertLessEqual(len(maximum),256);self.assertTrue(decode(maximum)['normal_return']);self.assertTrue(accept(maximum))

 def test_impossible_failure_prefix_site_and_readback(self):
  base=[-110,2,0x40000000]+[0]*14+[1,1,1<<16,0,0x9000011a,0x7ff]+[8191|(1<<13)|(2<<20),1,0x10f,0x400,0,0,0]
  for site,rc in ((0x11a,-110),(0x11b,-16),(0x11c,-5)):
   for prefix in range(16):
    for index in (0,1,8):
     for raw in (0,1,0x400,0x401):
      v=base.copy();v[0]=rc;v[21]=0x90000000|site;v[22]=0x7ff|(prefix<<28);v[28:]=[index,raw]
      expected=(site==0x11a and (prefix in (1,3) and index==raw==0 or prefix==7 and index==8 and raw!=0 or prefix==15 and index==8 and raw==0) or
       site==0x11b and prefix==1 and (index==1 and raw!=0 or index==8 and raw!=0x400) or
       site==0x11c and prefix==7 and index==8 and raw!=0)
      if expected:self.assertFalse(decode(line(v))['normal_return'])
      else:
       with self.assertRaises(ValueError):decode(line(v))
  # Pending cannot be smuggled into a rate failure or a completed result.
  for site,observed,failed,index,raw in ((0x301,0x7ff,0,0,0),(0x104,0x7f,0x40,7,1),(0x104,0xff,0x80,8,0x400)):
   v=base.copy();v[0]=-110 if site==0x301 else -16;v[21]=0x90000000|site;v[22]=(1<<28)|observed|(failed<<11);v[28:]=[index,raw]
   with self.assertRaises(ValueError):decode(line(v))

if __name__=='__main__':unittest.main()
