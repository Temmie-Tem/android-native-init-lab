"""Real native C admission and three independent HMAC phases over a PTY.

Only terminal effects are substituted here; the ARM64 VM runs actual init.
"""
import os
import struct
import unittest
from unittest import mock
import test_s22plus_native_observation_v3 as base
import test_s22plus_native_resident_v1 as producer
import test_s22plus_switch_root_observation_v1 as previous
import s22plus_switch_root_source_v1 as source
import s22plus_debian_handoff_profile_v1 as profile
import s22plus_debian_handoff_protocol_v1 as wire
import s22plus_native_observation_v3 as observation
import s22plus_native_host_v3 as host_module

PEER=previous.PEER[:previous.PEER.index(' unsigned char request[48]')].replace(
    'p328_store_le32(data+120,15);p328_store_le32(data+124,1);',
    'p328_store_le32(data+120,0);p328_store_le32(data+124,0);')+r'''
 for(unsigned phase=0;phase<2;++phase) {
  unsigned char request[48];unsigned used=0;unsigned sequence=phase?7:6;unsigned char kind=phase?40:39;
  while(used<sizeof(request)){long n=sys_read(s->fd,request+used,sizeof(request)-used);if(n>0)used+=n;else if(n==-EAGAIN||n==-P260_EINTR)usleep(1000);else fx_park();}
  unsigned char expected[32];
  p328_hmac_message(expected,"S22PLUS-FYG8-SWITCH-ROOT-v1",sizeof("S22PLUS-FYG8-SWITCH-ROOT-v1")-1,
   p328_run_id_bytes,s->nonce,sequence,1,&kind,1);
  if(memcmp(request,"S328",4)||request[4]!=1||request[5]!=kind||request[6]!=32||request[7]||
   p328_load_le32(request+8)!=sequence||p328_load_le32(request+12)!=p328_frame_crc(request,request+16,32)||memcmp(request+16,expected,32))fx_park();
  unsigned char accepted[4]={1,0,0,0};swfx_send(s,phase?173:171,sequence,accepted,4);
  if(!phase) {
   unsigned char data[116]={0};p328_store_le32(data,1);p328_store_le32(data+4,8);p328_store_le32(data+8,41);
   if(@@NAMESPACE@@_kernel_boot_id(data+12))fx_park();memset(data+44,0x66,32);memset(data+76,0x77,32);
   swfx_send(s,172,7,data,sizeof(data));
  }
 }
 for(;;)usleep(1000);
}
'''


class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.ObservationTests.setUpClass.__func__(cls)
        path=cls.folder/'native.c';text=source.upgrade_native(path.read_bytes(),producer.IDENTITY)
        start=text.index(b'static __attribute__((noreturn)) void sw_parent_park');end=text.index(b'static long rc1_console(',start)
        text=text[:start]+PEER.replace('@@NAMESPACE@@',producer.IDENTITY.namespace).encode()+text[end:];path.write_bytes(text)
        producer.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')
        cls.selection=dict(witness=dict(sha256='99'*32),installed_init=dict(sha256='66'*32),assets=dict(hook=dict(sha256='77'*32)))
        cls.image=dict(cls.image,profile=profile.PROFILE,debian_handoff=cls.selection)

    running=base.ObservationTests.running

    def observe(self,ctx,folder,transition,continuation):
        info=os.stat(ctx.name);endpoint=dict(tty_name=ctx.name.removeprefix('/dev/'),
            generation=dict(node=[info.st_dev,info.st_ino,info.st_rdev]))
        os.close(ctx.fd);ctx.fd=None
        host=host_module.NativeHost.__new__(host_module.NativeHost);host.config=dict(topology='3-7.9')
        host.holders=lambda **kw:(dict(endpoint=endpoint),dict(fixture=True));host.properties=lambda e:dict(fixture=True)
        with mock.patch.object(profile,'image_binding'),mock.patch.object(observation.target_io,'usb_snapshot',return_value=dict(fixture=True)),\
                mock.patch.object(observation.target_io,'wait_departure',return_value=dict(departed=True)),\
                mock.patch.object(host_module.census,'endpoint',return_value=endpoint):
            return observation.observe(folder,self.image,host,ending='handoff',hud=False,guard=lambda:None,
                before_extra=transition,before_terminal=continuation,first_boot=True,profile=profile.SELECTION)

    def test_original_native_admission_then_witness_init_release_and_closed_descriptor(self):
        with self.running() as ctx:
            intents=[];continuations=[];folder=ctx.folder/'complete'
            value=self.observe(ctx,folder,intents.append,continuations.append)
            self.assertEqual(len(intents),1);self.assertEqual(len(continuations),2)
            self.assertEqual(value['proof']['ending'],'handoff');self.assertTrue(value['proof']['debian_handoff']['init_proof'])
            self.assertTrue(observation.read(folder/'close.json')['acquisition']['local_carrier'])
            self.assertEqual(continuations[0]['request']['mode'],'debian-init-continue')
            self.assertEqual(continuations[1]['request']['mode'],'debian-acm-release')
            with mock.patch.object(profile,'image_binding'):
                self.assertEqual(value['proof'],observation.rederive(folder,self.image,ending='handoff',hud=False,
                    first_boot=True,profile=profile.SELECTION)['proof'])

    def test_capture_cut_after_init_preserves_pid1_but_cannot_release_or_claim_ssh(self):
        with self.running() as ctx:
            folder=ctx.folder/'cut';seen=[];original=observation.IO.frame
            def cut(io):
                frame=original(io)
                if frame.frame_type==wire.INIT_PROOF:raise OSError('cut after fsynced PID1 proof')
                return frame
            with mock.patch.object(observation.IO,'frame',cut),self.assertRaises(OSError):
                self.observe(ctx,folder,lambda d:None,seen.append)
            self.assertEqual(len(seen),1)
            prefix=observation.switch_prefix(folder,self.image)
            self.assertIsNotNone(prefix['debian_handoff']['init_proof'])
            self.assertFalse(prefix['debian_handoff']['acm_release_accepted'])
            self.assertFalse(prefix['debian_handoff']['ssh_access_proved']);self.assertFalse(prefix['replay_authorized'])
            tx=(folder/'tx.bin').read_bytes()
            run=bytes.fromhex(self.image['run_id_hex']);key=b'k'*32;bound=observation.identity(self.image)
            rx=(folder/'rx.bin').read_bytes();io=observation.IO(observation.Codec(bound.namespace),key,bound,rx=rx,tx=tx);io.handshake()
            forbidden=wire.encode(key,run,io.audit.nonce,wire.RELEASE,7)
            self.assertNotIn(forbidden,tx)

    def test_failed_continuation_receipt_never_transmits_init_request(self):
        with self.running() as ctx:
            folder=ctx.folder/'intent-cut'
            with self.assertRaises(OSError):
                self.observe(ctx,folder,lambda d:None,lambda d:(_ for _ in ()).throw(OSError('intent disk full')))
            prefix=observation.switch_prefix(folder,self.image)
            self.assertIsNotNone(prefix['debian_handoff']['root_transition']['proof'])
            self.assertFalse(prefix['debian_handoff']['continue_accepted'])
            self.assertIsNone(prefix['debian_handoff']['init_proof'])


if __name__=='__main__':unittest.main()
