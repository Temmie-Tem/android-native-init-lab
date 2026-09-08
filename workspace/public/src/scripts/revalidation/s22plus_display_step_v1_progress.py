"""Reinterpret the new variant's declared step checkpoint, never old wait evidence."""
class Progress(_BaseProgress):
    def __init__(self):
        super().__init__();self.step_checkpoint=None

    def accept(self,frame,key,nonce):
        if self.step_checkpoint is not None:raise ProgressError('record after step checkpoint')
        if len(frame.payload)==40 and frame.payload[2]==spec.WAIT_CHECK:
            ordinal=len(self.records)
            if ordinal>=spec.MAX_DIAGNOSTIC_FRAMES or frame.frame_type!=spec.FRAME_DIAGNOSTIC or frame.sequence!=spec.DIAGNOSTIC_SEQUENCE_BASE+ordinal:
                raise ProgressError('step checkpoint framing differs')
            body=frame.payload[:8]
            tag=hmac.new(key,spec.DIAGNOSTIC_DOMAIN+RUN_ID+nonce+struct.pack('<I',frame.sequence)+body,hashlib.sha256).digest()
            if not hmac.compare_digest(frame.payload[8:],tag):raise ProgressError('step checkpoint authentication differs')
            stage,event,reserved,code=struct.unpack('<HBBi',body)
            complete=code&3;started=(code>>2)&3
            if stage!=spec.WAIT_CHECK_STAGE or reserved or not self.ready_for_control() or not 0<=code<=127 or not 0<=complete<=started<=_STEP_MAX or (self.child is not None and code&64):
                raise ProgressError('step checkpoint fields differ')
            self.step_checkpoint=dict(completed_steps=complete,started_steps=started,pending=bool(code&16),failed=bool(code&32),child_unreaped_at_control=bool(code&64))
            self.records.append(dict(ordinal=ordinal,stage=stage,event=event,code=code));return
        return super().accept(frame,key,nonce)

    def projection(self):return dict(super().projection(),step_checkpoint=self.step_checkpoint)
