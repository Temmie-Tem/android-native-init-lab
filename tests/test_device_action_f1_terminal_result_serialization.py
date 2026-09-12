"""Regression coverage for compact terminal publication, under unchanged bounds."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / 'workspace/public/src/scripts/revalidation/device_action_f1_v2.py'
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))


class TerminalSerializationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('terminal_serialization_core', CORE_PATH)
        cls.core = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.core
        spec.loader.exec_module(cls.core)

    def test_structured_terminal_fits_without_changing_data_or_journal_encoding(self):
        value = {'entries': [{'k': 'x'} for _ in range(3000)]}
        core = self.core
        self.assertGreater(len(json.dumps(value, indent=2, sort_keys=True).encode()) + 1,
                           core.MAX_RESULT_RECORD)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / 'live-result.json'
            core._write_live_result(path, value)
            self.assertLessEqual(path.stat().st_size, core.MAX_RESULT_RECORD)
            self.assertEqual(json.loads(path.read_bytes()), value)
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
            small = folder / 'journal.json'
            core._write_exclusive(small, {'x': [1, 2]})
            self.assertEqual(small.read_bytes(), b'{\n  "x": [\n    1,\n    2\n  ]\n}\n')
            with self.assertRaisesRegex(core.F1V2Error, 'exceeds its bound'):
                core._write_exclusive(folder / 'large-journal.json', value)
            self.assertFalse((folder / 'large-journal.json').exists())

    def test_exact_limit_overflow_and_path_scope(self):
        core = self.core
        value = {'bounded': 'x' * (core.MAX_RESULT_RECORD - 15)}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'live-result.json'
            core._write_live_result(path, value)
            self.assertEqual(path.stat().st_size, core.MAX_RESULT_RECORD)
            retained = path.read_bytes()
            with self.assertRaisesRegex(core.F1V2Error, 'exceeds its bound'):
                core._write_live_result(path, {'bounded': value['bounded'] + 'x'})
            self.assertEqual(path.read_bytes(), retained)
            with self.assertRaisesRegex(core.F1V2Error, 'limited to live-result.json'):
                core._write_live_result(path.with_name('other.json'), {'x': 1})
            self.assertFalse(path.with_name('other.json').exists())

    def test_failed_write_or_invalid_number_keeps_prior_terminal(self):
        core = self.core
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'live-result.json'
            core._write_live_result(path, {'status': 'retained'})
            retained = path.read_bytes()
            with mock.patch.object(core.os, 'write', return_value=1):
                with self.assertRaisesRegex(core.F1V2Error, 'short durable record write'):
                    core._write_live_result(path, {'status': 'replacement'})
            self.assertEqual(path.read_bytes(), retained)
            with self.assertRaises(ValueError):
                core._write_live_result(path, {'value': float('nan')})
            self.assertEqual(path.read_bytes(), retained)

    def test_failed_fsync_keeps_prior_terminal(self):
        core = self.core
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'live-result.json'
            core._write_live_result(path, {'status': 'retained'})
            retained = path.read_bytes()
            with mock.patch.object(core.os, 'fsync', side_effect=OSError('fixture fsync failure')):
                with self.assertRaises(OSError):
                    core._write_live_result(path, {'status': 'replacement'})
            self.assertEqual(path.read_bytes(), retained)


if __name__ == '__main__':
    unittest.main(verbosity=2)
