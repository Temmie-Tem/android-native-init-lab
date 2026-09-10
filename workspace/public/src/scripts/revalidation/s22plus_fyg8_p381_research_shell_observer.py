"""v0.1.2-rc.4 output backpressure and bounded memory observations."""
from s22plus_fyg8_p381_namespace import load_predecessor
load_predecessor(globals())
import s22plus_memory_snapshot_v1 as memory_snapshot

# Memory commands follow functional qualification in the new sealed plan.
HUD_COMMAND=_gauge_command
QUALIFICATION_COMMANDS=QUALIFICATION_COMMANDS[:-1]+(
    QualificationStep(6,'fresh-gauge-hud-with-console',HUD_COMMAND,b''),)
_qualified_step=_memory_qualified
_rc4_observer_audit=audit_binding
_rc4_snapshot=_snapshot
_rc4_hud_proof=hud_log_proof


def hud_log_proof(raw):
    # HUD_MEM is optional diagnostic data, interpreted by the snapshot helper.
    # Preserve the original authenticated log identity and ancestor HUD guards.
    projected=b''.join(line for line in raw.splitlines(keepends=True)
        if not line.startswith(b'HUD_MEM '))
    result=_rc4_hud_proof(projected)
    result['log']=identity(raw)
    if len(raw)>262144 or not raw.endswith(b'\n'):result['proved']=False
    return result


def _snapshot(session,events):
    rows=_rc4_snapshot(session,events)
    for ordinal,row in enumerate(rows,1):
        if ordinal<=len(QUALIFICATION_COMMANDS):continue
        sequence=row['sequence'];body=session.request_bodies[sequence]
        timeout,cwd_size=struct.unpack('<IH',body[:6])
        phase=memory_snapshot.COMMAND_PHASES.get(body[6+cwd_size:])
        if phase is None or timeout!=15000 or body[6:6+cwd_size]!=b'/s22-root-work':continue
        streams={stream:b''.join(p[12:] for k,n,p in events if k==wire.OUTPUT and n==sequence and
                                struct.unpack_from('<I',p,8)[0]==stream) for stream in (1,2)}
        row['memory_snapshot']=memory_snapshot.from_command(streams[1],phase,row['terminal'],streams[2])
    return rows


def audit_binding():
    value=_rc4_observer_audit()
    value.update(optional_memory_snapshots=0,memory_stream='post-qualification-plan',
        memory_minimum_interval_seconds=2,memory_required_for_gauge=False,
        memory_snapshot_limit=4096,memory_diagnostics_qualify_console=False)
    return value
