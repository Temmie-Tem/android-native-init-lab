"""VALID eligibility through actual provider, collector, IPC and host decoder."""
from pathlib import Path
import json
import re
import socket
import subprocess
import unittest

import test_s22plus_native_thermal_v2 as previous
import s22plus_thermal_v3_fixtures as fixtures
import s22plus_native_thermal_source_v3 as source
import s22plus_native_thermal_observer_v3 as observer
import s22plus_native_baseline_v2_candidates as catalog

ROOT=source.ROOT


class ThermalV3(unittest.TestCase):
    SOURCE=source
    IDENTITY=catalog.DECLARATIONS['p391'].IDENTITY
    KERNEL_HARNESS=staticmethod(fixtures.kernel_harness)
    producer=previous.ThermalV2.producer
    collect=previous.ThermalV2.collect
    probe=staticmethod(previous.ThermalV2.probe)

    @classmethod
    def setUpClass(cls):
        previous.ThermalV2.setUpClass.__func__(cls)
        cls.views={}
        for name,profile in (('v2',source.previous),('v3',source)):
            folder=cls.out/name;folder.mkdir()
            (folder/'selected-wire.h').write_bytes(profile.wire_source())
            cls.ipc[name]=folder/'sample'
            flags=['cc','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all']
            subprocess.run([*flags,'-I',str(folder),str(ROOT/'tests/s22plus_thermal_v2_ipc_probe.c'),
                '-o',str(cls.ipc[name])],check=True,capture_output=True,timeout=40)
            raw=profile.render_display(cls.IDENTITY,[source.resident.common.MemoryModule('fixture.ko',123,0o400)])
            (folder/'view-renderer.c').write_bytes(raw)
            cls.views[name]=folder/'view'
            subprocess.run([*flags,'-I',str(folder),'-I',str(source.NATIVE),
                '-I',str(ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm'),
                '-DTEST_RUN="'+cls.IDENTITY.run_id_hex+'"',str(ROOT/'tests/s22plus_thermal_v3_view_probe.c'),
                '-o',str(cls.views[name])],check=True,capture_output=True,timeout=40)

    def sampled(self,case):
        p=subprocess.run([self.provider,case],capture_output=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr.decode())
        counts=[tuple(map(int,m)) for m in re.findall(rb'bank=(\d+) status_reads=(\d+) trdy_reads=(\d+)',p.stderr)]
        return observer.parse_sample(p.stdout.splitlines()[0]+b'\n'),counts,p.stdout

    def test_independent_TRDY_VALID_combinations_and_one_read_per_sensor(self):
        for trdy in (1,0,8):
            for valid in (1,0):
                with self.subTest(trdy=trdy,valid=valid):
                    s,counts,raw=self.sampled(f'cross-{trdy}-{valid}')
                    self.assertEqual(counts,[(0,11,1),(1,5,1)])
                    self.assertEqual(s['ready'],[trdy,trdy]);self.assertEqual(s['seen'],[15,15])
                    self.assertEqual(s['error'],[0,0]);self.assertEqual(s['mask'],65535 if valid else 0)
                    self.assertTrue(s['battery_valid'])
                    hud=observer.decode_hud(self.probe(self.collect(raw,'frame').stderr))
                    for domain in ('cpu','gpu','ddr'):self.assertEqual(hud[domain+'_temperature_observed'],bool(valid))
                    self.assertTrue(hud['battery_temperature_observed'])

    def test_failed_bank_preconditions_do_not_gain_status_reads(self):
        for case in ('wrong-map','wrong-resource','wrong-version','disabled','runtime-disabled','runtime-version'):
            with self.subTest(case=case):
                s,counts,_=self.sampled(case)
                self.assertEqual(counts[0][1],0);self.assertEqual(counts[1],(1,5,1))
                self.assertNotEqual(s['error'][0],0)
        s,counts,_=self.sampled('old-parent')
        self.assertEqual(counts,[(0,0,0),(1,0,0)]);self.assertEqual(s['mask'],0)

    def test_partial_zero_negative_and_range_semantics(self):
        for case in ('partial','missing-gpu','missing-ddr','zero','negative','cpu-range'):
            with self.subTest(case=case):
                s,_,raw=self.sampled(case);self.collect(raw)
                if case=='zero':self.assertEqual((s['mask'],s['temps']),(65535,[0]*16))
                elif case=='negative':self.assertEqual(s['temps'],[-10000]*16)
                else:self.assertNotEqual(s['mask'],65535);self.assertNotEqual(s['mask'],0)

    def test_ADC_fault_latch_preserves_VALID_TSENS(self):
        for case in ('adc-error','adc-wrong-format','adc-zero','adc-too-high'):
            with self.subTest(case=case):
                _,_,raw=self.sampled(case);samples=[observer.parse_sample(r+b'\n') for r in raw.splitlines()]
                self.assertEqual(len(samples),2)
                for s in samples:self.assertFalse(s['battery_valid']);self.assertEqual(s['mask'],65535)

    def test_stale_replay_and_inconsistent_records_remain_unavailable(self):
        raw=self.producer('cross-8-1')
        empty=b'valid=0 mask=0 cpu_mc=0 battery_deci=0 gpu_mc=0 gpu_mask=0 ddr_mc=0 ddr_mask=0\n'
        for case in ('repeat','before','stale','future'):self.assertEqual(self.collect(raw,case).stdout,empty)
        for bad in (raw.replace(b'phase=2,2',b'phase=1,2'),raw.replace(b'seen=15,15',b'seen=7,15'),
                    raw.replace(b'error=0,0',b'error=-19,0'),raw.replace(b'46400',b'150100')):
            with self.subTest(record=bad):
                self.assertEqual(self.collect(bad).stdout,empty)
                with self.assertRaises(ValueError):observer.parse_sample(bad)

    def test_default_V2_semantics_and_version_separation_are_preserved(self):
        old=observer.previous
        for trdy in (1,0,8):
            raw=self.producer(f'cross-{trdy}-1');as_v2=raw.replace(b'S22THERM3',b'S22THERM2')
            self.assertEqual(observer.parse_sample(raw)['mask'],65535)
            if trdy==1:self.assertEqual(old.parse_sample(as_v2)['mask'],65535)
            else:
                with self.assertRaises(ValueError):old.parse_sample(as_v2)
            with self.assertRaises(ValueError):old.parse_sample(raw)
            with self.assertRaises(ValueError):observer.parse_sample(as_v2)
        rows=self.collect(self.producer('cross-8-1'),'frame').stderr
        with self.assertRaises(ValueError):old.decode_hud(self.probe(rows))
        v2rows=rows.replace(b'S22THERM3',b'S22THERM2').replace(b'THERMAL3_FRAME',b'THERMAL2_FRAME')
        with self.assertRaises(ValueError):observer.decode_hud(self.probe(v2rows))

    def test_frame_join_acquisition_order_and_missing_companion(self):
        rows=self.collect(self.producer('cross-8-1'),'frame').stderr
        repeat=rows.replace(b'frame=1 ',b'frame=2 ').replace(b'_FRAME seq=1 ',b'_FRAME seq=2 ')
        self.assertTrue(observer.decode_hud(self.probe(rows+repeat))['cpu_temperature_observed'])
        for bad in (repeat.replace(b'ready=8,8',b'ready=0,8'),repeat.replace(b'46400',b'90000'),
                    repeat.replace(b'S22THERM3 seq=1 ',b'S22THERM3 seq=2 ').replace(b'thermal_seq=1 ',b'thermal_seq=2 ')
                        .replace(b'start_ms=1000 end_ms=1001',b'start_ms=1002 end_ms=1003')):
            with self.assertRaises(ValueError):observer.decode_hud(self.probe(rows+bad))
        missing=observer.decode_hud(self.probe(rows.split(b'\n',1)[1]))
        self.assertFalse(missing['thermal_diagnostics_complete']);self.assertFalse(missing['cpu_temperature_observed'])

    def test_equal_size_sample_and_actual_renderer_view_rejection(self):
        for binaries,size in ((self.ipc,304),(self.views,656)):
            for sending in ('v2','v3'):
                payload=subprocess.check_output([binaries[sending],'emit']);self.assertEqual(len(payload),size)
                for receiving in ('v2','v3'):
                    with self.subTest(size=size,sender=sending,receiver=receiving):
                        left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
                        with left,right:
                            left.sendall(payload)
                            try:
                                p=subprocess.run([binaries[receiving],'receive',str(right.fileno())],pass_fds=(right.fileno(),),
                                    capture_output=True,timeout=1 if size==656 and sending!=receiving else 5)
                            except subprocess.TimeoutExpired as error:
                                # The real renderer parks after failure for its external supervisor.
                                self.assertEqual(size,656);self.assertNotEqual(sending,receiving)
                                self.assertIn(b'DISPLAY_FAIL stage=hud-snapshot-order',error.stderr)
                                self.assertNotIn(b'ACCEPT',error.stdout or b'')
                                continue
                        if sending==receiving:self.assertEqual((p.returncode,p.stdout),(0,b'ACCEPT\n'))
                        elif size==304:self.assertEqual((p.returncode,p.stdout),(0,b'REJECT\n'))
                        else:self.fail('renderer rejection must retain its supervised failure park')

    def test_actual_maximum_width_rows_and_IPC_high_water_marks(self):
        raw=self.producer('cross-8-1');result=self.collect(raw,'bounds')
        fields=dict(item.split(b'=') for item in result.stdout.split())
        self.assertEqual((int(fields[b'sample_bytes']),int(fields[b'view_bytes'])),(304,656))
        self.assertLess(int(fields[b'record_bytes']),768)
        sample=b'S22THERM3 '+result.stderr.split(b' S22THERM3 ',1)[1]
        self.assertEqual(observer.parse_sample(sample)['seq'],(1<<64)-1)
        self.assertIn(b'acquisition order',self.collect(raw,'ipc').stdout)


if __name__=='__main__':unittest.main()
