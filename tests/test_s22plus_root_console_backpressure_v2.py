"""Real pipe backpressure, shared credits and ARM64 supervisor/BusyBox behavior."""
from pathlib import Path
import shlex
import struct
import subprocess
import time
import unittest
from unittest import mock
import test_s22plus_root_console_v1 as base
import test_s22plus_root_console_arm64 as arm64
import s22plus_fyg8_p381_research_shell_runtime as runtime
import s22plus_root_console_v1 as wire

_original_source=base.source


def source():
    return runtime.apply_backpressure(_original_source().encode()).decode()


class Behavior:
    def cat_command(self):
        if hasattr(self,'launcher'):
            return (shlex.quote(self.launcher[0])+' '+shlex.quote(str(self.folder/'busybox'))+' cat').encode()
        return b'cat'

    def burst(self,size=65536):
        out=(bytes(range(256))*((size+255)//256))[:size]
        err=(bytes(reversed(range(256)))*((size+255)//256))[:size]
        (self.folder/'out.data').write_bytes(out);(self.folder/'err.data').write_bytes(err)
        cat=self.cat_command()
        command=cat+b' out.data & '+cat+b' err.data >&2 & wait'
        seq=self.session.send(wire.EXEC,wire.command(command,cwd=str(self.folder).encode(),timeout_ms=15000))
        self.wait(wire.ACK,seq)
        return seq,out,err

    def test_dual_binary_burst_survives_paused_reader(self):
        seq,out,err=self.burst()
        time.sleep(.35)
        status=self.session.send(wire.STATUS);self.wait(wire.STATUS_REPLY,status)
        end=struct.unpack('<7I',self.wait(wire.EXIT,seq,timeout=12))
        self.assertEqual(end[1:4],(0,0,0));self.assertEqual(end[4:6],(len(out)+len(err),0))
        self.assertEqual(self.output(seq,1),out);self.assertEqual(self.output(seq,2),err)
        self.finish()

    def test_control_during_backpressure_does_not_claim_complete_output(self):
        seq,_,_=self.burst();time.sleep(.25)
        control=self.session.send(wire.CONTROL);self.wait(wire.CONTROL_ACK,control)
        end=struct.unpack('<7I',self.wait(wire.EXIT,seq))
        self.assertTrue(end[1]&32);self.assertTrue(end[1]&128)
        self.assertEqual(end[4],len(self.output(seq,1))+len(self.output(seq,2)))
        self.assertEqual(self.process.wait(timeout=3),0)

    def test_byte_budget_exhaustion_still_drains_and_reports_loss(self):
        size=1048576+4096
        (self.folder/'limit.data').write_bytes(b'x'*size)
        seq=self.session.send(wire.EXEC,wire.command(self.cat_command()+b' limit.data',
            cwd=str(self.folder).encode(),timeout_ms=15000))
        end=struct.unpack('<7I',self.wait(wire.EXIT,seq,timeout=12))
        self.assertEqual(end[1],4);self.assertGreater(end[5],0)
        self.assertLessEqual(end[4],1048576);self.assertEqual(end[4]+end[5],size)
        self.assertEqual(len(self.output(seq,1)),end[4]);self.finish()


class HostBackpressure(Behavior,base.ConsoleTests):
    @classmethod
    def setUpClass(cls):
        with mock.patch.object(base,'source',source):super().setUpClass()

    def run_boundary(self,name,main,short_writes=False):
        text=source();text=text[:text.index('int main(int argc,char **argv)')]
        if short_writes:
            old='static long sys_write(int fd,const void *p,size_t n){ return neg(write(fd,p,n)); }'
            self.assertEqual(text.count(old),1)
            text=text.replace(old,old.replace('write(fd,p,n)','write(fd,p,n>3?3:n)'))
        text+='\n#include <assert.h>\n#include <sys/socket.h>\n'+main
        binary=self.folder/name
        built=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-Wno-misleading-indentation','-o',str(binary)],
            input=text,text=True,capture_output=True,timeout=30)
        self.assertEqual(built.returncode,0,built.stderr)
        subprocess.run([str(binary)],check=True,timeout=5)
        self.finish()

    def test_partial_wire_write_keeps_credit_until_frame_is_complete(self):
        self.run_boundary('partial-credit',r'''
int main(void) {
 int tty[2],pipes[2][2];assert(!socketpair(AF_UNIX,SOCK_STREAM,0,tty));
 struct rc1_state s={0};s.fd=tty[0];s.id=3;char data[64]={0},check[64];
 for(unsigned i=0;i<2;i++){assert(!pipe2(pipes[i],O_NONBLOCK|O_CLOEXEC));s.pipe[i]=pipes[i][0];assert(write(pipes[i][1],data,64)==64);}
 for(unsigned i=0;i<5;i++)assert(!rc1_queue(&s,RC1_STATUS_REPLY,3,NULL,0));
 while(s.queue[0].used+3<s.queue[0].size){
  unsigned before=s.queue[0].used;assert(!rc1_flush(&s));assert(s.queue[0].used==before+3);
  assert(s.qcount==5);assert(!rc1_output_tick(&s));assert(!s.total&&!s.dropped);
 }
 assert(!rc1_flush(&s));assert(s.qcount==4);
 assert(!rc1_output_tick(&s));assert(s.qcount==5&&s.total==64&&s.ordinal==1);
 assert(read(pipes[1][0],check,64)==64);
 for(unsigned i=0;i<2;i++){close(pipes[i][0]);close(pipes[i][1]);}
 close(tty[0]);close(tty[1]);return 0;
}
''',short_writes=True)

    def test_reaped_backlog_keeps_cleanup_stop_and_control(self):
        self.run_boundary('reaped-backlog',r'''
static void request(struct rc1_state *s,unsigned type,const uint8_t *body,unsigned n) {
 memset(s->rx,0,sizeof(s->rx));s->rx[5]=type;p328_store_le32(s->rx+8,s->next);
 if(n)memcpy(s->rx+16,body,n);rc1_tag(s->rx+16+n,s->nonce,s->next,type,body,n);
 p328_store_le32(s->rx+12,p328_frame_crc(s->rx,s->rx+16,n+32));s->rx_size=16+n+32;
 assert(!rc1_request(s,3001));
}
int main(void) {
 int tty[2],pipes[2][2];assert(!socketpair(AF_UNIX,SOCK_STREAM,0,tty));
 for(unsigned i=0;i<2;i++)assert(!pipe2(pipes[i],O_NONBLOCK|O_CLOEXEC));
 pid_t child=fork();assert(child>=0);
 if(!child){assert(setsid()>0);char bytes[64]={0};for(unsigned i=0;i<2;i++)assert(write(pipes[i][1],bytes,64)==64);_exit(0);}
 int status;assert(waitpid(child,&status,0)==child&&status==0);
 struct rc1_state s={0};s.fd=tty[0];s.id=3;s.next=4;s.pid=child;s.reaped=1;
 s.active=1;s.exec_seen=1;s.timeout=15000;s.cancel_phase=1;s.cancel_start=1000;
 for(unsigned i=0;i<2;i++){close(pipes[i][1]);s.pipe[i]=pipes[i][0];}s.pipe[2]=-1;
 for(unsigned i=0;i<5;i++)assert(!rc1_queue(&s,RC1_STATUS_REPLY,3,NULL,0));
 assert(!rc1_child_tick(&s,3001));assert(s.blocked&&!s.active&&s.terminal_sent);
 assert(s.flags==(RC1_FLAG_CLEANUP|RC1_FLAG_OUTPUT_INCOMPLETE));assert(!s.dropped&&!s.total);
 assert(s.pipe[0]<0&&s.pipe[1]<0);
 uint8_t command[8]={0};p328_store_le32(command,1000);command[4]=1;command[6]='/';command[7]=':';
 request(&s,RC1_EXEC,command,sizeof(command));assert(!s.active&&s.qcount==7);
 assert(p328_load_le32(s.queue[6].bytes+16+4)==1);
 request(&s,RC1_CONTROL,NULL,0);assert(s.control==1);
 while(s.qcount)assert(!rc1_flush(&s));
 assert(!rc1_control_tick(&s));assert(s.control==2&&s.qcount==1&&s.queue[s.qhead].bytes[5]==RC1_CONTROL_ACK);
 assert(!rc1_flush(&s));close(tty[0]);close(tty[1]);return 0;
}
''')

    def test_single_credit_rotates_streams_and_exhausted_budget_needs_no_credit(self):
        text=source();text=text[:text.index('int main(int argc,char **argv)')]
        text+='''
#include <assert.h>
int main(void) {
 int p[2][2];struct rc1_state s={0};s.id=3;s.qcount=5;
 for(unsigned i=0;i<2;i++){assert(!pipe2(p[i],O_NONBLOCK|O_CLOEXEC));s.pipe[i]=p[i][0];}
 char data[64]={0},check[64];
 for(unsigned i=0;i<2;i++)assert(write(p[i][1],data,sizeof(data))==64);
 assert(!rc1_output_tick(&s));assert(!s.total&&!s.dropped&&!s.ordinal);
 for(unsigned i=0;i<2;i++)assert(read(p[i][0],check,sizeof(check))==64);
 for(unsigned i=0;i<2;i++)assert(write(p[i][1],data,sizeof(data))==64);
 s.qcount=4;assert(!rc1_output_tick(&s));assert(s.qcount==5&&s.ordinal==1&&s.output_turn==1);
 assert(p328_load_le32(s.queue[4].bytes+16+8)==1);
 s.qcount=4;assert(!rc1_output_tick(&s));assert(s.qcount==5&&s.ordinal==2&&s.output_turn==0);
 assert(p328_load_le32(s.queue[4].bytes+16+8)==2);
 for(unsigned i=0;i<2;i++)assert(write(p[i][1],data,sizeof(data))==64);
 s.ordinal=RC1_OUTPUT_FRAME_LIMIT;
 assert(!rc1_output_tick(&s));assert(s.qcount==5&&s.dropped==128&&(s.flags&RC1_FLAG_TRUNCATED));
 for(unsigned i=0;i<2;i++){close(p[i][0]);close(p[i][1]);}
 return 0;
}
'''
        binary=self.folder/'credit-test'
        subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-Wno-misleading-indentation','-o',str(binary)],
            input=text,text=True,capture_output=True,check=True,timeout=30)
        subprocess.run([str(binary)],check=True,timeout=5)
        self.finish()


class Arm64Backpressure(Behavior,arm64.Arm64ConsoleTests):
    @classmethod
    def setUpClass(cls):
        with mock.patch.object(arm64.base,'source',source):super().setUpClass()


if __name__=='__main__':unittest.main()
