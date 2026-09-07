"""P364 fixed signed progress grammar; partial evidence grants no control."""
import hashlib,hmac,struct
import s22plus_fyg8_p364_return_spec as spec
RUN_ID=bytes.fromhex('c364f1e0a90b5e6d7c8a9b0c1d2e3f0b')
SCHEMA='s22plus_fyg8_p364_native_progress_v1'

class ProgressError(ValueError): pass
class TerminalReported(ProgressError): pass

class Progress:
    def __init__(self):
        self.records=[];self.cursor=0;self.failed=None;self.terminal=None;self.child=None
    def accept(self,frame,key,nonce):
        ordinal=len(self.records)
        if ordinal>=spec.MAX_DIAGNOSTIC_FRAMES or frame.frame_type!=spec.FRAME_DIAGNOSTIC or frame.sequence!=spec.DIAGNOSTIC_SEQUENCE_BASE+ordinal or len(frame.payload)!=40:
            raise ProgressError('progress framing/ordinal differs')
        body=frame.payload[:8]
        expected=hmac.new(key,spec.DIAGNOSTIC_DOMAIN+RUN_ID+nonce+struct.pack('<I',frame.sequence)+body,hashlib.sha256).digest()
        if not hmac.compare_digest(frame.payload[8:],expected):raise ProgressError('progress authentication differs')
        stage,event,reserved,code=struct.unpack('<HBBi',body)
        if reserved or stage not in spec.STAGES or self.terminal is not None:raise ProgressError('progress fields/terminal differs')
        if event==spec.TERMINAL:
            if stage!=255 or not -4095<=code<0 or not self.records or (self.failed is not None and self.failed['code']!=code):raise ProgressError('terminal error differs')
            self.terminal=code
        elif self.failed is not None:raise ProgressError('operation follows failure')
        elif event in (spec.CHILD_EXIT,spec.CHILD_SIGNAL):
            if stage!=43 or self.cursor!=len(spec.SUCCESS_EVENTS) or self.child is not None or not (0<=code<=255 if event==spec.CHILD_EXIT else 1<=code<=64):raise ProgressError('child state differs')
            self.child=dict(event=event,code=code)
        else:
            if self.cursor>=len(spec.SUCCESS_EVENTS) or (stage,event)!=spec.SUCCESS_EVENTS[self.cursor] or not (code==0 if event==spec.ENTER else -4095<=code<=0):raise ProgressError('progress stage/order/code differs')
            self.cursor+=1
            if code<0:self.failed=dict(stage=stage,code=code)
        self.records.append(dict(ordinal=ordinal,stage=stage,event=event,code=code))
        if event==spec.TERMINAL:raise TerminalReported('native terminal error reported')
    def ready_for_control(self):
        return self.cursor==len(spec.SUCCESS_EVENTS) and self.failed is None and self.terminal is None
    def projection(self):
        pending=[]
        for r in self.records:
            if r['event']==spec.ENTER:pending.append(r['stage'])
            elif r['event']==spec.RETURN:
                if not pending or pending[-1]!=r['stage']:raise ProgressError('stage nesting differs')
                pending.pop()
        return dict(records=list(self.records),reported_failure=self.failed,
            terminal_error=self.terminal,child_status=self.child,
            preparation_and_clone_returned=self.ready_for_control(),
            unreturned_stage=pending[-1] if pending and self.failed is None and self.terminal is None else None,
            unreturned_stage_meaning='return-not-observed-not-proved-hang')


def projection(audit=None):
    p=getattr(audit,'native_progress',None) or Progress()
    return dict(schema=SCHEMA,run_id_hex=RUN_ID.hex(),**p.projection(),
        authenticated=bool(getattr(audit,'authenticated',False)),
        kernel_boot_identity_verified=len(getattr(audit,'boot_id',b''))==32,
        parent_identity_verified=bool(getattr(audit,'parent_identity_verified',False)),
        display_frame_fully_written=bool(getattr(audit,'display_frame_fully_written',False)),
        full_candidate_qualification=False,authority_granted=False)


def validate_projection(value):
    if type(value) is not dict or set(value)!=set(projection()):raise ProgressError('progress projection fields differ')
    p=Progress()
    # Rebuild grammar independently of transport; raw replay separately checks MACs.
    key=b'v'*32;nonce=b'n'*32
    rows=value.get('records')
    if type(rows) is not list or len(rows)>spec.MAX_DIAGNOSTIC_FRAMES:raise ProgressError('progress record bound differs')
    for i,row in enumerate(rows):
        if type(row) is not dict or set(row)!={'ordinal','stage','event','code'} or any(type(row[k]) is not int for k in row) or row['ordinal']!=i:raise ProgressError('progress row differs')
        try:body=struct.pack('<HBBi',row['stage'],row['event'],0,row['code'])
        except struct.error as exc:raise ProgressError('progress numeric range differs') from exc
        seq=spec.DIAGNOSTIC_SEQUENCE_BASE+i
        tag=hmac.new(key,spec.DIAGNOSTIC_DOMAIN+RUN_ID+nonce+struct.pack('<I',seq)+body,hashlib.sha256).digest()
        frame=type('Frame',(),dict(frame_type=spec.FRAME_DIAGNOSTIC,sequence=seq,payload=body+tag))()
        try:p.accept(frame,key,nonce)
        except TerminalReported:
            if i!=len(rows)-1:raise ProgressError('bytes follow terminal progress')
    expected=dict(projection(),**p.projection())
    for k in ('authenticated','kernel_boot_identity_verified','parent_identity_verified','display_frame_fully_written'):
        if type(value[k]) is not bool:raise ProgressError('progress boolean differs')
        expected[k]=value[k]
    if value!=expected:raise ProgressError('progress projection differs')
    if rows and not all(value[k] for k in ('authenticated','kernel_boot_identity_verified','parent_identity_verified','display_frame_fully_written')):raise ProgressError('signed stage without complete prefix')
    return value
