"""Accelerated actual producer and exact-name CPU selection; no device access."""
from pathlib import Path
import subprocess
import tempfile
import unittest

import s22plus_native_source_v1 as common
import s22plus_native_resident_source_v1 as source


class Metrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='s22-resident-metrics-h0-');cls.addClassCleanup(cls.temp.cleanup)
        folder=Path(cls.temp.name);identity=common.Identity('p386','42'*16,'v0.2.0-rc.4')
        raw=source.render_display(identity,[common.MemoryModule('fixture.ko',123,0o400)])
        raw=source.replace(raw,b'static int status_read(const char *path,char *text,size_t capacity,long filesystem) {',
            b'static int status_read(const char *,char *,size_t,long);\n'
            b'static __attribute__((unused)) int actual_status_read(const char *path,char *text,size_t capacity,long filesystem) {')
        (folder/'renderer.c').write_bytes(raw)
        (folder/'telemetry_core.h').write_bytes(source.provider_sources()['telemetry_core.h'])
        cls.binary=folder/'metrics'
        build=subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror','-I',str(folder),'-I',str(common.NATIVE),
            '-I',str(common.ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm'),
            str(common.ROOT/'tests/s22plus_resident_metrics_harness.c'),'-o',str(cls.binary)],capture_output=True,text=True,timeout=40)
        if build.returncode:raise AssertionError(build.stderr)

    def test_production_collectors_cross_601_900_hour_and_day_with_fresh_valid_samples(self):
        for source_index in (0,1):
            with self.subTest(source=source_index):
                result=subprocess.run([self.binary,str(source_index),'long'],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('samples=100000 ms=100000000',result.stderr)

    def test_cpu_selection_range_units_coverage_and_gauge_stop(self):
        for case in ('cpu-absent','cpu-duplicate','cpu-wrong-type','cpu-type-changed','cpu-malformed','cpu-range','cpu-negative','gauge-error','provider-overflow','log-backpressure'):
            with self.subTest(case=case):
                result=subprocess.run([self.binary,'1',case],capture_output=True,text=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('PASS',result.stdout+result.stderr)

    def test_cpu_allowlist_matches_exact_waipio_source_names(self):
        import re
        path=common.ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/qcom/proprietary/devicetree/qcom/waipio-thermal.dtsi'
        dt_names=set(re.findall(r'^\s*(cpu-[01]-[0-9]+)\s*\{',path.read_text(),re.M))
        selected=set(re.findall(r'"(cpu-[01]-[0-9]+)\\n"',source.read('collect.inc.c.in').decode()))
        self.assertEqual(selected,dt_names);self.assertEqual(len(selected),13)


if __name__=='__main__':unittest.main()
