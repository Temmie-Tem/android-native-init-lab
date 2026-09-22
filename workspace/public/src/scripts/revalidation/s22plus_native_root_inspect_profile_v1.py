"""Fixed read-only root inspection, including the partition-only RAM RO guard."""
import hashlib
from pathlib import Path
import re

import s22plus_root_console_v1 as wire
import s22plus_native_ext4_source_v1 as filesystem
from s22plus_native_records_v3 import read, require, verify

ROOT = filesystem.ROOT
SCHEMA = 's22plus-native-root-inspect-v1'
PROFILE = 'thermal-v3-reconnect-ufs-drain-root-inspect-v1'
SELECTION = 'root-inspection'
OPERATION = 'root-inspect'
PREVIOUS = ROOT / 'workspace/private/outputs/s22plus-debian-device-prep-20260921-1'
ARTIFACT = dict(path=str(PREVIOUS / 'artifact-7/artifact.json'), size=48870,
    sha256='bca7f42259a8e2f30806dfbf11ad213406f17959b9d38113cf5dca95c9ca2d17')
TERMINAL = dict(path=str(PREVIOUS / 'p401-first-boot-run-3/terminal.json'), size=956,
    sha256='e15acd4deb95c8e584628bf882b6168f6394709ca65622448e389d727caa9b39')
ROOTFS_SHA = 'ef8f10f95effcb92bf2b40525c9b8cb9c0e97857d2796c3b9e6c115a882df04f'
MAXIMUM = 65536


def prior_inputs():
    artifact = read(verify(ARTIFACT))
    terminal = read(verify(TERMINAL))
    plan = read(verify(terminal['plan']))
    require(artifact['filesystem_binding'] == filesystem.BINDING and
        artifact['rootfs']['sha256'] == ROOTFS_SHA and
        terminal['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and
        terminal['verdict'] == 'NO_PROOF_ANDROID_CLOSED_HEALTHY' and
        terminal['original_A_transfer_proved'] is True and
        plan['candidate']['ap'] == artifact['ap'], 'consumed P401 evidence identity differs')
    return artifact, terminal, plan


def image_binding(image):
    value = image['root_inspection']
    require(image['profile'] == PROFILE and set(value) == {'binding', 'artifact', 'terminal', 'helper', 'table',
        'table_count', 'boot_count', 'max_hashed_bytes', 'kernel_partition_ro', 'persistent_writes'},
        'root inspection binding schema differs')
    require(value['binding'] == filesystem.BINDING and value['artifact'] == ARTIFACT and
        value['terminal'] == TERMINAL and value['kernel_partition_ro'] is True and
        value['persistent_writes'] is False and value['max_hashed_bytes'] == 512 * 1024 * 1024 and
        type(value['table_count']) is int and 0 < value['table_count'] <= 20000 and
        type(value['boot_count']) is int and 0 < value['boot_count'] <= value['table_count'],
        'root inspection changes its original artifact or read bounds')
    prior_inputs()
    verify(value['binding']); verify(value['table'], maximum=2 * 1024 * 1024)
    verify(value['helper'], maximum=2 * 1024 * 1024)
    return value


def _row(line, prefix, fields):
    require(line.startswith(prefix + ' '), 'inspection record order differs: ' + prefix)
    items = line[len(prefix)+1:].split(' ')
    require(len(items) == len(fields), 'inspection record width differs: ' + prefix)
    result = {}
    for item, field in zip(items, fields):
        key, sep, value = item.partition('=')
        require(sep and key == field and value, 'inspection field order differs')
        if field in ('sha256', 'path_sha256', 'kind'):
            require(re.fullmatch('[0-9a-f]{64}', value) if field != 'kind' else
                value in ('missing', 'ancestor', 'metadata', 'content'), 'inspection text field differs')
            result[field] = value
        else:
            require(re.fullmatch('0|[1-9][0-9]{0,19}', value), 'inspection integer differs')
            result[field] = int(value)
    return result


def decode(stdout, stderr, binding):
    require(not stderr and 0 < len(stdout) <= MAXIMUM and stdout.endswith(b'\n'),
        'inspection output is incomplete or has diagnostics')
    lines = stdout.decode('ascii').splitlines()
    require(lines[:3] == ['RI1_BEGIN version=1', 'RI1_BIND exact=1', 'RI1_BLOCK_RO partition=1'],
        'exact binding or partition-only RO protection is absent')
    superblock = _row(lines[3], 'RI1_SUPER', ('clean', 'state', 'recover', 'orphan'))
    require(superblock['clean'] in (0, 1) and superblock['recover'] in (0, 1) and
        superblock['state'] <= 65535 and superblock['orphan'] <= 2**32-1 and
        bool(superblock['clean']) == (superblock['state'] == 1 and not superblock['recover'] and not superblock['orphan']),
        'inspection superblock cleanliness contradicts its raw fields')
    markers = tree = comparison = None
    findings = []
    if superblock['clean']:
        require(lines[4] == 'RI1_MOUNT readonly=1 noload=1 nodev=1 noexec=1 nosuid=1',
            'protected read-only mount is absent')
        markers = _row(lines[5], 'RI1_MARKERS', ('start', 'complete', 'witness'))
        require(all(v in (0, 1, 2) for v in markers.values()), 'inspection marker state differs')
        tree = _row(lines[6], 'RI1_TREE', ('entries', 'files', 'dirs', 'links', 'other', 'bytes', 'sha256'))
        require(tree['entries'] == sum(tree[k] for k in ('files', 'dirs', 'links', 'other')) and
            tree['entries'] <= 20000, 'inspection tree count differs')
        pos = 7
        while pos < len(lines) and lines[pos].startswith('RI1_FINDING '):
            findings.append(_row(lines[pos], 'RI1_FINDING', ('path_sha256', 'kind'))); pos += 1
        require(len(findings) <= 32, 'inspection finding bound exceeded')
        comparison = _row(lines[pos], 'RI1_COMPARE', ('expected', 'matched', 'missing', 'metadata', 'content',
            'boot_expected', 'boot_missing', 'boot_metadata', 'boot_content', 'hashed_bytes', 'findings'))
        require(comparison['expected'] == binding['table_count'] and comparison['boot_expected'] == binding['boot_count']
            and comparison['expected'] == sum(comparison[k] for k in ('matched', 'missing', 'metadata', 'content'))
            and sum(comparison[k] for k in ('boot_missing', 'boot_metadata', 'boot_content')) <= comparison['boot_expected']
            and all(comparison['boot_' + k] <= comparison[k] for k in ('missing', 'metadata', 'content'))
            and comparison['hashed_bytes'] <= binding['max_hashed_bytes'] and
            comparison['findings'] == len(findings) == min(32, sum(comparison[k] for k in ('missing', 'metadata', 'content'))),
            'inspection comparison accounting differs')
        require(lines[pos+1] == 'RI1_UNMOUNT complete=1', 'normal unmount is absent')
        pos += 2
    else:
        pos = 4
    require(len(lines) == pos + 2 and lines[pos] == 'RI1_FINAL super_unchanged=1 gpt_unchanged=1 partition_ro=1',
        'inspection final binding or exact output boundary differs')
    final = _row(lines[pos+1], 'RI1_RESULT', ('complete', 'stage', 'errno', 'cleanup_errno',
        'partition_ro', 'clean', 'mounted', 'unmounted'))
    require(final == dict(complete=1, stage=10, errno=0, cleanup_errno=0, partition_ro=1,
        clean=superblock['clean'], mounted=superblock['clean'], unmounted=superblock['clean']),
        'inspection did not complete its fixed read and cleanup')
    state = 'MOUNT_SKIPPED_UNCLEAN'
    boot_match = False
    if markers:
        boot_match = not any(comparison[k] for k in ('boot_missing', 'boot_metadata', 'boot_content'))
        if 2 in markers.values() or markers['witness'] != 1 or markers['complete'] and not markers['start']:
            state = 'MARKER_OR_WITNESS_MISMATCH'
        elif markers['start'] == 1 and markers['complete'] == 0:
            state = 'INCOMPLETE_INSTALLATION_RECORD'
        elif markers['start'] == markers['complete'] == 1:
            state = 'COMPLETE_RECORD_BOOT_INPUTS_MATCH' if boot_match else 'COMPLETE_RECORD_FILES_DIFFER'
        else:
            state = 'NO_INSTALLATION_RECORDS'
    return dict(status='PASS_INSPECTION_COMPLETED', root_state=state, superblock=superblock,
        markers=markers, tree=tree, comparison=comparison, findings=findings,
        mounted=bool(superblock['clean']), unmounted=bool(superblock['clean']), partition_ro=True,
        boot_inputs_match=boot_match, persistent_writes=False, chroot_proved=False, debian_boot_proved=False)


class Profile:
    RESULT_KEY = 'root_inspection'
    MUTATES = True  # One partition-only kernel RO control, never a data write.
    SETTLE_SECONDS = 0
    OBSERVATION_SECONDS = 300
    ADMISSION_SECONDS = 245

    def __init__(self, image):
        self.binding = image_binding(image)
        require(re.fullmatch('[0-9a-f]{32}', image['run_id_hex']), 'inspection command identity differs')
        self.BODY = wire.command(('exec /s22-root-inspect inspect ' + image['run_id_hex']).encode(),
            cwd=b'/s22-root-work', timeout_ms=240000)

    def project(self, stdout, stderr, terminal, *, requested):
        result = dict(schema=SCHEMA, status='NO_PROOF', requested=requested,
            stdout=dict(size=len(stdout), sha256=hashlib.sha256(stdout).hexdigest()),
            stderr=dict(size=len(stderr), sha256=hashlib.sha256(stderr).hexdigest()))
        if not requested:
            return dict(result, reason='ORIGINAL_OBSERVATION_BUDGET_INSUFFICIENT')
        if terminal is None or terminal[:4] != (5, 0, 0, 0) or terminal[4] != len(stdout)+len(stderr) or terminal[5] != 0:
            return dict(result, reason='INSPECTION_COMMAND_INCOMPLETE')
        try:
            proof = decode(stdout, stderr, self.binding)
        except (ValueError, UnicodeError, IndexError) as error:
            return dict(result, reason=str(error))
        return dict(result, **proof)
