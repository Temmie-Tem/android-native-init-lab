"""Exact FYG8 UAPI plus real AArch64 tty behavior; no Samsung USB proof."""
import os
from pathlib import Path
import pty
import shutil
import subprocess
import tempfile
import termios
import tty
import unittest

import s22plus_native_reconnect_source_v1 as source
import s22plus_native_reconnect_fixtures as fixtures
import test_s22plus_hud_arm64 as shared


class Arm64Reconnect(unittest.TestCase):
    def test_exact_FYG8_operands_and_real_ARM64_tty_syscalls(self):
        checks={
            'include/uapi/asm-generic/termbits.h':('#define NCCS 19','#define VTIME 5','#define VMIN 6',
                '#define CSIZE\t0000060','#define CS8\t0000060','#define CREAD\t0000200',
                '#define PARENB\t0000400','#define CLOCAL\t0004000'),
            'include/uapi/asm-generic/ioctls.h':('#define TCGETS\t\t0x5401','#define TCSETS\t\t0x5402'),
            'include/uapi/asm-generic/fcntl.h':('#define O_NOCTTY\t00000400','#define O_NONBLOCK\t00004000',
                '#define O_CLOEXEC\t02000000'),
            'include/uapi/asm-generic/unistd.h':('#define __NR_ioctl 29','#define __NR_openat 56',
                '#define __NR_close 57','#define __NR_read 63'),
            'include/uapi/asm-generic/errno-base.h':('#define\tENXIO\t\t 6',),
        }
        for path,lines in checks.items():
            rows={' '.join(line.split()) for line in (shared.KERNEL/path).read_text().splitlines()}
            for line in lines:self.assertTrue(any(row.startswith(' '.join(line.split())) for row in rows),path+': '+line)
        compiler=shutil.which('aarch64-linux-gnu-gcc');qemu=shutil.which('qemu-aarch64')
        self.assertTrue(compiler and qemu)
        with tempfile.TemporaryDirectory(prefix='s22-reconnect-arm64-') as folder:
            folder=Path(folder);binary=folder/'probe'
            (folder/'owned-tty.h').write_text(fixtures.platform_tty_definitions()+
                (source.TEMPLATES/'transport.inc.c.in').read_text())
            result=subprocess.run([compiler,'-static','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',
                '-I',str(folder),str(source.ROOT/'tests/s22plus_native_reconnect_arm64_harness.c'),'-o',str(binary)],
                capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('ARM aarch64',subprocess.check_output(['file',binary],text=True))
            master,slave=pty.openpty();next_master,next_slave=pty.openpty()
            try:
                tty.setraw(slave);os.set_blocking(slave,False)
                attrs=termios.tcgetattr(slave);attrs[6][termios.VMIN]=0
                termios.tcsetattr(slave,termios.TCSANOW,attrs)
                proc=subprocess.Popen([qemu,binary,str(slave),os.ttyname(next_slave)],pass_fds=(slave,),
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                os.close(slave);slave=None
                import select
                self.assertTrue(select.select([proc.stdout],[],[],5)[0])
                self.assertEqual(proc.stdout.readline().strip(),'READY normalized empty EAGAIN')
                os.close(master);master=None
                out,err=proc.communicate('H',timeout=5)
                self.assertEqual(proc.returncode,0,err);self.assertIn('PASS ARM64 real raw ioctl',out)
            finally:
                if 'proc' in locals() and proc.poll() is None:proc.kill();proc.communicate()
                for fd in (master,slave,next_master,next_slave):
                    if fd is not None:os.close(fd)


if __name__=='__main__':unittest.main()
