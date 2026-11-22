"""H0 checks for the terminal, timing-v3 and ordinary SCM source subjects."""
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

# These entry points are independent of the runtime declarations being tested.
# Shared multi-profile dispatchers have lazy branches for other operations.
# The selected downstream entries below trace the applicable lazy imports.
COMMON_ENTRIES = ('s22plus_mainline_task_v1', 's22plus_native_adapter_v3',
                  's22plus_mainline_attach_cue_v1')
TIMING_ENTRIES = ('s22plus_loader_android_session_v1', 's22plus_loader_android_access_v1',
                  's22plus_loader_android_profile_v1', 's22plus_loader_prefix_v1')
SCM_ENTRIES = ('s22plus_mainline_session_v1', 's22plus_mainline_scm_v1', 's22plus_mainline_access_v1')
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


def import_nodes(tree, *, lazy):
    todo = deque([tree])
    while todo:
        node = todo.popleft()
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            yield node
        elif lazy or not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            todo.extend(ast.iter_child_nodes(node))


def source_imports(path, *, lazy):
    tree = ast.parse(path.read_bytes(), filename=str(path))
    for node in import_nodes(tree, lazy=lazy):
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


def traced_sources(pinned, entries, *, timed, lazy_entries):
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
        todo.extend(source_imports(path, lazy=path in lazy))
    return seen


class CueReviewTests(unittest.TestCase):
    def setUp(self):
        self.selector = json.loads((ROOT/terminal.SELECTOR).read_bytes())
        selected = Path(self.selector['review']['path'])
        self.assertIsNotNone(re.fullmatch(r's22plus_approved_terminal_persistent_v[0-9]+_review\.json', selected.name))
        self.gateway = BINDINGS/selected.name
        self.deployment = selected.parents[len(self.gateway.parts)-1]
        self.records = {path: json.loads((ROOT/path).read_bytes()) for path in (self.gateway, LOADER, SCM)}

    def test_each_draft_binds_the_imported_and_declared_sources(self):
        gateway_sources = [dict(terminal.pin(path), path=str(self.deployment/path.relative_to(ROOT)))
                           for path in backend.review_sources(ROOT)]
        loader_sources = task.source_pins(ROOT, loader)
        scm_sources = task.source_pins(ROOT, image=SCM_IMAGE, ordinary_cue=True)
        for record, expected, entries, timed, lazy_entries in (
            (self.gateway, gateway_sources, COMMON_ENTRIES+TERMINAL_ENTRIES+TIMING_ENTRIES+SCM_ENTRIES, True,
             TIMING_ENTRIES+SCM_ENTRIES+TERMINAL_LAZY_ENTRIES),
            (LOADER, loader_sources, COMMON_ENTRIES+TIMING_ENTRIES, True,
             TIMING_ENTRIES+('s22plus_mainline_attach_cue_v1',)),
            (SCM, scm_sources, COMMON_ENTRIES+SCM_ENTRIES, False,
             SCM_ENTRIES+('s22plus_mainline_attach_cue_v1',)),
        ):
            with self.subTest(record=record.name):
                rows = self.records[record]['sources']
                self.assertEqual(rows, expected)
                pinned = {ROOT/Path(row['path']).relative_to(self.deployment)
                          if Path(row['path']).is_absolute() else ROOT/row['path'] for row in rows}
                missing = traced_sources(pinned, entries, timed=timed, lazy_entries=lazy_entries)-pinned
                self.assertEqual(sorted(str(path.relative_to(ROOT)) for path in missing), [])

    def test_pending_rejects_and_complete_adoption_verifies_together(self):
        self.assertEqual(self.selector['review'],
                         dict(terminal.pin(ROOT/self.gateway), path=str(self.deployment/self.gateway)))
        verdicts = {record['verdict'] for record in self.records.values()}
        self.assertIn(verdicts, ({'PENDING_INDEPENDENT_REVIEW'}, {'PASS_GO'}))
        self.assertTrue(all(bool(record['reviewer']) == (verdicts == {'PASS_GO'})
                            for record in self.records.values()))
        with tempfile.TemporaryDirectory(prefix='cue-review-') as folder:
            root = Path(folder)
            for record in self.records.values():
                for row in record['sources']+record.get('worker_sources', []):
                    stored = Path(row['path'])
                    relative = stored.relative_to(self.deployment) if stored.is_absolute() else stored
                    local = root/relative
                    local.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT/relative, local)
                    if stored.is_absolute():
                        row['path'] = str(local)

            def write_fixture(*, approved=False):
                (root/BINDINGS).mkdir(parents=True, exist_ok=True)
                for path, record in self.records.items():
                    value = dict(record, verdict='PASS_GO' if approved else 'PENDING_INDEPENDENT_REVIEW',
                                 reviewer='Synthetic H0 fixture' if approved else '')
                    (root/path).write_bytes(terminal.canonical(value))
                selector = dict(self.selector, review=terminal.pin(root/self.gateway))
                (root/terminal.SELECTOR).write_bytes(terminal.canonical(selector))

            def task_reviews(recovery):
                return (
                    lambda: task.capability(root, selected=loader, recovery=recovery),
                    lambda: task.capability(root, image=SCM_IMAGE, ordinary_cue=True, recovery=recovery),
                )

            write_fixture()
            with self.assertRaisesRegex(ValueError, 'not PASS_GO'):
                backend.verify_bridge(root)
            for recovery in (False, True):
                for verify in task_reviews(recovery):
                    with self.assertRaisesRegex(ValueError, 'not PASS_GO'):
                        verify()

            write_fixture(approved=True)
            self.assertEqual(backend.verify_bridge(root), terminal.pin(root/self.gateway))
            for recovery in (False, True):
                for verify, receipt in zip(task_reviews(recovery), (LOADER, SCM)):
                    self.assertEqual(verify(), terminal.pin(root/receipt))

            # The loader's eager storage dependency must still be checked when
            # reopening an original owner for recovery.
            storage = root/'workspace/public/src/scripts/revalidation/s22plus_native_android_storage_v1.py'
            storage.write_bytes(storage.read_bytes()+b'\n')
            with self.assertRaises(ValueError):
                backend.verify_bridge(root)
            with self.assertRaises(ValueError):
                task.capability(root, selected=loader, recovery=True)
