"""Generated PID1/root-console with actual host IPC and a fixture DRM child.

Device modules/credentials/DRM are explicit fixtures; no target device access.
"""
from pathlib import Path
import os
import signal
import socket
import subprocess
import tempfile
import time
import unittest
from unittest import mock
import test_s22plus_fyg8_p375_console_integration as predecessor
import device_action_f1_live_v2 as live
import s22plus_fyg8_p376_research_shell_runtime as runtime
import s22plus_fyg8_p376_research_shell_observer as observer
import test_s22plus_fyg8_p376_hud_renderer as renderer_test


def source():
    with mock.patch.object(predecessor,'runtime',runtime):value=predecessor.source().replace('p375','p376')
    value=value.replace('out->tv_sec=t.tv_sec*30+(t.tv_nsec*30)/1000000000;out->tv_nsec=(t.tv_nsec*30)%1000000000;return 0;',
        'out->tv_sec=t.tv_sec;out->tv_nsec=t.tv_nsec;return 0;')
    # P376 intentionally does not await HUD exit before Download. The old
    # fixture's all-children-reaped assertion encoded the P375-only lifecycle.
    value=value.replace('if(p!=-1||errno!=ECHILD)_Exit(91);',
        'if(p!=-1||errno!=ECHILD)fx_mark("hud-unreaped-at-park",0);')
    value=value.replace('#include <sys/syscall.h>','#include <sys/syscall.h>\n#include <sys/socket.h>')
    value=value.replace(' if(nr==25)return',''' if(nr==129)return neg(kill(a,b));
 if(nr==199){if(a!=1||b!=(5|O_NONBLOCK|O_CLOEXEC)||c!=0)_Exit(121);return neg(socketpair(a,b,c,(int*)d));}
 if(nr==206){if(d!=MSG_NOSIGNAL||e||f)_Exit(122);return neg(send(a,(void*)b,c,d));}
 if(nr==25)return''')
    value=value.replace('static long fx_openat(const char *p,int flags,int mode){','''static long fx_openat(const char *p,int flags,int mode){
 if(!strcmp(p,"/s22-root-work/hud.log")){char path[4096];snprintf(path,sizeof(path),"%s/hud.log",getenv("RC1_WORK"));if(flags!=(00000001|00000100|00000200|0100000|02000000))_Exit(127);return neg(open(path,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,mode));}''')
    start=value.index('if(!strcmp(p,"/s22-display")){');end=value.index('if(!strcmp(p,"/bin/busybox")){',start)
    child=r'''if(!strcmp(p,"/s22-display")){
 fx_mark("hud-child",0);
 if(getenv("HUD_RENDERER")&&*getenv("HUD_RENDERER")){char *args[]={getenv("HUD_RENDERER"),"ipc-live",NULL};return neg(execve(args[0],args,e));}
 if(fx_case("hud-exit"))_Exit(7);
 if(fx_case("hud-stall"))for(;;)usleep(10000);
 if(fx_case("hud-flood")){char data[512];memset(data,'x',sizeof(data));for(;;){ssize_t count=write(1,data,sizeof(data));if(count<0&&errno!=EAGAIN)_Exit(125);usleep(100);}}
 uint32_t last=0;
 for(;;){unsigned char bytes[40];ssize_t n=recv(0,bytes,sizeof(bytes),MSG_TRUNC);
  if(n<0&&(errno==EAGAIN||errno==EINTR)){usleep(1000);continue;}
  if(n!=40)_Exit(123);uint32_t seq,state;uint64_t up;memcpy(&seq,bytes+4,4);memcpy(&state,bytes+8,4);memcpy(&up,bytes+16,8);
  if(seq<=last)_Exit(124);last=seq;
  dprintf(1,"HUD_FRAME run=%s seq=%u uptime_ms=%llu state=%u event=matched visible=UNPROVED\n",a[2],seq,(unsigned long long)up,state);
 }
}'''
    value=value[:start]+child+value[end:]
    return value


class HudIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.folder=Path(cls.temp.name);cls.binary=cls.folder/'native'
        p=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation',
            '-o',str(cls.binary)],input=source(),text=True,capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)
        fixture,headers=renderer_test.fixture()
        (cls.folder/'renderer.c').write_bytes(renderer_test.renderer.render())
        (cls.folder/'renderer-fixture.c').write_text(fixture)
        cls.real_renderer=cls.folder/'renderer'
        built=subprocess.run(['cc','-O1','-Wall','-Wextra','-Werror','-D_DEFAULT_SOURCE','-I',str(headers),
            '-I',str(renderer_test.ROOT/'workspace/public/src/native-init'),str(cls.folder/'renderer-fixture.c'),
            '-o',str(cls.real_renderer)],capture_output=True,text=True)
        if built.returncode:raise AssertionError(built.stderr)

    def run_case(self,case,full=True):
        run=self.folder/(case+str(time.monotonic_ns()));run.mkdir()
        host,peer=socket.socketpair();host.setblocking(False);peer.setblocking(False)
        process=subprocess.Popen([str(self.binary),str(peer.fileno()),'1'],pass_fds=(peer.fileno(),),
            env=dict(os.environ,P364_CASE=case,P364_MARK=str(run/'marks'),RC1_WORK=str(run),HUD_RENDERER=getattr(self,'renderer','')),
            stderr=subprocess.PIPE,start_new_session=True);peer.close()
        codec=live._open_header_initial_observer_module(runtime,observer,'p376-integration')
        raw=bytearray();writer=type('Writer',(),{'write_stdout':lambda self,data:raw.extend(data)})();intents=[]
        result=error=None
        try:
            # Negative HUD cases keep all five real root commands and CONTROL;
            # the extra HUD proof remains unproved instead of masking it.
            try:result=observer.qualify(codec,host.fileno(),b'k'*32,None,set(),writer,
                deadline=time.monotonic()+20,before_control=intents.append,evidence=run/'console')
            except observer.QualificationError as exc:error=exc
            self.assertEqual(process.wait(timeout=3),0,process.stderr.read())
            marks=(run/'marks').read_text().splitlines()
            self.assertEqual(len(intents),1);self.assertEqual(marks.count('download 0'),1)
            log=(run/'hud.log').read_bytes()
            return result,error,log,marks
        finally:
            host.close()
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
            process.communicate(timeout=3)

    def test_hud_updates_while_root_commands_and_cancel_work(self):
        result,error,log,marks=self.run_case('normal')
        if error:raise AssertionError(repr(error.__cause__))
        self.assertTrue(result.receipt['proved']);self.assertEqual(result.receipt['qualified_command_count'],6)
        self.assertGreaterEqual(result.receipt['commands'][5]['hud']['busy_frames'],1)
        self.assertEqual(log.count(b'HUD_SIGNAL_ATTEMPT '),1)
        self.assertIn('hud-child 0',marks)
        audit=result.sessions[0].session.audit
        codec=live._open_header_initial_observer_module(runtime,observer,'p376-replay')
        self.assertEqual(observer.replay_session(codec,bytes(audit.rx),bytes(audit.tx),b'k'*32),result.receipt)

    def test_real_renderer_snapshot_decoder_and_console_share_boot(self):
        self.renderer=str(self.real_renderer)
        result,error,log,marks=self.run_case('normal')
        if error:raise AssertionError((repr(error.__cause__),log[-1500:]))
        self.assertTrue(result.receipt['proved']);self.assertGreaterEqual(log.count(b'HUD_FRAME '),3)
        self.assertEqual(log.count(b'HUD_SIGNAL_ATTEMPT '),1)

    def test_failed_and_parked_hud_preserve_commands_and_control(self):
        for case in ('hud-exit','hud-stall','hud-flood'):
            with self.subTest(case=case):
                result,error,log,marks=self.run_case(case)
                self.assertIsNone(result);self.assertIsNotNone(error)
                proof=error.partial_receipt
                self.assertFalse(proof['proved']);self.assertTrue(proof['control_acceptance_observed'])
                self.assertEqual(len(proof['commands']),6)
                self.assertTrue(all(row['accepted'] and row['terminal'] is not None for row in proof['commands']))
                self.assertLessEqual(len(log),131072)
                self.assertLessEqual(log.count(b'HUD_SIGNAL_ATTEMPT '),1)

if __name__=='__main__':unittest.main()
