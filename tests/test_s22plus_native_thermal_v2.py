"""Actual V2 kernel C -> collector/private IPC -> exact retained HUD reader."""
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest

import s22plus_native_thermal_source_v2 as source
import s22plus_native_thermal_observer_v2 as observer
import s22plus_thermal_v2_fixtures as fixtures
import s22plus_native_baseline_v2_candidates as catalog

ROOT=source.ROOT
IDENTITY=catalog.DECLARATIONS['p390'].IDENTITY


class ThermalV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='s22-thermal-v2-');cls.addClassCleanup(cls.temp.cleanup)
        cls.out=Path(cls.temp.name);cls.provider=cls.out/'provider';cls.collector=cls.out/'collector'
        for name,raw in source.provider_sources().items():(cls.out/name).write_bytes(raw)
        body='\n'.join(line for line in (cls.out/'s22plus_thermal_telemetry.c').read_text().splitlines() if not line.startswith('#include'))
        (cls.out/'provider-body.c').write_text(body)
        (cls.out/'dt-fixture.h').write_bytes(fixtures.header(fixtures.facts()))
        (cls.out/'kernel-harness.c').write_bytes(fixtures.kernel_harness())
        flags=['cc','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all']
        p=subprocess.run([*flags,'-Wno-unused-variable','-I',str(cls.out),str(cls.out/'kernel-harness.c'),'-o',str(cls.provider)],capture_output=True,text=True,timeout=40)
        if p.returncode:raise AssertionError(p.stderr)
        raw=source.render_display(IDENTITY,[source.resident.common.MemoryModule('fixture.ko',123,0o400)])
        raw=source.resident.replace(raw,b'static int status_read(const char *path,char *text,size_t capacity,long filesystem) {',
            b'static int status_read(const char *,char *,size_t,long);\n'
            b'static __attribute__((unused)) int actual_status_read(const char *path,char *text,size_t capacity,long filesystem) {')
        (cls.out/'renderer.c').write_bytes(raw)
        harness=(ROOT/'tests/s22plus_thermal_collector_harness.c').read_bytes().replace(b'test_sample[512]',b'test_sample[768]')
        harness=source.resident.replace(harness,b'    if(!strcmp(argv[1],"frame")){',
            (ROOT/'tests/s22plus_thermal_v2_collector_extra.c').read_bytes()+
            b'    if(!strcmp(argv[1],"frame") || !strcmp(argv[1],"paint")){')
        harness=source.resident.replace(harness,b'resident_view=v;hud_record(&v);return 0;',
            b'resident_view=v;if(!strcmp(argv[1],"paint")) {'
            b'struct buffer b={.pixels=calloc(1,BYTES)};assert(b.pixels);paint(&b,2);'
            b'assert(fwrite(b.pixels,1,BYTES,stdout)==BYTES);free(b.pixels);'
            b'}else hud_record(&v);return 0;')
        harness=source.resident.replace(harness,
            b'printf("valid=%u mask=%u cpu_mc=%d battery_deci=%d\\n",m.valid,m.cpu_mask,m.cpu_temp_mc,m.battery_temp_deci);',
            b'printf("valid=%u mask=%u cpu_mc=%d battery_deci=%d gpu_mc=%d gpu_mask=%u ddr_mc=%d ddr_mask=%u\\n",'
            b'm.valid,m.cpu_mask,m.cpu_temp_mc,m.battery_temp_deci,s22_thermal_max(&m.thermal,13,2),'
            b'(m.thermal.mask>>13)&3U,m.thermal.temp_mc[15],(m.thermal.mask>>15)&1U);')
        (cls.out/'collector-harness.c').write_bytes(harness)
        p=subprocess.run([*flags,'-I',str(cls.out),'-I',str(source.NATIVE),
            '-I',str(ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm'),
            str(cls.out/'collector-harness.c'),'-o',str(cls.collector)],capture_output=True,text=True,timeout=40)
        if p.returncode:raise AssertionError(p.stderr)
        cls.ipc={}
        for name,wire_source in (('old',source.resident.read('wire.h')),('new',source.wire_source())):
            folder=cls.out/name;folder.mkdir();(folder/'selected-wire.h').write_bytes(wire_source)
            binary=folder/'ipc'
            p=subprocess.run([*flags,'-I',str(folder),str(ROOT/'tests/s22plus_thermal_v2_ipc_probe.c'),'-o',str(binary)],capture_output=True,text=True,timeout=40)
            if p.returncode:raise AssertionError(p.stderr)
            cls.ipc[name]=binary

    def producer(self,case='good'):
        p=subprocess.run([self.provider,case],capture_output=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr.decode());return p.stdout

    def collect(self,raw,case='normal'):
        p=subprocess.run([self.collector,case],input=raw,capture_output=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr.decode());return p

    @staticmethod
    def probe(rows,uptime=b'2.00 0.00'):
        count=len(rows.splitlines())
        return (b'S22RPROBE1\n'+uptime+b'\n'+
            f'S22RLOG1 first=1 last={count} records={count} evicted=0 dropped=0 partial_bytes=0 exhausted=0\n'.encode()+
            rows+b'S22RLOG1 COMPLETE\nS22RPROBE1 COMPLETE\n')

    def test_exact_merged_DT_parent_and_all_sensors(self):
        first=fixtures.facts()
        self.assertEqual(first['zones'],'/soc/thermal-zones');self.assertFalse(first['old_parent_exists'])
        self.assertEqual(tuple(first['sensors']),source.sensor_map())
        for index in range(1,4):self.assertEqual(fixtures.facts(index),first)
        bad=observer.parse_sample(self.producer('old-parent'))
        self.assertEqual((bad['mask'],bad['seen'],bad['error']),(0,[0,0],[-19,-19]))
        self.assertTrue(bad['battery_valid'])

    def test_producer_consumer_named_domains_and_zero(self):
        raw=self.producer();s=observer.parse_sample(raw)
        self.assertEqual(s['mask'],65535);self.assertEqual(s['temps'][13:],[46400,46500,50900])
        self.assertEqual(self.collect(raw).stdout,
            b'valid=1808 mask=8191 cpu_mc=50400 battery_deci=250 gpu_mc=46500 gpu_mask=3 ddr_mc=50900 ddr_mask=1\n')
        zero=observer.parse_sample(self.producer('zero'))
        self.assertEqual(zero['mask'],65535);self.assertEqual(zero['temps'],[0]*16)
        negative=observer.parse_sample(self.producer('negative'))
        self.assertEqual(negative['temps'],[-10000]*16);self.assertEqual(negative['battery_temp_deci'],-150)

    def test_binding_read_presence_and_partial_failures(self):
        self.assertEqual(self.producer('wrong-model'),b'ROOT_REJECTED_BEFORE_REGISTRATION\n')
        for case in ('wrong-map','wrong-resource','wrong-version','disabled','not-ready','runtime-disabled',
                     'runtime-version','partial','cpu-range','no-valid','missing-gpu','missing-ddr',
                     'wrong-channel','wrong-scale','wrong-table'):
            with self.subTest(case=case):observer.parse_sample(self.producer(case))
        version=observer.parse_sample(self.producer('wrong-version'))
        self.assertEqual((version['phase'][0],version['seen'][0],version['version'][0]),(1,1,0x30000000))
        self.assertEqual((version['enable'][0],version['ready'][0]),(0,0))
        disabled=observer.parse_sample(self.producer('runtime-disabled'))
        self.assertEqual((disabled['phase'][0],disabled['seen'][0],disabled['error'][0]),(2,3,-61))
        for case,missing in (('missing-gpu',1<<13),('missing-ddr',1<<15)):
            s=observer.parse_sample(self.producer(case));self.assertEqual(s['mask'],65535&~missing)
            self.assertEqual(s['mask']&8191,8191)

    def test_ADC_fault_latch_and_late_read_only_discovery(self):
        for case in ('adc-error','adc-wrong-format','adc-zero','adc-too-high','late-bank','deferred'):
            with self.subTest(case=case):
                samples=[observer.parse_sample(line+b'\n') for line in self.producer(case).splitlines()]
                self.assertEqual(len(samples),2);self.assertGreater(samples[1]['seq'],samples[0]['seq'])
                if case.startswith('adc-'):
                    self.assertFalse(samples[1]['battery_valid']);self.assertEqual(samples[1]['mask'],65535)

    def test_collector_rejects_stale_replay_and_inconsistent_values(self):
        raw=self.producer()
        empty=b'valid=0 mask=0 cpu_mc=0 battery_deci=0 gpu_mc=0 gpu_mask=0 ddr_mc=0 ddr_mask=0\n'
        for case in ('repeat','before','stale','future'):self.assertEqual(self.collect(raw,case).stdout,empty)
        for bad in (raw.replace(b'mask=65535 bound=',b'mask=65536 bound='),
                    raw.replace(b'error=0,0',b'error=-19,0'),raw.replace(b'phase=2,2',b'phase=1,2'),
                    raw.replace(b'seen=15,15',b'seen=7,15'),raw.replace(b'46400',b'150100'),
                    raw.replace(b'battery_temp_deci=250',b'battery_temp_deci=251'),
                    raw.replace(b'seq=1 ',b'seq=18446744073709551616 ')):
            with self.subTest(record=bad):
                self.assertEqual(self.collect(bad).stdout,empty)
                with self.assertRaises(ValueError):observer.parse_sample(bad)

    def test_complete_rows_join_and_missing_companion_does_not_prove_temperature(self):
        rows=self.collect(self.producer(),'frame').stderr
        value=observer.decode_hud(self.probe(rows))
        for domain in ('cpu','gpu','ddr','battery'):self.assertTrue(value[domain+'_temperature_observed'],value)
        self.assertTrue(value['thermal_diagnostics_complete']);self.assertEqual(value['latest']['thermal']['mask'],65535)
        missing=rows.split(b'\n',1)[1]
        value=observer.decode_hud(self.probe(missing))
        self.assertFalse(value['thermal_diagnostics_complete']);self.assertFalse(value['cpu_temperature_observed'])
        for bad in (rows.replace(b'frame=1 ',b'frame=2 ')+rows.split(b'\n',1)[0]+b'\n',
                    rows.replace(b'thermal_seq=1 ',b'thermal_seq=2 '),
                    rows.replace(b'RESIDENT_THERMAL2_FRAME ',b'RESIDENT_THERMAL_FRAME ')):
            with self.subTest(record=bad),self.assertRaises(ValueError):observer.decode_hud(self.probe(bad))
        stale=observer.decode_hud(self.probe(rows,b'9.00 0.00'))
        self.assertFalse(stale['cpu_temperature_observed']);self.assertFalse(stale['gpu_temperature_observed'])

    def test_same_acquisition_is_immutable_across_retained_frames(self):
        rows=self.collect(self.producer(),'frame').stderr
        second=rows.replace(b'frame=1 ',b'frame=2 ').replace(b'_FRAME seq=1 ',b'_FRAME seq=2 ')
        repeated=observer.decode_hud(self.probe(rows+second))
        self.assertTrue(repeated['gpu_temperature_observed'])
        for bad in (second.replace(b'46400',b'90000'),
                    second.replace(b'version=537264128',b'version=537264129'),
                    second.replace(b'battery_uv=522166 battery_temp_deci=250',b'battery_uv=463703 battery_temp_deci=300'),
                    second.replace(b'start_ms=1000',b'start_ms=999'),
                    second.replace(b'S22THERM2 seq=1 ',b'S22THERM2 seq=2 ').replace(b'thermal_seq=1 ',b'thermal_seq=2 ')
                        .replace(b'start_ms=1000 end_ms=1001',b'start_ms=1002 end_ms=1003'),
                    second.replace(b'hardware_seq=1 ',b'hardware_seq=2 ')):
            with self.subTest(record=bad),self.assertRaises(ValueError):observer.decode_hud(self.probe(rows+bad))

    def test_actual_C_maximum_width_rows_and_IPC_semantics(self):
        raw=self.producer();result=self.collect(raw,'bounds')
        fields=dict(item.split(b'=') for item in result.stdout.split())
        self.assertEqual((int(fields[b'sample_bytes']),int(fields[b'view_bytes'])),(304,656))
        self.assertLess(int(fields[b'record_bytes']),768)
        sample=result.stderr.split(b' S22THERM2 ',1)[1]
        value=observer.parse_sample(b'S22THERM2 '+sample)
        self.assertEqual(value['seq'],(1<<64)-1)
        self.assertIn(b'PASS V2',self.collect(raw,'ipc').stdout)

    def test_real_seqpacket_rejects_crossed_old_and_new_IPC(self):
        for sending in ('old','new'):
            payload=subprocess.check_output([self.ipc[sending],'emit'])
            self.assertEqual(len(payload),128 if sending=='old' else 304)
            for receiving in ('old','new'):
                with self.subTest(sender=sending,receiver=receiving):
                    left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
                    with left,right:
                        left.sendall(payload)
                        value=subprocess.check_output([self.ipc[receiving],'receive',str(right.fileno())],pass_fds=(right.fileno(),))
                        self.assertEqual(value,b'ACCEPT\n' if sending==receiving else b'REJECT\n')


if __name__=='__main__':unittest.main()
