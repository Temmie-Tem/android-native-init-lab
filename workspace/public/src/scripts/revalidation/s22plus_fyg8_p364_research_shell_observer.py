"""P364 diagnostic successor; source-bound H0 capability only."""
from s22plus_fyg8_p364_namespace import load
load(globals())

import s22plus_fyg8_p364_progress as progress
_progress_base_protocol=_protocol
_progress_base_live=_live
_progress_base_session=validate_session_result
_progress_base_qualification=validate_qualification


def _protocol(observer,key,read_bytes,write_frame,audit,*,before_control=None):
    audit.native_progress=progress.Progress()
    def read(size):
        while True:
            raw=read_bytes(size)
            if (size!=observer._CODEC.HEADER.size or raw[5]!=control.FRAME_DIAGNOSTIC
                    or audit.current_stage not in ('ten-submissions-and-return-ready-read','control-ack-read')):return raw
            length=observer._CODEC.HEADER.unpack(raw)[3]
            if length!=control.DIAGNOSTIC_PAYLOAD_SIZE:raise progress.ProgressError('diagnostic length differs')
            frame=observer._CODEC.decode_frame(raw+read_bytes(length))
            audit.native_progress.accept(frame,key,audit.nonce)
    def write(kind,sequence,payload):
        if kind==runtime.FRAME_EXEC and sequence==4:audit.parent_identity_verified=True
        write_frame(kind,sequence,payload)
        if kind==runtime.FRAME_EXEC and sequence==4:audit.display_frame_fully_written=True
    def intent(request):
        p=audit.native_progress
        if not p.ready_for_control():raise progress.ProgressError('incomplete diagnostic preparation before control')
        if audit.control_ready_body[3] and p.child is None:raise progress.ProgressError('early child exit has no signed status')
        if before_control is not None:before_control(request)
    return _progress_base_protocol(observer,key,read,write,audit,before_control=intent)


def _live(observer,descriptor,key,writer,deadline,*,before_control):
    try:return _progress_base_live(observer,descriptor,key,writer,deadline,before_control=before_control)
    except QualificationError as exc:
        exc.partial_receipt['native_progress']=progress.projection(exc.audit)
        raise


def validate_session_result(shell,step):
    row=_progress_base_session(shell,step)
    value=progress.projection(shell.session.audit)
    if not value['preparation_and_clone_returned']:raise QualificationError('P364 diagnostic prefix incomplete')
    row['native_progress']=progress.validate_projection(value)
    return row


def validate_qualification(value):
    if type(value) is not dict or type(value.get('sessions')) is not list or len(value['sessions'])!=1 or type(value['sessions'][0]) is not dict:
        raise QualificationError('P364 qualification shape differs')
    clean=copy.deepcopy(value)
    try:diag=clean['sessions'][0].pop('native_progress')
    except (KeyError,IndexError,TypeError) as exc:raise QualificationError('P364 qualification progress missing') from exc
    _progress_base_qualification(clean)
    progress.validate_projection(diag)
    if not diag['preparation_and_clone_returned']:raise QualificationError('P364 qualification progress incomplete')
    return copy.deepcopy(value)


def progress_projection(audit=None):return progress.projection(audit)


def replay_progress(observer,rx,tx,key):
    """Reparse the same prefix on success, terminal failure or partial transport."""
    audit=observer.ExchangeAudit(auth_key_sha256=hashlib.sha256(key).hexdigest())
    positions=[0,0]
    def read(size):
        part=rx[positions[0]:positions[0]+size];positions[0]+=len(part);audit.rx.extend(part)
        if len(part)!=size:raise EOFError('retained RX ended')
        return part
    def write(kind,sequence,payload):
        wire=observer._CODEC.encode_frame(kind,sequence,payload)
        part=tx[positions[1]:positions[1]+len(wire)]
        if part!=wire[:len(part)]:raise progress.ProgressError('retained TX differs')
        positions[1]+=len(part);audit.tx.extend(part)
        if len(part)!=len(wire):raise EOFError('retained TX ended')
    try:_protocol(observer,key,read,write,audit,before_control=lambda request:None)
    except (ValueError,EOFError):pass
    if positions!=[len(rx),len(tx)]:raise progress.ProgressError('unconsumed retained progress bytes')
    return progress.validate_projection(progress.projection(audit))


_progress_base_audit=audit_binding

def audit_binding():
    value=_progress_base_audit()
    value.update(authenticated_progress=True,diagnostic_frame_type=control.FRAME_DIAGNOSTIC,
        diagnostic_max_frames=control.MAX_DIAGNOSTIC_FRAMES,
        diagnostic_payload_size=control.DIAGNOSTIC_PAYLOAD_SIZE,
        partial_progress_raw_replay=True)
    return value
