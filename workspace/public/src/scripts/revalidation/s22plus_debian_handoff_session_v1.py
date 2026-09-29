"""V3 graph for one installed-Debian boot and attended original-A return."""
import s22plus_debian_handoff_profile_v1 as profile
import s22plus_debian_access_v1 as access
from device_action_raw_capture_v1 import RawCaptureError
from s22plus_native_records_v3 import Journal,SessionError,clock,digest,pin,publish,read,require,verify


def normal_steps():
    from s22plus_native_session_v3 import Step
    return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
        Step('debian-handoff','observe','N','handoff'),Step('debian-health','debian-health','N'),
        Step('debian-shutdown','debian-shutdown','N'),Step('install-android','transfer','A'),Step('android-final','health','A'))


def validate_task(task,*,recovery):
    require(set(task['debian_access'])=={'link','client_key','known_hosts','nmcli','ssh','root_run_id','network_uuid'} and
        task['seconds']==3600,
        'Debian access scope or original window differs')
    if not recovery:require(task['debian_access']==access.inputs(task['N']['run_id_hex']),'Debian access provenance differs')


def intents(adapter,name):
    return [row['data'] for row in Journal(adapter.directory/'journal').rows()
        if row['event']=='effect-intent' and row['data']['step']==name]


def validate_result(adapter,step,value,request):
    if step.name=='debian-handoff':
        proof=value['proof'];folder=adapter.folder(step.name);records=intents(adapter,step.name)
        require(len(records)==1,'Debian handoff lacks unique compound intent')
        original=records[0]['detail'];selected=proof['debian_handoff']
        require(original==read(folder/'transition-intent.json') and original['mode']=='debian-handoff' and
            original['sequence']==5 and original['body_sha256']==digest(b'') and
            original['run_id_hex']==request['N']['run_id_hex'] and original['nonce_sha256']==proof['nonce_sha256'] and
            original['kernel_boot_identity_sha256']==proof['kernel_boot_identity_sha256'] and
            selected['status']=='PASS_INSTALLED_DEBIAN_PID1' and selected['continue_accepted'] is True and
            selected['acm_release_accepted'] is True,'Debian handoff proof does not join original effect')
        continued=read(folder/'debian-init-continue.json');released=read(folder/'debian-acm-release.json')
        require(continued==dict(transition=pin(folder/'transition-intent.json'),request=dict(original,
            mode='debian-init-continue',sequence=6,root_proof=selected['root_transition']['proof'])) and
            released['transition']==pin(folder/'transition-intent.json') and released['request']==dict(original,
            mode='debian-acm-release',sequence=7,init_proof=selected['init_proof']),
            'Debian continuation is not bound to its original proof')
        departure=read(verify(value['departure']))
        require(departure['departed'] is True and departure['before']==read(verify(released['departure'])) and
            departure['deadline_ns']==released['departure_deadline_ns'] and
            departure['observed_ns']<departure['deadline_ns'],'original ACM departure is not proved')
    elif step.action=='debian-health':require(value==access.Access(adapter,request).rederive_health(),'SSH health differs')
    elif step.action=='debian-shutdown':
        require(value==access.Access(adapter,request).rederive_shutdown(),'shutdown proof differs')
        rows=intents(adapter,step.name)
        require(len(rows)==1 and rows[0]['detail']==read(adapter.folder(step.name)/'intent.json'),
            'Debian shutdown lacks one original intent')


def terminal(adapter,request,*,recovered):
    from s22plus_native_observation_v3 import switch_prefix
    result=dict(status='NO_PROOF',debian_boot_proved=False,ssh_access_proved=False,
        clean_shutdown_proved=False,normal_return=not recovered,replay_authorized=False)
    try:
        original=read(adapter.folder('debian-handoff')/'transition-intent.json')
        rows=intents(adapter,'debian-handoff');require(len(rows)==1 and rows[0]['detail']==original,'missing compound intent')
        value=switch_prefix(adapter.folder('debian-handoff'),request['N'])
        require(value['nonce_sha256']==original['nonce_sha256'] and
            value['kernel_boot_identity_sha256']==original['kernel_boot_identity_sha256'],'handoff prefix identity differs')
        result['native_observation']=value['debian_handoff']
        if value['debian_handoff']['init_proof'] is not None:
            result.update(status='PASS_INSTALLED_DEBIAN_PID1',debian_boot_proved=True)
        healthy=access.Access(adapter,request).rederive_health()
        result.update(status='PASS_DEBIAN_PID1_AND_SSH',ssh_access_proved=True,ssh_health=healthy['health'])
    except (ValueError,OSError,KeyError,RawCaptureError) as error:
        result['evidence_error']=dict(type=type(error).__name__,message=str(error)[:256])
    return result


class Coordinator:
    def __init__(self,session):self.session=session

    def walk(self,*,allow_return):
        session=self.session
        for step in normal_steps():
            session.check()
            matches=[row for row in session.rows() if row['event']=='step-complete' and row['data']['step']==step.name]
            if matches:
                require(len(matches)==1,'duplicate Debian step completion')
                session.adapter.validate_result(step,read(verify(matches[0]['data']['result'])),session.request);continue
            if step.name=='install-android' and not allow_return:
                now=clock()
                receipt=publish(session.directory/'debian-return-ready.json',dict(operation=pin(session.directory/'operation.json'),
                    shutdown=pin(session.directory/'debian-shutdown.json'),requested_ns=now,
                    deadline_ns=min(session.grant['deadline_ns'],now+600_000_000_000)))
                return dict(state='AWAITING_PHYSICAL_DOWNLOAD',request=receipt,owner_retained=True,
                    next_action='Enter Download on the bound S22+; continue checks its exact endpoint before one original A transfer.')
            started=any(row['event']=='step-start' and row['data']['step']==step.name for row in session.rows())
            if started and step.action!='health':session.result(step,session.adapter.recover_step_result(step,session.request))
            else:session.perform(step)
        return None

    def stopped(self,error):
        from s22plus_native_session_v3 import ResultPublicationError
        session=self.session
        if isinstance(error,ResultPublicationError) or getattr(error,'protocol_completed',False):raise error
        session.journal.append('stopped',error_type=type(error).__name__,effect_intended=session.has_effect())
        if not session.has_recovery_basis():return session.close_unused()
        access.cleanup(session.adapter,session.request)
        return dict(state='AWAITING_ATTENDED_RECOVERY',recovery_required=True,owner_retained=True,
            device_activity='UNKNOWN',next_action='Use the original attended Download/A recovery; no handoff or SSH control replay.')

    def execute(self,*,attended):
        from s22plus_native_session_v3 import registry
        session=self.session
        with registry.target_session_lease(session.root):
            require(attended is True,'installed Debian handoff requires actual attendance')
            require(not session.rows() and not session.unused(),'Debian operation already started')
            session.check();registry.require_no_f1_owner(session.root)
            try:
                session.adapter.preflight(session.request,guard=lambda:session.check())
                session.journal.append('preflight-complete');pending=self.walk(allow_return=False)
            except Exception as error:return self.stopped(error)
            return pending if pending else session.close(normal_steps())

    def resume(self,*,attended,operator_statement=None):
        from s22plus_native_session_v3 import registry
        session=self.session
        with registry.target_session_lease(session.root):
            require(attended is True,'Debian original-A return requires actual attendance')
            session.check();registry.require_f1_owner(session.root,session.directory,session.binding)
            require(not any(row['event']=='stopped' for row in session.rows()) and
                not (session.directory/'terminal.json').exists(),'Debian normal work stopped or closed')
            pending=read(session.directory/'debian-return-ready.json')
            require(pending['operation']==pin(session.directory/'operation.json') and
                pending['shutdown']==pin(session.directory/'debian-shutdown.json'),'physical return request differs')
            try:result=self.walk(allow_return=True)
            except Exception as error:return self.stopped(error)
            require(result is None,'unexpected second physical pause');return session.close(normal_steps())
