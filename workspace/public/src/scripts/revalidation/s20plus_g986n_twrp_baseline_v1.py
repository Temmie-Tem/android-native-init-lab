#!/usr/bin/env python3
"""Qualify retained T2 as the S20+ recovery baseline; no partition operations."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

import s20plus_g986n_routine_actions as routine
import s20plus_g986n_twrp_boot_identity_d0 as identity

ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve()
POLICY = ROOT / 'docs/operations/S20PLUS_TWRP_BASELINE_V1.md'
# Prospective review under Revision 29. The consumed baseline retains its
# original qualification.json, focused-tests.log and source provenance.
REVIEW = ROOT / 'workspace/private/outputs/s20plus_g986n/twrp_binding_refresh_rev29/baseline-qualification.json'
TEST_LOG = REVIEW.with_name('baseline-tests.log')
TEST_SOURCE = ROOT / 'tests/test_s20plus_g986n_twrp_baseline_v1.py'
PREFIX = 'twrp-baseline-'
SCHEMA = 's20plus_g986n_twrp_baseline_v1'
READY_SECONDS = 120
MAX_COMMANDS = 80
SAFE_FIELDS = frozenset(identity.t2.h0.EXPECTED_RECOVERY_FIXED_OUTPUT) | {
    'model', 'device', 'product_name', 'incremental', 'boot_completed', 'bootanim', 'selinux'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_receipt(path):
    return identity.file_receipt(Path(path), label='baseline input', maximum=1024*1024)


def authority_identity():
    # Registry lifecycle prose is not an execution identity; keep target routing.
    lines = (ROOT/'AGENTS.md').read_text().splitlines()
    for index, line in enumerate(lines):
        if line.startswith('| Samsung Galaxy'):
            cells = line.strip('|').split('|')
            if len(cells) != 4:
                raise RuntimeError('target registry shape differs')
            lines[index] = '|'+'|'.join(cells[:3])+'| <LIVE_STATUS> |'
    target = (ROOT/'docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md').read_text()
    sections = {}
    for heading in ('## Retained-T2 baseline for prospective native-init experiments',
                    '## TWRP boot-identity metadata D0'):
        if target.count(heading+'\n') != 1:
            raise RuntimeError('baseline authority section differs')
        start = target.index(heading+'\n')
        end = target.find('\n## ', start+3)
        sections[heading] = hashlib.sha256(target[start:end if end>=0 else None].encode()).hexdigest()
    return {'common_contract_sha256':hashlib.sha256('\n'.join(lines).encode()).hexdigest(),
            'selected_target_sections':sections}


def fingerprint():
    paths = [SCRIPT, POLICY, TEST_SOURCE, Path(routine.__file__), Path(identity.__file__),
             Path(routine.base.__file__), Path(routine.routine.__file__),
             ROOT/'docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md']
    return {'files': {str(p.relative_to(ROOT)): file_receipt(p) for p in paths},
            'retained_t2_sources': identity.t2.source_closure(enforce_self=True),
            'authority':authority_identity()}


def require_review():
    value = read_json(REVIEW)
    if (stat.S_IMODE(REVIEW.stat().st_mode) != 0o400
            or value.get('schema') != SCHEMA+'-qualification'
            or value.get('review') != {'verdict':'PASS_GO','high':0,'medium':0,'low':0}
            or value.get('fingerprint') != fingerprint()
            or value.get('tests') != file_receipt(TEST_LOG)
            or not TEST_LOG.read_text().rstrip().endswith('OK')):
        raise RuntimeError('baseline capability review differs')
    return value


def read_json(path):
    file_receipt(path)
    payload = Path(path).read_bytes()
    value = json.loads(payload, object_pairs_hook=identity.t2.b0._unique_pairs, parse_constant=identity.t2.b0._reject_constant)
    expected = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    if type(value) is not dict or payload != expected:
        raise RuntimeError('baseline record is not canonical typed JSON')
    return value


def publish(path, value):
    identity.durable_json(Path(path), value)


def require_guard(run):
    guard = routine.read_guard(ROOT)
    if guard['action'] != 'enter-recovery' or Path(guard['run_dir']) != run:
        raise RuntimeError('baseline does not own this guard')
    if not re.fullmatch(PREFIX+r'[0-9]{19}', run.name):
        raise RuntimeError('guard is not a baseline transaction')


class CommandGate:
    def __init__(self, run, predecessor, command=None):
        self.run, self.predecessor, self.command = run, predecessor, command or routine.bounded_command
        self.count = 0
        self.reboot_armed = False
        self.ordinal = max((int(p.stem.split('-')[-1]) for p in run.glob('command-*.json')), default=0)

    def __call__(self, argv, timeout, maximum):
        require_guard(self.run)
        if self.count >= MAX_COMMANDS or argv[0] != str(identity.ADB):
            raise RuntimeError('baseline command budget/tool differs')
        if not (0 < timeout <= 30 and 0 < maximum <= routine.MAX_OUTPUT_BYTES):
            raise RuntimeError('baseline command bounds differ')
        label = 'inventory'
        if argv[1:] != ['devices','-l']:
            if (len(argv) < 4 or argv[1] != '-s'
                    or identity.sha256_text(argv[2]) != self.predecessor['serial_sha256']):
                raise RuntimeError('baseline selected another target')
            tail = argv[3:]
            fixed = {
                ('get-devpath',): 'topology',
                ('exec-out','sh','-c',routine.base.REMOTE_SNAPSHOT): 'android-preflight',
                ('exec-out','sh','-c',identity.t2.h0.RECOVERY_SHELL_ARGUMENT): 't2-identity',
                ('exec-out','sh','-c',identity.BOOT_METADATA_SCRIPT): 'boot-metadata',
            }
            if tail == ['reboot','recovery']:
                if not self.reboot_armed or not (self.run/'entry-intent.json').exists():
                    raise RuntimeError('baseline reboot is not armed')
                self.reboot_armed = False
                label = 'enter-recovery'
            elif tuple(tail) not in fixed:
                raise RuntimeError('baseline command is not fixed')
            else:
                label = fixed[tuple(tail)]
        self.count += 1
        self.ordinal += 1
        try:
            result = self.command(argv, timeout, maximum)
        except Exception as error:
            publish(self.run/f'command-{self.ordinal:04d}.json', {
                'stage':label,'failure_class':type(error).__name__,'outcome':'command-failed'})
            raise
        rc, stdout, stderr = result
        fields = {}
        if label in {'android-preflight','t2-identity'}:
            for line in stdout.decode('utf-8','replace').splitlines():
                key, separator, value = line.partition('=')
                if separator and key in SAFE_FIELDS:
                    fields[key] = value if value in identity.t2.h0.EXPECTED_RECOVERY_FIXED_OUTPUT.values() or re.fullmatch(r'[A-Za-z0-9_.:+-]{0,80}',value) else '<unexpected>'
        publish(self.run/f'command-{self.ordinal:04d}.json', {
            'stage':label,'returncode':rc,'stdout_size':len(stdout),'stderr_size':len(stderr),
            'stdout_sha256':hashlib.sha256(stdout).hexdigest(),
            'stderr_sha256':hashlib.sha256(stderr).hexdigest(),'fixed_property_fields':fields})
        return result


def recovery_ready(rows, predecessor):
    selected = [r for r in rows if identity.sha256_text(r['serial']) == predecessor['serial_sha256']]
    models = [r for r in rows if identity.t2.b0.EXPECTED_ADB_MODEL in r['metadata']]
    if len(selected)>1 or any(r not in selected for r in models):
        raise RuntimeError('baseline target is ambiguous')
    if not selected:
        return False
    if selected[0]['state'] in {'device','offline'}:
        return False
    if selected[0]['state'] != 'recovery':
        raise RuntimeError('baseline target has an unauthorized state')
    return True


def observe(gate, predecessor):
    deadline = time.monotonic() + READY_SECONDS
    while True:
        result = gate([str(identity.ADB),'devices','-l'],10,identity.MAX_COMMAND_BYTES)
        rows = identity.inventory_from_result(result,'baseline readiness')
        if recovery_ready(rows, predecessor):
            return identity.collect(command=gate, predecessor=predecessor)
        if time.monotonic() >= deadline:
            raise TimeoutError('baseline recovery readiness expired')
        time.sleep(2)


def validate_result(value, opening):
    recovery = value.get('recovery_health', {}).get('recovery', {})
    if (value.get('schema') != SCHEMA or value.get('verdict') != 'PROVED_S20PLUS_G986N_TWRP_BASELINE_HEALTHY'
            or value.get('target') != identity.TARGET or value.get('opening_sha256') != digest(opening)
            or value.get('entry_replay_permitted') is not False
            or value.get('f1_authorized') is not False or value.get('boot_content_verified') is not False
            or value.get('android_health_verified') is not False
            or type(value.get('partition_transfers')) is not int or value['partition_transfers'] != 0
            or type(value.get('other_target_commands')) is not int or value['other_target_commands'] != 0
            or recovery.get('serial_sha256') != opening['predecessor']['serial_sha256']
            or recovery.get('topology_sha256') != opening['predecessor']['topology_sha256']
            or recovery.get('t2_identity_without_boot_id') != identity.t2.h0.EXPECTED_RECOVERY_FIXED_OUTPUT
            or not re.fullmatch(r'[0-9a-f]{64}',str(recovery.get('current_boot_id_sha256')))):
        raise RuntimeError('baseline terminal health differs')


def finish(run, opening, gate):
    observation = observe(gate, opening['predecessor'])
    source = read_json(run/'source.json') if (run/'source.json').exists() else None
    if source and observation['recovery']['current_boot_id_sha256'] == source['boot_id_sha256']:
        raise RuntimeError('recovery entry did not change the source boot')
    if fingerprint() != opening['fingerprint']:
        raise RuntimeError('baseline source changed during observation')
    result = {'schema':SCHEMA,'verdict':'PROVED_S20PLUS_G986N_TWRP_BASELINE_HEALTHY',
              'target':identity.TARGET,'opening_sha256':digest(opening),
              'entry_attempts':int((run/'entry-intent.json').exists()),
              'entry_replay_permitted':False,'recovery_health':observation,
              'boot_content_verified':False,'android_health_verified':False,
              'partition_transfers':0,'other_target_commands':0,'f1_authorized':False,
              'completed_at':identity.datetime.now(identity.timezone.utc).isoformat()}
    validate_result(result,opening)
    publish(run/'baseline.json',result)
    routine.release_guard(ROOT,expected_run_dir=run,expected_action='enter-recovery')
    return result


def run_new(enter):
    require_review()
    host = identity.validate_host_closure(enforce_self=True)
    run = routine.allocate_run_dir(ROOT,'enter-recovery',
        ROOT/routine.DEFAULT_RUN_ROOT/(PREFIX+str(time.time_ns())))
    opening = {'schema':SCHEMA+'-opening','mode':'enter' if enter else 'observe',
               'predecessor':host['t2_predecessor'],'host_closure_sha256':identity.digest(host),
               'fingerprint':fingerprint(),'qualification':file_receipt(REVIEW)}
    publish(run/'opening.json',opening)
    routine.acquire_guard(ROOT,run,'enter-recovery',None)
    gate = CommandGate(run,opening['predecessor'])
    try:
        if enter:
            recorder = routine.Recorder(gate)
            source = routine.preflight(recorder,str(identity.ADB))
            if (source['serial_sha256'] != opening['predecessor']['serial_sha256']
                    or source['usb_topology_sha256'] != opening['predecessor']['topology_sha256']):
                raise RuntimeError('normal source differs from retained T2 target')
            publish(run/'source.json',{k:source[k] for k in ('serial_sha256','usb_topology_sha256','boot_id_sha256')})
            require_review()
            publish(run/'entry-intent.json',{'schema':SCHEMA+'-entry-intent',
                'opening_sha256':digest(opening),'attempt':1,'no_replay':True})
            gate.reboot_armed = True
            dispatched = gate([str(identity.ADB),'-s',source['serial'],'reboot','recovery'],20,routine.MAX_OUTPUT_BYTES)
            routine.decode(dispatched, 'baseline recovery entry')
        result = finish(run,opening,gate)
        return {**result,'run_dir':str(run)}
    except Exception as error:
        publish(run/'failure.json',{'schema':SCHEMA+'-failure','failure_class':type(error).__name__,
            'reason':str(error)[:200],'entry_replay_permitted':False,
            'read_only_resume_permitted':isinstance(error,TimeoutError)})
        if not (run/'entry-intent.json').exists():
            routine.release_guard(ROOT,expected_run_dir=run,expected_action='enter-recovery')
        raise


def resume():
    require_review()
    guard = routine.read_guard(ROOT)
    run = Path(guard['run_dir'])
    require_guard(run)
    opening = read_json(run/'opening.json')
    if opening['fingerprint'] != fingerprint() or opening['qualification'] != file_receipt(REVIEW):
        raise RuntimeError('baseline resume source differs')
    if (run/'baseline.json').exists():
        value = read_json(run/'baseline.json')
        validate_result(value,opening)
        routine.release_guard(ROOT,expected_run_dir=run,expected_action='enter-recovery')
        return {**value,'run_dir':str(run)}
    failures = ([run/'failure.json'] if (run/'failure.json').exists() else []) + sorted(run.glob('resume-failure-*.json'))
    if failures and read_json(failures[-1]).get('read_only_resume_permitted') is not True:
        raise RuntimeError('baseline failure requires cause-specific handling')
    try:
        result = finish(run,opening,CommandGate(run,opening['predecessor']))
        return {**result,'run_dir':str(run)}
    except Exception as error:
        ordinal = len(list(run.glob('resume-failure-*.json'))) + 1
        publish(run/f'resume-failure-{ordinal:04d}.json', {
            'schema':SCHEMA+'-failure','failure_class':type(error).__name__,
            'reason':str(error)[:200],'entry_replay_permitted':False,
            'read_only_resume_permitted':isinstance(error,TimeoutError)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--enter',action='store_true')
    modes.add_argument('--observe',action='store_true')
    modes.add_argument('--resume',action='store_true')
    modes.add_argument('--validate-host',action='store_true')
    args = parser.parse_args()
    try:
        if args.validate_host:
            host=identity.validate_host_closure(enforce_self=True)
            result={'verdict':'PASS_TWRP_BASELINE_HOST_CLOSURE','fingerprint':digest(fingerprint()),
                    'retained_t2_host':identity.digest(host),'device_commands':0}
        else:
            result=resume() if args.resume else run_new(args.enter)
        print(json.dumps(result,sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({'verdict':'STOP_TWRP_BASELINE','failure_class':type(error).__name__,
                          'reason':str(error)[:200],'device_effect_replay_permitted':False},sort_keys=True))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
