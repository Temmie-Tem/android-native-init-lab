"""P351 actual C readiness and one-shot failure capture, with no device access."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='p351-readiness-')
        cls.addClassCleanup(cls.temp.cleanup)
        folder = Path(cls.temp.name)
        (folder / 's22plus_native_display_plan.h').write_text(
            '#define P350_DISPLAY_MODULE_COUNT 12U\n'
            'struct p350_display_module {const char *path; unsigned long long size; int display;};\n'
            'static const struct p350_display_module p350_display_modules[]={\n' +
            ''.join('{"/s22-display-modules/module%d",1,%d},\n' % (i, i == 11) for i in range(12)) + '};\n')
        cls.program = folder / 'test'
        subprocess.run(['cc', '-O1', '-Wall', '-Wextra', '-Werror', '-I', str(folder),
                        str(ROOT / 'tests/s22plus_native_display_ready_v2_harness.c'),
                        '-o', str(cls.program)], check=True, capture_output=True)

    def run_case(self, name):
        return subprocess.run([self.program, name], capture_output=True, text=True, timeout=5)

    def test_fresh_success_and_delayed_readiness(self):
        for name, scans in [('success', 2), ('delayed', 4), ('lost', 4)]:
            result = self.run_case(name)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(f'COUNTS loads=12 logs=0 scans={scans} nodes=1', result.stdout)
            self.assertEqual(result.stdout.count('DISPLAY_READY ready=1'), 1)

    def test_fail_closed_without_module_replay(self):
        for name, stage in [('timeout', 'drm-readiness'), ('duplicate', 'ready-regulator-duplicate'),
                            ('wrong-driver', 'ready-driver-binding'), ('wrong-dev', 'ready-drm-number')]:
            result = self.run_case(name)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn('FAIL ' + stage, result.stdout)
            self.assertIn('COUNTS loads=12 logs=1', result.stdout)
            self.assertIn('nodes=0', result.stdout)
            self.assertEqual(result.stdout.count('DISPLAY_KMSG_BEGIN'), 1)
            self.assertNotIn('DISPLAY_READY ready=1', result.stdout)
        self.assertIn('elapsed=15000', self.run_case('timeout').stdout)

    def test_sysfs_rejected_before_load(self):
        result = self.run_case('wrong-fs')
        self.assertEqual(result.returncode, 1)
        self.assertIn('COUNTS loads=0 logs=0 scans=0 nodes=0', result.stdout)

    def test_failed_log_read_is_not_retried(self):
        result = self.run_case('log-error')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.count('DISPLAY_KMSG_BEGIN'), 1)
        self.assertIn('bytes=0 errno=1 coverage=bounded-tail', result.stdout)
        self.assertIn('COUNTS loads=0 logs=1', result.stdout)

    def test_generated_white_renderer_real_drm_core(self):
        sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/analysis'))
        import s22plus_fyg8_p351_display_renderer as renderer
        from test_s22plus_native_display_h0 import HEADER_CANDIDATES
        headers = next((p for p in HEADER_CANDIDATES if (p / 'msm_drm.h').is_file()), None)
        if headers is None:
            self.skipTest('DRM UAPI headers required')
        folder = Path(self.temp.name)
        (folder / 'renderer.c').write_bytes(renderer.render())
        source = (ROOT / 'tests/s22plus_native_display_h0_harness.c').read_text().replace(
            '../workspace/public/src/native-init/s22plus_native_display_h0.c', str(folder / 'renderer.c'))
        (folder / 'drm.c').write_text(source)
        subprocess.run(['cc', '-O1', '-Wall', '-Wextra', '-Werror', '-D_DEFAULT_SOURCE',
                        '-I', str(headers), '-I', str(renderer.NATIVE), str(folder / 'drm.c'),
                        '-o', str(folder / 'drm')], check=True, capture_output=True)
        cases = ['success', 'resource-overflow', 'competing-plane', 'test-rejected',
                 'commit-error', 'wrong-token', 'wrong-crtc', 'bad-length', 'timeout']
        for case in cases:
            result = subprocess.run([folder / 'drm', case], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0 if case == 'success' else 1, result.stderr)
            self.assertEqual(result.stdout.count(b'DISPLAY_FLIP '), 10 if case == 'success' else 0)


if __name__ == '__main__':
    unittest.main()
