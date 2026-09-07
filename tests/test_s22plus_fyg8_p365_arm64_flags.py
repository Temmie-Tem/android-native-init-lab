"""Real ARM64 opens and generated provider/module functions; no module insertion.

The fixed sysfs root is mapped to a private fixture. Module fstat/read/hash/seek
are real; only fixture owner IDs are normalized and finit_module is a rejecting
same-FD witness stub. Privileged target setup and USB are outside this test.
"""
from pathlib import Path
import hashlib,os,shutil,subprocess,tempfile,unittest
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_fyg8_p365_research_shell_runtime as runtime

PAYLOAD=b'P365 inert module fixture\n'

def function(source,name):
    a=source.index('static long '+name+'(')
    return source[a:source.index('\n}',a)+2]

def source():
    helper=runtime.build_helper(runtime.fixture_child_source()).decode()
    parser=(ROOT/'workspace/public/src/native-init/s22plus_fyg8_p318_max77705_result_parser.inc.c').read_text()
    sha=parser[parser.index('struct s22plus_max77705_runtime_sha256 {'):parser.index('static int s22plus_max77705_runtime_expect(')]
    sha+=parser[parser.index('static uint32_t s22plus_max77705_runtime_rotr('):parser.index('static int s22plus_max77705_runtime_active_timeout_slot(')]
    native=(ROOT/'workspace/public/src/native-init/s22plus_fyg8_p241_e2_runtime.c').read_text()
    a=native.index('struct s22_p241_kernel_stat {');stat=native[a:native.index('\n};',a)+3]
    prefix=r'''
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>
#undef st_atime
#undef st_mtime
#undef st_ctime
#define P260_EPROTO EPROTO
#define P260_EOVERFLOW EOVERFLOW
FLAG_DECLARATION
_Static_assert(S22_ARM64_O_DIRECTORY==O_DIRECTORY,"target O_DIRECTORY ABI");
_Static_assert(S22_ARM64_O_NOFOLLOW==O_NOFOLLOW,"target O_NOFOLLOW ABI");
_Static_assert(SYS_openat==56 && SYS_fstat==80 && SYS_lseek==62,"target syscall ABI");
STAT_DECLARATION
_Static_assert(sizeof(struct s22_p241_kernel_stat)==128,"stat ABI size");
_Static_assert(offsetof(struct s22_p241_kernel_stat,st_mode)==offsetof(struct stat,st_mode),"stat mode ABI");
struct s22_p241_linux_dirent64 {uint64_t d_ino;int64_t d_off;uint16_t d_reclen;uint8_t d_type;char d_name[];};
struct p365_return_module {const char *path;uint64_t size;uint8_t hash[32];const char *params;};
static struct p365_return_module p365_return_modules[1];
static int opened=-1,insertions=0;
static long neg(long n){return n<0?-errno:n;}
static size_t cstr_len(const char*s){return strlen(s);}
static int p260_bytes_equal(const char*a,const char*b,size_t n){return memcmp(a,b,n)==0;}
static int p328_constant_time_equal(const uint8_t*a,const uint8_t*b,size_t n){unsigned d=0;for(size_t i=0;i<n;i++)d|=a[i]^b[i];return !d;}
static long p282_make_path(char*out,size_t cap,const char*a,const char*b,const char*c){size_t n=strlen(a)+strlen(b)+strlen(c);if(!cap)return -EINVAL;if(n>=cap)return -EOVERFLOW;memcpy(out,a,strlen(a));memcpy(out+strlen(a),b,strlen(b));memcpy(out+strlen(a)+strlen(b),c,strlen(c)+1);return 0;}
static const char *map_path(const char*p){static char b[1024];const char*root="/sys/bus/nvmem/devices";size_t n=strlen(root);if(strncmp(p,root,n))return p;if(snprintf(b,sizeof(b),"%s%s",getenv("P365_FIXTURE"),p+n)>=(int)sizeof(b))abort();return b;}
static long sys_openat(const char*p,int flags,unsigned mode){long n=neg(syscall(SYS_openat,AT_FDCWD,map_path(p),flags,mode));opened=(int)n;printf("open=%ld flags=%#o\n",n,flags);return n;}
static long sys_read(int fd,void*p,size_t n){return neg(syscall(SYS_read,fd,p,n));}
static long sys_close(int fd){return neg(syscall(SYS_close,fd));}
static long p241_getdents64(int fd,void*p,size_t n){return neg(syscall(SYS_getdents64,fd,p,n));}
static long p241_readlinkat(const char*p,char*b,size_t n){return neg(syscall(SYS_readlinkat,AT_FDCWD,map_path(p),b,n));}
static long syscall6(long nr,long a,long b,long c,long d,long e,long f){
 if(nr==SYS_fstat){long rc=neg(syscall(nr,a,b));if(!rc){struct s22_p241_kernel_stat*s=(void*)b;if(s->st_uid!=getuid()||s->st_gid!=getgid())return -EPROTO;s->st_uid=s->st_gid=0;}return rc;}
 if(nr==SYS_lseek)return neg(syscall(nr,a,b,c));
 (void)d;(void)e;(void)f;abort();
}
static long p241_finit_module(int fd,const char*params){if(fd!=opened||strcmp(params,"")||syscall(SYS_lseek,fd,0,SEEK_CUR)!=0)abort();insertions++;return 0;}
static long p365_diag_enter(uint16_t stage){(void)stage;return 0;}
static long p365_diag_result(uint16_t stage,long code){(void)stage;return code;}
'''
    prefix=prefix.replace('FLAG_DECLARATION',runtime.FLAG_SOURCE.read_text()).replace('STAT_DECLARATION',stat)
    module=function(helper,'p365_insert_module');provider=function(helper,'p365_nvmem_providers')
    main=r'''
int main(int argc,char**argv){
 if(argc!=3)return 2;long rc;
 if(!strcmp(argv[1],"provider"))rc=p365_nvmem_providers();
 else if(!strcmp(argv[1],"module")){const uint8_t hash[32]={HASH_BYTES};p365_return_modules[0].path=argv[2];p365_return_modules[0].size=PAYLOAD_SIZE;p365_return_modules[0].params="";memcpy(p365_return_modules[0].hash,hash,32);rc=p365_insert_module(&p365_return_modules[0]);}
 else return 3;
 printf("result=%ld insertions=%d\n",rc,insertions);return 0;
}
'''.replace('HASH_BYTES',','.join(str(n) for n in hashlib.sha256(PAYLOAD).digest())).replace('PAYLOAD_SIZE',str(len(PAYLOAD)))
    return prefix+sha+module+'\n'+provider+main

class Arm64FlagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which('aarch64-linux-gnu-gcc');cls.qemu=shutil.which('qemu-aarch64')
        if not compiler or not cls.qemu:raise unittest.SkipTest('ARM64 compiler and qemu required')
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name);cls.binary=cls.root/'probe'
        result=subprocess.run([compiler,'-x','c','-','-static','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-o',str(cls.binary)],input=source(),text=True,capture_output=True,timeout=30)
        if result.returncode:raise AssertionError(result.stderr)
        result=subprocess.run(['file',str(cls.binary)],text=True,capture_output=True,check=True)
        if 'ARM aarch64' not in result.stdout:raise AssertionError(result.stdout)
    def setUp(self):
        self.case=tempfile.TemporaryDirectory(dir=self.root);self.addCleanup(self.case.cleanup)
        self.fixture=Path(self.case.name)
        for name,addr in [('spmi_sdam1','7100'),('spmi_sdam11','7200')]:
            p=self.fixture/name;p.mkdir();(p/'of_node').symlink_to('../../firmware/devicetree/base/soc/qcom,spmi@c42d000/qcom,pmk8350@0/sdam@'+addr)
        self.file=self.fixture/'module';self.file.write_bytes(PAYLOAD);self.file.chmod(0o400)
        self.link=self.fixture/'module-link';self.link.symlink_to('module')
    def run_probe(self,mode,path=None,root=None):
        p=subprocess.run([self.qemu,str(self.binary),mode,str(path or self.file)],env=dict(os.environ,P365_FIXTURE=str(root or self.fixture)),text=True,capture_output=True,timeout=5,check=True)
        return p.stdout
    def test_providers_and_directory_type(self):
        self.assertIn('result=0 insertions=0',self.run_probe('provider'))
        self.assertIn('result=-20 insertions=0',self.run_probe('provider',root=self.file))
    def test_missing_or_invalid_provider_link(self):
        p=self.fixture/'spmi_sdam1/of_node';p.unlink()
        self.assertIn('result=-2 insertions=0',self.run_probe('provider'))
        p.write_text('not a symlink')
        self.assertIn('result=-22 insertions=0',self.run_probe('provider'))
    def test_exact_generated_module_same_fd_path_and_symlink_rejection(self):
        self.assertIn('result=0 insertions=1',self.run_probe('module'))
        self.assertIn('result=-40 insertions=0',self.run_probe('module',self.link))
    def test_module_hash_and_metadata_reject_before_insertion(self):
        self.file.chmod(0o600)
        self.assertIn('result=-71 insertions=0',self.run_probe('module'))
        self.file.write_bytes(bytes([PAYLOAD[0]^1])+PAYLOAD[1:]);self.file.chmod(0o400)
        self.assertIn('result=-71 insertions=0',self.run_probe('module'))

if __name__=='__main__':unittest.main()
