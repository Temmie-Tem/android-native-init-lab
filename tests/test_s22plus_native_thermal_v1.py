"""Actual kernel producer -> actual renderer collector -> retained HUD reader."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import s22plus_native_thermal_source_v1 as source
import s22plus_native_thermal_observer_v1 as observer

ROOT=source.ROOT
MODULE=ROOT/'workspace/public/src/kernel-modules/s22plus_thermal_telemetry_v1'
IDENTITY=source.resident.common.Identity('p389','60d377fedd013a3cd41b7afc3b79563b','v0.2.0-rc.7')


class Thermal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='s22-thermal-h0-');cls.addClassCleanup(cls.temp.cleanup)
        cls.out=Path(cls.temp.name);cls.provider=cls.out/'provider';cls.collector=cls.out/'collector'
        body='\n'.join(line for line in (MODULE/'s22plus_thermal_telemetry.c').read_text().splitlines() if not line.startswith('#include'))
        (cls.out/'provider-body.c').write_text(body)
        flags=['cc','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all']
        p=subprocess.run([*flags,'-Wno-unused-variable','-I',str(MODULE),'-I',str(cls.out),
            str(ROOT/'tests/s22plus_thermal_kernel_harness.c'),'-o',str(cls.provider)],capture_output=True,text=True,timeout=40)
        if p.returncode:raise AssertionError(p.stderr)
        raw=source.render_display(IDENTITY,[source.resident.common.MemoryModule('fixture.ko',123,0o400)])
        raw=source.resident.replace(raw,b'static int status_read(const char *path,char *text,size_t capacity,long filesystem) {',
            b'static int status_read(const char *,char *,size_t,long);\n'
            b'static __attribute__((unused)) int actual_status_read(const char *path,char *text,size_t capacity,long filesystem) {')
        (cls.out/'renderer.c').write_bytes(raw)
        p=subprocess.run([*flags,'-I',str(cls.out),'-I',str(source.NATIVE),
            '-I',str(ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm'),
            str(ROOT/'tests/s22plus_thermal_collector_harness.c'),'-o',str(cls.collector)],capture_output=True,text=True,timeout=40)
        if p.returncode:raise AssertionError(p.stderr)

    def run_provider(self,case):
        result=subprocess.run([self.provider,case],capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        return result.stdout

    def collect(self,raw,case='normal'):
        result=subprocess.run([self.collector,case],input=raw,capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        return result

    def test_actual_kernel_wrapper_binding_reads_and_failures(self):
        for case in ('good','wrong-model','wrong-map','wrong-resource','wrong-version','disabled',
            'wrong-table','wrong-channel','wrong-scale','deferred','late-bank','partial','not-ready',
            'cpu-range','negative','adc-error','adc-wrong-format','adc-zero','adc-too-high'):
            with self.subTest(case=case):self.run_provider(case)

    def test_producer_consumer_units_and_replay_expiry(self):
        raw=self.run_provider('emit')
        self.assertEqual(self.collect(raw).stdout,'valid=272 mask=8191 cpu_mc=50400 battery_deci=250\n')
        for case in ('repeat','before','stale','future'):
            with self.subTest(case=case):self.assertEqual(self.collect(raw,case).stdout,'valid=0 mask=0 cpu_mc=0 battery_deci=0\n')
        for bad in (raw.replace('valid=3','valid=7'),raw.replace('battery_temp_deci=250','battery_temp_deci=251'),
            raw.replace('battery_uv=522166','battery_uv=0'),raw.replace('cpu_mask=8191','cpu_mask=8192'),
            raw.replace('seq=1 ','seq=18446744073709551616 '),raw.replace('cpu_temp_mc=50400','cpu_temp_mc=-40001'),
            raw.replace('cpu0_error=0','cpu0_error=-19'),raw.replace('end_ms=1001','end_ms=999')):
            with self.subTest(record=bad):self.assertEqual(self.collect(bad).stdout,'valid=0 mask=0 cpu_mc=0 battery_deci=0\n')

    def test_actual_new_frame_reopens_and_old_dialect_cannot_substitute(self):
        row=self.collect(self.run_provider('emit'),'frame').stderr.encode()
        raw=(b'S22RPROBE1\n2.00 0.00\nS22RLOG1 first=1 last=1 records=1 evicted=0 dropped=0 partial_bytes=0 exhausted=0\n'+
            row+b'S22RLOG1 COMPLETE\nS22RPROBE1 COMPLETE\n')
        value=observer.decode_hud(raw)
        self.assertTrue(value['cpu_temperature_observed']);self.assertTrue(value['battery_temperature_observed'])
        self.assertEqual(value['latest']['battery_temp_deci'],250);self.assertEqual(value['latest']['cpu_mask'],8191)
        old=raw.replace(b'RESIDENT_THERMAL_FRAME ',b'RESIDENT_FRAME ').replace(b' battery_temp_deci=250',b'')
        for bad in (old,raw+b'tail',raw.replace(b'battery_temp_deci=250',b'battery_temp_deci=901')):
            with self.assertRaises(ValueError):observer.decode_hud(bad)
        stale=raw.replace(b'2.00 0.00',b'9.00 0.00')
        value=observer.decode_hud(stale)
        self.assertFalse(value['cpu_temperature_observed']);self.assertFalse(value['battery_temperature_observed'])

    def test_declared_cpu_map_and_table_match_exact_primary_sources(self):
        kernel=ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform'
        dt=(kernel/'qcom/proprietary/devicetree/qcom/waipio-thermal.dtsi').read_text()
        core=(MODULE/'thermal_core.h').read_text()
        selected=re.findall(r'\{"(cpu-[01]-\d+)",(\d+),(\d+)\}',core)
        self.assertEqual(len(selected),13)
        for name,bank,sensor in selected:
            match=re.search(r'\b'+re.escape(name)+r'\s*\{.*?thermal-sensors\s*=\s*<&tsens(\d+)\s+(\d+)>',dt,re.S)
            self.assertIsNotNone(match,name);self.assertEqual(match.groups(),(bank,sensor))
        board=(kernel/'msm-kernel/arch/arm64/boot/dts/samsung/rainbow/g0q/g0q_kor_singlex_w00_r12.dts').read_text()
        table=re.search(r'battery,temp_table_adc = <([^>]+)>;',board).group(1)
        expected=[int(x,16) for x in table.split()]
        actual=re.search(r's22_thermal_uv\[S22_THERMAL_TABLE_COUNT\] = \{([^}]+)',core).group(1)
        self.assertEqual([int(x.strip(),16) for x in actual.split(',')],expected)
        self.assertEqual((expected[0],expected[-1]),(77530,970782))


if __name__=='__main__':unittest.main()
