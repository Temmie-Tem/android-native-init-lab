"""Re-derive diagnostic stage markers without completing a failed operation."""
from pathlib import Path
import struct

import device_action_raw_capture_v1 as raw
import s22plus_native_observation_v3 as native
import s22plus_native_baseline_protocol_v1 as protocol
import s22plus_native_staged_preflight_profile_v1 as profile
import s22plus_root_console_v1 as wire
from s22plus_native_wire_v3 import Codec
from s22plus_native_records_v3 import Journal,digest,pin,read,require


def from_bytes(image,rx,tx,intent):
    bound=native.identity(image);key=native.key_bytes(image)
    io=native.io_class(profile.SELECTION,image)(Codec(bound.namespace),key,bound,rx=rx,tx=tx)
    io.handshake()
    state,events,framing=wire.replay_prefix(key,bytes.fromhex(bound.run_id_hex),io.audit.nonce,
        rx[io.rpos:],tx[io.tpos:],session_class=protocol.Session)
    try: protocol._fixed_health(state,events)
    except StopIteration as exc:
        raise ValueError('diagnostic prefix lacks complete fixed health') from exc
    fixed=profile.Profile(image)
    require(state.requests.get(5)==wire.EXEC and state.request_bodies[5]==fixed.BODY and 5 in state.accepted and
        intent['mode']=='fixed-extra' and intent['sequence']==5 and intent['body_sha256']==digest(fixed.BODY) and
        intent['run_id_hex']==image['run_id_hex'] and intent['nonce_sha256']==digest(io.audit.nonce) and
        intent['kernel_boot_identity_sha256']==digest(io.audit.boot_id),
        'diagnostic prefix lacks its original authenticated command intent')
    require(all(events[i][1]<=events[i+1][1] for i in range(len(events)-1)),'diagnostic response order differs')
    stdout=b''.join(body[12:] for kind,seq,body in events if (kind,seq)==(wire.OUTPUT,5) and struct.unpack_from('<I',body,8)[0]==1)
    result=profile.progress(stdout)
    return dict(schema=profile.SCHEMA+'-diagnostic-prefix',status='DIAGNOSTIC_ONLY',
        progress=result,framing=framing,root_offsets=dict(rx=io.rpos,tx=io.tpos),session_completion_proved=False,cleanup_proved=False,
        run_id_hex=image['run_id_hex'],kernel_boot_identity_sha256=digest(io.audit.boot_id),nonce_sha256=digest(io.audit.nonce),
        stdout=dict(size=len(stdout),sha256=digest(stdout)),rx=dict(size=len(rx),sha256=digest(rx)),tx=dict(size=len(tx),sha256=digest(tx)))


def rederive(adapter,request):
    directory=adapter.folder(profile.SELECTION)
    opened=read(directory/'open.json');closed=read(directory/'close.json')
    require(opened['image']==closed['image']==request['N'] and
        opened.get('profile')==closed.get('profile')==profile.SELECTION and
        opened['ending']==closed['ending']=='detach' and opened['hud'] is closed['hud'] is False and
        closed['open']==pin(directory/'open.json'),'diagnostic capture context differs')
    handle=raw.load_handle(directory/'session.capture.json')
    rx=raw.read_stdout(handle,maximum=wire.RAW_CAPTURE_MAXIMUM);tx=raw.read_stderr(handle,maximum=65536)
    intents=[r['data'] for r in Journal(adapter.directory/'journal').rows()
        if r['event']=='effect-intent' and r['data']['step']==profile.SELECTION]
    require(len(intents)==1,'diagnostic prefix has no unique execution owner')
    value=from_bytes(request['N'],rx,tx,intents[0]['detail'])
    return dict(value,raw=pin(directory/'session.capture.json'),closed=pin(directory/'close.json'),
        producer=dict(returncode=handle.returncode,timed_out=handle.timed_out,output_exceeded=handle.output_exceeded,
            error_type=handle.producer_error_type))
