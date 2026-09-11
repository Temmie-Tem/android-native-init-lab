"""Actual resident C/IPC with explicit clocks, proc/sysfs, USB and DRM fixtures."""
from contextlib import contextmanager
import os
from pathlib import Path
import pty
import signal
import subprocess
import tempfile
import time
import tty
from types import SimpleNamespace

import test_s22plus_native_resident_v1 as previous
import s22plus_fyg8_p386_candidate as candidate
import s22plus_native_resident_source_v1 as source

CLOCK_HEADER=r'''
#ifndef RESIDENT_ADOPTION_FIXTURE_CLOCK_H
#define RESIDENT_ADOPTION_FIXTURE_CLOCK_H
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/syscall.h>
#include <unistd.h>
static uint64_t resident_fixture_offset(void){
 char path[4096];assert(snprintf(path,sizeof(path),"%s/resident-offset",getenv("RC1_WORK"))>0);
 FILE *file=fopen(path,"r");unsigned long long offset=0;
 if(file){assert(fscanf(file,"%llu",&offset)==1);assert(fclose(file)==0);}
 return offset;
}
static uint64_t resident_fixture_ms(void){
 uint64_t offset=resident_fixture_offset();struct timespec t;assert(syscall(SYS_clock_gettime,CLOCK_BOOTTIME,&t)==0);
 return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000+offset;
}
static __attribute__((unused)) int resident_fixture_clock(clockid_t id,struct timespec *out){
 assert(id==CLOCK_BOOTTIME);uint64_t ms=resident_fixture_ms();out->tv_sec=ms/1000;out->tv_nsec=ms%1000*1000000;return 0;
}
#endif
'''


def native_source():
    raw=previous.native_fixture()
    old,new=previous.IDENTITY,candidate.IDENTITY
    # Fixture platform identity is explicit data; production helper is generated
    # by the resident composition in the inherited fixture before instrumentation.
    for before,after in ((old.namespace,new.namespace),(old.namespace.upper(),new.namespace.upper()),
        (old.run_id_hex,new.run_id_hex),
        (','.join(str(v) for v in bytes.fromhex(old.run_id_hex)),','.join(str(v) for v in bytes.fromhex(new.run_id_hex))),
        (''.join(f'\\x{v:02x}' for v in old.run_id_hex.encode()),''.join(f'\\x{v:02x}' for v in new.run_id_hex.encode()))):
        assert before in raw;raw=raw.replace(before,after)
    raw=previous.swap(raw,'uint64_t ms=((uint64_t)t.tv_sec*1000+t.tv_nsec/1000000)*rate+fx_clock_offset_ms;',
        'uint64_t ms=resident_fixture_ms();')
    # The production workers receive a minimal environment. Host fixture workers
    # additionally need their clock-file and explicit sensor-case environment.
    assert raw.count('execve(args[0],args,e)')==2
    raw=raw.replace('execve(args[0],args,e)','execve(args[0],args,environ)')
    raw=previous.swap(raw,'const char *command=text;',r'''
const char *command=text;char resident_probe[8192];
if(strstr(command,"S22RPROBE1")){
 char path[4096];snprintf(path,sizeof(path),"%s/resident-uptime",getenv("RC1_WORK"));
 uint64_t ms=resident_fixture_ms();FILE *u=fopen(path,"w");if(!u)_Exit(144);
 fprintf(u,"%llu.%02llu 0.00\n",(unsigned long long)(ms/1000),(unsigned long long)(ms%1000/10));
 if(fclose(u))_Exit(145);
 int n=snprintf(resident_probe,sizeof(resident_probe),"printf 'S22RPROBE1\\n' && cat '%s' && cat hud.log && printf 'S22RPROBE1 COMPLETE\\n'",path);
 if(n<=0||(size_t)n>=sizeof(resident_probe))_Exit(146);command=resident_probe;
 if(fx_case("hud-read-fails"))command="exit 7";
}
''')
    return '#include "resident-fixture-clock.h"\n'+raw


def compile_c(*args):
    try:previous.compile_c(*args)
    except subprocess.CalledProcessError as exc:raise AssertionError(exc.stderr) from exc


def compile_components(cls):
    cls.temp=tempfile.TemporaryDirectory(prefix='s22-resident-adoption-h0-');cls.addClassCleanup(cls.temp.cleanup)
    cls.folder=Path(cls.temp.name)
    (cls.folder/'resident-fixture-clock.h').write_text(CLOCK_HEADER)
    (cls.folder/'native.c').write_text(native_source());cls.binary=cls.folder/'native'
    compile_c(cls.folder/'native.c',cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')
    raw=source.render_display(candidate.IDENTITY,previous.CENSUS)
    (cls.folder/'renderer.c').write_bytes(raw)
    renderer=previous.renderer_fixture().replace(previous.IDENTITY.run_id_hex,candidate.IDENTITY.run_id_hex)
    renderer=previous.swap(renderer,'if(!strcmp(scenario,"ipc-live"))return syscall(SYS_clock_gettime,id,value);',
        'if(!strcmp(scenario,"ipc-live"))return resident_frame_clock(id,value);')
    # Apply accelerated clock jumps between frame snapshots. A real suspend
    # during an in-flight flip belongs to the separately retained DRM fault
    # corpus, not this nominal clock-accelerated integration fixture.
    renderer=previous.swap(renderer,'if(!strcmp(scenario,"ipc-live"))return syscall(SYS_recvfrom,f,out,size,flags,NULL,NULL);',
        'if(!strcmp(scenario,"ipc-live")){ssize_t n=syscall(SYS_recvfrom,f,out,size,flags,NULL,NULL);'
        'if(n>0)resident_frame_offset=resident_fixture_offset();return n;}')
    renderer=previous.swap(renderer,'static unsigned commits, handles,retired,unmapped,closed,flips,pending;',
        '#include "resident-fixture-clock.h"\nstatic uint64_t resident_frame_offset;\n'
        'static int resident_frame_clock(clockid_t id,struct timespec *out){struct timespec t;'
        'assert(id==CLOCK_BOOTTIME&&syscall(SYS_clock_gettime,id,&t)==0);'
        'uint64_t ms=(uint64_t)t.tv_sec*1000+t.tv_nsec/1000000+resident_frame_offset;'
        'out->tv_sec=ms/1000;out->tv_nsec=ms%1000*1000000;return 0;}\n'
        'static unsigned commits, handles,retired,unmapped,closed,flips,pending;')
    (cls.folder/'drm.c').write_text(renderer);cls.renderer=cls.folder/'renderer'
    compile_c(cls.folder/'drm.c',cls.renderer,'-D_DEFAULT_SOURCE')
    raw=source.replace(raw,b'static int status_read(const char *path,char *text,size_t capacity,long filesystem) {',
        b'static int status_read(const char *,char *,size_t,long);\n'
        b'static __attribute__((unused)) int actual_status_read(const char *path,char *text,size_t capacity,long filesystem) {')
    (cls.folder/'collector-renderer.c').write_bytes(raw)
    (cls.folder/'telemetry_core.h').write_bytes(source.provider_sources()['telemetry_core.h'])
    metrics=(source.ROOT/'tests/s22plus_resident_metrics_harness.c').read_text()
    metrics=metrics.replace('#include "renderer.c"','#include "collector-renderer.c"')
    metrics=previous.swap(metrics,'if(real_output)return clock_gettime(id,out);','if(real_output)return resident_fixture_clock(id,out);')
    metrics=previous.swap(metrics,'if(real_output)return nanosleep(delay,remain);',
        'if(real_output)return nanosleep(&(struct timespec){0,2000000},remain);')
    metrics=previous.swap(metrics,'assert(argc==3);scenario=argv[2];real_output=!strcmp(scenario,"ipc");',
        'assert(argc==3);scenario=getenv("P364_CASE");if(!scenario)scenario="normal";real_output=1;')
    metrics=previous.swap(metrics,'return status_collect("42424242424242424242424242424242",(unsigned)atoi(argv[1]));',
        'assert(!strcmp(argv[1],"--collect-system")||!strcmp(argv[1],"--collect-hardware"));'
        'return status_collect(argv[2],!strcmp(argv[1],"--collect-hardware"));')
    metrics=previous.swap(metrics,'#undef open\n#include "telemetry_core.h"',
        '#undef open\n#include "resident-fixture-clock.h"\n#include "telemetry_core.h"')
    (cls.folder/'metrics.c').write_text(metrics);cls.collector=cls.folder/'collector'
    compile_c(cls.folder/'metrics.c',cls.collector)
    import device_action_f1_live_v2 as live
    cls.codec=live._open_header_initial_observer_module(candidate.runtime,candidate.observer,'p386-resident-h0')


class Fixture:
    @contextmanager
    def running(self,case='normal',folder=None):
        folder=Path(folder) if folder is not None else self.folder/str(time.monotonic_ns())
        folder.mkdir(exist_ok=True);master,fd=pty.openpty();tty.setraw(fd)
        os.set_blocking(master,False);os.set_blocking(fd,False);name=os.ttyname(fd)
        proc=subprocess.Popen([self.binary,str(master),'1'],pass_fds=(master,),start_new_session=True,
            stderr=subprocess.PIPE,env=dict(os.environ,P364_CASE=case,P364_MARK=str(folder/'marks'),RC1_WORK=str(folder),
                HUD_RENDERER=str(self.renderer),METRICS_COLLECTOR=str(self.collector),LOCAL_CLOCK_RATE='1'))
        os.close(master);ctx=SimpleNamespace(folder=folder,fd=fd,proc=proc,name=name,offset_ms=0)
        try:yield ctx
        finally:
            if ctx.fd is not None:os.close(ctx.fd)
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            _,err=proc.communicate(timeout=3)
            if proc.returncode not in (-signal.SIGKILL,0):raise AssertionError((proc.returncode,err,(folder/'marks').read_text()))

    @staticmethod
    def advance(ctx,millis):
        ctx.offset_ms+=millis
        (ctx.folder/'resident-offset-next').write_text(str(ctx.offset_ms))
        (ctx.folder/'resident-offset-next').replace(ctx.folder/'resident-offset')

    @staticmethod
    def reopen(ctx):
        os.close(ctx.fd);ctx.fd=os.open(ctx.name,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC);tty.setraw(ctx.fd)
