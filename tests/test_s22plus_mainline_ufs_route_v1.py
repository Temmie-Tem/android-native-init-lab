"""UFS V13 route composition: observer insertions, scope selection and no cue."""
from pathlib import Path
import difflib
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/host_tools'))
sys.path.insert(0, str(ROOT / 'workspace/public/src/mainline/s22plus_ufs_link_h0'))
import link_initramfs as builder
import s22plus_mainline_task_v1 as task
import s22plus_mainline_ufs_candidate_v2 as candidate
from s22plus_native_records_v3 import publish


class ObserverCompositionTests(unittest.TestCase):
    def test_route_adds_the_rendered_header_and_the_three_route_insertions(self):
        plain, route = builder.observer_source(), builder.observer_source(True)
        self.assertEqual(plain, builder.observer_source(False))
        header = builder.route_header()
        begin = '/* ---- rendered max77705-usb-route.h ---- */\n'
        end = '/* ---- end of rendered max77705-usb-route.h ---- */\n'
        self.assertEqual(route.count(begin), 1)
        self.assertIn(begin + header + end, route)
        outside = route.replace(begin + header + end, '')
        diff = [line for line in difflib.unified_diff(plain.splitlines(), outside.splitlines(), lineterm='', n=0)
                if line[:1] in '+-' and not line.startswith(('+++', '---'))]
        self.assertEqual(sorted(diff), sorted([
            '+/* No tick starts in the last second of the window. */',
            '+#define MX_TICK_GUARD_MS 1000U',
            '+    mx_begin();',
            '-        struct pollfd p={fd,POLLIN,0};int rc=poll(&p,1,(int)(deadline-now));',
            '+        struct pollfd p={fd,POLLIN,0};uint64_t wait=deadline-now;if(wait>MX_TICK_MS)wait=MX_TICK_MS;',
            '+        int rc=poll(&p,1,(int)wait);',
            '-        if(!rc) {error=ETIMEDOUT;break;}',
            '+        if(!rc) {uint64_t tick=now_ms();',
            '+            if(tick!=UINT64_MAX&&tick<deadline&&deadline-tick>=MX_TICK_GUARD_MS)mx_tick();',
            '+            continue;}']))
        # The timer child is armed before the first MAX77705 access.
        self.assertLess(route.index('recovery_begin()'), route.index('mx_begin();'))
        # The V13 response layout is unchanged: no route record is filled.
        self.assertNotIn('mx_fill(', outside)
        self.assertNotIn('mx_final();', outside)
        self.assertNotIn('#include "max77705-usb-route.h"', route)

    def test_rendered_header_adds_only_the_dispatch_deadline_check(self):
        original = (builder.CANARY / builder.ROUTE_HEADER).read_text()
        diff = [line for line in difflib.unified_diff(original.splitlines(), builder.route_header().splitlines(),
                                                      lineterm='', n=0)
                if line[:1] in '+-' and not line.startswith(('+++', '---'))]
        self.assertEqual(diff, [
            '+    /* V13 route composition: never dispatch on a failed clock read or at',
            '+     * or after the end of the 120 s first-connection window. */',
            '+    if (dispatch == UINT64_MAX || dispatch >= deadline) {',
            '+        mx.gate = MX_GATE_STALE;',
            '+        return;',
            '+    }'])


class DispatchDeadlineTests(unittest.TestCase):
    """The rendered header runs in the adopted route fake harness."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        fake = (builder.CANARY / 'max77705_route_fake.c').read_text()
        anchors = ('#include "max77705-usb-route.h"\n', 'static uint64_t mx_now(void) { return fake_ms; }\n',
                   '    scenario = argv[1];\n',
                   '    for (unsigned i = 0; i < MX_RECORD_SIZE; i++) printf("%02x", rec[i]);\n')
        for anchor in anchors:
            assert fake.count(anchor) == 1, anchor
        fake = fake.replace(anchors[0], 'static uint64_t deadline;\n' + builder.route_header())
        fake = fake.replace(anchors[1], 'static uint64_t clock_fail_at = UINT64_MAX;\n'
                            'static uint64_t mx_now(void) { return fake_ms >= clock_fail_at ? UINT64_MAX : fake_ms; }\n')
        fake = fake.replace(anchors[2], anchors[2] + '    deadline = strtoull(getenv("G0Q_DEADLINE_MS"), NULL, 10);\n'
                            '    if (getenv("G0Q_CLOCK_FAIL_AT")) clock_fail_at = strtoull(getenv("G0Q_CLOCK_FAIL_AT"), NULL, 10);\n')
        fake = fake.replace(anchors[3], '    printf("gate=%u stale=%u written=%llu\\n", mx.gate, MX_GATE_STALE, (unsigned long long)written_at);\n' + anchors[3])
        source = Path(cls.tmp.name) / 'fake.c'; source.write_text(fake)
        cls.exe = Path(cls.tmp.name) / 'fake'
        subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O1', '-I', str(builder.CANARY),
                        str(source), '-o', str(cls.exe)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_fake(self, deadline, clock_fail_at=None):
        env = dict(os.environ, G0Q_DEADLINE_MS=str(deadline))
        if clock_fail_at is not None:
            env['G0Q_CLOCK_FAIL_AT'] = str(clock_fail_at)
        lines = subprocess.run([str(self.exe), 'pass'], capture_output=True, text=True, check=True, env=env).stdout.splitlines()
        meta = dict(item.split('=') for item in lines[0].split())
        gate = dict(item.split('=') for item in lines[1].split())
        self.written = int(gate['written'])
        return int(meta['route_bus_writes']), int(gate['gate']), int(gate['stale'])

    def test_write_inside_the_window_is_unchanged(self):
        writes, gate, stale = self.run_fake(120000)
        self.assertEqual(writes, 1)
        self.assertNotEqual(gate, stale)

    def test_a_dispatch_at_or_after_the_window_end_is_refused(self):
        writes_ok, *_ = self.run_fake(120000)
        dispatch = self.written
        self.assertEqual(writes_ok, 1)
        self.assertGreater(dispatch, 0)
        # One millisecond after the dispatch time the write still goes; at it, never.
        self.assertEqual(self.run_fake(dispatch + 1)[0], 1)
        for deadline in (dispatch, dispatch - 1):
            with self.subTest(deadline=deadline):
                writes, gate, stale = self.run_fake(deadline)
                self.assertEqual((writes, gate), (0, stale))

    def test_a_failed_clock_read_at_dispatch_is_refused(self):
        writes, gate, stale = self.run_fake(120000, clock_fail_at=5000)
        self.assertEqual(writes, 0)

    def test_route_header_is_the_adopted_bytes(self):
        with mock.patch.object(builder, 'ROUTE_HEADER_SHA256', '0' * 64), \
                self.assertRaisesRegex(ValueError, 'route observer header differs'):
            builder.observer_source(True)
        with self.assertRaisesRegex(ValueError, 'explicit route composition mode'):
            builder.observer_source(1)

    def test_route_requires_the_board_v13_observer(self):
        for kwargs in (dict(vm=True, pre_effect_return=True), dict(vm=False, pre_effect_return=False)):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, 'route composition requires'):
                builder.build(Path('/nonexistent'), Path('/nonexistent'), Path('/nonexistent'), route=True, **kwargs)


class ScopeSelectionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.dir = Path(tmp.name)

    def image(self, scope):
        cap = publish(self.dir / f'cap-{scope}.json', dict(scope=scope))
        return dict(schema=task.IMAGE_V2, capability=cap)

    def test_route_scope_is_read_from_the_bound_capability(self):
        self.assertTrue(task.ufs_route(self.image(task.ROUTE_CAPABILITY_SCOPE)))
        self.assertFalse(task.ufs_route(self.image(task.CAPABILITY_SCOPE)))
        self.assertFalse(task.ufs_route(dict(schema=task.IMAGE_V2)))
        self.assertFalse(task.ufs_route(dict(schema='s22plus-mainline-image-v1')))

    def test_route_sources_are_added_only_for_the_route_scope(self):
        base = {str(p.relative_to(ROOT)) for p in task.source_paths(ROOT, image=dict(schema=task.IMAGE_V2))}
        route = {str(p.relative_to(ROOT)) for p in task.source_paths(ROOT, image=dict(schema=task.IMAGE_V2), route=True)}
        self.assertEqual(route - base, set(task.ROUTE_SOURCES))
        self.assertEqual(base, {str(p.relative_to(ROOT)) for p in
                                task.source_paths(ROOT, image=self.image(task.CAPABILITY_SCOPE))})
        self.assertEqual(route, {str(p.relative_to(ROOT)) for p in
                                 task.source_paths(ROOT, image=self.image(task.ROUTE_CAPABILITY_SCOPE))})

    def test_fixed_marker_must_match_the_scope(self):
        fixed = {name: None for name in candidate.FIXED_FIELDS}
        fixed['report_version'] = 13
        cases = ((task.CAPABILITY_SCOPE, dict(fixed, usb_route=True)),
                 (task.ROUTE_CAPABILITY_SCOPE, fixed),
                 (task.ROUTE_CAPABILITY_SCOPE, dict(fixed, usb_route=False)),
                 (task.ROUTE_CAPABILITY_SCOPE, dict(fixed, usb_route=True, report_version=12)))
        for scope, value in cases:
            with self.subTest(scope=scope, value={k: value[k] for k in ('report_version', 'usb_route') if k in value}):
                with self.assertRaisesRegex(ValueError, 'fixed capability fields or report mode'):
                    candidate.fixed_binding(dict(scope=scope, fixed=value))
        self.assertTrue(candidate.route_scope(dict(fixed, usb_route=True)))
        self.assertFalse(candidate.route_scope(fixed))


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.dir = Path(tmp.name)

    def test_automatic_return_selects_the_route_scope_like_v13(self):
        import s22plus_mainline_auto_recovery_v1 as auto
        for scope in (task.CAPABILITY_SCOPE, task.ROUTE_CAPABILITY_SCOPE):
            cap = publish(self.dir / f'cap-{scope}.json', dict(schema=task.CAPABILITY_SCHEMA, scope=scope,
                                                             fixed=dict(report_version=13)))
            request = dict(operation='mainline-ram', N=dict(schema=task.IMAGE_V2, capability=cap))
            with self.subTest(scope=scope):
                self.assertTrue(auto.selected(request))
        other = publish(self.dir / 'cap-other.json', dict(schema=task.CAPABILITY_SCHEMA, scope='OTHER',
                                                          fixed=dict(report_version=13)))
        with self.assertRaisesRegex(ValueError, 'automatic recovery capability scope'):
            auto.selected(dict(operation='mainline-ram', N=dict(schema=task.IMAGE_V2, capability=other)))

    def test_original_a_recovery_skips_only_the_guest_route_header(self):
        self.assertEqual(set(task.ROUTE_SOURCES) - set(task.ROUTE_GUEST_SOURCES), {task.ROUTE_CAPABILITY_POLICY})
        self.assertNotIn(task.ROUTE_CAPABILITY_POLICY, task.ROUTE_GUEST_SOURCES)


class NoCueTests(unittest.TestCase):
    def test_cue_tool_refuses_the_route_scope_and_keeps_v13(self):
        import s22plus_mainline_attach_cue_v1 as cue
        request = dict(N=dict(ufs_link=True))
        with mock.patch.object(task, 'ufs_route', return_value=True), \
                self.assertRaisesRegex(ValueError, 'UFS route scope has no attach cue'):
            cue.observation_action(None, request)
        with mock.patch.object(task, 'ufs_route', return_value=False):
            self.assertEqual(cue.observation_action(None, request), 'mainline-download')


if __name__ == '__main__':
    unittest.main()
