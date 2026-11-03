"""Fixed raw-first Android proof for one current uniLoader control boot."""
from pathlib import Path
import shlex

import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_native_android_storage_v1 as census
import s22plus_loader_android_profile_v1 as profile
import s22plus_loader_prefix_v1 as prefix
import s22plus_native_target_io_v3 as target
from s22plus_native_records_v3 import clock,host_boot,pin,publish,read,require,verify

MARKER_READ="printf 'loader_marker='; sha256sum /sys/firmware/devicetree/base/chosen/codex,uniloader-android-v1 | cut -d' ' -f1"
LOGM_READS=(('report','cat /sys/firmware/devicetree/base/chosen/codex,uniloader-logm-v1',128),
            ('last-kmsg','cat /proc/last_kmsg',4*1024*1024))

PREFIX_READS=(('report','cat /sys/firmware/devicetree/base/chosen/codex,uniloader-prefix-v1',256),)


def diagnostic(request):
    return ('prefix',PREFIX_READS) if 'prefix_control' in request['N'] else ('logm',LOGM_READS)


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
    value=dict(action=profile.SELECTION,status='PASS_LOADER_FYG8_ANDROID',health=health,
        proof=receipt,window=pin(folder/'window.json'),kernel_release=request['N']['kernel_release'],
        loader_marker_sha256=request['N']['marker_sha256'])
    if 'logm_control' in request['N'] or 'prefix_control' in request['N']:
        kind,_=diagnostic(request)
        value[kind+'_control']=rederive_logm(adapter,request,receipt,window)
    return value


def rederive_logm(adapter,request,first_receipt,window):
    kind,reads=diagnostic(request)
    folder=adapter.folder(profile.SELECTION)/kind
    attempt=read(folder/'attempt.json');complete=read(folder/'complete.json')
    require(set(attempt)=={'schema','window','before','usb_before','started_ns'} and
        attempt['schema']==f's22plus-loader-{kind}-capture-attempt-v1' and
        attempt['window']==window and attempt['before']==first_receipt and
        set(complete)=={'schema','attempt','features','captures','after','finished_ns'} and
        complete['schema']==f's22plus-loader-{kind}-capture-v1' and
        complete['attempt']==pin(folder/'attempt.json') and
        complete['features']==pin(folder/'features.capture.json') and
        complete['captures']=={name:pin(folder/(name+'.capture.json')) for name,_,_ in reads} and
        complete['after']==pin(folder/'after/complete.json'),'LOGM raw capture belongs to another attempt')
    first=rederive_health(adapter,request,first_receipt,window)
    last=rederive_health(adapter,request,complete['after'],window)
    first_complete=read(verify(first_receipt));last_complete=read(verify(complete['after']))
    last_attempt=read(verify(last_complete['attempt']))
    require(first['properties']==last['properties'] and first['boot_id_sha256']==last['boot_id_sha256'] and
        first_complete['usb_after']['identity']==attempt['usb_before']['identity']==last_attempt['usb_before']['identity'] and
        attempt['usb_before']['topology']==target.lane.SOURCE_TOPOLOGY and
        first_complete['finished_ns']<=attempt['usb_before']['boottime_ns']<=attempt['started_ns']<
        last_attempt['started_ns']<last_complete['finished_ns']<=complete['finished_ns']<window['deadline_ns'],
        'LOGM capture has no complete same-candidate-boot/time/USB bracket')
    census.require_shell_v2(complete['features'])
    data={}
    for name,_,maximum in reads:
        handle=raw.load_handle(verify(complete['captures'][name]));raw.require_success(handle)
        require(not raw.read_stderr(handle,maximum=16384),'LOGM fixed read returned diagnostics')
        data[name]=raw.read_stdout(handle,maximum=maximum)
    if kind=='prefix':
        cfg=request['N']['prefix_control']
        result=prefix.report(data['report'],cfg['configuration'],0x80ba00000+cfg['entry_offset'])
    else:result=profile.logm_projection(data['report'],data['last-kmsg'],request['N']['logm_control']['configuration'])
    result.update(capture=pin(folder/'complete.json'),before=first_receipt,after=complete['after'],
                  same_candidate_android_boot=True)
    return result


def capture_logm(adapter,request,first_receipt,guard,window):
    kind,reads=diagnostic(request)
    task=adapter.configuration(request);folder=adapter.folder(profile.SELECTION)/kind;folder.mkdir(mode=0o700)
    def bound_guard():
        guard();require(window['host_boot']==host_boot() and clock()<window['deadline_ns'],
                        'original LOGM observation window expired or host boot changed')
    bound_guard();usb=target.usb_snapshot(target.lane.SOURCE_TOPOLOGY,folder)
    require(usb['identity']==read(verify(first_receipt))['usb_after']['identity'],
            'candidate USB changed before LOGM capture')
    attempt=publish(folder/'attempt.json',dict(schema=f's22plus-loader-{kind}-capture-attempt-v1',
        window=window,before=first_receipt,usb_before=usb,started_ns=clock()))
    client=CandidateAndroid(task,folder,guard=bound_guard)
    features=client.command(['-s',task['target']['serial'],'features'],'features',
        timeout=min(10,(window['deadline_ns']-clock())/1e9),before_launch=bound_guard)
    census.require_shell_v2(pin(features.receipt_path));captures={}
    for name,command,maximum in reads:
        bound_guard()
        with transport.pin_regular_file(Path(task['adb']['path']),label='loader LOGM ADB',
                expected_size=task['adb']['size'],expected_sha256=task['adb']['sha256']) as adb:
            handle=raw.acquire_command([str(adb.path),'-s',task['target']['serial'],'shell','-T',
                'su -c '+shlex.quote(command)],folder,name,
                timeout=min(30,(window['deadline_ns']-clock())/1e9),stdout_maximum=maximum,
                stderr_maximum=16384,before_spawn=bound_guard)
        raw.require_success(handle)
        require(not raw.read_stderr(handle,maximum=16384),'LOGM fixed read returned diagnostics')
        captures[name]=pin(handle.receipt_path)
    after=capture_health(adapter,request,folder/'after',bound_guard,window,wait=False)
    bound_guard()
    publish(folder/'complete.json',dict(schema=f's22plus-loader-{kind}-capture-v1',attempt=attempt,
        features=pin(features.receipt_path),captures=captures,after=after,finished_ns=clock()))
    return rederive_logm(adapter,request,first_receipt,window)


def observe(adapter,request,guard):
    profile.image_binding(request['N'])
    folder=adapter.folder(profile.SELECTION,create=True);window=window_for(adapter,request)
    publish(folder/'window.json',window)
    first=capture_health(adapter,request,folder/'proof',guard,window,wait=True)
    if 'logm_control' in request['N'] or 'prefix_control' in request['N']:
        capture_logm(adapter,request,first,guard,window)
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
