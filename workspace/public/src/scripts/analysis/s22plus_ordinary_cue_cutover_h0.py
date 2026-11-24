"""Read-only pre-adoption check for the S22+ ordinary-cue squash."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory

if __name__ == '__main__':
    sys.dont_write_bytecode = True
scripts = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(scripts/name) for name in ('revalidation', 'host_tools')]
from s22plus_native_records_v3 import Journal, SCHEMA, clock, host_boot, pin, private_path, read, require, verify
from consumed_candidate_registry_v1 import require_no_f1_owner
from s22plus_approved_terminal_persistent_v1 import read_bytes, selected_review
from s22plus_approved_terminal_tasks_v1 import Controller, DISPATCH
from s22plus_mainline_task_v1 import selected_profile
from s22plus_native_session_v3 import Session, live_grant

BINDINGS = Path('workspace/public/src/device-action/bindings')
OLD_LOADER = BINDINGS/'s22plus_loader_android_timing_v3_review.json'
SELECTOR = BINDINGS/'s22plus_approved_terminal_persistent_current.json'
SOURCE_ROOTS = ('AGENTS.md', 'docs/operations', 'workspace/public/src')
GIT_ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')

# Run the proposed validators in a fresh interpreter so none of their
# imports resolve to the operating checkout or the checker checkout.
VALIDATOR_BOOTSTRAP = """
import json
from pathlib import Path
import re
import sys

def host_only(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn'):
        raise ValueError('unexpected external operation in proposal validation')

sys.addaudithook(host_only)
root = Path(sys.argv[1])
scripts = root/'workspace/public/src/scripts'
sys.path[:0] = [str(scripts/name) for name in ('host_tools', 'revalidation')]
import s22plus_mainline_task_v1 as task
"""

OPERATING_LOADER_CHECK = VALIDATOR_BOOTSTRAP + """
loader = task.selected_profile({'profile': 'loader-android-v1'})
receipt = task.capability(root, selected=loader)
print(json.dumps(Path(receipt['path']).relative_to(root).as_posix()))
"""

PRODUCTION_CHECK = VALIDATOR_BOOTSTRAP + """
snapshot = root
operating, selector_path = map(Path, sys.argv[2:])
import s22plus_approved_terminal_persistent_v1 as terminal
import s22plus_approved_terminal_tasks_v1 as backend

def relocate(receipt):
    path = Path(receipt['path'])
    terminal.require(path.is_absolute() and path.is_relative_to(operating)
                     and '..' not in path.parts and receipt['path'] == str(path),
                     'proposal receipt path is outside the canonical operating checkout')
    return dict(receipt, path=str(snapshot/path.relative_to(operating)))

terminal.require(Path(terminal.SELECTOR) == selector_path, 'proposed gateway selector path differs')
selector_file = snapshot/selector_path
selector = terminal.decode(terminal.read_bytes(selector_file))
# Verify the canonical selector's original hash and size before rebasing
# absolute paths. Only the disposable copy gets relocated metadata.
gateway_file = terminal.verify(snapshot, relocate(selector['review']))
gateway = terminal.decode(terminal.read_bytes(gateway_file))
for key in ('sources', 'worker_sources'):
    gateway[key] = [relocate(row) for row in gateway[key]]
gateway_file.write_bytes(terminal.canonical(gateway))
selector['review'] = terminal.pin(gateway_file)
selector_file.write_bytes(terminal.canonical(selector))
gateway_receipt = backend.verify_bridge(snapshot)
terminal.require(Path(gateway_receipt['path']) == gateway_file, 'proposed gateway selection differs')
terminal.require(type(gateway['reviewer']) is str and gateway['reviewer'].strip(),
                 'adoption requires independent gateway review attribution')

loader = task.selected_profile({'profile': 'loader-android-v1'})
bindings = selector_path.parent
routes = [('loader', task.LOADER_CUE_REVIEW, {'selected': loader}),
          ('SCM', task.profile.SCM_CUE_REVIEW, {'image': {'schema': task.profile.SCM_SCHEMA},
                                                'ordinary_cue': True})]
mx_review = getattr(task.profile, 'MX_REVIEW', None)
mx_policy = snapshot/'docs/operations/S22PLUS_MAINLINE_MAX77705_USB_V1.md'
mx_review_name = r's22plus_mainline_max77705_usb_v[1-9][0-9]*_review[.]json'
if mx_review is not None or mx_policy.exists() or any((snapshot/bindings).glob('s22plus_mainline_max77705_usb_v*_review.json')):
    terminal.require(type(mx_review) is str and re.fullmatch(mx_review_name, Path(mx_review).name),
                     'proposed MAX77705 review selection differs')
    routes.append(('MAX77705', mx_review, {'image': {'schema': task.profile.MX_SCHEMA},
                                         'ordinary_cue': True}))
mxr_review = getattr(task.profile, 'MXR_REVIEW', None)
mxr_policy = snapshot/'docs/operations/S22PLUS_MAINLINE_MAX77705_ROUTE_V1.md'
mxr_review_name = r's22plus_mainline_max77705_route_v[1-9][0-9]*_review[.]json'
if mxr_review is not None or mxr_policy.exists() or any((snapshot/bindings).glob('s22plus_mainline_max77705_route_v*_review.json')):
    terminal.require(type(mxr_review) is str and re.fullmatch(mxr_review_name, Path(mxr_review).name),
                     'proposed MAX77705 route review selection differs')
    routes.append(('MAX77705 route', mxr_review, {'image': {'schema': task.profile.MXR_SCHEMA},
                                                 'ordinary_cue': True}))

gateway_path = gateway_file.relative_to(snapshot)
reviews = {gateway_path}
paths = {selector_path, gateway_path}
paths.update(Path(row['path']).relative_to(snapshot) for key in ('sources', 'worker_sources')
             for row in gateway[key])
for name, expected, options in routes:
    review = Path(expected)
    terminal.require(review.parent == bindings and review not in reviews,
                     f'proposed {name} review path differs')
    for recovery in (False, True):
        selected = task.capability(snapshot, recovery=recovery, **options)
        terminal.require(Path(selected['path']) == snapshot/review, f'proposed {name} review selection differs')
    reviews.add(review)
    paths.add(review)
    paths.update(Path(row['path']) for row in task.read(snapshot/review)['sources'])
print(json.dumps(dict(paths=sorted(map(str, paths)), reviews=sorted(map(str, reviews)))))
"""


def git_argv(root, *args):
    return ['git', '--no-replace-objects', '--literal-pathspecs', '-C', str(root), *args]


def git(root, *args):
    return subprocess.check_output(git_argv(root, *args), env=GIT_ENV)


def tree_entries(root, commit):
    data = git(root, 'ls-tree', '-rz', '--full-tree', commit, '--', *SOURCE_ROOTS)
    entries = {}
    for entry in data.split(b'\0'):
        if entry:
            header, name = entry.split(b'\t', 1)
            mode, kind, oid = header.split()
            entries[Path(os.fsdecode(name))] = mode, kind, oid
    return entries


def blobs(root, requests):
    # Read exact Git bytes without checkout filters, hooks or index writes.
    with subprocess.Popen(git_argv(root, 'cat-file', '--batch'), env=GIT_ENV,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
        for path, (mode, kind, oid) in requests.items():
            require(mode in (b'100644', b'100755') and kind == b'blob', f'nonregular source: {path}')
            process.stdin.write(oid+b'\n')
            process.stdin.flush()
            header = process.stdout.readline().split()
            require(len(header) == 3 and header[:2] == [oid, b'blob'], f'Git blob unavailable: {path}')
            size = int(header[2])
            data = process.stdout.read(size)
            require(len(data) == size and process.stdout.read(1) == b'\n', f'incomplete Git blob: {path}')
            yield path, data
        process.stdin.close()
        require(process.wait() == 0, 'could not read proposal Git blobs')


def production_check(root, source, *args):
    checked = subprocess.run(
        [sys.executable, '-I', '-B', '-c', source, str(root), *map(str, args)],
        cwd=root, capture_output=True, text=True, timeout=30)
    if checked.returncode:
        reason = checked.stderr.strip().splitlines()[-1:] or ['no validator diagnostic']
        raise ValueError(f'production review validation failed: {reason[0]}')
    return json.loads(checked.stdout)


def validate_proposed_tree(root, entries):
    with TemporaryDirectory(prefix='s22-cue-proposal-') as folder:
        snapshot = Path(folder).resolve()
        for relative, data in blobs(root, entries):
            dest = snapshot/relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            if entries[relative][0] == b'100755':
                dest.chmod(0o755)
        checked = production_check(snapshot, PRODUCTION_CHECK, root, SELECTOR)
        paths = [Path(path) for path in checked['paths']]
        require(all(path in entries for path in paths), 'proposed review pin is outside the Git snapshot')
        return paths, [Path(path) for path in checked['reviews']]


def require_worktree_sources(root, current, paths, reviews):
    base = tree_entries(root, current)
    require(not set(reviews).intersection(base), 'adoption must select new review records')
    tracked = {path: base[path] for path in paths if path in base}
    for path, original in blobs(root, tracked):
        require(read_bytes(root/path) == original, f'operating source differs from HEAD: {path}')
    for path in paths:
        if path not in tracked:
            local = root/path
            require(local.resolve() == local and not local.exists() and not local.is_symlink(),
                    f'new successor path already exists or is indirect: {path}')
    index = subprocess.run(git_argv(root, 'diff', '--cached', '--quiet', '--no-ext-diff', '--no-textconv',
                                   current, '--', *map(str, paths)), env=GIT_ENV)
    require(index.returncode == 0, 'operating index differs from HEAD at a successor path')


def require_adoption_commit(root, candidate):
    current = git(root, 'rev-parse', 'HEAD').decode().strip()
    proposed = git(root, 'rev-parse', '--verify', '--end-of-options', candidate+'^{commit}').decode().strip()
    line = git(root, 'rev-list', '--parents', '-n', '1', proposed).decode().split()
    require(line == [proposed, current], 'adoption must be a single squash commit on the operating HEAD')

    paths, reviews = validate_proposed_tree(root, tree_entries(root, proposed))
    require_worktree_sources(root, current, paths, reviews)
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == current,
            'operating HEAD changed during proposal validation')
    return proposed


def private_walk(private):
    """Walk the private tree, failing closed on any directory the lab user owns but cannot list.

    Lab operation, task and grant records are always written by this uid. A
    directory owned by another uid that this uid can neither list, search nor
    write (rootless build trees mapped to subordinate uids) cannot hold them,
    and no production reader can reach anything beneath it, even by exact
    path, so it is skipped. A searchable directory is never skipped.
    Every other walk error still holds cutover."""
    uid = os.getuid()

    def unreadable(error):
        path = getattr(error, 'filename', None)
        try:
            info = os.lstat(path)
        except (OSError, TypeError, ValueError):
            raise error
        if (stat.S_ISDIR(info.st_mode) and info.st_uid != uid
                and not os.access(path, os.R_OK) and not os.access(path, os.W_OK)
                and not os.access(path, os.X_OK)):
            return
        raise error

    for folder, dirs, files in os.walk(private, onerror=unreadable):
        if '.git' in dirs:
            dirs.remove('.git')
        yield Path(folder), dirs, files


def loader_operations(private, review_path):
    for directory, dirs, files in private_walk(private):
        if not re.fullmatch(r'operation-[0-9]{4}', directory.name):
            continue
        if 'operation.json' not in files:
            task_path = directory.parent/'task.json'
            if task_path.is_file() and read(task_path)['review']['path'] == review_path:
                require(not {'journal', 'terminal.json', 'consumed.json'}.intersection(dirs+files),
                        'timing-v3 effect evidence lacks its operation.json')
            continue
        request = read(directory/'operation.json')
        if request.get('operation') == 'loader-android':
            require(request.get('schema') == SCHEMA, 'timing-v3 operation schema differs')
            yield directory, request


# Task closure schemas the reviewed task CLIs have written, each with its own
# raw-capture index name. Every other closure field is checked identically.
# The first mainline schema named its evidence per run (for example
# ml001-raw-capture-index.json); it is checked by pin within the run folder.
CLOSURE_RAW_INDEX = {
    's22plus-comparison-task-closed-v1': 'raw-index.json',
    's22plus-comparison-task-closed-v2': 'raw-index-v2.json',
    's22plus-mainline-task-closed-v1': None,
}


def closure_made_no_device_action(closure):
    """The comparison closures record device_actions_by_closure; the first
    mainline closure schema predates that field and records f1_owner_absent."""
    if closure['schema'] == 's22plus-mainline-task-closed-v1':
        return 'device_actions_by_closure' not in closure and closure.get('f1_owner_absent') is True
    return closure.get('device_actions_by_closure') == 0


def require_comparison_close(directory, task, grant, operation, rows, tail):
    folder = directory.parent
    closed = folder/'closed.json'
    require(closed.is_file(), 'requires closed.json at task level before cutover')
    closure = read(closed)
    terminal = directory/'terminal.json'
    final = read(terminal)
    android_writes = [row for row in rows if row['event'] == 'effect-intent' and
                      row['data'].get('action') == 'transfer' and row['data'].get('role') == 'A']
    require(closure.get('schema') in CLOSURE_RAW_INDEX and
            closure['task'] == pin(folder/'task.json') and closure['grant'] == grant and
            closure['operation'] == operation and closure['source_binding'] == task['review'] and
            closure['current_android_terminal'] == pin(terminal) and
            final['schema'] == SCHEMA and final['operation_sha256'] == operation['sha256'] and
            final['grant'] == grant and final['research_closed'] is True and
            closure['terminal_state'] == final['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and
            closure['journal_rows'] == len(rows) and closure['journal_tail'] == tail and
            closure['original_A_transfers_total'] == len(android_writes) == 1 and
            closure_made_no_device_action(closure),
            'task closure does not bind its healthy original-A operation')
    raw_index = CLOSURE_RAW_INDEX[closure['schema']]
    if raw_index is None:
        run = folder.parent.resolve(strict=True)
        for key in ('source_snapshot', 'raw_captures', 'canonical_timeline'):
            receipt = closure[key]
            require(type(receipt) is dict and Path(receipt['path']).resolve(strict=True).is_relative_to(run),
                    f'task closure {key} is outside its run folder')
            verify(receipt)
        return
    for key, filename in (('source_snapshot', 'source-snapshot.json'), ('raw_captures', raw_index),
                          ('canonical_timeline', 'timeline.json')):
        require(closure[key] == pin(folder/filename), f'task closure lacks its {filename}')


def mainline_task(value):
    require(type(value) is dict, 'task record must be an object')
    image = value.get('N')
    profile_name = image.get('profile') if type(image) is dict else None
    if profile_name != 'mainline-ram-v1' and value.get('operations') != ['mainline-ram']:
        return False
    require(type(image) is dict, 'mainline task image metadata is absent')
    profile = selected_profile(image)
    require(profile.OPERATION == 'mainline-ram' and value['operations'] == [profile.OPERATION] and
            value['schema'] == profile.TASK_SCHEMA, 'mainline task profile or schema differs')
    return True


def mainline_operation_closed(root, directory, task, task_pin, grant_pin):
    private_path(root, directory)
    operation = pin(directory/'operation.json')
    request = read(directory/'operation.json')
    require(request['schema'] == SCHEMA and request['operation'] == 'mainline-ram' and
            request['task'] == task_pin and request['grant'] == grant_pin and
            request.get('prior_terminal') is None, 'operation does not bind the original task and grant')
    # Session's journal constructor can create a directory. Only use it
    # where the original owner's journal already exists.
    private_path(root, directory/'journal')
    require((directory/'journal').is_dir(), 'operation journal is absent')
    session = Session(root, directory, None)
    if (directory/'unused.json').exists():
        require(session.unused() and not (directory/'terminal.json').exists(),
                'unused operation conflicts with terminal evidence')
        return False
    rows = session.rows()
    tail = pin(directory/'journal'/f'{len(rows)-1:04d}.json') if rows else None
    require_comparison_close(directory, task, grant_pin, operation, rows, tail)
    return True


def nested_fixture(private, folder, request):
    """A test fixture repository nested inside the private tree, not an operation of this checkout.

    Requires positive fixture evidence, because the production CLI also permits
    a nested layout: the folder sits beneath a nested `workspace/private`, the
    operation's grant path points inside that same nested root, and neither the
    operation nor its grant binds a task. Every production operation and grant
    binds its task, so a production operation whose task.json went missing
    still holds cutover."""
    if 'task' in request:
        return False
    relative = folder.relative_to(private).parts
    for index in range(len(relative) - 1):
        if relative[index:index + 2] == ('workspace', 'private'):
            nested = private.joinpath(*relative[:index + 2])
            grant = request.get('grant')
            path = grant.get('path') if isinstance(grant, dict) else None
            if not (isinstance(path, str) and Path(path).is_relative_to(nested)):
                return False
            try:
                value = read(Path(path))
            except (OSError, ValueError):
                return False
            return type(value) is dict and 'task' not in value
    return False


def require_mainline_quiescence(root, gateway_receipt):
    """Read the old owners' lifecycle facts without requalifying any image."""
    blockers = []
    closed_tasks = set()
    private = private_path(root, root/'workspace/private')
    errors = (OSError, ValueError, KeyError, TypeError)
    for folder, dirs, files in private_walk(private):
        operations = sorted(name for name in dirs+files if name.startswith('operation-'))
        if (re.fullmatch(r'operation-[0-9]{4}', folder.name) and 'operation.json' in files and
                not (folder.parent/'task.json').is_file()):
            try:
                request = read(folder/'operation.json')
                require(type(request) is dict, 'operation record must be an object')
                if request.get('operation') == 'mainline-ram' and not nested_fixture(private, folder, request):
                    blockers.append(f'{folder.relative_to(root)}: mainline operation lacks task.json')
            except errors as error:
                blockers.append(f'{folder.relative_to(root)}: cannot verify orphan operation ({error})')
        if 'task.json' not in files or ('grant.json' not in files and not operations):
            continue
        label = folder.relative_to(root)
        try:
            task = read(folder/'task.json')
            if not mainline_task(task):
                continue
            task_pin = pin(folder/'task.json')
            grant_pin = pin(folder/'grant.json')
            grant = read(folder/'grant.json')
            require(grant['schema'] == SCHEMA and grant['task'] == task_pin and
                    grant['directory'] == str(folder) and type(grant['host_boot']) is str and grant['host_boot'],
                    'grant does not bind the original mainline task')
            grant_open = grant['host_boot'] == host_boot()
            if grant_open:
                live_grant(grant, recovery=True)
                grant_open = clock() < grant['deadline_ns']
        except errors as error:
            blockers.append(f'{label}: cannot verify task or grant ({error})')
            continue
        task_closed = False
        for name in operations:
            try:
                task_closed |= mainline_operation_closed(root, folder/name, task, task_pin, grant_pin)
            except errors as error:
                blockers.append(f'{label}/{name}: unclosed operation ({error})')
        if task_closed:
            closed_tasks.add(folder)
        if grant_open and not task_closed:
            blockers.append(f'{label}/grant.json: open grant')

    # The gateway receipt was selected on the operating root before this
    # inventory. Its controller now reads the original bundle/dispatch only.
    controller = Controller(root, bridge_check=lambda _: gateway_receipt)
    for approval in sorted(controller.outputs.glob('*/operator-approval.json')):
        base = approval.parent
        if not ((base/'connector-preparation.json').exists() or (base/'task-1/task.json').exists()):
            continue
        label = base.relative_to(root)
        try:
            if not mainline_task(read(base/'task-1/task.json')):
                continue
            try:
                bound = controller.bundle(str(base), approval=True)
            except errors as error:
                # An approval written in an earlier format: accept it only when
                # its task was verified closed above and the original owner
                # closed its dispatch. Anything else still holds cutover.
                if ((base/'task-1') in closed_tasks and
                        controller.dispatch_state(base)['state'] == 'CLOSED_BY_ORIGINAL_OWNER'):
                    intent = read(base/DISPATCH/'intent.json')
                    require(intent['task'] == pin(base/'task-1/task.json') and
                            intent['approval'] == pin(approval),
                            'closed dispatch does not consume this task and approval')
                    continue
                raise error
            state = controller.dispatch_state(base)['state']
            if state == 'NOT_DISPATCHED':
                blockers.append(f'{label}/operator-approval.json: staged unconsumed approval')
                continue
            intent = read(base/DISPATCH/'intent.json')
            require(intent['task'] == bound['task'] and intent['approval'] == bound['approval'],
                    'dispatch does not consume the original task approval')
            if state != 'CLOSED_BY_ORIGINAL_OWNER':
                blockers.append(f'{label}/{DISPATCH}: unclosed dispatch ({state})')
        except errors as error:
            blockers.append(f'{label}/operator-approval.json: cannot verify approval or dispatch ({error})')
    require(not blockers, 'mainline tasks must be quiescent before cutover:\n'+'\n'.join(sorted(blockers)))


def require_task_closures(root, review_path=OLD_LOADER):
    require_no_f1_owner(root)
    private = private_path(root, root/'workspace/private')
    require(review_path.parent == BINDINGS, 'operating loader review is outside bindings')
    old_review = pin(root/review_path)
    review = read(root/review_path)
    require(review['schema'] == 's22plus-loader-android-review-v1' and
            review['scope'] == 'LOADER_ANDROID_F1_CAPABILITY' and
            review['verdict'] == 'PASS_GO' and review['findings'] == [],
            'run the cutover check while the original timing-v3 review is usable')
    for receipt in review['sources']:
        relative = Path(receipt['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'original review source path is indirect')
        source = root/relative
        require(pin(source) == dict(receipt, path=str(source)),
                'original timing-v3 review source differs')

    closed_count = 0
    for directory, request in loader_operations(private, old_review['path']):
        folder = directory.parent
        task = read(folder/'task.json')
        if task['review']['path'] != old_review['path']:
            continue
        task_pin = pin(folder/'task.json')
        grant_pin = pin(folder/'grant.json')
        grant = read(folder/'grant.json')
        require(task['review'] == old_review and request['task'] == grant['task'] == task_pin and
                request['grant'] == grant_pin and grant['directory'] == str(folder) and
                request.get('prior_terminal') is None, 'original timing-v3 task ownership differs')
        journal = directory/'journal'
        flags = ('terminal.json', 'consumed.json')
        possibly_used = any((directory/name).exists() for name in flags)
        if not journal.exists() and not possibly_used:
            continue
        require(journal.is_dir(), 'timing-v3 operation lacks its journal')
        private_path(root, journal)
        rows = Journal(journal).rows()
        effects = any(row['event'] == 'effect-intent' for row in rows)
        terminal = directory/'terminal.json'
        tail = pin(journal/f'{len(rows)-1:04d}.json') if rows else None
        operation = pin(directory/'operation.json')
        if not effects and not terminal.exists():
            if possibly_used:
                require(read(directory/'unused.json') == dict(
                    schema=SCHEMA, operation_sha256=operation['sha256'],
                    journal_rows=len(rows), journal_tail=tail),
                    'charged timing-v3 operation lacks its matching unused closure')
            continue

        try:
            require_comparison_close(directory, task, grant_pin, operation, rows, tail)
        except (ValueError, OSError, KeyError, TypeError) as error:
            raise ValueError(f'timing-v3 task {folder.relative_to(root)}: {error}') from error
        closed_count += 1
    return closed_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operating-root', type=Path, required=True)
    parser.add_argument('--adoption-commit', required=True)
    args = parser.parse_args()
    root = args.operating_root.resolve(strict=True)
    try:
        _, gateway_receipt = selected_review(root)
        require_mainline_quiescence(root, gateway_receipt)
        commit = require_adoption_commit(root, args.adoption_commit)
        retiring_loader = Path(production_check(root, OPERATING_LOADER_CHECK))
        count = require_task_closures(root, retiring_loader)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Cutover held. {error}\n')
    print(json.dumps({'adoption_commit': commit, 'old_timing_v3_tasks_closed': count}))


if __name__ == '__main__':
    main()
