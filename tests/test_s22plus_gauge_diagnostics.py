"""Actual ARM64 collector/parser with fixed sysfs I/O and failure fixtures."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import os
from test_s22plus_status_metrics_v2 import SOURCE,ROOT

MOCK=r'''
#include <sys/vfs.h>
#include <stdarg.h>
static int fixture_open_error,fixture_read_error;
static size_t sample_offset,detail_offset;
static char sample_value[512]="S22FG1 seq=1 start_ms=1000 valid=7 error=0 soc_raw=12800 voltage_raw=51200 current_raw=65408 soc_permille=500 voltage_uv=4000000 current_ua=-100000\n";
static char detail_value[193]="S22FGD1 probe=1 probe_error=0 bound=0 read=0 read_error=0 attempts=0 stopped=0\n";
static unsigned detail_opens;
static int fixture_open(const char *p,int flags,...){
 if(!strcmp(p,"/sys/module/s22plus_max77705_telemetry/parameters/sample")){
  assert(flags==(O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK));
  if(fixture_open_error){errno=fixture_open_error;return -1;}sample_offset=0;return 101;
 }
 if(!strcmp(p,"/sys/module/s22plus_max77705_telemetry/parameters/diagnostic")){detail_offset=0;detail_opens++;return 102;}
 return open(p,flags);
}
static ssize_t fixture_read(int fd,void *out,size_t size){
 if(fd==101||fd==102){
  if(fd==101&&fixture_read_error){errno=fixture_read_error;return -1;}
  const char *text=fd==101?sample_value:detail_value;size_t *off=fd==101?&sample_offset:&detail_offset;
  size_t n=strlen(text)-*off;if(n>size)n=size;memcpy(out,text+*off,n);*off+=n;return (ssize_t)n;
 }return read(fd,out,size);
}
static int fixture_statfs(int fd,struct statfs *out){if(fd==101||fd==102){memset(out,0,sizeof(*out));out->f_type=0x62656572L;return 0;}return fstatfs(fd,out);}
static int fixture_close(int fd){return fd==101||fd==102?0:close(fd);}
#define open fixture_open
#define read fixture_read
#define fstatfs fixture_statfs
#define close fixture_close
'''
MAIN=r'''
#undef open
#undef read
#undef fstatfs
#undef close
int main(void){
 assert(status_collect("invalid")==126);
 const char *path="/sys/module/s22plus_max77705_telemetry/parameters/sample";
 char raw[257];struct gauge_sample g;
 struct gauge_read_result r=gauge_read_text(path,raw,sizeof(raw));
 if(getenv("GAUGE_DEDUP")) {
  strcpy(detail_value,"S22FGD1 probe=13 probe_error=0 bound=1 read=35 read_error=0 read_ret=65408 attempts=1 stopped=0\n");
  gauge_diag_record(1,0,r,raw);
  strcpy(detail_value,"S22FGD1 probe=13 probe_error=0 bound=1 read=35 read_error=0 read_ret=256 attempts=2 stopped=0\n");
  gauge_diag_record(2,0,r,raw);assert(gauge_diag_count==1);return 0;
 }
 assert(!r.failure&&r.size==strlen(sample_value));
 assert(gauge_parse_reason(raw,&g)==GAUGE_PARSE_OK&&g.soc_permille==500&&g.voltage_uv==4000000&&g.current_ua==-100000);
 fixture_open_error=ENOENT;r=gauge_read_text(path,raw,sizeof(raw));assert(r.failure==GAUGE_READ_OPEN&&r.error==ENOENT&&!r.size);
 fixture_open_error=0;fixture_read_error=ENODEV;r=gauge_read_text(path,raw,sizeof(raw));assert(r.failure==GAUGE_READ_IO&&r.error==ENODEV&&!r.size);
 gauge_diag_record(1,100+r.failure,r,raw);assert(gauge_diag_count==1);
 for(unsigned i=0;i<20;i++)gauge_diag_record(i+2,100+r.failure,r,raw);
 assert(gauge_diag_count==1);
 strcpy(detail_value,"S22FGD1 probe=7 probe_error=-19 bound=0 read=0 read_error=0 attempts=0 stopped=0\n");
 gauge_diag_record(30,100+r.failure,r,raw);assert(gauge_diag_count==2);
 fixture_read_error=EAGAIN;r=gauge_read_text(path,raw,sizeof(raw));assert(r.error==EAGAIN);gauge_diag_record(31,100+r.failure,r,raw);
 fixture_read_error=0;
 strcpy(sample_value,"S22FG1 seq=0 start_ms=1000 valid=0 error=-19 soc_raw=0 voltage_raw=0 current_raw=0 soc_permille=0 voltage_uv=0 current_ua=0\n");
 r=gauge_read_text(path,raw,sizeof(raw));assert(!r.failure&&gauge_parse_reason(raw,&g)==GAUGE_PARSE_SOURCE_ERROR);
 gauge_diag_record(32,GAUGE_PARSE_SOURCE_ERROR,r,raw);
 strcpy(sample_value,"S22FG1 seq=1 start_ms=1000 valid=7 error=0 soc_raw=12800 voltage_raw=51200 current_raw=65408 soc_permille=500 voltage_uv=4000 current_ua=-100000\n");
 r=gauge_read_text(path,raw,sizeof(raw));assert(gauge_parse_reason(raw,&g)==GAUGE_PARSE_VOLTAGE);
 gauge_diag_record(33,GAUGE_PARSE_VOLTAGE,r,raw);
 strcpy(sample_value,"malformed\n");r=gauge_read_text(path,raw,sizeof(raw));assert(gauge_parse_reason(raw,&g)==GAUGE_PARSE_FORMAT);
 gauge_diag_record(34,GAUGE_PARSE_FORMAT,r,raw);
 for(unsigned i=0;i<40;i++)gauge_diag_record(35+i,200+i,r,raw);
 assert(gauge_diag_count==8);unsigned before=detail_opens;
 gauge_diag_record(99,999,r,raw);assert(detail_opens==before);
 memset(sample_value,'x',sizeof(sample_value)-1);sample_value[sizeof(sample_value)-1]=0;
 r=gauge_read_text(path,raw,sizeof(raw));assert(r.failure==GAUGE_READ_OVERFLOW&&r.size==256);
 puts("PASS ARM64 diagnostic distinctions, raw preservation and cap");return 0;
}
'''

class Diagnostics(unittest.TestCase):
    def test_actual_arm64(self):
        prefix=SOURCE[:SOURCE.index('int main(')].replace('#include "s22plus_status_metrics_v2.inc.c"',MOCK+'\n#include "s22plus_status_metrics_v3.inc.c"')
        with tempfile.TemporaryDirectory() as folder:
            binary=Path(folder)/'diagnostics'
            p=subprocess.run(['aarch64-linux-gnu-gcc','-x','c','-','-static','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'workspace/public/src/native-init'),'-o',str(binary)],input=prefix+MAIN,text=True,capture_output=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr)
            p=subprocess.run(['qemu-aarch64',binary],text=True,capture_output=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
            lines=p.stderr.splitlines();self.assertEqual(len(lines),8)
            self.assertTrue(all(line.startswith('GAUGE_DIAG ') and len(line)<1152 for line in lines))
            self.assertIn('errno=19',lines[0]);self.assertIn('errno=11',lines[2])
            self.assertIn(b'probe=7 probe_error=-19',bytes.fromhex(lines[1].split('diag_hex=')[1]))
            self.assertIn(b'error=-19',bytes.fromhex(lines[3].split('raw_hex=')[1].split()[0]))
            self.assertIn('reason=7 ',lines[4])
            p=subprocess.run(['qemu-aarch64',binary],text=True,capture_output=True,timeout=10,env=dict(os.environ,GAUGE_DEDUP='1'))
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(len(p.stderr.splitlines()),1)

if __name__=='__main__':unittest.main()
