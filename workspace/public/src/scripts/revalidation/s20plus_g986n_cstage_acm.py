"""One read-only ACM witness for the attended y2q C-stage transaction."""
from array import array
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import select
import socket
import stat
import termios
import subprocess
import time

import s20plus_g986n_early_pair_f1 as base
import s20plus_g986n_p0_pid1_usb_observer as tty_reader

PROFILE = "s20plus-g986n-cstage-list-f1"
CANDIDATE = "32e40210c5487f37de32c3d541e454df03e86855d74a5a9c5cf420f7811b5b68"
RUN_ROOT = base.view.PRIVATE / "runs" / PROFILE
HEADER = base.view.PRIVATE / "outputs/s20plus-y2q-mainline-h0-20261122.yy9l1A/build-id.h"
HEADER_SHA = "f1c3738ded8d0e8e4c04cd3c5ebcbf41ad26f63d743eb6e03bce024b901238d5"
WINDOW = 180
READ_SECONDS = 12
MAX_BYTES = 512
EVIDENCE = "s20plus_cstage_acm_evidence_v1"
require = base.require


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(v):
    return (json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def witness():
    header = base.pinned(HEADER, HEADER_SHA)
    match = re.fullmatch(rb'#define Y2Q_BUILD_ID "([a-f0-9]{32})"\n', header)
    require(match is not None, "unexpected initramfs build identifier")
    build_id = match[1]
    return (b'y2q-' + build_id).decode(), b'\nS20PLUS_Y2Q_MAINLINE_V1 id=' + build_id + b' pid=1 stage=ACM_READY\n'


def host_serial_policy():
    """Check the reviewed local ModemManager policy before new candidate effects."""
    daemon = Path('/usr/sbin/ModemManager')
    unit = Path('/usr/lib/systemd/system/ModemManager.service')
    base.pinned(daemon, 'e1c6e899c75385544423cf96d5a67e37d516038e16c01680e3ccb5c59941a5e6')
    base.pinned(unit, '7440e1296cf610dd3847641c2bc93cadf210b4021964d07b7a59b6cf3d5aee06')
    control = '/usr/bin/systemctl'
    keys = 'ActiveState,FragmentPath,DropInPaths,MainPID,ExecStart,Environment,PassEnvironment,UnsetEnvironment'
    response = subprocess.check_output([control,'show','ModemManager.service','-p',keys],
                                       timeout=5, env=base.view.clean_environment(), text=True)
    values = dict(line.split('=', 1) for line in response.splitlines())
    require(values['FragmentPath'] == str(unit) and all(values[key] == '' for key in
            ('DropInPaths','Environment','PassEnvironment','UnsetEnvironment'))
            and values['ExecStart'].startswith('{ path=/usr/sbin/ModemManager ; argv[]=/usr/sbin/ModemManager ;')
            and values['ExecStart'].count('argv[]=') == 1, "host serial filter differs")
    manager = subprocess.check_output([control, 'show-environment'], timeout=5,
                                      env=base.view.clean_environment()).splitlines()
    require(not any(line.startswith(b'MM_FILTER_RULE_') for line in manager), "host serial filter override")
    pid = int(values['MainPID'])
    if values['ActiveState'] == 'active':
        require(pid > 1 and (Path('/proc')/str(pid)/'cmdline').read_bytes() == bytes(daemon)+b'\0',
                "host serial daemon invocation differs")
    else:
        require(values['ActiveState'] == 'inactive' and pid == 0, "host serial daemon is transitioning")


def lookup(port, serial, usb_root=tty_reader.USB_ROOT, tty_root=tty_reader.TTY_ROOT):
    """Read attributes of the prepared port only, then locate its one CDC-ACM interface."""
    nodes = [p for p in usb_root.iterdir() if tty_reader.USB_NODE_RE.fullmatch(p.name)
             and sha(('usb:' + p.name).encode()) == port]
    if not nodes:
        return None
    require(len(nodes) == 1, "ambiguous prepared USB port")
    node = nodes[0]
    usb = node.resolve(strict=True)
    attr = lambda key: tty_reader.optional_attr(usb / key, key)
    if (attr('idVendor'), attr('idProduct')) != ('1d6b', '0104'):
        return None
    if (attr('product'), attr('serial')) != ('S20+ y2q mainline witness', serial):
        return None
    matches = tty_reader.ttys_for_usb(node.name, usb, tty_root)
    if not matches:
        return None
    require(len(matches) == 1, "ambiguous mainline tty")
    chosen = matches[0]
    codes = tuple(tty_reader.optional_attr(chosen.interface_path / key, key)
                  for key in ('bInterfaceClass','bInterfaceSubClass','bInterfaceProtocol'))
    if codes != ('02','02','00'):
        return None
    bus, dev = attr('busnum'), attr('devnum')
    require(bus and bus.isdecimal() and dev and dev.isdecimal(), "invalid USB session")
    stamp = [port, serial, bus, dev, str(usb), str(chosen.interface_path),
             chosen.tty_name, chosen.major, chosen.minor]
    return chosen, sha(json.dumps(stamp, separators=(',', ':')).encode())


def saved(path):
    return base.OWNER.strict_private(path, compact=True)


def ticket(run):
    require(run.parent == RUN_ROOT and re.fullmatch(r'run-[0-9]{19}', run.name)
            and run.resolve(strict=True) == run, "wrong C-stage run")
    return base.ticket_dir(run)


def source(run, prepared):
    """Only a validated, completed transfer of this candidate can start observation."""
    t = ticket(run)
    outer = saved(t / 'prepared.json')
    transfer = saved(run / 'candidate-result.json')
    key = prepared['binding_sha256']
    binding = prepared['binding']
    port = binding['endpoint']['topology_sha256']
    require(outer['run'] == str(run) and outer['profile'] == binding['version'] == PROFILE
            and outer['candidate'] == CANDIDATE and outer['original'] == base.ORIGINAL
            and binding['run_dir'] == str(run) and binding['target'] == base.OWNER.TARGET
            and key == sha(canonical(binding))
            and port == outer['health']['topology_sha256']
            and transfer['binding_sha256'] == key and transfer['classification'] == 'odin_transfer_completed'
            and transfer['receipt']['ap']['sha256'] == CANDIDATE and transfer['replay_permitted'] is False,
            "invalid mainline ACM binding")
    return key, port, sha((run / 'candidate-result.json').read_bytes())


def intent_for(run, prepared):
    key, port, transfer = source(run, prepared)
    observed = saved(run / 'candidate-observation-intent.json')
    require(observed['binding_sha256'] == key and observed['timeout_seconds'] == WINDOW, "wrong observation window")
    start_us = round(datetime.fromisoformat(observed['at']).timestamp()*1_000_000)
    return dict(binding_sha256=key, topology_sha256=port, transfer_sha256=transfer, start_us=start_us)


def remaining(intent):
    age_us = time.time_ns()//1000 - intent['start_us']
    return (WINDOW-age_us/1_000_000) if age_us >= 0 else 0


def live_guard(run):
    guard = saved(base.OWNER.GUARD)
    require(guard['run_dir'] == str(run) and guard['candidate_sha256'] == CANDIDATE
            and guard['version'] == PROFILE and guard['unresolved'] is True, "wrong ACM observation owner")
    require((run / 'candidate-observation-intent.json').is_file()
            and not any(os.path.lexists(run / n) for n in ('candidate-observation.json',
                        'physical-rollback-intent.json','rollback-intent.json','terminal.json')),
            "closed ACM observation")


def open_for_child(channel, run, approval):
    """The outer process exposes only this one validated read descriptor to its own child."""
    prepared = saved(run / 'prepared.json')
    expected = intent_for(run, prepared)
    t = ticket(run)
    outer = saved(t / 'prepared.json')
    outer_key = sha(canonical(outer))
    accepted = saved(t / 'accepted.json')
    require(approval == base.PREFIX + outer_key and accepted['grant_sha256'] == outer_key
            and outer['issued'] <= accepted['approved_at'] < outer['expires']
            and accepted['approval_sha256'] == sha(approval.encode()), "ACM grant mismatch")
    packet = channel.recv(130)
    intent = saved(t / 'acm-intent.json')
    require(intent == expected and packet == (expected['binding_sha256'] + ':open').encode(),
            "invalid ACM read request")
    live_guard(run)
    serial, _ = witness()
    now = lookup(expected['topology_sha256'], serial)
    require(now is not None, "ACM identity unavailable at open")
    require(remaining(intent) > 0, 'expired mainline observation')
    endpoint = tty_reader.DEV_ROOT / now[0].tty_name
    info = endpoint.lstat()
    require(stat.S_ISCHR(info.st_mode) and (os.major(info.st_rdev), os.minor(info.st_rdev)) ==
            (now[0].major, now[0].minor), "dynamic tty changed")
    require(remaining(intent) > 0, "mainline tty open deadline expired")
    fd = os.open(endpoint, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK | os.O_NOCTTY)
    try:
        tty_reader.verify_descriptor(now[0], fd)
        live_guard(run)
        again = lookup(expected['topology_sha256'], serial)
        require(again is not None and again[1] == now[1], "ACM endpoint changed during open")
        require(remaining(intent) > 0, "mainline descriptor handoff deadline expired")
        channel.sendmsg([now[1].encode()], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array('i', [fd]))])
    finally:
        os.close(fd)


def launch(namespace, env, run, approval):
    # The tty is created after the USB-hidden /dev mount. Send only the exact
    # tty fd on inherited stdin instead of exposing the host /dev filesystem.
    require(base.PROFILE == PROFILE and base.SCRIPT.name == 's20plus_g986n_cstage_list_f1.py',
            "ACM transport belongs to the dedicated owner")
    args = ['--execute','--run-dir',str(run),'--approval',approval]
    # The desktop can order CLI flags differently. The owner normalizes this
    # single command before entering the existing reviewed source view.
    require(namespace == base.OWNER.namespace(args, connected=True)
            and env == base.view.clean_environment(), "unexpected ACM source view")
    host, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    with host, child, subprocess.Popen(namespace, env=env, stdin=child) as process:
        child.close()
        while process.poll() is None:
            if select.select([host], [], [], 0.5)[0]:
                try:
                    if host.recv(1, socket.MSG_PEEK):
                        open_for_child(host, run, approval)
                except (OSError, ValueError, KeyError, base.OWNER.Stop, tty_reader.ObserverError):
                    pass  # Child turns a closed socket into a recorded observation gap.
                finally:
                    host.close()
                break
        return process.wait()


def get_descriptor(key, identity):
    with socket.socket(fileno=os.dup(0)) as channel:
        channel.settimeout(3)
        channel.sendall((key + ':open').encode())
        item = array('i')
        data, ancillary, flags, _ = channel.recvmsg(65, socket.CMSG_SPACE(item.itemsize), socket.MSG_CMSG_CLOEXEC)
        for level, kind, raw in ancillary:
            if (level, kind) == (socket.SOL_SOCKET, socket.SCM_RIGHTS):
                item.frombytes(raw)
        if len(item) != 1 or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC) or data != identity.encode():
            for fd in item:
                os.close(fd)
            raise OSError("no matching mainline tty descriptor")
        return item[0]


def bounded_read(fd, expected, deadline):
    import fcntl
    import tty
    require(time.monotonic() < deadline, "ACM setup deadline expired")
    fcntl.ioctl(fd, termios.TIOCEXCL)
    require(time.monotonic() < deadline, "ACM line setup deadline expired")
    tty.setraw(fd, termios.TCSANOW)
    buf = bytearray()
    while len(buf) < MAX_BYTES:
        wait = deadline - time.monotonic()
        if wait <= 0 or not select.select([fd], [], [], wait)[0]:
            break
        if time.monotonic() >= deadline:
            break
        try:
            chunk = os.read(fd, MAX_BYTES - len(buf))
        except BlockingIOError:
            continue
        if not chunk:
            break
        buf.extend(chunk)
        if expected in buf:
            break
    return bytes(buf)


def sample(run, prepared, intent, deadline):
    key, port = intent['binding_sha256'], intent['topology_sha256']
    serial, banner = witness()
    raw = b''
    before = after = verified_us = None
    status = 'not_seen'
    try:
        while time.monotonic() < deadline:
            chosen = lookup(port, serial)
            if chosen is not None:
                before = chosen[1]
                status = 'unproved'
                live_guard(run)
                require(time.monotonic() < deadline and remaining(intent) > 0, "late ACM selection")
                fd = get_descriptor(key, before)
                try:
                    tty_reader.verify_descriptor(chosen[0], fd)
                    left = min(remaining(intent), READ_SECONDS)
                    raw = bounded_read(fd, banner, min(deadline, time.monotonic()+left))
                    tty_reader.verify_descriptor(chosen[0], fd)
                    again = lookup(port, serial)
                    if again and time.monotonic() < deadline:
                        verified_us = time.time_ns()//1000
                        if intent['start_us'] <= verified_us < intent['start_us'] + WINDOW*1_000_000:
                            after = again[1]
                finally:
                    os.close(fd)
                if before == after and banner in raw:
                    status = 'pid1_exact'
                break
            time.sleep(min(0.25, max(0, deadline-time.monotonic())))
    except (OSError, ValueError, termios.error, base.OWNER.Stop, tty_reader.ObserverError):
        status = 'unproved'
    return dict(**intent, state=status, endpoint_before=before, endpoint_after=after, verified_us=verified_us,
                size=len(raw), stream_sha256=sha(raw), stream_hex=raw.hex())


def derive(raw, intent):
    require(all(raw[k] == v for k,v in intent.items()), "ACM raw binding differs")
    data = bytes.fromhex(raw['stream_hex'])
    state = raw['state']
    require(type(raw['size']) is int and len(data) == raw['size'] <= MAX_BYTES
            and raw['stream_sha256'] == sha(data) and state in ('pid1_exact','not_seen','unproved'),
            "ACM raw capture differs")
    for k in ('endpoint_before','endpoint_after'):
        require(raw[k] is None or re.fullmatch('[0-9a-f]{64}',raw[k]), "invalid endpoint bracket")
    verified = raw['verified_us']
    timely = type(verified) is int and intent['start_us'] <= verified < intent['start_us'] + WINDOW*1_000_000
    fact = (timely and raw['endpoint_before'] is not None and raw['endpoint_before'] == raw['endpoint_after']
            and witness()[1] in data)
    require((state == 'pid1_exact') == fact and (state != 'not_seen' or
            (not data and raw['endpoint_before'] is None and raw['endpoint_after'] is None)), "ACM witness differs")
    return dict(schema=EVIDENCE, binding_sha256=intent['binding_sha256'], state=state,
                raw_sha256=sha(canonical(raw)))


def observe(run, prepared):
    t = ticket(run)
    intent = intent_for(run, prepared)
    deadline = time.monotonic() + max(0, remaining(intent))
    live_guard(run)
    base.put(t, 'acm-intent', intent)
    raw = sample(run, prepared, intent, deadline)
    base.put(t, 'acm-raw', raw)
    result = derive(raw, intent)
    base.put(t, 'acm-evidence', result)
    time.sleep(max(0, deadline-time.monotonic()))
    return result


def validate(result, run, prepared):
    t = ticket(run)
    intent = intent_for(run, prepared)
    require(saved(t/'acm-intent.json') == intent and saved(t/'acm-evidence.json') == result
            and derive(saved(t/'acm-raw.json'), intent) == result, "saved ACM evidence differs")
    return result
