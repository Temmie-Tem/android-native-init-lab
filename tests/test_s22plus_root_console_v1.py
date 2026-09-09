"""Actual C supervisor joined to durable Python owner using real fork/pipes.

Host shell path is adapted to /bin/sh. This proves transport/process behavior,
not target root identity, USB continuity or Download recovery.
"""
from pathlib import Path
import os
import signal
import socket
import struct
import subprocess
import tempfile
import time
import unittest
from unittest import mock
import test_s22plus_fyg8_p345_c_host_join as base
import s22plus_root_console_v1 as wire
ROOT=Path(__file__).resolve().parents[1]
KEY=b'k'*32
NONCE=b'n'*32
RUN=base.runtime.P345_RUN_ID


def source():
    value=base.source()
    value=value[:value.index('int main(int argc,char **argv)')]
    value=value.replace('#include <sys/prctl.h>','#include <sys/prctl.h>\n#include <sys/syscall.h>')
    value=value.replace(' if(nr==157)', ' if(nr==25)return neg(fcntl((int)a,(int)b,c));\n if(nr==49)return neg(chdir((const char*)a));\n if(nr==175)return geteuid();\n if(nr==177)return getegid();\n if(nr==436)return neg(syscall(SYS_close_range,a,b,c));\n if(nr==157)')
    value=value.replace('return neg(execve(p,a,e));', '''if(!strcmp(p,"/bin/busybox")){char *args[]={"/bin/sh", "-c", a[3], NULL};return neg(execve("/bin/sh",args,e));}return neg(execve(p,a,e));''')
    value+='#define RC1_RUN_ID_ASCII "'+base.runtime.P345_RUN_ID_HEX+'"\n'
    value+=(ROOT/'workspace/public/src/native-init/s22plus_root_console_v1.inc.c').read_text()
    value+='''\nint main(int argc,char **argv){
 if(argc!=2)return 2;if(prctl(PR_SET_CHILD_SUBREAPER,1))return 3;
 uint8_t nonce[32];memset(nonce,'n',32);long rc=rc1_console(atoi(argv[1]),nonce);
 fprintf(stderr,"console=%ld\\n",rc);return rc==1?0:4;
}\n'''
    return value


class ConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.folder=Path(cls.temp.name);cls.binary=cls.folder/'native'
        p=subprocess.run(['cc','-x','c','-','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-misleading-indentation','-o',str(cls.binary)],input=source(),text=True,capture_output=True,timeout=30)
        if p.returncode:raise AssertionError(p.stderr)

    def setUp(self):
        self.host,peer=socket.socketpair();self.host.setblocking(False);peer.setblocking(False)
        peer.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,1024)
        self.process=subprocess.Popen([*getattr(self,'launcher',[str(self.binary)]),str(peer.fileno())],pass_fds=(peer.fileno(),),stderr=subprocess.PIPE,start_new_session=True)
        peer.close();self.session=wire.Session(self.host.fileno(),KEY,RUN,NONCE,self.folder/str(time.monotonic_ns()))
        self.events=[]
        self.wait(wire.READY,2)

    def tearDown(self):
        self.session.close();self.host.close()
        if self.process.poll() is None:os.killpg(self.process.pid,signal.SIGKILL)
        self.process.communicate(timeout=5)

    def wait(self,kind,seq,timeout=5):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            for item in self.events:
                if item[:2]==(kind,seq):return item[2]
            try:self.events.extend(self.session.poll())
            except EOFError:
                self.fail('peer closed: '+self.process.communicate(timeout=2)[1].decode())
            time.sleep(.001)
        self.fail('response timeout '+repr((kind,seq,self.events[-3:])))

    def execute(self,text,**kwargs):
        seq=self.session.send(wire.EXEC,wire.command(text,**kwargs))
        end=self.wait(wire.EXIT,seq)
        return seq,struct.unpack('<7I',end)

    def output(self,seq,stream):
        return b''.join(body[12:] for kind,identity,body in self.events
                        if kind==wire.OUTPUT and identity==seq and struct.unpack('<I',body[8:12])[0]==stream)

    def finish(self):
        seq=self.session.send(wire.CONTROL);self.wait(wire.CONTROL_ACK,seq)
        self.assertEqual(self.process.wait(timeout=3),0)

    def test_repeated_commands_binary_streams_nonzero_and_ram_files(self):
        cwd=str(self.folder).encode()
        seq,end=self.execute(b"printf 'A\\000B'; printf 'ERR' >&2; printf keep > state; exit 7",cwd=cwd)
        self.assertEqual(self.output(seq,1),b'A\0B');self.assertEqual(self.output(seq,2),b'ERR')
        self.assertEqual(end[2],7<<8);self.assertEqual(end[3],0)
        seq,end=self.execute(b'cat state; id -u; test -r /proc/self/status; test -d /sys; test -c /dev/null',cwd=cwd)
        self.assertEqual(self.output(seq,1),b'keep'+str(os.getuid()).encode()+b'\n')
        self.assertEqual(end[2],0);self.finish()

    def test_cancel_status_busy_and_stale_identity(self):
        seq=self.session.send(wire.EXEC,wire.command(b'sleep 20'))
        self.wait(wire.ACK,seq)
        status=self.session.send(wire.STATUS);self.assertEqual(struct.unpack('<8I',self.wait(wire.STATUS_REPLY,status))[2],1)
        busy=self.session.send(wire.EXEC,wire.command(b'echo forbidden'))
        self.assertEqual(struct.unpack('<8I',self.wait(wire.ACK,busy))[1],1)
        cancel=self.session.send(wire.CANCEL,struct.pack('<I',seq));self.wait(wire.ACK,cancel)
        end=struct.unpack('<7I',self.wait(wire.EXIT,seq));self.assertTrue(end[1]&1)
        cancel=self.session.send(wire.CANCEL,struct.pack('<I',seq))
        self.assertEqual(struct.unpack('<8I',self.wait(wire.ACK,cancel))[1],1)
        seq,end=self.execute(b'printf next');self.assertEqual(self.output(seq,1),b'next');self.finish()

    def test_output_flood_does_not_block_control(self):
        seq=self.session.send(wire.EXEC,wire.command(b'while :; do printf 1234567890123456789012345678901234567890; done'))
        self.wait(wire.ACK,seq);time.sleep(.2)
        status=self.session.send(wire.STATUS);self.wait(wire.STATUS_REPLY,status)
        self.finish()

    def test_complete_output_can_exceed_legacy_half_megabyte_capture(self):
        sequence,terminal=self.execute(b'/bin/busybox head -c 600000 /dev/zero')
        self.assertEqual(len(self.output(sequence,1)),600000)
        self.assertEqual(terminal[1]&4,0)
        self.assertGreater(self.session.raw_count,512*1024)
        self.assertLess(self.session.raw_count,wire.SESSION_RX_LIMIT)
        self.finish()

    def test_timeout_and_setup_failure_are_distinct(self):
        _,end=self.execute(b'sleep 20',timeout_ms=100)
        self.assertTrue(end[1]&2)
        _,end=self.execute(b'true',cwd=b'/definitely-absent-root-console-fixture')
        self.assertTrue(end[1]&16);self.assertEqual(struct.unpack('<i',struct.pack('<I',end[3]))[0],-2)
        self.finish()

    def test_duplicate_exec_stops_without_replay(self):
        seq=self.session.send(wire.EXEC,wire.command(b'printf once'))
        self.wait(wire.EXIT,seq)
        os.write(self.host.fileno(),wire.frame(KEY,RUN,NONCE,seq,wire.EXEC,wire.command(b'printf twice')))
        self.assertEqual(self.process.wait(timeout=3),4)

    def test_fragmented_and_malformed_authentication(self):
        data=wire.frame(KEY,RUN,NONCE,3,wire.STATUS)
        self.session.requests[3]=wire.STATUS;self.session.sequence=4
        for byte in data:os.write(self.host.fileno(),bytes([byte]));time.sleep(.0001)
        self.wait(wire.STATUS_REPLY,3)
        data=wire.frame(b'x'*32,RUN,NONCE,4,wire.EXEC,wire.command(b'printf bad'))
        os.write(self.host.fileno(),data);self.assertEqual(self.process.wait(timeout=3),4)

    def test_saturated_status_queue_retains_control_and_honest_terminal(self):
        seq=self.session.send(wire.EXEC,wire.command(b'while :; do printf 123456789012345678901234567890; done'))
        self.wait(wire.ACK,seq)
        # Deliberately violate the host request window to exercise native
        # overload admission while no output is being consumed.
        for number in range(4,20):
            self.session.requests[number]=wire.STATUS
            self.session.request_bodies[number]=b''
            os.write(self.host.fileno(),wire.frame(KEY,RUN,NONCE,number,wire.STATUS))
        self.session.sequence=20;time.sleep(.2)
        control=self.session.send(wire.CONTROL)
        self.wait(wire.CONTROL_ACK,control)
        end=struct.unpack('<7I',self.wait(wire.EXIT,seq))
        self.assertTrue(end[1]&32);self.assertTrue(end[1]&8);self.assertTrue(end[1]&128)
        self.assertEqual(self.process.wait(timeout=3),0)

    def test_host_rejects_replayed_and_impossible_lifecycle(self):
        seq=self.session.send(wire.EXEC,wire.command(b'sleep 20'))
        ack=self.wait(wire.ACK,seq)
        with self.assertRaisesRegex(wire.ProtocolError,'duplicate'):
            self.session._validate(wire.ACK,seq,ack)
        with self.assertRaisesRegex(wire.ProtocolError,'flags'):
            self.session._validate(wire.EXIT,seq,struct.pack('<7I',seq,512,0,0,0,0,0))
        with self.assertRaisesRegex(wire.ProtocolError,'exec errno'):
            self.session._validate(wire.EXIT,seq,struct.pack('<7I',seq,16,0,0,0,0,0))
        with self.assertRaisesRegex(wire.ProtocolError,'wait status'):
            self.session._validate(wire.EXIT,seq,struct.pack('<7I',seq,0,0x7f,0,0,0,0))
        self.finish()

    def test_parent_directory_fsync_precedes_any_transport_send(self):
        evidence=self.folder/str(time.monotonic_ns())
        original=os.fsync;seen=[]
        def failing(fd):
            target=os.readlink(f'/proc/self/fd/{fd}');seen.append(target)
            if target==str(evidence.parent):raise OSError('injected parent fsync failure')
            return original(fd)
        with mock.patch.object(os,'fsync',side_effect=failing):
            with self.assertRaisesRegex(OSError,'parent fsync'):
                wire.Session(self.host.fileno(),KEY,RUN,NONCE,evidence)
        self.assertEqual(seen,[str(evidence.parent)])
        self.assertEqual(list(evidence.iterdir()),[])
        self.assertIsNone(self.process.poll())


if __name__=='__main__':unittest.main()
