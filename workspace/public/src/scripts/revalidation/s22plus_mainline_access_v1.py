"""One exact USB2 NCM observation; raw first, one connection, no control API."""
import errno
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import socket
import time
import uuid

import device_action_raw_capture_v1 as raw
import s22plus_native_target_io_v3 as target
import s22plus_mainline_profile_v1 as profile
from s22plus_native_records_v3 import canonical,clock,digest,host_boot,pin,publish,read,require,verify

USB_FIELDS=('idVendor','idProduct','serial','product','manufacturer','busnum','devnum','speed')
MAX_SYSFS=32768
MAX_RX=profile.codec.RESPONSE+profile.codec.FDT_LIMIT+1


def field(path):
    try:
        with path.open('rb') as stream:value=stream.read(513)
        return dict(hex=value.hex(),errno=None)
    except OSError as error:return dict(hex=None,errno=error.errno)


def capture_endpoint(folder,label,*,usb_root=Path('/sys/bus/usb/devices'),net_root=Path('/sys/class/net')):
    """Only the predeclared USB2 path and its immediate network children."""
    writer=raw.RawCaptureWriter(folder,label,stdout_maximum=MAX_SYSFS,stderr_maximum=0,
                                argv0_name='fixed-mainline-usb2-sysfs')
    topology=target.lane.CANDIDATE_TOPOLOGY
    node=usb_root/topology.removeprefix('usb:')
    try:
        writer.write_stdout(canonical(dict(kind='begin',topology=topology,boottime_ns=clock())))
        try:
            parent=node.resolve(strict=True)
            writer.write_stdout(canonical(dict(kind='usb',errno=None,fields={k:field(node/k) for k in USB_FIELDS})))
        except FileNotFoundError:
            parent=None
            writer.write_stdout(canonical(dict(kind='usb',errno=errno.ENOENT,fields={})))
        related=0
        for count,interface in enumerate(net_root.iterdir(),1):
            require(count<=128,'network inventory exceeds bound')
            try:device=(interface/'device').resolve(strict=True)
            except FileNotFoundError:continue
            if parent is None or device.parent!=parent:continue
            related+=1;require(related<=4,'too many network children on selected USB path')
            try:driver=dict(name=(interface/'device/driver').resolve(strict=True).name,errno=None)
            except OSError as error:driver=dict(name=None,errno=error.errno)
            writer.write_stdout(canonical(dict(kind='interface',name=interface.name,device=str(device),
                address=field(interface/'address'),ifindex=field(interface/'ifindex'),driver=driver)))
        writer.write_stdout(canonical(dict(kind='end',related=related,boottime_ns=clock())))
    except BaseException as error:
        writer.finalize(returncode=None,producer_error_type=type(error).__name__);raise
    return writer.finalize(returncode=0)


def text(value):
    require(set(value)=={'hex','errno'} and value['errno'] is None,'incomplete sysfs field')
    data=bytes.fromhex(value['hex']);require(0<len(data)<=512,'sysfs field length')
    result=data.decode('utf-8').removesuffix('\n')
    require(result and not any(c in result for c in ('\x00','\n','\r')),'invalid sysfs text')
    return result


def endpoint(handle,manifest):
    require(isinstance(handle,raw.RawCaptureHandle),'USB parser requires a sealed capture')
    raw.require_success(handle)
    rows=[json.loads(line) for line in raw.read_stdout(handle,maximum=MAX_SYSFS).splitlines()]
    require(3<=len(rows)<=7 and rows[0]['kind']=='begin' and rows[-1]['kind']=='end' and
            rows[0]['topology']==target.lane.CANDIDATE_TOPOLOGY and
            rows[0]['boottime_ns']<=rows[-1]['boottime_ns'],'USB capture shape/ordering')
    device=rows[1];interfaces=rows[2:-1]
    require(device['kind']=='usb' and len(interfaces)==rows[-1]['related'] and
            all(i['kind']=='interface' for i in interfaces),'USB capture cardinality')
    if device['errno']==errno.ENOENT:
        require(not interfaces and not device['fields'],'absent USB has children');return None
    require(device['errno'] is None and set(device['fields'])==set(USB_FIELDS),'incomplete USB capture')
    fields={k:text(v) for k,v in device['fields'].items()}
    expected=dict(idVendor='1d6b',idProduct='0104',serial=manifest['network']['serial'],
                  product='G0Q RAM Canary',manufacturer='Native Init Lab')
    require(all(fields[k]==v for k,v in expected.items()),'wrong USB device on the bound path')
    require(all(re.fullmatch('[1-9][0-9]{0,5}',fields[k]) for k in ('busnum','devnum')) and
            fields['speed'] in ('12','480'),'unexpected USB generation/speed')
    if not interfaces:return None
    require(len(interfaces)==1,'ambiguous NCM interface')
    interface=interfaces[0]
    require(re.fullmatch('[A-Za-z0-9_.:-]{1,15}',interface['name']) and
            text(interface['address']).lower()==manifest['network']['host_mac'] and
            interface['driver']==dict(name='cdc_ncm',errno=None),'NCM interface identity differs')
    index=text(interface['ifindex']);require(re.fullmatch('[1-9][0-9]{0,9}',index),'invalid ifindex')
    return dict(interface=interface['name'],ifindex=int(index),device=interface['device'],
                topology=target.lane.CANDIDATE_TOPOLOGY,fields=fields,host_mac=manifest['network']['host_mac'])


def host_command(plan,tool,args,folder,label,*,timeout=8):
    profile.unchanged(plan[tool],32*1024*1024)
    return raw.acquire_command([plan[tool]['path'],*args],folder,label,timeout=timeout,
        stdout_maximum=262144,stderr_maximum=16384,env=dict(os.environ,LC_ALL='C',LANG='C'))


def require_host(handle):
    raw.require_success(handle)
    require(not raw.read_stderr(handle,maximum=16384),'host command has diagnostics')


def network_conflicts(handle,manifest,*,own_interface=None):
    require_host(handle)
    rows=json.loads(raw.decode_success_stdout(handle,maximum=262144))
    require(type(rows) is list and len(rows)<=128,'host address inventory bound')
    wanted=ipaddress.IPv4Network(manifest['network']['host_ip']+'/'+manifest['network']['netmask'],strict=False)
    for row in rows:
        require(type(row['ifname']) is str and type(row['addr_info']) is list,'host address shape')
        if row['ifname']==own_interface:continue
        for address in row['addr_info']:
            if address.get('family')!='inet':continue
            actual=ipaddress.IPv4Network(str(address['local'])+'/'+str(address['prefixlen']),strict=False)
            require(not wanted.overlaps(actual),'canary subnet conflicts with another host interface')
    return True


def connection_identity(handle,plan,found):
    require(not handle.timed_out and not handle.output_exceeded and handle.producer_error_type is None,
            'network profile inspection incomplete')
    output=raw.read_stdout(handle,maximum=16384)
    if handle.returncode==10 and not output:return False
    require_host(handle)
    lines=output.decode('utf-8').splitlines()
    require(len(lines)==4 and lines[:2]==[plan['name'],plan['uuid']] and
            lines[2].lower()==found['host_mac'] and lines[3]==found['interface'],
            'network UUID is not this task profile')
    return True


def inspect_connection(plan,folder,label):
    return host_command(plan,'nmcli',['--escape','no','-g',
        'connection.id,connection.uuid,802-3-ethernet.mac-address,connection.interface-name',
        'connection','show','uuid',plan['uuid']],folder,label)


def configure(plan,manifest,found,folder,guard):
    before=host_command(plan,'ip',['-j','address','show'],folder,'addresses-before')
    network_conflicts(before,manifest,own_interface=found['interface'])
    require(not connection_identity(inspect_connection(plan,folder,'profile-before'),plan,found),
            'network UUID was already present')
    publish(folder/'network-intent.json',dict(plan=plan,endpoint=found))
    prefix=ipaddress.IPv4Network('0.0.0.0/'+manifest['network']['netmask']).prefixlen
    args=['connection','add','save','no','type','ethernet','con-name',plan['name'],
        'ifname',found['interface'],'connection.uuid',plan['uuid'],'connection.autoconnect','no',
        '802-3-ethernet.mac-address',found['host_mac'],'ipv4.method','manual',
        'ipv4.addresses',manifest['network']['host_ip']+'/'+str(prefix),'ipv4.never-default','yes',
        'ipv4.ignore-auto-dns','yes','ipv4.ignore-auto-routes','yes','ipv6.method','disabled']
    guard();require_host(host_command(plan,'nmcli',args,folder,'network-create'))
    require(endpoint(capture_endpoint(folder,'usb-before-up'),manifest)==found,'NCM changed before activation')
    guard();require_host(host_command(plan,'nmcli',['connection','up','uuid',plan['uuid'],
        'ifname',found['interface']],folder,'network-up'))
    require(endpoint(capture_endpoint(folder,'usb-after-up'),manifest)==found,'NCM changed during activation')
    require(connection_identity(inspect_connection(plan,folder,'profile-after'),plan,found),'network profile absent')
    route=host_command(plan,'ip',['-j','route','get',manifest['network']['device_ip'],
        'from',manifest['network']['host_ip'],'oif',found['interface']],folder,'route')
    direct_route(route,manifest,found)


def direct_route(route,manifest,found):
    require_host(route);rows=json.loads(raw.decode_success_stdout(route,maximum=262144))
    require(type(rows) is list and len(rows)==1 and rows[0]['dev']==found['interface'] and
            rows[0].get('gateway') is None and rows[0].get('from')==manifest['network']['host_ip'],
            'canary route is not direct on the selected interface')


def capture_connection(folder,manifest,found,*,deadline_ns,guard,connect=None):
    """One attempted TCP connection. No parser or retry can precede raw sealing."""
    nonce=secrets.token_bytes(32)
    maximum=profile.codec.response_size(manifest)+profile.codec.FDT_LIMIT+1
    packet=profile.codec.request(Path(manifest['key_path']).read_bytes(),bytes.fromhex(manifest['candidate_id']),nonce,
                                 manifest=manifest)
    request=raw.RawCaptureWriter(folder,'request',stdout_maximum=len(packet),stderr_maximum=0)
    request.write_stdout(packet);request_handle=request.finalize(returncode=0)
    attempt=publish(folder/'attempt.json',dict(request=pin(request_handle.receipt_path),nonce=nonce.hex(),
        endpoint=found,opened_ns=clock(),deadline_ns=deadline_ns,host_boot=host_boot()))
    writer=raw.RawCaptureWriter(folder,'response',stdout_maximum=maximum,stderr_maximum=0,
        argv0_name='one-mainline-ncm-observation')
    client=None;received=0;sent=False;eof=False;failure=None;finished=None
    try:
        guard();require(clock()<deadline_ns,'original observation window expired')
        client=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        client.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,found['interface'].encode()+b'\0')
        client.bind((manifest['network']['host_ip'],0))
        client.settimeout(min(3,(deadline_ns-clock())/1e9))
        if connect is None:client.connect((manifest['network']['device_ip'],manifest['port']))
        else:connect(client)
        guard();require(clock()<deadline_ns,'connection completed after original window')
        require(client.getsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,64).rstrip(b'\0').decode()==found['interface'],
                'socket interface binding differs')
        client.settimeout(min(1,(deadline_ns-clock())/1e9));client.sendall(packet);sent=True
        while received<maximum:
            remaining=(deadline_ns-clock())/1e9
            require(remaining>0,'response exceeded original window')
            client.settimeout(min(1,remaining))
            try:data=client.recv(min(65536,maximum-received))
            except socket.timeout:continue  # Same connection, never another request.
            if not data:eof=True;break
            writer.write_stdout(data);received+=len(data)
        require(eof and received<maximum,'response is incomplete or exceeds bound')
        require(clock()<deadline_ns,'complete response arrived after original window')
    except BaseException as error:failure=error
    finally:
        if client is not None:
            try:client.close()
            except OSError as error:
                if failure is None:failure=error
        finished=clock()
        handle=writer.finalize(returncode=0 if failure is None else None,
            timed_out=finished>=deadline_ns,output_exceeded=received>=maximum,
            producer_error_type=type(failure).__name__ if failure else None)
        publish(folder/'connection.json',dict(attempt=attempt,response=pin(handle.receipt_path),
            sent_complete_request=sent,eof=eof,finished_ns=finished,descriptor_closed=True))
    if failure is not None:raise failure
    return handle


def rederive_base(adapter,request):
    folder=adapter.folder(profile.SELECTION)
    window=read(folder/'window.json');attempt=read(folder/'attempt.json');connection=read(folder/'connection.json')
    manifest=profile.image_binding(request['N'])
    wanted=window_for(adapter,request)
    require(window['operation']==pin(adapter.directory/'operation.json') and
            window['host_boot']==attempt['host_boot']==wanted['host_boot'] and
            connection['attempt']==pin(folder/'attempt.json') and
            connection['response']==pin(folder/'response.capture.json') and
            connection['sent_complete_request'] is True and connection['eof'] is True and
            connection['descriptor_closed'] is True and
            window['opened_ns']<=attempt['opened_ns']<connection['finished_ns']<window['deadline_ns']==attempt['deadline_ns'],
            'observation does not join its original complete window')
    require(window==wanted,'mainline observation window changed')
    selected=read(folder/'endpoint.json')
    require(attempt['endpoint']==selected and
            endpoint(raw.load_handle(folder/'usb-before-connect.capture.json'),manifest)==selected and
            endpoint(raw.load_handle(folder/'usb-after-connect.capture.json'),manifest)==selected and
            endpoint(raw.load_handle(folder/'usb-after-response.capture.json'),manifest)==selected,'NCM continuity differs')
    require_host(raw.load_handle(folder/'network-create.capture.json'))
    require_host(raw.load_handle(folder/'network-up.capture.json'))
    nonce=bytes.fromhex(attempt['nonce']);require(len(nonce)==32,'nonce length differs')
    planned=raw.load_handle(verify(attempt['request']))
    raw.require_success(planned)
    expected=profile.codec.request(Path(manifest['key_path']).read_bytes(),bytes.fromhex(manifest['candidate_id']),nonce,
                                   manifest=manifest)
    require(raw.read_stdout(planned,maximum=72)==expected,'retained request differs')
    proof=profile.codec.verify_capture(raw.load_handle(verify(connection['response'])),manifest,nonce)
    return dict(action='mainline-evidence',proof=proof,response=connection['response'],attempt=pin(folder/'attempt.json'),
                endpoint=pin(folder/'endpoint.json'),window=pin(folder/'window.json'))


def capture_ssh(folder,manifest,plan,found,proof,*,deadline_ns,guard):
    """Exactly one standard SSH invocation, inside the original N window."""
    from mainline.s22plus_canary_h0 import ssh_ram
    require(profile.codec.has_ssh(manifest) and proof.get('ssh_ready') is True,'SSH startup not proved')
    runtime=manifest['debian_ram']
    known=raw.publish_captured_bytes(folder,'ssh-known-hosts',stdout=ssh_ram.known_hosts(runtime),stderr=b'',
        argv0_name='fixed-mainline-ssh-host-key')
    argv=ssh_ram.command(runtime,plan['ssh']['path'],known.stdout_path,manifest['network']['device_ip'],
                         source=manifest['network']['host_ip'])
    guard()
    require(endpoint(capture_endpoint(folder,'usb-before-ssh'),manifest)==found,'NCM changed before SSH')
    # OpenSSH -b binds an address, not SO_BINDTODEVICE. Check the actual
    # unconstrained route from that address rather than forcing an oif result.
    route=host_command(plan,'ip',['-j','route','get',manifest['network']['device_ip'],
        'from',manifest['network']['host_ip']],folder,'ssh-route')
    direct_route(route,manifest,found)
    opened=clock();acquisition_deadline=deadline_ns-4_000_000_000
    timeout=min(20.0,(acquisition_deadline-opened)/1e9-0.1)
    require(timeout>=0.1,'original SSH observation window exhausted')
    intent=publish(folder/'ssh-intent.json',dict(argv=argv,executable=plan['ssh'],known_hosts=pin(known.receipt_path),
        endpoint=found,opened_ns=opened,deadline_ns=deadline_ns,acquisition_deadline_ns=acquisition_deadline,timeout_seconds=timeout,
        host_boot=host_boot(),boot_id=proof['boot_id']))
    def before_spawn():
        guard();profile.unchanged(plan['ssh'],32*1024*1024)
        require(clock()+int(timeout*1e9)<acquisition_deadline,'SSH spawn would exceed original window')
    handle=raw.acquire_command(argv,folder,'ssh',timeout=timeout,stdout_maximum=1024,stderr_maximum=16384,
        env={'LANG':'C','LC_ALL':'C','PATH':'/usr/bin:/bin'},before_spawn=before_spawn,
        boottime_deadline_ns=acquisition_deadline)
    finished=clock()
    publish(folder/'ssh-complete.json',dict(intent=intent,capture=pin(handle.receipt_path),finished_ns=finished))
    # Raw status and both streams are already durable before any interpretation.
    raw.require_success(handle)
    require(finished<deadline_ns,'SSH completed after original observation window')
    require(not raw.read_stderr(handle,maximum=16384),'SSH has diagnostics')
    require(endpoint(capture_endpoint(folder,'usb-after-ssh'),manifest)==found,'NCM changed during SSH')
    return ssh_ram.parse_stdout(raw.read_stdout(handle,maximum=1024),proof['boot_id'])


def rederive(adapter,request):
    value=rederive_base(adapter,request)
    manifest=profile.image_binding(request['N'])
    if not profile.codec.has_ssh(manifest):return value
    from mainline.s22plus_canary_h0 import ssh_ram
    require(value['proof']['ssh_ready'] is True,'SSH startup absent')
    folder=adapter.folder(profile.SELECTION);window=read(folder/'window.json');found=read(folder/'endpoint.json')
    intent=read(folder/'ssh-intent.json');complete=read(folder/'ssh-complete.json')
    plan=adapter.configuration(request)['mainline_access']
    known=raw.load_handle(verify(intent['known_hosts']));raw.require_success(known)
    require(known.receipt_path==folder/'ssh-known-hosts.capture.json' and
            raw.read_stdout(known,maximum=256)==ssh_ram.known_hosts(manifest['debian_ram']) and
            not raw.read_stderr(known,maximum=16384),'SSH host key pin differs')
    argv=ssh_ram.command(manifest['debian_ram'],plan['ssh']['path'],known.stdout_path,
        manifest['network']['device_ip'],source=manifest['network']['host_ip'])
    require(set(intent)=={'argv','executable','known_hosts','endpoint','opened_ns','deadline_ns','acquisition_deadline_ns','timeout_seconds',
                          'host_boot','boot_id'} and intent['argv']==argv and intent['executable']==plan['ssh'] and
            intent['endpoint']==found and intent['host_boot']==window['host_boot'] and
            intent['boot_id']==value['proof']['boot_id'] and intent['deadline_ns']==window['deadline_ns'] and
            intent['acquisition_deadline_ns']==window['deadline_ns']-4_000_000_000 and
            type(intent['timeout_seconds']) in (int,float) and 0.1<=intent['timeout_seconds']<=20 and
            intent['opened_ns']+int(intent['timeout_seconds']*1e9)<intent['acquisition_deadline_ns'] and
            read(folder/'connection.json')['finished_ns']<=intent['opened_ns']<complete['finished_ns']<window['deadline_ns'] and
            complete==dict(intent=pin(folder/'ssh-intent.json'),capture=pin(folder/'ssh.capture.json'),
                           finished_ns=complete['finished_ns']), 'SSH attempt/window binding differs')
    require(endpoint(raw.load_handle(folder/'usb-before-ssh.capture.json'),manifest)==found and
            endpoint(raw.load_handle(folder/'usb-after-ssh.capture.json'),manifest)==found,'SSH USB continuity differs')
    direct_route(raw.load_handle(folder/'ssh-route.capture.json'),manifest,found)
    handle=raw.load_handle(verify(complete['capture']));raw.require_success(handle)
    require(not raw.read_stderr(handle,maximum=16384),'SSH diagnostics')
    value['ssh']=ssh_ram.parse_stdout(raw.read_stdout(handle,maximum=1024),value['proof']['boot_id'])
    value['ssh_capture']=complete['capture'];value['ssh_intent']=complete['intent']
    return value


def window_for(adapter,request):
    from s22plus_native_session_v3 import Step
    receipt=adapter.recover_transfer_result(Step('install-native-first','transfer','N'),request)['launch']
    launch=read(verify(receipt))
    grant=read(verify(request['grant']))
    return dict(operation=pin(adapter.directory/'operation.json'),candidate_launch=receipt,host_boot=grant['host_boot'],
        opened_ns=launch['boottime_ns'],deadline_ns=min(grant['deadline_ns'],launch['boottime_ns']+profile.OBSERVATION_NS))


def observe(adapter,request,guard):
    manifest=profile.image_binding(request['N']);plan=adapter.configuration(request)['mainline_access']
    folder=adapter.folder(profile.SELECTION,create=True);window=window_for(adapter,request)
    publish(folder/'window.json',window);deadline=window['deadline_ns'];found=None
    for number in range(1,121):
        guard();require(clock()<deadline,'canary USB observation window expired')
        found=endpoint(capture_endpoint(folder,f'usb-{number:03d}'),manifest)
        if found is not None:break
        time.sleep(min(1,max(0,(deadline-clock())/1e9)))
    require(found is not None,'canary USB endpoint did not arrive')
    publish(folder/'endpoint.json',found)
    def bound_guard():
        guard();require(clock()<deadline,'original mainline window expired')
    configure(plan,manifest,found,folder,bound_guard)
    guard_calls=0
    def socket_guard():
        nonlocal guard_calls
        bound_guard()
        guard_calls+=1;require(guard_calls<=2,'unexpected additional socket guard')
        value=capture_endpoint(folder,'usb-before-connect' if guard_calls==1 else 'usb-after-connect')
        require(endpoint(value,manifest)==found,'NCM changed at socket connection')
    capture_connection(folder,manifest,found,deadline_ns=deadline,guard=socket_guard)
    require(endpoint(capture_endpoint(folder,'usb-after-response'),manifest)==found,'NCM changed during response')
    if profile.codec.has_ssh(manifest):
        base=rederive_base(adapter,request)
        capture_ssh(folder,manifest,plan,found,base['proof'],deadline_ns=deadline,guard=bound_guard)
    value=rederive(adapter,request)
    publish(folder/'result.json',value)
    return value


def cleanup(adapter,request):
    """Owned UUID only, after A handling. Never a precondition for device recovery."""
    try:return _cleanup(adapter,request)
    except Exception as error:
        return dict(status='HOST_CLEANUP_UNPROVED',error_type=type(error).__name__,device_recovery_blocked=False)


def _cleanup(adapter,request):
    folder=adapter.folder(profile.SELECTION)
    if not (folder/'network-intent.json').exists():return dict(status='NOT_CREATED')
    output=folder/('cleanup-'+uuid.uuid4().hex)
    try:
        output.mkdir(mode=0o700)
        original=read(folder/'network-intent.json');plan=adapter.configuration(request)['mainline_access']
        found=read(folder/'endpoint.json')
        require(original==dict(plan=plan,endpoint=found),'cleanup lacks exact owned network intent')
        exists=connection_identity(inspect_connection(plan,output,'before'),plan,found)
        if exists:
            require_host(host_command(plan,'nmcli',['connection','delete','uuid',plan['uuid']],output,'delete'))
            require(not connection_identity(inspect_connection(plan,output,'after'),plan,found),'owned network profile remains')
        result=dict(status='REMOVED' if exists else 'ALREADY_ABSENT',device_recovery_blocked=False)
    except Exception as error:result=dict(status='HOST_CLEANUP_UNPROVED',error_type=type(error).__name__,device_recovery_blocked=False)
    try:publish(output/'result.json',result)
    except Exception:pass
    return result
