"""One authenticated root transition, installed PID1 proof and ACM retirement.

The same compound intent owns all phases. No frame authorizes a second boot,
generic command, writable retry, shutdown or Android return.
"""
import hashlib
from pathlib import Path
import struct
import s22plus_switch_root_protocol_v1 as base
from s22plus_native_records_v3 import require

CONTINUE,CONTINUE_ACK,INIT_PROOF,RELEASE,RELEASE_ACK=39,171,172,40,173
MAXIMUM=base.MAXIMUM+2048
encode,frames,health=base.encode,base.frames,base.health


class Records(base.Records):
    def __init__(self,key,run,nonce,boot,witness_sha256,init_sha256,hook_sha256):
        super().__init__(key,run,nonce,boot,witness_sha256,root_readonly=False)
        self.expected_init,self.expected_hook=init_sha256,hook_sha256
        self.continued=self.released=False;self.init_proof=None

    def accept(self,frame):
        if frame.frame_type==base.RECORD and self.proof is None:return super().accept(frame)
        value=base.body(frame,self.key,self.run,self.nonce)
        require(self.proof is not None and not self.released and self.stop is None,'Debian phase lacks root proof')
        if frame.frame_type==base.RECORD:
            require(frame.sequence==1024+len(self.records) and len(value)==12 and
                struct.unpack('<I',value[:4])[0]==11 and 0<struct.unpack('<I',value[4:8])[0]<=4095 and
                value[8:]==struct.pack('<I',8),'Debian stop lacks original witness phase')
            self.stop=dict(errno=struct.unpack('<I',value[4:8])[0],last_stage=8);return
        if frame.frame_type==CONTINUE_ACK:
            require(not self.continued and self.init_proof is None and frame.sequence==6 and
                value==struct.pack('<I',1),'repeated or out-of-phase init continuation')
            self.continued=True;return
        if frame.frame_type==INIT_PROOF:
            require(self.continued and self.init_proof is None and frame.sequence==7 and len(value)==116,
                'unjoined installed PID1 proof')
            pid,major,minor=struct.unpack('<3I',value[:12]);acm,state=struct.unpack('<2I',value[108:])
            require(pid==1 and dict(major=major,minor=minor)==self.proof['root_device'] and
                value[12:44]==self.boot and value[44:76].hex()==self.expected_init and
                value[76:108].hex()==self.expected_hook and acm==state==0,'installed PID1 facts differ')
            self.init_proof=dict(pid=1,root_device=self.proof['root_device'],same_kernel_boot=True,
                init_sha256=self.expected_init,hook_sha256=self.expected_hook,inherited_acm_fds=0,inherited_state_fds=0)
            return
        require(frame.frame_type==RELEASE_ACK and self.init_proof is not None and frame.sequence==7 and
            value==struct.pack('<I',1),'unjoined ACM release acknowledgement')
        self.released=True

    def projection(self):
        return dict(status='PASS_INSTALLED_DEBIAN_PID1' if self.init_proof else 'NO_PROOF_DEBIAN_PID1',
            root_transition=super().projection(),init_proof=self.init_proof,continue_accepted=self.continued,
            acm_release_accepted=self.released,acm_departure_proved=False,ssh_access_proved=False,
            persistent_writes=True,clean_shutdown_proved=False,stop=self.stop)


def reader(key,run,nonce,boot,selection):
    return Records(key,run,nonce,boot,selection['witness']['sha256'],selection['installed_init']['sha256'],
        selection['assets']['hook']['sha256'])


def prefix(codec,identity,key,rx,tx,*,io_class,selection,complete=False):
    require(type(rx) is bytes and type(tx) is bytes and len(rx)<=MAXIMUM+65536 and len(tx)<=65536,
        'Debian retained stream bound differs')
    io=io_class(codec,key,identity,rx=rx,tx=tx);io.handshake()
    rend=base.baseline._root_end(rx,io.rpos,(base.ACCEPTED,));tend=base.baseline._root_end(tx,io.tpos,(base.REQUEST,))
    session,events=base.wire.replay(key,bytes.fromhex(identity.run_id_hex),io.audit.nonce,
        rx[io.rpos:rend],tx[io.tpos:tend],session_class=base.Session)
    base.baseline._fixed_health(session,events)
    records=reader(key,bytes.fromhex(identity.run_id_hex),io.audit.nonce,io.audit.boot_id,selection);error=None
    try:
        while rend<len(rx):
            require(len(rx)-rend>=16,'partial Debian handoff header')
            size=frames.HEADER.unpack(rx[rend:rend+16])[3];require(size<=1023,'Debian frame too large')
            records.accept(frames.decode_frame(rx[rend:rend+16+size]));rend+=16+size
        continuation=encode(key,records.run,records.nonce,CONTINUE,6)
        release=encode(key,records.run,records.nonce,RELEASE,7)
        transmitted=tx[tend:]
        require((continuation+release).startswith(transmitted),'unexpected or repeated Debian continuation')
        require(not transmitted or records.proof is not None,'continuation precedes root proof')
        require(len(transmitted)<=len(continuation) or records.init_proof is not None,'release precedes PID1 proof')
        require(not records.continued or len(transmitted)>=len(continuation),'continuation ACK lacks request')
        require(not records.released or transmitted==continuation+release,'release ACK lacks request')
        if complete:require(records.released and records.stop is None,'Debian native-side handoff incomplete')
    except (ValueError,EOFError) as failure:
        if complete:raise
        error=str(failure)
    return dict(schema='s22plus-debian-handoff-observation-v1',run_id_hex=identity.run_id_hex,
        native_health_proved=True,ending='handoff',terminal_sequence=7,
        control_acceptance_observed=records.released,detach_ack_observed=False,
        kernel_boot_identity_sha256=health.digest(io.audit.boot_id),nonce_sha256=health.digest(io.audit.nonce),
        kernel_boot_proof=io.audit.boot_id.hex(),preparation=io.preparation.projection(),
        baseline_info=io.preparation.info,root_ready=list(session.ready),hud_requested=False,
        debian_handoff=records.projection(),protocol_complete=complete,diagnostic_error=error,
        raw_prefix_bytes=rend,replay_authorized=False,
        rx=dict(size=len(rx),sha256=health.digest(rx)),tx=dict(size=len(tx),sha256=health.digest(tx)))


def replay_one(*args,**kwargs):
    value=prefix(*args,**kwargs,complete=True);return value,value['rx']['size'],value['tx']['size']


def qualify_one(io,*,evidence,before_terminal,before_extra,selection):
    require(callable(before_terminal) and callable(before_extra),'Debian handoff lacks compound owner callbacks')
    session=None;events=[]
    try:
        io.handshake();run=bytes.fromhex(io.identity.run_id_hex)
        session=base.Session(io.fd,io.key,run,io.audit.nonce,Path(evidence),on_rx=io.capture,
            on_tx=io.audit.tx.extend,before_write=io.before_write,clock=io.clock)
        health.run_console_checks(session,events,deadline=min(io.deadline,io.clock()+29.9),clock=io.clock)
        require(not session.decoder.pending and io.deadline-io.clock()>=305,'Debian admission window too short')
        request=dict(run_id_hex=io.identity.run_id_hex,mode='debian-handoff',sequence=5,
            body_sha256=health.digest(b''),nonce_sha256=health.digest(io.audit.nonce),
            kernel_boot_identity_sha256=health.digest(io.audit.boot_id),baseline_info=io.preparation.info)
        before_extra(request);session.send(base.REQUEST,timeout=2)
        frame=io.frame();decoder=base.wire.Decoder(io.key,run,io.audit.nonce)
        values=decoder.feed(frames.encode_frame(frame.frame_type,frame.sequence,frame.payload))
        require(len(values)==1 and values[0][:2]==(base.ACCEPTED,5),'Debian terminal admission ACK absent')
        session._validate(*values[0]);session.close();session=None
        records=reader(io.key,run,io.audit.nonce,io.audit.boot_id,selection)
        while records.proof is None:
            records.accept(io.frame());require(records.stop is None,'Debian root transition stopped')
        before_terminal(dict(request,mode='debian-init-continue',sequence=6,root_proof=records.proof))
        frame=frames.decode_frame(encode(io.key,run,io.audit.nonce,CONTINUE,6));io.send(frame.frame_type,frame.sequence,frame.payload)
        records.accept(io.frame());require(records.continued,'init continuation ACK absent')
        while records.init_proof is None:
            records.accept(io.frame());require(records.stop is None,'installed init observation stopped')
        before_terminal(dict(request,mode='debian-acm-release',sequence=7,init_proof=records.init_proof))
        frame=frames.decode_frame(encode(io.key,run,io.audit.nonce,RELEASE,7));io.send(frame.frame_type,frame.sequence,frame.payload)
        records.accept(io.frame());require(records.released,'ACM release ACK absent')
        rx,tx=bytes(io.audit.rx),bytes(io.audit.tx)
        value,_,_=replay_one(io.codec,io.identity,io.key,rx,tx,io_class=type(io),selection=selection)
        io.audit.done_seen=True;io.audit.current_stage='debian-acm-release-accepted';return value
    finally:
        if session is not None:session.close()
