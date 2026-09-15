"""Real ARM64 algorithm and direct-I/O callbacks over private regular files."""
import binascii
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'workspace/public/src/scripts/analysis'),
    str(ROOT/'workspace/public/src/scripts/revalidation')]
import s22plus_native_gpt_layout_h0 as plan
import s22plus_native_gpt_profile_v1 as profile
from test_s22plus_native_gpt_layout_h0 import original

TOTAL=62_305_280
NATIVE=ROOT/'workspace/public/src/native-init'


def reference(*,android32=False):
    a,b,_,_=original(duplicate=True)
    a,b=bytearray(a),bytearray(b)
    struct.pack_into('<II',a,454,1,TOTAL-1)
    table=bytearray(a[8192:8192+5632])
    struct.pack_into('<Q',table,39*128+40,TOTAL-10)
    for blob,offset,current,alternate,table_lba in ((a,4096,1,TOTAL-1,2),
            (b,32768,TOTAL-1,1,TOTAL-9)):
        struct.pack_into('<QQ',blob,offset+24,current,alternate)
        struct.pack_into('<Q',blob,offset+48,TOTAL-10)
        struct.pack_into('<Q',blob,offset+72,table_lba)
        start=8192 if current==1 else 0
        blob[start:start+len(table)]=table
        struct.pack_into('<I',blob,offset+88,binascii.crc32(table)&0xffffffff)
        struct.pack_into('<I',blob,offset+16,0)
        struct.pack_into('<I',blob,offset+16,binascii.crc32(blob[offset:offset+92])&0xffffffff)
    regions,_=plan.construct(bytes(a),bytes(b),TOTAL,native_guid=b'N'*16,native_bytes=128*1024**3)
    if android32:
        current=[r['proposed'] for r in regions]
        regions,_=plan.construct(*current,TOTAL,userdata_bytes=32*1024**3)
    return b''.join(r['original'] for r in regions),b''.join(r['proposed'] for r in regions)


CALLBACK_TEST=r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>
#include "s22plus_native_gpt_core_v1.h"
@VECTORS@
static const char gpt1_target_run_id[]="h0-fixture-only";
/* Only ownership is synthesized for this private sysfs fixture. Actual ARM64
 * open/read/stat calls, numeric parsing and original/proposed selection run. */
static int h0_fstat(int fd,struct stat *st) {
    int rc=fstat(fd,st); if(!rc)st->st_uid=0; return rc;
}
static int h0_lstat(const char *path,struct stat *st) {
    int rc=lstat(path,st); if(!rc)st->st_uid=0; return rc;
}
#define fstat h0_fstat
#define lstat h0_lstat
#include "s22plus_native_gpt_io_v1.inc.c"
#undef fstat
#undef lstat
static void text_file(const char *folder,const char *name,uint64_t value) {
    char path[PATH_MAX]; assert(snprintf(path,sizeof(path),"%s/%s",folder,name)>0);
    FILE *f=fopen(path,"w"); assert(f); assert(fprintf(f,"%" PRIu64 "\n",value)>0); assert(!fclose(f));
}
static void native_geometry_fixture(const char *file) {
    char parent[PATH_MAX],part[PATH_MAX],path[PATH_MAX];
    assert(snprintf(parent,sizeof(parent),"%s-sys/sda",file)>0);
    char top[PATH_MAX]; assert(snprintf(top,sizeof(top),"%s-sys",file)>0); assert(!mkdir(top,0700));
    assert(!mkdir(parent,0700)); assert(snprintf(part,sizeof(part),"%s/sda41",parent)>0);
    uint64_t value=0;
    const uint8_t *pair[]={gpt1_original,gpt1_proposed};
    for(unsigned i=0;i<2;i++) {
        const uint8_t *entry=pair[i]+2U*GPT1_BLOCK+40U*128U;
        uint64_t low=gpt1_little64(entry+32),high=gpt1_little64(entry+40);
        if(!low) {
            assert(!gpt1_native_partition(parent,gpt1_userdata_sectors(pair[i]),&value)&&value==0);
            continue;
        }
        if(mkdir(part,0700))assert(errno==EEXIST);
        text_file(part,"partition",41); text_file(part,"start",low*8U);
        text_file(part,"size",(high-low+1U)*8U);
        assert(snprintf(path,sizeof(path),"%s/uevent",part)>0);
        FILE *f=fopen(path,"w");assert(f);assert(fputs("MAJOR=8\nPARTNAME=native_data\n",f)>=0);assert(!fclose(f));
        assert(!gpt1_native_partition(parent,gpt1_userdata_sectors(pair[i]),&value));
        assert(value==(high-low+1U)*8U);
        text_file(part,"start",low*8U+8U);
        assert(gpt1_native_partition(parent,gpt1_userdata_sectors(pair[i]),&value));
        text_file(part,"start",low*8U);
    }
}
int main(int argc,char **argv) {
    assert(argc==2 || (argc==3 && !strcmp(argv[2],"apply-proof")));
    (void)gpt1_entry; /* Compiled endpoint, deliberately never called by H0. */
    assert(gpt1_userdata_sectors(gpt1_original)==@ORIGINAL_USER@ULL);
    assert(gpt1_userdata_sectors(gpt1_proposed)==@PROPOSED_USER@ULL);
    assert(gpt1_geometry_pair(gpt1_userdata_sectors(gpt1_original),
        gpt1_userdata_sectors(gpt1_proposed)));
    assert(!gpt1_geometry_pair((GPT1_TOTAL_LBAS-9U-3726848ULL)*8U,67108864ULL));
    assert(!gpt1_geometry_pair(@PROPOSED_USER@ULL,@ORIGINAL_USER@ULL));
    assert(!gpt1_geometry_pair(@ORIGINAL_USER@ULL,@ORIGINAL_USER@ULL));
    native_geometry_fixture(argv[1]);
    memcpy(gpt1_work,gpt1_proposed,GPT1_BYTES);
    memset(gpt1_work+2U*GPT1_BLOCK+39U*128U+32,0xff,16);
    assert(!gpt1_userdata_sectors(gpt1_work));
    int flags=O_RDWR|O_DIRECT|O_DSYNC|O_CLOEXEC|O_EXCL|O_NOFOLLOW;
    int f=open(argv[1],flags);
    assert(f>=0);
    struct stat st;
    assert(!fstat(f,&st) && S_ISREG(st.st_mode) && st.st_nlink==1 &&
        st.st_size==(off_t)(GPT1_TOTAL_LBAS*GPT1_BLOCK));
    int actual=fcntl(f,F_GETFL);
    assert((actual&(O_DIRECT|O_DSYNC|O_ACCMODE))==(O_DIRECT|O_DSYNC|O_RDWR));
    assert(fcntl(f,F_GETFD)&FD_CLOEXEC);
    struct gpt1_endpoint e={f,0};
    struct gpt1_io io={&e,gpt1_device_read,gpt1_device_write,gpt1_device_sync,gpt1_record};
    struct gpt1_result r;
    assert(gpt1_execute(GPT1_APPLY,&io,gpt1_original,gpt1_proposed,
        gpt1_work,gpt1_expected,&r)==GPT1_OK && r.final_kind==2 && r.writes_completed==4);
    assert(!memcmp(gpt1_work,gpt1_proposed,GPT1_BYTES));
    if(argc==3) {
        assert(!close(f));
        return gpt1_emit(GPT1_APPLY,GPT1_OK,0,0,&r,
            @ORIGINAL_USER@ULL,@ORIGINAL_NATIVE@ULL,0,0);
    }
    errno=0;
    assert(pread(f,gpt1_work+1,GPT1_BLOCK,0)==-1 && errno==EINVAL);
    assert(gpt1_device_write(&e,0,gpt1_original)==-1 && e.saved_errno==EPROTO);
    assert(!close(f));
    e.descriptor=open(argv[1],O_RDONLY|O_DIRECT|O_EXCL|O_NOFOLLOW|O_CLOEXEC);
    assert(e.descriptor>=0);
    assert(gpt1_device_write(&e,3,gpt1_original+3*GPT1_BLOCK)==-1 && e.saved_errno==EBADF);
    assert(!gpt1_device_read(&e,gpt1_work) && !memcmp(gpt1_work,gpt1_proposed,GPT1_BYTES));
    assert(!close(e.descriptor));
    e.descriptor=open(argv[1],flags);assert(e.descriptor>=0);e.saved_errno=0;
    assert(gpt1_execute(GPT1_RESTORE,&io,gpt1_original,gpt1_proposed,
        gpt1_work,gpt1_expected,&r)==GPT1_OK && r.final_kind==1 && r.writes_completed==4);
    assert(!memcmp(gpt1_work,gpt1_original,GPT1_BYTES));
    assert(!ftruncate(e.descriptor,GPT1_BLOCK));
    assert(gpt1_device_read(&e,gpt1_work)==-1 && e.saved_errno==EIO);
    assert(!close(e.descriptor));
    puts("PASS real_arm64_direct_sync_callbacks=1 unaligned_einval=1 readonly_ebadf=1 short_read_eio=1 block_endpoint_exercised=0");
    return 0;
}
'''


@unittest.skipUnless(shutil.which('aarch64-linux-gnu-gcc') and shutil.which('qemu-aarch64'),
                     'ARM64 toolchain/QEMU are required for target-ABI checks')
class GptTests(unittest.TestCase):
    android32=False
    @classmethod
    def setUpClass(cls):
        (ROOT/'workspace/private/tmp').mkdir(mode=0o700,parents=True,exist_ok=True)
        cls.directory=tempfile.TemporaryDirectory(prefix='gpt1-h0-',dir=ROOT/'workspace/private/tmp')
        cls.out=Path(cls.directory.name)
        cls.before,cls.after=reference(android32=cls.android32)
        for name,data in [('original',cls.before),('proposed',cls.after)]:
            (cls.out/(name+'.bin')).write_bytes(data)
        vectors='\n'.join('static const uint8_t gpt1_'+name+'[GPT1_BYTES] __attribute__((aligned(GPT1_BLOCK)))={'+
            ','.join(str(b) for b in data)+'};' for name,data in [('original',cls.before),('proposed',cls.after)])
        sealed=dict(original=cls.before,proposed=cls.after)
        old,new=profile.transition(sealed)
        source=CALLBACK_TEST.replace('@VECTORS@',vectors)
        for name,value in {'ORIGINAL_USER':old['userdata_sectors'],'PROPOSED_USER':new['userdata_sectors'],
                'ORIGINAL_NATIVE':old['native_sectors']}.items():source=source.replace('@'+name+'@',str(value))
        (cls.out/'callbacks.c').write_text(source)
        for name,source in [('core',ROOT/'tests/s22plus_native_gpt_core_v1_harness.c'),('callbacks',cls.out/'callbacks.c')]:
            subprocess.run(['aarch64-linux-gnu-gcc','-std=c11','-static','-O2','-Wall','-Wextra','-Werror',
                '-I',str(NATIVE),str(source),'-o',str(cls.out/name)],check=True,capture_output=True,timeout=30)
            kind=subprocess.check_output(['file','-b',str(cls.out/name)],text=True)
            if 'ARM aarch64' not in kind or 'statically linked' not in kind:raise AssertionError(kind)

    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()

    def test_actual_core_faults_and_adaptive_original_restore(self):
        run=subprocess.run(['qemu-aarch64',str(self.out/'core'),str(self.out/'original.bin'),
            str(self.out/'proposed.bin')],capture_output=True,text=True,timeout=15,check=True)
        self.assertFalse(run.stderr)
        self.assertRegex(run.stdout,r'^PASS apply_write_and_sync_faults=[1-9][0-9]* mixed_state_restores=[1-9][0-9]*')

    def test_actual_arm64_direct_sync_callbacks_on_sparse_regular_file(self):
        path=self.out/'metadata.sparse'
        with path.open('xb') as stream:
            stream.truncate(TOTAL*4096)
            stream.seek(0);stream.write(self.before[:24576])
            stream.seek((TOTAL-9)*4096);stream.write(self.before[24576:])
        self.assertLess(path.stat().st_blocks*512,1024*1024)
        run=subprocess.run(['qemu-aarch64',str(self.out/'callbacks'),str(path)],
            capture_output=True,text=True,timeout=15,check=True)
        self.assertFalse(run.stderr)
        self.assertIn('PASS real_arm64_direct_sync_callbacks=1',run.stdout)
        self.assertIn('block_endpoint_exercised=0',run.stdout)

    def test_actual_arm64_apply_output_is_consumed_by_the_live_profile_decoder(self):
        path=self.out/'proof.sparse'
        with path.open('xb') as stream:
            stream.truncate(TOTAL*4096);stream.write(self.before[:24576])
            stream.seek((TOTAL-9)*4096);stream.write(self.before[24576:])
        run=subprocess.run(['qemu-aarch64',str(self.out/'callbacks'),str(path),'apply-proof'],
            capture_output=True,timeout=15,check=True)
        self.assertFalse(run.stderr)
        value=profile.decode(run.stdout,'gpt-apply',dict(original=self.before,proposed=self.after))
        self.assertEqual((value['status'],value['writes'],value['final_pair']),('PASS_EXACT_GPT',4,'proposed'))


class Gpt32Tests(GptTests):
    android32=True


if __name__=='__main__':unittest.main()
