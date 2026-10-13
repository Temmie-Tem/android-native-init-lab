"""Strict local history semantics, independent of successful USB delivery."""
import copy
import errno
import hashlib
import os
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_evidence_v1 as e

KEY=b'K'*32;RUN=b'R'*16;BOOT=b'B'*32;NONCE=b'N'*32
EXPECTED=dict(run_id_hex=RUN.hex(),boot=BOOT.hex(),nonce_sha256=hashlib.sha256(NONCE).hexdigest(),
 init_sha256=(b'i'*32).hex(),hook_sha256=(b'h'*32).hex(),root_device=dict(major=8,minor=41),
 key_sha256=hashlib.sha256(KEY).hexdigest())


def header():
    h=bytearray(256);h[:8]=b'S22DE01\0';struct.pack_into('<II',h,8,1,256)
    h[16:32]=RUN;h[32:64]=BOOT;h[64:96]=NONCE
    struct.pack_into('<QQ4I',h,96,100000,400000,4,128,120,15616)
    h[128:160]=b'i'*32;h[160:192]=b'h'*32;struct.pack_into('<Q',h,192,os.makedev(8,41))
    h[224:]=e.tag(KEY,h[:224]);return bytes(h)


def encode(rows):
    raw=bytearray(header());last=bytes(raw[224:]);off=0
    for seq,row in enumerate(rows):
        kind,elapsed,phase,event,a,b,c=row
        r=bytearray(128);r[:8]=b'S22DER1\0';struct.pack_into('<IIQIIQQQII',r,8,seq,kind,elapsed,phase,event,a,b,c,off,0)
        r[64:96]=last;r[96:]=e.tag(KEY,r[:96]);last=bytes(r[96:]);raw+=r
        if kind==e.REPORT_LOST:off=1
    return bytes(raw)


def events(*,lost=False):
    rows=[(e.INIT,100,0,0,1,0,0),(e.START,200,0,0,8,0,0)]
    if lost:rows.append((e.REPORT_LOST,201,0,0,errno.EIO,175,8))
    rows.extend([(e.PROGRESS,300,1,0,0,0,0),
        (e.BOUNDARY,400,1,1,0,0,0),(e.BOUNDARY,500,1,2,0,0,0 if lost else 450),
        (e.BOUNDARY,600,1,3,42,0,0),(e.BOUNDARY,700,1,5,42,0,0),
        (e.PROGRESS,800,2,0,0,0,0),(e.BOUNDARY,900,2,2,0,0,0),
        (e.BOUNDARY,1000,2,3,43,0,0),(e.BOUNDARY,1100,2,5,43,0,0)])
    rows.extend((e.PROGRESS,1200+i*10000,3 if i==0 else 4,i,i*10000,3,0) for i in range(13))
    rows.append((e.COMPLETE,121201,0,0,0,0,0))
    if not lost:rows.append((e.RELEASE,121300,0,0,9,0,0))
    return rows


class EvidenceTests(unittest.TestCase):
    def decode(self,data,**kw):return e.decode(data,KEY,EXPECTED,**kw)

    def test_online_and_reporting_lost_have_same_local_runtime_proof(self):
        for lost in (False,True):
            value=self.decode(encode(events(lost=lost)))
            self.assertTrue(value['local_runtime_proved']);self.assertTrue(value['rcs_completed'])
            self.assertTrue(value['runlevel_completed']);self.assertEqual(value['report_disabled'],lost)
            self.assertEqual(value['release_authenticated'],not lost)
            self.assertFalse(value['host_receipt_proved']);self.assertFalse(value['ssh_access_proved'])
            self.assertFalse(value['replay_authorized']);self.assertLessEqual(value['raw']['size'],16384)
            opened=[r['reporting_reopened'] for r in value['records'] if r['kind']==e.BOUNDARY and r['event']==2]
            self.assertEqual(opened,[not lost,not lost])

    def test_every_partial_prefix_keeps_only_past_facts(self):
        data=encode(events())
        for size in (256,384,512,513,1025,len(data)-1):
            with self.subTest(size=size):
                value=self.decode(data[:size],allow_prefix=True)
                self.assertFalse(value['release_authenticated']);self.assertFalse(value['replay_authorized'])
                self.assertEqual(value['valid_prefix_bytes'],256+128*len(value['records']))
        with self.assertRaises(ValueError):self.decode(data[:-1])
        value=self.decode(data+b'bad',allow_prefix=True)
        self.assertTrue(value['local_runtime_proved']);self.assertEqual(value['status'],'AUTHENTICATED_PREFIX_ONLY')

    def test_wrong_key_run_boot_nonce_executable_and_root_reject(self):
        data=encode(events())
        for key,bad in [('run_id_hex','0'*32),('boot','0'*64),('nonce_sha256','0'*64),
            ('init_sha256','0'*64),('hook_sha256','0'*64),('root_device',dict(major=8,minor=42)),('key_sha256','0'*64)]:
            with self.subTest(key=key),self.assertRaises(ValueError):e.decode(data,KEY,dict(EXPECTED,**{key:bad}))
        with self.assertRaises(ValueError):e.decode(data,b'X'*32,EXPECTED)

    def test_unclassified_or_unjoined_report_loss_cannot_disable_reporting(self):
        prefix=events()[:2]
        cases=[(e.REPORT_LOST,201,2,0,errno.EPROTO,175,4095),
            (e.REPORT_LOST,201,0,0,errno.EIO,176,2000),(e.REPORT_LOST,201,0,0,errno.EIO,175,9),
            (e.REPORT_LOST,201,2,0,errno.ENOENT,0,0),(e.REPORT_LOST,201,1,0,errno.EACCES,0,0)]
        for row in cases:
            with self.subTest(row=row),self.assertRaises(ValueError):self.decode(encode(prefix+[row]))
        value=self.decode(encode(prefix+[(e.REPORT_LOST,201,1,0,errno.ENOENT,0,0)]))
        self.assertTrue(value['report_disabled']);self.assertFalse(value['rcs_completed'])

    def test_report_loss_is_sticky_and_forbids_release(self):
        rows=events(lost=True)
        with self.assertRaises(ValueError):self.decode(encode(rows+[(e.RELEASE,121300,0,0,9,0,0)]))
        with self.assertRaises(ValueError):self.decode(encode(rows[:3]+[rows[2]]))
        before_start=events()[:1]+[(e.REPORT_LOST,101,0,0,errno.EIO,175,8)]
        with self.assertRaises(ValueError):self.decode(encode(before_start))

    def test_liveness_cannot_outpace_original_time_or_skip_samples(self):
        for label in ('future','late','early','skip','services','child'):
            rows=events();index=next(i for i,r in enumerate(rows) if r[0]==e.PROGRESS and r[3]==1)
            row=list(rows[index])
            if label=='future':row[1]=1500
            if label=='late':row[4]=20001
            if label=='early':row[4]=9999
            if label=='skip':row[3]=2
            if label=='services':row[5]=1
            if label=='child':
                index=next(i for i,r in enumerate(rows) if r[0]==e.BOUNDARY and r[2]==1 and r[3]==5)
                row=list(rows[index]);row[5]=256
            rows[index]=tuple(row)
            with self.subTest(label=label),self.assertRaises(ValueError):self.decode(encode(rows))

    def test_corrupt_authentication_sequence_tail_and_header_reject(self):
        data=encode(events())
        for offset in (16,200,255,256+8,256+64,256+127):
            bad=bytearray(data);bad[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(ValueError):self.decode(bytes(bad))
        with self.assertRaises(ValueError):self.decode(data[:256]+data[384:])
        with self.assertRaises(ValueError):self.decode(data+b'\0'*16384)

    def test_stop_preserves_prior_proof_and_cannot_continue(self):
        rows=events()[:-1]+[(e.STOP,121202,0,0,errno.EIO,8,0)]
        result=self.decode(encode(rows));self.assertTrue(result['local_runtime_proved']);self.assertTrue(result['required_check_stopped'])
        with self.assertRaises(ValueError):self.decode(encode(rows+[(e.RELEASE,121203,0,0,9,0,0)]))
