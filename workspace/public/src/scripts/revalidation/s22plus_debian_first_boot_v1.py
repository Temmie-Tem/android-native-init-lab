#!/usr/bin/env python3
"""One attended Debian installation with an independently owned original-A exit.

No connected phase is available before the common/target capability review.
Debian SSH is an explicit observer, never an alias for native CDC CONTROL.
"""
import argparse
import ast
from dataclasses import asdict
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid

import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_odin_transition_core as transition
import s22plus_native_target_io_v3 as target
import s22plus_native_android_storage_v1 as census
import s22plus_native_gpt_android_v1 as android_storage
import s22plus_native_gpt_profile_v1 as gpt
from s22plus_native_records_v3 import (Journal as BaseJournal, canonical, clock, digest, host_boot,
    pin, private_path, publish, read, require, sync_dir, verify)

ROOT = Path(__file__).resolve().parents[5]
SCHEMA = 's22plus-debian-first-boot-v1'
POLICY = ROOT / 'docs/operations/S22PLUS_DEBIAN_FIRST_BOOT_V1.md'
TARGET_POLICY = ROOT / 'docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md'
COMMON = ROOT / 'docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md'
REVIEW = ROOT / 'workspace/public/src/device-action/bindings/s22plus_debian_first_boot_v1_review.json'
PROFILE = ROOT / 'workspace/public/src/device-action/profiles/s22plus_fyg8.json'
PRIOR = ROOT / 'workspace/private/runs/s22plus-native-session-v3/p399-p400-native-ext4-20260917-1'
PRIOR_CLOSED = dict(path=str(PRIOR / 'closed.json'), size=4308,
    sha256='0c2b78e9cb82dcded0b54728664794d121d6d997862ffb1f33f6e99bb80cc6b8')
EFFECTS = ('android-download', 'candidate-install', 'workload', 'debian-reboot', 'debian-shutdown', 'android-restore')
RESEARCH = EFFECTS[:-1]
OBSERVATIONS = ('first-health', 'workload-result', 'second-health', 'persistence')


class Journal:
    """Existing immutable journals linked across host boot epochs.

    Each segment retains the existing same-boot monotonic validation. A new
    host boot may open a recovery segment anchored to the entire old tail;
    it never resets the effect history or renews the research deadline.
    """
    def __init__(self, directory, *, schema=SCHEMA):
        self.directory = Path(directory)
        self.schema = schema
        self.directory.mkdir(mode=0o700, exist_ok=True)

    def segments(self):
        result, predecessor = [], None
        paths = []
        for path in self.directory.iterdir():
            if re.fullmatch(r'\.epoch-[0-9a-f]{32}\.tmp', path.name):
                require(path.is_dir() and not path.is_symlink(), 'journal epoch staging type differs')
                require(not (path / 'events').exists() or not list((path / 'events').iterdir()),
                        'unpublished epoch unexpectedly contains events')
                continue
            paths.append(path)
        for index, path in enumerate(sorted(paths)):
            require(path.name == f'epoch-{index:04d}' and path.is_dir() and not path.is_symlink(),
                    'journal host-epoch sequence differs')
            metadata = read(path / 'epoch.json')
            require(set(metadata) == {'schema', 'host_boot', 'previous'} and metadata['schema'] == self.schema + '-host-epoch' and
                    re.fullmatch('[0-9a-f]{64}', metadata['host_boot']) and metadata['previous'] == predecessor,
                    'journal host-epoch binding differs')
            require((path / 'events').is_dir() and not (path / 'events').is_symlink(), 'journal event directory is missing')
            journal = BaseJournal(path / 'events')
            rows = journal.rows()
            predecessor = pin(journal.directory / f'{len(rows)-1:04d}.json') if rows else pin(path / 'epoch.json')
            result.append((path, metadata, journal, rows))
        return result

    def rows(self):
        return [row for _, _, _, rows in self.segments() for row in rows]

    def append(self, event, **data):
        segments = self.segments()
        if not segments or segments[-1][1]['host_boot'] != host_boot():
            predecessor = None
            if segments:
                path, _, journal, rows = segments[-1]
                predecessor = pin(journal.directory / f'{len(rows)-1:04d}.json') if rows else pin(path / 'epoch.json')
            path = self.directory / f'epoch-{len(segments):04d}'
            staging = self.directory / ('.epoch-' + uuid.uuid4().hex + '.tmp')
            staging.mkdir(mode=0o700)
            publish(staging / 'epoch.json', dict(schema=self.schema + '-host-epoch', host_boot=host_boot(), previous=predecessor))
            BaseJournal(staging / 'events')
            # The global target lease serializes writers. A published segment is
            # nonempty, so rename cannot replace an existing complete segment.
            require(not path.exists(), 'journal epoch already exists')
            os.rename(staging, path)
            sync_dir(self.directory)
            journal = BaseJournal(path / 'events')
        else:
            journal = segments[-1][2]
        result = journal.append(event, **data)
        self.rows()  # Validate the durable state before a caller may launch.
        return result


def source_paths():
    """Imported recovery closure; unused V3 helpers do not bind this owner.

    Reachable shared transport/health functions use their module-level imports.
    Prepare-only local imports are bound separately by capability_paths().
    A changed shared function still changes its reviewed file identity.
    """
    base = Path(__file__).parent
    unused_local = {
        ('s22plus_debian_first_boot_v1.py', 'capability_paths'): {'s22plus_debian_profile_v1'},
        ('s22plus_debian_first_boot_v1.py', 'prepare'): {'s22plus_debian_artifact_v1'},
        ('s22plus_native_android_storage_v1.py', 'closed_android'):
            {'s22plus_native_adapter_v3', 's22plus_native_session_v3', 's22plus_native_task_v3'},
        ('s22plus_native_android_storage_v1.py', 'observe'): {'s22plus_native_task_v3'},
        ('s22plus_native_gpt_android_v1.py', 'projection'):
            {'s22plus_native_ext4_session_v1', 's22plus_native_gpt_session_v1',
             's22plus_native_root_inspect_session_v1'},
        ('s22plus_native_gpt_android_v1.py', 'observe'): {'s22plus_native_session_v3'},
        ('s22plus_native_gpt_android_v1.py', 'reboot_persistence'): {'s22plus_native_session_v3'},
    }
    def imports(node, path, function=None):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): function = node.name
        if isinstance(node, ast.Lambda): function = '<lambda>'
        if isinstance(node, ast.Import): names = [a.name.split('.')[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module: names = [node.module.split('.')[0]]
        else: names = []
        local = {name for name in names if (base / (name + '.py')).is_file()}
        if function:
            require(local <= unused_local.get((path.name, function), set()),
                    'new local runtime import needs an explicit reviewed recovery binding')
            names = []
        return names + [name for child in ast.iter_child_nodes(node) for name in imports(child, path, function)]
    pending, paths = [Path(__file__).stem], set()
    while pending:
        path = base / (pending.pop() + '.py')
        if not path.is_file() or path in paths: continue
        paths.add(path)
        pending += imports(ast.parse(path.read_text()), path)
    return sorted(paths)


def capability_paths():
    import s22plus_debian_profile_v1 as declaration
    return sorted({ROOT / name for name in declaration.EXECUTION_FILES} | {
            ROOT / 'AGENTS.md', COMMON, TARGET_POLICY, POLICY, PROFILE,
            ROOT / 'docs/operations/DEVICE_ACTION_PROCESS_V2.md',
            ROOT / 'docs/operations/DEVICE_ACTION_RISK_TIERS.md',
            ROOT / 'workspace/public/src/debian/s22plus_v1/h0.py',
            ROOT / 'workspace/public/src/debian/s22plus_v1/device/prepare.py',
            ROOT / 'workspace/public/src/debian/s22plus_v1/device/vm_install_test.py',
            ROOT / 'workspace/public/src/debian/s22plus_v1/device/virt-binding.inc.c',
            ROOT / 'workspace/public/src/scripts/revalidation/s22plus_debian_profile_v1.py',
            ROOT / 'workspace/public/src/scripts/revalidation/s22plus_debian_artifact_v1.py'})


def capability(*, recovery=None):
    value = read(verify(recovery)) if recovery else read(REVIEW)
    require(value['schema'] == SCHEMA + '-review' and value['verdict'] == 'PASS_GO' and
            value['findings'] == [], 'Debian capability is not independently reviewed')
    expected = [pin(path, maximum=4 * 1024 * 1024) for path in source_paths()]
    require(value['owner_sources'] == expected, 'reviewed Debian owner source changed')
    if recovery is None:
        require(value['capability_sources'] == [pin(path, maximum=4 * 1024 * 1024) for path in capability_paths()],
                'independent review omits, duplicates, or changes the policy/native closure')
        require(digest(COMMON.read_bytes()).encode() in (ROOT / 'AGENTS.md').read_bytes() and
                POLICY.name.encode() in COMMON.read_bytes() and POLICY.name.encode() in TARGET_POLICY.read_bytes() and
                b'Status: **REVIEW_GATED_CAPABILITY**' in POLICY.read_bytes(),
                'Debian exception is not common-incorporated and target-adopted')
    return value


def health_evidence(value, plan):
    require(target.health_projection(value['captures'], plan['target'], plan['A']) == value,
            'rooted Android proof does not rederive')
    return value


def android_projection(folder, plan):
    first = health_evidence(read(folder / 'before/health.json'), plan)
    last = health_evidence(read(folder / 'after/health.json'), plan)
    require(first['properties'] == last['properties'], 'Android changed during the storage bracket')
    census.require_shell_v2(pin(folder / 'read/shell-features.capture.json'))
    meta = raw.load_handle(folder / 'read/metadata.capture.json')
    stat = raw.load_handle(folder / 'read/stat.capture.json')
    raw.require_success(meta); raw.require_success(stat)
    sealed = gpt.vectors(plan['basis']['gpt'])
    metadata = android_storage.metadata(raw.read_stdout(meta, maximum=65536), sealed, 'proposed')
    capacity = android_storage.storage_stat(raw.decode_success_stdout(stat, maximum=16384),
        dict(layout='proposed', geometry=plan['basis']['geometry']), sealed)
    require(capacity['total_bytes'] == 34357624832, 'Android32 capacity changed')
    return dict(first_health=pin(folder / 'before/health.json'), final_health=pin(folder / 'after/health.json'),
        metadata=metadata, capacity=capacity, metadata_capture=pin(meta.receipt_path), stat_capture=pin(stat.receipt_path),
        boot_id_sha256=last['boot_id_sha256'])


def retained_basis():
    closed = read(verify(PRIOR_CLOSED))
    prior = read(verify(closed['task']))
    terminal = read(verify(closed['current_android_terminal']))
    require(closed['terminal_state'] == terminal['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and
            closed['f1_owner_absent'] is True and closed['additional_recovery_transfers'] == 0,
            'predecessor has no closed Android return')
    result = read(verify(terminal['terminal_result']))
    for name in ('health', 'initial_health'): health_evidence(read(verify(result[name])), prior)
    sealed = gpt.vectors(prior['N']['gpt'])
    basis = prior['N']['android_return']
    meta = raw.load_handle(verify(result['gpt_android']['metadata_capture'])); raw.require_success(meta)
    require(android_storage.metadata(raw.read_stdout(meta, maximum=65536), sealed, 'proposed') == result['gpt_android']['metadata'],
            'predecessor GPT proof differs')
    stat = raw.load_handle(verify(result['gpt_android']['stat_capture']))
    storage = android_storage.storage_stat(raw.decode_success_stdout(stat, maximum=16384), basis, sealed)
    require(storage == result['gpt_android']['storage'] and storage['total_bytes'] == 34357624832,
            'predecessor Android32 capacity differs')
    recovery = read(verify(prior['recovery_evidence']))
    require(recovery['target'] == prior['target'] and recovery['A'] == prior['A'],
            'demonstrated original-A recovery target differs')
    target.transfer_completed(raw.load_handle(verify(recovery['transfer']['raw'])))
    health_evidence(recovery['health'], prior)
    return prior, dict(source=PRIOR_CLOSED, terminal=closed['current_android_terminal'],
        filesystem_binding=prior['N']['filesystem']['binding'], gpt=prior['N']['gpt'],
        geometry=basis['geometry'], recovery_evidence=prior['recovery_evidence'])


def ap_member(artifact, *, android=False):
    with transport.pin_boot_only_ap(Path(artifact['path']), label='Android A' if android else 'Debian candidate',
            expected_size=artifact['size'], expected_sha256=artifact['sha256'],
            require_deterministic_metadata=not android) as pinned:
        return transport.boot_only_member_receipt(pinned, label='bound boot', require_deterministic_metadata=not android)


def candidate_identity(plan, binding):
    return registry.derive_candidate_identity({'target': dict(model='SM-S906N', device='g0q')},
        dict(manifest_id='s22plus-debian-first-boot-v1', run_id=plan['candidate']['run_id'],
            candidate_ap=plan['candidate']['ap'], allowed_member='boot.img.lz4'), plan['candidate']['ap']['sha256'],
        approval_binding_sha256=binding, candidate_receipt=dict(**{k: plan['candidate']['ap'][k] for k in ('size', 'sha256')},
            member=plan['candidate']['member']))


def install_claim_path(plan):
    # Neither a new archive, filesystem UUID, image, nor output name renews this.
    key = digest(canonical(dict(target=plan['target'], first_lba=12115456, last_lba=62305023)))
    return ROOT / 'workspace/private/runs/s22plus-debian-first-boot-v1/installation-claims' / (key + '.json')


def durable_install_claim_directory(plan):
    parent = install_claim_path(plan).parent
    for directory in (parent.parent, parent):
        if not directory.exists(): directory.mkdir(mode=0o700)
        require(directory.is_dir() and not directory.is_symlink(), 'installation claim directory type differs')
        sync_dir(directory)
        sync_dir(directory.parent)
    return parent


def journal_state(journal):
    effects, completed, observations = {}, {}, {}
    terminal = False
    for row in journal.rows():
        event, data = row['event'], row['data']
        require(not terminal, 'journal continues after terminal publication')
        terminal = event == 'terminal'
        if event == 'effect-intent':
            require(set(data) == {'step', 'detail'} and data['step'] in EFFECTS and data['step'] not in effects,
                    'duplicate or unknown device effect intent')
            step = data['step']
            if step != 'android-restore':
                require(step != 'candidate-install' or 'android-download' in completed, 'candidate precedes Download')
                require(step != 'workload' or 'first-health' in observations, 'workload lacks Debian health')
                require(step != 'debian-reboot' or 'workload-result' in observations, 'reboot lacks workload proof')
                require(step != 'debian-shutdown' or 'persistence' in observations, 'shutdown lacks persistence')
                require('android-restore' not in effects, 'research follows Android recovery')
            effects[step] = row
        elif event == 'effect-result':
            require(set(data) == {'step', 'receipt'} and data['step'] in effects and data['step'] not in completed,
                    'effect result lacks a unique intent')
            completed[data['step']] = data['receipt']
        elif event == 'observation':
            require(set(data) == {'step', 'receipt'} and data['step'] in OBSERVATIONS and data['step'] not in observations,
                    'duplicate observation publication')
            needed = {'first-health': ('candidate-install', completed), 'workload-result': ('workload', completed),
                      'second-health': ('debian-reboot', completed), 'persistence': ('second-health', observations)}
            name, collection = needed[data['step']]
            require(name in collection, 'observation precedes its consumed/completed producer')
            observations[data['step']] = data['receipt']
        else:
            require(event in {'owner-opened', 'research-stopped', 'physical-recovery-armed', 'terminal'},
                    'unknown Debian owner journal event')
    return effects, completed, observations


def validate_grant(grant, plan_receipt, *, current):
    require(isinstance(grant, dict) and set(grant) == {
        'schema', 'plan', 'operator_statement', 'attended', 'host_boot', 'opened_ns', 'deadline_ns'},
        'attended grant schema differs')
    require(grant['schema'] == SCHEMA + '-grant' and grant['plan'] == plan_receipt and
            grant['attended'] is True and isinstance(grant['operator_statement'], str) and
            grant['operator_statement'].strip() and isinstance(grant['host_boot'], str) and
            re.fullmatch('[0-9a-f]{64}', grant['host_boot']) and
            type(grant['opened_ns']) is int and type(grant['deadline_ns']) is int and
            0 <= grant['opened_ns'] and grant['deadline_ns'] == grant['opened_ns'] + 7200_000_000_000,
            'attended grant binding or finite budget differs')
    if current:
        require(grant['host_boot'] == host_boot() and grant['opened_ns'] <= clock() < grant['deadline_ns'],
                'original research grant expired')


def project_debian(handle, plan):
    text = raw.decode_success_stdout(handle, maximum=65536, strip=False)
    require(not raw.read_stderr(handle, maximum=16384), 'Debian health has diagnostics')
    require(text.startswith('S22PLUS_FYG8_DEBIAN_V1 ' + plan['candidate']['run_id'] + '\n') and
            text.endswith('DEBIAN_HEALTH_PASS\n'), 'Debian health identity or terminal differs')
    boot = re.findall(r'^boot_id=([0-9a-f-]{36})$', text, re.M)
    count = re.findall(r'^boot_count=([1-9][0-9]*)$', text, re.M)
    require(len(boot) == len(count) == 1 and target.UUID.fullmatch(boot[0]), 'Debian boot identity is ambiguous')
    require('pid1_exe=/usr/sbin/init\n' in text and 'pid1_root=/\n' in text,
            'Debian initial PID 1/root is unproved')
    if int(count[0]) == 1:
        require(text.count('DEBIAN_INSTALL_INTENT_DURABLE\n') == 1 and text.count('DEBIAN_INSTALL_COMPLETE\n') == 1,
                'first Debian boot lacks the completed installation record')
    elif int(count[0]) == 2:
        require('DEBIAN_INSTALL_INTENT_DURABLE\n' not in text and 'DEBIAN_INSTALL_COMPLETE\n' not in text,
                'second Debian boot repeated installation')
    source = re.findall(r'^reboot_source_boot=([0-9a-f-]{36})$', text, re.M)
    require((not source and int(count[0]) == 1) or
            (len(source) == 1 and target.UUID.fullmatch(source[0]) and int(count[0]) == 2),
            'device reboot intent is missing, duplicated, or out of order')
    return dict(boot_id_sha256=digest(boot[0].encode()), boot_count=int(count[0]),
                reboot_source_boot_sha256=digest(source[0].encode()) if source else None,
                run_id=plan['candidate']['run_id'], capture=pin(handle.receipt_path))


def control_projection(handle, command, address):
    require(command in ('reboot', 'shutdown') and not handle.timed_out and not handle.output_exceeded and
            handle.producer_error_type is None, 'unexplained Debian control producer failure')
    stdout, stderr = raw.read_stdout(handle, maximum=65536), raw.read_stderr(handle, maximum=16384)
    require(stdout == ('DEBIAN_' + command.upper() + '_REQUEST_ACCEPTED\n').encode(),
            'Debian did not acknowledge the orderly shutdown request')
    expected_close = ('Connection to ' + address + ' closed by remote host.\r\n').encode()
    require((handle.returncode == 0 and not stderr) or (handle.returncode == 255 and stderr == expected_close),
            'unexplained Debian control command outcome')
    return dict(dispatch_capture=pin(handle.receipt_path), request_accepted=True, transition_proved=False)


class Owner:
    def __init__(self, directory, *, recovery=False):
        self.directory = private_path(ROOT, directory)
        self.plan_receipt = pin(self.directory / 'plan.json')
        self.plan = read(self.directory / 'plan.json')
        self.recovery = recovery
        require(self.plan['schema'] == SCHEMA and self.plan['seconds'] == 7200 and
                self.plan['directory'] == str(self.directory), 'Debian task binding differs')
        self.journal = Journal(self.directory / 'journal')
        self.grant = read(self.directory / 'grant.json') if (self.directory / 'grant.json').exists() else None

    def guard(self, *, owned=True):
        capability(recovery=self.plan['review'] if self.recovery else None)
        if self.grant is not None:
            validate_grant(self.grant, self.plan_receipt, current=not self.recovery)
        if owned:
            require(self.grant is not None, 'current attended task grant is absent')
            registry.require_f1_owner(ROOT, self.directory, self.plan_receipt['sha256'])
            opened = [row for row in self.journal.rows() if row['event'] == 'owner-opened']
            require(len(opened) <= 1, 'duplicate owner opening')
            if opened:
                require(opened[0]['data'] == dict(plan=self.plan_receipt, grant=pin(self.directory / 'grant.json')),
                        'opened owner grant changed')
            else:
                require(self.recovery and not journal_state(self.journal)[0],
                        'device effects lack the original owner opening')
        target.lane.revalidate_binding(self.plan['lane'], source_topology=target.lane.SOURCE_TOPOLOGY)
        journal_state(self.journal)

    def folder(self, label):
        path = self.directory / label
        path.mkdir(mode=0o700)
        return path

    def result(self, step, value, *, observation=False):
        receipt = publish(self.directory / (step + '.json'), value)
        self.journal.append('observation' if observation else 'effect-result', step=step, receipt=receipt)
        return receipt

    def intent(self, step, detail):
        self.guard()
        require(step not in journal_state(self.journal)[0], 'effect is already consumed')
        self.journal.append('effect-intent', step=step, detail=detail)

    def android_health(self, label, *, prepared=False):
        folder = self.folder(label)
        guard = lambda: self.guard(owned=not prepared)
        before = target.Android(self.plan['adb'], self.plan['target'], self.plan['A'], folder / 'before', guard=guard)
        if not prepared: before.wait_ready(deadline_ns=clock() + 180_000_000_000)
        first = before.health()
        reader = target.Android(self.plan['adb'], self.plan['target'], self.plan['A'], folder / 'read', guard=guard)
        meta = census.command(reader)
        stat_handle = reader.command(['-s', self.plan['target']['serial'], 'shell',
            'su -c ' + shlex.quote(android_storage.STAT_SCRIPT)], 'stat', timeout=15)
        after = target.Android(self.plan['adb'], self.plan['target'], self.plan['A'], folder / 'after', guard=guard).health()
        require(first['properties'] == after['properties'], 'Android boot changed during storage reads')
        raw.require_success(meta)
        require(not raw.read_stderr(meta, maximum=16384) and not raw.read_stderr(stat_handle, maximum=16384),
                'Android storage observation has diagnostics')
        sealed = gpt.vectors(self.plan['basis']['gpt'])
        metadata = android_storage.metadata(raw.read_stdout(meta, maximum=65536), sealed, 'proposed')
        capacity = android_storage.storage_stat(raw.decode_success_stdout(stat_handle, maximum=16384),
            dict(layout='proposed', geometry=self.plan['basis']['geometry']), sealed)
        require(capacity['total_bytes'] == 34357624832, 'Android32 capacity changed')
        value = android_projection(folder, self.plan)
        publish(folder / 'result.json', value)
        return value

    def research_proof(self):
        effects, completed, observed = journal_state(self.journal)
        if set(observed) != set(OBSERVATIONS): return False
        if not all(step in effects and step in completed for step in RESEARCH): return False
        proofs = {}
        for step in ('first-health', 'second-health'):
            path = verify(observed[step]); require(path == self.directory / (step + '.json'), 'health result path differs')
            value = read(path)
            projection = project_debian(raw.load_handle(verify(value['capture'])), self.plan)
            require(projection == {k: v for k, v in value.items() if k != 'endpoint'}, 'stored Debian proof differs')
            fields = value['endpoint']['fields']
            require(fields['serial'] == self.plan['link']['serial'] and fields['idVendor'] == '1d6b' and
                    fields['idProduct'] == '0104' and fields['product'] == 'S22 Debian research',
                    'retained Debian endpoint differs')
            proofs[step] = projection
        require(proofs['first-health']['boot_count'] == 1 and proofs['second-health']['boot_count'] == 2 and
                proofs['first-health']['boot_id_sha256'] != proofs['second-health']['boot_id_sha256'] and
                proofs['second-health']['reboot_source_boot_sha256'] == proofs['first-health']['boot_id_sha256'],
                'retained Debian reboot continuity differs')
        for step in ('workload-result', 'persistence'):
            value = read(verify(observed[step])); handle = raw.load_handle(verify(value['capture']))
            require(raw.decode_success_stdout(handle, maximum=65536, strip=False) == 'DEBIAN_WORKLOAD_PASS\n',
                    'retained workload/persistence proof differs')
        require('candidate-install' in completed and 'workload' in completed, 'candidate/workload result is absent')
        candidate = read(verify(completed['candidate-install']))
        target.transfer_completed(raw.load_handle(verify(candidate['raw'])))
        workload = read(verify(completed['workload']))
        require(raw.decode_success_stdout(raw.load_handle(verify(workload['capture'])), maximum=65536, strip=False)
                .endswith('DEBIAN_WORKLOAD_DISPATCHED\n'), 'retained workload dispatch differs')
        for step, command in (('debian-reboot', 'reboot'), ('debian-shutdown', 'shutdown')):
            require(step in completed, 'control request was not acknowledged')
            value = read(verify(completed[step]))
            require(value == control_projection(raw.load_handle(verify(value['dispatch_capture'])), command,
                self.plan['link']['ssh_address']), 'control dispatch receipt differs')
        claim = read(self.directory / 'candidate-claim.json')
        identity = candidate_identity(self.plan, self.plan_receipt['sha256'])
        require(registry.active_claim(ROOT, identity['candidate_key']) == claim['record'] and
                read(install_claim_path(self.plan))['plan'] == self.plan_receipt,
                'candidate/installation consumed claims differ')
        return True

    def transfer_proved(self, step):
        effects, _, _ = journal_state(self.journal)
        if step not in effects: return False
        detail = effects[step]['data']['detail']
        folder = Path(detail['capture_directory'])
        require(folder.parent == self.directory / (step + '-transfer') and
                re.fullmatch('attempt-[0-9a-f]{32}', folder.name), 'transfer capture has no bound attempt directory')
        path = folder / 'odin.capture.json'
        if not path.exists(): return False
        wanted = self.plan['A']['ap'] if step == 'android-restore' else self.plan['candidate']['ap']
        require(detail['ap'] == wanted and detail['installation_consumed'] is (step == 'candidate-install'),
                'transfer intent artifact or role differs')
        try:
            target.transfer_completed(raw.load_handle(path))
            return True
        except (ValueError, OSError, raw.RawCaptureError):
            return False

    def usb_link(self):
        wanted = self.plan['link']
        matches = []
        for interface in Path('/sys/class/net').iterdir():
            try:
                if (interface / 'address').read_text().strip() != wanted['host_mac']: continue
                device = (interface / 'device').resolve(strict=True)
                for topology in (target.lane.SOURCE_TOPOLOGY, target.lane.CANDIDATE_TOPOLOGY):
                    usb = Path('/sys/bus/usb/devices') / topology.removeprefix('usb:')
                    try:
                        parent = usb.resolve(strict=True)
                    except FileNotFoundError:
                        # Android and Debian can use different bus paths. An
                        # absent first path must not hide the second one.
                        continue
                    if not device.is_relative_to(parent): continue
                    fields = {name: target.sysfs_field(usb, name) for name in
                        ('idVendor', 'idProduct', 'serial', 'product', 'busnum', 'devnum')}
                    require(fields['idVendor'] == '1d6b' and fields['idProduct'] == '0104' and
                        fields['serial'] == wanted['serial'] and fields['product'] == 'S22 Debian research',
                        'NCM descriptor identity differs')
                    matches.append(dict(interface=interface.name, topology=topology, fields=fields))
            except FileNotFoundError:
                continue
        require(len(matches) <= 1, 'NCM endpoint is ambiguous')
        return matches[0] if matches else None

    def host_command(self, args, folder, name):
        tool = self.plan['nmcli']
        verify(tool, maximum=32 * 1024 * 1024)
        handle = raw.acquire_command([tool['path'], *args], folder, name,
            timeout=30, stdout_maximum=16384, stderr_maximum=16384, env=dict(os.environ, LC_ALL='C', LANG='C'))
        raw.require_success(handle)
        return pin(handle.receipt_path)

    def network(self, label, *, create):
        folder = self.folder(label)
        deadline = min(self.grant['deadline_ns'], clock() + 180_000_000_000)
        found = None
        while clock() < deadline:
            self.guard()
            found = self.usb_link()
            if found: break
            time.sleep(1)
        require(found is not None, 'Debian NCM arrival unproved')
        publish(folder / 'endpoint.json', found)
        connection = self.plan['network_uuid']
        if create:
            publish(folder / 'create-intent.json', dict(uuid=connection, endpoint=found))
            self.host_command(['connection', 'add', 'save', 'no', 'type', 'ethernet',
                'con-name', 's22-debian-' + self.plan['candidate']['run_id'], 'ifname', found['interface'],
                'connection.uuid', connection, 'connection.autoconnect', 'no',
                '802-3-ethernet.mac-address', self.plan['link']['host_mac'],
                'ipv4.method', 'manual', 'ipv4.addresses', self.plan['link']['host_address'],
                'ipv4.never-default', 'yes', 'ipv6.method', 'disabled'], folder, 'create')
        self.guard()
        require(self.usb_link() == found, 'NCM changed before host link activation')
        publish(folder / 'up-intent.json', dict(uuid=connection, endpoint=found))
        self.host_command(['connection', 'up', 'uuid', connection, 'ifname', found['interface']], folder, 'up')
        require(self.usb_link() == found, 'NCM changed during host link activation')
        return found

    def ssh(self, command, folder, label, *, endpoint, before=None, user='root'):
        require(command in ('health', 'workload', 'workload-result', 'reboot', 'shutdown') and user == 'root',
                'SSH command is outside the fixed observer')
        self.guard()
        require(self.usb_link() == endpoint, 'SSH target endpoint changed')
        for key in ('ssh', 'client_key', 'known_hosts'): verify(self.plan[key], maximum=32 * 1024 * 1024)
        args = [self.plan['ssh']['path'], '-F', '/dev/null', '-i', self.plan['client_key']['path'],
            '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UserKnownHostsFile=' + self.plan['known_hosts']['path'], '-o', 'LogLevel=ERROR',
            '-o', 'ConnectTimeout=3', '-o', 'ConnectionAttempts=1', '-o', 'ServerAliveInterval=5',
            '-o', 'ServerAliveCountMax=1', '-b', self.plan['link']['host_address'].split('/')[0],
            'root@' + self.plan['link']['ssh_address'], command]
        if before: before()
        return raw.acquire_command(args, folder, label, timeout=60 if command == 'workload' else 20,
                                   stdout_maximum=65536, stderr_maximum=16384)

    def observe_debian(self, step, endpoint, *, previous=None):
        folder = self.folder(step + '-reads')
        deadline = min(self.grant['deadline_ns'], clock() + 180_000_000_000)
        ordinal = 0
        while clock() < deadline:
            ordinal += 1
            handle = self.ssh('health', folder, f'health-{ordinal:03d}', endpoint=endpoint)
            body = raw.read_stdout(handle, maximum=65536)
            if body.startswith(b'S22PLUS_FYG8_DEBIAN_V1 '):
                require(body.startswith(('S22PLUS_FYG8_DEBIAN_V1 ' + self.plan['candidate']['run_id'] + '\n').encode()),
                        'contradictory Debian run identity')
            if handle.returncode != 0 or handle.timed_out or handle.output_exceeded or handle.producer_error_type is not None:
                time.sleep(1); continue
            # A successful but contradictory identity is a research stop.
            value = project_debian(handle, self.plan)
            require(self.usb_link() == endpoint, 'Debian endpoint changed during health')
            require(value['boot_count'] == (2 if previous else 1), 'unexpected Debian boot count')
            if previous:
                require(value['boot_id_sha256'] != previous['boot_id_sha256'] and
                        value['reboot_source_boot_sha256'] == previous['boot_id_sha256'], 'ordinary Debian reboot is unproved')
            self.result(step, dict(value, endpoint=endpoint), observation=True)
            return value
        raise TimeoutError('Debian health did not complete within the original step')

    def workload_result(self, step, endpoint):
        folder = self.folder(step + '-reads')
        deadline = min(self.grant['deadline_ns'], clock() + 90_000_000_000)
        ordinal = 0
        while clock() < deadline:
            ordinal += 1
            handle = self.ssh('workload-result', folder, f'result-{ordinal:03d}', endpoint=endpoint)
            if handle.returncode == 0 and not handle.timed_out and not handle.output_exceeded and handle.producer_error_type is None:
                require(raw.read_stdout(handle, maximum=65536) == b'DEBIAN_WORKLOAD_PASS\n' and
                        not raw.read_stderr(handle, maximum=16384), 'successful workload observation is noncanonical')
                return self.result(step, dict(capture=pin(handle.receipt_path)), observation=True)
            time.sleep(2)
        raise TimeoutError('actual cron/package/log/persistence proof is incomplete')

    def transfer(self, step):
        android = step == 'android-restore'
        artifact = self.plan['A']['ap'] if android else self.plan['candidate']['ap']
        base = self.directory / (step + '-transfer'); base.mkdir(mode=0o700, exist_ok=True)
        require(step not in journal_state(self.journal)[0], 'transfer intent already consumed')
        folder = base / ('attempt-' + uuid.uuid4().hex); folder.mkdir(mode=0o700)
        endpoints = folder / 'endpoints'; endpoints.mkdir(mode=0o700)
        deadline = clock() + 90_000_000_000
        if not android: deadline = min(deadline, self.grant['deadline_ns'])
        with transport.pin_regular_file(Path(self.plan['odin']['path']), label='Odin',
                expected_size=self.plan['odin']['size'], expected_sha256=self.plan['odin']['sha256']) as odin, \
             transport.pin_boot_only_ap(Path(self.plan['A']['ap']['path']), label='original Android A',
                expected_size=self.plan['A']['ap']['size'], expected_sha256=self.plan['A']['ap']['sha256'],
                require_deterministic_metadata=False) as recovery, transition.transaction_session(endpoints) as lease:
            def observer():
                self.guard(); transport.revalidate_pinned_path(odin)
                return transition.measured_usbfs_observer(endpoints)
            found = transition.wait_for_single_live_endpoint(odin.path, endpoints,
                timeout_sec=max(0, (deadline - clock()) / 1e9), lease=lease,
                endpoint_observer_factory=observer, monotonic=lambda: clock() / 1e9)
            require(found.ticket is not None and not found.timed_out, 'exact Download endpoint did not arrive')
            ticket = found.ticket
            identity = target.download_identity(ticket.device)
            def before_launch():
                self.guard()
                checked = transition.revalidate_endpoint_ticket(odin.path, endpoints, ticket,
                    sequence=found.next_sequence, lease=lease, timeout_sec=10,
                    endpoint_observer_factory=observer, monotonic=lambda: clock() / 1e9)
                require(target.download_identity(ticket.device) == identity and clock() < deadline,
                        'Download identity or arrival deadline changed')
                transport.revalidate_pinned_path(recovery)
                if not android:
                    claim = registry.claim(ROOT, candidate_identity(self.plan, self.plan_receipt['sha256']))
                    publish(self.directory / 'candidate-claim.json', claim)
                    path = install_claim_path(self.plan)
                    durable_install_claim_directory(self.plan)
                    publish(path, dict(schema=SCHEMA + '-installation-claim', plan=self.plan_receipt,
                        candidate=self.plan['candidate']['ap'], boottime_ns=clock()))
                self.intent(step, dict(ap=artifact, ticket=asdict(ticket), endpoint=identity,
                    endpoint_revalidation=checked, installation_consumed=not android,
                    capture_directory=str(folder), physical_statement=self.physical_statement if android else None))
            receipt, handle = transport.execute_odin_boot_only(odin.path, Path(artifact['path']), ticket.device,
                odin_size=self.plan['odin']['size'], odin_sha256=self.plan['odin']['sha256'],
                ap_size=artifact['size'], ap_sha256=artifact['sha256'], label=step,
                require_deterministic_metadata=not android, capture_dir=folder, capture_name='odin',
                stdout_name='stdout.bin', stderr_name='stderr.bin', before_launch=before_launch)
        publish(folder / 'transport.json', receipt)
        target.transfer_completed(handle)
        return self.result(step, dict(transport=pin(folder / 'transport.json'), raw=pin(handle.receipt_path)))

    def execute(self):
        require(not self.journal.rows(), 'a started Debian operation resumes only through recovery')
        with registry.target_session_lease(ROOT):
            registry.require_no_f1_owner(ROOT)
            require(self.grant is not None, 'explicit attended grant is required')
            self.guard(owned=False)
            registry.begin_f1_owner(ROOT, self.directory, self.plan_receipt['sha256'])
            self.journal.append('owner-opened', plan=self.plan_receipt, grant=pin(self.directory / 'grant.json'))
            try:
                self.guard()
                require(not install_claim_path(self.plan).exists(), 'native installation already consumed')
                registry.preflight_candidate(ROOT, candidate_identity(self.plan, self.plan_receipt['sha256']))
                ap_member(self.plan['candidate']['ap'])
                self.android_health('fresh-start')
                folder = self.folder('android-download-io')
                before = target.usb_snapshot(target.lane.SOURCE_TOPOLOGY, folder)
                client = target.Android(self.plan['adb'], self.plan['target'], self.plan['A'], folder, guard=self.guard)
                departure_deadline = clock() + 30_000_000_000
                result = client.download(before_dispatch=lambda: self.intent('android-download', dict(
                    source=before, departure_deadline_ns=departure_deadline)))
                result['departure'] = target.wait_departure(before, folder, deadline_ns=departure_deadline, guard=self.guard)
                self.result('android-download', result)
                self.transfer('candidate-install')
                endpoint = self.network('network-first', create=True)
                first = self.observe_debian('first-health', endpoint)
                folder = self.folder('workload-io')
                handle = self.ssh('workload', folder, 'command', endpoint=endpoint,
                    before=lambda: self.intent('workload', dict(endpoint=endpoint)))
                require(raw.decode_success_stdout(handle, maximum=65536, strip=False).endswith('DEBIAN_WORKLOAD_DISPATCHED\n'),
                        'workload dispatch did not complete')
                self.result('workload', dict(capture=pin(handle.receipt_path)))
                self.workload_result('workload-result', endpoint)
                folder = self.folder('debian-reboot-io')
                handle = self.ssh('reboot', folder, 'command', endpoint=endpoint,
                    before=lambda: self.intent('debian-reboot', dict(endpoint=endpoint, first=first)))
                self.result('debian-reboot', control_projection(handle, 'reboot', self.plan['link']['ssh_address']))
                deadline = min(self.grant['deadline_ns'], clock() + 60_000_000_000)
                while clock() < deadline and self.usb_link() == endpoint: time.sleep(.5)
                require(self.usb_link() != endpoint, 'Debian reboot endpoint never departed')
                second_endpoint = self.network('network-second', create=False)
                self.observe_debian('second-health', second_endpoint, previous=first)
                self.workload_result('persistence', second_endpoint)
                folder = self.folder('debian-shutdown-io')
                handle = self.ssh('shutdown', folder, 'command', endpoint=second_endpoint,
                    before=lambda: self.intent('debian-shutdown', dict(endpoint=second_endpoint)))
                self.result('debian-shutdown', control_projection(handle, 'shutdown', self.plan['link']['ssh_address']))
                self.journal.append('physical-recovery-armed', reason='NORMAL_RETURN', plan=self.plan_receipt)
                print('WAIT_ATTENDED_PHYSICAL_DOWNLOAD', flush=True)
            except BaseException as error:
                self.journal.append('research-stopped', error_type=type(error).__name__, message=str(error)[:512])
                self.journal.append('physical-recovery-armed', reason='RESEARCH_STOP', plan=self.plan_receipt)
                raise

    def close(self, *, operator_statement):
        require(self.recovery, 'recovery owner mode required')
        with registry.target_session_lease(ROOT):
            effects, completed, observed = journal_state(self.journal)
            terminal_path = self.directory / 'terminal.json'
            if terminal_path.exists():
                capability(recovery=self.plan['review'])
                value = read(terminal_path)
                require(value['schema'] == SCHEMA + '-terminal' and value['plan'] == self.plan_receipt and
                        value['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and value['effects'] == list(effects) and
                        value['observations'] == observed and value['native_filesystem_integrity_after_shutdown'] == 'UNPROVED' and
                        value['installation_not_undone'] is True and value['verdict'] in {
                            'PASS_DEBIAN_FIRST_BOOT_RETURNED_ANDROID', 'NO_PROOF_ANDROID_CLOSED_HEALTHY',
                            'NO_EFFECT_ANDROID_CLOSED_HEALTHY'},
                        'retained terminal binding differs')
                receipt = pin(terminal_path)
                terminals = [row for row in self.journal.rows() if row['event'] == 'terminal']
                require(len(terminals) <= 1 and (not terminals or terminals[0]['data'] == dict(receipt=receipt)),
                        'terminal journal receipt differs from the published bytes')
                require(value['original_A_transfer_proved'] is self.transfer_proved('android-restore'),
                        'terminal original-A transfer claim no longer rederives')
                final_path = verify(value['final_health'])
                require(final_path.name == 'result.json' and final_path.parent.parent == self.directory and
                        final_path.parent.name.startswith('android-final-'), 'terminal health path differs')
                require(read(final_path) == android_projection(final_path.parent, self.plan), 'terminal health does not rederive')
                if value['verdict'] == 'PASS_DEBIAN_FIRST_BOOT_RETURNED_ANDROID':
                    require(value['original_A_transfer_proved'] and self.research_proof(), 'terminal research no longer rederives')
                require((value['verdict'] == 'NO_EFFECT_ANDROID_CLOSED_HEALTHY') is (not effects),
                        'terminal effect classification differs')
                if not any(row['event'] == 'terminal' for row in self.journal.rows()):
                    self.journal.append('terminal', receipt=receipt)
                registry.retire_f1_owner(ROOT, self.directory, self.plan_receipt['sha256'])
                return receipt
            self.guard()
            # An abrupt host loss may bypass every best-effort exception record.
            # The original durable effects and grant retain recovery ownership.
            if effects and not any(r['event'] == 'physical-recovery-armed' for r in self.journal.rows()):
                self.journal.append('physical-recovery-armed', reason='DURABLE_EFFECT_RECOVERY', plan=self.plan_receipt)
            if effects and 'android-restore' not in effects:
                require(operator_statement.strip(), 'current physical Download attendance statement required')
                self.physical_statement = publish(self.directory / ('physical-download-statement-' + uuid.uuid4().hex + '.json'), dict(statement=operator_statement,
                    plan=self.plan_receipt, boottime_ns=clock(), host_boot=host_boot()))
                self.transfer('android-restore')
            # A reporting cut or transfer uncertainty NEVER re-enters transfer().
            folder = 'android-final-' + uuid.uuid4().hex
            final = self.android_health(folder)
            transfer_proved = self.transfer_proved('android-restore')
            before = read(self.directory / 'prepared/result.json')
            require(not effects or final['boot_id_sha256'] != before['boot_id_sha256'], 'Android final boot did not change')
            self.cleanup_network()
            effects, completed, observed = journal_state(self.journal)
            research_error = None
            try: research_ok = self.research_proof()
            except (ValueError, OSError, raw.RawCaptureError) as error:
                # Lost/invalid research evidence cannot promote the candidate;
                # independently rederived original-A health can still close it.
                research_ok = False
                research_error = dict(type=type(error).__name__, message=str(error)[:512])
            terminal = dict(schema=SCHEMA + '-terminal', plan=self.plan_receipt,
                terminal_state='ANDROID_CLOSED_HEALTHY',
                verdict='PASS_DEBIAN_FIRST_BOOT_RETURNED_ANDROID' if research_ok and transfer_proved else
                    'NO_PROOF_ANDROID_CLOSED_HEALTHY' if effects else 'NO_EFFECT_ANDROID_CLOSED_HEALTHY',
                observations=observed, effects=list(effects), original_A_transfer_proved=transfer_proved,
                research_evidence_error=research_error,
                final_health=pin(self.directory / folder / 'result.json'),
                native_filesystem_integrity_after_shutdown='UNPROVED', installation_not_undone=True,
                closed_boottime_ns=clock())
            receipt = publish(self.directory / 'terminal.json', terminal)
            self.journal.append('terminal', receipt=receipt)
            registry.retire_f1_owner(ROOT, self.directory, self.plan_receipt['sha256'])
            print(terminal['verdict'], flush=True)
            return receipt

    def cleanup_network(self):
        if not (self.directory / 'network-first/create-intent.json').exists(): return
        folder = self.folder('network-cleanup-' + uuid.uuid4().hex)
        verify(self.plan['nmcli'], maximum=32 * 1024 * 1024)
        # Delete only this task's unguessable UUID after matching its exact name.
        handle = raw.acquire_command([self.plan['nmcli']['path'], '-g', 'connection.id', 'connection', 'show',
            'uuid', self.plan['network_uuid']], folder, 'inspect', timeout=15, stdout_maximum=4096, stderr_maximum=4096,
            env=dict(os.environ, LC_ALL='C', LANG='C'))
        if handle.returncode == 10:
            require(not handle.timed_out and not handle.output_exceeded and handle.producer_error_type is None and
                raw.read_stdout(handle, maximum=4096) == b'' and raw.read_stderr(handle, maximum=4096) ==
                ('Error: ' + self.plan['network_uuid'] + ' - no such connection profile.\n').encode(),
                'host connection absence is unproved')
            return
        name = raw.decode_success_stdout(handle, maximum=4096)
        require(name == 's22-debian-' + self.plan['candidate']['run_id'], 'network cleanup ownership differs')
        publish(folder / 'intent.json', dict(uuid=self.plan['network_uuid']))
        self.host_command(['connection', 'delete', 'uuid', self.plan['network_uuid']], folder, 'delete')


def prepare(directory, artifact_receipt):
    import s22plus_debian_artifact_v1 as qualification
    capability()
    directory = private_path(ROOT, directory, exists=False)
    require(not directory.exists(), 'fresh Debian task directory required')
    artifact = qualification.revalidate(artifact_receipt)
    built = read(verify(artifact['artifact']))
    for receipt in built['source_inputs']: verify(receipt, maximum=4 * 1024 * 1024)
    prior, basis = retained_basis()
    require(built['filesystem_binding'] == basis['filesystem_binding'], 'candidate changes retained filesystem identity')
    profile = read(PROFILE)
    require(prior['A']['ap'] == dict(profile['rollback']['ap'], path=str(ROOT / profile['rollback']['ap']['path'])),
            'original A differs from exact target profile')
    root = Path(artifact['artifact']['path']).parent
    candidate = dict(run_id=built['run_id'], ap=built['ap'], member=ap_member(built['ap']), qualification=artifact_receipt)
    require(candidate['member'] == artifact['actual']['member'] and
            artifact['actual']['client_key'] == pin(root / 'client-key') and
            artifact['actual']['known_hosts'] == pin(root / 'known_hosts') and
            artifact['actual']['link'] == pin(root / 'link.json'), 'prepared candidate joins differ')
    require(ap_member(prior['A']['ap'], android=True) == prior['A']['member'], 'original A archive member differs')
    directory.mkdir(mode=0o700)
    review_receipt = publish(directory / 'review.json', capability())
    plan = dict(schema=SCHEMA, directory=str(directory), target=prior['target'], A=prior['A'], basis=basis,
        candidate=candidate, adb=pin(Path('/usr/bin/adb').resolve(), maximum=32 * 1024 * 1024), odin=profile['transport']['odin'],
        ssh=pin(Path('/usr/bin/ssh').resolve(), maximum=32 * 1024 * 1024),
        nmcli=pin(Path('/usr/bin/nmcli').resolve(), maximum=32 * 1024 * 1024),
        client_key=pin(root / 'client-key'), known_hosts=pin(root / 'known_hosts'), link=read(root / 'link.json'),
        network_uuid=str(uuid.uuid4()), seconds=7200, review=review_receipt,
        lane=target.lane.capture_binding(target.lane.SOURCE_TOPOLOGY))
    receipt = publish(directory / 'plan.json', plan)
    owner = Owner(directory)
    with registry.target_session_lease(ROOT):
        registry.require_no_f1_owner(ROOT)
        durable_install_claim_directory(plan)
        registry.preflight_candidate(ROOT, candidate_identity(plan, receipt['sha256']))
        require(not install_claim_path(plan).exists(), 'Debian installation already attempted')
        owner.android_health('prepared', prepared=True)
    publish(directory / 'proposal.json', dict(plan=receipt, seconds=7200, attended=True,
        actions=list(EFFECTS), candidate_ap=plan['candidate']['ap'], original_A=plan['A']['ap'],
        physical_recovery_required=True, device_effects=0, prepared_health=pin(directory / 'prepared/result.json')))
    print(receipt['sha256'], flush=True)
    return receipt


def approve(directory, *, statement, plan_sha256):
    owner = Owner(directory)
    owner.guard(owned=False)
    require(statement.strip() and plan_sha256 == owner.plan_receipt['sha256'] and not owner.journal.rows(),
            'operator statement is not bound to the concrete unused proposal')
    require(read(directory / 'proposal.json')['plan'] == owner.plan_receipt, 'proposal binding changed')
    opened = clock()
    return publish(directory / 'grant.json', dict(schema=SCHEMA + '-grant', plan=owner.plan_receipt,
        operator_statement=statement, attended=True, host_boot=host_boot(), opened_ns=opened,
        deadline_ns=opened + 7200_000_000_000))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'approve', 'execute', 'recover'])
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--qualification', type=Path)
    parser.add_argument('--operator-statement')
    parser.add_argument('--plan-sha256')
    args = parser.parse_args()
    if args.phase == 'prepare':
        prepare(args.directory, pin(args.qualification.resolve(strict=True)))
    elif args.phase == 'approve':
        approve(args.directory.resolve(strict=True), statement=args.operator_statement or '', plan_sha256=args.plan_sha256)
    elif args.phase == 'execute':
        Owner(args.directory).execute()
    else:
        Owner(args.directory, recovery=True).close(operator_statement=args.operator_statement or '')
