"""Finite clock handoff and exact host-owned USB sharing for P463 only."""
import ipaddress
import json
import os
from pathlib import Path
import re
import time
import uuid

import device_action_raw_capture_v1 as raw
from s22plus_native_records_v3 import clock,digest,pin,publish,read,require,verify
import s22plus_debian_apt_v1 as spec

TIME=re.compile(r'apt-time ([12]) ([0-9a-f]{64}) ([1-9][0-9]{9}) (0|[1-9][0-9]{0,8})')
STATUS=re.compile(rb'S22_APT_CLOCK_V1 ([12]) ([0-9a-f]{64}) ([0-9]+) ([0-9]+) ([0-9]+) ([0-9]+) ([0-9]+) ([0-9]+) ([0-9]+)\n')


def selected(request):
    return request.get('operation')=='debian-autoboot' and request.get('N',{}).get('namespace')==spec.NAMESPACE


def command_allowed(request,phase,command):
    if not selected(request) or phase not in (1,2):return False
    if command=='apt-time-status':return True
    match=TIME.fullmatch(command)
    return bool(match and int(match[1])==phase and 1577836800<=int(match[3])<4102444800)


def state(handle):
    output=raw.read_stdout(handle,maximum=4096);diagnostic=raw.read_stderr(handle,maximum=16384)
    require(not handle.timed_out and not handle.output_exceeded and handle.producer_error_type is None and
        not diagnostic,'clock status producer failed')
    if handle.returncode==75 and output in (b'S22_APT_CLOCK_WAIT\n',b'S22_APT_CLOCK_READY\n',b'S22_APT_CLOCK_PENDING\n'):
        return output.decode().strip().removeprefix('S22_APT_CLOCK_')
    raw.require_success(handle);match=STATUS.fullmatch(output);require(match is not None,'clock readback shape differs')
    phase,boot,*values=match.groups();sec,ns,requested,before,after,observed_sec,observed_ns=map(int,values)
    require(1577836800<=sec<4102444800 and ns<1000000000 and requested<=before<=after<300000 and
        after-requested<=20000 and observed_ns<1000000000 and observed_sec<4102444800 and
        0<=(observed_sec-sec)*1000000000+observed_ns-ns<=1000000000,'clock readback values differ')
    return dict(phase=int(phase),boot_sha256=boot.decode(),utc_seconds=sec,utc_nanoseconds=ns,
        requested_ms=requested,before_ms=before,after_ms=after,observed_seconds=observed_sec,observed_nanoseconds=observed_ns)


def handoff(client,folder,found,guard,deadline,first_health):
    require(selected(client.request),'unselected clock handoff')
    require(not (folder/'clock-intent.json').exists(),'clock handoff intent is already consumed')
    boot=first_health['health']['boot_id_sha256'];ready=None
    for ordinal in range(1,31):
        guard();handle=client.ssh('apt-time-status',folder,f'clock-ready-{ordinal:02d}',found,guard,deadline_ns=deadline)
        value=state(handle)
        if value=='READY':ready=pin(handle.receipt_path);break
        require(value=='WAIT','clock handoff already claimed or applied')
        time.sleep(min(.2,max(0,(deadline-clock())/1_000_000_000)))
    require(ready is not None,'clock readiness budget exhausted')
    guard();started=clock();utc=time.time_ns();sec,ns=divmod(utc,1_000_000_000)
    require(1577836800<=sec<4102444800,'host wall time is outside the fixed UTC domain')
    command=f'apt-time {client.reboot_phase} {boot} {sec} {ns}'
    intent=dict(schema='s22plus-debian-apt-time-intent-v1',operation=pin(client.adapter.directory/'operation.json'),
        phase=client.reboot_phase,boot_sha256=boot,command=command,utc_ns=utc,host_started_ns=started,
        deadline_ns=deadline,ready=ready)
    # Publish before dispatch, and never send this mutating request again.
    publish(folder/'clock-intent.json',intent)
    handle=client.ssh(command,folder,'clock-request',found,guard,deadline_ns=deadline)
    output=raw.read_stdout(handle,maximum=4096);diagnostic=raw.read_stderr(handle,maximum=16384)
    acknowledged=(handle.returncode==0 and not handle.timed_out and not handle.output_exceeded and
        handle.producer_error_type is None and not diagnostic and output==b'S22_APT_CLOCK_REQUESTED\n')
    requested=pin(handle.receipt_path)
    # Only fixed status reads may resolve a lost/uncertain request response.
    for ordinal in range(1,61):
        guard();handle=client.ssh('apt-time-status',folder,f'clock-status-{ordinal:02d}',found,guard,deadline_ns=deadline)
        value=state(handle)
        if isinstance(value,dict):
            require((value['phase'],value['boot_sha256'],value['utc_seconds'],value['utc_nanoseconds'])==
                (client.reboot_phase,boot,sec,ns),'clock readback belongs to another request')
            finished=clock();guard()
            require(started<=finished<deadline and finished-started<=30_000_000_000,
                'clock handoff exceeded its original fresh-time bound')
            publish(folder/'clock.json',dict(intent=pin(folder/'clock-intent.json'),request=requested,
                acknowledged=acknowledged,status=pin(handle.receipt_path),readback=value,host_finished_ns=finished))
            return
        require(value in ('READY','PENDING'),'clock owner vanished after request')
        time.sleep(min(.2,max(0,(deadline-clock())/1_000_000_000)))
    raise TimeoutError('one clock request was not resolved by bounded status reads')


def rederive_request(client,folder,boot_sha256):
    value=read(folder/'clock.json');intent=read(verify(value['intent']))
    window=read(folder/'window.json')
    require(value['intent']==pin(folder/'clock-intent.json') and intent['operation']==pin(client.adapter.directory/'operation.json') and
        intent['phase']==client.reboot_phase and intent['boot_sha256']==boot_sha256 and
        window['basis']==client.basis() and intent['deadline_ns']==window['basis']['deadline_ns'] and
        window['opened_ns']<=intent['host_started_ns']<=value['host_finished_ns']<intent['deadline_ns'] and
        value['host_finished_ns']-intent['host_started_ns']<=30_000_000_000,'clock receipt ownership or window differs')
    require(state(raw.load_handle(verify(intent['ready'])))=='READY','clock ready receipt differs')
    result=state(raw.load_handle(verify(value['status'])))
    require(result==value['readback'] and result['phase']==client.reboot_phase and result['boot_sha256']==intent['boot_sha256'] and
        result['utc_seconds']*1_000_000_000+result['utc_nanoseconds']==intent['utc_ns'] and
        intent['command']==f"apt-time {client.reboot_phase} {intent['boot_sha256']} {result['utc_seconds']} {result['utc_nanoseconds']}",
        'clock status does not match the immutable request')
    request=raw.load_handle(verify(value['request']))
    ack=(request.returncode==0 and not request.timed_out and not request.output_exceeded and
        request.producer_error_type is None and not raw.read_stderr(request,maximum=16384) and
        raw.read_stdout(request,maximum=4096)==b'S22_APT_CLOCK_REQUESTED\n')
    require(value['acknowledged']==ack,'clock request acknowledgment differs')
    return value


def rederive(client,folder,proof):
    value=rederive_request(client,folder,proof['kernel_boot_identity_sha256']);result=value['readback']
    event=proof['runtime']['apt']['clock']
    require(event is not None and (event['a'],event['b'],event['c'])==
        (result['utc_seconds'],result['utc_nanoseconds'],result['after_ms']-result['requested_ms']),
        'clock readback is absent from authenticated runtime')
    return value


FIELDS='connection.id,connection.uuid,802-3-ethernet.mac-address,connection.interface-name,connection.autoconnect,ipv4.method,ipv4.addresses,ipv4.never-default,ipv6.method'


def network_rows(client,interface):
    return ['s22-debian-'+client.plan['candidate']['run_id'],client.plan['network_uuid'],
        client.plan['link']['host_mac'],interface,'no','shared',client.plan['link']['host_address'],'yes','disabled']


def network_inspection(client,handle,interfaces):
    raw.require_success(handle)
    require(not raw.read_stderr(handle,maximum=16384),'shared network inspection has diagnostics')
    rows=raw.read_stdout(handle,maximum=16384).decode('ascii').splitlines()
    if len(rows)==9:rows[2]=rows[2].lower()
    require(any(rows==network_rows(client,name) for name in interfaces),'shared network ownership or scope differs')


def inspect_network(client,folder,label):
    return client.host(['--escape','no','-g',FIELDS,'connection','show','uuid',client.plan['network_uuid']],folder,label)


def host_snapshot(client,folder,label):
    tool=client.plan['ip'];verify(tool,maximum=32*1024*1024)
    for kind,args in (('addresses',['address','show']),('routes',['route','show','table','all'])):
        handle=raw.acquire_command([tool['path'],'-j','-4',*args],folder,label+'-'+kind,timeout=10,
            stdout_maximum=65536,stderr_maximum=16384,env=dict(os.environ,LC_ALL='C',LANG='C'))
        raw.require_success(handle);require(not raw.read_stderr(handle,maximum=16384),'host network snapshot has diagnostics')
    with Path('/etc/resolv.conf').open('rb') as stream:resolver=stream.read(65537)
    require(len(resolver)<=65536,'host resolver exceeds bound')
    raw.publish_captured_bytes(folder,label+'-resolver',stdout=resolver)
    data=decode_host_snapshot(folder,label)
    publish(folder/(label+'.json'),data);return data


def decode_host_snapshot(folder,label):
    data={}
    for kind in ('addresses','routes','resolver'):
        handle=raw.load_handle(folder/(label+'-'+kind+'.capture.json'));raw.require_success(handle)
        require(not raw.read_stderr(handle,maximum=16384),'host snapshot raw evidence has diagnostics')
        output=raw.read_stdout(handle,maximum=65536)
        if kind=='resolver':data['resolver_sha256']=digest(output);continue
        rows=json.loads(output);require(isinstance(rows,list) and len(rows)<=512,'host snapshot raw shape differs')
        data[kind]=rows
    return data


def check_routes(client,snapshot,interface):
    subnet=ipaddress.ip_interface(client.plan['link']['host_address']).network
    for row in snapshot['addresses']:
        if row['ifname']==interface:continue
        for address in row['addr_info']:
            require(not subnet.overlaps(ipaddress.ip_network(f"{address['local']}/{address['prefixlen']}",strict=False)),
                'USB subnet conflicts with another host interface')
    for row in snapshot['routes']:
        if row.get('dst') in (None,'default') or row.get('dev')==interface:continue
        require(not subnet.overlaps(ipaddress.ip_network(row['dst'],strict=False)),'USB subnet conflicts with another host route')


def default_routes(snapshot):
    return sorted(json.dumps(r,sort_keys=True) for r in snapshot['routes'] if r.get('dst')=='default')


def configure_network(client,folder,found,guard):
    import s22plus_debian_access_v1 as base
    require(selected(client.request),'unselected host sharing')
    guard();require(base.endpoint(client.plan['link'])==found,'NCM changed before shared-network preparation')
    connection=client.plan['network_uuid'];interface=found['interface']
    before=host_snapshot(client,folder,'network-host-before');check_routes(client,before,interface)
    inventory=client.host(['--escape','no','-t','-f','UUID,TYPE','connection','show'],folder,'network-inventory')
    rows=raw.read_stdout(raw.load_handle(verify(inventory)),maximum=16384).decode('ascii').splitlines()
    require(len(rows)<=128,'host connection inventory exceeds bound')
    original=client.adapter.folder('debian-health')
    if client.reboot_phase==1:
        require(not any(r.split(':')[0]==connection for r in rows),'shared network UUID already exists')
    else:
        require(read(original/'network-intent.json')==dict(uuid=connection,endpoint=read(original/'endpoint.json')),
            'original sharing intent differs')
        network_inspection(client,raw.load_handle(verify(inspect_network(client,folder,'network-before'))),
            [read(original/'endpoint.json')['interface']])
    subnet=ipaddress.ip_interface(client.plan['link']['host_address']).network
    for ordinal,row in enumerate(rows):
        identity,kind=row.split(':',1);require(str(uuid.UUID(identity))==identity,'host connection UUID is malformed')
        if identity==connection or kind!='802-3-ethernet':continue
        receipt=client.host(['--escape','no','-g','connection.id,connection.interface-name,802-3-ethernet.mac-address,ipv4.addresses',
            'connection','show','uuid',identity],folder,f'network-foreign-{ordinal:03d}')
        values=raw.read_stdout(raw.load_handle(verify(receipt)),maximum=16384).decode('ascii').splitlines()
        require(len(values)==4,'foreign Ethernet ownership is incomplete')
        require(values[0]!=network_rows(client,interface)[0] and values[1]!=interface and
            values[2].lower()!=client.plan['link']['host_mac'],'another profile matches the selected USB endpoint')
        for address in filter(None,values[3].split(',')):
            require(not subnet.overlaps(ipaddress.ip_interface(address.strip()).network),'USB subnet conflicts with another profile')
    receipt=client.host(['--escape','no','-g','GENERAL.CON-UUID','device','show',interface],folder,'network-device-before')
    active=raw.read_stdout(raw.load_handle(verify(receipt)),maximum=16384).decode('ascii').strip()
    require(active in ('','--',connection),'USB endpoint belongs to another active connection')
    guard();require(base.endpoint(client.plan['link'])==found,'NCM changed before shared-network intent')
    publish(folder/'network-intent.json',dict(uuid=connection,endpoint=found))
    if client.reboot_phase==1:
        client.host(['connection','add','save','no','type','ethernet','con-name',network_rows(client,interface)[0],
            'ifname',interface,'connection.uuid',connection,'connection.autoconnect','no',
            '802-3-ethernet.mac-address',client.plan['link']['host_mac'],'ipv4.method','shared',
            'ipv4.addresses',client.plan['link']['host_address'],'ipv4.never-default','yes','ipv6.method','disabled'],folder,'network-create')
    else:
        client.host(['connection','modify','--temporary','uuid',connection,'connection.interface-name',interface],folder,'network-rebind')
    guard();require(base.endpoint(client.plan['link'])==found,'NCM changed before shared-network activation')
    network_inspection(client,raw.load_handle(verify(inspect_network(client,folder,'network-pre-up'))),[interface])
    client.host(['connection','up','uuid',connection,'ifname',interface],folder,'network-up')
    guard();require(base.endpoint(client.plan['link'])==found,'NCM changed during shared-network activation')
    network_inspection(client,raw.load_handle(verify(inspect_network(client,folder,'network-after'))),[interface])
    after=host_snapshot(client,folder,'network-host-after');check_routes(client,after,interface)
    require(default_routes(before)==default_routes(after) and before['resolver_sha256']==after['resolver_sha256'],
        'USB sharing changed host default routing or resolver')


def network_result(client,folder):
    found=read(folder/'endpoint.json');interface=found['interface']
    require(read(folder/'network-intent.json')==dict(uuid=client.plan['network_uuid'],endpoint=found),'shared-network intent differs')
    if client.reboot_phase==2:
        network_inspection(client,raw.load_handle(folder/'network-before.capture.json'),
            [read(client.adapter.folder('debian-health')/'endpoint.json')['interface']])
    for label in ('network-pre-up','network-after'):
        network_inspection(client,raw.load_handle(folder/(label+'.capture.json')),[interface])
    for label in ('network-create' if client.reboot_phase==1 else 'network-rebind','network-up'):
        raw.require_success(raw.load_handle(folder/(label+'.capture.json')))
    before,after=(read(folder/(label+'.json')) for label in ('network-host-before','network-host-after'))
    require(before==decode_host_snapshot(folder,'network-host-before') and after==decode_host_snapshot(folder,'network-host-after'),
        'shared-network host snapshot differs from raw evidence')
    for snapshot in (before,after):check_routes(client,snapshot,interface)
    require(default_routes(before)==default_routes(after) and before['resolver_sha256']==after['resolver_sha256'],
        'shared-network host preservation differs')


def cleanup_network(client):
    """Retire only the exact owned share; this host result never gates original A."""
    folder=client.cleanup_folder();intent=folder/'network-intent.json'
    if not intent.exists():return dict(status='NOT_CREATED')
    output=folder/('cleanup-'+uuid.uuid4().hex);output.mkdir(mode=0o700)
    try:
        value=read(intent);connection=client.plan['network_uuid']
        require(value==dict(uuid=connection,endpoint=read(folder/'endpoint.json')),'shared cleanup intent differs')
        def active(label):
            receipt=client.host(['--escape','no','-g','UUID','connection','show','--active'],output,label)
            return raw.read_stdout(raw.load_handle(verify(receipt)),maximum=16384).decode('ascii').splitlines()
        receipt=client.host(['--escape','no','-g','UUID','connection','show'],output,'inventory-before')
        existed=connection in raw.read_stdout(raw.load_handle(verify(receipt)),maximum=16384).decode('ascii').splitlines()
        if existed:
            network_inspection(client,raw.load_handle(verify(inspect_network(client,output,'before'))),client.cleanup_interfaces(value))
            if connection in active('active-before'):client.host(['connection','down','uuid',connection],output,'down')
            require(connection not in active('active-retired'),'owned sharing is still active')
            client.host(['connection','delete','uuid',connection],output,'delete')
        receipt=client.host(['--escape','no','-g','UUID','connection','show'],output,'inventory-after')
        require(connection not in raw.read_stdout(raw.load_handle(verify(receipt)),maximum=16384).decode('ascii').splitlines()
            and connection not in active('active-after'),'owned sharing was not removed')
        result=dict(status='REMOVED' if existed else 'ALREADY_ABSENT',intent=pin(intent),
            owned_profile_and_activation_absent=True,networkmanager_managed_rules_independently_observed=False,device_actions=0)
    except (ValueError,OSError,KeyError,TypeError,raw.RawCaptureError) as error:
        result=dict(status='HOST_CLEANUP_UNPROVED',error_type=type(error).__name__,message=str(error)[:256],
            original_A_recovery_blocked=False,device_actions=0)
    publish(output/'result.json',result);return result
