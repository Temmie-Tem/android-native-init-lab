"""Synthetic GPT semantics and real shell transport decoding; no block writes."""
import base64
import binascii
import gzip
from pathlib import Path
import struct
import stat
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_storage_census_v1 as census
import s22plus_root_console_v1 as wire


def fixture(*, backup_changed=False, overlap=False, count=128, backup_blocks=5):
    block=4096;total=62_500_000;first=3_726_848;last=total-backup_blocks-1
    table=bytearray(min(count,128)*128)
    def entry(index,name,start,end):
        offset=index*128
        struct.pack_into('<16s16sQQQ',table,offset,b'T'*16,(index+1).to_bytes(16,'little'),start,end,0)
        value=name.encode('utf-16-le');table[offset+56:offset+56+len(value)]=value
    entry(0,'boot',265,24840)
    entry(1,'metadata',24840 if overlap else 24841,33032)
    entry(39,'userdata',first,last)
    primary=bytearray(6*block);backup=bytearray(backup_blocks*block)
    primary[510:512]=b'\x55\xaa';primary[450]=0xee
    struct.pack_into('<II',primary,454,1,total-1)
    primary[2*block:2*block+len(table)]=table
    other=bytearray(table)
    if backup_changed:struct.pack_into('<Q',other,48,1)
    backup[:len(other)]=other
    def put_header(blob,offset,current,alternate,table_lba,array):
        header=bytearray(92)
        struct.pack_into('<8sIIIIQQQQ16sQIII',header,0,b'EFI PART',0x10000,92,0,0,
            current,alternate,265,last,b'D'*16,table_lba,count,128,binascii.crc32(array)&0xffffffff)
        struct.pack_into('<I',header,16,binascii.crc32(header)&0xffffffff)
        blob[offset:offset+92]=header
    put_header(primary,block,1,total-1,2,table)
    put_header(backup,(backup_blocks-1)*block,total-1,1,total-backup_blocks,other)
    lines=[b'/sys/devices/platform/soc/1d84000.ufshc/host0/target0:0:0/0:0:0:0/block/sda/sda40',
        b'8:40',str(first*8).encode(),str((last-first+1)*8).encode(),b'8:0',
        str(total*8).encode(),b'4096',b'8:0']
    geometry=b'\n'.join(lines)+b'\n'
    return b'G0\n'+geometry+primary+backup+b'G1\n'+geometry+b'END\n'


class CensusTests(unittest.TestCase):
    def test_matching_gpt_and_sysfs_retains_all_partition_metadata(self):
        value=census.decode(fixture())
        self.assertTrue(value['primary_and_backup_complete'])
        self.assertEqual(value['geometry']['capacity_bytes'],256_000_000_000)
        self.assertEqual([entry['name'] for entry in value['entries']],['boot','metadata','userdata'])
        self.assertEqual(value['userdata']['index'],40)
        self.assertEqual(value['gpt']['entry_count'],128)

    def test_crc_mismatch_disagreement_and_overlapping_extents_fail(self):
        good=fixture();start=good.index(b'EFI PART')
        damaged=bytearray(good);damaged[start+16]^=1
        for value in (bytes(damaged),fixture(backup_changed=True),fixture(overlap=True)):
            with self.subTest(kind=hash(value)),self.assertRaises(census.CensusError):census.decode(value)

    def test_complete_capture_may_not_claim_an_array_outside_its_bound(self):
        with self.assertRaisesRegex(census.CensusError,'exceeds'):
            census.decode(fixture(count=129))

    def test_explicit_tail9_contains_observed_44_entry_shape_without_changing_legacy_default(self):
        value=fixture(count=44,backup_blocks=9)
        self.assertEqual(census.decode(value,backup_blocks=9)['gpt']['entry_count'],44)
        with self.assertRaises(census.CensusError):census.decode(value)
        self.assertEqual(census.decode(fixture())['gpt']['entry_count'],128)
        with self.assertRaises(census.CensusError):census.decode(value,backup_blocks=8)

    def test_geometry_changes_wrong_lu_wrong_sector_size_and_trailing_bytes_fail(self):
        good=fixture()
        variants=[good.replace(b'/0:0:0:0/block/',b'/0:0:0:1/block/'),
            good.replace(b'\n4096\n',b'\n512\n'),good.replace(b'\n8:0\n',b'\n8:1\n',1),
            good[:-1],good+b'\n',good.replace(b'sda40',b'sda39',1)]
        for value in variants:
            with self.subTest(kind=hash(value)),self.assertRaises(census.CensusError):census.decode(value)

    def test_short_binary_dataset_is_unproved_with_private_raw_digest(self):
        raw=fixture()[:-100]
        value=census.project(raw,b'',(5,0,0,0,1,0,len(raw)),requested=True)
        self.assertEqual(value['status'],'NO_PROOF')
        self.assertEqual(value['stdout']['sha256'],census.sha(raw))
        self.assertFalse(value['grants_partition_write_authority'])
        self.assertEqual(census.project(b'',b'',None,requested=False)['reason'],
            'ORIGINAL_OBSERVATION_BUDGET_INSUFFICIENT')

    def test_malformed_device_numbers_remain_completed_negative_metadata(self):
        good=fixture();prefix=good[3:].split(b'\n',8)
        for index,bad in ((1,b'9'*5000+b':0'),(4,b'9'*5000+b':0'),
                (4,b'4096:0'),(4,b'8:1048576'),(7,b'1000:0'),(7,b'8:100000')):
            with self.subTest(index=index,length=len(bad)):
                lines=prefix[:8];lines[index]=bad
                raw=b'G0\n'+b'\n'.join(lines)+b'\n'+prefix[8]
                self.assertLessEqual(len(raw),census.MAX_OUTPUT)
                with self.assertRaises(census.CensusError):census.decode(raw)
                value=census.project(raw,b'',(5,0,0,0,1,0,len(raw)),requested=True)
                self.assertEqual(value['status'],'NO_PROOF')
                self.assertEqual(value['stdout']['sha256'],census.sha(raw))

    def test_fixed_transport_uses_existing_wire_encoding_and_decodes_exact_source(self):
        self.assertEqual(census.BODY,wire.command(census.COMMAND.encode(),cwd=census.CWD,timeout_ms=10000))
        self.assertLessEqual(len(census.COMMAND),767)
        self.assertEqual(gzip.decompress(base64.b64decode(census.ENCODED_SCRIPT,validate=True)),census.SCRIPT.encode())
        # Syntax validation executes no source command or attached-device read.
        subprocess.run(['/bin/sh','-n','-c',census.SCRIPT],check=True,capture_output=True,timeout=5)
        subprocess.run(['/bin/sh','-n','-c',census.COMMAND],check=True,capture_output=True,timeout=5)

    def test_failed_or_diagnostic_command_never_qualifies_metadata(self):
        for terminal,stderr in (((5,1,0,0,1,0,0),b''),((5,0,0,0,1,0,0),b'dd: read error\n')):
            value=census.project(fixture(),stderr,terminal,requested=True)
            self.assertEqual(value['status'],'NO_PROOF')

    def test_actual_arm64_busybox_decode_syntax_and_bounded_regular_file_reads(self):
        root=Path(__file__).resolve().parents[1]
        busybox=root/'workspace/private/inputs/s22plus_fyg8_p326/busybox/bin/busybox-aarch64-static-1.36.1'
        command=['/usr/bin/qemu-aarch64',str(busybox)]
        packed=subprocess.run(command+['base64','-d'],input=census.ENCODED_SCRIPT.encode(),
            capture_output=True,check=True,timeout=5).stdout
        plain=subprocess.run(command+['zcat'],input=packed,capture_output=True,check=True,timeout=5)
        self.assertEqual(plain.stdout,census.SCRIPT.encode());self.assertEqual(plain.stderr,b'')
        subprocess.run(command+['sh','-n','-c',census.SCRIPT],capture_output=True,check=True,timeout=5)
        with tempfile.TemporaryDirectory() as temporary:
            fifo=Path(temporary)/'ordinary-test-fifo'
            subprocess.run(command+['mknod','-m400',str(fifo),'p'],capture_output=True,check=True,timeout=5)
            self.assertTrue(stat.S_ISFIFO(fifo.stat().st_mode))
            self.assertEqual(stat.S_IMODE(fifo.stat().st_mode),0o400)
            before=fifo.stat().st_ino
            refused=subprocess.run(command+['mknod','-m400',str(fifo),'p'],capture_output=True,timeout=5)
            self.assertNotEqual(refused.returncode,0);self.assertEqual(fifo.stat().st_ino,before)
            subprocess.run(command+['rm',str(fifo)],capture_output=True,check=True,timeout=5)
            self.assertFalse(fifo.exists())
            path=Path(temporary)/'ordinary-fixture.bin'
            value=b''.join(bytes([i])*4096 for i in range(16));path.write_bytes(value)
            for start,count in ((0,6),(11,5)):
                result=subprocess.run(command+['dd',f'if={path}','bs=4096',f'skip={start}',
                    f'count={count}','status=none'],capture_output=True,check=True,timeout=5)
                self.assertEqual(result.stdout,value[start*4096:(start+count)*4096])
                self.assertEqual(result.stderr,b'')


if __name__=='__main__':unittest.main()
