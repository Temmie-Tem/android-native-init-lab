"""Fixed host installation and exclusive native tty acquisition for V3.

Host setup is explicit and separate from device sessions. No installation,
udev mutation or interactive authorization occurs in NativeHost.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import pwd
import stat
import termios
import tty

import device_action_raw_capture_v1 as raw
import s22plus_native_host_census_v1 as census
from s22plus_native_records_v3 import canonical, clock, digest, pin, publish, read, require

POLKIT = census.POLKIT
UDEV = census.UDEV
ACTION = census.ACTION
PKCHECK = Path('/usr/bin/pkcheck')
PKEXEC = Path('/usr/bin/pkexec')
UDEVADM = Path('/usr/bin/udevadm')


def installation_files(*, uid, account, topology):
    config = census.config_value(canonical(dict(schema=census.SCHEMA,uid=uid,account=account,
        topology=topology,vendor='04e8',product='6861',interface='00',driver='cdc_acm',serial_prefix='S22E3')))
    require(pwd.getpwuid(uid).pw_name==account,'host account does not match UID')
    serial = 'S22E3'+'[0-9a-f]'*32
    udev = ('# Fixed S22+ native research gadget on its bound USB port.\n'
        f'ACTION=="add|change|move|bind", SUBSYSTEM=="usb", KERNEL=="{topology}", '
        f'ATTR{{idVendor}}=="04e8", ATTR{{idProduct}}=="6861", ATTR{{serial}}=="{serial}", '
        'ENV{ID_MM_DEVICE_IGNORE}="1"\n'
        f'ACTION=="add|change|move|bind", SUBSYSTEM=="tty", KERNEL=="ttyACM*", KERNELS=="{topology}", '
        f'ATTRS{{idVendor}}=="04e8", ATTRS{{idProduct}}=="6861", ATTRS{{serial}}=="{serial}", '
        'ENV{ID_USB_INTERFACE_NUM}=="00", ENV{ID_MM_DEVICE_IGNORE}="1", ENV{ID_MM_PORT_IGNORE}="1"\n')
    polkit = ('// Read-only census of one configured native tty; no caller arguments.\n'
        'polkit.addRule(function(action, subject) {\n'
        f'    if (action.id === "{census.ACTION_ID}" &&\n'
        f'        subject.user === "{account}") {{\n'
        '        return polkit.Result.YES;\n'
        '    }\n'
        '});\n')
    action = ('<?xml version="1.0" encoding="UTF-8"?>\n<policyconfig>\n'
        '  <vendor>android-native-init-lab</vendor>\n'
        f'  <action id="{census.ACTION_ID}">\n'
        '    <description>Read the fixed S22+ native tty holder census</description>\n'
        '    <message>Authorize the fixed S22+ native tty holder census</message>\n'
        '    <defaults><allow_any>no</allow_any><allow_inactive>no</allow_inactive><allow_active>no</allow_active></defaults>\n'
        f'    <annotate key="org.freedesktop.policykit.exec.path">{census.HELPER}</annotate>\n'
        '  </action>\n</policyconfig>\n')
    return {census.HELPER: (Path(census.__file__).read_bytes(),0o755),
        census.CONFIG:(canonical(config),0o644),POLKIT:(polkit.encode(),0o644),UDEV:(udev.encode(),0o644),
        ACTION:(action.encode(),0o644)}


def prepare_installation(directory, *, uid, account, topology):
    """Create the exact reviewable host files; this performs no installation."""
    directory=Path(directory); directory.mkdir(mode=0o700)
    files=installation_files(uid=uid,account=account,topology=topology)
    rows=[]
    for index,(destination,(data,mode)) in enumerate(files.items()):
        source=directory/f'{index:02d}-{destination.name}'
        fd=os.open(source,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_CLOEXEC,0o600)
        with os.fdopen(fd,'wb') as stream: stream.write(data); stream.flush(); os.fsync(stream.fileno())
        rows.append(dict(destination=str(destination),mode=mode,source=pin(source,maximum=65536)))
    return publish(directory/'installation.json',dict(schema='s22plus-native-host-installation-v3',
        uid=uid,account=account,topology=topology,files=rows))


class NativeHost:
    def __init__(self, installation, evidence):
        self.installation=installation
        self.evidence=Path(evidence); self.evidence.mkdir(mode=0o700,exist_ok=True)
        self.sequence=0
        self.config=census.config_value(canonical(dict(schema=census.SCHEMA,uid=installation['uid'],
            account=installation['account'],topology=installation['topology'],vendor='04e8',product='6861',
            interface='00',driver='cdc_acm',serial_prefix='S22E3')))

    def command(self, argv, label, *, timeout=8, maximum=8192):
        name=f'{self.sequence:04d}-{label}'; self.sequence+=1
        handle=raw.acquire_command([str(value) for value in argv],self.evidence,name,
            timeout=timeout,stdout_maximum=maximum,stderr_maximum=maximum)
        value=raw.decode_success_stdout(handle,maximum=maximum)
        return value,pin(handle.receipt_path)

    def installed(self):
        require(self.installation['schema']=='s22plus-native-host-installation-v3','host installation schema differs')
        expected=installation_files(uid=self.config['uid'],account=self.config['account'],topology=self.config['topology'])
        rows=self.installation['files']
        require(len(rows)==len(expected) and {row['destination'] for row in rows}=={str(path) for path in expected},
            'host installation file set differs')
        for row in rows:
            destination=Path(row['destination']); data,mode=expected[destination]
            require(row['mode']==mode and row['source']['size']==len(data) and row['source']['sha256']==digest(data),
                'prepared host file differs from reviewed content')
            if destination!=POLKIT:
                require(census.trusted_file(destination,maximum=65536)==data
                    and stat.S_IMODE(destination.stat().st_mode)==mode,'installed host content or mode differs')
        # This PC's polkit rules directory is root:polkitd 0750. Its fixed-file
        # digest is acquired by the read-only helper, not by relaxing the parent.

    def ready(self):
        self.installed()
        require(os.getuid()==self.config['uid'],'host caller account differs')
        # /proc stat field 22 is starttime; the comm field may contain spaces.
        tail=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
        process=f'{os.getpid()},{int(tail[19])},{os.getuid()}'
        # Current polkit restricts detail-bearing queries to trusted callers.
        # The fixed policy action maps to only HELPER, so this unprivileged
        # readiness query needs no caller-supplied authorization details.
        _,receipt=self.command([PKCHECK,'--action-id',census.ACTION_ID,'--process',process],
            'polkit-ready',timeout=3)
        self.installed()
        return receipt

    def holders(self, *, descriptor=None, expected_run=None):
        self.ready()
        text,receipt=self.command([PKEXEC,'--disable-internal-agent',census.HELPER],'tty-census',timeout=8)
        value=json.loads(text)
        require(type(value) is dict and set(value)=={'schema','kind','state','complete','endpoint','holders',
            'config_sha256','observed_boottime_ns','installed_files'} and value['schema']==census.SCHEMA
            and value['kind']=='tty-census' and value['complete'] is True
            and value['config_sha256']==census.digest(self.config)
            and type(value['observed_boottime_ns']) is int
            and 0<=clock()-value['observed_boottime_ns']<=10_000_000_000,'root census is incomplete or stale')
        installed={str(path):dict(size=len(data),sha256=digest(data),mode=mode)
            for path,(data,mode) in installation_files(uid=self.config['uid'],account=self.config['account'],
                topology=self.config['topology']).items()}
        require(value['installed_files']==installed,'privileged host installation digest differs')
        current=census.endpoint(self.config)
        require(value['endpoint']==current and value['state']==('absent' if current is None else 'present'),
            'native endpoint changed across privileged census')
        require(type(value['holders']) is list and all(type(pid) is int and pid>0 for pid in value['holders']),
            'native census holder set differs')
        if descriptor is not None:
            require(current is not None and value['holders']==[os.getpid()],'native tty is not exclusively held')
            info=os.fstat(descriptor)
            require(stat.S_ISCHR(info.st_mode) and current['generation']['node']==[info.st_dev,info.st_ino,info.st_rdev],
                'native held descriptor is from a different generation')
        else:
            require(value['holders']==[],'native tty already has a holder')
        if expected_run is not None and current is not None:
            expected=dict(tty_name=current['tty_name'],topology=self.config['topology'],vendor='04e8',
                product='6861',serial='S22E3'+expected_run,interface='00',driver='cdc_acm')
            require(current['identity_sha256']==census.digest(expected),'native endpoint does not match selected image')
        return value,receipt

    def properties(self, endpoint):
        text,receipt=self.command([UDEVADM,'info','--query=property','--path',
            '/sys/class/tty/'+endpoint['tty_name']],'tty-properties',timeout=3)
        values={}
        for line in text.splitlines():
            name,separator,value=line.partition('=')
            require(separator and name not in values,'native udev property output differs'); values[name]=value
        require(values.get('ID_MM_DEVICE_IGNORE')=='1' and values.get('ID_MM_PORT_IGNORE')=='1'
            and values.get('ID_USB_INTERFACE_NUM')=='00','native udev ignore properties are absent')
        return receipt

    @contextmanager
    def open_native(self, run_id, *, before_open):
        before_open()
        census_before,first_receipt=self.holders(expected_run=run_id)
        endpoint=census_before['endpoint']; require(endpoint is not None,'selected native tty is absent')
        path=Path('/dev')/endpoint['tty_name']
        fd=os.open(path,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC|os.O_NOFOLLOW)
        acquisition=dict(endpoint=endpoint,before=first_receipt,close=None)
        try:
            info=os.fstat(fd)
            require(stat.S_ISCHR(info.st_mode) and endpoint['generation']['node']==[info.st_dev,info.st_ino,info.st_rdev],
                'opened native descriptor generation differs')
            fcntl.ioctl(fd,termios.TIOCEXCL)
            tty.setraw(fd,termios.TCSANOW)
            _,second_receipt=self.holders(descriptor=fd,expected_run=run_id)
            properties=self.properties(endpoint)
            require(census.endpoint(self.config)==endpoint,'native endpoint changed before authentication')
            before_open()
            acquisition.update(after=second_receipt,properties=properties)
            yield fd,acquisition
        finally:
            # TIOCEXCL can outlive the last client fd while the driver retains
            # the tty. Release only our descriptor's exclusion, then close it.
            # This does not retransmit or authorize another protocol attempt.
            release_errno=None
            try: fcntl.ioctl(fd,termios.TIOCNXCL)
            except OSError as error: release_errno=error.errno
            closed=False
            try:
                os.close(fd); closed=True
            finally:
                acquisition['close']=dict(descriptor_closed=closed,exclusive_release_errno=release_errno,
                    boottime_ns=clock())
