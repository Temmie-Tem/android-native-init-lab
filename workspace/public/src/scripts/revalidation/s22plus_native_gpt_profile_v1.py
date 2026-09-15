"""Fixed sealed GPT command/proof profiles; no endpoint or grant selection."""
import re
import struct

import s22plus_root_console_v1 as wire
from s22plus_native_records_v3 import digest, read, read_bytes, require, verify

SCHEMA='s22plus-native-gpt-proof-v1'
PROFILE='thermal-v3-reconnect-ufs-drain-gpt-v1'
BYTES=61440
OLD_USER=(62305271-3726848)*8
NEW_USER=(28750592-3726848)*8
NATIVE_SECTORS=128*1024**3//512
LBAS=(62305272,62305279,3,1)
SELECTIONS={'gpt-original':('observe',0,'original'),
    'gpt-proposed':('observe',0,'proposed'),'gpt-apply':('apply',1,'proposed'),
    'gpt-restore':('restore',2,'original'),'gpt-after-reset':('after-reset',0,'proposed'),
    'gpt-after-original-reset':('after-original-reset',0,'original')}
AFTER_RESET=('gpt-after-reset','gpt-after-original-reset')
RESULT=re.compile(rb'GPT1_RESULT mode=([0-2]) status=([0-9]+) io_errno=([0-9]+) close_errno=([0-9]+) '
    rb'writes=([0-9]+) completed=([0-9]+) skipped=([0-9]+) last_read_kind=([0-2]) '
    rb'userdata_sectors=([0-9]+) native_sectors=([0-9]+) filesystem_errno=([0-9]+)')
EVENT=re.compile(rb'GPT1_STEP event=([1-3]) ordinal=([0-3]) lba=([0-9]{1,8})')


def vectors(binding):
    require(type(binding) is dict and set(binding)=={'proposal','regions','layout'},'GPT image binding differs')
    value=read(verify(binding['proposal']))
    require(value['schema']=='s22plus-native-gpt-layout-construction-h0-v1'
        and value['status']=='PASS_H0_EXACT_LAYOUT_CONSTRUCTION'
        and value['regions']==binding['regions'] and value['layout']==binding['layout']
        and value['layout']['native_size_bytes']==128*1024**3
        and value['layout']['userdata_new_size_bytes']==NEW_USER*512
        and value['layout']['native_first_lba']==28750592
        and value['layout']['native_last_lba']==62305023
        and [row['lba'] for row in value['changed_blocks']]==[1,3,62305272,62305279],
        'GPT image does not join its sealed 128 GiB proposal')
    require([(row['name'],row['first_lba']) for row in binding['regions']]
        ==[('primary-six',0),('backup-nine',62305271)],'GPT bound regions differ')
    result={}
    for kind in ('original','proposed'):
        parts=[read_bytes(verify(row[kind])) for row in binding['regions']]
        require([len(part) for part in parts]==[24576,36864],'GPT bound byte lengths differ')
        result[kind]=b''.join(parts)
    return result


def f2fs_geometry(data, *, userdata_sectors=NEW_USER):
    require(userdata_sectors in (OLD_USER,NEW_USER),'F2FS selected partition size differs')
    require(len(data)==216 and data[:108]==data[108:],'F2FS geometry copies differ')
    first=data[:108]
    require(struct.unpack_from('<I',first)[0]==0xf2f52010,'F2FS magic differs')
    sector,per_block,block,per_segment=struct.unpack_from('<4I',first,8)
    count=struct.unpack_from('<Q',first,36)[0]
    segments=struct.unpack_from('<I',first,48)[0]
    segment0=struct.unpack_from('<I',first,72)[0]
    require(sector in (9,12) and per_block==12-sector and block==12 and per_segment==9
        and count==(userdata_sectors*512-16384)//4096
        and 0<segment0+segments*512<=count,'F2FS geometry is not the new userdata size')
    return dict(status='PASS_GEOMETRY_ONLY',block_size=4096,block_count=count,
        requested_bytes=count*4096,segment_count=segments,segment0_block=segment0,
        copies_agree=True,raw_geometry=dict(size=len(data),sha256=digest(data)),
        complete_filesystem_health_proved=False)


def decode(stdout, selection, sealed):
    require(selection in SELECTIONS and type(stdout) is bytes and len(stdout)<=65536,'GPT output bound differs')
    _,mode,kind=SELECTIONS[selection]
    prefix,separator,body=stdout.partition(b'GPT1_DATA bytes=61440\n')
    require(separator and len(prefix)<=4096 and prefix.endswith(b'\n'),'GPT result framing differs')
    lines=prefix.splitlines();match=RESULT.fullmatch(lines[-1])
    require(match is not None,'GPT result record differs')
    values=tuple(map(int,match.groups()))
    actual,status,error,close,writes,completed,skipped,final,user,native,fs_error=values
    require((actual,status,error,close,fs_error)==(mode,0,0,0,0)
        and final==({'original':1,'proposed':2}[kind]) and writes==completed,
        'GPT command did not report a complete successful final read')
    geometry=(NEW_USER,NATIVE_SECTORS) if selection in ('gpt-proposed','gpt-after-reset') else (OLD_USER,0)
    require((user,native)==geometry or selection=='gpt-restore'
        and (user,native)==(NEW_USER,NATIVE_SECTORS),'kernel partition geometry differs')
    require(body[:BYTES]==sealed[kind],'complete GPT bytes differ from the sealed target')
    tail=body[BYTES:];filesystem=None
    if selection in AFTER_RESET:
        marker=b'GPT1_F2FS bytes=216\n'
        require(tail.startswith(marker) and len(tail)==len(marker)+216+9,'F2FS prefix framing differs')
        filesystem=f2fs_geometry(tail[len(marker):-9],userdata_sectors=user);tail=tail[-9:]
    require(tail==b'GPT1_END\n','GPT trailing bytes differ')
    events=[]
    for line in lines[:-1]:
        match=EVENT.fullmatch(line);require(match is not None,'GPT event record differs')
        events.append(tuple(map(int,match.groups())))
    if mode==0:
        require(not events and (writes,completed,skipped)==(0,0,0),'read-only GPT command reported writes')
    else:
        require(writes+skipped==4 and (mode!=1 or (writes,skipped)==(4,0)),
            'GPT block completion count differs')
        position=0;order=[];actual_writes=0;actual_skips=0
        for ordinal in range(4):
            require(position<len(events),'GPT event sequence is incomplete')
            event,number,lba=events[position];position+=1;order.append(lba)
            require(number==ordinal,'GPT event ordinal differs')
            if event==3:actual_skips+=1
            else:
                require(event==1 and position<len(events) and events[position]==(2,ordinal,lba),
                    'GPT write intent/completion pair differs')
                position+=1;actual_writes+=1
        require(position==len(events) and tuple(order) in (LBAS,LBAS[2:]+LBAS[:2])
            and (actual_writes,actual_skips)==(writes,skipped),'GPT event order or counts differ')
        require(mode!=1 or tuple(order)==LBAS,'GPT apply copy order differs')
    return dict(status='PASS_EXACT_GPT',selection=selection,mode=mode,final_pair=kind,
        full_metadata=dict(size=BYTES,sha256=digest(body[:BYTES])),
        userdata_sectors=user,native_sectors=native,writes=writes,skipped=skipped,
        filesystem=filesystem,original_duplicate_guids_preserved=True)


class Profile:
    ADMISSION_SECONDS=17
    SETTLE_SECONDS=0
    RESULT_KEY='gpt'

    def __init__(self,image,selection):
        require(image['profile']==PROFILE and selection in SELECTIONS
            and re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'GPT command image/selection differs')
        self.selection=selection;self.sealed=vectors(image['gpt'])
        command,mode,_=SELECTIONS[selection]
        self.MUTATES=mode in (1,2)
        self.BODY=wire.command(('exec /s22-display --gpt-'+command+' '+image['run_id_hex']).encode(),
            cwd=b'/s22-root-work',timeout_ms=15000)

    def project(self,stdout,stderr,terminal,*,requested):
        result=dict(schema=SCHEMA,status='NO_PROOF',selection=self.selection,requested=requested,
            stdout=dict(size=len(stdout),sha256=digest(stdout)),
            stderr=dict(size=len(stderr),sha256=digest(stderr)),grants_device_authority=False)
        if not requested:return dict(result,reason='ORIGINAL_OBSERVATION_BUDGET_INSUFFICIENT')
        if (terminal is None or terminal[:4]!=(5,0,0,0) or terminal[4]!=len(stdout)
                or terminal[5]!=0 or stderr):
            return dict(result,reason='GPT_COMMAND_DID_NOT_COMPLETE_SUCCESSFULLY')
        try:value=decode(stdout,self.selection,self.sealed)
        except ValueError as error:return dict(result,reason=str(error))
        return dict(result,**value)
