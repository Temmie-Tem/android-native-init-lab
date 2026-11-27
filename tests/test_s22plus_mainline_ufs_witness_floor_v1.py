"""UFS route witness floor: the 300 s dwell replaced by a 60 s guest-BOOTTIME floor."""
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
sys.path.insert(0, str(ROOT / 'workspace/public/src'))
import link_initramfs as builder
import s22plus_mainline_task_v1 as task
import s22plus_mainline_ufs_candidate_v2 as candidate
import s22plus_mainline_ufs_image_v1 as image

BEGIN = '/* ---- rendered dwell.h ---- */\n'
END = '/* ---- end of rendered dwell.h ---- */\n'


class CompositionTests(unittest.TestCase):
    def test_floor_renders_only_the_dwell_header(self):
        route, floor = builder.observer_source(True), builder.observer_source(True, True)
        self.assertEqual(route, builder.observer_source(True, False))
        self.assertIn('#include "dwell.h"\n', route)
        self.assertNotIn('#include "dwell.h"', floor)
        self.assertEqual(floor.count(BEGIN), 1)
        rendered = BEGIN + builder.dwell_header() + END
        self.assertEqual(floor.replace(rendered, '#include "dwell.h"\n'), route)

    def test_rendered_dwell_changes_only_the_two_comparisons(self):
        original = (builder.HERE / 'dwell.h').read_text()
        diff = [line for line in difflib.unified_diff(original.splitlines(), builder.dwell_header().splitlines(),
                                                      lineterm='', n=0)
                if line[:1] in '+-' and not line.startswith(('+++', '---'))]
        self.assertEqual(diff, [
            '+/* Witness floor composition: the 300 s dwell after the first response is',
            '+ * replaced by an absolute guest BOOTTIME floor. */',
            '+#define ML030_FLOOR_MS 60000U',
            '-    if (now < t0 + ML030_DWELL_MS || now >= deadline) return ETIMEDOUT;',
            '+    if (now < ML030_FLOOR_MS || now <= t0 || now >= deadline) return ETIMEDOUT;',
            '-        ml030_u64(next + 216) < t0 + ML030_DWELL_MS || now_ms() >= deadline) return EPROTO;',
            '+        ml030_u64(next + 216) < ML030_FLOOR_MS || ml030_u64(next + 216) <= t0 ||',
            '+        now_ms() >= deadline) return EPROTO;'])

    def test_floor_requires_the_route_composition_and_adopted_bytes(self):
        with self.assertRaisesRegex(ValueError, 'only in the route composition'):
            builder.observer_source(False, True)
        with self.assertRaisesRegex(ValueError, 'explicit route composition mode'):
            builder.observer_source(True, 1)
        with mock.patch.object(builder, 'DWELL_HEADER_SHA256', '0' * 64), \
                self.assertRaisesRegex(ValueError, 'dwell header differs'):
            builder.observer_source(True, True)
        with self.assertRaisesRegex(ValueError, 'witness floor requires the route'):
            builder.build(Path('/nonexistent'), Path('/nonexistent'), Path('/nonexistent'), vm=False,
                          pre_effect_return=True, witness_floor=True)


HARNESS = r'''
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include "protocol.h"
static const unsigned char canary_id[32] = {1};
static const unsigned char canary_key[32] = {2};
static uint64_t deadline, fake_now, t0_env, query_env, next_env;
static uint8_t base_g[G0Q_RESPONSE_SIZE];
static void put64(uint8_t *p, uint64_t v) { g_put32(p, (uint32_t)v); g_put32(p + 4, (uint32_t)(v >> 32)); }
static uint64_t now_ms(void) { return fake_now; }
static int transfer(int fd, void *buffer, size_t length, int writing) {
    (void)fd;
    if (writing) { printf("WITNESS\n"); exit(0); }
    uint8_t *f = buffer;
    memset(f, 0, length); memcpy(f, "G030ASK1", 8); memcpy(f + 8, canary_id, 32);
    memcpy(f + 40, base_g + 40, 32); memset(f + 72, 0x55, 32); memcpy(f + 104, base_g + 72, 16);
    put64(f + 120, t0_env);
    g_tag(f + 136, canary_key, canary_id, 16, f, 136);
    fake_now = query_env;
    return 0;
}
static int proof(const uint8_t nonce[32], uint8_t response[G0Q_RESPONSE_SIZE]) {
    (void)nonce; memcpy(response, base_g, G0Q_RESPONSE_SIZE); put64(response + 216, next_env); return 0;
}
#include "DWELL"
int main(void) {
    t0_env = strtoull(getenv("T0"), NULL, 10); query_env = strtoull(getenv("QUERY"), NULL, 10);
    next_env = strtoull(getenv("NEXT"), NULL, 10);
    memset(base_g + 40, 0x11, 32); memset(base_g + 72, 0x22, 144); put64(base_g + 216, t0_env);
    fake_now = t0_env + 1;
    int rc = ml030_dwell(3, base_g);
    printf("%s\n", rc == ETIMEDOUT ? "ETIMEDOUT" : rc == EPROTO ? "EPROTO" : rc == EACCES ? "EACCES" : "OTHER");
    return 0;
}
'''


class GuestFloorTests(unittest.TestCase):
    """The rendered and the adopted dwell run against the same stub harness."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); folder = Path(cls.tmp.name)
        (folder / 'floor-dwell.h').write_text(builder.dwell_header())
        cls.exe = {}
        for name, header in (('floor', str(folder / 'floor-dwell.h')), ('adopted', str(builder.HERE / 'dwell.h'))):
            source = folder / f'{name}.c'; source.write_text(HARNESS.replace('DWELL', header))
            cls.exe[name] = folder / name
            subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                            '-Wno-unused-const-variable', '-DCANARY_DOWNLOAD_RAM', '-DCANARY_H0_VM',
                            '-I', str(builder.CANARY), '-I', str(builder.HERE), str(source), '-o', str(cls.exe[name])],
                           check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_dwell(self, name, t0, query, after):
        env = dict(os.environ, T0=str(t0), QUERY=str(query), NEXT=str(after))
        return subprocess.run([str(self.exe[name])], capture_output=True, text=True, check=True,
                              env=env).stdout.strip()

    def test_challenge_before_the_floor_is_refused(self):
        self.assertEqual(self.run_dwell('floor', 7212, 59999, 60000), 'ETIMEDOUT')
        self.assertEqual(self.run_dwell('floor', 7212, 60000, 60000), 'WITNESS')

    def test_a_late_first_response_still_needs_a_later_challenge(self):
        self.assertEqual(self.run_dwell('floor', 65000, 65000, 65001), 'ETIMEDOUT')
        self.assertEqual(self.run_dwell('floor', 65000, 65001, 65001), 'WITNESS')

    def test_the_witness_uptime_must_reach_the_floor_and_pass_the_first(self):
        self.assertEqual(self.run_dwell('floor', 7212, 60000, 59999), 'EPROTO')
        self.assertEqual(self.run_dwell('floor', 65000, 65001, 65000), 'EPROTO')

    def test_the_absolute_ceiling_is_unchanged(self):
        self.assertEqual(self.run_dwell('floor', 7212, 540000, 540000), 'ETIMEDOUT')
        self.assertEqual(self.run_dwell('floor', 7212, 539999, 539999), 'WITNESS')

    def test_the_adopted_dwell_keeps_300_seconds(self):
        self.assertEqual(self.run_dwell('adopted', 7212, 60000, 60000), 'ETIMEDOUT')
        self.assertEqual(self.run_dwell('adopted', 7212, 307211, 307212), 'ETIMEDOUT')
        self.assertEqual(self.run_dwell('adopted', 7212, 307212, 307212), 'WITNESS')


class HostGapTests(unittest.TestCase):
    def setUp(self):
        import s22plus_mainline_ufs_access_v1 as access
        self.access = access

    def gap(self, floor, t0):
        with mock.patch.object(self.access, 'witness_floor_for', return_value=floor):
            return self.access.witness_gap_ns(dict(N={}), t0)

    def test_without_the_floor_the_gap_stays_300_seconds(self):
        self.assertEqual(self.gap(False, 7212), 300_000_000_000)
        self.assertEqual(self.gap(False, None), 300_000_000_000)

    def test_the_floor_gap_reaches_60_seconds_with_margin(self):
        self.assertEqual(self.gap(True, 7212), (60_000 - 7212) * 1_000_000 + 2_000_000_000)
        self.assertEqual(self.gap(True, 59_500), 2_500_000_000)
        self.assertEqual(self.gap(True, 100_000), 1_000_000_000)

    def test_the_floor_gap_needs_a_valid_first_uptime(self):
        for t0 in (None, 0, 120_000, 7212.0, True):
            with self.subTest(t0=t0), self.assertRaisesRegex(ValueError, 'witness floor first uptime'):
                self.gap(True, t0)


class CapabilityTests(unittest.TestCase):
    def fixed(self, **extra):
        value = {name: None for name in candidate.FIXED_FIELDS}
        value.update(report_version=13, **extra)
        return value

    def test_floor_is_exact_and_route_only(self):
        self.assertTrue(candidate.witness_floor(self.fixed(usb_route=True, witness_floor_ms=60000)))
        for extra in (dict(witness_floor_ms=60000), dict(usb_route=True, witness_floor_ms=60000.0),
                      dict(usb_route=True, witness_floor_ms=True), dict(usb_route=True, witness_floor_ms=30000),
                      dict(usb_route=True)):
            with self.subTest(extra=extra):
                self.assertFalse(candidate.witness_floor(self.fixed(**extra)))

    def test_fixed_binding_rejects_a_floor_outside_the_route_capability(self):
        cases = ((task.CAPABILITY_SCOPE, self.fixed(witness_floor_ms=60000)),
                 (task.ROUTE_CAPABILITY_SCOPE, self.fixed(usb_route=True, witness_floor_ms=60000.0)),
                 (task.ROUTE_CAPABILITY_SCOPE, self.fixed(usb_route=True, witness_floor_ms=300000)),
                 (task.ROUTE_CAPABILITY_SCOPE, self.fixed(usb_route=True, witness_floor_ms=None)))
        for scope, value in cases:
            with self.subTest(scope=scope, floor=value.get('witness_floor_ms')), \
                    self.assertRaisesRegex(ValueError, 'fixed capability fields or report mode'):
                candidate.fixed_binding(dict(scope=scope, fixed=value))
        # An exact floor passes the field check and fails only later on the absent artifacts.
        for value in (self.fixed(usb_route=True, witness_floor_ms=60000), self.fixed(usb_route=True)):
            with self.subTest(floor='witness_floor_ms' in value):
                with self.assertRaises(Exception) as caught:
                    candidate.fixed_binding(dict(scope=task.ROUTE_CAPABILITY_SCOPE, fixed=value))
                self.assertNotIn('fixed capability fields or report mode', str(caught.exception))

    def test_only_an_exact_route_floor_declaration_changes_the_recipe(self):
        manifest, key = dict(inputs=[]), b'k' * 32
        route = image.expected_recipe(manifest, key, dict(report_version=13, usb_route=True))
        floor = image.expected_recipe(manifest, key, dict(report_version=13, usb_route=True, witness_floor_ms=60000))
        self.assertEqual(floor, dict(route, witness_floor_ms=60000))
        for declaration in (dict(report_version=13, witness_floor_ms=60000),
                            dict(report_version=13, usb_route=True, witness_floor_ms=60000.0),
                            dict(report_version=13, usb_route=True, witness_floor_ms=True)):
            with self.subTest(declaration=declaration):
                self.assertNotIn('witness_floor_ms', image.expected_recipe(manifest, key, declaration))
        self.assertFalse(image.recipe_matches(dict(floor, witness_floor_ms=60000.0), floor))
        self.assertFalse(image.recipe_matches(route, floor))

    def test_older_images_never_select_the_floor(self):
        self.assertFalse(image.witness_floor_for(dict(schema='s22plus-mainline-image-v1')))


class WireFloorTests(unittest.TestCase):
    """The host wire parser and permit builder apply the same floor (ML054: t0 = 7212 ms)."""
    import link_wire as wire
    key, identity, boot = b'k' * 32, b'i' * 32, b'b' * 16
    first, second, t0 = b'\x01' * 32, b'\x02' * 32, 7212

    def signed(self, t1, floor=None):
        return self.wire.frame(b'G030WIT1', 17, self.key, self.identity, self.first, self.second,
                               self.boot, self.t0, t1, floor_ms=floor)

    def parse(self, raw, floor=None):
        return self.wire.witness(raw, self.key, self.identity, self.first, self.second, self.boot,
                                 self.t0, floor_ms=floor)

    def test_floor_admits_a_witness_after_60_seconds(self):
        for t1 in (60000, 62000, 539999):
            with self.subTest(t1=t1):
                self.assertEqual(self.parse(self.signed(t1, 60000), 60000), t1)
                self.wire.frame(b'G030GO01', 18, self.key, self.identity, self.first, self.second,
                                self.boot, self.t0, t1, floor_ms=60000)

    def test_floor_rejects_early_late_and_unfloored_witnesses(self):
        unfloored = self.signed(self.t0 + 300000)
        self.assertEqual(self.parse(unfloored), self.t0 + 300000)
        for t1 in (59999, 540000):
            with self.subTest(t1=t1), self.assertRaisesRegex(ValueError, 'late uptime fields'):
                self.signed(t1, 60000)
        # A floor witness is still rejected by the unfloored 300 s parser and builder.
        raw = self.signed(62000, 60000)
        with self.assertRaisesRegex(ValueError, 'late uptime fields'):
            self.parse(raw)
        with self.assertRaisesRegex(ValueError, 'late uptime fields'):
            self.wire.frame(b'G030GO01', 18, self.key, self.identity, self.first, self.second,
                            self.boot, self.t0, 62000)

    def test_floor_never_admits_a_witness_not_later_than_the_first(self):
        early = self.wire.frame(b'G030ASK1', 16, self.key, self.identity, self.first, self.second,
                                self.boot, 61000, 0, floor_ms=60000)
        self.assertEqual(len(early), self.wire.HEADER.size + 32)
        with self.assertRaisesRegex(ValueError, 'late uptime fields'):
            self.wire.frame(b'G030WIT1', 17, self.key, self.identity, self.first, self.second,
                            self.boot, 61000, 61000, floor_ms=60000)

    def test_only_the_exact_floor_value_is_accepted(self):
        for floor in (60000.0, True, 30000, 300000, '60000'):
            with self.subTest(floor=floor), self.assertRaisesRegex(ValueError, 'late witness floor'):
                self.signed(62000, floor)


if __name__ == '__main__':
    unittest.main()
