"""Generated renderer and supervisor, real eventfd/fork/exec, fixture DRM/USB."""
from pathlib import Path
import importlib
import ast
import json
import subprocess
import sys
import textwrap
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'workspace/public/src/scripts/analysis'),str(ROOT/'workspace/public/src/scripts/revalidation'),str(ROOT/'tests')]
import s22plus_fyg8_display_kms_contract_h0 as kms
import test_s22plus_fyg8_p364_diagnostics as diagnostics


def renderer_fixture():
    # Reuse the established exact DRM property/paint oracle generator.
    previous=(ROOT/'tests/test_s22plus_fyg8_p361_renderer.py').read_text()
    begin=previous.index("        headers=ROOT/")
    end=previous.index("        (out/'renderer.c')",begin)
    ns=dict(ROOT=ROOT,json=json,kms=kms)
    tree=ast.parse(previous)
    setup=next(n for n in tree.body if isinstance(n,ast.ClassDef)).body[0]
    lo=previous[:begin].count('\n')+1;hi=previous[:end].count('\n')+1
    unit=ast.Module(body=[n for n in setup.body if lo<=n.lineno<hi],type_ignores=[])
    exec(compile(unit,'existing-drm-oracle','exec'),ns)
    source=ns['source']
    begin=source.index('int fake_nanosleep(');end=source.index('int fake_ioctl(',begin)
    source=source[:begin]+'''int fake_nanosleep(const struct timespec *d,struct timespec *r){return syscall(SYS_nanosleep,d,r);}
ssize_t fake_read(int fd,void *out,size_t n){assert(fd==0);return syscall(SYS_read,fd,out,n);}
'''+source[end:]
    source='#include <sys/syscall.h>\n'+source
    source=source[:source.index('int main(int argc')]+'''int main(int argc,char **argv){assert(argc==4);scenario=argv[3];char *args[]={argv[0],argv[1],argv[2],NULL};return renderer_main(3,args);}
'''
    return source,ns['headers']


def build_renderer(folder,prefix):
    renderer=importlib.import_module('s22plus_fyg8_'+prefix+'_display_renderer')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    source,headers=renderer_fixture()
    (folder/'renderer.c').write_bytes(renderer.render())
    (folder/'fixture.c').write_text(source)
    binary=folder/'renderer'
    p=subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-D_DEFAULT_SOURCE','-I',str(headers),'-I',str(ROOT/'workspace/public/src/native-init'),str(folder/'fixture.c'),'-o',str(binary)],capture_output=True)
    if p.returncode:raise AssertionError(p.stderr.decode())
    return binary


def native_source(prefix):
    runtime=importlib.import_module('s22plus_fyg8_'+prefix+'_research_shell_runtime')
    with mock.patch.object(diagnostics,'runtime',runtime):source=diagnostics.source().replace('p364',prefix)
    source=source.replace('#include <sys/prctl.h>','#include <sys/prctl.h>\n#include <sys/eventfd.h>')
    source=source.replace(' if(nr==25)return', ' if(nr==19)return neg(eventfd((unsigned)a,(int)b));\n if(nr==25)return')
    begin=source.index('if(!strcmp(p,"/s22-display")){');end=source.index('return neg(execve(p,a,e));',begin)
    source=source[:begin]+'''if(!strcmp(p,"/s22-display")){
 fx_mark("child",0);
 char *args[]={a[0],a[1],a[2],(char*)"success",NULL};
 if(fx_case("step-stall"))for(;;)usleep(10000);
 if(fx_case("step-early-exit"))_Exit(9);
 return neg(execve(getenv("DISPLAY_STEP_RENDERER"),args,e));
}'''+source[end:]
    source=source.replace('static long fx_write(int fd,const void*p,size_t n){', 'static long fx_write(int fd,const void*p,size_t n){\n if(fx_prepared && n==8 && fx_case("step-write-error")){fx_mark("step-write",0);return -EAGAIN;}\n if(fx_prepared && n==8 && fx_case("step-short-write")){fx_mark("step-write",0);return 4;}\n if(n==52 && ((const unsigned char*)p)[5]==0x90 && fx_case("step-ack-partial")){fx_partial=1;fx_mark("step-ack",0);return neg(write(fd,p,7));}')
    # Keep the established scaled native clock for bounded host tests.
    source=source.replace('long rc=p241_clock_gettime(out);out->tv_sec+=seconds;return rc;', 'long rc=p241_clock_gettime(out);if(rc)_Exit(104);out->tv_sec+=seconds;return rc;')
    source=source.replace('struct timespec64 d;p282_deadline_after(seconds,&d);','struct timespec64 d={0};p282_deadline_after(seconds,&d);')
    # Keep fixture PTY alive until its already-written ACK can be read; closing
    # a PTY master immediately discards queued bytes after an already-exited child.
    source=source.replace('fx_mark("park",0);_Exit(0);','fx_mark("park",0);usleep(50000);_Exit(0);')
    return source


def build_native(folder,prefix):
    binary=Path(folder)/'native'
    p=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-o',str(binary)],input=native_source(prefix),text=True,capture_output=True,timeout=30)
    if p.returncode:raise AssertionError(p.stderr)
    return binary
