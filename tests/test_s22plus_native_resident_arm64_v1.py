"""Exact target headers plus real AArch64 behavior under user-mode emulation."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import s22plus_native_source_v1 as common
import test_s22plus_hud_arm64 as shared


class Arm64(unittest.TestCase):
    def test_exact_target_operands_and_real_resident_syscalls(self):
        shared.HudArm64().test_exact_target_uapi()
        mapping={
            'include/uapi/asm-generic/unistd.h':['#define __NR3264_ftruncate 46','#define __NR3264_lseek 62',
                '#define __NR_ftruncate __NR3264_ftruncate','#define __NR_lseek __NR3264_lseek',
                '#define __NR_clock_gettime 113','#define __NR_recvfrom 207'],
            'include/uapi/linux/time.h':['#define CLOCK_BOOTTIME\t\t\t7'],
            'include/linux/socket.h':['#define MSG_TRUNC\t0x20','#define MSG_DONTWAIT\t0x40'],
        }
        for path,needles in mapping.items():
            text=(shared.KERNEL/path).read_text()
            for needle in needles:self.assertIn(needle,text,path)
        compiler=shutil.which('aarch64-linux-gnu-gcc');qemu=shutil.which('qemu-aarch64');self.assertTrue(compiler and qemu)
        with tempfile.TemporaryDirectory(prefix='s22-resident-arm64-h0-') as folder:
            binary=Path(folder)/'probe'
            build=subprocess.run([compiler,'-static','-O2','-Wall','-Wextra','-Werror','-I',str(common.NATIVE),
                str(common.ROOT/'tests/s22plus_resident_arm64_harness.c'),'-o',str(binary)],capture_output=True,text=True,timeout=30)
            self.assertEqual(build.returncode,0,build.stderr)
            self.assertIn('ARM aarch64',subprocess.check_output(['file',binary],text=True))
            result=subprocess.run([qemu,binary],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('PASS ARM64 resident',result.stdout)


if __name__=='__main__':unittest.main()
