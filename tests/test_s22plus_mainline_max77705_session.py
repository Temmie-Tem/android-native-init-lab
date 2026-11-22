"""MAX77705 readout and recovery regressions for the dormant mainline RAM variant."""
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_mainline_access_v1 as access
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_max77705_v1 as mx
import s22plus_mainline_session_v1 as session
import s22plus_mainline_task_v1 as task
from s22plus_native_records_v3 import pin, publish


class Max77705SessionTests(unittest.TestCase):
    def setUp(self):
        self.image = {'schema': profile.MX_SCHEMA}
        self.request = {'N': self.image, 'operation': 'mainline-ram'}

    @staticmethod
    def cue_review(request):
        return {'review': {'path': str(ROOT / profile.MX_REVIEW)}}

    def proof(self, verdict, **record):
        return dict(status=profile.MX_STATUS, runtime_schema=profile.MX_WIRE_SCHEMA, subject='max77705',
                    max77705_verdict=verdict, max77705=dict(dict(adapter='ok', commands=3, io_errors=0,
                    initial_uic_valid=True, initial_uic_bits=['APCmdResI'], events_total=0, events=[]), **record))

    def test_authenticated_verdicts_and_missing_response(self):
        for verdict in mx.OBSERVED:
            with self.subTest(verdict=verdict), patch.object(access, 'rederive', return_value={'proof': self.proof(verdict), 'attach': {'fixture': 'closure'}}):
                result = session.terminal(None, self.request, recovered=False)
                self.assertEqual(result['max77705_verdict'], verdict)
                self.assertEqual(result['status'], 'OBSERVED_MAX77705_USB_SWITCH')
                self.assertTrue(result['authenticated_usb'] and result['mainline_pid1'])
                self.assertTrue(result['physical_return_requested'])
                self.assertEqual(result['attach_closure'], {'fixture': 'closure'})
        absent = self.proof('NO_PROOF_ADAPTER_ABSENT', adapter='adapter-absent', commands=0)
        with patch.object(access, 'rederive', return_value={'proof': absent, 'attach': {'fixture': 'closure'}}):
            result = session.terminal(None, self.request, recovered=True)
        self.assertEqual(result['status'], 'MAX77705_OBSERVATION_INCONCLUSIVE')
        self.assertEqual((result['max77705_adapter'], result['max77705_commands']), ('adapter-absent', 0))
        self.assertTrue(result['authenticated_usb'])
        with patch.object(access, 'rederive', side_effect=FileNotFoundError):
            result = session.terminal(None, self.request, recovered=True)
        self.assertIsNone(result['max77705_verdict'])
        self.assertEqual(result['status'], 'NO_PROOF')
        self.assertFalse(result['authenticated_usb'])
        self.assertTrue(result['original_a_return_proved'])

    def test_boot_time_latch_refines_no_attach_with_the_real_decoder(self):
        sys.path.insert(0, str(ROOT / 'workspace/public/src/mainline/s22plus_canary_h0'))
        import max77705_record as rec
        from test_s22plus_max77705_usb_h0 import record
        events = [(5, 0, 0, 0x3f, 0), (10000, 2, 0, 0x3f, 0)]  # first read COM_OPEN, no later attach
        cases = ((0x20, 1, 'OPEN_BOOT_ATTACH_ONLY', 'OBSERVED_MAX77705_USB_SWITCH'),        # VBUSDetI latched at boot
                 (0x02, 1, 'OPEN_BOOT_ATTACH_ONLY', 'OBSERVED_MAX77705_USB_SWITCH'),        # CHGTypI latched at boot
                 (0x20, 0, 'OPEN_INITIAL_LATCH_UNREAD', 'MAX77705_OBSERVATION_INCONCLUSIVE'),
                 (0x80, 1, 'OPEN_NO_ATTACH_SEEN', 'OBSERVED_MAX77705_USB_SWITCH'))          # APCmdResI only
        for latch, valid, verdict, status in cases:
            raw = bytearray(record(events=events))
            raw[20], raw[21] = latch, valid
            decoded = rec.decode(bytes(raw))
            self.assertEqual(rec.verdict(decoded), 'OPEN_NO_ATTACH_SEEN')  # the pinned decoder alone
            with self.subTest(latch=latch, valid=valid):
                proof = dict(status=profile.MX_STATUS, runtime_schema=profile.MX_WIRE_SCHEMA, subject='max77705',
                             max77705_verdict=rec.verdict(decoded), max77705=decoded)
                result = mx.outcome(proof)
                self.assertEqual((result['max77705_verdict'], result['status']), (verdict, status))
                self.assertEqual(result['max77705_decoder_verdict'], 'OPEN_NO_ATTACH_SEEN')
        # a later attach event (the cued replug) keeps the decoder's after-attach verdict
        raw = bytearray(record(events=[(5, 0, 0, 0x3f, 0), (9000, 3, 0x22, 0x3f, 0)]))
        raw[20], raw[21] = 0x20, 1
        decoded = rec.decode(bytes(raw))
        proof = dict(status=profile.MX_STATUS, runtime_schema=profile.MX_WIRE_SCHEMA, subject='max77705',
                     max77705_verdict=rec.verdict(decoded), max77705=decoded)
        self.assertEqual(mx.outcome(proof)['max77705_verdict'], 'OPEN_UNCHANGED_AFTER_ATTACH')
        # more than 48 events: the dropped middle may hold an attach or a read
        def overflowed(later_attach_at):
            evs = [(5, 0, 0, 0x3f, 0)] + [(10 + i, 1, 0, None, 4) for i in range(1, 60)]  # status kind: skipped reads
            evs = [(t, k, u, (0 if c is None else c), st) for t, k, u, c, st in evs]
            if later_attach_at is not None:
                t, k, u, c, st = evs[later_attach_at]
                evs[later_attach_at] = (t, 3, 0x22, 0x3f, 0)
            return evs
        from test_s22plus_max77705_usb_h0 import record as build
        def ring(evs):  # the producer's slot rule: first 24 kept, then a ring of the latest 24
            slots = [None] * 48
            for n, e in enumerate(evs, 1):
                slots[n - 1 if n <= 48 else 24 + (n - 1 - 24) % 24] = e
            return build(events=slots, total=len(evs))
        for attach_at in (25, None):  # attach overwritten in the middle, or none at all
            raw = bytearray(ring(overflowed(attach_at)))
            raw[20], raw[21] = 0x20, 1
            dropped = rec.decode(bytes(raw))
            dropped_proof = dict(status=profile.MX_STATUS, runtime_schema=profile.MX_WIRE_SCHEMA, subject='max77705',
                                 max77705_verdict=rec.verdict(dropped), max77705=dropped)
            with self.subTest(attach_at=attach_at):
                self.assertEqual(rec.verdict(dropped), 'OPEN_NO_ATTACH_SEEN')
                result = mx.outcome(dropped_proof)
                self.assertEqual((result['max77705_verdict'], result['status']),
                                 ('EVENTS_DROPPED', 'MAX77705_OBSERVATION_INCONCLUSIVE'))
        read = {'ctrl1': 0x3f}
        prefix_read = [read] + [{'ctrl1': None}] * 47       # first successful read kept in the prefix
        tail_read = [{'ctrl1': None}] * 30 + [read] * 18    # first kept read is past the prefix
        for decoder_verdict, events, kept in (
                ('OPEN_UNCHANGED_AFTER_ATTACH', prefix_read, 'EVENTS_DROPPED'),
                ('OPEN_NO_READ_AFTER_ATTACH', prefix_read, 'EVENTS_DROPPED'),
                ('OPEN_THEN_COM_USB_AFTER_ATTACH', prefix_read, 'EVENTS_DROPPED'),
                ('OPEN_THEN_OTHER_AFTER_ATTACH', prefix_read, 'EVENTS_DROPPED'),
                ('INITIAL_COM_USB', prefix_read, 'INITIAL_COM_USB'),
                ('OTHER_INITIAL_CONTROL1', prefix_read, 'OTHER_INITIAL_CONTROL1'),
                ('INITIAL_COM_USB', tail_read, 'EVENTS_DROPPED'),
                ('OTHER_INITIAL_CONTROL1', tail_read, 'EVENTS_DROPPED')):
            with self.subTest(decoder=decoder_verdict, prefix=events is prefix_read):
                fixture = self.proof(decoder_verdict, events_total=60, events=events)
                self.assertEqual(mx.outcome(fixture)['max77705_verdict'], kept)
        # the reviewer's case: the first success at event 26 is overwritten by the ring
        evs = [(5, 0, 0, 0, 1)] + [(10 + i, 1, 0, 0, 4) for i in range(1, 25)] + [(40, 2, 0, 0x3f, 0)] + \
              [(50 + i, 1, 0, 0, 4) for i in range(22)] + [(80, 2, 0, 0x09, 0)] + [(90, 1, 0, 0, 4)]
        wrapped = rec.decode(ring(evs))
        self.assertIn(rec.verdict(wrapped), ('INITIAL_COM_USB', 'OTHER_INITIAL_CONTROL1'))
        wrapped_proof = dict(status=profile.MX_STATUS, runtime_schema=profile.MX_WIRE_SCHEMA, subject='max77705',
                             max77705_verdict=rec.verdict(wrapped), max77705=wrapped)
        self.assertEqual(mx.outcome(wrapped_proof)['max77705_verdict'], 'EVENTS_DROPPED')
        with self.assertRaisesRegex(ValueError, 'initial latch fields differ'):
            mx.outcome(dict(proof, max77705_verdict='OPEN_NO_ATTACH_SEEN', max77705=dict(decoded, initial_uic_valid=1)))

    def test_result_identity_and_unknown_verdict_are_rejected(self):
        for change in (dict(subject='scm'), dict(status='AUTHENTICATED_SCM_USB_TRANSCRIPT'),
                       dict(runtime_schema='s22plus-fyg8-debian-scm-usb-v1'), dict(max77705_verdict='GUESSED')):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    mx.outcome(dict(self.proof('INITIAL_COM_USB'), **change))
        # A malformed proof never blocks terminal closure on an already healthy A.
        bad = dict(self.proof('INITIAL_COM_USB'), subject='scm')
        with patch.object(access, 'rederive', return_value={'proof': bad, 'attach': {'fixture': 'closure'}}):
            result = session.terminal(None, self.request, recovered=True)
        self.assertEqual(result['status'], 'NO_PROOF')
        self.assertIn('evidence_error', result)

    def test_wire_selection_is_by_runtime_schema(self):
        self.assertIs(profile.observation_wire({'debian_ram': {'schema': 's22plus-other'}}), profile.codec)
        with self.assertRaisesRegex(ValueError, 'MAX77705 decoder selection differs'):
            profile.observation_wire({'debian_ram': {'schema': profile.MX_WIRE_SCHEMA},
                                      'max77705_decoder': {'sha256': '0' * 64}})

    def test_optional_candidate_code_failure_uses_recoverable_error(self):
        adapter = SimpleNamespace(root=ROOT, configuration=self.cue_review)
        for failure in (ModuleNotFoundError, SyntaxError):
            with self.subTest(error=failure), patch.object(task, 'capability'), \
                    patch.object(access, 'rederive_base', side_effect=failure):
                with self.assertRaisesRegex(ValueError, 'MAX77705 observation code unavailable'):
                    access.rederive(adapter, self.request)
        with patch.object(task, 'capability', side_effect=ValueError('review differs')), \
                patch.object(access, 'rederive_base', side_effect=AssertionError('unchecked import')):
            with self.assertRaisesRegex(ValueError, 'review differs'):
                access.rederive(adapter, self.request)

    def test_original_a_review_skips_only_candidate_code_in_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / profile.MX_MODULE
            source.parent.mkdir(parents=True)
            source.write_text('# synthetic MAX77705 fixture\n')
            policy = root / profile.MX_POLICY
            policy.parent.mkdir(parents=True)
            policy.write_text('Fixture policy\n')
            files = [policy, source]
            rows = [dict(pin(f), path=str(f.relative_to(root))) for f in files]
            review = root / profile.MX_REVIEW
            review.parent.mkdir(parents=True)
            receipt = publish(review, dict(schema=profile.REVIEW_SCHEMA, scope=profile.MX_SCOPE,
                verdict='PASS_GO', sources=rows, reviewer='H0 test fixture only', findings=[]))
            with patch.object(task, 'source_paths', return_value=files):
                self.assertEqual(task.capability(root, image=self.image, ordinary_cue=True), receipt)
                source.unlink()
                with self.assertRaises(OSError):
                    task.capability(root, image=self.image, ordinary_cue=True)
                self.assertEqual(task.capability(root, image=self.image, recovery=True, ordinary_cue=True), receipt)
                policy.write_text('Altered policy\n')
                with self.assertRaises(ValueError):
                    task.capability(root, image=self.image, recovery=True, ordinary_cue=True)

    def test_unknown_qualification_and_decoder_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unqualified MAX77705 board artifact'):
            mx.qualification({'sha256': '0' * 64})
        with self.assertRaisesRegex(ValueError, 'unreviewed board decoder'):
            mx._decoder(b'raise AssertionError("executed unchecked source")')

    def test_malformed_record_and_missing_cue_closure_are_value_errors(self):
        adapter = SimpleNamespace(root=ROOT, directory=Path('/nonexistent'), folder=lambda name: Path('/nonexistent'),
                                  configuration=self.cue_review)
        self.assertRaisesRegex(ValueError, 'requires its cue scope', access.rederive,
            SimpleNamespace(root=ROOT, configuration=lambda request: {'review': {'path': '/other'}}), self.request)
        import s22plus_fyg8_p319_max77705_irq_dt_audit as dt_audit
        for failure in (TypeError("'<' not supported between 'NoneType' and 'int'"), AttributeError('x'),
                        dt_audit.AuditError('malformed FDT')):
            with self.subTest(error=type(failure)), patch.object(task, 'capability'), \
                    patch.object(access, 'rederive_base', side_effect=failure):
                with self.assertRaisesRegex(ValueError, 'malformed MAX77705 observation record'):
                    access.rederive(adapter, self.request)
        common = (patch.object(task, 'capability'),
                  patch.object(access, 'rederive_base', return_value={'proof': {}, 'window': {'fixture': 'window'}}),
                  patch.object(access, 'verify', lambda receipt: receipt))
        with common[0], common[1], common[2], \
                patch.object(access.attach, 'rederive', side_effect=ValueError('attach closure binding differs')):
            with self.assertRaisesRegex(ValueError, 'attach closure'):
                access.rederive(adapter, self.request)
        common = (patch.object(task, 'capability'),
                  patch.object(access, 'rederive_base', return_value={'proof': {}, 'window': {'fixture': 'window'}}),
                  patch.object(access, 'verify', lambda receipt: receipt))
        with common[0], common[1], common[2], \
                patch.object(access.attach, 'rederive', return_value={'fixture': 'closure'}), \
                patch.object(access, 'read', side_effect=[{'finished_ns': 5}, {'closed_ns': 6}]):
            self.assertEqual(access.rederive(adapter, self.request)['attach'], {'fixture': 'closure'})
        with common[0], common[1], common[2], \
                patch.object(access.attach, 'rederive', return_value={'fixture': 'closure'}), \
                patch.object(access, 'read', side_effect=[{'finished_ns': 7}, {'closed_ns': 6}]):
            with self.assertRaisesRegex(ValueError, 'closure precedes the sealed response'):
                access.rederive(adapter, self.request)

    def test_ordinary_cue_selection(self):
        def adapter(review):
            return SimpleNamespace(root=ROOT, configuration=lambda request: {'review': {'path': str(ROOT/review)}})
        self.assertTrue(profile.ordinary_cue(adapter(profile.MX_REVIEW), self.request))
        # only its own dedicated scope: another review never opens the MAX77705 cue
        for review in (profile.SCM_CUE_REVIEW, profile.SCM_REVIEW, profile.REVIEW):
            self.assertFalse(profile.ordinary_cue(adapter(review), self.request))
        for image in ({'schema': profile.SCM_SCHEMA}, {'schema': profile.MX_SCHEMA, 'ufs_link': True},
                      {'schema': profile.MX_SCHEMA, 'udc_observation': {}}, {}):
            self.assertFalse(profile.ordinary_cue(adapter(profile.MX_REVIEW), dict(self.request, N=image)))

    def test_capability_and_closure_require_the_cue_scope(self):
        with self.assertRaisesRegex(ValueError, 'only with its cue scope'):
            task.source_paths(ROOT, image=self.image)
        with self.assertRaisesRegex(ValueError, 'only with its cue scope'):
            task.capability(ROOT, image=self.image)
        paths = {str(p.relative_to(ROOT)) for p in task.source_paths(ROOT, image=self.image, ordinary_cue=True)}
        self.assertTrue({profile.MX_POLICY, profile.MX_MODULE} <= paths)


sys.path.insert(0, str(ROOT / 'tests'))
import test_s22plus_mainline_attach_cue_v1 as cue_tests  # noqa: E402

MX_IMAGE = {'ap': {'fixture': 'N AP'}, 'member': {'fixture': 'boot-only member'}, 'schema': profile.MX_SCHEMA}


class Max77705CueTests(cue_tests.CueTests):
    """The real cue caller and interlock on a MAX77705 image's ordinary evidence step."""

    def setUp(self):
        cue = cue_tests.cue
        original_append = cue.Journal.append
        original_publish = cue_tests.publish

        def append(journal, event, **data):
            if event == 'step-start' and data.get('step') == 'mainline-evidence':
                data['action'] = 'mainline-evidence'
            return original_append(journal, event, **data)

        def publish(path, value):
            if Path(path).name == 'operation.json' and value.get('operation') == 'mainline-ram':
                value['N'] = dict(MX_IMAGE)
            return original_publish(path, value)
        with patch.object(cue.Journal, 'append', append), patch.object(cue_tests, 'publish', publish):
            super().setUp()
        # The task binds the dedicated MAX77705 cue review, as validate_task requires.
        self.stack.enter_context(patch.object(cue.Adapter, 'configuration',
            lambda adapter, request: {'review': {'path': str(adapter.root / profile.MX_REVIEW)}}))

    def test_fixture_is_the_ordinary_route(self):
        self.assertEqual(self.request['N']['schema'], profile.MX_SCHEMA)
        self.assertEqual(self.journal.rows()[-1]['data']['action'], 'mainline-evidence')

    def test_download_action_is_refused_for_ordinary_image(self):
        rows = self.journal.rows()
        changed = rows[:-1] + [dict(rows[-1], data=dict(rows[-1]['data'], action='mainline-download'))]
        with patch.object(cue_tests.cue.Journal, 'rows', lambda journal: changed):
            with self.assertRaisesRegex(ValueError, 'observation is not active'):
                self.inspect()
