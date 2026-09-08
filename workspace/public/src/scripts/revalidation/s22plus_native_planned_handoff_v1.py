"""One predeclared host tty handoff; no device command or retry implementation."""
from pathlib import Path
import time
import device_action_f1_v2 as core
from s22plus_fyg8_p363_return_host import stable_record,identity,_digest,host_boot_sha256
import s22plus_fyg8_p370_return_spec as spec

INTENT_NAME='p370-handoff-intent.json'
REOPEN_NAME='p370-handoff-reopen.json'
RUN_ID='c370f1e0a90b5e6d7c8a9b0c1d2e3f0b'
MIN_CLOSED_NS=200_000_000

class HandoffError(ValueError):pass

def exists(run):
    return any((Path(run)/n).exists() or (Path(run)/n).is_symlink() for n in (INTENT_NAME,REOPEN_NAME))

def _source():return identity(Path(__file__).read_bytes())

def _request(request):
    fixed=dict(run_id_hex=RUN_ID,mode='planned-handoff',sequence=5,
        boot_id_semantic=spec.BOOT_ID_SEMANTIC,boot_receipt_semantic=spec.BOOT_RECEIPT_SEMANTIC)
    if type(request) is not dict or set(request)!=set(fixed)|{'nonce_sha256','kernel_boot_identity_sha256'} or any(type(request[k]) is not type(v) or request[k]!=v for k,v in fixed.items()) or not all(_digest(request[k]) for k in ('nonce_sha256','kernel_boot_identity_sha256')):
        raise HandoffError('handoff request differs')

def write_intent(run,*,binding,request,endpoint_identity_sha256,lane):
    if exists(run):raise HandoffError('handoff intent exists; no replay')
    _request(request)
    if type(binding) is not dict or not binding or not _digest(endpoint_identity_sha256) or type(lane) is not dict or lane.get('accepted_for_p324') is not True:
        raise HandoffError('handoff binding differs')
    value=dict(schema='s22plus_planned_handoff_intent_v1',binding=binding,request=request,
        endpoint_identity_sha256=endpoint_identity_sha256,lane=lane,source=_source(),
        host_boot_sha256=host_boot_sha256(),created_monotonic_ns=time.monotonic_ns(),replay_forbidden=True)
    core._write_exclusive(Path(run)/INTENT_NAME,value)
    return read_intent(run,binding=binding)[1]

def read_intent(run,*,binding=None,proof=None):
    value,receipt=stable_record(Path(run)/INTENT_NAME)
    expected={'schema','binding','request','endpoint_identity_sha256','lane','source','host_boot_sha256','created_monotonic_ns','replay_forbidden'}
    if set(value)!=expected or value['schema']!='s22plus_planned_handoff_intent_v1' or value['replay_forbidden'] is not True or value['source']!=_source() or type(value['created_monotonic_ns']) is not int or value['created_monotonic_ns']<=0 or not _digest(value['endpoint_identity_sha256']) or not _digest(value['host_boot_sha256']) or type(value['lane']) is not dict or value['lane'].get('accepted_for_p324') is not True:
        raise HandoffError('handoff intent record differs')
    _request(value['request'])
    if binding is not None and value['binding']!=binding:raise HandoffError('handoff prepared binding differs')
    if proof is not None:
        first=proof['sessions'][0]
        if value['request']['nonce_sha256']!=first['nonce_sha256'] or value['request']['kernel_boot_identity_sha256']!=first['boot_id_sha256']:
            raise HandoffError('handoff first-leg join differs')
    return value,receipt

def write_reopen(run,*,binding,request,endpoint_identity_sha256,closed_ns,opened_ns,poll_count):
    intent,ir=read_intent(run,binding=binding)
    if request!=intent['request'] or endpoint_identity_sha256!=intent['endpoint_identity_sha256'] or intent['host_boot_sha256']!=host_boot_sha256():raise HandoffError('reopen identity differs')
    value=dict(schema='s22plus_planned_handoff_reopen_v1',binding=binding,intent=ir,
        endpoint_identity_sha256=endpoint_identity_sha256,closed_monotonic_ns=closed_ns,
        opened_monotonic_ns=opened_ns,poll_count=poll_count,close_completed=True,
        open_completed=True,reopen_count=1,exact_endpoint_before=True,exact_endpoint_during=True,
        exact_endpoint_after=True,host_boot_sha256=intent['host_boot_sha256'],source=_source())
    _validate_reopen(value,intent,ir,binding)
    core._write_exclusive(Path(run)/REOPEN_NAME,value)
    return read_reopen(run,binding=binding)[1]

def _validate_reopen(value,intent,ir,binding):
    fixed=dict(schema='s22plus_planned_handoff_reopen_v1',binding=binding,intent=ir,
        endpoint_identity_sha256=intent['endpoint_identity_sha256'],close_completed=True,
        open_completed=True,reopen_count=1,exact_endpoint_before=True,exact_endpoint_during=True,
        exact_endpoint_after=True,host_boot_sha256=intent['host_boot_sha256'],source=_source())
    if type(value) is not dict or set(value)!=set(fixed)|{'closed_monotonic_ns','opened_monotonic_ns','poll_count'} or any(type(value[k]) is not type(v) or value[k]!=v for k,v in fixed.items()):raise HandoffError('reopen record fields differ')
    if any(type(value[k]) is not int for k in ('closed_monotonic_ns','opened_monotonic_ns','poll_count')) or value['closed_monotonic_ns']<intent['created_monotonic_ns'] or value['opened_monotonic_ns']-value['closed_monotonic_ns']<MIN_CLOSED_NS or not 1<=value['poll_count']<=1200:
        raise HandoffError('reopen time/count differs')

def read_reopen(run,*,binding,proof=None):
    intent,ir=read_intent(run,binding=binding,proof=proof)
    value,receipt=stable_record(Path(run)/REOPEN_NAME);_validate_reopen(value,intent,ir,binding)
    return value,receipt

class PlannedHandoffObserverMixin:
    """Only the common observer owner may use this exact one-close/one-open path."""
    def _qualify_on_descriptor(self,codec,descriptor,writer,deadline):
        import os,fcntl,termios
        if exists(self.run_dir):raise HandoffError('handoff already exists; no new exchange')
        self._require_control_absent()
        def before_handoff(request):
            current=self.owned_descriptor
            if current is None or not self._endpoint_exact(self.endpoint,current):raise HandoffError('endpoint differs before handoff intent')
            lane=self._lane_supplement(True)
            self.handoff_intent_receipt=write_intent(self.run_dir,binding=dict(self.base.binding),request=request,
                endpoint_identity_sha256=self.endpoint.identity_sha256,lane=lane)
        def reopen(request):
            intent,_=read_intent(self.run_dir,binding=dict(self.base.binding))
            current=self.owned_descriptor
            if request!=intent['request'] or current is None or not self._endpoint_exact(self.endpoint,current) or deadline-time.monotonic()<=1:
                raise HandoffError('acknowledged handoff endpoint/deadline differs')
            fcntl.ioctl(current,termios.TIOCNXCL)
            # Ownership is relinquished before close; an uncertain close is never retried.
            self.owned_descriptor=None
            os.close(current);closed=time.monotonic_ns();polls=0
            until=closed+MIN_CLOSED_NS
            while time.monotonic_ns()<until:
                if time.monotonic()>=deadline or not self._endpoint_exact(self.endpoint):raise HandoffError('endpoint changed during planned close')
                polls+=1;time.sleep(min(.05,max(0,(until-time.monotonic_ns())/1e9)))
            if not self._endpoint_exact(self.endpoint) or time.monotonic()>=deadline:raise HandoffError('endpoint differs before one reopen')
            fd=os.open(self.base.dev_root/self.endpoint.tty_name,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC)
            self.owned_descriptor=fd
            fcntl.ioctl(fd,termios.TIOCEXCL)
            if not self._endpoint_exact(self.endpoint,fd):raise HandoffError('reopened endpoint differs')
            self.base._raw_tty(fd)
            self.handoff_reopen_receipt=write_reopen(self.run_dir,binding=dict(self.base.binding),request=request,
                endpoint_identity_sha256=self.endpoint.identity_sha256,closed_ns=closed,
                opened_ns=time.monotonic_ns(),poll_count=polls)
            return fd
        def before_control(request):
            current=self.owned_descriptor
            if current is None:raise HandoffError('reopened descriptor ownership missing')
            read_reopen(self.run_dir,binding=dict(self.base.binding))
            self._seal_control_intent(request,current)
        return self.qualification_observer.qualify(codec,descriptor,self.auth_key,None,set(),writer,
            deadline=deadline,before_handoff=before_handoff,reopen=reopen,before_control=before_control)
