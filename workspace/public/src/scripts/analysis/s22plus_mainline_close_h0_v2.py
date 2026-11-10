"""Offline mainline closure with bounded raw-index pages; no live owner changes.

Run only after a durable healthy Android terminal and owner release. The original
execution source binding remains immutable; this reporting tool has its own
review and retained source. Existing v1 closures use the original v1 verifier.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(ROOT/'workspace/public/src/scripts/revalidation'),
               str(ROOT/'workspace/public/src/scripts/host_tools')]
import s22plus_mainline_task_v1 as original
from s22plus_native_adapter_v3 import Adapter
from s22plus_native_session_v3 import Session
from s22plus_native_records_v3 import (canonical, digest, pin, private_path, publish,
                                     read, read_bytes, require, sync_dir, verify)

PAGE_SIZE = 256
INDEX_SCHEMA = 's22plus-comparison-raw-index-v2'
PAGE_SCHEMA = 's22plus-comparison-raw-page-v2'
CLOSED_SCHEMA = 's22plus-comparison-task-closed-v2'
REVIEW_SCHEMA = 's22plus-mainline-close-h0-review-v2'


def retain(path, value):
    if path.exists():
        require(read_bytes(path) == canonical(value), 'retained close artifact differs: '+path.name)
        return pin(path)
    return publish(path, value)


def capture_rows(folder):
    rows = []
    for path in sorted(folder.rglob('*.capture.json')):
        handle = original.access.raw.load_handle(path)
        original.access.raw.read_stdout(handle, maximum=max(handle.stdout['size'], 1))
        original.access.raw.read_stderr(handle, maximum=max(handle.stderr['size'], 1))
        rows.append(dict(receipt=pin(path), returncode=handle.returncode, timed_out=handle.timed_out))
    return rows


def raw_index(folder, *, write=False):
    """Verify complete discovery, all raw bytes and deterministic page contents."""
    if write and (folder/'raw-index-v2.json').exists():
        return raw_index(folder)
    rows = capture_rows(folder)
    page_dir = folder/'raw-pages-v2'
    if write and not page_dir.exists():
        page_dir.mkdir(mode=0o700)
        sync_dir(folder)
    pages = []
    expected_paths = []
    for number, start in enumerate(range(0, len(rows), PAGE_SIZE)):
        captures = rows[start:start+PAGE_SIZE]
        value = dict(schema=PAGE_SCHEMA, number=number, start=start,
                     count=len(captures), captures=captures)
        path = page_dir/f'{number:05d}.json'
        if write:
            receipt = retain(path, value)
        else:
            require(read_bytes(path) == canonical(value), 'raw page differs from complete capture set')
            receipt = pin(path)
        pages.append(receipt)
        expected_paths.append(path)
    require(page_dir.is_dir() and sorted(page_dir.glob('*.json')) == expected_paths,
            'raw page set differs')
    value = dict(schema=INDEX_SCHEMA, page_size=PAGE_SIZE, capture_count=len(rows), pages=pages)
    path = folder/'raw-index-v2.json'
    if write:
        receipt = retain(path, value)
    else:
        require(read_bytes(path) == canonical(value), 'raw index differs from complete capture set')
        receipt = pin(path)
    return receipt, rows


def derivation(root, task_path):
    """Same original validation, raw-proved terminal, counts and timeline as v1."""
    root = Path(root).resolve(strict=True)
    task_path = private_path(root, task_path)
    task_pin = pin(task_path)
    task = read(task_path)
    selected = original.selected_profile(task['N'])
    require(selected is original.profile, 'offline finalizer is mainline-only')
    original.validate_task(root, task, live=True, recovery=True, require_android=False)
    folder = task_path.parent
    grant = pin(folder/'grant.json')
    original.tasks.validate_grant(task, read(verify(grant)), Path(grant['path']))
    operations = sorted(folder.glob('operation-*/operation.json'))
    require(len(operations) == 1, 'comparison task has no unique operation')
    operation = operations[0]
    request = read(operation)
    require(request['task'] == task_pin and request['grant'] == grant and
            request['operation'] == selected.OPERATION, 'close differs from original task')
    prior = read(operation.parent/'terminal.json')
    require(prior['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and prior['research_closed'] is True,
            'offline finalizer requires an existing healthy terminal')
    original.registry.require_no_f1_owner(root)
    session = Session(root, operation.parent, Adapter(root, operation.parent))
    terminal = session.repair_close()
    require(terminal == prior, 'terminal rederivation differs')
    original.registry.require_no_f1_owner(root)
    rows = session.rows()
    effects = [r for r in rows if r['event'] == 'effect-intent']
    transfers = [r for r in effects if r['data']['action'] == 'transfer']
    a = [r for r in transfers if r['data']['role'] == 'A']
    n = [r for r in transfers if r['data']['role'] == 'N']
    require(len(a) == 1 and len(n) <= 1 and len(a)+len(n) == len(transfers),
            'comparison transfer count differs')
    opened = read(verify(grant))['opened_ns']

    def event(label, kind, step):
        matches = [r for r in rows if r['event'] == kind and r['data'].get('step') == step]
        require(len(matches) <= 1, 'duplicate timeline transition')
        if not matches:
            return dict(event=label, seconds=None, status='NOT_PROVED')
        row = matches[0]
        return dict(event=label, seconds=(row['boottime_ns']-opened)/1e9,
                    journal=pin(session.journal.directory/f"{row['sequence']:04d}.json"))

    ended = rows[-1]['boottime_ns']
    timeline = dict(schema='s22plus-canonical-timeline-v1', events=[
        dict(event='live_session_start', seconds=0, grant=grant),
        event('candidate_flash_start', 'effect-intent', 'install-native-first'),
        event('candidate_flash_done', 'step-complete', 'install-native-first'),
        event('candidate_boot_ready', 'step-complete', selected.SELECTION),
        event('rollback_flash_start', 'effect-intent', a[0]['data']['step']),
        event('rollback_flash_done', 'step-complete', a[0]['data']['step']),
        event('rollback_boot_ready', 'step-complete', terminal['terminal_step']),
        dict(event='live_session_end', seconds=(ended-opened)/1e9, status='DURABLE_SESSION_CLOSE')])
    value = dict(schema=CLOSED_SCHEMA, task=task_pin, grant=grant, operation=pin(operation),
        current_android_terminal=pin(operation.parent/'terminal.json'), terminal_state=terminal['terminal_state'],
        scientific_status=terminal['mainline']['status'], recovered=terminal['recovered'],
        closed_boottime_ns=ended, original_N_transfers_total=len(n), original_A_transfers_total=len(a),
        device_controls_total=sum(r['data']['action'] in ('download', 'mainline-download') for r in effects)+
                              sum(r['event'] == 'ml030-return-intent' for r in rows),
        automatic_recovery_proved=False, native_admitted=False,
        source_binding=task['review'], source_snapshot=pin(folder/'source-snapshot.json'),
        device_actions_by_closure=0, journal_rows=len(rows),
        journal_tail=pin(session.journal.directory/f'{len(rows)-1:04d}.json'))
    # Reopen retained execution bytes; reporting never replaces these pins.
    for item in read(verify(value['source_snapshot']))['sources']:
        verify(item['retained'])
        require(all(item['original'][k] == item['retained'][k] for k in ('size', 'sha256')),
                'retained execution source differs')
    return value, timeline


def reporting(folder, review_path):
    review_pin = pin(review_path)
    review = read(verify(review_pin))
    source = pin(Path(__file__).resolve(strict=True))
    require(review.get('schema') == REVIEW_SCHEMA and review.get('verdict') == 'PASS_GO' and
            review.get('source') == source and review.get('findings') == [] and
            type(review.get('reviewer')) is str and review['reviewer'].strip() and
            review.get('device_actions') == 0, 'reporting review is absent or changed')
    text = read_bytes(Path(source['path'])).decode('utf-8')
    require(digest(text.encode()) == source['sha256'], 'reporting source changed')
    retained = retain(folder/'reporting-source-v2.json', dict(source=source, text=text))
    return dict(source=source, retained_source=retained, review=review_pin)


def close_task(root, task_path, review_path):
    root = Path(root).resolve(strict=True)
    task_path = private_path(root, task_path)
    folder = task_path.parent
    closed = folder/'closed.json'
    if closed.exists() and read(closed)['schema'] == 's22plus-comparison-task-closed-v1':
        # Keep historical schema and bytes; use its actual original verifier.
        return original.close_task(root, task_path)
    value, timeline = derivation(root, task_path)
    provenance = reporting(folder, private_path(root, review_path))
    index, _ = raw_index(folder, write=True)
    value.update(raw_captures=index, canonical_timeline=retain(folder/'timeline.json', timeline),
                 reporting_provenance=provenance)
    # Verify every page, capture and raw file again before publishing closed last.
    require(raw_index(folder)[0] == index, 'raw evidence changed during publication')
    return retain(closed, value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', type=Path)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(canonical(close_task(args.root, args.task, args.review)).decode(), end='')


if __name__ == '__main__':
    main()
