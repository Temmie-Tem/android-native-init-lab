"""One framed RAM proof and one authenticated Download control on its socket."""
from pathlib import Path
import secrets
import socket
import time

import device_action_raw_capture_v1 as raw
import s22plus_mainline_access_v1 as access
import s22plus_mainline_attach_v1 as attach
import s22plus_mainline_profile_v1 as profile
from s22plus_native_records_v3 import Journal,canonical,clock,host_boot,pin,publish,read,require,verify

ACTION='mainline-download'


def codec(manifest=None):
    # Candidate-only decoding must not prevent stopped-owner original-A
    # recovery merely by being imported with the Session coordinator.
    try:
        if manifest is not None and profile.codec.has_cycle(manifest):
            from mainline.s22plus_canary_h0 import service_ram
            return service_ram
        from mainline.s22plus_canary_h0 import download_ram
        return download_ram
    except (ImportError,SyntaxError) as error:
        raise ValueError('reviewed Download codec is unavailable') from error


def ack_proof(manifest,wire,data,key,identity,nonce,proof):
    extra={'proof':proof} if profile.codec.has_cycle(manifest) else {}
    return wire.verify_ack(data,key,identity,nonce,proof['boot_id'],**extra)


def selected(request):
    return request.get('operation')=='mainline-ram' and 'download_return' in request.get('N',{})


def receive(client,writer,size,deadline):
    received=0
    while received<size:
        remaining=(deadline-clock())/1e9;require(remaining>0,'original Download observation window expired')
        client.settimeout(min(1,remaining))
        try:data=client.recv(min(65536,size-received))
        except socket.timeout:continue
        require(data,'framed Download response ended early')
        writer.write_stdout(data);received+=len(data)


def capture_connection(folder,manifest,found,*,deadline_ns,guard,before_control,connect=None):
    """Raw-first framing; a complete base frame never claims socket EOF."""
    require(profile.codec.has_download(manifest),'unselected Download runtime')
    wire=codec(manifest)
    key=Path(manifest['key_path']).read_bytes();identity=bytes.fromhex(manifest['candidate_id'])
    nonce=secrets.token_bytes(32);packet=profile.codec.request(key,identity,nonce,manifest=manifest)
    request=raw.publish_captured_bytes(folder,'request',stdout=packet,stderr=b'')
    attempt=publish(folder/'attempt.json',dict(request=pin(request.receipt_path),nonce=nonce.hex(),endpoint=found,
        opened_ns=clock(),deadline_ns=deadline_ns,host_boot=host_boot()))
    prefix=raw.RawCaptureWriter(folder,'prefix',stdout_maximum=384,stderr_maximum=0)
    writer=raw.RawCaptureWriter(folder,'response',stdout_maximum=384+profile.codec.FDT_LIMIT,stderr_maximum=0)
    ack_writer=raw.RawCaptureWriter(folder,'ack',stdout_maximum=wire.ACK_SIZE+1,stderr_maximum=0)
    client=None;failure=None;prefix_handle=None;base_handle=None;sent=False;control_sent=False;eof=False;closed=False
    try:
        guard('before-connect');require(clock()<deadline_ns,'original connection window expired')
        client=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        client.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,found['interface'].encode()+b'\0')
        client.bind((manifest['network']['host_ip'],0));client.settimeout(min(3,(deadline_ns-clock())/1e9))
        if connect is None:client.connect((manifest['network']['device_ip'],manifest['port']))
        else:connect(client)
        guard('after-connect');require(clock()<deadline_ns,'connection completed after original window')
        require(client.getsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,64).rstrip(b'\0').decode()==found['interface'],
                'Download socket interface binding differs')
        client.settimeout(min(1,(deadline_ns-clock())/1e9));client.sendall(packet);sent=True
        receive(client,prefix,384,deadline_ns);prefix_handle=prefix.finalize(returncode=0)
        prefix_bytes=raw.read_stdout(prefix_handle,maximum=384)
        writer.write_stdout(prefix_bytes)
        length=wire.frame_size(prefix_bytes)
        receive(client,writer,length-384,deadline_ns);base_handle=writer.finalize(returncode=0)
        finished=clock();require(finished<deadline_ns,'base frame completed after original window')
        publish(folder/'base-complete.json',dict(attempt=attempt,response=pin(base_handle.receipt_path),
            prefix=pin(prefix_handle.receipt_path),sent_complete_request=True,finished_ns=finished,
            framing='length',descriptor_open=True))
        proof=profile.codec.verify_capture(base_handle,manifest,nonce)
        require(proof['download_ready'] is True,'exact reboot-mode binding was not observed')
        command=wire.control(key,identity,nonce,proof['boot_id'])
        control=raw.publish_captured_bytes(folder,'control',stdout=command,stderr=b'')
        before_control(proof,pin(control.receipt_path))
        # The callback has performed the fresh Session check and durable intent.
        # This final check is bounded endpoint/clock validation, not a new grant.
        guard('before-control');require(clock()<deadline_ns,'control dispatch exceeded original window')
        client.settimeout(min(1,(deadline_ns-clock())/1e9));client.sendall(command);control_sent=True
        receive(client,ack_writer,wire.ACK_SIZE,deadline_ns)
        while True:
            remaining=(deadline_ns-clock())/1e9;require(remaining>0,'ACK EOF exceeded original window')
            client.settimeout(min(1,remaining))
            try:extra=client.recv(1)
            except socket.timeout:continue
            if extra:ack_writer.write_stdout(extra);require(False,'extra Download acknowledgment bytes')
            eof=True;break
    except BaseException as error:failure=error
    finally:
        if client is not None:
            try:client.close();closed=True
            except OSError as error:
                if failure is None:failure=error
        finished=clock();error_name=type(failure).__name__ if failure else None
        if prefix_handle is None:prefix_handle=prefix.finalize(returncode=None,producer_error_type=error_name)
        if base_handle is None:base_handle=writer.finalize(returncode=None,producer_error_type=error_name)
        ack=ack_writer.finalize(returncode=0 if failure is None else None,
            timed_out=finished>=deadline_ns,producer_error_type=error_name)
        publish(folder/'connection.json',dict(attempt=attempt,response=pin(base_handle.receipt_path),
            ack=pin(ack.receipt_path),sent_complete_request=sent,sent_complete_control=control_sent,
            eof=eof,descriptor_closed=closed,finished_ns=finished))
    if failure is not None:raise failure
    return ack_proof(manifest,wire,raw.read_stdout(ack,maximum=wire.ACK_SIZE+1),key,identity,nonce,proof)


def rederive_base(adapter,request):
    require(selected(request),'unselected Download evidence')
    folder=adapter.folder(profile.SELECTION);window=read(folder/'window.json');attempt=read(folder/'attempt.json')
    completed=read(folder/'base-complete.json');manifest=profile.image_binding(request['N'])
    require(profile.codec.has_download(manifest) and window==access.window_for(adapter,request) and
            completed['attempt']==pin(folder/'attempt.json') and completed['response']==pin(folder/'response.capture.json') and
            completed['prefix']==pin(folder/'prefix.capture.json') and completed['framing']=='length' and
            completed['descriptor_open'] is True and completed['sent_complete_request'] is True and
            attempt['host_boot']==window['host_boot'] and
            window['opened_ns']<=attempt['opened_ns']<completed['finished_ns']<window['deadline_ns']==attempt['deadline_ns'],
            'Download frame does not join the original window')
    found=read(folder/'endpoint.json')
    require(attempt['endpoint']==found and all(access.endpoint(raw.load_handle(folder/(label+'.capture.json')),manifest)==found
            for label in ('usb-before-connect','usb-after-connect')),'Download base endpoint changed')
    for label in ('network-create','network-up'):access.require_host(raw.load_handle(folder/(label+'.capture.json')))
    nonce=bytes.fromhex(attempt['nonce']);require(len(nonce)==32,'Download nonce length')
    planned=raw.load_handle(verify(attempt['request']));raw.require_success(planned)
    require(raw.read_stdout(planned,maximum=72)==profile.codec.request(Path(manifest['key_path']).read_bytes(),
            bytes.fromhex(manifest['candidate_id']),nonce,manifest=manifest),'retained base request changed')
    prefix=raw.load_handle(verify(completed['prefix']));raw.require_success(prefix)
    prefix_bytes=raw.read_stdout(prefix,maximum=384)
    response=raw.load_handle(verify(completed['response']));raw.require_success(response)
    data=raw.read_stdout(response,maximum=384+profile.codec.FDT_LIMIT)
    require(data[:384]==prefix_bytes and len(data)==codec(manifest).frame_size(prefix_bytes),'sealed frame length differs')
    proof=profile.codec.verify_capture(response,manifest,nonce)
    return dict(action=ACTION,proof=proof,response=completed['response'],base=pin(folder/'base-complete.json'),
        attempt=pin(folder/'attempt.json'),endpoint=pin(folder/'endpoint.json'),window=pin(folder/'window.json'))


def ssh_receipt(adapter,request,base,manifest,closure):
    folder=adapter.folder(profile.SELECTION)
    checked=access.rederive_ssh(adapter,request,base,manifest,not_before_ns=read(verify(closure))['closed_ns'])
    return dict(proof=checked['ssh'],capture=checked['ssh_capture'],intent=checked['ssh_intent'],
                complete=pin(folder/'ssh-complete.json'))


def control_intent(adapter,request):
    folder=adapter.folder(profile.SELECTION);base=rederive_base(adapter,request)
    manifest=profile.image_binding(request['N']);window=read(verify(base['window']))
    value=read(folder/'control-intent.json');grant=read(verify(request['grant']));wire=codec(manifest)
    cycle=profile.codec.has_cycle(manifest)
    require(base['proof']['download_ready'] is True and set(value)=={'operation','base','control','attach',
            'boot_id','candidate_id','requested_ns','deadline_ns','observation_deadline_ns','host_boot'}|({'ssh'} if cycle else set()) and
            value['operation']==pin(adapter.directory/'operation.json') and value['base']==base and
            value['attach']==attach.rederive(adapter.directory,base['window']) and
            value['control']==pin(folder/'control.capture.json') and value['host_boot']==grant['host_boot']==window['host_boot'] and
            value['boot_id']==base['proof']['boot_id'] and value['candidate_id']==manifest['candidate_id'] and
            read(verify(base['base']))['finished_ns']<=read(verify(value['attach']))['closed_ns']<=value['requested_ns']<window['deadline_ns'] and
            value['observation_deadline_ns']==window['deadline_ns'] and
            value['deadline_ns']==min(grant['deadline_ns'],value['requested_ns']+600_000_000_000),
            'Download control intent differs')
    if cycle:
        checked=ssh_receipt(adapter,request,base,manifest,value['attach'])
        require(canonical(value['ssh'])==canonical(checked) and read(verify(checked['complete']))['finished_ns']<=value['requested_ns'],
                'service control does not follow its single same-boot SSH command')
    packet=raw.load_handle(verify(value['control']));raw.require_success(packet)
    require(raw.read_stdout(packet,maximum=wire.CONTROL_SIZE)==wire.control(Path(manifest['key_path']).read_bytes(),
            bytes.fromhex(manifest['candidate_id']),bytes.fromhex(read(verify(base['attempt']))['nonce']),value['boot_id']),
            'retained Download control differs')
    rows=[r['data'] for r in Journal(adapter.directory/'journal').rows() if r['event']=='effect-intent' and
          r['data']['step']==profile.SELECTION]
    require(len(rows)==1 and rows[0]['action']==ACTION and rows[0]['role']=='N' and
            rows[0]['recovery'] is False and rows[0]['detail']==value,'Download lacks its unique Session intent')
    return value


def rederive(adapter,request):
    value=control_intent(adapter,request);folder=adapter.folder(profile.SELECTION)
    base=value['base'];connection=read(folder/'connection.json');manifest=profile.image_binding(request['N'])
    require(connection==dict(attempt=base['attempt'],response=base['response'],ack=pin(folder/'ack.capture.json'),
            sent_complete_request=True,sent_complete_control=True,eof=True,descriptor_closed=True,
            finished_ns=connection['finished_ns']) and
            value['requested_ns']<connection['finished_ns']<value['observation_deadline_ns'],
            'Download control connection incomplete')
    require(access.endpoint(raw.load_handle(folder/'usb-before-control.capture.json'),manifest)==
            read(verify(base['endpoint'])),'Download dispatch endpoint changed')
    ack=raw.load_handle(verify(connection['ack']));raw.require_success(ack)
    wire=codec(manifest)
    accepted=ack_proof(manifest,wire,raw.read_stdout(ack,maximum=wire.ACK_SIZE+1),Path(manifest['key_path']).read_bytes(),
        bytes.fromhex(manifest['candidate_id']),bytes.fromhex(read(verify(base['attempt']))['nonce']),base['proof'])
    if profile.codec.has_cycle(manifest):base=dict(base,ssh=value['ssh']['proof'],ssh_capture=value['ssh']['capture'])
    return dict(base,control=pin(folder/'control-intent.json'),ack=connection['ack'],accepted=accepted,
                connection=pin(folder/'connection.json'))


def return_request(adapter,request,*,create=False):
    intent=control_intent(adapter,request);value=rederive(adapter,request)
    expected=dict(operation=pin(adapter.directory/'operation.json'),observation=pin(adapter.directory/(profile.SELECTION+'.json')),
        control=value['control'],requested_ns=intent['requested_ns'],deadline_ns=intent['deadline_ns'])
    require(read(verify(expected['observation']))==value,'Download return lacks its completed control step')
    path=adapter.directory/'mainline-return-ready.json'
    if create and not path.exists():publish(path,expected)
    require(read(path)==expected,'Download return window was renewed or changed')
    return expected


def observe(adapter,request,guard,before_control):
    require(selected(request),'Download action is not selected')
    manifest=profile.image_binding(request['N']);plan=adapter.configuration(request)['mainline_access']
    folder=adapter.folder(profile.SELECTION,create=True);window=access.window_for(adapter,request)
    window_pin=publish(folder/'window.json',window);deadline=window['deadline_ns'];found=None
    def bound_guard():
        guard();require(clock()<deadline,'original Download observation window expired')
    for number in range(1,121):
        bound_guard();found=access.endpoint(access.capture_endpoint(folder,f'usb-{number:03d}'),manifest)
        if found is not None:break
        time.sleep(min(1,max(0,(deadline-clock())/1e9)))
    require(found is not None,'Download observer USB endpoint did not arrive')
    found=access.configure(plan,manifest,found,folder,bound_guard,deadline_ns=deadline)
    def socket_guard(phase):
        require(phase in ('before-connect','after-connect','before-control'),'unknown socket phase')
        if phase!='before-control':bound_guard()
        else:require(clock()<deadline,'original control window expired')
        require(access.endpoint(access.capture_endpoint(folder,'usb-'+phase),manifest)==found,
                'Download socket endpoint changed')
    def dispatch(proof,packet):
        base=rederive_base(adapter,request);require(base['proof']==proof,'Download base proof changed')
        closure=attach.close_issuance(adapter.directory,window_pin,guard=bound_guard)
        ssh={}
        if profile.codec.has_cycle(manifest):
            access.capture_ssh(folder,manifest,plan,found,proof,deadline_ns=deadline,guard=bound_guard)
            ssh['ssh']=ssh_receipt(adapter,request,base,manifest,closure)
        def detail():
            now=clock();require(now<deadline,'original control intent window expired')
            value=dict(operation=pin(adapter.directory/'operation.json'),base=base,control=packet,attach=closure,
                boot_id=proof['boot_id'],candidate_id=manifest['candidate_id'],requested_ns=now,
                deadline_ns=min(read(verify(request['grant']))['deadline_ns'],now+600_000_000_000),
                observation_deadline_ns=deadline,host_boot=window['host_boot'],**ssh)
            publish(folder/'control-intent.json',value);return value
        before_control(detail)
    capture_connection(folder,manifest,found,deadline_ns=deadline,guard=socket_guard,before_control=dispatch)
    value=rederive(adapter,request);publish(folder/'result.json',value);return value
