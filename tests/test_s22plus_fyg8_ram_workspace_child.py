"""Actual user/mount-namespace and seccomp behavior of the RAM child, H0 only."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_fyg8_ram_workspace_child_v1 as child

PREFIX = r'''
#define _GNU_SOURCE
#include <stddef.h>
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <sys/wait.h>
static long syscall6(long n,long a,long b,long c,long d,long e,long f) {
 long r=syscall(n,a,b,c,d,e,f); return r<0?-errno:r;
}
static long sys_openat(const char *p,int f,unsigned int m) {
 return syscall6(SYS_openat,-100,(long)p,f,m,0,0);
}
static long sys_close(int f) { return syscall6(SYS_close,f,0,0,0,0,0); }
static long sys_read(int f,void *p,size_t n) { return syscall6(SYS_read,f,(long)p,n,0,0,0); }
static long sys_write(int f,const void *p,size_t n) { return syscall6(SYS_write,f,(long)p,n,0,0,0); }
static long sys_mount(const char *s,const char *t,const char *fs,unsigned long f,const char *d) {
 return syscall6(SYS_mount,(long)s,(long)t,(long)fs,f,(long)d,0);
}
'''
MAIN = r'''
int main(int argc,char **argv) {
 if(argc<3)return 90;
 if(sys_mount(argv[1],argv[1],NULL,4096UL|16384UL,NULL))return 89;
 if(chroot(argv[1])||chdir("/"))return 91;
 long rc=p349_prepare_workspace();
 if(rc){fprintf(stderr,"parent setup %ld\n",rc);return 92;}
 for(int i=2;i<argc;i++) {
  pid_t pid=fork();
  if(pid<0)return 93;
  if(pid==0) {
   rc=p345_enter_readonly_child();
   if(rc){fprintf(stderr,"child setup %ld\n",rc);_exit(94);}
   char *args[]={"/bin/busybox","ash","-o","pipefail","-c",argv[i],NULL};
   char *env[]={"PATH=/bin","HOME=/work",NULL};
   syscall6(P345_NR_EXECVE,(long)args[0],(long)args,(long)env,0,0,0);
   _exit(95);
  }
  int status=0;if(waitpid(pid,&status,0)!=pid)return 96;
  if(!WIFEXITED(status)||WEXITSTATUS(status)!=0) {
   fprintf(stderr,"action %d status %d\n",i-1,status);return 97;
  }
 }
 return 0;
}
'''


def host_definitions(source):
    pp = subprocess.run(['cc','-dM','-E','-x','c','-include','sys/syscall.h','-'],
                        input='',capture_output=True,text=True,check=True).stdout
    numbers = {k:int(v) for k,v in re.findall(r'^#define __NR_([a-z0-9_]+) (\d+)$',pp,re.M)}
    definitions = ['-DP345_HOST_TEST_EXTRA_SYSCALLS','-DP345_AUDIT_ARCH=0xc000003eU']
    for prefix,name in re.findall(rb'^#define (P345|P349)_NR_([A-Z0-9_]+) \d+',source,re.M):
        definitions.append(f'-D{prefix.decode()}_NR_{name.decode()}={numbers[name.decode().lower()]}')
    for name in ('mkdir','unlink','rename'):
        definitions.append(f'-DP349_NR_HOST_{name.upper()}={numbers[name]}')
    return definitions


class RamWorkspaceChildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.source = cls.root/'child.c'
        cls.source.write_text(PREFIX+child.child_source().decode()+MAIN)
        cls.exe = cls.root/'child'
        result = subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O2',
            *host_definitions(child.child_source()),str(cls.source),'-o',str(cls.exe)],capture_output=True,text=True)
        if result.returncode:
            raise AssertionError(result.stderr)
        result = subprocess.run(['unshare','--user','--map-root-user','--map-auto','--mount','true'],capture_output=True)
        if result.returncode:
            raise AssertionError('Actual namespace qualification unavailable: '+result.stderr.decode())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_commands(self,*commands):
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            view = Path(directory)
            for name in ('bin','dev','proc','sys/class/udc/a600000.dwc3'):
                (view/name).mkdir(parents=True,exist_ok=True)
            shutil.copyfile('/bin/busybox',view/'bin/busybox')
            (view/'bin/busybox').chmod(0o555)
            for item in child.SNAPSHOT_FILES:
                path=view/item['view'].lstrip('/')
                path.write_text('fixture-text\n')
                path.chmod(0o444)
            result = subprocess.run(['unshare','--user','--map-root-user','--map-auto','--mount',
                str(self.exe),str(view),*commands],capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return result

    def test_exact_acceptance_ram_commands_across_children(self):
        import s22plus_fyg8_p349_research_shell_observer as observer
        roles = ('ram-create', 'ram-modify', 'ram-script',
                 'witness-20min', 'witness-40min', 'witness-60min')
        specs = [observer.LATER_ACCEPTANCE_COMMANDS[role] for role in roles]
        result = self.run_commands(*(spec['command'].decode() for spec in specs))
        self.assertEqual(result.stdout.encode(), b''.join(spec['middle']['output'] for spec in specs))

    def test_arm64_compile_and_syscall_numbers(self):
        compiler = shutil.which('aarch64-linux-gnu-gcc')
        self.assertIsNotNone(compiler, 'Required target toolchain unavailable')
        target = self.root/'target-child.o'
        build = subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
            '-O2', '-c', str(self.source), '-o', str(target)], capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertIn('ARM aarch64', subprocess.check_output(['file', str(target)], text=True))
        pp = subprocess.run([compiler, '-dM', '-E', '-x', 'c', '-include', 'asm/unistd.h', '-'],
            input='', capture_output=True, text=True, check=True).stdout
        numbers = {k:int(v) for k,v in re.findall(r'^#define __NR_([a-z0-9_]+) (\d+)$', pp, re.M)}
        for name, value in re.findall(rb'^#define (?:P345|P349)_NR_([A-Z0-9_]+) (\d+)$', child.child_source(), re.M):
            if name in (b'ARCH_PRCTL', b'DUP2'):
                continue
            self.assertEqual(int(value), numbers[name.decode().lower()], name)

    def test_actual_workspace_survives_children_and_executes_script(self):
        result=self.run_commands(
            'test "$(/bin/busybox id -u)" = 65534 || exit 10; '
            'printf "alpha" > /work/value || exit 11; '
            'printf "printf RAM-SCRIPT-PASS" > /work/script || exit 12; '
            '/bin/busybox mkdir /work/sub || exit 13',
            'test "$(/bin/busybox cat /work/value)" = alpha || exit 14; '
            'printf "beta" >> /work/value || exit 15; '
            '/bin/busybox ash /work/script || exit 16; '
            '/bin/busybox mv /work/script /work/sub/script || exit 17',
            'test "$(/bin/busybox cat /work/value)" = alphabeta || exit 18; '
            '/bin/busybox ash /work/sub/script || exit 19; '
            '/bin/busybox rm /work/sub/script /work/value || exit 20')
        self.assertEqual(result.stdout,'RAM-SCRIPT-PASSRAM-SCRIPT-PASS')

    def test_actual_surrounding_view_and_escape_paths_remain_denied(self):
        result=self.run_commands(
            'if printf x > /proc/version; then exit 10; fi; '
            'if printf x > /bin/busybox; then exit 11; fi; '
            'if printf x > /work/../../proc/version; then exit 12; fi; '
            'if /bin/busybox mkdir /outside; then exit 13; fi; '
            'if /bin/busybox ln -s /proc/version /work/link; then exit 14; fi; '
            'if /bin/busybox mknod /work/node b 8 0; then exit 15; fi; '
            'if /bin/busybox mount -t tmpfs tmpfs /work; then exit 16; fi; '
            'test ! -e /proc/self/fd || exit 17; '
            'test ! -e /dev || exit 18; '
            'test "$(/bin/busybox cat /proc/version)" = fixture-text || exit 19; '
            'printf x > /work/allowed || exit 20; printf DENIAL-PASS')
        self.assertEqual(result.stdout,'DENIAL-PASS')

    def test_actual_capacity_exhaustion_cleanup_and_reuse(self):
        result=self.run_commands(
            's=$(/bin/busybox awk \'BEGIN {for(i=0;i<32768;i++)printf "x"}\') || exit 10; '
            'i=0; while test "$i" -lt 160; do '
            'if printf "%s%s" "$s" "$s" > /work/cap-$i; then i=$((i+1)); else break; fi; done; '
            'test "$i" -gt 100 || exit 11; test "$i" -lt 160 || exit 12; '
            '/bin/busybox rm /work/cap-* || exit 13; '
            'printf recovered > /work/after || exit 14; printf CAPACITY-PASS',
            'test "$(/bin/busybox cat /work/after)" = recovered || exit 15; '
            '/bin/busybox rm /work/after || exit 16')
        self.assertEqual(result.stdout,'CAPACITY-PASS')


if __name__=='__main__':
    unittest.main()
