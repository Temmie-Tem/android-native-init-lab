#!/usr/bin/env python3
"""Foreground-goal Android D0 reads and attended ordinary-reboot D1.

No caller shell/path payload, Download, flash, or unattended action entry.
The operator's goal grant is recorded by the trusted foreground task owner;
this CLI cannot establish human authority or attendance by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
import uuid

import consumed_candidate_registry_v1 as registry
import device_action_d0_v2 as d0

ROOT = Path(__file__).resolve().parents[5]
BASE = Path('workspace/private/runs/s22plus-goal-research-v1')
REVIEW = Path('workspace/public/src/device-action/bindings/s22plus_goal_research_v1_review.json')
PROFILE = Path('workspace/public/src/device-action/profiles/s22plus_fyg8.json')
SOURCES = {
    'runner': Path(__file__).resolve().relative_to(ROOT),
    'd0': Path(d0.__file__).resolve().relative_to(ROOT),
    'raw_capture': Path(d0.raw_capture.__file__).resolve().relative_to(ROOT),
    'registry': Path(registry.__file__).resolve().relative_to(ROOT),
    'f1_owner': Path('workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py'),
    'profile': PROFILE,
    'common': Path('docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md'),
    'target': Path('docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md'),
    'policy': Path('docs/operations/targets/S22PLUS_FYG8_GOAL_RESEARCH_V1.md'),
}
# All text is fixed. These procfs/property interfaces are ordinary status reads;
# no arbitrary proc/sys/dev path, process argument/environment or log-body read.
STATUS_HUD_READ = """printf 'STATUS_HUD_V1_BEGIN\\n'
for path in /proc/meminfo /sys/class/power_supply/battery/type /sys/class/power_supply/battery/capacity /sys/class/power_supply/battery/status /sys/class/power_supply/battery/temp; do
    printf 'FIELD %s\\n' "$path"
    if [ -r "$path" ]; then head -c 8192 "$path" || exit 1; else printf 'UNAVAILABLE\\n'; fi
    printf '\\nEND_FIELD\\n'
done
printf 'FIELD cpu_first\\n'; head -n 1 /proc/stat || exit 1; printf 'END_FIELD\\n'
sleep 1
printf 'FIELD cpu_second\\n'; head -n 1 /proc/stat || exit 1; printf 'END_FIELD\\n'
printf 'STATUS_HUD_V1_END\\n'"""
READS = {
    'identity': ('id && uname -r', True),
    'processes': ('ps -A -o PID,PPID,UID,STAT,NAME', True),
    'memory': ('cat /proc/meminfo && cat /proc/vmstat', True),
    'mounts': ('cat /proc/mounts', True),
    'usb-state': ('getprop sys.usb.state && getprop sys.usb.config', False),
    'status-hud': (STATUS_HUD_READ, True),
}
ACTIONS = frozenset(READS) | {'health', 'normal-reboot'}
RETURN_SECONDS = 360


class ResearchError(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise ResearchError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    require(not path.is_symlink() and path.is_file(), 'missing/indirect record')
    require(path.stat().st_size <= 65536, 'record bound')
    return json.loads(path.read_text())


def publish(path, value):
    d0.durable_create(path, value)


def source_identity(root):
    return {key: digest(root / path) for key, path in SOURCES.items()}


def reviewed(root):
    review = read(root / REVIEW)
    require(review.get('verdict') == 'PASS_GO', 'capability review not active')
    require(review.get('sources') == source_identity(root), 'reviewed source changed')
    require(review.get('actions') == sorted(ACTIONS), 'reviewed action scope changed')
    return digest(root / REVIEW)


def private_path(root, path):
    path = path.resolve()
    require(path.is_relative_to((root / BASE).resolve()), 'outside private research root')
    return path


def open_goal(root, goal, target_file, actions):
    review = reviewed(root)
    require(isinstance(goal, str) and 0 < len(goal.strip()) <= 1024, 'goal text required')
    require(actions and set(actions) <= ACTIONS, 'unknown/empty goal action scope')
    require(target_file.resolve().is_relative_to((root / 'workspace/private').resolve()), 'private target required')
    target = read(target_file)
    require(set(target) == {'serial', 'topology'}, 'exact prior D0 target binding required')
    require(d0.SERIAL_RE.fullmatch(target['serial']) and d0.DEVPATH_RE.fullmatch(target['topology']), 'target grammar')
    folder = root / BASE / uuid.uuid4().hex
    folder.mkdir(parents=True, mode=0o700)
    value = dict(schema='s22plus_goal_grant_v1', goal=goal, target=target,
                 actions=sorted(set(actions)), review_sha256=review,
                 authority='explicit-current-foreground-goal', unattended=False)
    publish(folder / 'grant.json', value)
    return folder / 'grant.json'


def load_goal(root, path):
    path = private_path(root, path)
    grant = read(path)
    require(path.name == 'grant.json' and not (path.parent / 'closed.json').exists(), 'goal closed or invalid')
    require(grant.get('schema') == 's22plus_goal_grant_v1' and grant.get('unattended') is False, 'goal type')
    require(grant.get('review_sha256') == reviewed(root), 'goal review changed')
    require(grant.get('authority') == 'explicit-current-foreground-goal', 'goal authority')
    require(grant.get('actions') and set(grant['actions']) <= ACTIONS, 'goal actions')
    return grant


def close_goal(root, path):
    path = private_path(root, path)
    require(path.name == 'grant.json', 'goal path')
    read(path)
    if not (path.parent / 'closed.json').exists():
        publish(path.parent / 'closed.json', dict(reason='operator-stop-or-goal-complete'))
    # Closing a grant never clears an uncertain device effect.
    return dict(verdict='GOAL_CLOSED')


def observe(client, target, profile, *, full=False):
    serial = client.one_serial()
    require(serial == target['serial'] and client.topology(serial) == target['topology'], 'target drift')
    props = client.properties(serial)
    for key, expected in [('model', 'SM-S906N'), ('device', 'g0q'), ('incremental', 'S906NKSS7FYG8'), ('bootloader', 'S906NKSS7FYG8')]:
        require(props[key] == expected, 'target firmware mismatch')
    require(d0.BOOT_ID_RE.fullmatch(props['boot_id']), 'boot identity')
    health = None
    if full:
        # Existing exact rooted Android health/hash validator, not a candidate
        # observer or broad arbitrary partition reader.
        census = d0.usb_snapshot(d0.DEFAULT_USB_ROOT, profile['target']['download'])
        health = d0.validate_health(SimpleNamespace(profile=profile), props,
                                  client.root_health(serial), census['download_endpoint_count'] == 0)
    return dict(properties=props, health=health)


def wait_return(client, target, profile, old_boot, *, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + RETURN_SECONDS
    original_run = client._run
    def bounded_run(arguments, label, timeout=20):
        remaining = deadline - clock()
        require(remaining > 0, 'return deadline expired')
        return original_run(arguments, label, min(timeout, remaining))
    client._run = bounded_run
    try:
        while clock() < deadline:
            # Expected offline/absence after our one reboot is the only polling
            # exception. Failed commands, malformed inventory and wrong targets stop.
            text = client._run(['devices', '-l'], 'reboot return inventory', 10)
            rows = [line.split() for line in text.splitlines() if line and not line.startswith('List of devices attached')]
            require(all(len(row) >= 2 for row in rows), 'malformed return inventory')
            matches = [row for row in rows if row[0] == target['serial']]
            foreign = [row for row in rows if row[0] != target['serial'] and {'model:SM_S906N', 'device:g0q'} <= set(row[2:])]
            require(not foreign and len(matches) <= 1, 'ambiguous return target')
            if matches:
                require(matches[0][1] in {'device', 'offline'}, 'unauthorized/unexpected return state')
                if matches[0][1] == 'device':
                    observed = observe(client, target, profile)
                    props = observed['properties']
                    if props['boot_completed'] == '1' and props['bootanim'] == 'stopped' and props['boot_id'] != old_boot:
                        result = observe(client, target, profile, full=True)
                        require(result['properties']['boot_id'] == props['boot_id'], 'boot changed during health')
                        require(clock() <= deadline, 'return health exceeded bound')
                        return result
            sleep(1)
        raise ResearchError('bounded reboot return unproved; observe only, never replay')
    finally:
        client._run = original_run


def execute(root, grant_path, action, *, attended=False, client_factory=None):
    grant_path = private_path(root, grant_path)
    grant = load_goal(root, grant_path)
    require(action in grant['actions'], 'action outside goal')
    require(action != 'normal-reboot' or attended, 'D1 requires current operator attendance')
    # Same process interlock as F1. A durable pending reboot blocks other effects
    # across process death; only this fixed D0 entry may inspect a pending run.
    with registry.target_session_lease(root, research_read_only=action != 'normal-reboot'):
        pending = root / registry.RESEARCH_PENDING
        if action == 'normal-reboot':
            registry.require_no_f1_owner(root)
        require(action != 'normal-reboot' or not pending.exists(), 'unresolved D1 intent')
        if pending.exists():
            require(read(pending)['target'] == grant['target'], 'pending target differs')
        run = grant_path.parent / uuid.uuid4().hex
        run.mkdir(mode=0o700)
        profile = read(root / PROFILE)
        factory = client_factory or (lambda: d0.AdbReadOnlyClient(d0.default_adb(), expected_model='SM-S906N', expected_device='g0q'))
        client = factory()
        client.bind_raw_capture_dir(run)
        intent = False
        try:
            before = observe(client, grant['target'], profile, full=action in {'health', 'normal-reboot'})
            publish(run / 'before.json', before)
            if action == 'normal-reboot':
                value = dict(schema='s22plus_goal_d1_intent_v1', grant_sha256=digest(grant_path),
                             run=str(run), target=grant['target'], boot_id=before['properties']['boot_id'],
                             command='adb-selected-serial-reboot', replay=False, attended=True)
                intent = True
                # The shared record is the authoritative intent. It must
                # precede the local mirror so a cut cannot leave an unguarded
                # consumed intent visible only inside the action directory.
                publish(pending, value)
                publish(run / 'intent.json', value)
                client._run(['-s', grant['target']['serial'], 'reboot'], 'ordinary reboot once', 10)
                after = wait_return(client, grant['target'], profile, before['properties']['boot_id'])
            else:
                if action in READS:
                    command, root_read = READS[action]
                    client._shell(grant['target']['serial'], command, root=root_read, timeout=20)
                after = observe(client, grant['target'], profile)
                require(after['properties']['boot_id'] == before['properties']['boot_id'], 'boot changed during D0')
            result = dict(schema='s22plus_goal_action_result_v1', action=action, verdict='PASS',
                          before=before, after=after, device_effect_count=int(intent), other_target_commands=0)
            publish(run / 'result.json', result)
            if intent:
                pending.unlink()
                d0._fsync_dir(pending.parent)
            return dict(run=str(run), verdict='PASS', action=action)
        except Exception as exc:
            publish(run / 'stop.json', dict(verdict='STOP', error_type=type(exc).__name__,
                                          device_effect_possible=intent, replay=False))
            # A failed goal is not automatically renewed by late healthy reads.
            if not (grant_path.parent / 'closed.json').exists():
                publish(grant_path.parent / 'closed.json', dict(reason='action-failed', run=str(run)))
            raise


def reconcile(root, *, client_factory=None):
    """One bounded health read after a cut; never dispatch/retry a reboot.

    Late healthy return can close recovery bookkeeping but ends the old goal;
    it cannot turn the failed bounded action into PASS or renew its authority.
    """
    reviewed(root)
    with registry.target_session_lease(root, research_read_only=True):
        pending = root / registry.RESEARCH_PENDING
        intent = read(pending)
        run = private_path(root, Path(intent['run']))
        if (run / 'intent.json').exists():
            require(read(run / 'intent.json') == intent, 'intent join')
        grant_path = run.parent / 'grant.json'
        grant = read(grant_path)
        require(digest(grant_path) == intent['grant_sha256'] and grant['target'] == intent['target'], 'pending goal join')
        require(grant['review_sha256'] == reviewed(root), 'pending source changed')
        recovery = run / ('health-observation-' + uuid.uuid4().hex)
        recovery.mkdir(mode=0o700)
        factory = client_factory or (lambda: d0.AdbReadOnlyClient(d0.default_adb(), expected_model='SM-S906N', expected_device='g0q'))
        client = factory()
        client.bind_raw_capture_dir(recovery)
        after = observe(client, intent['target'], read(root / PROFILE), full=True)
        require(after['properties']['boot_id'] != intent['boot_id'], 'changed healthy boot not observed')
        result = dict(verdict='LATE_HEALTH_OBSERVED_GOAL_CLOSED', action_proof='NOT_UPGRADED', after=after, reboot_replayed=False)
        publish(recovery / 'result.json', result)
        if not (run.parent / 'closed.json').exists():
            publish(run.parent / 'closed.json', dict(reason='post-intent-reconciliation', run=str(run)))
        pending.unlink()
        d0._fsync_dir(pending.parent)
        return dict(run=str(recovery), verdict=result['verdict'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--open-goal')
    parser.add_argument('--target-file', type=Path)
    parser.add_argument('--actions', nargs='+', choices=sorted(ACTIONS))
    parser.add_argument('--grant', type=Path)
    parser.add_argument('--action', choices=sorted(ACTIONS))
    parser.add_argument('--attended', action='store_true')
    parser.add_argument('--reconcile', action='store_true')
    parser.add_argument('--close-goal', action='store_true')
    args = parser.parse_args()
    if args.close_goal:
        require(args.grant is not None and args.action is None and args.open_goal is None and not args.reconcile, 'close arguments')
        print(json.dumps(close_goal(ROOT, args.grant)))
    elif args.reconcile:
        require(args.open_goal is None and args.grant is None and args.action is None, 'reconcile arguments')
        print(json.dumps(reconcile(ROOT)))
    elif args.open_goal is not None:
        require(args.target_file is not None and args.actions and args.grant is None and args.action is None, 'open arguments')
        print(open_goal(ROOT, args.open_goal, args.target_file, args.actions))
    else:
        require(args.grant is not None and args.action is not None, 'action arguments')
        print(json.dumps(execute(ROOT, args.grant, args.action, attended=args.attended)))


if __name__ == '__main__':
    main()
