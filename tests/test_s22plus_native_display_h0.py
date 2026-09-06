"""Actual fixed renderer against a host fake DRM; never opens a device."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER_CANDIDATES = (
    ROOT / 'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm',
    Path('/usr/include/drm'),
    Path('/usr/include/libdrm'),
)


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc = shutil.which('cc')
        headers = next((p for p in HEADER_CANDIDATES if (p / 'msm_drm.h').is_file()), None)
        if not cc or headers is None:
            raise unittest.SkipTest('host C compiler and DRM UAPI headers required')
        cls.directory = tempfile.TemporaryDirectory(prefix='s22-display-fake-')
        cls.addClassCleanup(cls.directory.cleanup)
        cls.program = Path(cls.directory.name) / 'renderer-test'
        subprocess.run([
            cc, '-O1', '-Wall', '-Wextra', '-Werror', '-D_DEFAULT_SOURCE',
            '-I', str(headers), str(ROOT / 'tests/s22plus_native_display_h0_harness.c'),
            '-o', str(cls.program),
        ], check=True, capture_output=True)

    def test_current_panel_parameter_binding(self):
        headers = next(p for p in HEADER_CANDIDATES if (p / 'msm_drm.h').is_file())
        folder = Path(self.directory.name)
        # The plan is unused by this harness: only the pure parser is called.
        (folder / 's22plus_native_display_plan.h').write_text(
            '#define P350_DISPLAY_MODULE_COUNT 1U\n'
            'struct p350_display_module {const char *path; unsigned long long size; int display;};\n'
            'static const struct p350_display_module p350_display_modules[]={{"unused",1,1}};\n')
        binary = folder / 'parameters'
        subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-I',str(headers),
            '-I',str(folder),str(ROOT/'tests/s22plus_native_display_parameters_harness.c'),
            '-o',str(binary)],check=True,capture_output=True)
        display='msm_drm.dsi_display0=ss_dsi_panel_S6E3FAC_AMB655AY01_FHD:'
        for key,value in [('msm_drm.lcd_id','123abc'),('lcd_id','0x123ABC')]:
            result=subprocess.run([binary,display+' '+key+'='+value],capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,b'dsi_display0=ss_dsi_panel_S6E3FAC_AMB655AY01_FHD: lcd_id=123abc\n')
        cases=[display,display+' msm_drm.lcd_id=123abg',
            display+' lcd_id=ffffff',display+' lcd_id=123abc msm_drm.lcd_id=123abc',
            display+' lcd_id=123abc msm_drm.dsi_display1=x',
            display+' lcd_id=123abc androidboot.boot_recovery=1']
        for command in cases:
            result=subprocess.run([binary,command],capture_output=True,timeout=5)
            self.assertEqual(result.returncode,1,result.stderr)
            self.assertNotIn(b'DISPLAY_LOAD',result.stdout)

    def test_ten_completed_frames_then_disable(self):
        result = subprocess.run([self.program, 'success'], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count(b'DISPLAY_FLIP '), 10)
        self.assertIn(b'completed_frames=10 disabled=1\n', result.stdout)

    def test_rejects_uncertain_or_conflicting_state(self):
        cases = {
            'resource-overflow': 'resources-bound',
            'competing-plane': 'competing-plane',
            'test-rejected': 'test-only',
            'commit-error': 'commit',
            'wrong-token': 'event-binding',
            'wrong-crtc': 'event-binding',
            'bad-length': 'event-length',
            'timeout': 'flip-poll',
        }
        for case, stage in cases.items():
            with self.subTest(case=case):
                result = subprocess.run([self.program, case], capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(f'stage={stage} '.encode(), result.stderr)
                self.assertNotIn(b'DISPLAY_DONE', result.stdout)
                self.assertNotIn(b'DISPLAY_FLIP', result.stdout)


if __name__ == '__main__':
    unittest.main()
