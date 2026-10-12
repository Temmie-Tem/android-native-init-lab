"""Fixed native log calibration followed by physical original-A return."""
import s22plus_native_log_profile_v1 as profile
from s22plus_debian_handoff_session_v1 import Coordinator as PhysicalCoordinator
from s22plus_native_records_v3 import pin,read,require,verify


def normal_steps():
    from s22plus_native_session_v3 import Step
    return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
        Step(profile.SELECTION,'observe','N','detach'),Step('install-android','transfer','A'),
        Step('android-final','health','A'))


def return_request(adapter,request):
    from s22plus_native_root_inspect_session_v1 import validate_result
    require(request['operation']==profile.OPERATION,'unselected calibration return')
    ready=read(adapter.directory/Coordinator.READY_FILE)
    step=next(s for s in normal_steps() if s.name==profile.SELECTION)
    value=adapter.recover_step_result(step,request);validate_result(adapter,step,value,request)
    require(ready['operation']==pin(adapter.directory/'operation.json') and
        read(verify(ready['observation']))==value and
        ready['deadline_ns']<=read(verify(request['grant']))['deadline_ns'] and
        0<ready['deadline_ns']-ready['requested_ns']<=600_000_000_000,
        'calibration physical return request differs')
    return ready


class Coordinator(PhysicalCoordinator):
    READY_FILE='native-log-return-ready.json'
    SUBJECT_FIELD='observation'
    SUBJECT_STEP=profile.SELECTION

    def steps(self):return normal_steps()

    def cleanup(self):return None
