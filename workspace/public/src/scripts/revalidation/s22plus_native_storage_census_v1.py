"""Fixed read-only LU0 metadata census; no partition writer or formatter.

The firmware PIT names a six-block PGPT0 and a five-block secondary GPT.
Those bounded reads are admitted only for a 4096-byte logical block device
whose live userdata ancestry identifies the exact FYG8 UFS controller/LU0.
All returned metadata stays private. A census is not partition-write authority.
"""
import base64
import binascii
import gzip
import hashlib
import re
import struct
import s22plus_root_console_v1 as wire

SCHEMA = 's22plus-native-storage-census-v1'
BLOCK_SIZE = 4096
PRIMARY_BLOCKS = 6
BACKUP_BLOCKS = 5
MAX_OUTPUT = 65536
ADMISSION_SECONDS = 12
SETTLE_SECONDS = 0

# This is one authenticated EXEC with no caller command/path substitution.
# dd has only an input operand: the metadata-sized reads never write a device.
SCRIPT = (
    'set -eu;'
    'B=/bin/busybox;'
    'u=;'
    'for x in /sys/class/block/sd*[0-9];'
    'do [ -f "$x/partition" ]||continue;'
    '[ "$($B sed -n \'s/^PARTNAME=//p\' "$x/uevent")" = userdata ]||continue;'
    '[ -z "$u" ]||exit 1;'
    'u=$x;'
    'done;'
    '[ -n "$u" ];'
    'r=$($B readlink -f "$u");'
    'p=${r%/*};'
    'case "$p" in /sys/devices/platform/soc*/1d84000.ufshc/host*/target*/*:0:0:0/block/sd?) ;'
    ';'
    '*)exit 1;'
    ';'
    'esac;'
    'IFS=: read a b <"$p/dev";'
    'd=/dev/.s22-gpt-$$;'
    '$B mknod -m400 "$d" b "$a" "$b";'
    'trap \'$B rm -f "$d"\' EXIT;'
    '[ "$($B cat "$p/queue/logical_block_size")" = 4096 ];'
    's=$($B cat "$p/size");'
    '[ $((s%8)) = 0 ];'
    '[ "$s" -gt 128 ];'
    'g(){ printf \'%s\\n\' "$r";'
    'for f in "$u"/dev "$u"/start "$u"/size "$p"/dev "$p"/size "$p"/queue/logical_block_size;'
    'do $B cat "$f";'
    'done;'
    '$B stat -c %t:%T "$d";'
    '};'
    "printf 'G0\\n';"
    'g;'
    '$B dd if="$d" bs=4096 count=6 status=none;'
    '$B dd if="$d" bs=4096 skip=$((s/8-5)) count=5 status=none;'
    "printf 'G1\\n';"
    'g;'
    '$B rm "$d";'
    'trap - EXIT;'
    "printf 'END\\n'"
)
# Literal gzip bytes keep the existing 767-byte command limit. Decompression
# is only transport encoding of this reviewed fixed script, never user input.
ENCODED_SCRIPT = (
    'H4sIAAAAAAAC/3VS72vbMBD9Vw7hkDjgyiltSaOJ0bJs9MPK2PJhkHVFseVUJJE9n1TSX//7TnJq1rFhsMTdu7v33gm1g0x7cSn5yli+8viwqvfCS1HVLezBWOD4gLzYKkS+2tbFhmM5XubZ+Y0oa1hCVgFL9rxRrTPO1JbBzfNzUVtnrNdiSclRcgmoS8gsDJH//HLxdXF98XkuOW+Gsdbre20dSxlI8KjbUjn1V5fskZA+9tZ742BCFJM9MbAxaw9Z0co4rtWq3Bq76dh5lopGJk/tgI9fRKFQU7BhvbhS35tCI2+2ypHsHce6GPNJOT3J8/zIV3hX8Lsa3Zg71a41neNZHr7ekPcpCDFOD9SERlWIq4/f5CwyAQUreEcjwyQmShlOfoTHx9m6cVmSCKK829iaPNrRTGJXMiphiWL0WzHhWtXAMAjbdZJKNoT596tFb3ChXBDFf3ntNd/Wa1Oo7W3kd4vmUXfunuTnZ+QSyjc1XZ5aJaMRDqZpSsicYKE3MsjWJOp4SoH1KH2CpjXWVTAc4A8b9tey+FaqYGfwOojrLkh2ucOVRkTTD9nmz9D/OIcH1tOsWLft8JgcRbICBm42WEQzxIt4pfUpJ1piHXBlCaaSnZkoo/ai9tbJs9jCo7SHjv9A4sbQmyFD+DQ7JUu6ytM3lf3MST+TFhQJxY1l3Y5eYfPrD4T7DVhsu95zAwAA'
)
if not re.fullmatch(r'[A-Za-z0-9+/]+={0,2}',ENCODED_SCRIPT):
    raise ValueError('fixed census encoding is not a shell-safe literal')
if gzip.decompress(base64.b64decode(ENCODED_SCRIPT,validate=True))!=SCRIPT.encode():
    raise ValueError('fixed census encoding differs from its readable script')
COMMAND = 'B=/bin/busybox;echo '+ENCODED_SCRIPT+'|$B base64 -d|$B zcat|$B sh'
CWD = b'/s22-root-work'
BODY = wire.command(COMMAND.encode(),cwd=CWD,timeout_ms=10000)
if len(BODY)+32 > 1055:
    raise ValueError('fixed census exceeds the existing authenticated EXEC frame')


class CensusError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CensusError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def device_number(value, *, hexadecimal=False):
    # Exact target include/linux/{types,kdev_t}.h: u32 dev_t, 20 minor bits.
    # Bound the spelling before int(), including Python's decimal digit limit.
    pattern=r'[0-9a-f]{1,3}:[0-9a-f]{1,5}' if hexadecimal else r'[0-9]{1,4}:[0-9]{1,7}'
    require(re.fullmatch(pattern,value), 'device number spelling is not bounded')
    major,minor=(int(part,16 if hexadecimal else 10) for part in value.split(':'))
    require(0<=major<2**12 and 0<=minor<2**20, 'device number exceeds target dev_t')
    return major,minor


def geometry(lines):
    require(len(lines)==8, 'geometry field count differs')
    try:
        values=[line.decode('ascii') for line in lines]
    except UnicodeError as error:
        raise CensusError('geometry is not ASCII') from error
    match=re.fullmatch(
        r'/sys/devices/platform/(?:soc|soc@0)/1d84000\.ufshc/host([0-9]+)/'
        r'target\1:0:0/\1:0:0:0/block/(sd[a-z])/(\2[1-9][0-9]*)',values[0])
    require(match is not None, 'userdata is not on the exact FYG8 UFS LU0')
    device_number(values[1])
    expected_device=device_number(values[4])
    held_device=device_number(values[7],hexadecimal=True)
    require(all(re.fullmatch(r'[0-9]{1,16}',values[index]) for index in (2,3,5,6)),
        'geometry length is not bounded decimal')
    start,size,sectors,block_size=(int(values[index]) for index in (2,3,5,6))
    bytes_total=sectors*512
    require(block_size==BLOCK_SIZE and 128<sectors<2**48 and sectors%8==0
        and 0<start<start+size<=sectors
        and start%8==size%8==0, 'geometry capacity or alignment differs')
    require(held_device==expected_device,
        'held block path has a different device number')
    return dict(ancestry=values[0],parent=match[2],userdata=match[3],
        userdata_device=values[1],parent_device=values[4],logical_block_size=block_size,
        capacity_bytes=bytes_total,total_lbas=sectors//8,
        userdata_first_lba=start//8,userdata_last_lba=(start+size)//8-1)


def header(blob, *, capture_first_lba, my_lba, alternate_lba, total_lbas):
    offset=(my_lba-capture_first_lba)*BLOCK_SIZE
    require(0<=offset and offset+BLOCK_SIZE<=len(blob), 'GPT header is outside its fixed capture')
    block=blob[offset:offset+BLOCK_SIZE]
    fields=struct.unpack_from('<8sIIIIQQQQ16sQIII',block)
    signature,revision,size,crc,reserved,current,alternate,first,last,guid,table_lba,count,entry_size,table_crc=fields
    require(signature==b'EFI PART' and revision==0x10000 and 92<=size<=BLOCK_SIZE
        and reserved==0 and current==my_lba and alternate==alternate_lba,
        'GPT header identity differs')
    checked=bytearray(block[:size]);checked[16:20]=b'\0'*4
    require(binascii.crc32(checked)&0xffffffff==crc, 'GPT header CRC differs')
    require(guid!=b'\0'*16 and PRIMARY_BLOCKS<=first<=last<total_lbas-BACKUP_BLOCKS,
        'GPT usable range differs')
    require(0<count<=128 and entry_size>=128 and entry_size%128==0
        and count*entry_size<=4*BLOCK_SIZE, 'GPT entry array exceeds the fixed metadata read')
    table_offset=(table_lba-capture_first_lba)*BLOCK_SIZE
    table_end=table_offset+count*entry_size
    require(0<=table_offset<table_end<=len(blob)
        and (table_end<=offset or offset+BLOCK_SIZE<=table_offset),
        'GPT entry array is outside its capture or overlaps its header')
    if current==1:
        require(table_lba>=2 and table_lba+(count*entry_size+BLOCK_SIZE-1)//BLOCK_SIZE<=first,
            'primary GPT array overlaps usable storage')
    else:
        require(table_lba>last and table_lba+(count*entry_size+BLOCK_SIZE-1)//BLOCK_SIZE<=current,
            'backup GPT array overlaps usable storage')
    table=blob[table_offset:table_end]
    require(binascii.crc32(table)&0xffffffff==table_crc, 'GPT entry-array CRC differs')
    return dict(first_usable_lba=first,last_usable_lba=last,disk_guid=guid.hex(),
        entry_count=count,entry_size=entry_size,entries_sha256=sha(table)),table


def decode(stdout):
    require(type(stdout) is bytes and len(stdout)<=MAX_OUTPUT and stdout.startswith(b'G0\n'),
        'census prefix or output bound differs')
    prefix=stdout[3:].split(b'\n',8)
    require(len(prefix)==9, 'initial geometry is incomplete')
    before=geometry(prefix[:8]);remaining=prefix[8]
    primary_size=PRIMARY_BLOCKS*BLOCK_SIZE;backup_size=BACKUP_BLOCKS*BLOCK_SIZE
    require(len(remaining)>=primary_size+backup_size+3, 'GPT capture is short')
    primary=remaining[:primary_size];backup=remaining[primary_size:primary_size+backup_size]
    tail=remaining[primary_size+backup_size:]
    require(tail.startswith(b'G1\n') and tail.endswith(b'END\n'), 'final geometry bracket is absent')
    after=geometry(tail[3:-4].splitlines())
    require(before==after, 'LU0 geometry changed during the census')
    require(primary[510:512]==b'\x55\xaa', 'protective MBR signature differs')
    mbr=[primary[446+i*16:462+i*16] for i in range(4)]
    protective=[row for row in mbr if row[4]==0xee]
    require(len(protective)==1 and all(row[4] in (0,0xee) for row in mbr),
        'protective MBR is missing or hybrid')
    mbr_start,mbr_count=struct.unpack_from('<II',protective[0],8)
    require(mbr_start==1 and mbr_count==min(before['total_lbas']-1,0xffffffff),
        'protective MBR capacity differs')
    total=before['total_lbas']
    h1,t1=header(primary,capture_first_lba=0,my_lba=1,alternate_lba=total-1,total_lbas=total)
    h2,t2=header(backup,capture_first_lba=total-BACKUP_BLOCKS,my_lba=total-1,alternate_lba=1,total_lbas=total)
    require(h1==h2 and t1==t2, 'primary and backup GPT disagree')
    entries=[];guids=set();names=set()
    for index in range(h1['entry_count']):
        entry=t1[index*h1['entry_size']:(index+1)*h1['entry_size']]
        if entry[:16]==b'\0'*16:
            require(not any(entry), 'unused GPT entry contains unexpected bytes')
            continue
        type_guid,unique_guid,first,last,attributes=struct.unpack_from('<16s16sQQQ',entry)
        try:
            name=entry[56:128].decode('utf-16-le').split('\0',1)[0]
        except UnicodeError as error:
            raise CensusError('GPT partition name is malformed') from error
        require(name and re.fullmatch(r'[A-Za-z0-9_.-]{1,36}',name)
            and name.lower() not in names and unique_guid!=b'\0'*16 and unique_guid not in guids,
            'GPT partition name or GUID is missing or ambiguous')
        require(h1['first_usable_lba']<=first<=last<=h1['last_usable_lba'],
            'GPT partition is outside usable storage')
        names.add(name.lower());guids.add(unique_guid)
        entries.append(dict(index=index+1,name=name,type_guid=type_guid.hex(),
            unique_guid=unique_guid.hex(),first_lba=first,last_lba=last,attributes=attributes,
            size_bytes=(last-first+1)*BLOCK_SIZE,entry_sha256=sha(entry)))
    ordered=sorted(entries,key=lambda entry:entry['first_lba'])
    require(all(a['last_lba']<b['first_lba'] for a,b in zip(ordered,ordered[1:])),
        'GPT partition extents overlap')
    users=[entry for entry in entries if entry['name'].lower()=='userdata']
    require(len(users)==1 and users[0]['first_lba']==before['userdata_first_lba']
        and users[0]['last_lba']==before['userdata_last_lba']
        and before['userdata']==before['parent']+str(users[0]['index']),
        'live userdata GPT and sysfs extents disagree')
    return dict(geometry=before,gpt=h1,entries=entries,userdata=users[0],
        primary_sha256=sha(primary),backup_sha256=sha(backup),
        primary_and_backup_complete=True,crc_and_geometry_verified=True,ram_block_alias_removed=True)


def project(stdout, stderr, terminal, *, requested):
    result=dict(schema=SCHEMA,status='NO_PROOF',requested=requested,
        stdout=dict(size=len(stdout),sha256=sha(stdout)),stderr=dict(size=len(stderr),sha256=sha(stderr)),
        grants_partition_write_authority=False)
    if not requested:
        return dict(result,reason='ORIGINAL_OBSERVATION_BUDGET_INSUFFICIENT')
    if terminal is None or terminal[:4]!=(5,0,0,0) or terminal[5]!=0 or stderr:
        return dict(result,reason='CENSUS_COMMAND_DID_NOT_COMPLETE_SUCCESSFULLY')
    try:
        value=decode(stdout)
    except CensusError as error:
        return dict(result,reason=str(error))
    return dict(result,status='PASS_METADATA_ONLY',**value)
