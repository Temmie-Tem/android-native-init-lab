"""Mainline observation using the existing one-shot Session and physical return."""
import s22plus_mainline_profile_v1 as profile
import s22plus_mainline_access_v1 as access
from s22plus_debian_handoff_session_v1 import Coordinator as PhysicalCoordinator
from s22plus_native_records_v3 import Journal,pin,read,require,verify
from device_action_raw_capture_v1 import RawCaptureError


def normal_steps():
    from s22plus_native_session_v3 import Step
    return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
        Step(profile.SELECTION,'mainline-evidence','N'),Step('install-android','transfer','A'),
        Step('android-final','health','A'))


def validate_result(adapter,step,value,request):
    if step.name!=profile.SELECTION:return
    expected=('AUTHENTICATED_DEBIAN_SYSVINIT_RAM_OBSERVATION' if 'debian_ram' in request['N']
              else 'AUTHENTICATED_CANARY_OBSERVATION')
    require(value==access.rederive(adapter,request) and
            value['proof']['status']==expected, 'mainline raw proof differs')
    rows=Journal(adapter.directory/'journal').rows()
    require(sum(row['event']=='effect-intent' and row['data']['step']=='install-native-first' for row in rows)==1 and
            not any(row['event']=='effect-intent' and row['data']['step']==step.name for row in rows),
            'mainline observation does not follow one candidate transfer')


def return_request(adapter,request):
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
        value=access.rederive(adapter,request)
        status='PASS_DEBIAN_SYSVINIT_RAM_PID1' if 'debian_ram' in request['N'] else 'PASS_MAINLINE_RAM_USB'
        result.update(status=status,mainline_pid1=True,authenticated_usb=True,
                      observation=value,physical_return_requested=not recovered)
    except (ValueError,OSError,KeyError,TypeError,RawCaptureError) as error:
        result['evidence_error']=dict(type=type(error).__name__,message=str(error)[:256])
    return result


class Coordinator(PhysicalCoordinator):
    READY_FILE='mainline-return-ready.json'
    SUBJECT_FIELD='observation'
    SUBJECT_STEP=profile.SELECTION

    def steps(self):return normal_steps()

    def cleanup(self):
        # The inherited stop path must reach physical recovery without waiting
        # for host-network cleanup. Cleanup follows A handling in resume/recover.
        return None

    def resume(self,*,attended,operator_statement=None):
        try:return super().resume(attended=attended,operator_statement=operator_statement)
        finally:access.cleanup(self.session.adapter,self.session.request)
