"""Bounded offline closure publication, complete raw-set and interruption checks."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'workspace/public/src/scripts/analysis')]
import s22plus_mainline_close_h0_v2 as close
from s22plus_native_records_v3 import canonical, read, pin, publish, SessionError
import device_action_raw_capture_v1 as raw


class RawIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        for name in ('acquire_command',):
            guard = patch.object(raw, name, side_effect=AssertionError('offline acquisition'))
            guard.start(); self.addCleanup(guard.stop)

    def captures(self, count, start=0):
        for i in range(start, count):
            writer = raw.RawCaptureWriter(self.folder, f'fixture-{i:05d}', stdout_maximum=32, stderr_maximum=32)
            writer.write_stdout(f'raw {i}'.encode())
            if i % 3 == 0:
                writer.write_stderr(b'negative fixture')
            writer.finalize(returncode=i % 3, timed_out=False)

    def test_256_and_257_boundaries_and_idempotent_retry(self):
        self.captures(256)
        # Immutable output must reject later raw-set growth.
        rows = close.capture_rows(self.folder)
        self.assertEqual(len(rows), 256)
        receipt, _ = close.raw_index(self.folder, write=True)
        self.assertEqual(len(read(Path(receipt['path']))['pages']), 1)
        self.assertEqual(close.raw_index(self.folder)[0], receipt)
        self.captures(257, start=256)
        with self.assertRaises(OSError): close.raw_index(self.folder)
        with self.assertRaises(OSError): close.raw_index(self.folder, write=True)

    def test_257_pages_are_complete(self):
        self.captures(257)
        receipt, rows = close.raw_index(self.folder, write=True)
        index = read(Path(receipt['path']))
        self.assertEqual(index['capture_count'], 257)
        self.assertEqual([read(Path(p['path']))['count'] for p in index['pages']], [256, 1])
        before = {p: p.read_bytes() for p in self.folder.rglob('*') if p.is_file()}
        self.assertEqual(close.raw_index(self.folder, write=True), (receipt, rows))
        self.assertEqual(before, {p: p.read_bytes() for p in self.folder.rglob('*') if p.is_file()})

    def test_missing_reordered_duplicate_or_changed_page_and_index(self):
        self.captures(3); receipt, _ = close.raw_index(self.folder, write=True)
        page = self.folder/'raw-pages-v2/00000.json'; data = page.read_bytes()
        base = read(page)
        variants = []
        x = copy.deepcopy(base); x['captures'].reverse(); variants.append(x)
        x = copy.deepcopy(base); x['captures'][1] = x['captures'][0]; variants.append(x)
        x = copy.deepcopy(base); x['captures'].pop(); variants.append(x)
        x = copy.deepcopy(base); x['captures'][0]['returncode'] = 99; variants.append(x)
        x = copy.deepcopy(base); x['start'] = 1; variants.append(x)
        x = copy.deepcopy(base); x['number'] = 1; variants.append(x)
        page.chmod(0o600)
        for value in variants:
            page.write_bytes(canonical(value))
            with self.assertRaises(SessionError): close.raw_index(self.folder)
        page.unlink()
        with self.assertRaises(OSError): close.raw_index(self.folder)
        page.write_bytes(data)
        index_path = Path(receipt['path']); index = read(index_path)
        index['pages'].append(index['pages'][0]); index_path.chmod(0o600); index_path.write_bytes(canonical(index))
        with self.assertRaises(SessionError): close.raw_index(self.folder)

    def test_extra_page_missing_capture_and_modified_raw_bytes(self):
        self.captures(2); close.raw_index(self.folder, write=True)
        extra = self.folder/'raw-pages-v2/00001.json'; extra.write_bytes(b'{}\n')
        with self.assertRaises(SessionError): close.raw_index(self.folder)
        extra.unlink()
        receipt = self.folder/'fixture-00001.capture.json'; data = receipt.read_bytes(); receipt.unlink()
        with self.assertRaises(SessionError): close.raw_index(self.folder)
        receipt.write_bytes(data); receipt.chmod(0o400)
        h = raw.load_handle(receipt)
        path = h.stdout_path; path.chmod(0o600); path.write_bytes(b'changed')
        with self.assertRaises((ValueError, raw.RawCaptureError)): close.raw_index(self.folder)

    def test_interrupted_publication_resumes_without_replacing_page(self):
        self.captures(257)
        real = close.publish
        calls = []
        def fail_second(path, value):
            calls.append(path)
            if len(calls) == 2: raise OSError('fixture interruption')
            return real(path, value)
        with patch.object(close, 'publish', side_effect=fail_second):
            with self.assertRaises(OSError): close.raw_index(self.folder, write=True)
        page = self.folder/'raw-pages-v2/00000.json'
        before = (page.stat().st_ino, page.read_bytes())
        self.assertFalse((self.folder/'raw-index-v2.json').exists())
        receipt, _ = close.raw_index(self.folder, write=True)
        self.assertEqual(before, (page.stat().st_ino, page.read_bytes()))
        self.assertEqual(close.raw_index(self.folder)[0], receipt)

    def test_mismatched_partial_output_is_never_overwritten(self):
        self.captures(2); directory = self.folder/'raw-pages-v2'; directory.mkdir()
        page = directory/'00000.json'; page.write_bytes(b'{}\n')
        with self.assertRaises(SessionError): close.raw_index(self.folder, write=True)
        self.assertEqual(page.read_bytes(), b'{}\n')
        self.assertFalse((self.folder/'raw-index-v2.json').exists())


class ClosureTests(unittest.TestCase):
    def test_existing_v1_delegates_unchanged_to_original_verifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root/'workspace/private/task'; folder.mkdir(parents=True)
            task = folder/'task.json'; task.write_bytes(b'{}\n')
            old = publish(folder/'closed.json', {'schema':'s22plus-comparison-task-closed-v1'})
            with patch.object(close.original, 'close_task', return_value=old) as original:
                self.assertEqual(close.close_task(root, task, folder/'unused-review'), old)
                original.assert_called_once_with(root, task)
            self.assertEqual(pin(folder/'closed.json'), old)

    def test_closed_is_last_and_retry_keeps_all_published_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root/'workspace/private/task'; folder.mkdir(parents=True)
            task = folder/'task.json'; task.write_bytes(b'{}\n')
            review = folder/'review.json'; review.write_bytes(b'{}\n')
            writer = raw.RawCaptureWriter(folder, 'fixture', stdout_maximum=8, stderr_maximum=0)
            writer.write_stdout(b'raw'); writer.finalize(returncode=0)
            value = dict(schema=close.CLOSED_SCHEMA, source_binding={'execution':'unchanged'})
            timeline = {'events':['original evidence']}; provenance = {'reporting':'separate'}
            real = close.publish
            order = []
            def interrupted(path, data):
                order.append(path.name)
                if path.name == 'closed.json': raise OSError('fixture interrupted before close')
                return real(path, data)
            with patch.object(close, 'derivation', return_value=(value, timeline)), \
                 patch.object(close, 'reporting', return_value=provenance), \
                 patch.object(close, 'publish', side_effect=interrupted):
                with self.assertRaises(OSError): close.close_task(root, task, review)
            self.assertEqual(order[-1], 'closed.json')
            self.assertFalse((folder/'closed.json').exists())
            before = {p:p.read_bytes() for p in folder.rglob('*') if p.is_file()}
            with patch.object(close, 'derivation', return_value=(value, timeline)), \
                 patch.object(close, 'reporting', return_value=provenance):
                receipt = close.close_task(root, task, review)
                self.assertEqual(close.close_task(root, task, review), receipt)
            self.assertTrue(all(p.read_bytes() == b for p,b in before.items()))
            result = read(folder/'closed.json')
            self.assertEqual(result['source_binding'], {'execution':'unchanged'})
            self.assertEqual(result['reporting_provenance'], provenance)


if __name__ == '__main__': unittest.main()
