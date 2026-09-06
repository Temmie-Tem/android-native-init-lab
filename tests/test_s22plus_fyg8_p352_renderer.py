"""Real generated renderer against source-derived vendor responses; no device I/O."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'workspace/public/src/scripts/analysis'),
               str(ROOT / 'workspace/public/src/scripts/revalidation')]
import s22plus_fyg8_p352_display_renderer as renderer
import s22plus_fyg8_display_kms_contract_h0 as kms
import s22plus_fyg8_p352_stock_candidate_build as builder
import s22plus_fyg8_p352_research_shell_observer as observer


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = builder.qualified_kms_contract()
        cls.directory = tempfile.TemporaryDirectory(prefix='p352-renderer-')
        cls.addClassCleanup(cls.directory.cleanup)
        cls.folder = Path(cls.directory.name)
        cls.headers = ROOT / 'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel/include/uapi/drm'
        cls.modes = cls.contract['results'][0]['modes']
        # All applicable DTs independently derive the same nominal probe list.
        for row in cls.contract['results']:
            if row['modes'] != cls.modes:
                raise AssertionError('applicable DT nominal modes differ')
        initializers = []
        for mode in cls.modes:
            initializers.append('{' + ','.join('.' + k + '=' + json.dumps(v) for k, v in mode.items()) + '}')
        cls.mode_c = ',\n'.join(initializers)
        base = (ROOT / 'tests/s22plus_native_display_h0_harness.c').read_text()
        base = base.replace('0123456789abcdef0123456789abcdef', observer.RUN_ID_HEX)
        base = base.replace('#include "../workspace/public/src/native-init/s22plus_native_display_h0.c"', '#include "renderer.c"')
        base = base.replace('static int pending;', 'static int pending;\nstatic const struct drm_mode_modeinfo source_modes[]={' + cls.mode_c + '};')
        base = base.replace('memcpy(q->name,"msm",4);q->name_len=3;',
                            'memcpy(q->name,"' + cls.contract['driver_name'] + '",8);q->name_len=7;'
                            'if(!strcmp(scenario,"wrong-driver"))q->name[0]=\'x\';'
                            'if(!strcmp(scenario,"driver-length"))q->name_len=1000;')
        start = base.index('  if(q->count_modes&&q->modes_ptr)')
        end = base.index('return 0;}', start) + len('return 0;}')
        base = base[:start] + '''  unsigned count=sizeof(source_modes)/sizeof(source_modes[0]);
  struct drm_mode_modeinfo modes[32];memcpy(modes,source_modes,sizeof(source_modes));
  unsigned selected=0;for(unsigned i=0;i<count;i++)if(!strcmp(modes[i].name,"1080x2340x30xcmdHS"))selected=i;
  if(!strcmp(scenario,"duplicate-mode"))modes[count++]=modes[selected];
  if(!strcmp(scenario,"missing-mode"))modes[selected].vrefresh=29;
  if(!strcmp(scenario,"mode-clock"))modes[selected].clock++;
  if(!strcmp(scenario,"mode-name"))strcpy(modes[selected].name,"1080x2340x30xcmdPHS");
  if(!strcmp(scenario,"mode-unterminated"))memset(modes[selected].name,'x',sizeof(modes[selected].name));
  if(!strcmp(scenario,"filtered")){modes[0]=modes[selected];count=1;}
  if(!strcmp(scenario,"preferred"))modes[selected].type=DRM_MODE_TYPE_PREFERRED;
  if(q->count_modes&&q->modes_ptr){assert(q->count_modes>=count);memcpy((void *)(uintptr_t)q->modes_ptr,modes,count*sizeof(modes[0]));}
  if(q->count_encoders&&q->encoders_ptr)((uint32_t *)(uintptr_t)q->encoders_ptr)[0]=40;
  q->count_modes=count;q->count_encoders=1;q->connector_type=DRM_MODE_CONNECTOR_DSI;q->connection=1;return 0;}''' + base[end:]
        base = base.replace('strcpy(q->name,pn[q->prop_id]);',
                            'strcpy(q->name,pn[q->prop_id]);if(!strcmp(scenario,"missing-property")&&q->prop_id==12)strcpy(q->name,"OTHER");')
        base = base.replace('q->offset=4096;', 'q->offset=!strcmp(scenario,"map-offset")?4097:4096;')
        base = base.replace('q->pixel_format==DRM_FORMAT_XRGB8888',
                            'q->pixel_format==DRM_FORMAT_XRGB8888&&q->pitches[0]==4352&&q->offsets[0]==0&&q->flags==0')
        base = base.replace('assert(!strcmp(scenario,"success")&&',
                            'assert((!strcmp(scenario,"success")||!strcmp(scenario,"filtered")||!strcmp(scenario,"preferred"))&&')
        base = base.replace('assert(f==7);va_list ap;',
                            'assert(f==7);fprintf(stderr,"H0_CALL op=%lu\\n",op);va_list ap;')
        (cls.folder / 'fixture.c').write_text(base)
        cls.programs = {}
        for version, code in [('p351', renderer.predecessor.render()),
                              ('name-only', renderer.predecessor.render().replace(b'!strcmp(name,"msm")', b'!strcmp(name,"msm_drm")')),
                              ('p352', renderer.render())]:
            (cls.folder / 'renderer.c').write_bytes(code)
            binary = cls.folder / version
            subprocess.run(['cc', '-O1', '-Wall', '-Wextra', '-Werror', '-D_DEFAULT_SOURCE',
                            '-I', str(cls.headers), '-I', str(ROOT / 'workspace/public/src/native-init'),
                            str(cls.folder / 'fixture.c'), '-o', str(binary)], check=True, capture_output=True)
            cls.programs[version] = binary

    def run_case(self, version, scenario):
        return subprocess.run([self.programs[version], scenario], capture_output=True, timeout=10)

    def test_source_producer_reproduces_both_old_assumptions(self):
        for version, stage in [('p351', 'driver-name'), ('name-only', 'mode-selection')]:
            result = self.run_case(version, 'success')
            self.assertEqual(result.returncode, 1)
            self.assertIn(('stage=' + stage + ' ').encode(), result.stderr)
            self.assertNotIn(b'DISPLAY_FLIP', result.stdout)

    def test_source_modes_filtered_subset_and_preference(self):
        for case in ('success', 'filtered', 'preferred'):
            result = self.run_case('p352', case)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count(b'DISPLAY_FLIP '), 10)
            self.assertIn(b'completed_frames=10 disabled=1', result.stdout)
            self.assertNotIn(b'DISPLAY_DIAG', result.stderr)
            expected = observer.display_output(20, dict(mdp=1, dsi=1, elapsed_ms=2, scans=2))
            self.assertEqual(result.stdout, expected[expected.index(b'DISPLAY_FLIP '):])

    def test_failure_paths_never_complete_or_retry(self):
        cases = {'wrong-driver':'driver-name', 'driver-length':'driver-name',
                 'duplicate-mode':'mode-selection', 'missing-mode':'mode-selection',
                 'mode-clock':'mode-selection', 'mode-name':'mode-selection',
                 'mode-unterminated':'mode-selection', 'missing-property':'missing-property',
                 'map-offset':'map-offset-bound', 'resource-overflow':'resources-bound',
                 'competing-plane':'competing-plane', 'test-rejected':'test-only',
                 'commit-error':'commit', 'wrong-token':'event-binding',
                 'wrong-crtc':'event-binding', 'bad-length':'event-length', 'timeout':'flip-poll'}
        for case, stage in cases.items():
            with self.subTest(case=case):
                result = self.run_case('p352', case)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(('stage=' + stage + ' ').encode(), result.stderr)
                self.assertEqual(result.stderr.count(b'DISPLAY_FAIL '), 1)
                self.assertIn(b'DISPLAY_DIAG ioctl=', result.stderr)
                self.assertLess(len(result.stderr), 16384)
                self.assertNotIn(b'DISPLAY_FLIP', result.stdout)
                self.assertNotIn(b'DISPLAY_DONE', result.stdout)
        result = self.run_case('p352', 'missing-property')
        self.assertIn(b'property=CRTC_H', result.stderr)
        self.assertIn(b'driver_length=7 driver_hex=6d736d5f64726d', result.stderr)


if __name__ == '__main__':
    unittest.main()
