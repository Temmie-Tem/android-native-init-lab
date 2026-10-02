"""One authenticated root transition, installed PID1 proof and ACM retirement.

The same compound intent owns all phases. No frame authorizes a second boot,
generic command, writable retry, shutdown or Android return.
"""
import hashlib
from pathlib import Path
import struct
import time
import s22plus_switch_root_protocol_v1 as base
from s22plus_native_records_v3 import publish,require

CONTINUE,CONTINUE_ACK,INIT_PROOF,RELEASE,RELEASE_ACK=39,171,172,40,173
START,START_ACK,PROGRESS=41,175,176
BOUNDARY=177
BOUNDARY_MAX=40
START_SEQUENCE,RELEASE_SEQUENCE=8,9
SAMPLE_MS,SAMPLES=10000,12
MAXIMUM=base.MAXIMUM+8192
encode,frames,health=base.encode,base.frames,base.health


class Records(base.Records):
    def __init__(self,key,run,nonce,boot,witness_sha256,init_sha256,hook_sha256,*,observer_revision=2):
        super().__init__(key,run,nonce,boot,witness_sha256,root_readonly=False)
        require(type(observer_revision) is int and observer_revision in (2,3),'unknown Debian observer revision')
        self.observer_revision=observer_revision;self.boundaries=[]
        self.expected_init,self.expected_hook=init_sha256,hook_sha256
        self.continued=self.started=self.released=False;self.init_proof=None;self.progress=[]

    def startup_complete(self,phase):
        rows=[r for r in self.boundaries if r['phase']==phase]
        return bool(rows and rows[-1]['event']==5 and rows[-1]['wait_status']==0)

    def boundary(self,frame,value):
        require(self.observer_revision==3 and self.started and len(self.progress) in (1,2) and
            len(self.boundaries)<BOUNDARY_MAX and len(value)==64,'unselected or excessive startup boundary')
        phase,event,pid,status,elapsed,closed=struct.unpack('<4I2Q',value[:32])
        require(phase==len(self.progress) and value[32:]==self.boot and elapsed<300000 and
            (not self.boundaries or elapsed>=self.boundaries[-1]['elapsed_ms']),
            'startup boundary boot, phase or original deadline differs')
        rows=[r for r in self.boundaries if r['phase']==phase]
        require(frame.sequence==(3000 if phase==1 else 3100)+len(rows),'startup boundary sequence differs')
        previous=rows[-1]['event'] if rows else 0
        allowed={0:(1,) if phase==1 else (2,),1:(2,),2:(3,),3:(4,5),4:(4,5),5:()}
        require(event in allowed[previous] and (pid==0 if event<=2 else 1<pid<=2147483647) and
            (status==0 if event!=5 else 0<=status<=65535) and
            (rows[-1]['elapsed_ms']<=closed<=elapsed if phase==1 and event==2 else closed==0),
            'startup boundary ordering, close return or child identity differs')
        if event>=4:
            require(pid==rows[-1]['child_pid'] and
                (event!=4 or elapsed-rows[-1]['elapsed_ms']>=SAMPLE_MS),
                'startup wait child or heartbeat interval differs')
        self.boundaries.append(dict(phase=phase,event=event,child_pid=pid,wait_status=status,
            elapsed_ms=elapsed,close_return_elapsed_ms=closed))

    @property
    def runtime_proof(self):
        if len(self.progress)!=SAMPLES+3:return None
        return dict(rcs_entered=True,rcs_completed=True,runlevel_completed=True,pid=1,
            same_kernel_boot=True,cron_and_sshd=True,samples=SAMPLES+1,
            elapsed_ms=self.progress[-1]['elapsed_ms'])

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
        if frame.frame_type==START_ACK:
            require(self.init_proof is not None and not self.started and frame.sequence==START_SEQUENCE and
                value==struct.pack('<I',1),'unjoined or repeated Debian service start')
            self.started=True;return
        if frame.frame_type==BOUNDARY:
            self.boundary(frame,value);return
        if frame.frame_type==PROGRESS:
            ordinal=len(self.progress)
            require(self.started and ordinal<SAMPLES+3 and frame.sequence==2000+ordinal and len(value)==56,
                'out-of-order Debian progress')
            if self.observer_revision==3 and ordinal in (1,2):
                require(self.startup_complete(ordinal),'startup completion lacks exact child success')
            stage,sample,pid,services,elapsed=struct.unpack('<4IQ',value[:24])
            expected_stage=ordinal+1 if ordinal<3 else 4
            expected_sample=max(0,ordinal-2)
            require(stage==expected_stage and sample==expected_sample and pid==1 and value[24:]==self.boot and
                services==(0 if ordinal<2 else 3) and
                (elapsed==0 if ordinal<2 else sample*SAMPLE_MS<=elapsed<=sample*SAMPLE_MS+10000) and
                (ordinal<3 or elapsed>self.progress[-1]['elapsed_ms']),
                'Debian progress lacks same-boot ordered service liveness')
            self.progress.append(dict(stage=stage,sample=sample,elapsed_ms=elapsed,services=services));return
        require(frame.frame_type==RELEASE_ACK and self.runtime_proof is not None and frame.sequence==RELEASE_SEQUENCE and
            value==struct.pack('<I',1),'unjoined ACM release acknowledgement')
        self.released=True

    def projection(self):
        value=dict(status='PASS_INSTALLED_DEBIAN_PID1' if self.init_proof else 'NO_PROOF_DEBIAN_PID1',
            root_transition=super().projection(),init_proof=self.init_proof,continue_accepted=self.continued,
            services_start_accepted=self.started,progress=self.progress,runtime_proof=self.runtime_proof,
            acm_release_accepted=self.released,acm_departure_proved=False,ssh_access_proved=False,
            persistent_writes=True,clean_shutdown_proved=False,stop=self.stop)
        if self.observer_revision==3:value.update(observer_revision=3,startup_boundaries=self.boundaries)
        return value


def reader(key,run,nonce,boot,selection):
    return Records(key,run,nonce,boot,selection['witness']['sha256'],selection['installed_init']['sha256'],
        selection['assets']['hook']['sha256'],observer_revision=selection.get('observer_revision',2))


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
        start=encode(key,records.run,records.nonce,START,START_SEQUENCE)
        release=encode(key,records.run,records.nonce,RELEASE,RELEASE_SEQUENCE)
        transmitted=tx[tend:]
        require((continuation+start+release).startswith(transmitted),'unexpected or repeated Debian continuation')
        require(not transmitted or records.proof is not None,'continuation precedes root proof')
        require(len(transmitted)<=len(continuation) or records.init_proof is not None,'service start precedes PID1 proof')
        require(len(transmitted)<=len(continuation+start) or records.runtime_proof is not None,'release precedes runtime proof')
        require(not records.continued or len(transmitted)>=len(continuation),'continuation ACK lacks request')
        require(not records.started or len(transmitted)>=len(continuation+start),'start ACK lacks request')
        require(not records.released or transmitted==continuation+start+release,'release ACK lacks request')
        if complete:require(records.released and records.stop is None,'Debian native-side handoff incomplete')
    except (ValueError,EOFError) as failure:
        if complete:raise
        error=str(failure)
    return dict(schema='s22plus-debian-handoff-observation-v1',run_id_hex=identity.run_id_hex,
        native_health_proved=True,ending='handoff',terminal_sequence=RELEASE_SEQUENCE,
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
        receipts=0
        def receive():
            nonlocal receipts
            frame=io.frame()  # The IO has already retained the raw bytes.
            if records.observer_revision==3:
                require(receipts<128,'Debian receive receipt bound exceeded')
                publish(Path(evidence)/('debian-receive-%03d.json'%receipts),dict(
                    clock='CLOCK_BOOTTIME',received_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME),
                    raw_prefix_bytes=len(io.audit.rx),frame_type=frame.frame_type,sequence=frame.sequence,
                    frame_sha256=health.digest(frames.encode_frame(frame.frame_type,frame.sequence,frame.payload))))
                receipts+=1
            records.accept(frame)
        while records.proof is None:
            receive();require(records.stop is None,'Debian root transition stopped')
        before_terminal(dict(request,mode='debian-init-continue',sequence=6,root_proof=records.proof))
        frame=frames.decode_frame(encode(io.key,run,io.audit.nonce,CONTINUE,6));io.send(frame.frame_type,frame.sequence,frame.payload)
        receive();require(records.continued,'init continuation ACK absent')
        while records.init_proof is None:
            receive();require(records.stop is None,'installed init observation stopped')
        before_terminal(dict(request,mode='debian-services-start',sequence=START_SEQUENCE,init_proof=records.init_proof))
        frame=frames.decode_frame(encode(io.key,run,io.audit.nonce,START,START_SEQUENCE));io.send(frame.frame_type,frame.sequence,frame.payload)
        receive();require(records.started,'service start ACK absent')
        while records.runtime_proof is None:
            receive();require(records.stop is None,'Debian service progress stopped')
        before_terminal(dict(request,mode='debian-acm-release',sequence=RELEASE_SEQUENCE,
            init_proof=records.init_proof,runtime_proof=records.runtime_proof))
        frame=frames.decode_frame(encode(io.key,run,io.audit.nonce,RELEASE,RELEASE_SEQUENCE));io.send(frame.frame_type,frame.sequence,frame.payload)
        receive();require(records.released,'ACM release ACK absent')
        rx,tx=bytes(io.audit.rx),bytes(io.audit.tx)
        value,_,_=replay_one(io.codec,io.identity,io.key,rx,tx,io_class=type(io),selection=selection)
        io.audit.done_seen=True;io.audit.current_stage='debian-acm-release-accepted';return value
    finally:
        if session is not None:session.close()
