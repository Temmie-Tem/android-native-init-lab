"""P369 fixed display-wait experiment; no device authority."""
from s22plus_fyg8_p369_namespace import load
load(globals())

_BaseProgress=Progress

class Progress(_BaseProgress):
    def __init__(self):
        super().__init__();self.wait_checkpoint=None
    def accept(self,frame,key,nonce):
        if self.wait_checkpoint is not None:raise ProgressError('record after control checkpoint')
        if len(frame.payload)==40 and frame.payload[2]==spec.WAIT_CHECK:
            ordinal=len(self.records)
            if (ordinal>=spec.MAX_DIAGNOSTIC_FRAMES or frame.frame_type!=spec.FRAME_DIAGNOSTIC
                    or frame.sequence!=spec.DIAGNOSTIC_SEQUENCE_BASE+ordinal):
                raise ProgressError('wait checkpoint framing differs')
            body=frame.payload[:8]
            tag=hmac.new(key,spec.DIAGNOSTIC_DOMAIN+RUN_ID+nonce+struct.pack('<I',frame.sequence)+body,hashlib.sha256).digest()
            if not hmac.compare_digest(frame.payload[8:],tag):raise ProgressError('wait checkpoint authentication differs')
            stage,event,reserved,code=struct.unpack('<HBBi',body)
            if (stage!=spec.WAIT_CHECK_STAGE or reserved or not self.ready_for_control()
                    or not 0<=code<=127 or (code&15)>10 or (code&32 and not code&16)
                    or (self.child is not None and code&64)):
                raise ProgressError('wait checkpoint fields differ')
            self.wait_checkpoint=dict(submitted_swaps=code&15,exact_wait_marker=bool(code&16),
                marker_age_at_least_two_seconds=bool(code&32),child_unreaped_at_control=bool(code&64))
            self.records.append(dict(ordinal=ordinal,stage=stage,event=event,code=code))
            return
        return super().accept(frame,key,nonce)
    def projection(self):
        return dict(super().projection(),wait_checkpoint=self.wait_checkpoint)
