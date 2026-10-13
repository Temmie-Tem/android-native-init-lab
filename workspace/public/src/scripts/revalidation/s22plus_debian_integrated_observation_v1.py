"""Single compound integrated-start, bounded continuations and raw-first proof."""
import os
from pathlib import Path
import secrets
import select

import device_action_raw_capture_v1 as raw
import s22plus_debian_integrated_profile_v1 as profile
import s22plus_debian_integrated_protocol_v1 as protocol
import s22plus_native_target_io_v3 as target
from s22plus_native_records_v3 import clock,digest,pin,publish,read,require,verify

CONTINUATIONS=((protocol.handoff.CONTINUE,6,'continue','proof'),
    (protocol.handoff.START,8,'start','init_proof'),
    (protocol.handoff.RELEASE,9,'release','runtime_proof'))


def rederive(directory,image,*,complete=True):
    directory=Path(directory);bound=profile.image_binding(image)
    opened=read(directory/'open.json');intent=read(directory/'start-intent.json')
    require(opened['image']==image and intent==dict(mode=profile.OPERATION,image=image,
        run_id_hex=image['run_id_hex'],nonce_sha256=opened['nonce_sha256'],open=pin(directory/'open.json'),
        endpoint=opened['acquisition']['endpoint'],deadline_ns=opened['deadline_ns']),
        'integrated original start binding differs')
    handle=raw.load_handle(directory/'session.capture.json')
    proof=protocol.replay(raw.read_stdout(handle,maximum=protocol.MAXIMUM),
        raw.read_stderr(handle,maximum=224),key=verify(image['key'],maximum=32).read_bytes(),
        run=bytes.fromhex(image['run_id_hex']),expected=bound['expected'],
        module_names=bound['module_names'],selection=read(verify(bound['handoff'])),complete=complete)
    require(proof['nonce_sha256']==opened['nonce_sha256'],'integrated nonce changed')
    result=dict(proof=proof,capture=pin(handle.receipt_path),intent=pin(directory/'start-intent.json'))
    if complete:
        require(handle.returncode==0 and not handle.timed_out and not handle.output_exceeded and
            handle.producer_error_type is None,'integrated raw producer incomplete')
        closed=read(directory/'close.json');acquisition=closed['acquisition']
        require(closed['open']==pin(directory/'open.json') and closed['error_type'] is None and
            acquisition['local_carrier'] is True and acquisition['close']['descriptor_closed'] is True and
            acquisition['close']['exclusive_release_errno'] in (None,5),
            'integrated descriptor closure differs')
        selected=proof['debian_handoff']
        for _,sequence,name,field in CONTINUATIONS:
            wanted=selected['root_transition']['proof'] if field=='proof' else selected[field]
            record=read(directory/(name+'.json'))
            require(record['intent']==result['intent'] and record['sequence']==sequence and record['proof']==wanted,
                'integrated continuation proof differs')
        release=read(directory/'release.json');departure=read(directory/'departure.json')
        require(departure['departed'] is True and departure['before']==read(verify(release['departure'])) and
            departure['deadline_ns']==release['departure_deadline_ns'] and
            departure['observed_ns']<departure['deadline_ns'],'integrated ACM departure unproved')
        result['departure']=pin(directory/'departure.json')
    return result


def observe(directory,image,host,*,guard,before_start,deadline_ns):
    bound=profile.image_binding(image);directory=Path(directory);directory.mkdir(mode=0o700)
    key=verify(image['key'],maximum=32).read_bytes();run=bytes.fromhex(image['run_id_hex'])
    nonce=secrets.token_bytes(32);state=protocol.Records(key,run,nonce,bound['expected'],
        bound['module_names'],read(verify(bound['handoff'])))
    writer=raw.RawCaptureWriter(directory,'session',stdout_maximum=protocol.MAXIMUM,stderr_maximum=224,
        stdout_name='rx.bin',stderr_name='tx.bin',argv0_name='fixed-debian-integrated-v1')
    deadline_ns=min(deadline_ns,clock()+360_000_000_000)
    acquisition=None;error=None;complete=False;pending=bytearray();sent=set();before=None;departure_deadline=None
    try:
        with host.open_native(image['run_id_hex'],before_open=guard,local_carrier=True) as (fd,acquisition):
            publish(directory/'open.json',dict(image=image,nonce_sha256=digest(nonce),acquisition=acquisition,
                deadline_ns=deadline_ns,started_ns=clock()))
            detail=dict(mode=profile.OPERATION,image=image,run_id_hex=image['run_id_hex'],nonce_sha256=digest(nonce),
                open=pin(directory/'open.json'),endpoint=acquisition['endpoint'],deadline_ns=deadline_ns)
            intent=publish(directory/'start-intent.json',detail)
            before_start(detail)
            def send(data):
                guard();require(clock()<deadline_ns,'integrated original host window expired')
                # The one durable effect intent already consumes an uncertain
                # write. Fsync intended raw bytes before every transmission.
                writer.write_stderr(data);os.fsync(writer.stream_fds()[1])
                require(os.write(fd,data)==len(data),'integrated short write; no replay')
            send(protocol.request(key,run,nonce))
            while not (state.handoff and state.handoff.released):
                # Collection stays within the original clock window. Reuse
                # successful immutable qualification during RX; the full
                # live guard runs again before every outgoing continuation.
                require(clock()<deadline_ns,'integrated host deadline expired')
                ready,_,_=select.select([fd],[],[],.1)
                if not ready:continue
                part=os.read(fd,4096);require(part,'integrated observer disconnected')
                writer.write_stdout(part);pending.extend(part)
                while len(pending)>=16:
                    size=int.from_bytes(pending[6:8],'little');require(size<=1023,'integrated frame bound')
                    if len(pending)<16+size:break
                    state.accept(protocol.frames.decode_frame(bytes(pending[:16+size])));del pending[:16+size]
                    if state.handoff:
                        require(state.handoff.stop is None,'integrated device stopped')
                        for kind,sequence,name,field in CONTINUATIONS:
                            proof=getattr(state.handoff,field)
                            if proof is None or kind in sent:continue
                            record=dict(intent=intent,sequence=sequence,proof=proof)
                            if name=='release':
                                before=target.usb_snapshot('usb:'+host.config['topology'],directory)
                                publish(directory/'departure-before.json',before)
                                departure_deadline=min(deadline_ns,clock()+30_000_000_000)
                                record.update(departure=pin(directory/'departure-before.json'),
                                    departure_deadline_ns=departure_deadline)
                            publish(directory/(name+'.json'),record)
                            send(protocol.handoff.encode(key,run,nonce,kind,sequence));sent.add(kind)
            require(not pending,'bytes follow integrated release');complete=True
    except BaseException as caught:error=caught
    finally:
        try:
            if (directory/'open.json').exists():
                publish(directory/'close.json',dict(open=pin(directory/'open.json'),acquisition=acquisition,
                    error_type=type(error).__name__ if error else None,protocol_complete=complete))
        except BaseException as caught:
            if error is None:error=caught
        finally:
            writer.finalize(returncode=0 if complete and error is None else None,timed_out=isinstance(error,TimeoutError),
                producer_error_type=type(error).__name__ if error else None)
    if error is not None:raise error
    publish(directory/'departure.json',target.wait_departure(before,directory,deadline_ns=departure_deadline,guard=guard))
    return rederive(directory,image)
