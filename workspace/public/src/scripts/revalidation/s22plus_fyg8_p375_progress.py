"""Signed P375 Download preparation and root RAM workspace witnesses."""
import hashlib
import hmac
import struct
import s22plus_fyg8_p375_research_shell_runtime as runtime

DOMAIN=b'S22PLUS-FYG8-P375-PROGRESS-v1'
EXPECTED=[(1,0)]
for index in range(5):
    if index==4:
        for stage in (30,31,32):EXPECTED.extend(((stage,0),(stage,1)))
    for stage in range(10+3*index,13+3*index):EXPECTED.extend(((stage,0),(stage,1)))
EXPECTED.extend(((33,0),(33,1),(1,1)))
for stage in (60,61,62):EXPECTED.extend(((stage,0),(stage,1)))
EXPECTED=tuple(EXPECTED)


class Progress:
    def __init__(self):self.records=[];self.failure=None

    def accept(self, frame, key, nonce):
        payload=frame.payload
        if frame.frame_type!=0x8b or frame.sequence!=0x100+len(self.records) or len(payload)!=40:
            raise ValueError('P375 progress frame/ordinal differs')
        expected=hmac.digest(key,DOMAIN+runtime.P375_RUN_ID+nonce+struct.pack('<I',frame.sequence)+payload[:8],'sha256')
        if not hmac.compare_digest(expected,payload[8:]):raise ValueError('P375 progress authentication differs')
        stage,event,reserved,code=struct.unpack('<HBBi',payload[:8])
        if reserved or event not in (0,1,4) or not -4095<=code<=0:
            raise ValueError('P375 progress fields differ')
        if event==4:
            if stage!=255 or not code or self.failure is None:raise ValueError('unjoined terminal preparation error')
        else:
            if self.failure is not None or len(self.records)>=len(EXPECTED) or (stage,event)!=EXPECTED[len(self.records)]:
                raise ValueError('P375 preparation order differs')
            if event==0 and code:raise ValueError('ENTER carries a return value')
            if code:self.failure=dict(stage=stage,code=code)
        self.records.append(dict(stage=stage,event=event,code=code))

    def ready(self):
        return len(self.records)==len(EXPECTED) and self.failure is None

    def projection(self):
        return dict(schema='s22plus-fyg8-p375-preparation-progress-v1',
                    records=list(self.records),failure=self.failure,complete=self.ready())
