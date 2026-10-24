"""Authenticated bounded local Debian history, independent of USB delivery."""
import errno
import hashlib
import hmac
import os
import re
import struct
from s22plus_native_records_v3 import require

DOMAIN=b'S22PLUS-FYG8-DEBIAN-DURABLE-v1'
HEADER,RECORD,RECORDS=256,128,120
MAXIMUM=HEADER+RECORD*RECORDS
REPORT_MS=500
NAMES=('INIT','START','PROGRESS','BOUNDARY','REPORT_LOST','COMPLETE','RELEASE','STOP')
INIT,START,PROGRESS,BOUNDARY,REPORT_LOST,COMPLETE,RELEASE,STOP=range(1,9)


def binding(run):
    require(type(run) is str and re.fullmatch('[0-9a-f]{32}',run),'durable run identity differs')
    return dict(schema='s22plus-debian-durable-v1',path='/var/lib/lab/s22-evidence-'+run,
        mode=0o100600,uid=0,gid=0,links=1,header_bytes=HEADER,record_bytes=RECORD,
        maximum_records=RECORDS,maximum_bytes=MAXIMUM,report_milliseconds=REPORT_MS,
        exclusive_create=True,checked_file_sync=True,checked_parent_sync=True,
        report_loss_requires_started=True,report_loss_sticky=True,reopen_after_loss=False,
        autonomous_release=False)


def wire_seal():
    constants=dict(HEADER=HEADER,RECORD=RECORD,RECORDS=RECORDS,MAXIMUM=MAXIMUM,REPORT_MS=REPORT_MS,
        **{name:i for i,name in enumerate(NAMES,1)})
    return ''.join(f'#define DE_{name} {n}U\n' for name,n in constants.items()).encode()


def seal(run):
    value=binding(run)
    return wire_seal()+(
        'static const char dh_evidence_name[]="'+value['path'].rsplit('/',1)[1]+'";\n').encode()


def tag(key,body,*,autoboot=False,reboot=False):
    domain=b'S22PLUS-FYG8-DEBIAN-AUTO-DURABLE-v1' if autoboot else DOMAIN
    if reboot:
        from s22plus_debian_reboot_v1 import DURABLE_DOMAIN
        require(autoboot,'reboot durable domain requires automatic startup');domain=DURABLE_DOMAIN
    return hmac.new(key,domain+body,hashlib.sha256).digest()


class Chain:
    def __init__(self,first_tag,*,autoboot=False,single_cpu=False,reboot=None):
        self.tag=first_tag;self.rows=[];self.started=False;self.off=False;self.complete=False
        self.released=False;self.stopped=False;self.progress=[];self.boundaries=[];self.elapsed=0
        self.autoboot=autoboot
        require(not single_cpu or autoboot,'single CPU evidence requires automatic startup')
        self.single_cpu=single_cpu
        self.reboot=reboot;self.control=None

    def append(self,raw,key):
        require(len(raw)==RECORD and raw[:8]==b'S22DER1\0','durable record framing differs')
        seq,kind,elapsed,phase,event,a,b,c,flags,reserved=struct.unpack_from('<IIQIIQQQII',raw,8)
        require(seq==len(self.rows)<RECORDS and not reserved and flags==int(self.off) and not self.stopped and self.control is None and
            self.elapsed<=elapsed<300000 and raw[64:96]==self.tag and hmac.compare_digest(raw[96:],tag(key,raw[:96],autoboot=self.autoboot,reboot=self.reboot is not None)),
            'durable record sequence, deadline, state or authentication differs')
        row=dict(sequence=seq,kind=kind,name=NAMES[kind-1] if kind in range(1,9) else 'UNKNOWN',
            elapsed_ms=elapsed,phase=phase,event=event,a=a,b=b,c=c,report_disabled=bool(flags))
        if kind==INIT:
            require(seq==0 and (phase,event,a,b,c)==(0,0,1,0,0),'durable init fact differs')
        elif kind==START:
            require(seq==1 and not self.started and (phase,event,a,b,c)==(0,0,8,0,0),'durable START is out of order')
            self.started=True
        elif kind==REPORT_LOST:
            require(not self.autoboot,'automatic record cannot claim transport loss')
            require(self.started and not self.off and not self.released and phase<=2 and not event,
                'durable reporting loss phase differs')
            last=self.rows[-1]
            if b==0:
                require(c==0 and a in (errno.ENOENT,errno.EIO,errno.ENODEV,errno.ENXIO) and
                    (phase==1 and ((not self.progress and last['kind']==START) or
                        (len(self.progress)==1 and last['kind']==BOUNDARY and last['event']==1)) or
                     phase==2 and len(self.progress)==2 and last['kind']==PROGRESS),
                    'durable open loss is unclassified or out of order')
            else:
                require(a in (errno.EIO,errno.ENODEV,errno.ENXIO,errno.EPIPE,errno.ECONNRESET,errno.ETIMEDOUT),
                    'durable send loss is not a reporting error')
                if b==175:require(phase==0 and c==8 and last['kind']==START,'START ACK loss differs')
                elif b==176:
                    require(last['kind']==PROGRESS and phase==(1 if len(self.progress)<=2 else 2) and
                        c==2000+len(self.progress)-1,'progress loss differs from preceding event')
                elif b==177:
                    prior=[r for r in self.boundaries if r['phase']==phase]
                    require(last['kind']==BOUNDARY and phase in (1,2) and phase==last['phase'] and
                        c==(3000 if phase==1 else 3100)+len(prior)-1,'boundary loss differs from preceding event')
                else:require(False,'unknown reporting loss operation')
            self.off=True
        elif kind==PROGRESS:
            ordinal=len(self.progress);expected=ordinal+1 if ordinal<3 else 4
            require(self.started and not self.complete and ordinal<15 and phase==expected and
                event==(0 if ordinal<3 else ordinal-2) and
                (c==257 if self.single_cpu else c==0) and
                ((a==b==0) if ordinal<2 else b==3 and event*10000<=a<=event*10000+10000 and a<=elapsed and
                    (ordinal<3 or a>self.progress[-1]['a'])),
                'durable progress accounting differs')
            if ordinal in (1,2):
                prior=[r for r in self.boundaries if r['phase']==ordinal]
                require(prior and prior[-1]['event']==5 and prior[-1]['b']==0,'local completion lacks successful child')
            self.progress.append(row)
            if self.single_cpu:
                row['platform']=dict(online_cpus=[0],watchdog_driver_enabled=True,
                    hardware_pet_proved=False)
        elif kind==BOUNDARY:
            require(self.started and not self.complete and phase in (1,2) and len(self.progress)==phase,
                'durable boundary phase differs')
            prior=[r for r in self.boundaries if r['phase']==phase];last=prior[-1]['event'] if prior else 0
            allowed={0:(1,) if phase==1 else (2,),1:(2,),2:(3,),3:(4,5),4:(4,5),5:()}
            require(len(prior)<40 and event in allowed[last] and
                ((a==b==0) if event<=2 else 1<a<=2147483647 and b<=65535 and (event==5 or b==0)),
                'durable boundary ordering or child differs')
            if phase==1 and event==2:
                require((c==0) if self.off else prior[-1]['elapsed_ms']<=c<=elapsed,'local close-return differs')
            else:require(c==0,'unexpected local close-return value')
            if event>=4:
                require(a==prior[-1]['a'] and (event!=4 or elapsed-prior[-1]['elapsed_ms']>=10000),
                    'local wait child or sample timing differs')
            row['reporting_reopened']=event==2 and not self.off and not self.autoboot
            self.boundaries.append(row)
        elif kind==COMPLETE:
            require(self.started and not self.complete and len(self.progress)==15 and (phase,event,a,b,c)==(0,0,0,0,0),
                'durable local completion precedes full service proof')
            self.complete=True
        elif kind==RELEASE:
            require(not self.autoboot,'automatic record cannot claim host release')
            require(self.complete and not self.off and not self.released and (phase,event,a,b,c)==(0,0,9,0,0),
                'durable release lacks ordered host-authorized boundary')
            self.released=True
        elif kind in (9,10) and self.reboot is not None:
            wanted=1 if kind==9 else 2
            require(self.complete and not self.off and not self.released and
                self.reboot['phase']==wanted and (phase,event,a,b,c)==
                (wanted,0,self.reboot['initial_mount_count'],self.reboot['initial_mount_count']+2*wanted,0),
                'reboot control intent is not the selected completed phase')
            row['name']='REBOOT_INTENT' if kind==9 else 'SHUTDOWN_INTENT';self.control=kind
        elif kind==STOP:
            require(seq>0 and not phase and not event and 0<a<=4095 and b==8 and not c,'durable stop differs')
            self.stopped=True
        else:require(False,'unknown durable event')
        self.tag=raw[96:];self.elapsed=elapsed;self.rows.append(row)


def decode(data,key,expected,*,allow_prefix=False,autoboot=False,single_cpu=False,reboot=None):
    """Expected identity comes from the retained qualified image/authenticated run.

    A valid historical prefix can survive a later malformed/torn tail. It
    grants no continuation and does not claim complete file or host delivery.
    """
    require(not single_cpu or autoboot,'single CPU evidence requires automatic startup')
    if reboot is not None:
        from s22plus_debian_reboot_v1 import PHASES,count as mount_count
        require(autoboot and single_cpu and set(reboot)=={'phase','initial_mount_count'} and
            type(reboot['phase']) is int and reboot['phase'] in PHASES,'durable reboot selection differs')
        mount_count(reboot['initial_mount_count'])
    require(type(data) is bytes and HEADER<=len(data)<=MAXIMUM and len(key)==32 and
        hashlib.sha256(key).hexdigest()==expected['key_sha256'],
        'durable file size or key differs')
    h=data[:HEADER]
    require(h[:8]==b'S22DE01\0' and struct.unpack_from('<II',h,8)==(1,HEADER) and
        struct.unpack_from('<4I',h,112)==(7 if reboot is not None else 6 if single_cpu else 5 if autoboot else 4,RECORD,RECORDS,MAXIMUM) and
        (struct.unpack_from('<3I',h,200)==(reboot['phase'],reboot['initial_mount_count'],reboot['initial_mount_count']+2*reboot['phase'])
            and not any(h[212:224]) if reboot is not None else not any(h[200:224])) and
        hmac.compare_digest(h[224:],tag(key,h[:224],autoboot=autoboot,reboot=reboot is not None)),
        'durable header authentication or shape differs')
    origin,deadline=struct.unpack_from('<QQ',h,96);device=struct.unpack_from('<Q',h,192)[0]
    require(deadline>=300000 and deadline-origin==300000 and h[16:32].hex()==expected['run_id_hex'] and
        h[32:64].hex()==expected['boot'] and hashlib.sha256(h[64:96]).hexdigest()==expected['nonce_sha256'] and
        h[128:160].hex()==expected['init_sha256'] and h[160:192].hex()==expected['hook_sha256'] and
        device==os.makedev(expected['root_device']['major'],expected['root_device']['minor']),
        'durable identity does not join retained run/boot/init/root')
    require(not autoboot or (origin,deadline)==(0,300000),'automatic deadline was renewed')
    chain=Chain(h[224:],autoboot=autoboot,single_cpu=single_cpu,reboot=reboot);error=None;pos=HEADER
    while pos<len(data):
        try:chain.append(data[pos:pos+RECORD],key)
        except ValueError as failure:
            if not allow_prefix:raise
            error=str(failure);break
        pos+=RECORD
    result=dict(schema='s22plus-debian-durable-projection-v1',status='AUTHENTICATED_PREFIX_ONLY' if error else 'AUTHENTICATED_HISTORY',
        run_id_hex=expected['run_id_hex'],boot=expected['boot'],origin_ms=origin,deadline_ms=deadline,
        records=chain.rows,valid_prefix_bytes=pos,complete_framing=error is None,tail_error=error,
        local_init_observed=bool(chain.rows),start_authenticated=chain.started,report_disabled=chain.off,
        rcs_completed=len(chain.progress)>=2,runlevel_completed=len(chain.progress)>=3,
        local_runtime_proved=chain.complete,release_authenticated=chain.released,required_check_stopped=chain.stopped,
        host_receipt_proved=False,ssh_access_proved=False,clean_shutdown_proved=False,replay_authorized=False,
        raw=dict(size=len(data),sha256=hashlib.sha256(data).hexdigest()))
    if autoboot:
        result.update(schema='s22plus-debian-autoboot-durable-projection-v1',automatic_start=chain.started,
            start_authenticated=False,release_authenticated=False)
    if single_cpu:
        result['single_cpu']=dict(sample_count=len(chain.progress),
            cpu0_and_enabled_watchdog_at_all_samples=bool(chain.progress),
            service_window_120_seconds=chain.complete,hardware_pet_proved=False,
            continuous_cpu_online_proved=False)
    if reboot is not None:
        result.update(schema='s22plus-debian-reboot-durable-projection-v1',
            reboot_phase=dict(reboot,installed_mount_count=reboot['initial_mount_count']+2*reboot['phase']),
            reboot_intent=chain.control==9,shutdown_intent=chain.control==10)
    return result
