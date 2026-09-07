"""Real generated C framing/control joined to Python through local sockets.

The platform module readiness and renderer are explicit fixtures. Reboot is a
record-only syscall stub; the actual control parser/HMAC/UUID implementation and
supervisor child cleanup are compiled unchanged. No device or host reboot.
"""
from pathlib import Path
import hashlib
import hmac
import os
import socket
import struct
import subprocess
import tempfile
import time
import unittest
from unittest import mock
import test_s22plus_fyg8_p345_c_host_join as base
import s22plus_fyg8_p363_research_shell_runtime as runtime
import s22plus_fyg8_p363_research_shell_observer as observer
import device_action_f1_live_v2 as live

UUID = b'01234567-89ab-4cde-8fab-0123456789ab'
KEY = b'k'*32


def source(mode=1):
    text = base.source(runtime)
    modules = (runtime.return_spec.render_module_table()+runtime.MODULE_SOURCE.read_bytes()).decode()
    assert text.count(modules) == 1
    text = text.replace(modules,'static long p363_prepare_return(void){return 0;}')
    text = text.replace('#include <sys/prctl.h>','#include <sys/prctl.h>\n#include <sys/mman.h>\n#define P260_EOVERFLOW EOVERFLOW')
    text = text.replace('static long neg(long n)', r'''
static size_t cstr_len(const char *s){return strlen(s);}
static long p345_close_extra_fds(void){return 0;}
static long p345_apply_limits(void){return 0;}
static void mark(const char *s){int f=open(getenv("P363_H0_MARK"),O_WRONLY|O_CREAT|O_APPEND,0600);if(f<0)_Exit(88);if(write(f,s,strlen(s))!=(ssize_t)strlen(s))_Exit(87);close(f);}
static void terminal_park(void){int status;if(waitpid(-1,&status,WNOHANG)!=-1||errno!=ECHILD)_Exit(89);mark("park\n");_Exit(0);}
static long neg(long n)''')
    text = text.replace('return neg(open(p,flags,mode));', r'''
if(!strcmp(p,"/proc/sys/kernel/random/boot_id")){
 int f=memfd_create("p363-uuid-fixture",0);if(f<0)return -errno;
 const char *u=getenv("P363_H0_UUID");if(!u)u="01234567-89ab-4cde-8fab-0123456789ab\n";
 if(write(f,u,strlen(u))!=(ssize_t)strlen(u))_Exit(86);lseek(f,0,SEEK_SET);return f;
}return neg(open(p,flags,mode));''')
    text = text.replace('return neg(write(fd,p,n));', r'''
static int partial_ack;
if(partial_ack)return -EIO;
if(n>=16 && ((const unsigned char*)p)[5]==0x8a){
 const char *which=getenv("P363_H0_CASE");
 if(!strcmp(which,"ack-fail"))return -EIO;
 if(!strcmp(which,"ack-partial")){partial_ack=1;return neg(write(fd,p,10));}
}return neg(write(fd,p,n));''')
    text = text.replace('return neg(execve(p,a,e));', r'''
if(!strcmp(p,"/s22-display")){
 mark("child-start\n");const char *which=getenv("P363_H0_CASE");
 if(!strcmp(which,"stall"))for(;;)usleep(10000);
 if(!strcmp(which,"child-backlog")){
  dprintf(1,"DISPLAY_SWAP_SUBMITTED run=%s swap=1 ioctl_return=0 visible=UNPROVED\n",a[2]);
  char padding[3000];memset(padding,'x',sizeof(padding));padding[2999]='\n';
  if(write(1,padding,sizeof(padding))!=(ssize_t)sizeof(padding))_Exit(80);
  for(unsigned int i=2;i<=10;i++)dprintf(1,"DISPLAY_SWAP_SUBMITTED run=%s swap=%u ioctl_return=0 visible=UNPROVED\n",a[2],i);
  _Exit(7);
 }
 unsigned int count=!strcmp(which,"child-error")?3:10;
 for(unsigned int i=1;i<=count;i++){
  dprintf(1,"DISPLAY_SWAP_SUBMITTED run=%s swap=%u ioctl_return=0 visible=UNPROVED\n",a[2],i);
 }
 if(!strcmp(which,"child-error"))_Exit(7);
 for(;;)usleep(10000);
}return neg(execve(p,a,e));''')
    text = text.replace('if(nr==157)return neg(setsid());', r'''
if(nr==25)return neg(fcntl(a,b,c));
if(nr==142){
 if(a!=0xfee1deadUL||b!=672274793UL)_Exit(84);
 if(c==0xa1b2c3d4UL&&d&&!strcmp((char*)d,"download"))mark("download\n");
 else if(c==0x01234567UL&&!d)mark("restart\n");else _Exit(83);
 return -EIO;
}
if(nr==157)return neg(setsid());''')
    # Scale fixture clock for the actual sixty-second deadline (2 real seconds).
    text = text.replace('out->tv_sec=t.tv_sec;out->tv_nsec=t.tv_nsec;return 0;',
        'out->tv_sec=t.tv_sec*30+(t.tv_nsec*30)/1000000000;out->tv_nsec=(t.tv_nsec*30)%1000000000;return 0;')
    text = text.replace('struct timespec64 d;p282_deadline_after(seconds,&d);','struct timespec64 d={0};if(p282_deadline_after(seconds,&d))_Exit(81);')
    text = text.replace('struct timespec64 n;p241_clock_gettime(&n);','struct timespec64 n={0};if(p241_clock_gettime(&n))_Exit(82);')
    text = text.replace('    (void)sys_close(pipe_fds[1]);\n\n    struct timespec64 deadline', '    (void)sys_close(pipe_fds[1]);\n    if(!strcmp(getenv("P363_H0_CASE"),"child-backlog"))usleep(100000);\n\n    struct timespec64 deadline')
    text = text.replace('for (;;) p282_poll_delay();','terminal_park();')
    text = text.replace("uint8_t boot[32];memset(boot,'b',32);",
        'uint8_t boot[32];if(p335_getrandom_boot_id(boot))return 5;')
    text = text.replace('const char *a,const char *b,size_t n','const void *a,const void *b,size_t n')
    if mode == 2:
        text = text.replace('#define P363_LIVE_MODE P363_MODE_DOWNLOAD','#define P363_LIVE_MODE P363_MODE_RESTART')
    return text


class CJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name);cls.binary = cls.root/'peer'
        result = subprocess.run(['cc','-x','c','-','-o',str(cls.binary),'-O2','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-Wno-misleading-indentation'],input=source().encode(),capture_output=True,timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr.decode())

    def run_case(self, case='normal', mutation=None, before=None, uuid=None):
        marks = self.root/(self.id().split('.')[-1]+'-'+str(time.monotonic_ns())+'.log')
        host,peer = socket.socketpair();host.setblocking(False);peer.setblocking(False)
        environment = dict(os.environ,P363_H0_MARK=str(marks),P363_H0_CASE=case)
        if uuid is not None:
            environment['P363_H0_UUID'] = uuid
        process = subprocess.Popen([str(self.binary),str(peer.fileno()),'1'],env=environment,
            pass_fds=(peer.fileno(),),stderr=subprocess.PIPE)
        peer.close()
        codec = live._open_header_initial_observer_module(runtime,observer,'p363-real-c')
        output = bytearray();writer = type('Writer',(),{'write_stdout':lambda self,b:output.extend(b)})()
        sent = codec._CODEC._send
        intent_calls = []
        def intent(request):
            intent_calls.append(request)
            if before is not None:
                before(request)
        def send(fd,kind,seq,payload,deadline,audit):
            if mutation == 'early' and kind == runtime.FRAME_EXEC and seq == 4:
                sent(fd,kind,seq,payload,deadline,audit)
                body=observer.control.CONTROL_BODY
                return sent(fd,observer.control.FRAME_CONTROL,5,
                    body+observer._tag(KEY,observer.control.DOMAIN_CONTROL,audit.nonce,body),deadline,audit)
            if kind != observer.control.FRAME_CONTROL or mutation is None:
                return sent(fd,kind,seq,payload,deadline,audit)
            if mutation == 'wrong-mac':
                payload = payload[:-1]+bytes((payload[-1]^1,))
            elif mutation == 'wrong-mode':
                payload = bytes((2,0,0,0))+payload[4:]
            elif mutation == 'wrong-reserved':
                payload = bytes((1,1,0,0))+payload[4:]
            elif mutation == 'wrong-sequence':
                seq += 1
            elif mutation == 'oversized':
                payload += b'x'
            elif mutation == 'wrong-run':
                body = payload[:4]
                payload = body+hmac.new(KEY,observer.control.DOMAIN_CONTROL+b'x'*16+audit.nonce+struct.pack('<I',seq)+body,hashlib.sha256).digest()
            elif mutation == 'wrong-nonce':
                body = payload[:4]
                payload = body+hmac.new(KEY,observer.control.DOMAIN_CONTROL+runtime.P363_RUN_ID+b'x'*32+struct.pack('<I',seq)+body,hashlib.sha256).digest()
            wire = codec._CODEC.encode_frame(kind,seq,payload)
            if mutation == 'partial':
                wire = wire[:20]
            if mutation == 'split':
                for byte in wire:
                    os.write(fd,bytes((byte,)));audit.tx.extend(bytes((byte,)))
                return
            os.write(fd,wire);audit.tx.extend(wire)
            if mutation == 'duplicate':
                os.write(fd,wire);audit.tx.extend(wire)
        value = error = None
        started = time.monotonic()
        try:
            with mock.patch.object(codec._CODEC,'_send',side_effect=send):
                try:
                    value = observer.qualify(codec,host.fileno(),KEY,None,set(),writer,
                        deadline=time.monotonic()+4,before_control=intent)
                except observer.QualificationError as exc:
                    error = exc
            host.close()
            code = process.wait(timeout=4)
            stderr = process.stderr.read().decode()
            lines = marks.read_text().splitlines() if marks.exists() else []
            self.assertLess(time.monotonic()-started,5)
            self.assertIn(code,(0,5),stderr)
            return value,error,lines,intent_calls,codec
        finally:
            host.close()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3);process.stderr.close()

    def test_exact_real_c_control_and_kernel_uuid_digest(self):
        value,error,lines,intents,codec = self.run_case()
        self.assertIsNone(error)
        self.assertEqual(lines,['child-start','download','park'])
        self.assertEqual(len(intents),1)
        row = value.receipt['sessions'][0]
        self.assertEqual(row['boot_id_sha256'],hashlib.sha256(hashlib.sha256(UUID).digest()).hexdigest())
        self.assertEqual(row['semantic']['display_submitted_swaps'],10)
        self.assertFalse(row['semantic']['display_child_exited_before_ready'])
        self.assertEqual(row['semantic']['software_download_arrival'],'UNPROVED')
        audit = value.sessions[0].session.audit
        parsed = observer.parse_captured_session(codec,bytes(audit.rx),bytes(audit.tx),KEY)
        self.assertEqual(observer.validate_session_result(parsed,observer.DISPLAY_STEP),row)

    def test_early_child_exit_does_not_remove_parent_control(self):
        value,error,lines,intents,_ = self.run_case('child-error')
        self.assertIsNone(error)
        self.assertEqual(lines,['child-start','download','park'])
        row = value.receipt['sessions'][0]['semantic']
        self.assertEqual(row['display_submitted_swaps'],3)
        self.assertTrue(row['display_child_exited_before_ready'])

    def test_early_exit_backlog_cannot_change_signed_ready_count(self):
        value,error,lines,intents,_ = self.run_case('child-backlog')
        self.assertIsNone(error);self.assertEqual(lines,['child-start','download','park'])
        self.assertEqual(len(intents),1)
        semantic=value.receipt['sessions'][0]['semantic']
        self.assertEqual(semantic['display_submitted_swaps'],1)
        self.assertTrue(semantic['display_child_exited_before_ready'])

    def test_bad_frames_never_reboot(self):
        for mutation in ('wrong-mac','wrong-mode','wrong-reserved','wrong-sequence','oversized','wrong-run','wrong-nonce','partial'):
            with self.subTest(mutation=mutation):
                value,error,lines,_,_ = self.run_case(mutation=mutation)
                self.assertIsNone(value);self.assertIsNotNone(error)
                self.assertNotIn('download',lines);self.assertEqual(lines[-1],'park')

    def test_split_control_remains_one_effect(self):
        value,error,lines,_,_ = self.run_case(mutation='split')
        self.assertIsNone(error);self.assertIsNotNone(value)
        self.assertEqual(lines.count('download'),1)

    def test_duplicate_control_cannot_repeat_effect_or_qualify_capture(self):
        value,error,lines,_,codec = self.run_case(mutation='duplicate')
        self.assertEqual(lines.count('download'),1)
        if value is not None:
            audit=value.sessions[0].session.audit
            with self.assertRaises(ValueError):
                observer.parse_captured_session(codec,bytes(audit.rx),bytes(audit.tx),KEY)
        else:
            self.assertIsNotNone(error)

    def test_intent_failure_precedes_any_control_effect(self):
        def fail(_):raise OSError('simulated fsync failure')
        value,error,lines,intents,_ = self.run_case(before=fail)
        self.assertIsNone(value);self.assertIsNotNone(error);self.assertEqual(len(intents),1)
        self.assertNotIn('download',lines)

    def test_stalled_child_reaches_original_absolute_deadline(self):
        value,error,lines,intents,_ = self.run_case('stall')
        self.assertIsNone(value);self.assertIsNotNone(error);self.assertEqual(intents,[])
        self.assertEqual(lines,['child-start','park'])

    def test_ack_write_failure_consumes_without_syscall(self):
        for case in ('ack-fail','ack-partial'):
            with self.subTest(case=case):
                value,error,lines,intents,_ = self.run_case(case)
                self.assertIsNone(value);self.assertIsNotNone(error)
                self.assertEqual(len(intents),1);self.assertNotIn('download',lines)
                self.assertEqual(lines[-1],'park')

    def test_ordinary_restart_mapping_is_h0_only(self):
        binary=self.root/'ordinary-peer'
        built=subprocess.run(['cc','-x','c','-','-o',str(binary),'-O2','-Wall','-Wextra','-Werror',
            '-Wno-unused-function','-Wno-misleading-indentation'],input=source(mode=2).encode(),capture_output=True,timeout=30)
        self.assertEqual(built.returncode,0,built.stderr.decode())
        host,peer=socket.socketpair();host.setblocking(False);peer.setblocking(False)
        mark=self.root/'ordinary-mark.log'
        process=subprocess.Popen([str(binary),str(peer.fileno()),'1'],
            env=dict(os.environ,P363_H0_MARK=str(mark),P363_H0_CASE='normal'),
            pass_fds=(peer.fileno(),),stderr=subprocess.PIPE)
        peer.close()
        codec=live._open_header_initial_observer_module(runtime,observer,'p363-ordinary-h0')
        def protocol(obs,key,read_bytes,write_frame,audit,*,before_control):
            observer._dispatch_prefix_protocol(obs,key,read_bytes,write_frame,audit)
            def status(kind,body,domain):
                header=read_bytes(obs._CODEC.HEADER.size)
                size=obs._CODEC.HEADER.unpack(header)[3]
                self.assertEqual(size,36)
                value=obs._CODEC._expect(obs._CODEC.decode_frame(header+read_bytes(size)),kind,5)
                self.assertEqual(value,body+observer._tag(key,domain,audit.nonce,body))
            status(observer.control.FRAME_CONTROL_READY,bytes((2,10,1,0)),observer.control.DOMAIN_READY)
            body=bytes((2,0,0,0))
            write_frame(observer.control.FRAME_CONTROL,5,body+observer._tag(key,observer.control.DOMAIN_CONTROL,audit.nonce,body))
            status(observer.control.FRAME_CONTROL_ACK,bytes((2,0,10,0)),observer.control.DOMAIN_ACK)
            return 'ordinary-h0-accepted'
        writer=type('Writer',(),{'write_stdout':lambda self,b:None})()
        try:
            with mock.patch.object(observer,'_protocol',side_effect=protocol):
                result=observer._live(codec,host.fileno(),KEY,writer,time.monotonic()+4,before_control=lambda _:None)
            self.assertEqual(result,'ordinary-h0-accepted')
            host.close();self.assertEqual(process.wait(timeout=4),0,process.stderr.read().decode())
            self.assertEqual(mark.read_text().splitlines(),['child-start','restart','park'])
            self.assertEqual(observer.control.CONTROL_BODY,bytes((1,0,0,0)))
            self.assertIn(b'#define P363_LIVE_MODE P363_MODE_DOWNLOAD',runtime.CONTROL_SOURCE.read_bytes())
        finally:
            host.close()
            if process.poll() is None:process.kill()
            process.wait(timeout=3);process.stderr.close()

    def test_control_before_ready_is_rejected(self):
        value,error,lines,intents,_ = self.run_case('stall',mutation='early')
        self.assertIsNone(value);self.assertIsNotNone(error);self.assertEqual(intents,[])
        self.assertNotIn('download',lines)

    def test_malformed_kernel_uuid_fails_before_child_or_control(self):
        for uuid in ('bad\n','01234567-89AB-4cde-8fab-0123456789ab\n',UUID.decode(),UUID.decode()+'\nextra'):
            with self.subTest(uuid=uuid):
                value,error,lines,intents,_ = self.run_case(uuid=uuid)
                self.assertIsNone(value);self.assertIsNotNone(error)
                self.assertEqual(lines,[]);self.assertEqual(intents,[])


if __name__ == '__main__':unittest.main()
