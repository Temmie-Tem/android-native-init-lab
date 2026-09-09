"""P376 boot HUD with the reviewed root console; fresh identity."""
from s22plus_fyg8_p376_namespace import load_template
load_template(globals(),lambda source:source.replace(b"value.get('qualified_command_count')!=5",b"value.get('qualified_command_count')!=len(QUALIFICATION_COMMANDS)"))

import re
HUD_COMMAND=(b'n=0; while [ "$n" -lt 10 ]; do '
    b'[ "$(/bin/busybox grep -c \'^HUD_FRAME \' hud.log)" -ge 3 ] && break; '
    b'n=$((n+1)); /bin/busybox sleep 1; done; /bin/busybox cat hud.log')
QUALIFICATION_COMMANDS=QUALIFICATION_COMMANDS+(QualificationStep(6,'hud-updates-with-console',HUD_COMMAND,b''),)
TOTAL_COMMANDS=len(QUALIFICATION_COMMANDS)
PROOF_SCOPE='root-console-and-immutable-HUD-flip-events-pixels-unproved'
HUD_SCHEMA='s22plus-fyg8-p376-hud-log-proof-v1'
_FRAME=re.compile(rb'HUD_FRAME run=([0-9a-f]{32}) seq=([0-9]+) uptime_ms=([0-9]+) state=([0-2]) event=matched visible=UNPROVED')

def hud_log_proof(raw):
    result=dict(schema=HUD_SCHEMA,proved=False,log=identity(raw),frame_count=0,
        first_sequence=0,last_sequence=0,first_uptime_ms=0,last_uptime_ms=0,busy_frames=0)
    if len(raw)>131072 or not raw.endswith(b'\n'):return result
    starts=[];frames=[]
    for line in raw.splitlines():
        if line.startswith(b'HUD_START '):
            if not re.fullmatch(rb'HUD_START [1-9][0-9]*',line):return result
            starts.append(int(line.split()[1]))
        elif line.startswith(b'HUD_FRAME '):
            match=_FRAME.fullmatch(line)
            if match is None or match[1].decode()!=RUN_ID_HEX:return result
            seq,up,state=map(int,match.groups()[1:])
            if not seq or seq>601 or not up or (frames and (seq<=frames[-1][0] or up<=frames[-1][1])):return result
            frames.append((seq,up,state))
        elif line.startswith(b'HUD_') or line.startswith(b'DISPLAY_FAIL '):return result
    if len(starts)!=1 or starts[0]<=1 or len(frames)<3:return result
    result.update(frame_count=len(frames),first_sequence=frames[0][0],last_sequence=frames[-1][0],
        first_uptime_ms=frames[0][1],last_uptime_ms=frames[-1][1],busy_frames=sum(state==1 for _,_,state in frames))
    result['proved']=frames[-1][1]-frames[0][1]>=2000 and result['busy_frames']>=1
    return result

_snapshot_base=_snapshot

def _snapshot(session,events):
    rows=_snapshot_base(session,events)
    if len(rows)>=6:
        row=rows[5];seq=row['sequence']
        raw=b''.join(p[12:] for k,n,p in events if k==wire.OUTPUT and n==seq and struct.unpack('<I',p[8:12])[0]==1)
        row['hud']=hud_log_proof(raw)
    return rows

_qualified_base=_qualified_step

def _qualified_step(row,step,events):
    if step.ordinal!=6:return _qualified_base(row,step,events)
    if (not row['accepted'] or row['rejected'] or row['command']!=identity(HUD_COMMAND)
            or row['cwd']!=identity(b'/s22-root-work') or row['timeout_ms']!=15000
            or row['stderr']!=identity(b'')):return False
    terminal=row['terminal'];hud=row.get('hud')
    if terminal is None or any(terminal[i] for i in (1,2,3,5)):return False
    if type(hud) is not dict or set(hud)!={'schema','proved','log','frame_count','first_sequence','last_sequence','first_uptime_ms','last_uptime_ms','busy_frames'}:return False
    if hud['schema']!=HUD_SCHEMA or hud['proved'] is not True or hud['log']!=row['stdout']:return False
    if not all(type(hud[k]) is int for k in ('frame_count','first_sequence','last_sequence','first_uptime_ms','last_uptime_ms','busy_frames')):return False
    return (3<=hud['frame_count']<=601 and 0<hud['first_sequence']<hud['last_sequence']<=601
        and hud['last_sequence']-hud['first_sequence']>=hud['frame_count']-1
        and 0<hud['first_uptime_ms']<=hud['last_uptime_ms']-2000
        and 1<=hud['busy_frames']<=hud['frame_count'])

_audit_base=audit_binding

def audit_binding():
    return dict(_audit_base(),qualified_exec_count=TOTAL_COMMANDS,
        hud_required=True,hud_frame_minimum=3,hud_busy_frame_required=True,
        hud_log_limit=131072,hud_pixel_proof=False)
