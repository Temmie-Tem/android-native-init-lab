"""Actual generated authenticated C prefix and supervisor after host disconnect.

Platform wrappers use host fork/pipes; display executable is a fixed local
canary. Timeout case scales the fixture clock, not the generated 60s constant.
No DRM, target device, or real privilege/isolation qualification here.
"""
from pathlib import Path
import os
import socket
import subprocess
import tempfile
import time
import unittest
import test_s22plus_fyg8_p345_c_host_join as base
import s22plus_fyg8_p355_research_shell_runtime as runtime
import s22plus_fyg8_p355_research_shell_observer as observer
import device_action_f1_live_v2 as live


def source():
    text=base.source(runtime)
    text=text.replace('static long neg(long n)', '''static int h0_tty=-1,h0_dispatched;
static long p345_close_extra_fds(void){return 0;}
static long p345_apply_limits(void){return 0;}
static void mark(const char *s){int f=open(getenv("P355_H0_MARK"),O_WRONLY|O_CREAT|O_APPEND,0600);if(f<0)_Exit(88);if(write(f,s,strlen(s))!=(ssize_t)strlen(s))_Exit(87);close(f);}
static void terminal_park(void){int status; if(waitpid(-1,&status,WNOHANG)!=-1 || errno!=ECHILD)_Exit(89);mark("park\\n");_Exit(0);}
static long neg(long n)''')
    text=text.replace('return neg(read(fd,p,n));','if(fd==h0_tty&&h0_dispatched)_Exit(80);return neg(read(fd,p,n));')
    text=text.replace('return neg(write(fd,p,n));','if(fd==h0_tty&&h0_dispatched)_Exit(81);return neg(write(fd,p,n));')
    text=text.replace('return neg(kill(pid,sig));','if(pid>0&&sig==SIGKILL)mark("kill\\n");return neg(kill(pid,sig));')
    text=text.replace('return neg(execve(p,a,e));', '''if(!strcmp(p,"/s22-display")){
 mark("start\\n");if(write(1,"local-diagnostic\\n",17)!=17)_Exit(86);usleep(300000);mark("after-close\\n");
 if(!strcmp(getenv("P355_H0_CASE"),"timeout"))for(;;)usleep(10000);
 _Exit(!strcmp(getenv("P355_H0_CASE"),"error")?7:0);
 }return neg(execve(p,a,e));''')
    text=text.replace('if(nr==157)return neg(setsid());','if(nr==25)return neg(fcntl(a,b,c));\n if(nr==157)return neg(setsid());')
    text=text.replace('out->tv_sec=t.tv_sec;out->tv_nsec=t.tv_nsec;return 0;', '''int factor=h0_dispatched&&!strcmp(getenv("P355_H0_CASE"),"timeout")?60:1;
 out->tv_sec=t.tv_sec*factor+(t.tv_nsec*factor)/1000000000;
 out->tv_nsec=(t.tv_nsec*factor)%1000000000;return 0;''')
    text=text.replace('if (p355_display) {\n        if (p355_display_consumed)', 'if (p355_display) {\n        h0_dispatched=1;\n        if (p355_display_consumed)')
    text=text.replace('for (;;) p282_poll_delay();','terminal_park(); /* intercepted terminal park; no generic return */')
    text=text.replace('int fd=atoi(argv[1]),count=atoi(argv[2]);','int fd=atoi(argv[1]),count=atoi(argv[2]);h0_tty=fd;')
    text=text.replace('const char *a,const char *b,size_t n','const void *a,const void *b,size_t n')
    return text


class CJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name);cls.binary=cls.root/'peer'
        result=subprocess.run(['cc','-x','c','-','-o',str(cls.binary),'-O2','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-Wno-unused-function','-Wno-misleading-indentation'],input=source().encode(),capture_output=True,timeout=30)
        if result.returncode:raise AssertionError(result.stderr.decode())

    def run_case(self,case):
        mark=self.root/(case+'.log');host,peer=socket.socketpair();host.setblocking(False);peer.setblocking(False)
        env=dict(os.environ,P355_H0_MARK=str(mark),P355_H0_CASE=case)
        process=subprocess.Popen([str(self.binary),str(peer.fileno()),'1'],env=env,pass_fds=(peer.fileno(),),stderr=subprocess.PIPE)
        peer.close()
        try:
            codec=live._open_header_initial_observer_module(runtime,observer,'p355-real-c-'+case)
            output=bytearray();writer=type('Writer',(),{'write_stdout':lambda self,b:output.extend(b)})()
            value=observer.qualify(codec,host.fileno(),b'k'*32,None,set(),writer,deadline=time.monotonic()+4)
            self.assertTrue(value.receipt['display_request_dispatched']);host.close()
            code=process.wait(timeout=5)
            self.assertEqual(code,0,process.stderr.read().decode())
            lines=mark.read_text().splitlines()
            self.assertEqual(lines[:2],['start','after-close']);self.assertEqual(lines[-1],'park')
            self.assertEqual('kill' in lines,case=='timeout')
        finally:
            host.close()
            if process.poll() is None:process.kill()
            process.wait(timeout=3);process.stderr.close()

    def test_normal_exit_without_tty_io_or_next_session(self):self.run_case('normal')
    def test_error_exit_without_tty_io_or_error_publisher(self):self.run_case('error')
    def test_original_sixty_second_bound_with_scaled_host_clock(self):self.run_case('timeout')


if __name__=='__main__':unittest.main()
