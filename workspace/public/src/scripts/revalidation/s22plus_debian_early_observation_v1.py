"""Exact-endpoint one-challenge observation; no native console or CONTROL."""
import os
from pathlib import Path
import select
import secrets

import device_action_raw_capture_v1 as raw
import s22plus_debian_early_profile_v1 as profile
import s22plus_debian_early_protocol_v1 as protocol
from s22plus_native_records_v3 import clock,pin,publish,read,require,verify


def rederive(directory,image):
    directory=Path(directory);bound=profile.image_binding(image)
    opened=read(directory/'open.json');closed=read(directory/'close.json')
    require(opened['image']==image and closed['open']==pin(directory/'open.json') and closed['error_type'] is None,
        'early observer context or completion differs')
    require(closed['acquisition']['local_carrier'] is True and
        closed['acquisition']['close']['descriptor_closed'] is True and
        closed['acquisition']['close']['exclusive_release_errno'] is None,'early tty close was not complete')
    handle=raw.load_handle(directory/'session.capture.json')
    require(handle.returncode==0 and not handle.timed_out and not handle.output_exceeded and
        handle.producer_error_type is None,'early raw producer did not complete')
    rx=raw.read_stdout(handle,maximum=protocol.MAXIMUM);tx=raw.read_stderr(handle,maximum=80)
    proof=protocol.replay(rx,tx,key=verify(image['key'],maximum=32).read_bytes(),run=bytes.fromhex(image['run_id_hex']),
        expected=bound['expected'],module_names=bound['module_names'])
    require(proof['nonce_sha256']==opened['nonce_sha256'],'early challenge changed')
    return dict(proof=proof,capture=pin(handle.receipt_path),open=pin(directory/'open.json'),close=pin(directory/'close.json'))


def observe(directory,image,host,*,guard,deadline_ns):
    from s22plus_native_records_v3 import digest
    bound=profile.image_binding(image)
    directory=Path(directory);directory.mkdir(mode=0o700)
    nonce=secrets.token_bytes(32);key=verify(image['key'],maximum=32).read_bytes();run=bytes.fromhex(image['run_id_hex'])
    tx=protocol.request(key,run,nonce);rx=bytearray();pending=bytearray();state=protocol.Records(key,run,nonce,bound['expected'],bound['module_names'])
    writer=raw.RawCaptureWriter(directory,'session',stdout_maximum=protocol.MAXIMUM,stderr_maximum=80,
        stdout_name='rx.bin',stderr_name='tx.bin',argv0_name='fixed-debian-early-observation-v1')
    acquisition=None;error=None;complete=False
    deadline_ns=min(deadline_ns,clock()+60_000_000_000)
    try:
        with host.open_native(image['run_id_hex'],before_open=guard,local_carrier=True) as (fd,acquisition):
            publish(directory/'open.json',dict(image=image,nonce_sha256=digest(nonce),acquisition=acquisition,
                deadline_ns=deadline_ns,started_ns=clock()))
            guard()
            # Capture before transmission; finalization fsyncs both streams.
            # The durable step-start already forbids replay after interruption.
            # A short write is an uncertain request, never a reason to resend.
            writer.write_stderr(tx)
            written=os.write(fd,tx);require(written==len(tx),'early request short write; no retry')
            while not state.complete:
                guard()
                if clock()>=deadline_ns:raise TimeoutError('early observation deadline')
                readable,_,_=select.select([fd],[],[],.1)
                if not readable:continue
                part=os.read(fd,4096)
                if not part:raise EOFError('early observer disconnected')
                writer.write_stdout(part);rx.extend(part);pending.extend(part)
                require(len(rx)<=protocol.MAXIMUM,'early output bound')
                while len(pending)>=16:
                    size=int.from_bytes(pending[6:8],'little');require(size<=800,'early frame size')
                    if len(pending)<16+size:break
                    state.accept(protocol.frames.decode_frame(bytes(pending[:16+size])));del pending[:16+size]
            require(not pending,'bytes follow early terminal');complete=True
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
    return rederive(directory,image)
