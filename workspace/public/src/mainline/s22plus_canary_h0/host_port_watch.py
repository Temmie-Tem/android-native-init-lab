#!/usr/bin/env python3
"""Stage 0 host-only observation for the S22+ mainline replug dependency.

Records, without touching the phone or any sysfs control:
- the host hub port `state` of each selected topology (e.g. "not attached",
  "powered", "default", "addressed", "configured") and whether a USB device
  node exists there, sampled at a fixed interval, transitions only;
- the host kernel log (`journalctl -k -f`) if the user may read it;
- `udevadm monitor` kernel USB events.

The question it answers: during the untouched-cable window, does the phone's
D+ pull-up ever reach the host port (port leaves "not attached", or the
kernel logs enumeration errors), or does the port stay "not attached"?

Read-only: it opens sysfs attributes for reading only and starts two
read-only monitor subprocesses. It has no device transport.

usage: host_port_watch.py --output FRESH_DIR [--port 3-1.3 --port 2-1.3]
                          [--duration 180] [--interval 0.1]
                          [--cable c-to-a|c-to-c|unknown] [--note TEXT]
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

USB_ROOT = Path('/sys/bus/usb/devices')
DEFAULT_PORTS = ('3-1.3', '2-1.3')  # candidate USB2 lane, Download/Android SS lane
DEVICE_FIELDS = ('idVendor', 'idProduct', 'speed', 'devnum', 'serial', 'product')
MAX_DURATION = 1800


def port_node(topology, usb_root=USB_ROOT):
    """Map a device topology such as 3-1.3 to its parent port directory."""
    topology = topology.removeprefix('usb:')
    bus, sep, chain = topology.partition('-')
    if not (bus.isdigit() and sep and chain and all(p.isdigit() for p in chain.split('.'))):
        raise ValueError(f'bad topology {topology!r}')
    parts = chain.split('.')
    port = parts[-1]
    if len(parts) == 1:  # root hub port
        return usb_root / f'usb{bus}' / f'{bus}-0:1.0' / f'usb{bus}-port{port}'
    parent = f'{bus}-' + '.'.join(parts[:-1])
    return usb_root / f'{parent}:1.0' / f'{parent}-port{port}'


def read_field(path):
    try:
        with open(path, 'rb') as stream:
            data = stream.read(257)
    except FileNotFoundError:
        return None
    except OSError as error:
        return f'<errno {error.errno}>'
    return data.decode('utf-8', 'replace').strip()


def snapshot(topology, usb_root=USB_ROOT):
    node = port_node(topology, usb_root)
    device = usb_root / topology.removeprefix('usb:')
    fields = None
    if device.is_dir():
        fields = {k: read_field(device / k) for k in DEVICE_FIELDS}
    return {
        'port_state': read_field(node / 'state'),
        'connect_type': read_field(node / 'connect_type'),
        'device': fields,
    }


def start_monitor(argv, path):
    exe = shutil.which(argv[0])
    if exe is None:
        return None, f'{argv[0]} not found'
    stream = open(path, 'wb')
    try:
        proc = subprocess.Popen([exe] + argv[1:], stdout=stream, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
    except OSError as error:
        stream.close()
        return None, str(error)
    return (proc, stream), None


def stop_monitor(handle):
    if handle is None:
        return None
    proc, stream = handle
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
    stream.close()
    return proc.returncode


def classify(events, topology):
    """Summarise one port's transitions into a coarse, non-causal label."""
    states = [e['snapshot']['port_state'] for e in events if e['topology'] == topology]
    devices = [e['snapshot']['device'] for e in events if e['topology'] == topology]
    if any(d is not None for d in devices):
        label = 'DEVICE_ENUMERATED'
    elif any(s not in (None, 'not attached') for s in states):
        label = 'PORT_LEFT_NOT_ATTACHED_WITHOUT_DEVICE'
    elif states and all(s == 'not attached' for s in states):
        label = 'PORT_STAYED_NOT_ATTACHED'
    else:
        label = 'PORT_STATE_UNREADABLE'
    return {'label': label, 'distinct_states': sorted({str(s) for s in states}),
            'transitions': len(states)}


def watch(ports, duration, interval, output, *, usb_root=USB_ROOT, clock=time.monotonic,
          sleep=time.sleep, wall=time.time, monitors=True, meta=None):
    output = Path(output)
    output.mkdir(mode=0o700)
    handles, errors = {}, {}
    if monitors:
        for name, argv in (('journal', ['journalctl', '-k', '-f', '-n', '0', '-o', 'short-monotonic']),
                           ('udev', ['udevadm', 'monitor', '--kernel', '--subsystem-match=usb'])):
            handles[name], err = start_monitor(argv, output / f'{name}.log')
            if err:
                errors[name] = err
    start = clock()
    events, last = [], {}
    log = (output / 'ports.jsonl').open('w')
    try:
        while True:
            now = clock() - start
            for topology in ports:
                snap = snapshot(topology, usb_root)
                if last.get(topology) != snap:
                    event = {'t': round(now, 4), 'wall': round(wall(), 4),
                             'topology': topology, 'snapshot': snap}
                    events.append(event)
                    log.write(json.dumps(event, sort_keys=True) + '\n')
                    log.flush()
                    last[topology] = snap
            if now >= duration:
                break
            sleep(interval)
    except KeyboardInterrupt:
        errors['interrupted'] = round(clock() - start, 4)
    finally:
        log.close()
        codes = {name: stop_monitor(h) for name, h in handles.items()}
    summary = {
        'schema': 's22plus-mainline-host-port-watch-v1',
        'device_contact': False,
        'ports': {p: {'port_node': str(port_node(p, usb_root)), **classify(events, p)} for p in ports},
        'duration_s': duration, 'interval_s': interval,
        'monitor_errors': errors, 'monitor_returncodes': codes,
        'meta': meta or {},
    }
    (output / 'summary.json').write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--output', required=True)
    ap.add_argument('--port', action='append')
    ap.add_argument('--duration', type=float, default=180.0)
    ap.add_argument('--interval', type=float, default=0.1)
    ap.add_argument('--cable', choices=('c-to-a', 'c-to-c', 'unknown'), default='unknown')
    ap.add_argument('--note', default='')
    args = ap.parse_args(argv)
    if not 0 < args.duration <= MAX_DURATION or not 0.01 <= args.interval <= 5:
        ap.error('duration or interval out of range')
    ports = tuple(args.port or DEFAULT_PORTS)
    for p in ports:
        port_node(p)
    summary = watch(ports, args.duration, args.interval, args.output,
                    meta={'cable': args.cable, 'note': args.note, 'argv': sys.argv[1:]})
    print(json.dumps(summary['ports'], indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
