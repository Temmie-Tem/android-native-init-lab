"""Phase 2c: one fixed rooted-Android read of the UFS test block after a V17 series step.

A fixed D0 read on the healthy original Android that the preceding series step
returned to. It uses Android's existing LU0 block node, read only, and reads
exactly the 4096-byte block at LBA 62,305,152. It creates no node or mount,
loads no module, opens nothing writable, accepts no caller path, offset or
length, changes no boot mode and performs no transfer. The read is one claimed
series step: it is never retried, and a stopped read is not repeated. It runs
attended, on the same host boot, within the series step time of the V17
closure, and only on the very Android boot that closure's final health proved.
"""
import argparse
import hashlib
from pathlib import Path
import shlex
import sys

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_mainline_series_v1 as series
import s22plus_mainline_task_v1 as mainline
import s22plus_native_target_io_v3 as target_io
from s22plus_native_records_v3 import canonical, clock, digest, host_boot, pin, private_path, publish, read, require, verify

SCHEMA = 's22plus-mainline-ufs-android-block-v1'
TEST_LBA = 62305152
LU0_SECTORS = 62305280 * 8
TEST_SECTOR = TEST_LBA * 8
ZERO_SHA256 = hashlib.sha256(bytes(4096)).hexdigest()
PATTERN_SHA256 = '1155097a861b1bdf671fc262e660197e2974599d89831fd1d32b20304e820d18'
SCRIPT = r'''set -eu
B=/system/bin/toybox
v=$($B readlink -f /dev/block/by-name/userdata)
u=/sys/class/block/${v##*/}
r=$($B readlink -f "$u")
p=${r%/*}
case "$p" in /sys/devices/platform/soc*/1d84000.ufshc/host*/target*/*:0:0:0/block/sd?) ;; *) exit 1;; esac
d=/dev/block/${p##*/}
[ -b "$d" ]
IFS=: read a b <"$p/dev"
[ "$($B stat -c %t:%T "$d")" = "$(printf '%x:%x' "$a" "$b")" ]
[ "$($B cat "$p/queue/logical_block_size")" = 4096 ]
[ "$($B cat "$p/size")" = LU0_SECTORS ]
for n in "$p/${p##*/}"[0-9]*; do
  s=$($B cat "$n/start"); z=$($B cat "$n/size")
  case "$s$z" in ''|*[!0-9]*) exit 1;; esac
  [ $((s+z)) -le TEST_SECTOR ]
done
printf 'B0\n'
$B dd if="$d" bs=4096 skip=TEST_LBA count=1 status=none
printf 'END\n'
'''.replace('LU0_SECTORS', str(LU0_SECTORS)).replace('TEST_SECTOR', str(TEST_SECTOR)).replace(
    'TEST_LBA', str(TEST_LBA))
MAX_OUTPUT = 4096 + 64


def command(android):
    features = android.command(['-s', android.target['serial'], 'features'], 'shell-features', timeout=10)
    handle = raw.load_handle(verify(pin(features.receipt_path)))
    require('shell_v2' in raw.decode_success_stdout(handle, maximum=16384).splitlines(),
            'Android shell-v2 transport is unavailable; no legacy fallback')
    android.guard()
    with transport.pin_regular_file(Path(android.tool['path']), label='ADB',
            expected_size=android.tool['size'], expected_sha256=android.tool['sha256']) as tool:
        android.guard()
        return raw.acquire_command([str(tool.path), '-s', android.target['serial'],
            'shell', '-T', 'su -c ' + shlex.quote(SCRIPT)], android.directory, 'block',
            timeout=15, stdout_maximum=MAX_OUTPUT, stderr_maximum=16384)


def projection(receipt):
    handle = raw.load_handle(verify(receipt))
    stdout = raw.read_stdout(handle, maximum=MAX_OUTPUT)
    stderr = raw.read_stderr(handle, maximum=16384)
    if (handle.returncode != 0 or handle.timed_out or handle.output_exceeded or
            handle.producer_error_type is not None or stderr or len(stdout) != 4096 + 7 or
            not stdout.startswith(b'B0\n') or not stdout.endswith(b'END\n')):
        return dict(status='NO_PROOF', capture=receipt, sha256=None)
    value = hashlib.sha256(stdout[3:-4]).hexdigest()
    status = 'PATTERN' if value == PATTERN_SHA256 else 'ZERO' if value == ZERO_SHA256 else 'OTHER'
    return dict(status=status, capture=receipt, sha256=value, test_lba=TEST_LBA)


def closure_boot(closed):
    """The Android boot the preceding V17 closure's final health proved."""
    return series.final_health(read(verify(closed['current_android_terminal'])))['boot_id_sha256']


def read_block(root, series_pin, index, output, *, attended):
    require(attended is True, 'the Android block read runs only attended')
    root = Path(root).resolve(strict=True)
    output = private_path(root, output, exists=False)
    require(not output.exists(), 'Android block output already exists; no retry')
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root)
        subject = dict(output=str(output))
        current, base, approved = series.bind_step(root, series_pin, index, kind='android-block', task_pin=subject)
        require(output == series.block_path(base, index), 'the Android block read writes only <series>/block-<step>')
        earlier = read(series.claim_path(base, current['steps'][index]['of_step']))
        closed = read(verify(pin(Path(earlier['closed']['path']))))
        task_pin = closed['task']
        task = read(verify(task_pin))
        require(task_pin == earlier['subject'] and mainline.ufs_storage(task['N']) and
                read(verify(task['N']['capability']))['fixed']['report_version'] >= 17,
                'the preceding step is not a V17 storage task')
        # The reader is in that capability's closure; its sources must be unchanged.
        review = mainline.capability(root, image=task['N'])
        require(review == task['review'], 'preceding capability changed')
        # Directly after that closure, on this host boot (the series checked it).
        expected_boot = closure_boot(closed)
        window = (closed['closed_boottime_ns'], closed['closed_boottime_ns'] + current['seconds'] * 1_000_000_000)
        require(window[0] <= clock() < window[1], 'the Android block read is not within the step time of its V17 closure')
        output.mkdir(mode=0o700)
        claimed = read(verify(series.claim(root, series_pin, index, subject=subject, closed_path=output/'terminal.json')))
        # Decided once, by the claim's own recorded time: a claim made after the window
        # is consumed and never reads. The read then runs under the ordinary D0 bound.
        require(window[0] <= claimed['claimed_ns'] < window[1],
                'the Android block read was claimed after the step time of its V17 closure; consumed, not run')
        epoch, start = host_boot(), clock()

        def guard():
            require(host_boot() == epoch and clock() < start + 600_000_000_000, 'Android D0 host epoch or bound changed')
            registry.require_no_f1_owner(root)
        publish(output/'open.json', dict(schema=SCHEMA, series=series_pin, step=index, task=task_pin,
            closed=pin(Path(earlier['closed']['path'])), approval=pin(base/'operator-approval.json'),
            command_sha256=digest(SCRIPT.encode()), host_boot=epoch, started_ns=start,
            closure_boot_id_sha256=expected_boot, attended=True))
        try:
            before = target_io.Android(task['adb'], task['target'], task['A'], output/'before', guard=guard)
            require(before.health()['boot_id_sha256'] == expected_boot,
                    'Android is not on the boot its V17 closure proved')
            reader = target_io.Android(task['adb'], task['target'], task['A'], output/'read', guard=guard)
            command(reader)
            # One post-read health bracket, also after a failed read; never a second read.
            after = target_io.Android(task['adb'], task['target'], task['A'], output/'after', guard=guard)
            after.health(); guard()
            result = rederive(output, task)
            publish(output/'terminal.json', result)
            return result
        except Exception as error:
            # A read that completed keeps its content class even if the run stopped
            # afterwards, so a foreign block still stops the lane.
            capture = output/'read/block.capture.json'
            try:
                block = projection(pin(capture)) if capture.exists() else None
            except Exception:
                block = None
            publish(output/'stopped.json', dict(schema=SCHEMA, error_type=type(error).__name__,
                    block=block, retry_permitted=False, device_writes_permitted=False))
            raise


def rederive(output, task):
    output = Path(output); opened = read(output/'open.json')
    require(opened['schema'] == SCHEMA and opened['command_sha256'] == digest(SCRIPT.encode()) and
            read(verify(opened['task'])) == task, 'Android block read record differs')
    before, after = read(output/'before/health.json'), read(output/'after/health.json')
    for value in (before, after):
        require(target_io.health_projection(value['captures'], task['target'], task['A']) == value,
                'Android block health does not rederive')
    require(before['properties'] == after['properties'] and before['boot_id_sha256'] == after['boot_id_sha256'],
            'Android boot changed across the block read')
    require(before['boot_id_sha256'] == opened['closure_boot_id_sha256'] and opened['attended'] is True,
            'Android block read is not on its V17 closure boot')
    return dict(schema=SCHEMA, terminal_state='ANDROID_CLOSED_HEALTHY', research_closed=True,
                block=projection(pin(output/'read/block.capture.json')), series=opened['series'],
                step=opened['step'], task=opened['task'], initial_health=pin(output/'before/health.json'),
                final_health=pin(output/'after/health.json'), boot_id_sha256=after['boot_id_sha256'],
                device_writes=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[5])
    parser.add_argument('command', choices=('read',))
    parser.add_argument('series', type=Path)
    parser.add_argument('step', type=int)
    parser.add_argument('output', type=Path)
    parser.add_argument('--attended', action='store_true', required=True,
                        help='the operator is present for this one read')
    args = parser.parse_args()
    result = read_block(args.root, pin(private_path(args.root.resolve(strict=True), args.series)), args.step,
                        args.output, attended=args.attended)
    sys.stdout.write(canonical(result).decode())


if __name__ == '__main__':
    main()
