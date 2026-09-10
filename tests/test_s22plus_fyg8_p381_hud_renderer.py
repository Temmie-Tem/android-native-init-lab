"""Status HUD uses the actual generated renderer and immutable DRM fixtures."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import test_s22plus_fyg8_p376_hud_renderer as base
import s22plus_fyg8_p381_display_renderer as renderer
ROOT=base.ROOT


def fixture():
    source,headers=base.fixture()
    source=source.replace('0x76','0x81').replace('c376','c381')
    source=source.replace('ticks+=100;', 'if(!strcmp(scenario,"metrics-stale")&&!ticks)ticks=10000;if(!strcmp(scenario,"metrics-event-stale")&&commits)ticks+=6000;ticks+=100;')
    source=source.replace('assert(white>10000', 'for(unsigned y=0;y<HEIGHT;y++){for(unsigned x=0;x<WIDTH;x++){if(pixels[y*(PITCH/4)+x]==0xffffffffU)assert(x>=120&&x<984&&y>=120&&y<2202);}}assert(white>10000')
    source=source.replace('int fake_close(int f){(void)f;', 'int fake_close(int f){if(f==3)return 0;')
    source=source.replace(' static unsigned seq,empty;assert', r'''
 if(f==3){
  static unsigned sequence,empty;
  assert(size==96&&flags==(MSG_DONTWAIT|MSG_TRUNC));
  if(!strcmp(scenario,"ipc-live"))return syscall(SYS_recvfrom,f,out,size,flags,NULL,NULL);
  if(!strcmp(scenario,"metrics-eof")||!strcmp(scenario,"paint-bounds"))return 0;
  if(empty){empty=0;errno=EAGAIN;return -1;}
  if(sequence&&!strcmp(scenario,"metrics-blocked")){errno=EAGAIN;return -1;}
  struct status_metrics value={.magic=0x32545353U,.sequence=++sequence,.valid=255,.gauge_sequence=sequence,.gauge_ms=2,.gauge_soc_permille=735,.gauge_voltage_uv=4000000,.gauge_current_ua=-123400,.collected_ms=1,
    .mem_total_kib=8*1024*1024,.mem_available_kib=3*1024*1024,.cpu_permille=357,.battery_pct=100,.charge=4,.battery_temp_deci=262};
  const unsigned char id[16]={0xc3,0x81,0xf1,0xe0,0xa9,0x0b,0x5e,0x6d,0x7c,0x8a,0x9b,0x0c,0x1d,0x2e,0x3f,0x0b};memcpy(value.run,id,16);
  if(!strcmp(scenario,"metrics-malformed"))value.valid=256;
  if(!strcmp(scenario,"metrics-stale"))value.collected_ms=0;
  if(!strcmp(scenario,"metrics-range"))value.cpu_permille=1001;
  if(!strcmp(scenario,"metrics-invalid-temp")){value.valid=3;value.battery_temp_deci=INT32_MIN;}
  if(!strcmp(scenario,"metrics-run"))value.run[0]^=1;
  if(!strcmp(scenario,"gauge-range"))value.gauge_current_ua=INT32_MIN;
  if(!strcmp(scenario,"gauge-cache-change")){value.gauge_sequence=1;value.gauge_current_ua-=sequence;}
  if(!strcmp(scenario,"gauge-regression")&&sequence>1)value.gauge_sequence=0;
  memcpy(out,&value,96);empty=1;return 96;
 }
 static unsigned seq,empty;assert''')
    source=source.replace('paint(&b,0xffffffffU);','run_id="c381f1e0a90b5e6d7c8a9b0c1d2e3f0b";paint(&b,0xffffffffU);')
    source=source.replace('"NNN");','"NNN",6);').replace('"OVERFLOW");','"OVERFLOW",6);')
    return source,headers


class StatusRenderer(base.HudRenderer):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        folder=Path(cls.temp.name);source,headers=fixture()
        (folder/'renderer.c').write_bytes(renderer.render());(folder/'fixture.c').write_text(source)
        cls.binary=folder/'renderer'
        p=subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-D_DEFAULT_SOURCE','-I',str(headers),'-I',str(ROOT/'workspace/public/src/native-init'),str(folder/'fixture.c'),'-o',str(cls.binary)],capture_output=True)
        if p.returncode:raise AssertionError(p.stderr.decode())

    def test_bad_metrics_keep_rendering(self):
        for case in ('metrics-eof','metrics-malformed','metrics-range','metrics-run'):
            with self.subTest(case=case):
                p=self.run_case(case);self.assertEqual(p.returncode,0,p.stderr)
                self.assertEqual(p.stderr.count(b'HUD_FRAME'),3)
                self.assertEqual(p.stderr.count(b' valid=0 '),3)

    def test_stale_sample_is_not_current(self):
        p=self.run_case('metrics-stale');self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stderr.count(b' valid=0 '),3)

    def test_slow_commit_cannot_certify_paint_time_freshness(self):
        p=self.run_case('metrics-event-stale');self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stderr.count(b' valid=0 '),3)

    def test_invalid_temperature_is_not_formatted(self):
        p=self.run_case('metrics-invalid-temp');self.assertEqual(p.returncode,0,p.stderr)

    def test_metrics_are_recorded(self):
        p=self.run_case('success');self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn(b'cpu_permille=357 battery_pct=100 charge=4 temp_deci=262',p.stderr)


    def test_invalid_gauge_disables_metrics(self):
        for case in ('gauge-range','gauge-cache-change','gauge-regression'):
            p=self.run_case(case);self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn(b' valid=0 ',p.stderr)

    def test_gem_records_follow_successful_retirement(self):
        p=self.run_case('success');self.assertEqual(p.returncode,0,p.stderr)
        lines=[line for line in p.stderr.splitlines() if line.startswith(b'HUD_MEM ')]
        self.assertEqual(len(lines),3)
        for i,line in enumerate(lines,1):
            self.assertLessEqual(len(line)+1,128)
            self.assertIn(f'alloc={i} retired={i-1} live=1 peak={1 if i==1 else 2}'.encode(),line)
        for case in ('rmfb-error','unmap-error','gem-close-error'):
            with self.subTest(case=case):
                failed=self.run_case(case)
                self.assertEqual(failed.stderr.count(b'HUD_MEM '),1)

if __name__=='__main__':unittest.main()
