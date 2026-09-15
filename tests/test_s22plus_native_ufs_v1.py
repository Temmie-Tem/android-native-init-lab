"""Actual ARM64 fixed-loader file/error paths; no kernel module is inserted."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'),
    str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/analysis')]
import s22plus_native_ufs_source_v1 as source
import s22plus_native_ufs_build_v1 as build

HARNESS=r'''
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>
static void fail(const char *why) { fprintf(stderr,"FAIL=%s\n",why);exit(100); }
static void require(int ok,const char *why) { if(!ok)fail(why); }
static int test_open(const char *path,int flags) {
    require(!strcmp(path,"/"),"unexpected-root");
    require(flags==(O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW),"root-flags");
    return open(getenv("FIXTURE_ROOT"),flags);
}
static int test_openat(int parent,const char *name,int flags) {
    int directory=!strcmp(name,"lib")||!strcmp(name,"modules");
    require(flags==(O_RDONLY|O_CLOEXEC|O_NOFOLLOW|(directory?O_DIRECTORY:0)),"openat-flags");
    return openat(parent,name,flags);
}
static int test_fstat(int fd,struct stat *value) {
    int result=fstat(fd,value);
    /* Fixture ownership stands in for the sealed root-owned vendor archive.
     * File type, link count, mode, size and open behavior are real syscalls. */
    if(!result) { value->st_uid=getenv("BAD_OWNER")?1:0;value->st_gid=0; }
    return result;
}
static long test_syscall(long number,...) {
    static unsigned calls;
    va_list args;va_start(args,number);
    int fd=va_arg(args,int);const char *params=va_arg(args,const char *);int flags=va_arg(args,int);
    va_end(args);
    require(number==SYS_finit_module&&!strcmp(params,"")&&flags==0,"insertion-arguments");
    require((fcntl(fd,F_GETFL)&O_ACCMODE)==O_RDONLY&&
        (fcntl(fd,F_GETFD)&FD_CLOEXEC),"insertion-fd-flags");
    printf("INSERT index=%u\n",calls);fflush(stdout);
    const char *cut=getenv("FAIL_AT");
    if(cut&&calls++==(unsigned)atoi(cut)) { errno=EIO;return -1; }
    if(!cut)calls++;
    return 0;
}
#define open test_open
#define openat test_openat
#define fstat test_fstat
#define syscall test_syscall
'''


@unittest.skipUnless(shutil.which('qemu-aarch64') and shutil.which('aarch64-linux-gnu-gcc'),
    'ARM64 compiler and qemu-user are required')
class LoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        folder=Path(cls.temp.name);program=folder/'loader.c';cls.binary=folder/'loader'
        program.write_bytes(HARNESS.encode()+source.loader_source()+
            b'\nint main(void) { ufs1_prepare();puts("COMPLETE");return 0; }\n')
        compiler=build.shared.packager._bind_tools()['gcc']
        subprocess.run([compiler,'-std=c11','-O2','-static','-Wall','-Wextra','-Werror',
            str(program),'-o',str(cls.binary)],capture_output=True,check=True,timeout=30)
        description=subprocess.run(['file','-b',str(cls.binary)],capture_output=True,check=True).stdout
        if b'ARM aarch64' not in description or b'statically linked' not in description:
            raise AssertionError('loader is not an actual static ARM64 executable')

    def fixture(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name);modules=root/'lib/modules';modules.mkdir(parents=True)
        for name,_,size,_ in source.MODULES:
            path=modules/name
            with path.open('wb') as stream:stream.truncate(size)
            path.chmod(0o644)
        return root,modules

    def run_loader(self,root,**changes):
        return subprocess.run(['qemu-aarch64',str(self.binary)],capture_output=True,timeout=5,
            env=dict(os.environ,FIXTURE_ROOT=str(root),**changes))

    def test_actual_arm64_directory_flags_and_fixed_insertion_order(self):
        root,_=self.fixture();result=self.run_loader(root)
        self.assertEqual(result.returncode,0,result.stderr)
        inserted=[line for line in result.stdout.splitlines() if line.startswith(b'INSERT')]
        self.assertEqual(inserted,[f'INSERT index={i}'.encode() for i in range(len(source.MODULES))])
        self.assertTrue(result.stdout.endswith(b'COMPLETE\n'))
        self.assertEqual(result.stderr,b'')

    def test_missing_symlink_hardlink_size_mode_and_type_fail_before_insertion(self):
        for mutation in ('missing','symlink','hardlink','size','mode','directory'):
            with self.subTest(mutation=mutation):
                root,modules=self.fixture();path=modules/source.MODULES[2][0]
                if mutation in ('missing','symlink','directory'):path.unlink()
                if mutation=='symlink':path.symlink_to(modules/source.MODULES[1][0])
                if mutation=='hardlink':os.link(path,modules/'other-link')
                if mutation=='size':path.write_bytes(b'short')
                if mutation=='mode':path.chmod(0o600)
                if mutation=='directory':path.mkdir()
                result=self.run_loader(root)
                self.assertEqual(result.returncode,100)
                self.assertEqual(result.stdout.count(b'INSERT index='),2)
                self.assertNotIn(b'COMPLETE',result.stdout)

    def test_wrong_owner_and_failed_finit_never_retry_or_unload(self):
        root,_=self.fixture();owner=self.run_loader(root,BAD_OWNER='1')
        self.assertEqual(owner.returncode,100);self.assertNotIn(b'INSERT',owner.stdout)
        failed=self.run_loader(root,FAIL_AT='3')
        self.assertEqual(failed.returncode,100)
        self.assertEqual(failed.stdout.count(b'INSERT index='),4)
        self.assertEqual(failed.stdout.count(b'INSERT index=3'),1)
        self.assertIn(b'FAIL=ufs-module-insertion',failed.stderr)
        self.assertNotIn(b'COMPLETE',failed.stdout)

    def test_loader_composition_preserves_existing_runtime_and_collectors(self):
        identity=source.resident.common.Identity('p998','a'*32,'v0.2.2')
        census=(source.resident.common.MemoryModule('fixture.ko',1,0o644),)
        old=source.previous.render_display(identity,census)
        new=source.render_display(identity,census)
        restored=new.replace(source.loader_source()+b'\n',b'',1).replace(
            b'    p351_prepare_driver();\n    ufs1_prepare();',b'    p351_prepare_driver();',1)
        self.assertEqual(restored,old)
        self.assertLess(new.index(b'    ufs1_prepare();'),new.index(b'    p350_drop_privileges();'))
        self.assertEqual(source.helper_template(identity),source.previous.helper_template(identity))

    def test_newly_loaded_ufs_files_are_excluded_from_unselected_file_census(self):
        identity=source.resident.common.Identity('p998','a'*32,'v0.2.2')
        row=source.resident.common.MemoryModule
        modules=tuple(sorted([row('fixture.ko',1,0o644)]+
            [row(name,size,0o644) for name,_,size,_ in source.MODULES],key=lambda item:item.name))
        rendered=source.render_display(identity,modules)
        self.assertIn(b'#define MS_MANIFEST_COUNT 1U',rendered)
        self.assertIn(b'{"fixture.ko", 1ULL, 0644U}',rendered)


if __name__=='__main__':unittest.main()
