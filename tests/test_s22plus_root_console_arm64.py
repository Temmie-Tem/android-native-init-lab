"""Exact target UAPI plus actual ARM64 supervisor and packaged BusyBox under QEMU.

This is an H0 Linux-user syscall test; target PID1/USB/recovery are not proved.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import test_s22plus_root_console_v1 as base
import s22plus_fyg8_p350_stock_candidate_build as package
ROOT=Path(__file__).resolve().parents[1]
KERNEL=ROOT/'workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel'


class Arm64ConsoleTests(base.ConsoleTests):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.folder=Path(cls.temp.name);cls.binary=cls.folder/'native'
        qemu=shutil.which('qemu-aarch64');compiler=shutil.which('aarch64-linux-gnu-gcc')
        if not qemu or not compiler:raise AssertionError('ARM64 tools absent')
        boot=package.stable(package.BASE/'candidate-a/boot.img')
        busybox=package.entries(boot)[1]['bin/busybox'].data
        if hashlib.sha256(busybox).hexdigest()!='d4e1ca8235fd5c47a7dfca5c9c60ad2243f5d17d3c43d58a7c42355f10fa2cba':
            raise AssertionError('packaged BusyBox changed')
        bb=cls.folder/'busybox';bb.write_bytes(busybox);bb.chmod(0o500)
        value=base.source()
        a=value.index('static long syscall6(');b=value.index('static long p241_clock_gettime',a)
        value=value[:a]+'''static long syscall6(long nr,long a,long b,long c,long d,long e,long f){return neg(syscall(nr,a,b,c,d,e,f));}\n'''+value[b:]
        old='char *args[]={"/bin/sh", "-c", a[3], NULL};return neg(execve("/bin/sh",args,e));'
        new='char *args[]={'+json.dumps(qemu)+','+json.dumps(str(bb))+',"sh","-c",a[3],NULL};return neg(execve('+json.dumps(qemu)+',args,e));'
        if value.count(old)!=1:raise AssertionError('exec adapter seam changed')
        value=value.replace(old,new)
        value=value.replace('return neg(fork());','return neg(syscall(SYS_clone,SIGCHLD,0,0,0,0));')
        value+='''\n_Static_assert(SYS_fcntl==25 && SYS_chdir==49 && SYS_close_range==436,"ARM64 syscall identities");
_Static_assert(SYS_clone==220 && SYS_setsid==157 && SYS_pipe2==59 && SYS_wait4==260,"ARM64 process syscalls");
_Static_assert(O_NONBLOCK==04000 && O_CLOEXEC==02000000 && F_SETFL==4,"ARM64 flags");
'''
        p=subprocess.run([compiler,'-x','c','-','-static','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-o',str(cls.binary)],input=value,text=True,capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)
        info=subprocess.check_output(['file',str(cls.binary)],text=True)
        if 'ARM aarch64' not in info or 'statically linked' not in info:raise AssertionError(info)
        cls.launcher=[qemu,str(cls.binary)]

    def test_exact_target_uapi(self):
        text=(KERNEL/'include/uapi/asm-generic/unistd.h').read_text()
        for item in ('#define __NR3264_fcntl 25','#define __NR_chdir 49',
                     '#define __NR_close_range 436','#define __NR_clone 220',
                     '#define __NR_setsid 157','#define __NR_pipe2 59','#define __NR_wait4 260'):
            self.assertIn(item,text)
        flags=(KERNEL/'include/uapi/asm-generic/fcntl.h').read_text()
        for item in ('#define O_NONBLOCK\t00004000','#define O_CLOEXEC\t02000000','#define F_SETFL\t\t4'):
            self.assertIn(item,flags)
        for name in ('fcntl.h','unistd.h'):
            arm=(KERNEL/'arch/arm64/include/uapi/asm'/name).read_text()
            self.assertIn('#include <asm-generic/'+name+'>',arm)
        self.finish()


if __name__=='__main__':unittest.main()
