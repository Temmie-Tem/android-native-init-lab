"""H0 checks for the terminal, timing-v3 and ordinary board source subjects."""
import ast
from collections import deque
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT/'workspace/public/src'
SCRIPTS = PUBLIC/'scripts'
SEARCH = [SCRIPTS/name for name in ('host_tools', 'revalidation', 'analysis')]
sys.path[:0] = [str(path) for path in SEARCH]
import s22plus_approved_terminal_persistent_v1 as terminal
import s22plus_approved_terminal_tasks_v1 as backend
import s22plus_loader_android_profile_v1 as loader
import s22plus_mainline_task_v1 as task


BINDINGS = Path(terminal.SELECTOR).parent
LOADER = Path(task.LOADER_CUE_REVIEW)
SCM = Path(task.profile.SCM_CUE_REVIEW)
SCM_IMAGE = {'schema': task.profile.SCM_SCHEMA}
MX = getattr(task.profile, 'MX_REVIEW', None)
BOARD_ROUTES = [(SCM, SCM_IMAGE, 'scm_board', 's22plus_mainline_scm_v1')]
if MX is not None:
    BOARD_ROUTES.append((Path(MX), {'schema': task.profile.MX_SCHEMA},
                         'max77705_board', 's22plus_mainline_max77705_v1'))
MXR = getattr(task.profile, 'MXR_REVIEW', None)
if MXR is not None:
    BOARD_ROUTES.append((Path(MXR), {'schema': task.profile.MXR_SCHEMA},
                         'max77705_route_board', 's22plus_mainline_max77705_route_v1'))
# Board reviews and whether their scope carries the ordinary cue.
CUE = {route[0]: True for route in BOARD_ROUTES}
MXT = getattr(task.profile, 'MXT_REVIEW', None)
if MXT is not None:
    BOARD_ROUTES.append((Path(MXT), {'schema': task.profile.MXT_SCHEMA},
                         'max77705_route_timer_board', 's22plus_mainline_max77705_route_timer_v1'))
    CUE[Path(MXT)] = False

# These entry points are independent of the runtime declarations being tested.
# Shared multi-profile dispatchers have lazy branches for other operations.
# The selected downstream entries below trace the applicable lazy imports.
COMMON_ENTRIES = ('s22plus_mainline_task_v1', 's22plus_native_adapter_v3',
                  's22plus_mainline_attach_cue_v1')
TIMING_ENTRIES = ('s22plus_loader_android_session_v1', 's22plus_loader_android_access_v1',
                  's22plus_loader_android_profile_v1', 's22plus_loader_prefix_v1')
BOARD_ENTRIES = ('s22plus_mainline_session_v1', 's22plus_mainline_access_v1')
TERMINAL_LAZY_ENTRIES = (
    's22plus_approved_terminal_persistent_v1', 's22plus_approved_terminal_tasks_v1',
    's22plus_mainline_terminal_v1', 's22plus_debian_autoboot_session_v1',
    's22plus_debian_autoboot_access_v1', 's22plus_debian_autoboot_qualification_v1',
)
TERMINAL_ENTRIES = TERMINAL_LAZY_ENTRIES + (
    's22plus_mainline_ufs_access_v1',
    's22plus_mainline_ufs_candidate_v2', 'mainline.s22plus_canary_h0.download_ram',
    'mainline.s22plus_canary_h0.service_ram', 'mainline.s22plus_canary_h0.ssh_ram',
    'mainline.s22plus_canary_h0.download_vm', 'mainline.s22plus_canary_h0.prepare',
    'mainline.s22plus_udc_observation_h0.decode',
    's22plus_debian_file_profile_v1', 's22plus_debian_apt_access_v1', 's22plus_debian_reboot_access_v1',
    's22plus_native_journal_recovery_h0', 's22plus_native_staged_preflight_evidence_v1',
    's22plus_journal_replay_tool_h0',
)

TRACE_IMPORTS = """
import importlib
import importlib.machinery
import json
from pathlib import Path
import sys

root = Path.cwd()
public = root/'workspace/public/src'
sys.path[:0] = [str(public/'scripts'/name) for name in ('host_tools', 'revalidation', 'analysis')]
sys.path.insert(3, str(public))
loaded = set()
original = importlib.machinery.SourceFileLoader.exec_module

def trace(self, module):
    path = Path(self.path).resolve()
    if path.is_relative_to(public):
        loaded.add(str(path.relative_to(root)))
    return original(self, module)

importlib.machinery.SourceFileLoader.exec_module = trace
timed, *entries = sys.argv[1:]
for name in entries:
    importlib.import_module(name)
if timed == 'yes':
    importlib.import_module('s22plus_loader_android_profile_v1').timing_codec()
print(json.dumps(sorted(loaded)))
"""


def local_module(name):
    parts = name.split('.')
    for directory in (*SEARCH, PUBLIC):
        path = directory.joinpath(*parts)
        for candidate in (path.with_suffix('.py'), path/'__init__.py'):
            if candidate.is_file():
                return candidate
    return None


def import_nodes(tree, *, lazy, boards):
    todo = deque([tree])
    while todo:
        node = todo.popleft()
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            yield node
        elif isinstance(node, ast.If) and isinstance(node.test, ast.Call) and (
                ast.unparse(node.test.func) in ('profile.scm_board', 'profile.max77705_board',
                                                'profile.max77705_route_board',
                                                'profile.max77705_route_timer_board')):
            # Candidate branches belong to their task route. Eager and
            # unconditional imports still count for the gateway.
            selected = node.test.func.attr in boards
            todo.extend(node.body if selected else node.orelse)
        elif lazy or not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            todo.extend(ast.iter_child_nodes(node))


def source_imports(path, *, lazy, boards):
    tree = ast.parse(path.read_bytes(), filename=str(path))
    for node in import_nodes(tree, lazy=lazy, boards=boards):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        else:
            prefix = list(path.relative_to(PUBLIC).parts[:-node.level]) if node.level else []
            base = '.'.join(prefix + ([node.module] if node.module else []))
            names = [base, *(f'{base}.{alias.name}' for alias in node.names)]
        for name in names:
            parts = name.split('.')
            for count in range(1, len(parts)+1):
                candidate = local_module('.'.join(parts[:count]))
                if candidate:
                    yield candidate


def traced_sources(pinned, entries, *, timed, lazy_entries, boards):
    process = subprocess.run(
        [sys.executable, '-I', '-B', '-c', TRACE_IMPORTS, 'yes' if timed else 'no', *entries],
        cwd=ROOT, capture_output=True, text=True, check=True, timeout=20,
    )
    runtime = {ROOT/path for path in json.loads(process.stdout)}
    # Follow eager imports of every bound source, including build-only Python
    # without running the builders. Scan lazy imports in the selected leaf
    # entries, and dynamically trace the timing codec's file-based load.
    lazy = {local_module(name) for name in lazy_entries}
    todo = list(lazy | runtime | pinned)
    seen = set()
    while todo:
        path = todo.pop()
        if path in seen or path.suffix != '.py':
            continue
        seen.add(path)
        todo.extend(source_imports(path, lazy=path in lazy, boards=boards))
    return seen


def _ufs_capability_only():
    closure = {str(path.relative_to(ROOT)) for path in task.source_paths(
        ROOT, image=dict(schema=task.IMAGE_V2), route=True, storage=True, write=True)}
    ufs = {path for path in closure if path.startswith('workspace/public/src/mainline/s22plus_ufs_link_h0/') or
           re.fullmatch(r'workspace/public/src/scripts/revalidation/s22plus_mainline_(ufs_[a-z_]+|series)_v[0-9]+\.py', path)}
    return {ROOT/path for path in ufs}


UFS_CAPABILITY_ONLY = _ufs_capability_only()


class CueReviewTests(unittest.TestCase):
    def setUp(self):
        self.selector = json.loads((ROOT/terminal.SELECTOR).read_bytes())
        selected = Path(self.selector['review']['path'])
        self.assertIsNotNone(re.fullmatch(r's22plus_approved_terminal_persistent_v[0-9]+_review\.json', selected.name))
        self.gateway = BINDINGS/selected.name
        self.deployment = selected.parents[len(self.gateway.parts)-1]
        paths = (self.gateway, LOADER, *(route[0] for route in BOARD_ROUTES))
        self.records = {path: json.loads((ROOT/path).read_bytes()) for path in paths}

    def test_each_draft_binds_the_imported_and_declared_sources(self):
        gateway_sources = [dict(terminal.pin(path), path=str(self.deployment/path.relative_to(ROOT)))
                           for path in backend.review_sources(ROOT)]
        loader_sources = task.source_pins(ROOT, loader)
        scopes = [
            (self.gateway, gateway_sources, COMMON_ENTRIES+TERMINAL_ENTRIES+TIMING_ENTRIES+BOARD_ENTRIES,
             True, TIMING_ENTRIES+BOARD_ENTRIES+TERMINAL_LAZY_ENTRIES, ()),
            (LOADER, loader_sources, COMMON_ENTRIES+TIMING_ENTRIES, True,
             TIMING_ENTRIES+('s22plus_mainline_attach_cue_v1',), ()),
        ]
        for record, image, board, module in BOARD_ROUTES:
            entries = BOARD_ENTRIES+(module,)
            scopes.append((record, task.source_pins(ROOT, image=image, ordinary_cue=CUE[record]),
                           COMMON_ENTRIES+entries, False,
                           entries+(('s22plus_mainline_attach_cue_v1',) if CUE[record] else ()), (board,)))
        for record, expected, entries, timed, lazy_entries, boards in scopes:
            with self.subTest(record=record.name):
                rows = self.records[record]['sources']
                self.assertEqual(rows, expected)
                pinned = {ROOT/Path(row['path']).relative_to(self.deployment)
                          if Path(row['path']).is_absolute() else ROOT/row['path'] for row in rows}
                missing = traced_sources(pinned, entries, timed=timed, lazy_entries=lazy_entries, boards=boards)-pinned
                # The UFS host decoder and candidate validator are lazy UFS-image imports
                # bound only by the UFS capability closure (never by these receipts), so a
                # new report version re-reviews only that capability.
                missing -= UFS_CAPABILITY_ONLY
                self.assertEqual(sorted(str(path.relative_to(ROOT)) for path in missing), [])

    def copy_fixture_sources(self, root):
        for record in self.records.values():
            for row in record['sources']+record.get('worker_sources', []):
                stored = Path(row['path'])
                relative = stored.relative_to(self.deployment) if stored.is_absolute() else stored
                local = root/relative
                local.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/relative, local)

    def write_fixture_reviews(self, root, *, approved=False):
        (root/BINDINGS).mkdir(parents=True, exist_ok=True)
        for path, record in self.records.items():
            value = dict(record, verdict='PASS_GO' if approved else 'PENDING_INDEPENDENT_REVIEW',
                         reviewer='Synthetic H0 fixture' if approved else '')
            if path == self.gateway:
                for key in ('sources', 'worker_sources'):
                    value[key] = [terminal.pin(root/Path(row['path']).relative_to(self.deployment))
                                  for row in record[key]]
            (root/path).write_bytes(terminal.canonical(value))
        selector = dict(self.selector, review=terminal.pin(root/self.gateway))
        (root/terminal.SELECTOR).write_bytes(terminal.canonical(selector))

    def test_pending_rejects_and_complete_adoption_verifies_together(self):
        self.assertEqual(self.selector['review'],
                         dict(terminal.pin(ROOT/self.gateway), path=str(self.deployment/self.gateway)))
        verdicts = {record['verdict'] for record in self.records.values()}
        self.assertIn(verdicts, ({'PENDING_INDEPENDENT_REVIEW'}, {'PASS_GO'}))
        self.assertTrue(all(bool(record['reviewer']) == (verdicts == {'PASS_GO'})
                            for record in self.records.values()))
        with tempfile.TemporaryDirectory(prefix='cue-review-') as folder:
            root = Path(folder)
            self.copy_fixture_sources(root)

            def task_reviews(recovery):
                yield LOADER, {'selected': loader, 'recovery': recovery}
                for record, image, _, _ in BOARD_ROUTES:
                    yield record, {'image': image, 'ordinary_cue': CUE[record], 'recovery': recovery}

            self.write_fixture_reviews(root)
            with self.assertRaisesRegex(ValueError, 'not PASS_GO'):
                backend.verify_bridge(root)
            for recovery in (False, True):
                for _, options in task_reviews(recovery):
                    with self.assertRaisesRegex(ValueError, 'not PASS_GO'):
                        task.capability(root, **options)

            self.write_fixture_reviews(root, approved=True)
            self.assertEqual(backend.verify_bridge(root), terminal.pin(root/self.gateway))
            for recovery in (False, True):
                for receipt, options in task_reviews(recovery):
                    self.assertEqual(task.capability(root, **options), terminal.pin(root/receipt))

            # The loader's eager storage dependency must still be checked when
            # reopening an original owner for recovery.
            storage = root/'workspace/public/src/scripts/revalidation/s22plus_native_android_storage_v1.py'
            storage.write_bytes(storage.read_bytes()+b'\n')
            with self.assertRaises(ValueError):
                backend.verify_bridge(root)
            with self.assertRaises(ValueError):
                task.capability(root, selected=loader, recovery=True)

    def test_original_owner_dispatch_does_not_need_candidate_board_modules(self):
        with tempfile.TemporaryDirectory(prefix='cue-recovery-') as folder:
            root = Path(folder)
            self.copy_fixture_sources(root)
            (root/'workspace/private').mkdir()
            entry = root/terminal.BACKEND
            source = entry.read_text()
            invocation = "if __name__ == '__main__': main()"
            self.assertIn(invocation, source)
            # Keep the real frame, selector, backend verification and tool
            # dispatch. Stop at the continuation handler before any live work.
            shim = """
UID = os.getuid()
nnp = lambda: 0
Controller.continue_task = lambda self, directory, tool: dict(dispatched=tool, directory=directory)
"""
            entry.write_text(source.replace(invocation, shim+'\n'+invocation))
            self.write_fixture_reviews(root, approved=True)
            gateway = terminal.Gateway(root)

            for receipt, image, _, module in BOARD_ROUTES:
                local = root/local_module(module).relative_to(ROOT)
                with self.subTest(module=module):
                    self.assertEqual(task.capability(root, image=image, ordinary_cue=CUE[receipt]),
                                     terminal.pin(root/receipt))
                    local.unlink()
                    with self.assertRaises(FileNotFoundError) as missing:
                        task.capability(root, image=image, ordinary_cue=CUE[receipt])
                    self.assertEqual(Path(missing.exception.filename).name, local.name)
                    self.assertEqual(task.capability(root, image=image, ordinary_cue=CUE[receipt], recovery=True),
                                     terminal.pin(root/receipt))

            self.assertEqual(task.capability(root, selected=loader, recovery=True), terminal.pin(root/LOADER))
            preparation = str(root/'workspace/private/outputs/s22plus-recovery-fixture-h0-20261122-1')
            for tool in ('recover_approved_task', 'resume_approved_health'):
                with self.subTest(tool=tool):
                    self.assertEqual(gateway.call(tool, {'preparation_directory': preparation}),
                                     {'dispatched': tool, 'directory': preparation})
