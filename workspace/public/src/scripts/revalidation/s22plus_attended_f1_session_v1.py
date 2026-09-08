#!/usr/bin/env python3
"""Finite attended F1 authority; no device transport and no consent synthesis.

Only the trusted foreground owner may record an actual operator grant/attendance.
The flags below cannot establish either fact. Activation requires a source-bound
independent review; a session never changes consumed-run recovery authority.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import time
import uuid

import device_action_f1_v2 as core
import consumed_candidate_registry_v1 as registry

ROOT = Path(__file__).resolve().parents[5]
BASE = Path('workspace/private/runs/s22plus-attended-f1-session-v1')
PROFILE = 'workspace/public/src/device-action/profiles/s22plus_fyg8.json'
REVIEW = Path('workspace/public/src/device-action/bindings/s22plus_attended_f1_session_v1_review.json')
POLICY = Path('docs/operations/targets/S22PLUS_FYG8_ATTENDED_F1_SESSION_V1.md')
AUTH_FILE = 'attended-session-authorization.json'
LIMIT = 3
SECONDS = 7200
SCHEMA = 's22plus_attended_f1_session_v1'
SOURCES = [
    Path(__file__).resolve().relative_to(ROOT),
    Path('workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py'),
    Path('workspace/public/src/scripts/revalidation/device_action_f1_v2.py'),
    Path('workspace/public/src/scripts/revalidation/consumed_candidate_registry_v1.py'),
    Path('workspace/public/src/scripts/revalidation/device_action_d0_v2.py'),
    Path(PROFILE), POLICY,
    Path('docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md'),
    Path('docs/operations/DEVICE_ACTION_PROCESS_V2.md'),
    Path('docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md'),
]


class SessionError(core.F1V2Error):
    pass


def require(condition, message):
    if not condition:
        raise SessionError(message)


def identity(path):
    return core._stable_read(path, 'session bound file', core.MAX_JSON)[1]


def read(path):
    value, receipt = core.load_json(path, 'session record')
    return value, receipt['sha256']


def direct(root, path, *, private=False):
    path = Path(path)
    path = path if path.is_absolute() else root / path
    path = path.absolute()
    require(path.resolve() == path, 'indirect session path')
    require(path.is_relative_to(root / ('workspace/private' if private else '')), 'path outside allowed root')
    return path


def immutable(path):
    value, digest = read(path)
    info = path.stat()
    require(stat.S_IMODE(info.st_mode) == 0o400 and info.st_nlink == 1 and info.st_uid == os.getuid(), 'session record ownership/mode/link differs')
    return value, digest


def publish(path, value):
    core._write_exclusive(path, value)


def host_boot():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def sources(root):
    return {str(path): identity(root / path)['sha256'] for path in SOURCES}


def reviewed(root):
    value, digest = read(root / REVIEW)
    require(value.get('verdict') == 'PASS_GO' and value.get('findings') == [], 'session review unavailable')
    require(value.get('sources') == sources(root), 'session reviewed source changed')
    require(value.get('limits') == {'reservations': LIMIT, 'seconds': SECONDS}, 'session reviewed limits changed')
    require(value.get('activation') == SCHEMA, 'session capability not activated')
    return digest


def verify_receipt(root, receipt):
    core._exact(receipt, {'path', 'size', 'sha256'}, 'session file receipt')
    actual = identity(direct(root, receipt['path']))
    require({k: actual[k] for k in ('size', 'sha256')} == {k: receipt[k] for k in ('size', 'sha256')}, 'reviewed file changed')


def catalog_entry(live, root, manifest_path, review_path):
    manifest_path = direct(root, manifest_path)
    review_path = direct(root, review_path, private=True)
    bundle = core.verify_bundle(root, manifest_path, runtime_bound=True)
    m = bundle.manifest
    require(m['target_profile'] == PROFILE and m['status'] == 'ready-for-f1-approval', 'session needs exact ready S22+ profile')
    observer = m['observation']['candidate_observer']
    require(observer.get('mandatory_rollback') is True and observer.get('control_mode') == 'download', 'session needs reviewed native Download return')
    review, review_sha = read(review_path)
    require(review.get('verdict') == 'PASS_GO' and review.get('findings') == [], 'candidate capability not reviewed')
    require(review.get('current_sources'), 'candidate review has no source binding')
    for receipt in review['current_sources'].values():
        verify_receipt(root, receipt)
    static = m['observation']['acceptance']['contract']['candidate_static']
    require(review.get('static_result') == static, 'candidate review/static mismatch')
    verify_receipt(root, static)
    static_value, _ = read(direct(root, static['path'], private=True))
    closure = static_value['source_closure']
    cb = review.get('execution_closure_binding', {})
    require(cb.get('record') == static and cb.get('field') == 'source_closure' and cb.get('canonical_sha256') == core.json_sha256(closure), 'candidate review closure mismatch')
    require(review.get('candidate_ap') == {k: m['candidate_ap'][k] for k in ('size','sha256')}, 'candidate review AP mismatch')
    return dict(manifest=str(manifest_path.relative_to(root)), manifest_sha256=identity(manifest_path)['sha256'],
                review=str(review_path.relative_to(root)), review_sha256=review_sha,
                bundle_sha256=bundle.sha256, closure_sha256=core.json_sha256(live._closure(root, bundle)),
                candidate=m['candidate_ap'], rollback=m['rollback_ap'])


def grant_path(root, path):
    path = direct(root, path, private=True)
    require(path.is_relative_to(root / BASE) and path.name == 'grant.json', 'invalid session grant location')
    return path


def open_session(live, root, *, goal, target_file, catalog, attended, reservations=LIMIT, seconds=SECONDS):
    require(attended is True, 'explicit current attendance required')
    require(type(reservations) is int and 1 <= reservations <= LIMIT, 'reservation limit')
    require(type(seconds) is int and 1 <= seconds <= SECONDS, 'time limit')
    require(type(goal) is str and 0 < len(goal.strip()) <= 1024, 'bounded research goal required')
    require(type(catalog) is list and 1 <= len(catalog) <= reservations, 'catalog limit')
    require(all(type(pair) in (list,tuple) and len(pair) == 2 and all(isinstance(p,(str,Path)) for p in pair) for pair in catalog), 'catalog entry shape')
    review_sha = reviewed(root)
    target, _ = read(direct(root, target_file, private=True))
    core._exact(target, {'serial', 'topology'}, 'prior exact target')
    require(live.d0.SERIAL_RE.fullmatch(target['serial']) and live.d0.DEVPATH_RE.fullmatch(target['topology']), 'target grammar')
    with registry.target_session_lease(root):
        registry.require_no_f1_owner(root)
        entries = [catalog_entry(live, root, *pair) for pair in catalog]
        require(len({e['manifest'] for e in entries}) == len(entries), 'duplicate catalog manifest')
        require(len({e['candidate']['sha256'] for e in entries}) == len(entries), 'duplicate candidate')
        require(all(e['rollback'] == entries[0]['rollback'] for e in entries), 'rollback differs within session')
        folder = root / BASE / uuid.uuid4().hex
        folder.mkdir(parents=True, mode=0o700)
        core._fsync_dir(folder.parent)
        start = time.monotonic_ns()
        value = dict(schema=SCHEMA, goal=goal, target=target, review_sha256=review_sha,
                     authority='explicit-operator-attended-session', unattended=False,
                     host_boot=host_boot(), started_ns=start, deadline_ns=start + seconds*1_000_000_000,
                     reservations=reservations, catalog=entries)
        publish(folder / 'grant.json', value)
        return folder / 'grant.json'


def load_grant(root, path, *, active=False):
    path = grant_path(root, path)
    g, digest = immutable(path)
    core._exact(g, {'schema','goal','target','review_sha256','authority','unattended','host_boot','started_ns','deadline_ns','reservations','catalog'}, 'session grant')
    require(g['schema'] == SCHEMA and g['authority'] == 'explicit-operator-attended-session' and g['unattended'] is False, 'session authority shape')
    require(type(g['reservations']) is int and 1 <= g['reservations'] <= LIMIT, 'grant reservation range')
    require(type(g['started_ns']) is int and type(g['deadline_ns']) is int and 0 < g['deadline_ns'] - g['started_ns'] <= SECONDS*1_000_000_000, 'grant time range')
    require(type(g['catalog']) is list and 1 <= len(g['catalog']) <= g['reservations'], 'grant catalog range')
    if active:
        require(not os.path.lexists(path.parent / 'closed.json'), 'session closed')
        require(g['review_sha256'] == reviewed(root), 'session review changed')
        require(g['host_boot'] == host_boot() and g['started_ns'] <= time.monotonic_ns() < g['deadline_ns'], 'session expired or host changed')
    return g, digest


def close(root, path, reason):
    path = grant_path(root, path)
    _, digest = load_grant(root, path)
    closed = path.parent / 'closed.json'
    if not os.path.lexists(closed):
        try:
            publish(closed, dict(grant_sha256=digest, reason=reason))
        except FileExistsError:
            pass
    # No owner/journal mutation: withdrawal cannot cancel existing recovery.
    return {'verdict': 'ATTENDED_F1_SESSION_CLOSED'}


def authorization(prepared):
    path = prepared.run_dir / AUTH_FILE
    a, _ = immutable(path)
    core._exact(a, {'grant','grant_sha256','ordinal','reservation_sha256','binding_sha256','run_dir','manifest'}, 'session authorization')
    require(type(a['ordinal']) is int and 1 <= a['ordinal'] <= LIMIT, 'authorization ordinal')
    gpath = grant_path(prepared.root, a['grant'])
    g, gd = load_grant(prepared.root, gpath)
    require(a['grant_sha256'] == gd and a['binding_sha256'] == prepared.binding_sha256 and a['run_dir'] == str(prepared.run_dir.relative_to(prepared.root)), 'authorization binding differs')
    reservation, rd = immutable(gpath.parent / f"{a['ordinal']:02d}-reserved.json")
    require(rd == a['reservation_sha256'] and reservation == {k: a[k] for k in ('grant_sha256','ordinal','binding_sha256','run_dir','manifest')}, 'reservation differs')
    require(a['ordinal'] <= g['reservations'] and {k: prepared.private_target[k] for k in ('serial','topology')} == g['target'], 'authorization target/limit differs')
    return a


def journal_authority(prepared):
    a = authorization(prepared)
    return dict(authorization_kind='attended_session', grant_sha256=a['grant_sha256'],
                session_ordinal=a['ordinal'], reservation_sha256=a['reservation_sha256'])


def validate_journal(prepared, records):
    claimed = [r for r in records if r.get('details', {}).get('authorization_kind') == 'attended_session']
    exists = os.path.lexists(prepared.run_dir / AUTH_FILE)
    if not exists and not claimed:
        return
    require(exists, 'journal session authority missing sidecar')
    expected = journal_authority(prepared)
    require(len(claimed) == 1 and claimed[0]['kind'] == 'transition' and claimed[0]['state'] == 'APPROVED' and all(claimed[0]['details'].get(k) == v for k,v in expected.items()), 'journal session attribution differs')
    require(claimed[0]['details'].get('approval_binding_sha256') == prepared.binding_sha256 and claimed[0]['details'].get('rollback_preapproved') is True, 'journal session rollback binding differs')


def before_recovery(live, prepared):
    """A device-session interruption cannot be cleared by later healthy recovery."""
    a = authorization(prepared)
    journal = core.Journal.reopen(prepared.run_dir / 'transaction', prepared.binding_sha256)
    if journal.state() == 'CLOSED':
        return  # Host-only terminal publication repair; no new device transition.
    if journal.state() == 'ABORTED' and not os.path.lexists(prepared.run_dir / 'candidate-download-request-intent.json'):
        path = prepared.run_dir / 'live-result.json'
        if path.is_file() and not path.is_symlink():
            result, _ = read(path)
            live.validate_live_result(result, prepared)
            if result['live_state'].get('candidate_classification') == 'not-attempted' and result['recovery_required'] is False:
                return
    close(prepared.root, a['grant'], 'interrupted-device-session-recovery')


def finish(live, prepared, result):
    a = authorization(prepared)
    live.validate_live_result(result, prepared)
    require(read(prepared.run_dir / "live-result.json")[0] == result, "published result differs")
    state = result['live_state']
    pre_effect = (result['current_state'] == 'ABORTED' and result['recovery_required'] is False
                  and state.get('candidate_classification') == 'not-attempted'
                  and not os.path.lexists(prepared.run_dir / 'candidate-download-request-intent.json'))
    successful = (result['current_state'] == 'CLOSED' and result['verdict'].startswith('PASS_')
                  and result['recovery_required'] is False and state.get('final_verified') is True)
    eligible = successful or pre_effect
    record = dict(reservation_sha256=a['reservation_sha256'], result_sha256=identity(prepared.run_dir/'live-result.json')['sha256'], eligible=eligible)
    terminal = direct(prepared.root, a['grant']).parent / f"{a['ordinal']:02d}-completed.json"
    if os.path.lexists(terminal):
        require(immutable(terminal)[0] == record, 'completed reservation changed')
    else:
        publish(terminal, record)
    g, _ = load_grant(prepared.root, a['grant'])
    if not eligible:
        close(prepared.root, a['grant'], 'preceding-experiment-did-not-pass-or-recovery-unproved')
    elif a['ordinal'] == g['reservations'] or (successful and a['manifest'] == g['catalog'][-1]['manifest']):
        close(prepared.root, a['grant'], 'budget-consumed-or-catalog-complete')
    return eligible


def require_unreserved(prepared):
    """The grant reservation is authoritative even before the run sidecar exists."""
    base = prepared.root / BASE
    if not base.exists():
        return
    require(base.resolve() == base, 'indirect session root')
    for path in sorted(base.glob('*/*-reserved.json')):
        record, _ = immutable(path)
        require(type(record.get('run_dir')) is str, 'invalid reservation run')
        require(record['run_dir'] != str(prepared.run_dir.relative_to(prepared.root)),
                'prepared run already has an authoritative session reservation')


def reserve(live, prepared, path, *, attended):
    # Caller MUST hold the existing target session lease for the whole execute.
    require(attended is True, 'operator attendance required')
    gpath = grant_path(prepared.root, path)
    g, gd = load_grant(prepared.root, gpath, active=True)
    require({k: prepared.private_target[k] for k in ('serial','topology')} == g['target'], 'session target differs')
    require(not os.path.lexists(prepared.run_dir/'transaction') and not os.path.lexists(prepared.run_dir/AUTH_FILE), 'prepared run already reserved or consumed')
    registry.require_no_f1_owner(prepared.root)
    require_unreserved(prepared)
    entry = next((e for e in g['catalog'] if e['bundle_sha256'] == prepared.bundle.sha256), None)
    require(entry is not None, 'candidate outside fixed catalog')
    require(catalog_entry(live, prepared.root, entry['manifest'], entry['review']) == entry, 'catalog source/artifact drift')
    ordinal = 1
    catalog_index = 0
    while os.path.lexists(gpath.parent/f'{ordinal:02d}-reserved.json'):
        old, _ = immutable(gpath.parent/f'{ordinal:02d}-reserved.json')
        require(old.get('grant_sha256') == gd and type(old.get('ordinal')) is int and old['ordinal'] == ordinal, 'previous reservation belongs to another grant/ordinal')
        require(os.path.lexists(gpath.parent/f'{ordinal:02d}-completed.json'), 'previous reservation unresolved')
        require(catalog_index < len(g['catalog']) and old['manifest'] == g['catalog'][catalog_index]['manifest'], 'prior reservation is out of catalog order')
        prior = live.load_prepared(prepared.root, Path(old['manifest']), direct(prepared.root, old['run_dir'], private=True))
        result, _ = read(prior.run_dir/'live-result.json')
        require(finish(live, prior, result), 'preceding experiment did not pass')
        if result['current_state'] == 'CLOSED':
            catalog_index += 1
        ordinal += 1
    require(ordinal <= g['reservations'], 'session reservation budget exhausted')
    require(catalog_index < len(g['catalog']) and entry == g['catalog'][catalog_index], 'candidate is out of fixed catalog order')
    receipt = dict(grant_sha256=gd, ordinal=ordinal, binding_sha256=prepared.binding_sha256,
                   run_dir=str(prepared.run_dir.relative_to(prepared.root)), manifest=entry['manifest'])
    destination = gpath.parent / f'{ordinal:02d}-reserved.json'
    publish(destination, receipt)
    a = dict(receipt, grant=str(gpath.relative_to(prepared.root)), reservation_sha256=immutable(destination)[1])
    publish(prepared.run_dir / AUTH_FILE, a)
    return authorization(prepared)


def check_effect_start(prepared):
    a = authorization(prepared)
    load_grant(prepared.root, a['grant'], active=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--open', action='store_true')
    modes.add_argument('--close', type=Path)
    parser.add_argument('--goal')
    parser.add_argument('--target-file', type=Path)
    parser.add_argument('--catalog', type=Path, help='private JSON: entries of [manifest, existing capability review]')
    parser.add_argument('--attended', action='store_true')
    parser.add_argument('--reservations', type=int, default=LIMIT)
    parser.add_argument('--seconds', type=int, default=SECONDS)
    args = parser.parse_args(argv)
    import device_action_f1_live_v2 as live
    if args.close:
        print(close(ROOT, args.close, 'operator-withdrawal'))
    else:
        require(args.catalog is not None and args.target_file is not None, 'catalog and target required')
        catalog, _ = read(direct(ROOT, args.catalog, private=True))
        core._exact(catalog, {'entries'}, 'catalog')
        path = open_session(live, ROOT, goal=args.goal, target_file=args.target_file,
                            catalog=catalog['entries'], attended=args.attended,
                            reservations=args.reservations, seconds=args.seconds)
        print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
