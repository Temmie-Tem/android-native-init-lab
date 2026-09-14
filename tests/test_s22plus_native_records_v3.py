"""Real host atomic publication, short writes and recoverable journal staging."""
import errno
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_records_v3 as records


class RecordsTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)

    def test_atomic_no_replace_uses_real_host_renameat2(self):
        path=self.root/'record.json'
        first=records.publish(path,dict(value=1))
        with self.assertRaises(FileExistsError): records.publish(path,dict(value=2))
        self.assertEqual(records.read(path),dict(value=1))
        self.assertEqual(records.pin(path),first); self.assertEqual(path.stat().st_nlink,1)
        self.assertEqual(list(self.root.iterdir()),[path])

    def test_partial_write_failure_leaves_prior_intent_readable(self):
        journal=records.Journal(self.root/'journal'); journal.append('effect-intent',role='N')
        write=os.write; calls=0
        def short_then_full(fd,data):
            nonlocal calls
            calls+=1
            if calls==1: return write(fd,data[:5])
            raise OSError(errno.ENOSPC,'fixture disk full')
        with mock.patch.object(os,'write',side_effect=short_then_full),self.assertRaises(OSError):
            journal.append('step-complete',role='N')
        self.assertEqual([row['event'] for row in journal.rows()],['effect-intent'])
        self.assertFalse((journal.directory/'0001.json').exists())
        journal.append('stopped',reason='publication failure')
        self.assertEqual([row['event'] for row in journal.rows()],['effect-intent','stopped'])

    def test_crash_staging_has_no_authority_and_does_not_hide_prior_intent(self):
        journal=records.Journal(self.root/'journal'); journal.append('effect-intent',role='A')
        staging=journal.directory/('.publish-'+'a'*32+'.tmp'); staging.write_bytes(b'{"par')
        self.assertEqual(len(journal.rows()),1)
        journal.append('stopped',reason='interrupted publication')
        self.assertEqual(len(journal.rows()),2)
        (journal.directory/'unknown').write_bytes(b'x')
        with self.assertRaises(records.SessionError): journal.rows()


if __name__=='__main__': unittest.main()
