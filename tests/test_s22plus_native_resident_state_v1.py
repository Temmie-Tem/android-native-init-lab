"""Actual PID1 ring/IPC/fault paths with fixed host-only syscall boundaries."""
from pathlib import Path
import subprocess
import tempfile
import unittest

import test_s22plus_native_resident_v1 as integration
import s22plus_native_resident_protocol_v1 as protocol


class State(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='s22-resident-state-h0-');cls.addClassCleanup(cls.temp.cleanup)
        cls.folder=Path(cls.temp.name);text=integration.native_fixture()
        text=text[:text.rindex('int main(int argc,char **argv)')]
        # Synthetic PIDs can never reach the host kill/wait APIs.
        text='#define RESIDENT_FIXTURE_STUCK_PID 2147483600\n#define RESIDENT_FIXTURE_UNKNOWN_PID 2147483601\n'+text
        text=integration.swap(text,'static long sys_wait4(long pid,int *status,int options){',
            'static long sys_wait4(long pid,int *status,int options){if(pid==RESIDENT_FIXTURE_STUCK_PID)return 0;if(pid==RESIDENT_FIXTURE_UNKNOWN_PID)return -ECHILD;')
        text=integration.swap(text,'if(nr==129)return neg(kill(a,b));',
            'if(nr==129){if(a==RESIDENT_FIXTURE_STUCK_PID)return 0;if(a==RESIDENT_FIXTURE_UNKNOWN_PID)_Exit(138);return neg(kill(a,b));}')
        text+='\n#include <assert.h>\n'+(integration.common.ROOT/'tests/s22plus_resident_state_harness.c').read_text()
        path=cls.folder/'state.c';path.write_text(text);cls.binary=cls.folder/'state'
        try:integration.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')
        except subprocess.CalledProcessError as exc:raise AssertionError(exc.stderr) from exc

    def test_real_bounded_state_and_no_descriptor_or_child_reuse(self):
        for case in ('root-dir','root-mount','ring','ipc','lifecycle'):
            with self.subTest(case=case):
                folder=self.folder/case;folder.mkdir()
                result=subprocess.run([self.binary,folder,case],capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr);self.assertIn('PASS',result.stdout)
                if case=='ring':
                    raw=(folder/'hud.log').read_bytes();decoded=protocol.decode_log(raw)
                    self.assertEqual((decoded['first'],decoded['last'],decoded['evicted'],decoded['dropped']),(99937,100000,99936,2))
                    self.assertEqual(decoded['partial_bytes'],4);self.assertFalse(decoded['complete_history'])
                    self.assertLess(len(raw),64*768+337)
                    for invalid in (raw[:-1],raw+b'x',raw.replace(b'first=99937',b'first=1'),raw.replace(b'EVENT sequence=99937\n',b'x\n'*800)):
                        with self.assertRaises(ValueError):protocol.decode_log(invalid)


if __name__=='__main__':unittest.main()
