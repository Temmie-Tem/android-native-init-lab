"""Observed FYG8 device naming, individual readiness failures and ARM64 parity."""
import errno
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class LoggerBinding(unittest.TestCase):
    def test_actual_predicate_on_host_and_arm64(self):
        cases={
            ('observed-eight',3):(0,0),('soc-only',3):(errno.ENOENT,2),
            ('module-absent',3):(errno.ENOENT,1),('driver-absent',3):(errno.ENOENT,2),
            ('driver-file',3):(errno.EPROTO,2),('driver-owner',3):(errno.EPROTO,2),
            ('dangling',3):(errno.ENOENT,3),('target-file',3):(errno.EPROTO,3),
            ('last-absent',3):(errno.ENOENT,4),('last-symlink',3):(errno.EPROTO,4),
            ('ap-absent',3):(errno.ENOENT,5),('ap-absent',1):(0,0),
            ('last-absent',2):(0,0),('observed-eight',0):(errno.EINVAL,99),
        }
        with tempfile.TemporaryDirectory(prefix='s22-logger-bind-') as directory:
            for compiler,runner in (('gcc',[]),('aarch64-linux-gnu-gcc',['qemu-aarch64'])):
                self.assertIsNotNone(shutil.which(compiler))
                if runner:self.assertIsNotNone(shutil.which(runner[0]))
                binary=Path(directory)/compiler
                subprocess.run([compiler,'-static','-Wall','-Wextra','-Werror',
                    '-I',str(ROOT/'workspace/public/src/native-init'),
                    str(ROOT/'tests/s22plus_fyg8_logger_binding_harness.c'),'-o',str(binary)],check=True)
                description=subprocess.check_output(['file',str(binary)],text=True)
                self.assertIn('statically linked',description)
                if runner:self.assertIn('ARM aarch64',description)
                for (fixture,mask),expected in cases.items():
                    with self.subTest(compiler=compiler,fixture=fixture,mask=mask):
                        raw=subprocess.check_output([*runner,str(binary),fixture,str(mask)],text=True)
                        self.assertEqual(tuple(map(int,raw.split())),expected)


if __name__=='__main__':unittest.main()
