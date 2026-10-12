"""One Debian-owned early boot, fixed observation and physical original A."""
import s22plus_debian_early_profile_v1 as profile
from device_action_raw_capture_v1 import RawCaptureError
from s22plus_debian_handoff_session_v1 import Coordinator as PhysicalCoordinator
from s22plus_native_records_v3 import Journal,pin,publish,read,require,verify


def normal_steps():
    from s22plus_native_session_v3 import Step
    return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
        Step(profile.SELECTION,'early-evidence','N'),Step('install-android','transfer','A'),
        Step('android-final','health','A'))


def validate_result(adapter,step,value,request):
    if step.name!=profile.SELECTION:return
    if request['N']['profile']==profile.FILE_PROFILE:
        from s22plus_debian_file_window_v1 import rederive
        require(value==rederive(adapter,request) and value['proof']['status']=='AWAITING_OFFLINE_FILE_RECORD',
            'file window was promoted to live execution proof')
    else:
        expected='PASS_DEBIAN_USB_FIRST_OBSERVED' if request['N']['profile']==profile.USB_PROFILE else 'PASS_DEBIAN_EARLY_OBSERVED'
        require(value['proof']['status']==expected and value['proof']['debian_early_pid1'] is True and
            value['proof']['installed_debian_pid1'] is False and value['proof']['root_admitted'] is False,
            'early evidence lacks its exact bounded meaning')
    intents=[row['data'] for row in Journal(adapter.directory/'journal').rows() if row['event']=='effect-intent']
    require(sum(row['step']=='install-native-first' and row['action']=='transfer' and row['role']=='N' for row in intents)==1,
        'automatic preparation has no unique candidate transfer intent')
    require(not any(row['step']==step.name for row in intents),'read-only evidence unexpectedly has a control intent')


def return_request(adapter,request):
    ready=read(adapter.directory/Coordinator.READY_FILE)
    step=next(s for s in normal_steps() if s.name==profile.SELECTION)
    value=adapter.recover_step_result(step,request);validate_result(adapter,step,value,request)
    require(ready['operation']==pin(adapter.directory/'operation.json') and
        read(verify(ready['observation']))==value and
        ready['deadline_ns']<=read(verify(request['grant']))['deadline_ns'] and
        0<ready['deadline_ns']-ready['requested_ns']<=600_000_000_000,'early physical return request differs')
    return ready


def terminal(adapter,request,*,recovered):
    result=dict(status='NO_PROOF',debian_early_pid1=False,installed_debian_pid1=False,
        preparation_complete=False,normal_return=not recovered,native_admitted=False,replay_authorized=False)
    try:
        step=next(s for s in normal_steps() if s.name==profile.SELECTION)
        value=adapter.recover_step_result(step,request);validate_result(adapter,step,value,request)
        result.update(value['proof'])
    except (ValueError,OSError,KeyError,RawCaptureError) as error:
        result['evidence_error']=dict(type=type(error).__name__,message=str(error)[:256])
    return result


class Coordinator(PhysicalCoordinator):
    READY_FILE='debian-early-return-ready.json'
    SUBJECT_FIELD='observation'
    SUBJECT_STEP=profile.SELECTION

    def steps(self):return normal_steps()

    def cleanup(self):
        # No network manager setup, SSH service or native control was acquired.
        return None
