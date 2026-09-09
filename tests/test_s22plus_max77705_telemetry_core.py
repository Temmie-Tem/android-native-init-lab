"""Real AArch64 fixed fuel-gauge protocol and conversion tests, H0 only."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include "telemetry_core.h"
struct fixture {unsigned calls;int fault_at;int id,revision,soc,voltage,current;};
static int byte(void *ctx,unsigned address,unsigned reg) {
 struct fixture *f=ctx;assert(address==0x66&&reg<=1);
 f->calls++;if(f->fault_at==(int)f->calls)return -EIO;
 return reg?f->revision:f->id;
}
static int word(void *ctx,unsigned address,unsigned reg) {
 struct fixture *f=ctx;assert(address==0x36);
 unsigned order[]={0x06,0x09,0x0a};assert(reg==order[f->calls%3]);
 f->calls++;if(f->fault_at==(int)f->calls)return -EIO;
 return reg==6?f->soc:reg==9?f->voltage:f->current;
}
static const struct s22_telemetry_ops ops={byte,word};
int main(void) {
 struct fixture f={.id=0x15,.revision=2,.soc=12800,.voltage=51200,.current=128};
 assert(!s22_telemetry_identity(&ops,&f)&&f.calls==2);
 f.calls=0;f.id=5;assert(s22_telemetry_identity(&ops,&f)==-ENODEV&&f.calls==1);
 f.id=0x15;f.revision=3;f.calls=0;assert(s22_telemetry_identity(&ops,&f)==-ENODEV&&f.calls==2);
 f.revision=2;f.calls=0;f.fault_at=1;assert(s22_telemetry_identity(&ops,&f)==-EIO&&f.calls==1);f.fault_at=0;
 struct s22_telemetry_state state={0};struct s22_telemetry_sample s;
 f.calls=0;s22_telemetry_read(&state,&ops,&f,&s);
 assert(s.sequence==1&&s.valid==7&&!s.error&&s.soc_permille==500&&s.voltage_uv==4000000&&s.current_ua==100000);
 f.current=65536-128;s22_telemetry_read(&state,&ops,&f,&s);assert(s.current_ua==-100000);
 f.current=32768;s22_telemetry_read(&state,&ops,&f,&s);assert(s.current_ua==-25600000);
 f.current=32767;s22_telemetry_read(&state,&ops,&f,&s);assert(s.current_ua==25599218);
 f.soc=100*256;f.current=0;s22_telemetry_read(&state,&ops,&f,&s);assert(s.soc_permille==1000&&s.current_ua==0);
 f.soc=100*256+1;f.voltage=0;s22_telemetry_read(&state,&ops,&f,&s);assert(s.valid==5&&!s.error&&s.soc_permille==1000);
 for(int fault=1;fault<=3;fault++) {
  state=(struct s22_telemetry_state){0};f.calls=0;f.fault_at=fault;
  s22_telemetry_read(&state,&ops,&f,&s);assert(s.error==-EIO&&f.calls==(unsigned)fault);
  s22_telemetry_read(&state,&ops,&f,&s);assert(s.error==-EIO&&f.calls==(unsigned)fault);
 }
 state=(struct s22_telemetry_state){0};f.calls=0;f.fault_at=0;f.soc=0;f.voltage=51200;
 for(unsigned i=0;i<601;i++)s22_telemetry_read(&state,&ops,&f,&s);
 assert(f.calls==1803&&s.sequence==601);s22_telemetry_read(&state,&ops,&f,&s);
 assert(s.error==-EOVERFLOW&&f.calls==1803);
 puts("PASS fixed reads conversions faults and finite budget");return 0;
}
'''

class TelemetryCore(unittest.TestCase):
    def test_real_arm64(self):
        cc=shutil.which('aarch64-linux-gnu-gcc');qemu=shutil.which('qemu-aarch64')
        self.assertTrue(cc and qemu)
        with tempfile.TemporaryDirectory() as folder:
            binary=Path(folder)/'test'
            p=subprocess.run([cc,'-x','c','-','-static','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'workspace/public/src/kernel-modules/s22plus_max77705_telemetry'),'-o',str(binary)],input=SOURCE,text=True,capture_output=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('ARM aarch64',subprocess.check_output(['file',binary],text=True))
            p=subprocess.run([qemu,binary],text=True,capture_output=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('PASS fixed reads',p.stdout)

if __name__=='__main__':unittest.main()
