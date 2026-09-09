"""Generated P375 auth/preparation/root console/CONTROL with fixture hardware.

Module/registry/UID/mount and root-witness output are explicit host fixtures.
Actual fork/exec/pipes and protocol are exercised; this is not target root proof.
"""
from pathlib import Path
import base64
import os
import signal
import socket
import subprocess
import tempfile
import time
import unittest
from unittest import mock
import test_s22plus_fyg8_p364_diagnostics as diagnostics
import device_action_f1_live_v2 as live
import s22plus_fyg8_p375_research_shell_runtime as runtime
import s22plus_fyg8_p375_research_shell_observer as observer
import s22plus_fyg8_p375_console_owner as console_owner
ROOT=Path(__file__).resolve().parents[1]


def source():
    with mock.patch.object(diagnostics,'runtime',runtime):value=diagnostics.source().replace('p364','p375')
    value=value.replace('#include <sys/prctl.h>','#include <sys/prctl.h>\n#include <sys/syscall.h>')
    value=value.replace(' if(nr==25)return', ''' if(nr>=174 && nr<=177)return 0; /* fixture numeric credentials */
 if(nr==34){if(strcmp((char*)b,"/s22-root-work")||a!=-100||c!=0700)_Exit(112);fx_mark("root-dir",0);return fx_case("root-dir")?-EACCES:0;}
 if(nr==49){const char *path=(const char*)a;return neg(chdir(!strcmp(path,"/s22-root-work")?getenv("RC1_WORK"):path));}
 if(nr==436)return neg(syscall(SYS_close_range,a,b,c));
 if(nr==25)return''')
    old='static long sys_mount(const char*s,const char*p,const char*t,unsigned long f,const void*d){'
    new=old+'''if(!strcmp(p,"/s22-root-work")){if(strcmp(s,"tmpfs")||strcmp(t,"tmpfs")||f!=6||strcmp(d,"size=64m,nr_inodes=4096,mode=0700"))_Exit(113);fx_mark("root-mount",0);return fx_case("root-mount")?-EPERM:0;}'''
    value=value.replace(old,new)
    value=value.replace('return neg(execve(p,a,e));', '''if(!strcmp(p,"/bin/busybox")){
 const char *command=a[3];
 if(strstr(command,"RC1_ROOT"))command=fx_case("root-witness")?"printf 'BAD\\\\n'":"printf 'RC1_ROOT\\\\n0\\\\n0\\\\n1\\\\nREAL_TREES\\\\n'";
 if(strstr(command,"WAITING")&&fx_case("cancel-no-output"))command="exit 7";
 char *args[]={"/bin/sh","-c",(char*)command,NULL};return neg(execve("/bin/sh",args,e));
}return neg(execve(p,a,e));''')
    # Host /bin/sh uses host tools where target commands use packaged BusyBox.
    value=value.replace('const char *command=a[3];','char text[1024];size_t used=0;const char *input=a[3];while(*input){if(!strncmp(input,"/bin/busybox ",13)){input+=13;continue;}text[used++]=*input++;}text[used]=0;const char *command=text;')
    value=value.replace('for(;;)p282_poll_delay();','fx_park();return -EIO;')
    value=value.replace('struct timespec64 n;p241_clock_gettime(&n);','struct timespec64 n={0};if(p241_clock_gettime(&n))_Exit(103);')
    return value


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.folder=Path(cls.temp.name);cls.binary=cls.folder/'native'
        p=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-Wno-unused-const-variable',
            '-Wno-misleading-indentation','-o',str(cls.binary)],
            input=source(),text=True,capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)

    def run_case(self,case,interactive=None,deadline_sec=4):
        run=self.folder/(case+'-'+str(time.monotonic_ns()));run.mkdir()
        host,peer=socket.socketpair();host.setblocking(False);peer.setblocking(False)
        process=subprocess.Popen([str(self.binary),str(peer.fileno()),'1'],pass_fds=(peer.fileno(),),
            env=dict(os.environ,P364_CASE=case,P364_MARK=str(run/'marks'),RC1_WORK=str(run)),
            stderr=subprocess.PIPE,start_new_session=True);peer.close()
        codec=live._open_header_initial_observer_module(runtime,observer,'p375-integration')
        raw=bytearray();writer=type('Writer',(),{'write_stdout':lambda self,data:raw.extend(data)})();intents=[]
        result=error=None
        try:
            try:result=observer.qualify(codec,host.fileno(),b'k'*32,None,set(),writer,
                    deadline=time.monotonic()+deadline_sec,before_control=intents.append,evidence=run/'console',
                    interactive=interactive)
            except observer.QualificationError as exc:error=exc
            if error:
                # Failure paths are parked in the production runtime and exit
                # only through the explicit fixture park adapter.
                process.wait(timeout=3)
            else:self.assertEqual(process.wait(timeout=3),0)
            marks=(run/'marks').read_text().splitlines() if (run/'marks').exists() else []
            return result,error,marks,intents,bytes(raw)
        finally:
            host.close()
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
            process.communicate(timeout=3)

    def test_generated_full_path(self):
        result,error,marks,intents,raw=self.run_case('normal')
        if error:raise AssertionError(repr(error.__cause__))
        self.assertTrue(result.receipt['proved']);self.assertEqual(result.receipt['command_count'],5)
        self.assertEqual(len(intents),1);self.assertIn('download 0',marks)
        self.assertEqual(marks[-1],'park 0');self.assertIn('root-dir 0',marks);self.assertIn('root-mount 0',marks)
        codec=live._open_header_initial_observer_module(runtime,observer,'p375-raw-replay')
        audit=result.sessions[0].session.audit
        self.assertEqual(observer.replay_session(codec,bytes(audit.rx),bytes(audit.tx),b'k'*32),result.receipt)
        changed=bytearray(audit.rx);changed[-1]^=1
        with self.assertRaises(ValueError):observer.replay_session(codec,bytes(changed),bytes(audit.tx),b'k'*32)

    def test_ram_preparation_failure_never_starts_console_or_control(self):
        for case,stage in (('root-dir',61),('root-mount',62)):
            with self.subTest(case=case):
                result,error,marks,intents,raw=self.run_case(case)
                self.assertIsNone(result);self.assertIsNotNone(error)
                self.assertEqual(error.partial_receipt['preparation']['failure']['stage'],stage)
                records=error.partial_receipt['preparation']['records']
                self.assertEqual(records[-1],dict(stage=255,event=4,
                    code=error.partial_receipt['preparation']['failure']['code']))
                codec=live._open_header_initial_observer_module(runtime,observer,
                    'p375-preparation-failure-replay')
                self.assertEqual(observer.replay_progress(codec,bytes(error.audit.rx),
                    bytes(error.audit.tx),b'k'*32),error.partial_receipt['preparation'])
                self.assertEqual(intents,[]);self.assertNotIn('download 0',marks)

    def test_operator_plan_uses_same_transport_and_raw_replays(self):
        command=b"printf 'PLAN\\n'; exit 7"
        plan={"schema":console_owner.SCHEMA,"commands":[{
            "command_base64":base64.b64encode(command).decode(),
            "cwd":"/s22-root-work","timeout_ms":1000}]}
        result,error,marks,intents,raw=self.run_case('normal',
            lambda session,events,deadline:console_owner.run(session,events,deadline,plan),15)
        if error:raise AssertionError(repr(error.__cause__))
        self.assertEqual(result.receipt['command_count'],6)
        row=result.receipt['commands'][-1]
        self.assertEqual(row['timeout_ms'],1000)
        self.assertEqual(row['stdout'],observer.identity(b'PLAN\n'))
        self.assertEqual(row['terminal'][2],7<<8)
        execution=console_owner.execution_projection(plan,[row])
        self.assertTrue(execution['all_planned_terminal'])
        self.assertEqual(execution['results'][0]['outcome'],'command-failed')
        codec=live._open_header_initial_observer_module(runtime,observer,'p375-plan-replay')
        audit=result.sessions[0].session.audit
        self.assertEqual(observer.replay_session(codec,bytes(audit.rx),bytes(audit.tx),b'k'*32),
            result.receipt)

    def test_known_fixed_failures_retain_control_and_no_proof(self):
        for case in ('pipe','root-witness','cancel-no-output'):
            with self.subTest(case=case):
                result,error,marks,intents,raw=self.run_case(case)
                self.assertIsNone(result);self.assertIsNotNone(error)
                proof=error.partial_receipt
                self.assertFalse(proof['proved'])
                self.assertTrue(proof['control_acceptance_observed'])
                self.assertEqual(len(intents),1)
                self.assertIn('download 0',marks)
                self.assertTrue(proof['all_commands_terminal_or_rejected'])
                codec=live._open_header_initial_observer_module(runtime,observer,
                    'p375-known-negative-replay')
                audit=error.audit
                self.assertEqual(observer.replay_session(codec,bytes(audit.rx),
                    bytes(audit.tx),b'k'*32,partial=True),proof)


if __name__=='__main__':unittest.main()
