"""Authenticate one actual-PID1 transition over the original descriptor.

Root-console health and its terminal acceptance retain their old wire domain.
The new program uses a separate domain and emits its own post-exec proof.
"""
import hashlib
import hmac
from pathlib import Path
import struct

import s22plus_native_baseline_protocol_v1 as baseline
import s22plus_native_baseline_health_v1 as health
import s22plus_native_wire_v3 as frames
import s22plus_root_console_v1 as wire
from s22plus_native_records_v3 import require

REQUEST,ACCEPTED,RECORD,RETURN,RETURN_ACK=37,168,169,38,170
DOMAIN=b'S22PLUS-FYG8-SWITCH-ROOT-v1'
MAXIMUM=256*1039
STAGES={1:'entered-pid1',2:'workers-settled',3:'root-admitted',4:'storage-rechecked',
    5:'ram-witness-ready',6:'mounts-moved',7:'switch-root-exec',8:'post-exec-witness',
    9:'download',10:'preparation-log',11:'stopped'}
LABELS={1:b'actual-pid1',2:b'three-workers-reaped',3:b'exact-root-checker',
    4:b'protected-after-retirement',5:b'fixed-ram-witness',6:b'mounts-moved-work-unmounted',7:b'busybox-switch-root'}


def tag(key,run,nonce,kind,sequence,body=b''):
    return hmac.digest(key,DOMAIN+run+nonce+struct.pack('<IB',sequence,kind)+body,'sha256')


def encode(key,run,nonce,kind,sequence,body=b''):
    return frames.encode_frame(kind,sequence,body+tag(key,run,nonce,kind,sequence,body))


def body(frame,key,run,nonce):
    require(32<=len(frame.payload)<=1023,'switch frame bound differs')
    value,signature=frame.payload[:-32],frame.payload[-32:]
    require(hmac.compare_digest(signature,tag(key,run,nonce,frame.frame_type,frame.sequence,value)),
        'switch frame authentication differs')
    return value


class Session(baseline.Session):
    @staticmethod
    def _validate_request(kind,value):
        if kind==REQUEST:require(not value,'fixed transition has no request body')
        else:wire.validate_request(kind,value)

    @staticmethod
    def _terminal_request(kind):return kind==REQUEST

    def _validate(self,kind,seq,value):
        if kind!=ACCEPTED:return super()._validate(kind,seq,value)
        require(not self.finished and seq==5 and self.requests=={3:wire.EXEC,4:wire.STATUS,5:REQUEST} and
            self.accepted==self.terminals=={3} and self.responses=={3,4} and
            len(value)==32 and struct.unpack('<8I',value)==(3,0,0,1,0,len(health.STDOUT)+len(health.STDERR),0,3),
            'PID1 transition lacks exact idle native health and unique terminal acceptance')
        require(getattr(self,'_last_terminal',None)==(3,0,0),'transition follows a failed command')
        self.responses.add(seq);self.finished=True
        self._record(dict(event='response',sequence=seq,kind=kind,fields=list(struct.unpack('<8I',value))))


class Records:
    def __init__(self,key,run,nonce,boot,witness_sha256):
        self.key,self.run,self.nonce,self.boot=key,run,nonce,boot
        self.expected_witness=witness_sha256
        self.records=[];self.logs=bytearray();self.last=0;self.proof=None;self.stop=None;self.returned=False

    def accept(self,frame):
        value=body(frame,self.key,self.run,self.nonce)
        if frame.frame_type==RETURN_ACK:
            require(self.proof is not None and not self.returned and self.stop is None and
                frame.sequence==6 and value==struct.pack('<I',1),'unjoined switch return acknowledgement')
            self.returned=True;return
        require(frame.frame_type==RECORD and not self.returned and self.proof is None and self.stop is None and
            frame.sequence==1024+len(self.records) and len(self.records)<256 and len(value)>=8,
            'switch stage ordinal or terminal state differs')
        stage,error=struct.unpack('<II',value[:8]);data=value[8:]
        require(stage in STAGES and error<=4095,'switch stage fields differ')
        if stage==10:
            require(error==0 and self.last==2 and len(data)<=768 and len(self.logs)+len(data)<=128*1024,
                'preparation log outside its admitted phase')
            self.logs.extend(data)
        elif stage==11:
            require(error and len(data)==4 and struct.unpack('<I',data)[0]==self.last,'switch stop lacks failed phase')
            self.stop=dict(errno=error,last_stage=self.last)
        else:
            require(stage==self.last+1 and error==0 and stage<=8,'switch stage skipped, repeated or failed')
            if stage<8:require(data==LABELS[stage],'switch stage payload differs')
            else:
                require(len(data)==120,'post-exec proof width differs')
                pid,major,minor,mounts=struct.unpack('<4I',data[:16]);flags,ro=struct.unpack('<2I',data[112:])
                require(pid==1 and (major,minor)!=(0,0) and 6<=mounts<=32 and flags==15 and ro==1 and
                    data[16:48]==self.boot and data[48:80].hex()==self.expected_witness and any(data[80:112]),
                    'post-exec PID/root/boot/executable/mount facts differ')
                self.proof=dict(pid=pid,root_device=dict(major=major,minor=minor),root_type='ext4',root_flags=flags,
                    partition_readonly=True,mount_count=mounts,mount_sha256=data[80:112].hex(),
                    witness_sha256=data[48:80].hex(),workers_settled=True,other_userspace=0,
                    descriptor_whitelist=[0,1,2,3],same_transport=True)
            self.last=stage
        self.records.append(dict(sequence=frame.sequence,stage=STAGES[stage],errno=error,size=len(data),
            sha256=hashlib.sha256(data).hexdigest()))

    def projection(self):
        return dict(status='PASS_SWITCH_ROOT_WITNESS' if self.proof is not None else 'NO_PROOF',
            verdict='PROVED_READONLY_HOST_PID1_ROOT_TRANSITION' if self.proof is not None else 'NO_PROOF',
            pid1_handoff_proved=self.proof is not None,debian_boot_proved=False,persistent_writes=False,
            return_accepted=self.returned,proof=self.proof,stages=self.records,stop=self.stop,
            preparation_log=dict(size=len(self.logs),sha256=hashlib.sha256(self.logs).hexdigest()))


def replay_one(codec,identity,key,rx,tx,*,io_class,witness_sha256):
    require(type(rx) is bytes and type(tx) is bytes and len(rx)<=MAXIMUM+65536 and len(tx)<=65536,
        'switch retained stream bound differs')
    io=io_class(codec,key,identity,rx=rx,tx=tx);io.handshake()
    rend=baseline._root_end(rx,io.rpos,(ACCEPTED,));tend=baseline._root_end(tx,io.tpos,(REQUEST,))
    session,events=wire.replay(key,bytes.fromhex(identity.run_id_hex),io.audit.nonce,
        rx[io.rpos:rend],tx[io.tpos:tend],session_class=Session)
    baseline._fixed_health(session,events)
    records=Records(key,bytes.fromhex(identity.run_id_hex),io.audit.nonce,io.audit.boot_id,witness_sha256)
    while rend<len(rx):
        require(len(rx)-rend>=16,'partial switch frame header')
        size=frames.HEADER.unpack(rx[rend:rend+16])[3];require(size<=1023,'switch frame oversized')
        frame=frames.decode_frame(rx[rend:rend+16+size]);records.accept(frame);rend+=16+size
    require(records.proof is not None and records.returned,'complete post-exec witness and return ACK required')
    expected=encode(key,records.run,records.nonce,RETURN,6)
    require(tx[tend:]==expected,'switch return is absent, repeated or followed by a new request')
    return dict(schema='s22plus-switch-root-observation-v1',run_id_hex=identity.run_id_hex,
        native_health_proved=True,ending='download',terminal_sequence=6,control_acceptance_observed=True,
        detach_ack_observed=False,kernel_boot_identity_sha256=health.digest(io.audit.boot_id),
        nonce_sha256=health.digest(io.audit.nonce),preparation=io.preparation.projection(),
        baseline_info=io.preparation.info,root_ready=list(session.ready),hud_requested=False,
        switch_root=records.projection(),rx=dict(size=len(rx),sha256=health.digest(rx)),
        tx=dict(size=len(tx),sha256=health.digest(tx))),len(rx),len(tx)


def replay_prefix(codec,identity,key,rx,tx,*,io_class,witness_sha256):
    """Preserve independently authenticated post-exec proof after a later cut.

    This grants neither return completion nor permission to send another byte.
    """
    require(len(rx)<=MAXIMUM+65536 and len(tx)<=65536,'switch prefix exceeds capture bounds')
    io=io_class(codec,key,identity,rx=rx,tx=tx);io.handshake()
    rend=baseline._root_end(rx,io.rpos,(ACCEPTED,));tend=baseline._root_end(tx,io.tpos,(REQUEST,))
    session,events=wire.replay(key,bytes.fromhex(identity.run_id_hex),io.audit.nonce,
        rx[io.rpos:rend],tx[io.tpos:tend],session_class=Session)
    baseline._fixed_health(session,events)
    records=Records(key,bytes.fromhex(identity.run_id_hex),io.audit.nonce,io.audit.boot_id,witness_sha256)
    error=None
    try:
        while rend<len(rx):
            require(len(rx)-rend>=16,'partial switch prefix header')
            size=frames.HEADER.unpack(rx[rend:rend+16])[3];require(size<=1023,'oversized switch prefix')
            records.accept(frames.decode_frame(rx[rend:rend+16+size]));rend+=16+size
        returned=tx[tend:];expected=encode(key,records.run,records.nonce,RETURN,6)
        require(expected.startswith(returned),'unexpected post-transition request bytes')
        require(not records.returned or returned==expected,'return ACK lacks a complete original request')
    except (ValueError,EOFError) as failure:error=str(failure)
    return dict(records.projection(),protocol_complete=False,raw_prefix_bytes=rend,
        diagnostic_error=error,replay_authorized=False,
        nonce_sha256=health.digest(io.audit.nonce),kernel_boot_identity_sha256=health.digest(io.audit.boot_id))


def qualify_one(io,*,evidence,before_terminal,before_extra,witness_sha256):
    require(callable(before_terminal) and callable(before_extra),'switch effects lack their owner callbacks')
    session=None;events=[]
    try:
        io.handshake();run=bytes.fromhex(io.identity.run_id_hex)
        session=Session(io.fd,io.key,run,io.audit.nonce,Path(evidence),on_rx=io.capture,
            on_tx=io.audit.tx.extend,before_write=io.before_write,clock=io.clock)
        health.run_console_checks(session,events,deadline=min(io.deadline,io.clock()+29.9),clock=io.clock)
        require(not session.decoder.pending and io.deadline-io.clock()>=305,'switch admission lacks a full bounded window')
        request=dict(run_id_hex=io.identity.run_id_hex,mode='fixed-pid1-transition',sequence=5,
            body_sha256=health.digest(b''),nonce_sha256=health.digest(io.audit.nonce),
            kernel_boot_identity_sha256=health.digest(io.audit.boot_id),baseline_info=io.preparation.info)
        before_extra(request);session.send(REQUEST,timeout=2)
        # Read exactly one native-domain ACK, then use the new executable's
        # distinct domain. A bulk read must not misinterpret coalesced frames.
        frame=io.frame();decoder=wire.Decoder(io.key,run,io.audit.nonce)
        values=decoder.feed(frames.encode_frame(frame.frame_type,frame.sequence,frame.payload))
        require(len(values)==1 and values[0][:2]==(ACCEPTED,5),'fixed terminal acceptance absent')
        session._validate(*values[0]);session.close();session=None
        records=Records(io.key,run,io.audit.nonce,io.audit.boot_id,witness_sha256)
        while records.proof is None:
            records.accept(io.frame())
            require(records.stop is None,'native PID1 transition stopped before proof')
        before_terminal(dict(request,mode='switch-root-return',sequence=6))
        encoded=encode(io.key,run,io.audit.nonce,RETURN,6)
        frame=frames.decode_frame(encoded);io.send(frame.frame_type,frame.sequence,frame.payload)
        records.accept(io.frame());require(records.returned,'fixed witness return unproved')
        rx,tx=bytes(io.audit.rx),bytes(io.audit.tx)
        value,_,_=replay_one(io.codec,io.identity,io.key,rx,tx,io_class=type(io),witness_sha256=witness_sha256)
        io.audit.done_seen=True;io.audit.current_stage='switch-root-return-accepted';return value
    finally:
        if session is not None:session.close()
