"""Fixed S22+ Android health and USB identity, without a Process-v2 owner."""
from dataclasses import asdict
import copy
import os
from pathlib import Path
import re
import shlex
import time

import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_fyg8_p324_typec_lane_binding as lane
import s22plus_odin_usbfs_identity as usbfs
from s22plus_native_records_v3 import clock, digest, pin, publish, read, require, verify

TARGET = 'SM-S906N/g0q/S906NKSS7FYG8'
PROPERTIES = """printf 'model='; getprop ro.product.model
printf 'device='; getprop ro.product.device
printf 'bootloader='; getprop ro.boot.bootloader
printf 'incremental='; getprop ro.build.version.incremental
printf 'boot_completed='; getprop sys.boot_completed
printf 'bootanim='; getprop init.svc.bootanim
printf 'verified_boot_state='; getprop ro.boot.verifiedbootstate
printf 'boot_id='; cat /proc/sys/kernel/random/boot_id
printf 'kernel_release='; uname -r"""
ROOT_HEALTH = """printf 'root='; id
printf 'boot='; sha256sum /dev/block/by-name/boot | cut -d' ' -f1
printf 'vendor_boot='; sha256sum /dev/block/by-name/vendor_boot | cut -d' ' -f1
printf 'dtbo='; sha256sum /dev/block/by-name/dtbo | cut -d' ' -f1
printf 'recovery='; sha256sum /dev/block/by-name/recovery | cut -d' ' -f1"""
PROPERTY_FIELDS = {'model','device','bootloader','incremental','boot_completed','bootanim',
    'verified_boot_state','boot_id','kernel_release'}
HEALTH_FIELDS = {'root','boot','vendor_boot','dtbo','recovery'}
UUID = re.compile('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')


class _RootHealthReadFailure(raw.RawCaptureError):
    """Only a root-read decoder failure, never an owner/source-guard failure."""


def fields(text, expected):
    result={}
    for line in text.splitlines():
        key,separator,value=line.partition('=')
        require(separator and key not in result and value,'fixed Android field is missing or duplicated')
        result[key]=value
    require(set(result)==expected,'fixed Android field set differs')
    return result


def select_android(text, target):
    require(type(target) is dict and set(target)=={'serial','topology'}
        and re.fullmatch('[A-Za-z0-9._:-]{1,128}',target['serial'])
        and target['topology']==lane.SOURCE_TOPOLOGY,'exact S22+ target binding differs')
    lines=text.splitlines()
    require(lines and lines[0]=='List of devices attached','ADB inventory header differs')
    rows=[]; matches=[]
    for line in lines[1:]:
        if not line.strip(): continue
        tokens=line.split(); require(len(tokens)>=2,'ADB inventory row is malformed')
        require(tokens[0] not in [row[0] for row in rows],'duplicate ADB serial')
        rows.append(tokens)
        if {'model:SM_S906N','device:g0q'}<=set(tokens[2:]): matches.append(tokens)
    require(len(matches)==1 and matches[0][0]==target['serial'] and matches[0][1]=='device',
        'ADB target identity or authorization differs')
    return rows


def health_projection(captures, target, android):
    require(len(captures)==7,'fixed Android same-boot bracket is incomplete')
    texts=[]
    for receipt in captures:
        handle=raw.load_handle(verify(receipt))
        texts.append(raw.decode_success_stdout(handle,maximum=16384))
        require(not raw.read_stderr(handle,maximum=16384),'fixed Android read returned diagnostics')
    inventory=select_android(texts[0],target)
    repeated=select_android(texts[4],target)
    first=fields(texts[2],PROPERTY_FIELDS); last=fields(texts[6],PROPERTY_FIELDS)
    health=fields(texts[3],HEALTH_FIELDS)
    require(inventory==repeated and texts[1]==texts[5]==target['topology'] and first==last,
        'Android target or boot changed during health bracket')
    require({key:first[key] for key in ('model','device','bootloader','incremental','boot_completed','bootanim','verified_boot_state')}
        ==dict(model='SM-S906N',device='g0q',bootloader='S906NKSS7FYG8',incremental='S906NKSS7FYG8',
            boot_completed='1',bootanim='stopped',verified_boot_state='orange') and UUID.fullmatch(first['boot_id']),
        'required rooted FYG8 Android state differs')
    require(re.fullmatch(r'uid=0(?:\([^()\s]*\))? gid=0(?:\([^()\s]*\))?(?: .*)?',health['root']),
        'Android numeric root UID/GID is not proved')
    require(set(android['partition_sha256'])==HEALTH_FIELDS-{'root'}
        and all(re.fullmatch('[0-9a-f]{64}',health[key]) and health[key]==android['partition_sha256'][key]
            for key in HEALTH_FIELDS-{'root'}),'Android rollback/supporting partition digest differs')
    return dict(target=TARGET,serial_sha256=digest(target['serial'].encode()),
        topology_sha256=digest(target['topology'].encode()),boot_id_sha256=digest(first['boot_id'].encode()),
        rooted_android_health=True,properties=first,partition_sha256=android['partition_sha256'],captures=captures)


class Android:
    def __init__(self, tool, target, android, directory, *, guard):
        self.tool=tool; self.target=target; self.android=android
        self.directory=Path(directory); self.directory.mkdir(mode=0o700,exist_ok=True)
        self.guard=guard

    def command(self, arguments, name, *, timeout, before_launch=None):
        self.guard()
        # Tool identity remains exact before every connected command.
        with transport.pin_regular_file(Path(self.tool['path']),label='ADB',
                expected_size=self.tool['size'],expected_sha256=self.tool['sha256']) as tool:
            self.guard()
            options=dict(before_spawn=before_launch) if before_launch is not None else {}
            return raw.acquire_command([str(tool.path),*arguments],self.directory,name,
                timeout=timeout,stdout_maximum=16384,stderr_maximum=16384,**options)

    def health(self, *, reobserve_root_disappearance=False, deadline_ns=None):
        """One full bracket, with an explicitly adopted return-health exception.

        Only a completed same-serial ADB disappearance at the root read can
        replace the bracket. No successful prefix is reused. Legacy callers
        retain their single attempt and original capture paths.
        """
        if reobserve_root_disappearance:
            require(deadline_ns is None or type(deadline_ns) is int and deadline_ns>0,
                'health deadline is not a positive absolute time')
            deadline_ns=min(clock()+260_000_000_000,
                2**63-1 if deadline_ns is None else deadline_ns)
        else:
            require(deadline_ns is None,'health deadline requires the adopted return profile')
        captures=[]
        try:
            result=self._health_attempt(captures,deadline_ns=deadline_ns)
        except _RootHealthReadFailure:
            if not reobserve_root_disappearance or len(captures)!=4:raise
            failed=raw.load_handle(verify(captures[-1]))
            require(failed.returncode==1 and not failed.timed_out and not failed.output_exceeded
                and failed.producer_error_type is None
                and raw.read_stdout(failed,maximum=16384)==b''
                and raw.read_stderr(failed,maximum=16384)==
                    ("adb: device '"+self.target['serial']+"' not found\n").encode('ascii'),
                'failed health read is not the adopted ADB disappearance')
            prefix=[raw.load_handle(verify(p)) for p in captures[:3]]
            texts=[raw.decode_success_stdout(h,maximum=16384) for h in prefix]
            require(all(not raw.read_stderr(h,maximum=16384) for h in prefix),
                'abandoned health prefix returned diagnostics')
            select_android(texts[0],self.target)
            require(texts[1]==self.target['topology'],'abandoned health devpath differs')
            expected=dict(model='SM-S906N',device='g0q',bootloader='S906NKSS7FYG8',
                incremental='S906NKSS7FYG8',boot_completed='1',bootanim='stopped')
            partial='\n'.join(k+'='+v for k,v in expected.items())
            anchor=None
            if texts[2].rstrip('\n')!=partial:
                old=fields(texts[2],PROPERTY_FIELDS)
                require(all(old[k]==v for k,v in expected.items()) and
                    old['verified_boot_state']=='orange' and UUID.fullmatch(old['boot_id']),
                    'abandoned health properties differ')
                anchor=digest(old['boot_id'].encode())
            self.guard()
            require(clock()<deadline_ns,'health reobservation exhausted the original deadline')
            # A shallow copy keeps the caller's command implementation and guards.
            replacement=copy.copy(self)
            replacement.directory=self.directory/'reobservation-1'
            replacement.directory.mkdir(mode=0o700)
            publish(replacement.directory/'intent.json',dict(
                schema='s22plus-android-root-read-reobservation-v1',abandoned_captures=captures,
                deadline_ns=deadline_ns,prior_boot_id_sha256=anchor))
            replacement.wait_ready(deadline_ns=deadline_ns)
            result=replacement._health_attempt([],deadline_ns=deadline_ns)
            require(anchor is None or result['boot_id_sha256']==anchor,
                'Android boot changed after the abandoned health bracket')
        if deadline_ns is not None:
            self.guard()
            require(clock()<deadline_ns,'Android health projection exceeded the original deadline')
        publish(self.directory/'health.json',result)
        return result

    def _health_attempt(self, captures, *, deadline_ns):
        serial=self.target['serial']
        properties=['-s',serial,'shell','sh -c '+shlex.quote(PROPERTIES)]
        health=['-s',serial,'shell','su -c '+shlex.quote(ROOT_HEALTH)]
        commands=[(['devices','-l'],10),(['-s',serial,'get-devpath'],10),(properties,20),(health,180),
            (['devices','-l'],10),(['-s',serial,'get-devpath'],10),(properties,20)]
        for index,(arguments,timeout) in enumerate(commands):
            def remaining():
                self.guard()
                left=(deadline_ns-clock())/1_000_000_000
                require(left>=.1,'Android health exhausted the original deadline')
                return min(timeout,left)
            options={} if deadline_ns is None else dict(before_launch=remaining)
            handle=self.command(arguments,f'{index:02d}-health',
                timeout=timeout if deadline_ns is None else remaining(),**options)
            receipt=pin(handle.receipt_path); captures.append(receipt)
            if deadline_ns is not None:remaining()
            try:text=raw.decode_success_stdout(handle,maximum=16384)
            except raw.RawCaptureError as error:
                if index==3 and deadline_ns is not None:
                    require(raw.load_handle(handle.receipt_path)==handle,
                        'root health capture handle differs from its immutable receipt')
                    raw.read_stdout(handle,maximum=16384)
                    raw.read_stderr(handle,maximum=16384)
                    raise _RootHealthReadFailure(str(error)) from error
                raise
            # Validate the selector before the first target-specific command.
            if index in (0,4): select_android(text,self.target)
            if index in (1,5): require(text==self.target['topology'],'Android devpath differs')
        return health_projection(captures,self.target,self.android)

    def download(self, *, before_dispatch):
        handle=self.command(['-s',self.target['serial'],'reboot','download'],'download',timeout=15,
            before_launch=before_dispatch)
        raw.require_success(handle)
        return dict(capture=pin(handle.receipt_path),request='adb-reboot-download',accepted=True)

    def wait_ready(self, *, deadline_ns):
        """Bounded readiness reads; the required seven-read health is separate."""
        def remaining_timeout():
            remaining=(deadline_ns-clock())/1_000_000_000
            if remaining<.1:raise TimeoutError('Android readiness did not complete')
            return min(10,remaining)
        def observe(arguments,name):
            # Recheck after tool/source guards as well as between the two reads.
            # A late completion cannot become readiness or renew this deadline.
            return self.command(arguments,name,timeout=remaining_timeout(),
                before_launch=remaining_timeout)
        index=0
        while clock()<deadline_ns:
            inventory=observe(['devices','-l'],f'wait-{index:03d}-inventory')
            text=raw.decode_success_stdout(inventory,maximum=16384)
            require(not raw.read_stderr(inventory,maximum=16384),'ADB readiness inventory returned diagnostics')
            lines=text.splitlines()
            require(lines and lines[0]=='List of devices attached','ADB readiness inventory header differs')
            rows=[line.split() for line in lines[1:] if line.strip()]
            require(all(len(row)>=2 for row in rows),'ADB readiness inventory is malformed')
            selected=[row for row in rows if row[0]==self.target['serial']]
            candidates=[row for row in rows if {'model:SM_S906N','device:g0q'}<=set(row[2:])]
            require(len(selected)<=1 and len(candidates)<=1
                and (not candidates or candidates[0][0]==self.target['serial']),
                'ADB readiness target is ambiguous')
            if selected and selected[0][1]=='device':
                select_android(text,self.target)
                command=['-s',self.target['serial'],'shell','getprop sys.boot_completed']
                handle=observe(command,f'wait-{index:03d}-boot')
                vanished=(handle.returncode==1 and not handle.timed_out and not handle.output_exceeded and
                    handle.producer_error_type is None and raw.read_stdout(handle,maximum=16)==b'' and
                    raw.read_stderr(handle,maximum=16384)==
                    ("adb: device '"+self.target['serial']+"' not found\n").encode('ascii'))
                if vanished:
                    # Keep this immutable failure and select the exact target
                    # again in the next bounded inventory; never retry control.
                    value=''
                else:
                    value=raw.decode_success_stdout(handle,maximum=16)
                    require(not raw.read_stderr(handle,maximum=16384),'Android readiness read returned diagnostics')
                require(value in ('','0','1'),'Android boot-complete property is malformed')
                if value=='1':
                    require(clock()<deadline_ns,'Android readiness exceeded original deadline')
                    return
            index+=1
            require(index<256,'Android readiness inventory exceeds bound')
            time.sleep(.5)
        raise TimeoutError('Android readiness did not complete')


def sysfs_field(node, name, *, optional=False):
    path=Path(node)/name
    try:
        with path.open('rb') as stream: data=stream.read(513)
    except FileNotFoundError:
        if optional: return None
        raise
    require(len(data)<=512,'USB sysfs field exceeds bound')
    value=data.decode('ascii').strip()
    require('\x00' not in value and '\n' not in value and '\r' not in value,'USB sysfs field malformed')
    return value


def download_identity(device, *, topology=lane.SOURCE_TOPOLOGY, usb_root=Path('/sys/bus/usb/devices')):
    require(transport.ODIN_DEVICE_RE.fullmatch(device) and topology==lane.SOURCE_TOPOLOGY,
        'Download endpoint or physical lane differs')
    node=usb_root/topology.removeprefix('usb:')
    names=('busnum','devnum','idVendor','idProduct','product','manufacturer','serial')
    first={name:sysfs_field(node,name,optional=name=='serial') for name in names}
    last={name:sysfs_field(node,name,optional=name=='serial') for name in names}
    bus,dev=map(int,device.split('/')[-2:])
    require(first==last and first['busnum']==str(bus) and first['devnum']==str(dev)
        and (first['idVendor'],first['idProduct'],first['product'],first['manufacturer'])
            ==('04e8','685d','SAMSUNG USB','Samsung') and first['serial'] in (None,''),
        'Download endpoint is not the exact stable S22+ lane identity')
    return dict(device=device,topology=topology,fields=first)


def usb_snapshot(topology, directory):
    require(topology in (lane.SOURCE_TOPOLOGY,lane.CANDIDATE_TOPOLOGY),'USB topology is outside bound lane')
    node=Path('/sys/bus/usb/devices')/topology.removeprefix('usb:')
    before=[sysfs_field(node,name) for name in ('busnum','devnum')]
    require(all(re.fullmatch('[0-9]+',value) for value in before),'USB coordinates differ')
    path=f'/dev/bus/usb/{int(before[0]):03d}/{int(before[1]):03d}'
    value=usbfs.snapshot_node(path,birth_reader=lambda device:usbfs.read_birth_time_ns(device,Path(directory)))
    require(before==[sysfs_field(node,name) for name in ('busnum','devnum')],'USB coordinates changed during snapshot')
    return dict(topology=topology,snapshot=asdict(value),identity=usbfs.immutable_identity(value),boottime_ns=clock())


def wait_departure(before, directory, *, deadline_ns, guard):
    """Only the prebound generation is observed; no command or reconnect retry."""
    require(type(deadline_ns) is int and deadline_ns>0,'original USB departure deadline differs')
    path=before['snapshot']['path']
    while clock()<deadline_ns:
        guard()
        require(clock()<deadline_ns,'USB departure guard exceeded original deadline')
        try:
            current=usbfs.snapshot_node(path,birth_reader=lambda device:usbfs.read_birth_time_ns(device,Path(directory)))
        except usbfs.UsbfsEndpointDeparture:
            observed=clock()
            require(observed<deadline_ns,'USB departure observation exceeded original deadline')
            return dict(before=before,departed=True,reason='old-node-absent',observed_ns=observed,deadline_ns=deadline_ns)
        require(usbfs.immutable_identity(current)==before['identity'],
            'bound USB identity changed without proved departure')
        time.sleep(.1)
    raise TimeoutError('bound USB generation did not depart')


def transfer_completed(handle):
    require(raw.load_handle(handle.receipt_path)==handle and handle.returncode==0
        and not handle.timed_out and not handle.output_exceeded and handle.producer_error_type is None,
        'Odin producer did not complete')
    stdout=raw.read_stdout(handle,maximum=8*1024*1024)
    stderr=raw.read_stderr(handle,maximum=8*1024*1024)
    output=stdout+b'\n'+stderr
    require(all(marker in output for marker in (b'Setup Connection',b'Upload Binaries',b'boot.img.lz4',
        b'100%',b'Close Connection')),'Odin raw output does not prove a completed boot transfer')
    return True
