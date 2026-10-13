"""One Debian-owned integrated boot; existing physical original-A recovery."""
import s22plus_debian_integrated_profile_v1 as profile
import s22plus_debian_integrated_observation_v1 as observation
import s22plus_debian_access_v1 as access
from s22plus_debian_handoff_session_v1 import Coordinator as PhysicalCoordinator,intents
from device_action_raw_capture_v1 import RawCaptureError
from s22plus_native_records_v3 import pin,read,require


def normal_steps():
    from s22plus_native_session_v3 import Step
    return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
        Step(profile.SELECTION,'integrated-start','N'),Step('debian-health','debian-health','N'),
        Step('debian-shutdown','debian-shutdown','N'),Step('install-android','transfer','A'),
        Step('android-final','health','A'))


def original_intent(adapter,request):
    rows=intents(adapter,profile.SELECTION);record=read(adapter.folder(profile.SELECTION)/'start-intent.json')
    require(len(rows)==1 and rows[0]['action']=='integrated-start' and rows[0]['role']=='N' and
        rows[0]['detail']==record and record['image']==request['N'],'integrated compound intent differs')
    return record


def validate_result(adapter,step,value,request):
    if step.name==profile.SELECTION:
        original_intent(adapter,request)
        require(value==observation.rederive(adapter.folder(step.name),request['N']) and
            value['proof']['status']=='PASS_DEBIAN_INTEGRATED_RUNTIME','integrated runtime not complete')
    elif step.action=='debian-health':require(value==access.Access(adapter,request).rederive_health(),'integrated SSH differs')
    elif step.action=='debian-shutdown':
        require(value==access.Access(adapter,request).rederive_shutdown(),'integrated shutdown differs')
        rows=intents(adapter,step.name)
        require(len(rows)==1 and rows[0]['detail']==read(adapter.folder(step.name)/'intent.json'),'shutdown intent differs')


def terminal(adapter,request,*,recovered):
    result=dict(status='NO_PROOF',debian_early_pid1=False,debian_boot_proved=False,debian_runtime_proved=False,
        ssh_access_proved=False,clean_shutdown_proved=False,normal_return=not recovered,replay_authorized=False)
    try:
        original_intent(adapter,request)
        value=observation.rederive(adapter.folder(profile.SELECTION),request['N'],complete=False)['proof']
        result['observation']=value
        if value['initial_parent'] is not None:result.update(status='PASS_INITIAL_DEBIAN_PARENT',debian_early_pid1=True)
        selected=value['debian_handoff']
        if selected and selected['init_proof'] is not None:result.update(status='PASS_INSTALLED_DEBIAN_PID1',debian_boot_proved=True)
        if selected and selected['runtime_proof'] is not None:result.update(status='PASS_DEBIAN_RUNTIME_120S',debian_runtime_proved=True)
        healthy=access.Access(adapter,request).rederive_health()
        result.update(status='PASS_DEBIAN_INITIAL_PID1_TO_SSH',ssh_access_proved=True,ssh_health=healthy['health'])
    except (ValueError,OSError,KeyError,RawCaptureError) as error:
        result['evidence_error']=dict(type=type(error).__name__,message=str(error)[:256])
    return result


class Coordinator(PhysicalCoordinator):
    def steps(self):return normal_steps()
