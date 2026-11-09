"""Fixed caller for the existing attended mainline USB attach condition.

Load and test this entry before N. It reads sealed evidence, never USB/ADB,
and does not open a grant, extend a window or perform a device effect.
Only explicit issue/resolve verbs write the existing operation-local records.
"""
import argparse
import errno
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import consumed_candidate_registry_v1 as registry
import device_action_raw_capture_v1 as raw
import s22plus_mainline_access_v1 as access
import s22plus_mainline_attach_v1 as attach
from s22plus_native_adapter_v3 import Adapter
from s22plus_native_records_v3 import (
    Journal, canonical, clock, host_boot, pin, private_path, read, require, verify,
)
from s22plus_native_session_v3 import Session, Step

MIN_REMAINING_NS = 60_000_000_000
INSTRUCTION = (
    'Disconnect the phone end once for about three seconds, then reconnect '
    'using the same cable, host port and orientation, without pressing buttons. '
    'Report completion or cancellation promptly; do not repeat the action.'
)


def context(operation):
    operation = private_path(ROOT, Path(operation))
    require((operation / 'journal').is_dir(), 'existing operation journal required')
    adapter = Adapter(ROOT, operation)
    session = Session(ROOT, operation, adapter)
    require(session.request['operation'] == 'mainline-ram' and
            session.request['N'].get('ufs_link') is True,
            'caller selects only the mainline UFS-link observation')

    def guard():
        session.check()
        require(session.consumed() is not None, 'original operation was not consumed')
        registry.require_f1_owner(ROOT, operation, session.binding)

    return adapter, session.request, guard


def inspect(adapter, request, guard, *, diagnostics=None):
    """Recheck the existing cue conditions using the real retained consumers."""
    diagnostics = diagnostics if diagnostics is not None else {}
    diagnostics['phase'] = 'owner-guard-initial'
    guard()
    operation = adapter.directory
    folder = adapter.folder('mainline-evidence')
    window_pin = pin(folder / 'window.json')
    window = read(verify(window_pin))
    require(window == access.window_for(adapter, request) and
            window['host_boot'] == host_boot(), 'original observation window differs')
    transferred = adapter.recover_transfer_result(Step('install-native-first', 'transfer', 'N'), request)
    require(read(operation / 'install-native-first.json') == transferred, 'N is not raw-complete')
    rows = Journal(operation / 'journal').rows()
    require(rows and rows[-1]['event'] == 'step-start' and
            rows[-1]['data']['step'] == 'mainline-evidence' and
            rows[-1]['data']['action'] == 'mainline-download', 'observation is not active')
    require(sum(row['event'] == 'step-complete' and row['data']['step'] ==
                'install-native-first' for row in rows) == 1 and
            not any(row['event'] == 'stopped' for row in rows), 'N completion or stop differs')
    forbidden = [folder / name for name in (
        'endpoint.json', 'network-intent.json', 'attempt.json', 'base-complete.json',
        'witness-intent.json', 'permit-intent.json', 'control-intent.json',
        'connection.json', 'result.json')]
    forbidden += [operation / name for name in (
        'mainline-evidence.json', 'mainline-return-ready.json', 'terminal.json',
        'install-android.json', 'recover-android.json', 'mainline-attach-cue.json',
        'mainline-attach-resolution.json', 'mainline-attach-closed.json')]
    require(not any(path.exists() for path in forbidden), 'selection, return or cue already exists')
    require(window['deadline_ns'] - clock() > MIN_REMAINING_NS, 'cue needs more than 60 seconds')
    # Finish the potentially expensive source/artifact/owner guard before
    # selecting current raw evidence. The normal observer keeps publishing
    # while that guard runs; an older ordinal is not an identity boundary.
    diagnostics['phase'] = 'owner-guard-final'
    guard()
    diagnostics['phase'] = 'state-after-guard'
    require(Journal(operation / 'journal').rows() == rows and
            not any(path.exists() for path in forbidden), 'selection changed before cue')
    diagnostics['phase'] = 'census-selection'
    captures = sorted(path for path in folder.glob('usb-*.capture.json')
                      if re.fullmatch(r'usb-\d{3}\.capture\.json', path.name))
    require(bool(captures), 'no complete sealed census')
    latest = captures[-1]
    diagnostics['selected_census_path'] = str(latest)
    diagnostics['phase'] = 'census-load'
    handle = raw.load_handle(latest)
    diagnostics['selected_census'] = pin(latest)
    raw.require_success(handle)
    require(not raw.read_stderr(handle, maximum=16384), 'census has diagnostics')
    diagnostics['phase'] = 'census-parse'
    data = [json.loads(line) for line in raw.read_stdout(handle, maximum=access.MAX_SYSFS).splitlines()]
    require(len(data) == 3 and data[0]['kind'] == 'begin' and
            data[0]['topology'] == access.target.lane.CANDIDATE_TOPOLOGY and
            data[1] == dict(errno=errno.ENOENT, fields={}, kind='usb') and
            data[2]['kind'] == 'end' and data[2]['related'] == 0 and
            window['opened_ns'] <= data[0]['boottime_ns'] <= data[2]['boottime_ns'] <= clock(),
            'latest sealed census is not exact absent-without-children evidence')
    diagnostics['phase'] = 'state-after-census'
    require(Journal(operation / 'journal').rows() == rows and
            not any(path.exists() for path in forbidden), 'selection changed before cue')
    diagnostics['phase'] = 'census-tail'
    current = sorted(path for path in folder.glob('usb-*.capture.json')
                     if re.fullmatch(r'usb-\d{3}\.capture\.json', path.name))
    diagnostics['latest_census_path'] = str(current[-1]) if current else None
    require(current and current[-1] == latest, 'new sealed census arrived during final cue check')
    require(raw.load_handle(latest) == handle, 'selected sealed census changed during final cue check')
    diagnostics['phase'] = 'final-window'
    checked = clock()
    require(window['deadline_ns'] - checked > MIN_REMAINING_NS,
            'cue issuance window elapsed during validation')
    return dict(window=window_pin, native_transfer=pin(operation / 'install-native-first.json'),
                last_sealed_census=pin(latest),
                journal_tail=pin(operation / 'journal' / f"{rows[-1]['sequence']:04d}.json"),
                checked_ns=checked, remaining_seconds=(window['deadline_ns'] - checked) / 1e9)


def issue(adapter, request, guard, *, diagnostics=None):
    diagnostics = diagnostics if diagnostics is not None else {}
    operation = adapter.directory
    window = pin(adapter.folder('mainline-evidence') / 'window.json')
    evidence = {}

    def check():
        evidence.update(inspect(adapter, request, guard, diagnostics=diagnostics))
        require(evidence['window'] == window, 'cue window changed')
        diagnostics['phase'] = 'cue-publication'

    error_type = None
    try:
        receipt = attach.issue(operation, window, evidence=evidence, check=check)
    except (ValueError, OSError) as error:
        cue = operation / 'mainline-attach-cue.json'
        if not cue.exists():
            raise
        receipt = pin(cue)
        retained = read(verify(receipt))
        require(evidence and retained == dict(attach.binding(operation, window),
                evidence=evidence, issued_ns=retained['issued_ns']),
                'failed publication does not identify this checked cue')
        error_type = type(error).__name__
    recorded = read(verify(receipt))
    deadline = read(verify(window))['deadline_ns']
    # A delayed publication is not permission to display a late instruction.
    # Retain the existing cue and interlock; never delete, retry or infer a
    # physical completion/cancellation from this local result.
    display = error_type is None and deadline - recorded['issued_ns'] > MIN_REMAINING_NS and deadline - clock() > MIN_REMAINING_NS
    return dict(status='CUE_RECORDED_DISPLAY_NOW' if display else 'CUE_RECORDED_DO_NOT_DISPLAY',
                cue=receipt, instruction=INSTRUCTION if display else None,
                resolution_required=True, publication_error_type=error_type, device_actions=0)


def resolve(operation, resolution, statement):
    operation = private_path(ROOT, Path(operation))
    require((operation / 'mainline-attach-cue.json').is_file(), 'no actual cue to resolve')
    # Evidence-only resolution may be needed after the original window/owner
    # stops; it does not require or renew a live grant.
    return attach.resolve(operation, pin(operation / 'io-mainline-evidence/window.json'),
                          cue=pin(operation / 'mainline-attach-cue.json'),
                          resolution=resolution, operator_statement=statement)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='verb', required=True)
    for name in ('check', 'issue', 'resolve'):
        command = commands.add_parser(name)
        command.add_argument('operation', type=Path)
        if name == 'resolve':
            command.add_argument('resolution', choices=('completed', 'cancelled'))
            command.add_argument('operator_statement')
    args = parser.parse_args()
    diagnostics = dict(phase='context', operation=str(args.operation), verb=args.verb)
    try:
        if args.verb == 'resolve':
            result = resolve(args.operation, args.resolution, args.operator_statement)
        else:
            adapter, request, guard = context(args.operation)
            result = (inspect(adapter, request, guard, diagnostics=diagnostics) if args.verb == 'check'
                      else issue(adapter, request, guard, diagnostics=diagnostics))
        if args.verb == 'issue' and result['instruction'] is not None:
            diagnostics['phase'] = 'display-window'
            window = read(verify(read(verify(result['cue']))['window']))
            if window['deadline_ns'] - clock() <= MIN_REMAINING_NS:
                result.update(status='CUE_RECORDED_DO_NOT_DISPLAY', instruction=None)
    except (ValueError, OSError, KeyError, TypeError, raw.RawCaptureError) as error:
        # The caller's stdout/stderr must be retained by the prepared invocation.
        # A refusal is not proof that a cue was never published. No diagnostic
        # failure removes a cue, grants a retry, or resolves physical action.
        diagnostics.update(error_type=type(error).__name__, error=str(error))
        sys.stderr.write(canonical(dict(status='CUE_CALL_REFUSED', diagnostics=diagnostics)).decode())
        raise SystemExit(1) from error
    print(canonical(result).decode(), end='')


if __name__ == '__main__':
    main()
