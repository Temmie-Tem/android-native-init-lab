"""Construct private FYG8 reservation/32 GiB userdata bytes; no block devices.

This preserves existing duplicate GUIDs as opaque historical data. It does not
qualify GPT/PIT compatibility, an execution order, physical restoration or any
device write. Inputs and outputs are bounded regular files under private/.
"""
import argparse
import binascii
import os
from pathlib import Path
import re
import struct
import sys
import uuid

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_native_storage_census_v1 as gpt
from s22plus_native_records_v3 import (digest,pin,private_path,publish,read,read_bytes,
    require,sync_dir,verify)

SCHEMA='s22plus-native-gpt-layout-construction-h0-v1'
BLOCK=4096
NATIVE_BYTES=64*1024**3
ALIGN_BLOCKS=256
NAME='native_data'


def table_name(entry):
    try:name=entry[56:128].decode('utf-16-le').split('\0',1)[0]
    except UnicodeError as error:raise ValueError('GPT name is malformed') from error
    require(re.fullmatch(r'[A-Za-z0-9_.-]{1,36}',name) is not None,'GPT name differs')
    return name


def replace_table(blob,table,*,first_lba,header_lba):
    out=bytearray(blob);offset=(header_lba-first_lba)*BLOCK
    size=struct.unpack_from('<I',blob,offset+12)[0]
    table_lba=struct.unpack_from('<Q',blob,offset+72)[0]
    start=(table_lba-first_lba)*BLOCK
    require(0<=start<start+len(table)<=len(blob),'proposal table leaves original capture')
    out[start:start+len(table)]=table
    struct.pack_into('<I',out,offset+88,binascii.crc32(table)&0xffffffff)
    struct.pack_into('<I',out,offset+16,0)
    struct.pack_into('<I',out,offset+16,binascii.crc32(out[offset:offset+size])&0xffffffff)
    return bytes(out)


def construct(primary,backup,total_lbas,*,native_guid=None,native_bytes=NATIVE_BYTES,userdata_bytes=None):
    resizing=userdata_bytes is not None
    if resizing:
        require(type(userdata_bytes) is int and userdata_bytes==32*1024**3
            and native_guid is None and native_bytes==NATIVE_BYTES,
            'existing native resize requires exactly 32 GiB userdata and no new GUID')
    else:
        require(type(native_bytes) is int and native_bytes in (64*1024**3,128*1024**3),
            'native reservation must be 64 or 128 GiB')
    require(type(primary) is bytes and len(primary)==6*BLOCK
        and type(backup) is bytes and len(backup)==9*BLOCK,'original metadata ranges differ')
    require(type(total_lbas) is int and 16<total_lbas<2**48,'LU0 capacity differs')
    protective=[primary[446+i*16:462+i*16] for i in range(4)]
    selected=[row for row in protective if row[4]==0xee]
    require(primary[510:512]==b'\x55\xaa' and len(selected)==1
        and all(row[4] in (0,0xee) for row in protective)
        and struct.unpack_from('<II',selected[0],8)==(1,min(total_lbas-1,0xffffffff)),
        'original protective MBR differs')
    h1,table=gpt.header(primary,capture_first_lba=0,my_lba=1,
        alternate_lba=total_lbas-1,total_lbas=total_lbas,backup_blocks=9)
    h2,other=gpt.header(backup,capture_first_lba=total_lbas-9,my_lba=total_lbas-1,
        alternate_lba=1,total_lbas=total_lbas,backup_blocks=9)
    require(h1==h2 and table==other,'original GPT copies disagree')
    require(h1['entry_count']==44 and h1['entry_size']==128,'FYG8 entry-array shape differs')
    entries=[table[i*128:(i+1)*128] for i in range(44)]
    used=41 if resizing else 40
    require(all(row[:16]!=b'\0'*16 and row[16:32]!=b'\0'*16 for row in entries[:used])
        and all(not any(row) for row in entries[used:]),'FYG8 used/unused entry shape differs')
    names=[table_name(row) for row in entries[:used]]
    require(len({name.lower() for name in names})==used and names[39].lower()=='userdata'
        and (names[40]==NAME if resizing else NAME not in {name.lower() for name in names}),
        'userdata or proposed name is ambiguous')
    extents=[struct.unpack_from('<QQ',row,32) for row in entries[:used]]
    require(all(h1['first_usable_lba']<=a<=b<=h1['last_usable_lba'] for a,b in extents),
        'original extent is outside usable storage')
    ordered=sorted(extents)
    require(all(a[1]<b[0] for a,b in zip(ordered,ordered[1:]))
        and (extents[39:]==ordered[-2:] if resizing else extents[39]==ordered[-1]),
        'original extents overlap or userdata/native are not last')
    require(struct.unpack_from('<Q',entries[39],48)[0]==0,'userdata attributes differ')
    user_first,user_last=extents[39]
    if resizing:
        old_native_first,old_native_last=extents[40]
        require(old_native_first==user_last+1 and old_native_first%ALIGN_BLOCKS==0
            and (old_native_last+1)%ALIGN_BLOCKS==0
            and (old_native_last-old_native_first+1)*BLOCK==128*1024**3
            and entries[40][:16]==entries[39][:16]
            and struct.unpack_from('<Q',entries[40],48)[0]==0,
            'existing native partition is not the adjacent 128 GiB reservation')
        require(entries[40][16:32] not in {row[16:32] for row in entries[:40]}
            and entries[40][16:32].hex()!=h1['disk_guid'],'existing native GUID aliases another identity')
        end_exclusive=old_native_last+1
        native_first=user_first+userdata_bytes//BLOCK
        require(native_first<old_native_first,'32 GiB proposal does not shrink userdata')
        native_bytes=(end_exclusive-native_first)*BLOCK
        fresh=bytearray(entries[40])
        struct.pack_into('<Q',fresh,32,native_first)
    else:
        require(type(native_guid) is bytes and len(native_guid)==16 and any(native_guid)
            and native_guid.hex()!=h1['disk_guid']
            and native_guid not in {row[16:32] for row in entries[:40]},'new GUID is zero or reused')
        end_exclusive=(user_last+1)//ALIGN_BLOCKS*ALIGN_BLOCKS
        native_first=end_exclusive-native_bytes//BLOCK
        fresh=bytearray(128)
        struct.pack_into('<16s16sQQQ',fresh,0,entries[39][:16],native_guid,
            native_first,end_exclusive-1,0)
        label=NAME.encode('utf-16-le');fresh[56:56+len(label)]=label
    require(user_first<native_first<end_exclusive and user_first%ALIGN_BLOCKS==0,
        'native reservation leaves no aligned userdata')
    changed=bytearray(table)
    struct.pack_into('<Q',changed,39*128+40,native_first-1)
    changed[40*128:41*128]=fresh
    changed=bytes(changed)
    require(changed[:39*128]==table[:39*128] and changed[41*128:]==table[41*128:],
        'non-userdata entries changed')
    old_user=entries[39];new_user=changed[39*128:40*128]
    require(new_user[:40]==old_user[:40] and new_user[48:]==old_user[48:],
        'userdata fields other than ending LBA changed')
    regions=[]
    for name,original,start,header in [('primary-six',primary,0,1),
            ('backup-nine',backup,total_lbas-9,total_lbas-1)]:
        proposed=replace_table(original,changed,first_lba=start,header_lba=header)
        header_check,table_check=gpt.header(proposed,capture_first_lba=start,my_lba=header,
            alternate_lba=total_lbas-1 if start==0 else 1,total_lbas=total_lbas,backup_blocks=9)
        require(table_check==changed and {k:v for k,v in header_check.items() if k!='entries_sha256'}
            =={k:v for k,v in h1.items() if k!='entries_sha256'},'proposal changes GPT header semantics')
        # Only table bytes and the two CRC fields may differ, including padding.
        inverse=replace_table(proposed,table,first_lba=start,header_lba=header)
        require(inverse==original,'inverse table/CRC transform does not restore exact originals')
        regions.append(dict(name=name,first_lba=start,original=original,proposed=proposed))
    layout=dict(userdata_first_lba=user_first,userdata_new_last_lba=native_first-1,
        userdata_new_size_bytes=(native_first-user_first)*BLOCK,native_entry_index=41,
        native_name=NAME,native_first_lba=native_first,native_last_lba=end_exclusive-1,
        native_size_bytes=native_bytes,
        unused_tail_bytes=((h1['last_usable_lba']+1 if resizing else user_last+1)-end_exclusive)*BLOCK,
        non_userdata_entries_preserved=39,original_duplicate_guids_preserved=True)
    if resizing:
        require(bytes(fresh[:32])==entries[40][:32] and bytes(fresh[40:])==entries[40][40:],
            'native fields other than starting LBA changed')
        layout.update(construction='resize-existing-native-32g-v1',
            userdata_original_size_bytes=(user_last-user_first+1)*BLOCK,
            native_original_first_lba=old_native_first,native_original_size_bytes=128*1024**3,
            predecessor_native_identity_preserved=True)
    return regions,layout


def regular_output(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
    try:
        with os.fdopen(os.dup(fd),'wb') as stream:
            require(stream.write(data)==len(data),'short H0 output write');stream.flush();os.fsync(stream.fileno())
    finally:os.close(fd)
    require(read_bytes(path)==data,'H0 output readback differs')
    return pin(path)


def prepare(layout_path,output,*,native_gib=64):
    require(type(native_gib) is int and native_gib in (64,128),'native GiB differs')
    layout_path=private_path(ROOT,layout_path);source=read(layout_path)
    require(source['schema']=='s22plus-native-64g-layout-h0-v1','layout source schema differs')
    def original(key):
        receipt=source[key];path=private_path(ROOT,Path(receipt['path']))
        verify(receipt);return read_bytes(path)
    primary,backup=original('private_original_primary'),original('private_original_backup')
    guid=uuid.uuid4().bytes_le
    # Validate the retained 64 GiB source proposal unchanged, then derive the
    # requested successor from the same originals without editing that record.
    regions,layout=construct(primary,backup,source['geometry']['total_lbas'],native_guid=guid)
    for key in ('userdata_first_lba','userdata_new_last_lba','userdata_new_size_bytes','native_entry_index',
                'native_first_lba','native_last_lba','native_size_bytes','unused_tail_bytes'):
        require(layout[key]==source['proposal'][key],'constructed layout differs from the original proposal')
    if native_gib!=64:
        regions,layout=construct(primary,backup,source['geometry']['total_lbas'],
            native_guid=guid,native_bytes=native_gib*1024**3)
    return publish_proposal(output,regions,layout,source_layout=pin(layout_path))


def prepare_resize(close_path,output):
    """H0 successor from the completed current layout, never pre-G2 originals."""
    close_path=private_path(ROOT,close_path);closed=read(close_path)
    require(closed['schema']=='s22plus-native-session-v3-task-close-v1'
        and closed['terminal_state']=='ANDROID_CLOSED_HEALTHY' and closed['f1_owner_absent'] is True,
        'resize source is not a closed healthy Android task')
    terminal=read(verify(closed['current_android_terminal']))
    require(terminal['terminal_state']=='ANDROID_CLOSED_HEALTHY'
        and terminal['gpt']==closed['gpt']
        and terminal['gpt']['status']=='RESERVED_ANDROID_REBOOT_VERIFIED',
        'resize source lacks rooted Android GPT/reboot qualification')
    operation=read(verify(terminal['operation_record']))
    basis=operation['N']['gpt'];source=read(verify(basis['proposal']))
    require(source['regions']==basis['regions'] and source['layout']==basis['layout']
        and source['layout']['native_size_bytes']==128*1024**3
        and source['layout']['userdata_new_size_bytes']==102497255424,
        'resize source is not the completed 128 GiB proposal')
    original=[read_bytes(verify(row['proposed'])) for row in source['regions']]
    result=read(verify(terminal['terminal_result']))
    metadata=result['gpt_android']['metadata']
    require(metadata['layout']=='proposed' and metadata['status']=='PASS_EXACT_GPT'
        and metadata['full_metadata']==dict(size=61440,sha256=digest(b''.join(original))),
        'completed Android GPT differs from resize original bytes')
    regions,layout=construct(*original,62305280,userdata_bytes=32*1024**3)
    require(layout['userdata_first_lba']==3726848 and layout['native_last_lba']==62305023,
        'resize source geometry differs from FYG8')
    return publish_proposal(output,regions,layout,source_close=pin(close_path),
        source_proposal=basis['proposal'],source_terminal=closed['current_android_terminal'])


def publish_proposal(output,regions,layout,**source):
    output=private_path(ROOT,output,exists=False);require(not output.exists(),'H0 output already exists')
    output.mkdir(mode=0o700)
    receipts=[];blocks=[]
    for region in regions:
        name=region['name'];original=region['original'];proposed=region['proposed']
        receipts.append(dict(name=name,first_lba=region['first_lba'],
            original=regular_output(output/(name+'-original.bin'),original),
            proposed=regular_output(output/(name+'-proposed.bin'),proposed)))
        for offset in range(0,len(original),BLOCK):
            a,b=original[offset:offset+BLOCK],proposed[offset:offset+BLOCK]
            if a!=b:blocks.append(dict(lba=region['first_lba']+offset//BLOCK,
                original_sha256=digest(a),proposed_sha256=digest(b),size=BLOCK))
    sync_dir(output)
    return publish(output/'result.json',dict(schema=SCHEMA,status='PASS_H0_EXACT_LAYOUT_CONSTRUCTION',
        **source,producer=pin(Path(__file__)),layout=layout,regions=receipts,
        changed_blocks=blocks,execution_order_qualified=False,block_atomicity_assumed=False,
        physical_restoration_qualified=False,gpt_pit_compatibility_qualified=False,
        partition_write_authority=False,device_effects=0))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('layout',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--native-gib',type=int,choices=(64,128),default=64)
    parser.add_argument('--resize-userdata-32g',action='store_true',
        help='interpret layout input as the closed 128 GiB task and preserve existing native identity')
    args=parser.parse_args()
    print(prepare_resize(args.layout,args.output) if args.resize_userdata_32g
        else prepare(args.layout,args.output,native_gib=args.native_gib))
