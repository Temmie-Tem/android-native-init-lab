"""Host byte construction/inverse vectors, without device or firmware writes."""
import binascii
from pathlib import Path
import struct
import sys
import unittest

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/analysis'),
    str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation')]
import s22plus_native_gpt_layout_h0 as plan
import s22plus_native_storage_census_v1 as census
from test_s22plus_native_storage_census_v1 import fixture


def original(*,duplicate=False,occupied=False,overlap=False):
    raw=fixture(count=44,backup_blocks=9);prefix=raw[3:].split(b'\n',8)
    geometry=prefix[:8];body=prefix[8]
    primary=bytearray(body[:24576]);backup=bytearray(body[24576:61440])
    table=bytearray(primary[8192:8192+44*128])
    for i in range(2,39):
        offset=i*128;first=35000+i*16
        guid=(i+1).to_bytes(16,'little')
        if duplicate and i==3:guid=(3).to_bytes(16,'little')
        struct.pack_into('<16s16sQQQ',table,offset,b'T'*16,guid,first,first+7,0)
        label=('part'+str(i+1)).encode('utf-16-le');table[offset+56:offset+56+len(label)]=label
    if occupied:table[40*128:41*128]=table[:128]
    if overlap:struct.pack_into('<Q',table,3*128+32,35000+2*16)
    primary[8192:8192+len(table)]=table;backup[:len(table)]=table
    for data,offset in ((primary,4096),(backup,8*4096)):
        struct.pack_into('<I',data,offset+88,binascii.crc32(table)&0xffffffff)
        struct.pack_into('<I',data,offset+16,0)
        struct.pack_into('<I',data,offset+16,binascii.crc32(data[offset:offset+92])&0xffffffff)
    return bytes(primary),bytes(backup),62_500_000,geometry


def joined(regions,layout,geometry):
    lines=list(geometry)
    lines[3]=str((layout['userdata_new_last_lba']+1-layout['userdata_first_lba'])*8).encode()
    bracket=b'\n'.join(lines)+b'\n'
    return b'G0\n'+bracket+b''.join(row['proposed'] for row in regions)+b'G1\n'+bracket+b'END\n'


class LayoutTests(unittest.TestCase):
    def test_128g_reservation_preserves_originals_and_changes_only_the_same_blocks(self):
        primary,backup,total,geometry=original()
        regions,layout=plan.construct(primary,backup,total,native_guid=b'N'*16,
            native_bytes=128*1024**3)
        decoded=census.decode(joined(regions,layout,geometry),backup_blocks=9)
        self.assertEqual(decoded['entries'][-1]['size_bytes'],128*1024**3)
        self.assertEqual(decoded['entries'][-1]['first_lba'],decoded['userdata']['last_lba']+1)
        self.assertEqual(regions[0]['original'],primary)
        self.assertEqual(regions[1]['original'],backup)
        self.assertEqual([r['first_lba']+off//4096 for r in regions
            for off in range(0,len(r['original']),4096)
            if r['original'][off:off+4096]!=r['proposed'][off:off+4096]],
            [1,3,total-8,total-1])
        self.assertEqual(regions[0]['proposed'][8192:8192+39*128],primary[8192:8192+39*128])
        for size in (True,0,65*1024**3,256*1024**3):
            with self.subTest(size=size),self.assertRaises(ValueError):
                plan.construct(primary,backup,total,native_guid=b'N'*16,native_bytes=size)

    def test_exact_64g_shape_and_only_four_metadata_blocks_change(self):
        primary,backup,total,geometry=original()
        regions,layout=plan.construct(primary,backup,total,native_guid=b'N'*16)
        decoded=census.decode(joined(regions,layout,geometry),backup_blocks=9)
        self.assertEqual(len(decoded['entries']),41)
        native=decoded['entries'][-1]
        self.assertEqual((native['index'],native['name'],native['size_bytes']),(41,'native_data',64*1024**3))
        self.assertEqual(native['first_lba']*4096%1048576,0)
        self.assertEqual(native['first_lba'],decoded['userdata']['last_lba']+1)
        self.assertEqual(native['type_guid'],decoded['userdata']['type_guid'])
        changes=[]
        for region in regions:
            for offset in range(0,len(region['original']),4096):
                if region['original'][offset:offset+4096]!=region['proposed'][offset:offset+4096]:
                    changes.append(region['first_lba']+offset//4096)
        self.assertEqual(changes,[1,3,total-8,total-1])
        self.assertEqual(regions[0]['proposed'][:4096],primary[:4096])
        self.assertEqual(regions[0]['proposed'][8192:8192+39*128],primary[8192:8192+39*128])

    def test_original_duplicate_guids_are_preserved_without_strict_proof_upgrade(self):
        primary,backup,total,geometry=original(duplicate=True)
        regions,layout=plan.construct(primary,backup,total,native_guid=b'N'*16)
        self.assertEqual(regions[0]['proposed'][8192:8192+39*128],primary[8192:8192+39*128])
        with self.assertRaisesRegex(census.CensusError,'GUID'):
            census.decode(joined(regions,layout,geometry),backup_blocks=9)

    def test_exact_original_blocks_restore_every_simulated_prefix_and_torn_block(self):
        primary,backup,total,_=original(duplicate=True)
        regions,_=plan.construct(primary,backup,total,native_guid=b'N'*16)
        before=b''.join(row['original'] for row in regions)
        after=b''.join(row['proposed'] for row in regions)
        offsets=[i for i in range(0,len(before),4096) if before[i:i+4096]!=after[i:i+4096]]
        # Byte-array interruption models make no storage atomicity claim.
        for count in range(len(offsets)+1):
            for cut in (0,1,511,512,4095,4096):
                state=bytearray(before)
                for off in offsets[:count]:state[off:off+4096]=after[off:off+4096]
                if count<len(offsets):
                    off=offsets[count];state[off:off+cut]=after[off:off+cut]
                for off in offsets:state[off:off+4096]=before[off:off+4096]
                self.assertEqual(bytes(state),before)

    def test_bad_originals_and_reused_guid_fail_before_any_proposal(self):
        primary,backup,total,_=original()
        for guid in (b'\0'*16,(1).to_bytes(16,'little'),b'D'*16,b'short'):
            with self.subTest(guid=guid),self.assertRaises(ValueError):
                plan.construct(primary,backup,total,native_guid=guid)
        for args in ({'occupied':True},{'overlap':True}):
            a,b,t,_=original(**args)
            with self.assertRaises(ValueError):plan.construct(a,b,t,native_guid=b'N'*16)
        damaged=bytearray(primary);damaged[510]=0
        with self.assertRaisesRegex(ValueError,'MBR'):
            plan.construct(bytes(damaged),backup,total,native_guid=b'N'*16)
        damaged=bytearray(backup);damaged[-4096+16]^=1
        with self.assertRaisesRegex(ValueError,'CRC'):
            plan.construct(primary,bytes(damaged),total,native_guid=b'N'*16)


if __name__=='__main__':unittest.main()
