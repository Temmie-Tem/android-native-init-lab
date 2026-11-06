"""Mainline observation using the existing one-shot Session and physical return."""
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_access_v1 as access
import s22plus_mainline_download_access_v1 as download
from s22plus_debian_handoff_session_v1 import Coordinator as PhysicalCoordinator
from s22plus_native_records_v3 import Journal,pin,read,require,verify
from device_action_raw_capture_v1 import RawCaptureError


def normal_steps(request=None):
    from s22plus_native_session_v3 import Step
    return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
        Step(profile.SELECTION,download.ACTION if request is not None and download.selected(request) else 'mainline-evidence','N'),Step('install-android','transfer','A'),
        Step('android-final','health','A'))


def validate_result(adapter,step,value,request):
    if step.name!=profile.SELECTION:return
    expected=('AUTHENTICATED_DEBIAN_SYSVINIT_RAM_OBSERVATION' if 'debian_ram' in request['N']
              else 'AUTHENTICATED_CANARY_OBSERVATION')
    selected=download.selected(request)
    require(step.action==(download.ACTION if selected else 'mainline-evidence') and
            value==(download.rederive(adapter,request) if selected else access.rederive(adapter,request)) and
            value['proof']['status']==expected, 'mainline raw proof differs')
    rows=Journal(adapter.directory/'journal').rows()
    require(sum(row['event']=='effect-intent' and row['data']['step']=='install-native-first' for row in rows)==1 and
            sum(row['event']=='effect-intent' and row['data']['step']==step.name for row in rows)==int(selected),
            'mainline observation does not follow one candidate transfer')


def return_request(adapter,request):
    if download.selected(request):return download.return_request(adapter,request)
    ready=read(adapter.directory/Coordinator.READY_FILE)
    value=access.rederive(adapter,request)
    require(ready['operation']==pin(adapter.directory/'operation.json') and
            ready['observation']==pin(adapter.directory/(profile.SELECTION+'.json')) and
            read(verify(ready['observation']))==value and
            ready['deadline_ns']<=read(verify(request['grant']))['deadline_ns'] and
            0<ready['deadline_ns']-ready['requested_ns']<=600_000_000_000,
            'mainline physical return request differs')
    return ready


def arrival_deadline(adapter,step,request):
    if step.name=='install-android':return return_request(adapter,request)['deadline_ns']
    require(step.name=='install-native-first','unselected mainline normal transfer')
    rows=[r['data'] for r in Journal(adapter.directory/'journal').rows() if r['event']=='effect-intent']
    require(len(rows)==1 and rows[0]['step']=='android-download' and rows[0]['action']=='download',
            'mainline candidate lacks its original Android Download intent')
    return rows[0]['detail']['departure_deadline_ns']+60_000_000_000


def terminal(adapter,request,*,recovered):
    result=dict(status='NO_PROOF',mainline_pid1=False,authenticated_usb=False,
                automatic_recovery_proved=False,original_a_return_proved=True,
                native_admitted=False,replay_authorized=False)
    try:
        value=download.rederive(adapter,request) if download.selected(request) else access.rederive(adapter,request)
        status='PASS_DEBIAN_SYSVINIT_RAM_PID1' if 'debian_ram' in request['N'] else 'PASS_MAINLINE_RAM_USB'
        if 'ssh' in value:status='PASS_DEBIAN_SSH_RAM'
        result.update(status=status,mainline_pid1=True,authenticated_usb=True,
                      observation=value,physical_return_requested=not recovered and not download.selected(request))
        if download.selected(request):
            # A health-only continuation may complete this original normal A;
            # a physical recover-android transfer cannot substitute for it.
            from s22plus_native_session_v3 import Step
            ready=download.return_request(adapter,request)
            returned=adapter.recover_transfer_result(Step('install-android','transfer','A'),request)
            launch=read(verify(returned['launch']))
            require(launch['arrival_deadline_ns']==ready['deadline_ns'] and
                    ready['requested_ns']<launch['boottime_ns']<ready['deadline_ns'] and
                    launch['ticket'] and launch['revalidation'] and returned['completed'] is True,
                    'normal Download/A does not join its original control intent')
            cycle=value['proof'].get('runtime_schema')==profile.codec.CYCLE_SCHEMA
            if cycle:require(value['accepted']['status']=='AUTHENTICATED_RC6_SSH_STOP' and
                    value['ssh']['boot_id']==value['accepted']['boot_id']==value['proof']['boot_id'],
                    'service cycle/SSH evidence absent from normal return')
            result.update(status='PASS_DEBIAN_RC_SSH_CYCLE_RAM' if cycle else 'PASS_MAINLINE_DOWNLOAD_RAM',automatic_download_return_proved=True,
                          original_A_return=returned,download_return=pin(adapter.directory/Coordinator.READY_FILE))
    except (ValueError,OSError,KeyError,TypeError,RawCaptureError) as error:
        result['evidence_error']=dict(type=type(error).__name__,message=str(error)[:256])
        if download.selected(request):result.update(status='NO_PROOF',automatic_download_return_proved=False)
        # Preserve independent base proof when the later SSH unit fails; no
        # connected action is performed by either rederivation path.
        try:
            if download.selected(request):
                base=download.rederive_base(adapter,request)
                result.update(status='NO_PROOF',mainline_pid1=True,authenticated_usb=True,
                              observation=base,automatic_download_return_proved=False)
                if base['proof'].get('runtime_schema')==profile.codec.CYCLE_SCHEMA:
                    manifest=profile.image_binding(request['N'])
                    closure=download.attach.rederive(adapter.directory,base['window'])
                    ssh=download.ssh_receipt(adapter,request,base,manifest,closure)
                    result.update(observation=dict(base,ssh=ssh['proof'],ssh_capture=ssh['capture']),ssh_proved=True)
                return link_fact(adapter,request,result)
            qualification=read(verify(request['N']['debian_ram']))
            if 'ssh' in qualification:
                base=access.rederive_base(adapter,request)
                if base['proof'].get('runtime_schema')==profile.codec.SSH_SCHEMA:
                    result.update(mainline_pid1=True,authenticated_usb=True,observation=base,ssh_proved=False)
        except (ValueError,OSError,KeyError,TypeError,RawCaptureError):pass
    return link_fact(adapter,request,result)


def link_fact(adapter,request,result):
    if request.get('N',{}).get('ufs_link') is not True:
        return result
    try:
        from s22plus_mainline_ufs_access_v1 import rederive_witness, rederive_link
        witness=rederive_witness(adapter,request)
        result.update(mainline_pid1=True,authenticated_usb=True,five_minute_same_boot=True,
                      ufs_witness=witness)
    except (ImportError,SyntaxError,ValueError,OSError,KeyError,TypeError,RawCaptureError) as error:
        result['ufs_witness_error']=dict(type=type(error).__name__,message=str(error)[:256])
        return result
    try:
        link=rederive_link(adapter,request)
        complete=link['result']['status']=='UFS_LINK_COMPLETED'
        result.update(ufs_link_completed=complete,ufs_evidence=link)
        if complete:
            result['status']='PASS_MAINLINE_UFS_LINK'
    except (ImportError,SyntaxError,ValueError,OSError,KeyError,TypeError,RawCaptureError) as error:
        result['ufs_evidence_error']=dict(type=type(error).__name__,message=str(error)[:256])
    return result


class Coordinator(PhysicalCoordinator):
    READY_FILE='mainline-return-ready.json'
    SUBJECT_FIELD='observation'
    SUBJECT_STEP=profile.SELECTION

    def steps(self):return normal_steps(self.session.request)

    def prepare_automatic_return(self):
        if not download.selected(self.session.request):return False
        download.return_request(self.session.adapter,self.session.request,create=True)
        return True

    def execute(self,*,attended):
        try:return super().execute(attended=attended)
        finally:
            if download.selected(self.session.request) and any(row['event']=='step-complete' and
                row['data']['step']=='install-android' for row in self.session.rows()):
                access.cleanup(self.session.adapter,self.session.request)

    def cleanup(self):
        # The inherited stop path must reach physical recovery without waiting
        # for host-network cleanup. Cleanup follows A handling in resume/recover.
        return None

    def resume(self,*,attended,operator_statement=None):
        try:return super().resume(attended=attended,operator_statement=operator_statement)
        finally:access.cleanup(self.session.adapter,self.session.request)
