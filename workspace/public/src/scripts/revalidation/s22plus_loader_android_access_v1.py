"""Fixed raw-first Android proof for one current uniLoader control boot."""
from pathlib import Path

import s22plus_loader_android_profile_v1 as profile
import s22plus_native_target_io_v3 as target
from s22plus_native_records_v3 import clock,host_boot,pin,publish,read,require,verify

MARKER_READ="printf 'loader_marker='; sha256sum /sys/firmware/devicetree/base/chosen/codex,uniloader-android-v1 | cut -d' ' -f1"


def candidate_artifact(task):
    return dict(partition_sha256=dict(task['A']['partition_sha256'],boot=task['N']['boot_sha256']))


def project_health(captures,task):
    value=target.health_projection(captures,task['target'],candidate_artifact(task),
        loader_marker_sha256=task['N']['marker_sha256'])
    require(value['properties']['kernel_release']==task['N']['kernel_release'],
            'candidate executed an unexpected kernel release')
    return value


class CandidateAndroid(target.Android):
    ROOT_COMMAND=target.ROOT_HEALTH+'\n'+MARKER_READ
    READY_COMMAND="printf 'boot_completed=%s\\nbootanim=%s\\n' \"$(getprop sys.boot_completed)\" \"$(getprop init.svc.bootanim)\""
    READY_MAXIMUM=128

    def __init__(self,task,directory,*,guard):
        self.task=task
        super().__init__(task['adb'],task['target'],candidate_artifact(task),directory,guard=guard)

    def project_health(self,captures):return project_health(captures,self.task)

    def readiness_complete(self,value):
        if value=='':return False
        lines=value.splitlines()
        require(len(lines)==2 and lines[0].startswith('boot_completed=') and
                lines[1].startswith('bootanim='),'candidate readiness field order differs')
        values=dict(line.split('=',1) for line in lines)
        require(values['boot_completed'] in ('','0','1') and
                values['bootanim'] in ('','running','restarting','stopped'),'candidate readiness properties malformed')
        return values=={'boot_completed':'1','bootanim':'stopped'}


def window_for(adapter,request):
    from s22plus_native_session_v3 import Step
    receipt=adapter.recover_transfer_result(Step('install-native-first','transfer','N'),request)['launch']
    launch=read(verify(receipt));grant=read(verify(request['grant']))
    return dict(operation=pin(adapter.directory/'operation.json'),candidate_launch=receipt,
        host_boot=grant['host_boot'],opened_ns=launch['boottime_ns'],
        deadline_ns=min(grant['deadline_ns'],launch['boottime_ns']+profile.OBSERVATION_NS))


def capture_health(adapter,request,folder,guard,window,*,wait):
    task=adapter.configuration(request);folder=Path(folder);folder.mkdir(mode=0o700)
    def bound_guard():
        guard();require(window['host_boot']==host_boot() and clock()<window['deadline_ns'],
                        'original loader observation window expired or host boot changed')
    client=CandidateAndroid(task,folder,guard=bound_guard)
    if wait:client.wait_ready(deadline_ns=window['deadline_ns'])
    bound_guard()
    before=target.usb_snapshot(target.lane.SOURCE_TOPOLOGY,folder)
    attempt=publish(folder/'attempt.json',dict(schema='s22plus-loader-android-proof-attempt-v1',
        window=window,started_ns=clock(),usb_before=before))
    value=client._health_attempt([],deadline_ns=window['deadline_ns'])
    bound_guard();after=target.usb_snapshot(target.lane.SOURCE_TOPOLOGY,folder)
    require(before['identity']==after['identity'],'candidate USB generation changed during proof')
    finished=clock();require(finished<window['deadline_ns'],'proof ended outside original window')
    health=publish(folder/'health.json',value)
    return publish(folder/'complete.json',dict(schema='s22plus-loader-android-proof-v1',
        attempt=attempt,health=health,usb_after=after,finished_ns=finished))


def rederive_health(adapter,request,receipt,window):
    folder=Path(receipt['path']).parent
    value=read(verify(receipt));attempt=read(verify(value['attempt']))
    require(set(value)=={'schema','attempt','health','usb_after','finished_ns'} and
        value['schema']=='s22plus-loader-android-proof-v1' and
        set(attempt)=={'schema','window','started_ns','usb_before'} and
        attempt['schema']=='s22plus-loader-android-proof-attempt-v1' and
        attempt['window']==window and window['host_boot']==read(verify(request['grant']))['host_boot'] and
        value['attempt']==pin(folder/'attempt.json') and value['health']==pin(folder/'health.json'),
        'candidate proof belongs to another original attempt')
    before,after=attempt['usb_before'],value['usb_after']
    require(before['topology']==after['topology']==target.lane.SOURCE_TOPOLOGY and
        before['identity']==after['identity'] and
        window['opened_ns']<=before['boottime_ns']<=attempt['started_ns']<
        after['boottime_ns']<=value['finished_ns']<window['deadline_ns'],
        'candidate proof has no complete original time/generation bracket')
    health=read(verify(value['health']))
    require(health==project_health(health['captures'],adapter.configuration(request)) and
        all(Path(p['path']).parent==folder for p in health['captures']),
        'candidate raw health projection differs or belongs elsewhere')
    return health


def rederive(adapter,request):
    folder=adapter.folder(profile.SELECTION);window=window_for(adapter,request)
    require(read(folder/'window.json')==window,'loader observation window differs')
    receipt=pin(folder/'proof/complete.json')
    health=rederive_health(adapter,request,receipt,window)
    initial=read(adapter.folder('preflight')/'health.json')
    require(health['boot_id_sha256']!=initial['boot_id_sha256'],'candidate proof reused initial Android boot')
    return dict(action=profile.SELECTION,status='PASS_LOADER_FYG8_ANDROID',health=health,
        proof=receipt,window=pin(folder/'window.json'),kernel_release=request['N']['kernel_release'],
        loader_marker_sha256=request['N']['marker_sha256'])


def observe(adapter,request,guard):
    profile.image_binding(request['N'])
    folder=adapter.folder(profile.SELECTION,create=True);window=window_for(adapter,request)
    publish(folder/'window.json',window)
    capture_health(adapter,request,folder/'proof',guard,window,wait=True)
    value=rederive(adapter,request)
    publish(folder/'result.json',value)
    return value


def before_return(adapter,request,folder,guard):
    original=rederive(adapter,request);window=window_for(adapter,request)
    receipt=capture_health(adapter,request,Path(folder)/'proof',guard,window,wait=False)
    current=rederive_health(adapter,request,receipt,window)
    require(current['boot_id_sha256']==original['health']['boot_id_sha256'],
            'candidate rebooted before normal Download')
    return receipt


def return_proof(adapter,request,receipt,*,current_usb=None):
    original=rederive(adapter,request);window=window_for(adapter,request)
    require(receipt==pin(adapter.folder(profile.RETURN)/'proof/complete.json'),'return proof location differs')
    current=rederive_health(adapter,request,receipt,window)
    require(current['boot_id_sha256']==original['health']['boot_id_sha256'],
            'normal return does not belong to the observed candidate boot')
    if current_usb is not None:
        require(window['host_boot']==host_boot() and clock()<window['deadline_ns'] and
            current_usb['identity']==read(verify(receipt))['usb_after']['identity'],
            'candidate changed or original window expired before Download intent')
    return current
