#!/usr/bin/python3 -I
"""Installed, no-argument, read-only census of one configured S22+ native tty.

The installed copy uses only the standard library and root-owned configuration.
It never imports the checkout, opens a tty, changes udev, or signals a holder.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import time

SCHEMA = 's22plus-native-host-policy-v1'
CONFIG = Path('/etc/android-native-init-lab/s22plus-native-host.json')
HELPER = Path('/usr/local/libexec/s22plus-native-tty-census')
POLKIT = Path('/etc/polkit-1/rules.d/49-s22plus-native-census.rules')
UDEV = Path('/etc/udev/rules.d/79-s22plus-native-mm-ignore.rules')
ACTION_ID = 'org.androidnativeinit.s22plus.tty-census'
ACTION = Path('/usr/share/polkit-1/actions/'+ACTION_ID+'.policy')
FUSER = '/usr/bin/fuser'
MAX_BYTES = 8192
MAX_SECONDS = 5


class CensusError(RuntimeError):
    pass


def require(condition, reason):
    if not condition: raise CensusError(reason)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def trusted_file(path, *, maximum=MAX_BYTES):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path, 'indirect installed path')
    for parent in path.parents:
        entry = parent.stat()
        require(stat.S_ISDIR(entry.st_mode) and entry.st_uid == 0 and not entry.st_mode & 0o022,
                'writable installed directory')
    entry = path.lstat()
    require(stat.S_ISREG(entry.st_mode) and entry.st_uid == 0 and entry.st_nlink == 1
            and not entry.st_mode & 0o022 and 0 < entry.st_size <= maximum, 'untrusted installed file')
    with path.open('rb') as stream: data = stream.read(maximum+1)
    require(len(data) == entry.st_size, 'installed file changed or exceeded bound')
    return data


def config_value(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate configuration key'); result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    require(type(value) is dict and set(value) == {'schema','uid','account','topology',
        'vendor','product','interface','driver','serial_prefix'}, 'configuration fields differ')
    require(value['schema'] == SCHEMA and type(value['uid']) is int and 0 < value['uid'] < 2**31
            and type(value['account']) is str and re.fullmatch('[a-z_][a-z0-9_-]{0,31}', value['account'])
            and type(value['topology']) is str and re.fullmatch('[0-9]+-[0-9]+(?:\\.[0-9]+)*', value['topology'])
            and (value['vendor'],value['product'],value['interface'],value['driver'],value['serial_prefix'])
                == ('04e8','6861','00','cdc_acm','S22E3'), 'configuration target or account differs')
    return value


def read_text(path):
    with Path(path).open('rb') as stream: data = stream.read(513)
    require(0 < len(data) <= 512, 'sysfs field empty or oversized')
    text = data.decode('ascii').strip()
    require(text and '\n' not in text and '\r' not in text, 'sysfs field malformed')
    return text


def endpoint(config, *, class_tty=Path('/sys/class/tty'), dev_root=Path('/dev')):
    # glob silently treats an unavailable inventory as empty on some Python
    # versions. Explicit enumeration must succeed before absence is meaningful.
    entries = []
    with os.scandir(class_tty) as inventory:
        for count, entry in enumerate(inventory, 1):
            require(count <= 4096, 'tty class inventory exceeds bound')
            if entry.name.startswith('ttyACM'): entries.append(Path(entry.path))
    entries.sort()
    require(len(entries) <= 16, 'tty inventory exceeds bound')
    matches = []
    for entry in entries:
        require(re.fullmatch('ttyACM[0-9]+', entry.name), 'noncanonical tty entry')
        device = (entry/'device').resolve(strict=True)
        interface = next((p for p in (device,*device.parents) if (p/'bInterfaceNumber').is_file()), None)
        require(interface is not None and ':' in interface.name, 'incomplete tty ancestry')
        usb = interface.parent
        require(usb.name == interface.name.split(':',1)[0], 'incomplete USB ancestry')
        if usb.name != config['topology']: continue
        identity = dict(tty_name=entry.name, topology=usb.name,
            vendor=read_text(usb/'idVendor'), product=read_text(usb/'idProduct'),
            serial=read_text(usb/'serial'), interface=read_text(interface/'bInterfaceNumber'),
            driver=(interface/'driver').resolve(strict=True).name)
        require(all(identity[name] == config[name] for name in ('vendor','product','interface','driver'))
                and re.fullmatch(config['serial_prefix']+'[0-9a-f]{32}',identity['serial']),
                'configured native port has a different identity')
        coordinate = read_text(entry/'dev')
        require(re.fullmatch('[0-9]+:[0-9]+', coordinate), 'tty device coordinate malformed')
        major, minor = map(int, coordinate.split(':'))
        node = dev_root/entry.name; info = node.lstat()
        require(stat.S_ISCHR(info.st_mode) and (os.major(info.st_rdev),os.minor(info.st_rdev)) == (major,minor),
                'tty node differs from sysfs')
        generation = dict(node=[info.st_dev,info.st_ino,info.st_rdev],
            tty=[entry.stat().st_dev,entry.stat().st_ino],
            usb=[usb.stat().st_dev,usb.stat().st_ino])
        matches.append(dict(tty_name=entry.name, identity_sha256=digest(identity),
            major=major, minor=minor, generation=generation))
    require(len(matches) <= 1, 'configured native tty is ambiguous')
    return matches[0] if matches else None


def bounded_fuser(node, *, timeout=MAX_SECONDS):
    """Bound stdout/stderr while collecting; a timeout never reports a census."""
    # Installed psmisc fuser does not accept a standalone "--" separator.
    # The node is internally derived and absolute, never a caller option.
    require(Path(node).is_absolute(), 'census node must be absolute')
    process = subprocess.Popen([FUSER, str(node)], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
    buffers = {process.stdout:bytearray(), process.stderr:bytearray()}
    remaining = set(buffers); deadline = time.monotonic()+timeout
    try:
        while remaining:
            require(time.monotonic() < deadline, 'census command timed out')
            readable,_,_ = select.select(list(remaining),[],[],min(.05,max(0,deadline-time.monotonic())))
            for stream in readable:
                data = os.read(stream.fileno(),4096)
                if not data: remaining.remove(stream); continue
                buffers[stream].extend(data)
                require(len(buffers[stream]) <= MAX_BYTES, 'census output exceeded bound')
        status = process.wait(timeout=max(.001,deadline-time.monotonic()))
        stdout,stderr = bytes(buffers[process.stdout]),bytes(buffers[process.stderr])
        if status == 1 and not stdout and not stderr: return []
        require(status == 0, 'census command failed')
        label = str(node).encode()+b':'
        require(stderr.startswith(label) and stderr[len(label):].endswith(b'\n')
                and all(c in b' \t' for c in stderr[len(label):-1]), 'census diagnostics are not a node label')
        tokens = stdout.split()
        require(tokens and all(token.isdigit() and 0 < int(token) < 2**31 for token in tokens), 'census PID output malformed')
        return sorted({int(token) for token in tokens})
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGKILL)
        try: process.wait(timeout=1)
        finally:
            process.stdout.close(); process.stderr.close()


def collect(config):
    first = endpoint(config)
    holders = [] if first is None else bounded_fuser(Path('/dev')/first['tty_name'])
    require(endpoint(config) == first, 'native endpoint changed during census')
    return dict(schema=SCHEMA, kind='tty-census', state='absent' if first is None else 'present',
        complete=True, endpoint=first, holders=holders, config_sha256=digest(config),
        observed_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME))


def installed_files():
    result={}
    for path in (HELPER,CONFIG,POLKIT,UDEV,ACTION):
        data=trusted_file(path,maximum=65536)
        result[str(path)]=dict(size=len(data),sha256=hashlib.sha256(data).hexdigest(),
            mode=stat.S_IMODE(path.stat().st_mode))
    return result


def main(argv=None):
    argv = sys.argv if argv is None else argv
    require(len(argv) == 1, 'the installed helper accepts no arguments')
    require(os.geteuid() == 0, 'root execution required')
    config = config_value(trusted_file(CONFIG))
    require(os.environ.get('PKEXEC_UID') == str(config['uid']), 'invoking account differs')
    before=installed_files()
    result = collect(config)
    require(installed_files()==before,'installed host files changed during census')
    require(config_value(trusted_file(CONFIG))==config,'root configuration changed during census')
    result['installed_files']=before
    payload = json.dumps(result, sort_keys=True, separators=(',', ':'))+'\n'
    require(len(payload.encode()) <= MAX_BYTES, 'census result exceeded bound')
    sys.stdout.write(payload)
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (CensusError,OSError,ValueError,subprocess.SubprocessError) as error:
        sys.stderr.write('S22+ native tty census failed: '+type(error).__name__+'\n')
        raise SystemExit(1)
