"""One automatic N lifetime, fixed shutdown, attended original-A return."""
from device_action_raw_capture_v1 import RawCaptureError
from s22plus_native_records_v3 import read,require
from s22plus_debian_handoff_session_v1 import Coordinator as PhysicalCoordinator,intents,validate_task
from s22plus_debian_autoboot_access_v1 import Access


def normal_steps():
    from s22plus_native_session_v3 import Step
    return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
        Step('debian-health','debian-health','N'),Step('debian-shutdown','debian-shutdown','N'),
        Step('install-android','transfer','A'),Step('android-final','health','A'))


def validate_result(adapter,step,value,request):
    selected=Access(adapter,request)
    if step.action=='debian-health':require(value==selected.rederive_health(),'automatic health differs')
    elif step.action=='debian-shutdown':
        require(value==selected.rederive_shutdown(),'automatic shutdown differs')
        rows=intents(adapter,step.name)
        require(len(rows)==1 and rows[0]['detail']==read(adapter.folder(step.name)/'intent.json'),'automatic shutdown intent differs')


def terminal(adapter,request,*,recovered):
    result=dict(status='NO_PROOF',debian_early_pid1=False,debian_boot_proved=False,debian_runtime_proved=False,
        ssh_access_proved=False,clean_shutdown_proved=False,normal_return=not recovered,replay_authorized=False)
    try:
        selected=Access(adapter,request);evidence=selected.evidence()
        result.update(status='PASS_AUTOMATIC_DEBIAN_RUNTIME_120S',debian_early_pid1=True,
            debian_boot_proved=True,debian_runtime_proved=True,observation=evidence['proof'])
        health=selected.rederive_health()
        result.update(status='PASS_DEBIAN_AUTOMATIC_INITIAL_PID1_TO_SSH',ssh_access_proved=True,ssh_health=health['health'])
    except (ValueError,OSError,KeyError,RawCaptureError) as error:
        result['evidence_error']=dict(type=type(error).__name__,message=str(error)[:256])
    return result


class Coordinator(PhysicalCoordinator):
    def steps(self):return normal_steps()
