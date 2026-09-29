"""Actual native C terminal framing on PTY; ARM64 VM proves the root effects.

Only the terminal effect body is substituted with a fixed C wire peer here.
This fixture does not claim that a host process is the device PID1.
"""
from pathlib import Path
import os
import struct
from unittest import mock
import unittest
import test_s22plus_native_observation_v3 as base
import test_s22plus_native_resident_v1 as producer
import s22plus_switch_root_source_v1 as source
import s22plus_switch_root_profile_v1 as profile
import s22plus_switch_root_protocol_v1 as wire
import s22plus_native_observation_v3 as observation
import s22plus_native_host_v3 as native_host

WITNESS='99'*32
PEER=r'''
static void swfx_send(struct rc1_state *s,unsigned kind,unsigned seq,const unsigned char *data,unsigned size) {
 static const char domain[]="S22PLUS-FYG8-SWITCH-ROOT-v1";
 unsigned char body[1024],signed_body[992];signed_body[0]=kind;memcpy(signed_body+1,data,size);
 memcpy(body,data,size);p328_hmac_message(body+size,domain,sizeof(domain)-1,p328_run_id_bytes,s->nonce,seq,1,signed_body,size+1);
 if(p328_write_frame(s->fd,kind,seq,body,size+32))fx_park();
}
static __attribute__((noreturn)) void sw_parent_exec(struct rc1_state *s) {
 const char *labels[]={"actual-pid1","three-workers-reaped","exact-root-checker","protected-after-retirement",
  "fixed-ram-witness","mounts-moved-work-unmounted","busybox-switch-root"};
 for(unsigned stage=1;stage<=8;stage++) {
  unsigned char data[128]={0};p328_store_le32(data,stage);
  unsigned size;
  if(stage<8){size=strlen(labels[stage-1]);memcpy(data+8,labels[stage-1],size);}
  else {
   size=120;p328_store_le32(data+8,1);p328_store_le32(data+12,8);p328_store_le32(data+16,41);p328_store_le32(data+20,7);
   if(@@NAMESPACE@@_kernel_boot_id(data+24))fx_park();memset(data+56,0x99,32);memset(data+88,0x55,32);
   p328_store_le32(data+120,15);p328_store_le32(data+124,1);
  }
  swfx_send(s,169,1023+stage,data,size+8);
 }
 unsigned char request[48];unsigned used=0;
 while(used<sizeof(request)){long n=sys_read(s->fd,request+used,sizeof(request)-used);if(n>0)used+=n;else if(n==-EAGAIN||n==-P260_EINTR)usleep(1000);else fx_park();}
 unsigned char expected[32],tail=38;
 p328_hmac_message(expected,"S22PLUS-FYG8-SWITCH-ROOT-v1",sizeof("S22PLUS-FYG8-SWITCH-ROOT-v1")-1,
  p328_run_id_bytes,s->nonce,6,1,&tail,1);
 if(memcmp(request,"S328",4)||request[4]!=1||request[5]!=38||request[6]!=32||request[7]||
  p328_load_le32(request+8)!=6||p328_load_le32(request+12)!=p328_frame_crc(request,request+16,32)||memcmp(request+16,expected,32))fx_park();
 unsigned char accepted[4]={1,0,0,0};swfx_send(s,170,6,accepted,4);fx_park();__builtin_unreachable();
}
'''


class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.ObservationTests.setUpClass.__func__(cls)
        path=cls.folder/'native.c';text=path.read_bytes()
        text=source.upgrade_native(text,producer.IDENTITY)
        start=text.index(b'static __attribute__((noreturn)) void sw_parent_park')
        end=text.index(b'static long rc1_console(',start)
        text=text[:start]+PEER.replace('@@NAMESPACE@@',producer.IDENTITY.namespace).encode()+text[end:]
        path.write_bytes(text)
        producer.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')
        cls.image=dict(cls.image,switch_root=dict(witness=dict(sha256=WITNESS)))

    running=base.ObservationTests.running

    def observe(self,ctx,folder,*,transition,returned):
        before=dict(fixture=True)
        info=os.stat(ctx.name);endpoint=dict(tty_name=ctx.name.removeprefix('/dev/'),
            generation=dict(node=[info.st_dev,info.st_ino,info.st_rdev]))
        os.close(ctx.fd);ctx.fd=None
        host=native_host.NativeHost.__new__(native_host.NativeHost);host.config=dict(topology='3-7.9')
        host.holders=lambda **kwargs:(dict(endpoint=endpoint),dict(fixture=True))
        host.properties=lambda selected:dict(fixture=True)
        with mock.patch.object(profile,'image_binding'),mock.patch.object(observation.target_io,'usb_snapshot',return_value=before),\
                mock.patch.object(observation.target_io,'wait_departure',return_value=dict(before=before,departed=True)),\
                mock.patch.object(native_host.census,'endpoint',return_value=endpoint):
            return observation.observe(folder,self.image,host,ending='download',hud=False,guard=lambda:None,
                before_extra=transition,before_terminal=returned,first_boot=True,profile=profile.SELECTION)

    def test_actual_native_terminal_ack_and_separate_c_witness_domain(self):
        with self.running() as ctx:
            transitions=[];returns=[];folder=ctx.folder/'complete'
            value=self.observe(ctx,folder,transition=transitions.append,returned=returns.append)
            self.assertEqual(len(transitions),1);self.assertEqual(len(returns),1)
            self.assertTrue(value['proof']['switch_root']['pid1_handoff_proved'])
            self.assertTrue(value['proof']['switch_root']['return_accepted'])
            self.assertEqual(observation.read(folder/'transition-intent.json'),transitions[0])
            with mock.patch.object(profile,'image_binding'):
                self.assertEqual(value['proof'],observation.rederive(folder,self.image,ending='download',hud=False,
                    first_boot=True,profile=profile.SELECTION)['proof'])

    def test_fsynced_pre_exec_cut_never_sends_return_or_promotes_pid1(self):
        with self.running() as ctx:
            transitions=[];returned=mock.Mock();original=observation.IO.frame
            def interrupted(io):
                frame=original(io)
                if frame.frame_type==wire.RECORD and frame.payload[:4]==struct.pack('<I',7):raise OSError('cut after fsynced exec marker')
                return frame
            folder=ctx.folder/'cut'
            with mock.patch.object(observation.IO,'frame',interrupted),self.assertRaises(OSError):
                self.observe(ctx,folder,transition=transitions.append,returned=returned)
            returned.assert_not_called();self.assertEqual(len(transitions),1)
            prefix=observation.switch_prefix(folder,self.image)
            self.assertFalse(prefix['pid1_handoff_proved']);self.assertFalse(prefix['replay_authorized'])

    def test_reached_witness_survives_failed_return_intent_and_partial_tail(self):
        with self.running() as ctx:
            transitions=[];folder=ctx.folder/'witness-cut'
            def unavailable(detail):raise OSError('return owner unavailable before transmission')
            with self.assertRaises(OSError):self.observe(ctx,folder,transition=transitions.append,returned=unavailable)
            prefix=observation.switch_prefix(folder,self.image)
            self.assertTrue(prefix['pid1_handoff_proved']);self.assertFalse(prefix['return_accepted'])
            self.assertFalse(prefix['protocol_complete']);self.assertEqual(len(transitions),1)
            rx=(folder/'rx.bin').read_bytes();tx=(folder/'tx.bin').read_bytes();identity=observation.identity(self.image)
            for tail in (b'S3',b'BAD!'+bytes(12)):
                value=wire.replay_prefix(observation.Codec(identity.namespace),identity,b'k'*32,rx+tail,tx,
                    io_class=observation.IO,witness_sha256=WITNESS)
                self.assertTrue(value['pid1_handoff_proved']);self.assertIsNotNone(value['diagnostic_error'])


if __name__=='__main__':unittest.main()
