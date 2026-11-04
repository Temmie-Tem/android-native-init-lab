"""Actual observer Download protocol cases in QEMU, never Samsung PMIC proof."""
import json
from pathlib import Path
import socket
import time
import uuid

if __package__:
    from .prepare import digest,require
    from . import download_ram as codec,verify
else:
    from prepare import digest,require
    import download_ram as codec
    import verify

CASES=('positive','wrong-control-key','wrong-boot','legacy-command','extra-tail','partial-control','missing-eof')
SSH_CASES=tuple('ssh-'+case for case in ('wrong-key','root','forced-command','pty','forwarding','sftp'))
EVIDENCE={'control.raw','ack.raw','download-case.json','qmp.raw','qmp-command.json'}


def open_monitor(path,output,persist):
    """H0 QEMU events only; the sole command enables event delivery."""
    command=b'{"execute":"qmp_capabilities"}\n'
    persist(output/'qmp-command.json',command)
    client=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);client.settimeout(2)
    try:client.connect(str(path));client.sendall(command)
    except BaseException:client.close();raise
    return dict(client=client,closed=False)


def finish_monitor(monitor,output,persist):
    if monitor['closed']:return
    data=bytearray();client=monitor['client']
    try:
        while len(data)<16385:
            chunk=client.recv(min(4096,16385-len(data)))
            if not chunk:break
            data.extend(chunk)
    finally:
        client.close();monitor['closed']=True;persist(output/'qmp.raw',bytes(data))
    require(len(data)<16385,'QEMU monitor exceeded bound')


def reset_event(directory,*,expected):
    require((directory/'qmp-command.json').read_bytes()==b'{"execute":"qmp_capabilities"}\n','unexpected QEMU monitor command')
    data=(directory/'qmp.raw').read_bytes();require(len(data)<=16384,'QEMU monitor raw bound')
    rows=[json.loads(row) for row in data.splitlines()]
    require(rows and 'QMP' in rows[0] and any(row.get('return')=={} for row in rows) and
            not any('error' in row for row in rows),'QEMU event channel incomplete')
    events=[row for row in rows if row.get('event')=='SHUTDOWN' and row.get('data',{}).get('guest') is True and
            row['data'].get('reason')=='guest-reset']
    require(len(events)==int(expected),'QEMU guest-reset event differs')
    shutdowns=[row for row in rows if row.get('event')=='SHUTDOWN']
    require(len(shutdowns)==1 and shutdowns[0]['data']==
            dict(guest=expected,reason='guest-reset' if expected else 'host-signal'),
            'VM termination is not the selected guest reset or host stop')
    return events


def wire_for(manifest):
    if not verify.has_cycle(manifest):return codec
    if __package__:
        from . import service_ram
    else:
        import service_ram
    return service_ram


def ack_proof(wire,data,key,identity,nonce,proof):
    extra={} if wire is codec else {'proof':proof}
    return wire.verify_ack(data,key,identity,nonce,proof['boot_id'],**extra)


def exchange(client,output,manifest,nonce,case,persist,*,before_control=None):
    wire=wire_for(manifest)
    require(case in CASES or wire is not codec and case in SSH_CASES,'unselected Download VM case')
    data=bytearray();ack=bytearray();command=b''
    try:
        def exact(size):
            while len(data)<size:
                chunk=client.recv(min(65536,size-len(data)))
                require(chunk,'VM Download base frame truncated');data.extend(chunk)
        exact(384)
        # Retain the prefix before interpreting even its length.
        persist(output/'prefix.raw',bytes(data))
        exact(wire.frame_size(bytes(data)))
        persist(output/'response.raw',bytes(data))
        proof=verify.verify(output/'response.raw',manifest,nonce,vm=True)
        require(proof['download_ready'] is True,'VM fixture readiness absent')
        if before_control is not None:before_control(proof)
        key=Path(manifest['key_path']).read_bytes();identity=bytes.fromhex(manifest['candidate_id'])
        boot=proof['boot_id']
        if case=='wrong-control-key':key=bytes([key[0]^1])+key[1:]
        if case=='wrong-boot':boot=str(uuid.UUID(int=uuid.UUID(boot).int^1))
        command=wire.control(key,identity,nonce,boot)
        if case=='legacy-command':
            head=b'G0QSRQ1\0'+command[8:56];command=head+wire.tag(key,identity,2,head)
        if case=='extra-tail':command+=b'X'
        if case=='partial-control':command=command[:1]
        if case in SSH_CASES:command=b''  # SSH capability check only; no control consent for this case.
        persist(output/'control.raw',command)
        if command:client.sendall(command)
        if case=='partial-control' or case in SSH_CASES:client.shutdown(socket.SHUT_WR)
        while len(ack)<=wire.ACK_SIZE:
            chunk=client.recv(wire.ACK_SIZE+1-len(ack))
            if not chunk:break
            ack.extend(chunk)
        persist(output/'ack.raw',bytes(ack))
        expected_ack=case in ('positive','extra-tail','missing-eof')
        if expected_ack:ack_proof(wire,bytes(ack),key,identity,nonce,proof)
        else:require(not ack,'rejected Download command produced an ACK')
        if case=='missing-eof':
            # Keep this original socket open through the observer's original
            # 120-second deadline. No retransmit, reconnect, or clock renewal.
            until=time.monotonic()+125
            while time.monotonic()<until:
                text=(output/'serial.log').read_bytes()
                if b'G0Q_RAM_PARK error=110' in text:break
                require(b'G0Q_DOWNLOAD_RESTART2_PREPARED' not in text,'missing EOF caused a reset')
                time.sleep(.1)
            else:require(False,'missing EOF did not reach original deadline')
        persist(output/'download-case.json',json.dumps(dict(case=case,expected_ack=expected_ack,
            base_framing='length',pmic_hardware_proved=False),sort_keys=True).encode()+b'\n')
        return data
    finally:
        for name,value in (('response.raw',data),('control.raw',command),('ack.raw',ack)):
            if not (output/name).exists():persist(output/name,bytes(value))


def settled(output,proc,case,monitor,persist):
    until=time.monotonic()+10
    while time.monotonic()<until:
        serial=(output/'serial.log').read_bytes()
        if case=='positive' and proc.poll() is not None:break
        if case!='positive' and b'G0Q_RAM_PARK error=' in serial:break
        time.sleep(.05)
    if case=='positive':
        require(proc.poll()==0 and serial.count(b'G0Q_DOWNLOAD_RESTART2_PREPARED')==1,'actual VM process reset not proved')
        finish_monitor(monitor,output,persist);reset_event(output,expected=True)
    else:
        errors={'wrong-control-key':13,'wrong-boot':13,'legacy-command':13,'extra-tail':71,
                'partial-control':32,'missing-eof':110,**dict.fromkeys(SSH_CASES,32)}
        require(proc.poll() is None and b'G0Q_DOWNLOAD_RESTART2_PREPARED' not in serial and
                ('G0Q_RAM_PARK error='+str(errors[case])).encode() in serial,'Download rejection/reset exclusion differs')


def check_case(directory,manifest,manifest_pin,kernel,case):
    if __package__:
        from .debian_ram import pin
    else:
        from debian_ram import pin
    directory=Path(directory);capture=json.loads((directory/'capture.json').read_text())
    wire=wire_for(manifest);cycle=wire is not codec
    require((case in CASES or cycle and case in SSH_CASES) and capture['device_actions']==0 and capture['bad_key'] is False and
            capture['inputs']['manifest']=={k:manifest_pin[k] for k in ('path','sha256')} and
            capture['inputs']['kernel']=={k:kernel[k] for k in ('path','sha256')},'Download VM inputs differ')
    ssh_files={'ssh.capture.json','ssh.stdout.bin','ssh.stderr.bin','ssh-command.json','known-hosts'} if cycle else set()
    require(set(capture['evidence'])=={'command.json','nonce.bin','request.raw','response.raw','serial.log','qemu.stderr','prefix.raw'}|EVIDENCE|ssh_files,
            'Download complete VM raw evidence required')
    for name,sha in capture['evidence'].items():require(digest(directory/name)==sha,'Download VM raw changed')
    require({'download_vm.py','download_ram.py'}<=set(capture['source']),'Download VM producer provenance missing')
    if cycle:
        require(capture['schema']=='g0q-h0-vm-capture-v1' and type(capture['qemu_returncode']) is int and
                capture['qemu_returncode'] in ((0,) if case=='positive' else (0,-15,-9)) and
                {'vm.py','vm_evidence.py','verify.py','service_ram.py','ssh_ram.py','debian_ram.py',
                 'device_action_raw_capture_v1.py'}<=set(capture['source']),'service VM producer provenance missing')
        command=json.loads((directory/'command.json').read_text())['command']
        require(capture['inputs']['initramfs']=={k:manifest['initramfs'][k] for k in ('path','sha256')} and
                all(command.count(flag)==1 and command[command.index(flag)+1:command.index(flag)+2]==[path]
                    for flag,path in (('-kernel',kernel['path']),('-initrd',manifest['initramfs']['path']))),
                'service VM command does not select the bound kernel and initramfs')
    for name,sha in capture['source'].items():
        require(Path(name).name==name and digest(directory/'source'/name)==sha,'Download VM source changed')
    record=json.loads((directory/'download-case.json').read_text())
    expected_ack=case in ('positive','extra-tail','missing-eof')
    require(record==dict(case=case,expected_ack=expected_ack,base_framing='length',pmic_hardware_proved=False),
            'Download VM case differs')
    nonce=(directory/'nonce.bin').read_bytes();key=Path(manifest['key_path']).read_bytes()
    identity=bytes.fromhex(manifest['candidate_id'])
    require((directory/'request.raw').read_bytes()==verify.request(key,identity,nonce,manifest=manifest),
            'Download VM request differs')
    data=(directory/'response.raw').read_bytes();prefix=(directory/'prefix.raw').read_bytes()
    require(data[:384]==prefix and len(data)==codec.frame_size(prefix),'Download VM frame differs')
    proof=verify.verify(directory/'response.raw',manifest,nonce,vm=True)
    require(proof['download_ready'] is True,'VM Download fixture binding absent')
    boot=proof['boot_id']
    if case=='wrong-control-key':key=bytes([key[0]^1])+key[1:]
    if case=='wrong-boot':boot=str(uuid.UUID(int=uuid.UUID(boot).int^1))
    command=wire.control(key,identity,nonce,boot)
    if case=='legacy-command':
        head=b'G0QSRQ1\0'+command[8:56];command=head+wire.tag(key,identity,2,head)
    if case=='extra-tail':command+=b'X'
    if case=='partial-control':command=command[:1]
    if case in SSH_CASES:command=b''
    require((directory/'control.raw').read_bytes()==command,'actual VM control differs')
    ack=(directory/'ack.raw').read_bytes()
    accepted=None
    if expected_ack:accepted=ack_proof(wire,ack,key,identity,nonce,proof)
    else:require(not ack,'negative Download VM acknowledged')
    serial=(directory/'serial.log').read_bytes()
    reset_event(directory,expected=case=='positive')
    if case=='positive':require(capture['qemu_returncode']==0 and serial.count(b'G0Q_DOWNLOAD_RESTART2_PREPARED')==1,
        'settled actual VM reset absent')
    else:
        errors={'wrong-control-key':13,'wrong-boot':13,'legacy-command':13,'extra-tail':71,'partial-control':32,'missing-eof':110,**dict.fromkeys(SSH_CASES,32)}
        require(b'G0Q_DOWNLOAD_RESTART2_PREPARED' not in serial and ('G0Q_RAM_PARK error='+str(errors[case])).encode() in serial,
                'settled VM rejection absent')
    result=json.loads((directory/'result.json').read_text())
    require(result['download_case']==case and result['device_actions']==0 and result['kernel_sha256']==kernel['sha256'] and
            all(result[k]==v for k,v in proof.items()),'Download VM result differs')
    record=dict(capture=pin(directory/'capture.json'),result=pin(directory/'result.json'),case=case,
                vm_restart_proved=case=='positive',physical_download_proved=False)
    if cycle:
        ssh_case=case[4:] if case in SSH_CASES else 'positive'
        checked=wire.ssh_ram.recheck_vm(directory,manifest,proof['boot_id'],case=ssh_case)
        require(proof['ssh_ready'] is True and result['ssh']==checked['proof'] and result['ssh_case']==ssh_case,
                'rc-managed SSH raw evidence differs')
        record.update(ssh=checked,service_ack=accepted)
    return record
