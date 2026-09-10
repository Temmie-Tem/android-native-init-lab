"""Bounded snapshot behavior with real tmpfs/stat calls on x86 and ARM64.

Only fixed paths, procfs identity and test-user credentials are adapted. Open
flags, sparse allocation metadata and reads run through the real host kernel.
"""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import time
import unittest
import s22plus_memory_snapshot_v1 as decoder

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'workspace/public/src/native-init/s22plus_memory_snapshot_v1.inc.c'
KEYS=('MemTotal MemAvailable MemFree RbinTotal RbinAlloced RbinFree RbinCached RbinPool '
      'CmaTotal CmaFree Shmem Cached Slab SReclaimable SUnreclaim KernelStack PageTables Percpu '
      'SwapTotal SwapFree HugepagePool AnonPages').split()

PREFIX=r'''
#define _GNU_SOURCE
#include <assert.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/vfs.h>
#include <time.h>
#include <unistd.h>
#include <linux/magic.h>
static const char *fixture,*scenario;static unsigned kind[4096];
static int fx_open(const char *path,int flags,...) {
 assert((flags&O_ACCMODE)==O_RDONLY&&!(flags&(O_CREAT|O_TRUNC)));
 char file[4096];unsigned k=0;
 if(!strcmp(path,"/")){snprintf(file,sizeof(file),"%s",fixture);k=1;}
 else if(!strncmp(path,"/proc/",6)){snprintf(file,sizeof(file),"%s/%s",fixture,path+6);k=2;}
 else {assert(!"unexpected fixed path");return -1;}
 int f=open(file,flags);if(f>=0){assert(f<4096);kind[f]=k;}return f;
}
static int fx_openat(int dir,const char *name,int flags,...) {
 assert((flags&O_ACCMODE)==O_RDONLY&&!(flags&(O_CREAT|O_TRUNC)));
 assert(!strstr(name,".ko")); /* A module content open is forbidden. */
 int f=openat(dir,name,flags);if(f>=0){assert(f<4096);kind[f]=!strcmp(name,"modules")?3:0;}return f;
}
static int fx_close(int f){kind[f]=0;return close(f);}
static void fixture_owner(struct stat *st) {if(st->st_uid==getuid())st->st_uid=0;if(st->st_gid==getgid())st->st_gid=0;}
static int fx_fstat(int f,struct stat *st){int rc=fstat(f,st);if(!rc){fixture_owner(st);if(kind[f]==3&&!strcmp(scenario,"mount-mismatch"))st->st_dev^=1;}return rc;}
static int fx_fstatat(int f,const char *name,struct stat *st,int flags){
 assert(flags==(AT_SYMLINK_NOFOLLOW|AT_NO_AUTOMOUNT));
 assert(strcmp(scenario,"wrongfs"));
 int rc=fstatat(f,name,st,flags);if(!rc){fixture_owner(st);if(!strcmp(scenario,"wrong-owner"))st->st_uid=1;}return rc;
}
static int fx_fstatfs(int f,struct statfs *fs){int rc=fstatfs(f,fs);if(!rc){
 if(kind[f]==2)fs->f_type=PROC_SUPER_MAGIC;
 else if(!strcmp(scenario,"wrongfs"))fs->f_type=EXT4_SUPER_MAGIC;
 }return rc;
}
#define open fx_open
#define openat fx_openat
#define close fx_close
#define fstat fx_fstat
#define fstatat fx_fstatat
#define fstatfs fx_fstatfs
#define MS_GEM_BUFFER_BYTES 10183680ULL
#define MS_MANIFEST_COUNT 3U
#define MS_MANIFEST_ROWS {"solid.ko",17ULL,0644U},{"sparse.ko",8192ULL,0644U},{"tiny.ko",4ULL,0644U}
'''
SUFFIX=r'''
int main(int argc,char **argv){assert(argc==4);fixture=argv[1];scenario=argv[2];return memory_snapshot(argv[3]);}
'''


def row(name,slabs,pages=1,objects=10):
    return f'{name} {objects} {objects} 64 64 {pages} : tunables 0 0 0 : slabdata {slabs} {slabs} 0\n'


class SnapshotCases:
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.binary=Path(cls.temp.name)/'memory'
        text=PREFIX+SOURCE.read_text()+SUFFIX
        if cls.arm:
            text+='\n_Static_assert(O_DIRECTORY==040000&&O_NOFOLLOW==0100000&&O_CLOEXEC==02000000,"target open flags");\n_Static_assert(AT_SYMLINK_NOFOLLOW==0x100&&AT_NO_AUTOMOUNT==0x800,"target stat flags");\n'
        cc='aarch64-linux-gnu-gcc' if cls.arm else 'cc'
        built=subprocess.run([cc,'-x','c','-','-static','-O2','-Wall','-Wextra','-Werror','-o',str(cls.binary)],
            input=text,text=True,capture_output=True,timeout=30)
        if built.returncode:raise AssertionError(built.stderr)
        info=subprocess.check_output(['file',str(cls.binary)],text=True)
        if cls.arm and 'ARM aarch64' not in info:raise AssertionError(info)
        cls.launcher=[shutil.which('qemu-aarch64'),str(cls.binary)] if cls.arm else [str(cls.binary)]

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='codex-s22-memory-',dir='/dev/shm');self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.modules=self.folder/'lib/modules';self.modules.mkdir(parents=True)
        self.work=self.folder/'s22-root-work';self.work.mkdir()
        for name,data in [('solid.ko',b'x'*17),('tiny.ko',b'tiny')]:
            p=self.modules/name;p.write_bytes(data);p.chmod(0o644)
        with (self.modules/'sparse.ko').open('wb') as f:f.truncate(8192)
        (self.modules/'sparse.ko').chmod(0o644)
        self.meminfo=''.join(f'{key}: {1000 if key=="MemTotal" else 900 if key=="MemAvailable" else 0} kB\n' for key in KEYS)
        (self.folder/'meminfo').write_text(self.meminfo)
        (self.folder/'cmdline').write_text('androidboot.serialno=DO_NOT_EXPORT kasan=off page_pinner=off kasan=on root=/private/device rootfstype=tmpfs\n')
        (self.folder/'slabinfo').write_text('slabinfo - version: 2.1\n# comment\n'+row('small',1)+row('large',20,2)+row('medium',5))
        stamp=int(time.monotonic()*1000)-1000
        self.gem=f'HUD_MEM seq=2 ms={stamp} alloc=2 retired=1 live=1 peak=2 bytes=10183680\n'
        (self.work/'hud.log').write_text('HUD_START 123\n'+self.gem);(self.work/'hud.log').chmod(0o400)

    def run_case(self,scenario='normal',phase='early'):
        before={p.name:(p.lstat().st_mode,p.lstat().st_size,p.lstat().st_blocks) for p in self.modules.iterdir()}
        p=subprocess.run([*self.launcher,str(self.folder),scenario,phase],capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stderr,b'');self.assertLessEqual(len(p.stdout),4096)
        self.assertTrue(p.stdout.startswith(b'S22MEM1 BEGIN phase='+phase.encode()))
        self.assertIn(b'S22MEM1 END phase='+phase.encode(),p.stdout)
        self.assertNotIn(b'DO_NOT_EXPORT',p.stdout);self.assertNotIn(b'/private/device',p.stdout)
        after={p.name:(p.lstat().st_mode,p.lstat().st_size,p.lstat().st_blocks) for p in self.modules.iterdir()}
        self.assertEqual(before,after)
        interpreted=decoder.parse(p.stdout,phase)
        self.assertTrue(interpreted['valid'],interpreted)
        self.assertFalse(interpreted['reclaimability_proved'])
        self.assertFalse(interpreted['kernel_gem_ownership_proved'])
        return p.stdout.decode()

    def test_full_snapshot_real_sparse_metadata_and_ordered_arguments(self):
        value=self.run_case()
        self.assertIn('MEM status=ok',value);self.assertIn('MemTotal=1000 MemAvailable=900',value)
        self.assertIn('arg0=kasan=off arg1=page_pinner=off arg2=kasan=on',value)
        self.assertIn('kasan_count=2',value);self.assertIn('page_pinner_count=1',value)
        allocated=sum(p.stat().st_blocks*512 for p in self.modules.iterdir())
        self.assertIn('metadata_match=3',value);self.assertIn('logical_bytes=8213',value)
        self.assertIn(f'allocated_metadata_bytes={allocated}',value);self.assertLess(allocated,8213)
        self.assertLess(value.index('CACHE name=large'),value.index('CACHE name=medium'))
        self.assertIn('nominal_bytes=163840',value);self.assertIn('GEM status=ok',value)
        self.assertIn('physical_bytes=NA',value)

    def test_missing_and_malformed_meminfo_are_not_zero(self):
        for data in [self.meminfo+'MemTotal: 1 kB\n',self.meminfo.replace('1000 kB','18446744073709551616 kB'),
                     *(self.meminfo.replace('1000 kB',bad) for bad in ('1000 MB','1000xkB','1000:kB','1000kB')),'x'*8193]:
            with self.subTest(kind=data[:30]):
                (self.folder/'meminfo').write_text(data);v=self.run_case();self.assertIn('MEM status=unavailable',v);self.assertNotIn('MemTotal=0',v)
        (self.folder/'meminfo').unlink();self.assertIn('MEM status=unavailable',self.run_case())

    def test_cmdline_truncation_never_claims_absence(self):
        (self.folder/'cmdline').write_text('a'*8193+' page_owner=on')
        value=self.run_case();self.assertIn('CMD status=unavailable',value);self.assertNotIn('page_owner_count=0',value)

    def test_mismatch_missing_symlink_and_wrong_owner_are_explicit(self):
        (self.modules/'tiny.ko').unlink();(self.modules/'tiny.ko').symlink_to(self.folder/'cmdline')
        (self.modules/'solid.ko').unlink()
        value=self.run_case();self.assertIn('status=partial expected=3 present=2 metadata_match=1 missing=1 mismatch=1',value)
        value=self.run_case('wrong-owner');self.assertIn('metadata_match=0',value)
        self.assertIn('FILES status=unavailable',self.run_case('mount-mismatch'))
        self.assertIn('FILES status=unavailable',self.run_case('wrongfs'))

    def test_parent_symlink_is_not_followed(self):
        (self.folder/'lib').rename(self.folder/'other');(self.folder/'lib').symlink_to('other')
        self.modules=self.folder/'other/modules'
        self.assertIn('FILES status=unavailable',self.run_case())

    def test_partial_slab_top_is_labelled_partial(self):
        for tail in [row('large',20,2),'broken\n',row('overflow',18446744073709551615,2),'x'*513+'\n','trailing']:
            with self.subTest(tail=tail[:25]):
                (self.folder/'slabinfo').write_text('slabinfo - version: 2.1\n'+row('large',20,2)+tail)
                self.assertIn('SLAB status=partial',self.run_case())

    def test_slab_byte_and_record_caps_are_explicit(self):
        (self.folder/'slabinfo').write_text('slabinfo - version: 2.1\n'+('# short\n'*40000))
        self.assertIn('SLAB status=partial',self.run_case())
        (self.folder/'slabinfo').write_text('slabinfo - version: 2.1\n'+''.join(row('cache'+str(i),1) for i in range(1025)))
        self.assertIn('SLAB status=partial',self.run_case())

    def test_stale_bad_and_regressed_gem_records(self):
        p=self.work/'hud.log';p.chmod(0o600)
        old=int(time.monotonic()*1000)-8000
        p.write_text(f'HUD_MEM seq=1 ms={old} alloc=1 retired=0 live=1 peak=1 bytes=10183680\n');p.chmod(0o400)
        self.assertIn('GEM status=stale',self.run_case())
        for suffix in ['HUD_MEM broken\n',self.gem,self.gem.replace('seq=2','seq=1')]:
            p.chmod(0o600);p.write_text(self.gem+suffix);p.chmod(0o400)
            self.assertIn('GEM status=unavailable',self.run_case())

    def test_section_format_overflow_still_finishes_packet(self):
        (self.folder/'cmdline').write_text(' '.join(['slub_debug='+('x'*65)]*20))
        value=self.run_case(phase='late');self.assertIn('CMD status=unavailable',value)

    def test_invalid_phase_does_no_snapshot(self):
        p=subprocess.run([*self.launcher,str(self.folder),'normal','invalid'],capture_output=True,timeout=5)
        self.assertEqual(p.returncode,126);self.assertEqual(p.stdout,b'')

    def test_decoder_rejects_changed_coverage_and_incomplete_terminal(self):
        raw=self.run_case().encode()
        for changed in [raw.replace(b'metadata_match=3',b'metadata_match=4'),
                        raw.replace(b'MemTotal=1000',b'MemTotal=1000 MemTotal=1000'),
                        raw.replace(b'nominal_bytes=163840',b'nominal_bytes=1'),raw[:-1],b'x'*4097]:
            self.assertFalse(decoder.parse(changed,'early')['valid'])
        for flags in (4,128,32|128):
            result=decoder.from_command(raw,'early',[3,flags,0,0,len(raw),0,1],b'')
            self.assertFalse(result['valid']);self.assertFalse(result['command_complete'])


class HostSnapshots(SnapshotCases,unittest.TestCase):arm=False
class Arm64Snapshots(SnapshotCases,unittest.TestCase):arm=True


if __name__=='__main__':unittest.main()
