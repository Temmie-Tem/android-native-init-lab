"""Revision-3 startup evidence: exact child status, raw cuts and no release."""
import struct
import hashlib
import json
import os
import signal
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import test_s22plus_debian_handoff_v1 as old
import test_s22plus_debian_handoff_observation_v1 as transport
import s22plus_debian_handoff_protocol_v1 as wire
import s22plus_debian_handoff_profile_v1 as profile
from s22plus_native_records_v3 import pin


def boundary(phase,event,ordinal,*,pid=0,status=0,elapsed=None,closed=0,boot=old.BOOT):
    elapsed=100+phase*10+event if elapsed is None else elapsed
    return wire.encode(old.KEY,old.RUN,old.NONCE,wire.BOUNDARY,
        (3000 if phase==1 else 3100)+ordinal,struct.pack('<4I2Q',phase,event,pid,status,elapsed,closed)+boot)


def startup(phase):
    events=(1,2,3,5) if phase==1 else (2,3,5)
    return [boundary(phase,e,i,pid=123 if e>=3 else 0,closed=111 if phase==1 and e==2 else 0)
        for i,e in enumerate(events)]


def transcript():
    rows=old.transcript()
    return rows[:12]+startup(1)+rows[12:13]+startup(2)+rows[13:]


class BoundaryTests(unittest.TestCase):
    def reader(self):return wire.Records(old.KEY,old.RUN,old.NONCE,old.BOOT,old.WITNESS,old.INIT,old.HOOK,observer_revision=3)
    def accept(self,reader,rows):
        for row in rows:reader.accept(wire.frames.decode_frame(row))

    def test_complete_and_legacy_are_distinct(self):
        reader=self.reader();self.accept(reader,transcript())
        self.assertTrue(reader.released);self.assertEqual(len(reader.boundaries),7)
        self.assertEqual(reader.runtime_proof['elapsed_ms'],120000)
        with self.assertRaises(ValueError):self.accept(self.reader(),old.transcript())
        legacy=old.RecordsTests().reader()
        with self.assertRaises(ValueError):self.accept(legacy,transcript())
        current=wire.Records(old.KEY,old.RUN,old.NONCE,old.BOOT,old.WITNESS,old.INIT,old.HOOK,observer_revision=4)
        self.accept(current,transcript());self.assertTrue(current.released)
        self.assertEqual(current.projection()['observer_revision'],4)
        for revision in (True,1,5,'3'):
            with self.assertRaises(ValueError):
                wire.Records(old.KEY,old.RUN,old.NONCE,old.BOOT,old.WITNESS,old.INIT,old.HOOK,observer_revision=revision)

    def test_every_cut_keeps_only_its_prefix_without_runtime_or_release(self):
        rows=transcript()
        for cut in range(12,21):
            reader=self.reader();self.accept(reader,rows[:cut])
            self.assertIsNotNone(reader.init_proof)
            self.assertIsNone(reader.runtime_proof);self.assertFalse(reader.released)

    def test_invalid_close_order_boot_child_status_deadline_and_duplicate_reject(self):
        good=transcript()
        changes=[(13,boundary(1,2,1,closed=110)),(13,boundary(1,2,1,closed=113)),
            (13,boundary(1,2,1,closed=111,boot=b'x'*32)),(14,boundary(1,3,2,pid=1)),
            (15,boundary(1,5,3,pid=124)),(15,boundary(1,5,3,pid=123,status=23<<8)),
            (15,boundary(1,5,3,pid=123,status=15)),(15,boundary(1,5,3,pid=123,elapsed=300000)),
            (14,good[13]),(13,good[14])]
        for index,row in changes:
            with self.subTest(index=index,row=row[:16]):
                rows=list(good);rows[index]=row;reader=self.reader()
                with self.assertRaises(ValueError):self.accept(reader,rows)
                self.assertIsNone(reader.runtime_proof);self.assertFalse(reader.released)

    def test_wait_heartbeat_is_bounded_and_never_completes_startup(self):
        reader=self.reader();self.accept(reader,transcript()[:15])
        self.accept(reader,[boundary(1,4,3,pid=123,elapsed=10113)])
        self.assertFalse(reader.startup_complete(1));self.assertIsNone(reader.runtime_proof)
        with self.assertRaises(ValueError):self.accept(reader,[boundary(1,4,4,pid=123,elapsed=10114)])

    def test_image_revision_cannot_downgrade_pinned_helper_evidence(self):
        # Unchanged root admission and payload generation are outside this
        # test; helper/selection pins, file verification and revision checks run.
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);asset=directory/'asset';asset.write_bytes(b'asset')
            row=pin(asset);close=directory/'close.json'
            close.write_text(json.dumps(dict(terminal_state='ANDROID_CLOSED_HEALTHY')))
            payloads={n:b'asset' for n in ('inittab','qualify','defer-usb','crontab','usb')}
            for helper_revision,selected,valid in ((None,None,True),(3,3,True),(3,None,False),
                    (3,2,False),(None,3,False),(3,True,False),(3,4,False)):
                helpers=directory/'helpers.json'
                helpers.write_text(json.dumps({} if helper_revision is None else dict(observer_revision=helper_revision)))
                # Use real pinned files. The BusyBox metadata check is fixed,
                # with only that unrelated large input's verifier substituted.
                busybox=dict(size=1975064,sha256=profile.switch.BUSYBOX_SHA256)
                value=dict(prepare=row,witness=row,busybox=busybox,checker=row,
                    assets={n:row for n in (*payloads,'hook')},installed_init=dict(size=4,sha256=hashlib.sha256(b'init').hexdigest()),
                    seconds=300,request=37,init_request=39,start_request=41,release_request=40,
                    root_readonly=False,installed_exec=True,persistent_writes=True,helpers_result=pin(helpers))
                if selected is not None:value['observer_revision']=selected
                image=dict(profile=profile.PROFILE,root_admission={},debian_handoff=value)
                original=profile.verify
                with mock.patch.object(profile.inspection,'image_binding',return_value=dict(helper=row)),\
                        mock.patch.object(profile,'payloads',return_value=(b'init',payloads)),\
                        mock.patch.object(profile.staged,'execution_binding',return_value=dict(checker=row)),\
                        mock.patch.object(profile,'PREVIOUS_CLOSE',pin(close)),\
                        mock.patch.object(profile,'verify',side_effect=lambda r:asset if r is busybox else original(r)):
                    if valid:profile.image_binding(image)
                    else:
                        with self.assertRaises(ValueError):profile.image_binding(image)


BOUNDARIES=r'''
    if(ordinal<2) {
     unsigned phase=ordinal+1,number=0;
     for(unsigned event=phase==1?1:2;event<=5;++event) {
      if(event==4)continue;
      unsigned char edge[64]={0};p328_store_le32(edge,phase);p328_store_le32(edge+4,event);
      p328_store_le32(edge+8,event>=3?123:0);p328_store_le32(edge+16,100+phase*10+event);
      if(phase==1&&event==2)p328_store_le32(edge+24,111);
      if(@@NAMESPACE@@_kernel_boot_id(edge+32))fx_park();
      swfx_send(s,177,(phase==1?3000:3100)+number++,edge,sizeof(edge));
      if(phase==1&&event==2&&!strcmp(getenv("P364_CASE"),"boundary-pause"))for(;;)usleep(1000);
     }
    }
'''


class BoundaryTransportTests(transport.ObservationTests):
    PEER=transport.PEER.replace('swfx_send(s,176,2000+ordinal,data,sizeof(data));',
        'swfx_send(s,176,2000+ordinal,data,sizeof(data));'+BOUNDARIES)

    @classmethod
    def setUpClass(cls):
        super().setUpClass();cls.selection['observer_revision']=3

    def test_cut_after_reopen_retains_boundary_without_releasing_or_reconnecting(self):
        with self.running() as ctx:
            folder=ctx.folder/'boundary-cut';seen=[];original=transport.observation.IO.frame
            def cut(io):
                frame=original(io)
                if frame.frame_type==wire.BOUNDARY and frame.sequence==3001:
                    raise OSError('transport lost after retained reopen boundary')
                return frame
            with mock.patch.object(transport.observation.IO,'frame',cut),self.assertRaises(OSError):
                self.observe(ctx,folder,lambda d:None,seen.append)
            value=transport.observation.switch_prefix(folder,self.image)['debian_handoff']
            self.assertEqual([r['event'] for r in value['startup_boundaries']],[1,2])
            self.assertEqual(len(seen),2);self.assertIsNone(value['runtime_proof'])
            self.assertFalse(value['acm_release_accepted']);self.assertFalse(value['ssh_access_proved'])
            receipts=[transport.observation.read(p) for p in sorted(folder.rglob('debian-receive-*.json'))]
            self.assertTrue(receipts);self.assertTrue(all(r['clock']=='CLOCK_BOOTTIME' for r in receipts))
            self.assertEqual([r['received_ns'] for r in receipts],sorted(r['received_ns'] for r in receipts))

    def test_receipt_failure_keeps_raw_evidence_without_release(self):
        with self.running() as ctx:
            folder=ctx.folder/'receipt-cut';seen=[];original=wire.publish
            def publish(path,value):
                if value.get('frame_type')==wire.BOUNDARY:raise OSError('receipt write failed')
                return original(path,value)
            with mock.patch.object(wire,'publish',publish),self.assertRaises(OSError):
                self.observe(ctx,folder,lambda d:None,seen.append)
            value=transport.observation.switch_prefix(folder,self.image)['debian_handoff']
            self.assertTrue(value['startup_boundaries']);self.assertEqual(len(seen),2)
            self.assertFalse(value['acm_release_accepted'])

    def test_real_pty_hangup_closes_owner_and_preserves_reopen_prefix(self):
        with self.running('boundary-pause') as ctx:
            folder=ctx.folder/'pty-hangup';seen=[];original=transport.observation.IO.frame
            def hangup(io):
                frame=original(io)
                if frame.frame_type==wire.BOUNDARY and frame.sequence==3001:
                    os.killpg(ctx.proc.pid,signal.SIGKILL);ctx.proc.wait(timeout=3)
                return frame
            with mock.patch.object(transport.observation.IO,'frame',hangup),self.assertRaises(EOFError):
                self.observe(ctx,folder,lambda d:None,seen.append)
            value=transport.observation.switch_prefix(folder,self.image)['debian_handoff']
            self.assertEqual([r['event'] for r in value['startup_boundaries']],[1,2])
            self.assertEqual(len(seen),2);self.assertIsNone(value['runtime_proof'])
            self.assertFalse(value['acm_release_accepted'])
            close=transport.observation.read(folder/'close.json')['acquisition']['close']
            self.assertTrue(close['descriptor_closed']);self.assertEqual(close['exclusive_release_errno'],5)


if __name__=='__main__':unittest.main()
