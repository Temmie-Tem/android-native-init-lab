"""v0.1.1-rc.1 system-status HUD, fresh candidate identity."""
from s22plus_fyg8_p377_namespace import load_predecessor
load_predecessor(globals())

HUD_SCHEMA='s22plus-fyg8-p377-status-hud-log-proof-v1'
PROOF_SCOPE='root-console-and-fresh-memory-CPU-HUD-flip-events-pixels-unproved'
_FRAME=re.compile(rb'HUD_FRAME run=([0-9a-f]{32}) seq=([0-9]+) uptime_ms=([0-9]+) state=([0-2]) metrics_seq=([0-9]+) valid=([0-9]+) age_ms=([0-9]+) mem_total=([0-9]+) mem_available=([0-9]+) cpu_permille=([0-9]+) battery_pct=([0-9]+) charge=([0-9]+) temp_deci=(-?[0-9]+) event=matched visible=UNPROVED')


def hud_log_proof(raw):
    result=dict(schema=HUD_SCHEMA,proved=False,log=identity(raw),frame_count=0,
        first_sequence=0,last_sequence=0,first_uptime_ms=0,last_uptime_ms=0,busy_frames=0)
    if len(raw)>262144 or not raw.endswith(b'\n'):return result
    starts=[];collectors=[];frames=[];fresh=[];last_metrics=0
    for line in raw.splitlines():
        if line.startswith((b'HUD_START ',b'METRICS_START ')):
            if not re.fullmatch(rb'(HUD|METRICS)_START [1-9][0-9]*',line):return result
            (starts if line.startswith(b'HUD_') else collectors).append(int(line.split()[1]))
        elif line.startswith(b'HUD_FRAME '):
            match=_FRAME.fullmatch(line)
            if match is None or match[1].decode()!=RUN_ID_HEX:return result
            seq,up,state,ms,valid,age,total,available,cpu,cap,charge,temp=map(int,match.groups()[1:])
            if not 0<seq<=601 or not up or (frames and (seq<=frames[-1][0] or up<=frames[-1][1])):return result
            if not 0<=ms<=601 or valid&~31 or age>2**64-1:return result
            if valid and (not ms or age>5000):return result
            if ms and ms<last_metrics:return result
            if ms:last_metrics=ms
            if valid&1 and not 0<=available<=total<=2**30:return result
            if valid&1 and not total:return result
            if valid&2 and cpu>1000:return result
            if valid&4 and cap>100:return result
            if valid&8 and charge>4:return result
            if valid&16 and not -500<=temp<=1500:return result
            frames.append((seq,up,state))
            if valid&3==3:fresh.append((seq,up,state,ms))
        elif line.startswith((b'HUD_',b'METRICS_',b'DISPLAY_FAIL ')):return result
    if len(starts)!=1 or len(collectors)!=1 or min(starts+collectors)<=1 or starts==collectors or len(frames)<3:return result
    result.update(frame_count=len(frames),first_sequence=frames[0][0],last_sequence=frames[-1][0],
        first_uptime_ms=frames[0][1],last_uptime_ms=frames[-1][1],busy_frames=sum(state==1 for _,_,state in frames))
    result['proved']=(len(fresh)>=3 and len({row[3] for row in fresh})>=3 and fresh[-1][1]-fresh[0][1]>=2000
        and any(row[2]==1 for row in fresh) and result['busy_frames']>=1)
    return result

_status_audit_base=audit_binding

def audit_binding():
    value=_status_audit_base()
    value.update(hud_log_limit=262144,hud_fresh_memory_cpu_frames=3,hud_battery_required=False)
    return value

# Wait for the declared fresh memory/CPU evidence, including the initial CPU
# baseline interval, rather than stopping after three arbitrary HUD frames.
HUD_COMMAND=(b'n=0; while [ "$n" -lt 10 ]; do '
    b'[ "$(/bin/busybox awk \'/^HUD_FRAME / {split($6,s,"="); split($7,v,"="); if (v[2]%4==3 && !seen[s[2]]++) n++} END {print n+0}\' hud.log)" -ge 3 ] && break; '
    b'n=$((n+1)); /bin/busybox sleep 1; done; /bin/busybox cat hud.log')
QUALIFICATION_COMMANDS=QUALIFICATION_COMMANDS[:-1]+(QualificationStep(6,'fresh-status-hud-with-console',HUD_COMMAND,b''),)
