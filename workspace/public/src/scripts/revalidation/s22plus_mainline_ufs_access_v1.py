"""ML030 same-socket late witness, one module permit and conditional Download."""
from pathlib import Path
import hashlib
import secrets
import time
import uuid

import device_action_raw_capture_v1 as raw
import s22plus_mainline_access_v1 as access
import s22plus_mainline_attach_v1 as attach
import s22plus_mainline_download_access_v1 as download
import s22plus_mainline_profile_v1 as profile
from s22plus_native_records_v3 import Journal, clock, host_boot, pin, publish, read, require, verify
from mainline.s22plus_ufs_link_h0 import link_wire as wire

LATE_NS=540_000_000_000
GAP_NS=300_000_000_000
RETURN_EVENT='ml030-return-intent'


def selected(request):
    return download.selected(request) and request['N'].get('ufs_link') is True


def late_window(adapter,request):
    base=access.window_for(adapter,request)
    grant=read(verify(request['grant']))
    return dict(initial=pin(adapter.folder(profile.SELECTION)/'window.json'),host_boot=base['host_boot'],
                opened_ns=base['opened_ns'],deadline_ns=min(grant['deadline_ns'],base['opened_ns']+LATE_NS))


def capture_frame(client,folder,name,size,deadline):
    writer=raw.RawCaptureWriter(folder,name,stdout_maximum=size,stderr_maximum=0)
    try:
        download.receive(client,writer,size,deadline)
    except BaseException as error:
        writer.finalize(returncode=None,timed_out=clock()>=deadline,producer_error_type=type(error).__name__)
        raise
    return writer.finalize(returncode=0)


def bytes_for(folder,label,maximum):
    handle=raw.load_handle(folder/(label+'.capture.json'))
    raw.require_success(handle)
    return raw.read_stdout(handle,maximum=maximum)


def wire_identity(manifest,base):
    key=Path(manifest['key_path']).read_bytes()
    identity=bytes.fromhex(manifest['candidate_id'])
    first=bytes.fromhex(read(verify(base['attempt']))['nonce'])
    boot=uuid.UUID(base['proof']['boot_id']).bytes
    return key,identity,first,boot,base['proof']['uptime_ms']


def rederive_witness(adapter,request):
    require(selected(request),'ML030 witness selection')
    folder=adapter.folder(profile.SELECTION)
    base=download.rederive_base(adapter,request)
    manifest=profile.image_binding(request['N'])
    window=read(folder/'late-window.json')
    require(window==late_window(adapter,request),'ML030 original late window')
    issuance=attach.rederive(adapter.directory,base['window'])
    first_done=read(verify(base['base']))['finished_ns']
    closed=read(verify(issuance))['closed_ns']
    intent=read(folder/'witness-intent.json'); completed=read(folder/'witness-complete.json')
    require(intent==dict(base=base,attach=issuance,window=pin(folder/'late-window.json'),
            query=pin(folder/'late-query.capture.json'),requested_ns=intent['requested_ns']) and
            completed==dict(intent=pin(folder/'witness-intent.json'),reply=pin(folder/'witness.capture.json'),
                            finished_ns=completed['finished_ns']) and
            first_done<=closed<read(verify(base['window']))['deadline_ns'] and
            first_done+GAP_NS<=intent['requested_ns']<completed['finished_ns']<window['deadline_ns'],
            'ML030 witness ordering or records')
    key,identity,n0,boot,t0=wire_identity(manifest,base)
    query=bytes_for(folder,'late-query',wire.HEADER.size+32)
    require(len(query)==wire.HEADER.size+32,'ML030 query size')
    n1=wire.HEADER.unpack_from(query)[3]
    require(query==wire.frame(b'G030ASK1',16,key,identity,n0,n1,boot,t0,0),'ML030 fresh challenge')
    reply=bytes_for(folder,'witness',wire.HEADER.size+32)
    t1=wire.witness(reply,key,identity,n0,n1,boot,t0)
    endpoint=read(verify(base['endpoint']))
    require(access.endpoint(raw.load_handle(folder/'usb-before-witness.capture.json'),manifest)==endpoint,
            'ML030 witness endpoint changed')
    return dict(base=base,window=pin(folder/'late-window.json'),witness=pin(folder/'witness-complete.json'),
                boot_id=base['proof']['boot_id'],uptime_ms=t1,host_gap_ns=intent['requested_ns']-first_done)


def permit_intent(adapter,request):
    witness=rederive_witness(adapter,request);folder=adapter.folder(profile.SELECTION)
    manifest=profile.image_binding(request['N']);value=read(folder/'permit-intent.json')
    require(value==dict(operation=pin(adapter.directory/'operation.json'),witness=witness,
            permit=pin(folder/'permit.capture.json'),requested_ns=value['requested_ns'],
            deadline_ns=read(verify(witness['window']))['deadline_ns'],host_boot=read(verify(witness['window']))['host_boot']) and
            read(verify(witness['witness']))['finished_ns']<=value['requested_ns']<value['deadline_ns'],
            'ML030 permit intent binding')
    key,identity,n0,boot,t0=wire_identity(manifest,witness['base'])
    reply=bytes_for(folder,'witness',wire.HEADER.size+32);n1=wire.HEADER.unpack_from(reply)[3]
    require(bytes_for(folder,'permit',wire.HEADER.size+32)==wire.frame(b'G030GO01',18,key,identity,n0,n1,boot,t0,witness['uptime_ms']),
            'ML030 permit bytes')
    rows=[r['data'] for r in Journal(adapter.directory/'journal').rows() if r['event']=='effect-intent' and
          r['data']['step']==profile.SELECTION]
    require(len(rows)==1 and rows[0]['action']==download.ACTION and rows[0]['role']=='N' and
            rows[0]['recovery'] is False and rows[0]['detail']==value,'ML030 unique compound intent')
    return value


def rederive_link(adapter,request):
    """Independent of Download intent, ACK, step completion, rollback and health."""
    intent=permit_intent(adapter,request);folder=adapter.folder(profile.SELECTION)
    manifest=profile.image_binding(request['N']);base=intent['witness']['base']
    sent=read(folder/'permit-sent.json');done=read(folder/'link-complete.json')
    require(sent==dict(intent=pin(folder/'permit-intent.json'),sent_ns=sent['sent_ns']) and
            done==dict(permit=pin(folder/'permit-sent.json'),response=pin(folder/'link.capture.json'),finished_ns=done['finished_ns']) and
            intent['requested_ns']<=sent['sent_ns']<done['finished_ns']<intent['deadline_ns'],
            'ML030 result does not follow original permit')
    require(access.endpoint(raw.load_handle(folder/'usb-before-permit.capture.json'),manifest)==read(verify(base['endpoint'])),
            'ML030 dispatch endpoint changed')
    key,identity,_,_,_=wire_identity(manifest,base)
    data=bytes_for(folder,'link',wire.RESULT_SIZE)
    facts=wire.result(data,bytes_for(folder,'witness',wire.HEADER.size+32),key,identity)
    if 'control_nonce' in facts:facts=dict(facts,control_nonce=facts['control_nonce'].hex())
    return dict(base=base,witness=intent['witness'],result=facts,response=done['response'],complete=pin(folder/'link-complete.json'))


def return_intent(adapter,request):
    link=rederive_link(adapter,request);folder=adapter.folder(profile.SELECTION)
    require(link['result']['normal_return'] is True,'ML030 link cannot authorize normal return')
    value=read(folder/'control-intent.json');window=read(verify(link['witness']['window']))
    grant=read(verify(request['grant']))
    require(value==dict(operation=pin(adapter.directory/'operation.json'),link=link,control=pin(folder/'control.capture.json'),
            requested_ns=value['requested_ns'],deadline_ns=min(grant['deadline_ns'],value['requested_ns']+600_000_000_000),
            observation_deadline_ns=window['deadline_ns'],host_boot=window['host_boot']) and
            read(verify(link['complete']))['finished_ns']<=value['requested_ns']<window['deadline_ns'],
            'ML030 return intent ordering')
    rows=[r for r in Journal(adapter.directory/'journal').rows() if r['event']==RETURN_EVENT]
    require(len(rows)==1 and rows[0]['data']==dict(step=profile.SELECTION,intent=pin(folder/'control-intent.json')) and
            value['requested_ns']<=rows[0]['boottime_ns']<window['deadline_ns'],'ML030 unique conditional return intent')
    manifest=profile.image_binding(request['N']);key,identity,_,_,_=wire_identity(manifest,link['base'])
    require(bytes_for(folder,'control',download.codec(manifest).CONTROL_SIZE)==download.codec(manifest).control(
            key,identity,bytes.fromhex(link['result']['control_nonce']),link['base']['proof']['boot_id']),
            'ML030 return does not bind the complete signed result')
    return value


def rederive_return(adapter,request):
    intent=return_intent(adapter,request);folder=adapter.folder(profile.SELECTION)
    link=intent['link'];base=link['base'];connection=read(folder/'connection.json')
    manifest=profile.image_binding(request['N'])
    require(connection==dict(attempt=base['attempt'],response=base['response'],ack=pin(folder/'ack.capture.json'),
            sent_complete_request=True,sent_complete_control=True,eof=True,descriptor_closed=True,
            finished_ns=connection['finished_ns']) and
            intent['requested_ns']<connection['finished_ns']<intent['observation_deadline_ns'], 'ML030 return connection incomplete')
    require(access.endpoint(raw.load_handle(folder/'usb-before-control.capture.json'),manifest)==read(verify(base['endpoint'])),
            'ML030 return endpoint changed')
    key,identity,_,_,_=wire_identity(manifest,base);codec=download.codec(manifest)
    accepted=codec.verify_ack(bytes_for(folder,'ack',codec.ACK_SIZE+1),key,identity,
                              bytes.fromhex(link['result']['control_nonce']),base['proof']['boot_id'])
    return dict(base,action=download.ACTION,accepted=accepted,link=link,
                control=pin(folder/'control-intent.json'),ack=pin(folder/'ack.capture.json'),connection=pin(folder/'connection.json'))


def observe(adapter,request,guard,before_permit):
    require(selected(request),'ML030 observation selection')
    manifest=profile.image_binding(request['N']);folder=adapter.folder(profile.SELECTION,create=True)
    window=access.window_for(adapter,request);window_pin=publish(folder/'window.json',window)
    late=late_window(adapter,request);publish(folder/'late-window.json',late)
    def checked_endpoint(phase,limit):
        guard();require(clock()<limit,'ML030 dispatch window expired')
        require(access.endpoint(access.capture_endpoint(folder,'usb-'+phase),manifest)==found,'ML030 endpoint changed')
        require(clock()<limit,'ML030 endpoint capture exceeded window')
    def initial_guard():
        guard();require(clock()<window['deadline_ns'],'ML030 first observation expired')
    found=None
    for number in range(1,121):
        initial_guard();found=access.endpoint(access.capture_endpoint(folder,f'usb-{number:03d}'),manifest)
        if found is not None:break
        time.sleep(min(1,max(0,(window['deadline_ns']-clock())/1e9)))
    require(found is not None,'ML030 USB endpoint absent')
    found=access.configure(adapter.configuration(request)['mainline_access'],manifest,found,folder,initial_guard,
                           deadline_ns=window['deadline_ns'])
    def socket_guard(phase):
        require(phase in ('before-connect','after-connect','before-control'),'ML030 socket phase')
        checked_endpoint(phase,late['deadline_ns'] if phase=='before-control' else window['deadline_ns'])
    def after_base(client,proof,nonce):
        base=download.rederive_base(adapter,request);require(base['proof']==proof,'ML030 W0 changed')
        closure=attach.close_issuance(adapter.directory,window_pin,guard=initial_guard)
        ready=read(verify(base['base']))['finished_ns']+GAP_NS
        require(ready<late['deadline_ns'],'ML030 witness cannot fit original window')
        while clock()<ready:
            time.sleep(min(1,max(0,(ready-clock())/1e9)))
        checked_endpoint('before-witness',late['deadline_ns'])
        n1=secrets.token_bytes(32);key,identity,n0,boot,t0=wire_identity(manifest,base)
        require(nonce==n0,'ML030 W0 nonce changed')
        query=wire.frame(b'G030ASK1',16,key,identity,n0,n1,boot,t0,0)
        packet=raw.publish_captured_bytes(folder,'late-query',stdout=query,stderr=b'')
        publish(folder/'witness-intent.json',dict(base=base,attach=closure,window=pin(folder/'late-window.json'),
                query=pin(packet.receipt_path),requested_ns=clock()))
        require(clock()<late['deadline_ns'],'ML030 late query expired')
        client.settimeout(min(1,(late['deadline_ns']-clock())/1e9));client.sendall(query)
        reply=capture_frame(client,folder,'witness',wire.HEADER.size+32,late['deadline_ns'])
        publish(folder/'witness-complete.json',dict(intent=pin(folder/'witness-intent.json'),reply=pin(reply.receipt_path),finished_ns=clock()))
        witness=rederive_witness(adapter,request)
        permit=wire.frame(b'G030GO01',18,key,identity,n0,n1,boot,t0,witness['uptime_ms'])
        planned=raw.publish_captured_bytes(folder,'permit',stdout=permit,stderr=b'')
        def detail():
            value=dict(operation=pin(adapter.directory/'operation.json'),witness=witness,permit=pin(planned.receipt_path),
                       requested_ns=clock(),deadline_ns=late['deadline_ns'],host_boot=host_boot())
            require(value['requested_ns']<late['deadline_ns'],'ML030 permit publication expired')
            publish(folder/'permit-intent.json',value)
            return value
        before_permit(detail)
        permit_intent(adapter,request)
        checked_endpoint('before-permit',late['deadline_ns'])
        client.settimeout(min(1,(late['deadline_ns']-clock())/1e9));client.sendall(permit)
        publish(folder/'permit-sent.json',dict(intent=pin(folder/'permit-intent.json'),sent_ns=clock()))
        result=capture_frame(client,folder,'link',wire.RESULT_SIZE,late['deadline_ns'])
        publish(folder/'link-complete.json',dict(permit=pin(folder/'permit-sent.json'),response=pin(result.receipt_path),finished_ns=clock()))
        link=rederive_link(adapter,request)
        require(link['result']['normal_return'],'ML030 hardware result stops normal control')
        return bytes.fromhex(link['result']['control_nonce']),late['deadline_ns']
    def before_return(proof,packet):
        link=rederive_link(adapter,request);require(link['base']['proof']==proof and link['result']['normal_return'],'ML030 return condition')
        guard();now=clock();require(now<late['deadline_ns'],'ML030 return intent expired')
        grant=read(verify(request['grant']))
        value=dict(operation=pin(adapter.directory/'operation.json'),link=link,control=packet,requested_ns=now,
                   deadline_ns=min(grant['deadline_ns'],now+600_000_000_000),observation_deadline_ns=late['deadline_ns'],host_boot=host_boot())
        receipt=publish(folder/'control-intent.json',value)
        journal=Journal(adapter.directory/'journal')
        require(not any(row['event']==RETURN_EVENT for row in journal.rows()),'ML030 return already consumed')
        journal.append(RETURN_EVENT,step=profile.SELECTION,intent=receipt)
        return_intent(adapter,request)
        guard();require(clock()<late['deadline_ns'],'ML030 final return guard expired')
    download.capture_connection(folder,manifest,found,deadline_ns=window['deadline_ns'],guard=socket_guard,
                                before_control=before_return,after_base=after_base)
    value=rederive_return(adapter,request);publish(folder/'result.json',value)
    return value
