"""Fixed unprivileged installed-Debian probe over the protected root inspector."""
import hashlib
import re
import struct

import s22plus_native_root_inspect_profile_v1 as inspection
import s22plus_root_console_v1 as wire
from s22plus_native_records_v3 import read, require, verify

ROOT = inspection.ROOT
SCHEMA = 's22plus-native-userspace-probe-v1'
PROFILE = 'thermal-v3-reconnect-ufs-drain-userspace-probe-v1'
OPERATION = SELECTION = 'userspace-probe'
P402 = ROOT / 'workspace/private/outputs/s22plus-debian-root-inspect-h0-20260923-1/prepared-1/task'
TERMINAL = dict(path=str(P402 / 'operation-0001/terminal.json'), size=2432,
    sha256='995b6784fbbc193581676ff60fc9cd04efad22abc878ba027bc94a6dd1dbf9a6')
CLOSED = dict(path=str(P402 / 'closed.json'), size=2809,
    sha256='2e1f073c959069fe7176975feaf560d5f8780520ab91bbe6cca9f5b90a3a5b01')
WORKLOAD = b'''set -eu
[ "$(/usr/bin/id -u)" = 65534 ]
[ "$(/usr/bin/id -g)" = 65534 ]
[ ! -e /proc/self ] && [ ! -e /sys/kernel ] && [ ! -e /dev/null ]
printf 'UP_WORK shell uid=65534 gid=65534\\n'
/usr/bin/printf 'UP_WORK libc external\\n'
/bin/sh -c '/usr/bin/printf "UP_WORK fork child\\n"'
if /bin/sh -c 'exit 23'; then exit 81; else status=$?; fi
[ "$status" -eq 23 ]
/usr/bin/printf 'UP_WORK exit observed=23\\n'
'''
EXPECTED_STDOUT = (b'UP_WORK shell uid=65534 gid=65534\n'
    b'UP_WORK libc external\nUP_WORK fork child\nUP_WORK exit observed=23\n')


def prior_inputs():
    artifact, _, plan = inspection.prior_inputs()
    terminal = read(verify(TERMINAL)); closed = read(verify(CLOSED))
    result = terminal['root_inspection']
    require(terminal['terminal_state'] == closed['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and
        terminal['research_closed'] is True and closed['current_android_terminal'] == TERMINAL and
        closed['consumed_operations'] == closed['operation_budget'] == 1 and closed['f1_owner_absent'] is True and
        result['status'] == 'PASS_INSPECTION_COMPLETED' and
        result['root_state'] == 'COMPLETE_RECORD_BOOT_INPUTS_MATCH' and
        result['comparison']['matched'] == result['comparison']['expected'] and
        result['markers'] == dict(start=1, complete=1, witness=1) and
        result['mounted'] is result['unmounted'] is result['partition_ro'] is True and
        result['persistent_writes'] is False and result['android_storage']['total_bytes'] == 34357624832,
        'P402 protected root observation and Android close differ')
    return artifact, terminal, plan


def execution_binding():
    return dict(terminal=TERMINAL, closed=CLOSED, uid=65534, gid=65534,
        workload_sha256=hashlib.sha256(WORKLOAD).hexdigest(),
        stdout_sha256=hashlib.sha256(EXPECTED_STDOUT).hexdigest(),
        output_maximum=4096, child_seconds=30, mount_flags='private-bind-remount-ro-exec-nodev-nosuid',
        native_parent_noexec=True, persistent_writes=False, pid1_handoff=False)


def image_binding(image):
    require(image['profile'] == PROFILE and image['userspace_probe'] == execution_binding(),
        'userspace probe execution or predecessor scope differs')
    prior_inputs()
    return inspection.image_binding(dict(image, profile=inspection.PROFILE))


def _output(line, stream):
    match = re.fullmatch(r'UP1_OUTPUT stream=' + stream + r' bytes=(0|[1-9][0-9]{0,4}) hex=(-|[0-9a-f]+)', line)
    require(match is not None, 'userspace output frame differs')
    size = int(match[1]); data = b'' if match[2] == '-' else bytes.fromhex(match[2])
    require(len(data) == size and size <= (16 if stream == 'setup' else 4096) and
        (match[2] == '-') == (size == 0), 'userspace output length differs')
    return data


def decode(stdout, stderr, binding):
    require(not stderr and 0 < len(stdout) <= inspection.MAXIMUM and stdout.endswith(b'\n'),
        'userspace probe capture is incomplete')
    lines = stdout.decode('ascii').splitlines()
    require(lines[-1].startswith('UP1_RESULT '), 'userspace terminal is absent')
    final = inspection._row(lines[-1], 'UP1_RESULT', ('complete', 'attempted', 'proved', 'error'))
    base_lines = [line for line in lines[:-1] if not line.startswith('UP1_')]
    base = inspection.decode(('\n'.join(base_lines)+'\n').encode(), b'', binding)
    extra = [line for line in lines[:-1] if line.startswith('UP1_')]
    require(final['complete'] == 1 and final['error'] == 0 and final['attempted'] in (0, 1) and final['proved'] in (0, 1),
        'userspace probe or cleanup did not complete')
    result = dict(status='PASS_PROBE_COMPLETED', userspace_proved=False, root_inspection=base,
        child=None, persistent_writes=False, chroot_proved=False, debian_boot_proved=False)
    if not base['superblock']['clean']:
        require(not extra and final == dict(complete=1, attempted=0, proved=0, error=0),
            'unclean root reached userspace')
        return dict(result, verdict='SKIPPED_UNCLEAN_ROOT')
    # The only extension is a contiguous block between comparison and unmount.
    position = next(i for i, line in enumerate(lines) if line.startswith('RI1_COMPARE ')) + 1
    require(lines[position:position+len(extra)] == extra and lines[position+len(extra)] == 'RI1_UNMOUNT complete=1',
        'userspace records are outside the owned mount lifetime')
    eligible = inspection._row(extra[0], 'UP1_ELIGIBLE', ('exact',))
    require(eligible['exact'] in (0, 1), 'userspace eligibility differs')
    if not eligible['exact']:
        require(len(extra) == 1 and final == dict(complete=1, attempted=0, proved=0, error=0),
            'ineligible root executed a workload')
        return dict(result, verdict='SKIPPED_ROOT_NOT_EXACT')
    comparison, tree = base['comparison'], base['tree']
    require(base['markers'] == dict(start=1, complete=1, witness=1) and
        comparison['expected'] == comparison['matched'] and tree['entries'] == comparison['expected']+4 and
        tree['other'] == 0 and len(extra) == 6 and final['attempted'] == 1,
        'userspace execution lacks exact complete root closure')
    out = _output(extra[1], 'stdout'); err = _output(extra[2], 'stderr'); setup = _output(extra[3], 'setup')
    child = inspection._row(extra[4], 'UP1_CHILD', ('attempted', 'reaped', 'adopted', 'settled', 'status',
        'setup_stage', 'setup_errno', 'error', 'proved'))
    require(child['attempted'] == child['reaped'] == child['settled'] == 1 and child['error'] == 0 and
        child['status'] <= 65535 and child['adopted'] <= 16 and child['proved'] in (0, 1) and
        extra[5] == 'UP1_PARENT readonly=1 noexec=1 partition_ro=1',
        'userspace process settlement or parent protection is absent')
    require(len(setup) in (8, 16), 'absent or partial exec setup evidence')
    packets = [struct.unpack('<II', setup[i:i+8]) for i in range(0, len(setup), 8)]
    if packets:
        require(packets[-1] == (child['setup_stage'], child['setup_errno']) and
            ((len(packets) == 1 and (packets[0] == (100, 0) or
                1 <= packets[0][0] <= 7 and 0 < packets[0][1] <= 4095)) or
             (len(packets) == 2 and packets[0] == (100, 0) and packets[1][0] == 101 and 0 < packets[1][1] <= 4095)),
            'userspace setup/exec result framing differs')
    proved = packets == [(100, 0)] and child['status'] == child['adopted'] == 0 and out == EXPECTED_STDOUT and not err
    require(child['proved'] == final['proved'] == int(proved), 'userspace verdict differs from actual child evidence')
    captures = {name:dict(size=len(data), sha256=hashlib.sha256(data).hexdigest())
        for name, data in (('stdout', out), ('stderr', err), ('setup', setup))}
    return dict(result, verdict='PROVED_FIXED_DEBIAN_USERSPACE' if proved else 'WORKLOAD_NOT_PROVED',
        userspace_proved=proved, chroot_proved=bool(packets and packets[0] == (100, 0)),
        child=dict(child, **captures), workload_sha256=hashlib.sha256(WORKLOAD).hexdigest())


class Profile:
    RESULT_KEY = 'userspace_probe'
    MUTATES = True  # Intended before the partition RAM RO control and child launch.
    SETTLE_SECONDS = 0
    OBSERVATION_SECONDS = 300
    ADMISSION_SECONDS = 245

    def __init__(self, image):
        self.binding = image_binding(image)
        require(re.fullmatch('[0-9a-f]{32}', image['run_id_hex']), 'userspace command identity differs')
        self.BODY = wire.command(('exec /s22-userspace-probe probe ' + image['run_id_hex']).encode(),
            cwd=b'/s22-root-work', timeout_ms=240000)

    def project(self, stdout, stderr, terminal, *, requested):
        result = dict(schema=SCHEMA, status='NO_PROOF', requested=requested,
            stdout=dict(size=len(stdout), sha256=hashlib.sha256(stdout).hexdigest()),
            stderr=dict(size=len(stderr), sha256=hashlib.sha256(stderr).hexdigest()))
        if not requested: return dict(result, reason='ORIGINAL_OBSERVATION_BUDGET_INSUFFICIENT')
        if terminal is None or terminal[:4] != (5, 0, 0, 0) or terminal[4] != len(stdout)+len(stderr) or terminal[5] != 0:
            return dict(result, reason='USERSPACE_COMMAND_INCOMPLETE')
        try: proof = decode(stdout, stderr, self.binding)
        except (ValueError, UnicodeError, IndexError) as error: return dict(result, reason=str(error))
        return dict(result, **proof)
