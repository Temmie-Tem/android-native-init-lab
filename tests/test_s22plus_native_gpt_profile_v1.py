"""Exact-byte GPT parsing and real C/PTTY pre-effect callback ordering."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'workspace/public/src/scripts/revalidation'),
    str(ROOT/'workspace/public/src/scripts/analysis')]
import s22plus_native_gpt_profile_v1 as gpt
import s22plus_native_gpt_layout_h0 as layout
import s22plus_native_observation_v3 as observation
import s22plus_native_output_drain_source_v1 as drain
import s22plus_native_records_v3 as records
import test_s22plus_native_observation_v3 as base
import test_s22plus_native_resident_v1 as producer
from test_s22plus_native_gpt_v1_h0 import reference


def binding(directory):
    before,after=reference()
    regions,geometry=layout.construct(before[:24576],before[24576:],62305280,
        native_guid=b'N'*16,native_bytes=128*1024**3)
    receipts=[]
    for row in regions:
        item=dict(name=row['name'],first_lba=row['first_lba'])
        for key in ('original','proposed'):
            path=directory/(row['name']+'-'+key+'.bin');path.write_bytes(row[key]);item[key]=records.pin(path)
        receipts.append(item)
    value=dict(schema=layout.SCHEMA,status='PASS_H0_EXACT_LAYOUT_CONSTRUCTION',regions=receipts,
        layout=geometry,changed_blocks=[dict(lba=n) for n in (1,3,62305272,62305279)])
    return dict(proposal=records.publish(directory/'proposal.json',value),regions=receipts,layout=geometry),\
        dict(original=before,proposed=after)


def output(selection,sealed,*,order=gpt.LBAS,skips=(),kernel_new=None):
    _,mode,kind=gpt.SELECTIONS[selection]
    events=[]
    if mode:
        for index,lba in enumerate(order):
            for event in ((3,) if index in skips else (1,2)):
                events.append(f'GPT1_STEP event={event} ordinal={index} lba={lba}\n')
    writes=4-len(skips) if mode else 0
    new=selection in ('gpt-proposed','gpt-after-reset') if kernel_new is None else kernel_new
    user,native=(gpt.NEW_USER,gpt.NATIVE_SECTORS) if new else (gpt.OLD_USER,0)
    header=''.join(events)+(f'GPT1_RESULT mode={mode} status=0 io_errno=0 close_errno=0 '
        f'writes={writes} completed={writes} skipped={len(skips)} last_read_kind={1 if kind=="original" else 2} '
        f'userdata_sectors={user} native_sectors={native} filesystem_errno=0\nGPT1_DATA bytes=61440\n')
    tail=b''
    if selection in gpt.AFTER_RESET:
        sb=bytearray(108);struct.pack_into('<I',sb,0,0xf2f52010)
        struct.pack_into('<4I',sb,8,12,0,12,9)
        count=(user*512-16384)//4096
        struct.pack_into('<Q',sb,36,count)
        struct.pack_into('<I',sb,48,count//512-1);struct.pack_into('<I',sb,72,512)
        tail=b'GPT1_F2FS bytes=216\n'+bytes(sb)*2
    return header.encode()+sealed[kind]+tail+b'GPT1_END\n'


class ProfileTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.folder=Path(temporary.name);self.binding,self.sealed=binding(self.folder)
        self.image=dict(profile=gpt.PROFILE,run_id_hex='1'*32,gpt=self.binding)

    def test_exact_modes_include_reverse_side_restoration_and_new_filesystem_geometry(self):
        for selection in gpt.SELECTIONS:
            with self.subTest(selection=selection):
                profile=gpt.Profile(self.image,selection);raw=output(selection,self.sealed)
                result=profile.project(raw,b'',(5,0,0,0,len(raw),0,1),requested=True)
                self.assertEqual(result['status'],'PASS_EXACT_GPT')
                self.assertEqual(profile.MUTATES,selection in ('gpt-apply','gpt-restore'))
        raw=output('gpt-restore',self.sealed,order=gpt.LBAS[2:]+gpt.LBAS[:2],skips=(0,1),kernel_new=True)
        result=gpt.decode(raw,'gpt-restore',self.sealed)
        self.assertEqual((result['writes'],result['skipped'],result['final_pair']),(2,2,'original'))
        fs=gpt.decode(output('gpt-after-reset',self.sealed),'gpt-after-reset',self.sealed)['filesystem']
        self.assertEqual(fs['requested_bytes'],102497239040)
        self.assertFalse(fs['complete_filesystem_health_proved'])

    def test_partial_media_stale_kind_wrong_geometry_and_lost_events_cannot_pass(self):
        good=output('gpt-apply',self.sealed)
        cut=good.index(b'GPT1_DATA bytes=61440\n')+len(b'GPT1_DATA bytes=61440\n')
        damaged=bytearray(good);damaged[cut+12345]^=1
        variants=[good[:-1],good+b'extra',bytes(damaged),good.replace(b'io_errno=0',b'io_errno=5'),
            good.replace(b'status=0',b'status=6'),good.replace(b'completed=4',b'completed=3'),
            good.replace(b'last_read_kind=2',b'last_read_kind=1'),good.split(b'\n',1)[1],
            output('gpt-apply',self.sealed,order=gpt.LBAS[2:]+gpt.LBAS[:2]),
            output('gpt-apply',self.sealed,kernel_new=True)]
        profile=gpt.Profile(self.image,'gpt-apply')
        for raw in variants:
            with self.subTest(sha=records.digest(raw)):
                self.assertEqual(profile.project(raw,b'',(5,0,0,0,len(raw),0,1),requested=True)['status'],'NO_PROOF')
        for terminal in (None,(5,4,0,0,len(good),1,1),(5,0,0,0,len(good)-1,0,1)):
            self.assertEqual(profile.project(good,b'',terminal,requested=True)['status'],'NO_PROOF')
        self.assertEqual(profile.project(b'',b'',None,requested=False)['status'],'NO_PROOF')

    def test_old_filesystem_capacity_and_mismatched_superblocks_are_rejected(self):
        raw=output('gpt-after-reset',self.sealed)
        start=raw.index(b'GPT1_F2FS bytes=216\n')+len(b'GPT1_F2FS bytes=216\n')
        wrong=bytearray(raw);struct.pack_into('<Q',wrong,start+36,gpt.OLD_USER//8)
        struct.pack_into('<Q',wrong,start+108+36,gpt.OLD_USER//8)
        mismatch=bytearray(raw);mismatch[start+108+48]^=1
        for value in (wrong,mismatch):
            with self.assertRaises(ValueError):gpt.decode(bytes(value),'gpt-after-reset',self.sealed)


class GptObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.ObservationTests.setUpClass.__func__(cls)
        cls.binding,cls.sealed=binding(cls.folder)
        cls.image=dict(cls.image,profile=gpt.PROFILE,gpt=cls.binding)
        path=cls.folder/'native.c';text=drain.upgrade_native(path.read_bytes()).decode()
        marker='const char *command=text;';assert text.count(marker)==1
        text=text.replace(marker,marker+'''\n
 if(!strncmp(command,"exec /s22-display --gpt-",sizeof("exec /s22-display --gpt-")-1))
   command=strstr(command,"--gpt-apply ")?"test -f gpt-intent && cat gpt.bin":"cat gpt.bin";
''')
        path.write_text(text)
        producer.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')

    running=base.ObservationTests.running

    def test_durable_callback_precedes_actual_c_execution_and_full_raw_replay(self):
        with self.running() as ctx:
            (ctx.folder/'gpt.bin').write_bytes(output('gpt-apply',self.sealed))
            calls=[]
            def intent(request):
                calls.append(request)
                records.publish(ctx.folder/'gpt-intent',request)
            directory=ctx.folder/'apply'
            value=observation.observe(directory,self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,before_extra=intent,
                first_boot=True,profile='gpt-apply')
            self.assertEqual(len(calls),1);self.assertEqual(calls[0]['sequence'],5)
            self.assertEqual(calls[0]['body_sha256'],records.digest(gpt.Profile(self.image,'gpt-apply').BODY))
            self.assertEqual(value['proof']['gpt']['status'],'PASS_EXACT_GPT')
            self.assertTrue(value['proof']['detach_ack_observed']);self.assertIsNone(ctx.fd)
            self.assertEqual(value,observation.rederive(directory,self.image,ending='detach',hud=False,
                first_boot=True,profile='gpt-apply'))

    def test_failed_intent_or_stale_boot_sends_no_mutating_exec(self):
        for stale in (False,True):
            with self.subTest(stale=stale),self.running() as ctx:
                host=base.HostFixture(ctx);previous=None
                if stale:
                    previous=observation.observe(ctx.folder/'initial',self.image,host,ending='detach',hud=False,
                        guard=lambda:None,before_terminal=lambda:None,first_boot=True)['proof']
                    previous=dict(previous,kernel_boot_identity_sha256='0'*64)
                directory=ctx.folder/'blocked';callback=mock.Mock(side_effect=OSError('durable store unavailable'))
                with self.assertRaises((ValueError,OSError)):
                    observation.observe(directory,self.image,host,ending='detach',hud=False,
                        guard=lambda:None,before_terminal=lambda:None,before_extra=callback,
                        first_boot=not stale,previous=previous,profile='gpt-apply')
                self.assertNotIn(gpt.Profile(self.image,'gpt-apply').BODY,(directory/'tx.bin').read_bytes())
                if stale:callback.assert_not_called()
                else:self.assertEqual(callback.call_count,1)
                self.assertIsNone(ctx.fd)

    def test_missing_owner_callback_is_rejected_before_open(self):
        with self.running() as ctx:
            with self.assertRaisesRegex(ValueError,'durable owner callback'):
                observation.observe(ctx.folder/'unowned',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                    guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile='gpt-apply')
            self.assertFalse((ctx.folder/'unowned').exists())


if __name__=='__main__':unittest.main()
