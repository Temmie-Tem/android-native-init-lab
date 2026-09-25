"""Bounded private diagnostics of the two fixed Debian USB paths; no effects.

This is explanatory evidence only. The owner's existing endpoint selector and
authenticated health checks still decide whether a connection is acceptable.
"""
import errno
import json
from pathlib import Path

import device_action_raw_capture_v1 as raw
import s22plus_native_target_io_v3 as target
from s22plus_native_records_v3 import canonical, clock, pin, publish, require

FIELDS = ('idVendor', 'idProduct', 'serial', 'product', 'busnum', 'devnum')
MAX_FIELD = 512
MAX_INTERFACES = 128
MAX_RELATED = 8
MAX_CAPTURE = 32768
MAX_SAMPLES = 180


def _field(path):
    try:
        with path.open('rb') as stream:
            value = stream.read(MAX_FIELD + 1)
        return dict(hex=value.hex(), errno=None)
    except OSError as error:
        return dict(hex=None, errno=error.errno)


def capture(folder, ordinal, wanted, *, usb_root=Path('/sys/bus/usb/devices'),
            net_root=Path('/sys/class/net')):
    require(type(ordinal) is int and 1 <= ordinal <= MAX_SAMPLES,
            'USB diagnostic sample budget exhausted')
    writer = raw.RawCaptureWriter(folder, f'usb-{ordinal:03d}',
        stdout_maximum=MAX_CAPTURE, stderr_maximum=0,
        argv0_name='fixed-debian-usb-sysfs')
    def emit(row):
        writer.write_stdout(canonical(row))
    try:
        emit(dict(kind='begin', ordinal=ordinal, boottime_ns=clock()))
        parents = {}
        for topology in (target.lane.SOURCE_TOPOLOGY, target.lane.CANDIDATE_TOPOLOGY):
            path = usb_root / topology.removeprefix('usb:')
            try:
                parent = path.resolve(strict=True)
                parents[topology] = parent
                fields = {name: _field(path / name) for name in FIELDS}
                emit(dict(kind='usb', topology=topology, errno=None, fields=fields))
            except OSError as error:
                emit(dict(kind='usb', topology=topology, errno=error.errno, fields={}))
        related = 0
        # Enumerate names with a finite bound; do not capture unrelated MACs,
        # addresses, descriptors or device paths.
        for count, interface in enumerate(net_root.iterdir(), 1):
            require(count <= MAX_INTERFACES, 'USB diagnostic interface inventory exceeds bound')
            try:
                device = (interface / 'device').resolve(strict=True)
            except OSError:
                continue
            topologies = [name for name, parent in parents.items() if device.is_relative_to(parent)]
            if not topologies:
                continue
            related += 1
            require(related <= MAX_RELATED, 'USB diagnostic related interfaces exceed bound')
            emit(dict(kind='interface', name=interface.name, topologies=topologies,
                      address=_field(interface / 'address')))
        emit(dict(kind='end', related=related, boottime_ns=clock()))
    except BaseException as error:
        writer.finalize(returncode=None, producer_error_type=type(error).__name__)
        raise
    handle = writer.finalize(returncode=0)
    # Publish exact acquired bytes and their receipt before interpreting them.
    result = classify(handle, wanted)
    return publish(folder / f'usb-{ordinal:03d}.json', result)


def _text(field):
    if field['errno'] is not None:
        return None
    value = bytes.fromhex(field['hex'])
    require(len(value) <= MAX_FIELD, 'USB diagnostic field exceeds bound')
    value = value.decode('ascii').strip()
    require('\x00' not in value and '\n' not in value and '\r' not in value,
            'USB diagnostic field is malformed')
    return value


def classify(handle, wanted):
    raw.require_success(handle)
    rows = [json.loads(line) for line in raw.read_stdout(handle, maximum=MAX_CAPTURE).splitlines()]
    require(rows[0]['kind'] == 'begin' and rows[-1]['kind'] == 'end',
            'USB diagnostic capture is incomplete')
    results = []
    for usb in (row for row in rows if row['kind'] == 'usb'):
        topology = usb['topology']
        interfaces = [row for row in rows if row['kind'] == 'interface' and topology in row['topologies']]
        if usb['errno'] is not None:
            state = 'ABSENT_USB' if usb['errno'] == errno.ENOENT else 'USB_READ_ERROR'
        else:
            fields = {name: _text(value) for name, value in usb['fields'].items()}
            if None in fields.values():
                state = 'USB_FIELD_UNAVAILABLE'
            elif any(fields[name] != value for name, value in dict(idVendor='1d6b', idProduct='0104',
                    serial=wanted['serial'], product='S22 Debian research').items()):
                state = 'USB_IDENTITY_MISMATCH'
            elif not interfaces:
                state = 'USB_WITHOUT_NETWORK_INTERFACE'
            else:
                addresses = [_text(row['address']) for row in interfaces]
                matches = addresses.count(wanted['host_mac'])
                state = ('MATCHING_ENDPOINT_OBSERVED' if matches == 1 else
                         'AMBIGUOUS_INTERFACES' if matches > 1 else
                         'INTERFACE_ADDRESS_UNAVAILABLE' if None in addresses else 'MAC_MISMATCH')
        results.append(dict(topology=topology, state=state,
                            interfaces=[row['name'] for row in interfaces]))
    return dict(schema='s22plus-debian-usb-observation-v1', ordinal=rows[0]['ordinal'],
                capture=pin(handle.receipt_path), paths=results,
                diagnostic_only=True, endpoint_acceptance=False)
