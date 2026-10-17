"""Sealed two-file selection and complete maximum-size protocol framing."""
import hashlib
import struct
import unittest
from unittest import mock

import test_s22plus_native_evidence_v1 as previous
import s22plus_native_evidence_profile_v1 as p
import s22plus_native_evidence_build_v1 as builder
import s22plus_native_baseline_v2_candidates as catalog

RUN='a'*32
BINDING=p.binding(RUN,p.AUTOBOOT_PAIR)


def child(data=(b'early',b'runtime')):
    raw=bytearray(b'S22NE01\0'+struct.pack('<4I',2,65535,1,4294967295)+bytes(8))
    for ordinal,((_,mode,gid,maximum,capture),body) in enumerate(zip(p.paths(RUN,p.AUTOBOOT_PAIR),data)):
        row=bytearray(96)
        struct.pack_into('<2IQ6IQI',row,0,ordinal,0,0,100+ordinal,mode,0,gid,1,0,len(body),len(body))
        row[64:96]=hashlib.sha256(body).digest();raw+=row+body
    raw+=b'S22NEND\0'+struct.pack('<Q4I',65536,16,0,len(raw)+32,0)
    return bytes(raw)


def fixture(data=(b'early',b'runtime')):
    body=child(data)
    rows=['RI1_BEGIN version=1','RI1_BIND exact=1','RI1_BLOCK_RO partition=1',
        'RI1_SUPER clean=0 state=65535 recover=1 orphan=4294967295',
        'NE1_READ mount=0 replay=0 output_max=32256']
    for name,value in (('stdout',body),('stderr',b''),('setup',struct.pack('<II',100,0))):
        rows.append(f'UP1_OUTPUT stream={name} bytes={len(value)} hex={value.hex() or "-"}')
    rows+=['UP1_CHILD attempted=1 reaped=1 adopted=0 settled=1 status=0 setup_stage=100 setup_errno=0 error=0 proved=1',
        'RI1_FINAL super_unchanged=1 gpt_unchanged=1 partition_ro=1',
        'RI1_RESULT complete=1 stage=10 errno=0 cleanup_errno=0 partition_ro=1 clean=0 mounted=0 unmounted=0']
    return ('\n'.join(rows)+'\n').encode()


class PairTests(unittest.TestCase):
    def test_only_two_sealed_files_and_distinct_bounds(self):
        rows=p.paths(RUN,p.AUTOBOOT_PAIR)
        self.assertEqual([row[0] for row in rows],['var/lib/lab/s22-early-'+RUN,'var/lib/lab/s22-evidence-'+RUN])
        self.assertEqual([row[3:] for row in rows],[(16384,16384),(15616,15616)])
        self.assertEqual(p.child_maximum(),24576)
        self.assertEqual(p.child_maximum(p.AUTOBOOT_PAIR),64+2*96+32000)
        for run,selection in ((None,p.AUTOBOOT_PAIR),(RUN,'arbitrary'),('../etc/shadow',p.AUTOBOOT_PAIR)):
            with self.assertRaises(ValueError):p.paths(run,selection)

    def test_maximum_pair_fits_unchanged_complete_outer_cap(self):
        data=(b'A'*16384,b'B'*15616);outer=fixture(data)
        self.assertEqual(len(child(data)),p.PAIR_CHILD_MAXIMUM)
        self.assertLessEqual(len(outer),p.MAXIMUM)
        result=p.decode(outer,b'',BINDING)
        self.assertEqual([bytes.fromhex(row['raw_hex']) for row in result['files']],list(data))
        self.assertFalse(result['source_view_clean']);self.assertFalse(result['absence_proves_nonexecution'])
        self.assertEqual(p.decode(fixture((b'',b'')),b'',BINDING)['files'][0]['size'],0)

    def test_wrong_row_set_bound_order_or_tail_cannot_be_promoted(self):
        good=fixture()
        for bad in (good[:-1],good+b'extra\n',good.replace(b'output_max=32256',b'output_max=24576')):
            with self.assertRaises(ValueError):p.decode(bad,b'',BINDING)
        with self.assertRaises(ValueError):p.decode(previous.fixture(),b'',BINDING)
        with self.assertRaises(ValueError):p.decode(good,b'',dict(record_run=RUN))
        for data in ((b'A'*16385,b'B'),(b'A',b'B'*15617)):
            with self.assertRaises(ValueError):p.decode(fixture(data),b'',BINDING)

    def test_selection_propagates_to_builder_and_is_not_a_command_argument(self):
        declared=catalog.declaration('p999','b'*32,'v1.0.0','c'*64,runtime_source=catalog.evidence_source,
            evidence_run=RUN,evidence_selection=p.AUTOBOOT_PAIR)
        image=builder.Builder(declared)
        self.assertEqual(image.native_selection()['runtime_profile']['root_evidence'],BINDING)
        with mock.patch.object(builder.previous.previous.Builder,'build_native_init'), \
                mock.patch.object(builder.producer,'build') as build:
            image.build_native_init(previous.Path('/fixture'),False)
            self.assertEqual(build.call_args.kwargs['selection'],p.AUTOBOOT_PAIR)
        for kwargs in (dict(evidence_selection=p.AUTOBOOT_PAIR),
                dict(runtime_source=catalog.evidence_source,evidence_selection=p.AUTOBOOT_PAIR),
                dict(runtime_source=catalog.evidence_source,evidence_run=RUN,evidence_selection='other')):
            with self.assertRaises(ValueError):catalog.declaration('p999','b'*32,'v1.0.0','c'*64,**kwargs)


if __name__=='__main__':unittest.main()
