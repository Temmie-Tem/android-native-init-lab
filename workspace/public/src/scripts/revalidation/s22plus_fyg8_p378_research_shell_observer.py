"""v0.1.2-rc.1 gauge telemetry HUD, prospective fresh candidate."""
from s22plus_fyg8_p378_namespace import load_predecessor
load_predecessor(globals())

HUD_SCHEMA='s22plus-fyg8-p378-gauge-hud-log-proof-v1'
PROOF_SCOPE='root-console-and-fresh-memory-CPU-gauge-HUD-flip-events-pixels-unproved'
_GAUGE_FRAME=re.compile(rb'(HUD_FRAME run=[0-9a-f]{32} seq=[0-9]{1,20} uptime_ms=[0-9]{1,20} state=[0-2] metrics_seq=[0-9]{1,20} valid=)([0-9]{1,20})( age_ms=[0-9]{1,20} mem_total=[0-9]{1,20} mem_available=[0-9]{1,20} cpu_permille=[0-9]{1,20} battery_pct=[0-9]{1,20} charge=[0-9]{1,20} temp_deci=-?[0-9]{1,20}) gauge_seq=([0-9]{1,20}) gauge_age_ms=([0-9]{1,20}) gauge_soc=([0-9]{1,20}) voltage_uv=([0-9]{1,20}) current_ua=(-?[0-9]{1,20})( event=matched visible=UNPROVED)')
_gauge_base_proof=hud_log_proof


def hud_log_proof(raw):
    if len(raw)>262144:
        result=_gauge_base_proof(b'');result['log']=identity(raw);result['proved']=False;return result
    projected=[];fresh=[];last_gauge=0;bad=False
    for line in raw.splitlines():
        if not line.startswith(b'HUD_FRAME '):projected.append(line);continue
        match=_GAUGE_FRAME.fullmatch(line)
        if match is None:bad=True;break
        valid,seq,age,soc,voltage,current=map(int,(match[2],match[4],match[5],match[6],match[7],match[8]))
        if valid&~255 or not 0<=seq<=601 or age>2**64-1:bad=True;break
        if valid&224 and (not seq or age>5000):bad=True;break
        if seq and seq<last_gauge:bad=True;break
        if seq:last_gauge=seq
        if valid&32 and soc>1000:bad=True;break
        if valid&64 and not 2000000<=voltage<=5000000:bad=True;break
        if valid&128 and not -25600000<=current<=25599218:bad=True;break
        projected.append(match[1]+str(valid&31).encode()+match[3]+match[9])
        if valid&227==227:
            up=int(re.search(rb' uptime_ms=([0-9]{1,20})',line)[1]);busy=b' state=1 ' in line
            fresh.append((seq,up,busy))
    result=_gauge_base_proof(b'\n'.join(projected)+(b'\n' if raw.endswith(b'\n') else b''))
    result['log']=identity(raw)
    result['proved']=(result['proved'] and not bad and len(raw)<=262144 and len({row[0] for row in fresh})>=3
        and fresh[-1][1]-fresh[0][1]>=2000 and any(row[2] for row in fresh))
    return result


# Field positions are fixed by HUD_FRAME. Wait for distinct valid gauge samples
# while memory/CPU are also fresh, not repeated displays of one gauge sample.
HUD_COMMAND=(b'n=0; while [ "$n" -lt 12 ]; do '
    b'[ "$(/bin/busybox awk \'/^HUD_FRAME / {split($7,v,"="); split($15,s,"="); if (v[2]%4==3 && int(v[2]/32)==7 && !seen[s[2]]++) n++} END {print n+0}\' hud.log)" -ge 3 ] && break; '
    b'n=$((n+1)); /bin/busybox sleep 1; done; /bin/busybox cat hud.log')
QUALIFICATION_COMMANDS=QUALIFICATION_COMMANDS[:-1]+(QualificationStep(6,'fresh-gauge-status-hud-with-console',HUD_COMMAND,b''),)
_gauge_base_audit=audit_binding

def audit_binding():
    value=_gauge_base_audit();value.update(hud_gauge_fresh_samples=3,gauge_voltage_current_required=True,gauge_soc='capped-gauge-register-estimate')
    return value
