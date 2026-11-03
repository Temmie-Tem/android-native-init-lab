"""Loader comparison graph using the existing one-shot owner and A recovery."""
import s22plus_loader_android_profile_v1 as profile
import s22plus_loader_android_access_v1 as access
from s22plus_debian_handoff_session_v1 import Coordinator as PhysicalCoordinator
from s22plus_native_records_v3 import Journal,pin,read,require,verify
from device_action_raw_capture_v1 import RawCaptureError


def normal_steps():
    from s22plus_native_session_v3 import Step
    return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
        Step(profile.SELECTION,profile.SELECTION,'N'),Step(profile.RETURN,'download','N'),
        Step('install-android','transfer','A'),Step('android-final','health','A'))


def arrival_deadline(adapter,step,request):
    require(step.name in ('install-native-first','install-android'),'unselected normal control transfer')
    name='android-download' if step.name=='install-native-first' else profile.RETURN
    intents=[r['data'] for r in Journal(adapter.directory/'journal').rows() if r['event']=='effect-intent']
    require(intents and intents[-1]['step']==name and intents[-1]['action']=='download' and
        intents[-1]['role']==('A' if name=='android-download' else 'N') and
        sum(r['step']==name for r in intents)==1,'transfer has no unique preceding Download intent')
    return intents[-1]['detail']['departure_deadline_ns']+60_000_000_000


def validate_result(adapter,step,value,request):
    if step.name==profile.SELECTION:
        require(value==access.rederive(adapter,request),'loader observation does not rederive')
    elif step.name==profile.RETURN:
        rows=[r['data'] for r in Journal(adapter.directory/'journal').rows()
              if r['event']=='effect-intent' and r['data']['step']==profile.RETURN]
        require(len(rows)==1 and rows[0]['action']=='download' and rows[0]['role']=='N',
                'candidate Download lacks its unique intent')
        proof=rows[0]['detail']['candidate_proof']
        access.return_proof(adapter,request,proof)
        require(read(verify(rows[0]['detail']['departure']))['identity']==
                read(verify(proof))['usb_after']['identity'],'Download generation differs from fresh proof')
    elif step.action=='health':
        # A's exact partition proof is rederived by the shared adapter. Preserve
        # the independent requirement that it is a new boot after the candidate.
        folder=adapter.folder(profile.SELECTION)/'proof/complete.json'
        if folder.exists():
            try:candidate=access.rederive(adapter,request)['health']
            except (ValueError,OSError,KeyError,TypeError,RawCaptureError):candidate=None
            if candidate is not None:
                require(read(verify(value['health']))['boot_id_sha256']!=candidate['boot_id_sha256'],
                        'original-A health reused the candidate boot')


def terminal(adapter,request,*,recovered):
    result=dict(status='NO_PROOF',loader_handoff_proved=False,vendor_android_proved=False,
        normal_download_return_proved=False,original_a_return_proved=True,
        automatic_recovery_proved=False,native_admitted=False,replay_authorized=False)
    try:
        value=access.rederive(adapter,request)
        result.update(status='PASS_LOADER_FYG8_ANDROID',loader_handoff_proved=True,
                      vendor_android_proved=True,observation=value)
        if 'prefix_control' in value:
            result['mainline_prefix_return_proved']=value['prefix_control']['mainline_prefix_return_proved']
            result['mainline_boot_proved']=False
        step=normal_steps()[3]
        observed=adapter.recover_step_result(step,request)
        adapter.validate_result(step,observed,request)
        result['normal_download_return_proved']=True
    except (ValueError,OSError,KeyError,TypeError,RawCaptureError) as error:
        result['evidence_error']=dict(type=type(error).__name__,message=str(error)[:256])
    return result


class Coordinator(PhysicalCoordinator):
    def steps(self):return normal_steps()

    def cleanup(self):return None

    def prepare_automatic_return(self):
        step=self.steps()[3]
        value=self.session.adapter.recover_step_result(step,self.session.request)
        self.session.adapter.validate_result(step,value,self.session.request)
        return True

    def stopped(self,error):
        # Even a result-publication failure leaves a stopped original owner.
        # Its recovery first rederives completed A/health and never retransfers
        # a raw-proved A. No new candidate read/control can resume this graph.
        session=self.session
        session.journal.append('stopped',error_type=type(error).__name__,error_message=str(error)[:4096],
            transfer_failure=getattr(error,'transfer_failure',None),effect_intended=session.has_effect())
        if not session.has_recovery_basis():return session.close_unused()
        android=[row for row in session.rows() if row['event']=='effect-intent' and
                 row['data']['action']=='transfer' and row['data']['role']=='A']
        action=('Original-A transfer already has an intent. Do not enter Download or repeat the transfer. '
                'Reconcile its retained raw completion; if complete, wait for Android and use health-only continuation.'
                if android else
                'Enter physical Download on the bound S22+ for original-A recovery; do not repeat candidate control.')
        return dict(state='AWAITING_ATTENDED_RECOVERY',recovery_required=True,owner_retained=True,
            device_activity='UNKNOWN',original_a_transfer_intended=bool(android),next_action=action)
