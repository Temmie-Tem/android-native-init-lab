#!/usr/bin/env python3
"""P341: exact P340 packaging reuse with the reviewed host-first runtime.

The Image identity transform preserves layout; /init changes behavior. No
device tool is invoked. Existing output directories are never overwritten.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / 'workspace/public/src/scripts/revalidation'
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import s22plus_fyg8_p341_artifact_identity as artifact
import s22plus_fyg8_p341_open_read_branch_runtime as runtime
import s22plus_fyg8_p341_open_read_branch_acm_observer as observer

TEMPLATE = ANALYSIS / 's22plus_fyg8_p340_stock_candidate_build.py'
TEMPLATE_IDENTITY = {'size': 33081, 'sha256': '2f4d4279359008821ac5a390c8c62a22177a25d5a049a7fa00141d3d77caf7f8'}


def identity(value: bytes):
    return {'size': len(value), 'sha256': hashlib.sha256(value).hexdigest()}


payload = TEMPLATE.read_bytes()
if identity(payload) != TEMPLATE_IDENTITY:
    raise RuntimeError('P341 packaging template identity differs')
# Mechanical namespace substitution is explicit and byte-pinned, not a
# mutation of the imported predecessor or its defaults.
source = payload.decode().replace('P340', 'NEXT_UPPER').replace('p340', 'next_lower').replace('P3.40', 'NEXT_DOT')
source = source.replace('P339', 'P340').replace('p339', 'p340').replace('P3.39', 'P3.40')
source = source.replace('NEXT_UPPER', 'P341').replace('next_lower', 'p341').replace('NEXT_DOT', 'P3.41')


def replace_once(old: str, new: str) -> None:
    global source
    if source.count(old) != 1:
        raise RuntimeError('P341 packaging semantic anchor differs')
    source = source.replace(old, new, 1)


replace_once('s22plus_fyg8_p340/stock-candidate-build-v1-20260905-04',
             's22plus_fyg8_p340/stock-candidate-build-v1-20260905-01')
replace_once('"PASS_P341_STOCK_CANDIDATE_BUILD_H0_IDENTITY_ONLY"',
             '"PASS_P341_STOCK_CANDIDATE_BUILD_H0_HOST_FIRST_OPEN"')
replace_once('"IMPLEMENTED_H0_IDENTITY_ONLY_REVIEW_PENDING"',
             '"IMPLEMENTED_H0_HOST_FIRST_OPEN_REVIEW_PENDING"')
replace_once('"runtime_delta_identity_only": True', '"runtime_delta_identity_only": False, "host_first_open": True')
replace_once('"s22plus-fyg8-p341-open-header-capture-acm-observer-v1"', repr(observer.CONTRACT_ID))
replace_once('P341 changes only the run-ID-bearing Image, fixed runtime command marker, and compiler-bound /init identity.',
             'P341 changes initial OPEN ordering and consumed-input handling in /init, plus fresh run identity; Image layout is preserved.')
replace_once('P340 stage-3 grammar=1, semantic=4, and four header-word diagnostics are unchanged.',
             'Existing diagnostic encoding is retained; no-input waits emit no unsolicited data and partial input is consumed.')
replace_once('P341 reuses the existing pinned P319 packaging helper and exact P340 -04 source closure.',
             'P341 reuses the existing pinned P319 packaging helper and exact P340 -01 source closure.')
# Retain the shared transform in copied build inputs as well as current
# execution closure. It is not merely a prose statement in the result.
replace_once('("p341-adapter.py", P341_ADAPTER_SOURCE),',
             '("host-first-open.py", runtime.HOST_FIRST_SOURCE), ("p341-adapter.py", P341_ADAPTER_SOURCE),')
replace_once('result["runtime_transform"] = runtime_repair',
             'result["helper_sources"]["host-first-open.py"] = identity(runtime.HOST_FIRST_SOURCE.read_bytes())\n    result["runtime_transform"] = runtime_repair')

_engine = types.ModuleType('s22plus_fyg8_p341_bound_packager')
_engine.__file__ = str(Path(__file__).resolve())
exec(compile(source, str(TEMPLATE), 'exec', dont_inherit=True), _engine.__dict__)
# Exact retained predecessor; no current-source guess or regenerated history.
_engine.P340_RESULT_IDENTITY = {'size': 71170, 'sha256': 'f145ed1f55b78ad85b15d112e8c3d1849b792a6d6fbc3dc1435ea3c3404f8454'}
_engine.P340_BUILDER_IDENTITY = dict(TEMPLATE_IDENTITY)
_engine.DEFAULT_OUTPUT_ROOT = ROOT / 'workspace/private/outputs/s22plus_fyg8_p341/stock-candidate-build-v1-20260905-02'
DEFAULT_OUTPUT_ROOT = _engine.DEFAULT_OUTPUT_ROOT
SCHEMA, VERDICT, STATUS = _engine.SCHEMA, _engine.VERDICT, _engine.STATUS
AuditError = _engine.AuditError
TARGET = _engine.TARGET
P341_RUN_ID_HEX, P341_RUN_ID = runtime.P341_RUN_ID_HEX, runtime.P341_RUN_ID


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT):
    result = _engine.audit_existing(output_root)
    # Check what current scripts actually execute, not just copied metadata.
    current = {
        'p319_stock_candidate_build.py': _engine.P319_PACKAGER_SOURCE,
        'p340_stock_candidate_build.py': TEMPLATE,
        'p340_artifact_identity.py': _engine.P340_ARTIFACT_SOURCE,
        'p340_open_read_branch_runtime.py': _engine.P340_RUNTIME_SOURCE,
        'p340_open_read_branch_acm_observer.py': _engine.P340_OBSERVER_SOURCE,
        'p341_stock_candidate_build.py': Path(__file__).resolve(),
        'p341_artifact_identity.py': _engine.P341_ARTIFACT_SOURCE,
        'p341_open_read_branch_runtime.py': _engine.P341_RUNTIME_SOURCE,
        'p341_open_read_branch_acm_observer.py': _engine.P341_OBSERVER_SOURCE,
        'p341_stock_process_v2_adapter.py': _engine.P341_ADAPTER_SOURCE,
        'host-first-open.py': runtime.HOST_FIRST_SOURCE,
    }
    if set(result['helper_sources']) != set(current):
        raise AuditError('P341 helper source membership differs')
    for name, path in current.items():
        _engine._stable(path, 'P341 current helper', 2 << 20, result['helper_sources'][name])
    for name, expected in result['inputs'].items():
        _engine._stable(Path(output_root) / 'inputs' / name, 'P341 copied input', 128 << 20, expected, mode=0o400, nlink=1)
    return result


def build_result(output_root: Path = DEFAULT_OUTPUT_ROOT, *, audit_only: bool = False):
    if not audit_only:
        _engine._build_once(Path(output_root).absolute())
    return audit_existing(Path(output_root).absolute())


def __getattr__(name):
    return getattr(_engine, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_engine)))


if __name__ == '__main__':
    _engine.build_result = build_result
    raise SystemExit(_engine.main())
