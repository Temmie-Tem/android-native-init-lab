#!/usr/bin/env python3
"""Typed observation contracts for Device Action Process v2."""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import os
import re
import stat
import sys
import types
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any, Callable


def _stable_local_import_bytes(path: Path) -> bytes:
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"stable local module is indirect: {path.name}")
        with path.open("rb") as stream:
            data = stream.read(2 * 1024 * 1024 + 1)
            inside = os.fstat(stream.fileno())
        after = path.lstat()
    except OSError as exc:
        raise RuntimeError(f"stable local module is unavailable: {path.name}") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if (
        before_id
        != (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
        or before_id
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or len(data) != before.st_size
        or len(data) > 2 * 1024 * 1024
    ):
        raise RuntimeError(f"stable local module changed while reading: {path.name}")
    return data


def _stable_local_import_closure(
    root_name: str, directory: Path
) -> dict[str, bytes]:
    pending = [root_name]
    payloads: dict[str, bytes] = {}
    while pending:
        name = pending.pop()
        if name in payloads:
            continue
        path = directory / f"{name}.py"
        payload = _stable_local_import_bytes(path)
        try:
            tree = ast.parse(payload, filename=str(path))
        except SyntaxError as exc:
            raise RuntimeError(f"stable local module is unparseable: {name}") from exc
        payloads[name] = payload
        dependencies: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                dependencies.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                dependencies.add(node.module.split(".", 1)[0])
        pending.extend(
            dependency
            for dependency in sorted(dependencies, reverse=True)
            if (directory / f"{dependency}.py").is_file()
        )
    return payloads


class _StableLocalImportLoader(importlib.abc.Loader):
    def __init__(self, name: str, directory: Path, payloads: dict[str, bytes]):
        self.name = name
        self.directory = directory
        self.payloads = payloads

    def create_module(self, spec: Any) -> None:
        return None

    def exec_module(self, module: types.ModuleType) -> None:
        path = self.directory / f"{self.name}.py"
        module.__file__ = str(path)
        module.__package__ = ""
        exec(
            compile(self.payloads[self.name], str(path), "exec", dont_inherit=True),
            module.__dict__,
        )


class _StableLocalImportFinder(importlib.abc.MetaPathFinder):
    def __init__(self, directory: Path, payloads: dict[str, bytes]):
        self.directory = directory
        self.payloads = payloads

    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
        del path, target
        if fullname not in self.payloads:
            return None
        return importlib.util.spec_from_loader(
            fullname,
            _StableLocalImportLoader(fullname, self.directory, self.payloads),
            origin=str(self.directory / f"{fullname}.py"),
        )


def _load_stable_local_module(
    root_name: str, directory: Path | None = None
) -> types.ModuleType:
    source_dir = Path(__file__).resolve().parent if directory is None else directory
    payloads = _stable_local_import_closure(root_name, source_dir)
    prior = {name: sys.modules.get(name) for name in payloads}
    for name in payloads:
        sys.modules.pop(name, None)
    finder = _StableLocalImportFinder(source_dir, payloads)
    sys.meta_path.insert(0, finder)
    try:
        module = importlib.import_module(root_name)
    finally:
        sys.meta_path.remove(finder)
        for name, previous in prior.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    for name, payload in payloads.items():
        if _stable_local_import_bytes(source_dir / f"{name}.py") != payload:
            raise RuntimeError(f"stable local module changed after import: {name}")
    return module

import s22plus_fyg8_r4w1e_checkpoint_contract as checkpoint
import s22plus_fyg8_p219_same_ring_decoder as same_ring
import s22plus_fyg8_p230_same_ring_multiboot_decoder as same_ring_multiboot
import s22plus_fyg8_p233_e1_decoder as e1_latest_stage
import s22plus_fyg8_p242_e2_stock_closure as e2_closure
import s22plus_fyg8_p253_e2_stock_closure as e2_closure_selector
import s22plus_fyg8_p286_e2_stock_closure as p286_e2_closure
import s22plus_fyg8_p286_source_contracts as source_contracts
import s22plus_fyg8_p288_e2_stock_closure as p288_e2_closure
import s22plus_fyg8_p290_e2_stock_closure as p290_e2_closure
import s22plus_fyg8_p292_e2_stock_closure as p292_e2_closure
import s22plus_fyg8_p294_e2_stock_closure as p294_e2_closure
import s22plus_fyg8_p296_e2_stock_closure as p296_e2_closure
import s22plus_fyg8_p298_e2_stock_closure as p298_e2_closure
import s22plus_fyg8_p298_identity_tiers as p298_identity
import s22plus_fyg8_p300_e2_stock_closure as p300_e2_closure
import s22plus_fyg8_p300_source_contract as p300_source_contract
import s22plus_fyg8_p301_overlay_contract as p301_overlay
import s22plus_fyg8_p301_telemetry_decoder as p301_decoder
import s22plus_fyg8_p302_overlay_contract as p302_overlay
import s22plus_fyg8_p303_overlay_contract as p303_overlay
import s22plus_fyg8_p303_stock_log_baseline_binding as p303_stock_binding
import s22plus_fyg8_p303_telemetry_decoder as p303_decoder
import s22plus_fyg8_p304_e2_stock_closure as p304_e2_closure
import s22plus_fyg8_p304_overlay_contract as p304_overlay
import s22plus_fyg8_p305_overlay_contract as p305_overlay
import s22plus_fyg8_p306_overlay_contract as p306_overlay
import s22plus_fyg8_p306_telemetry_decoder as p306_decoder
import s22plus_fyg8_p307_overlay_contract as p307_overlay
import s22plus_fyg8_p307_telemetry_decoder as p307_decoder
import s22plus_fyg8_p307_telemetry_spec as p307_spec
import s22plus_fyg8_p308_overlay_contract as p308_overlay
import s22plus_fyg8_p308_telemetry_decoder as p308_decoder
import s22plus_fyg8_p308_telemetry_spec as p308_spec
import s22plus_fyg8_p310_e2_stock_closure as p310_e2_closure
import s22plus_fyg8_p310_source_contract as p310_source_contract
import s22plus_fyg8_p310_telemetry_decoder as p310_decoder
import s22plus_fyg8_p311_overlay_contract as p311_overlay
import s22plus_fyg8_p311_e2_stock_closure as p311_e2_closure
import s22plus_fyg8_p311_telemetry_decoder as p311_decoder
import s22plus_fyg8_p311_telemetry_spec as p311_spec
import s22plus_fyg8_p312_overlay_contract as p312_overlay
import s22plus_fyg8_p312_e2_stock_closure as p312_e2_closure
import s22plus_fyg8_p312_telemetry_decoder as p312_decoder
import s22plus_fyg8_p312_telemetry_spec as p312_spec
import s22plus_fyg8_p313_overlay_contract as p313_overlay
import s22plus_fyg8_p313_e2_stock_closure as p313_e2_closure
import s22plus_fyg8_p313_telemetry_decoder as p313_decoder
import s22plus_fyg8_p313_telemetry_spec as p313_spec
import s22plus_fyg8_p314_design_contract as p314_design
import s22plus_fyg8_p314_e2_stock_closure as p314_e2_closure
import s22plus_fyg8_p314_overlay_contract as p314_overlay
import s22plus_fyg8_p314_telemetry_decoder as p314_decoder
import s22plus_fyg8_p314_telemetry_spec as p314_spec
import s22plus_fyg8_p315_design_contract as p315_design
import s22plus_fyg8_p315_e2_stock_closure as p315_e2_closure
import s22plus_fyg8_p315_overlay_contract as p315_overlay
import s22plus_fyg8_p315_telemetry_decoder as p315_decoder
import s22plus_fyg8_p315_telemetry_spec as p315_spec
import s22plus_fyg8_p316_e2_stock_closure as p316_e2_closure
import s22plus_fyg8_p317_e2_stock_closure as p317_e2_closure
import s22plus_fyg8_p318_e2_stock_closure as p318_e2_closure
p319_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p319_stock_process_v2_adapter"
)
p320_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p320_stock_process_v2_adapter"
)
p321_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p321_stock_process_v2_adapter"
)
p322_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p322_stock_process_v2_adapter"
)
p323_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p323_stock_process_v2_adapter"
)
p324_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p324_stock_process_v2_adapter"
)
p325_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p325_stock_process_v2_adapter"
)
p326_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p326_stock_process_v2_adapter"
)
p327_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p327_stock_process_v2_adapter"
)
p328_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p328_stock_process_v2_adapter"
)
p328_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p328_artifact_identity"
)
p329_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p329_stock_process_v2_adapter"
)
p329_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p329_artifact_identity"
)
p330_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p330_stock_process_v2_adapter"
)
p330_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p330_artifact_identity"
)
p331_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p331_stock_process_v2_adapter"
)
p331_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p331_artifact_identity"
)
p331_resident_exec_runtime = _load_stable_local_module(
    "s22plus_fyg8_p331_resident_exec_runtime"
)
p331_resident_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p331_resident_acm_observer"
)
p332_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p332_stock_process_v2_adapter"
)
p332_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p332_artifact_identity"
)
p332_logical_resident_exec_runtime = _load_stable_local_module(
    "s22plus_fyg8_p332_logical_resident_exec_runtime"
)
p332_logical_resident_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p332_logical_resident_acm_observer"
)
p333_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p333_stock_process_v2_adapter"
)
p333_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p333_artifact_identity"
)
p333_open_entry_diag_runtime = _load_stable_local_module(
    "s22plus_fyg8_p333_open_entry_diag_runtime"
)
p333_open_entry_diag_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p333_open_entry_diag_acm_observer"
)
p334_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p334_stock_process_v2_adapter"
)
p334_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p334_artifact_identity"
)
p334_first_read_rc_runtime = _load_stable_local_module(
    "s22plus_fyg8_p334_first_read_rc_runtime"
)
p334_first_read_rc_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p334_first_read_rc_acm_observer"
)
p335_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p335_stock_process_v2_adapter"
)
p335_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p335_artifact_identity"
)
p335_retained_listener_runtime = _load_stable_local_module(
    "s22plus_fyg8_p335_retained_listener_runtime"
)
p335_retained_listener_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p335_retained_listener_acm_observer"
)
p336_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p336_stock_process_v2_adapter"
)
p336_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p336_artifact_identity"
)
p336_long_idle_runtime = _load_stable_local_module(
    "s22plus_fyg8_p336_long_idle_runtime"
)
p336_long_idle_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p336_long_idle_acm_observer"
)
p337_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p337_stock_process_v2_adapter"
)
p337_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p337_artifact_identity"
)
p337_open_read_diag_runtime = _load_stable_local_module(
    "s22plus_fyg8_p337_open_read_diag_runtime"
)
p337_open_read_diag_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p337_open_read_diag_acm_observer"
)
p338_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p338_stock_process_v2_adapter"
)
p338_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p338_artifact_identity"
)
p338_open_read_branch_runtime = _load_stable_local_module(
    "s22plus_fyg8_p338_open_read_branch_runtime"
)
p338_open_read_branch_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p338_open_read_branch_acm_observer"
)
p339_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p339_stock_process_v2_adapter"
)
p339_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p339_artifact_identity"
)
p339_open_read_branch_runtime = _load_stable_local_module(
    "s22plus_fyg8_p339_open_read_branch_runtime"
)
p339_open_read_branch_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p339_open_read_branch_acm_observer"
)
p340_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p340_stock_process_v2_adapter"
)
p340_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p340_artifact_identity"
)
p340_open_read_branch_runtime = _load_stable_local_module(
    "s22plus_fyg8_p340_open_read_branch_runtime"
)
p340_open_read_branch_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p340_open_read_branch_acm_observer"
)
p341_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p341_stock_process_v2_adapter"
)
p341_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p341_artifact_identity"
)
p341_open_read_branch_runtime = _load_stable_local_module(
    "s22plus_fyg8_p341_open_read_branch_runtime"
)
p341_open_read_branch_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p341_open_read_branch_acm_observer"
)
# P342 is a fresh identity successor whose common proof adds one bounded
# same-FD idle receipt to the existing host-first OPEN session proof.  Keep
# the runtime/observer imports independent of the adapter so H0 source
# qualification can run while the candidate builder closure is still being
# assembled.
p342_open_read_branch_runtime = _load_stable_local_module(
    "s22plus_fyg8_p342_open_read_branch_runtime"
)
p342_open_read_branch_acm_observer = _load_stable_local_module(
    "s22plus_fyg8_p342_open_read_branch_acm_observer"
)
p342_stock_adapter = _load_stable_local_module(
    "s22plus_fyg8_p342_stock_process_v2_adapter"
)
p342_artifact_identity = _load_stable_local_module(
    "s22plus_fyg8_p342_artifact_identity"
)
# The P336 adapter intentionally keeps its exact-loaded predecessor graph
# private.  Common evidence still needs the carrier model/shape interface for
# normal E1 projection; expose only the immutable parser symbols, never a new
# command or path surface.
for _name in (
    "model", "spec", "DecodeError", "RAW_SIZE", "LONG_FAMILY", "UNSAT_FAMILY",
    "TERMINAL_STAGE", "encode_fixture", "decode_record",
):
    if not hasattr(p336_stock_adapter, _name) and hasattr(
        p336_stock_adapter, "_P335"
    ):
        setattr(p336_stock_adapter, _name, getattr(p336_stock_adapter._P335, _name))
if not hasattr(p336_stock_adapter, "_ORIGINAL_CLASSIFY_OBSERVATION"):
    _p336_parent = getattr(p336_stock_adapter, "_P335", None)
    _p336_parser = getattr(_p336_parent, "_P334", None)
    for _name in ("_ORIGINAL_CLASSIFY_OBSERVATION", "_ORIGINAL_CLASSIFY_CLEAN_BASELINE"):
        if _p336_parser is not None and hasattr(_p336_parser, _name):
            setattr(p336_stock_adapter, _name, getattr(_p336_parser, _name))
            if _p336_parent is not None and not hasattr(_p336_parent, _name):
                setattr(_p336_parent, _name, getattr(_p336_parser, _name))
if not hasattr(p336_stock_adapter, "source_bytes"):
    setattr(p336_stock_adapter, "source_bytes", p335_stock_adapter.source_bytes)
if not hasattr(p336_stock_adapter, "SOURCE_KEYS"):
    setattr(p336_stock_adapter, "SOURCE_KEYS", frozenset(p335_stock_adapter.SOURCE_KEYS))
# P337 is the same closed carrier/parser surface with one failure-only device
# diagnostic.  Export the immutable parser model expected by common evidence.
for _name in (
    "model", "spec", "DecodeError", "RAW_SIZE", "LONG_FAMILY", "UNSAT_FAMILY",
    "TERMINAL_STAGE", "encode_fixture", "decode_record", "source_bytes",
    "SOURCE_KEYS", "proof_class",
):
    if not hasattr(p337_stock_adapter, _name) and hasattr(
        p337_stock_adapter._P335, _name
    ):
        setattr(p337_stock_adapter, _name, getattr(p337_stock_adapter._P335, _name))
if not hasattr(p337_stock_adapter, "_ORIGINAL_CLASSIFY_OBSERVATION"):
    _p337_parser = getattr(p337_stock_adapter, "_P335", None)
    for _name in ("_ORIGINAL_CLASSIFY_OBSERVATION", "_ORIGINAL_CLASSIFY_CLEAN_BASELINE"):
        if _p337_parser is not None and hasattr(_p337_parser, _name):
            setattr(p337_stock_adapter, _name, getattr(_p337_parser, _name))
# P338 preserves the exact P337 Carrier/parser shape and only changes the ACM
# branch diagnostic.  Export the immutable parser symbols expected by the
# common classifier without importing or widening any device-facing surface.
_p338_parent = getattr(
    p338_stock_adapter,
    "_P337",
    getattr(p338_stock_adapter, "predecessor", None),
)
if _p338_parent is not None and hasattr(_p338_parent, "_P335"):
    _p338_parent = _p338_parent._P335
for _name in (
    "model", "spec", "DecodeError", "RAW_SIZE", "LONG_FAMILY", "UNSAT_FAMILY",
    "TERMINAL_STAGE", "encode_fixture", "decode_record", "source_bytes",
    "SOURCE_KEYS", "proof_class",
):
    if not hasattr(p338_stock_adapter, _name) and _p338_parent is not None and hasattr(
        _p338_parent, _name
    ):
        setattr(p338_stock_adapter, _name, getattr(_p338_parent, _name))
if not hasattr(p338_stock_adapter, "_ORIGINAL_CLASSIFY_OBSERVATION"):
    _p338_parser = _p338_parent
    for _name in ("_ORIGINAL_CLASSIFY_OBSERVATION", "_ORIGINAL_CLASSIFY_CLEAN_BASELINE"):
        if _p338_parser is not None and hasattr(_p338_parser, _name):
            setattr(p338_stock_adapter, _name, getattr(_p338_parser, _name))

# The P338 adapter deliberately keeps the inherited Carrier parser private.
# Common source-closure validation still needs a fresh, JSON-safe round-trip
# probe; expose a tiny P338-bound façade rather than calling the P328 helper
# whose global run binding is consumed by the predecessor.
if not hasattr(p338_stock_adapter, "DecodeError"):
    setattr(p338_stock_adapter, "DecodeError", getattr(p337_stock_adapter, "DecodeError", ValueError))
_p338_existing_encoder = getattr(p338_stock_adapter, "encode_fixture", None)
if not callable(_p338_existing_encoder) or getattr(
    _p338_existing_encoder, "__module__", ""
).startswith("s22plus_fyg8_p328_"):
    def _p338_encode_fixture(*args: Any, **kwargs: Any) -> bytes:
        if args or kwargs:
            raise p338_stock_adapter.DecodeError("P338 fixture arguments are not allowlisted")
        return p338_stock_adapter.model.initialize_record(
            p338_stock_adapter.PROFILE, p338_stock_adapter.P338_RUN_ID
        )

    setattr(p338_stock_adapter, "encode_fixture", _p338_encode_fixture)
_p338_existing_decoder = getattr(p338_stock_adapter, "decode_record", None)
if not callable(_p338_existing_decoder) or getattr(
    _p338_existing_decoder, "__module__", ""
).startswith("s22plus_fyg8_p328_"):
    def _p338_decode_record(
        record: bytes,
        *,
        expected_profile: str = p338_stock_adapter.PROFILE,
        expected_run_id: bytes | None = None,
    ) -> dict[str, Any]:
        bound = p338_stock_adapter.P338_RUN_ID if expected_run_id is None else expected_run_id
        if bound != p338_stock_adapter.P338_RUN_ID:
            raise p338_stock_adapter.DecodeError("P338 Carrier run ID differs")
        try:
            value = p338_stock_adapter.model.decode_record(
                record,
                expected_profile=expected_profile,
                expected_run_id=p338_stock_adapter.P338_RUN_ID,
            )
        except Exception as exc:
            raise p338_stock_adapter.DecodeError(str(exc)) from exc
        if not isinstance(value, dict):
            raise p338_stock_adapter.DecodeError("P338 Carrier record is not an object")

        def _json_value(current: Any) -> Any:
            if isinstance(current, bytes):
                return {"encoding": "hex", "value": current.hex()}
            if isinstance(current, dict):
                return {key: _json_value(child) for key, child in current.items()}
            if isinstance(current, (list, tuple)):
                return [_json_value(child) for child in current]
            return current

        return _json_value(value)

    setattr(p338_stock_adapter, "decode_record", _p338_decode_record)
if not hasattr(p338_stock_adapter, "source_bytes"):
    setattr(p338_stock_adapter, "source_bytes", p337_stock_adapter.source_bytes)
# P339 preserves the Carrier bytes and changes only failure-only OPEN
# diagnostics.  Re-export the immutable parser surface required by the common
# classifier without adding a command or device-facing path.
_p339_parent = getattr(p339_stock_adapter, "predecessor", None)
_p339_parser = getattr(
    _p339_parent,
    "_P335",
    getattr(getattr(_p339_parent, "predecessor", None), "_P335", _p339_parent),
)
for _name in (
    "model", "spec", "DecodeError", "RAW_SIZE", "LONG_FAMILY", "UNSAT_FAMILY",
    "TERMINAL_STAGE", "source_bytes", "SOURCE_KEYS", "proof_class",
    "_ORIGINAL_CLASSIFY_OBSERVATION", "_ORIGINAL_CLASSIFY_CLEAN_BASELINE",
):
    if (
        not hasattr(p339_stock_adapter, _name)
        and _p339_parser is not None
        and hasattr(_p339_parser, _name)
    ):
        setattr(p339_stock_adapter, _name, getattr(_p339_parser, _name))
if not hasattr(p339_stock_adapter, "DecodeError"):
    setattr(p339_stock_adapter, "DecodeError", p338_stock_adapter.DecodeError)


def _p339_encode_fixture(*args: Any, **kwargs: Any) -> bytes:
    if args or kwargs:
        raise p339_stock_adapter.DecodeError(
            "P339 fixture arguments are not allowlisted"
        )
    return p339_stock_adapter.model.initialize_record(
        p339_stock_adapter.PROFILE, p339_stock_adapter.P339_RUN_ID
    )


def _p339_decode_record(
    record: bytes,
    *,
    expected_profile: str = p339_stock_adapter.PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    bound = p339_stock_adapter.P339_RUN_ID if expected_run_id is None else expected_run_id
    if bound != p339_stock_adapter.P339_RUN_ID:
        raise p339_stock_adapter.DecodeError("P339 Carrier run ID differs")
    try:
        value = p339_stock_adapter.model.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=p339_stock_adapter.P339_RUN_ID,
        )
    except Exception as exc:
        raise p339_stock_adapter.DecodeError(str(exc)) from exc
    if not isinstance(value, dict):
        raise p339_stock_adapter.DecodeError("P339 Carrier record is not an object")

    def json_value(current: Any) -> Any:
        if isinstance(current, bytes):
            return {"encoding": "hex", "value": current.hex()}
        if isinstance(current, dict):
            return {key: json_value(child) for key, child in current.items()}
        if isinstance(current, (list, tuple)):
            return [json_value(child) for child in current]
        return current

    return json_value(value)


p339_stock_adapter.encode_fixture = _p339_encode_fixture
p339_stock_adapter.decode_record = _p339_decode_record

# P340 preserves the P339 Carrier bytes and fixed successful protocol while
# binding a fresh run namespace.  Re-export only the immutable parser surface
# required by common evidence; the P340 adapter itself remains the authority
# for its fresh contract and observer IDs.
for _name in (
    "model", "spec", "DecodeError", "RAW_SIZE", "LONG_FAMILY", "UNSAT_FAMILY",
    "TERMINAL_STAGE", "source_bytes", "SOURCE_KEYS", "proof_class",
    "_ORIGINAL_CLASSIFY_OBSERVATION", "_ORIGINAL_CLASSIFY_CLEAN_BASELINE",
):
    if not hasattr(p340_stock_adapter, _name) and hasattr(
        p339_stock_adapter, _name
    ):
        setattr(p340_stock_adapter, _name, getattr(p339_stock_adapter, _name))
if not hasattr(p340_stock_adapter, "DecodeError"):
    setattr(p340_stock_adapter, "DecodeError", p339_stock_adapter.DecodeError)


def _p340_encode_fixture(*args: Any, **kwargs: Any) -> bytes:
    if args or kwargs:
        raise p340_stock_adapter.DecodeError(
            "P340 fixture arguments are not allowlisted"
        )
    return p340_stock_adapter.model.initialize_record(
        p340_stock_adapter.PROFILE, p340_stock_adapter.P340_RUN_ID
    )


def _p340_decode_record(
    record: bytes,
    *,
    expected_profile: str = p340_stock_adapter.PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    bound = p340_stock_adapter.P340_RUN_ID if expected_run_id is None else expected_run_id
    if bound != p340_stock_adapter.P340_RUN_ID:
        raise p340_stock_adapter.DecodeError("P340 Carrier run ID differs")
    try:
        value = p340_stock_adapter.model.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=p340_stock_adapter.P340_RUN_ID,
        )
    except Exception as exc:
        raise p340_stock_adapter.DecodeError(str(exc)) from exc
    if not isinstance(value, dict):
        raise p340_stock_adapter.DecodeError("P340 Carrier record is not an object")

    def json_value(current: Any) -> Any:
        if isinstance(current, bytes):
            return {"encoding": "hex", "value": current.hex()}
        if isinstance(current, dict):
            return {key: json_value(child) for key, child in current.items()}
        if isinstance(current, (list, tuple)):
            return [json_value(child) for child in current]
        return current

    return json_value(value)


p340_stock_adapter.encode_fixture = _p340_encode_fixture
p340_stock_adapter.decode_record = _p340_decode_record

# P341 keeps the P340 Carrier bytes and authenticated command grammar but
# binds a fresh host-first-OPEN namespace.  Re-export only the immutable
# parser surface required by common evidence; the P341 adapter remains the
# authority for its fresh contract and observer IDs.
for _name in (
    "model", "spec", "DecodeError", "RAW_SIZE", "LONG_FAMILY", "UNSAT_FAMILY",
    "TERMINAL_STAGE", "source_bytes", "SOURCE_KEYS", "proof_class",
    "_ORIGINAL_CLASSIFY_OBSERVATION", "_ORIGINAL_CLASSIFY_CLEAN_BASELINE",
):
    if not hasattr(p341_stock_adapter, _name) and hasattr(
        p340_stock_adapter, _name
    ):
        setattr(p341_stock_adapter, _name, getattr(p340_stock_adapter, _name))
if not hasattr(p341_stock_adapter, "DecodeError"):
    setattr(p341_stock_adapter, "DecodeError", p340_stock_adapter.DecodeError)


def _p341_encode_fixture(*args: Any, **kwargs: Any) -> bytes:
    if args or kwargs:
        raise p341_stock_adapter.DecodeError(
            "P341 fixture arguments are not allowlisted"
        )
    return p341_stock_adapter.model.initialize_record(
        p341_stock_adapter.PROFILE, p341_stock_adapter.P341_RUN_ID
    )


def _p341_decode_record(
    record: bytes,
    *,
    expected_profile: str = p341_stock_adapter.PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    bound = p341_stock_adapter.P341_RUN_ID if expected_run_id is None else expected_run_id
    if bound != p341_stock_adapter.P341_RUN_ID:
        raise p341_stock_adapter.DecodeError("P341 Carrier run ID differs")
    try:
        value = p341_stock_adapter.model.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=p341_stock_adapter.P341_RUN_ID,
        )
    except Exception as exc:
        raise p341_stock_adapter.DecodeError(str(exc)) from exc
    if not isinstance(value, dict):
        raise p341_stock_adapter.DecodeError("P341 Carrier record is not an object")

    def json_value(current: Any) -> Any:
        if isinstance(current, bytes):
            return {"encoding": "hex", "value": current.hex()}
        if isinstance(current, dict):
            return {key: json_value(child) for key, child in current.items()}
        if isinstance(current, (list, tuple)):
            return [json_value(child) for child in current]
        return current

    return json_value(value)


p341_stock_adapter.encode_fixture = _p341_encode_fixture
p341_stock_adapter.decode_record = _p341_decode_record

# P342 retains the P341 Carrier grammar through a private adapter projection.
# Its adapter deliberately exposes only the fresh overlay/source identity;
# provide the immutable parser symbols required by common classification in
# this module, without widening the adapter's device-facing surface.
for _name in (
    "model", "spec", "DecodeError", "RAW_SIZE", "LONG_FAMILY", "UNSAT_FAMILY",
    "TERMINAL_STAGE", "source_bytes", "SOURCE_KEYS", "proof_class",
    "_ORIGINAL_CLASSIFY_OBSERVATION", "_ORIGINAL_CLASSIFY_CLEAN_BASELINE",
):
    if not hasattr(p342_stock_adapter, _name) and hasattr(p341_stock_adapter, _name):
        setattr(p342_stock_adapter, _name, getattr(p341_stock_adapter, _name))
if not hasattr(p342_stock_adapter, "DecodeError"):
    setattr(p342_stock_adapter, "DecodeError", p340_stock_adapter.DecodeError)


def _p342_encode_fixture(*args: Any, **kwargs: Any) -> bytes:
    if args or kwargs:
        raise p342_stock_adapter.DecodeError(
            "P342 fixture arguments are not allowlisted"
        )
    return p342_stock_adapter.model.initialize_record(
        p342_stock_adapter.PROFILE, p342_stock_adapter.P342_RUN_ID
    )


def _p342_decode_record(
    record: bytes,
    *,
    expected_profile: str = p342_stock_adapter.PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    bound = p342_stock_adapter.P342_RUN_ID if expected_run_id is None else expected_run_id
    if bound != p342_stock_adapter.P342_RUN_ID:
        raise p342_stock_adapter.DecodeError("P342 Carrier run ID differs")
    try:
        value = p342_stock_adapter.model.decode_record(
            record,
            expected_profile=expected_profile,
            expected_run_id=p342_stock_adapter.P342_RUN_ID,
        )
    except Exception as exc:
        raise p342_stock_adapter.DecodeError(str(exc)) from exc
    if not isinstance(value, dict):
        raise p342_stock_adapter.DecodeError("P342 Carrier record is not an object")

    def json_value(current: Any) -> Any:
        if isinstance(current, bytes):
            return {"encoding": "hex", "value": current.hex()}
        if isinstance(current, dict):
            return {key: json_value(child) for key, child in current.items()}
        if isinstance(current, (list, tuple)):
            return [json_value(child) for child in current]
        return current

    return json_value(value)


p342_stock_adapter.encode_fixture = _p342_encode_fixture
p342_stock_adapter.decode_record = _p342_decode_record
p323_predecessor_baseline = _load_stable_local_module(
    "s22plus_fyg8_p323_p322_carrier_reanalysis"
)
import s22plus_fyg8_max77705_telemetry_decoder as max77705_decoder
import s22plus_fyg8_p317_max77705_telemetry_decoder as p317_max77705_decoder
import s22plus_fyg8_p318_max77705_telemetry_decoder as p318_max77705_decoder
import s22plus_fyg8_p318_topology_receipt as p318_topology_receipt


MARKER_KIND = "retained_marker_after_rollback"
CHECKPOINT_KIND = "retained_checkpoint_after_rollback"
PID1_USERSPACE_KIND = "retained_pid1_userspace_after_rollback"
SAME_RING_KIND = "retained_pid1_same_ring_discriminator_after_rollback"
SAME_RING_MULTIBOOT_KIND = (
    "retained_pid1_same_ring_multiboot_discriminator_after_rollback"
)
E1_LATEST_STAGE_KIND = "retained_e1_latest_stage_multiboot_after_rollback"
CANDIDATE_ARRIVAL_PROOF_ROLE_KEY = "candidate_arrival_proof_role"
CANDIDATE_ARRIVAL_PROOF_STATE_KEY = "candidate_arrival_proof"
# This is deliberately a manifest opt-in.  Existing manifests have no role and
# retain their historical ACM/Carrier precedence.
CANDIDATE_ARRIVAL_PROOF_ROLE = "cdc_acm_primary_v1"
P323_ACM_PRIMARY_ROLE = CANDIDATE_ARRIVAL_PROOF_ROLE
CANDIDATE_BIDIRECTIONAL_CONSOLE_ROLE = "cdc_acm_bidirectional_console_v1"
CANDIDATE_FRAMED_FIXED_COMMAND_ROLE = "p327_framed_fixed_command_session_v1"
CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE = (
    "p328_authenticated_framed_exec_session_v1"
)
CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE = (
    "p329_authenticated_framed_exec_udev_settle_session_v1"
)
CANDIDATE_AUTHENTICATED_DIAGNOSTIC_EXEC_ROLE = (
    "p330_authenticated_framed_exec_preauth_diagnostic_session_v1"
)
# P3.31 retains the authenticated S328 exchange but narrows the proof role to
# a fixed heartbeat in exactly two sessions with one clean reconnect.  Keep a
# single canonical value; the aliases are descriptive compatibility names for
# callers that spell the resident role differently.
CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE = (
    "p331_authenticated_resident_framed_exec_session_v1"
)
CANDIDATE_AUTHENTICATED_RESIDENT_RECONNECT_ROLE = (
    CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE
)
CANDIDATE_AUTHENTICATED_RESIDENT_SESSION_ROLE = (
    CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE
)
CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE = (
    "p332_authenticated_logical_resident_same_fd_session_v1"
)
CANDIDATE_ARRIVAL_PROOF_SCHEMA = "device_action_f1_candidate_arrival_proof_v1"
P323_ACM_PRIMARY_RUNTIME_CONTRACT_ID = (
    "s22plus-fyg8-p323-acm-primary-runtime-v1"
)
P323_ACM_PRIMARY_RUN_ID_HEX = "c323f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P323_ACM_PRIMARY_BANNER_SIZE = 49
P323_ACM_PRIMARY_VERDICT = (
    "PASS_F1_V2_ACM_PRIMARY_NATIVE_PID1_USB_ARRIVAL_AND_ROLLED_BACK"
)
P323_ACM_PRIMARY_OUTCOME = (
    "acm_primary_native_pid1_usb_arrival_rollback_verified"
)
P323_ACM_PRIMARY_NO_PROOF_OUTCOME = (
    "p323_acm_primary_native_pid1_arrival_unproved_rollback_verified"
)
P324_ACM_PRIMARY_RUNTIME_CONTRACT_ID = (
    "s22plus-fyg8-p324-acm-primary-runtime-v1"
)
P324_ACM_PRIMARY_RUN_ID_HEX = "c324f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P324_ACM_PRIMARY_BANNER_SIZE = 49
P324_ACM_PRIMARY_VERDICT = (
    "PASS_F1_V2_P324_ACM_PRIMARY_NATIVE_PID1_USB_ARRIVAL_AND_ROLLED_BACK"
)
P324_ACM_PRIMARY_OUTCOME = (
    "p324_acm_primary_native_pid1_usb_arrival_rollback_verified"
)
P324_ACM_PRIMARY_NO_PROOF_OUTCOME = (
    "p324_acm_primary_native_pid1_arrival_unproved_rollback_verified"
)
P325_ACM_PRIMARY_RUNTIME_CONTRACT_ID = (
    "s22plus-fyg8-p325-acm-primary-runtime-v1"
)
P325_ACM_PRIMARY_RUN_ID_HEX = "c325f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P325_ACM_PRIMARY_BANNER_SIZE = 49
P325_ACM_PRIMARY_VERDICT = (
    "PASS_F1_V2_P325_ACM_PRIMARY_NATIVE_PID1_USB_ARRIVAL_AND_ROLLED_BACK"
)
P325_ACM_PRIMARY_OUTCOME = (
    "p325_acm_primary_native_pid1_usb_arrival_rollback_verified"
)
P325_ACM_PRIMARY_NO_PROOF_OUTCOME = (
    "p325_acm_primary_native_pid1_arrival_unproved_rollback_verified"
)
P326_CONSOLE_RUNTIME_CONTRACT_ID = (
    "s22plus-fyg8-p326-bidirectional-console-runtime-v1"
)
P326_CONSOLE_RUN_ID_HEX = "c326f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P326_CONSOLE_TRANSCRIPT_SIZE = 145
P326_CONSOLE_VERDICT = (
    "PASS_F1_V2_P326_NATIVE_PID1_BIDIRECTIONAL_USB_BUSYBOX_SHELL_AND_ROLLED_BACK"
)
P326_CONSOLE_OUTCOME = (
    "p326_native_pid1_bidirectional_usb_busybox_shell_rollback_verified"
)
P326_CONSOLE_NO_PROOF_OUTCOME = (
    "p326_bidirectional_usb_busybox_shell_unproved_rollback_verified"
)
P327_FRAMED_EXEC_RUNTIME_CONTRACT_ID = (
    "s22plus-fyg8-p327-framed-exec-runtime-v1"
)
P327_FRAMED_EXEC_RUN_ID_HEX = "c327f1e0a90b5e6d7c8a9b0c1d2e3f3b"
P327_FRAMED_EXEC_COMMAND_COUNT = 3
P327_FRAMED_EXEC_MAX_FRAME_PAYLOAD = 1024
P327_FRAMED_EXEC_COMMAND_TIMEOUT_SEC = 10
P327_FRAMED_EXEC_MAX_OUTPUT_BYTES = 128 * 1024
P327_FRAMED_EXEC_VERDICT = (
    "PASS_F1_V2_P327_NATIVE_PID1_FRAMED_EXEC_FIXED_COMMANDS_AND_ROLLED_BACK"
)
P327_FRAMED_EXEC_OUTCOME = (
    "p327_native_pid1_framed_exec_fixed_commands_rollback_verified"
)
P327_FRAMED_EXEC_NO_PROOF_OUTCOME = (
    "p327_framed_exec_fixed_commands_unproved_rollback_verified"
)
P328_AUTH_EXEC_RUNTIME_CONTRACT_ID = (
    "s22plus-fyg8-p328-auth-exec-runtime-v1"
)
P328_AUTH_EXEC_OBSERVER_CONTRACT_ID = (
    "s22plus-fyg8-p328-auth-acm-observer-v1"
)
P328_AUTH_EXEC_RUN_ID_HEX = "c328f1e0a90b5e6d7c8a9b0c1d2e3f2b"
P328_AUTH_EXEC_COMMAND_COUNT = 3
P328_AUTH_EXEC_MAX_FRAME_PAYLOAD = 1055
P328_AUTH_EXEC_MAX_COMMANDS = 16
P328_AUTH_EXEC_COMMAND_TIMEOUT_SEC = 15
P328_AUTH_EXEC_MAX_OUTPUT_BYTES = 128 * 1024
P328_AUTH_EXEC_AUTH_ALGORITHM = "hmac-sha256"
P328_AUTH_EXEC_AUTH_TAG_SIZE = 32
P328_AUTH_EXEC_AUTH_KEY_SCHEMA = "s22plus_fyg8_p328_auth_key_v1"
P328_AUTH_EXEC_AUTH_KEY_SIZE = 32
P328_AUTH_EXEC_AUTH_KEY_IDENTITY = {
    "size": 32,
    "sha256": "7eb6a32ca96daa9cd125b2798834f45515265a76d653ae719091d98f0a1f515b",
}
P328_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P328_AUTHENTICATED_PID1_BOUNDED_COMMANDS_AND_ROLLED_BACK"
)
P328_AUTH_EXEC_OUTCOME = (
    "p328_authenticated_pid1_bounded_commands_rollback_verified"
)
P328_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p328_authenticated_framed_exec_unproved_rollback_verified"
)
P329_AUTH_EXEC_RUNTIME_CONTRACT_ID = "s22plus-fyg8-p329-auth-exec-runtime-v1"
P329_AUTH_EXEC_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p329-auth-acm-observer-v1"
P329_AUTH_EXEC_RUN_ID_HEX = p329_stock_adapter.P329_RUN_ID_HEX
P329_AUTH_EXEC_COMMAND_COUNT = P328_AUTH_EXEC_COMMAND_COUNT
P329_AUTH_EXEC_MAX_FRAME_PAYLOAD = P328_AUTH_EXEC_MAX_FRAME_PAYLOAD
P329_AUTH_EXEC_MAX_COMMANDS = P328_AUTH_EXEC_MAX_COMMANDS
P329_AUTH_EXEC_COMMAND_TIMEOUT_SEC = P328_AUTH_EXEC_COMMAND_TIMEOUT_SEC
P329_AUTH_EXEC_MAX_OUTPUT_BYTES = P328_AUTH_EXEC_MAX_OUTPUT_BYTES
P329_AUTH_EXEC_AUTH_ALGORITHM = P328_AUTH_EXEC_AUTH_ALGORITHM
P329_AUTH_EXEC_AUTH_TAG_SIZE = P328_AUTH_EXEC_AUTH_TAG_SIZE
P329_AUTH_EXEC_AUTH_KEY_SCHEMA = P328_AUTH_EXEC_AUTH_KEY_SCHEMA
P329_AUTH_EXEC_AUTH_KEY_SIZE = P328_AUTH_EXEC_AUTH_KEY_SIZE
P329_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P328_AUTH_EXEC_AUTH_KEY_IDENTITY)
P329_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P329_AUTHENTICATED_PID1_BOUNDED_COMMANDS_UDEV_SETTLED_AND_ROLLED_BACK"
)
P329_AUTH_EXEC_OUTCOME = (
    "p329_authenticated_pid1_bounded_commands_udev_settled_rollback_verified"
)
P329_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p329_authenticated_framed_exec_unproved_rollback_verified"
)
P330_AUTH_EXEC_RUNTIME_CONTRACT_ID = "s22plus-fyg8-p330-auth-exec-runtime-v1"
P330_AUTH_EXEC_OBSERVER_CONTRACT_ID = "s22plus-fyg8-p330-auth-acm-observer-v1"
P330_AUTH_EXEC_RUN_ID_HEX = p330_stock_adapter.P330_RUN_ID_HEX
P330_AUTH_EXEC_COMMAND_COUNT = P328_AUTH_EXEC_COMMAND_COUNT
P330_AUTH_EXEC_MAX_FRAME_PAYLOAD = P328_AUTH_EXEC_MAX_FRAME_PAYLOAD
P330_AUTH_EXEC_MAX_COMMANDS = P328_AUTH_EXEC_MAX_COMMANDS
P330_AUTH_EXEC_COMMAND_TIMEOUT_SEC = P328_AUTH_EXEC_COMMAND_TIMEOUT_SEC
P330_AUTH_EXEC_MAX_OUTPUT_BYTES = P328_AUTH_EXEC_MAX_OUTPUT_BYTES
P330_AUTH_EXEC_AUTH_ALGORITHM = P328_AUTH_EXEC_AUTH_ALGORITHM
P330_AUTH_EXEC_AUTH_TAG_SIZE = P328_AUTH_EXEC_AUTH_TAG_SIZE
P330_AUTH_EXEC_AUTH_KEY_SCHEMA = P328_AUTH_EXEC_AUTH_KEY_SCHEMA
P330_AUTH_EXEC_AUTH_KEY_SIZE = P328_AUTH_EXEC_AUTH_KEY_SIZE
P330_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P328_AUTH_EXEC_AUTH_KEY_IDENTITY)
P330_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = 0x86
P330_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = 8
P330_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = 64
P330_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P330_AUTHENTICATED_PID1_BOUNDED_COMMANDS_DIAGNOSTIC_AND_ROLLED_BACK"
)
P330_AUTH_EXEC_OUTCOME = (
    "p330_authenticated_pid1_bounded_commands_diagnostic_rollback_verified"
)
P330_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p330_authenticated_framed_exec_diagnostic_unproved_rollback_verified"
)
P331_AUTH_EXEC_RUNTIME_CONTRACT_ID = p331_resident_exec_runtime.CONTRACT_ID
P331_AUTH_EXEC_OBSERVER_CONTRACT_ID = p331_resident_acm_observer.CONTRACT_ID
P331_AUTH_EXEC_RUN_ID_HEX = p331_stock_adapter.P331_RUN_ID_HEX
P331_AUTH_EXEC_COMMAND_COUNT = 1
P331_AUTH_EXEC_MAX_FRAME_PAYLOAD = p331_resident_exec_runtime.MAX_FRAME_PAYLOAD
P331_AUTH_EXEC_FRAME_HEADER_SIZE = p331_resident_exec_runtime.FRAME_HEADER_SIZE
P331_AUTH_EXEC_MAX_COMMANDS = p331_resident_exec_runtime.MAX_COMMANDS
P331_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p331_resident_exec_runtime.COMMAND_TIMEOUT_SEC
P331_AUTH_EXEC_MAX_OUTPUT_BYTES = p331_resident_exec_runtime.MAX_OUTPUT_BYTES
P331_AUTH_EXEC_AUTH_ALGORITHM = P328_AUTH_EXEC_AUTH_ALGORITHM
P331_AUTH_EXEC_AUTH_TAG_SIZE = p331_resident_exec_runtime.AUTH_TAG_SIZE
P331_AUTH_EXEC_AUTH_KEY_SCHEMA = P328_AUTH_EXEC_AUTH_KEY_SCHEMA
P331_AUTH_EXEC_AUTH_KEY_SIZE = p331_resident_exec_runtime.AUTH_KEY_SIZE
P331_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P330_AUTH_EXEC_AUTH_KEY_IDENTITY)
P331_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p331_resident_exec_runtime.DIAGNOSTIC_FRAME_TYPE
P331_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P330_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P331_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p331_resident_exec_runtime.RNG_EAGAIN_RETRY_LIMIT
P331_AUTH_EXEC_SESSION_CAP = p331_resident_exec_runtime.MAX_SESSIONS
P331_AUTH_EXEC_RECONNECT_CAP = p331_resident_exec_runtime.MAX_RECONNECTS
P331_AUTH_EXEC_HEARTBEAT_COMMAND = p331_resident_exec_runtime.HEARTBEAT_COMMAND
P331_AUTH_EXEC_HEARTBEAT_OUTPUT = p331_resident_exec_runtime.HEARTBEAT_OUTPUT
P331_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P331_AUTHENTICATED_RESIDENT_HEARTBEAT_AND_ROLLED_BACK"
)
P331_AUTH_EXEC_OUTCOME = (
    "p331_authenticated_resident_heartbeat_rollback_verified"
)
P331_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p331_authenticated_resident_heartbeat_unproved_rollback_verified"
)
P332_AUTH_EXEC_RUNTIME_CONTRACT_ID = p332_logical_resident_exec_runtime.CONTRACT_ID
P332_AUTH_EXEC_OBSERVER_CONTRACT_ID = p332_logical_resident_acm_observer.CONTRACT_ID
P332_AUTH_EXEC_RUN_ID_HEX = p332_stock_adapter.P332_RUN_ID_HEX
P332_AUTH_EXEC_COMMAND_COUNT = len(p332_logical_resident_exec_runtime.DEFAULT_COMMANDS)
P332_AUTH_EXEC_MAX_FRAME_PAYLOAD = p332_logical_resident_exec_runtime.MAX_FRAME_PAYLOAD
P332_AUTH_EXEC_FRAME_HEADER_SIZE = p332_logical_resident_exec_runtime.FRAME_HEADER_SIZE
P332_AUTH_EXEC_MAX_COMMANDS = p332_logical_resident_exec_runtime.MAX_COMMANDS
P332_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p332_logical_resident_exec_runtime.COMMAND_TIMEOUT_SEC
P332_AUTH_EXEC_MAX_OUTPUT_BYTES = p332_logical_resident_exec_runtime.MAX_OUTPUT_BYTES
P332_AUTH_EXEC_AUTH_ALGORITHM = P328_AUTH_EXEC_AUTH_ALGORITHM
P332_AUTH_EXEC_AUTH_TAG_SIZE = p332_logical_resident_exec_runtime.AUTH_TAG_SIZE
P332_AUTH_EXEC_AUTH_KEY_SCHEMA = P328_AUTH_EXEC_AUTH_KEY_SCHEMA
P332_AUTH_EXEC_AUTH_KEY_SIZE = p332_logical_resident_exec_runtime.AUTH_KEY_SIZE
P332_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P331_AUTH_EXEC_AUTH_KEY_IDENTITY)
P332_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p332_logical_resident_exec_runtime.DIAGNOSTIC_FRAME_TYPE
P332_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P330_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P332_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p332_logical_resident_exec_runtime.RNG_EAGAIN_RETRY_LIMIT
P332_AUTH_EXEC_SESSION_CAP = p332_logical_resident_exec_runtime.MAX_SESSIONS
P332_AUTH_EXEC_RECONNECT_CAP = p332_logical_resident_exec_runtime.MAX_RECONNECTS
P332_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P332_AUTHENTICATED_LOGICAL_RESIDENT_SAME_FD_AND_ROLLED_BACK"
)
P332_AUTH_EXEC_OUTCOME = (
    "p332_authenticated_logical_resident_same_fd_rollback_verified"
)
P332_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p332_authenticated_logical_resident_same_fd_unproved_rollback_verified"
)
P333_AUTH_EXEC_RUNTIME_CONTRACT_ID = p333_open_entry_diag_runtime.CONTRACT_ID
P333_AUTH_EXEC_OBSERVER_CONTRACT_ID = p333_open_entry_diag_acm_observer.CONTRACT_ID
P333_AUTH_EXEC_RUN_ID_HEX = p333_stock_adapter.P333_RUN_ID_HEX
P333_AUTH_EXEC_COMMAND_COUNT = len(p333_open_entry_diag_runtime.DEFAULT_COMMANDS)
P333_AUTH_EXEC_MAX_FRAME_PAYLOAD = p333_open_entry_diag_runtime.MAX_FRAME_PAYLOAD
P333_AUTH_EXEC_FRAME_HEADER_SIZE = p333_open_entry_diag_runtime.FRAME_HEADER_SIZE
P333_AUTH_EXEC_MAX_COMMANDS = p333_open_entry_diag_runtime.MAX_COMMANDS
P333_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p333_open_entry_diag_runtime.COMMAND_TIMEOUT_SEC
P333_AUTH_EXEC_MAX_OUTPUT_BYTES = p333_open_entry_diag_runtime.MAX_OUTPUT_BYTES
P333_AUTH_EXEC_AUTH_ALGORITHM = P332_AUTH_EXEC_AUTH_ALGORITHM
P333_AUTH_EXEC_AUTH_TAG_SIZE = p333_open_entry_diag_runtime.AUTH_TAG_SIZE
P333_AUTH_EXEC_AUTH_KEY_SCHEMA = P332_AUTH_EXEC_AUTH_KEY_SCHEMA
P333_AUTH_EXEC_AUTH_KEY_SIZE = p333_open_entry_diag_runtime.AUTH_KEY_SIZE
P333_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P332_AUTH_EXEC_AUTH_KEY_IDENTITY)
P333_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p333_open_entry_diag_runtime.DIAGNOSTIC_FRAME_TYPE
P333_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P332_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P333_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p333_open_entry_diag_runtime.RNG_EAGAIN_RETRY_LIMIT
P333_AUTH_EXEC_SESSION_CAP = p333_open_entry_diag_runtime.MAX_SESSIONS
P333_AUTH_EXEC_RECONNECT_CAP = p333_open_entry_diag_runtime.MAX_RECONNECTS
P333_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P333_AUTHENTICATED_LOGICAL_RESIDENT_OPEN_ENTRY_DIAGNOSTIC_AND_ROLLED_BACK"
)
P333_AUTH_EXEC_OUTCOME = (
    "p333_authenticated_logical_resident_open_entry_diagnostic_rollback_verified"
)
P333_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p333_authenticated_logical_resident_open_entry_diagnostic_unproved_rollback_verified"
)
P334_AUTH_EXEC_RUNTIME_CONTRACT_ID = p334_first_read_rc_runtime.CONTRACT_ID
P334_AUTH_EXEC_OBSERVER_CONTRACT_ID = p334_first_read_rc_acm_observer.CONTRACT_ID
P334_AUTH_EXEC_RUN_ID_HEX = p334_stock_adapter.P334_RUN_ID_HEX
P334_AUTH_EXEC_COMMAND_COUNT = len(p334_first_read_rc_runtime.DEFAULT_COMMANDS)
P334_AUTH_EXEC_MAX_FRAME_PAYLOAD = p334_first_read_rc_runtime.MAX_FRAME_PAYLOAD
P334_AUTH_EXEC_FRAME_HEADER_SIZE = p334_first_read_rc_runtime.FRAME_HEADER_SIZE
P334_AUTH_EXEC_MAX_COMMANDS = p334_first_read_rc_runtime.MAX_COMMANDS
P334_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p334_first_read_rc_runtime.COMMAND_TIMEOUT_SEC
P334_AUTH_EXEC_MAX_OUTPUT_BYTES = p334_first_read_rc_runtime.MAX_OUTPUT_BYTES
P334_AUTH_EXEC_AUTH_ALGORITHM = P333_AUTH_EXEC_AUTH_ALGORITHM
P334_AUTH_EXEC_AUTH_TAG_SIZE = p334_first_read_rc_runtime.AUTH_TAG_SIZE
P334_AUTH_EXEC_AUTH_KEY_SCHEMA = P333_AUTH_EXEC_AUTH_KEY_SCHEMA
P334_AUTH_EXEC_AUTH_KEY_SIZE = p334_first_read_rc_runtime.AUTH_KEY_SIZE
P334_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P333_AUTH_EXEC_AUTH_KEY_IDENTITY)
P334_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p334_first_read_rc_runtime.DIAGNOSTIC_FRAME_TYPE
P334_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P333_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P334_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p334_first_read_rc_runtime.RNG_EAGAIN_RETRY_LIMIT
P334_AUTH_EXEC_SESSION_CAP = p334_first_read_rc_runtime.MAX_SESSIONS
P334_AUTH_EXEC_RECONNECT_CAP = p334_first_read_rc_runtime.MAX_RECONNECTS
P334_AUTH_EXEC_DETAIL_PREFIX = p334_first_read_rc_runtime.P334_DETAIL_PREFIX
P334_AUTH_EXEC_DETAIL_SENTINEL = p334_first_read_rc_runtime.P334_DETAIL_SENTINEL
P334_AUTH_EXEC_MAX_ENCODED_ERRNO = p334_first_read_rc_runtime.P334_MAX_ENCODED_ERRNO
P334_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P334_AUTHENTICATED_LOGICAL_RESIDENT_FIRST_CONSOLE_RETURN_AND_ROLLED_BACK"
)
P334_AUTH_EXEC_OUTCOME = (
    "p334_authenticated_logical_resident_first_console_return_rollback_verified"
)
P334_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p334_authenticated_logical_resident_first_console_return_unproved_rollback_verified"
)
P335_AUTH_EXEC_RUNTIME_CONTRACT_ID = p335_retained_listener_runtime.CONTRACT_ID
P335_AUTH_EXEC_OBSERVER_CONTRACT_ID = p335_retained_listener_acm_observer.CONTRACT_ID
P335_AUTH_EXEC_RUN_ID_HEX = p335_stock_adapter.P335_RUN_ID_HEX
P335_AUTH_EXEC_COMMAND_COUNT = len(p335_retained_listener_runtime.DEFAULT_COMMANDS)
P335_AUTH_EXEC_MAX_FRAME_PAYLOAD = p335_retained_listener_runtime.MAX_FRAME_PAYLOAD
P335_AUTH_EXEC_FRAME_HEADER_SIZE = p335_retained_listener_runtime.FRAME_HEADER_SIZE
P335_AUTH_EXEC_MAX_COMMANDS = p335_retained_listener_runtime.MAX_COMMANDS
P335_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p335_retained_listener_runtime.COMMAND_TIMEOUT_SEC
P335_AUTH_EXEC_MAX_OUTPUT_BYTES = p335_retained_listener_runtime.MAX_OUTPUT_BYTES
P335_AUTH_EXEC_AUTH_ALGORITHM = P334_AUTH_EXEC_AUTH_ALGORITHM
P335_AUTH_EXEC_AUTH_TAG_SIZE = p335_retained_listener_runtime.AUTH_TAG_SIZE
P335_AUTH_EXEC_AUTH_KEY_SCHEMA = P334_AUTH_EXEC_AUTH_KEY_SCHEMA
P335_AUTH_EXEC_AUTH_KEY_SIZE = p335_retained_listener_runtime.AUTH_KEY_SIZE
P335_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P334_AUTH_EXEC_AUTH_KEY_IDENTITY)
P335_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p335_retained_listener_runtime.DIAGNOSTIC_FRAME_TYPE
P335_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P334_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P335_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p335_retained_listener_runtime.RNG_EAGAIN_RETRY_LIMIT
P335_AUTH_EXEC_SESSION_CAP = p335_retained_listener_acm_observer.MAX_SESSIONS
P335_AUTH_EXEC_RECONNECT_CAP = p335_retained_listener_acm_observer.MAX_RECONNECTS
P335_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P335_AUTHENTICATED_ATTENDED_RESIDENT_AND_ROLLED_BACK"
)
P335_AUTH_EXEC_OUTCOME = (
    "p335_authenticated_attended_resident_rollback_verified"
)
P335_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p335_authenticated_attended_resident_unproved_rollback_verified"
)
P336_AUTH_EXEC_RUNTIME_CONTRACT_ID = p336_long_idle_runtime.CONTRACT_ID
P336_AUTH_EXEC_OBSERVER_CONTRACT_ID = p336_long_idle_acm_observer.CONTRACT_ID
P336_AUTH_EXEC_RUN_ID_HEX = p336_stock_adapter.P336_RUN_ID_HEX
P336_AUTH_EXEC_COMMAND_COUNT = len(p336_long_idle_runtime.DEFAULT_COMMANDS)
P336_AUTH_EXEC_MAX_FRAME_PAYLOAD = p336_long_idle_runtime.MAX_FRAME_PAYLOAD
P336_AUTH_EXEC_FRAME_HEADER_SIZE = p336_long_idle_runtime.FRAME_HEADER_SIZE
P336_AUTH_EXEC_MAX_COMMANDS = p336_long_idle_runtime.MAX_COMMANDS
P336_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p336_long_idle_runtime.COMMAND_TIMEOUT_SEC
P336_AUTH_EXEC_MAX_OUTPUT_BYTES = p336_long_idle_runtime.MAX_OUTPUT_BYTES
P336_AUTH_EXEC_AUTH_ALGORITHM = P335_AUTH_EXEC_AUTH_ALGORITHM
P336_AUTH_EXEC_AUTH_TAG_SIZE = p336_long_idle_runtime.AUTH_TAG_SIZE
P336_AUTH_EXEC_AUTH_KEY_SCHEMA = P335_AUTH_EXEC_AUTH_KEY_SCHEMA
P336_AUTH_EXEC_AUTH_KEY_SIZE = p336_long_idle_runtime.AUTH_KEY_SIZE
P336_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P335_AUTH_EXEC_AUTH_KEY_IDENTITY)
P336_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p336_long_idle_runtime.DIAGNOSTIC_FRAME_TYPE
P336_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P335_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P336_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p336_long_idle_runtime.RNG_EAGAIN_RETRY_LIMIT
P336_AUTH_EXEC_SESSION_CAP = p336_long_idle_acm_observer.MAX_SESSIONS
P336_AUTH_EXEC_RECONNECT_CAP = p336_long_idle_acm_observer.MAX_RECONNECTS
P336_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P336_AUTHENTICATED_LONG_IDLE_RESIDENT_AND_ROLLED_BACK"
)
P336_AUTH_EXEC_OUTCOME = (
    "p336_authenticated_long_idle_resident_rollback_verified"
)
P336_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p336_authenticated_long_idle_resident_unproved_rollback_verified"
)
P337_AUTH_EXEC_RUNTIME_CONTRACT_ID = p337_open_read_diag_runtime.CONTRACT_ID
P337_AUTH_EXEC_OBSERVER_CONTRACT_ID = p337_open_read_diag_acm_observer.CONTRACT_ID
P337_AUTH_EXEC_RUN_ID_HEX = p337_stock_adapter.P337_RUN_ID_HEX
P337_AUTH_EXEC_COMMAND_COUNT = len(p337_open_read_diag_runtime.DEFAULT_COMMANDS)
P337_AUTH_EXEC_MAX_FRAME_PAYLOAD = p337_open_read_diag_runtime.MAX_FRAME_PAYLOAD
P337_AUTH_EXEC_FRAME_HEADER_SIZE = p337_open_read_diag_runtime.FRAME_HEADER_SIZE
P337_AUTH_EXEC_MAX_COMMANDS = p337_open_read_diag_runtime.MAX_COMMANDS
P337_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p337_open_read_diag_runtime.COMMAND_TIMEOUT_SEC
P337_AUTH_EXEC_MAX_OUTPUT_BYTES = p337_open_read_diag_runtime.MAX_OUTPUT_BYTES
P337_AUTH_EXEC_AUTH_ALGORITHM = P336_AUTH_EXEC_AUTH_ALGORITHM
P337_AUTH_EXEC_AUTH_TAG_SIZE = p337_open_read_diag_runtime.AUTH_TAG_SIZE
P337_AUTH_EXEC_AUTH_KEY_SCHEMA = P336_AUTH_EXEC_AUTH_KEY_SCHEMA
P337_AUTH_EXEC_AUTH_KEY_SIZE = p337_open_read_diag_runtime.AUTH_KEY_SIZE
P337_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P336_AUTH_EXEC_AUTH_KEY_IDENTITY)
P337_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p337_open_read_diag_runtime.DIAGNOSTIC_FRAME_TYPE
P337_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P336_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P337_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p337_open_read_diag_runtime.RNG_EAGAIN_RETRY_LIMIT
P337_AUTH_EXEC_SESSION_CAP = p337_open_read_diag_acm_observer.MAX_SESSIONS
P337_AUTH_EXEC_RECONNECT_CAP = p337_open_read_diag_acm_observer.MAX_RECONNECTS
P337_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P337_AUTHENTICATED_RESIDENT_OPEN_READ_DIAGNOSTIC_AND_ROLLED_BACK"
)
P337_AUTH_EXEC_OUTCOME = (
    "p337_authenticated_resident_open_read_diagnostic_rollback_verified"
)
P337_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p337_authenticated_resident_open_read_diagnostic_unproved_rollback_verified"
)
P338_AUTH_EXEC_RUNTIME_CONTRACT_ID = p338_open_read_branch_runtime.CONTRACT_ID
P338_AUTH_EXEC_OBSERVER_CONTRACT_ID = p338_open_read_branch_acm_observer.CONTRACT_ID
P338_AUTH_EXEC_RUN_ID_HEX = p338_stock_adapter.P338_RUN_ID_HEX
P338_AUTH_EXEC_COMMAND_COUNT = len(p338_open_read_branch_runtime.DEFAULT_COMMANDS)
P338_AUTH_EXEC_MAX_FRAME_PAYLOAD = p338_open_read_branch_runtime.MAX_FRAME_PAYLOAD
P338_AUTH_EXEC_FRAME_HEADER_SIZE = p338_open_read_branch_runtime.FRAME_HEADER_SIZE
P338_AUTH_EXEC_MAX_COMMANDS = p338_open_read_branch_runtime.MAX_COMMANDS
P338_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p338_open_read_branch_runtime.COMMAND_TIMEOUT_SEC
P338_AUTH_EXEC_MAX_OUTPUT_BYTES = p338_open_read_branch_runtime.MAX_OUTPUT_BYTES
P338_AUTH_EXEC_AUTH_ALGORITHM = P337_AUTH_EXEC_AUTH_ALGORITHM
P338_AUTH_EXEC_AUTH_TAG_SIZE = p338_open_read_branch_runtime.AUTH_TAG_SIZE
P338_AUTH_EXEC_AUTH_KEY_SCHEMA = P337_AUTH_EXEC_AUTH_KEY_SCHEMA
P338_AUTH_EXEC_AUTH_KEY_SIZE = p338_open_read_branch_runtime.AUTH_KEY_SIZE
P338_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P337_AUTH_EXEC_AUTH_KEY_IDENTITY)
P338_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p338_open_read_branch_runtime.DIAGNOSTIC_FRAME_TYPE
P338_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P337_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P338_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p338_open_read_branch_runtime.RNG_EAGAIN_RETRY_LIMIT
P338_AUTH_EXEC_SESSION_CAP = p338_open_read_branch_acm_observer.MAX_SESSIONS
P338_AUTH_EXEC_RECONNECT_CAP = p338_open_read_branch_acm_observer.MAX_RECONNECTS
P338_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS = dict(
    (str(key), value)
    for key, value in p338_open_read_branch_runtime.OPEN_READ_BRANCHES.items()
)
P338_AUTH_EXEC_OPEN_READ_BRANCH_COUNT = len(P338_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS)
P338_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P338_AUTHENTICATED_RESIDENT_OPEN_READ_BRANCH_AND_ROLLED_BACK"
)
P338_AUTH_EXEC_OUTCOME = (
    "p338_authenticated_resident_open_read_branch_rollback_verified"
)
P338_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p338_authenticated_resident_open_read_branch_unproved_rollback_verified"
)
P339_AUTH_EXEC_RUNTIME_CONTRACT_ID = p339_open_read_branch_runtime.CONTRACT_ID
P339_AUTH_EXEC_OBSERVER_CONTRACT_ID = p339_open_read_branch_acm_observer.CONTRACT_ID
P339_AUTH_EXEC_RUN_ID_HEX = p339_stock_adapter.P339_RUN_ID_HEX
P339_AUTH_EXEC_COMMAND_COUNT = len(p339_open_read_branch_runtime.DEFAULT_COMMANDS)
P339_AUTH_EXEC_MAX_FRAME_PAYLOAD = p339_open_read_branch_runtime.MAX_FRAME_PAYLOAD
P339_AUTH_EXEC_FRAME_HEADER_SIZE = p339_open_read_branch_runtime.FRAME_HEADER_SIZE
P339_AUTH_EXEC_MAX_COMMANDS = p339_open_read_branch_runtime.MAX_COMMANDS
P339_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p339_open_read_branch_runtime.COMMAND_TIMEOUT_SEC
P339_AUTH_EXEC_MAX_OUTPUT_BYTES = p339_open_read_branch_runtime.MAX_OUTPUT_BYTES
P339_AUTH_EXEC_AUTH_ALGORITHM = P338_AUTH_EXEC_AUTH_ALGORITHM
P339_AUTH_EXEC_AUTH_TAG_SIZE = p339_open_read_branch_runtime.AUTH_TAG_SIZE
P339_AUTH_EXEC_AUTH_KEY_SCHEMA = P338_AUTH_EXEC_AUTH_KEY_SCHEMA
P339_AUTH_EXEC_AUTH_KEY_SIZE = p339_open_read_branch_runtime.AUTH_KEY_SIZE
P339_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(P338_AUTH_EXEC_AUTH_KEY_IDENTITY)
P339_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p339_open_read_branch_runtime.DIAGNOSTIC_FRAME_TYPE
P339_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P338_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P339_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p339_open_read_branch_runtime.RNG_EAGAIN_RETRY_LIMIT
P339_AUTH_EXEC_SESSION_CAP = p339_open_read_branch_acm_observer.MAX_SESSIONS
P339_AUTH_EXEC_RECONNECT_CAP = p339_open_read_branch_acm_observer.MAX_RECONNECTS
P339_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS = {
    str(key): value for key, value in p339_open_read_branch_runtime.OPEN_READ_BRANCHES.items()
}
P339_AUTH_EXEC_OPEN_READ_BRANCH_COUNT = len(P339_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS)
P339_AUTH_EXEC_OPEN_HEADER_WORD_STAGES = list(
    p339_open_read_branch_runtime.OPEN_HEADER_WORD_STAGES
)
P339_AUTH_EXEC_OPEN_HEADER_SIZE = p339_open_read_branch_runtime.OPEN_HEADER_SIZE
P339_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P339_AUTHENTICATED_RESIDENT_OPEN_HEADER_CAPTURE_AND_ROLLED_BACK"
)
P339_AUTH_EXEC_OUTCOME = (
    "p339_authenticated_resident_open_header_capture_rollback_verified"
)
P339_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p339_authenticated_resident_open_header_capture_unproved_rollback_verified"
)
P340_AUTH_EXEC_RUNTIME_CONTRACT_ID = p340_open_read_branch_runtime.CONTRACT_ID
P340_AUTH_EXEC_OBSERVER_CONTRACT_ID = p340_open_read_branch_acm_observer.CONTRACT_ID
P340_AUTH_EXEC_RUN_ID_HEX = p340_stock_adapter.P340_RUN_ID_HEX
P340_AUTH_EXEC_COMMAND_COUNT = len(p340_open_read_branch_runtime.DEFAULT_COMMANDS)
P340_AUTH_EXEC_MAX_FRAME_PAYLOAD = p340_open_read_branch_runtime.MAX_FRAME_PAYLOAD
P340_AUTH_EXEC_FRAME_HEADER_SIZE = p340_open_read_branch_runtime.FRAME_HEADER_SIZE
P340_AUTH_EXEC_MAX_COMMANDS = p340_open_read_branch_runtime.MAX_COMMANDS
P340_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p340_open_read_branch_runtime.COMMAND_TIMEOUT_SEC
P340_AUTH_EXEC_MAX_OUTPUT_BYTES = p340_open_read_branch_runtime.MAX_OUTPUT_BYTES
P340_AUTH_EXEC_AUTH_ALGORITHM = P339_AUTH_EXEC_AUTH_ALGORITHM
P340_AUTH_EXEC_AUTH_TAG_SIZE = p340_open_read_branch_runtime.AUTH_TAG_SIZE
P340_AUTH_EXEC_AUTH_KEY_SCHEMA = P339_AUTH_EXEC_AUTH_KEY_SCHEMA
P340_AUTH_EXEC_AUTH_KEY_SIZE = p340_open_read_branch_runtime.AUTH_KEY_SIZE
P340_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(
    p340_artifact_identity.auth_key_identity()
)
P340_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p340_open_read_branch_runtime.DIAGNOSTIC_FRAME_TYPE
P340_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P339_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P340_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p340_open_read_branch_runtime.RNG_EAGAIN_RETRY_LIMIT
P340_AUTH_EXEC_SESSION_CAP = p340_open_read_branch_acm_observer.MAX_SESSIONS
P340_AUTH_EXEC_RECONNECT_CAP = p340_open_read_branch_acm_observer.MAX_RECONNECTS
P340_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS = {
    str(key): value
    for key, value in p340_open_read_branch_runtime.OPEN_READ_BRANCHES.items()
}
P340_AUTH_EXEC_OPEN_READ_BRANCH_COUNT = len(P340_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS)
P340_AUTH_EXEC_OPEN_HEADER_WORD_STAGES = list(
    p340_open_read_branch_runtime.OPEN_HEADER_WORD_STAGES
)
P340_AUTH_EXEC_OPEN_HEADER_SIZE = p340_open_read_branch_runtime.OPEN_HEADER_SIZE
P340_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P340_AUTHENTICATED_RESIDENT_OPEN_HEADER_CAPTURE_AND_ROLLED_BACK"
)
P340_AUTH_EXEC_OUTCOME = (
    "p340_authenticated_resident_open_header_capture_rollback_verified"
)
P340_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p340_authenticated_resident_open_header_capture_unproved_rollback_verified"
)
P341_AUTH_EXEC_RUNTIME_CONTRACT_ID = p341_open_read_branch_runtime.CONTRACT_ID
P341_AUTH_EXEC_OBSERVER_CONTRACT_ID = p341_open_read_branch_acm_observer.CONTRACT_ID
P341_AUTH_EXEC_RUN_ID_HEX = p341_stock_adapter.P341_RUN_ID_HEX
P341_AUTH_EXEC_COMMAND_COUNT = len(p341_open_read_branch_runtime.DEFAULT_COMMANDS)
P341_AUTH_EXEC_MAX_FRAME_PAYLOAD = p341_open_read_branch_runtime.MAX_FRAME_PAYLOAD
P341_AUTH_EXEC_FRAME_HEADER_SIZE = p341_open_read_branch_runtime.FRAME_HEADER_SIZE
P341_AUTH_EXEC_MAX_COMMANDS = p341_open_read_branch_runtime.MAX_COMMANDS
P341_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p341_open_read_branch_runtime.COMMAND_TIMEOUT_SEC
P341_AUTH_EXEC_MAX_OUTPUT_BYTES = p341_open_read_branch_runtime.MAX_OUTPUT_BYTES
P341_AUTH_EXEC_AUTH_ALGORITHM = P340_AUTH_EXEC_AUTH_ALGORITHM
P341_AUTH_EXEC_AUTH_TAG_SIZE = p341_open_read_branch_runtime.AUTH_TAG_SIZE
P341_AUTH_EXEC_AUTH_KEY_SCHEMA = P340_AUTH_EXEC_AUTH_KEY_SCHEMA
P341_AUTH_EXEC_AUTH_KEY_SIZE = p341_open_read_branch_runtime.AUTH_KEY_SIZE
P341_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(
    p341_artifact_identity.auth_key_identity()
)
P341_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = p341_open_read_branch_runtime.DIAGNOSTIC_FRAME_TYPE
P341_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P340_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P341_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = p341_open_read_branch_runtime.RNG_EAGAIN_RETRY_LIMIT
P341_AUTH_EXEC_SESSION_CAP = p341_open_read_branch_acm_observer.MAX_SESSIONS
P341_AUTH_EXEC_RECONNECT_CAP = p341_open_read_branch_acm_observer.MAX_RECONNECTS
P341_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS = {
    str(key): value
    for key, value in p341_open_read_branch_runtime.OPEN_READ_BRANCHES.items()
}
P341_AUTH_EXEC_OPEN_READ_BRANCH_COUNT = len(P341_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS)
P341_AUTH_EXEC_OPEN_HEADER_WORD_STAGES = list(
    p341_open_read_branch_runtime.OPEN_HEADER_WORD_STAGES
)
P341_AUTH_EXEC_OPEN_HEADER_SIZE = p341_open_read_branch_runtime.OPEN_HEADER_SIZE
P341_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P341_AUTHENTICATED_RESIDENT_OPEN_HEADER_CAPTURE_AND_ROLLED_BACK"
)
P341_AUTH_EXEC_OUTCOME = (
    "p341_authenticated_resident_open_header_capture_rollback_verified"
)
P341_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p341_authenticated_resident_open_header_capture_unproved_rollback_verified"
)
P342_AUTH_EXEC_RUNTIME_CONTRACT_ID = p342_open_read_branch_runtime.CONTRACT_ID
P342_AUTH_EXEC_OBSERVER_CONTRACT_ID = p342_open_read_branch_acm_observer.CONTRACT_ID
P342_AUTH_EXEC_RUN_ID_HEX = p342_open_read_branch_runtime.P342_RUN_ID_HEX
P342_AUTH_EXEC_COMMAND_COUNT = len(p342_open_read_branch_runtime.DEFAULT_COMMANDS)
P342_AUTH_EXEC_MAX_FRAME_PAYLOAD = p342_open_read_branch_runtime.MAX_FRAME_PAYLOAD
P342_AUTH_EXEC_FRAME_HEADER_SIZE = p342_open_read_branch_runtime.FRAME_HEADER_SIZE
P342_AUTH_EXEC_MAX_COMMANDS = p342_open_read_branch_runtime.MAX_COMMANDS
P342_AUTH_EXEC_COMMAND_TIMEOUT_SEC = p342_open_read_branch_runtime.COMMAND_TIMEOUT_SEC
P342_AUTH_EXEC_MAX_OUTPUT_BYTES = p342_open_read_branch_runtime.MAX_OUTPUT_BYTES
P342_AUTH_EXEC_AUTH_ALGORITHM = P341_AUTH_EXEC_AUTH_ALGORITHM
P342_AUTH_EXEC_AUTH_TAG_SIZE = p342_open_read_branch_runtime.AUTH_TAG_SIZE
P342_AUTH_EXEC_AUTH_KEY_SCHEMA = P341_AUTH_EXEC_AUTH_KEY_SCHEMA
P342_AUTH_EXEC_AUTH_KEY_SIZE = p342_open_read_branch_runtime.AUTH_KEY_SIZE
# P342 keeps the authenticated wire key unchanged; its fresh artifact helper
# reopens the exact private key identity without publishing key bytes.
P342_AUTH_EXEC_AUTH_KEY_IDENTITY = dict(
    p342_artifact_identity.auth_key_identity()
)
P342_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE = (
    p342_open_read_branch_runtime.DIAGNOSTIC_FRAME_TYPE
)
P342_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE = P341_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE
P342_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT = (
    p342_open_read_branch_runtime.RNG_EAGAIN_RETRY_LIMIT
)
P342_AUTH_EXEC_SESSION_CAP = p342_open_read_branch_acm_observer.MAX_SESSIONS
P342_AUTH_EXEC_RECONNECT_CAP = p342_open_read_branch_acm_observer.MAX_RECONNECTS
P342_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS = {
    str(key): value
    for key, value in p342_open_read_branch_runtime.OPEN_READ_BRANCHES.items()
}
P342_AUTH_EXEC_OPEN_READ_BRANCH_COUNT = len(P342_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS)
P342_AUTH_EXEC_OPEN_HEADER_WORD_STAGES = list(
    p342_open_read_branch_runtime.OPEN_HEADER_WORD_STAGES
)
P342_AUTH_EXEC_OPEN_HEADER_SIZE = p342_open_read_branch_runtime.OPEN_HEADER_SIZE
P342_AUTH_EXEC_VERDICT = (
    "PASS_F1_V2_P342_AUTHENTICATED_RESIDENT_OPEN_HEADER_IDLE_REUSE_AND_ROLLED_BACK"
)
P342_AUTH_EXEC_OUTCOME = (
    "p342_authenticated_resident_open_header_idle_reuse_rollback_verified"
)
P342_AUTH_EXEC_NO_PROOF_OUTCOME = (
    "p342_authenticated_resident_open_header_idle_reuse_unproved_rollback_verified"
)
# P342's only new proof material is the host-side timing receipt.  It does
# not create or activate a resident/later-action lease.
P342_IDLE_REUSE_PHASE = "same-fd-idle"
P342_IDLE_REUSE_BEFORE_SESSION_INDEX = 2
P342_IDLE_REUSE_REQUESTED_SECONDS = 120
P342_IDLE_REUSE_MIN_ELAPSED_SECONDS = 120
P342_IDLE_REUSE_MAX_ELAPSED_SECONDS = 180
P342_SAME_FD_SESSION_COUNT = 3
P342_TOTAL_SESSION_COUNT = 4
P342_TOTAL_COMMAND_COUNT = (
    P342_TOTAL_SESSION_COUNT * P342_AUTH_EXEC_COMMAND_COUNT
)
P342_PHYSICAL_REOPEN_INDEXES = (0, 0, 0, 1)
CHECKPOINT_DECODER = "s22plus_fyg8_r4w1e_checkpoint_v1"
PID1_USERSPACE_DECODER = "s22plus_fyg8_r4w1e0_pid1_userspace_v1"
SAME_RING_DECODER = "s22plus_fyg8_p219_same_ring_v1"
SAME_RING_MULTIBOOT_DECODER = "s22plus_fyg8_p230_same_ring_multiboot_v1"
E1_LATEST_STAGE_DECODER = e1_latest_stage.DECODER_ID
E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p234_run_manifest_v1"
E1_LATEST_STAGE_STATIC_SCHEMA = "s22plus_fyg8_p234_process_v2_static_result_v1"
E1_LATEST_STAGE_STATIC_VERDICT = "PASS_P234_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION"
E1_LATEST_STAGE_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p234_candidate_static_checker_v1"
)
E1_LATEST_STAGE_CANDIDATE_STATIC_VERDICT = (
    "PASS_P234_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P286_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p286_candidate_static_checker_v1"
)
P286_CANDIDATE_STATIC_VERDICT = (
    "PASS_P286_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P286_SOURCE_CONTRACT_ID = p286_e2_closure.source_contract.CONTRACT_ID
P288_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p288_candidate_static_checker_v1"
)
P288_CANDIDATE_STATIC_VERDICT = (
    "PASS_P288_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P288_SOURCE_CONTRACT_ID = p288_e2_closure.source_contract.CONTRACT_ID
P290_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p290_candidate_static_checker_v1"
)
P290_CANDIDATE_STATIC_VERDICT = (
    "PASS_P290_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P290_SOURCE_CONTRACT_ID = p290_e2_closure.source_contract.CONTRACT_ID
P292_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p292_candidate_static_checker_v1"
)
P292_CANDIDATE_STATIC_VERDICT = (
    "PASS_P292_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P292_SOURCE_CONTRACT_ID = p292_e2_closure.source_contract.CONTRACT_ID
P294_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p294_candidate_static_checker_v1"
)
P294_CANDIDATE_STATIC_VERDICT = (
    "PASS_P294_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P294_SOURCE_CONTRACT_ID = p294_e2_closure.source_contract.CONTRACT_ID
P296_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p296_candidate_static_checker_v1"
)
P296_CANDIDATE_STATIC_VERDICT = (
    "PASS_P296_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P296_SOURCE_CONTRACT_ID = p296_e2_closure.source_contract.CONTRACT_ID
P298_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p298_candidate_static_checker_v1"
)
P298_CANDIDATE_STATIC_VERDICT = (
    "PASS_P298_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P298_SOURCE_CONTRACT_ID = p298_e2_closure.source_contract.CONTRACT_ID
P300_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p300_candidate_static_checker_v1"
)
P300_CANDIDATE_STATIC_VERDICT = (
    "PASS_P300_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P300_SOURCE_CONTRACT_ID = p300_e2_closure.source_contract.CONTRACT_ID
P310_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p310_candidate_static_checker_v1"
)
P310_CANDIDATE_STATIC_VERDICT = (
    "PASS_P310_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P310_SOURCE_CONTRACT_ID = p310_source_contract.CONTRACT_ID
P301_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p301_candidate_static_checker_v1"
)
P301_CANDIDATE_STATIC_VERDICT = (
    "PASS_P301_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P301_OVERLAY_CONTRACT_ID = p301_overlay.CONTRACT_ID
P302_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p302_candidate_static_checker_v1"
)
P302_CANDIDATE_STATIC_VERDICT = (
    "PASS_P302_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P302_OVERLAY_CONTRACT_ID = p302_overlay.CONTRACT_ID
P303_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p303_candidate_static_checker_v1"
)
P303_CANDIDATE_STATIC_VERDICT = (
    "PASS_P303_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P303_OVERLAY_CONTRACT_ID = p303_overlay.CONTRACT_ID
P304_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p304_candidate_static_checker_v1"
)
P304_CANDIDATE_STATIC_VERDICT = (
    "PASS_P304_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P304_OVERLAY_CONTRACT_ID = p304_overlay.CONTRACT_ID
P305_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p305_candidate_static_checker_v1"
)
P305_CANDIDATE_STATIC_VERDICT = (
    "PASS_P305_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P305_OVERLAY_CONTRACT_ID = p305_overlay.CONTRACT_ID
P306_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p306_candidate_static_checker_v1"
)
P306_CANDIDATE_STATIC_VERDICT = (
    "PASS_P306_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P306_OVERLAY_CONTRACT_ID = p306_overlay.CONTRACT_ID
P307_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p307_candidate_static_checker_v1"
)
P307_CANDIDATE_STATIC_VERDICT = (
    "PASS_P307_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P307_OVERLAY_CONTRACT_ID = p307_overlay.CONTRACT_ID
P308_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p308_candidate_static_checker_v1"
)
P308_CANDIDATE_STATIC_VERDICT = (
    "PASS_P308_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P308_OVERLAY_CONTRACT_ID = p308_overlay.CONTRACT_ID
P311_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p311_candidate_static_checker_v1"
)
P311_CANDIDATE_STATIC_VERDICT = (
    "PASS_P311_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P311_OVERLAY_CONTRACT_ID = p311_overlay.CONTRACT_ID
P312_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p312_candidate_static_checker_v1"
)
P312_CANDIDATE_STATIC_VERDICT = (
    "PASS_P312_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P312_OVERLAY_CONTRACT_ID = p312_overlay.CONTRACT_ID
P313_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p313_candidate_static_checker_v1"
)
P313_CANDIDATE_STATIC_VERDICT = (
    "PASS_P313_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P313_OVERLAY_CONTRACT_ID = p313_overlay.CONTRACT_ID
P314_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p314_candidate_static_checker_v1"
)
P314_CANDIDATE_STATIC_VERDICT = (
    "PASS_P314_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P314_OVERLAY_CONTRACT_ID = p314_overlay.CONTRACT_ID
P315_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p315_candidate_static_checker_v1"
)
P315_CANDIDATE_STATIC_VERDICT = (
    "PASS_P315_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P315_OVERLAY_CONTRACT_ID = p315_overlay.CONTRACT_ID
MAX77705_OVERLAY_CONTRACT_ID = max77705_decoder.OVERLAY_CONTRACT_ID
P317_MAX77705_OVERLAY_CONTRACT_ID = p317_max77705_decoder.OVERLAY_CONTRACT_ID
P318_MAX77705_OVERLAY_CONTRACT_ID = p318_max77705_decoder.OVERLAY_CONTRACT_ID
P319_STOCK_OVERLAY_CONTRACT_ID = p319_stock_adapter.OVERLAY_CONTRACT_ID
P319_STOCK_OVERLAY_IDS = frozenset({P319_STOCK_OVERLAY_CONTRACT_ID})
P320_STOCK_OVERLAY_CONTRACT_ID = p320_stock_adapter.OVERLAY_CONTRACT_ID
P320_STOCK_OVERLAY_IDS = frozenset({P320_STOCK_OVERLAY_CONTRACT_ID})
P321_STOCK_OVERLAY_CONTRACT_ID = p321_stock_adapter.OVERLAY_CONTRACT_ID
P321_STOCK_OVERLAY_IDS = frozenset({P321_STOCK_OVERLAY_CONTRACT_ID})
P322_STOCK_OVERLAY_CONTRACT_ID = p322_stock_adapter.OVERLAY_CONTRACT_ID
P322_STOCK_OVERLAY_IDS = frozenset({P322_STOCK_OVERLAY_CONTRACT_ID})
P323_STOCK_OVERLAY_CONTRACT_ID = p323_stock_adapter.OVERLAY_CONTRACT_ID
P323_STOCK_OVERLAY_IDS = frozenset({P323_STOCK_OVERLAY_CONTRACT_ID})
P324_STOCK_OVERLAY_CONTRACT_ID = p324_stock_adapter.OVERLAY_CONTRACT_ID
P324_STOCK_OVERLAY_IDS = frozenset({P324_STOCK_OVERLAY_CONTRACT_ID})
P325_STOCK_OVERLAY_CONTRACT_ID = p325_stock_adapter.OVERLAY_CONTRACT_ID
P325_STOCK_OVERLAY_IDS = frozenset({P325_STOCK_OVERLAY_CONTRACT_ID})
P326_STOCK_OVERLAY_CONTRACT_ID = p326_stock_adapter.OVERLAY_CONTRACT_ID
P326_STOCK_OVERLAY_IDS = frozenset({P326_STOCK_OVERLAY_CONTRACT_ID})
P327_STOCK_OVERLAY_CONTRACT_ID = p327_stock_adapter.OVERLAY_CONTRACT_ID
P327_STOCK_OVERLAY_IDS = frozenset({P327_STOCK_OVERLAY_CONTRACT_ID})
P328_STOCK_OVERLAY_CONTRACT_ID = p328_stock_adapter.OVERLAY_CONTRACT_ID
P328_STOCK_OVERLAY_IDS = frozenset({P328_STOCK_OVERLAY_CONTRACT_ID})
P329_STOCK_OVERLAY_CONTRACT_ID = p329_stock_adapter.OVERLAY_CONTRACT_ID
P329_STOCK_OVERLAY_IDS = frozenset({P329_STOCK_OVERLAY_CONTRACT_ID})
P330_STOCK_OVERLAY_CONTRACT_ID = p330_stock_adapter.OVERLAY_CONTRACT_ID
P330_STOCK_OVERLAY_IDS = frozenset({P330_STOCK_OVERLAY_CONTRACT_ID})
P331_STOCK_OVERLAY_CONTRACT_ID = p331_stock_adapter.OVERLAY_CONTRACT_ID
P331_STOCK_OVERLAY_IDS = frozenset({P331_STOCK_OVERLAY_CONTRACT_ID})
P332_STOCK_OVERLAY_CONTRACT_ID = p332_stock_adapter.OVERLAY_CONTRACT_ID
P332_STOCK_OVERLAY_IDS = frozenset({P332_STOCK_OVERLAY_CONTRACT_ID})
P333_STOCK_OVERLAY_CONTRACT_ID = p333_stock_adapter.OVERLAY_CONTRACT_ID
P333_STOCK_OVERLAY_IDS = frozenset({P333_STOCK_OVERLAY_CONTRACT_ID})
P334_STOCK_OVERLAY_CONTRACT_ID = p334_stock_adapter.OVERLAY_CONTRACT_ID
P334_STOCK_OVERLAY_IDS = frozenset({P334_STOCK_OVERLAY_CONTRACT_ID})
P335_STOCK_OVERLAY_CONTRACT_ID = p335_stock_adapter.OVERLAY_CONTRACT_ID
P335_STOCK_OVERLAY_IDS = frozenset({P335_STOCK_OVERLAY_CONTRACT_ID})
P336_STOCK_OVERLAY_CONTRACT_ID = p336_stock_adapter.OVERLAY_CONTRACT_ID
P336_STOCK_OVERLAY_IDS = frozenset({P336_STOCK_OVERLAY_CONTRACT_ID})
P337_STOCK_OVERLAY_CONTRACT_ID = p337_stock_adapter.OVERLAY_CONTRACT_ID
P337_STOCK_OVERLAY_IDS = frozenset({P337_STOCK_OVERLAY_CONTRACT_ID})
P338_STOCK_OVERLAY_CONTRACT_ID = p338_stock_adapter.OVERLAY_CONTRACT_ID
P338_STOCK_OVERLAY_IDS = frozenset({P338_STOCK_OVERLAY_CONTRACT_ID})
P339_STOCK_OVERLAY_CONTRACT_ID = p339_stock_adapter.OVERLAY_CONTRACT_ID
P339_STOCK_OVERLAY_IDS = frozenset({P339_STOCK_OVERLAY_CONTRACT_ID})
P340_STOCK_OVERLAY_CONTRACT_ID = p340_stock_adapter.OVERLAY_CONTRACT_ID
P340_STOCK_OVERLAY_IDS = frozenset({P340_STOCK_OVERLAY_CONTRACT_ID})
P341_STOCK_OVERLAY_CONTRACT_ID = p341_stock_adapter.OVERLAY_CONTRACT_ID
P341_STOCK_OVERLAY_IDS = frozenset({P341_STOCK_OVERLAY_CONTRACT_ID})
# P342 is intentionally not accepted through the P341 overlay or run ID.  The
# adapter owns the same wire/parser lineage but receives this distinct public
# overlay namespace when its source module is loaded.
P342_STOCK_OVERLAY_CONTRACT_ID = p342_stock_adapter.OVERLAY_CONTRACT_ID
P342_STOCK_OVERLAY_IDS = frozenset({P342_STOCK_OVERLAY_CONTRACT_ID})
STOCK_ADAPTERS = {
    P319_STOCK_OVERLAY_CONTRACT_ID: p319_stock_adapter,
    P320_STOCK_OVERLAY_CONTRACT_ID: p320_stock_adapter,
    P321_STOCK_OVERLAY_CONTRACT_ID: p321_stock_adapter,
    P322_STOCK_OVERLAY_CONTRACT_ID: p322_stock_adapter,
    P323_STOCK_OVERLAY_CONTRACT_ID: p323_stock_adapter,
    P324_STOCK_OVERLAY_CONTRACT_ID: p324_stock_adapter,
    P325_STOCK_OVERLAY_CONTRACT_ID: p325_stock_adapter,
    P326_STOCK_OVERLAY_CONTRACT_ID: p326_stock_adapter,
    P327_STOCK_OVERLAY_CONTRACT_ID: p327_stock_adapter,
    P328_STOCK_OVERLAY_CONTRACT_ID: p328_stock_adapter,
    P329_STOCK_OVERLAY_CONTRACT_ID: p329_stock_adapter,
    P330_STOCK_OVERLAY_CONTRACT_ID: p330_stock_adapter,
    P331_STOCK_OVERLAY_CONTRACT_ID: p331_stock_adapter,
    P332_STOCK_OVERLAY_CONTRACT_ID: p332_stock_adapter,
    P333_STOCK_OVERLAY_CONTRACT_ID: p333_stock_adapter,
    P334_STOCK_OVERLAY_CONTRACT_ID: p334_stock_adapter,
    P335_STOCK_OVERLAY_CONTRACT_ID: p335_stock_adapter,
    P336_STOCK_OVERLAY_CONTRACT_ID: p336_stock_adapter,
    P337_STOCK_OVERLAY_CONTRACT_ID: p337_stock_adapter,
    P338_STOCK_OVERLAY_CONTRACT_ID: p338_stock_adapter,
    P339_STOCK_OVERLAY_CONTRACT_ID: p339_stock_adapter,
    P340_STOCK_OVERLAY_CONTRACT_ID: p340_stock_adapter,
    P341_STOCK_OVERLAY_CONTRACT_ID: p341_stock_adapter,
    P342_STOCK_OVERLAY_CONTRACT_ID: p342_stock_adapter,
}
P316_CANDIDATE_STATIC_SCHEMA = "s22plus_fyg8_p316_candidate_static_checker_v1"
P316_CANDIDATE_STATIC_VERDICT = (
    "PASS_P316_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P317_CANDIDATE_STATIC_SCHEMA = "s22plus_fyg8_p317_candidate_static_checker_v1"
P317_CANDIDATE_STATIC_VERDICT = (
    "PASS_P317_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P318_CANDIDATE_STATIC_SCHEMA = "s22plus_fyg8_p318_candidate_static_checker_v1"
P318_CANDIDATE_STATIC_VERDICT = (
    "PASS_P318_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
)
P319_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p319_process_v2_candidate_static_v1"
)
P319_CANDIDATE_STATIC_VERDICT = (
    "PASS_P319_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P320_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p320_process_v2_candidate_static_v1"
)
P320_CANDIDATE_STATIC_VERDICT = (
    "PASS_P320_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P321_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p321_process_v2_candidate_static_v1"
)
P321_CANDIDATE_STATIC_VERDICT = (
    "PASS_P321_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P322_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p322_process_v2_candidate_static_v1"
)
P322_CANDIDATE_STATIC_VERDICT = (
    "PASS_P322_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P323_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p323_process_v2_candidate_static_v1"
)
P323_CANDIDATE_STATIC_VERDICT = (
    "PASS_P323_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P324_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p324_process_v2_candidate_static_v1"
)
P324_CANDIDATE_STATIC_VERDICT = (
    "PASS_P324_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P325_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p325_process_v2_candidate_static_v1"
)
P325_CANDIDATE_STATIC_VERDICT = (
    "PASS_P325_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P326_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p326_process_v2_candidate_static_v1"
)
P326_CANDIDATE_STATIC_VERDICT = (
    "PASS_P326_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P327_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p327_process_v2_candidate_static_v1"
)
P327_CANDIDATE_STATIC_VERDICT = (
    "PASS_P327_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P328_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p328_process_v2_candidate_static_v1"
)
P328_CANDIDATE_STATIC_VERDICT = (
    "PASS_P328_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P329_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p329_process_v2_candidate_static_v1"
)
P329_CANDIDATE_STATIC_VERDICT = (
    "PASS_P329_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P330_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p330_process_v2_candidate_static_v1"
)
P330_CANDIDATE_STATIC_VERDICT = (
    "PASS_P330_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P331_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p331_process_v2_candidate_static_v1"
)
P331_CANDIDATE_STATIC_VERDICT = (
    "PASS_P331_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P332_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p332_process_v2_candidate_static_v1"
)
P332_CANDIDATE_STATIC_VERDICT = (
    "PASS_P332_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P333_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p333_process_v2_candidate_static_v1"
)
P333_CANDIDATE_STATIC_VERDICT = (
    "PASS_P333_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P334_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p334_process_v2_candidate_static_v1"
)
P334_CANDIDATE_STATIC_VERDICT = (
    "PASS_P334_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P335_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p335_process_v2_candidate_static_v1"
)
P335_CANDIDATE_STATIC_VERDICT = (
    "PASS_P335_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P336_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p336_process_v2_candidate_static_v1"
)
P336_CANDIDATE_STATIC_VERDICT = (
    "PASS_P336_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P337_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p337_process_v2_candidate_static_v1"
)
P337_CANDIDATE_STATIC_VERDICT = (
    "PASS_P337_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P338_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p338_process_v2_candidate_static_v1"
)
P338_CANDIDATE_STATIC_VERDICT = (
    "PASS_P338_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P339_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p339_process_v2_candidate_static_v1"
)
P339_CANDIDATE_STATIC_VERDICT = (
    "PASS_P339_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P340_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p340_process_v2_candidate_static_v1"
)
P340_CANDIDATE_STATIC_VERDICT = (
    "PASS_P340_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P341_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p341_process_v2_candidate_static_v1"
)
P341_CANDIDATE_STATIC_VERDICT = (
    "PASS_P341_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
P342_CANDIDATE_STATIC_SCHEMA = (
    "s22plus_fyg8_p342_process_v2_candidate_static_v1"
)
P342_CANDIDATE_STATIC_VERDICT = (
    "PASS_P342_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
)
MAX77705_OVERLAY_CONTRACT_IDS = frozenset(
    {
        MAX77705_OVERLAY_CONTRACT_ID,
        P317_MAX77705_OVERLAY_CONTRACT_ID,
        P318_MAX77705_OVERLAY_CONTRACT_ID,
    }
)
DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES = 1024 * 1024
P316_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P317_CANDIDATE_STATIC_MAX_BYTES = 5 * 1024 * 1024
P318_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P319_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P320_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P321_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P322_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P323_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P324_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P325_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P326_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P327_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P328_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P329_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P330_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P331_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P332_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P333_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P334_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P335_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P336_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P337_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P338_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P339_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P340_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P341_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P342_CANDIDATE_STATIC_MAX_BYTES = 2 * 1024 * 1024
P319_RUN_ID = "b9cc424d0d184f5accbce94a844e817d"
P320_RUN_ID = p320_stock_adapter.P320_STOCK_RUN_ID.hex()
P321_RUN_ID = p321_stock_adapter.P321_RUN_ID_HEX
P322_RUN_ID = p322_stock_adapter.P322_RUN_ID_HEX
P323_RUN_ID = p323_stock_adapter.P323_RUN_ID_HEX
P324_RUN_ID = p324_stock_adapter.P324_RUN_ID_HEX
P325_RUN_ID = p325_stock_adapter.P325_RUN_ID_HEX
P326_RUN_ID = p326_stock_adapter.P326_RUN_ID_HEX
P327_RUN_ID = p327_stock_adapter.P327_RUN_ID_HEX
P328_RUN_ID = p328_stock_adapter.P328_RUN_ID_HEX
P329_RUN_ID = p329_stock_adapter.P329_RUN_ID_HEX
P330_RUN_ID = p330_stock_adapter.P330_RUN_ID_HEX
P331_RUN_ID = p331_stock_adapter.P331_RUN_ID_HEX
P331_PREDECESSOR_RUN_ID = p331_stock_adapter.P330_PREDECESSOR_RUN_ID_HEX
P332_RUN_ID = p332_stock_adapter.P332_RUN_ID_HEX
P332_PREDECESSOR_RUN_ID = p332_stock_adapter.P331_PREDECESSOR_RUN_ID_HEX
P333_RUN_ID = p333_stock_adapter.P333_RUN_ID_HEX
P333_PREDECESSOR_RUN_ID = p333_stock_adapter.P332_PREDECESSOR_RUN_ID_HEX
P334_RUN_ID = p334_stock_adapter.P334_RUN_ID_HEX
P334_PREDECESSOR_RUN_ID = p334_stock_adapter.P333_PREDECESSOR_RUN_ID_HEX
P335_RUN_ID = p335_stock_adapter.P335_RUN_ID_HEX
P335_PREDECESSOR_RUN_ID = p335_stock_adapter.P334_PREDECESSOR_RUN_ID_HEX
P336_RUN_ID = p336_stock_adapter.P336_RUN_ID_HEX
P336_PREDECESSOR_RUN_ID = p336_stock_adapter.P335_PREDECESSOR_RUN_ID_HEX
P337_RUN_ID = p337_stock_adapter.P337_RUN_ID_HEX
P337_PREDECESSOR_RUN_ID = p337_stock_adapter.P336_PREDECESSOR_RUN_ID_HEX
P338_RUN_ID = p338_stock_adapter.P338_RUN_ID_HEX
P338_PREDECESSOR_RUN_ID = p338_stock_adapter.P337_PREDECESSOR_RUN_ID_HEX
P339_RUN_ID = p339_stock_adapter.P339_RUN_ID_HEX
P339_PREDECESSOR_RUN_ID = p339_stock_adapter.P338_PREDECESSOR_RUN_ID_HEX
P340_RUN_ID = p340_stock_adapter.P340_RUN_ID_HEX
P340_PREDECESSOR_RUN_ID = p340_stock_adapter.P339_PREDECESSOR_RUN_ID_HEX
P341_RUN_ID = p341_stock_adapter.P341_RUN_ID_HEX
P341_PREDECESSOR_RUN_ID = p341_stock_adapter.P340_PREDECESSOR_RUN_ID_HEX
P342_RUN_ID = P342_AUTH_EXEC_RUN_ID_HEX
P342_PREDECESSOR_RUN_ID = P341_RUN_ID
P320_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p320_process_v2_candidate_static.py"
)
P321_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p321_process_v2_candidate_static.py"
)
P322_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p322_process_v2_candidate_static.py"
)
P323_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p323_process_v2_candidate_static.py"
)
P324_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p324_process_v2_candidate_static.py"
)
P325_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p325_process_v2_candidate_static.py"
)
P326_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p326_process_v2_candidate_static.py"
)
P327_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p327_process_v2_candidate_static.py"
)
P328_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p328_process_v2_candidate_static.py"
)
P329_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p329_process_v2_candidate_static.py"
)
P330_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p330_process_v2_candidate_static.py"
)
P331_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p331_process_v2_candidate_static.py"
)
P332_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p332_process_v2_candidate_static.py"
)
P333_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p333_process_v2_candidate_static.py"
)
P334_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p334_process_v2_candidate_static.py"
)
P335_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p335_process_v2_candidate_static.py"
)
P336_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p336_process_v2_candidate_static.py"
)
P337_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p337_process_v2_candidate_static.py"
)
P338_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p338_process_v2_candidate_static.py"
)
P339_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p339_process_v2_candidate_static.py"
)
P340_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p340_process_v2_candidate_static.py"
)
P341_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p341_process_v2_candidate_static.py"
)
P342_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p342_process_v2_candidate_static.py"
)
P319_CANDIDATE_STATIC_AUTHORITY_PATH = (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_process_v2_candidate_static.py"
)
P319_TARGET = {
    "model": "SM-S906N",
    "codename": "g0q",
    "build": "S906NKSS7FYG8",
}
P320_TARGET = dict(P319_TARGET)
P321_TARGET = dict(P319_TARGET)
P322_TARGET = dict(P319_TARGET)
P323_TARGET = dict(P319_TARGET)
P324_TARGET = dict(P319_TARGET)
P325_TARGET = dict(P319_TARGET)
P326_TARGET = dict(P319_TARGET)
P327_TARGET = dict(P319_TARGET)
P328_TARGET = dict(P319_TARGET)
P329_TARGET = dict(P319_TARGET)
P330_TARGET = dict(P319_TARGET)
P331_TARGET = dict(P330_TARGET)
P332_TARGET = dict(P331_TARGET)
P333_TARGET = dict(P332_TARGET)
P334_TARGET = dict(P333_TARGET)
P335_TARGET = dict(P334_TARGET)
P336_TARGET = dict(P335_TARGET)
P337_TARGET = dict(P336_TARGET)
P338_TARGET = dict(P337_TARGET)
P339_TARGET = dict(P338_TARGET)
P340_TARGET = dict(P339_TARGET)
P341_TARGET = dict(P340_TARGET)
P342_TARGET = dict(P341_TARGET)
P323_CONSUMED_P322_BASELINE_IDENTITY = {
    "size": 2_097_136,
    "sha256": "3d186a2a46cdca7eed219d6a915906322d3c2da001e7380b3a75e8b52ef7b4e2",
}
P323_CONSUMED_P322_RECORD_OFFSET = 1_634_466
P324_CONSUMED_P323_BASELINE_IDENTITY = {
    "size": 2_097_136,
    "sha256": "da8df4578847a3a857907c0ea17d20e9723f0b69d7bd9b109981515c0404afc6",
}
P324_CONSUMED_P323_RECORD_OFFSET = 1_657_064
P325_CONSUMED_P324_BASELINE_IDENTITY = {
    "size": 2_097_136,
    "sha256": "e64815cf43f0772226518d39e566d6b8670f225a0469bca89022e50a9d918552",
}
P325_CONSUMED_P324_RECORD_OFFSET = 1_657_196
P331_CONSUMED_P330_BASELINE_IDENTITY = {
    "size": 2_097_136,
    "sha256": "3136c504434fac224f9fb9ffe1f688d1bf73062fbb75cb0da8117a885f3e05c6",
}
P331_CONSUMED_P330_RECORD_OFFSET = 1_657_877
P332_CONSUMED_P331_BASELINE_IDENTITY = {
    "size": 2_097_136,
    "sha256": "f33384fbedd604deca988bfb8ac9522e492aa930f5e81a816348730a5d0e3238",
}
P332_CONSUMED_P331_RECORD_OFFSET = 1_767_463
P333_CONSUMED_P332_BASELINE_IDENTITY = {
    "size": 2_097_136,
    "sha256": "455eec000b3aa14e8fca155b857910b4ed4c16285e55e390e59dcfb2f3386ab4",
}
P333_CONSUMED_P332_RECORD_OFFSET = 1_658_084
P334_CONSUMED_P333_BASELINE_IDENTITY = {
    "size": 2_097_136,
    "sha256": "ce236dfaddd23c9edd5165cee871d576cb8bb106ad4dbbf508c2861162ae617d",
}
P334_CONSUMED_P333_RECORD_OFFSET = 1_652_363
P338_CONSUMED_P337_BASELINE_IDENTITY = {
    "size": 2_097_136,
    "sha256": "64ac7a5b6666c4a21ce23effce2ec13015cdbdb985555300202ad46d8fe26a11",
}
P338_CONSUMED_P337_RECORD_OFFSET = 1_657_825
P339_CONSUMED_P338_BASELINE_IDENTITY = {
    "size": 2_097_136,
    "sha256": "321b03b24c488aa86f9cd2809dfdfdd2fa28fc8f5905183bbfe510cb1d58ab23",
}
P339_CONSUMED_P338_RUN_OFFSET = 1_658_754
P319_EXACT_ARTIFACTS = {
    "ap_tar_md5": {
        "size": 27_279_401,
        "sha256": "db5666ac794dfbf6f64192d7ea341ed79ff330f03db74c57da5ef61f659032f6",
    },
    "boot_img": {
        "size": 100_663_296,
        "sha256": "2b492a71808a0483f62896eb804042da38ed9ba7867aea045c5de630c9a86cb1",
    },
    "boot_img_lz4": {
        "size": 27_267_991,
        "sha256": "0491d50adecf485d10ec5e58ea4f58c2f62a874897564fb7151059348205c7e0",
    },
    "image": {
        "size": 41_490_944,
        "sha256": "71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8",
    },
    "init": {
        "size": 80_080,
        "sha256": "f6e6ea932c6c5297e18a932197e2fe1a131fac93c9caff9416d8fb873b055acb",
    },
    "child": {
        "size": 1_376,
        "sha256": "eb3c072b41ab4d4953fd1d862388d3be5ca5a40e9a07f074cb273f96a28557cf",
    },
    "latch": {
        "size": 423_232,
        "sha256": "27be8abfe121867e50b0f8b2094fff1d615181e2e0168e5c37e9f8fab2364a2b",
    },
}
P319_GENERIC_ROOTFS_NAMES = frozenset(
    {
        ".backup",
        ".backup/.magisk",
        ".backup/.rmlist",
        ".backup/init.xz",
        "debug_ramdisk",
        "dev",
        "init",
        "lib/modules/s22plus_dwc3_event_latch.ko",
        "metadata",
        "mnt",
        "overlay.d",
        "overlay.d/sbin",
        "overlay.d/sbin/init-ld.xz",
        "overlay.d/sbin/magisk.xz",
        "overlay.d/sbin/stub.xz",
        "proc",
        "s22-e1-child",
        "second_stage_resources",
        "sys",
        "system",
        "system/etc",
        "system/etc/ramdisk",
        "system/etc/ramdisk/build.prop",
    }
)
P301_TELEMETRY_OVERLAY_IDS = frozenset(
    {
        P301_OVERLAY_CONTRACT_ID,
        P302_OVERLAY_CONTRACT_ID,
        P303_OVERLAY_CONTRACT_ID,
        P304_OVERLAY_CONTRACT_ID,
        P305_OVERLAY_CONTRACT_ID,
        P306_OVERLAY_CONTRACT_ID,
        P307_OVERLAY_CONTRACT_ID,
        P308_OVERLAY_CONTRACT_ID,
        P311_OVERLAY_CONTRACT_ID,
        P312_OVERLAY_CONTRACT_ID,
        P313_OVERLAY_CONTRACT_ID,
        P314_OVERLAY_CONTRACT_ID,
        P315_OVERLAY_CONTRACT_ID,
        MAX77705_OVERLAY_CONTRACT_ID,
        P317_MAX77705_OVERLAY_CONTRACT_ID,
        P318_MAX77705_OVERLAY_CONTRACT_ID,
    }
)
P298_HISTORICAL_POSTBUILD_RESULT = {
    "sha256": "a7bfff7bdc82683999ef0d91349f20560b659ea703cb0542eeb37ca36a3ff997",
    "size": 71342,
}
P298_HISTORICAL_QUALIFICATION = {
    "sha256": "f3533d20ef3edc5c4feaf410296492820138dcd2c56861ee81be02fca78b89eb",
    "size": 115141,
}
P298_REPAIR_TIER2_KEYS = frozenset(
    {
        "p298_e2_stock_closure",
        "p298_candidate_static_checker",
        "p298_contract_test",
    }
)
P298_BUILD_ARTIFACTS = frozenset(
    {
        ".config",
        "Image",
        "System.map",
        "abi.xml",
        "build-result.json",
        "vmlinux",
        "vmlinux.symvers",
    }
)
E1_LATEST_STAGE_CANDIDATE_CONTRACT_SCHEMA = (
    "s22plus_fyg8_p234_candidate_contract_v1"
)
E1_LATEST_STAGE_CANDIDATE_CONTRACT_VERDICT = (
    "PASS_P234_CANDIDATE_CONTRACT_HOST_ONLY"
)
E1_LATEST_STAGE_PREIMAGE_SCHEMA = (
    "s22plus_fyg8_p234_candidate_identity_preimage_v1"
)
E1_LATEST_STAGE_RUN_ID_DOMAINS = {
    "E1A": b"S22PLUS-FYG8-P234-E1A-RUN-ID-V1\0",
    "E1B": b"S22PLUS-FYG8-P239-E1B-RUN-ID-V1\0",
    "E2": b"S22PLUS-FYG8-P242-E2-RUN-ID-V1\0",
}
E1_LATEST_STAGE_SOURCE_KEYS = {
    "E1A": {
        "base_patch",
        "checkpoint_client",
        "runtime_wrapper",
        "legacy_runtime",
        "legacy_header",
        "child",
        "decoder",
        "design_model",
        "source_checker",
    },
    "E1B": {
        "base_patch",
        "checkpoint_client",
        "runtime_wrapper",
        "legacy_runtime",
        "legacy_header",
        "child",
        "decoder",
        "design_model",
        "source_checker",
    },
    "E2": {
        "base_patch",
        "checkpoint_client",
        "runtime_wrapper",
        "plan_header",
        "loader_core",
        "legacy_runtime",
        "legacy_header",
        "child",
        "decoder",
        "design_model",
        "source_checker",
        "planner",
        "dtbo_contract",
        "stock_closure",
    },
}
E1_LATEST_STAGE_KERNEL_INTERVAL = (4096, 41495040)
CHECKPOINT_SOURCE = "/proc/last_kmsg"
PID1_USERSPACE_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
PID1_USERSPACE_ENTRY = b"\n[[S22P1U|ba234c7de4105b2a23222436284605f2]]\n"
PID1_USERSPACE_PROOF = b"\n[[S22P1U|ec8d029b05288644bbe7b5f7c7af190c]]\n"
PID1_USERSPACE_FAMILY = b"[[S22P1U|"
PID1_USERSPACE_PROBE_ID = "64554e8469385878c5bf8d57c44edeea"
SAME_RING_CONTRACT_ID = same_ring.CONTRACT_ID.hex()
SAME_RING_MULTIBOOT_POLICY_ID = same_ring_multiboot.POLICY_ID.hex()
SAME_RING_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p219_run_manifest_v1"
SAME_RING_STATIC_SCHEMA = "s22plus_fyg8_p219_candidate_static_checker_v1"
SAME_RING_STATIC_VERDICT = "PASS_P219_OFFLINE_CANDIDATE_STATIC_CONTRACT"
OUTCOME_NAMES = {
    checkpoint.OUTCOME_PROGRESS: "progress",
    checkpoint.OUTCOME_SUCCESS: "success",
    checkpoint.OUTCOME_FAILURE: "failure",
}
HEX32_RE = re.compile(r"[0-9a-f]{32}")
HASH_RE = re.compile(r"[0-9a-f]{64}")
E1_LATEST_STAGE_BASE_FILES = {
    "kernel_platform/common/arch/arm64/configs/gki_defconfig": (
        "12661b7d249fb8f80135c3fdcd331733b86d5215f2f4e88e356d1516831ab493"
    ),
    "kernel_platform/common/init/Kconfig": (
        "8273d233a441c21df2fcb1d5d17a590321d758205fd5babd8b8dcb4e6a334019"
    ),
    "kernel_platform/common/init/main.c": (
        "7d281c86ca63646083b9f489eed28281c7d2518f397f34ceccf34c223eaa663a"
    ),
}


def _candidate_base_files(
    source_contract_id: str | None,
    profile: str,
) -> dict[str, str]:
    expected = dict(E1_LATEST_STAGE_BASE_FILES)
    if source_contract_id not in {
        P294_SOURCE_CONTRACT_ID,
        P296_SOURCE_CONTRACT_ID,
        P298_SOURCE_CONTRACT_ID,
        P300_SOURCE_CONTRACT_ID,
        P310_SOURCE_CONTRACT_ID,
    }:
        return expected
    driver_sources = getattr(
        _selected_contract(source_contract_id, profile).module,
        "DRIVER_SOURCE_RECEIPTS",
        None,
    )
    if (
        not isinstance(driver_sources, dict)
        or not driver_sources
        or any(
            not isinstance(path, str)
            or not isinstance(digest, str)
            or HASH_RE.fullmatch(digest) is None
            for path, digest in driver_sources.items()
        )
        or set(expected) & set(driver_sources)
    ):
        raise EvidenceError("versioned driver source receipts are invalid")
    expected.update(driver_sources)
    return expected
E1B_MODULE_SPECS = [
    {
        "file": "smem.ko",
        "runtime": "smem",
        "size": 28_704,
        "sha256": "27a80d5598329d6a526384d09806de63983204988748ea4e7d3fccfafc24a524",
    },
    {
        "file": "minidump.ko",
        "runtime": "minidump",
        "size": 37_312,
        "sha256": "e5e6f4dfe1ddac2cd4f8d15c11a50d4d32b6e9de278fedbed44747630a5c554d",
    },
    {
        "file": "qcom-scm.ko",
        "runtime": "qcom_scm",
        "size": 218_384,
        "sha256": "e12ba8661808c2c47acf42c9939157e509fcdb5b98f6e650f79b92dba18a1af3",
    },
    {
        "file": "qcom_wdt_core.ko",
        "runtime": "qcom_wdt_core",
        "size": 48_640,
        "sha256": "ef484fb4f1f17586ff63852e0ea9579d07f275f7966ad117d20039055c2d7599",
    },
    {
        "file": "gh_virt_wdt.ko",
        "runtime": "gh_virt_wdt",
        "size": 18_944,
        "sha256": "f030c5486a41b1fbe4b0ea3aa85a401dd16daa1f1a551a626f6ea424ee90dd39",
    },
]
E1B_MODULE_FILES = [row["file"] for row in E1B_MODULE_SPECS]
E1B_MODULE_RUNTIME_NAMES = [row["runtime"] for row in E1B_MODULE_SPECS]
E1B_MODULE_ORDER_MODEL = (
    "modules.dep topological order with stock modules.load.recovery tie-breaks"
)
E1B_STOCK_RECOVERY_POSITIONS = {
    "gh_virt_wdt.ko": 5,
    "minidump.ko": 51,
    "qcom-scm.ko": 83,
    "qcom_wdt_core.ko": 6,
    "smem.ko": 124,
}
E1B_VENDOR_METADATA_HASHES = {
    "modules.alias": "5679e647fcdcb6a13bd4f20d24a901f158e641fbd0a813274c99006ec8fa2c20",
    "modules.dep": "21eae389f1d8b0a9fc93cec0b12d36e736cfac656d91ae55055c793f2ed67b27",
    "modules.load": "8491b842e6e05cfba42694ad003301a6598e8d152ec10cc8f0cc6fb17f10e232",
    "modules.load.recovery": "616bdb71f2b68d76eca23f72883aea25d5202d4e14f5c99dd934720df863ac10",
    "modules.softdep": "21d6a678d186356c2fb0349a8a9a5190e6e225dab0feb5012e495a100c33afb0",
}
E1B_COMPOSITION_ORDER = ["generic", "vendor[0]/"]
E1B_EFFECTIVE_ENTRY_COUNT = 474
E1B_EFFECTIVE_MODULE_ROWS = [
    {"file": name, "runtime": runtime, "layer": "vendor[0]/"}
    for name, runtime in zip(E1B_MODULE_FILES, E1B_MODULE_RUNTIME_NAMES)
]
E1B_ELF_ENTRYPOINTS = {"init": 4_198_200, "child": 4_194_508}
E1B_STOCK_VENDOR_BOOT = {
    "size": 100_663_296,
    "sha256": "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7",
}


def _e1_reachable_slot_variant_count(
    profile: str, source_contract_id: str | None = None
) -> int:
    if source_contract_id is not None:
        return _selected_contract(
            source_contract_id, profile
        ).contract.reachable_variants
    model = e1_latest_stage.model
    sequence = model.PROFILE_STAGE_SEQUENCES.get(profile)
    terminal = model.PROFILE_TERMINALS.get(profile)
    if not sequence or sequence[-1] != terminal or sequence.count(terminal) != 1:
        raise EvidenceError("E1 profile stage sequence is not terminal-bound")
    return sum(1 if stage == terminal else 1 + 4095 for stage in sequence)


class EvidenceError(ValueError):
    pass


def _selected_contract(
    source_contract_id: str | None, profile: str
) -> source_contracts.SelectedSourceContract:
    if source_contract_id == P310_SOURCE_CONTRACT_ID:
        try:
            contract = p310_source_contract.require(source_contract_id, profile)
        except p310_source_contract.SourceContractError as exc:
            raise EvidenceError(str(exc)) from exc
        return source_contracts.SelectedSourceContract(
            module=p310_source_contract,
            contract=contract,
            implementation_verdict=p310_source_contract.IMPLEMENTATION_VERDICT,
            source_check_run_id=p310_source_contract.SOURCE_CHECK_RUN_ID,
            userspace_verdict=p310_source_contract.USERSPACE_VERDICT,
        )
    if source_contract_id == P300_SOURCE_CONTRACT_ID:
        try:
            contract = p300_source_contract.require(source_contract_id, profile)
        except p300_source_contract.SourceContractError as exc:
            raise EvidenceError(str(exc)) from exc
        return source_contracts.SelectedSourceContract(
            module=p300_source_contract,
            contract=contract,
            implementation_verdict=p300_source_contract.IMPLEMENTATION_VERDICT,
            source_check_run_id=p300_source_contract.SOURCE_CHECK_RUN_ID,
            userspace_verdict=p300_source_contract.USERSPACE_VERDICT,
        )
    try:
        return source_contracts.select(source_contract_id, profile)
    except source_contracts.SourceContractSelectionError as exc:
        raise EvidenceError(str(exc)) from exc


def _latest_stage_decoder(
    source_contract_id: str | None, profile: str
):
    if source_contract_id is None:
        return e1_latest_stage
    return _selected_contract(source_contract_id, profile).decoder


def _latest_stage_observation_decoder(
    source_contract_id: str | None,
    profile: str,
    userspace_overlay_contract_id: str | None = None,
):
    if userspace_overlay_contract_id is None:
        return _latest_stage_decoder(source_contract_id, profile)
    if userspace_overlay_contract_id == P342_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p342_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p342_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.42 idle-reuse userspace observation overlay is unsupported"
            )
        selected = p342_stock_adapter
    elif userspace_overlay_contract_id == P341_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p341_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p341_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.41 host-first open userspace observation overlay is unsupported"
            )
        selected = p341_stock_adapter
    elif userspace_overlay_contract_id == P340_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p340_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p340_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.40 open-read branch userspace observation overlay is unsupported"
            )
        selected = p340_stock_adapter
    elif userspace_overlay_contract_id == P339_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p339_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p339_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.39 open-read branch userspace observation overlay is unsupported"
            )
        selected = p339_stock_adapter
    elif userspace_overlay_contract_id == P338_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p338_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p338_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.38 open-read branch userspace observation overlay is unsupported"
            )
        selected = p338_stock_adapter
    elif userspace_overlay_contract_id == P337_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p337_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p337_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.37 open-read diagnostic userspace observation overlay is unsupported"
            )
        selected = p337_stock_adapter
    elif userspace_overlay_contract_id == P336_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p336_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p336_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.36 long-idle userspace observation overlay is unsupported"
            )
        selected = p336_stock_adapter
    elif userspace_overlay_contract_id == P335_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p335_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p335_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.35 attended-resident userspace observation overlay is unsupported"
            )
        selected = p335_stock_adapter
    elif userspace_overlay_contract_id == P334_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p334_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p334_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.34 first-console-return userspace observation overlay is unsupported"
            )
        selected = p334_stock_adapter
    elif userspace_overlay_contract_id == P333_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p333_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p333_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.33 OPEN-entry diagnostic userspace observation overlay is unsupported"
            )
        selected = p333_stock_adapter
    elif userspace_overlay_contract_id == P332_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p332_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p332_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.32 logical resident authenticated userspace observation overlay is unsupported"
            )
        selected = p332_stock_adapter
    elif userspace_overlay_contract_id == P331_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p331_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p331_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.31 resident authenticated userspace observation overlay is unsupported"
            )
        selected = p331_stock_adapter
    elif userspace_overlay_contract_id == P330_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p330_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p330_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.30 diagnostic authenticated userspace observation overlay is unsupported"
            )
        selected = p330_stock_adapter
    elif userspace_overlay_contract_id == P329_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p329_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p329_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.29 authenticated settle userspace observation overlay is unsupported"
            )
        selected = p329_stock_adapter
    elif userspace_overlay_contract_id == P328_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p328_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p328_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.28 authenticated exec userspace observation overlay is unsupported"
            )
        selected = p328_stock_adapter
    elif userspace_overlay_contract_id == P327_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p327_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p327_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.27 stock userspace observation overlay is unsupported"
            )
        selected = p327_stock_adapter
    elif userspace_overlay_contract_id == P326_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p326_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p326_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.26 stock userspace observation overlay is unsupported"
            )
        selected = p326_stock_adapter
    elif userspace_overlay_contract_id == P325_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p325_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p325_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.25 stock userspace observation overlay is unsupported"
            )
        selected = p325_stock_adapter
    elif userspace_overlay_contract_id == P324_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p324_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p324_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.24 stock userspace observation overlay is unsupported"
            )
        selected = p324_stock_adapter
    elif userspace_overlay_contract_id == P323_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p323_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p323_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.23 stock userspace observation overlay is unsupported"
            )
        selected = p323_stock_adapter
    elif userspace_overlay_contract_id == P322_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p322_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p322_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.22 stock userspace observation overlay is unsupported"
            )
        selected = p322_stock_adapter
    elif userspace_overlay_contract_id == P321_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p321_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p321_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.21 stock userspace observation overlay is unsupported"
            )
        selected = p321_stock_adapter
    elif userspace_overlay_contract_id == P320_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p320_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p320_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.20 stock userspace observation overlay is unsupported"
            )
        selected = p320_stock_adapter
    elif userspace_overlay_contract_id == P319_STOCK_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID
            or profile != p319_stock_adapter.PROFILE
        ):
            raise EvidenceError(
                "P3.19 stock userspace observation overlay is unsupported"
            )
        selected = p319_stock_adapter
    elif userspace_overlay_contract_id == P318_MAX77705_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id
            != p318_max77705_decoder.PARENT_SOURCE_CONTRACT_ID
            or profile != p318_max77705_decoder.PROFILE
        ):
            raise EvidenceError(
                "P3.18 Max77705 userspace observation overlay is unsupported"
            )
        selected = p318_max77705_decoder
    elif userspace_overlay_contract_id == P317_MAX77705_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id
            != p317_max77705_decoder.PARENT_SOURCE_CONTRACT_ID
            or profile != p317_max77705_decoder.PROFILE
        ):
            raise EvidenceError(
                "P3.17 Max77705 userspace observation overlay is unsupported"
            )
        selected = p317_max77705_decoder
    elif userspace_overlay_contract_id == MAX77705_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != max77705_decoder.PARENT_SOURCE_CONTRACT_ID
            or profile != max77705_decoder.PROFILE
        ):
            raise EvidenceError(
                "Max77705 userspace observation overlay is unsupported"
            )
        selected = max77705_decoder
    elif userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != P310_SOURCE_CONTRACT_ID
            or profile != p311_overlay.PROFILE
        ):
            raise EvidenceError("P3.11 userspace observation overlay is unsupported")
        selected = p311_decoder
    elif userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != P310_SOURCE_CONTRACT_ID
            or profile != p312_overlay.PROFILE
        ):
            raise EvidenceError("P3.12 userspace observation overlay is unsupported")
        selected = p312_decoder
    elif userspace_overlay_contract_id == P313_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != P310_SOURCE_CONTRACT_ID
            or profile != p313_overlay.PROFILE
        ):
            raise EvidenceError("P3.13 userspace observation overlay is unsupported")
        selected = p313_decoder
    elif userspace_overlay_contract_id == P315_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != P310_SOURCE_CONTRACT_ID
            or profile != p315_overlay.PROFILE
        ):
            raise EvidenceError("P3.15 userspace observation overlay is unsupported")
        selected = p315_decoder
    elif userspace_overlay_contract_id == P314_OVERLAY_CONTRACT_ID:
        if (
            source_contract_id != P310_SOURCE_CONTRACT_ID
            or profile != p314_overlay.PROFILE
        ):
            raise EvidenceError("P3.14 userspace observation overlay is unsupported")
        selected = p314_decoder
    else:
        if (
            userspace_overlay_contract_id not in P301_TELEMETRY_OVERLAY_IDS
            or source_contract_id != P300_SOURCE_CONTRACT_ID
            or profile != p301_overlay.PROFILE
        ):
            raise EvidenceError("userspace observation overlay is unsupported")
        if userspace_overlay_contract_id == P307_OVERLAY_CONTRACT_ID:
            selected = p307_decoder
        elif userspace_overlay_contract_id == P308_OVERLAY_CONTRACT_ID:
            selected = p308_decoder
        elif userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
            selected = p306_decoder
        elif userspace_overlay_contract_id in {
            P303_OVERLAY_CONTRACT_ID,
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
        }:
            selected = p303_decoder
        else:
            selected = p301_decoder
    return _validate_decoder_carrier_authority(
        selected, source_contract_id=source_contract_id, profile=profile
    )


def _validate_decoder_carrier_authority(
    selected_decoder: Any,
    *,
    source_contract_id: str | None,
    profile: str,
):
    """Bind overlay semantics to the source contract's retained-record ABI."""

    source_decoder = _latest_stage_decoder(source_contract_id, profile)
    attributes = (
        "LONG_FAMILY",
        "UNSAT_FAMILY",
        "LONG_RECORD_SIZE",
        "FORMAT_VERSION",
    )
    if any(
        getattr(selected_decoder.model, name, None)
        != getattr(source_decoder.model, name, None)
        for name in attributes
    ):
        raise EvidenceError(
            "userspace observation decoder carrier differs from source contract"
        )
    try:
        run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
        if selected_decoder in STOCK_ADAPTERS.values():
            record = selected_decoder.encode_fixture()
        else:
            record = source_decoder.model.initialize_record(profile, run_id)
        decoded = selected_decoder.decode_record(
            record,
            expected_profile=profile,
            expected_run_id=(
                selected_decoder.STOCK_RUN_ID
                if selected_decoder in STOCK_ADAPTERS.values()
                else run_id
            ),
        )
        json.dumps(decoded, sort_keys=True, allow_nan=False)
    except (AttributeError, TypeError, ValueError, selected_decoder.DecodeError) as exc:
        raise EvidenceError(
            "userspace observation decoder is not JSON-safe for its carrier"
        ) from exc
    return selected_decoder


def _validate_p301_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p301_overlay.verify_intent(
            root,
            root / p301_overlay.DEFAULT_INTENT,
        )
    except (p301_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.01 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.01 overlay contract differs from current intent")
    return current


def _validate_p302_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p302_overlay.verify_intent(
            root,
            root / p302_overlay.DEFAULT_INTENT,
        )
    except (p302_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.02 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.02 overlay contract differs from current intent")
    return current


def _validate_p303_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p303_overlay.verify_intent(
            root,
            root / p303_overlay.DEFAULT_INTENT,
        )
    except (p303_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.03 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.03 overlay contract differs from current intent")
    return current


def _validate_p304_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p304_overlay.verify_intent(root, root / p304_overlay.DEFAULT_INTENT)
    except (p304_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.04 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.04 overlay contract differs from current intent")
    return current


def _validate_p305_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p305_overlay.verify_intent(root, root / p305_overlay.DEFAULT_INTENT)
    except (p305_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.05 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.05 overlay contract differs from current intent")
    return current


def _validate_p306_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p306_overlay.verify_intent(root, root / p306_overlay.DEFAULT_INTENT)
    except (p306_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.06 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.06 overlay contract differs from current intent")
    return current


def _validate_p307_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p307_overlay.verify_intent(root, root / p307_overlay.DEFAULT_INTENT)
    except (p307_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.07 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.07 overlay contract differs from current intent")
    return current


def _validate_p308_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p308_overlay.verify_intent(root, root / p308_overlay.DEFAULT_INTENT)
    except (p308_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.08 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.08 overlay contract differs from current intent")
    return current


def _validate_p311_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p311_overlay.verify_intent(root, root / p311_overlay.DEFAULT_INTENT)
    except (p311_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.11 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.11 overlay contract differs from current intent")
    return current


def _validate_p312_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p312_overlay.verify_intent(root, root / p312_overlay.DEFAULT_INTENT)
    except (p312_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.12 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.12 overlay contract differs from current intent")
    return current


def _validate_p313_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p313_overlay.verify_intent(root, root / p313_overlay.DEFAULT_INTENT)
    except (p313_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.13 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.13 overlay contract differs from current intent")
    return current


def _validate_p314_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p314_overlay.verify_intent(root, root / p314_overlay.DEFAULT_INTENT)
    except (p314_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.14 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.14 overlay contract differs from current intent")
    return current


def _validate_p315_overlay_contract(value: Any) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[5]
    try:
        current = p315_overlay.verify_intent(root, root / p315_overlay.DEFAULT_INTENT)
    except (p315_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.15 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.15 overlay contract differs from current intent")
    return current


def _validate_p316_overlay_contract(value: Any) -> dict[str, Any]:
    import s22plus_fyg8_p316_overlay_contract as p316_overlay

    root = Path(__file__).resolve().parents[5]
    try:
        current = p316_overlay.verify_intent(root, root / p316_overlay.DEFAULT_INTENT)
    except (p316_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.16 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.16 overlay contract differs from current intent")
    return current


def _validate_p317_overlay_contract(value: Any) -> dict[str, Any]:
    import s22plus_fyg8_p317_overlay_contract as p317_overlay

    root = Path(__file__).resolve().parents[5]
    try:
        current = p317_overlay.verify_intent(root, root / p317_overlay.DEFAULT_INTENT)
    except (p317_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.17 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.17 overlay contract differs from current intent")
    return current


def _validate_p318_overlay_contract(value: Any) -> dict[str, Any]:
    import s22plus_fyg8_p318_overlay_contract as p318_overlay

    root = Path(__file__).resolve().parents[5]
    try:
        current = p318_overlay.verify_intent(
            root, root / p318_overlay.DEFAULT_INTENT
        )
    except (p318_overlay.OverlayContractError, OSError) as exc:
        raise EvidenceError("P3.18 overlay intent verification failed") from exc
    if value != current:
        raise EvidenceError("P3.18 overlay contract differs from current intent")
    return current


def _validate_userspace_overlay_contract(
    value: Any, userspace_overlay_contract_id: str
) -> dict[str, Any]:
    if userspace_overlay_contract_id == P342_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p342_stock_adapter.validate_contract(value)
        except (p342_stock_adapter.DecodeError, p342_stock_adapter.ContractError) as exc:
            raise EvidenceError(
                "P3.42 idle-reuse overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P341_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p341_stock_adapter.validate_contract(value)
        except (p341_stock_adapter.DecodeError, p341_stock_adapter.ContractError) as exc:
            raise EvidenceError(
                "P3.41 host-first open overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P340_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p340_stock_adapter.validate_contract(value)
        except (p340_stock_adapter.DecodeError, p340_stock_adapter.ContractError) as exc:
            raise EvidenceError(
                "P3.40 open-read branch overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P339_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p339_stock_adapter.validate_contract(value)
        except (p339_stock_adapter.DecodeError, p339_stock_adapter.ContractError) as exc:
            raise EvidenceError(
                "P3.39 open-read branch overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P338_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p338_stock_adapter.validate_contract(value)
        except (p338_stock_adapter.DecodeError, p338_stock_adapter.ContractError) as exc:
            raise EvidenceError(
                "P3.38 open-read branch overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P337_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p337_stock_adapter.validate_contract(value)
        except (p337_stock_adapter.DecodeError, p337_stock_adapter.ContractError) as exc:
            raise EvidenceError(
                "P3.37 open-read diagnostic overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P336_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p336_stock_adapter.validate_contract(value)
        except (p336_stock_adapter.DecodeError, p336_stock_adapter.ContractError) as exc:
            raise EvidenceError(
                "P3.36 long-idle overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P335_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p335_stock_adapter.validate_contract(value)
        except (p335_stock_adapter.DecodeError, p335_stock_adapter.ContractError) as exc:
            raise EvidenceError(
                "P3.35 attended-resident overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P334_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p334_stock_adapter.validate_contract(value)
        except p334_stock_adapter.DecodeError as exc:
            raise EvidenceError(
                "P3.34 first-console-return overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P333_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p333_stock_adapter.validate_contract(value)
        except p333_stock_adapter.DecodeError as exc:
            raise EvidenceError(
                "P3.33 OPEN-entry diagnostic overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P332_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p332_stock_adapter.validate_contract(value)
        except p332_stock_adapter.DecodeError as exc:
            raise EvidenceError(
                "P3.32 logical resident authenticated overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P331_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p331_stock_adapter.validate_contract(value)
        except p331_stock_adapter.DecodeError as exc:
            raise EvidenceError(
                "P3.31 resident authenticated overlay metadata differs"
            ) from exc
    if userspace_overlay_contract_id == P330_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p330_stock_adapter.validate_contract(value)
        except p330_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.30 diagnostic authenticated overlay metadata differs") from exc
    if userspace_overlay_contract_id == P329_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p329_stock_adapter.validate_contract(value)
        except p329_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.29 authenticated settle overlay metadata differs") from exc
    if userspace_overlay_contract_id == P328_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p328_stock_adapter.validate_contract(value)
        except p328_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.28 authenticated exec overlay metadata differs") from exc
    if userspace_overlay_contract_id == P327_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p327_stock_adapter.validate_contract(value)
        except p327_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.27 stock overlay metadata differs") from exc
    if userspace_overlay_contract_id == P326_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p326_stock_adapter.validate_contract(value)
        except p326_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.26 stock overlay metadata differs") from exc
    if userspace_overlay_contract_id == P325_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p325_stock_adapter.validate_contract(value)
        except p325_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.25 stock overlay metadata differs") from exc
    if userspace_overlay_contract_id == P324_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p324_stock_adapter.validate_contract(value)
        except p324_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.24 stock overlay metadata differs") from exc
    if userspace_overlay_contract_id == P323_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p323_stock_adapter.validate_contract(value)
        except p323_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.23 stock overlay metadata differs") from exc
    if userspace_overlay_contract_id == P322_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p322_stock_adapter.validate_contract(value)
        except p322_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.22 stock overlay metadata differs") from exc
    if userspace_overlay_contract_id == P321_STOCK_OVERLAY_CONTRACT_ID:
        try:
            return p321_stock_adapter.validate_contract(value)
        except p321_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.21 stock overlay metadata differs") from exc
    if userspace_overlay_contract_id == P320_STOCK_OVERLAY_CONTRACT_ID:
        # P320 is a distinct ABI-v4 stock overlay.  The adapter validates the
        # observer contract and its P310 Carrier parent without creating a
        # second DEFAULT_INTENT or reinterpreting P319 metadata.
        try:
            return p320_stock_adapter.validate_contract(value)
        except p320_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.20 stock overlay metadata differs") from exc
    if userspace_overlay_contract_id == P319_STOCK_OVERLAY_CONTRACT_ID:
        # P319 deliberately validates only the explicit metadata object.  Its
        # future candidate-static promotion must provide its own parent/static
        # contract; this branch never invents DEFAULT_INTENT or verify_intent.
        try:
            return p319_stock_adapter.validate_contract(value)
        except p319_stock_adapter.DecodeError as exc:
            raise EvidenceError("P3.19 stock overlay metadata differs") from exc
    if userspace_overlay_contract_id == P318_MAX77705_OVERLAY_CONTRACT_ID:
        return _validate_p318_overlay_contract(value)
    if userspace_overlay_contract_id == P317_MAX77705_OVERLAY_CONTRACT_ID:
        return _validate_p317_overlay_contract(value)
    if userspace_overlay_contract_id == MAX77705_OVERLAY_CONTRACT_ID:
        return _validate_p316_overlay_contract(value)
    if userspace_overlay_contract_id == P301_OVERLAY_CONTRACT_ID:
        return _validate_p301_overlay_contract(value)
    if userspace_overlay_contract_id == P302_OVERLAY_CONTRACT_ID:
        return _validate_p302_overlay_contract(value)
    if userspace_overlay_contract_id == P303_OVERLAY_CONTRACT_ID:
        return _validate_p303_overlay_contract(value)
    if userspace_overlay_contract_id == P304_OVERLAY_CONTRACT_ID:
        return _validate_p304_overlay_contract(value)
    if userspace_overlay_contract_id == P305_OVERLAY_CONTRACT_ID:
        return _validate_p305_overlay_contract(value)
    if userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
        return _validate_p306_overlay_contract(value)
    if userspace_overlay_contract_id == P307_OVERLAY_CONTRACT_ID:
        return _validate_p307_overlay_contract(value)
    if userspace_overlay_contract_id == P308_OVERLAY_CONTRACT_ID:
        return _validate_p308_overlay_contract(value)
    if userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
        return _validate_p311_overlay_contract(value)
    if userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
        return _validate_p312_overlay_contract(value)
    if userspace_overlay_contract_id == P313_OVERLAY_CONTRACT_ID:
        return _validate_p313_overlay_contract(value)
    if userspace_overlay_contract_id == P314_OVERLAY_CONTRACT_ID:
        return _validate_p314_overlay_contract(value)
    if userspace_overlay_contract_id == P315_OVERLAY_CONTRACT_ID:
        return _validate_p315_overlay_contract(value)
    raise EvidenceError("userspace observation overlay is unsupported")


def _select_e2_closure(
    source_contract_id: str | None,
    userspace_overlay_contract_id: str | None = None,
):
    if userspace_overlay_contract_id == P342_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p342_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.42 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P341_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p341_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.41 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P340_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p340_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.40 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P339_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p339_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.39 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P338_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p338_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.38 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P337_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p337_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.37 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P336_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p336_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.36 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P335_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p335_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.35 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P334_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p334_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.34 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P333_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p333_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.33 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P332_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p332_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.32 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P331_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p331_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.31 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P330_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p330_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.30 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P329_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p329_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.29 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P328_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p328_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.28 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P327_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p327_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.27 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P326_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p326_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.26 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P325_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p325_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.25 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P324_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p324_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.24 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P323_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p323_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.23 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P322_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p322_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.22 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P321_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p321_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.21 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P320_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p320_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.20 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P319_STOCK_OVERLAY_CONTRACT_ID:
        if source_contract_id != p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.19 stock parent source contract differs")
        return p310_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P318_MAX77705_OVERLAY_CONTRACT_ID:
        if source_contract_id != P310_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.18 parent source contract differs")
        return p318_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P317_MAX77705_OVERLAY_CONTRACT_ID:
        if source_contract_id != P310_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.17 parent source contract differs")
        return p317_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == MAX77705_OVERLAY_CONTRACT_ID:
        if source_contract_id != P310_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.16 parent source contract differs")
        return p316_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id in {
        P304_OVERLAY_CONTRACT_ID,
        P305_OVERLAY_CONTRACT_ID,
        P306_OVERLAY_CONTRACT_ID,
        P307_OVERLAY_CONTRACT_ID,
        P308_OVERLAY_CONTRACT_ID,
    }:
        if source_contract_id != P300_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.04 parent source contract differs")
        return p304_e2_closure
    if userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
        if source_contract_id != P310_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.11 parent source contract differs")
        return p311_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
        if source_contract_id != P310_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.12 parent source contract differs")
        return p312_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P313_OVERLAY_CONTRACT_ID:
        if source_contract_id != P310_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.13 parent source contract differs")
        return p313_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P314_OVERLAY_CONTRACT_ID:
        if source_contract_id != P310_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.14 parent source contract differs")
        return p314_e2_closure.select(source_contract_id)
    if userspace_overlay_contract_id == P315_OVERLAY_CONTRACT_ID:
        if source_contract_id != P310_SOURCE_CONTRACT_ID:
            raise EvidenceError("P3.15 parent source contract differs")
        return p315_e2_closure.select(source_contract_id)
    if source_contract_id == P300_SOURCE_CONTRACT_ID:
        return p300_e2_closure.select(source_contract_id)
    if source_contract_id == P310_SOURCE_CONTRACT_ID:
        return p310_e2_closure.select(source_contract_id)
    if source_contract_id == P298_SOURCE_CONTRACT_ID:
        return p298_e2_closure.select(source_contract_id)
    if source_contract_id == P296_SOURCE_CONTRACT_ID:
        return p296_e2_closure.select(source_contract_id)
    if source_contract_id == P294_SOURCE_CONTRACT_ID:
        return p294_e2_closure.select(source_contract_id)
    if source_contract_id == P292_SOURCE_CONTRACT_ID:
        return p292_e2_closure.select(source_contract_id)
    if source_contract_id == P290_SOURCE_CONTRACT_ID:
        return p290_e2_closure.select(source_contract_id)
    if source_contract_id == P288_SOURCE_CONTRACT_ID:
        return p288_e2_closure.select(source_contract_id)
    if source_contract_id == P286_SOURCE_CONTRACT_ID:
        return p286_e2_closure.select(source_contract_id)
    return e2_closure_selector.select(source_contract_id)


def _e2_authority_context(source_contract_id: str | None, closure_api: Any):
    if source_contract_id not in {
        P286_SOURCE_CONTRACT_ID,
        P288_SOURCE_CONTRACT_ID,
        P290_SOURCE_CONTRACT_ID,
        P292_SOURCE_CONTRACT_ID,
        P294_SOURCE_CONTRACT_ID,
        P296_SOURCE_CONTRACT_ID,
        P298_SOURCE_CONTRACT_ID,
        P300_SOURCE_CONTRACT_ID,
        P310_SOURCE_CONTRACT_ID,
    }:
        return nullcontext()
    authority_context = getattr(closure_api, "_p286_authority_paths", None)
    if not callable(authority_context):
        raise EvidenceError(
            "versioned stock-closure authority adapter is unavailable"
        )
    return authority_context()


def _p310_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p310_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.10 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.10 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


def _p311_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p311_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.11 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.11 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


def _p312_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p312_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.12 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.12 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


def _p313_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p313_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.13 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.13 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


def _p314_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p314_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.14 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.14 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


def _p315_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p315_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.15 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.15 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


def _p316_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p316_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.16 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.16 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


def _p317_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p317_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.17 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.17 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


def _p318_e2_authority_context(
    closure_api: Any,
    entries: list[Any],
    expected_init: dict[str, Any],
):
    if closure_api is not p318_e2_closure.select(P310_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.18 stock-closure authority adapter differs")
    matching = [
        entry
        for entry in entries
        if entry.name == "init" and entry.file_type == "regular"
    ]
    if (
        len(matching) != 1
        or e2_closure.receipt(matching[0].data) != expected_init
    ):
        raise EvidenceError("P3.18 exact init authority is unavailable")
    return closure_api.exact_init_authority(matching[0].data)


@contextmanager
def _p301_e2_authority_context(
    closure_api: Any, expected_init: dict[str, Any]
):
    if closure_api is not p300_e2_closure.select(P300_SOURCE_CONTRACT_ID):
        raise EvidenceError("P3.01 parent stock-closure adapter differs")
    previous = p300_e2_closure.p286.p282._validate_p282_authority_strings  # noqa: SLF001

    def validate(data: bytes) -> None:
        if e2_closure.receipt(data) != expected_init:
            raise p300_e2_closure.ClosureError(
                "P3.01 effective init differs from bound identity"
            )
        printable = p300_e2_closure.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            data
        )
        paths = p300_e2_closure.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS
        if (
            p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS - paths
            or incidental != {'/E9"', "/R9@"}
            or any(data.count(value.encode("ascii")) != 1 for value in incidental)
        ):
            raise p300_e2_closure.ClosureError(
                "P3.01 effective init authority path set differs"
            )
        scrubbed = data
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))
        with p300_e2_closure._p300_authority_globals():  # noqa: SLF001
            p300_e2_closure._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001

    p300_e2_closure.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300_e2_closure.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


@contextmanager
def _p303_e2_authority_context(
    closure_api: Any, expected_init: dict[str, Any]
):
    if closure_api not in {
        p300_e2_closure.select(P300_SOURCE_CONTRACT_ID),
        p304_e2_closure,
    }:
        raise EvidenceError("P3.03 parent stock-closure adapter differs")
    previous = p300_e2_closure.p286.p282._validate_p282_authority_strings  # noqa: SLF001

    def validate(data: bytes) -> None:
        if e2_closure.receipt(data) != expected_init:
            raise p300_e2_closure.ClosureError(
                "P3.03 effective init differs from bound identity"
            )
        required = frozenset(
            {*p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS, "/dev/kmsg"}
        )
        allowed = frozenset(
            {*p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS, "/dev/kmsg"}
        )
        printable = p300_e2_closure.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            data
        )
        paths = p300_e2_closure.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - allowed
        if (
            required - paths
            or incidental != {'/E9"'}
            or data.count(b"/dev/kmsg") != 1
            or any(data.count(value.encode("ascii")) != 1 for value in incidental)
        ):
            raise p300_e2_closure.ClosureError(
                "P3.03 effective init authority path set differs"
            )
        scrubbed = data
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))
        old_required = p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS
        old_allowed = p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS
        p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = required
        p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = allowed
        try:
            with p300_e2_closure._p300_authority_globals():  # noqa: SLF001
                p300_e2_closure._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001
        finally:
            p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = old_required
            p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = old_allowed

    p300_e2_closure.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300_e2_closure.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


@contextmanager
def _p306_e2_authority_context(
    closure_api: Any, expected_init: dict[str, Any]
):
    if closure_api is not p304_e2_closure:
        raise EvidenceError("P3.06 parent stock-closure adapter differs")
    previous = p300_e2_closure.p286.p282._validate_p282_authority_strings  # noqa: SLF001

    def validate(data: bytes) -> None:
        if e2_closure.receipt(data) != expected_init:
            raise p300_e2_closure.ClosureError(
                "P3.06 effective init differs from bound identity"
            )
        additions = {
            "/dev/kmsg",
            "/sys/kernel/debug",
            "/sys/kernel/debug/ipc_logging/a600000_ssusb/log",
        }
        required = frozenset(
            {*p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS, *additions}
        )
        allowed = frozenset(
            {*p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS, *additions}
        )
        printable = p300_e2_closure.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            data
        )
        paths = p300_e2_closure.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - allowed
        if (
            required - paths
            or incidental != {'/E9"'}
            or data.count(b"/dev/kmsg") != 1
            or data.count(b"/sys/kernel/debug/ipc_logging/a600000_ssusb/log") != 1
            or any(data.count(value.encode("ascii")) != 1 for value in incidental)
        ):
            raise p300_e2_closure.ClosureError(
                "P3.06 effective init authority path set differs"
            )
        scrubbed = data
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))
        old_required = p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS
        old_allowed = p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS
        p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = required
        p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = allowed
        try:
            with p300_e2_closure._p300_authority_globals():  # noqa: SLF001
                p300_e2_closure._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001
        finally:
            p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = old_required
            p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = old_allowed

    p300_e2_closure.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300_e2_closure.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


@contextmanager
def _p307_e2_authority_context(
    closure_api: Any, expected_init: dict[str, Any]
):
    if closure_api is not p304_e2_closure:
        raise EvidenceError("P3.07 parent stock-closure adapter differs")
    previous = p300_e2_closure.p286.p282._validate_p282_authority_strings  # noqa: SLF001

    def validate(data: bytes) -> None:
        if e2_closure.receipt(data) != expected_init:
            raise p300_e2_closure.ClosureError(
                "P3.07 effective init differs from bound identity"
            )
        additions = {"/dev/kmsg", p307_spec.EUD_CACHE_PATH}
        required = frozenset(
            {*p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS, *additions}
        )
        allowed = frozenset(
            {*p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS, *additions}
        )
        printable = p300_e2_closure.p286.p282.p280.isolated_p260._printable_strings(  # noqa: SLF001
            data
        )
        paths = p300_e2_closure.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
        incidental = paths - allowed
        if (
            required - paths
            or incidental != {'/E9"'}
            or data.count(b"/dev/kmsg") != 1
            or data.count(p307_spec.EUD_CACHE_PATH.encode("ascii")) != 1
            or any(data.count(value.encode("ascii")) != 1 for value in incidental)
        ):
            raise p300_e2_closure.ClosureError(
                "P3.07 effective init authority path set differs"
            )
        scrubbed = data
        for value in sorted(incidental):
            encoded = value.encode("ascii")
            scrubbed = scrubbed.replace(encoded, b"\0" * len(encoded))
        old_required = p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS
        old_allowed = p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS
        p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = required
        p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = allowed
        try:
            with p300_e2_closure._p300_authority_globals():  # noqa: SLF001
                p300_e2_closure._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001
        finally:
            p300_e2_closure.REQUIRED_ABSOLUTE_PATH_STRINGS = old_required
            p300_e2_closure.ALLOWED_ABSOLUTE_PATH_STRINGS = old_allowed

    p300_e2_closure.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300_e2_closure.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001


def _latest_stage_terminal(selected_decoder, profile: str) -> int:
    terminal = getattr(selected_decoder, "TERMINAL_STAGE", None)
    if terminal is None:
        position = getattr(selected_decoder, "TERMINAL_POSITION", None)
        inherited = selected_decoder
        seen: set[int] = set()
        while position is None:
            inherited = getattr(inherited, "inherited", None)
            if inherited is None or id(inherited) in seen:
                break
            seen.add(id(inherited))
            position = getattr(inherited, "TERMINAL_POSITION", None)
        if (
            isinstance(position, tuple)
            and len(position) == 2
            and type(position[0]) is int
        ):
            terminal = position[0]
    if terminal is None:
        terminal = selected_decoder.model.PROFILE_TERMINALS.get(profile)
    if (
        isinstance(terminal, bool)
        or not isinstance(terminal, int)
        or not 0 <= terminal <= 0xFF
    ):
        raise EvidenceError("selected decoder terminal stage is invalid")
    return terminal


def _expected_reachable_record_contract(
    profile: str,
    source_contract_id: str | None,
    run_id_hex: str,
) -> dict[str, Any]:
    if source_contract_id is None:
        return {
            "reachable_slot_variants": _e1_reachable_slot_variant_count(
                profile
            ),
            "profiles": [profile],
            "checked_run_ids": {profile: run_id_hex},
            "adjacent_slot_combinations_verified": True,
            "zero_crc_count": 0,
            "family_collision_count": 0,
            "decoder_policy_id": e1_latest_stage.POLICY_ID,
            "verified": True,
        }
    try:
        result = _selected_contract(
            source_contract_id, profile
        ).validate_reachable_records(bytes.fromhex(run_id_hex))
    except (TypeError, ValueError) as exc:
        raise EvidenceError(
            "versioned reachable-record contract validation failed"
        ) from exc
    if not isinstance(result, dict):
        raise EvidenceError(
            "versioned reachable-record contract is not structured"
        )
    return dict(result)


def _validate_reachable_record_contract(
    value: Any,
    profile: str,
    source_contract_id: str | None,
    run_id_hex: str,
) -> dict[str, Any]:
    expected = _expected_reachable_record_contract(
        profile, source_contract_id, run_id_hex
    )
    actual = _exact(
        value,
        set(expected),
        "versioned reachable-record contract",
    )
    if any(
        type(actual[name]) is not type(expected_value)
        for name, expected_value in expected.items()
    ) or actual != expected:
        raise EvidenceError(
            "candidate static source contract is not E1A-bound, "
            "E1B-bound, or E2-bound: reachable-record contract "
            "differs from its source"
        )
    return actual


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise EvidenceError(f"{label} keys do not match the evidence schema")
    return value


def _strict_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python bool/int equivalence."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return (
            set(left) == set(right)
            and all(_strict_equal(left[key], right[key]) for key in left)
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _strict_equal(actual, expected)
            for actual, expected in zip(left, right, strict=True)
        )
    return left == right


def _artifact(
    value: Any,
    label: str,
    *,
    maximum: int = DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES,
) -> dict[str, Any]:
    item = _exact(value, {"path", "size", "sha256"}, label)
    if (
        not isinstance(item["path"], str)
        or not item["path"]
        or isinstance(item["size"], bool)
        or not isinstance(item["size"], int)
        or not 1 <= item["size"] <= maximum
        or not isinstance(item["sha256"], str)
        or HASH_RE.fullmatch(item["sha256"]) is None
    ):
        raise EvidenceError(f"{label} identity is invalid")
    return item


def _artifact_matches(value: Any, expected: dict[str, Any]) -> bool:
    return (
        isinstance(value, dict)
        and value.get("size") == expected.get("size")
        and value.get("sha256") == expected.get("sha256")
    )


def _binary_identity(value: Any, label: str) -> dict[str, Any]:
    item = _exact(value, {"size", "sha256"}, label)
    if (
        isinstance(item["size"], bool)
        or not isinstance(item["size"], int)
        or not 1 <= item["size"] <= 2**40
        or not isinstance(item["sha256"], str)
        or HASH_RE.fullmatch(item["sha256"]) is None
    ):
        raise EvidenceError(f"{label} identity is invalid")
    return item


def _validate_p298_historical_build_repair(
    source_build: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    repair = source_build.get("tier2_repair")
    expected_repair_keys = {
        "schema",
        "historical_postbuild_result",
        "historical_pre_lto_qualification",
        "a_b_artifacts_reopened",
        "a_b_artifact_inodes_distinct",
        "byte_identical_artifacts_reverified",
        "tier1_candidate_identity_changed",
        "tier2_repair_files",
        "fresh_full_lto_claimed",
        "verified",
    }
    expected_equal = sorted(P298_BUILD_ARTIFACTS - {"build-result.json"})
    if (
        source_build.get("fresh_reverification") is not False
        or source_build.get("immutable_build_time_proof_revalidated") is not True
        or source_build.get("result") != P298_HISTORICAL_POSTBUILD_RESULT
        or not isinstance(repair, dict)
        or set(repair) != expected_repair_keys
        or repair.get("schema")
        != "s22plus_fyg8_p298_postbuild_tier2_repair_v1"
        or repair.get("historical_postbuild_result")
        != P298_HISTORICAL_POSTBUILD_RESULT
        or repair.get("historical_pre_lto_qualification")
        != P298_HISTORICAL_QUALIFICATION
        or repair.get("a_b_artifact_inodes_distinct") is not True
        or repair.get("byte_identical_artifacts_reverified") != expected_equal
        or repair.get("tier1_candidate_identity_changed") is not False
        or repair.get("fresh_full_lto_claimed") is not False
        or repair.get("verified") is not True
    ):
        raise EvidenceError("P2.98 historical build repair contract differs")

    reopened = repair.get("a_b_artifacts_reopened")
    if not isinstance(reopened, dict) or set(reopened) != {"build_a", "build_b"}:
        raise EvidenceError("P2.98 historical A/B artifact proof is incomplete")
    normalized: dict[str, dict[str, dict[str, Any]]] = {}
    for build_name in ("build_a", "build_b"):
        artifacts = reopened.get(build_name)
        if not isinstance(artifacts, dict) or set(artifacts) != P298_BUILD_ARTIFACTS:
            raise EvidenceError(
                f"P2.98 historical {build_name} artifact inventory differs"
            )
        normalized[build_name] = {
            name: _binary_identity(value, f"P2.98 {build_name} {name}")
            for name, value in artifacts.items()
        }
    for name in expected_equal:
        if normalized["build_a"][name] != normalized["build_b"][name]:
            raise EvidenceError(f"P2.98 historical A/B {name} receipt differs")
    image = _binary_identity(source_build.get("image"), "P2.98 kernel Image")
    if (
        normalized["build_a"]["Image"] != image
        or normalized["build_b"]["Image"] != image
    ):
        raise EvidenceError("P2.98 historical A/B Image identity differs")

    expected_repair_paths = {
        p298_identity.TIER2_DIRECT_PATHS[name].as_posix()
        for name in P298_REPAIR_TIER2_KEYS
    }
    repair_files = repair.get("tier2_repair_files")
    if not isinstance(repair_files, dict) or set(repair_files) != expected_repair_paths:
        raise EvidenceError("P2.98 Tier-2 repair file inventory differs")
    return {
        path: _binary_identity(value, f"P2.98 Tier-2 repair {path}")
        for path, value in repair_files.items()
    }


def validate_candidate_source_preimage(
    contract: dict[str, Any], profile: str, run_id: str
) -> dict[str, dict[str, Any]]:
    source_contract_id = contract.get("source_contract_id")
    selected_decoder = _latest_stage_decoder(source_contract_id, profile)
    preimage_keys = {
        "schema",
        "target",
        "profile",
        "profile_number",
        "nonce",
        "decoder_id",
        "decoder_policy_id",
        "record_layout",
        "sources",
    }
    if source_contract_id is not None:
        _selected_contract(source_contract_id, profile)
        preimage_keys.add("source_contract_id")
    preimage = _exact(
        contract.get("identity_preimage"),
        preimage_keys,
        "candidate identity preimage",
    )
    source_keys = (
        _selected_contract(source_contract_id, profile).source_keys
        if source_contract_id is not None
        else E1_LATEST_STAGE_SOURCE_KEYS.get(profile)
    )
    sources = preimage.get("sources")
    if source_keys is None or not isinstance(sources, dict) or set(sources) != source_keys:
        raise EvidenceError("candidate identity source set is invalid")
    normalized_sources = {
        name: _binary_identity(value, f"candidate source {name}")
        for name, value in sources.items()
    }
    preimage_sha256 = hashlib.sha256(_canonical(preimage)).hexdigest()
    nonce = preimage.get("nonce")
    expected_schema = (
        _selected_contract(source_contract_id, profile).preimage_schema
        if source_contract_id is not None
        else E1_LATEST_STAGE_PREIMAGE_SCHEMA
    )
    run_id_domain = (
        _selected_contract(source_contract_id, profile).run_id_domain
        if source_contract_id is not None
        else E1_LATEST_STAGE_RUN_ID_DOMAINS[profile]
    )
    if (
        preimage.get("schema") != expected_schema
        or preimage.get("source_contract_id") != source_contract_id
        or preimage.get("target") != PID1_USERSPACE_TARGET
        or preimage.get("profile") != profile
        or type(preimage.get("profile_number")) is not int
        or preimage.get("profile_number")
        != selected_decoder.model.PROFILE_NUMBERS[profile]
        or not isinstance(nonce, str)
        or HEX32_RE.fullmatch(nonce) is None
        or nonce == "0" * 32
        or preimage.get("decoder_id") != selected_decoder.DECODER_ID
        or preimage.get("decoder_policy_id") != selected_decoder.POLICY_ID
        or preimage.get("record_layout")
        != (
            "S22E1L2-192-ab-header-slot-crc-payload64"
            if source_contract_id == P310_SOURCE_CONTRACT_ID
            else "S22E1L1-45-ab-crc32"
        )
        or contract.get("identity_preimage_sha256") != preimage_sha256
        or hashlib.sha256(
            run_id_domain + _canonical(preimage)
        ).digest()[:16].hex()
        != run_id
    ):
        raise EvidenceError("candidate source preimage or run ID derivation is invalid")
    return normalized_sources


def _generic_rootfs_module_closure(
    source_contract_id: str | None,
    closure_api: Any,
    module_closure: dict[str, Any],
) -> dict[str, Any]:
    if closure_api is p304_e2_closure:
        return module_closure
    if source_contract_id == P310_SOURCE_CONTRACT_ID:
        if closure_api not in {
            p310_e2_closure.select(P310_SOURCE_CONTRACT_ID),
            p311_e2_closure.select(P310_SOURCE_CONTRACT_ID),
            p312_e2_closure.select(P310_SOURCE_CONTRACT_ID),
            p313_e2_closure.select(P310_SOURCE_CONTRACT_ID),
            p314_e2_closure.select(P310_SOURCE_CONTRACT_ID),
            p315_e2_closure.select(P310_SOURCE_CONTRACT_ID),
            p316_e2_closure.select(P310_SOURCE_CONTRACT_ID),
            p317_e2_closure.select(P310_SOURCE_CONTRACT_ID),
            p318_e2_closure.select(P310_SOURCE_CONTRACT_ID),
        }:
            raise EvidenceError("P3.10 generic-rootfs closure adapter differs")
        return module_closure
    if source_contract_id not in {
        e2_closure_selector.P280_CONTRACT_ID,
        e2_closure_selector.P282_CONTRACT_ID,
        e2_closure_selector.P284_CONTRACT_ID,
        P286_SOURCE_CONTRACT_ID,
        P288_SOURCE_CONTRACT_ID,
        P290_SOURCE_CONTRACT_ID,
        P292_SOURCE_CONTRACT_ID,
        P294_SOURCE_CONTRACT_ID,
        P296_SOURCE_CONTRACT_ID,
        P298_SOURCE_CONTRACT_ID,
        P300_SOURCE_CONTRACT_ID,
        P310_SOURCE_CONTRACT_ID,
    }:
        return module_closure
    adapter_api = closure_api
    label = "P2.80"
    if source_contract_id in {
        e2_closure_selector.P284_CONTRACT_ID,
        P286_SOURCE_CONTRACT_ID,
        P288_SOURCE_CONTRACT_ID,
        P290_SOURCE_CONTRACT_ID,
        P292_SOURCE_CONTRACT_ID,
        P294_SOURCE_CONTRACT_ID,
        P296_SOURCE_CONTRACT_ID,
        P298_SOURCE_CONTRACT_ID,
        P300_SOURCE_CONTRACT_ID,
        P310_SOURCE_CONTRACT_ID,
    }:
        inherited_p282 = getattr(closure_api, "p282", None)
        adapter_api = getattr(inherited_p282, "p280", None)
        label = {
            P286_SOURCE_CONTRACT_ID: "P2.86",
            P288_SOURCE_CONTRACT_ID: "P2.88",
            P290_SOURCE_CONTRACT_ID: "P2.90",
            P292_SOURCE_CONTRACT_ID: "P2.92",
            P294_SOURCE_CONTRACT_ID: "P2.94",
            P296_SOURCE_CONTRACT_ID: "P2.96",
            P298_SOURCE_CONTRACT_ID: "P2.98",
            P300_SOURCE_CONTRACT_ID: "P3.00",
            P310_SOURCE_CONTRACT_ID: "P3.10",
            e2_closure_selector.P284_CONTRACT_ID: "P2.84",
        }[source_contract_id]
    elif source_contract_id == e2_closure_selector.P282_CONTRACT_ID:
        adapter_api = getattr(closure_api, "p280", None)
        label = "P2.82"
    try:
        if (
            getattr(
                getattr(adapter_api, "source_contract", None),
                "CONTRACT_ID",
                None,
            )
            != e2_closure_selector.P280_CONTRACT_ID
        ):
            raise AttributeError
        p257_adapter = adapter_api.isolated_p260.p257
        p253_adapter = adapter_api.isolated_p260.p253
        full_count = module_closure.get("count")
        if (
            isinstance(full_count, bool)
            or not isinstance(full_count, int)
            or full_count != closure_api.EXPECTED_MODULE_COUNT
        ):
            raise EvidenceError(
                f"{label} full module closure count is invalid"
            )
        expected_count = full_count - 1
        adapted = p253_adapter._legacy_view(
            p257_adapter._legacy_view(module_closure)
        )
    except (AttributeError, e2_closure.ClosureError) as exc:
        raise EvidenceError(
            f"{label} generic-rootfs module adapter is unavailable"
        ) from exc
    adapted_modules = adapted.get("modules") if isinstance(adapted, dict) else None
    if (
        not isinstance(adapted, dict)
        or adapted is module_closure
        or adapted.get("count") != expected_count
        or not isinstance(adapted_modules, list)
        or len(adapted_modules) != expected_count
    ):
        raise EvidenceError(
            f"{label} generic-rootfs module adapter result is invalid"
        )
    return adapted


def _latest_stage_accepted_identity(
    profile: str,
    source_contract_id: str | None,
    userspace_overlay_contract_id: str | None,
) -> str:
    if userspace_overlay_contract_id == P342_STOCK_OVERLAY_CONTRACT_ID:
        return "P342_STOCK_OBSERVER_V4_IDLE_REUSE"
    if userspace_overlay_contract_id == P341_STOCK_OVERLAY_CONTRACT_ID:
        return "P341_STOCK_OBSERVER_V4_OPEN_HEADER_CAPTURE"
    if userspace_overlay_contract_id == P340_STOCK_OVERLAY_CONTRACT_ID:
        return "P340_STOCK_OBSERVER_V4_OPEN_HEADER_CAPTURE"
    if userspace_overlay_contract_id == P339_STOCK_OVERLAY_CONTRACT_ID:
        return "P339_STOCK_OBSERVER_V4_OPEN_HEADER_CAPTURE"
    if userspace_overlay_contract_id == P338_STOCK_OVERLAY_CONTRACT_ID:
        return "P338_STOCK_OBSERVER_V4_OPEN_READ_BRANCH"
    if userspace_overlay_contract_id == P337_STOCK_OVERLAY_CONTRACT_ID:
        return "P337_STOCK_OBSERVER_V4_OPEN_READ_DIAGNOSTIC"
    if userspace_overlay_contract_id == P336_STOCK_OVERLAY_CONTRACT_ID:
        return "P336_STOCK_OBSERVER_V4_LONG_IDLE"
    if userspace_overlay_contract_id == P335_STOCK_OVERLAY_CONTRACT_ID:
        return "P335_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P334_STOCK_OVERLAY_CONTRACT_ID:
        return "P334_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P333_STOCK_OVERLAY_CONTRACT_ID:
        return "P333_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P332_STOCK_OVERLAY_CONTRACT_ID:
        return "P332_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P331_STOCK_OVERLAY_CONTRACT_ID:
        return "P331_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P330_STOCK_OVERLAY_CONTRACT_ID:
        return "P330_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P329_STOCK_OVERLAY_CONTRACT_ID:
        return "P329_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P328_STOCK_OVERLAY_CONTRACT_ID:
        return "P328_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P327_STOCK_OVERLAY_CONTRACT_ID:
        return "P327_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P326_STOCK_OVERLAY_CONTRACT_ID:
        return "P326_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P325_STOCK_OVERLAY_CONTRACT_ID:
        return "P325_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P324_STOCK_OVERLAY_CONTRACT_ID:
        return "P324_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P323_STOCK_OVERLAY_CONTRACT_ID:
        return "P323_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P322_STOCK_OVERLAY_CONTRACT_ID:
        return "P322_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P321_STOCK_OVERLAY_CONTRACT_ID:
        return "P321_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P320_STOCK_OVERLAY_CONTRACT_ID:
        return "P320_STOCK_OBSERVER_V4_RETAINED"
    if userspace_overlay_contract_id == P319_STOCK_OVERLAY_CONTRACT_ID:
        return "P319_STOCK_WITNESS_RETAINED"
    if (
        userspace_overlay_contract_id in P301_TELEMETRY_OVERLAY_IDS
        or source_contract_id == P310_SOURCE_CONTRACT_ID
    ):
        return "P301_TELEMETRY_RETAINED"
    return f"{profile}_TERMINAL_SUCCESS_REACHED"


def _validate_p319_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    authority = _exact(
        value.get("authority_source"),
        {"path", "size", "sha256"},
        "P3.19 candidate-static authority source",
    )
    if (
        authority["path"] != P319_CANDIDATE_STATIC_AUTHORITY_PATH
        or type(authority["size"]) is not int
        or authority["size"] <= 0
        or authority["size"] > 2 * 1024 * 1024
        or not isinstance(authority["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", authority["sha256"]) is None
    ):
        raise EvidenceError("P3.19 candidate-static authority identity differs")
    root = Path(__file__).resolve().parents[5]
    path = root / P319_CANDIDATE_STATIC_AUTHORITY_PATH
    try:
        before = path.lstat()
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
        ):
            raise EvidenceError("P3.19 candidate-static authority is indirect")
        data = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise EvidenceError("P3.19 candidate-static authority is unavailable") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    observed = {
        "path": P319_CANDIDATE_STATIC_AUTHORITY_PATH,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if before_id != after_id or before.st_size != len(data) or authority != observed:
        raise EvidenceError("P3.19 candidate-static authority source changed")
    namespace: dict[str, Any] = {
        "__file__": str(path),
        "__name__": "p319_candidate_static_bound_authority",
        "__package__": "",
    }
    try:
        exec(compile(data, str(path), "exec"), namespace)
        validator_name = "validate_bound_result" if runtime_bound else "validate_result"
        validate = namespace.get(validator_name)
        if not callable(validate):
            raise EvidenceError(
                f"P3.19 candidate-static authority lacks {validator_name}"
            )
        validate(value)
    except EvidenceError:
        raise
    except Exception as exc:
        raise EvidenceError(
            "P3.19 candidate-static authority rejected the result"
        ) from exc
    return observed


def _validate_p319_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema",
            "verdict",
            "authority_source",
            "target",
            "profile",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
            "integration",
            "candidate",
            "preflight",
            "adapter_contract",
            "adapter_source_receipts",
            "result_contract_arming",
            "runtime_observation_contract",
            "ready_manifest_created",
            "run_manifest_created",
            "approval_created",
            "safety",
        },
        "P3.19 candidate-static result",
    )
    if (
        item["schema"] != P319_CANDIDATE_STATIC_SCHEMA
        or item["verdict"] != P319_CANDIDATE_STATIC_VERDICT
        or item["target"] != P319_TARGET
        or item["profile"] != p319_stock_adapter.PROFILE
        or item["run_id"] != P319_RUN_ID
        or item["source_contract_id"]
        != p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P319_STOCK_OVERLAY_CONTRACT_ID
        or item["ready_manifest_created"] is not False
        or item["run_manifest_created"] is not False
        or item["approval_created"] is not False
    ):
        raise EvidenceError("P3.19 candidate-static header differs")

    adapter_contract = _exact(
        item["adapter_contract"],
        {
            "userspace_overlay_contract_id",
            "decoder",
            "policy_id",
            "profile",
            "acm_supplemental",
            "source_contract_id",
        },
        "P3.19 adapter contract",
    )
    try:
        p319_stock_adapter.validate_contract(adapter_contract)
    except p319_stock_adapter.DecodeError as exc:
        raise EvidenceError("P3.19 candidate-static adapter contract differs") from exc

    root = Path(__file__).resolve().parents[5]
    source_receipts = _exact(
        item["adapter_source_receipts"],
        set(p319_stock_adapter.SOURCE_KEYS),
        "P3.19 adapter source receipts",
    )
    try:
        source_payloads = p319_stock_adapter.source_bytes(root)
    except (OSError, p319_stock_adapter.DecodeError) as exc:
        raise EvidenceError("P3.19 adapter source closure is unavailable") from exc
    for name, payload in source_payloads.items():
        receipt = _exact(
            source_receipts[name],
            {"path", "size", "sha256"},
            f"P3.19 adapter source {name}",
        )
        if (
            receipt["path"] != p319_stock_adapter.SOURCE_PATHS[name]
            or _binary_identity(
                {key: receipt[key] for key in ("size", "sha256")},
                f"P3.19 adapter source {name}",
            )
            != {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        ):
            raise EvidenceError(f"P3.19 adapter source {name} differs")

    try:
        expected_arming = p319_stock_adapter.audit_result_contract_arming()
    except p319_stock_adapter.DecodeError as exc:
        raise EvidenceError("P3.19 result-contract arming cannot be reproduced") from exc
    if _canonical(item["result_contract_arming"]) != _canonical(expected_arming):
        raise EvidenceError("P3.19 result-contract arming differs")

    candidate = _exact(
        item["candidate"],
        {"plan", "identity", "cross_binding", "artifacts", "artifact_files"},
        "P3.19 candidate-static candidate",
    )
    plan = _exact(
        candidate["plan"],
        {"count", "eud_index", "overlay_delta"},
        "P3.19 candidate module plan",
    )
    if (
        type(plan["count"]) is not int
        or plan["count"] != 73
        or type(plan["eud_index"]) is not int
        or plan["eud_index"] != 38
        or plan["overlay_delta"] != ["s22plus_dwc3_event_latch.ko"]
    ):
        raise EvidenceError("P3.19 candidate module plan differs")
    expected_artifacts = {
        "candidate": {
            name: P319_EXACT_ARTIFACTS[name]
            for name in ("ap_tar_md5", "boot_img", "boot_img_lz4")
        },
        "userspace": {
            name: P319_EXACT_ARTIFACTS[name] for name in ("child", "init")
        },
    }
    if _canonical(candidate["artifacts"]) != _canonical(expected_artifacts):
        raise EvidenceError("P3.19 candidate artifact identity differs")
    cross_binding = candidate["cross_binding"]
    if (
        not isinstance(cross_binding, dict)
        or cross_binding.get("status") != "PASS_AUTHORITATIVE"
        or cross_binding.get("authoritative") is not True
        or _canonical(cross_binding.get("artifacts"))
        != _canonical(expected_artifacts)
        or _canonical(cross_binding.get("artifact_files"))
        != _canonical(candidate["artifact_files"])
    ):
        raise EvidenceError("P3.19 candidate cross-binding differs")
    identity_value = candidate["identity"]
    closure = identity_value.get("closure") if isinstance(identity_value, dict) else None
    if (
        not isinstance(closure, dict)
        or identity_value.get("run_id") != P319_RUN_ID
        or identity_value.get("fixed_image") != P319_EXACT_ARTIFACTS["image"]
        or closure.get("module_plan") != plan
    ):
        raise EvidenceError("P3.19 candidate identity closure differs")

    integration = _exact(
        item["integration"],
        {
            "receipt",
            "source",
            "zero_blockers",
            "candidate_baseline_cross_binding",
            "runtime_values_observed",
        },
        "P3.19 Integration V2 binding",
    )
    _artifact(integration["receipt"], "P3.19 Integration V2 receipt")
    _artifact(integration["source"], "P3.19 Integration V2 source")
    if (
        integration["zero_blockers"] is not True
        or integration["candidate_baseline_cross_binding"] != "PASS_AUTHORITATIVE"
        or integration["runtime_values_observed"] is not False
    ):
        raise EvidenceError("P3.19 Integration V2 boundary differs")

    preflight = _exact(
        item["preflight"],
        {
            "fresh_baseline",
            "consumed_candidate_registry",
            "prerequisite",
            "download_request_recovery",
        },
        "P3.19 candidate-static preflight",
    )
    if (
        not isinstance(preflight["fresh_baseline"], dict)
        or preflight["fresh_baseline"].get("authoritative") is not True
        or not isinstance(preflight["consumed_candidate_registry"], dict)
        or preflight["consumed_candidate_registry"].get("status") != "PRESENT"
        or not isinstance(preflight["prerequisite"], dict)
        or preflight["prerequisite"].get("registry_capability_authoritative")
        is not True
        or preflight["prerequisite"].get("runner_registry_consumption_proved")
        is not True
        or not isinstance(preflight["download_request_recovery"], dict)
        or preflight["download_request_recovery"].get("status")
        != "PASS_HOST_ONLY_RUNNER_FIXTURES"
        or preflight["download_request_recovery"].get("failures") != 0
        or preflight["download_request_recovery"].get("errors") != 0
        or preflight["download_request_recovery"].get("device_contact") is not False
        or preflight["download_request_recovery"].get("candidate_backend_called")
        is not False
    ):
        raise EvidenceError("P3.19 candidate-static preflight is incomplete")

    runtime = _exact(
        item["runtime_observation_contract"],
        {
            "post_run_classification_only",
            "runtime_values_observed",
            "witnesses",
            "missing_or_malformed_result",
            "precondition_failure_result",
            "complete_result",
            "acm_supplemental",
            "causal_result_allowed",
            "candidate_success",
            "mux_result_claimable",
            "host_silent_claimable",
        },
        "P3.19 runtime observation contract",
    )
    witnesses = _exact(
        runtime["witnesses"],
        {
            "module_results",
            "vbusdet_irq_tuple",
            "initial_status_classification_probe",
            "retained_carrier",
        },
        "P3.19 runtime witnesses",
    )
    for name, witness in witnesses.items():
        row = _exact(
            witness,
            {"required", "status", "accepted_as_preflight_fact", "requirement"},
            f"P3.19 runtime witness {name}",
        )
        if (
            row["required"] is not True
            or row["status"] != "PENDING_FRESH_CANDIDATE_RUN"
            or row["accepted_as_preflight_fact"] is not False
            or not isinstance(row["requirement"], str)
            or not row["requirement"]
        ):
            raise EvidenceError(f"P3.19 runtime witness {name} differs")
    if runtime != {
        **runtime,
        "post_run_classification_only": True,
        "runtime_values_observed": False,
        "missing_or_malformed_result": "NO_PROOF_OBSERVER",
        "precondition_failure_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
        "complete_result": "NONCAUSAL_SUCCESS_PATH",
        "acm_supplemental": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "mux_result_claimable": False,
        "host_silent_claimable": False,
    }:
        raise EvidenceError("P3.19 runtime result boundary differs")

    expected_safety = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "odin_transfer": False,
        "flash": False,
        "partition_write": False,
        "live_authorized": False,
        "d0_authorized": False,
        "d1_authorized": False,
        "f1_authorized": False,
        "replay_authorized": False,
        "causal_result_allowed": False,
        "candidate_success": False,
    }
    if item["safety"] != expected_safety:
        raise EvidenceError("P3.19 candidate-static safety boundary differs")
    _validate_p319_candidate_static_authority(
        item,
        runtime_bound=runtime_bound,
    )
    return item


def _validate_candidate_static_authority(
    value: dict[str, Any],
    *,
    authority_path: str,
    label: str,
    maximum: int,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Reopen a candidate-static validator at its exact source path."""
    authority = _exact(
        value.get("authority_source"),
        {"path", "size", "sha256"},
        f"{label} candidate-static authority source",
    )
    if (
        authority["path"] != authority_path
        or type(authority["size"]) is not int
        or authority["size"] <= 0
        or authority["size"] > maximum
        or not isinstance(authority["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", authority["sha256"]) is None
    ):
        raise EvidenceError(f"{label} candidate-static authority identity differs")
    root = Path(__file__).resolve().parents[5]
    path = root / authority_path
    try:
        before = path.lstat()
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
        ):
            raise EvidenceError(f"{label} candidate-static authority is indirect")
        data = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise EvidenceError(f"{label} candidate-static authority is unavailable") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    observed = {
        "path": authority_path,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if before_id != after_id or before.st_size != len(data) or authority != observed:
        raise EvidenceError(f"{label} candidate-static authority source changed")
    namespace: dict[str, Any] = {
        "__file__": str(path),
        "__name__": f"{label.lower().replace('.', '')}_candidate_static_bound_authority",
        "__package__": "",
    }
    try:
        exec(compile(data, str(path), "exec"), namespace)
        validator_name = "validate_bound_result" if runtime_bound else "validate_result"
        validate = namespace.get(validator_name)
        if not callable(validate):
            raise EvidenceError(
                f"{label} candidate-static authority lacks {validator_name}"
            )
        validate(value)
    except EvidenceError:
        raise
    except Exception as exc:
        raise EvidenceError(f"{label} candidate-static authority rejected the result") from exc
    return observed


def _validate_p320_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P320_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.20",
        maximum=P320_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p320_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.20 candidate-static result is not an object")
    _validate_p320_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p321_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P321_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.21",
        maximum=P321_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p321_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.21 candidate-static result is not an object")
    _validate_p321_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p322_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P322_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.22",
        maximum=P322_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p322_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.22 candidate-static result is not an object")
    _validate_p322_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p323_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P323_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.23",
        maximum=P323_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p323_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.23 candidate-static result is not an object")
    _validate_p323_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p324_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P324_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.24",
        maximum=P324_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p324_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.24 candidate-static result is not an object")
    _validate_p324_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p325_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P325_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.25",
        maximum=P325_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p325_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.25 candidate-static result is not an object")
    _validate_p325_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p326_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P326_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.26",
        maximum=P326_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p326_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.26 candidate-static result is not an object")
    _validate_p326_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p327_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P327_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.27",
        maximum=P327_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p327_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.27 candidate-static result is not an object")
    _validate_p327_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p328_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P328_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.28",
        maximum=P328_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p328_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.28 candidate-static result is not an object")
    _validate_p328_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p329_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P329_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.29",
        maximum=P329_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p329_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.29 candidate-static result is not an object")
    _validate_p329_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p330_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P330_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.30",
        maximum=P330_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p330_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.30 candidate-static result is not an object")
    _validate_p330_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p331_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P331_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.31",
        maximum=P331_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p331_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.31 candidate-static result is not an object")
    _validate_p331_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p332_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P332_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.32",
        maximum=P332_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p332_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.32 candidate-static result is not an object")
    _validate_p332_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p333_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P333_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.33",
        maximum=P333_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p333_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.33 candidate-static result is not an object")
    _validate_p333_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p334_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P334_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.34",
        maximum=P334_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p334_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.34 candidate-static result is not an object")
    _validate_p334_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p335_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P335_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.35",
        maximum=P335_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p335_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.35 candidate-static result is not an object")
    _validate_p335_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p336_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P336_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.36",
        maximum=P336_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p336_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.36 candidate-static result is not an object")
    _validate_p336_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p337_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P337_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.37",
        maximum=P337_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p337_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.37 candidate-static result is not an object")
    _validate_p337_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p338_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P338_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.38",
        maximum=P338_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p338_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.38 candidate-static result is not an object")
    _validate_p338_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p339_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P339_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.39",
        maximum=P339_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p339_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.39 candidate-static result is not an object")
    _validate_p339_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p340_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P340_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.40",
        maximum=P340_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p340_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.40 candidate-static result is not an object")
    _validate_p340_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p341_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P341_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.41",
        maximum=P341_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p341_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.41 candidate-static result is not an object")
    _validate_p341_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _validate_p342_candidate_static_authority(
    value: dict[str, Any],
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    return _validate_candidate_static_authority(
        value,
        authority_path=P342_CANDIDATE_STATIC_AUTHORITY_PATH,
        label="P3.42",
        maximum=P342_CANDIDATE_STATIC_MAX_BYTES,
        runtime_bound=runtime_bound,
    )


def _validate_p342_candidate_static(
    value: Any,
    *,
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("P3.42 candidate-static result is not an object")
    _validate_p342_candidate_static_authority(value, runtime_bound=runtime_bound)
    return value


def _p319_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    artifacts = candidate_static["candidate"]["artifacts"]
    return {
        "kind": "p319_exact_stock_witness_ap_v1",
        "boot_img_lz4": artifacts["candidate"]["boot_img_lz4"],
        "boot_image": artifacts["candidate"]["boot_img"],
        "image": P319_EXACT_ARTIFACTS["image"],
        "init": artifacts["userspace"]["init"],
        "child": artifacts["userspace"]["child"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "run_id": candidate_static["run_id"],
        "module_plan": candidate_static["candidate"]["plan"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p320_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    userspace = candidate["userspace"]["a"]
    artifacts = candidate["a"]
    return {
        "kind": "p320_exact_stock_observer_ap_v1",
        "boot_img_lz4": artifacts["boot_img_lz4"],
        "boot_image": artifacts["boot_img"],
        "image": candidate_static["builder_closure"]["inputs"]["fixed-Image"],
        "init": userspace["init"],
        "child": userspace["child"],
        "latch": candidate_static["builder_closure"]["module_bytes"][
            "s22plus_dwc3_event_latch.ko"
        ],
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p321_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    artifacts = candidate["a"]
    return {
        "kind": "p321_exact_stock_observer_ap_v1",
        "boot_img_lz4": artifacts["boot_img_lz4"],
        "boot_image": artifacts["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p322_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    artifacts = candidate["a"]
    return {
        "kind": "p322_exact_stock_observer_ap_v1",
        "boot_img_lz4": artifacts["boot_img_lz4"],
        "boot_image": artifacts["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p323_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    artifacts = candidate["a"]
    return {
        "kind": "p323_exact_stock_observer_ap_v1",
        "boot_img_lz4": artifacts["boot_img_lz4"],
        "boot_image": artifacts["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p324_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    artifacts = candidate["a"]
    return {
        "kind": "p324_exact_stock_observer_ap_v1",
        "boot_img_lz4": artifacts["boot_img_lz4"],
        "boot_image": artifacts["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p325_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    artifacts = candidate["a"]
    return {
        "kind": "p325_exact_stock_observer_ap_v1",
        "boot_img_lz4": artifacts["boot_img_lz4"],
        "boot_image": artifacts["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p326_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    artifacts = candidate["a"]
    return {
        "kind": "p326_exact_bidirectional_console_ap_v1",
        "boot_img_lz4": artifacts["boot_img_lz4"],
        "boot_image": artifacts["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p327_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p327_exact_framed_fixed_command_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p328_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    """Return the boot-only P3.28 AP closure without publishing key bytes."""
    candidate = candidate_static["candidate"]
    return {
        "kind": "p328_exact_authenticated_framed_exec_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P328_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P328_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P328_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p329_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p329_exact_authenticated_udev_settle_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P329_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P329_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P329_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p330_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p330_exact_authenticated_diagnostic_udev_settle_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P330_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P330_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P330_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p331_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p331_exact_authenticated_resident_udev_settle_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P331_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P331_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P331_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p332_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p332_exact_authenticated_logical_resident_same_fd_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P332_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P332_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P332_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p333_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p333_exact_authenticated_logical_resident_open_entry_diag_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P333_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P333_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P333_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p334_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p334_exact_authenticated_logical_resident_first_console_return_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P334_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P334_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P334_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p335_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p335_exact_authenticated_attended_resident_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P335_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P335_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P335_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p336_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p336_exact_authenticated_long_idle_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P336_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P336_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P336_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p337_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p337_exact_authenticated_open_read_diagnostic_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P337_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P337_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P337_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p338_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p338_exact_authenticated_open_read_branch_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P338_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P338_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P338_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p339_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p339_exact_authenticated_open_read_branch_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P339_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P339_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P339_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p340_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p340_exact_authenticated_open_read_branch_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P340_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P340_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P340_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p341_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p341_exact_authenticated_open_read_branch_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P341_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P341_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P341_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _p342_ap_payload_closure(candidate_static: dict[str, Any]) -> dict[str, Any]:
    candidate = candidate_static["candidate"]
    return {
        "kind": "p342_exact_authenticated_idle_reuse_ap_v1",
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "boot_image": candidate["a"]["boot_img"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
        "auth_key_schema": P342_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P342_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P342_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "run_id": candidate_static["run_id"],
        "source_contract_id": candidate_static["source_contract_id"],
        "userspace_overlay_contract_id": candidate_static[
            "userspace_overlay_contract_id"
        ],
    }


def _validate_p319_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
            "run_id",
            "module_plan",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.19 E2 AP payload closure",
    )
    identities = {
        name: _binary_identity(item[name], f"P3.19 E2 AP {name}")
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
        )
    }
    if (
        item["kind"] != "p319_exact_stock_witness_ap_v1"
        or item["run_id"] != P319_RUN_ID
        or not isinstance(item["module_plan"], dict)
        or set(item["module_plan"])
        != {"count", "eud_index", "overlay_delta"}
        or type(item["module_plan"].get("count")) is not int
        or item["module_plan"]["count"] != 73
        or type(item["module_plan"].get("eud_index")) is not int
        or item["module_plan"]["eud_index"] != 38
        or item["module_plan"].get("overlay_delta")
        != ["s22plus_dwc3_event_latch.ko"]
        or item["source_contract_id"]
        != p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P319_STOCK_OVERLAY_CONTRACT_ID
        or identities
        != {
            "boot_img_lz4": P319_EXACT_ARTIFACTS["boot_img_lz4"],
            "boot_image": P319_EXACT_ARTIFACTS["boot_img"],
            "image": P319_EXACT_ARTIFACTS["image"],
            "init": P319_EXACT_ARTIFACTS["init"],
            "child": P319_EXACT_ARTIFACTS["child"],
            "latch": P319_EXACT_ARTIFACTS["latch"],
        }
    ):
        raise EvidenceError("P3.19 E2 AP payload identity differs")
    if e2_closure.receipt(frame) != identities["boot_img_lz4"]:
        raise EvidenceError("P3.19 E2 AP boot member differs")
    try:
        boot_payload = e2_closure.boot_verify.decompress_lz4_frame_python(
            frame, expected_size=identities["boot_image"]["size"]
        )
        if e2_closure.receipt(boot_payload) != identities["boot_image"]:
            raise EvidenceError("P3.19 E2 AP decoded boot differs")
        boot = e2_closure.boot_verify.parse_boot_v4(boot_payload)
        if e2_closure.receipt(boot.kernel) != identities["image"]:
            raise EvidenceError("P3.19 E2 AP Image differs")
        ramdisk = e2_closure.boot_verify.decompress_lz4_stream_python(
            boot.ramdisk, maximum=128 * 1024 * 1024
        )
        entries = e2_closure.boot_verify.parse_newc(ramdisk)
    except e2_closure.boot_verify.BootVerifyError as exc:
        raise EvidenceError("P3.19 E2 AP cannot be independently decoded") from exc
    if len({entry.name for entry in entries}) != len(entries):
        raise EvidenceError("P3.19 E2 AP rootfs contains duplicate names")
    by_name = {entry.name: entry for entry in entries}
    if set(by_name) != P319_GENERIC_ROOTFS_NAMES:
        raise EvidenceError("P3.19 E2 AP generic rootfs inventory differs")
    checks = {
        "init": ("init", 0o100750),
        "child": ("s22-e1-child", 0o100750),
        "latch": ("lib/modules/s22plus_dwc3_event_latch.ko", 0o100640),
    }
    for identity_name, (entry_name, expected_mode) in checks.items():
        entry = by_name[entry_name]
        if entry.mode != expected_mode or e2_closure.receipt(entry.data) != identities[identity_name]:
            raise EvidenceError(f"P3.19 E2 AP {entry_name} differs")
    if {
        name for name in by_name if name.startswith("lib/modules/")
    } != {"lib/modules/s22plus_dwc3_event_latch.ko"}:
        raise EvidenceError("P3.19 E2 AP generic module overlay differs")
    return {"verified": True, **identities, "rootfs_entry_count": len(entries)}


def _validate_p320_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.20 E2 AP payload closure",
    )
    identities = {
        name: _binary_identity(item[name], f"P3.20 E2 AP {name}")
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
        )
    }
    if (
        item["kind"] != "p320_exact_stock_observer_ap_v1"
        or item["run_id"] != P320_RUN_ID
        or item["source_contract_id"] != p320_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P320_STOCK_OVERLAY_CONTRACT_ID
    ):
        raise EvidenceError("P3.20 E2 AP payload header differs")
    if e2_closure.receipt(frame) != identities["boot_img_lz4"]:
        raise EvidenceError("P3.20 E2 AP boot member differs")
    try:
        boot_payload = e2_closure.boot_verify.decompress_lz4_frame_python(
            frame, expected_size=identities["boot_image"]["size"]
        )
        if e2_closure.receipt(boot_payload) != identities["boot_image"]:
            raise EvidenceError("P3.20 E2 AP decoded boot differs")
        boot = e2_closure.boot_verify.parse_boot_v4(boot_payload)
        if e2_closure.receipt(boot.kernel) != identities["image"]:
            raise EvidenceError("P3.20 E2 AP Image differs")
        ramdisk = e2_closure.boot_verify.decompress_lz4_stream_python(
            boot.ramdisk, maximum=128 * 1024 * 1024
        )
        entries = e2_closure.boot_verify.parse_newc(ramdisk)
    except e2_closure.boot_verify.BootVerifyError as exc:
        raise EvidenceError("P3.20 E2 AP cannot be independently decoded") from exc
    if len({entry.name for entry in entries}) != len(entries):
        raise EvidenceError("P3.20 E2 AP rootfs contains duplicate names")
    by_name = {entry.name: entry for entry in entries}
    if set(by_name) != P319_GENERIC_ROOTFS_NAMES:
        raise EvidenceError("P3.20 E2 AP rootfs inventory differs")
    checks = {
        "init": ("init", 0o100750),
        "child": ("s22-e1-child", 0o100750),
        "latch": ("lib/modules/s22plus_dwc3_event_latch.ko", 0o100640),
    }
    for identity_name, (entry_name, expected_mode) in checks.items():
        entry = by_name[entry_name]
        if (
            entry.mode != expected_mode
            or e2_closure.receipt(entry.data) != identities[identity_name]
        ):
            raise EvidenceError(f"P3.20 E2 AP {entry_name} differs")
    return {"verified": True, **identities, "rootfs_entry_count": len(entries)}


def _validate_p321_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.21 E2 AP payload closure",
    )
    if (
        item["kind"] != "p321_exact_stock_observer_ap_v1"
        or item["run_id"] != P321_RUN_ID
        or item["source_contract_id"] != p321_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P321_STOCK_OVERLAY_CONTRACT_ID
    ):
        raise EvidenceError("P3.21 E2 AP payload header differs")
    identities = {
        name: _binary_identity(item[name], f"P3.21 E2 AP {name}")
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
        )
    }
    # P3.21 has the same generic rootfs/AP semantics as P3.20.  Validate those
    # bytes through the reviewed helper, while retaining the fresh P3.21 header.
    p320_closure = {
        **item,
        "kind": "p320_exact_stock_observer_ap_v1",
        "run_id": P320_RUN_ID,
        "userspace_overlay_contract_id": P320_STOCK_OVERLAY_CONTRACT_ID,
    }
    verified = _validate_p320_e2_ap_payload(frame, p320_closure)
    return {
        "verified": True,
        **identities,
        "rootfs_entry_count": verified["rootfs_entry_count"],
        "run_id": P321_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
    }


def _validate_p322_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.22 E2 AP payload closure",
    )
    if (
        item["kind"] != "p322_exact_stock_observer_ap_v1"
        or item["run_id"] != P322_RUN_ID
        or item["source_contract_id"] != p322_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P322_STOCK_OVERLAY_CONTRACT_ID
    ):
        raise EvidenceError("P3.22 E2 AP payload header differs")
    identities = {
        name: _binary_identity(item[name], f"P3.22 E2 AP {name}")
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
        )
    }
    # P3.22 retains the reviewed generic rootfs/AP semantics of P3.20 while
    # rebinding the fresh P3.22 run and overlay identities.
    p320_closure = {
        **item,
        "kind": "p320_exact_stock_observer_ap_v1",
        "run_id": P320_RUN_ID,
        "userspace_overlay_contract_id": P320_STOCK_OVERLAY_CONTRACT_ID,
    }
    verified = _validate_p320_e2_ap_payload(frame, p320_closure)
    return {
        "verified": True,
        **identities,
        "rootfs_entry_count": verified["rootfs_entry_count"],
        "run_id": P322_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
    }


def _validate_p323_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.23 E2 AP payload closure",
    )
    if (
        item["kind"] != "p323_exact_stock_observer_ap_v1"
        or item["run_id"] != P323_RUN_ID
        or item["source_contract_id"] != p323_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P323_STOCK_OVERLAY_CONTRACT_ID
    ):
        raise EvidenceError("P3.23 E2 AP payload header differs")
    identities = {
        name: _binary_identity(item[name], f"P3.23 E2 AP {name}")
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
        )
    }
    # The P323 userspace keeps the reviewed generic rootfs shape; only the
    # exact candidate identities and P323 header are fresh.
    p322_closure = {
        **item,
        "kind": "p322_exact_stock_observer_ap_v1",
        "run_id": P322_RUN_ID,
        "userspace_overlay_contract_id": P322_STOCK_OVERLAY_CONTRACT_ID,
    }
    # Reuse the structural checker while preserving the P323 identities in
    # this return value.  The checker only validates the decoded frame against
    # the closure supplied to it.
    p320_closure = {
        **p322_closure,
        "kind": "p320_exact_stock_observer_ap_v1",
        "run_id": P320_RUN_ID,
        "userspace_overlay_contract_id": P320_STOCK_OVERLAY_CONTRACT_ID,
    }
    verified = _validate_p320_e2_ap_payload(frame, p320_closure)
    return {
        "verified": True,
        **identities,
        "rootfs_entry_count": verified["rootfs_entry_count"],
        "run_id": P323_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
    }


def _validate_p324_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.24 E2 AP payload closure",
    )
    if (
        item["kind"] != "p324_exact_stock_observer_ap_v1"
        or item["run_id"] != P324_RUN_ID
        or item["source_contract_id"]
        != p324_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P324_STOCK_OVERLAY_CONTRACT_ID
    ):
        raise EvidenceError("P3.24 E2 AP payload header differs")
    identities = {
        name: _binary_identity(item[name], f"P3.24 E2 AP {name}")
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
        )
    }
    structural = {
        **item,
        "kind": "p320_exact_stock_observer_ap_v1",
        "run_id": P320_RUN_ID,
        "userspace_overlay_contract_id": P320_STOCK_OVERLAY_CONTRACT_ID,
    }
    verified = _validate_p320_e2_ap_payload(frame, structural)
    return {
        "verified": True,
        **identities,
        "rootfs_entry_count": verified["rootfs_entry_count"],
        "run_id": P324_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item[
            "userspace_overlay_contract_id"
        ],
    }


def _validate_p325_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.25 E2 AP payload closure",
    )
    if (
        item["kind"] != "p325_exact_stock_observer_ap_v1"
        or item["run_id"] != P325_RUN_ID
        or item["source_contract_id"]
        != p325_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P325_STOCK_OVERLAY_CONTRACT_ID
    ):
        raise EvidenceError("P3.25 E2 AP payload header differs")
    identities = {
        name: _binary_identity(item[name], f"P3.25 E2 AP {name}")
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "latch",
        )
    }
    structural = {
        **item,
        "kind": "p320_exact_stock_observer_ap_v1",
        "run_id": P320_RUN_ID,
        "userspace_overlay_contract_id": P320_STOCK_OVERLAY_CONTRACT_ID,
    }
    verified = _validate_p320_e2_ap_payload(frame, structural)
    return {
        "verified": True,
        **identities,
        "rootfs_entry_count": verified["rootfs_entry_count"],
        "run_id": P325_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item[
            "userspace_overlay_contract_id"
        ],
    }


def _validate_p326_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.26 E2 AP payload closure",
    )
    if (
        item["kind"] != "p326_exact_bidirectional_console_ap_v1"
        or item["run_id"] != P326_RUN_ID
        or item["source_contract_id"]
        != p326_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P326_STOCK_OVERLAY_CONTRACT_ID
    ):
        raise EvidenceError("P3.26 E2 AP payload header differs")
    identities = {
        name: _binary_identity(item[name], f"P3.26 E2 AP {name}")
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
        )
    }
    if e2_closure.receipt(frame) != identities["boot_img_lz4"]:
        raise EvidenceError("P3.26 E2 AP boot member differs")
    try:
        boot_payload = e2_closure.boot_verify.decompress_lz4_frame_python(
            frame, expected_size=identities["boot_image"]["size"]
        )
        if e2_closure.receipt(boot_payload) != identities["boot_image"]:
            raise EvidenceError("P3.26 E2 AP decoded boot differs")
        boot = e2_closure.boot_verify.parse_boot_v4(boot_payload)
        if e2_closure.receipt(boot.kernel) != identities["image"]:
            raise EvidenceError("P3.26 E2 AP Image differs")
        ramdisk = e2_closure.boot_verify.decompress_lz4_stream_python(
            boot.ramdisk, maximum=128 * 1024 * 1024
        )
        entries = e2_closure.boot_verify.parse_newc(ramdisk)
    except e2_closure.boot_verify.BootVerifyError as exc:
        raise EvidenceError("P3.26 E2 AP cannot be independently decoded") from exc
    if len({entry.name for entry in entries}) != len(entries):
        raise EvidenceError("P3.26 E2 AP rootfs contains duplicate names")
    by_name = {entry.name: entry for entry in entries}
    expected_names = set(P319_GENERIC_ROOTFS_NAMES) | {"bin", "bin/busybox"}
    if set(by_name) != expected_names:
        raise EvidenceError("P3.26 E2 AP rootfs inventory differs")
    checks = {
        "init": ("init", 0o100750),
        "child": ("s22-e1-child", 0o100750),
        "busybox": ("bin/busybox", 0o100755),
        "latch": ("lib/modules/s22plus_dwc3_event_latch.ko", 0o100640),
    }
    for identity_name, (entry_name, expected_mode) in checks.items():
        entry = by_name[entry_name]
        if (
            entry.mode != expected_mode
            or e2_closure.receipt(entry.data) != identities[identity_name]
        ):
            raise EvidenceError(f"P3.26 E2 AP {entry_name} differs")
    if by_name["bin"].mode != 0o040755 or by_name["bin"].data:
        raise EvidenceError("P3.26 E2 AP bin directory differs")
    return {
        "verified": True,
        **identities,
        "rootfs_entry_count": len(entries),
        "run_id": P326_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
    }


def _validate_p327_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.27 E2 AP payload closure",
    )
    if (
        item["kind"] != "p327_exact_framed_fixed_command_ap_v1"
        or item["run_id"] != P327_RUN_ID
        or item["source_contract_id"]
        != p327_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P327_STOCK_OVERLAY_CONTRACT_ID
    ):
        raise EvidenceError("P3.27 E2 AP payload header differs")
    identities = {
        name: _binary_identity(item[name], f"P3.27 E2 AP {name}")
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
        )
    }
    if e2_closure.receipt(frame) != identities["boot_img_lz4"]:
        raise EvidenceError("P3.27 E2 AP boot member differs")
    try:
        boot_payload = e2_closure.boot_verify.decompress_lz4_frame_python(
            frame, expected_size=identities["boot_image"]["size"]
        )
        if e2_closure.receipt(boot_payload) != identities["boot_image"]:
            raise EvidenceError("P3.27 E2 AP decoded boot differs")
        boot = e2_closure.boot_verify.parse_boot_v4(boot_payload)
        if e2_closure.receipt(boot.kernel) != identities["image"]:
            raise EvidenceError("P3.27 E2 AP Image differs")
        ramdisk = e2_closure.boot_verify.decompress_lz4_stream_python(
            boot.ramdisk, maximum=128 * 1024 * 1024
        )
        entries = e2_closure.boot_verify.parse_newc(ramdisk)
    except e2_closure.boot_verify.BootVerifyError as exc:
        raise EvidenceError(
            "P3.27 E2 AP cannot be independently decoded"
        ) from exc
    if len({entry.name for entry in entries}) != len(entries):
        raise EvidenceError("P3.27 E2 AP rootfs contains duplicate names")
    by_name = {entry.name: entry for entry in entries}
    expected_names = set(P319_GENERIC_ROOTFS_NAMES) | {"bin", "bin/busybox"}
    if set(by_name) != expected_names:
        raise EvidenceError("P3.27 E2 AP rootfs inventory differs")
    checks = {
        "init": ("init", 0o100750),
        "child": ("s22-e1-child", 0o100750),
        "busybox": ("bin/busybox", 0o100755),
        "latch": ("lib/modules/s22plus_dwc3_event_latch.ko", 0o100640),
    }
    for identity_name, (entry_name, expected_mode) in checks.items():
        entry = by_name[entry_name]
        if (
            entry.mode != expected_mode
            or e2_closure.receipt(entry.data) != identities[identity_name]
        ):
            raise EvidenceError(f"P3.27 E2 AP {entry_name} differs")
    if by_name["bin"].mode != 0o040755 or by_name["bin"].data:
        raise EvidenceError("P3.27 E2 AP bin directory differs")
    return {
        "verified": True,
        **identities,
        "rootfs_entry_count": len(entries),
        "run_id": P327_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
    }


def _validate_p328_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.28's authenticated successor with the P3.27 AP parser."""
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
            "auth_key_schema",
            "auth_key_size",
            "auth_key",
            "auth_key_path_published",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.28 E2 AP payload closure",
    )
    if (
        item["kind"] != "p328_exact_authenticated_framed_exec_ap_v1"
        or item["run_id"] != P328_RUN_ID
        or item["source_contract_id"]
        != p328_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P328_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P328_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P328_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P328_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.28 E2 AP payload header differs")
    identities = {
        name: _binary_identity(item[name], f"P3.28 E2 AP {name}")
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
        )
    }
    structural = {
        name: item[name]
        for name in (
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
        )
    }
    structural.update(
        {
            "kind": "p327_exact_framed_fixed_command_ap_v1",
            "run_id": P327_RUN_ID,
            "source_contract_id": p327_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P327_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p327_e2_ap_payload(frame, structural)
    return {
        "verified": True,
        **identities,
        "rootfs_entry_count": verified["rootfs_entry_count"],
        "run_id": P328_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item[
            "userspace_overlay_contract_id"
        ],
        "auth_key_schema": item["auth_key_schema"],
        "auth_key_size": item["auth_key_size"],
        "auth_key": dict(item["auth_key"]),
        "auth_key_path_published": False,
    }


def _validate_p329_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.29 by reusing P3.28's unchanged AP/rootfs grammar."""
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
            "auth_key_schema",
            "auth_key_size",
            "auth_key",
            "auth_key_path_published",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.29 E2 AP payload closure",
    )
    if (
        item["kind"] != "p329_exact_authenticated_udev_settle_ap_v1"
        or item["run_id"] != P329_RUN_ID
        or item["source_contract_id"]
        != p329_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P329_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P329_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P329_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P329_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.29 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p328_exact_authenticated_framed_exec_ap_v1",
            "run_id": P328_RUN_ID,
            "source_contract_id": p328_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P328_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p328_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P329_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "udev_guard_settle_bounded": True,
    }


def _validate_p330_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.30 through P3.29's unchanged AP/rootfs grammar."""
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
            "auth_key_schema",
            "auth_key_size",
            "auth_key",
            "auth_key_path_published",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.30 E2 AP payload closure",
    )
    if (
        item["kind"]
        != "p330_exact_authenticated_diagnostic_udev_settle_ap_v1"
        or item["run_id"] != P330_RUN_ID
        or item["source_contract_id"]
        != p330_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P330_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P330_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P330_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P330_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.30 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p329_exact_authenticated_udev_settle_ap_v1",
            "run_id": P329_RUN_ID,
            "source_contract_id": p329_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P329_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p329_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P330_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "udev_guard_settle_bounded": True,
        "preauth_diagnostics_bounded": True,
    }


def _validate_p331_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.31 through the unchanged boot-only/rootfs grammar."""
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
            "auth_key_schema",
            "auth_key_size",
            "auth_key",
            "auth_key_path_published",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.31 E2 AP payload closure",
    )
    if (
        item["kind"] != "p331_exact_authenticated_resident_udev_settle_ap_v1"
        or item["run_id"] != P331_RUN_ID
        or item["source_contract_id"]
        != p331_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P331_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P331_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P331_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P331_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.31 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p330_exact_authenticated_diagnostic_udev_settle_ap_v1",
            "run_id": P330_RUN_ID,
            "source_contract_id": p330_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P330_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p330_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P331_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "udev_guard_settle_bounded": True,
        "preauth_diagnostics_bounded": True,
        "resident_sessions_bounded": True,
        "resident_reconnect_bounded": True,
        "fixed_heartbeat_only": True,
    }


def _validate_p332_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.32 through the unchanged boot-only/rootfs grammar."""
    item = _exact(
        closure,
        {
            "kind",
            "boot_img_lz4",
            "boot_image",
            "image",
            "init",
            "child",
            "busybox",
            "latch",
            "auth_key_schema",
            "auth_key_size",
            "auth_key",
            "auth_key_path_published",
            "run_id",
            "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.32 E2 AP payload closure",
    )
    if (
        item["kind"] != "p332_exact_authenticated_logical_resident_same_fd_ap_v1"
        or item["run_id"] != P332_RUN_ID
        or item["source_contract_id"]
        != p332_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P332_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P332_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P332_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P332_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.32 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p330_exact_authenticated_diagnostic_udev_settle_ap_v1",
            "run_id": P330_RUN_ID,
            "source_contract_id": p330_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P330_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p330_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P332_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "udev_guard_settle_bounded": True,
        "preauth_diagnostics_bounded": True,
        "logical_sessions_bounded": True,
        "same_tty_fd_required": True,
        "physical_reopen_count": 0,
        "fixed_p330_commands": True,
    }


def _validate_p333_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate the P3.33 one-anchor delta through the P3.32 AP grammar."""
    item = _exact(
        closure,
        {
            "kind", "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch", "auth_key_schema", "auth_key_size", "auth_key",
            "auth_key_path_published", "run_id", "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.33 E2 AP payload closure",
    )
    if (
        item["kind"]
        != "p333_exact_authenticated_logical_resident_open_entry_diag_ap_v1"
        or item["run_id"] != P333_RUN_ID
        or item["source_contract_id"]
        != p333_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P333_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P333_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P333_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P333_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.33 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p332_exact_authenticated_logical_resident_same_fd_ap_v1",
            "run_id": P332_RUN_ID,
            "source_contract_id": p332_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P332_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p332_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P333_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "entry_diagnostic_stage": 0,
        "entry_diagnostic_before_console": True,
    }


def _validate_p334_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.34 through the unchanged P3.33 AP grammar."""
    item = _exact(
        closure,
        {
            "kind", "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch", "auth_key_schema", "auth_key_size", "auth_key",
            "auth_key_path_published", "run_id", "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.34 E2 AP payload closure",
    )
    if (
        item["kind"]
        != "p334_exact_authenticated_logical_resident_first_console_return_ap_v1"
        or item["run_id"] != P334_RUN_ID
        or item["source_contract_id"]
        != p334_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"]
        != P334_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P334_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P334_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P334_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.34 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p333_exact_authenticated_logical_resident_open_entry_diag_ap_v1",
            "run_id": P333_RUN_ID,
            "source_contract_id": p333_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P333_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    # P3.34's AP bytes retain the P3.33 boot-only grammar.  The outer
    # first-console-return detail is a runtime receipt and does not alter the
    # payload member closure.
    verified = _validate_p333_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P334_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "entry_diagnostic_stage": 0,
        "entry_diagnostic_before_console": True,
        "first_console_return_checkpoint_only": True,
        "first_console_return_detail_prefix": P334_AUTH_EXEC_DETAIL_PREFIX,
        "first_console_return_detail_sentinel": P334_AUTH_EXEC_DETAIL_SENTINEL,
        "first_read_attribution_requires_stage0_without_stage1": True,
    }


def _validate_p335_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.35 through the unchanged boot-only P3.34 AP grammar."""
    item = _exact(
        closure,
        {
            "kind", "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch", "auth_key_schema", "auth_key_size", "auth_key",
            "auth_key_path_published", "run_id", "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.35 E2 AP payload closure",
    )
    if (
        item["kind"] != "p335_exact_authenticated_attended_resident_ap_v1"
        or item["run_id"] != P335_RUN_ID
        or item["source_contract_id"] != p335_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P335_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P335_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P335_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P335_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.35 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p334_exact_authenticated_logical_resident_first_console_return_ap_v1",
            "run_id": P334_RUN_ID,
            "source_contract_id": p334_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P334_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p334_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P335_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "initial_session_count": P335_AUTH_EXEC_SESSION_CAP,
        "physical_reopen_count": 1,
        "per_boot_identity_required": True,
        "listener_wait_after_proof": True,
    }


def _validate_p336_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.36 through the exact P3.35 boot-only AP grammar."""
    item = _exact(
        closure,
        {
            "kind", "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch", "auth_key_schema", "auth_key_size", "auth_key",
            "auth_key_path_published", "run_id", "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.36 E2 AP payload closure",
    )
    if (
        item["kind"] != "p336_exact_authenticated_long_idle_ap_v1"
        or item["run_id"] != P336_RUN_ID
        or item["source_contract_id"] != p336_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P336_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P336_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P336_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P336_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.36 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p335_exact_authenticated_attended_resident_ap_v1",
            "run_id": P335_RUN_ID,
            "source_contract_id": p335_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P335_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p335_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P336_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "initial_session_count": P336_AUTH_EXEC_SESSION_CAP,
        "physical_reopen_count": 1,
        "per_boot_identity_required": True,
        "listener_wait_after_proof": True,
        "long_idle_host_resync": True,
        "later_action_open_before_resync": True,
    }


def _validate_p337_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.37 through the exact P3.36 boot-only AP grammar."""
    item = _exact(
        closure,
        {
            "kind", "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch", "auth_key_schema", "auth_key_size", "auth_key",
            "auth_key_path_published", "run_id", "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.37 E2 AP payload closure",
    )
    if (
        item["kind"] != "p337_exact_authenticated_open_read_diagnostic_ap_v1"
        or item["run_id"] != P337_RUN_ID
        or item["source_contract_id"] != p337_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P337_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P337_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P337_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P337_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.37 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p336_exact_authenticated_long_idle_ap_v1",
            "run_id": P336_RUN_ID,
            "source_contract_id": p336_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P336_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p336_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P337_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "retry_added": False,
        "timeout_changed": False,
    }


def _validate_p338_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.38 through the unchanged P3.37 boot-only AP grammar."""
    item = _exact(
        closure,
        {
            "kind", "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch", "auth_key_schema", "auth_key_size", "auth_key",
            "auth_key_path_published", "run_id", "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.38 E2 AP payload closure",
    )
    if (
        item["kind"] != "p338_exact_authenticated_open_read_branch_ap_v1"
        or item["run_id"] != P338_RUN_ID
        or item["source_contract_id"] != p338_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P338_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P338_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P338_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P338_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.38 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p337_exact_authenticated_open_read_diagnostic_ap_v1",
            "run_id": P337_RUN_ID,
            "source_contract_id": p337_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P337_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p337_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P338_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "open_read_branch_ordinals": dict(P338_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
        "open_read_branch_count": P338_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
        "original_errno_returned_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
    }


def _validate_p339_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.39 through the unchanged P3.38 boot-only AP grammar."""
    item = _exact(
        closure,
        {
            "kind", "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch", "auth_key_schema", "auth_key_size", "auth_key",
            "auth_key_path_published", "run_id", "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.39 E2 AP payload closure",
    )
    if (
        item["kind"] != "p339_exact_authenticated_open_read_branch_ap_v1"
        or item["run_id"] != P339_RUN_ID
        or item["source_contract_id"] != p339_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P339_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P339_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P339_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P339_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.39 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p338_exact_authenticated_open_read_branch_ap_v1",
            "run_id": P338_RUN_ID,
            "source_contract_id": p338_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P338_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p338_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P339_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "open_read_branch_ordinals": dict(P339_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
        "open_read_branch_count": P339_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
        "open_header_word_stages": list(P339_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
        "open_header_size": P339_AUTH_EXEC_OPEN_HEADER_SIZE,
        "open_header_capture_best_effort": True,
        "original_errno_returned_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
    }


def _validate_p340_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.40 through the unchanged P3.39/P3.38 AP grammar."""
    item = _exact(
        closure,
        {
            "kind", "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch", "auth_key_schema", "auth_key_size", "auth_key",
            "auth_key_path_published", "run_id", "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.40 E2 AP payload closure",
    )
    if (
        item["kind"] != "p340_exact_authenticated_open_read_branch_ap_v1"
        or item["run_id"] != P340_RUN_ID
        or item["source_contract_id"] != p340_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P340_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P340_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P340_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P340_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.40 E2 AP payload header differs")
    inherited = dict(item)
    inherited.update(
        {
            "kind": "p339_exact_authenticated_open_read_branch_ap_v1",
            "run_id": P339_RUN_ID,
            "source_contract_id": p339_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P339_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p339_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P340_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "open_read_branch_ordinals": dict(P340_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
        "open_read_branch_count": P340_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
        "open_header_word_stages": list(P340_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
        "open_header_size": P340_AUTH_EXEC_OPEN_HEADER_SIZE,
        "open_header_capture_best_effort": True,
        "original_errno_returned_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
        "initial_failure_suffix_capture": True,
        "maximum_failure_suffix_bytes": 96,
    }


def _validate_p341_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.41 through the exact P3.40 AP grammar and host-first ID."""
    item = _exact(
        closure,
        {
            "kind", "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch", "auth_key_schema", "auth_key_size", "auth_key",
            "auth_key_path_published", "run_id", "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.41 E2 AP payload closure",
    )
    if (
        item["kind"] != "p341_exact_authenticated_open_read_branch_ap_v1"
        or item["run_id"] != P341_RUN_ID
        or item["source_contract_id"] != p341_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P341_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P341_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P341_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P341_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.41 E2 AP payload header differs")
    # Validate the physical boot/AP/rootfs geometry through the oldest fixed
    # grammar.  Only the host-first closure header above is P341-specific;
    # this avoids relabelling a P340 AP while keeping the inherited parser
    # implementation private to the validation seam.
    inherited = {
        key: item[key]
        for key in (
            "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch",
        )
    }
    inherited.update(
        {
            "kind": "p327_exact_framed_fixed_command_ap_v1",
            "run_id": P327_RUN_ID,
            "source_contract_id": p327_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P327_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p327_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P341_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "open_read_branch_ordinals": dict(P341_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
        "open_read_branch_count": P341_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
        "open_header_word_stages": list(P341_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
        "open_header_size": P341_AUTH_EXEC_OPEN_HEADER_SIZE,
        "open_header_capture_best_effort": True,
        "host_first_open": True,
        "banner_after_open": True,
        "original_errno_returned_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
    }


def _validate_p342_e2_ap_payload(frame: bytes, closure: Any) -> dict[str, Any]:
    """Validate P3.42 through the fixed boot/AP grammar and fresh header."""
    item = _exact(
        closure,
        {
            "kind", "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch", "auth_key_schema", "auth_key_size", "auth_key",
            "auth_key_path_published", "run_id", "source_contract_id",
            "userspace_overlay_contract_id",
        },
        "P3.42 E2 AP payload closure",
    )
    if (
        item["kind"] != "p342_exact_authenticated_idle_reuse_ap_v1"
        or item["run_id"] != P342_RUN_ID
        or item["source_contract_id"] != p342_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or item["userspace_overlay_contract_id"] != P342_STOCK_OVERLAY_CONTRACT_ID
        or item["auth_key_schema"] != P342_AUTH_EXEC_AUTH_KEY_SCHEMA
        or item["auth_key_size"] != P342_AUTH_EXEC_AUTH_KEY_SIZE
        or item["auth_key"] != P342_AUTH_EXEC_AUTH_KEY_IDENTITY
        or item["auth_key_path_published"] is not False
    ):
        raise EvidenceError("P3.42 E2 AP payload header differs")
    inherited = {
        key: item[key]
        for key in (
            "boot_img_lz4", "boot_image", "image", "init", "child",
            "busybox", "latch",
        )
    }
    inherited.update(
        {
            "kind": "p327_exact_framed_fixed_command_ap_v1",
            "run_id": P327_RUN_ID,
            "source_contract_id": p327_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P327_STOCK_OVERLAY_CONTRACT_ID,
        }
    )
    verified = _validate_p327_e2_ap_payload(frame, inherited)
    return {
        **verified,
        "run_id": P342_RUN_ID,
        "source_contract_id": item["source_contract_id"],
        "userspace_overlay_contract_id": item["userspace_overlay_contract_id"],
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "open_read_branch_ordinals": dict(P342_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
        "open_read_branch_count": P342_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
        "open_header_word_stages": list(P342_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
        "open_header_size": P342_AUTH_EXEC_OPEN_HEADER_SIZE,
        "open_header_capture_best_effort": True,
        "host_first_open": True,
        "banner_after_open": True,
        "idle_reuse": {
            "same_fd_session_count": P342_SAME_FD_SESSION_COUNT,
            "requested_seconds": P342_IDLE_REUSE_REQUESTED_SECONDS,
            "total_session_count": P342_TOTAL_SESSION_COUNT,
            "total_command_count": P342_TOTAL_COMMAND_COUNT,
        },
        "original_errno_returned_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
    }


def validate_e2_ap_payload(
    frame: bytes, closure: Any
) -> dict[str, Any]:
    source_contract_id = (
        closure.get("source_contract_id") if isinstance(closure, dict) else None
    )
    userspace_overlay_contract_id = (
        closure.get("userspace_overlay_contract_id")
        if isinstance(closure, dict)
        else None
    )
    if userspace_overlay_contract_id == P342_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p342_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P341_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p341_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P340_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p340_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P339_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p339_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P338_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p338_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P337_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p337_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P336_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p336_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P335_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p335_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P334_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p334_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P333_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p333_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P332_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p332_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P331_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p331_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P330_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p330_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P329_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p329_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P328_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p328_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P327_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p327_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P326_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p326_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P325_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p325_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P324_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p324_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P323_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p323_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P322_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p322_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P321_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p321_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P320_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p320_e2_ap_payload(frame, closure)
    if userspace_overlay_contract_id == P319_STOCK_OVERLAY_CONTRACT_ID:
        return _validate_p319_e2_ap_payload(frame, closure)
    expected_keys = {
        "boot_img_lz4",
        "boot_image",
        "image",
        "init",
        "child",
        "run_id",
        "module_closure",
        "effective_rootfs",
    }
    if source_contract_id is not None:
        _selected_contract(source_contract_id, "E2")
        expected_keys.add("source_contract_id")
    if userspace_overlay_contract_id is not None:
        _latest_stage_observation_decoder(
            source_contract_id,
            "E2",
            userspace_overlay_contract_id,
        )
        expected_keys.add("userspace_overlay_contract_id")
    closure_api = _select_e2_closure(
        source_contract_id, userspace_overlay_contract_id
    )
    expected = _exact(
        closure,
        expected_keys,
        "E2 AP payload closure",
    )
    identities = {
        name: _binary_identity(value, f"E2 AP {name}")
        for name, value in expected.items()
        if name in {"boot_img_lz4", "boot_image", "image", "init", "child"}
    }
    run_id = expected.get("run_id")
    if not isinstance(run_id, str) or HEX32_RE.fullmatch(run_id) is None:
        raise EvidenceError("E2 AP run ID is invalid")
    try:
        module_closure = closure_api.validate_module_closure(
            expected.get("module_closure")
        )
        effective_rootfs = closure_api.validate_effective_rootfs(
            expected.get("effective_rootfs"),
            expected_init=identities["init"],
            expected_child=identities["child"],
            module_closure=module_closure,
        )
    except e2_closure.ClosureError as exc:
        raise EvidenceError("E2 AP semantic closure is invalid") from exc
    if e2_closure.receipt(frame) != identities["boot_img_lz4"]:
        raise EvidenceError("E2 AP boot member identity mismatch")
    try:
        boot_payload = e2_closure.boot_verify.decompress_lz4_frame_python(
            frame,
            expected_size=identities["boot_image"]["size"],
        )
        if e2_closure.receipt(boot_payload) != identities["boot_image"]:
            raise EvidenceError("E2 AP decoded boot identity mismatch")
        boot = e2_closure.boot_verify.parse_boot_v4(boot_payload)
        if e2_closure.receipt(boot.kernel) != identities["image"]:
            raise EvidenceError("E2 AP kernel identity mismatch")
        ramdisk = e2_closure.boot_verify.decompress_lz4_stream_python(
            boot.ramdisk, maximum=128 * 1024 * 1024
        )
        entries = e2_closure.boot_verify.parse_newc(ramdisk)
        generic_module_closure = _generic_rootfs_module_closure(
            source_contract_id, closure_api, module_closure
        )
        if userspace_overlay_contract_id == P318_MAX77705_OVERLAY_CONTRACT_ID:
            authority_context = _p318_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif userspace_overlay_contract_id == P317_MAX77705_OVERLAY_CONTRACT_ID:
            authority_context = _p317_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif userspace_overlay_contract_id in MAX77705_OVERLAY_CONTRACT_IDS:
            authority_context = _p316_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif userspace_overlay_contract_id == P315_OVERLAY_CONTRACT_ID:
            authority_context = _p315_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif userspace_overlay_contract_id == P314_OVERLAY_CONTRACT_ID:
            authority_context = _p314_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif userspace_overlay_contract_id == P313_OVERLAY_CONTRACT_ID:
            authority_context = _p313_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
            authority_context = _p312_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
            authority_context = _p311_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif source_contract_id == P310_SOURCE_CONTRACT_ID:
            authority_context = _p310_e2_authority_context(
                closure_api, entries, identities["init"]
            )
        elif userspace_overlay_contract_id in {
            P307_OVERLAY_CONTRACT_ID,
            P308_OVERLAY_CONTRACT_ID,
        }:
            authority_context = _p307_e2_authority_context(
                closure_api, identities["init"]
            )
        elif userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
            authority_context = _p306_e2_authority_context(
                closure_api, identities["init"]
            )
        elif userspace_overlay_contract_id in {
            P303_OVERLAY_CONTRACT_ID,
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
        }:
            authority_context = _p303_e2_authority_context(
                closure_api, identities["init"]
            )
        elif userspace_overlay_contract_id in P301_TELEMETRY_OVERLAY_IDS:
            authority_context = _p301_e2_authority_context(
                closure_api, identities["init"]
            )
        else:
            authority_context = _e2_authority_context(
                source_contract_id, closure_api
            )
        with authority_context:
            generic_rootfs = closure_api.audit_candidate_generic_rootfs(
                boot,
                entries,
                expected_init=identities["init"],
                expected_child=identities["child"],
                run_id=bytes.fromhex(run_id),
                module_closure=generic_module_closure,
            )
    except e2_closure.boot_verify.BootVerifyError as exc:
        raise EvidenceError("E2 AP payload cannot be independently decoded") from exc
    except e2_closure.ClosureError as exc:
        raise EvidenceError("E2 AP executable semantics mismatch") from exc
    if _canonical(generic_rootfs) != _canonical(effective_rootfs["generic_rootfs"]):
        raise EvidenceError("E2 AP generic rootfs differs from static closure")
    return {"verified": True, **identities, "generic_rootfs": generic_rootfs}


def validate_e1b_stock_closure(
    *,
    module_closure: Any,
    effective_rootfs: Any,
    stock_vendor_boot: Any,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
) -> None:
    closure = _exact(
        module_closure,
        {
            "files",
            "runtime_names",
            "count",
            "modules",
            "order_model",
            "stock_recovery_positions",
            "vendor_metadata_hashes",
        },
        "E1B module closure",
    )
    expected_closure = {
        "files": E1B_MODULE_FILES,
        "runtime_names": E1B_MODULE_RUNTIME_NAMES,
        "count": len(E1B_MODULE_FILES),
        "modules": E1B_MODULE_SPECS,
        "order_model": E1B_MODULE_ORDER_MODEL,
        "stock_recovery_positions": E1B_STOCK_RECOVERY_POSITIONS,
        "vendor_metadata_hashes": E1B_VENDOR_METADATA_HASHES,
    }
    if closure != expected_closure:
        raise EvidenceError("E1B stock module derivation differs from the pinned closure")

    rootfs = _exact(
        effective_rootfs,
        {
            "composition_order",
            "entry_count",
            "no_duplicate_override_or_alias",
            "init",
            "child",
            "modules",
            "module_count",
            "rdinit_override_absent",
            "verified",
        },
        "E1B effective rootfs",
    )
    init = _exact(
        rootfs["init"],
        {"size", "sha256", "elf", "run_id_count"},
        "E1B effective init",
    )
    child = _exact(
        rootfs["child"], {"size", "sha256", "elf"}, "E1B effective child"
    )
    init_elf = _exact(
        init["elf"],
        {
            "machine",
            "entrypoint",
            "interpreter",
            "dynamic",
            "executable_stack",
            "entrypoint_mapped",
            "verified",
        },
        "E1B effective init ELF",
    )
    child_elf = _exact(
        child["elf"],
        {
            "machine",
            "entrypoint",
            "interpreter",
            "dynamic",
            "executable_stack",
            "entrypoint_mapped",
            "verified",
        },
        "E1B effective child ELF",
    )
    expected_elf = {
        "machine": "AArch64",
        "interpreter": False,
        "dynamic": False,
        "executable_stack": False,
        "entrypoint_mapped": True,
        "verified": True,
    }
    if (
        _binary_identity(
            {name: init[name] for name in ("size", "sha256")},
            "E1B effective init",
        )
        != expected_init
        or _binary_identity(
            {name: child[name] for name in ("size", "sha256")},
            "E1B effective child",
        )
        != expected_child
        or init.get("run_id_count") != 1
        or init_elf
        != {**expected_elf, "entrypoint": E1B_ELF_ENTRYPOINTS["init"]}
        or child_elf
        != {**expected_elf, "entrypoint": E1B_ELF_ENTRYPOINTS["child"]}
        or rootfs.get("composition_order") != E1B_COMPOSITION_ORDER
        or rootfs.get("entry_count") != E1B_EFFECTIVE_ENTRY_COUNT
        or rootfs.get("no_duplicate_override_or_alias") is not True
        or rootfs.get("modules") != E1B_EFFECTIVE_MODULE_ROWS
        or rootfs.get("module_count") != len(E1B_EFFECTIVE_MODULE_ROWS)
        or rootfs.get("rdinit_override_absent") is not True
        or rootfs.get("verified") is not True
    ):
        raise EvidenceError("E1B effective stock rootfs differs from the pinned closure")

    if _binary_identity(stock_vendor_boot, "E1B stock vendor_boot") != E1B_STOCK_VENDOR_BOOT:
        raise EvidenceError("E1B stock vendor_boot identity changed")


def _record_blob_claim(
    value: Any, label: str, artifact: dict[str, Any]
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "label",
            "size",
            "sha256",
            "entry_count",
            "userspace_count",
            "unsat_count",
            "long_family_count",
            "unsat_family_count",
            "old_e0_entry_count",
            "old_e0_userspace_count",
            "verified",
        },
        label,
    )
    expected_counts = {
        "entry_count": 1,
        "userspace_count": 1,
        "unsat_count": 1,
        "long_family_count": 2,
        "unsat_family_count": 1,
        "old_e0_entry_count": 0,
        "old_e0_userspace_count": 0,
    }
    if (
        item["label"] != label
        or not _artifact_matches(item, artifact)
        or any(item[key] != count for key, count in expected_counts.items())
        or item["verified"] is not True
    ):
        raise EvidenceError(f"{label} record claim is invalid")
    return item


def _bounded_text(value: Any, label: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or "\x00" in value
    ):
        raise EvidenceError(f"{label} must be a bounded string")
    return value


def p328_authenticated_framed_observer_spec() -> dict[str, Any]:
    """Return the exact fixed-proof projection for the P3.28 ACM lane."""
    commands = tuple(
        (
            "size",
            len(command),
            "sha256",
            hashlib.sha256(command).hexdigest(),
        )
        for command in (
            b"/bin/busybox id",
            b"/bin/busybox uname -a",
            (
                "/bin/busybox echo P328-NONCE "
                + P328_AUTH_EXEC_RUN_ID_HEX
            ).encode("ascii"),
        )
    )
    return {
        "kind": "exact_cdc_acm_authenticated_framed_commands_v1",
        "usb_vendor_id": "04e8",
        "usb_product_id": "6861",
        "usb_serial": "S22E3" + P328_AUTH_EXEC_RUN_ID_HEX,
        "usb_driver": "cdc_acm",
        "usb_interface_number": "00",
        "banner_hex": (
            "S22PLUS-FYG8-E3:" + P328_AUTH_EXEC_RUN_ID_HEX + "\n"
        ).encode("ascii").hex(),
        "protocol_contract": P328_AUTH_EXEC_OBSERVER_CONTRACT_ID,
        "wire_magic": "S328",
        "frame_header_size": 16,
        "max_frame_payload": P328_AUTH_EXEC_MAX_FRAME_PAYLOAD,
        "max_commands": P328_AUTH_EXEC_MAX_COMMANDS,
        "command_timeout_sec": P328_AUTH_EXEC_COMMAND_TIMEOUT_SEC,
        "max_output_bytes": P328_AUTH_EXEC_MAX_OUTPUT_BYTES,
        "auth_algorithm": P328_AUTH_EXEC_AUTH_ALGORITHM,
        "auth_tag_size": P328_AUTH_EXEC_AUTH_TAG_SIZE,
        "auth_key_schema": P328_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key_size": P328_AUTH_EXEC_AUTH_KEY_SIZE,
        "auth_key": dict(P328_AUTH_EXEC_AUTH_KEY_IDENTITY),
        "auth_key_path_published": False,
        "authentication_required": True,
        "per_session_random_nonce": True,
        "proof_command_count": P328_AUTH_EXEC_COMMAND_COUNT,
        "commands": [
            {key: value for key, value in zip(entry[::2], entry[1::2])}
            for entry in commands
        ],
        "caller_selected_command": True,
        "interactive_pty": False,
        "raw_rx_forwarded_before_classification": True,
        "host_only": True,
        "device_contact": False,
    }


def p329_authenticated_framed_observer_spec() -> dict[str, Any]:
    """Return P3.28's protocol with the fresh P3.29 run and bounded settle."""
    value = p328_authenticated_framed_observer_spec()
    value.update(
        {
            "usb_serial": "S22E3" + P329_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": (
                "S22PLUS-FYG8-E3:" + P329_AUTH_EXEC_RUN_ID_HEX + "\n"
            ).encode("ascii").hex(),
            "protocol_contract": P329_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in (
                    b"/bin/busybox id",
                    b"/bin/busybox uname -a",
                    (
                        "/bin/busybox echo P328-NONCE "
                        + P329_AUTH_EXEC_RUN_ID_HEX
                    ).encode("ascii"),
                )
            ],
            "udev_guard_settle_timeout_ms": 500,
            "udev_guard_settle_poll_ms": 25,
            "guard_properties_required": [
                "ID_MM_DEVICE_IGNORE=1",
                "ID_MM_PORT_IGNORE=1",
            ],
        }
    )
    return value


def p330_authenticated_framed_observer_spec() -> dict[str, Any]:
    """Return P3.29's settled lane with bounded P3.30 diagnostics."""
    value = p329_authenticated_framed_observer_spec()
    value.update(
        {
            "usb_serial": "S22E3" + P330_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": (
                "S22PLUS-FYG8-E3:" + P330_AUTH_EXEC_RUN_ID_HEX + "\n"
            ).encode("ascii").hex(),
            "protocol_contract": P330_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in (
                    b"/bin/busybox id",
                    b"/bin/busybox uname -a",
                    (
                        "/bin/busybox echo P328-NONCE "
                        + P330_AUTH_EXEC_RUN_ID_HEX
                    ).encode("ascii"),
                )
            ],
            "diagnostic_frame_type": P330_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE,
            "diagnostic_payload_size": P330_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE,
            "diagnostic_stages": [
                {"stage": 1, "name": "open-parsed"},
                {"stage": 2, "name": "rng"},
            ],
            "rng_eagain_retry_limit": P330_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT,
            "open_diagnostic_timeout_ms": 5000,
            "rng_diagnostic_timeout_ms": 10000,
            "partial_exchange_durable": True,
        }
    )
    return value


def p331_authenticated_resident_framed_observer_spec() -> dict[str, Any]:
    """Return the exact P3.31 two-session resident observer identity."""
    value = p330_authenticated_framed_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_resident_framed_session_v1",
            "schema": p331_resident_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P331_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": (
                "S22PLUS-FYG8-E3:" + P331_AUTH_EXEC_RUN_ID_HEX + "\n"
            ).encode("ascii").hex(),
            "protocol_contract": P331_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(P331_AUTH_EXEC_HEARTBEAT_COMMAND),
                    "sha256": hashlib.sha256(
                        P331_AUTH_EXEC_HEARTBEAT_COMMAND
                    ).hexdigest(),
                }
            ],
            "proof_command_count": P331_AUTH_EXEC_COMMAND_COUNT,
            "max_commands": P331_AUTH_EXEC_MAX_COMMANDS,
            "caller_selected_command": False,
            "auth_key_schema": P331_AUTH_EXEC_AUTH_KEY_SCHEMA,
            "auth_key_size": P331_AUTH_EXEC_AUTH_KEY_SIZE,
            "auth_key": dict(P331_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "diagnostic_frame_type": P331_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE,
            "diagnostic_payload_size": P331_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE,
            "diagnostic_stages": [
                {"stage": 1, "name": "open-parsed"},
                {"stage": 2, "name": "rng"},
            ],
            "rng_eagain_retry_limit": P331_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT,
            "open_diagnostic_timeout_ms": 5000,
            "rng_diagnostic_timeout_ms": 10000,
            "partial_exchange_durable": True,
            "session_cap": P331_AUTH_EXEC_SESSION_CAP,
            "reconnect_cap": P331_AUTH_EXEC_RECONNECT_CAP,
            "clean_close_required": True,
            "clean_reconnect_required": True,
            "fresh_distinct_nonce_hashes": True,
            "diagnostics_per_session": True,
            "fixed_heartbeat_only": True,
            "arbitrary_file_transfer": False,
            "persistent_state": False,
            "resident_loop_proof": True,
        }
    )
    return value


p331_authenticated_framed_observer_spec = (
    p331_authenticated_resident_framed_observer_spec
)
p331_resident_observer_spec = p331_authenticated_resident_framed_observer_spec


def validate_p331_resident_proof(value: Any) -> dict[str, Any]:
    """Validate the bounded observer receipt without inventing nonce bytes."""
    expected_keys = {
        "schema",
        "contract_id",
        "target",
        "run_id_hex",
        "session_cap",
        "reconnect_cap",
        "session_count",
        "successful_sessions",
        "reconnect_count",
        "sessions",
        "banner_attempts",
        "banner_scope",
        "fixed_heartbeat_status",
        "caller_selected_command",
        "interactive_pty",
        "arbitrary_file_transfer",
        "persistent_state",
        "resident_loop_proof",
        "partial_raw_retention",
    }
    item = _exact(value, expected_keys, "P3.31 resident observer proof")
    if (
        item["schema"] != p331_resident_acm_observer.SCHEMA
        or item["contract_id"] != P331_AUTH_EXEC_OBSERVER_CONTRACT_ID
        or item["target"] != p331_resident_exec_runtime.TARGET
        or item["run_id_hex"] != P331_AUTH_EXEC_RUN_ID_HEX
        or any(
            type(item[key]) is not int
            for key in (
                "session_cap",
                "reconnect_cap",
                "session_count",
                "successful_sessions",
                "reconnect_count",
                "banner_attempts",
            )
        )
        or item["session_cap"] != P331_AUTH_EXEC_SESSION_CAP
        or item["reconnect_cap"] != P331_AUTH_EXEC_RECONNECT_CAP
        or item["session_count"] != P331_AUTH_EXEC_SESSION_CAP
        or item["successful_sessions"] != P331_AUTH_EXEC_SESSION_CAP
        or item["reconnect_count"] != P331_AUTH_EXEC_RECONNECT_CAP
        or item["banner_attempts"] != P331_AUTH_EXEC_SESSION_CAP
        or item["banner_scope"] != "resident_loop_per_session"
        or item["fixed_heartbeat_status"] is not True
        or item["caller_selected_command"] is not False
        or item["interactive_pty"] is not False
        or item["arbitrary_file_transfer"] is not False
        or item["persistent_state"] is not False
        or item["resident_loop_proof"] is not True
        or item["partial_raw_retention"] is not True
    ):
        raise EvidenceError("P3.31 resident observer proof header differs")
    sessions = item["sessions"]
    if not isinstance(sessions, list) or len(sessions) != P331_AUTH_EXEC_SESSION_CAP:
        raise EvidenceError("P3.31 resident observer session count differs")
    nonce_hashes: set[str] = set()
    session_keys = {
        "session_index",
        "reconnect_index",
        "challenge_nonce_sha256",
        "auth_key_sha256",
        "tx",
        "rx",
        "authenticated",
        "clean_close",
        "command",
        "output",
    }
    for index, session in enumerate(sessions):
        row = _exact(session, session_keys, f"P3.31 resident session {index}")
        nonce_hash = row["challenge_nonce_sha256"]
        if (
            type(row["session_index"]) is not int
            or type(row["reconnect_index"]) is not int
            or row["session_index"] != index
            or row["reconnect_index"] != index
            or not isinstance(nonce_hash, str)
            or HASH_RE.fullmatch(nonce_hash) is None
            or nonce_hash == "0" * 64
            or nonce_hash in nonce_hashes
            or row["auth_key_sha256"] != P331_AUTH_EXEC_AUTH_KEY_IDENTITY["sha256"]
            or row["authenticated"] is not True
            or row["clean_close"] is not True
        ):
            raise EvidenceError(
                f"P3.31 resident session {index} authentication/nonce differs"
            )
        nonce_hashes.add(nonce_hash)
        for label, expected in (
            ("command", P331_AUTH_EXEC_HEARTBEAT_COMMAND),
            ("output", P331_AUTH_EXEC_HEARTBEAT_OUTPUT),
        ):
            identity = _binary_identity(
                row[label], f"P3.31 resident session {index} {label}"
            )
            if identity != {
                "size": len(expected),
                "sha256": hashlib.sha256(expected).hexdigest(),
            }:
                raise EvidenceError(
                    f"P3.31 resident session {index} {label} differs"
                )
        _binary_identity(row["tx"], f"P3.31 resident session {index} TX")
        _binary_identity(row["rx"], f"P3.31 resident session {index} RX")
    return item


validate_p331_resident_arrival_proof = validate_p331_resident_proof


def p332_authenticated_logical_resident_observer_spec() -> dict[str, Any]:
    """Return the exact P3.32 two-session, one-descriptor observer identity."""
    value = p330_authenticated_framed_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_logical_resident_same_fd_session_v1",
            "schema": p332_logical_resident_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P332_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": (
                "S22PLUS-FYG8-E3:" + P332_AUTH_EXEC_RUN_ID_HEX + "\n"
            ).encode("ascii").hex(),
            "protocol_contract": P332_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p332_logical_resident_exec_runtime.DEFAULT_COMMANDS
            ],
            "proof_command_count": P332_AUTH_EXEC_COMMAND_COUNT,
            "max_commands": P332_AUTH_EXEC_MAX_COMMANDS,
            "caller_selected_command": False,
            "auth_key_schema": P332_AUTH_EXEC_AUTH_KEY_SCHEMA,
            "auth_key_size": P332_AUTH_EXEC_AUTH_KEY_SIZE,
            "auth_key": dict(P332_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "diagnostic_frame_type": P332_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE,
            "diagnostic_payload_size": P332_AUTH_EXEC_DIAGNOSTIC_PAYLOAD_SIZE,
            "diagnostic_stages": [
                {"stage": 1, "name": "open-parsed"},
                {"stage": 2, "name": "rng"},
            ],
            "rng_eagain_retry_limit": P332_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT,
            "open_diagnostic_timeout_ms": 5000,
            "rng_diagnostic_timeout_ms": 10000,
            "partial_exchange_durable": True,
            "session_cap": P332_AUTH_EXEC_SESSION_CAP,
            "reconnect_cap": P332_AUTH_EXEC_RECONNECT_CAP,
            "clean_close_required": True,
            "fresh_distinct_nonce_hashes": True,
            "diagnostics_per_session": True,
            "fixed_p330_commands": True,
            "same_tty_fd_required": True,
            "host_tty_close_reopen": False,
            "transport_reconnect": False,
            "arbitrary_file_transfer": False,
            "persistent_state": False,
            "logical_resident_proof": True,
        }
    )
    return value


def validate_p332_logical_resident_proof(value: Any) -> dict[str, Any]:
    try:
        return p332_logical_resident_acm_observer.validate_proof_value(
            value,
            expected_auth_key_sha256=P332_AUTH_EXEC_AUTH_KEY_IDENTITY["sha256"],
        )
    except (ValueError, p332_logical_resident_acm_observer.AuthObserverError) as exc:
        raise EvidenceError("P3.32 logical resident observer proof differs") from exc


def p333_authenticated_logical_resident_observer_spec() -> dict[str, Any]:
    """Return P3.32's exact same-FD role plus the stage-0 entry diagnostic."""
    value = p332_authenticated_logical_resident_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_logical_resident_open_entry_diag_session_v1",
            "schema": p333_open_entry_diag_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P333_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": (
                "S22PLUS-FYG8-E3:" + P333_AUTH_EXEC_RUN_ID_HEX + "\n"
            ).encode("ascii").hex(),
            "protocol_contract": P333_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p333_open_entry_diag_runtime.DEFAULT_COMMANDS
            ],
            "proof_command_count": P333_AUTH_EXEC_COMMAND_COUNT,
            "max_commands": P333_AUTH_EXEC_MAX_COMMANDS,
            "auth_key": dict(P333_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "diagnostic_stages": [
                {"stage": 0, "name": "console-enter"},
                {"stage": 1, "name": "open-parsed"},
                {"stage": 2, "name": "rng"},
            ],
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
        }
    )
    return value


def validate_p333_logical_resident_proof(value: Any) -> dict[str, Any]:
    try:
        return p333_open_entry_diag_acm_observer.validate_proof_value(
            value,
            expected_auth_key_sha256=P333_AUTH_EXEC_AUTH_KEY_IDENTITY["sha256"],
        )
    except (ValueError, p333_open_entry_diag_acm_observer.AuthObserverError) as exc:
        raise EvidenceError("P3.33 logical resident observer proof differs") from exc


def p334_authenticated_logical_resident_observer_spec() -> dict[str, Any]:
    """Return P3.33's exact session contract with the P3.34 return receipt."""
    value = p333_authenticated_logical_resident_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_logical_resident_first_console_return_session_v1",
            "schema": p334_first_read_rc_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P334_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": (
                "S22PLUS-FYG8-E3:" + P334_AUTH_EXEC_RUN_ID_HEX + "\n"
            ).encode("ascii").hex(),
            "protocol_contract": P334_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p334_first_read_rc_runtime.DEFAULT_COMMANDS
            ],
            "proof_command_count": P334_AUTH_EXEC_COMMAND_COUNT,
            "max_commands": P334_AUTH_EXEC_MAX_COMMANDS,
            "auth_key": dict(P334_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "first_console_return_checkpoint_only": True,
            "first_console_return_detail_prefix": P334_AUTH_EXEC_DETAIL_PREFIX,
            "first_console_return_detail_sentinel": P334_AUTH_EXEC_DETAIL_SENTINEL,
            "first_read_attribution_requires_stage0_without_stage1": True,
        }
    )
    return value


def validate_p334_logical_resident_proof(value: Any) -> dict[str, Any]:
    try:
        return p334_first_read_rc_acm_observer.validate_proof_value(
            value,
            expected_auth_key_sha256=P334_AUTH_EXEC_AUTH_KEY_IDENTITY["sha256"],
        )
    except (ValueError, p334_first_read_rc_acm_observer.AuthObserverError) as exc:
        raise EvidenceError("P3.34 logical resident observer proof differs") from exc


def p335_authenticated_attended_resident_observer_spec() -> dict[str, Any]:
    """Return the exact P3.35 three-session/reopen retained-listener contract."""
    value = p334_authenticated_logical_resident_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_attended_resident_listener_session_v1",
            "schema": p335_retained_listener_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P335_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": p335_retained_listener_runtime.DEVICE_BANNER.hex(),
            "protocol_contract": P335_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p335_retained_listener_runtime.DEFAULT_COMMANDS
            ],
            "proof_command_count": P335_AUTH_EXEC_COMMAND_COUNT,
            "max_commands": P335_AUTH_EXEC_MAX_COMMANDS,
            "auth_key": dict(P335_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "session_cap": P335_AUTH_EXEC_SESSION_CAP,
            "reconnect_cap": P335_AUTH_EXEC_RECONNECT_CAP,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
            "physical_reopen_count": 1,
            "per_boot_identity_required": True,
            "listener_wait_after_proof": True,
            "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
            "resident_lease_duration_sec": 3_600,
            "resident_lease_action_cap": 16,
            "action_retry": False,
        }
    )
    for key in (
        "first_console_return_checkpoint_only",
        "first_console_return_detail_prefix",
        "first_console_return_detail_sentinel",
        "first_read_attribution_requires_stage0_without_stage1",
    ):
        value.pop(key, None)
    return value


def validate_p335_attended_resident_proof(value: Any) -> dict[str, Any]:
    try:
        return p335_retained_listener_acm_observer.validate_proof_value(
            value,
            expected_auth_key_sha256=P335_AUTH_EXEC_AUTH_KEY_IDENTITY["sha256"],
        )
    except (ValueError, p335_retained_listener_acm_observer.AuthObserverError) as exc:
        raise EvidenceError("P3.35 attended resident observer proof differs") from exc


def p336_authenticated_long_idle_observer_spec() -> dict[str, Any]:
    """Return the P3.36 initial-resident plus later-resync observer contract."""
    value = p335_authenticated_attended_resident_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_long_idle_resident_session_v1",
            "schema": p336_long_idle_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P336_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": p336_long_idle_runtime.DEVICE_BANNER.hex(),
            "protocol_contract": P336_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p336_long_idle_runtime.DEFAULT_COMMANDS
            ],
            "auth_key": dict(P336_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "resident_lease_schema": p336_stock_adapter.LEASE_SCHEMA,
            "initial_session_count": p336_stock_adapter.INITIAL_SESSION_COUNT,
            "initial_reconnect_count": p336_stock_adapter.INITIAL_RECONNECT_COUNT,
            "resident_sessions": p336_stock_adapter.INITIAL_SESSION_COUNT,
            "resident_reconnects": p336_stock_adapter.INITIAL_RECONNECT_COUNT,
            "later_action_open_before_resync": True,
            "long_idle_host_resync": True,
            "later_action_max_preamble_pairs": p336_long_idle_acm_observer.MAX_PREAMBLE_PAIRS,
            "later_action_max_resync_bytes": p336_long_idle_acm_observer.MAX_RESYNC_BYTES,
            "action_retry": False,
        }
    )
    return value


def validate_p336_long_idle_proof(value: Any) -> dict[str, Any]:
    """Validate the strict three-session P336 initial proof projection."""
    if not isinstance(value, dict):
        raise EvidenceError("P3.36 long-idle proof is not an object")
    expected_keys = {
        "schema", "contract_id", "target", "run_id_hex", "session_cap",
        "reconnect_cap", "session_count", "successful_sessions",
        "reconnect_count", "physical_reopen_count", "fixed_command_count",
        "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof", "diagnostic_order_proof",
        "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
        "same_boot_id", "descriptor_reopened", "retained_listener_proof",
        "partial_raw_retention", "caller_selected_command", "interactive_pty",
        "arbitrary_file_transfer", "persistent_state", "listener_replays_commands",
        "fixed_commands", "sessions",
    }
    if set(value) != expected_keys:
        raise EvidenceError("P3.36 long-idle proof key set differs")
    if (
        value["schema"] != p336_long_idle_acm_observer.SCHEMA
        or value["contract_id"] != P336_AUTH_EXEC_OBSERVER_CONTRACT_ID
        or value["target"] != p336_long_idle_runtime.TARGET
        or value["run_id_hex"] != P336_AUTH_EXEC_RUN_ID_HEX
        or value["session_cap"] != P336_AUTH_EXEC_SESSION_CAP
        or value["reconnect_cap"] != P336_AUTH_EXEC_RECONNECT_CAP
        or value["session_count"] != P336_AUTH_EXEC_SESSION_CAP
        or value["successful_sessions"] != P336_AUTH_EXEC_SESSION_CAP
        or value["reconnect_count"] != P336_AUTH_EXEC_RECONNECT_CAP
        or value["physical_reopen_count"] != p336_long_idle_acm_observer.PHYSICAL_REOPEN_COUNT
        or value["fixed_command_count"] != P336_AUTH_EXEC_COMMAND_COUNT
        or any(
            value[key] is not True
            for key in (
                "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "diagnostic_order_proof",
                "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
                "same_boot_id", "descriptor_reopened", "retained_listener_proof",
                "partial_raw_retention",
            )
        )
        or any(
            value[key] is not False
            for key in (
                "caller_selected_command", "interactive_pty",
                "arbitrary_file_transfer", "persistent_state",
                "listener_replays_commands",
            )
        )
        or not isinstance(value["fixed_commands"], list)
        or len(value["fixed_commands"]) != P336_AUTH_EXEC_COMMAND_COUNT
        or any(
            item != {
                "size": len(command),
                "sha256": hashlib.sha256(command).hexdigest(),
            }
            for item, command in zip(
                value["fixed_commands"], p336_long_idle_runtime.DEFAULT_COMMANDS
            )
        )
    ):
        raise EvidenceError("P3.36 long-idle proof identity differs")
    sessions = value["sessions"]
    if not isinstance(sessions, list) or len(sessions) != P336_AUTH_EXEC_SESSION_CAP:
        raise EvidenceError("P3.36 long-idle proof sessions differ")
    nonces: set[str] = set()
    boots: set[str] = set()
    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            raise EvidenceError("P3.36 long-idle proof session is malformed")
        if (
            session.get("session_index") != index
            or session.get("physical_reopen_index") != (0 if index < 2 else 1)
            or set(session) != {
                "session_index", "physical_reopen_index", "challenge_nonce_sha256",
                "boot_id_sha256", "auth_key_sha256", "commands", "tx", "raw_tx",
                "rx", "raw_rx", "diagnostics", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "interactive_pty_proof",
                "caller_selected_command",
            }
        ):
            raise EvidenceError("P3.36 long-idle proof session binding differs")
        for key in ("challenge_nonce_sha256", "boot_id_sha256", "auth_key_sha256"):
            digest = session[key]
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None or digest == "0" * 64:
                raise EvidenceError("P3.36 long-idle proof digest differs")
        if session["challenge_nonce_sha256"] in nonces:
            raise EvidenceError("P3.36 long-idle nonce repeated")
        nonces.add(session["challenge_nonce_sha256"])
        boots.add(session["boot_id_sha256"])
        if (
            session["pid1_authenticated_framed_exec_proof"] is not True
            or session["busybox_ash_command_proof"] is not True
            or session["interactive_pty_proof"] is not False
            or session["caller_selected_command"] is not False
            or not isinstance(session["commands"], list)
            or len(session["commands"]) != P336_AUTH_EXEC_COMMAND_COUNT
        ):
            raise EvidenceError("P3.36 long-idle proof command binding differs")
        for rendered, command, sequence in zip(
            session["commands"], p336_long_idle_runtime.DEFAULT_COMMANDS, (3, 4, 5)
        ):
            if (
                not isinstance(rendered, dict)
                or rendered.get("sequence") != sequence
                or rendered.get("command_sha256") != hashlib.sha256(command).hexdigest()
            ):
                raise EvidenceError("P3.36 long-idle proof command differs")
    if len(boots) != 1:
        raise EvidenceError("P3.36 long-idle boot identity differs")
    return value


def p337_authenticated_open_read_diagnostic_observer_spec() -> dict[str, Any]:
    """Return the P3.37 initial-resident plus later-resync observer contract."""
    value = p335_authenticated_attended_resident_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_open_read_diagnostic_resident_session_v1",
            "schema": p337_open_read_diag_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P337_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": p337_open_read_diag_runtime.DEVICE_BANNER.hex(),
            "protocol_contract": P337_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p337_open_read_diag_runtime.DEFAULT_COMMANDS
            ],
            "auth_key": dict(P337_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "resident_lease_schema": p337_stock_adapter.LEASE_SCHEMA,
            "initial_session_count": p337_stock_adapter.INITIAL_SESSION_COUNT,
            "initial_reconnect_count": p337_stock_adapter.INITIAL_RECONNECT_COUNT,
            "resident_sessions": p337_stock_adapter.INITIAL_SESSION_COUNT,
            "resident_reconnects": p337_stock_adapter.INITIAL_RECONNECT_COUNT,
            "later_action_open_before_resync": True,
            "long_idle_host_resync": True,
            "later_action_max_preamble_pairs": p337_open_read_diag_acm_observer.MAX_PREAMBLE_PAIRS,
            "later_action_max_resync_bytes": p337_open_read_diag_acm_observer.MAX_RESYNC_BYTES,
            "action_retry": False,
        }
    )
    return value



def validate_p337_open_read_diagnostic_proof(value: Any) -> dict[str, Any]:
    """Validate the strict three-session P337 initial proof projection."""
    if not isinstance(value, dict):
        raise EvidenceError("P3.37 open-read diagnostic proof is not an object")
    expected_keys = {
        "schema", "contract_id", "target", "run_id_hex", "session_cap",
        "reconnect_cap", "session_count", "successful_sessions",
        "reconnect_count", "physical_reopen_count", "fixed_command_count",
        "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof", "diagnostic_order_proof",
        "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
        "same_boot_id", "descriptor_reopened", "retained_listener_proof",
        "partial_raw_retention", "caller_selected_command", "interactive_pty",
        "arbitrary_file_transfer", "persistent_state", "listener_replays_commands",
        "fixed_commands", "sessions",
    }
    if set(value) != expected_keys:
        raise EvidenceError("P3.37 open-read diagnostic proof key set differs")
    if (
        value["schema"] != p337_open_read_diag_acm_observer.SCHEMA
        or value["contract_id"] != P337_AUTH_EXEC_OBSERVER_CONTRACT_ID
        or value["target"] != p337_open_read_diag_runtime.TARGET
        or value["run_id_hex"] != P337_AUTH_EXEC_RUN_ID_HEX
        or value["session_cap"] != P337_AUTH_EXEC_SESSION_CAP
        or value["reconnect_cap"] != P337_AUTH_EXEC_RECONNECT_CAP
        or value["session_count"] != P337_AUTH_EXEC_SESSION_CAP
        or value["successful_sessions"] != P337_AUTH_EXEC_SESSION_CAP
        or value["reconnect_count"] != P337_AUTH_EXEC_RECONNECT_CAP
        or value["physical_reopen_count"] != p337_open_read_diag_acm_observer.PHYSICAL_REOPEN_COUNT
        or value["fixed_command_count"] != P337_AUTH_EXEC_COMMAND_COUNT
        or any(
            value[key] is not True
            for key in (
                "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "diagnostic_order_proof",
                "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
                "same_boot_id", "descriptor_reopened", "retained_listener_proof",
                "partial_raw_retention",
            )
        )
        or any(
            value[key] is not False
            for key in (
                "caller_selected_command", "interactive_pty",
                "arbitrary_file_transfer", "persistent_state",
                "listener_replays_commands",
            )
        )
        or not isinstance(value["fixed_commands"], list)
        or len(value["fixed_commands"]) != P337_AUTH_EXEC_COMMAND_COUNT
        or any(
            item != {
                "size": len(command),
                "sha256": hashlib.sha256(command).hexdigest(),
            }
            for item, command in zip(
                value["fixed_commands"], p337_open_read_diag_runtime.DEFAULT_COMMANDS
            )
        )
    ):
        raise EvidenceError("P3.37 open-read diagnostic proof identity differs")
    sessions = value["sessions"]
    if not isinstance(sessions, list) or len(sessions) != P337_AUTH_EXEC_SESSION_CAP:
        raise EvidenceError("P3.37 open-read diagnostic proof sessions differ")
    nonces: set[str] = set()
    boots: set[str] = set()
    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            raise EvidenceError("P3.37 open-read diagnostic proof session is malformed")
        if (
            session.get("session_index") != index
            or session.get("physical_reopen_index") != (0 if index < 2 else 1)
            or set(session) != {
                "session_index", "physical_reopen_index", "challenge_nonce_sha256",
                "boot_id_sha256", "auth_key_sha256", "commands", "tx", "raw_tx",
                "rx", "raw_rx", "diagnostics", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "interactive_pty_proof",
                "caller_selected_command",
            }
        ):
            raise EvidenceError("P3.37 open-read diagnostic proof session binding differs")
        for key in ("challenge_nonce_sha256", "boot_id_sha256", "auth_key_sha256"):
            digest = session[key]
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None or digest == "0" * 64:
                raise EvidenceError("P3.37 open-read diagnostic proof digest differs")
        if session["challenge_nonce_sha256"] in nonces:
            raise EvidenceError("P3.37 open-read diagnostic nonce repeated")
        nonces.add(session["challenge_nonce_sha256"])
        boots.add(session["boot_id_sha256"])
        if (
            session["pid1_authenticated_framed_exec_proof"] is not True
            or session["busybox_ash_command_proof"] is not True
            or session["interactive_pty_proof"] is not False
            or session["caller_selected_command"] is not False
            or not isinstance(session["commands"], list)
            or len(session["commands"]) != P337_AUTH_EXEC_COMMAND_COUNT
        ):
            raise EvidenceError("P3.37 open-read diagnostic proof command binding differs")
        for rendered, command, sequence in zip(
            session["commands"], p337_open_read_diag_runtime.DEFAULT_COMMANDS, (3, 4, 5)
        ):
            if (
                not isinstance(rendered, dict)
                or rendered.get("sequence") != sequence
                or rendered.get("command_sha256") != hashlib.sha256(command).hexdigest()
            ):
                raise EvidenceError("P3.37 open-read diagnostic proof command differs")
    if len(boots) != 1:
        raise EvidenceError("P3.37 open-read diagnostic boot identity differs")
    return value


def p338_authenticated_open_read_branch_observer_spec() -> dict[str, Any]:
    """Return the P3.38 resident observer contract with four-way OPEN branches."""
    value = p337_authenticated_open_read_diagnostic_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_open_read_branch_resident_session_v1",
            "schema": p338_open_read_branch_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P338_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": p338_open_read_branch_runtime.DEVICE_BANNER.hex(),
            "protocol_contract": P338_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p338_open_read_branch_runtime.DEFAULT_COMMANDS
            ],
            "auth_key": dict(P338_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "resident_lease_schema": p338_stock_adapter.LEASE_SCHEMA,
            "open_read_branch_ordinals": dict(P338_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
            "open_read_branch_count": P338_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
            "original_errno_returned_unchanged": True,
        }
    )
    return value


def validate_p338_open_read_branch_proof(value: Any) -> dict[str, Any]:
    """Validate P3.38 identity before projecting the inherited P337 grammar.

    The inherited validator intentionally knows only the P337 namespace.  It
    is therefore unsafe to rewrite a P338 proof into P337 labels first: a
    stale P337 proof could otherwise be accepted as a P338 proof.  Keep this
    exact, pre-projection gate deliberately parallel to the P337 validator and
    check every fixed command in every session before making the compatibility
    projection below.
    """
    if not isinstance(value, dict):
        raise EvidenceError("P3.38 open-read branch proof is not an object")
    expected_keys = {
        "schema", "contract_id", "target", "run_id_hex", "session_cap",
        "reconnect_cap", "session_count", "successful_sessions",
        "reconnect_count", "physical_reopen_count", "fixed_command_count",
        "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof", "diagnostic_order_proof",
        "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
        "same_boot_id", "descriptor_reopened", "retained_listener_proof",
        "partial_raw_retention", "caller_selected_command", "interactive_pty",
        "arbitrary_file_transfer", "persistent_state", "listener_replays_commands",
        "fixed_commands", "sessions",
    }
    if set(value) != expected_keys:
        raise EvidenceError("P3.38 open-read branch proof key set differs")
    expected_commands = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in p338_open_read_branch_runtime.DEFAULT_COMMANDS
    ]
    if (
        value["schema"] != p338_open_read_branch_acm_observer.SCHEMA
        or value["contract_id"] != P338_AUTH_EXEC_OBSERVER_CONTRACT_ID
        or value["target"] != p338_open_read_branch_runtime.TARGET
        or value["run_id_hex"] != P338_AUTH_EXEC_RUN_ID_HEX
        or value["session_cap"] != P338_AUTH_EXEC_SESSION_CAP
        or value["reconnect_cap"] != P338_AUTH_EXEC_RECONNECT_CAP
        or value["session_count"] != P338_AUTH_EXEC_SESSION_CAP
        or value["successful_sessions"] != P338_AUTH_EXEC_SESSION_CAP
        or value["reconnect_count"] != P338_AUTH_EXEC_RECONNECT_CAP
        or value["physical_reopen_count"]
        != p338_open_read_branch_acm_observer.PHYSICAL_REOPEN_COUNT
        or value["fixed_command_count"] != P338_AUTH_EXEC_COMMAND_COUNT
        or any(
            value[key] is not True
            for key in (
                "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "diagnostic_order_proof",
                "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
                "same_boot_id", "descriptor_reopened", "retained_listener_proof",
                "partial_raw_retention",
            )
        )
        or any(
            value[key] is not False
            for key in (
                "caller_selected_command", "interactive_pty",
                "arbitrary_file_transfer", "persistent_state",
                "listener_replays_commands",
            )
        )
        or value["fixed_commands"] != expected_commands
    ):
        raise EvidenceError("P3.38 open-read branch proof identity differs")
    sessions = value["sessions"]
    if not isinstance(sessions, list) or len(sessions) != P338_AUTH_EXEC_SESSION_CAP:
        raise EvidenceError("P3.38 open-read branch proof sessions differ")
    nonces: set[str] = set()
    boots: set[str] = set()
    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            raise EvidenceError("P3.38 open-read branch proof session is malformed")
        if (
            session.get("session_index") != index
            or session.get("physical_reopen_index") != (0 if index < 2 else 1)
            or set(session) != {
                "session_index", "physical_reopen_index", "challenge_nonce_sha256",
                "boot_id_sha256", "auth_key_sha256", "commands", "tx", "raw_tx",
                "rx", "raw_rx", "diagnostics", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "interactive_pty_proof",
                "caller_selected_command",
            }
        ):
            raise EvidenceError("P3.38 open-read branch proof session binding differs")
        for key in ("challenge_nonce_sha256", "boot_id_sha256", "auth_key_sha256"):
            digest = session[key]
            if (
                not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or digest == "0" * 64
            ):
                raise EvidenceError("P3.38 open-read branch proof digest differs")
        if session["challenge_nonce_sha256"] in nonces:
            raise EvidenceError("P3.38 open-read branch nonce repeated")
        nonces.add(session["challenge_nonce_sha256"])
        boots.add(session["boot_id_sha256"])
        commands = session["commands"]
        if (
            session["pid1_authenticated_framed_exec_proof"] is not True
            or session["busybox_ash_command_proof"] is not True
            or session["interactive_pty_proof"] is not False
            or session["caller_selected_command"] is not False
            or not isinstance(commands, list)
            or len(commands) != P338_AUTH_EXEC_COMMAND_COUNT
        ):
            raise EvidenceError("P3.38 open-read branch proof command binding differs")
        for rendered, command, sequence in zip(
            commands, p338_open_read_branch_runtime.DEFAULT_COMMANDS, (3, 4, 5)
        ):
            if (
                not isinstance(rendered, dict)
                or rendered.get("sequence") != sequence
                or rendered.get("command_sha256") != hashlib.sha256(command).hexdigest()
            ):
                raise EvidenceError("P3.38 open-read branch proof command differs")
    if len(boots) != 1:
        raise EvidenceError("P3.38 open-read branch boot identity differs")

    # Only now make the inherited compatibility projection.  The projection is
    # intentionally a deep copy and does not mutate or authorize P338 input.
    projected = copy.deepcopy(value)
    projected["schema"] = p337_open_read_diag_acm_observer.SCHEMA
    projected["contract_id"] = P337_AUTH_EXEC_OBSERVER_CONTRACT_ID
    projected["target"] = p337_open_read_diag_runtime.TARGET
    projected["run_id_hex"] = P337_AUTH_EXEC_RUN_ID_HEX
    projected["fixed_commands"] = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in p337_open_read_diag_runtime.DEFAULT_COMMANDS
    ]
    projected_sessions = projected["sessions"]
    for session in projected_sessions:
        for rendered, command in zip(
            session["commands"], p337_open_read_diag_runtime.DEFAULT_COMMANDS
        ):
            rendered["command_sha256"] = hashlib.sha256(command).hexdigest()
    try:
        validate_p337_open_read_diagnostic_proof(projected)
    except (EvidenceError, TypeError) as exc:
        raise EvidenceError("P3.38 open-read branch proof differs") from exc
    return value


def p339_authenticated_open_read_branch_observer_spec() -> dict[str, Any]:
    """Return the P3.39 resident observer contract with header capture."""
    value = p338_authenticated_open_read_branch_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_open_header_capture_resident_session_v1",
            "schema": p339_open_read_branch_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P339_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": p339_open_read_branch_runtime.DEVICE_BANNER.hex(),
            "protocol_contract": P339_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p339_open_read_branch_runtime.DEFAULT_COMMANDS
            ],
            "auth_key": dict(P339_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "resident_lease_schema": p339_stock_adapter.LEASE_SCHEMA,
            "open_read_branch_ordinals": dict(P339_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
            "open_read_branch_count": P339_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
            "open_header_word_stages": list(P339_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
            "open_header_size": P339_AUTH_EXEC_OPEN_HEADER_SIZE,
            "open_header_capture_best_effort": True,
            "original_errno_returned_unchanged": True,
        }
    )
    return value


def validate_p339_open_read_branch_proof(value: Any) -> dict[str, Any]:
    """Validate P3.39 identity before projecting the inherited P338 grammar.

    The inherited validator intentionally knows only the P338 namespace.  It
    is therefore unsafe to rewrite a P339 proof into P338 labels first: a
    stale P338 proof could otherwise be accepted as a P339 proof.  Keep this
    exact, pre-projection gate deliberately parallel to the P338 validator and
    check every fixed command in every session before making the compatibility
    projection below.
    """
    if not isinstance(value, dict):
        raise EvidenceError("P3.39 open-read branch proof is not an object")
    expected_keys = {
        "schema", "contract_id", "target", "run_id_hex", "session_cap",
        "reconnect_cap", "session_count", "successful_sessions",
        "reconnect_count", "physical_reopen_count", "fixed_command_count",
        "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof", "diagnostic_order_proof",
        "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
        "same_boot_id", "descriptor_reopened", "retained_listener_proof",
        "partial_raw_retention", "caller_selected_command", "interactive_pty",
        "arbitrary_file_transfer", "persistent_state", "listener_replays_commands",
        "fixed_commands", "sessions",
    }
    if set(value) != expected_keys:
        raise EvidenceError("P3.39 open-read branch proof key set differs")
    expected_commands = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in p339_open_read_branch_runtime.DEFAULT_COMMANDS
    ]
    if (
        value["schema"] != p339_open_read_branch_acm_observer.SCHEMA
        or value["contract_id"] != P339_AUTH_EXEC_OBSERVER_CONTRACT_ID
        or value["target"] != p339_open_read_branch_runtime.TARGET
        or value["run_id_hex"] != P339_AUTH_EXEC_RUN_ID_HEX
        or value["session_cap"] != P339_AUTH_EXEC_SESSION_CAP
        or value["reconnect_cap"] != P339_AUTH_EXEC_RECONNECT_CAP
        or value["session_count"] != P339_AUTH_EXEC_SESSION_CAP
        or value["successful_sessions"] != P339_AUTH_EXEC_SESSION_CAP
        or value["reconnect_count"] != P339_AUTH_EXEC_RECONNECT_CAP
        or value["physical_reopen_count"]
        != p339_open_read_branch_acm_observer.PHYSICAL_REOPEN_COUNT
        or value["fixed_command_count"] != P339_AUTH_EXEC_COMMAND_COUNT
        or any(
            value[key] is not True
            for key in (
                "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "diagnostic_order_proof",
                "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
                "same_boot_id", "descriptor_reopened", "retained_listener_proof",
                "partial_raw_retention",
            )
        )
        or any(
            value[key] is not False
            for key in (
                "caller_selected_command", "interactive_pty",
                "arbitrary_file_transfer", "persistent_state",
                "listener_replays_commands",
            )
        )
        or value["fixed_commands"] != expected_commands
    ):
        raise EvidenceError("P3.39 open-read branch proof identity differs")
    sessions = value["sessions"]
    if not isinstance(sessions, list) or len(sessions) != P339_AUTH_EXEC_SESSION_CAP:
        raise EvidenceError("P3.39 open-read branch proof sessions differ")
    nonces: set[str] = set()
    boots: set[str] = set()
    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            raise EvidenceError("P3.39 open-read branch proof session is malformed")
        if (
            session.get("session_index") != index
            or session.get("physical_reopen_index") != (0 if index < 2 else 1)
            or set(session) != {
                "session_index", "physical_reopen_index", "challenge_nonce_sha256",
                "boot_id_sha256", "auth_key_sha256", "commands", "tx", "raw_tx",
                "rx", "raw_rx", "diagnostics", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "interactive_pty_proof",
                "caller_selected_command",
            }
        ):
            raise EvidenceError("P3.39 open-read branch proof session binding differs")
        for key in ("challenge_nonce_sha256", "boot_id_sha256", "auth_key_sha256"):
            digest = session[key]
            if (
                not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or digest == "0" * 64
            ):
                raise EvidenceError("P3.39 open-read branch proof digest differs")
        if session["challenge_nonce_sha256"] in nonces:
            raise EvidenceError("P3.39 open-read branch nonce repeated")
        nonces.add(session["challenge_nonce_sha256"])
        boots.add(session["boot_id_sha256"])
        commands = session["commands"]
        if (
            session["pid1_authenticated_framed_exec_proof"] is not True
            or session["busybox_ash_command_proof"] is not True
            or session["interactive_pty_proof"] is not False
            or session["caller_selected_command"] is not False
            or not isinstance(commands, list)
            or len(commands) != P339_AUTH_EXEC_COMMAND_COUNT
        ):
            raise EvidenceError("P3.39 open-read branch proof command binding differs")
        for rendered, command, sequence in zip(
            commands, p339_open_read_branch_runtime.DEFAULT_COMMANDS, (3, 4, 5)
        ):
            if (
                not isinstance(rendered, dict)
                or rendered.get("sequence") != sequence
                or rendered.get("command_sha256") != hashlib.sha256(command).hexdigest()
            ):
                raise EvidenceError("P3.39 open-read branch proof command differs")
    if len(boots) != 1:
        raise EvidenceError("P3.39 open-read branch boot identity differs")

    # Only now make the inherited compatibility projection.  The projection is
    # intentionally a deep copy and does not mutate or authorize P339 input.
    projected = copy.deepcopy(value)
    projected["schema"] = p338_open_read_branch_acm_observer.SCHEMA
    projected["contract_id"] = P338_AUTH_EXEC_OBSERVER_CONTRACT_ID
    projected["target"] = p338_open_read_branch_runtime.TARGET
    projected["run_id_hex"] = P338_AUTH_EXEC_RUN_ID_HEX
    projected["fixed_commands"] = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in p338_open_read_branch_runtime.DEFAULT_COMMANDS
    ]
    projected_sessions = projected["sessions"]
    for session in projected_sessions:
        for rendered, command in zip(
            session["commands"], p338_open_read_branch_runtime.DEFAULT_COMMANDS
        ):
            rendered["command_sha256"] = hashlib.sha256(command).hexdigest()
    try:
        validate_p338_open_read_branch_proof(projected)
    except (EvidenceError, TypeError) as exc:
        raise EvidenceError("P3.39 open-read branch proof differs") from exc
    return value


def p340_authenticated_open_read_branch_observer_spec() -> dict[str, Any]:
    """Return the P3.40 resident observer contract with suffix capture."""
    value = p339_authenticated_open_read_branch_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_open_header_capture_resident_session_v1",
            "schema": p340_open_read_branch_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P340_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": p340_open_read_branch_runtime.DEVICE_BANNER.hex(),
            "protocol_contract": P340_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p340_open_read_branch_runtime.DEFAULT_COMMANDS
            ],
            "auth_key": dict(P340_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "resident_lease_schema": p340_stock_adapter.LEASE_SCHEMA,
            "open_read_branch_ordinals": dict(
                P340_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS
            ),
            "open_read_branch_count": P340_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
            "open_header_word_stages": list(P340_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
            "open_header_size": P340_AUTH_EXEC_OPEN_HEADER_SIZE,
            "open_header_capture_best_effort": True,
            "original_errno_returned_unchanged": True,
            "initial_failure_suffix_capture": True,
            "maximum_failure_suffix_bytes": 96,
        }
    )
    return value


def validate_p340_open_read_branch_proof(value: Any) -> dict[str, Any]:
    """Validate P3.40 proof identity before the inherited P339 projection.

    P340 has a new run, observer and command namespace even though its framed
    session grammar is unchanged.  All fresh fields are checked before a
    private P339 compatibility projection is constructed; stale P339 proof
    bytes therefore cannot be relabelled as P340 evidence.
    """
    if not isinstance(value, dict):
        raise EvidenceError("P3.40 open-read branch proof is not an object")
    expected_keys = {
        "schema", "contract_id", "target", "run_id_hex", "session_cap",
        "reconnect_cap", "session_count", "successful_sessions",
        "reconnect_count", "physical_reopen_count", "fixed_command_count",
        "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof", "diagnostic_order_proof",
        "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
        "same_boot_id", "descriptor_reopened", "retained_listener_proof",
        "partial_raw_retention", "caller_selected_command", "interactive_pty",
        "arbitrary_file_transfer", "persistent_state", "listener_replays_commands",
        "fixed_commands", "sessions",
    }
    if set(value) != expected_keys:
        raise EvidenceError("P3.40 open-read branch proof key set differs")
    expected_commands = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in p340_open_read_branch_runtime.DEFAULT_COMMANDS
    ]
    if (
        value["schema"] != p340_open_read_branch_acm_observer.SCHEMA
        or value["contract_id"] != P340_AUTH_EXEC_OBSERVER_CONTRACT_ID
        or value["target"] != p340_open_read_branch_runtime.TARGET
        or value["run_id_hex"] != P340_AUTH_EXEC_RUN_ID_HEX
        or value["session_cap"] != P340_AUTH_EXEC_SESSION_CAP
        or value["reconnect_cap"] != P340_AUTH_EXEC_RECONNECT_CAP
        or value["session_count"] != P340_AUTH_EXEC_SESSION_CAP
        or value["successful_sessions"] != P340_AUTH_EXEC_SESSION_CAP
        or value["reconnect_count"] != P340_AUTH_EXEC_RECONNECT_CAP
        or value["physical_reopen_count"]
        != p340_open_read_branch_acm_observer.PHYSICAL_REOPEN_COUNT
        or value["fixed_command_count"] != P340_AUTH_EXEC_COMMAND_COUNT
        or any(
            value[key] is not True
            for key in (
                "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "diagnostic_order_proof",
                "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
                "same_boot_id", "descriptor_reopened", "retained_listener_proof",
                "partial_raw_retention",
            )
        )
        or any(
            value[key] is not False
            for key in (
                "caller_selected_command", "interactive_pty",
                "arbitrary_file_transfer", "persistent_state",
                "listener_replays_commands",
            )
        )
        or value["fixed_commands"] != expected_commands
    ):
        raise EvidenceError("P3.40 open-read branch proof identity differs")
    sessions = value["sessions"]
    if not isinstance(sessions, list) or len(sessions) != P340_AUTH_EXEC_SESSION_CAP:
        raise EvidenceError("P3.40 open-read branch proof sessions differ")
    nonces: set[str] = set()
    boots: set[str] = set()
    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            raise EvidenceError("P3.40 open-read branch proof session is malformed")
        if (
            session.get("session_index") != index
            or session.get("physical_reopen_index") != (0 if index < 2 else 1)
            or set(session) != {
                "session_index", "physical_reopen_index", "challenge_nonce_sha256",
                "boot_id_sha256", "auth_key_sha256", "commands", "tx", "raw_tx",
                "rx", "raw_rx", "diagnostics", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "interactive_pty_proof",
                "caller_selected_command",
            }
        ):
            raise EvidenceError("P3.40 open-read branch proof session binding differs")
        for key in ("challenge_nonce_sha256", "boot_id_sha256", "auth_key_sha256"):
            digest = session[key]
            if (
                not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                or digest == "0" * 64
            ):
                raise EvidenceError("P3.40 open-read branch proof digest differs")
        if session["challenge_nonce_sha256"] in nonces:
            raise EvidenceError("P3.40 open-read branch nonce repeated")
        nonces.add(session["challenge_nonce_sha256"])
        boots.add(session["boot_id_sha256"])
        commands = session["commands"]
        if (
            session["pid1_authenticated_framed_exec_proof"] is not True
            or session["busybox_ash_command_proof"] is not True
            or session["interactive_pty_proof"] is not False
            or session["caller_selected_command"] is not False
            or not isinstance(commands, list)
            or len(commands) != P340_AUTH_EXEC_COMMAND_COUNT
        ):
            raise EvidenceError("P3.40 open-read branch proof command binding differs")
        for rendered, command, sequence in zip(
            commands, p340_open_read_branch_runtime.DEFAULT_COMMANDS, (3, 4, 5)
        ):
            if (
                not isinstance(rendered, dict)
                or rendered.get("sequence") != sequence
                or rendered.get("command_sha256")
                != hashlib.sha256(command).hexdigest()
            ):
                raise EvidenceError("P3.40 open-read branch proof command differs")
    if len(boots) != 1:
        raise EvidenceError("P3.40 open-read branch boot identity differs")

    projected = copy.deepcopy(value)
    projected["schema"] = p339_open_read_branch_acm_observer.SCHEMA
    projected["contract_id"] = P339_AUTH_EXEC_OBSERVER_CONTRACT_ID
    projected["target"] = p339_open_read_branch_runtime.TARGET
    projected["run_id_hex"] = P339_AUTH_EXEC_RUN_ID_HEX
    projected["fixed_commands"] = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in p339_open_read_branch_runtime.DEFAULT_COMMANDS
    ]
    for session in projected["sessions"]:
        for rendered, command in zip(
            session["commands"], p339_open_read_branch_runtime.DEFAULT_COMMANDS
        ):
            rendered["command_sha256"] = hashlib.sha256(command).hexdigest()
    try:
        validate_p339_open_read_branch_proof(projected)
    except (EvidenceError, TypeError) as exc:
        raise EvidenceError("P3.40 open-read branch proof differs") from exc
    return value


def p341_authenticated_open_read_branch_observer_spec() -> dict[str, Any]:
    """Return the P3.41 host-first-OPEN observer contract."""
    value = p340_authenticated_open_read_branch_observer_spec()
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_host_first_open_resident_session_v1",
            "schema": p341_open_read_branch_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P341_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": p341_open_read_branch_runtime.DEVICE_BANNER.hex(),
            "protocol_contract": P341_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p341_open_read_branch_runtime.DEFAULT_COMMANDS
            ],
            "auth_key": dict(P341_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "resident_lease_schema": p341_stock_adapter.LEASE_SCHEMA,
            "open_read_branch_ordinals": dict(
                P341_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS
            ),
            "open_read_branch_count": P341_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
            "open_header_word_stages": list(P341_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
            "open_header_size": P341_AUTH_EXEC_OPEN_HEADER_SIZE,
            "open_header_capture_best_effort": True,
            "host_first_open": True,
            "banner_after_open": True,
            "no_unsolicited_preamble": True,
            "original_errno_returned_unchanged": True,
            "initial_failure_suffix_capture": True,
            "maximum_failure_suffix_bytes": 96,
        }
    )
    return value


def validate_p341_open_read_branch_proof(value: Any) -> dict[str, Any]:
    """Validate P3.41 proof identity before private P3.40 compatibility."""
    if not isinstance(value, dict):
        raise EvidenceError("P3.41 open-read branch proof is not an object")
    # Host-first proof retains the exact bounded P340 receipt shape.  Require
    # the fresh observer/run/commands first, then validate all session fields
    # using an isolated P340 compatibility projection.
    expected_commands = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in p341_open_read_branch_runtime.DEFAULT_COMMANDS
    ]
    if (
        value.get("schema") != p341_open_read_branch_acm_observer.SCHEMA
        or value.get("contract_id") != P341_AUTH_EXEC_OBSERVER_CONTRACT_ID
        or value.get("target") != p341_open_read_branch_runtime.TARGET
        or value.get("run_id_hex") != P341_AUTH_EXEC_RUN_ID_HEX
        or value.get("fixed_commands") != expected_commands
    ):
        raise EvidenceError("P3.41 open-read branch proof identity differs")
    # The fresh observer may expose these as explicit proof flags; if present,
    # they are fixed booleans and never widen the wire protocol.
    for key in ("host_first_open", "banner_after_open", "no_unsolicited_preamble"):
        if key in value and value[key] is not True:
            raise EvidenceError("P3.41 host-first proof flag differs")
    projected = copy.deepcopy(value)
    projected["schema"] = p340_open_read_branch_acm_observer.SCHEMA
    projected["contract_id"] = P340_AUTH_EXEC_OBSERVER_CONTRACT_ID
    projected["target"] = p340_open_read_branch_runtime.TARGET
    projected["run_id_hex"] = P340_AUTH_EXEC_RUN_ID_HEX
    projected["fixed_commands"] = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in p340_open_read_branch_runtime.DEFAULT_COMMANDS
    ]
    for session in projected.get("sessions", []):
        for rendered, command in zip(
            session.get("commands", []), p340_open_read_branch_runtime.DEFAULT_COMMANDS
        ):
            rendered["command_sha256"] = hashlib.sha256(command).hexdigest()
    # Extra host-first metadata is proof-local and not accepted by the older
    # strict compatibility validator.
    for key in ("host_first_open", "banner_after_open", "no_unsolicited_preamble"):
        projected.pop(key, None)
    try:
        validate_p340_open_read_branch_proof(projected)
    except (EvidenceError, TypeError) as exc:
        raise EvidenceError("P3.41 open-read branch proof differs") from exc
    return value


def p342_authenticated_open_read_branch_observer_spec() -> dict[str, Any]:
    """Return the distinct P3.42 four-session idle/reuse observer contract.

    P342 keeps the P341 host-first OPEN wire ordering but has its own schema,
    run marker, command identities, and four-session proof.  The timing
    receipt is deliberately a proof-local requirement; it is not a lease or
    a source of device authority.
    """
    value = copy.deepcopy(p341_authenticated_open_read_branch_observer_spec())
    value.update(
        {
            "kind": "exact_cdc_acm_authenticated_idle_reuse_resident_session_v1",
            "schema": p342_open_read_branch_acm_observer.SCHEMA,
            "usb_serial": "S22E3" + P342_AUTH_EXEC_RUN_ID_HEX,
            "banner_hex": p342_open_read_branch_runtime.DEVICE_BANNER.hex(),
            "protocol_contract": P342_AUTH_EXEC_OBSERVER_CONTRACT_ID,
            "commands": [
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                }
                for command in p342_open_read_branch_runtime.DEFAULT_COMMANDS
            ],
            "auth_key": dict(P342_AUTH_EXEC_AUTH_KEY_IDENTITY),
            "open_read_branch_ordinals": dict(
                P342_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS
            ),
            "open_read_branch_count": P342_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
            "open_header_word_stages": list(P342_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
            "open_header_size": P342_AUTH_EXEC_OPEN_HEADER_SIZE,
            "open_header_capture_best_effort": True,
            "host_first_open": True,
            "banner_after_open": True,
            "no_unsolicited_preamble": True,
            "original_errno_returned_unchanged": True,
            "initial_failure_suffix_capture": True,
            "maximum_failure_suffix_bytes": 96,
            "same_fd_session_count": P342_SAME_FD_SESSION_COUNT,
            "total_session_count": P342_TOTAL_SESSION_COUNT,
            "total_command_count": P342_TOTAL_COMMAND_COUNT,
            "physical_reopen_count": p342_open_read_branch_acm_observer.PHYSICAL_REOPEN_COUNT,
            "physical_reopen_indexes": list(P342_PHYSICAL_REOPEN_INDEXES),
            "session_cap": P342_AUTH_EXEC_SESSION_CAP,
            "reconnect_cap": P342_AUTH_EXEC_RECONNECT_CAP,
            "idle_reuse": {
                "phase": P342_IDLE_REUSE_PHASE,
                "before_session_index": P342_IDLE_REUSE_BEFORE_SESSION_INDEX,
                "requested_seconds": P342_IDLE_REUSE_REQUESTED_SECONDS,
                "elapsed_seconds_min": P342_IDLE_REUSE_MIN_ELAPSED_SECONDS,
                "elapsed_seconds_max": P342_IDLE_REUSE_MAX_ELAPSED_SECONDS,
                "same_descriptor": True,
                "completed": True,
                "received_bytes": 0,
            },
            "later_action_lease_active": False,
        }
    )
    # These are compatibility receipt fields required by the retained
    # session runner.  They do not activate the lease: the fresh adapter and
    # observer both carry ``later_action_lease_active=False``.
    value.update(
        {
            "resident_lease_schema": p342_stock_adapter.LEASE_SCHEMA,
            "resident_lease_duration_sec": p342_stock_adapter.LEASE_DURATION_SEC,
            "resident_lease_action_cap": p342_stock_adapter.LEASE_ACTION_CAP,
        }
    )
    return value


def _p342_digest(value: Any, label: str) -> None:
    if (
        type(value) is not str
        or re.fullmatch(r"[0-9a-f]{64}", value) is None
        or value == "0" * 64
    ):
        raise EvidenceError(f"P3.42 {label} digest differs")


def _validate_p342_idle_reuse_receipt(value: Any) -> dict[str, Any]:
    expected_keys = {
        "phase",
        "before_session_index",
        "requested_seconds",
        "elapsed_seconds",
        "same_descriptor",
        "completed",
        "received_bytes",
    }
    if type(value) is not dict or set(value) != expected_keys:
        raise EvidenceError("P3.42 idle-reuse receipt shape differs")
    elapsed = value["elapsed_seconds"]
    if (
        value["phase"] != P342_IDLE_REUSE_PHASE
        or type(value["before_session_index"]) is not int
        or value["before_session_index"] != P342_IDLE_REUSE_BEFORE_SESSION_INDEX
        or type(value["requested_seconds"]) is not int
        or value["requested_seconds"] != P342_IDLE_REUSE_REQUESTED_SECONDS
        or value["same_descriptor"] is not True
        or value["completed"] is not True
        or type(value["received_bytes"]) is not int
        or value["received_bytes"] != 0
        or type(elapsed) not in (int, float)
        or P342_IDLE_REUSE_MIN_ELAPSED_SECONDS > elapsed
        or elapsed > P342_IDLE_REUSE_MAX_ELAPSED_SECONDS
    ):
        raise EvidenceError("P3.42 idle-reuse interval is not proved")
    return dict(value)


def validate_p342_open_read_branch_proof(value: Any) -> dict[str, Any]:
    """Validate P3.42's fresh four-session proof and exact idle receipt.

    This validator intentionally does not project into P341/P340.  A P341
    proof, overlay, or run marker is a consumed predecessor and cannot be
    relabelled as P342 evidence.
    """
    if not isinstance(value, dict):
        raise EvidenceError("P3.42 open-read branch proof is not an object")
    expected_keys = {
        "schema", "contract_id", "target", "run_id_hex", "session_cap",
        "reconnect_cap", "session_count", "successful_sessions",
        "reconnect_count", "physical_reopen_count", "fixed_command_count",
        "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
        "busybox_ash_command_proof", "diagnostic_order_proof",
        "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
        "same_boot_id", "descriptor_reopened", "retained_listener_proof",
        "partial_raw_retention", "caller_selected_command", "interactive_pty",
        "arbitrary_file_transfer", "persistent_state", "listener_replays_commands",
        "fixed_commands", "sessions", "idle_reuse",
    }
    if set(value) != expected_keys:
        raise EvidenceError("P3.42 open-read branch proof key set differs")
    expected_commands = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in p342_open_read_branch_runtime.DEFAULT_COMMANDS
    ]
    if (
        value["schema"] != p342_open_read_branch_acm_observer.SCHEMA
        or value["contract_id"] != P342_AUTH_EXEC_OBSERVER_CONTRACT_ID
        or value["target"] != p342_open_read_branch_runtime.TARGET
        or value["run_id_hex"] != P342_AUTH_EXEC_RUN_ID_HEX
        or value["session_cap"] != P342_AUTH_EXEC_SESSION_CAP
        or value["reconnect_cap"] != P342_AUTH_EXEC_RECONNECT_CAP
        or value["session_count"] != P342_TOTAL_SESSION_COUNT
        or value["successful_sessions"] != P342_TOTAL_SESSION_COUNT
        or value["reconnect_count"] != P342_AUTH_EXEC_RECONNECT_CAP
        or value["physical_reopen_count"]
        != p342_open_read_branch_acm_observer.PHYSICAL_REOPEN_COUNT
        or value["fixed_command_count"] != P342_AUTH_EXEC_COMMAND_COUNT
        or any(
            value[key] is not True
            for key in (
                "hmac_authenticated", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "diagnostic_order_proof",
                "per_boot_identity_proof", "same_initial_fd", "same_tty_fd",
                "same_boot_id", "descriptor_reopened", "retained_listener_proof",
                "partial_raw_retention",
            )
        )
        or any(
            value[key] is not False
            for key in (
                "caller_selected_command", "interactive_pty",
                "arbitrary_file_transfer", "persistent_state",
                "listener_replays_commands",
            )
        )
        or value["fixed_commands"] != expected_commands
    ):
        raise EvidenceError("P3.42 open-read branch proof identity differs")
    _validate_p342_idle_reuse_receipt(value["idle_reuse"])
    sessions = value["sessions"]
    if type(sessions) is not list or len(sessions) != P342_TOTAL_SESSION_COUNT:
        raise EvidenceError("P3.42 open-read branch proof sessions differ")
    nonces: set[str] = set()
    boots: set[str] = set()
    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            raise EvidenceError("P3.42 open-read branch proof session is malformed")
        if (
            session.get("session_index") != index
            or session.get("physical_reopen_index")
            != P342_PHYSICAL_REOPEN_INDEXES[index]
            or set(session)
            != {
                "session_index", "physical_reopen_index", "challenge_nonce_sha256",
                "boot_id_sha256", "auth_key_sha256", "commands", "tx", "raw_tx",
                "rx", "raw_rx", "diagnostics", "pid1_authenticated_framed_exec_proof",
                "busybox_ash_command_proof", "interactive_pty_proof",
                "caller_selected_command",
            }
        ):
            raise EvidenceError("P3.42 open-read branch proof session binding differs")
        for key in ("challenge_nonce_sha256", "boot_id_sha256", "auth_key_sha256"):
            _p342_digest(session[key], key)
        if session["challenge_nonce_sha256"] in nonces:
            raise EvidenceError("P3.42 open-read branch nonce repeated")
        nonces.add(session["challenge_nonce_sha256"])
        boots.add(session["boot_id_sha256"])
        commands = session["commands"]
        if (
            session["pid1_authenticated_framed_exec_proof"] is not True
            or session["busybox_ash_command_proof"] is not True
            or session["interactive_pty_proof"] is not False
            or session["caller_selected_command"] is not False
            or type(commands) is not list
            or len(commands) != P342_AUTH_EXEC_COMMAND_COUNT
        ):
            raise EvidenceError("P3.42 open-read branch proof command binding differs")
        for rendered, command, sequence in zip(
            commands, p342_open_read_branch_runtime.DEFAULT_COMMANDS, (3, 4, 5)
        ):
            if (
                not isinstance(rendered, dict)
                or rendered.get("sequence") != sequence
                or rendered.get("command_sha256")
                != hashlib.sha256(command).hexdigest()
            ):
                raise EvidenceError("P3.42 open-read branch proof command differs")
    if len(boots) != 1:
        raise EvidenceError("P3.42 open-read branch boot identity differs")

    # The observer module independently validates the four-session/reopen
    # geometry.  It uses command_size rather than the durable sequence field,
    # so supply a non-mutating serialization projection for that check.
    observer_value = copy.deepcopy(value)
    for session in observer_value["sessions"]:
        session["commands"] = [
            {
                "command_size": len(command),
                "command_sha256": hashlib.sha256(command).hexdigest(),
            }
            for command in p342_open_read_branch_runtime.DEFAULT_COMMANDS
        ]
    try:
        p342_open_read_branch_acm_observer.validate_four_session_proof(
            observer_value
        )
    except Exception as exc:
        raise EvidenceError("P3.42 four-session observer proof differs") from exc
    return value


def validate_candidate_arrival_proof_role(
    value: Any,
    candidate_observer: Any = None,
    *,
    expected_run_id: str | None = None,
) -> str | None:
    """Validate the narrow ACM-primary role without elevating Carrier.

    The role is intentionally a string rather than a second observer schema:
    the existing candidate-observer validator remains the authority for the
    USB binding and receipt grammar.  This helper only makes the opt-in
    versioned and requires the exact 49-byte ACM banner shape.
    """
    if value is None:
        return None
    if value == CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE:
        specs = {
            P342_AUTH_EXEC_RUN_ID_HEX: (
                "P3.42",
                p342_authenticated_open_read_branch_observer_spec(),
            ),
            P341_AUTH_EXEC_RUN_ID_HEX: (
                "P3.41",
                p341_authenticated_open_read_branch_observer_spec(),
            ),
            P340_AUTH_EXEC_RUN_ID_HEX: (
                "P3.40",
                p340_authenticated_open_read_branch_observer_spec(),
            ),
            P339_AUTH_EXEC_RUN_ID_HEX: (
                "P3.39",
                p339_authenticated_open_read_branch_observer_spec(),
            ),
            P338_AUTH_EXEC_RUN_ID_HEX: (
                "P3.38",
                p338_authenticated_open_read_branch_observer_spec(),
            ),
            P332_AUTH_EXEC_RUN_ID_HEX: (
                "P3.32",
                p332_authenticated_logical_resident_observer_spec(),
            ),
            P333_AUTH_EXEC_RUN_ID_HEX: (
                "P3.33",
                p333_authenticated_logical_resident_observer_spec(),
            ),
            P334_AUTH_EXEC_RUN_ID_HEX: (
                "P3.34",
                p334_authenticated_logical_resident_observer_spec(),
            ),
            P335_AUTH_EXEC_RUN_ID_HEX: (
                "P3.35",
                p335_authenticated_attended_resident_observer_spec(),
            ),
            P336_AUTH_EXEC_RUN_ID_HEX: (
                "P3.36",
                p336_authenticated_long_idle_observer_spec(),
            ),
            P337_AUTH_EXEC_RUN_ID_HEX: (
                "P3.37",
                p337_authenticated_open_read_diagnostic_observer_spec(),
            ),
        }
        selected = specs.get(expected_run_id)
        if selected is None or not isinstance(candidate_observer, dict):
            raise EvidenceError("logical resident authenticated identity differs")
        label, expected = selected
        if not _strict_equal(candidate_observer, expected):
            raise EvidenceError(f"{label} logical resident authenticated observer differs")
        return value
    if value == CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE:
        if (
            expected_run_id != P331_AUTH_EXEC_RUN_ID_HEX
            or not isinstance(candidate_observer, dict)
        ):
            raise EvidenceError("P3.31 resident authenticated identity differs")
        if not _strict_equal(
            candidate_observer,
            p331_authenticated_resident_framed_observer_spec(),
        ):
            raise EvidenceError("P3.31 resident authenticated observer differs")
        return value
    if value == CANDIDATE_AUTHENTICATED_DIAGNOSTIC_EXEC_ROLE:
        if (
            expected_run_id != P330_AUTH_EXEC_RUN_ID_HEX
            or not isinstance(candidate_observer, dict)
        ):
            raise EvidenceError("P3.30 diagnostic authenticated identity differs")
        if not _strict_equal(
            candidate_observer, p330_authenticated_framed_observer_spec()
        ):
            raise EvidenceError("P3.30 diagnostic authenticated observer differs")
        return value
    if value == CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE:
        if (
            expected_run_id != P329_AUTH_EXEC_RUN_ID_HEX
            or not isinstance(candidate_observer, dict)
        ):
            raise EvidenceError("P3.29 authenticated settle identity differs")
        if not _strict_equal(
            candidate_observer, p329_authenticated_framed_observer_spec()
        ):
            raise EvidenceError("P3.29 authenticated settle observer differs")
        return value
    if value == CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE:
        if (
            expected_run_id != P328_AUTH_EXEC_RUN_ID_HEX
            or not isinstance(candidate_observer, dict)
        ):
            raise EvidenceError("P3.28 authenticated exec identity differs")
        expected_observer = p328_authenticated_framed_observer_spec()
        if not _strict_equal(candidate_observer, expected_observer):
            raise EvidenceError("P3.28 authenticated observer identity differs")
        return value
    if value == CANDIDATE_FRAMED_FIXED_COMMAND_ROLE:
        if (
            expected_run_id != P327_FRAMED_EXEC_RUN_ID_HEX
            or not isinstance(candidate_observer, dict)
        ):
            raise EvidenceError("P3.27 framed command identity differs")
        expected_commands = tuple(
            (
                command,
                {
                    "size": len(command),
                    "sha256": hashlib.sha256(command).hexdigest(),
                },
            )
            for command in (
                b"/bin/busybox id",
                b"/bin/busybox uname -a",
                (
                    "/bin/busybox echo P327-NONCE "
                    + P327_FRAMED_EXEC_RUN_ID_HEX
                ).encode("ascii"),
            )
        )
        expected_observer = {
            "kind": "exact_cdc_acm_framed_fixed_commands_v1",
            "usb_vendor_id": "04e8",
            "usb_product_id": "6861",
            "usb_serial": "S22E3" + P327_FRAMED_EXEC_RUN_ID_HEX,
            "usb_driver": "cdc_acm",
            "usb_interface_number": "00",
            "banner_hex": (
                "S22PLUS-FYG8-E3:" + P327_FRAMED_EXEC_RUN_ID_HEX + "\n"
            ).encode("ascii").hex(),
            "protocol_contract": "s22plus-fyg8-p327-framed-acm-observer-v1",
            "wire_magic": "S327",
            "frame_header_size": 16,
            "max_frame_payload": P327_FRAMED_EXEC_MAX_FRAME_PAYLOAD,
            "max_commands": P327_FRAMED_EXEC_COMMAND_COUNT,
            "command_timeout_sec": P327_FRAMED_EXEC_COMMAND_TIMEOUT_SEC,
            "max_output_bytes": P327_FRAMED_EXEC_MAX_OUTPUT_BYTES,
            "commands": [entry for _command, entry in expected_commands],
            "caller_selected_command": False,
            "interactive_pty": False,
        }
        if not _strict_equal(candidate_observer, expected_observer):
            raise EvidenceError("P3.27 framed command observer identity differs")
        return value
    if value == CANDIDATE_BIDIRECTIONAL_CONSOLE_ROLE:
        if (
            expected_run_id != P326_CONSOLE_RUN_ID_HEX
            or not isinstance(candidate_observer, dict)
            or candidate_observer.get("kind") != "exact_cdc_acm_banner_v1"
            or candidate_observer.get("usb_serial")
            != "S22E3" + P326_CONSOLE_RUN_ID_HEX
        ):
            raise EvidenceError("P3.26 bidirectional console identity differs")
        expected_transcript = (
            "S22PLUS-FYG8-E3:" + P326_CONSOLE_RUN_ID_HEX + "\n"
            + "PONG " + P326_CONSOLE_RUN_ID_HEX + " pid=1\n"
            + "SHELL-OK " + P326_CONSOLE_RUN_ID_HEX + " busybox=1\n"
        ).encode("ascii")
        try:
            supplied_transcript = bytes.fromhex(
                candidate_observer.get("banner_hex", "")
            )
        except (TypeError, ValueError) as exc:
            raise EvidenceError("P3.26 bidirectional transcript differs") from exc
        if (
            len(expected_transcript) != P326_CONSOLE_TRANSCRIPT_SIZE
            or supplied_transcript != expected_transcript
        ):
            raise EvidenceError("P3.26 bidirectional transcript differs")
        return value
    if value != CANDIDATE_ARRIVAL_PROOF_ROLE:
        raise EvidenceError("candidate arrival proof role is not allowlisted")
    if not isinstance(candidate_observer, dict):
        raise EvidenceError(
            "candidate arrival proof role requires a candidate observer"
        )
    if candidate_observer.get("kind") != "exact_cdc_acm_banner_v1":
        raise EvidenceError(
            "candidate arrival proof role requires the exact CDC ACM observer"
        )
    banner_hex = candidate_observer.get("banner_hex")
    if (
        not isinstance(banner_hex, str)
        or not banner_hex
        or len(banner_hex) % 2
        or re.fullmatch(r"[0-9a-f]+", banner_hex) is None
    ):
        raise EvidenceError(
            "candidate arrival proof role requires an exact ACM banner"
        )
    try:
        banner_size = len(bytes.fromhex(banner_hex))
    except ValueError as exc:
        raise EvidenceError(
            "candidate arrival proof role requires an exact ACM banner"
        ) from exc
    expected = {
        run_id: (
            ("S22PLUS-FYG8-E3:" + run_id + "\n").encode("ascii"),
            "S22E3" + run_id,
        )
        for run_id in (
            P323_ACM_PRIMARY_RUN_ID_HEX,
            P324_ACM_PRIMARY_RUN_ID_HEX,
            P325_ACM_PRIMARY_RUN_ID_HEX,
        )
    }
    supplied = (
        bytes.fromhex(banner_hex),
        candidate_observer.get("usb_serial"),
    )
    if expected_run_id is not None and expected_run_id not in expected:
        raise EvidenceError(
            "candidate arrival proof role run identity is not allowlisted"
        )
    accepted_identities = (
        {expected[expected_run_id]}
        if expected_run_id is not None
        else set(expected.values())
    )
    if (
        banner_size != P323_ACM_PRIMARY_BANNER_SIZE
        or supplied not in accepted_identities
    ):
        label = (
            "P3.25"
            if expected_run_id == P325_ACM_PRIMARY_RUN_ID_HEX
            else "P3.24"
            if expected_run_id == P324_ACM_PRIMARY_RUN_ID_HEX
            else "P3.23"
            if expected_run_id == P323_ACM_PRIMARY_RUN_ID_HEX
            else "ACM-primary"
        )
        raise EvidenceError(
            f"candidate arrival proof role requires the exact {label} ACM identity"
        )
    return value


def validate_acceptance(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("acceptance must be an object")
    kind = value.get("kind")
    if kind == MARKER_KIND:
        item = _exact(
            value,
            {"kind", "source", "marker", "family", "exact_count"},
            "marker acceptance",
        )
        if item["source"] != CHECKPOINT_SOURCE or item["exact_count"] != 1:
            raise EvidenceError("marker acceptance source or count is invalid")
        _bounded_text(item["marker"], "acceptance.marker", 512)
        _bounded_text(item["family"], "acceptance.family", 128)
        return item
    if kind == SAME_RING_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "decoder",
                "contract_id",
                "records",
                "families",
                "accepted_identity",
                "exact_count",
                "contract",
            },
            "same-ring acceptance",
        )
        expected_records = {
            "entry_hex": same_ring.ENTRY_PROOF.hex(),
            "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
            "unsat_hex": same_ring.UNSAT_PROOF.hex(),
        }
        expected_families = {
            "long_hex": same_ring.ENTRY_FAMILY.hex(),
            "unsat_hex": same_ring.UNSAT_FAMILY.hex(),
        }
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != SAME_RING_DECODER
            or item["contract_id"] != SAME_RING_CONTRACT_ID
            or item["records"] != expected_records
            or item["families"] != expected_families
            or item["accepted_identity"] != "USERSPACE_CALLBACK_REACHED"
            or item["exact_count"] != 1
        ):
            raise EvidenceError("same-ring acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "same-ring contract",
        )
        _artifact(contract["run_manifest"], "same-ring contract run_manifest")
        _artifact(contract["static_check"], "same-ring contract static_check")
        return item
    if kind == SAME_RING_MULTIBOOT_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "decoder",
                "contract_id",
                "policy_id",
                "records",
                "families",
                "accepted_identity",
                "minimum_exact_count",
                "contract",
            },
            "same-ring multiboot acceptance",
        )
        expected_records = {
            "entry_hex": same_ring.ENTRY_PROOF.hex(),
            "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
            "unsat_hex": same_ring.UNSAT_PROOF.hex(),
        }
        expected_families = {
            "long_hex": same_ring.ENTRY_FAMILY.hex(),
            "unsat_hex": same_ring.UNSAT_FAMILY.hex(),
        }
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != SAME_RING_MULTIBOOT_DECODER
            or item["contract_id"] != SAME_RING_CONTRACT_ID
            or item["policy_id"] != SAME_RING_MULTIBOOT_POLICY_ID
            or item["records"] != expected_records
            or item["families"] != expected_families
            or item["accepted_identity"]
            != "USERSPACE_CALLBACK_REACHED_ONE_OR_MORE_BOOTS"
            or item["minimum_exact_count"] != 1
        ):
            raise EvidenceError("same-ring multiboot acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "same-ring multiboot contract",
        )
        _artifact(
            contract["run_manifest"],
            "same-ring multiboot contract run_manifest",
        )
        _artifact(
            contract["static_check"],
            "same-ring multiboot contract static_check",
        )
        return item
    if kind == E1_LATEST_STAGE_KIND:
        source_contract_id = value.get("source_contract_id")
        userspace_overlay_contract_id = value.get(
            "userspace_overlay_contract_id"
        )
        if userspace_overlay_contract_id == P342_STOCK_OVERLAY_CONTRACT_ID:
            template = p342_stock_adapter.acceptance_fixture()
            expected_keys = set(template) | {"auth_key"}
            item = _exact(value, expected_keys, "P3.42 E1 latest-stage acceptance")
            for key, expected in template.items():
                if key == "contract":
                    continue
                if not _strict_equal(item.get(key), expected):
                    raise EvidenceError(f"P3.42 acceptance field differs: {key}")
            if item["auth_key"] != P342_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise EvidenceError("P3.42 acceptance auth-key identity differs")
            contract = _exact(
                item["contract"],
                {"candidate_static", "run_manifest", "static_check"},
                "P3.42 E1 latest-stage contract",
            )
            for name in ("candidate_static", "run_manifest", "static_check"):
                _artifact(
                    contract[name],
                    f"P3.42 E1 latest-stage {name}",
                    maximum=(
                        P342_CANDIDATE_STATIC_MAX_BYTES
                        if name == "candidate_static"
                        else DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES
                    ),
                )
            return item
        if userspace_overlay_contract_id == P341_STOCK_OVERLAY_CONTRACT_ID:
            template = p341_stock_adapter.acceptance_fixture()
            expected_keys = set(template) | {"auth_key"}
            item = _exact(value, expected_keys, "P3.41 E1 latest-stage acceptance")
            for key, expected in template.items():
                if key == "contract":
                    continue
                if not _strict_equal(item.get(key), expected):
                    raise EvidenceError(f"P3.41 acceptance field differs: {key}")
            if item["auth_key"] != P341_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise EvidenceError("P3.41 acceptance auth-key identity differs")
            contract = _exact(
                item["contract"],
                {"candidate_static", "run_manifest", "static_check"},
                "P3.41 E1 latest-stage contract",
            )
            for name in ("candidate_static", "run_manifest", "static_check"):
                _artifact(
                    contract[name],
                    f"P3.41 E1 latest-stage {name}",
                    maximum=(
                        P341_CANDIDATE_STATIC_MAX_BYTES
                        if name == "candidate_static"
                        else DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES
                    ),
                )
            return item
        if userspace_overlay_contract_id == P340_STOCK_OVERLAY_CONTRACT_ID:
            template = p340_stock_adapter.acceptance_fixture()
            expected_keys = set(template) | {"auth_key"}
            item = _exact(value, expected_keys, "P3.40 E1 latest-stage acceptance")
            for key, expected in template.items():
                if key == "contract":
                    continue
                if not _strict_equal(item.get(key), expected):
                    raise EvidenceError(f"P3.40 acceptance field differs: {key}")
            if item["auth_key"] != P340_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise EvidenceError("P3.40 acceptance auth-key identity differs")
            contract = _exact(
                item["contract"],
                {"candidate_static", "run_manifest", "static_check"},
                "P3.40 E1 latest-stage contract",
            )
            for name in ("candidate_static", "run_manifest", "static_check"):
                _artifact(
                    contract[name],
                    f"P3.40 E1 latest-stage {name}",
                    maximum=(
                        P340_CANDIDATE_STATIC_MAX_BYTES
                        if name == "candidate_static"
                        else DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES
                    ),
                )
            return item
        if userspace_overlay_contract_id == P339_STOCK_OVERLAY_CONTRACT_ID:
            template = p339_stock_adapter.acceptance_fixture()
            expected_keys = set(template) | {"auth_key"}
            item = _exact(value, expected_keys, "P3.39 E1 latest-stage acceptance")
            for key, expected in template.items():
                if key == "contract":
                    continue
                if not _strict_equal(item.get(key), expected):
                    raise EvidenceError(f"P3.39 acceptance field differs: {key}")
            if item["auth_key"] != P339_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise EvidenceError("P3.39 acceptance auth-key identity differs")
            contract = _exact(
                item["contract"],
                {"candidate_static", "run_manifest", "static_check"},
                "P3.39 E1 latest-stage contract",
            )
            for name in ("candidate_static", "run_manifest", "static_check"):
                _artifact(
                    contract[name],
                    f"P3.39 E1 latest-stage {name}",
                    maximum=(
                        P339_CANDIDATE_STATIC_MAX_BYTES
                        if name == "candidate_static"
                        else DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES
                    ),
                )
            return item
        if userspace_overlay_contract_id == P338_STOCK_OVERLAY_CONTRACT_ID:
            template = p338_stock_adapter.acceptance_fixture()
            expected_keys = set(template) | {"auth_key"}
            item = _exact(value, expected_keys, "P3.38 E1 latest-stage acceptance")
            for key, expected in template.items():
                if key == "contract":
                    continue
                if not _strict_equal(item.get(key), expected):
                    raise EvidenceError(f"P3.38 acceptance field differs: {key}")
            if item["auth_key"] != P338_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise EvidenceError("P3.38 acceptance auth-key identity differs")
            contract = _exact(
                item["contract"],
                {"candidate_static", "run_manifest", "static_check"},
                "P3.38 E1 latest-stage contract",
            )
            for name in ("candidate_static", "run_manifest", "static_check"):
                _artifact(
                    contract[name],
                    f"P3.38 E1 latest-stage {name}",
                    maximum=(
                        P338_CANDIDATE_STATIC_MAX_BYTES
                        if name == "candidate_static"
                        else DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES
                    ),
                )
            return item
        if userspace_overlay_contract_id == P337_STOCK_OVERLAY_CONTRACT_ID:
            template = p337_stock_adapter.acceptance_fixture()
            expected_keys = set(template) | {"auth_key"}
            item = _exact(value, expected_keys, "P3.37 E1 latest-stage acceptance")
            for key, expected in template.items():
                if key == "contract":
                    continue
                if not _strict_equal(item.get(key), expected):
                    raise EvidenceError(f"P3.37 acceptance field differs: {key}")
            if item["auth_key"] != P337_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise EvidenceError("P3.37 acceptance auth-key identity differs")
            contract = _exact(
                item["contract"],
                {"candidate_static", "run_manifest", "static_check"},
                "P3.37 E1 latest-stage contract",
            )
            for name in ("candidate_static", "run_manifest", "static_check"):
                _artifact(
                    contract[name],
                    f"P3.37 E1 latest-stage {name}",
                    maximum=(
                        P337_CANDIDATE_STATIC_MAX_BYTES
                        if name == "candidate_static"
                        else DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES
                    ),
                )
            return item
        if userspace_overlay_contract_id == P336_STOCK_OVERLAY_CONTRACT_ID:
            template = p336_stock_adapter.acceptance_fixture()
            expected_keys = set(template) | {"auth_key"}
            item = _exact(value, expected_keys, "P3.36 E1 latest-stage acceptance")
            for key, expected in template.items():
                if key == "contract":
                    continue
                if not _strict_equal(item.get(key), expected):
                    raise EvidenceError(f"P3.36 acceptance field differs: {key}")
            if item["auth_key"] != P336_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise EvidenceError("P3.36 acceptance auth-key identity differs")
            contract = _exact(
                item["contract"],
                {"candidate_static", "run_manifest", "static_check"},
                "P3.36 E1 latest-stage contract",
            )
            for name in ("candidate_static", "run_manifest", "static_check"):
                _artifact(
                    contract[name],
                    f"P3.36 E1 latest-stage {name}",
                    maximum=(
                        P336_CANDIDATE_STATIC_MAX_BYTES
                        if name == "candidate_static"
                        else DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES
                    ),
                )
            return item
        if userspace_overlay_contract_id == P335_STOCK_OVERLAY_CONTRACT_ID:
            template = p335_stock_adapter.acceptance_fixture()
            expected_keys = set(template) | {"auth_key"}
            item = _exact(value, expected_keys, "P3.35 E1 latest-stage acceptance")
            for key, expected in template.items():
                if key == "contract":
                    continue
                if not _strict_equal(item.get(key), expected):
                    raise EvidenceError(f"P3.35 acceptance field differs: {key}")
            if item["auth_key"] != P335_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise EvidenceError("P3.35 acceptance auth-key identity differs")
            contract = _exact(
                item["contract"],
                {"candidate_static", "run_manifest", "static_check"},
                "P3.35 E1 latest-stage contract",
            )
            for name in ("candidate_static", "run_manifest", "static_check"):
                _artifact(
                    contract[name],
                    f"P3.35 E1 latest-stage {name}",
                    maximum=(
                        P335_CANDIDATE_STATIC_MAX_BYTES
                        if name == "candidate_static"
                        else DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES
                    ),
                )
            return item
        expected_keys = {
            "kind",
            "source",
            "decoder",
            "policy_id",
            "profile",
            "run_id",
            "long_family_hex",
            "unsat_family_hex",
            "terminal_stage",
            "minimum_success_count",
            "clean_baseline_required",
            "contract",
        }
        if source_contract_id is not None:
            expected_keys.add("source_contract_id")
        if userspace_overlay_contract_id is not None:
            expected_keys.add("userspace_overlay_contract_id")
        if userspace_overlay_contract_id in {
            P334_STOCK_OVERLAY_CONTRACT_ID,
            P333_STOCK_OVERLAY_CONTRACT_ID,
            P332_STOCK_OVERLAY_CONTRACT_ID,
            P331_STOCK_OVERLAY_CONTRACT_ID,
            P320_STOCK_OVERLAY_CONTRACT_ID,
            P321_STOCK_OVERLAY_CONTRACT_ID,
            P322_STOCK_OVERLAY_CONTRACT_ID,
            P323_STOCK_OVERLAY_CONTRACT_ID,
            P324_STOCK_OVERLAY_CONTRACT_ID,
            P325_STOCK_OVERLAY_CONTRACT_ID,
            P326_STOCK_OVERLAY_CONTRACT_ID,
            P327_STOCK_OVERLAY_CONTRACT_ID,
            P328_STOCK_OVERLAY_CONTRACT_ID,
            P329_STOCK_OVERLAY_CONTRACT_ID,
            P330_STOCK_OVERLAY_CONTRACT_ID,
        }:
            expected_keys.update(
                {"observer_contract", "causal_result_allowed", "candidate_success"}
            )
            if userspace_overlay_contract_id in {
                P334_STOCK_OVERLAY_CONTRACT_ID,
                P333_STOCK_OVERLAY_CONTRACT_ID,
                P332_STOCK_OVERLAY_CONTRACT_ID,
                P331_STOCK_OVERLAY_CONTRACT_ID,
                P323_STOCK_OVERLAY_CONTRACT_ID,
                P324_STOCK_OVERLAY_CONTRACT_ID,
                P325_STOCK_OVERLAY_CONTRACT_ID,
                P326_STOCK_OVERLAY_CONTRACT_ID,
                P327_STOCK_OVERLAY_CONTRACT_ID,
                P328_STOCK_OVERLAY_CONTRACT_ID,
                P329_STOCK_OVERLAY_CONTRACT_ID,
                P330_STOCK_OVERLAY_CONTRACT_ID,
            }:
                expected_keys.update({"schema", "overlay_contract_id"})
            if userspace_overlay_contract_id in {
                P334_STOCK_OVERLAY_CONTRACT_ID,
                P333_STOCK_OVERLAY_CONTRACT_ID,
                P332_STOCK_OVERLAY_CONTRACT_ID,
                P331_STOCK_OVERLAY_CONTRACT_ID,
                P328_STOCK_OVERLAY_CONTRACT_ID,
                P329_STOCK_OVERLAY_CONTRACT_ID,
                P330_STOCK_OVERLAY_CONTRACT_ID,
            }:
                expected_keys.update(
                    {
                        "authenticated_exec",
                        "authentication_required",
                        "auth_key_schema",
                        "auth_key_size",
                        "auth_key",
                    }
                )
            if userspace_overlay_contract_id in {
                P334_STOCK_OVERLAY_CONTRACT_ID,
                P333_STOCK_OVERLAY_CONTRACT_ID,
                P332_STOCK_OVERLAY_CONTRACT_ID,
                P330_STOCK_OVERLAY_CONTRACT_ID,
                P331_STOCK_OVERLAY_CONTRACT_ID,
            }:
                expected_keys.add("preauth_diagnostics")
            if userspace_overlay_contract_id in {
                P332_STOCK_OVERLAY_CONTRACT_ID,
                P333_STOCK_OVERLAY_CONTRACT_ID,
                P334_STOCK_OVERLAY_CONTRACT_ID,
            }:
                expected_keys.update(
                    {
                        "predecessor_run_id_rejected",
                        "predecessor_run_ids_rejected",
                        "resident_sessions",
                        "resident_reconnects",
                        "logical_same_tty",
                        "same_tty_fd",
                        "host_tty_close_reopen",
                        "transport_reconnect",
                        "fixed_heartbeat_only",
                        "fixed_p330_commands",
                        "command_count_per_session",
                    }
                )
                if userspace_overlay_contract_id in {
                    P333_STOCK_OVERLAY_CONTRACT_ID,
                    P334_STOCK_OVERLAY_CONTRACT_ID,
                }:
                    expected_keys.update(
                        {"entry_diagnostic_stage", "entry_diagnostic_before_console"}
                    )
                    if userspace_overlay_contract_id == P334_STOCK_OVERLAY_CONTRACT_ID:
                        expected_keys.update(
                            {
                                "first_console_return_checkpoint_only",
                                "first_console_return_detail_prefix",
                                "first_console_return_detail_sentinel",
                                "first_read_attribution_requires_stage0_without_stage1",
                            }
                        )
            if userspace_overlay_contract_id == P331_STOCK_OVERLAY_CONTRACT_ID:
                expected_keys.update(
                    {
                        "predecessor_run_id_rejected",
                        "resident_sessions",
                        "resident_reconnects",
                        "fixed_heartbeat_only",
                    }
                )
        item = _exact(
            value,
            expected_keys,
            "E1 latest-stage acceptance",
        )
        profile = item["profile"]
        selected_decoder = _latest_stage_observation_decoder(
            source_contract_id,
            profile,
            userspace_overlay_contract_id,
        )
        model = selected_decoder.model
        terminal_stage = _latest_stage_terminal(selected_decoder, profile)
        model_ids = {model.model_run_id(name).hex() for name in model.PROFILE_NUMBERS}
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != selected_decoder.DECODER_ID
            or item["policy_id"] != selected_decoder.POLICY_ID
            or profile not in model.PROFILE_NUMBERS
            or not isinstance(item["run_id"], str)
            or HEX32_RE.fullmatch(item["run_id"]) is None
            or item["run_id"] == "0" * 32
            or item["run_id"] in model_ids
            or item["long_family_hex"] != model.LONG_FAMILY.hex()
            or item["unsat_family_hex"] != model.UNSAT_FAMILY.hex()
            or type(item["terminal_stage"]) is not int
            or item["terminal_stage"] != terminal_stage
            or type(item["minimum_success_count"]) is not int
            or item["minimum_success_count"] != 1
            or item["clean_baseline_required"] is not True
        ):
            raise EvidenceError("E1 latest-stage acceptance identity is invalid")
        if userspace_overlay_contract_id in {
            P334_STOCK_OVERLAY_CONTRACT_ID,
            P333_STOCK_OVERLAY_CONTRACT_ID,
            P332_STOCK_OVERLAY_CONTRACT_ID,
            P331_STOCK_OVERLAY_CONTRACT_ID,
            P328_STOCK_OVERLAY_CONTRACT_ID,
            P329_STOCK_OVERLAY_CONTRACT_ID,
            P330_STOCK_OVERLAY_CONTRACT_ID,
        }:
            if (
                item["authenticated_exec"] is not True
                or item["authentication_required"] is not True
                or item["auth_key_schema"] != P328_AUTH_EXEC_AUTH_KEY_SCHEMA
                or type(item["auth_key_size"]) is not int
                or item["auth_key_size"] != P328_AUTH_EXEC_AUTH_KEY_SIZE
                or item["auth_key"] != P328_AUTH_EXEC_AUTH_KEY_IDENTITY
            ):
                raise EvidenceError("P3.28 authentication acceptance identity is invalid")
            if userspace_overlay_contract_id in {
                P334_STOCK_OVERLAY_CONTRACT_ID,
                P333_STOCK_OVERLAY_CONTRACT_ID,
                P332_STOCK_OVERLAY_CONTRACT_ID,
                P330_STOCK_OVERLAY_CONTRACT_ID,
                P331_STOCK_OVERLAY_CONTRACT_ID,
            } and item[
                "preauth_diagnostics"
            ] != {
                "frame_type": (
                    P333_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE
                    if userspace_overlay_contract_id
                    == P333_STOCK_OVERLAY_CONTRACT_ID
                    else P332_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE
                    if userspace_overlay_contract_id
                    == P332_STOCK_OVERLAY_CONTRACT_ID
                    else P331_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE
                    if userspace_overlay_contract_id
                    == P331_STOCK_OVERLAY_CONTRACT_ID
                    else P330_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE
                ),
                "stages": ["open-parsed", "rng"],
                "eagain_only_retry": True,
            }:
                raise EvidenceError(
                    "P3.33 diagnostic acceptance identity is invalid"
                    if userspace_overlay_contract_id
                    == P333_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.32 diagnostic acceptance identity is invalid"
                    if userspace_overlay_contract_id
                    == P332_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.31 diagnostic acceptance identity is invalid"
                    if userspace_overlay_contract_id
                    == P331_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.30 diagnostic acceptance identity is invalid"
                )
            if userspace_overlay_contract_id == P334_STOCK_OVERLAY_CONTRACT_ID and (
                item["predecessor_run_id_rejected"] != P334_PREDECESSOR_RUN_ID
                or item["predecessor_run_ids_rejected"]
                != [P330_RUN_ID, P331_RUN_ID, P332_RUN_ID, P334_PREDECESSOR_RUN_ID]
                or item["resident_sessions"] != P334_AUTH_EXEC_SESSION_CAP
                or item["resident_reconnects"] != 0
                or item["logical_same_tty"] is not True
                or item["same_tty_fd"] is not True
                or item["host_tty_close_reopen"] is not False
                or item["transport_reconnect"] is not False
                or item["fixed_heartbeat_only"] is not False
                or item["fixed_p330_commands"] is not True
                or item["command_count_per_session"] != P334_AUTH_EXEC_COMMAND_COUNT
                or item["entry_diagnostic_stage"] != 0
                or item["entry_diagnostic_before_console"] is not True
                or item["first_console_return_checkpoint_only"] is not True
                or item["first_console_return_detail_prefix"] != P334_AUTH_EXEC_DETAIL_PREFIX
                or item["first_console_return_detail_sentinel"] != P334_AUTH_EXEC_DETAIL_SENTINEL
                or item["first_read_attribution_requires_stage0_without_stage1"] is not True
            ):
                raise EvidenceError("P3.34 first-console-return acceptance identity is invalid")
            if userspace_overlay_contract_id == P333_STOCK_OVERLAY_CONTRACT_ID and (
                item["predecessor_run_id_rejected"] != P333_PREDECESSOR_RUN_ID
                or item["predecessor_run_ids_rejected"]
                != [P330_RUN_ID, P331_RUN_ID, P333_PREDECESSOR_RUN_ID]
                or item["resident_sessions"] != P333_AUTH_EXEC_SESSION_CAP
                or item["resident_reconnects"] != 0
                or item["logical_same_tty"] is not True
                or item["same_tty_fd"] is not True
                or item["host_tty_close_reopen"] is not False
                or item["transport_reconnect"] is not False
                or item["fixed_heartbeat_only"] is not False
                or item["fixed_p330_commands"] is not True
                or item["command_count_per_session"] != P333_AUTH_EXEC_COMMAND_COUNT
                or item["entry_diagnostic_stage"] != 0
                or item["entry_diagnostic_before_console"] is not True
            ):
                raise EvidenceError("P3.33 OPEN-entry acceptance identity is invalid")
            if userspace_overlay_contract_id == P332_STOCK_OVERLAY_CONTRACT_ID and (
                item["predecessor_run_id_rejected"] != P332_PREDECESSOR_RUN_ID
                or item["predecessor_run_ids_rejected"]
                != [P330_RUN_ID, P332_PREDECESSOR_RUN_ID]
                or item["resident_sessions"] != P332_AUTH_EXEC_SESSION_CAP
                or item["resident_reconnects"] != 0
                or item["logical_same_tty"] is not True
                or item["same_tty_fd"] is not True
                or item["host_tty_close_reopen"] is not False
                or item["transport_reconnect"] is not False
                or item["fixed_heartbeat_only"] is not False
                or item["fixed_p330_commands"] is not True
                or item["command_count_per_session"] != P332_AUTH_EXEC_COMMAND_COUNT
            ):
                raise EvidenceError("P3.32 logical resident acceptance identity is invalid")
            if userspace_overlay_contract_id == P331_STOCK_OVERLAY_CONTRACT_ID and (
                item["predecessor_run_id_rejected"] != P331_PREDECESSOR_RUN_ID
                or item["resident_sessions"] != P331_AUTH_EXEC_SESSION_CAP
                or item["resident_reconnects"] != P331_AUTH_EXEC_RECONNECT_CAP
                or item["fixed_heartbeat_only"] is not True
            ):
                raise EvidenceError("P3.31 resident acceptance identity is invalid")
        contract_keys = {"candidate_static", "run_manifest", "static_check"}
        stock_keys = {"stock_baseline_raw", "stock_baseline_result"}
        if userspace_overlay_contract_id in {
            P303_OVERLAY_CONTRACT_ID,
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
        }:
            supplied = stock_keys & set(item["contract"])
            if supplied not in (set(), stock_keys):
                raise EvidenceError(
                    "P3.03 stock baseline contract must be absent or an exact pair"
                )
            contract_keys.update(supplied)
        contract = _exact(
            item["contract"],
            contract_keys,
            "E1 latest-stage contract",
        )
        _artifact(
            contract["candidate_static"],
            "E1 latest-stage candidate_static",
            maximum=(
                P334_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P334_STOCK_OVERLAY_CONTRACT_ID
                else
                P333_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P333_STOCK_OVERLAY_CONTRACT_ID
                else P327_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P327_STOCK_OVERLAY_CONTRACT_ID
                else P329_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P329_STOCK_OVERLAY_CONTRACT_ID
                else P330_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P330_STOCK_OVERLAY_CONTRACT_ID
                else P331_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P331_STOCK_OVERLAY_CONTRACT_ID
                else P332_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P332_STOCK_OVERLAY_CONTRACT_ID
                else P328_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P328_STOCK_OVERLAY_CONTRACT_ID
                else P326_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P326_STOCK_OVERLAY_CONTRACT_ID
                else P325_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P325_STOCK_OVERLAY_CONTRACT_ID
                else P324_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P324_STOCK_OVERLAY_CONTRACT_ID
                else P323_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P323_STOCK_OVERLAY_CONTRACT_ID
                else P322_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P322_STOCK_OVERLAY_CONTRACT_ID
                else P321_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P321_STOCK_OVERLAY_CONTRACT_ID
                else P320_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id == P320_STOCK_OVERLAY_CONTRACT_ID
                else P319_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P319_STOCK_OVERLAY_CONTRACT_ID
                else P318_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P318_MAX77705_OVERLAY_CONTRACT_ID
                else P317_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id
                == P317_MAX77705_OVERLAY_CONTRACT_ID
                else P316_CANDIDATE_STATIC_MAX_BYTES
                if userspace_overlay_contract_id == MAX77705_OVERLAY_CONTRACT_ID
                else DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES
            ),
        )
        _artifact(contract["run_manifest"], "E1 latest-stage run_manifest")
        _artifact(contract["static_check"], "E1 latest-stage static_check")
        if stock_keys <= set(contract):
            _artifact(
                contract["stock_baseline_raw"],
                "P3.03 stock baseline raw",
            )
            _artifact(
                contract["stock_baseline_result"],
                "P3.03 stock baseline result",
            )
        if userspace_overlay_contract_id == P319_STOCK_OVERLAY_CONTRACT_ID:
            try:
                p319_stock_adapter.validate_acceptance_item(item)
            except p319_stock_adapter.DecodeError as exc:
                raise EvidenceError("P3.19 stock acceptance identity is invalid") from exc
        elif userspace_overlay_contract_id in {
            P334_STOCK_OVERLAY_CONTRACT_ID,
            P333_STOCK_OVERLAY_CONTRACT_ID,
            P332_STOCK_OVERLAY_CONTRACT_ID,
            P331_STOCK_OVERLAY_CONTRACT_ID,
            P320_STOCK_OVERLAY_CONTRACT_ID,
            P321_STOCK_OVERLAY_CONTRACT_ID,
            P322_STOCK_OVERLAY_CONTRACT_ID,
            P323_STOCK_OVERLAY_CONTRACT_ID,
            P324_STOCK_OVERLAY_CONTRACT_ID,
            P325_STOCK_OVERLAY_CONTRACT_ID,
            P326_STOCK_OVERLAY_CONTRACT_ID,
            P327_STOCK_OVERLAY_CONTRACT_ID,
            P328_STOCK_OVERLAY_CONTRACT_ID,
            P329_STOCK_OVERLAY_CONTRACT_ID,
            P330_STOCK_OVERLAY_CONTRACT_ID,
        }:
            if userspace_overlay_contract_id in {
                P334_STOCK_OVERLAY_CONTRACT_ID,
                P333_STOCK_OVERLAY_CONTRACT_ID,
                P332_STOCK_OVERLAY_CONTRACT_ID,
                P323_STOCK_OVERLAY_CONTRACT_ID,
                P324_STOCK_OVERLAY_CONTRACT_ID,
                P325_STOCK_OVERLAY_CONTRACT_ID,
                P326_STOCK_OVERLAY_CONTRACT_ID,
                P327_STOCK_OVERLAY_CONTRACT_ID,
                P328_STOCK_OVERLAY_CONTRACT_ID,
                P329_STOCK_OVERLAY_CONTRACT_ID,
                P330_STOCK_OVERLAY_CONTRACT_ID,
                P331_STOCK_OVERLAY_CONTRACT_ID,
            }:
                selected_adapter = STOCK_ADAPTERS[userspace_overlay_contract_id]
                if (
                    item["schema"] != selected_adapter.SCHEMA
                    or item["overlay_contract_id"]
                    != userspace_overlay_contract_id
                ):
                    label = (
                        "P3.34"
                        if userspace_overlay_contract_id
                        == P334_STOCK_OVERLAY_CONTRACT_ID
                        else
                        "P3.33"
                        if userspace_overlay_contract_id
                        == P333_STOCK_OVERLAY_CONTRACT_ID
                        else "P3.32"
                        if userspace_overlay_contract_id
                        == P332_STOCK_OVERLAY_CONTRACT_ID
                        else "P3.31"
                        if userspace_overlay_contract_id
                        == P331_STOCK_OVERLAY_CONTRACT_ID
                        else "P3.30"
                        if userspace_overlay_contract_id
                        == P330_STOCK_OVERLAY_CONTRACT_ID
                        else "P3.29"
                        if userspace_overlay_contract_id
                        == P329_STOCK_OVERLAY_CONTRACT_ID
                        else "P3.28"
                        if userspace_overlay_contract_id
                        == P328_STOCK_OVERLAY_CONTRACT_ID
                        else "P3.27"
                        if userspace_overlay_contract_id
                        == P327_STOCK_OVERLAY_CONTRACT_ID
                        else "P3.26"
                        if userspace_overlay_contract_id
                        == P326_STOCK_OVERLAY_CONTRACT_ID
                        else "P3.25"
                        if userspace_overlay_contract_id
                        == P325_STOCK_OVERLAY_CONTRACT_ID
                        else "P3.24"
                        if userspace_overlay_contract_id
                        == P324_STOCK_OVERLAY_CONTRACT_ID
                        else "P3.23"
                    )
                    raise EvidenceError(
                        f"{label} stock acceptance identity is invalid"
                    )
            try:
                STOCK_ADAPTERS[userspace_overlay_contract_id].validate_acceptance_item(
                    item
                )
            except STOCK_ADAPTERS[userspace_overlay_contract_id].DecodeError as exc:
                label = (
                    "P3.34"
                    if userspace_overlay_contract_id
                    == P334_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.33"
                    if userspace_overlay_contract_id
                    == P333_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.32"
                    if userspace_overlay_contract_id
                    == P332_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.31"
                    if userspace_overlay_contract_id
                    == P331_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.30"
                    if userspace_overlay_contract_id == P330_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.29"
                    if userspace_overlay_contract_id == P329_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.27"
                    if userspace_overlay_contract_id == P327_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.28"
                    if userspace_overlay_contract_id == P328_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.26"
                    if userspace_overlay_contract_id == P326_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.25"
                    if userspace_overlay_contract_id == P325_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.24"
                    if userspace_overlay_contract_id == P324_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.23"
                    if userspace_overlay_contract_id == P323_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "P3.22"
                    if userspace_overlay_contract_id == P322_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.21"
                    if userspace_overlay_contract_id == P321_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.20"
                )
                raise EvidenceError(f"{label} stock acceptance identity is invalid") from exc
        return item
    if kind == PID1_USERSPACE_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "marker",
                "family",
                "exact_count",
                "decoder",
                "probe_id",
                "entry_marker",
                "contract",
            },
            "PID1 userspace acceptance",
        )
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["marker"] != PID1_USERSPACE_PROOF.decode("ascii")
            or item["entry_marker"] != PID1_USERSPACE_ENTRY.decode("ascii")
            or item["family"] != PID1_USERSPACE_FAMILY.decode("ascii")
            or item["exact_count"] != 1
            or item["decoder"] != PID1_USERSPACE_DECODER
            or item["probe_id"] != PID1_USERSPACE_PROBE_ID
        ):
            raise EvidenceError("PID1 userspace acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "PID1 userspace contract",
        )
        _artifact(contract["run_manifest"], "PID1 userspace contract run_manifest")
        _artifact(contract["static_check"], "PID1 userspace contract static_check")
        return item
    if kind != CHECKPOINT_KIND:
        raise EvidenceError("acceptance kind is not allowlisted")

    item = _exact(
        value,
        {
            "kind",
            "source",
            "marker",
            "family",
            "exact_count",
            "decoder",
            "profile",
            "run_id",
            "terminal_stage",
            "terminal_outcome",
            "require_two_valid_slots",
            "contract",
        },
        "checkpoint acceptance",
    )
    if (
        item["source"] != CHECKPOINT_SOURCE
        or item["marker"] != checkpoint.ENTRY_PROOF.decode("ascii")
        or item["family"] != checkpoint.ENTRY_FAMILY.decode("ascii")
        or item["exact_count"] != 1
        or item["decoder"] != CHECKPOINT_DECODER
        or item["profile"] != "E1"
        or item["terminal_stage"] != checkpoint.PROFILE_TERMINAL_STAGE["E1"]
        or item["terminal_outcome"] != "success"
        or item["require_two_valid_slots"] is not True
        or not isinstance(item["run_id"], str)
        or HEX32_RE.fullmatch(item["run_id"]) is None
        or item["run_id"] == "0" * 32
        or item["run_id"]
        == checkpoint.MODEL_RUN_IDS["E1"].hex()
    ):
        raise EvidenceError("checkpoint acceptance identity is invalid")
    contract = _exact(
        item["contract"], {"run_manifest", "static_check"}, "checkpoint contract"
    )
    _artifact(contract["run_manifest"], "checkpoint contract run_manifest")
    _artifact(contract["static_check"], "checkpoint contract static_check")
    return item


def contract_artifacts(acceptance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    item = validate_acceptance(acceptance)
    if item["kind"] not in {
        CHECKPOINT_KIND,
        PID1_USERSPACE_KIND,
        SAME_RING_KIND,
        SAME_RING_MULTIBOOT_KIND,
        E1_LATEST_STAGE_KIND,
    }:
        return {}
    return {
        name: dict(value)
        for name, value in item["contract"].items()
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise EvidenceError(f"duplicate evidence JSON key: {key}")
        value[key] = item
    return value


def _json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} is not canonical JSON") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} is not an object")
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EvidenceError("run manifest is not canonical ASCII JSON") from exc


def _verify_checkpoint_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != CHECKPOINT_KIND:
        raise EvidenceError("offline checkpoint contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline checkpoint contract artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline checkpoint contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "run manifest")
    static_result = _json(payloads["static_check"], "static checker result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    run_id = canonical_sha256[:32]
    if (
        run_manifest.get("schema")
        != "s22plus_fyg8_r4w1e_e1_run_manifest_v1"
        or run_manifest.get("target") != checkpoint.TARGET
        or run_manifest.get("profile") != item["profile"]
        or run_manifest.get("checkpoint_carrier_sha256")
        != checkpoint.CARRIER_SHA256
        or run_manifest.get("checkpoint_patch_sha256") != checkpoint.PATCH_SHA256
        or run_id != item["run_id"]
    ):
        raise EvidenceError("run manifest does not bind the checkpoint acceptance")

    binding = static_result.get("run_binding")
    candidate = static_result.get("candidate")
    artifacts = candidate.get("artifacts") if isinstance(candidate, dict) else None
    blockers = static_result.get("blockers")
    safety = static_result.get("safety")
    if (
        static_result.get("schema")
        != "s22plus_fyg8_r4w1e_e1_candidate_static_checker_v1"
        or static_result.get("target") != checkpoint.TARGET
        or static_result.get("verdict")
        != "PASS_R4W1E_E1_OFFLINE_CANDIDATE_STATIC_CONTRACT"
        or blockers != []
        or not isinstance(binding, dict)
        or binding.get("run_id") != item["run_id"]
        or binding.get("canonical_manifest_size") != len(canonical)
        or binding.get("canonical_manifest_sha256") != canonical_sha256
        or binding.get("fresh_non_model_id") is not True
        or binding.get("verified") is not True
        or not isinstance(artifacts, dict)
        or not _artifact_matches(artifacts.get("ap"), candidate_ap)
        or not _artifact_matches(
            artifacts.get("run_manifest"), receipts["run_manifest"]
        )
        or candidate.get("boot_only_ap") is not True
        or not isinstance(safety, dict)
        or safety.get("host_only") is not True
        or any(
            safety.get(key) is not False
            for key in (
                "device_contact",
                "device_write",
                "odin_invoked",
                "odin_transfer",
                "flash",
                "partition_write",
                "live_authorized",
            )
        )
    ):
        raise EvidenceError("static checker result does not bind the candidate")
    return {
        "schema": "device_action_f1_checkpoint_offline_contract_v2",
        "decoder": item["decoder"],
        "profile": item["profile"],
        "run_id": item["run_id"],
        "terminal_stage": item["terminal_stage"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "verified": True,
    }
def _verify_pid1_userspace_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != PID1_USERSPACE_KIND:
        raise EvidenceError("offline PID1 userspace contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline PID1 userspace artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline PID1 userspace contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "run manifest")
    static_result = _json(payloads["static_check"], "static checker result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    observation = run_manifest.get("observation_contract")
    if (
        run_manifest.get("schema") != "s22plus_fyg8_r4w1e0_run_manifest_v1"
        or run_manifest.get("target") != PID1_USERSPACE_TARGET
        or run_manifest.get("profile") != "E0"
        or run_manifest.get("probe_id") != item["probe_id"]
        or run_manifest.get("entry_proof")
        != PID1_USERSPACE_ENTRY.decode("ascii").strip()
        or run_manifest.get("userspace_proof")
        != PID1_USERSPACE_PROOF.decode("ascii").strip()
        or observation
        != {
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
            "baseline_family_count": 0,
            "post_family_count": 1,
        }
    ):
        raise EvidenceError("run manifest does not bind PID1 userspace acceptance")

    binding = static_result.get("run_binding")
    candidate = static_result.get("candidate")
    artifacts = candidate.get("artifacts") if isinstance(candidate, dict) else None
    blockers = static_result.get("blockers")
    safety = static_result.get("safety")
    if (
        static_result.get("schema")
        != "s22plus_fyg8_r4w1e0_candidate_static_checker_v1"
        or static_result.get("target") != PID1_USERSPACE_TARGET
        or static_result.get("verdict")
        != "PASS_R4W1E0_OFFLINE_CANDIDATE_STATIC_CONTRACT"
        or blockers != []
        or not isinstance(binding, dict)
        or binding.get("run_id") != item["probe_id"]
        or binding.get("canonical_manifest_size") != len(canonical)
        or binding.get("canonical_manifest_sha256") != canonical_sha256
        or binding.get("fixed_probe_id") is not True
        or binding.get("clean_baseline_required") is not True
        or binding.get("verified") is not True
        or not isinstance(artifacts, dict)
        or not _artifact_matches(artifacts.get("ap"), candidate_ap)
        or not _artifact_matches(
            artifacts.get("run_manifest"), receipts["run_manifest"]
        )
        or candidate.get("boot_only_ap") is not True
        or not isinstance(safety, dict)
        or safety.get("host_only") is not True
        or any(
            safety.get(key) is not False
            for key in (
                "device_contact",
                "device_write",
                "odin_invoked",
                "odin_transfer",
                "flash",
                "partition_write",
                "live_authorized",
            )
        )
    ):
        raise EvidenceError("static checker result does not bind E0 candidate")
    return {
        "schema": "device_action_f1_pid1_userspace_offline_contract_v2",
        "decoder": item["decoder"],
        "probe_id": item["probe_id"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "verified": True,
    }


def _same_ring_records() -> dict[str, str]:
    return {
        "entry_hex": same_ring.ENTRY_PROOF.hex(),
        "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
        "unsat_hex": same_ring.UNSAT_PROOF.hex(),
    }


def _verify_same_ring_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] not in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        raise EvidenceError("offline same-ring contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline same-ring artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline same-ring contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "same-ring run manifest")
    static_result = _json(payloads["static_check"], "same-ring static result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    records = _same_ring_records()
    expected_observation = {
        "accepted_identity": "USERSPACE_CALLBACK_REACHED",
        "zero_classification": "ZERO_AMBIGUOUS",
        "entry_threshold": same_ring.ENTRY_SIZE,
        "unsat_threshold": same_ring.UNSAT_SIZE,
        "clean_baseline_required": True,
    }
    if (
        set(run_manifest)
        != {
            "schema",
            "target",
            "profile",
            "contract_id",
            "contract_sha256",
            "records",
            "observation_contract",
            "candidate_ap",
        }
        or run_manifest.get("schema") != SAME_RING_RUN_MANIFEST_SCHEMA
        or run_manifest.get("target") != same_ring.TARGET
        or run_manifest.get("profile") != "P219"
        or run_manifest.get("contract_id") != SAME_RING_CONTRACT_ID
        or run_manifest.get("contract_sha256") != same_ring.CONTRACT_SHA256
        or run_manifest.get("records") != records
        or run_manifest.get("observation_contract") != expected_observation
        or not _artifact_matches(run_manifest.get("candidate_ap"), candidate_ap)
        or payloads["run_manifest"] != canonical
    ):
        raise EvidenceError("run manifest does not bind the same-ring candidate")

    if (
        set(static_result)
        != {
            "schema",
            "target",
            "verdict",
            "contract_id",
            "contract_sha256",
            "records",
            "run_binding",
            "candidate",
            "safety",
        }
        or static_result.get("schema") != SAME_RING_STATIC_SCHEMA
        or static_result.get("target") != same_ring.TARGET
        or static_result.get("verdict") != SAME_RING_STATIC_VERDICT
        or static_result.get("contract_id") != SAME_RING_CONTRACT_ID
        or static_result.get("contract_sha256") != same_ring.CONTRACT_SHA256
        or static_result.get("records") != records
        or static_result.get("run_binding")
        != {
            "canonical_manifest_size": len(canonical),
            "canonical_manifest_sha256": canonical_sha256,
            "verified": True,
        }
    ):
        raise EvidenceError("static checker header does not bind P2.19 candidate")

    candidate = _exact(
        static_result["candidate"],
        {"artifacts", "record_verification"},
        "same-ring candidate",
    )
    artifacts = _exact(
        candidate["artifacts"],
        {"ap", "run_manifest", "image", "vmlinux", "boot_image"},
        "same-ring candidate artifacts",
    )
    identities = {
        name: _binary_identity(value, f"same-ring {name}")
        for name, value in artifacts.items()
    }
    verification = _exact(
        candidate["record_verification"],
        {
            "image",
            "vmlinux",
            "boot_image",
            "boot_kernel",
            "ap_members",
            "boot_only_ap",
            "verified",
        },
        "same-ring record verification",
    )
    image_claim = _record_blob_claim(
        verification["image"], "Image", identities["image"]
    )
    _record_blob_claim(
        verification["vmlinux"], "vmlinux", identities["vmlinux"]
    )
    boot_image_claim = _binary_identity(
        verification["boot_image"], "verified boot image"
    )
    boot_kernel_claim = _exact(
        verification["boot_kernel"],
        {"size", "sha256", "equals_image"},
        "verified boot kernel",
    )
    if (
        not _artifact_matches(identities["ap"], candidate_ap)
        or not _artifact_matches(
            identities["run_manifest"], receipts["run_manifest"]
        )
        or boot_image_claim != identities["boot_image"]
        or boot_kernel_claim
        != {
            "size": image_claim["size"],
            "sha256": image_claim["sha256"],
            "equals_image": True,
        }
        or verification["ap_members"]
        != [{"name": "boot.img.lz4", "type": "regular"}]
        or verification["boot_only_ap"] is not True
        or verification["verified"] is not True
        or static_result.get("safety")
        != {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
        }
    ):
        raise EvidenceError("static checker result does not bind P2.19 candidate")
    multiboot = item["kind"] == SAME_RING_MULTIBOOT_KIND
    result = {
        "schema": (
            "device_action_f1_same_ring_multiboot_offline_contract_v1"
            if multiboot
            else "device_action_f1_same_ring_offline_contract_v2"
        ),
        "decoder": (
            SAME_RING_MULTIBOOT_DECODER if multiboot else SAME_RING_DECODER
        ),
        "contract_id": SAME_RING_CONTRACT_ID,
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "zero_is_ambiguous": True,
        "verified": True,
    }
    if multiboot:
        result["policy_id"] = SAME_RING_MULTIBOOT_POLICY_ID
        result["minimum_exact_count"] = 1
    return result


P320_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p320_process_v2_run_manifest_v1"
P320_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p320_process_v2_static_result_v1"
P320_STATIC_RESULT_VERDICT = "PASS_P320_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P321_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p321_process_v2_run_manifest_v1"
P321_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p321_process_v2_static_result_v1"
P321_STATIC_RESULT_VERDICT = "PASS_P321_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P322_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p322_process_v2_run_manifest_v1"
P322_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p322_process_v2_static_result_v1"
P322_STATIC_RESULT_VERDICT = "PASS_P322_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P323_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p323_process_v2_run_manifest_v1"
P323_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p323_process_v2_static_result_v1"
P323_STATIC_RESULT_VERDICT = "PASS_P323_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P324_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p324_process_v2_run_manifest_v1"
P324_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p324_process_v2_static_result_v1"
P324_STATIC_RESULT_VERDICT = "PASS_P324_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P325_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p325_process_v2_run_manifest_v1"
P325_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p325_process_v2_static_result_v1"
P325_STATIC_RESULT_VERDICT = "PASS_P325_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P326_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p326_process_v2_run_manifest_v1"
P326_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p326_process_v2_static_result_v1"
P326_STATIC_RESULT_VERDICT = "PASS_P326_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P327_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p327_process_v2_run_manifest_v1"
P327_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p327_process_v2_static_result_v1"
P327_STATIC_RESULT_VERDICT = "PASS_P327_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P328_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p328_process_v2_run_manifest_v1"
P328_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p328_process_v2_static_result_v1"
P328_STATIC_RESULT_VERDICT = "PASS_P328_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P329_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p329_process_v2_run_manifest_v1"
P329_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p329_process_v2_static_result_v1"
P329_STATIC_RESULT_VERDICT = "PASS_P329_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P330_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p330_process_v2_run_manifest_v1"
P330_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p330_process_v2_static_result_v1"
P330_STATIC_RESULT_VERDICT = "PASS_P330_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P331_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p331_process_v2_run_manifest_v1"
P331_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p331_process_v2_static_result_v1"
P331_STATIC_RESULT_VERDICT = "PASS_P331_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P332_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p332_process_v2_run_manifest_v1"
P332_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p332_process_v2_static_result_v1"
P332_STATIC_RESULT_VERDICT = "PASS_P332_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P333_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p333_process_v2_run_manifest_v1"
P333_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p333_process_v2_static_result_v1"
P333_STATIC_RESULT_VERDICT = "PASS_P333_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P334_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p334_process_v2_run_manifest_v1"
P334_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p334_process_v2_static_result_v1"
P334_STATIC_RESULT_VERDICT = "PASS_P334_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P335_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p335_process_v2_run_manifest_v1"
P335_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p335_process_v2_static_result_v1"
P335_STATIC_RESULT_VERDICT = "PASS_P335_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P336_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p336_process_v2_run_manifest_v1"
P336_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p336_process_v2_static_result_v1"
P336_STATIC_RESULT_VERDICT = "PASS_P336_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P337_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p337_process_v2_run_manifest_v1"
P337_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p337_process_v2_static_result_v1"
P337_STATIC_RESULT_VERDICT = "PASS_P337_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P338_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p338_process_v2_run_manifest_v1"
P338_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p338_process_v2_static_result_v1"
P338_STATIC_RESULT_VERDICT = "PASS_P338_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P339_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p339_process_v2_run_manifest_v1"
P339_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p339_process_v2_static_result_v1"
P339_STATIC_RESULT_VERDICT = "PASS_P339_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P340_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p340_process_v2_run_manifest_v1"
P340_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p340_process_v2_static_result_v1"
P340_STATIC_RESULT_VERDICT = "PASS_P340_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P341_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p341_process_v2_run_manifest_v1"
P341_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p341_process_v2_static_result_v1"
P341_STATIC_RESULT_VERDICT = "PASS_P341_PROCESS_V2_STATIC_RESULT_HOST_ONLY"
P342_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p342_process_v2_run_manifest_v1"
P342_STATIC_RESULT_SCHEMA = "s22plus_fyg8_p342_process_v2_static_result_v1"
P342_STATIC_RESULT_VERDICT = "PASS_P342_PROCESS_V2_STATIC_RESULT_HOST_ONLY"


def _verify_p321_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P321_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.21 offline contract is not applicable")
    expected_names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != expected_names or set(receipts) != expected_names:
        raise EvidenceError("P3.21 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.21 offline contract {name} changed")
    candidate_static = _json(payloads["candidate_static"], "P3.21 candidate-static result")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.21 candidate-static bytes are not canonical")
    candidate_static = _validate_p321_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.21 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.21 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.21 AP boot member"),
    }
    if (
        candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate_static.get("run_id") != P321_RUN_ID
        or candidate_ap_identity == P319_EXACT_ARTIFACTS["ap_tar_md5"]
    ):
        raise EvidenceError("P3.21 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    records = {
        "long_family_hex": p321_stock_adapter.LONG_FAMILY.hex(),
        "unsat_family_hex": p321_stock_adapter.UNSAT_FAMILY.hex(),
        "terminal_stage": p321_stock_adapter.TERMINAL_STAGE,
    }
    expected_observation = {
        "accepted_identity": "P321_STOCK_OBSERVER_V4_RETAINED",
        "minimum_success_count": 1,
        "clean_baseline_required": True,
        "runtime_values_preflighted": False,
        "complete_is_noncausal": True,
        "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
        "receipt_result": "NO_PROOF_OBSERVER",
    }
    run_manifest = _json(payloads["run_manifest"], "P3.21 run manifest")
    expected_manifest = {
        "schema": P321_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p321_stock_adapter.PROFILE,
        "run_id": P321_RUN_ID,
        "decoder": p321_stock_adapter.DECODER_ID,
        "policy_id": p321_stock_adapter.POLICY_ID,
        "records": records,
        "observation_contract": expected_observation,
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p321_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P321_STOCK_OVERLAY_CONTRACT_ID,
    }
    if run_manifest != expected_manifest or payloads["run_manifest"] != _canonical(run_manifest):
        raise EvidenceError("P3.21 run manifest differs from candidate-static")
    static_result = _json(payloads["static_check"], "P3.21 static result")
    run_payload = _canonical(run_manifest)
    expected_static = {
        "schema": P321_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P321_STATIC_RESULT_VERDICT,
        "profile": p321_stock_adapter.PROFILE,
        "run_id": P321_RUN_ID,
        "decoder": p321_stock_adapter.DECODER_ID,
        "policy_id": p321_stock_adapter.POLICY_ID,
        "source_contract_id": p321_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P321_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": candidate_ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "latch": P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if static_result != expected_static or payloads["static_check"] != _canonical(static_result):
        raise EvidenceError("P3.21 static result differs")
    source_contract = _selected_contract(
        p321_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p321_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.21 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p321_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.21 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p321_stock_offline_contract_v1",
        "decoder": p321_stock_adapter.DECODER_ID,
        "policy_id": p321_stock_adapter.POLICY_ID,
        "profile": p321_stock_adapter.PROFILE,
        "run_id": P321_RUN_ID,
        "terminal_stage": p321_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p321_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.21 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p321_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p321_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P321_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p321_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "verified": True,
    }


def _verify_p322_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P322_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.22 offline contract is not applicable")
    expected_names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != expected_names or set(receipts) != expected_names:
        raise EvidenceError("P3.22 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.22 offline contract {name} changed")
    candidate_static = _json(payloads["candidate_static"], "P3.22 candidate-static result")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.22 candidate-static bytes are not canonical")
    candidate_static = _validate_p322_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.22 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.22 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.22 AP boot member"),
    }
    if (
        candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate_static.get("run_id") != P322_RUN_ID
        or candidate_ap_identity == P319_EXACT_ARTIFACTS["ap_tar_md5"]
    ):
        raise EvidenceError("P3.22 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    records = {
        "long_family_hex": p322_stock_adapter.LONG_FAMILY.hex(),
        "unsat_family_hex": p322_stock_adapter.UNSAT_FAMILY.hex(),
        "terminal_stage": p322_stock_adapter.TERMINAL_STAGE,
    }
    expected_observation = {
        "accepted_identity": "P322_STOCK_OBSERVER_V4_RETAINED",
        "minimum_success_count": 1,
        "clean_baseline_required": True,
        "runtime_values_preflighted": False,
        "complete_is_noncausal": True,
        "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
        "receipt_result": "NO_PROOF_OBSERVER",
    }
    run_manifest = _json(payloads["run_manifest"], "P3.22 run manifest")
    expected_manifest = {
        "schema": P322_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p322_stock_adapter.PROFILE,
        "run_id": P322_RUN_ID,
        "decoder": p322_stock_adapter.DECODER_ID,
        "policy_id": p322_stock_adapter.POLICY_ID,
        "records": records,
        "observation_contract": expected_observation,
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p322_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P322_STOCK_OVERLAY_CONTRACT_ID,
    }
    if run_manifest != expected_manifest or payloads["run_manifest"] != _canonical(run_manifest):
        raise EvidenceError("P3.22 run manifest differs from candidate-static")
    static_result = _json(payloads["static_check"], "P3.22 static result")
    run_payload = _canonical(run_manifest)
    expected_static = {
        "schema": P322_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P322_STATIC_RESULT_VERDICT,
        "profile": p322_stock_adapter.PROFILE,
        "run_id": P322_RUN_ID,
        "decoder": p322_stock_adapter.DECODER_ID,
        "policy_id": p322_stock_adapter.POLICY_ID,
        "source_contract_id": p322_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P322_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": candidate_ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "latch": P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if static_result != expected_static or payloads["static_check"] != _canonical(static_result):
        raise EvidenceError("P3.22 static result differs")
    source_contract = _selected_contract(
        p322_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p322_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.22 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p322_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.22 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p322_stock_offline_contract_v1",
        "decoder": p322_stock_adapter.DECODER_ID,
        "policy_id": p322_stock_adapter.POLICY_ID,
        "profile": p322_stock_adapter.PROFILE,
        "run_id": P322_RUN_ID,
        "terminal_stage": p322_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p322_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.22 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p322_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p322_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P322_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p322_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "verified": True,
    }


def _verify_p323_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the P323 static bundle while keeping Carrier supplemental."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P323_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.23 offline contract is not applicable")
    expected_names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != expected_names or set(receipts) != expected_names:
        raise EvidenceError("P3.23 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.23 offline contract {name} changed")
    candidate_static = _json(payloads["candidate_static"], "P3.23 candidate-static result")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.23 candidate-static bytes are not canonical")
    candidate_static = _validate_p323_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.23 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.23 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.23 AP boot member"),
    }
    if (
        candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate_static.get("run_id") != P323_RUN_ID
        or candidate_ap_identity == P319_EXACT_ARTIFACTS["ap_tar_md5"]
    ):
        raise EvidenceError("P3.23 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    run_manifest = _json(payloads["run_manifest"], "P3.23 run manifest")
    expected_manifest = {
        "schema": P323_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p323_stock_adapter.PROFILE,
        "run_id": P323_RUN_ID,
        "decoder": p323_stock_adapter.DECODER_ID,
        "policy_id": p323_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p323_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p323_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p323_stock_adapter.TERMINAL_STAGE,
        },
        "observation_contract": {
            "accepted_identity": "P323_STOCK_OBSERVER_V4_RETAINED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_result": "NO_PROOF_OBSERVER",
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p323_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P323_STOCK_OVERLAY_CONTRACT_ID,
    }
    if run_manifest != expected_manifest or payloads["run_manifest"] != _canonical(run_manifest):
        raise EvidenceError("P3.23 run manifest differs from candidate-static")
    static_result = _json(payloads["static_check"], "P3.23 static result")
    run_payload = _canonical(run_manifest)
    expected_static = {
        "schema": P323_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P323_STATIC_RESULT_VERDICT,
        "profile": p323_stock_adapter.PROFILE,
        "run_id": P323_RUN_ID,
        "decoder": p323_stock_adapter.DECODER_ID,
        "policy_id": p323_stock_adapter.POLICY_ID,
        "source_contract_id": p323_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P323_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": candidate_ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "latch": P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if static_result != expected_static or payloads["static_check"] != _canonical(static_result):
        raise EvidenceError("P3.23 static result differs")
    source_contract = _selected_contract(
        p323_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p323_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.23 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p323_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.23 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p323_stock_offline_contract_v1",
        "decoder": p323_stock_adapter.DECODER_ID,
        "policy_id": p323_stock_adapter.POLICY_ID,
        "profile": p323_stock_adapter.PROFILE,
        "run_id": P323_RUN_ID,
        "terminal_stage": p323_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p323_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.23 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p323_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p323_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P323_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p323_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "verified": True,
    }


def _verify_p324_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the P324 identity successor and its exact host-only closure."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P324_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.24 offline contract is not applicable")
    expected_names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != expected_names or set(receipts) != expected_names:
        raise EvidenceError("P3.24 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.24 offline contract {name} changed")
    candidate_static = _json(
        payloads["candidate_static"], "P3.24 candidate-static result"
    )
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.24 candidate-static bytes are not canonical")
    candidate_static = _validate_p324_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.24 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.24 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(
            candidate["a"].get("boot_img_lz4"), "P3.24 AP boot member"
        ),
    }
    if (
        candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate_static.get("run_id") != P324_RUN_ID
        or candidate_ap_identity == P319_EXACT_ARTIFACTS["ap_tar_md5"]
    ):
        raise EvidenceError("P3.24 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    run_manifest = _json(payloads["run_manifest"], "P3.24 run manifest")
    expected_manifest = {
        "schema": P324_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p324_stock_adapter.PROFILE,
        "run_id": P324_RUN_ID,
        "decoder": p324_stock_adapter.DECODER_ID,
        "policy_id": p324_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p324_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p324_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p324_stock_adapter.TERMINAL_STAGE,
        },
        "observation_contract": {
            "accepted_identity": "P324_STOCK_OBSERVER_V4_RETAINED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_result": "NO_PROOF_OBSERVER",
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p324_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P324_STOCK_OVERLAY_CONTRACT_ID,
    }
    if run_manifest != expected_manifest or payloads["run_manifest"] != _canonical(run_manifest):
        raise EvidenceError("P3.24 run manifest differs from candidate-static")
    static_result = _json(payloads["static_check"], "P3.24 static result")
    run_payload = _canonical(run_manifest)
    expected_static = {
        "schema": P324_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P324_STATIC_RESULT_VERDICT,
        "profile": p324_stock_adapter.PROFILE,
        "run_id": P324_RUN_ID,
        "decoder": p324_stock_adapter.DECODER_ID,
        "policy_id": p324_stock_adapter.POLICY_ID,
        "source_contract_id": p324_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P324_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": candidate_ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "latch": P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if static_result != expected_static or payloads["static_check"] != _canonical(static_result):
        raise EvidenceError("P3.24 static result differs")
    source_contract = _selected_contract(
        p324_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        p324_stock_adapter.PROFILE,
    )
    try:
        _source_payloads, candidate_source_receipts = (
            source_contract.module.source_receipts(
                Path(__file__).resolve().parents[5]
            )
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.24 parent source receipts are unavailable") from exc
    lineage_sources = (
        candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    )
    if (
        not isinstance(lineage_sources, dict)
        or set(lineage_sources) != p324_stock_adapter.SOURCE_KEYS
    ):
        raise EvidenceError("P3.24 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p324_stock_offline_contract_v1",
        "decoder": p324_stock_adapter.DECODER_ID,
        "policy_id": p324_stock_adapter.POLICY_ID,
        "profile": p324_stock_adapter.PROFILE,
        "run_id": P324_RUN_ID,
        "terminal_stage": p324_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p324_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.24 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p324_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p324_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P324_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p324_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "verified": True,
    }


def _verify_p325_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the fresh P325 static bundle and its host-only closure."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P325_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.25 offline contract is not applicable")
    expected_names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != expected_names or set(receipts) != expected_names:
        raise EvidenceError("P3.25 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.25 offline contract {name} changed")
    candidate_static = _json(
        payloads["candidate_static"], "P3.25 candidate-static result"
    )
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.25 candidate-static bytes are not canonical")
    candidate_static = _validate_p325_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.25 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.25 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(
            candidate["a"].get("boot_img_lz4"), "P3.25 AP boot member"
        ),
    }
    if (
        candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate_static.get("run_id") != P325_RUN_ID
        or candidate_ap_identity == P319_EXACT_ARTIFACTS["ap_tar_md5"]
    ):
        raise EvidenceError("P3.25 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    run_manifest = _json(payloads["run_manifest"], "P3.25 run manifest")
    expected_manifest = {
        "schema": P325_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p325_stock_adapter.PROFILE,
        "run_id": P325_RUN_ID,
        "decoder": p325_stock_adapter.DECODER_ID,
        "policy_id": p325_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p325_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p325_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p325_stock_adapter.TERMINAL_STAGE,
        },
        "observation_contract": {
            "accepted_identity": "P325_STOCK_OBSERVER_V4_RETAINED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_result": "NO_PROOF_OBSERVER",
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p325_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P325_STOCK_OVERLAY_CONTRACT_ID,
    }
    if (
        run_manifest != expected_manifest
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.25 run manifest differs from candidate-static")
    static_result = _json(payloads["static_check"], "P3.25 static result")
    run_payload = _canonical(run_manifest)
    expected_static = {
        "schema": P325_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P325_STATIC_RESULT_VERDICT,
        "profile": p325_stock_adapter.PROFILE,
        "run_id": P325_RUN_ID,
        "decoder": p325_stock_adapter.DECODER_ID,
        "policy_id": p325_stock_adapter.POLICY_ID,
        "source_contract_id": p325_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P325_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": candidate_ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "latch": P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if (
        static_result != expected_static
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.25 static result differs")
    source_contract = _selected_contract(
        p325_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        p325_stock_adapter.PROFILE,
    )
    try:
        _source_payloads, candidate_source_receipts = (
            source_contract.module.source_receipts(
                Path(__file__).resolve().parents[5]
            )
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.25 parent source receipts are unavailable") from exc
    lineage_sources = (
        candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    )
    if (
        not isinstance(lineage_sources, dict)
        or set(lineage_sources) != p325_stock_adapter.SOURCE_KEYS
    ):
        raise EvidenceError("P3.25 adapter source receipts are incomplete")
    guard_adapter = candidate_static.get("guard_adapter")
    guard_source = (
        guard_adapter.get("source")
        if isinstance(guard_adapter, dict)
        else None
    )
    if not isinstance(guard_source, dict):
        raise EvidenceError("P3.25 guard adapter source receipt is missing")
    guard_source = _artifact(
        guard_source,
        "P3.25 guard adapter source",
        maximum=2 * 1024 * 1024,
    )
    if guard_source["path"] != (
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p325_cdc_acm_guard_adapter.py"
    ):
        raise EvidenceError("P3.25 guard adapter source path differs")
    guard_source = _binary_identity(
        {key: guard_source[key] for key in ("size", "sha256")},
        "P3.25 guard adapter source identity",
    )
    return {
        "schema": "device_action_f1_p325_stock_offline_contract_v1",
        "decoder": p325_stock_adapter.DECODER_ID,
        "policy_id": p325_stock_adapter.POLICY_ID,
        "profile": p325_stock_adapter.PROFILE,
        "run_id": P325_RUN_ID,
        "terminal_stage": p325_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p325_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.25 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p325_guard_adapter_source": guard_source,
        "p325_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p325_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P325_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p325_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "verified": True,
    }


def _verify_p326_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the P326 static, AP, BusyBox, and observer closure."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P326_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.26 offline contract is not applicable")
    expected_names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != expected_names or set(receipts) != expected_names:
        raise EvidenceError("P3.26 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.26 offline contract {name} changed")
    candidate_static = _json(
        payloads["candidate_static"], "P3.26 candidate-static result"
    )
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.26 candidate-static bytes are not canonical")
    candidate_static = _validate_p326_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.26 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.26 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.26 AP boot member"),
    }
    if (
        candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate_static.get("run_id") != P326_RUN_ID
        or candidate_ap_identity == P319_EXACT_ARTIFACTS["ap_tar_md5"]
    ):
        raise EvidenceError("P3.26 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    run_manifest = _json(payloads["run_manifest"], "P3.26 run manifest")
    expected_manifest = {
        "schema": P326_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p326_stock_adapter.PROFILE,
        "run_id": P326_RUN_ID,
        "decoder": p326_stock_adapter.DECODER_ID,
        "policy_id": p326_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p326_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p326_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p326_stock_adapter.TERMINAL_STAGE,
        },
        "observation_contract": {
            "accepted_identity": "P326_STOCK_OBSERVER_V4_RETAINED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_result": "NO_PROOF_OBSERVER",
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p326_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P326_STOCK_OVERLAY_CONTRACT_ID,
    }
    if run_manifest != expected_manifest or payloads["run_manifest"] != _canonical(run_manifest):
        raise EvidenceError("P3.26 run manifest differs from candidate-static")
    static_result = _json(payloads["static_check"], "P3.26 static result")
    run_payload = _canonical(run_manifest)
    expected_static = {
        "schema": P326_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P326_STATIC_RESULT_VERDICT,
        "profile": p326_stock_adapter.PROFILE,
        "run_id": P326_RUN_ID,
        "decoder": p326_stock_adapter.DECODER_ID,
        "policy_id": p326_stock_adapter.POLICY_ID,
        "source_contract_id": p326_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P326_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": candidate_ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "busybox": candidate["busybox"],
                "latch": P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if static_result != expected_static or payloads["static_check"] != _canonical(static_result):
        raise EvidenceError("P3.26 static result differs")
    source_contract = _selected_contract(
        p326_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        p326_stock_adapter.PROFILE,
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.26 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p326_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.26 adapter source receipts are incomplete")
    observer_source = candidate_static.get("observer_adapter", {}).get("source")
    if not isinstance(observer_source, dict):
        raise EvidenceError("P3.26 observer source receipt is missing")
    observer_source = _artifact(
        observer_source, "P3.26 observer source", maximum=2 * 1024 * 1024
    )
    if observer_source["path"] != (
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p326_bidirectional_acm_observer.py"
    ):
        raise EvidenceError("P3.26 observer source path differs")
    observer_source_identity = _binary_identity(
        {key: observer_source[key] for key in ("size", "sha256")},
        "P3.26 observer source identity",
    )
    console_source = candidate_static.get("source_closure", {}).get(
        "p326_bidirectional_console_runtime"
    )
    if not isinstance(console_source, dict):
        raise EvidenceError("P3.26 console runtime source receipt is missing")
    console_source = _artifact(
        console_source, "P3.26 console runtime source", maximum=2 * 1024 * 1024
    )
    if console_source["path"] != (
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p326_bidirectional_console_runtime.py"
    ):
        raise EvidenceError("P3.26 console runtime source path differs")
    console_source_identity = _binary_identity(
        {key: console_source[key] for key in ("size", "sha256")},
        "P3.26 console runtime source identity",
    )
    return {
        "schema": "device_action_f1_p326_stock_offline_contract_v1",
        "decoder": p326_stock_adapter.DECODER_ID,
        "policy_id": p326_stock_adapter.POLICY_ID,
        "profile": p326_stock_adapter.PROFILE,
        "run_id": P326_RUN_ID,
        "terminal_stage": p326_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p326_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.26 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p326_observer_source": observer_source_identity,
        "p326_console_runtime_source": console_source_identity,
        "p326_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p326_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P326_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p326_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "verified": True,
    }


def _verify_p327_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the P3.27 static, AP, BusyBox, and framed observer closure."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P327_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.27 offline contract is not applicable")
    expected_names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != expected_names or set(receipts) != expected_names:
        raise EvidenceError("P3.27 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.27 offline contract {name} changed")
    candidate_static = _json(
        payloads["candidate_static"], "P3.27 candidate-static result"
    )
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.27 candidate-static bytes are not canonical")
    candidate_static = _validate_p327_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.27 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.27 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.27 AP boot member"),
    }
    if (
        candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate_static.get("run_id") != P327_RUN_ID
        or candidate_static.get("predecessor_run_id") != P326_RUN_ID
    ):
        raise EvidenceError("P3.27 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    run_manifest = _json(payloads["run_manifest"], "P3.27 run manifest")
    expected_manifest = {
        "schema": P327_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p327_stock_adapter.PROFILE,
        "run_id": P327_RUN_ID,
        "decoder": p327_stock_adapter.DECODER_ID,
        "policy_id": p327_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p327_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p327_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p327_stock_adapter.TERMINAL_STAGE,
        },
        "observation_contract": {
            "accepted_identity": "P327_STOCK_OBSERVER_V4_RETAINED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_result": "NO_PROOF_OBSERVER",
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p327_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P327_STOCK_OVERLAY_CONTRACT_ID,
    }
    if (
        not _strict_equal(run_manifest, expected_manifest)
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.27 run manifest differs from candidate-static")
    static_result = _json(payloads["static_check"], "P3.27 static result")
    run_payload = _canonical(run_manifest)
    expected_static = {
        "schema": P327_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P327_STATIC_RESULT_VERDICT,
        "profile": p327_stock_adapter.PROFILE,
        "run_id": P327_RUN_ID,
        "decoder": p327_stock_adapter.DECODER_ID,
        "policy_id": p327_stock_adapter.POLICY_ID,
        "source_contract_id": p327_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P327_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": candidate_ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "busybox": candidate["busybox"],
                "latch": P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if (
        not _strict_equal(static_result, expected_static)
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.27 static result differs")
    source_contract = _selected_contract(
        p327_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        p327_stock_adapter.PROFILE,
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.27 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if (
        not isinstance(lineage_sources, dict)
        or set(lineage_sources) != p327_stock_adapter.SOURCE_KEYS
    ):
        raise EvidenceError("P3.27 adapter source receipts are incomplete")
    observer_source = candidate_static.get("observer_adapter", {}).get("source")
    runtime_source = candidate_static.get("observer_adapter", {}).get("runtime_source")
    if not isinstance(observer_source, dict) or not isinstance(runtime_source, dict):
        raise EvidenceError("P3.27 framed observer source receipts are incomplete")
    observer_source = _artifact(
        observer_source, "P3.27 framed observer source", maximum=2 * 1024 * 1024
    )
    runtime_source = _artifact(
        runtime_source, "P3.27 framed runtime source", maximum=2 * 1024 * 1024
    )
    expected_observer_path = (
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p327_framed_acm_observer.py"
    )
    expected_runtime_path = (
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p327_framed_exec_runtime.py"
    )
    if observer_source["path"] != expected_observer_path:
        raise EvidenceError("P3.27 framed observer source path differs")
    if runtime_source["path"] != expected_runtime_path:
        raise EvidenceError("P3.27 framed runtime source path differs")
    observer_source_identity = _binary_identity(
        {key: observer_source[key] for key in ("size", "sha256")},
        "P3.27 framed observer source identity",
    )
    runtime_source_identity = _binary_identity(
        {key: runtime_source[key] for key in ("size", "sha256")},
        "P3.27 framed runtime source identity",
    )
    observer_adapter = candidate_static.get("observer_adapter")
    if not isinstance(observer_adapter, dict):
        raise EvidenceError("P3.27 observer adapter metadata is missing")
    expected_observer_adapter = {
        "schema": "s22plus_fyg8_p327_framed_acm_session_v1",
        "contract_id": "s22plus-fyg8-p327-framed-acm-observer-v1",
        "wire_magic": "S327",
        "frame_header_size": 16,
        "max_frame_payload": P327_FRAMED_EXEC_MAX_FRAME_PAYLOAD,
        "max_commands": P327_FRAMED_EXEC_COMMAND_COUNT,
        "command_timeout_sec": P327_FRAMED_EXEC_COMMAND_TIMEOUT_SEC,
        "max_output_bytes": P327_FRAMED_EXEC_MAX_OUTPUT_BYTES,
        "commands": [
            {"size": len(command), "sha256": hashlib.sha256(command).hexdigest()}
            for command in (
                b"/bin/busybox id",
                b"/bin/busybox uname -a",
                f"/bin/busybox echo P327-NONCE {P327_RUN_ID}".encode("ascii"),
            )
        ],
        "caller_selected_command": False,
        "interactive_pty": False,
        "raw_rx_forwarded_before_classification": True,
        "host_only": True,
        "device_contact": False,
    }
    if any(
        not _strict_equal(observer_adapter.get(key), value)
        for key, value in expected_observer_adapter.items()
    ):
        raise EvidenceError("P3.27 framed observer contract differs")
    return {
        "schema": "device_action_f1_p327_stock_offline_contract_v1",
        "decoder": p327_stock_adapter.DECODER_ID,
        "policy_id": p327_stock_adapter.POLICY_ID,
        "profile": p327_stock_adapter.PROFILE,
        "run_id": P327_RUN_ID,
        "terminal_stage": p327_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p327_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.27 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p327_framed_observer_source": observer_source_identity,
        "p327_framed_runtime_source": runtime_source_identity,
        "p327_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p327_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P327_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p327_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "verified": True,
    }


def _verify_p328_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the P3.28 boot-only/authenticated promotion closure."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P328_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.28 offline contract is not applicable")
    expected_names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != expected_names or set(receipts) != expected_names:
        raise EvidenceError("P3.28 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.28 offline contract {name} changed")

    candidate_static = _json(
        payloads["candidate_static"], "P3.28 candidate-static result"
    )
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.28 candidate-static bytes are not canonical")
    candidate_static = _validate_p328_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.28 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.28 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.28 AP boot member"),
    }
    if (
        candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate_static.get("run_id") != P328_RUN_ID
        or candidate_static.get("predecessor_run_id") != P327_RUN_ID
    ):
        raise EvidenceError("P3.28 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    run_manifest = _json(payloads["run_manifest"], "P3.28 run manifest")
    expected_manifest = {
        "schema": P328_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p328_stock_adapter.PROFILE,
        "run_id": P328_RUN_ID,
        "decoder": p328_stock_adapter.DECODER_ID,
        "policy_id": p328_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p328_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p328_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p328_stock_adapter.TERMINAL_STAGE,
        },
        "observation_contract": {
            "accepted_identity": "P328_STOCK_OBSERVER_V4_RETAINED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_result": "NO_PROOF_OBSERVER",
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p328_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P328_STOCK_OVERLAY_CONTRACT_ID,
    }
    if (
        not _strict_equal(run_manifest, expected_manifest)
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.28 run manifest differs from candidate-static")
    static_result = _json(payloads["static_check"], "P3.28 static result")
    run_payload = _canonical(run_manifest)
    expected_static = {
        "schema": P328_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P328_STATIC_RESULT_VERDICT,
        "profile": p328_stock_adapter.PROFILE,
        "run_id": P328_RUN_ID,
        "decoder": p328_stock_adapter.DECODER_ID,
        "policy_id": p328_stock_adapter.POLICY_ID,
        "source_contract_id": p328_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P328_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": candidate_ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "busybox": candidate["busybox"],
                "latch": P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if (
        not _strict_equal(static_result, expected_static)
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.28 static result differs")

    source_contract = _selected_contract(
        p328_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        p328_stock_adapter.PROFILE,
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.28 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get(
        "sources"
    )
    if (
        not isinstance(lineage_sources, dict)
        or set(lineage_sources) != p328_stock_adapter.SOURCE_KEYS
    ):
        raise EvidenceError("P3.28 adapter source receipts are incomplete")

    observer_adapter = candidate_static.get("observer_adapter")
    if not isinstance(observer_adapter, dict):
        raise EvidenceError("P3.28 observer adapter metadata is missing")
    observer_source = observer_adapter.get("source")
    runtime_source = observer_adapter.get("runtime_source")
    if not isinstance(observer_source, dict) or not isinstance(runtime_source, dict):
        raise EvidenceError("P3.28 authenticated observer source receipts are incomplete")
    observer_source = _artifact(
        observer_source, "P3.28 authenticated observer source", maximum=2 * 1024 * 1024
    )
    runtime_source = _artifact(
        runtime_source, "P3.28 authenticated runtime source", maximum=2 * 1024 * 1024
    )
    artifact_source = candidate_static.get("source_closure", {}).get(
        "p328_artifact_identity"
    )
    if not isinstance(artifact_source, dict):
        raise EvidenceError("P3.28 artifact identity source receipt is missing")
    artifact_source = _artifact(
        artifact_source, "P3.28 artifact identity source", maximum=2 * 1024 * 1024
    )
    expected_observer_path = (
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p328_auth_acm_observer.py"
    )
    expected_runtime_path = (
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p328_auth_exec_runtime.py"
    )
    expected_artifact_path = (
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p328_artifact_identity.py"
    )
    if (
        observer_source["path"] != expected_observer_path
        or runtime_source["path"] != expected_runtime_path
        or artifact_source["path"] != expected_artifact_path
    ):
        raise EvidenceError("P3.28 authenticated source path differs")
    key_identity = _binary_identity(
        candidate_static.get("artifact_identity", {}).get("auth_key"),
        "P3.28 public auth key identity",
    )
    if key_identity != P328_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.28 public auth key identity differs")
    expected_observer_adapter = {
        "schema": "s22plus_fyg8_p328_auth_acm_session_v1",
        "contract_id": P328_AUTH_EXEC_OBSERVER_CONTRACT_ID,
        "wire_magic": "S328",
        "frame_header_size": 16,
        "max_frame_payload": P328_AUTH_EXEC_MAX_FRAME_PAYLOAD,
        "max_commands": P328_AUTH_EXEC_MAX_COMMANDS,
        "proof_command_count": P328_AUTH_EXEC_COMMAND_COUNT,
        "command_timeout_sec": P328_AUTH_EXEC_COMMAND_TIMEOUT_SEC,
        "max_output_bytes": P328_AUTH_EXEC_MAX_OUTPUT_BYTES,
        "commands": [
            {"size": len(command), "sha256": hashlib.sha256(command).hexdigest()}
            for command in (
                b"/bin/busybox id",
                b"/bin/busybox uname -a",
                f"/bin/busybox echo P328-NONCE {P328_RUN_ID}".encode("ascii"),
            )
        ],
        "caller_selected_command": True,
        "interactive_pty": False,
        "raw_rx_forwarded_before_classification": True,
        "authenticated": True,
        "authentication_required": True,
        "auth_algorithm": P328_AUTH_EXEC_AUTH_ALGORITHM,
        "per_session_random_nonce": True,
        "auth_tag_size": P328_AUTH_EXEC_AUTH_TAG_SIZE,
        "auth_key_schema": P328_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key": key_identity,
        "auth_key_path_published": False,
        "host_only": True,
        "device_contact": False,
    }
    if any(
        not _strict_equal(observer_adapter.get(key), value)
        for key, value in expected_observer_adapter.items()
    ):
        raise EvidenceError("P3.28 authenticated observer contract differs")
    return {
        "schema": "device_action_f1_p328_stock_offline_contract_v1",
        "decoder": p328_stock_adapter.DECODER_ID,
        "policy_id": p328_stock_adapter.POLICY_ID,
        "profile": p328_stock_adapter.PROFILE,
        "run_id": P328_RUN_ID,
        "terminal_stage": p328_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p328_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.28 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p328_authenticated_observer_source": _binary_identity(
            {key: observer_source[key] for key in ("size", "sha256")},
            "P3.28 authenticated observer source identity",
        ),
        "p328_authenticated_runtime_source": _binary_identity(
            {key: runtime_source[key] for key in ("size", "sha256")},
            "P3.28 authenticated runtime source identity",
        ),
        "p328_artifact_identity_source": _binary_identity(
            {key: artifact_source[key] for key in ("size", "sha256")},
            "P3.28 artifact identity source identity",
        ),
        "p328_auth_key": dict(key_identity),
        "p328_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p328_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P328_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p328_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "verified": True,
    }


def _verify_p330_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify P3.30's fresh diagnostic identity without promoting diagnostics."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P330_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.30 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.30 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.30 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.30 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.30 candidate-static bytes are not canonical")
    candidate_static = _validate_p330_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.30 candidate package is incomplete")
    ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.30 candidate AP",
    )
    member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.30 AP member"),
    }
    if (
        ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != member
        or candidate_static.get("run_id") != P330_RUN_ID
        or candidate_static.get("predecessor_run_id") != P329_RUN_ID
    ):
        raise EvidenceError("P3.30 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    run_manifest = _json(payloads["run_manifest"], "P3.30 run manifest")
    expected_manifest = {
        "schema": P330_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p330_stock_adapter.PROFILE,
        "run_id": P330_RUN_ID,
        "decoder": p330_stock_adapter.DECODER_ID,
        "policy_id": p330_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p330_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p330_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p330_stock_adapter.TERMINAL_STAGE,
        },
        "observation_contract": {
            "accepted_identity": "P330_STOCK_OBSERVER_V4_RETAINED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_result": "NO_PROOF_OBSERVER",
        },
        "candidate_ap": ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p330_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P330_STOCK_OVERLAY_CONTRACT_ID,
    }
    if not _strict_equal(run_manifest, expected_manifest) or payloads[
        "run_manifest"
    ] != _canonical(run_manifest):
        raise EvidenceError("P3.30 run manifest differs")
    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.30 static result")
    expected_static = {
        "schema": P330_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P330_STATIC_RESULT_VERDICT,
        "profile": p330_stock_adapter.PROFILE,
        "run_id": P330_RUN_ID,
        "decoder": p330_stock_adapter.DECODER_ID,
        "policy_id": p330_stock_adapter.POLICY_ID,
        "source_contract_id": p330_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P330_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "busybox": candidate["busybox"],
                "latch": P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if not _strict_equal(static_result, expected_static) or payloads[
        "static_check"
    ] != _canonical(static_result):
        raise EvidenceError("P3.30 static result differs")
    key_identity = _binary_identity(
        candidate_static.get("artifact_identity", {}).get("auth_key"),
        "P3.30 public auth key identity",
    )
    if key_identity != P330_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.30 public auth key identity differs")
    artifact_source = _artifact(
        candidate_static.get("source_closure", {}).get("p328_artifact_identity"),
        "P3.30 artifact identity source",
        maximum=2 * 1024 * 1024,
    )
    observer_adapter = candidate_static.get("observer_adapter")
    if (
        not isinstance(observer_adapter, dict)
        or observer_adapter.get("schema") != "s22plus_fyg8_p330_auth_acm_session_v1"
        or observer_adapter.get("contract_id")
        != P330_AUTH_EXEC_OBSERVER_CONTRACT_ID
        or observer_adapter.get("wire_magic") != "S328"
        or observer_adapter.get("preauth_diagnostic_frame")
        != P330_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE
        or observer_adapter.get("diagnostic_stages") != [1, 2]
        or observer_adapter.get("rng_eagain_retry_limit")
        != P330_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT
        or observer_adapter.get("diagnostics_non_authoritative") is not True
        or observer_adapter.get("eagain_only_retry") is not True
    ):
        raise EvidenceError("P3.30 observer adapter differs")
    runtime_repair = candidate_static.get("runtime_repair")
    if (
        not isinstance(runtime_repair, dict)
        or runtime_repair.get("contract_id") != P330_AUTH_EXEC_RUNTIME_CONTRACT_ID
        or runtime_repair.get("run_id_hex") != P330_RUN_ID
        or runtime_repair.get("preauth_diagnostic_frame")
        != P330_AUTH_EXEC_DIAGNOSTIC_FRAME_TYPE
        or runtime_repair.get("rng_eagain_retry_limit")
        != P330_AUTH_EXEC_RNG_EAGAIN_RETRY_LIMIT
        or runtime_repair.get("diagnostics_non_authoritative") is not True
    ):
        raise EvidenceError("P3.30 runtime diagnostic binding differs")
    source_contract = _selected_contract(
        p330_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        p330_stock_adapter.PROFILE,
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.30 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get(
        "sources"
    )
    if (
        not isinstance(lineage_sources, dict)
        or set(lineage_sources) != p330_stock_adapter.SOURCE_KEYS
    ):
        raise EvidenceError("P3.30 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p330_stock_offline_contract_v1",
        "decoder": p330_stock_adapter.DECODER_ID,
        "policy_id": p330_stock_adapter.POLICY_ID,
        "profile": p330_stock_adapter.PROFILE,
        "run_id": P330_RUN_ID,
        "terminal_stage": p330_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p330_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.30 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p330_authenticated_observer_source": _binary_identity(
            {key: observer_adapter["source"][key] for key in ("size", "sha256")},
            "P3.30 observer source",
        ),
        "p330_authenticated_runtime_source": _binary_identity(
            {
                key: observer_adapter["runtime_source"][key]
                for key in ("size", "sha256")
            },
            "P3.30 runtime source",
        ),
        "p330_artifact_identity_source": _binary_identity(
            {key: artifact_source[key] for key in ("size", "sha256")},
            "P3.30 artifact source identity",
        ),
        "p330_auth_key": dict(key_identity),
        "p330_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p330_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P330_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p330_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "udev_guard_settle_bounded": True,
        "preauth_diagnostics_bounded": True,
        "diagnostics_non_authoritative": True,
        "verified": True,
    }


def _verify_p331_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Consume a complete P3.31 package without manufacturing build hashes."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P331_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.31 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.31 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.31 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.31 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.31 candidate-static bytes are not canonical")
    candidate_static = _validate_p331_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.31 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.31 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.31 AP boot member"),
    }
    if (
        candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate_static.get("run_id") != P331_RUN_ID
        or candidate_static.get("predecessor_run_id") != P331_PREDECESSOR_RUN_ID
    ):
        raise EvidenceError("P3.31 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.31 run manifest")
    records = {
        "long_family_hex": p331_stock_adapter.LONG_FAMILY.hex(),
        "unsat_family_hex": p331_stock_adapter.UNSAT_FAMILY.hex(),
        "terminal_stage": p331_stock_adapter.TERMINAL_STAGE,
    }
    expected_manifest = {
        "schema": P331_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p331_stock_adapter.PROFILE,
        "run_id": P331_RUN_ID,
        "decoder": p331_stock_adapter.DECODER_ID,
        "policy_id": p331_stock_adapter.POLICY_ID,
        "records": records,
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p331_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P331_STOCK_OVERLAY_CONTRACT_ID,
    }
    if (
        not isinstance(run_manifest.get("observation_contract"), dict)
        or run_manifest["observation_contract"].get("accepted_identity")
        != "P331_STOCK_OBSERVER_V4_RETAINED"
        or run_manifest["observation_contract"].get("minimum_success_count") != 1
        or run_manifest["observation_contract"].get("clean_baseline_required")
        is not True
        or run_manifest["observation_contract"].get("runtime_values_preflighted")
        is not False
        or run_manifest["observation_contract"].get("complete_is_noncausal")
        is not True
        or run_manifest["observation_contract"].get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or run_manifest["observation_contract"].get("receipt_result")
        != "NO_PROOF_OBSERVER"
    ):
        raise EvidenceError("P3.31 run manifest observation contract differs")
    for key, expected in expected_manifest.items():
        if not _strict_equal(run_manifest.get(key), expected):
            raise EvidenceError("P3.31 run manifest differs from candidate-static")
    if payloads["run_manifest"] != _canonical(run_manifest):
        raise EvidenceError("P3.31 run manifest is not canonical")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.31 static result")
    expected_static_header = {
        "schema": P331_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P331_STATIC_RESULT_VERDICT,
        "profile": p331_stock_adapter.PROFILE,
        "run_id": P331_RUN_ID,
        "decoder": p331_stock_adapter.DECODER_ID,
        "policy_id": p331_stock_adapter.POLICY_ID,
        "source_contract_id": p331_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P331_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    for key, expected in expected_static_header.items():
        if not _strict_equal(static_result.get(key), expected):
            raise EvidenceError("P3.31 static result differs")
    static_candidate = static_result.get("candidate")
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
    }
    if (
        not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
    ):
        raise EvidenceError("P3.31 static candidate projection differs")
    expected_safety = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "odin_transfer": False,
        "flash": False,
        "partition_write": False,
        "live_authorized": False,
        "causal_result_allowed": False,
        "candidate_success": False,
    }
    safety = static_result.get("safety")
    if not isinstance(safety, dict) or any(
        safety.get(key) is not expected for key, expected in expected_safety.items()
    ):
        raise EvidenceError("P3.31 static safety boundary differs")
    if payloads["static_check"] != _canonical(static_result):
        raise EvidenceError("P3.31 static result is not canonical")

    artifact_identity = candidate_static.get("artifact_identity")
    key_identity = _binary_identity(
        artifact_identity.get("auth_key") if isinstance(artifact_identity, dict) else None,
        "P3.31 public auth key identity",
    )
    if (
        not isinstance(artifact_identity, dict)
        or artifact_identity.get("run_id_hex") != P331_RUN_ID
        or artifact_identity.get("predecessor_run_id_rejected")
        != P331_PREDECESSOR_RUN_ID
        or artifact_identity.get("boot_only") is not True
        or key_identity != P331_AUTH_EXEC_AUTH_KEY_IDENTITY
        or artifact_identity.get("auth_key_path_published") is not False
    ):
        raise EvidenceError("P3.31 artifact identity differs")

    source_closure = candidate_static.get("source_closure")
    if not isinstance(source_closure, dict):
        raise EvidenceError("P3.31 source closure is missing")
    artifact_source = _artifact(
        source_closure.get("p331_artifact_identity"),
        "P3.31 artifact identity source",
        maximum=2 * 1024 * 1024,
    )
    expected_paths = {
        "p331_artifact_identity": (
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p331_artifact_identity.py"
        ),
        "p331_authenticated_acm_observer": (
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p331_resident_acm_observer.py"
        ),
        "p331_resident_exec_runtime": (
            "workspace/public/src/scripts/revalidation/"
            "s22plus_fyg8_p331_resident_exec_runtime.py"
        ),
    }
    if artifact_source["path"] != expected_paths["p331_artifact_identity"]:
        raise EvidenceError("P3.31 artifact identity source path differs")
    observer_adapter = candidate_static.get("observer_adapter")
    if not isinstance(observer_adapter, dict):
        raise EvidenceError("P3.31 resident observer metadata is missing")
    observer_source = _artifact(
        observer_adapter.get("source"),
        "P3.31 resident observer source",
        maximum=2 * 1024 * 1024,
    )
    runtime_source = _artifact(
        observer_adapter.get("runtime_source"),
        "P3.31 resident runtime source",
        maximum=2 * 1024 * 1024,
    )
    if (
        observer_source["path"] != expected_paths["p331_authenticated_acm_observer"]
        or runtime_source["path"] != expected_paths["p331_resident_exec_runtime"]
    ):
        raise EvidenceError("P3.31 resident source path differs")
    expected_observer = {
        "schema": p331_resident_acm_observer.SCHEMA,
        "contract_id": P331_AUTH_EXEC_OBSERVER_CONTRACT_ID,
        "wire_magic": "S328",
        "frame_header_size": P331_AUTH_EXEC_FRAME_HEADER_SIZE,
        "commands": [
            {
                "size": len(P331_AUTH_EXEC_HEARTBEAT_COMMAND),
                "sha256": hashlib.sha256(P331_AUTH_EXEC_HEARTBEAT_COMMAND).hexdigest(),
            }
        ],
        "proof_command_count": P331_AUTH_EXEC_COMMAND_COUNT,
        "max_commands": P331_AUTH_EXEC_MAX_COMMANDS,
        "caller_selected_command": False,
        "command_timeout_sec": P331_AUTH_EXEC_COMMAND_TIMEOUT_SEC,
        "max_output_bytes": P331_AUTH_EXEC_MAX_OUTPUT_BYTES,
        "auth_algorithm": P331_AUTH_EXEC_AUTH_ALGORITHM,
        "auth_tag_size": P331_AUTH_EXEC_AUTH_TAG_SIZE,
        "auth_key_schema": P331_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key": key_identity,
        "auth_key_path_published": False,
        "per_session_random_nonce": True,
        "fixed_heartbeat_only": True,
        "session_cap": P331_AUTH_EXEC_SESSION_CAP,
        "reconnect_cap": P331_AUTH_EXEC_RECONNECT_CAP,
        "host_only": True,
        "device_contact": False,
        "raw_rx_forwarded_before_classification": True,
        "interactive_pty": False,
    }
    if any(
        not _strict_equal(observer_adapter.get(key), expected)
        for key, expected in expected_observer.items()
    ):
        raise EvidenceError("P3.31 resident observer contract differs")
    runtime_repair = candidate_static.get("runtime_repair")
    if (
        not isinstance(runtime_repair, dict)
        or runtime_repair.get("contract_id") != P331_AUTH_EXEC_RUNTIME_CONTRACT_ID
        or runtime_repair.get("run_id_hex") != P331_RUN_ID
        or runtime_repair.get("command_policy") != "fixed_heartbeat_status_v1"
        or runtime_repair.get("caller_selected_command") is not False
        or runtime_repair.get("session_cap") != P331_AUTH_EXEC_SESSION_CAP
        or runtime_repair.get("reconnect_cap") != P331_AUTH_EXEC_RECONNECT_CAP
        or runtime_repair.get("banner_scope") != "resident_loop_per_session"
        or runtime_repair.get("auth_key_path_published") is not False
    ):
        raise EvidenceError("P3.31 resident runtime binding differs")

    source_contract = _selected_contract(
        p331_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        p331_stock_adapter.PROFILE,
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.31 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get(
        "sources"
    )
    if (
        not isinstance(lineage_sources, dict)
        or set(lineage_sources) != p331_stock_adapter.SOURCE_KEYS
    ):
        raise EvidenceError("P3.31 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p331_stock_offline_contract_v1",
        "decoder": p331_stock_adapter.DECODER_ID,
        "policy_id": p331_stock_adapter.POLICY_ID,
        "profile": p331_stock_adapter.PROFILE,
        "run_id": P331_RUN_ID,
        "terminal_stage": p331_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p331_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.31 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p331_resident_observer_source": {
            key: observer_source[key] for key in ("size", "sha256")
        },
        "p331_resident_runtime_source": {
            key: runtime_source[key] for key in ("size", "sha256")
        },
        "p331_artifact_identity_source": {
            key: artifact_source[key] for key in ("size", "sha256")
        },
        "p331_authenticated_observer_source": {
            key: observer_source[key] for key in ("size", "sha256")
        },
        "p331_authenticated_runtime_source": {
            key: runtime_source[key] for key in ("size", "sha256")
        },
        "p331_auth_key": dict(key_identity),
        "p331_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p331_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P331_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p331_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "udev_guard_settle_bounded": True,
        "preauth_diagnostics_bounded": True,
        "diagnostics_non_authoritative": True,
        "resident_sessions_bounded": True,
        "resident_reconnect_bounded": True,
        "fixed_heartbeat_only": True,
        "verified": True,
    }


def _verify_p332_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the fresh P3.32 same-FD logical-session package."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P332_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.32 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.32 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.32 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.32 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.32 candidate-static bytes are not canonical")
    candidate_static = _validate_p332_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.32 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.32 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.32 AP boot member"),
    }
    if (
        candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate_static.get("run_id") != P332_RUN_ID
        or candidate_static.get("predecessor_run_id") != P332_PREDECESSOR_RUN_ID
    ):
        raise EvidenceError("P3.32 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.32 run manifest")
    expected_manifest = {
        "schema": P332_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p332_stock_adapter.PROFILE,
        "run_id": P332_RUN_ID,
        "decoder": p332_stock_adapter.DECODER_ID,
        "policy_id": p332_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p332_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p332_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p332_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p332_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P332_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P332_STOCK_OBSERVER_V4_RETAINED"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
    ):
        raise EvidenceError("P3.32 run manifest observation contract differs")
    if any(
        not _strict_equal(run_manifest.get(key), expected)
        for key, expected in expected_manifest.items()
    ) or payloads["run_manifest"] != _canonical(run_manifest):
        raise EvidenceError("P3.32 run manifest differs from candidate-static")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.32 static result")
    expected_static_header = {
        "schema": P332_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P332_STATIC_RESULT_VERDICT,
        "profile": p332_stock_adapter.PROFILE,
        "run_id": P332_RUN_ID,
        "decoder": p332_stock_adapter.DECODER_ID,
        "policy_id": p332_stock_adapter.POLICY_ID,
        "source_contract_id": p332_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P332_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    if any(
        not _strict_equal(static_result.get(key), expected)
        for key, expected in expected_static_header.items()
    ):
        raise EvidenceError("P3.32 static result differs")
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
    }
    static_candidate = static_result.get("candidate")
    if (
        not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
    ):
        raise EvidenceError("P3.32 static candidate projection differs")
    safety = static_result.get("safety")
    expected_safety = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "odin_transfer": False,
        "flash": False,
        "partition_write": False,
        "live_authorized": False,
        "causal_result_allowed": False,
        "candidate_success": False,
    }
    if (
        not isinstance(safety, dict)
        or any(safety.get(key) is not expected for key, expected in expected_safety.items())
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.32 static safety or canonical form differs")

    artifact_identity = candidate_static.get("artifact_identity")
    key_identity = _binary_identity(
        artifact_identity.get("auth_key")
        if isinstance(artifact_identity, dict)
        else None,
        "P3.32 public auth key identity",
    )
    if (
        not isinstance(artifact_identity, dict)
        or artifact_identity.get("run_id_hex") != P332_RUN_ID
        or artifact_identity.get("predecessor_run_id_rejected")
        != P332_PREDECESSOR_RUN_ID
        or artifact_identity.get("boot_only") is not True
        or key_identity != P332_AUTH_EXEC_AUTH_KEY_IDENTITY
        or artifact_identity.get("auth_key_path_published") is not False
    ):
        raise EvidenceError("P3.32 artifact identity differs")

    source_closure = candidate_static.get("source_closure")
    observer_adapter = candidate_static.get("observer_adapter")
    if not isinstance(source_closure, dict) or not isinstance(observer_adapter, dict):
        raise EvidenceError("P3.32 source closure is incomplete")
    artifact_source = _artifact(
        source_closure.get("p332_artifact_identity"),
        "P3.32 artifact identity source",
        maximum=2 * 1024 * 1024,
    )
    observer_source = _artifact(
        observer_adapter.get("source"),
        "P3.32 logical resident observer source",
        maximum=2 * 1024 * 1024,
    )
    runtime_source = _artifact(
        observer_adapter.get("runtime_source"),
        "P3.32 logical resident runtime source",
        maximum=2 * 1024 * 1024,
    )
    expected_paths = {
        "artifact": "workspace/public/src/scripts/revalidation/s22plus_fyg8_p332_artifact_identity.py",
        "observer": "workspace/public/src/scripts/revalidation/s22plus_fyg8_p332_logical_resident_acm_observer.py",
        "runtime": "workspace/public/src/scripts/revalidation/s22plus_fyg8_p332_logical_resident_exec_runtime.py",
    }
    if (
        artifact_source["path"] != expected_paths["artifact"]
        or observer_source["path"] != expected_paths["observer"]
        or runtime_source["path"] != expected_paths["runtime"]
    ):
        raise EvidenceError("P3.32 execution source path differs")
    expected_observer = {
        "schema": p332_logical_resident_acm_observer.SCHEMA,
        "contract_id": P332_AUTH_EXEC_OBSERVER_CONTRACT_ID,
        "wire_magic": "S328",
        "frame_header_size": P332_AUTH_EXEC_FRAME_HEADER_SIZE,
        "commands": [
            {
                "size": len(command),
                "sha256": hashlib.sha256(command).hexdigest(),
            }
            for command in p332_logical_resident_exec_runtime.DEFAULT_COMMANDS
        ],
        "proof_command_count": P332_AUTH_EXEC_COMMAND_COUNT,
        "max_commands": P332_AUTH_EXEC_MAX_COMMANDS,
        "caller_selected_command": False,
        "command_timeout_sec": P332_AUTH_EXEC_COMMAND_TIMEOUT_SEC,
        "max_output_bytes": P332_AUTH_EXEC_MAX_OUTPUT_BYTES,
        "auth_algorithm": P332_AUTH_EXEC_AUTH_ALGORITHM,
        "auth_tag_size": P332_AUTH_EXEC_AUTH_TAG_SIZE,
        "auth_key_schema": P332_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key": key_identity,
        "auth_key_path_published": False,
        "per_session_random_nonce": True,
        "fixed_heartbeat_only": False,
        "fixed_p330_commands": True,
        "session_cap": P332_AUTH_EXEC_SESSION_CAP,
        "reconnect_cap": 0,
        "host_only": True,
        "device_contact": False,
        "raw_rx_forwarded_before_classification": True,
        "interactive_pty": False,
        "same_tty_fd": True,
        "host_tty_close_reopen": False,
        "transport_reconnect": False,
    }
    if any(
        not _strict_equal(observer_adapter.get(key), expected)
        for key, expected in expected_observer.items()
    ):
        raise EvidenceError("P3.32 logical resident observer contract differs")
    runtime_repair = candidate_static.get("runtime_repair")
    if (
        not isinstance(runtime_repair, dict)
        or runtime_repair.get("contract_id") != P332_AUTH_EXEC_RUNTIME_CONTRACT_ID
        or runtime_repair.get("run_id_hex") != P332_RUN_ID
        or runtime_repair.get("command_policy") != "fixed_p330_commands_v1"
        or runtime_repair.get("caller_selected_command") is not False
        or runtime_repair.get("session_count") != P332_AUTH_EXEC_SESSION_CAP
        or runtime_repair.get("reconnect_count") != 0
        or runtime_repair.get("same_tty_fd") is not True
        or runtime_repair.get("physical_reopen_count") != 0
    ):
        raise EvidenceError("P3.32 logical resident runtime binding differs")

    source_contract = _selected_contract(
        p332_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        p332_stock_adapter.PROFILE,
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.32 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get(
        "sources"
    )
    if (
        not isinstance(lineage_sources, dict)
        or set(lineage_sources) != p332_stock_adapter.SOURCE_KEYS
    ):
        raise EvidenceError("P3.32 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p332_stock_offline_contract_v1",
        "decoder": p332_stock_adapter.DECODER_ID,
        "policy_id": p332_stock_adapter.POLICY_ID,
        "profile": p332_stock_adapter.PROFILE,
        "run_id": P332_RUN_ID,
        "terminal_stage": p332_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p332_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.32 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p332_logical_resident_observer_source": {
            key: observer_source[key] for key in ("size", "sha256")
        },
        "p332_logical_resident_runtime_source": {
            key: runtime_source[key] for key in ("size", "sha256")
        },
        "p332_artifact_identity_source": {
            key: artifact_source[key] for key in ("size", "sha256")
        },
        "p332_auth_key": dict(key_identity),
        "p332_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p332_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P332_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p332_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "udev_guard_settle_bounded": True,
        "preauth_diagnostics_bounded": True,
        "diagnostics_non_authoritative": True,
        "logical_sessions_bounded": True,
        "same_tty_fd_required": True,
        "physical_reopen_count": 0,
        "fixed_p330_commands": True,
        "verified": True,
    }


def _verify_p337_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the narrow P3.37 first-OPEN diagnostic bundle."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P337_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.37 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.37 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        if actual != {key: pin[key] for key in ("size", "sha256")} or actual != {
            key: receipts[name].get(key) for key in ("size", "sha256")
        }:
            raise EvidenceError(f"P3.37 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.37 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.37 candidate-static bytes are not canonical")
    candidate_static = _validate_p337_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    expected_header = {
        "schema": P337_CANDIDATE_STATIC_SCHEMA,
        "verdict": P337_CANDIDATE_STATIC_VERDICT,
        "target": P337_TARGET,
        "run_id": P337_RUN_ID,
        "predecessor_run_id": P337_PREDECESSOR_RUN_ID,
        "source_contract_id": p337_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P337_STOCK_OVERLAY_CONTRACT_ID,
        "profile": p337_stock_adapter.PROFILE,
    }
    candidate = candidate_static.get("candidate")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.37 candidate AP",
    )
    if (
        any(
            not _strict_equal(candidate_static.get(key), expected)
            for key, expected in expected_header.items()
        )
        or not isinstance(candidate, dict)
        or not isinstance(candidate.get("a"), dict)
        or candidate["a"].get("ap_tar_md5") != candidate_ap_identity
        or candidate.get("b", {}).get("ap_tar_md5") != candidate_ap_identity
        or candidate_ap.get("member")
        != {"name": "boot.img.lz4", **candidate["a"]["boot_img_lz4"]}
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
    ):
        raise EvidenceError("P3.37 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.37 run manifest")
    expected_manifest = {
        "schema": P337_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p337_stock_adapter.PROFILE,
        "run_id": P337_RUN_ID,
        "decoder": p337_stock_adapter.DECODER_ID,
        "policy_id": p337_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p337_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p337_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p337_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p337_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P337_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        any(
            not _strict_equal(run_manifest.get(key), expected)
            for key, expected in expected_manifest.items()
        )
        or not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P337_STOCK_OBSERVER_V4_OPEN_READ_DIAGNOSTIC"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.37 run manifest differs")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.37 static result")
    expected_static_header = {
        "schema": P337_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P337_STATIC_RESULT_VERDICT,
        "profile": p337_stock_adapter.PROFILE,
        "run_id": P337_RUN_ID,
        "decoder": p337_stock_adapter.DECODER_ID,
        "policy_id": p337_stock_adapter.POLICY_ID,
        "source_contract_id": p337_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P337_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    static_candidate = static_result.get("candidate")
    safety = static_result.get("safety")
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
    }
    if (
        any(
            not _strict_equal(static_result.get(key), expected)
            for key, expected in expected_static_header.items()
        )
        or not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
        or not isinstance(safety, dict)
        or any(
            safety.get(key) is not expected
            for key, expected in {
                "host_only": True, "device_contact": False, "device_write": False,
                "odin_invoked": False, "odin_transfer": False, "flash": False,
                "partition_write": False, "live_authorized": False,
                "causal_result_allowed": False, "candidate_success": False,
            }.items()
        )
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.37 static result differs")

    source_closure = candidate_static.get("source_closure")
    if not isinstance(source_closure, dict):
        raise EvidenceError("P3.37 source closure is incomplete")
    source_specs = {
        "artifact": (
            "p337_artifact_identity",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p337_artifact_identity.py",
        ),
        "observer": (
            "p337_open_read_diag_acm_observer",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p337_open_read_diag_acm_observer.py",
        ),
        "runtime": (
            "p337_open_read_diag_runtime",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p337_open_read_diag_runtime.py",
        ),
    }
    source_values: dict[str, dict[str, Any]] = {}
    for name, (key, path) in source_specs.items():
        value = _artifact(
            source_closure.get(key), f"P3.37 {name} source", maximum=2 * 1024 * 1024
        )
        if value["path"] != path:
            raise EvidenceError(f"P3.37 {name} source path differs")
        source_values[name] = value
    key_identity = _binary_identity(
        candidate_static.get("authentication", {}).get("key"),
        "P3.37 public auth key identity",
    )
    if key_identity != P337_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.37 auth key identity differs")
    source_contract = _selected_contract(
        p337_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p337_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.37 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p337_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.37 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p337_stock_offline_contract_v1",
        "decoder": p337_stock_adapter.DECODER_ID,
        "policy_id": p337_stock_adapter.POLICY_ID,
        "profile": p337_stock_adapter.PROFILE,
        "run_id": P337_RUN_ID,
        "terminal_stage": p337_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p337_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.37 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p337_open_read_diag_acm_observer_source": {
            key: source_values["observer"][key] for key in ("size", "sha256")
        },
        "p337_open_read_diag_runtime_source": {
            key: source_values["runtime"][key] for key in ("size", "sha256")
        },
        "p337_artifact_identity_source": {
            key: source_values["artifact"][key] for key in ("size", "sha256")
        },
        "p337_auth_key": dict(key_identity),
        "p337_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p337_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P337_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p337_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "initial_sessions_bounded": True,
        "physical_reopen_count": p337_stock_adapter.INITIAL_RECONNECT_COUNT,
        "per_boot_identity_required": True,
        "first_open_failure_diagnostic": True,
        "later_action_open_before_resync": True,
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "retry_added": False,
        "timeout_changed": False,
        "listener_wait_after_proof": True,
        "resident_lease_schema": p337_stock_adapter.LEASE_SCHEMA,
        "resident_lease_duration_sec": p337_stock_adapter.LEASE_DURATION_SEC,
        "resident_lease_action_cap": p337_stock_adapter.LEASE_ACTION_CAP,
        "verified": True,
    }


def _verify_p338_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the distinct P3.38 static/AP/source closure.

    P338 intentionally reuses the P337 boot-only artifact grammar, but every
    authority-bearing namespace is checked here before any inherited helper is
    considered.  In particular a P337 candidate-static, run manifest, or
    source closure can never be relabelled as P338 by this verifier.
    """
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P338_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.38 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.38 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        actual = {
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if actual != {key: pin[key] for key in ("size", "sha256")} or actual != {
            key: receipts[name].get(key) for key in ("size", "sha256")
        }:
            raise EvidenceError(f"P3.38 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.38 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.38 candidate-static bytes are not canonical")
    candidate_static = _validate_p338_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    expected_header = {
        "schema": P338_CANDIDATE_STATIC_SCHEMA,
        "verdict": P338_CANDIDATE_STATIC_VERDICT,
        "target": P338_TARGET,
        "run_id": P338_RUN_ID,
        "predecessor_run_id": P338_PREDECESSOR_RUN_ID,
        "source_contract_id": p338_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P338_STOCK_OVERLAY_CONTRACT_ID,
        "profile": p338_stock_adapter.PROFILE,
    }
    candidate = candidate_static.get("candidate")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.38 candidate AP",
    )
    if (
        any(
            not _strict_equal(candidate_static.get(key), expected)
            for key, expected in expected_header.items()
        )
        or not isinstance(candidate, dict)
        or not isinstance(candidate.get("a"), dict)
        or candidate["a"].get("ap_tar_md5") != candidate_ap_identity
        or candidate.get("b", {}).get("ap_tar_md5") != candidate_ap_identity
        or candidate_ap.get("member")
        != {"name": "boot.img.lz4", **candidate["a"]["boot_img_lz4"]}
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
    ):
        raise EvidenceError("P3.38 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.38 run manifest")
    expected_manifest = {
        "schema": P338_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p338_stock_adapter.PROFILE,
        "run_id": P338_RUN_ID,
        "decoder": p338_stock_adapter.DECODER_ID,
        "policy_id": p338_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p338_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p338_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p338_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p338_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P338_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        any(
            not _strict_equal(run_manifest.get(key), expected)
            for key, expected in expected_manifest.items()
        )
        or not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P338_STOCK_OBSERVER_V4_OPEN_READ_BRANCH"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.38 run manifest differs")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.38 static result")
    expected_static_header = {
        "schema": P338_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P338_STATIC_RESULT_VERDICT,
        "profile": p338_stock_adapter.PROFILE,
        "run_id": P338_RUN_ID,
        "decoder": p338_stock_adapter.DECODER_ID,
        "policy_id": p338_stock_adapter.POLICY_ID,
        "source_contract_id": p338_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P338_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    static_candidate = static_result.get("candidate")
    safety = static_result.get("safety")
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
    }
    if (
        any(
            not _strict_equal(static_result.get(key), expected)
            for key, expected in expected_static_header.items()
        )
        or not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
        or not isinstance(safety, dict)
        or any(
            safety.get(key) is not expected
            for key, expected in {
                "host_only": True, "device_contact": False, "device_write": False,
                "odin_invoked": False, "odin_transfer": False, "flash": False,
                "partition_write": False, "live_authorized": False,
                "causal_result_allowed": False, "candidate_success": False,
            }.items()
        )
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.38 static result differs")

    source_closure = candidate_static.get("source_closure")
    if not isinstance(source_closure, dict):
        raise EvidenceError("P3.38 source closure is incomplete")
    source_specs = {
        "artifact": (
            "p338_artifact_identity",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p338_artifact_identity.py",
        ),
        "observer": (
            "p338_open_read_branch_acm_observer",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p338_open_read_branch_acm_observer.py",
        ),
        "runtime": (
            "p338_open_read_branch_runtime",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p338_open_read_branch_runtime.py",
        ),
    }
    source_values: dict[str, dict[str, Any]] = {}
    for name, (key, path) in source_specs.items():
        value = _artifact(
            source_closure.get(key), f"P3.38 {name} source", maximum=2 * 1024 * 1024
        )
        if value["path"] != path:
            raise EvidenceError(f"P3.38 {name} source path differs")
        source_values[name] = value
    key_identity = _binary_identity(
        candidate_static.get("authentication", {}).get("key"),
        "P3.38 public auth key identity",
    )
    if key_identity != P338_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.38 auth key identity differs")
    source_contract = _selected_contract(
        p338_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p338_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.38 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p338_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.38 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p338_stock_offline_contract_v1",
        "decoder": p338_stock_adapter.DECODER_ID,
        "policy_id": p338_stock_adapter.POLICY_ID,
        "profile": p338_stock_adapter.PROFILE,
        "run_id": P338_RUN_ID,
        "terminal_stage": p338_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p338_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.38 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p338_open_read_branch_acm_observer_source": {
            key: source_values["observer"][key] for key in ("size", "sha256")
        },
        "p338_open_read_branch_runtime_source": {
            key: source_values["runtime"][key] for key in ("size", "sha256")
        },
        "p338_artifact_identity_source": {
            key: source_values["artifact"][key] for key in ("size", "sha256")
        },
        "p338_auth_key": dict(key_identity),
        "p338_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p338_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P338_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p338_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "initial_sessions_bounded": True,
        "physical_reopen_count": p338_stock_adapter.INITIAL_RECONNECT_COUNT,
        "per_boot_identity_required": True,
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "open_read_branch_ordinals": dict(P338_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
        "open_read_branch_count": P338_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
        "original_errno_returned_unchanged": True,
        "later_action_open_before_resync": True,
        "retry_added": False,
        "timeout_changed": False,
        "listener_wait_after_proof": True,
        "resident_lease_schema": p338_stock_adapter.LEASE_SCHEMA,
        "resident_lease_duration_sec": p338_stock_adapter.LEASE_DURATION_SEC,
        "resident_lease_action_cap": p338_stock_adapter.LEASE_ACTION_CAP,
        "verified": True,
    }


def _verify_p339_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the distinct P3.39 static/AP/source closure.

    P339 intentionally reuses the P338 boot-only artifact grammar, but every
    authority-bearing namespace is checked here before any inherited helper is
    considered.  In particular a P338 candidate-static, run manifest, or
    source closure can never be relabelled as P339 by this verifier.
    """
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P339_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.39 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.39 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        actual = {
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if actual != {key: pin[key] for key in ("size", "sha256")} or actual != {
            key: receipts[name].get(key) for key in ("size", "sha256")
        }:
            raise EvidenceError(f"P3.39 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.39 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.39 candidate-static bytes are not canonical")
    candidate_static = _validate_p339_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    expected_header = {
        "schema": P339_CANDIDATE_STATIC_SCHEMA,
        "verdict": P339_CANDIDATE_STATIC_VERDICT,
        "target": P339_TARGET,
        "run_id": P339_RUN_ID,
        "predecessor_run_id": P339_PREDECESSOR_RUN_ID,
        "source_contract_id": p339_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P339_STOCK_OVERLAY_CONTRACT_ID,
        "profile": p339_stock_adapter.PROFILE,
    }
    candidate = candidate_static.get("candidate")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.39 candidate AP",
    )
    if (
        any(
            not _strict_equal(candidate_static.get(key), expected)
            for key, expected in expected_header.items()
        )
        or not isinstance(candidate, dict)
        or not isinstance(candidate.get("a"), dict)
        or candidate["a"].get("ap_tar_md5") != candidate_ap_identity
        or candidate.get("b", {}).get("ap_tar_md5") != candidate_ap_identity
        or candidate_ap.get("member")
        != {"name": "boot.img.lz4", **candidate["a"]["boot_img_lz4"]}
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
    ):
        raise EvidenceError("P3.39 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.39 run manifest")
    expected_manifest = {
        "schema": P339_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p339_stock_adapter.PROFILE,
        "run_id": P339_RUN_ID,
        "decoder": p339_stock_adapter.DECODER_ID,
        "policy_id": p339_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p339_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p339_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p339_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p339_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P339_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        any(
            not _strict_equal(run_manifest.get(key), expected)
            for key, expected in expected_manifest.items()
        )
        or not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P339_STOCK_OBSERVER_V4_OPEN_HEADER_CAPTURE"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.39 run manifest differs")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.39 static result")
    expected_static_header = {
        "schema": P339_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P339_STATIC_RESULT_VERDICT,
        "profile": p339_stock_adapter.PROFILE,
        "run_id": P339_RUN_ID,
        "decoder": p339_stock_adapter.DECODER_ID,
        "policy_id": p339_stock_adapter.POLICY_ID,
        "source_contract_id": p339_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P339_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    static_candidate = static_result.get("candidate")
    safety = static_result.get("safety")
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
    }
    if (
        any(
            not _strict_equal(static_result.get(key), expected)
            for key, expected in expected_static_header.items()
        )
        or not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
        or not isinstance(safety, dict)
        or any(
            safety.get(key) is not expected
            for key, expected in {
                "host_only": True, "device_contact": False, "device_write": False,
                "odin_invoked": False, "odin_transfer": False, "flash": False,
                "partition_write": False, "live_authorized": False,
                "causal_result_allowed": False, "candidate_success": False,
            }.items()
        )
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.39 static result differs")

    source_closure = candidate_static.get("source_closure")
    if not isinstance(source_closure, dict):
        raise EvidenceError("P3.39 source closure is incomplete")
    source_specs = {
        "artifact": (
            "p339_artifact_identity",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p339_artifact_identity.py",
        ),
        "observer": (
            "p339_open_read_branch_acm_observer",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p339_open_read_branch_acm_observer.py",
        ),
        "runtime": (
            "p339_open_read_branch_runtime",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p339_open_read_branch_runtime.py",
        ),
    }
    source_values: dict[str, dict[str, Any]] = {}
    for name, (key, path) in source_specs.items():
        value = _artifact(
            source_closure.get(key), f"P3.39 {name} source", maximum=2 * 1024 * 1024
        )
        if value["path"] != path:
            raise EvidenceError(f"P3.39 {name} source path differs")
        source_values[name] = value
    key_identity = _binary_identity(
        candidate_static.get("authentication", {}).get("key"),
        "P3.39 public auth key identity",
    )
    if key_identity != P339_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.39 auth key identity differs")
    source_contract = _selected_contract(
        p339_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p339_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.39 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p339_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.39 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p339_stock_offline_contract_v1",
        "decoder": p339_stock_adapter.DECODER_ID,
        "policy_id": p339_stock_adapter.POLICY_ID,
        "profile": p339_stock_adapter.PROFILE,
        "run_id": P339_RUN_ID,
        "terminal_stage": p339_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p339_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.39 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p339_open_read_branch_acm_observer_source": {
            key: source_values["observer"][key] for key in ("size", "sha256")
        },
        "p339_open_read_branch_runtime_source": {
            key: source_values["runtime"][key] for key in ("size", "sha256")
        },
        "p339_artifact_identity_source": {
            key: source_values["artifact"][key] for key in ("size", "sha256")
        },
        "p339_auth_key": dict(key_identity),
        "p339_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p339_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P339_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p339_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "initial_sessions_bounded": True,
        "physical_reopen_count": p339_stock_adapter.INITIAL_RECONNECT_COUNT,
        "per_boot_identity_required": True,
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "open_read_branch_ordinals": dict(P339_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
        "open_read_branch_count": P339_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
        "open_header_word_stages": list(P339_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
        "open_header_size": P339_AUTH_EXEC_OPEN_HEADER_SIZE,
        "open_header_capture_best_effort": True,
        "original_errno_returned_unchanged": True,
        "later_action_open_before_resync": True,
        "retry_added": False,
        "timeout_changed": False,
        "listener_wait_after_proof": True,
        "resident_lease_schema": p339_stock_adapter.LEASE_SCHEMA,
        "resident_lease_duration_sec": p339_stock_adapter.LEASE_DURATION_SEC,
        "resident_lease_action_cap": p339_stock_adapter.LEASE_ACTION_CAP,
        "verified": True,
    }


def _verify_p340_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the distinct P3.40 identity-only static/AP/source closure."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P340_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.40 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.40 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        actual = {
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if actual != {key: pin[key] for key in ("size", "sha256")} or actual != {
            key: receipts[name].get(key) for key in ("size", "sha256")
        }:
            raise EvidenceError(f"P3.40 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.40 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static):
        raise EvidenceError("P3.40 candidate-static bytes are not canonical")
    candidate_static = _validate_p340_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    expected_header = {
        "schema": P340_CANDIDATE_STATIC_SCHEMA,
        "verdict": P340_CANDIDATE_STATIC_VERDICT,
        "target": P340_TARGET,
        "run_id": P340_RUN_ID,
        "predecessor_run_id": P340_PREDECESSOR_RUN_ID,
        "source_contract_id": p340_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P340_STOCK_OVERLAY_CONTRACT_ID,
        "profile": p340_stock_adapter.PROFILE,
    }
    candidate = candidate_static.get("candidate")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.40 candidate AP",
    )
    if (
        any(
            not _strict_equal(candidate_static.get(key), expected)
            for key, expected in expected_header.items()
        )
        or not isinstance(candidate, dict)
        or not isinstance(candidate.get("a"), dict)
        or candidate["a"].get("ap_tar_md5") != candidate_ap_identity
        or candidate.get("b", {}).get("ap_tar_md5") != candidate_ap_identity
        or candidate_ap.get("member")
        != {"name": "boot.img.lz4", **candidate["a"]["boot_img_lz4"]}
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
    ):
        raise EvidenceError("P3.40 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.40 run manifest")
    expected_manifest = {
        "schema": P340_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p340_stock_adapter.PROFILE,
        "run_id": P340_RUN_ID,
        "decoder": p340_stock_adapter.DECODER_ID,
        "policy_id": p340_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p340_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p340_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p340_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p340_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P340_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        any(
            not _strict_equal(run_manifest.get(key), expected)
            for key, expected in expected_manifest.items()
        )
        or not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P340_STOCK_OBSERVER_V4_OPEN_HEADER_CAPTURE"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.40 run manifest differs")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.40 static result")
    expected_static_header = {
        "schema": P340_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P340_STATIC_RESULT_VERDICT,
        "profile": p340_stock_adapter.PROFILE,
        "run_id": P340_RUN_ID,
        "decoder": p340_stock_adapter.DECODER_ID,
        "policy_id": p340_stock_adapter.POLICY_ID,
        "source_contract_id": p340_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P340_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    static_candidate = static_result.get("candidate")
    safety = static_result.get("safety")
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": {
            key: candidate_static["source_closure"]["latch"][key]
            for key in ("size", "sha256")
        },
    }
    if (
        any(
            not _strict_equal(static_result.get(key), expected)
            for key, expected in expected_static_header.items()
        )
        or not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
        or not isinstance(safety, dict)
        or any(
            safety.get(key) is not expected
            for key, expected in {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "odin_transfer": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
                "causal_result_allowed": False,
                "candidate_success": False,
            }.items()
        )
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.40 static result differs")

    source_closure = candidate_static.get("source_closure")
    expected_source_names = {
        "latch",
        "p340_artifact_identity",
        "p340_open_failure_capture",
        "p340_open_read_branch_acm_observer",
        "p340_open_read_branch_runtime",
        "p340_stock_candidate_build",
        "p340_stock_process_v2_adapter",
        "rollback_ap",
    }
    if not isinstance(source_closure, dict) or set(source_closure) != expected_source_names:
        raise EvidenceError("P3.40 source closure is incomplete")
    source_specs = {
        "artifact": (
            "p340_artifact_identity",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p340_artifact_identity.py",
        ),
        "observer": (
            "p340_open_read_branch_acm_observer",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p340_open_read_branch_acm_observer.py",
        ),
        "runtime": (
            "p340_open_read_branch_runtime",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p340_open_read_branch_runtime.py",
        ),
        "capture": (
            "p340_open_failure_capture",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_open_failure_capture.py",
        ),
        "builder": (
            "p340_stock_candidate_build",
            "workspace/public/src/scripts/analysis/s22plus_fyg8_p340_stock_candidate_build.py",
        ),
        "adapter": (
            "p340_stock_process_v2_adapter",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p340_stock_process_v2_adapter.py",
        ),
    }
    source_values: dict[str, dict[str, Any]] = {}
    for name, (key, path) in source_specs.items():
        value = _artifact(
            source_closure.get(key), f"P3.40 {name} source", maximum=2 * 1024 * 1024
        )
        if value["path"] != path:
            raise EvidenceError(f"P3.40 {name} source path differs")
        source_values[name] = value
    latch = _artifact(
        source_closure["latch"], "P3.40 latch source", maximum=8 * 1024 * 1024
    )
    if {
        key: latch[key] for key in ("size", "sha256")
    } != P319_EXACT_ARTIFACTS["latch"]:
        raise EvidenceError("P3.40 latch source differs")
    rollback = _artifact(
        source_closure["rollback_ap"], "P3.40 rollback source", maximum=64 * 1024 * 1024
    )
    if {
        key: rollback[key] for key in ("size", "sha256")
    } != {
        "size": 23_367_721,
        "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
    }:
        raise EvidenceError("P3.40 rollback source differs")

    key_identity = _binary_identity(
        candidate_static.get("authentication", {}).get("key"),
        "P3.40 public auth key identity",
    )
    if key_identity != P340_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.40 auth key identity differs")
    source_contract = _selected_contract(
        p340_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p340_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.40 parent source receipts are unavailable") from exc
    lineage_sources = (
        candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    )
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p340_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.40 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p340_stock_offline_contract_v1",
        "decoder": p340_stock_adapter.DECODER_ID,
        "policy_id": p340_stock_adapter.POLICY_ID,
        "profile": p340_stock_adapter.PROFILE,
        "run_id": P340_RUN_ID,
        "terminal_stage": p340_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p340_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.40 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p340_open_read_branch_acm_observer_source": {
            key: source_values["observer"][key] for key in ("size", "sha256")
        },
        "p340_open_read_branch_runtime_source": {
            key: source_values["runtime"][key] for key in ("size", "sha256")
        },
        "p340_artifact_identity_source": {
            key: source_values["artifact"][key] for key in ("size", "sha256")
        },
        "p340_open_failure_capture_source": {
            key: source_values["capture"][key] for key in ("size", "sha256")
        },
        "p340_stock_candidate_build_source": {
            key: source_values["builder"][key] for key in ("size", "sha256")
        },
        "p340_stock_process_v2_adapter_source": {
            key: source_values["adapter"][key] for key in ("size", "sha256")
        },
        "p340_latch_source": {
            key: latch[key] for key in ("size", "sha256")
        },
        "p340_rollback_source": {
            key: rollback[key] for key in ("size", "sha256")
        },
        "p340_auth_key": dict(key_identity),
        "p340_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p340_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P340_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p340_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "initial_sessions_bounded": True,
        "physical_reopen_count": p340_stock_adapter.INITIAL_RECONNECT_COUNT,
        "per_boot_identity_required": True,
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "open_read_branch_ordinals": dict(P340_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
        "open_read_branch_count": P340_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
        "open_header_word_stages": list(P340_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
        "open_header_size": P340_AUTH_EXEC_OPEN_HEADER_SIZE,
        "open_header_capture_best_effort": True,
        "initial_failure_suffix_capture": True,
        "maximum_failure_suffix_bytes": 96,
        "original_errno_returned_unchanged": True,
        "later_action_open_before_resync": True,
        "retry_added": False,
        "timeout_changed": False,
        "listener_wait_after_proof": True,
        "resident_lease_schema": p340_stock_adapter.LEASE_SCHEMA,
        "resident_lease_duration_sec": p340_stock_adapter.LEASE_DURATION_SEC,
        "resident_lease_action_cap": p340_stock_adapter.LEASE_ACTION_CAP,
        "verified": True,
    }


def _verify_p341_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the distinct P3.41 host-first OPEN static/AP/source closure."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P341_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.41 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.41 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        actual = {
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if actual != {key: pin[key] for key in ("size", "sha256")} or actual != {
            key: receipts[name].get(key) for key in ("size", "sha256")
        }:
            raise EvidenceError(f"P3.41 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.41 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static):
        raise EvidenceError("P3.41 candidate-static bytes are not canonical")
    candidate_static = _validate_p341_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    expected_header = {
        "schema": P341_CANDIDATE_STATIC_SCHEMA,
        "verdict": P341_CANDIDATE_STATIC_VERDICT,
        "target": P341_TARGET,
        "run_id": P341_RUN_ID,
        "predecessor_run_id": P341_PREDECESSOR_RUN_ID,
        "source_contract_id": p341_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P341_STOCK_OVERLAY_CONTRACT_ID,
        "profile": p341_stock_adapter.PROFILE,
    }
    candidate = candidate_static.get("candidate")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.41 candidate AP",
    )
    if (
        any(
            not _strict_equal(candidate_static.get(key), expected)
            for key, expected in expected_header.items()
        )
        or not isinstance(candidate, dict)
        or not isinstance(candidate.get("a"), dict)
        or candidate["a"].get("ap_tar_md5") != candidate_ap_identity
        or candidate.get("b", {}).get("ap_tar_md5") != candidate_ap_identity
        or candidate_ap.get("member")
        != {"name": "boot.img.lz4", **candidate["a"]["boot_img_lz4"]}
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
    ):
        raise EvidenceError("P3.41 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.41 run manifest")
    expected_manifest = {
        "schema": P341_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p341_stock_adapter.PROFILE,
        "run_id": P341_RUN_ID,
        "decoder": p341_stock_adapter.DECODER_ID,
        "policy_id": p341_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p341_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p341_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p341_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p341_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P341_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        any(
            not _strict_equal(run_manifest.get(key), expected)
            for key, expected in expected_manifest.items()
        )
        or not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P341_STOCK_OBSERVER_V4_OPEN_HEADER_CAPTURE"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
        or observation_contract.get("host_first_open") is not True
        or observation_contract.get("host_open_before_banner") is not True
        or observation_contract.get("device_banner_after_open") is not True
        or observation_contract.get("stage_zero_after_banner") is not True
        or observation_contract.get("open_parsed_after_stage_zero") is not True
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.41 run manifest differs")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.41 static result")
    expected_static_header = {
        "schema": P341_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P341_STATIC_RESULT_VERDICT,
        "profile": p341_stock_adapter.PROFILE,
        "run_id": P341_RUN_ID,
        "decoder": p341_stock_adapter.DECODER_ID,
        "policy_id": p341_stock_adapter.POLICY_ID,
        "source_contract_id": p341_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P341_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    static_candidate = static_result.get("candidate")
    safety = static_result.get("safety")
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": {
            key: candidate_static["source_closure"]["latch"][key]
            for key in ("size", "sha256")
        },
    }
    if (
        any(
            not _strict_equal(static_result.get(key), expected)
            for key, expected in expected_static_header.items()
        )
        or not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
        or not isinstance(safety, dict)
        or any(
            safety.get(key) is not expected
            for key, expected in {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "odin_transfer": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
                "causal_result_allowed": False,
                "candidate_success": False,
            }.items()
        )
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.41 static result differs")

    source_closure = candidate_static.get("source_closure")
    expected_source_names = {
        "latch",
        "p341_artifact_identity",
        "p341_host_first_open",
        "p341_open_failure_capture",
        "p341_open_read_branch_acm_observer",
        "p341_open_read_branch_runtime",
        "p341_stock_candidate_build",
        "p341_stock_process_v2_adapter",
        "rollback_ap",
    }
    if not isinstance(source_closure, dict) or set(source_closure) != expected_source_names:
        raise EvidenceError("P3.41 source closure is incomplete")
    source_specs = {
        "artifact": (
            "p341_artifact_identity",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p341_artifact_identity.py",
        ),
        "host_first": (
            "p341_host_first_open",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_host_first_open.py",
        ),
        "observer": (
            "p341_open_read_branch_acm_observer",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p341_open_read_branch_acm_observer.py",
        ),
        "runtime": (
            "p341_open_read_branch_runtime",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p341_open_read_branch_runtime.py",
        ),
        "capture": (
            "p341_open_failure_capture",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_open_failure_capture.py",
        ),
        "builder": (
            "p341_stock_candidate_build",
            "workspace/public/src/scripts/analysis/s22plus_fyg8_p341_stock_candidate_build.py",
        ),
        "adapter": (
            "p341_stock_process_v2_adapter",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p341_stock_process_v2_adapter.py",
        ),
    }
    source_values: dict[str, dict[str, Any]] = {}
    for name, (key, path) in source_specs.items():
        value = _artifact(
            source_closure.get(key), f"P3.41 {name} source", maximum=2 * 1024 * 1024
        )
        if value["path"] != path:
            raise EvidenceError(f"P3.41 {name} source path differs")
        source_values[name] = value
    if source_values["host_first"] != {
        "path": source_specs["host_first"][1],
        **p341_open_read_branch_runtime.HOST_FIRST_SOURCE_IDENTITY,
    }:
        raise EvidenceError("P3.41 host-first source identity differs")
    latch = _artifact(
        source_closure["latch"], "P3.41 latch source", maximum=8 * 1024 * 1024
    )
    if {key: latch[key] for key in ("size", "sha256")} != P319_EXACT_ARTIFACTS["latch"]:
        raise EvidenceError("P3.41 latch source differs")
    rollback = _artifact(
        source_closure["rollback_ap"], "P3.41 rollback source", maximum=64 * 1024 * 1024
    )
    if {key: rollback[key] for key in ("size", "sha256")} != {
        "size": 23_367_721,
        "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
    }:
        raise EvidenceError("P3.41 rollback source differs")

    key_identity = _binary_identity(
        candidate_static.get("authentication", {}).get("key"),
        "P3.41 public auth key identity",
    )
    if key_identity != P341_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.41 auth key identity differs")
    source_contract = _selected_contract(
        p341_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p341_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.41 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p341_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.41 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p341_stock_offline_contract_v1",
        "decoder": p341_stock_adapter.DECODER_ID,
        "policy_id": p341_stock_adapter.POLICY_ID,
        "profile": p341_stock_adapter.PROFILE,
        "run_id": P341_RUN_ID,
        "terminal_stage": p341_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p341_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.41 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p341_open_read_branch_acm_observer_source": {
            key: source_values["observer"][key] for key in ("size", "sha256")
        },
        "p341_open_read_branch_runtime_source": {
            key: source_values["runtime"][key] for key in ("size", "sha256")
        },
        "p341_artifact_identity_source": {
            key: source_values["artifact"][key] for key in ("size", "sha256")
        },
        "p341_host_first_open_source": {
            key: source_values["host_first"][key] for key in ("size", "sha256")
        },
        "p341_open_failure_capture_source": {
            key: source_values["capture"][key] for key in ("size", "sha256")
        },
        "p341_stock_candidate_build_source": {
            key: source_values["builder"][key] for key in ("size", "sha256")
        },
        "p341_stock_process_v2_adapter_source": {
            key: source_values["adapter"][key] for key in ("size", "sha256")
        },
        "p341_latch_source": {
            key: latch[key] for key in ("size", "sha256")
        },
        "p341_rollback_source": {
            key: rollback[key] for key in ("size", "sha256")
        },
        "p341_auth_key": dict(key_identity),
        "p341_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p341_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P341_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p341_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "initial_sessions_bounded": True,
        "physical_reopen_count": p341_stock_adapter.INITIAL_RECONNECT_COUNT,
        "per_boot_identity_required": True,
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "open_read_branch_ordinals": dict(P341_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
        "open_read_branch_count": P341_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
        "open_header_word_stages": list(P341_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
        "open_header_size": P341_AUTH_EXEC_OPEN_HEADER_SIZE,
        "open_header_capture_best_effort": True,
        "initial_failure_suffix_capture": True,
        "maximum_failure_suffix_bytes": 96,
        "host_first_open": True,
        "host_open_before_banner": True,
        "device_banner_after_open": True,
        "stage_zero_after_banner": True,
        "open_parsed_after_stage_zero": True,
        "no_unsolicited_device_tx": True,
        "silent_no_peer_no_proof": True,
        "consumed_partial_open_no_replay": True,
        "original_errno_returned_unchanged": True,
        "later_action_open_before_resync": True,
        "retry_added": False,
        "timeout_changed": False,
        "listener_wait_after_proof": True,
        "resident_lease_schema": p341_stock_adapter.LEASE_SCHEMA,
        "resident_lease_duration_sec": p341_stock_adapter.LEASE_DURATION_SEC,
        "resident_lease_action_cap": p341_stock_adapter.LEASE_ACTION_CAP,
        "verified": True,
    }


def _verify_p342_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the P3.42 static/AP/source closure without a P341 projection."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P342_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.42 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.42 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        pin = item["contract"][name]
        if actual != {key: pin[key] for key in ("size", "sha256")} or actual != {
            key: receipts[name].get(key) for key in ("size", "sha256")
        }:
            raise EvidenceError(f"P3.42 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.42 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static):
        raise EvidenceError("P3.42 candidate-static bytes are not canonical")
    candidate_static = _validate_p342_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    expected_header = {
        "schema": P342_CANDIDATE_STATIC_SCHEMA,
        "verdict": P342_CANDIDATE_STATIC_VERDICT,
        "target": P342_TARGET,
        "run_id": P342_RUN_ID,
        "predecessor_run_id": P342_PREDECESSOR_RUN_ID,
        "source_contract_id": p342_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P342_STOCK_OVERLAY_CONTRACT_ID,
        "profile": p342_stock_adapter.PROFILE,
    }
    candidate = candidate_static.get("candidate")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.42 candidate AP",
    )
    if (
        any(
            not _strict_equal(candidate_static.get(key), expected)
            for key, expected in expected_header.items()
        )
        or not isinstance(candidate, dict)
        or not isinstance(candidate.get("a"), dict)
        or candidate["a"].get("ap_tar_md5") != candidate_ap_identity
        or candidate.get("b", {}).get("ap_tar_md5") != candidate_ap_identity
        or candidate_ap.get("member")
        != {"name": "boot.img.lz4", **candidate["a"]["boot_img_lz4"]}
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
    ):
        raise EvidenceError("P3.42 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.42 run manifest")
    expected_manifest = {
        "schema": P342_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p342_stock_adapter.PROFILE,
        "run_id": P342_RUN_ID,
        "decoder": p342_stock_adapter.DECODER_ID,
        "policy_id": p342_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p342_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p342_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p342_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p342_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P342_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        any(
            not _strict_equal(run_manifest.get(key), expected)
            for key, expected in expected_manifest.items()
        )
        or not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P342_STOCK_OBSERVER_V4_IDLE_REUSE"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
        or observation_contract.get("host_first_open") is not True
        or observation_contract.get("host_open_before_banner") is not True
        or observation_contract.get("device_banner_after_open") is not True
        or observation_contract.get("stage_zero_after_banner") is not True
        or observation_contract.get("open_parsed_after_stage_zero") is not True
        or observation_contract.get("same_fd_session_count")
        != P342_SAME_FD_SESSION_COUNT
        or observation_contract.get("idle_seconds")
        != P342_IDLE_REUSE_REQUESTED_SECONDS
        or observation_contract.get("total_session_count") != P342_TOTAL_SESSION_COUNT
        or observation_contract.get("total_command_count") != P342_TOTAL_COMMAND_COUNT
        or observation_contract.get("physical_reopen_count") != 1
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.42 run manifest differs")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.42 static result")
    expected_static_header = {
        "schema": P342_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P342_STATIC_RESULT_VERDICT,
        "profile": p342_stock_adapter.PROFILE,
        "run_id": P342_RUN_ID,
        "decoder": p342_stock_adapter.DECODER_ID,
        "policy_id": p342_stock_adapter.POLICY_ID,
        "source_contract_id": p342_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P342_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    static_candidate = static_result.get("candidate")
    safety = static_result.get("safety")
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": {
            key: candidate_static["source_closure"]["latch"][key]
            for key in ("size", "sha256")
        },
    }
    if (
        any(
            not _strict_equal(static_result.get(key), expected)
            for key, expected in expected_static_header.items()
        )
        or not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
        or not isinstance(safety, dict)
        or any(
            safety.get(key) is not expected
            for key, expected in {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "odin_transfer": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
                "causal_result_allowed": False,
                "candidate_success": False,
            }.items()
        )
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.42 static result differs")

    source_closure = candidate_static.get("source_closure")
    expected_source_names = {
        "latch",
        "p342_artifact_identity",
        "p342_host_first_open",
        "p342_open_failure_capture",
        "p342_open_read_branch_acm_observer",
        "p342_open_read_branch_runtime",
        "p342_idle_reuse_probe",
        "p342_stock_candidate_build",
        "p342_stock_process_v2_adapter",
        "rollback_ap",
    }
    if not isinstance(source_closure, dict) or set(source_closure) != expected_source_names:
        raise EvidenceError("P3.42 source closure is incomplete")
    source_specs = {
        "artifact": (
            "p342_artifact_identity",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p342_artifact_identity.py",
        ),
        "host_first": (
            "p342_host_first_open",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_host_first_open.py",
        ),
        "observer": (
            "p342_open_read_branch_acm_observer",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p342_open_read_branch_acm_observer.py",
        ),
        "runtime": (
            "p342_open_read_branch_runtime",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p342_open_read_branch_runtime.py",
        ),
        "capture": (
            "p342_open_failure_capture",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_open_failure_capture.py",
        ),
        "idle": (
            "p342_idle_reuse_probe",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_idle_reuse_probe.py",
        ),
        "builder": (
            "p342_stock_candidate_build",
            "workspace/public/src/scripts/analysis/s22plus_fyg8_p342_stock_candidate_build.py",
        ),
        "adapter": (
            "p342_stock_process_v2_adapter",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p342_stock_process_v2_adapter.py",
        ),
    }
    source_values: dict[str, dict[str, Any]] = {}
    for name, (key, path) in source_specs.items():
        value = _artifact(
            source_closure.get(key), f"P3.42 {name} source", maximum=2 * 1024 * 1024
        )
        if value["path"] != path:
            raise EvidenceError(f"P3.42 {name} source path differs")
        source_values[name] = value
    if source_values["host_first"] != {
        "path": source_specs["host_first"][1],
        **p342_open_read_branch_runtime.HOST_FIRST_SOURCE_IDENTITY,
    }:
        raise EvidenceError("P3.42 host-first source identity differs")
    latch = _artifact(source_closure["latch"], "P3.42 latch source", maximum=8 * 1024 * 1024)
    if {key: latch[key] for key in ("size", "sha256")} != P319_EXACT_ARTIFACTS["latch"]:
        raise EvidenceError("P3.42 latch source differs")
    rollback = _artifact(
        source_closure["rollback_ap"], "P3.42 rollback source", maximum=64 * 1024 * 1024
    )
    if {key: rollback[key] for key in ("size", "sha256")} != {
        "size": 23_367_721,
        "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
    }:
        raise EvidenceError("P3.42 rollback source differs")

    key_identity = _binary_identity(
        candidate_static.get("authentication", {}).get("key"),
        "P3.42 public auth key identity",
    )
    if key_identity != P342_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.42 auth key identity differs")
    source_contract = _selected_contract(
        p342_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p342_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.42 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p342_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.42 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p342_stock_offline_contract_v1",
        "decoder": p342_stock_adapter.DECODER_ID,
        "policy_id": p342_stock_adapter.POLICY_ID,
        "profile": p342_stock_adapter.PROFILE,
        "run_id": P342_RUN_ID,
        "terminal_stage": p342_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p342_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.42 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p342_open_read_branch_acm_observer_source": {
            key: source_values["observer"][key] for key in ("size", "sha256")
        },
        "p342_open_read_branch_runtime_source": {
            key: source_values["runtime"][key] for key in ("size", "sha256")
        },
        "p342_artifact_identity_source": {
            key: source_values["artifact"][key] for key in ("size", "sha256")
        },
        "p342_host_first_open_source": {
            key: source_values["host_first"][key] for key in ("size", "sha256")
        },
        "p342_open_failure_capture_source": {
            key: source_values["capture"][key] for key in ("size", "sha256")
        },
        "p342_idle_reuse_probe_source": {
            key: source_values["idle"][key] for key in ("size", "sha256")
        },
        "p342_stock_candidate_build_source": {
            key: source_values["builder"][key] for key in ("size", "sha256")
        },
        "p342_stock_process_v2_adapter_source": {
            key: source_values["adapter"][key] for key in ("size", "sha256")
        },
        "p342_latch_source": {key: latch[key] for key in ("size", "sha256")},
        "p342_rollback_source": {
            key: rollback[key] for key in ("size", "sha256")
        },
        "p342_auth_key": dict(key_identity),
        "p342_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p342_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P342_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p342_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "initial_sessions_bounded": True,
        "physical_reopen_count": p342_stock_adapter.INITIAL_RECONNECT_COUNT,
        "same_fd_session_count": P342_SAME_FD_SESSION_COUNT,
        "idle_seconds": P342_IDLE_REUSE_REQUESTED_SECONDS,
        "total_session_count": P342_TOTAL_SESSION_COUNT,
        "total_command_count": P342_TOTAL_COMMAND_COUNT,
        "per_boot_identity_required": True,
        "first_open_failure_diagnostic": True,
        "open_read_diagnostic_stage": 3,
        "open_read_branch_ordinals": dict(P342_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS),
        "open_read_branch_count": P342_AUTH_EXEC_OPEN_READ_BRANCH_COUNT,
        "open_header_word_stages": list(P342_AUTH_EXEC_OPEN_HEADER_WORD_STAGES),
        "open_header_size": P342_AUTH_EXEC_OPEN_HEADER_SIZE,
        "open_header_capture_best_effort": True,
        "initial_failure_suffix_capture": True,
        "maximum_failure_suffix_bytes": 96,
        "host_first_open": True,
        "host_open_before_banner": True,
        "device_banner_after_open": True,
        "stage_zero_after_banner": True,
        "open_parsed_after_stage_zero": True,
        "no_unsolicited_device_tx": True,
        "silent_no_peer_no_proof": True,
        "consumed_partial_open_no_replay": True,
        "original_errno_returned_unchanged": True,
        "retry_added": False,
        "timeout_changed": False,
        "listener_wait_after_proof": True,
        "later_action_lease_active": False,
        "verified": True,
    }


def _verify_p336_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the P3.36 long-idle bundle and its distinct source closure."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P336_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.36 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.36 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        if actual != {key: pin[key] for key in ("size", "sha256")} or actual != {
            key: receipts[name].get(key) for key in ("size", "sha256")
        }:
            raise EvidenceError(f"P3.36 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.36 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.36 candidate-static bytes are not canonical")
    candidate_static = _validate_p336_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    expected_header = {
        "schema": P336_CANDIDATE_STATIC_SCHEMA,
        "verdict": P336_CANDIDATE_STATIC_VERDICT,
        "target": P336_TARGET,
        "run_id": P336_RUN_ID,
        "predecessor_run_id": P336_PREDECESSOR_RUN_ID,
        "source_contract_id": p336_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P336_STOCK_OVERLAY_CONTRACT_ID,
        "profile": p336_stock_adapter.PROFILE,
    }
    candidate = candidate_static.get("candidate")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.36 candidate AP",
    )
    if (
        any(
            not _strict_equal(candidate_static.get(key), expected)
            for key, expected in expected_header.items()
        )
        or not isinstance(candidate, dict)
        or not isinstance(candidate.get("a"), dict)
        or candidate["a"].get("ap_tar_md5") != candidate_ap_identity
        or candidate.get("b", {}).get("ap_tar_md5") != candidate_ap_identity
        or candidate_ap.get("member")
        != {"name": "boot.img.lz4", **candidate["a"]["boot_img_lz4"]}
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
    ):
        raise EvidenceError("P3.36 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.36 run manifest")
    expected_manifest = {
        "schema": P336_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p336_stock_adapter.PROFILE,
        "run_id": P336_RUN_ID,
        "decoder": p336_stock_adapter.DECODER_ID,
        "policy_id": p336_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p336_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p336_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p336_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p336_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P336_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        any(
            not _strict_equal(run_manifest.get(key), expected)
            for key, expected in expected_manifest.items()
        )
        or not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P336_STOCK_OBSERVER_V4_LONG_IDLE"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.36 run manifest differs")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.36 static result")
    expected_static_header = {
        "schema": P336_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P336_STATIC_RESULT_VERDICT,
        "profile": p336_stock_adapter.PROFILE,
        "run_id": P336_RUN_ID,
        "decoder": p336_stock_adapter.DECODER_ID,
        "policy_id": p336_stock_adapter.POLICY_ID,
        "source_contract_id": p336_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P336_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    static_candidate = static_result.get("candidate")
    safety = static_result.get("safety")
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
    }
    if (
        any(
            not _strict_equal(static_result.get(key), expected)
            for key, expected in expected_static_header.items()
        )
        or not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
        or not isinstance(safety, dict)
        or any(
            safety.get(key) is not expected
            for key, expected in {
                "host_only": True, "device_contact": False, "device_write": False,
                "odin_invoked": False, "odin_transfer": False, "flash": False,
                "partition_write": False, "live_authorized": False,
                "causal_result_allowed": False, "candidate_success": False,
            }.items()
        )
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.36 static result differs")

    source_closure = candidate_static.get("source_closure")
    if not isinstance(source_closure, dict):
        raise EvidenceError("P3.36 source closure is incomplete")
    source_specs = {
        "artifact": (
            "p336_artifact_identity",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p336_artifact_identity.py",
        ),
        "observer": (
            "p336_long_idle_acm_observer",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p336_long_idle_acm_observer.py",
        ),
        "runtime": (
            "p336_long_idle_runtime",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p336_long_idle_runtime.py",
        ),
        "action": (
            "p336_long_idle_action",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p336_long_idle_action.py",
        ),
        "action_activation": (
            "p336_long_idle_action_activation",
            "workspace/public/src/device-action/bindings/s22plus_fyg8_p336_long_idle_action_v1.json",
        ),
    }
    source_values: dict[str, dict[str, Any]] = {}
    for name, (key, path) in source_specs.items():
        value = _artifact(
            source_closure.get(key), f"P3.36 {name} source", maximum=2 * 1024 * 1024
        )
        if value["path"] != path:
            raise EvidenceError(f"P3.36 {name} source path differs")
        source_values[name] = value
    key_identity = _binary_identity(
        candidate_static.get("authentication", {}).get("key"),
        "P3.36 public auth key identity",
    )
    if key_identity != P336_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.36 auth key identity differs")
    source_contract = _selected_contract(
        p336_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p336_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.36 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p336_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.36 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p336_stock_offline_contract_v1",
        "decoder": p336_stock_adapter.DECODER_ID,
        "policy_id": p336_stock_adapter.POLICY_ID,
        "profile": p336_stock_adapter.PROFILE,
        "run_id": P336_RUN_ID,
        "terminal_stage": p336_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p336_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.36 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p336_long_idle_acm_observer_source": {
            key: source_values["observer"][key] for key in ("size", "sha256")
        },
        "p336_long_idle_runtime_source": {
            key: source_values["runtime"][key] for key in ("size", "sha256")
        },
        "p336_long_idle_action_source": {
            key: source_values["action"][key] for key in ("size", "sha256")
        },
        "p336_long_idle_action_activation": {
            key: source_values["action_activation"][key] for key in ("size", "sha256")
        },
        "p336_artifact_identity_source": {
            key: source_values["artifact"][key] for key in ("size", "sha256")
        },
        "p336_auth_key": dict(key_identity),
        "p336_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p336_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P336_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p336_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "initial_sessions_bounded": True,
        "physical_reopen_count": p336_stock_adapter.INITIAL_RECONNECT_COUNT,
        "per_boot_identity_required": True,
        "long_idle_host_resync": True,
        "later_action_open_before_resync": True,
        "listener_wait_after_proof": True,
        "resident_lease_schema": p336_stock_adapter.LEASE_SCHEMA,
        "resident_lease_duration_sec": p336_stock_adapter.LEASE_DURATION_SEC,
        "resident_lease_action_cap": p336_stock_adapter.LEASE_ACTION_CAP,
        "verified": True,
    }


def _verify_p335_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the narrow P3.35 retained-listener bundle."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P335_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.35 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.35 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        pin = item["contract"][name]
        if actual != {key: pin[key] for key in ("size", "sha256")} or actual != {
            key: receipts[name].get(key) for key in ("size", "sha256")
        }:
            raise EvidenceError(f"P3.35 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.35 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.35 candidate-static bytes are not canonical")
    candidate_static = _validate_p335_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    expected_header = {
        "schema": P335_CANDIDATE_STATIC_SCHEMA,
        "verdict": P335_CANDIDATE_STATIC_VERDICT,
        "target": P335_TARGET,
        "run_id": P335_RUN_ID,
        "predecessor_run_id": P335_PREDECESSOR_RUN_ID,
        "source_contract_id": p335_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P335_STOCK_OVERLAY_CONTRACT_ID,
        "profile": p335_stock_adapter.PROFILE,
    }
    candidate = candidate_static.get("candidate")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.35 candidate AP",
    )
    if (
        any(
            not _strict_equal(candidate_static.get(key), value)
            for key, value in expected_header.items()
        )
        or not isinstance(candidate, dict)
        or not isinstance(candidate.get("a"), dict)
        or candidate["a"].get("ap_tar_md5") != candidate_ap_identity
        or candidate.get("b", {}).get("ap_tar_md5") != candidate_ap_identity
        or candidate_ap.get("member")
        != {"name": "boot.img.lz4", **candidate["a"]["boot_img_lz4"]}
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
    ):
        raise EvidenceError("P3.35 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.35 run manifest")
    expected_manifest = {
        "schema": P335_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p335_stock_adapter.PROFILE,
        "run_id": P335_RUN_ID,
        "decoder": p335_stock_adapter.DECODER_ID,
        "policy_id": p335_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p335_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p335_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p335_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p335_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P335_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        any(
            not _strict_equal(run_manifest.get(key), value)
            for key, value in expected_manifest.items()
        )
        or not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P335_STOCK_OBSERVER_V4_RETAINED"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.35 run manifest differs")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.35 static result")
    expected_static_header = {
        "schema": P335_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P335_STATIC_RESULT_VERDICT,
        "profile": p335_stock_adapter.PROFILE,
        "run_id": P335_RUN_ID,
        "decoder": p335_stock_adapter.DECODER_ID,
        "policy_id": p335_stock_adapter.POLICY_ID,
        "source_contract_id": p335_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P335_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
    }
    static_candidate = static_result.get("candidate")
    safety = static_result.get("safety")
    if (
        any(
            not _strict_equal(static_result.get(key), value)
            for key, value in expected_static_header.items()
        )
        or not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
        or not isinstance(safety, dict)
        or any(
            safety.get(key) is not expected
            for key, expected in {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "odin_transfer": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
                "causal_result_allowed": False,
                "candidate_success": False,
            }.items()
        )
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.35 static result differs")

    source_closure = candidate_static.get("source_closure")
    if not isinstance(source_closure, dict):
        raise EvidenceError("P3.35 source closure is incomplete")
    source_specs = {
        "artifact": (
            "p335_artifact_identity",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p335_artifact_identity.py",
        ),
        "observer": (
            "p335_retained_listener_acm_observer",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p335_retained_listener_acm_observer.py",
        ),
        "runtime": (
            "p335_retained_listener_runtime",
            "workspace/public/src/scripts/revalidation/s22plus_fyg8_p335_retained_listener_runtime.py",
        ),
    }
    source_values: dict[str, dict[str, Any]] = {}
    for name, (key, path) in source_specs.items():
        value = _artifact(
            source_closure.get(key), f"P3.35 {name} source", maximum=2 * 1024 * 1024
        )
        if value["path"] != path:
            raise EvidenceError(f"P3.35 {name} source path differs")
        source_values[name] = value
    key_identity = _binary_identity(
        candidate_static.get("authentication", {}).get("key"),
        "P3.35 public auth key identity",
    )
    if key_identity != P335_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.35 auth key identity differs")
    source_contract = _selected_contract(
        p335_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p335_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.35 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p335_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.35 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p335_stock_offline_contract_v1",
        "decoder": p335_stock_adapter.DECODER_ID,
        "policy_id": p335_stock_adapter.POLICY_ID,
        "profile": p335_stock_adapter.PROFILE,
        "run_id": P335_RUN_ID,
        "terminal_stage": p335_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p335_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.35 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p335_retained_listener_observer_source": {
            key: source_values["observer"][key] for key in ("size", "sha256")
        },
        "p335_retained_listener_runtime_source": {
            key: source_values["runtime"][key] for key in ("size", "sha256")
        },
        "p335_artifact_identity_source": {
            key: source_values["artifact"][key] for key in ("size", "sha256")
        },
        "p335_auth_key": dict(key_identity),
        "p335_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p335_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P335_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p335_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "initial_sessions_bounded": True,
        "physical_reopen_count": 1,
        "per_boot_identity_required": True,
        "listener_wait_after_proof": True,
        "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
        "resident_lease_duration_sec": 3_600,
        "resident_lease_action_cap": 16,
        "verified": True,
    }


def _verify_p334_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify P3.34 without adding a second logical-session proof path."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P334_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.34 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.34 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        if actual != {key: pin[key] for key in ("size", "sha256")} or actual != {
            key: receipts[name].get(key) for key in ("size", "sha256")
        }:
            raise EvidenceError(f"P3.34 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.34 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.34 candidate-static bytes are not canonical")
    candidate_static = _validate_p334_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.34 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.34 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.34 AP boot member"),
    }
    expected_header = {
        "schema": P334_CANDIDATE_STATIC_SCHEMA,
        "verdict": P334_CANDIDATE_STATIC_VERDICT,
        "target": P334_TARGET,
        "run_id": P334_RUN_ID,
        "predecessor_run_id": P334_PREDECESSOR_RUN_ID,
        "source_contract_id": p334_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P334_STOCK_OVERLAY_CONTRACT_ID,
        "profile": p334_stock_adapter.PROFILE,
    }
    if (
        any(not _strict_equal(candidate_static.get(key), value) for key, value in expected_header.items())
        or candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate.get("b", {}).get("ap_tar_md5") != candidate_ap_identity
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
    ):
        raise EvidenceError("P3.34 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.34 run manifest")
    expected_manifest = {
        "schema": P334_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p334_stock_adapter.PROFILE,
        "run_id": P334_RUN_ID,
        "decoder": p334_stock_adapter.DECODER_ID,
        "policy_id": p334_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p334_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p334_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p334_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p334_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P334_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P334_STOCK_OBSERVER_V4_RETAINED"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
        or any(not _strict_equal(run_manifest.get(key), value) for key, value in expected_manifest.items())
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.34 run manifest differs")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.34 static result")
    expected_static_header = {
        "schema": P334_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P334_STATIC_RESULT_VERDICT,
        "profile": p334_stock_adapter.PROFILE,
        "run_id": P334_RUN_ID,
        "decoder": p334_stock_adapter.DECODER_ID,
        "policy_id": p334_stock_adapter.POLICY_ID,
        "source_contract_id": p334_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P334_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
    }
    static_candidate = static_result.get("candidate")
    safety = static_result.get("safety")
    expected_safety = {
        "host_only": True, "device_contact": False, "device_write": False,
        "odin_invoked": False, "odin_transfer": False, "flash": False,
        "partition_write": False, "live_authorized": False,
        "causal_result_allowed": False, "candidate_success": False,
    }
    if (
        any(not _strict_equal(static_result.get(key), value) for key, value in expected_static_header.items())
        or not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
        or not isinstance(safety, dict)
        or any(safety.get(key) is not value for key, value in expected_safety.items())
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.34 static result differs")

    artifact_identity = candidate_static.get("artifact_identity")
    key_identity = _binary_identity(
        artifact_identity.get("auth_key") if isinstance(artifact_identity, dict) else None,
        "P3.34 public auth key identity",
    )
    if (
        not isinstance(artifact_identity, dict)
        or artifact_identity.get("run_id_hex") != P334_RUN_ID
        or artifact_identity.get("predecessor_run_id_rejected") != P334_PREDECESSOR_RUN_ID
        or artifact_identity.get("boot_only") is not True
        or key_identity != P334_AUTH_EXEC_AUTH_KEY_IDENTITY
        or artifact_identity.get("auth_key_path_published") is not False
    ):
        raise EvidenceError("P3.34 artifact identity differs")

    source_closure = candidate_static.get("source_closure")
    observer_adapter = candidate_static.get("observer_adapter")
    if not isinstance(source_closure, dict) or not isinstance(observer_adapter, dict):
        raise EvidenceError("P3.34 source closure is incomplete")
    source_specs = {
        "artifact": ("p334_artifact_identity", "workspace/public/src/scripts/revalidation/s22plus_fyg8_p334_artifact_identity.py"),
        "observer": ("p334_first_read_rc_acm_observer", "workspace/public/src/scripts/revalidation/s22plus_fyg8_p334_first_read_rc_acm_observer.py"),
        "runtime": ("p334_first_read_rc_runtime", "workspace/public/src/scripts/revalidation/s22plus_fyg8_p334_first_read_rc_runtime.py"),
    }
    source_values: dict[str, dict[str, Any]] = {}
    for name, (key, path) in source_specs.items():
        value = _artifact(source_closure.get(key), f"P3.34 {name} source", maximum=2 * 1024 * 1024)
        if value["path"] != path:
            raise EvidenceError(f"P3.34 {name} source path differs")
        source_values[name] = value
    expected_observer = {
        "schema": p334_first_read_rc_acm_observer.SCHEMA,
        "contract_id": P334_AUTH_EXEC_OBSERVER_CONTRACT_ID,
        "wire_magic": "S328",
        "frame_header_size": P334_AUTH_EXEC_FRAME_HEADER_SIZE,
        "commands": [{"size": len(command), "sha256": hashlib.sha256(command).hexdigest()} for command in p334_first_read_rc_runtime.DEFAULT_COMMANDS],
        "proof_command_count": P334_AUTH_EXEC_COMMAND_COUNT,
        "max_commands": P334_AUTH_EXEC_MAX_COMMANDS,
        "caller_selected_command": False,
        "command_timeout_sec": P334_AUTH_EXEC_COMMAND_TIMEOUT_SEC,
        "max_output_bytes": P334_AUTH_EXEC_MAX_OUTPUT_BYTES,
        "auth_algorithm": P334_AUTH_EXEC_AUTH_ALGORITHM,
        "auth_tag_size": P334_AUTH_EXEC_AUTH_TAG_SIZE,
        "auth_key_schema": P334_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key": key_identity,
        "auth_key_path_published": False,
        "per_session_random_nonce": True,
        "fixed_heartbeat_only": False,
        "fixed_p330_commands": True,
        "session_cap": P334_AUTH_EXEC_SESSION_CAP,
        "reconnect_cap": 0,
        "host_only": True,
        "device_contact": False,
        "raw_rx_forwarded_before_classification": True,
        "interactive_pty": False,
        "same_tty_fd": True,
        "host_tty_close_reopen": False,
        "transport_reconnect": False,
        "entry_diagnostic_stage": 0,
        "entry_diagnostic_before_console": True,
        "entry_diagnostic_count": 2,
        "diagnostics_non_authoritative": True,
        "first_console_return_checkpoint_only": True,
        "first_console_return_detail_prefix": P334_AUTH_EXEC_DETAIL_PREFIX,
        "first_console_return_detail_sentinel": P334_AUTH_EXEC_DETAIL_SENTINEL,
        "first_read_attribution_requires_stage0_without_stage1": True,
    }
    if any(not _strict_equal(observer_adapter.get(key), value) for key, value in expected_observer.items()):
        raise EvidenceError("P3.34 first-console-return observer contract differs")
    runtime_repair = candidate_static.get("runtime_repair")
    if (
        not isinstance(runtime_repair, dict)
        or runtime_repair.get("contract_id") != P334_AUTH_EXEC_RUNTIME_CONTRACT_ID
        or runtime_repair.get("run_id_hex") != P334_RUN_ID
        or runtime_repair.get("command_policy") != "fixed_p330_commands_v1"
        or runtime_repair.get("caller_selected_command") is not False
        or runtime_repair.get("session_count") != P334_AUTH_EXEC_SESSION_CAP
        or runtime_repair.get("reconnect_count") != 0
        or runtime_repair.get("same_tty_fd") is not True
        or runtime_repair.get("physical_reopen_count") != 0
        or runtime_repair.get("entry_diagnostic_stage") != 0
        or runtime_repair.get("entry_diagnostic_before_console") is not True
        or runtime_repair.get("entry_diagnostic_count") != 2
        or runtime_repair.get("first_console_return_checkpoint_only") is not True
        or runtime_repair.get("first_console_return_prefix")
        != P334_AUTH_EXEC_DETAIL_PREFIX
        or runtime_repair.get("first_console_return_sentinel")
        != P334_AUTH_EXEC_DETAIL_SENTINEL
        or runtime_repair.get(
            "first_read_interpretation_requires_stage0_without_stage1"
        )
        is not True
        or runtime_repair.get("console_body_changed") is not False
    ):
        raise EvidenceError("P3.34 first-console-return runtime binding differs")

    source_contract = _selected_contract(
        p334_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p334_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.34 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p334_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.34 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p334_stock_offline_contract_v1",
        "decoder": p334_stock_adapter.DECODER_ID,
        "policy_id": p334_stock_adapter.POLICY_ID,
        "profile": p334_stock_adapter.PROFILE,
        "run_id": P334_RUN_ID,
        "terminal_stage": p334_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p334_adapter_source_receipts": {name: _binary_identity(value, f"P3.34 adapter source {name}") for name, value in lineage_sources.items()},
        "p334_first_read_rc_observer_source": {key: source_values["observer"][key] for key in ("size", "sha256")},
        "p334_first_read_rc_runtime_source": {key: source_values["runtime"][key] for key in ("size", "sha256")},
        "p334_artifact_identity_source": {key: source_values["artifact"][key] for key in ("size", "sha256")},
        "p334_authenticated_observer_source": {key: source_values["observer"][key] for key in ("size", "sha256")},
        "p334_authenticated_runtime_source": {key: source_values["runtime"][key] for key in ("size", "sha256")},
        "p334_auth_key": dict(key_identity),
        "p334_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p334_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P334_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p334_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "udev_guard_settle_bounded": True,
        "preauth_diagnostics_bounded": True,
        "diagnostics_non_authoritative": True,
        "logical_sessions_bounded": True,
        "same_tty_fd_required": True,
        "physical_reopen_count": 0,
        "fixed_p330_commands": True,
        "entry_diagnostic_stage": 0,
        "entry_diagnostic_before_console": True,
        "first_console_return_checkpoint_only": True,
        "first_console_return_detail_prefix": P334_AUTH_EXEC_DETAIL_PREFIX,
        "first_console_return_detail_sentinel": P334_AUTH_EXEC_DETAIL_SENTINEL,
        "first_read_attribution_requires_stage0_without_stage1": True,
        "verified": True,
    }




def _verify_p333_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify P3.33 without adding a second logical-session proof path."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P333_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.33 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.33 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        if actual != {key: pin[key] for key in ("size", "sha256")} or actual != {
            key: receipts[name].get(key) for key in ("size", "sha256")
        }:
            raise EvidenceError(f"P3.33 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.33 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.33 candidate-static bytes are not canonical")
    candidate_static = _validate_p333_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.33 candidate package is incomplete")
    candidate_ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.33 candidate AP",
    )
    expected_member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.33 AP boot member"),
    }
    expected_header = {
        "schema": P333_CANDIDATE_STATIC_SCHEMA,
        "verdict": P333_CANDIDATE_STATIC_VERDICT,
        "target": P333_TARGET,
        "run_id": P333_RUN_ID,
        "predecessor_run_id": P333_PREDECESSOR_RUN_ID,
        "source_contract_id": p333_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P333_STOCK_OVERLAY_CONTRACT_ID,
        "profile": p333_stock_adapter.PROFILE,
    }
    if (
        any(not _strict_equal(candidate_static.get(key), value) for key, value in expected_header.items())
        or candidate_ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != expected_member
        or candidate.get("b", {}).get("ap_tar_md5") != candidate_ap_identity
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
    ):
        raise EvidenceError("P3.33 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }

    run_manifest = _json(payloads["run_manifest"], "P3.33 run manifest")
    expected_manifest = {
        "schema": P333_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p333_stock_adapter.PROFILE,
        "run_id": P333_RUN_ID,
        "decoder": p333_stock_adapter.DECODER_ID,
        "policy_id": p333_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p333_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p333_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p333_stock_adapter.TERMINAL_STAGE,
        },
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p333_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P333_STOCK_OVERLAY_CONTRACT_ID,
    }
    observation_contract = run_manifest.get("observation_contract")
    if (
        not isinstance(observation_contract, dict)
        or observation_contract.get("accepted_identity")
        != "P333_STOCK_OBSERVER_V4_RETAINED"
        or observation_contract.get("minimum_success_count") != 1
        or observation_contract.get("clean_baseline_required") is not True
        or observation_contract.get("runtime_values_preflighted") is not False
        or observation_contract.get("complete_is_noncausal") is not True
        or observation_contract.get("incomplete_result")
        != "NO_PROOF_EXPERIMENT_PRECONDITION"
        or observation_contract.get("receipt_result") != "NO_PROOF_OBSERVER"
        or any(not _strict_equal(run_manifest.get(key), value) for key, value in expected_manifest.items())
        or payloads["run_manifest"] != _canonical(run_manifest)
    ):
        raise EvidenceError("P3.33 run manifest differs")

    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.33 static result")
    expected_static_header = {
        "schema": P333_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P333_STATIC_RESULT_VERDICT,
        "profile": p333_stock_adapter.PROFILE,
        "run_id": P333_RUN_ID,
        "decoder": p333_stock_adapter.DECODER_ID,
        "policy_id": p333_stock_adapter.POLICY_ID,
        "source_contract_id": p333_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P333_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
    }
    expected_artifacts = {
        "ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "boot_image": candidate["a"]["boot_img"],
        "boot_img_lz4": candidate["a"]["boot_img_lz4"],
        "image": candidate["image"],
        "init": candidate["init"],
        "child": candidate["child"],
        "busybox": candidate["busybox"],
        "latch": P319_EXACT_ARTIFACTS["latch"],
    }
    static_candidate = static_result.get("candidate")
    safety = static_result.get("safety")
    expected_safety = {
        "host_only": True, "device_contact": False, "device_write": False,
        "odin_invoked": False, "odin_transfer": False, "flash": False,
        "partition_write": False, "live_authorized": False,
        "causal_result_allowed": False, "candidate_success": False,
    }
    if (
        any(not _strict_equal(static_result.get(key), value) for key, value in expected_static_header.items())
        or not isinstance(static_candidate, dict)
        or static_candidate.get("artifacts") != expected_artifacts
        or static_candidate.get("boot_only_ap") is not True
        or static_candidate.get("independent_static_contract") is not True
        or static_candidate.get("complete_is_noncausal") is not True
        or static_candidate.get("runtime_values_observed") is not False
        or static_candidate.get("verified") is not True
        or not isinstance(safety, dict)
        or any(safety.get(key) is not value for key, value in expected_safety.items())
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.33 static result differs")

    artifact_identity = candidate_static.get("artifact_identity")
    key_identity = _binary_identity(
        artifact_identity.get("auth_key") if isinstance(artifact_identity, dict) else None,
        "P3.33 public auth key identity",
    )
    if (
        not isinstance(artifact_identity, dict)
        or artifact_identity.get("run_id_hex") != P333_RUN_ID
        or artifact_identity.get("predecessor_run_id_rejected") != P333_PREDECESSOR_RUN_ID
        or artifact_identity.get("boot_only") is not True
        or key_identity != P333_AUTH_EXEC_AUTH_KEY_IDENTITY
        or artifact_identity.get("auth_key_path_published") is not False
    ):
        raise EvidenceError("P3.33 artifact identity differs")

    source_closure = candidate_static.get("source_closure")
    observer_adapter = candidate_static.get("observer_adapter")
    if not isinstance(source_closure, dict) or not isinstance(observer_adapter, dict):
        raise EvidenceError("P3.33 source closure is incomplete")
    source_specs = {
        "artifact": ("p333_artifact_identity", "workspace/public/src/scripts/revalidation/s22plus_fyg8_p333_artifact_identity.py"),
        "observer": ("p333_open_entry_diag_acm_observer", "workspace/public/src/scripts/revalidation/s22plus_fyg8_p333_open_entry_diag_acm_observer.py"),
        "runtime": ("p333_open_entry_diag_runtime", "workspace/public/src/scripts/revalidation/s22plus_fyg8_p333_open_entry_diag_runtime.py"),
    }
    source_values: dict[str, dict[str, Any]] = {}
    for name, (key, path) in source_specs.items():
        value = _artifact(source_closure.get(key), f"P3.33 {name} source", maximum=2 * 1024 * 1024)
        if value["path"] != path:
            raise EvidenceError(f"P3.33 {name} source path differs")
        source_values[name] = value
    expected_observer = {
        "schema": p333_open_entry_diag_acm_observer.SCHEMA,
        "contract_id": P333_AUTH_EXEC_OBSERVER_CONTRACT_ID,
        "wire_magic": "S328",
        "frame_header_size": P333_AUTH_EXEC_FRAME_HEADER_SIZE,
        "commands": [{"size": len(command), "sha256": hashlib.sha256(command).hexdigest()} for command in p333_open_entry_diag_runtime.DEFAULT_COMMANDS],
        "proof_command_count": P333_AUTH_EXEC_COMMAND_COUNT,
        "max_commands": P333_AUTH_EXEC_MAX_COMMANDS,
        "caller_selected_command": False,
        "command_timeout_sec": P333_AUTH_EXEC_COMMAND_TIMEOUT_SEC,
        "max_output_bytes": P333_AUTH_EXEC_MAX_OUTPUT_BYTES,
        "auth_algorithm": P333_AUTH_EXEC_AUTH_ALGORITHM,
        "auth_tag_size": P333_AUTH_EXEC_AUTH_TAG_SIZE,
        "auth_key_schema": P333_AUTH_EXEC_AUTH_KEY_SCHEMA,
        "auth_key": key_identity,
        "auth_key_path_published": False,
        "per_session_random_nonce": True,
        "fixed_heartbeat_only": False,
        "fixed_p330_commands": True,
        "session_cap": P333_AUTH_EXEC_SESSION_CAP,
        "reconnect_cap": 0,
        "host_only": True,
        "device_contact": False,
        "raw_rx_forwarded_before_classification": True,
        "interactive_pty": False,
        "same_tty_fd": True,
        "host_tty_close_reopen": False,
        "transport_reconnect": False,
        "entry_diagnostic_stage": 0,
        "entry_diagnostic_before_console": True,
        "entry_diagnostic_count": 2,
        "diagnostics_non_authoritative": True,
    }
    if any(not _strict_equal(observer_adapter.get(key), value) for key, value in expected_observer.items()):
        raise EvidenceError("P3.33 OPEN-entry observer contract differs")
    runtime_repair = candidate_static.get("runtime_repair")
    if (
        not isinstance(runtime_repair, dict)
        or runtime_repair.get("contract_id") != P333_AUTH_EXEC_RUNTIME_CONTRACT_ID
        or runtime_repair.get("run_id_hex") != P333_RUN_ID
        or runtime_repair.get("command_policy") != "fixed_p330_commands_v1"
        or runtime_repair.get("caller_selected_command") is not False
        or runtime_repair.get("session_count") != P333_AUTH_EXEC_SESSION_CAP
        or runtime_repair.get("reconnect_count") != 0
        or runtime_repair.get("same_tty_fd") is not True
        or runtime_repair.get("physical_reopen_count") != 0
        or runtime_repair.get("entry_diagnostic_stage") != 0
        or runtime_repair.get("entry_diagnostic_before_console") is not True
        or runtime_repair.get("entry_diagnostic_count") != 2
    ):
        raise EvidenceError("P3.33 OPEN-entry runtime binding differs")

    source_contract = _selected_contract(
        p333_stock_adapter.PARENT_SOURCE_CONTRACT_ID, p333_stock_adapter.PROFILE
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.33 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get("sources")
    if not isinstance(lineage_sources, dict) or set(lineage_sources) != p333_stock_adapter.SOURCE_KEYS:
        raise EvidenceError("P3.33 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p333_stock_offline_contract_v1",
        "decoder": p333_stock_adapter.DECODER_ID,
        "policy_id": p333_stock_adapter.POLICY_ID,
        "profile": p333_stock_adapter.PROFILE,
        "run_id": P333_RUN_ID,
        "terminal_stage": p333_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p333_adapter_source_receipts": {name: _binary_identity(value, f"P3.33 adapter source {name}") for name, value in lineage_sources.items()},
        "p333_open_entry_diag_observer_source": {key: source_values["observer"][key] for key in ("size", "sha256")},
        "p333_open_entry_diag_runtime_source": {key: source_values["runtime"][key] for key in ("size", "sha256")},
        "p333_artifact_identity_source": {key: source_values["artifact"][key] for key in ("size", "sha256")},
        "p333_authenticated_observer_source": {key: source_values["observer"][key] for key in ("size", "sha256")},
        "p333_authenticated_runtime_source": {key: source_values["runtime"][key] for key in ("size", "sha256")},
        "p333_auth_key": dict(key_identity),
        "p333_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p333_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P333_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p333_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "udev_guard_settle_bounded": True,
        "preauth_diagnostics_bounded": True,
        "diagnostics_non_authoritative": True,
        "logical_sessions_bounded": True,
        "same_tty_fd_required": True,
        "physical_reopen_count": 0,
        "fixed_p330_commands": True,
        "entry_diagnostic_stage": 0,
        "entry_diagnostic_before_console": True,
        "verified": True,
    }


def _verify_p329_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    """Verify the fresh P3.29 identity and the small host settle delta."""
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P329_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.29 offline contract is not applicable")
    names = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != names or set(receipts) != names:
        raise EvidenceError("P3.29 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipts[name].get("size") != pin["size"]
            or receipts[name].get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.29 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.29 candidate-static")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.29 candidate-static bytes are not canonical")
    candidate_static = _validate_p329_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    candidate = candidate_static.get("candidate")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("a"), dict):
        raise EvidenceError("P3.29 candidate package is incomplete")
    ap_identity = _binary_identity(
        {key: candidate_ap.get(key) for key in ("size", "sha256")},
        "P3.29 candidate AP",
    )
    member = {
        "name": "boot.img.lz4",
        **_binary_identity(candidate["a"].get("boot_img_lz4"), "P3.29 AP member"),
    }
    if (
        ap_identity != candidate["a"].get("ap_tar_md5")
        or candidate_ap.get("member") != member
        or candidate_static.get("run_id") != P329_RUN_ID
        or candidate_static.get("predecessor_run_id") != P328_RUN_ID
    ):
        raise EvidenceError("P3.29 candidate AP binding differs")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    run_manifest = _json(payloads["run_manifest"], "P3.29 run manifest")
    expected_manifest = {
        "schema": P329_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p329_stock_adapter.PROFILE,
        "run_id": P329_RUN_ID,
        "decoder": p329_stock_adapter.DECODER_ID,
        "policy_id": p329_stock_adapter.POLICY_ID,
        "records": {
            "long_family_hex": p329_stock_adapter.LONG_FAMILY.hex(),
            "unsat_family_hex": p329_stock_adapter.UNSAT_FAMILY.hex(),
            "terminal_stage": p329_stock_adapter.TERMINAL_STAGE,
        },
        "observation_contract": {
            "accepted_identity": "P329_STOCK_OBSERVER_V4_RETAINED",
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "runtime_values_preflighted": False,
            "complete_is_noncausal": True,
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_result": "NO_PROOF_OBSERVER",
        },
        "candidate_ap": ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p329_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P329_STOCK_OVERLAY_CONTRACT_ID,
    }
    if not _strict_equal(run_manifest, expected_manifest) or payloads[
        "run_manifest"
    ] != _canonical(run_manifest):
        raise EvidenceError("P3.29 run manifest differs")
    run_payload = _canonical(run_manifest)
    static_result = _json(payloads["static_check"], "P3.29 static result")
    expected_static = {
        "schema": P329_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P329_STATIC_RESULT_VERDICT,
        "profile": p329_stock_adapter.PROFILE,
        "run_id": P329_RUN_ID,
        "decoder": p329_stock_adapter.DECODER_ID,
        "policy_id": p329_stock_adapter.POLICY_ID,
        "source_contract_id": p329_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P329_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "busybox": candidate["busybox"],
                "latch": P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if not _strict_equal(static_result, expected_static) or payloads[
        "static_check"
    ] != _canonical(static_result):
        raise EvidenceError("P3.29 static result differs")
    key_identity = _binary_identity(
        candidate_static.get("artifact_identity", {}).get("auth_key"),
        "P3.29 public auth key identity",
    )
    if key_identity != P329_AUTH_EXEC_AUTH_KEY_IDENTITY:
        raise EvidenceError("P3.29 public auth key identity differs")
    artifact_source = _artifact(
        candidate_static.get("source_closure", {}).get("p328_artifact_identity"),
        "P3.29 artifact identity source",
        maximum=2 * 1024 * 1024,
    )
    observer_adapter = candidate_static.get("observer_adapter")
    if (
        not isinstance(observer_adapter, dict)
        or observer_adapter.get("schema") != "s22plus_fyg8_p329_auth_acm_session_v1"
        or observer_adapter.get("contract_id")
        != P329_AUTH_EXEC_OBSERVER_CONTRACT_ID
        or observer_adapter.get("wire_magic") != "S328"
    ):
        raise EvidenceError("P3.29 observer adapter differs")
    source_contract = _selected_contract(
        p329_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        p329_stock_adapter.PROFILE,
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.29 parent source receipts are unavailable") from exc
    lineage_sources = candidate_static.get("adapter", {}).get("lineage", {}).get(
        "sources"
    )
    if (
        not isinstance(lineage_sources, dict)
        or set(lineage_sources) != p329_stock_adapter.SOURCE_KEYS
    ):
        raise EvidenceError("P3.29 adapter source receipts are incomplete")
    return {
        "schema": "device_action_f1_p329_stock_offline_contract_v1",
        "decoder": p329_stock_adapter.DECODER_ID,
        "policy_id": p329_stock_adapter.POLICY_ID,
        "profile": p329_stock_adapter.PROFILE,
        "run_id": P329_RUN_ID,
        "terminal_stage": p329_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p329_adapter_source_receipts": {
            name: _binary_identity(value, f"P3.29 adapter source {name}")
            for name, value in lineage_sources.items()
        },
        "p329_authenticated_observer_source": _binary_identity(
            {
                key: observer_adapter["source"][key]
                for key in ("size", "sha256")
            },
            "P3.29 observer source",
        ),
        "p329_authenticated_runtime_source": _binary_identity(
            {
                key: observer_adapter["runtime_source"][key]
                for key in ("size", "sha256")
            },
            "P3.29 runtime source",
        ),
        "p329_artifact_identity_source": _binary_identity(
            {key: artifact_source[key] for key in ("size", "sha256")},
            "P3.29 artifact source identity",
        ),
        "p329_auth_key": dict(key_identity),
        "p329_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p329_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P329_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p329_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "udev_guard_settle_bounded": True,
        "verified": True,
    }


def _verify_p320_stock_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item.get("userspace_overlay_contract_id") != P320_STOCK_OVERLAY_CONTRACT_ID:
        raise EvidenceError("P3.20 offline contract is not applicable")
    expected_payloads = {"candidate_static", "run_manifest", "static_check"}
    if set(payloads) != expected_payloads or set(receipts) != expected_payloads:
        raise EvidenceError("P3.20 promotion artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"P3.20 offline contract {name} changed")

    candidate_static = _json(payloads["candidate_static"], "P3.20 candidate-static result")
    if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
        raise EvidenceError("P3.20 candidate-static bytes are not canonical")
    candidate_static = _validate_p320_candidate_static(
        candidate_static, runtime_bound=runtime_bound
    )
    run_manifest = _json(payloads["run_manifest"], "P3.20 run manifest")
    static_result = _json(payloads["static_check"], "P3.20 static result")
    if (
        payloads["run_manifest"] != _canonical(run_manifest)
        or payloads["static_check"] != _canonical(static_result)
    ):
        raise EvidenceError("P3.20 promotion artifacts are not canonical")
    static_identity = {
        "size": len(payloads["candidate_static"]),
        "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
    }
    candidate_ap_identity = _binary_identity(
        {"size": candidate_ap.get("size"), "sha256": candidate_ap.get("sha256")},
        "P3.20 candidate AP",
    )
    candidate = candidate_static["candidate"]
    expected_member = {
        "name": "boot.img.lz4",
        **candidate["a"]["boot_img_lz4"],
    }
    if (
        candidate_ap_identity != candidate["a"]["ap_tar_md5"]
        or candidate_ap.get("member") != expected_member
        or candidate_ap_identity == P319_EXACT_ARTIFACTS["ap_tar_md5"]
    ):
        raise EvidenceError("P3.20 candidate AP binding differs")
    expected_records = {
        "long_family_hex": p320_stock_adapter.LONG_FAMILY.hex(),
        "unsat_family_hex": p320_stock_adapter.UNSAT_FAMILY.hex(),
        "terminal_stage": p320_stock_adapter.TERMINAL_STAGE,
    }
    expected_observation = {
        "accepted_identity": "P320_STOCK_OBSERVER_V4_RETAINED",
        "minimum_success_count": 1,
        "clean_baseline_required": True,
        "runtime_values_preflighted": False,
        "complete_is_noncausal": True,
        "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
        "receipt_result": "NO_PROOF_OBSERVER",
    }
    expected_run_manifest = {
        "schema": P320_RUN_MANIFEST_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "profile": p320_stock_adapter.PROFILE,
        "run_id": P320_RUN_ID,
        "decoder": p320_stock_adapter.DECODER_ID,
        "policy_id": p320_stock_adapter.POLICY_ID,
        "records": expected_records,
        "observation_contract": expected_observation,
        "candidate_ap": candidate_ap_identity,
        "candidate_static": static_identity,
        "source_contract_id": p320_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P320_STOCK_OVERLAY_CONTRACT_ID,
    }
    if run_manifest != expected_run_manifest:
        raise EvidenceError("P3.20 run manifest differs from candidate-static")
    run_payload = _canonical(run_manifest)
    expected_static_result = {
        "schema": P320_STATIC_RESULT_SCHEMA,
        "target": PID1_USERSPACE_TARGET,
        "verdict": P320_STATIC_RESULT_VERDICT,
        "profile": p320_stock_adapter.PROFILE,
        "run_id": P320_RUN_ID,
        "decoder": p320_stock_adapter.DECODER_ID,
        "policy_id": p320_stock_adapter.POLICY_ID,
        "source_contract_id": p320_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P320_STOCK_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": candidate_ap_identity,
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate_static["builder_closure"]["inputs"]["fixed-Image"],
                "init": candidate["userspace"]["a"]["init"],
                "child": candidate["userspace"]["a"]["child"],
                "latch": candidate_static["builder_closure"]["module_bytes"][
                    "s22plus_dwc3_event_latch.ko"
                ],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    if static_result != expected_static_result:
        raise EvidenceError("P3.20 static result differs")
    source_contract = _selected_contract(
        p320_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        p320_stock_adapter.PROFILE,
    )
    try:
        _source_payloads, candidate_source_receipts = source_contract.module.source_receipts(
            Path(__file__).resolve().parents[5]
        )
    except (OSError, source_contract.module.SourceContractError) as exc:
        raise EvidenceError("P3.20 parent source receipts are unavailable") from exc
    adapter_receipts = {
        name: {
            key: candidate_static["source_closure"][name][key]
            for key in ("size", "sha256")
        }
        for name in p320_stock_adapter.SOURCE_KEYS
    }
    return {
        "schema": "device_action_f1_p320_stock_offline_contract_v1",
        "decoder": p320_stock_adapter.DECODER_ID,
        "policy_id": p320_stock_adapter.POLICY_ID,
        "profile": p320_stock_adapter.PROFILE,
        "run_id": P320_RUN_ID,
        "terminal_stage": p320_stock_adapter.TERMINAL_STAGE,
        "candidate_ap_sha256": candidate_ap_identity["sha256"],
        "candidate_static_sha256": static_identity["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_static_authority": candidate_static["authority_source"],
        "candidate_source_receipts": candidate_source_receipts,
        "p320_adapter_source_receipts": adapter_receipts,
        "p320_builder_result": candidate_static["builder_result"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "source_contract_id": p320_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": P320_STOCK_OVERLAY_CONTRACT_ID,
        "ap_payload_closure": _p320_ap_payload_closure(candidate_static),
        "runtime_values_observed": False,
        "complete_is_noncausal": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "verified": True,
    }


def _verify_e1_latest_stage_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != E1_LATEST_STAGE_KIND:
        raise EvidenceError("offline E1 latest-stage contract is not applicable")
    profile = item["profile"]
    source_contract_id = item.get("source_contract_id")
    userspace_overlay_contract_id = item.get("userspace_overlay_contract_id")
    if userspace_overlay_contract_id == P342_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p342_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P341_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p341_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P340_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p340_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P339_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p339_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P338_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p338_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P337_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p337_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P336_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p336_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P335_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p335_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P334_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p334_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P333_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p333_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P332_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p332_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P331_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p331_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P330_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p330_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P329_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p329_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P328_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p328_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P327_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p327_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P326_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p326_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P325_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p325_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P324_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p324_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P323_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p323_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P322_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p322_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P321_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p321_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P320_STOCK_OVERLAY_CONTRACT_ID:
        return _verify_p320_stock_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if userspace_overlay_contract_id == P319_STOCK_OVERLAY_CONTRACT_ID:
        expected_payloads = {"candidate_static", "run_manifest", "static_check"}
        if set(payloads) != expected_payloads or set(receipts) != expected_payloads:
            raise EvidenceError(
                "P3.19 Process-v2 offline promotion artifacts are incomplete"
            )
        for name, payload in payloads.items():
            pin = item["contract"][name]
            receipt = receipts[name]
            if (
                len(payload) != pin["size"]
                or hashlib.sha256(payload).hexdigest() != pin["sha256"]
                or receipt.get("size") != pin["size"]
                or receipt.get("sha256") != pin["sha256"]
            ):
                raise EvidenceError(f"P3.19 offline contract {name} changed")

        candidate_static = _json(
            payloads["candidate_static"], "P3.19 candidate-static result"
        )
        if payloads["candidate_static"] != _canonical(candidate_static) + b"\n":
            raise EvidenceError("P3.19 candidate-static bytes are not canonical")
        candidate_static = _validate_p319_candidate_static(
            candidate_static,
            runtime_bound=runtime_bound,
        )
        run_manifest = _json(payloads["run_manifest"], "P3.19 run manifest")
        static_result = _json(payloads["static_check"], "P3.19 static result")
        if (
            payloads["run_manifest"] != _canonical(run_manifest)
            or payloads["static_check"] != _canonical(static_result)
        ):
            raise EvidenceError("P3.19 promotion artifacts are not canonical")
        candidate_static_identity = {
            "size": len(payloads["candidate_static"]),
            "sha256": hashlib.sha256(payloads["candidate_static"]).hexdigest(),
        }
        candidate_ap_identity = _binary_identity(
            {
                "size": candidate_ap.get("size"),
                "sha256": candidate_ap.get("sha256"),
            },
            "P3.19 candidate AP",
        )
        if (
            candidate_ap_identity != P319_EXACT_ARTIFACTS["ap_tar_md5"]
            or candidate_ap.get("member")
            != {
                "name": "boot.img.lz4",
                **P319_EXACT_ARTIFACTS["boot_img_lz4"],
            }
        ):
            raise EvidenceError("P3.19 candidate AP binding differs")
        expected_run_manifest = {
            "schema": E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA,
            "target": PID1_USERSPACE_TARGET,
            "profile": p319_stock_adapter.PROFILE,
            "run_id": P319_RUN_ID,
            "decoder": p319_stock_adapter.DECODER_ID,
            "policy_id": p319_stock_adapter.POLICY_ID,
            "records": {
                "long_family_hex": p319_stock_adapter.LONG_FAMILY.hex(),
                "unsat_family_hex": p319_stock_adapter.UNSAT_FAMILY.hex(),
                "terminal_stage": p319_stock_adapter.TERMINAL_STAGE,
            },
            "observation_contract": {
                "accepted_identity": "P319_STOCK_WITNESS_RETAINED",
                "minimum_success_count": 1,
                "clean_baseline_required": True,
                "runtime_witnesses_required": sorted(
                    candidate_static["runtime_observation_contract"]["witnesses"]
                ),
                "runtime_values_preflighted": False,
                "complete_is_noncausal": True,
            },
            "candidate_ap": candidate_ap_identity,
            "candidate_static": candidate_static_identity,
            "source_contract_id": p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P319_STOCK_OVERLAY_CONTRACT_ID,
        }
        if _canonical(run_manifest) != _canonical(expected_run_manifest):
            raise EvidenceError("P3.19 run manifest differs from candidate-static")
        run_payload = _canonical(run_manifest)
        expected_static_result = {
            "schema": E1_LATEST_STAGE_STATIC_SCHEMA,
            "target": PID1_USERSPACE_TARGET,
            "verdict": E1_LATEST_STAGE_STATIC_VERDICT,
            "profile": p319_stock_adapter.PROFILE,
            "run_id": P319_RUN_ID,
            "decoder": p319_stock_adapter.DECODER_ID,
            "policy_id": p319_stock_adapter.POLICY_ID,
            "source_contract_id": p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P319_STOCK_OVERLAY_CONTRACT_ID,
            "run_binding": {
                "canonical_manifest_size": len(run_payload),
                "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
                "verified": True,
            },
            "candidate": {
                "artifacts": {
                    "ap": P319_EXACT_ARTIFACTS["ap_tar_md5"],
                    "candidate_static": candidate_static_identity,
                    "boot_image": P319_EXACT_ARTIFACTS["boot_img"],
                    "boot_img_lz4": P319_EXACT_ARTIFACTS["boot_img_lz4"],
                    "image": P319_EXACT_ARTIFACTS["image"],
                    "init": P319_EXACT_ARTIFACTS["init"],
                    "child": P319_EXACT_ARTIFACTS["child"],
                    "latch": P319_EXACT_ARTIFACTS["latch"],
                },
                "boot_only_ap": True,
                "independent_static_contract": True,
                "complete_is_noncausal": True,
                "runtime_values_observed": False,
                "verified": True,
            },
            "safety": {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "odin_transfer": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
                "causal_result_allowed": False,
                "candidate_success": False,
            },
        }
        if _canonical(static_result) != _canonical(expected_static_result):
            raise EvidenceError("P3.19 static result differs")
        source_contract = _selected_contract(
            p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            p319_stock_adapter.PROFILE,
        )
        try:
            _source_payloads, candidate_source_receipts = (
                source_contract.module.source_receipts(
                    Path(__file__).resolve().parents[5]
                )
            )
        except (OSError, source_contract.module.SourceContractError) as exc:
            raise EvidenceError("P3.19 parent source receipts are unavailable") from exc
        return {
            "schema": "device_action_f1_p319_stock_offline_contract_v1",
            "decoder": p319_stock_adapter.DECODER_ID,
            "policy_id": p319_stock_adapter.POLICY_ID,
            "profile": p319_stock_adapter.PROFILE,
            "run_id": P319_RUN_ID,
            "terminal_stage": p319_stock_adapter.TERMINAL_STAGE,
            "candidate_ap_sha256": candidate_ap_identity["sha256"],
            "candidate_static_sha256": candidate_static_identity["sha256"],
            "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
            "candidate_static_authority": candidate_static["authority_source"],
            "candidate_source_receipts": candidate_source_receipts,
            "p319_adapter_source_receipts": {
                name: {
                    key: receipt[key] for key in ("size", "sha256")
                }
                for name, receipt in candidate_static[
                    "adapter_source_receipts"
                ].items()
            },
            "run_manifest_sha256": receipts["run_manifest"]["sha256"],
            "static_check_sha256": receipts["static_check"]["sha256"],
            "clean_baseline_required": True,
            "minimum_success_count": 1,
            "source_contract_id": p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": P319_STOCK_OVERLAY_CONTRACT_ID,
            "ap_payload_closure": _p319_ap_payload_closure(candidate_static),
            "runtime_values_observed": False,
            "complete_is_noncausal": True,
            "causal_result_allowed": False,
            "candidate_success": False,
            "verified": True,
        }
    source_decoder = _latest_stage_decoder(source_contract_id, profile)
    selected_decoder = _latest_stage_observation_decoder(
        source_contract_id,
        profile,
        userspace_overlay_contract_id,
    )
    expected_payloads = {
        "candidate_static",
        "run_manifest",
        "static_check",
    }
    stock_keys = {"stock_baseline_raw", "stock_baseline_result"}
    if (
        userspace_overlay_contract_id
        in {
            P303_OVERLAY_CONTRACT_ID,
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
        }
        and stock_keys <= set(item["contract"])
    ):
        expected_payloads.update(
            stock_keys
        )
    if set(payloads) != expected_payloads or set(receipts) != set(payloads):
        raise EvidenceError(
            "P2.34 E1 latest-stage evidence has no candidate-bound offline contract"
        )
    for name, payload in payloads.items():
        pin = item["contract"][name]
        value = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or value.get("size") != pin["size"]
            or value.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline E1 latest-stage contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "E1 latest-stage run manifest")
    static_result = _json(payloads["static_check"], "E1 latest-stage static result")
    p303_stock_baseline = None
    if stock_keys <= set(payloads):
        try:
            p303_stock_baseline = p303_stock_binding.verify_payloads(
                Path(__file__).resolve().parents[5],
                payloads["stock_baseline_raw"],
                payloads["stock_baseline_result"],
                expected_raw_path=item["contract"]["stock_baseline_raw"]["path"],
            )
        except (p303_stock_binding.BindingError, OSError) as exc:
            raise EvidenceError("P3.03 stock baseline binding is invalid") from exc
    if (
        run_manifest.get("schema") != E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA
        or static_result.get("schema") != E1_LATEST_STAGE_STATIC_SCHEMA
    ):
        raise EvidenceError(
            "P2.34 E1 latest-stage evidence has no candidate-bound offline contract"
        )
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    expected_records = {
        "long_family_hex": selected_decoder.model.LONG_FAMILY.hex(),
        "unsat_family_hex": selected_decoder.model.UNSAT_FAMILY.hex(),
        "terminal_stage": item["terminal_stage"],
    }
    expected_observation = {
        "accepted_identity": _latest_stage_accepted_identity(
            profile,
            source_contract_id,
            userspace_overlay_contract_id,
        ),
        "minimum_success_count": 1,
        "clean_baseline_required": True,
    }
    run_manifest_keys = {
        "schema",
        "target",
        "profile",
        "run_id",
        "decoder",
        "policy_id",
        "records",
        "observation_contract",
        "candidate_ap",
        "candidate_static",
    }
    if source_contract_id is not None:
        run_manifest_keys.add("source_contract_id")
    if userspace_overlay_contract_id is not None:
        run_manifest_keys.add("userspace_overlay_contract_id")
    if (
        set(run_manifest) != run_manifest_keys
        or run_manifest.get("schema") != E1_LATEST_STAGE_RUN_MANIFEST_SCHEMA
        or run_manifest.get("target") != PID1_USERSPACE_TARGET
        or run_manifest.get("profile") != item["profile"]
        or run_manifest.get("source_contract_id") != source_contract_id
        or run_manifest.get("userspace_overlay_contract_id")
        != userspace_overlay_contract_id
        or run_manifest.get("run_id") != item["run_id"]
        or run_manifest.get("decoder") != selected_decoder.DECODER_ID
        or run_manifest.get("policy_id") != selected_decoder.POLICY_ID
        or run_manifest.get("records") != expected_records
        or run_manifest.get("observation_contract") != expected_observation
        or not _artifact_matches(run_manifest.get("candidate_ap"), candidate_ap)
        or payloads["run_manifest"] != canonical
    ):
        raise EvidenceError("run manifest does not bind the E1 candidate")
    candidate_static = _binary_identity(
        run_manifest.get("candidate_static"), "E1A candidate static result"
    )
    if not _artifact_matches(receipts["candidate_static"], candidate_static):
        raise EvidenceError("run manifest does not bind the candidate static payload")

    candidate_static_result = _json(
        payloads["candidate_static"], "E1A candidate static result"
    )
    overlay_static_contracts = {
        P301_OVERLAY_CONTRACT_ID: (
            P301_CANDIDATE_STATIC_SCHEMA, P301_CANDIDATE_STATIC_VERDICT
        ),
        P302_OVERLAY_CONTRACT_ID: (
            P302_CANDIDATE_STATIC_SCHEMA, P302_CANDIDATE_STATIC_VERDICT
        ),
        P303_OVERLAY_CONTRACT_ID: (
            P303_CANDIDATE_STATIC_SCHEMA, P303_CANDIDATE_STATIC_VERDICT
        ),
        P304_OVERLAY_CONTRACT_ID: (
            P304_CANDIDATE_STATIC_SCHEMA, P304_CANDIDATE_STATIC_VERDICT
        ),
        P305_OVERLAY_CONTRACT_ID: (
            P305_CANDIDATE_STATIC_SCHEMA, P305_CANDIDATE_STATIC_VERDICT
        ),
        P306_OVERLAY_CONTRACT_ID: (
            P306_CANDIDATE_STATIC_SCHEMA, P306_CANDIDATE_STATIC_VERDICT
        ),
        P307_OVERLAY_CONTRACT_ID: (
            P307_CANDIDATE_STATIC_SCHEMA, P307_CANDIDATE_STATIC_VERDICT
        ),
        P308_OVERLAY_CONTRACT_ID: (
            P308_CANDIDATE_STATIC_SCHEMA, P308_CANDIDATE_STATIC_VERDICT
        ),
        P311_OVERLAY_CONTRACT_ID: (
            P311_CANDIDATE_STATIC_SCHEMA, P311_CANDIDATE_STATIC_VERDICT
        ),
        P312_OVERLAY_CONTRACT_ID: (
            P312_CANDIDATE_STATIC_SCHEMA, P312_CANDIDATE_STATIC_VERDICT
        ),
        P313_OVERLAY_CONTRACT_ID: (
            P313_CANDIDATE_STATIC_SCHEMA, P313_CANDIDATE_STATIC_VERDICT
        ),
        P314_OVERLAY_CONTRACT_ID: (
            P314_CANDIDATE_STATIC_SCHEMA, P314_CANDIDATE_STATIC_VERDICT
        ),
        P315_OVERLAY_CONTRACT_ID: (
            P315_CANDIDATE_STATIC_SCHEMA, P315_CANDIDATE_STATIC_VERDICT
        ),
        MAX77705_OVERLAY_CONTRACT_ID: (
            P316_CANDIDATE_STATIC_SCHEMA, P316_CANDIDATE_STATIC_VERDICT
        ),
        P317_MAX77705_OVERLAY_CONTRACT_ID: (
            P317_CANDIDATE_STATIC_SCHEMA, P317_CANDIDATE_STATIC_VERDICT
        ),
        P318_MAX77705_OVERLAY_CONTRACT_ID: (
            P318_CANDIDATE_STATIC_SCHEMA, P318_CANDIDATE_STATIC_VERDICT
        ),
    }
    source_static_contracts = {
        P286_SOURCE_CONTRACT_ID: (
            P286_CANDIDATE_STATIC_SCHEMA, P286_CANDIDATE_STATIC_VERDICT
        ),
        P288_SOURCE_CONTRACT_ID: (
            P288_CANDIDATE_STATIC_SCHEMA, P288_CANDIDATE_STATIC_VERDICT
        ),
        P290_SOURCE_CONTRACT_ID: (
            P290_CANDIDATE_STATIC_SCHEMA, P290_CANDIDATE_STATIC_VERDICT
        ),
        P292_SOURCE_CONTRACT_ID: (
            P292_CANDIDATE_STATIC_SCHEMA, P292_CANDIDATE_STATIC_VERDICT
        ),
        P294_SOURCE_CONTRACT_ID: (
            P294_CANDIDATE_STATIC_SCHEMA, P294_CANDIDATE_STATIC_VERDICT
        ),
        P296_SOURCE_CONTRACT_ID: (
            P296_CANDIDATE_STATIC_SCHEMA, P296_CANDIDATE_STATIC_VERDICT
        ),
        P298_SOURCE_CONTRACT_ID: (
            P298_CANDIDATE_STATIC_SCHEMA, P298_CANDIDATE_STATIC_VERDICT
        ),
        P300_SOURCE_CONTRACT_ID: (
            P300_CANDIDATE_STATIC_SCHEMA, P300_CANDIDATE_STATIC_VERDICT
        ),
        P310_SOURCE_CONTRACT_ID: (
            P310_CANDIDATE_STATIC_SCHEMA, P310_CANDIDATE_STATIC_VERDICT
        ),
    }
    expected_candidate_static_schema, expected_candidate_static_verdict = (
        overlay_static_contracts.get(userspace_overlay_contract_id)
        or source_static_contracts.get(source_contract_id)
        or (
            E1_LATEST_STAGE_CANDIDATE_STATIC_SCHEMA,
            E1_LATEST_STAGE_CANDIDATE_STATIC_VERDICT,
        )
    )
    expected_candidate_static_keys = {
        "schema",
        "target",
        "verdict",
        "candidate_contract",
        "build_repro",
        "candidate",
        "tools",
        "limits",
        "safety",
    }
    if userspace_overlay_contract_id == P302_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.add("carrier_identity")
    if userspace_overlay_contract_id == P313_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p313_tracefs_abi",
                "p313_cross_gate_audit",
                "p313_runtime_fixture",
                "p313_process_v2_adapter_fixture",
                "p313_hazard_closure",
                "p313_telemetry",
                "p313_observer",
            }
        )
    if userspace_overlay_contract_id == P314_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p314_tracefs_abi",
                "p314_cross_gate_audit",
                "p314_runtime_fixture",
                "p314_matrix_fixture",
                "p314_process_v2_adapter_fixture",
                "p314_hazard_closure",
                "p314_qualification_closure",
                "p314_telemetry",
                "p314_observer",
            }
        )
    if userspace_overlay_contract_id == P315_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p315_tracefs_abi",
                "p315_cross_gate_audit",
                "p315_restart_source_geometry",
                "p315_runtime_fixture",
                "p315_matrix_fixture",
                "p315_process_v2_adapter_fixture",
                "p315_prepackaging_closure",
                "p315_qualification_closure",
                "p315_telemetry",
                "p315_observer",
            }
        )
    if userspace_overlay_contract_id == P318_MAX77705_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p318_runtime_qualification",
                "p318_envelope_qualification",
                "p318_process_v2_adapter_fixture",
                "p318_topology_receipt",
                "p318_qualification_closure",
                "p318_telemetry",
                "p318_observer",
            }
        )
    elif userspace_overlay_contract_id == P317_MAX77705_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p317_runtime_fixture",
                "p317_envelope_fixture",
                "p317_process_v2_adapter_fixture",
                "p317_executability_fixed_point",
                "p317_late_loader_lifecycle",
                "p317_sidecar_positive_control",
                "p317_qualification_closure",
                "p317_telemetry",
                "p317_observer",
            }
        )
    elif userspace_overlay_contract_id == MAX77705_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p316_runtime_fixture",
                "p316_late_loader_lifecycle",
                "p316_process_v2_adapter_fixture",
                "p316_sidecar_positive_control",
                "p316_qualification_closure",
                "p316_telemetry",
                "p316_observer",
            }
        )
    elif userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p312_callsite_audit",
                "p312_delayed_arm_qemu",
                "p312_tracefs_abi",
                "p312_cross_gate_audit",
                "p312_carrier_decoder_authority",
                "p312_runtime_fixture",
                "p312_telemetry",
                "p312_observer",
            }
        )
    elif userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p311_callsite_audit",
                "p311_delayed_arm_qemu",
                "p311_tracefs_abi",
                "p311_cross_gate_audit",
                "p311_runtime_fixture",
                "p311_telemetry",
                "p311_observer",
            }
        )
    elif userspace_overlay_contract_id == P308_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p303_callsite_audit",
                "p307_qscratch_audit",
                "p308_telemetry",
                "p308_observer",
                "p308_cross_gate_audit",
            }
        )
    elif userspace_overlay_contract_id == P307_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {
                "p303_callsite_audit",
                "p307_qscratch_audit",
                "p307_telemetry",
                "p307_observer",
            }
        )
    elif userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.update(
            {"p303_callsite_audit", "p306_ipc_telemetry", "p306_observer"}
        )
    elif userspace_overlay_contract_id in {
        P303_OVERLAY_CONTRACT_ID,
        P304_OVERLAY_CONTRACT_ID,
        P305_OVERLAY_CONTRACT_ID,
    }:
        expected_candidate_static_keys.update(
            {"p303_callsite_audit", "p303_offset_probe_rule"}
        )
    if userspace_overlay_contract_id == P305_OVERLAY_CONTRACT_ID:
        expected_candidate_static_keys.add("p305_folded_tail")
    if (
        set(candidate_static_result) != expected_candidate_static_keys
        or candidate_static_result.get("schema")
        != expected_candidate_static_schema
        or candidate_static_result.get("target") != PID1_USERSPACE_TARGET
        or candidate_static_result.get("verdict")
        != expected_candidate_static_verdict
    ):
        raise EvidenceError("candidate static result header is not accepted")
    source_contract_keys = {
        "schema",
        "target",
        "verdict",
        "profile",
        "profile_number",
        "run_id",
        "unsat_record_hex",
        "unsat_tag_hex",
        "decoder_id",
        "decoder_policy_id",
        "identity_preimage",
        "identity_preimage_sha256",
        "intent",
        "patch",
        "base_files",
        "patched_files",
        "config_lines",
        "reachable_record_contract",
        "verified",
        "safety",
    }
    if source_contract_id is not None:
        source_contract_keys.update(
            {"source_contract_id", "materialized_sources"}
        )
    candidate_contract_value = candidate_static_result.get("candidate_contract")
    p301_overlay_source_receipts = None
    p302_overlay_source_receipts = None
    p303_overlay_source_receipts = None
    p304_overlay_source_receipts = None
    p305_overlay_source_receipts = None
    p306_overlay_source_receipts = None
    p307_overlay_source_receipts = None
    p308_overlay_source_receipts = None
    p311_overlay_source_receipts = None
    p312_overlay_source_receipts = None
    p313_overlay_source_receipts = None
    p314_overlay_source_receipts = None
    p315_overlay_source_receipts = None
    p316_overlay_source_receipts = None
    p317_overlay_source_receipts = None
    p318_overlay_source_receipts = None
    p318_contract = None
    p302_contract = None
    p303_contract = None
    if userspace_overlay_contract_id == P301_OVERLAY_CONTRACT_ID:
        p301_contract = _validate_p301_overlay_contract(candidate_contract_value)
        if (
            p301_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p301_contract.get("source_contract_id") != source_contract_id
            or p301_contract.get("profile") != profile
            or p301_contract.get("run_id") != item["run_id"]
            or p301_contract.get("telemetry", {}).get("decoder_id")
            != selected_decoder.DECODER_ID
            or p301_contract.get("telemetry", {}).get("decoder_policy_id")
            != selected_decoder.POLICY_ID
            or p301_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.01 overlay candidate contract is invalid")
        candidate_contract_value = p301_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = p301_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P318_MAX77705_OVERLAY_CONTRACT_ID:
        import s22plus_fyg8_p318_overlay_contract as p318_overlay
        import s22plus_fyg8_p318_qualification_closure as p318_qualification

        p318_contract = _validate_p318_overlay_contract(candidate_contract_value)
        qualified = candidate_static_result.get("p318_qualification_closure")
        if not isinstance(qualified, dict):
            raise EvidenceError("P3.18 qualification closure is absent")
        root = Path(__file__).resolve().parents[5]
        try:
            p318_qualification.validate_qualification_artifact(
                qualified,
                root=root,
                candidate_tree=qualified.get("candidate_tree"),
                intent_path=root / p318_overlay.DEFAULT_INTENT,
            )
        except p318_qualification.QualificationError as exc:
            raise EvidenceError("P3.18 qualification closure is invalid") from exc
        if (
            p318_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p318_contract.get("source_contract_id") != source_contract_id
            or p318_contract.get("profile") != profile
            or p318_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p318_max77705_decoder
            or candidate_static_result.get("p318_runtime_qualification")
            != p318_contract.get("runtime_qualification")
            or candidate_static_result.get("p318_envelope_qualification")
            != p318_contract.get("envelope_qualification")
            or candidate_static_result.get("p318_process_v2_adapter_fixture")
            != p318_contract.get("process_v2_adapter_fixture")
            or candidate_static_result.get("p318_topology_receipt")
            != p318_contract.get("topology_receipt")
            or candidate_static_result.get("p318_telemetry")
            != p318_contract.get("telemetry")
            or candidate_static_result.get("p318_observer")
            != p318_contract.get("observer")
            or qualified.get("schema") != p318_qualification.FINAL_SCHEMA
            or qualified.get("verified") is not True
            or p318_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.18 overlay candidate contract is invalid")
        candidate_contract_value = p318_contract.get("parent_candidate_contract")
        p318_overlay_source_receipts = p318_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P317_MAX77705_OVERLAY_CONTRACT_ID:
        import s22plus_fyg8_p317_qualification_closure as p317_qualification

        p317_contract = _validate_p317_overlay_contract(candidate_contract_value)
        telemetry = p317_contract.get("telemetry")
        observer = p317_contract.get("observer")
        runtime = candidate_static_result.get("p317_runtime_fixture")
        envelope = candidate_static_result.get("p317_envelope_fixture")
        adapter = candidate_static_result.get("p317_process_v2_adapter_fixture")
        fixed_point = candidate_static_result.get("p317_executability_fixed_point")
        lifecycle = candidate_static_result.get("p317_late_loader_lifecycle")
        sidecar = candidate_static_result.get("p317_sidecar_positive_control")
        qualified = candidate_static_result.get("p317_qualification_closure")
        if not isinstance(qualified, dict):
            raise EvidenceError("P3.17 qualification closure is absent")
        try:
            p317_qualification.validate_qualification_artifact(
                qualified,
                root=Path(__file__).resolve().parents[5],
                candidate_tree=qualified.get("candidate_tree"),
            )
        except p317_qualification.QualificationError as exc:
            raise EvidenceError("P3.17 qualification closure is invalid") from exc
        if (
            p317_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p317_contract.get("source_contract_id") != source_contract_id
            or p317_contract.get("profile") != profile
            or p317_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p317_max77705_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("decoder_id") != selected_decoder.DECODER_ID
            or telemetry.get("decoder_policy_id") != selected_decoder.POLICY_ID
            or telemetry.get("verified") is not True
            or not isinstance(observer, dict)
            or observer.get("candidate_window_sec") != 300
            or observer.get("guard_lifetime_sec") != 1200
            or observer.get("final_pair_before_banner") is not True
            or observer.get("usb_sidecar_required") is not True
            or observer.get("verified") is not True
            or not isinstance(runtime, dict)
            or runtime.get("verdict")
            != "PASS_P317_EXECUTABILITY_RUNTIME_FIXTURE_HOST_ONLY"
            or runtime.get("provider_count") != 3
            or runtime.get("verified") is not True
            or not isinstance(envelope, dict)
            or envelope.get("verdict")
            != "PASS_P317_MAX77705_NATIVE_ENVELOPE_V3_HOST_ONLY"
            or envelope.get("row_count") != 107
            or envelope.get("observable_eagain_rows") != 6
            or envelope.get("additional_eagain_rows") != 2
            or envelope.get("claim_busy_policy_rejected") is not True
            or envelope.get("claim_busy_decoder_preimage_empty") is not True
            or envelope.get("verified") is not True
            or not isinstance(adapter, dict)
            or adapter.get("verdict")
            != "PASS_P317_REAL_PROCESS_V2_RETAINED_SEMANTICS_HOST_ONLY"
            or adapter.get("observable_eagain_preimages") != 6
            or adapter.get("additional_eagain_preimages") != 2
            or adapter.get("retained_vector_preimages") != 107
            or adapter.get("actual_native_envelope_preimages") != 107
            or adapter.get("retained_vector_cross_group_unique") is not True
            or adapter.get("retained_vector_reverse_map_complete") is not True
            or adapter.get("native_envelope_adapter_input_byte_identity") is not True
            or adapter.get("claim_busy_policy_rejected") is not True
            or adapter.get("claim_busy_decoder_preimage_empty") is not True
            or adapter.get("claim_busy_normalized_observer_round_trip") is not True
            or adapter.get(
                "claim_busy_native_envelope_adapter_input_byte_identity"
            ) is not True
            or adapter.get("verified") is not True
            or not isinstance(fixed_point, dict)
            or fixed_point.get("module_delta", {}).get("added_early_module_count") != 5
            or not isinstance(lifecycle, dict)
            or lifecycle.get("verdict")
            != "PASS_P317_LATE_LOADER_LIFECYCLE_HOST_ONLY"
            or lifecycle.get("claim_busy_runtime_observation_byte_identical")
            is not True
            or lifecycle.get("claim_busy_runtime_wrapper_byte_identical")
            is not True
            or lifecycle.get(
                "claim_busy_runtime_wrapper_immediate_caller_verified"
            ) is not True
            or lifecycle.get(
                "claim_busy_runtime_wrapper_actual_c_executed_by_native_fixture"
            ) is not True
            or lifecycle.get(
                "claim_busy_runtime_wrapper_negative_envelope_sha256"
            ) != envelope.get("claim_busy_negative_envelope_sha256")
            or lifecycle.get("verified") is not True
            or not isinstance(sidecar, dict)
            or sidecar.get("verdict")
            != "PASS_P316_USB_SIDECAR_POSITIVE_CONTROL_HOST_ONLY"
            or sidecar.get("verified") is not True
            or qualified.get("schema") != p317_qualification.FINAL_SCHEMA
            or qualified.get("verified") is not True
            or candidate_static_result.get("p317_telemetry") != telemetry
            or candidate_static_result.get("p317_observer") != observer
            or p317_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.17 overlay candidate contract is invalid")
        candidate_contract_value = p317_contract.get("parent_candidate_contract")
        p317_overlay_source_receipts = p317_contract.get("source_receipts")
    elif userspace_overlay_contract_id == MAX77705_OVERLAY_CONTRACT_ID:
        import s22plus_fyg8_p316_qualification_closure as p316_qualification

        p316_contract = _validate_p316_overlay_contract(candidate_contract_value)
        telemetry = p316_contract.get("telemetry")
        observer = p316_contract.get("observer")
        runtime = candidate_static_result.get("p316_runtime_fixture")
        lifecycle = candidate_static_result.get("p316_late_loader_lifecycle")
        adapter = candidate_static_result.get("p316_process_v2_adapter_fixture")
        sidecar = candidate_static_result.get("p316_sidecar_positive_control")
        qualified = candidate_static_result.get("p316_qualification_closure")
        if not isinstance(qualified, dict):
            raise EvidenceError("P3.16 qualification closure is absent")
        try:
            p316_qualification.validate_qualification_artifact(
                qualified,
                root=Path(__file__).resolve().parents[5],
                candidate_tree=qualified.get("candidate_tree"),
            )
        except p316_qualification.QualificationError as exc:
            raise EvidenceError("P3.16 qualification closure is invalid") from exc
        if (
            p316_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p316_contract.get("source_contract_id") != source_contract_id
            or p316_contract.get("profile") != profile
            or p316_contract.get("run_id") != item["run_id"]
            or selected_decoder is not max77705_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("decoder_id") != selected_decoder.DECODER_ID
            or telemetry.get("decoder_policy_id") != selected_decoder.POLICY_ID
            or telemetry.get("verified") is not True
            or not isinstance(observer, dict)
            or observer.get("candidate_window_sec") != 300
            or observer.get("guard_lifetime_sec") != 1200
            or observer.get("final_pair_before_banner") is not True
            or observer.get("usb_sidecar_required") is not True
            or observer.get("verified") is not True
            or not isinstance(runtime, dict)
            or runtime.get("verdict")
            != "PASS_P316_15_DEVICE_RUNTIME_FIXTURE_HOST_ONLY"
            or runtime.get("device_count") != 15
            or runtime.get("target_count") != 3
            or runtime.get("blocked_count") != 12
            or runtime.get("verified") is not True
            or not isinstance(lifecycle, dict)
            or lifecycle.get("verdict")
            != "PASS_P316_LATE_LOADER_LIFECYCLE_HOST_ONLY"
            or lifecycle.get("verified") is not True
            or not isinstance(adapter, dict)
            or adapter.get("verdict")
            != "PASS_MAX77705_REAL_PROCESS_V2_RETAINED_SEMANTICS_HOST_ONLY"
            or adapter.get("verified") is not True
            or not isinstance(sidecar, dict)
            or sidecar.get("verdict")
            != "PASS_P316_USB_SIDECAR_POSITIVE_CONTROL_HOST_ONLY"
            or sidecar.get("verified") is not True
            or qualified.get("schema") != p316_qualification.FINAL_SCHEMA
            or qualified.get("verified") is not True
            or candidate_static_result.get("p316_telemetry") != telemetry
            or candidate_static_result.get("p316_observer") != observer
            or p316_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.16 overlay candidate contract is invalid")
        candidate_contract_value = p316_contract.get("parent_candidate_contract")
        p316_overlay_source_receipts = p316_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P315_OVERLAY_CONTRACT_ID:
        p315_contract = _validate_p315_overlay_contract(candidate_contract_value)
        telemetry = p315_contract.get("telemetry")
        cross_gate = p315_contract.get("cross_gate_audit")
        geometry = p315_contract.get("restart_source_geometry")
        abi = p315_contract.get("tracefs_abi")
        observer = p315_contract.get("observer")
        prepackaging = p315_contract.get("prepackaging_closure")
        matrix = p315_contract.get("matrix_fixture")
        fixture = candidate_static_result.get("p315_runtime_fixture")
        adapter_fixture = candidate_static_result.get(
            "p315_process_v2_adapter_fixture"
        )
        qualification = candidate_static_result.get("p315_qualification_closure")
        if not isinstance(qualification, dict):
            raise EvidenceError("P3.15 qualification closure is absent")
        try:
            p315_design.validate_qualification_artifact(
                qualification,
                root=Path(__file__).resolve().parents[5],
                candidate_tree=qualification.get("artifacts", {}).get(
                    "candidate_tree"
                ),
            )
        except p315_design.P315DesignError as exc:
            raise EvidenceError("P3.15 qualification closure is invalid") from exc
        if (
            p315_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p315_contract.get("source_contract_id") != source_contract_id
            or p315_contract.get("profile") != profile
            or p315_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p315_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != p315_spec.SCHEMA
            or telemetry.get("a_output_count") != 126
            or telemetry.get("b_output_count") != 2222
            or telemetry.get("matrix_b_value_count") != 2223
            or telemetry.get("pair_mask_detail_range") != [0x6C01, 0x6FFF]
            or telemetry.get("reserved_detail_names")
            != {
                "0x6721": "profile-only-nested-hit",
                "0x6722": "gadget-start-zero-without-run-on",
                "0x6723": "run-on-provenance-contradiction",
            }
            or telemetry.get("decoder_id") != selected_decoder.DECODER_ID
            or telemetry.get("decoder_policy_id") != selected_decoder.POLICY_ID
            or telemetry.get("verified") is not True
            or not isinstance(cross_gate, dict)
            or cross_gate.get("a_outputs_validated") != 126
            or cross_gate.get("b_outputs_validated") != 2222
            or cross_gate.get("pair_masks_validated") != 1023
            or cross_gate.get("legacy_0x6712_emit_capable") is not False
            or cross_gate.get("reserved_details_validated")
            != [0x6721, 0x6722, 0x6723]
            or cross_gate.get("verified") is not True
            or not isinstance(geometry, dict)
            or geometry.get("verdict")
            != "PASS_P315_RESTART_SOURCE_GEOMETRY_HOST_ONLY"
            or geometry.get("restart_geometry", {}).get("pair_counts")
            != p315_design.RESTART_EXPECTED_COUNTS
            or geometry.get("restart_geometry", {})
            .get("auxiliary_geometry", {})
            .get("total_records")
            != 41
            or geometry.get("verified") is not True
            or not isinstance(abi, dict)
            or abi.get("verified") is not True
            or not isinstance(prepackaging, dict)
            or prepackaging.get("verdict") != p315_design.VERDICT
            or prepackaging.get("requirements_sha256")
            != p315_design.requirements_sha256()
            or prepackaging.get("verified") is not True
            or not isinstance(matrix, dict)
            or matrix.get("matrix_cells") != 251_450
            or matrix.get("real_process_v2_adapter_round_trip") is not True
            or matrix.get("persistence_round_trip") is not True
            or matrix.get("verified") is not True
            or not isinstance(observer, dict)
            or observer.get("role_event_count") != 5
            or observer.get("direct_event_count") != 15
            or observer.get("cycle_event_count") != 25
            or observer.get("record_capacity") != 64
            or observer.get("cycle_record_contract") != [14, 41, 49, 65]
            or observer.get("restart_completion_max_snapshots") != 301
            or observer.get("stop_and_restart_profile_reads") != 2
            or observer.get("guard_lifetime_sec") != 1200
            or observer.get("verified") is not True
            or candidate_static_result.get("p315_tracefs_abi") != abi
            or candidate_static_result.get("p315_cross_gate_audit") != cross_gate
            or candidate_static_result.get("p315_restart_source_geometry")
            != geometry
            or candidate_static_result.get("p315_prepackaging_closure")
            != prepackaging
            or candidate_static_result.get("p315_matrix_fixture") != matrix
            or candidate_static_result.get("p315_telemetry") != telemetry
            or candidate_static_result.get("p315_observer") != observer
            or not isinstance(fixture, dict)
            or fixture.get("verdict")
            != "PASS_P315_RUNTIME_WRAPPER_FIXTURE_HOST_ONLY"
            or fixture.get("restart_clean_records") != 41
            or fixture.get("actual_live_wrapper_executed") is not True
            or fixture.get("verified") is not True
            or not isinstance(adapter_fixture, dict)
            or adapter_fixture.get("verdict")
            != "PASS_P315_PROCESS_V2_ADAPTER_PERSISTENCE_HOST_ONLY"
            or adapter_fixture.get("decoder_id") != selected_decoder.DECODER_ID
            or adapter_fixture.get("policy_id") != selected_decoder.POLICY_ID
            or adapter_fixture.get("matrix_cells") != 251_450
            or adapter_fixture.get("json_safe") is not True
            or adapter_fixture.get("unknown_overlay_rejected") is not True
            or adapter_fixture.get("verified") is not True
            or qualification.get("schema") != p315_design.QUALIFICATION_SCHEMA
            or qualification.get("verified") is not True
            or p315_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.15 overlay candidate contract is invalid")
        candidate_contract_value = p315_contract.get("parent_candidate_contract")
        p315_overlay_source_receipts = p315_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P314_OVERLAY_CONTRACT_ID:
        p314_contract = _validate_p314_overlay_contract(candidate_contract_value)
        telemetry = p314_contract.get("telemetry")
        cross_gate = p314_contract.get("cross_gate_audit")
        abi = p314_contract.get("tracefs_abi")
        observer = p314_contract.get("observer")
        hazards = p314_contract.get("hazard_closure")
        matrix = p314_contract.get("matrix_fixture")
        fixture = candidate_static_result.get("p314_runtime_fixture")
        adapter_fixture = candidate_static_result.get(
            "p314_process_v2_adapter_fixture"
        )
        qualification = candidate_static_result.get("p314_qualification_closure")
        if not isinstance(qualification, dict):
            raise EvidenceError("P3.14 qualification closure is absent")
        try:
            qualification_authority = p314_design.prepackaging_authority(
                Path(__file__).resolve().parents[5], p314_contract
            )
            p314_design.validate_qualification_artifact(
                qualification,
                authority=qualification_authority,
                candidate_tree=qualification.get("artifacts", {}).get(
                    "candidate_tree"
                ),
            )
        except p314_design.P314DesignError as exc:
            raise EvidenceError("P3.14 qualification closure is invalid") from exc
        if (
            p314_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p314_contract.get("source_contract_id") != source_contract_id
            or p314_contract.get("profile") != profile
            or p314_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p314_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != p314_spec.SCHEMA
            or telemetry.get("a_output_count") != 126
            or telemetry.get("b_output_count") != 2222
            or telemetry.get("matrix_b_value_count") != 2223
            or telemetry.get("pair_mask_detail_range") != [0x6C01, 0x6FFF]
            or telemetry.get("pair_mask_output_count") != 1023
            or telemetry.get("legacy_0x6712_decode_only") is not True
            or telemetry.get("decoder_id") != selected_decoder.DECODER_ID
            or telemetry.get("decoder_policy_id") != selected_decoder.POLICY_ID
            or telemetry.get("verified") is not True
            or not isinstance(cross_gate, dict)
            or cross_gate.get("a_outputs_validated") != 126
            or cross_gate.get("b_outputs_validated") != 2222
            or cross_gate.get("pair_masks_validated") != 1023
            or cross_gate.get("legacy_0x6712_emit_capable") is not False
            or cross_gate.get("verified") is not True
            or not isinstance(abi, dict)
            or abi.get("verified") is not True
            or not isinstance(hazards, dict)
            or hazards.get("verdict")
            != "PASS_P314_PREPACKAGING_HAZARD_CLOSURE_HOST_ONLY"
            or hazards.get("verified") is not True
            or not isinstance(matrix, dict)
            or matrix.get("matrix_cells") != 251_450
            or matrix.get("accepted_cells") != 238_094
            or matrix.get("rejected_cells") != 13_356
            or matrix.get("real_process_v2_adapter_round_trip") is not True
            or matrix.get("persistence_round_trip") is not True
            or matrix.get("verified") is not True
            or not isinstance(observer, dict)
            or observer.get("role_event_count") != 5
            or observer.get("direct_event_count") != 15
            or observer.get("cycle_event_count") != 25
            or observer.get("record_capacity") != 64
            or observer.get("cycle_record_contract") != [14, 41, 49, 65]
            or observer.get("diagnostic_continue_enabled") is not False
            or observer.get("guard_lifetime_sec") != 1200
            or observer.get("verified") is not True
            or candidate_static_result.get("p314_tracefs_abi") != abi
            or candidate_static_result.get("p314_cross_gate_audit") != cross_gate
            or candidate_static_result.get("p314_hazard_closure") != hazards
            or candidate_static_result.get("p314_matrix_fixture") != matrix
            or candidate_static_result.get("p314_telemetry") != telemetry
            or candidate_static_result.get("p314_observer") != observer
            or not isinstance(fixture, dict)
            or fixture.get("verdict")
            != "PASS_P314_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY"
            or fixture.get("pair_masks_exercised") != 1023
            or fixture.get("legacy_0x6712_emit_sites_zero") is not True
            or fixture.get("verified") is not True
            or not isinstance(adapter_fixture, dict)
            or adapter_fixture.get("verdict")
            != "PASS_P314_PROCESS_V2_CARRIER_V2_ADAPTER_HOST_ONLY"
            or adapter_fixture.get("decoder_id") != selected_decoder.DECODER_ID
            or adapter_fixture.get("policy_id") != selected_decoder.POLICY_ID
            or adapter_fixture.get("json_safe") is not True
            or adapter_fixture.get("foreign_count_zero") is not True
            or adapter_fixture.get("unknown_overlay_rejected") is not True
            or adapter_fixture.get("verified") is not True
            or qualification.get("schema")
            != "s22plus_fyg8_p314_qualification_closure_v1"
            or qualification.get("verified") is not True
            or p314_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.14 overlay candidate contract is invalid")
        candidate_contract_value = p314_contract.get("parent_candidate_contract")
        p314_overlay_source_receipts = p314_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P313_OVERLAY_CONTRACT_ID:
        p313_contract = _validate_p313_overlay_contract(candidate_contract_value)
        telemetry = p313_contract.get("telemetry")
        cross_gate = p313_contract.get("cross_gate_audit")
        abi = p313_contract.get("tracefs_abi")
        observer = p313_contract.get("observer")
        hazards = p313_contract.get("hazard_closure")
        fixture = candidate_static_result.get("p313_runtime_fixture")
        adapter_fixture = candidate_static_result.get(
            "p313_process_v2_adapter_fixture"
        )
        if (
            p313_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p313_contract.get("source_contract_id") != source_contract_id
            or p313_contract.get("profile") != profile
            or p313_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p313_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != p313_spec.SCHEMA
            or telemetry.get("a_output_count") != 126
            or telemetry.get("b_output_count") != 1200
            or telemetry.get("a_detail_range") != [0xD00, 0xD7D]
            or telemetry.get("normal_detail_range") != [0x4801, 0x4C00]
            or telemetry.get("direct_detail_range") != [0x4C01, 0x4C02]
            or telemetry.get("controller_detail_range") != [0x5001, 0x5050]
            or telemetry.get("drift_detail_range") != [0x5061, 0x507F]
            or telemetry.get("contradiction_detail_range") != [0x6701, 0x673F]
            or telemetry.get("decoder_id") != selected_decoder.DECODER_ID
            or telemetry.get("decoder_policy_id") != selected_decoder.POLICY_ID
            or telemetry.get("verified") is not True
            or not isinstance(cross_gate, dict)
            or cross_gate.get("a_outputs_validated") != 126
            or cross_gate.get("b_outputs_validated") != 1200
            or cross_gate.get("retained_pair_round_trip") is not True
            or cross_gate.get("foreign_count_zero") is not True
            or cross_gate.get("verified") is not True
            or not isinstance(abi, dict)
            or abi.get("verified") is not True
            or not isinstance(hazards, dict)
            or hazards.get("verdict")
            != "PASS_P313_OBSERVER_HAZARD_CLOSURE_HOST_ONLY"
            or hazards.get("verified") is not True
            or not isinstance(observer, dict)
            or observer.get("role_event_count") != 5
            or observer.get("direct_event_count") != 15
            or observer.get("cycle_event_count") != 25
            or observer.get("record_capacity") != 64
            or observer.get("direct_prefix_capacity") != 32
            or observer.get("cycle_record_contract") != [37, 45, 65]
            or observer.get("profile_hits_lower_bound_records") is not True
            or observer.get("profile_missed_must_be_zero") is not True
            or observer.get("ring_loss_must_be_zero") is not True
            or observer.get("final_pair_before_banner") is not True
            or observer.get("candidate_window_sec") != 300
            or observer.get("guard_lifetime_sec") != 1200
            or observer.get("verified") is not True
            or candidate_static_result.get("p313_tracefs_abi") != abi
            or candidate_static_result.get("p313_cross_gate_audit") != cross_gate
            or candidate_static_result.get("p313_hazard_closure") != hazards
            or candidate_static_result.get("p313_telemetry") != telemetry
            or candidate_static_result.get("p313_observer") != observer
            or not isinstance(fixture, dict)
            or fixture.get("verdict")
            != "PASS_P313_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY"
            or fixture.get("legacy_four_event_semantics_preserved") is not True
            or fixture.get("strict_five_event_role_matrix") is not True
            or fixture.get("profile_excess_accepted") is not True
            or fixture.get("profile_deficit_rejected") is not True
            or fixture.get("verified") is not True
            or not isinstance(adapter_fixture, dict)
            or adapter_fixture.get("verdict")
            != "PASS_P313_PROCESS_V2_CARRIER_V2_ADAPTER_HOST_ONLY"
            or adapter_fixture.get("decoder_id") != selected_decoder.DECODER_ID
            or adapter_fixture.get("policy_id") != selected_decoder.POLICY_ID
            or adapter_fixture.get("json_safe") is not True
            or adapter_fixture.get("foreign_count_zero") is not True
            or adapter_fixture.get("unknown_overlay_rejected") is not True
            or adapter_fixture.get("verified") is not True
            or p313_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.13 overlay candidate contract is invalid")
        candidate_contract_value = p313_contract.get("parent_candidate_contract")
        p313_overlay_source_receipts = p313_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
        p312_contract = _validate_p312_overlay_contract(candidate_contract_value)
        telemetry = p312_contract.get("telemetry")
        cross_gate = p312_contract.get("cross_gate_audit")
        carrier_authority = p312_contract.get("carrier_decoder_authority")
        callsites = p312_contract.get("callsite_audit", {}).get("result", {})
        delayed = p312_contract.get("delayed_arm_qemu", {}).get("result", {})
        abi = p312_contract.get("tracefs_abi")
        observer = p312_contract.get("observer")
        fixture = candidate_static_result.get("p312_runtime_fixture")
        if (
            p312_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p312_contract.get("source_contract_id") != source_contract_id
            or p312_contract.get("profile") != profile
            or p312_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p312_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != "s22plus_fyg8_p312_telemetry_spec_v1"
            or telemetry.get("early_event_count") != 30
            or telemetry.get("callsite_count") != 24
            or telemetry.get("first_detail_range") != [0xD00, 0xD51]
            or telemetry.get("summary_detail_range") != [0x4001, 0x4640]
            or telemetry.get("profile_hits_may_exceed_records_outside_recording_window")
            is not True
            or telemetry.get("decoder_id") != selected_decoder.DECODER_ID
            or telemetry.get("decoder_policy_id") != selected_decoder.POLICY_ID
            or telemetry.get("verified") is not True
            or not isinstance(cross_gate, dict)
            or cross_gate.get("verified") is not True
            or cross_gate.get("retained_pair_round_trip") is not True
            or cross_gate.get("foreign_count_zero") is not True
            or not isinstance(carrier_authority, dict)
            or carrier_authority.get("verdict")
            != "PASS_P312_CARRIER_DECODER_CROSS_AUTHORITY_HOST_ONLY"
            or carrier_authority.get("p311_historical_mismatch_rejected") is not True
            or carrier_authority.get("p312_carrier_v2_json_safe") is not True
            or carrier_authority.get("records_generated_by_source_carrier") is not True
            or carrier_authority.get("verified") is not True
            or callsites.get("verdict")
            != "PASS_P311_24_EXACT_POST_BL_CALLSITES_HOST_ONLY"
            or callsites.get("callsite_count") != 24
            or delayed.get("verdict")
            != "PASS_P311_DELAYED_MODULE_KPROBE_QEMU_HOST_ONLY"
            or not isinstance(abi, dict)
            or abi.get("verified") is not True
            or not isinstance(observer, dict)
            or observer.get("pending_module_local_probes") is not True
            or observer.get("global_clock_probe") is not False
            or observer.get("event_count") != 30
            or observer.get("profile_hits_lower_bound_records") is not True
            or observer.get("profile_missed_must_be_zero") is not True
            or observer.get("semantic_call_pairs_complete") is not True
            or observer.get("ring_loss_must_be_zero") is not True
            or observer.get("carrier_v2_family") != "S22E1L2|"
            or observer.get("verified") is not True
            or candidate_static_result.get("p312_callsite_audit")
            != p312_contract.get("callsite_audit")
            or candidate_static_result.get("p312_delayed_arm_qemu")
            != p312_contract.get("delayed_arm_qemu")
            or candidate_static_result.get("p312_tracefs_abi") != abi
            or candidate_static_result.get("p312_cross_gate_audit") != cross_gate
            or candidate_static_result.get("p312_carrier_decoder_authority")
            != carrier_authority
            or candidate_static_result.get("p312_telemetry") != telemetry
            or candidate_static_result.get("p312_observer") != observer
            or not isinstance(fixture, dict)
            or fixture.get("verdict")
            != "PASS_P312_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY"
            or fixture.get("fixture_count") != 9
            or fixture.get("profile_excess_accepted") is not True
            or fixture.get("profile_below_records_rejected") is not True
            or fixture.get("verified") is not True
            or p312_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.12 overlay candidate contract is invalid")
        candidate_contract_value = p312_contract.get("parent_candidate_contract")
        p312_overlay_source_receipts = p312_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
        p311_contract = _validate_p311_overlay_contract(candidate_contract_value)
        telemetry = p311_contract.get("telemetry")
        cross_gate = p311_contract.get("cross_gate_audit")
        callsites = p311_contract.get("callsite_audit", {}).get("result", {})
        delayed = p311_contract.get("delayed_arm_qemu", {}).get("result", {})
        abi = p311_contract.get("tracefs_abi")
        observer = p311_contract.get("observer")
        fixture = candidate_static_result.get("p311_runtime_fixture")
        if (
            p311_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p311_contract.get("source_contract_id") != source_contract_id
            or p311_contract.get("profile") != profile
            or p311_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p311_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != "s22plus_fyg8_p311_telemetry_spec_v1"
            or telemetry.get("early_event_count") != 30
            or telemetry.get("callsite_count") != 24
            or telemetry.get("first_detail_range") != [0xD00, 0xD51]
            or telemetry.get("summary_detail_range") != [0x4001, 0x4640]
            or telemetry.get("decoder_id") != selected_decoder.DECODER_ID
            or telemetry.get("decoder_policy_id") != selected_decoder.POLICY_ID
            or telemetry.get("verified") is not True
            or not isinstance(cross_gate, dict)
            or cross_gate.get("verified") is not True
            or callsites.get("verdict")
            != "PASS_P311_24_EXACT_POST_BL_CALLSITES_HOST_ONLY"
            or callsites.get("callsite_count") != 24
            or delayed.get("verdict")
            != "PASS_P311_DELAYED_MODULE_KPROBE_QEMU_HOST_ONLY"
            or not isinstance(abi, dict)
            or abi.get("verified") is not True
            or not isinstance(observer, dict)
            or observer.get("pending_module_local_probes") is not True
            or observer.get("global_clock_probe") is not False
            or observer.get("event_count") != 30
            or observer.get("verified") is not True
            or candidate_static_result.get("p311_callsite_audit")
            != p311_contract.get("callsite_audit")
            or candidate_static_result.get("p311_delayed_arm_qemu")
            != p311_contract.get("delayed_arm_qemu")
            or candidate_static_result.get("p311_tracefs_abi") != abi
            or candidate_static_result.get("p311_cross_gate_audit") != cross_gate
            or candidate_static_result.get("p311_telemetry") != telemetry
            or candidate_static_result.get("p311_observer") != observer
            or not isinstance(fixture, dict)
            or fixture.get("verdict")
            != "PASS_P311_MATERIALIZED_RUNTIME_FIXTURES_HOST_ONLY"
            or fixture.get("fixture_count") != 8
            or fixture.get("verified") is not True
            or p311_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.11 overlay candidate contract is invalid")
        candidate_contract_value = p311_contract.get("parent_candidate_contract")
        p311_overlay_source_receipts = p311_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P308_OVERLAY_CONTRACT_ID:
        p308_contract = _validate_p308_overlay_contract(candidate_contract_value)
        p307_contract = _validate_p307_overlay_contract(
            p308_contract.get("parent_overlay_contract")
        )
        p305_contract = _validate_p305_overlay_contract(
            p307_contract.get("parent_overlay_contract")
        )
        p304_contract = _validate_p304_overlay_contract(
            p305_contract.get("parent_overlay_contract")
        )
        p303_contract = _validate_p303_overlay_contract(
            p304_contract.get("parent_overlay_contract")
        )
        parent_overlay = p303_contract.get("parent_overlay_contract")
        expected_observer = {
            "kmsg_opened_before_modules": True,
            "eud_cache_path": p307_spec.EUD_CACHE_PATH,
            "eud_cache_read_after_module_index": p307_spec.EUD_MODULE_INDEX,
            "eud_cache_read_count": 1,
            "message_body_ends_at_first_literal_lf": True,
            "dictionary_suffix_excluded": True,
            "local_parser_failure_latched": True,
            "local_parser_failure_drain_continues": True,
            "parent_kmsg_integrity_errors_remain_immediate": True,
            "degraded_pair_preserves_clock_qscratch_site_prefix_mask": True,
            "raw_excerpt_retained": False,
            "kernel_changed": False,
            "module_plan_changed": False,
            "carrier_changed": False,
            "log_level_changed": False,
            "read_only": True,
            "verified": True,
        }
        telemetry = p308_contract.get("telemetry")
        cross_gate = p308_contract.get("cross_gate_audit")
        qscratch = p308_contract.get("qscratch_audit")
        if (
            p308_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p308_contract.get("parent_overlay_contract_id")
            != P307_OVERLAY_CONTRACT_ID
            or p308_contract.get("source_contract_id") != source_contract_id
            or p308_contract.get("profile") != profile
            or p308_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p308_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != p308_spec.SCHEMA
            or telemetry.get("enumerated_family_value_count") != 5988
            or telemetry.get("summary_detail_range") != [0x4001, 0x4FEB]
            or telemetry.get("degraded_detail_range") != [0x6100, 0x673F]
            or telemetry.get("verified") is not True
            or not isinstance(cross_gate, dict)
            or cross_gate.get("verified") is not True
            or cross_gate.get("telemetry") != telemetry
            or p308_contract.get("observer") != expected_observer
            or p308_contract.get("callsite_audit", {}).get("verified") is not True
            or p308_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or not isinstance(qscratch, dict)
            or qscratch.get("verified") is not True
            or qscratch.get("probe", {}).get("offset")
            != p307_spec.QSCRATCH_PROBE_OFFSET
            or p308_contract.get("module_delta", {}).get("verified") is not True
            or p308_contract.get("module_delta", {}).get("plan_count_after") != 61
            or p308_contract.get("folded_tail", {}).get("verified") is not True
            or p307_contract.get("userspace_overlay_contract_id")
            != P307_OVERLAY_CONTRACT_ID
            or p305_contract.get("userspace_overlay_contract_id")
            != P305_OVERLAY_CONTRACT_ID
            or p304_contract.get("userspace_overlay_contract_id")
            != P304_OVERLAY_CONTRACT_ID
            or p303_contract.get("userspace_overlay_contract_id")
            != P303_OVERLAY_CONTRACT_ID
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p308_contract.get("carrier_v2_design_input", {}).get(
                "raw_excerpt_must_not_create_foreign_family_count"
            ) is not True
            or p308_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.08 loss-resistant overlay candidate contract is invalid")
        if (
            candidate_static_result.get("p303_callsite_audit")
            != p308_contract.get("callsite_audit")
            or candidate_static_result.get("p307_qscratch_audit") != qscratch
            or candidate_static_result.get("p308_telemetry") != telemetry
            or candidate_static_result.get("p308_observer") != expected_observer
            or candidate_static_result.get("p308_cross_gate_audit") != cross_gate
        ):
            raise EvidenceError("P3.08 observer proof is invalid")
        candidate_contract_value = p308_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
        p304_overlay_source_receipts = p304_contract.get("source_receipts")
        p305_overlay_source_receipts = p305_contract.get("source_receipts")
        p307_overlay_source_receipts = p307_contract.get("source_receipts")
        p308_overlay_source_receipts = p308_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P307_OVERLAY_CONTRACT_ID:
        p307_contract = _validate_p307_overlay_contract(candidate_contract_value)
        p305_contract = _validate_p305_overlay_contract(
            p307_contract.get("parent_overlay_contract")
        )
        p304_contract = _validate_p304_overlay_contract(
            p305_contract.get("parent_overlay_contract")
        )
        p303_contract = _validate_p303_overlay_contract(
            p304_contract.get("parent_overlay_contract")
        )
        parent_overlay = p303_contract.get("parent_overlay_contract")
        expected_observer = {
            "kmsg_opened_before_modules": True,
            "eud_cache_path": p307_spec.EUD_CACHE_PATH,
            "eud_cache_read_after_module_index": p307_spec.EUD_MODULE_INDEX,
            "eud_cache_read_count": 1,
            "ordered_first_init_attribution": True,
            "qscratch_module": p307_spec.DWC3_MODULE_RUNTIME_NAME,
            "qscratch_symbol": p307_spec.QSCRATCH_SYMBOL,
            "qscratch_offset": p307_spec.QSCRATCH_PROBE_OFFSET,
            "qscratch_register": "w21",
            "kernel_changed": False,
            "module_plan_changed": False,
            "log_level_changed": False,
            "read_only": True,
            "verified": True,
        }
        telemetry = p307_contract.get("telemetry")
        qscratch = p307_contract.get("qscratch_audit")
        if (
            p307_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p307_contract.get("parent_overlay_contract_id")
            != P305_OVERLAY_CONTRACT_ID
            or p307_contract.get("source_contract_id") != source_contract_id
            or p307_contract.get("profile") != profile
            or p307_contract.get("run_id") != item["run_id"]
            or selected_decoder is not p307_decoder
            or not isinstance(telemetry, dict)
            or telemetry.get("schema") != p307_spec.SCHEMA
            or telemetry.get("attribution_detail_range") != [0xD00, 0xD95]
            or telemetry.get("summary_detail_range") != [0x4001, 0x4FEB]
            or telemetry.get("qscratch_state_count") != 25
            or telemetry.get("verified") is not True
            or p307_contract.get("observer") != expected_observer
            or p307_contract.get("callsite_audit", {}).get("verified") is not True
            or p307_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or not isinstance(qscratch, dict)
            or qscratch.get("verified") is not True
            or qscratch.get("probe", {}).get("offset")
            != p307_spec.QSCRATCH_PROBE_OFFSET
            or p307_contract.get("module_delta", {}).get("verified") is not True
            or p307_contract.get("module_delta", {}).get("plan_count_after") != 61
            or p307_contract.get("folded_tail", {}).get("verified") is not True
            or p305_contract.get("userspace_overlay_contract_id")
            != P305_OVERLAY_CONTRACT_ID
            or p304_contract.get("userspace_overlay_contract_id")
            != P304_OVERLAY_CONTRACT_ID
            or p303_contract.get("userspace_overlay_contract_id")
            != P303_OVERLAY_CONTRACT_ID
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p307_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.07 EUD/QSCRATCH overlay candidate contract is invalid")
        if (
            candidate_static_result.get("p303_callsite_audit")
            != p307_contract.get("callsite_audit")
            or candidate_static_result.get("p307_qscratch_audit") != qscratch
            or candidate_static_result.get("p307_telemetry") != telemetry
            or candidate_static_result.get("p307_observer") != expected_observer
        ):
            raise EvidenceError("P3.07 EUD/QSCRATCH observer proof is invalid")
        candidate_contract_value = p307_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
        p304_overlay_source_receipts = p304_contract.get("source_receipts")
        p305_overlay_source_receipts = p305_contract.get("source_receipts")
        p307_overlay_source_receipts = p307_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
        p306_contract = _validate_p306_overlay_contract(candidate_contract_value)
        p305_contract = _validate_p305_overlay_contract(
            p306_contract.get("parent_overlay_contract")
        )
        p304_contract = _validate_p304_overlay_contract(
            p305_contract.get("parent_overlay_contract")
        )
        p303_contract = _validate_p303_overlay_contract(
            p304_contract.get("parent_overlay_contract")
        )
        parent_overlay = p303_contract.get("parent_overlay_contract")
        expected_observer = {
            "path": "/sys/kernel/debug/ipc_logging/a600000_ssusb/log",
            "armed_after_module_index": 58,
            "armed_before_module_index": 59,
            "kernel_changed": False,
            "module_plan_changed": False,
            "log_level_changed": False,
            "passive_read_only": True,
            "verified": True,
        }
        ipc_telemetry = p306_contract.get("ipc_telemetry")
        if (
            p306_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p306_contract.get("parent_overlay_contract_id")
            != P305_OVERLAY_CONTRACT_ID
            or p306_contract.get("source_contract_id") != source_contract_id
            or p306_contract.get("profile") != profile
            or p306_contract.get("run_id") != item["run_id"]
            or not isinstance(ipc_telemetry, dict)
            or ipc_telemetry.get("schema")
            != "s22plus_fyg8_p306_ipc_state_telemetry_spec_v1"
            or ipc_telemetry.get("chain_detail_range") != [0xD01, 0xD80]
            or ipc_telemetry.get("summary_detail_range") != [0x4001, 0x4800]
            or ipc_telemetry.get("verified") is not True
            or p306_contract.get("observer") != expected_observer
            or p306_contract.get("callsite_audit", {}).get("verified") is not True
            or p306_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or p306_contract.get("module_delta", {}).get("verified") is not True
            or p306_contract.get("module_delta", {}).get("plan_count_after") != 61
            or p306_contract.get("folded_tail", {}).get("verified") is not True
            or p305_contract.get("userspace_overlay_contract_id")
            != P305_OVERLAY_CONTRACT_ID
            or p304_contract.get("userspace_overlay_contract_id")
            != P304_OVERLAY_CONTRACT_ID
            or p303_contract.get("userspace_overlay_contract_id")
            != P303_OVERLAY_CONTRACT_ID
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p306_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.06 IPC overlay candidate contract is invalid")
        if (
            candidate_static_result.get("p303_callsite_audit")
            != p306_contract.get("callsite_audit")
            or candidate_static_result.get("p306_ipc_telemetry") != ipc_telemetry
            or candidate_static_result.get("p306_observer") != expected_observer
        ):
            raise EvidenceError("P3.06 IPC observer proof is invalid")
        candidate_contract_value = p306_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
        p304_overlay_source_receipts = p304_contract.get("source_receipts")
        p305_overlay_source_receipts = p305_contract.get("source_receipts")
        p306_overlay_source_receipts = p306_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P305_OVERLAY_CONTRACT_ID:
        p305_contract = _validate_p305_overlay_contract(candidate_contract_value)
        p304_contract = _validate_p304_overlay_contract(
            p305_contract.get("parent_overlay_contract")
        )
        p303_contract = _validate_p303_overlay_contract(
            p304_contract.get("parent_overlay_contract")
        )
        parent_overlay = p303_contract.get("parent_overlay_contract")
        if (
            p305_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p305_contract.get("parent_overlay_contract_id")
            != P304_OVERLAY_CONTRACT_ID
            or p305_contract.get("source_contract_id") != source_contract_id
            or p305_contract.get("profile") != profile
            or p305_contract.get("run_id") != item["run_id"]
            or p305_contract.get("telemetry", {}).get("decoder_id")
            != selected_decoder.DECODER_ID
            or p305_contract.get("telemetry", {}).get("decoder_policy_id")
            != selected_decoder.POLICY_ID
            or p305_contract.get("callsite_audit", {}).get("verified") is not True
            or p305_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or p305_contract.get("module_delta", {}).get("verified") is not True
            or p305_contract.get("module_delta", {}).get("plan_count_after") != 61
            or p305_contract.get("folded_tail", {}).get("verified") is not True
            or p305_contract.get("folded_tail", {}).get("later_ordinals_unchanged")
            is not True
            or p305_contract.get("folded_tail", {}).get("success_stage") != 0x7B
            or p305_contract.get("folded_tail", {}).get("first_gate_stage") != 0x7C
            or p304_contract.get("userspace_overlay_contract_id")
            != P304_OVERLAY_CONTRACT_ID
            or p304_contract.get("parent_overlay_contract_id")
            != P303_OVERLAY_CONTRACT_ID
            or p303_contract.get("parent_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p305_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.05 overlay candidate contract is invalid")
        callsites = candidate_static_result.get("p303_callsite_audit")
        offset_rule = _exact(
            candidate_static_result.get("p303_offset_probe_rule"),
            {
                "p300_epilogue_rejection_preserved",
                "immediate_post_bl_only",
                "w0_immediately_consumed",
                "fixed_module_receipt_shared_by_candidate_a_b",
                "hit_zero_distinct_from_rc_zero",
                "verified",
            },
            "P3.05 inherited post-BL offset probe rule",
        )
        if (
            callsites != p305_contract.get("callsite_audit")
            or candidate_static_result.get("p305_folded_tail")
            != p305_contract.get("folded_tail")
            or any(value is not True for value in offset_rule.values())
        ):
            raise EvidenceError("P3.05 folded-tail or callsite proof is invalid")
        candidate_contract_value = p305_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
        p304_overlay_source_receipts = p304_contract.get("source_receipts")
        p305_overlay_source_receipts = p305_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P304_OVERLAY_CONTRACT_ID:
        p304_contract = _validate_p304_overlay_contract(candidate_contract_value)
        p303_contract = _validate_p303_overlay_contract(
            p304_contract.get("parent_overlay_contract")
        )
        parent_overlay = p303_contract.get("parent_overlay_contract")
        if (
            p304_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p304_contract.get("parent_overlay_contract_id")
            != P303_OVERLAY_CONTRACT_ID
            or p304_contract.get("source_contract_id") != source_contract_id
            or p304_contract.get("profile") != profile
            or p304_contract.get("run_id") != item["run_id"]
            or p304_contract.get("telemetry", {}).get("decoder_id")
            != selected_decoder.DECODER_ID
            or p304_contract.get("telemetry", {}).get("decoder_policy_id")
            != selected_decoder.POLICY_ID
            or p304_contract.get("callsite_audit", {}).get("verified") is not True
            or p304_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or p304_contract.get("module_delta", {}).get("verified") is not True
            or p304_contract.get("module_delta", {}).get("plan_count_after") != 61
            or p304_contract.get("module_delta", {}).get("module", {}).get("sha256")
            != p304_overlay.MODULE_SHA256
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p304_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.04 overlay candidate contract is invalid")
        callsites = candidate_static_result.get("p303_callsite_audit")
        offset_rule = _exact(
            candidate_static_result.get("p303_offset_probe_rule"),
            {
                "p300_epilogue_rejection_preserved",
                "immediate_post_bl_only",
                "w0_immediately_consumed",
                "fixed_module_receipt_shared_by_candidate_a_b",
                "hit_zero_distinct_from_rc_zero",
                "verified",
            },
            "P3.04 inherited post-BL offset probe rule",
        )
        if (
            callsites != p304_contract.get("callsite_audit")
            or any(value is not True for value in offset_rule.values())
        ):
            raise EvidenceError("P3.04 inherited callsite proof is invalid")
        candidate_contract_value = p304_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
        p304_overlay_source_receipts = p304_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P303_OVERLAY_CONTRACT_ID:
        p303_contract = _validate_p303_overlay_contract(candidate_contract_value)
        parent_overlay = p303_contract.get("parent_overlay_contract")
        if (
            p303_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p303_contract.get("parent_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p303_contract.get("source_contract_id") != source_contract_id
            or p303_contract.get("profile") != profile
            or p303_contract.get("run_id") != item["run_id"]
            or p303_contract.get("telemetry", {}).get("decoder_id")
            != selected_decoder.DECODER_ID
            or p303_contract.get("telemetry", {}).get("decoder_policy_id")
            != selected_decoder.POLICY_ID
            or p303_contract.get("callsite_audit", {}).get("verified") is not True
            or p303_contract.get("callsite_audit", {}).get("callsite_count") != 12
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p303_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.03 overlay candidate contract is invalid")
        callsites = candidate_static_result.get("p303_callsite_audit")
        offset_rule = _exact(
            candidate_static_result.get("p303_offset_probe_rule"),
            {
                "p300_epilogue_rejection_preserved",
                "immediate_post_bl_only",
                "w0_immediately_consumed",
                "fixed_module_receipt_shared_by_candidate_a_b",
                "hit_zero_distinct_from_rc_zero",
                "verified",
            },
            "P3.03 post-BL offset probe rule",
        )
        if (
            callsites != p303_contract.get("callsite_audit")
            or any(value is not True for value in offset_rule.values())
        ):
            raise EvidenceError("P3.03 post-BL callsite proof is invalid")
        candidate_contract_value = p303_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p303_overlay_source_receipts = p303_contract.get("source_receipts")
    elif userspace_overlay_contract_id == P302_OVERLAY_CONTRACT_ID:
        p302_contract = _validate_p302_overlay_contract(candidate_contract_value)
        parent_overlay = p302_contract.get("parent_overlay_contract")
        if (
            p302_contract.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
            or p302_contract.get("parent_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p302_contract.get("source_contract_id") != source_contract_id
            or p302_contract.get("profile") != profile
            or p302_contract.get("run_id") != item["run_id"]
            or p302_contract.get("telemetry", {}).get("decoder_id")
            != selected_decoder.DECODER_ID
            or p302_contract.get("telemetry", {}).get("decoder_policy_id")
            != selected_decoder.POLICY_ID
            or p302_contract.get("carrier", {}).get("id")
            != "P302_ELECTRICAL_CARRIER_V1"
            or p302_contract.get("carrier", {}).get("execution_delta")
            != "nonalloc_elf_identity_section_only"
            or not isinstance(parent_overlay, dict)
            or parent_overlay.get("userspace_overlay_contract_id")
            != P301_OVERLAY_CONTRACT_ID
            or p302_contract.get("verified") is not True
        ):
            raise EvidenceError("P3.02 overlay candidate contract is invalid")
        candidate_contract_value = p302_contract.get("parent_candidate_contract")
        p301_overlay_source_receipts = parent_overlay.get("source_receipts")
        p302_overlay_source_receipts = p302_contract.get("source_receipts")
        carrier_identity = _exact(
            candidate_static_result.get("carrier_identity"),
            {
                "carrier_id",
                "section",
                "section_allocatable",
                "alloc_sections_byte_identical",
                "elf_header_execution_fields_identical",
                "program_headers_byte_identical",
                "program_segment_bytes_identical_except_section_table_fields",
                "file_prefix_and_padding_identical_except_section_table_fields",
                "identity_section_exact",
                "identity_in_program_segment",
                "baseline_size",
                "carried_size",
                "parent_init",
                "parent_child",
                "child_byte_identical",
                "fixed_image_sha256",
                "kernel_rebuilt",
                "module_binaries_injected",
                "verified",
            },
            "P3.02 carrier identity",
        )
        _binary_identity(carrier_identity["parent_init"], "P3.02 parent init")
        _binary_identity(carrier_identity["parent_child"], "P3.02 parent child")
        if (
            carrier_identity.get("carrier_id")
            != p302_contract.get("carrier", {}).get("id")
            or carrier_identity.get("section")
            != p302_contract.get("carrier", {}).get("section")
            or carrier_identity.get("section_allocatable") is not False
            or carrier_identity.get("alloc_sections_byte_identical")
            != [".text", ".rodata", ".data.rel.ro", ".data", ".bss"]
            or carrier_identity.get("elf_header_execution_fields_identical")
            is not True
            or carrier_identity.get("program_headers_byte_identical") is not True
            or carrier_identity.get(
                "program_segment_bytes_identical_except_section_table_fields"
            )
            is not True
            or carrier_identity.get(
                "file_prefix_and_padding_identical_except_section_table_fields"
            )
            is not True
            or carrier_identity.get("identity_section_exact") is not True
            or carrier_identity.get("identity_in_program_segment") is not False
            or type(carrier_identity.get("baseline_size")) is not int
            or type(carrier_identity.get("carried_size")) is not int
            or carrier_identity["baseline_size"] <= 0
            or carrier_identity["carried_size"] <= carrier_identity["baseline_size"]
            or carrier_identity.get("child_byte_identical") is not True
            or carrier_identity.get("fixed_image_sha256")
            != p302_contract.get("fixed_image", {}).get("sha256")
            or carrier_identity.get("kernel_rebuilt") is not False
            or carrier_identity.get("module_binaries_injected") != 0
            or carrier_identity.get("verified") is not True
        ):
            raise EvidenceError("P3.02 carrier identity is invalid")
    source_contract = _exact(
        candidate_contract_value,
        source_contract_keys,
        "E1A candidate source contract",
    )
    if source_contract.get("source_contract_id") != source_contract_id:
        raise EvidenceError("candidate source contract selector mismatch")
    run_id = bytes.fromhex(item["run_id"])
    candidate_source_receipts = validate_candidate_source_preimage(
        source_contract, profile, item["run_id"]
    )
    if source_contract_id is not None:
        selected_contract = _selected_contract(source_contract_id, profile)
        materialized = _exact(
            source_contract.get("materialized_sources"),
            set(selected_contract.materialized_filenames),
            "versioned materialized source contract",
        )
        for name, filename in selected_contract.materialized_filenames.items():
            row = _exact(
                materialized.get(name),
                {"path", "size", "sha256"},
                f"versioned materialized source {name}",
            )
            if (
                row.get("path") != f"materialized-sources/{filename}"
                or {
                    key: row.get(key) for key in ("size", "sha256")
                }
                != candidate_source_receipts[name]
            ):
                raise EvidenceError(
                    f"versioned materialized source identity mismatch: {name}"
                )
    unsat_record = source_decoder.model.unsat_record(profile, run_id)
    unsat_tag = unsat_record[len(source_decoder.model.UNSAT_FAMILY) :]
    expected_config_lines = [
        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y",
        f"CONFIG_S22PLUS_FYG8_E1_PROFILE={source_decoder.model.PROFILE_NUMBERS[profile]}",
        f'CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{item["run_id"]}"',
        f'CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="{unsat_tag.hex()}"',
    ]
    source_intent = _binary_identity(
        source_contract["intent"], "E1A candidate intent"
    )
    expected_base_files = _candidate_base_files(source_contract_id, profile)
    source_base_files = _exact(
        source_contract["base_files"],
        set(expected_base_files),
        "E1A candidate base files",
    )
    source_patched_files = _exact(
        source_contract["patched_files"],
        set(expected_base_files),
        "E1A candidate patched files",
    )
    source_patch = _exact(
        source_contract["patch"],
        {
            "size",
            "sha256",
            "targets",
            "base_files",
            "patched_files",
            "config_lines",
            "clean_apply",
            "verified",
        },
        "E1A candidate patch",
    )
    _binary_identity(
        {name: source_patch[name] for name in ("size", "sha256")},
        "E1A candidate patch",
    )
    _validate_reachable_record_contract(
        source_contract["reachable_record_contract"],
        profile,
        source_contract_id,
        item["run_id"],
    )
    source_contract_safety = _exact(
        source_contract["safety"],
        {
            "host_only",
            "device_contact",
            "device_write",
            "odin_invoked",
            "live_authorized",
        },
        "E1A candidate contract safety",
    )
    expected_contract_schema = (
        _selected_contract(
            source_contract_id, profile
        ).contract_schema
        if source_contract_id is not None
        else E1_LATEST_STAGE_CANDIDATE_CONTRACT_SCHEMA
    )
    expected_contract_verdict = (
        _selected_contract(
            source_contract_id, profile
        ).contract_verdict
        if source_contract_id is not None
        else E1_LATEST_STAGE_CANDIDATE_CONTRACT_VERDICT
    )
    if (
        source_contract.get("schema") != expected_contract_schema
        or source_contract.get("target") != PID1_USERSPACE_TARGET
        or source_contract.get("verdict") != expected_contract_verdict
        or source_contract.get("profile") != item["profile"]
        or type(source_contract.get("profile_number")) is not int
        or source_contract.get("profile_number")
        != source_decoder.model.PROFILE_NUMBERS[profile]
        or source_contract.get("run_id") != item["run_id"]
        or source_contract.get("unsat_record_hex") != unsat_record.hex()
        or source_contract.get("unsat_tag_hex") != unsat_tag.hex()
        or source_contract.get("decoder_id") != source_decoder.DECODER_ID
        or source_contract.get("decoder_policy_id")
        != source_decoder.POLICY_ID
        or source_base_files != expected_base_files
        or any(
            not isinstance(value, str) or HASH_RE.fullmatch(value) is None
            for value in source_patched_files.values()
        )
        or source_patch["targets"] != sorted(expected_base_files)
        or source_patch["base_files"] != source_base_files
        or source_patch["patched_files"] != source_patched_files
        or source_patch["config_lines"] != expected_config_lines
        or source_patch["clean_apply"] is not True
        or source_patch["verified"] is not True
        or source_contract["config_lines"] != expected_config_lines
        or any(type(value) is not bool for value in source_contract_safety.values())
        or source_contract_safety
        != {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        }
        or source_contract.get("verified") is not True
    ):
        raise EvidenceError(
            "candidate static source contract is not E1A-bound, E1B-bound, or E2-bound"
        )
    source_build_keys = {
        "result",
        "image",
        "fresh_reverification",
        "two_clean_builds_byte_identical",
        "linked_audit_verified",
    }
    if source_contract_id == P298_SOURCE_CONTRACT_ID:
        source_build_keys.update(
            {"immutable_build_time_proof_revalidated", "tier2_repair"}
        )
    source_build = _exact(
        candidate_static_result.get("build_repro"),
        source_build_keys,
        "E1A candidate static build closure",
    )
    p298_repair_files = None
    if source_contract_id == P298_SOURCE_CONTRACT_ID:
        p298_repair_files = _validate_p298_historical_build_repair(source_build)
    if (
        not isinstance(source_build, dict)
        or (
            source_contract_id != P298_SOURCE_CONTRACT_ID
            and source_build.get("fresh_reverification") is not True
        )
        or source_build.get("two_clean_builds_byte_identical") is not True
        or source_build.get("linked_audit_verified") is not True
    ):
        raise EvidenceError("candidate static build closure is incomplete")
    source_result_identity = _binary_identity(
        source_build.get("result"), "E1A build reproducibility result"
    )
    source_image_identity = _binary_identity(
        source_build.get("image"), "E1A kernel Image"
    )
    candidate_keys = {
        "artifacts",
        "candidate_b_artifacts",
        "base_boot",
        "ap",
        "fixed_interval",
        "userspace",
        "independent_reconstruction",
        "independent_lz4_roundtrip",
        "independent_magiskboot_unpack",
        "writer_exclusion_verified",
        "two_package_builds_byte_identical",
        "manifest_absent",
        "boot_only_ap",
        "verified",
    }
    if profile in {"E1B", "E2"}:
        candidate_keys.update(
            {"module_closure", "effective_rootfs", "stock_vendor_boot"}
        )
    if userspace_overlay_contract_id in MAX77705_OVERLAY_CONTRACT_IDS:
        candidate_keys.update({"diagnostic_module", "diagnostic_ramdisk_path"})
    if userspace_overlay_contract_id == P318_MAX77705_OVERLAY_CONTRACT_ID:
        candidate_keys.update({"latch_module", "latch_ramdisk_path"})
    source_candidate = _exact(
        candidate_static_result.get("candidate"),
        candidate_keys,
        "E1A candidate static artifact closure",
    )
    source_artifacts = _exact(
        source_candidate["artifacts"],
        {"artifact_result", "boot_img", "boot_img_lz4", "ap_tar_md5"},
        "E1A source artifacts",
    )
    source_b_artifacts = _exact(
        source_candidate["candidate_b_artifacts"],
        set(source_artifacts),
        "E1A source candidate-B artifacts",
    )
    normalized_source_artifacts = {
        name: _binary_identity(value, f"E1A source {name}")
        for name, value in source_artifacts.items()
    }
    normalized_source_b_artifacts = {
        name: _binary_identity(value, f"E1A source candidate-B {name}")
        for name, value in source_b_artifacts.items()
    }
    source_userspace = _exact(
        source_candidate["userspace"],
        {"result", "init", "child", "two_build_byte_identical", "verified"},
        "E1A source userspace",
    )
    normalized_source_userspace = {
        name: _binary_identity(source_userspace[name], f"E1A userspace {name}")
        for name in ("result", "init", "child")
    }
    source_base_boot = _binary_identity(
        source_candidate["base_boot"], "E1A source base boot"
    )
    source_ap = _exact(
        source_candidate["ap"], {"tar_md5", "member"}, "E1A source AP"
    )
    source_member = _exact(
        source_ap["member"],
        {"name", "size", "mode", "uid", "gid", "mtime", "uname", "gname"},
        "E1A source AP member",
    )
    source_fixed_interval = _exact(
        source_candidate["fixed_interval"],
        {
            "kernel_start",
            "kernel_end_exclusive",
            "header_preserved",
            "ramdisk_preserved",
            "outside_interval_changed_byte_count",
            "verified",
        },
        "E1A source fixed interval",
    )
    if profile == "E1B":
        validate_e1b_stock_closure(
            module_closure=source_candidate.get("module_closure"),
            effective_rootfs=source_candidate.get("effective_rootfs"),
            stock_vendor_boot=source_candidate.get("stock_vendor_boot"),
            expected_init=normalized_source_userspace["init"],
            expected_child=normalized_source_userspace["child"],
        )
    elif profile == "E2":
        closure_api = _select_e2_closure(
            source_contract_id, userspace_overlay_contract_id
        )
        try:
            closure = closure_api.validate_module_closure(
                source_candidate.get("module_closure")
            )
            closure_api.validate_effective_rootfs(
                source_candidate.get("effective_rootfs"),
                expected_init=normalized_source_userspace["init"],
                expected_child=normalized_source_userspace["child"],
                module_closure=closure,
            )
        except e2_closure.ClosureError as exc:
            raise EvidenceError("E2 stock rootfs closure is invalid") from exc
        if (
            _binary_identity(
                source_candidate.get("stock_vendor_boot"),
                "E2 stock vendor_boot",
            )
            != E1B_STOCK_VENDOR_BOOT
        ):
            raise EvidenceError("E2 stock vendor_boot identity mismatch")
    source_tools = _exact(
        candidate_static_result["tools"],
        {"lz4", "magiskboot", "qemu_aarch64"},
        "E1A candidate static tools",
    )
    for name, value in source_tools.items():
        _binary_identity(value, f"E1A source tool {name}")
    expected_limits = [
        "host-only artifact qualification grants no D0, D1, F1, or live authority",
        "candidate execution and retained observation remain unproved",
    ]
    if (
        normalized_source_b_artifacts != normalized_source_artifacts
        or not _artifact_matches(source_artifacts["ap_tar_md5"], candidate_ap)
        or (
            profile == "E2"
            and candidate_ap.get("member")
            != {
                "name": "boot.img.lz4",
                **normalized_source_artifacts["boot_img_lz4"],
            }
        )
        or source_member
        != {
            "name": "boot.img.lz4",
            "size": normalized_source_artifacts["boot_img_lz4"]["size"],
            "mode": 0o644,
            "uid": 0,
            "gid": 0,
            "mtime": 0,
            "uname": "",
            "gname": "",
        }
        or not isinstance(source_ap["tar_md5"], str)
        or HEX32_RE.fullmatch(source_ap["tar_md5"]) is None
        or source_fixed_interval
        != {
            "kernel_start": E1_LATEST_STAGE_KERNEL_INTERVAL[0],
            "kernel_end_exclusive": E1_LATEST_STAGE_KERNEL_INTERVAL[1],
            "header_preserved": True,
            "ramdisk_preserved": True,
            "outside_interval_changed_byte_count": 0,
            "verified": True,
        }
        or source_userspace.get("two_build_byte_identical") is not True
        or source_userspace.get("verified") is not True
        or source_candidate.get("boot_only_ap") is not True
        or source_candidate.get("independent_reconstruction") is not True
        or source_candidate.get("independent_lz4_roundtrip") is not True
        or source_candidate.get("independent_magiskboot_unpack") is not True
        or source_candidate.get("writer_exclusion_verified") is not True
        or source_candidate.get("two_package_builds_byte_identical") is not True
        or source_candidate.get("manifest_absent") is not True
        or source_candidate.get("verified") is not True
        or (
            userspace_overlay_contract_id == P318_MAX77705_OVERLAY_CONTRACT_ID
            and (
                not isinstance(p318_contract, dict)
                or _binary_identity(
                    source_candidate.get("latch_module"),
                    "P3.18 latch module",
                )
                != {
                    name: p318_contract.get("module_identities", {})
                    .get("early_latch", {})
                    .get(name)
                    for name in ("size", "sha256")
                }
                or source_candidate.get("latch_ramdisk_path")
                != "lib/modules/s22plus_dwc3_event_latch.ko"
                or _binary_identity(
                    source_candidate.get("diagnostic_module"),
                    "P3.18 diagnostic module",
                )
                != {
                    name: p318_contract.get("module_identities", {})
                    .get("late_diagnostic", {})
                    .get(name)
                    for name in ("size", "sha256")
                }
                or source_candidate.get("diagnostic_ramdisk_path")
                != "lib/modules/s22plus_max77705_mux_diag_p318.ko"
            )
        )
        or (
            userspace_overlay_contract_id
            in {
                MAX77705_OVERLAY_CONTRACT_ID,
                P317_MAX77705_OVERLAY_CONTRACT_ID,
            }
            and (
                _binary_identity(
                    source_candidate.get("diagnostic_module"),
                    "P3.16 diagnostic module",
                )
                != {
                    "size": 293_400,
                    "sha256": "4f4f485a35cdb12206b814390b56674ca6a6d691c9a1d7a29c97030053231849",
                }
                or source_candidate.get("diagnostic_ramdisk_path")
                != "lib/modules/s22plus_max77705_mux_diag.ko"
            )
        )
        or candidate_static_result.get("limits") != expected_limits
    ):
        raise EvidenceError("candidate static artifact closure is not accepted")
    source_safety = candidate_static_result.get("safety")
    expected_source_safety = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "flash": False,
        "partition_write": False,
        "manifest_created": False,
        "live_authorized": False,
    }
    if source_safety != expected_source_safety:
        raise EvidenceError("candidate static safety contract changed")

    static_result_keys = {
        "schema",
        "target",
        "verdict",
        "profile",
        "run_id",
        "decoder",
        "policy_id",
        "run_binding",
        "candidate",
        "safety",
    }
    if source_contract_id is not None:
        static_result_keys.add("source_contract_id")
    if userspace_overlay_contract_id is not None:
        static_result_keys.add("userspace_overlay_contract_id")
    if (
        set(static_result) != static_result_keys
        or static_result.get("schema") != E1_LATEST_STAGE_STATIC_SCHEMA
        or static_result.get("target") != PID1_USERSPACE_TARGET
        or static_result.get("verdict") != E1_LATEST_STAGE_STATIC_VERDICT
        or static_result.get("profile") != item["profile"]
        or static_result.get("source_contract_id") != source_contract_id
        or static_result.get("userspace_overlay_contract_id")
        != userspace_overlay_contract_id
        or static_result.get("run_id") != item["run_id"]
        or static_result.get("decoder") != selected_decoder.DECODER_ID
        or static_result.get("policy_id") != selected_decoder.POLICY_ID
        or static_result.get("run_binding")
        != {
            "canonical_manifest_size": len(canonical),
            "canonical_manifest_sha256": canonical_sha256,
            "verified": True,
        }
    ):
        raise EvidenceError("static checker header does not bind the E1A candidate")
    candidate_result = _exact(
        static_result["candidate"],
        {
            "artifacts",
            "boot_only_ap",
            "two_clean_builds_byte_identical",
            "two_package_builds_byte_identical",
            "linked_audit_verified",
            "independent_reconstruction",
            "writer_exclusion_verified",
            "verified",
        },
        "E1A candidate result",
    )
    artifacts = _exact(
        candidate_result["artifacts"],
        {
            "ap",
            "candidate_static",
            "image",
            "boot_image",
            "boot_img_lz4",
            "init",
            "child",
        },
        "E1A candidate artifacts",
    )
    for name, value in artifacts.items():
        artifacts[name] = _binary_identity(value, f"E1A {name}")
    expected_artifacts = {
        "ap": normalized_source_artifacts["ap_tar_md5"],
        "candidate_static": candidate_static,
        "image": source_image_identity,
        "boot_image": normalized_source_artifacts["boot_img"],
        "boot_img_lz4": normalized_source_artifacts["boot_img_lz4"],
        "init": normalized_source_userspace["init"],
        "child": normalized_source_userspace["child"],
    }
    safety = _exact(
        static_result["safety"],
        {
            "host_only",
            "device_contact",
            "device_write",
            "odin_invoked",
            "odin_transfer",
            "flash",
            "partition_write",
            "live_authorized",
        },
        "E1A static safety",
    )
    if (
        artifacts != expected_artifacts
        or source_result_identity["size"] <= 0
        or source_base_boot["size"] <= 0
        or candidate_result["boot_only_ap"] is not True
        or candidate_result["two_clean_builds_byte_identical"] is not True
        or candidate_result["two_package_builds_byte_identical"] is not True
        or candidate_result["linked_audit_verified"] is not True
        or candidate_result["independent_reconstruction"] is not True
        or candidate_result["writer_exclusion_verified"] is not True
        or candidate_result["verified"] is not True
        or safety["host_only"] is not True
        or any(value is not False for name, value in safety.items() if name != "host_only")
    ):
        raise EvidenceError("static checker result does not bind the E1A candidate")
    result = {
        "schema": "device_action_f1_e1_latest_stage_offline_contract_v1",
        "decoder": item["decoder"],
        "policy_id": item["policy_id"],
        "profile": item["profile"],
        "run_id": item["run_id"],
        "terminal_stage": item["terminal_stage"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "candidate_static_sha256": candidate_static["sha256"],
        "candidate_static_payload_sha256": receipts["candidate_static"]["sha256"],
        "candidate_source_receipts": candidate_source_receipts,
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "minimum_success_count": 1,
        "verified": True,
    }
    if source_contract_id is not None:
        result["source_contract_id"] = source_contract_id
    if userspace_overlay_contract_id is not None:
        result["userspace_overlay_contract_id"] = userspace_overlay_contract_id
        result["p301_overlay_source_receipts"] = p301_overlay_source_receipts
        if userspace_overlay_contract_id == P302_OVERLAY_CONTRACT_ID:
            result["p302_overlay_source_receipts"] = (
                p302_overlay_source_receipts
            )
        if userspace_overlay_contract_id in {
            P303_OVERLAY_CONTRACT_ID,
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
        }:
            result["p303_overlay_source_receipts"] = (
                p303_overlay_source_receipts
            )
            result["p303_stock_baseline"] = p303_stock_baseline
        if userspace_overlay_contract_id in {
            P306_OVERLAY_CONTRACT_ID,
            P307_OVERLAY_CONTRACT_ID,
            P308_OVERLAY_CONTRACT_ID,
        }:
            result["p303_overlay_source_receipts"] = (
                p303_overlay_source_receipts
            )
        if userspace_overlay_contract_id in {
            P304_OVERLAY_CONTRACT_ID,
            P305_OVERLAY_CONTRACT_ID,
            P306_OVERLAY_CONTRACT_ID,
            P307_OVERLAY_CONTRACT_ID,
            P308_OVERLAY_CONTRACT_ID,
        }:
            result["p304_overlay_source_receipts"] = (
                p304_overlay_source_receipts
            )
        if userspace_overlay_contract_id in {
            P305_OVERLAY_CONTRACT_ID,
            P306_OVERLAY_CONTRACT_ID,
            P307_OVERLAY_CONTRACT_ID,
            P308_OVERLAY_CONTRACT_ID,
        }:
            result["p305_overlay_source_receipts"] = (
                p305_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P306_OVERLAY_CONTRACT_ID:
            result["p306_overlay_source_receipts"] = (
                p306_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P307_OVERLAY_CONTRACT_ID:
            result["p307_overlay_source_receipts"] = (
                p307_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P308_OVERLAY_CONTRACT_ID:
            result["p307_overlay_source_receipts"] = (
                p307_overlay_source_receipts
            )
            result["p308_overlay_source_receipts"] = (
                p308_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P311_OVERLAY_CONTRACT_ID:
            result["p311_overlay_source_receipts"] = (
                p311_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P312_OVERLAY_CONTRACT_ID:
            result["p312_overlay_source_receipts"] = (
                p312_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P313_OVERLAY_CONTRACT_ID:
            result["p313_overlay_source_receipts"] = (
                p313_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P314_OVERLAY_CONTRACT_ID:
            result["p314_overlay_source_receipts"] = (
                p314_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P315_OVERLAY_CONTRACT_ID:
            result["p315_overlay_source_receipts"] = (
                p315_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P317_MAX77705_OVERLAY_CONTRACT_ID:
            result["p317_overlay_source_receipts"] = (
                p317_overlay_source_receipts
            )
        if userspace_overlay_contract_id == P318_MAX77705_OVERLAY_CONTRACT_ID:
            result["p318_overlay_source_receipts"] = (
                p318_overlay_source_receipts
            )
        if userspace_overlay_contract_id == MAX77705_OVERLAY_CONTRACT_ID:
            result["p316_overlay_source_receipts"] = (
                p316_overlay_source_receipts
            )
    if p298_repair_files is not None:
        result["tier2_repair_files"] = p298_repair_files
    if profile == "E2":
        result["ap_payload_closure"] = {
            "boot_img_lz4": normalized_source_artifacts["boot_img_lz4"],
            "boot_image": normalized_source_artifacts["boot_img"],
            "image": source_image_identity,
            "init": normalized_source_userspace["init"],
            "child": normalized_source_userspace["child"],
            "run_id": item["run_id"],
            "module_closure": source_candidate["module_closure"],
            "effective_rootfs": source_candidate["effective_rootfs"],
        }
        if source_contract_id is not None:
            result["ap_payload_closure"][
                "source_contract_id"
            ] = source_contract_id
        if userspace_overlay_contract_id is not None:
            result["ap_payload_closure"][
                "userspace_overlay_contract_id"
            ] = userspace_overlay_contract_id
    return result


def verify_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    runtime_bound: bool = False,
) -> dict[str, Any]:
    if acceptance.get("kind") == E1_LATEST_STAGE_KIND:
        return _verify_e1_latest_stage_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
            runtime_bound=runtime_bound,
        )
    if acceptance.get("kind") in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        return _verify_same_ring_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
        )
    if acceptance.get("kind") == PID1_USERSPACE_KIND:
        return _verify_pid1_userspace_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
        )
    return _verify_checkpoint_offline_contract(
        acceptance,
        payloads=payloads,
        receipts=receipts,
        candidate_ap=candidate_ap,
    )


def _base_classification(
    *,
    classification: str,
    exact_count: int,
    family_count: int,
    integrity_issue: bool,
) -> dict[str, Any]:
    return {
        "classification": classification,
        "exact_count": exact_count,
        "exact_record_count": exact_count,
        "family_count": family_count,
        "foreign_count": max(0, family_count - exact_count),
        "foreign_records_hex": [],
        "unterminated_offsets": [],
        "delimiter_mismatch_count": 0,
        "partial_at_head": False,
        "partial_at_tail": False,
        "historical_family_count": 0,
        "integrity_issue": integrity_issue,
        "baseline_absent": family_count == 0 and exact_count == 0,
        "acceptance_present": False,
        "accepted": False,
        "checkpoint": None,
    }


def classify_checkpoint(payload: bytes, acceptance: dict[str, Any]) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != CHECKPOINT_KIND:
        raise EvidenceError("checkpoint classifier received another evidence kind")
    marker = checkpoint.ENTRY_PROOF
    family = checkpoint.ENTRY_FAMILY
    exact_count = payload.count(marker)
    family_count = payload.count(family)
    prefix_counts = [payload.count(prefix) for prefix in checkpoint.ENTRY_PREFIXES]
    partial_head = any(
        payload.startswith(marker[-length:])
        for length in range(len(b"[[S22P1"), len(marker))
    )
    partial_tail = any(
        payload.endswith(marker[:length])
        for length in range(len(b"[[S22P1"), len(marker))
    )
    if not any(prefix_counts) and exact_count == 0 and not partial_head and not partial_tail:
        return _base_classification(
            classification="CHECKPOINT_ABSENT",
            exact_count=0,
            family_count=0,
            integrity_issue=False,
        )
    if (
        exact_count != item["exact_count"]
        or family_count != item["exact_count"]
        or any(count != item["exact_count"] for count in prefix_counts)
        or partial_head
        or partial_tail
    ):
        result = _base_classification(
            classification="CHECKPOINT_FAMILY_INTEGRITY_FAILURE",
            exact_count=exact_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["partial_at_head"] = partial_head
        result["partial_at_tail"] = partial_tail
        return result

    position = payload.index(marker)
    region = payload[position : position + checkpoint.REGION_SIZE]
    try:
        decoded = checkpoint.decode_region(
            region,
            item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
    except checkpoint.CheckError as exc:
        result = _base_classification(
            classification="CHECKPOINT_DECODE_FAILURE",
            exact_count=exact_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["checkpoint"] = {"error": str(exc), "observer_offset": position}
        return result

    active = decoded["active"]
    outcome_name = OUTCOME_NAMES.get(active["outcome"], "unknown")
    two_slots = len(decoded["valid_slots"]) == 2
    accepted = (
        decoded["terminal"] is True
        and active["stage"] == item["terminal_stage"]
        and outcome_name == item["terminal_outcome"]
        and (two_slots or item["require_two_valid_slots"] is not True)
    )
    if accepted:
        classification = "CHECKPOINT_TERMINAL_SUCCESS"
    elif decoded["terminal"] and outcome_name == "failure":
        classification = "CHECKPOINT_TERMINAL_FAILURE"
    elif decoded["terminal"]:
        classification = "CHECKPOINT_TERMINAL_MISMATCH"
    else:
        classification = "CHECKPOINT_PROGRESS_ONLY"
    result = _base_classification(
        classification=classification,
        exact_count=exact_count,
        family_count=family_count,
        integrity_issue=False,
    )
    result["acceptance_present"] = accepted
    result["accepted"] = accepted
    result["checkpoint"] = {
        **decoded,
        "observer_offset": position,
        "outcome_name": outcome_name,
        "two_valid_slots": two_slots,
        "boot_identity_self_consistent": two_slots,
    }
    return result


def classify_pid1_userspace(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != PID1_USERSPACE_KIND:
        raise EvidenceError("PID1 userspace classifier received another evidence kind")
    entry_count = payload.count(PID1_USERSPACE_ENTRY)
    userspace_count = payload.count(PID1_USERSPACE_PROOF)
    family_count = payload.count(PID1_USERSPACE_FAMILY)
    markers = (PID1_USERSPACE_ENTRY, PID1_USERSPACE_PROOF)
    partial_head = any(
        payload.startswith(marker[-length:])
        for marker in markers
        for length in range(len(b"[[S22P1"), len(marker))
    )
    partial_tail = any(
        payload.endswith(marker[:length])
        for marker in markers
        for length in range(len(b"[[S22P1"), len(marker))
    )
    if family_count == 0 and not partial_head and not partial_tail:
        result = _base_classification(
            classification="PID1_USERSPACE_ABSENT",
            exact_count=0,
            family_count=0,
            integrity_issue=False,
        )
    elif (
        family_count != 1
        or entry_count + userspace_count != 1
        or partial_head
        or partial_tail
    ):
        result = _base_classification(
            classification="PID1_USERSPACE_FAMILY_INTEGRITY_FAILURE",
            exact_count=userspace_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["partial_at_head"] = partial_head
        result["partial_at_tail"] = partial_tail
    elif userspace_count == 1:
        result = _base_classification(
            classification="PID1_USERSPACE_CALLBACK_REACHED",
            exact_count=1,
            family_count=1,
            integrity_issue=False,
        )
        result["acceptance_present"] = True
        result["accepted"] = True
    else:
        result = _base_classification(
            classification="PID1_ENTRY_ONLY",
            exact_count=0,
            family_count=1,
            integrity_issue=False,
        )
    result["entry_count"] = entry_count
    result["userspace_count"] = userspace_count
    result["probe_id"] = item["probe_id"]
    return result


def classify_same_ring(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != SAME_RING_KIND:
        raise EvidenceError("same-ring classifier received another evidence kind")
    try:
        decoded = same_ring.classify_observation(payload)
    except same_ring.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    exact_record_count = (
        decoded["entry_count"]
        + decoded["userspace_count"]
        + decoded["unsat_count"]
    )
    family_count = decoded["long_family_count"] + decoded["unsat_family_count"]
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=decoded["userspace_count"],
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = exact_record_count
    result["foreign_count"] = max(0, family_count - exact_record_count)
    result["partial_at_head"] = decoded["partial_at_snapshot_edge"]
    result["partial_at_tail"] = decoded["partial_at_snapshot_edge"]
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["entry_count"] = decoded["entry_count"]
    result["userspace_count"] = decoded["userspace_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["long_family_count"] = decoded["long_family_count"]
    result["unsat_family_count"] = decoded["unsat_family_count"]
    result["contract_id"] = item["contract_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    return result


def classify_same_ring_multiboot(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != SAME_RING_MULTIBOOT_KIND:
        raise EvidenceError("same-ring multiboot classifier received another kind")
    try:
        decoded = same_ring_multiboot.classify_observation(payload)
    except same_ring_multiboot.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    family_count = decoded["long_family_count"] + decoded["unsat_family_count"]
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=decoded["userspace_count"],
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = decoded["exact_record_count"]
    result["foreign_count"] = max(0, family_count - decoded["exact_record_count"])
    result["partial_at_head"] = decoded["partial_at_snapshot_edge"]
    result["partial_at_tail"] = decoded["partial_at_snapshot_edge"]
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["entry_count"] = decoded["entry_count"]
    result["userspace_count"] = decoded["userspace_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["long_family_count"] = decoded["long_family_count"]
    result["unsat_family_count"] = decoded["unsat_family_count"]
    result["minimum_candidate_boots"] = decoded["minimum_candidate_boots"]
    result["contract_id"] = item["contract_id"]
    result["policy_id"] = item["policy_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    return result


def _p303_bound_stock_baseline(item: dict[str, Any]) -> dict[str, Any] | None:
    root = Path(__file__).resolve().parents[5]
    contract = item["contract"]
    stock_keys = {"stock_baseline_raw", "stock_baseline_result"}
    supplied = stock_keys & set(contract)
    if not supplied:
        return None
    if supplied != stock_keys:
        raise EvidenceError(
            "P3.03 stock baseline contract must be absent or an exact pair"
        )
    payloads: dict[str, bytes] = {}
    for name in ("stock_baseline_raw", "stock_baseline_result"):
        pin = contract[name]
        path = (root / pin["path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise EvidenceError("P3.03 stock baseline escaped the repository") from exc
        try:
            before = path.stat()
            if path.is_symlink() or not path.is_file():
                raise EvidenceError("P3.03 stock baseline artifact is indirect")
            payload = path.read_bytes()
            after = path.stat()
        except OSError as exc:
            raise EvidenceError("P3.03 stock baseline artifact is unavailable") from exc
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise EvidenceError("P3.03 stock baseline artifact changed")
        payloads[name] = payload
    try:
        return p303_stock_binding.verify_payloads(
            root,
            payloads["stock_baseline_raw"],
            payloads["stock_baseline_result"],
            expected_raw_path=contract["stock_baseline_raw"]["path"],
        )
    except (p303_stock_binding.BindingError, OSError) as exc:
        raise EvidenceError("P3.03 stock baseline comparison input is invalid") from exc


def classify_e1_latest_stage(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != E1_LATEST_STAGE_KIND:
        raise EvidenceError("E1 latest-stage classifier received another kind")
    selected_decoder = _latest_stage_observation_decoder(
        item.get("source_contract_id"),
        item["profile"],
        item.get("userspace_overlay_contract_id"),
    )
    decoder_errors = (selected_decoder.DecodeError,)
    if selected_decoder in STOCK_ADAPTERS.values():
        adapter_identity_error = getattr(
            selected_decoder, "AdapterIdentityError", None
        )
        if (
            isinstance(adapter_identity_error, type)
            and issubclass(adapter_identity_error, ValueError)
            and adapter_identity_error is not ValueError
        ):
            decoder_errors += (adapter_identity_error,)
    try:
        decoded = selected_decoder.classify_observation(
            payload,
            expected_profile=item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
    except decoder_errors as exc:
        raise EvidenceError(str(exc)) from exc

    model = selected_decoder.model
    long_family_count = payload.count(model.LONG_FAMILY)
    unsat_family_count = payload.count(model.UNSAT_FAMILY)
    carrier_v2 = item.get("source_contract_id") == P310_SOURCE_CONTRACT_ID
    family_count = (
        decoded["family_count"]
        if carrier_v2
        else long_family_count + unsat_family_count
    )
    exact_record_count = decoded["long_record_count"] + decoded["unsat_count"]
    accepted_count = (
        decoded.get("telemetry_count", 0)
        if (
            item.get("userspace_overlay_contract_id")
            in P301_TELEMETRY_OVERLAY_IDS
            or carrier_v2
        )
        else decoded["success_count"]
    )
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=accepted_count,
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = exact_record_count
    result["foreign_count"] = (
        decoded["foreign_count"]
        if carrier_v2
        else max(0, family_count - exact_record_count)
    )
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["long_record_count"] = decoded["long_record_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["entry_count"] = decoded["entry_count"]
    result["progress_count"] = decoded["progress_count"]
    result["failure_count"] = decoded["failure_count"]
    result["success_count"] = decoded["success_count"]
    if (
        item.get("userspace_overlay_contract_id") in P301_TELEMETRY_OVERLAY_IDS
        or carrier_v2
    ):
        result["telemetry_count"] = decoded["telemetry_count"]
        result["contradiction_count"] = decoded["contradiction_count"]
        if "degraded_count" in decoded:
            result["degraded_count"] = decoded["degraded_count"]
        if "pair_excess_count" in decoded:
            result["pair_excess_count"] = decoded["pair_excess_count"]
    result["fallback_record_count"] = decoded["fallback_record_count"]
    result["minimum_candidate_boots"] = decoded["minimum_candidate_boots"]
    result["records"] = decoded["records"]
    result["integrity_issues"] = decoded["integrity_issues"]
    result["policy_id"] = item["policy_id"]
    result["profile"] = item["profile"]
    result["run_id"] = item["run_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    if item.get("userspace_overlay_contract_id") == P342_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P342_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P341_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P341_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P340_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P340_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P339_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P339_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P338_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P338_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P337_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P337_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P336_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P336_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P335_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P335_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P334_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P334_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P333_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P333_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P332_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P332_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P331_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P331_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P330_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P330_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P329_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P329_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P328_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P328_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P327_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P327_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P326_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P326_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P325_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P325_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P324_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P324_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P323_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P323_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P322_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P322_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P321_STOCK_OVERLAY_CONTRACT_ID:
        result["overlay_contract_id"] = P321_STOCK_OVERLAY_CONTRACT_ID
    if item.get("userspace_overlay_contract_id") == P319_STOCK_OVERLAY_CONTRACT_ID:
        # Preserve the adapter's typed result boundary.  In particular,
        # ``accepted`` is not candidate proof: COMPLETE is deliberately
        # NONCAUSAL_SUCCESS_PATH and all causal/host-silent claims stay false.
        for name in (
            "proof_class",
            "causal_result_allowed",
            "candidate_success",
            "mux_result_claimable",
            "host_silent_claimable",
            "acm_supplemental",
            "acm_required_for_acceptance",
            "stock_result_count",
        ):
            if name not in decoded:
                raise EvidenceError(f"P3.19 stock result omitted {name}")
            result[name] = decoded[name]
        stock_rows = [
            row.get("p319_stock")
            for row in decoded.get("records", ())
            if isinstance(row, dict) and "p319_stock" in row
        ]
    result["p319_stock"] = stock_rows
    if item.get("userspace_overlay_contract_id") in {
        P342_STOCK_OVERLAY_CONTRACT_ID,
        P341_STOCK_OVERLAY_CONTRACT_ID,
        P340_STOCK_OVERLAY_CONTRACT_ID,
        P339_STOCK_OVERLAY_CONTRACT_ID,
        P338_STOCK_OVERLAY_CONTRACT_ID,
        P337_STOCK_OVERLAY_CONTRACT_ID,
        P336_STOCK_OVERLAY_CONTRACT_ID,
        P335_STOCK_OVERLAY_CONTRACT_ID,
        P334_STOCK_OVERLAY_CONTRACT_ID,
        P333_STOCK_OVERLAY_CONTRACT_ID,
        P332_STOCK_OVERLAY_CONTRACT_ID,
        P331_STOCK_OVERLAY_CONTRACT_ID,
        P320_STOCK_OVERLAY_CONTRACT_ID,
        P321_STOCK_OVERLAY_CONTRACT_ID,
        P322_STOCK_OVERLAY_CONTRACT_ID,
        P323_STOCK_OVERLAY_CONTRACT_ID,
        P324_STOCK_OVERLAY_CONTRACT_ID,
        P325_STOCK_OVERLAY_CONTRACT_ID,
        P326_STOCK_OVERLAY_CONTRACT_ID,
        P327_STOCK_OVERLAY_CONTRACT_ID,
        P328_STOCK_OVERLAY_CONTRACT_ID,
        P329_STOCK_OVERLAY_CONTRACT_ID,
        P330_STOCK_OVERLAY_CONTRACT_ID,
    }:
        # Keep the P320 projection distinct from P319.  The adapter owns the
        # ABI-v4 receipt/state policy; this classifier only carries its typed
        # predicates into the existing E1 result shape.
        if (
            item.get("userspace_overlay_contract_id")
            in {
                P342_STOCK_OVERLAY_CONTRACT_ID,
                P341_STOCK_OVERLAY_CONTRACT_ID,
                P339_STOCK_OVERLAY_CONTRACT_ID,
                P338_STOCK_OVERLAY_CONTRACT_ID,
                P337_STOCK_OVERLAY_CONTRACT_ID,
                P336_STOCK_OVERLAY_CONTRACT_ID,
                P335_STOCK_OVERLAY_CONTRACT_ID,
                P334_STOCK_OVERLAY_CONTRACT_ID,
                P333_STOCK_OVERLAY_CONTRACT_ID,
                P332_STOCK_OVERLAY_CONTRACT_ID,
                P331_STOCK_OVERLAY_CONTRACT_ID,
                P323_STOCK_OVERLAY_CONTRACT_ID,
                P324_STOCK_OVERLAY_CONTRACT_ID,
                P325_STOCK_OVERLAY_CONTRACT_ID,
                P326_STOCK_OVERLAY_CONTRACT_ID,
                P327_STOCK_OVERLAY_CONTRACT_ID,
                P328_STOCK_OVERLAY_CONTRACT_ID,
                P329_STOCK_OVERLAY_CONTRACT_ID,
                P330_STOCK_OVERLAY_CONTRACT_ID,
            }
            and decoded.get("proof_class")
            in {
                "P342_STOCK_ENCODER_FAILURE",
                "P341_STOCK_ENCODER_FAILURE",
                "P340_STOCK_ENCODER_FAILURE",
                "P339_STOCK_ENCODER_FAILURE",
                "P338_STOCK_ENCODER_FAILURE",
                "P337_STOCK_ENCODER_FAILURE",
                "P336_STOCK_ENCODER_FAILURE",
                "P335_STOCK_ENCODER_FAILURE",
                "P334_STOCK_ENCODER_FAILURE",
                "P333_STOCK_ENCODER_FAILURE",
                "P332_STOCK_ENCODER_FAILURE",
                "P331_STOCK_ENCODER_FAILURE",
                "P323_STOCK_ENCODER_FAILURE",
                "P324_STOCK_ENCODER_FAILURE",
                "P325_STOCK_ENCODER_FAILURE",
                "P326_STOCK_ENCODER_FAILURE",
                "P327_STOCK_ENCODER_FAILURE",
                "P328_STOCK_ENCODER_FAILURE",
                "P329_STOCK_ENCODER_FAILURE",
                "P330_STOCK_ENCODER_FAILURE",
            }
            and decoded.get("producer_failure") is True
            and "stock_result_count" not in decoded
        ):
            decoded = dict(decoded)
            decoded["stock_result_count"] = 0
        for name in (
            "proof_class",
            "causal_result_allowed",
            "candidate_success",
            "mux_result_claimable",
            "host_silent_claimable",
            "acm_supplemental",
            "acm_required_for_acceptance",
            "stock_result_count",
        ):
            if name not in decoded:
                label = (
                    "P3.42"
                    if item.get("userspace_overlay_contract_id")
                    == P342_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "P3.41"
                    if item.get("userspace_overlay_contract_id")
                    == P341_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.40"
                    if item.get("userspace_overlay_contract_id")
                    == P340_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "P3.39"
                    if item.get("userspace_overlay_contract_id")
                    == P339_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.38"
                    if item.get("userspace_overlay_contract_id")
                    == P338_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.37"
                    if item.get("userspace_overlay_contract_id")
                    == P337_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.36"
                    if item.get("userspace_overlay_contract_id")
                    == P336_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "P3.35"
                    if item.get("userspace_overlay_contract_id")
                    == P335_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.34"
                    if item.get("userspace_overlay_contract_id")
                    == P334_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.33"
                    if item.get("userspace_overlay_contract_id")
                    == P333_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.32"
                    if item.get("userspace_overlay_contract_id")
                    == P332_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.31"
                    if item.get("userspace_overlay_contract_id")
                    == P331_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "P3.30"
                    if item.get("userspace_overlay_contract_id") == P330_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.29"
                    if item.get("userspace_overlay_contract_id") == P329_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.28"
                    if item.get("userspace_overlay_contract_id") == P328_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.27"
                    if item.get("userspace_overlay_contract_id") == P327_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.26"
                    if item.get("userspace_overlay_contract_id") == P326_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.25"
                    if item.get("userspace_overlay_contract_id") == P325_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.24"
                    if item.get("userspace_overlay_contract_id") == P324_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.23"
                    if item.get("userspace_overlay_contract_id") == P323_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "P3.22"
                    if item.get("userspace_overlay_contract_id") == P322_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.21"
                    if item.get("userspace_overlay_contract_id") == P321_STOCK_OVERLAY_CONTRACT_ID
                    else "P3.20"
                )
                raise EvidenceError(f"{label} stock result omitted {name}")
            result[name] = decoded[name]
        stock_key = (
            "p342_stock"
            if item.get("userspace_overlay_contract_id")
            == P342_STOCK_OVERLAY_CONTRACT_ID
            else
            "p341_stock"
            if item.get("userspace_overlay_contract_id")
            == P341_STOCK_OVERLAY_CONTRACT_ID
            else "p340_stock"
            if item.get("userspace_overlay_contract_id")
            == P340_STOCK_OVERLAY_CONTRACT_ID
            else
            "p339_stock"
            if item.get("userspace_overlay_contract_id")
            == P339_STOCK_OVERLAY_CONTRACT_ID
            else "p338_stock"
            if item.get("userspace_overlay_contract_id")
            == P338_STOCK_OVERLAY_CONTRACT_ID
            else "p337_stock"
            if item.get("userspace_overlay_contract_id")
            == P337_STOCK_OVERLAY_CONTRACT_ID
            else "p336_stock"
            if item.get("userspace_overlay_contract_id")
            == P336_STOCK_OVERLAY_CONTRACT_ID
            else
            "p335_stock"
            if item.get("userspace_overlay_contract_id")
            == P335_STOCK_OVERLAY_CONTRACT_ID
            else "p334_stock"
            if item.get("userspace_overlay_contract_id")
            == P334_STOCK_OVERLAY_CONTRACT_ID
            else "p333_stock"
            if item.get("userspace_overlay_contract_id")
            == P333_STOCK_OVERLAY_CONTRACT_ID
            else "p332_stock"
            if item.get("userspace_overlay_contract_id")
            == P332_STOCK_OVERLAY_CONTRACT_ID
            else "p331_stock"
            if item.get("userspace_overlay_contract_id")
            == P331_STOCK_OVERLAY_CONTRACT_ID
            else
            "p330_stock"
            if item.get("userspace_overlay_contract_id") == P330_STOCK_OVERLAY_CONTRACT_ID
            else "p329_stock"
            if item.get("userspace_overlay_contract_id") == P329_STOCK_OVERLAY_CONTRACT_ID
            else "p328_stock"
            if item.get("userspace_overlay_contract_id") == P328_STOCK_OVERLAY_CONTRACT_ID
            else "p327_stock"
            if item.get("userspace_overlay_contract_id") == P327_STOCK_OVERLAY_CONTRACT_ID
            else "p326_stock"
            if item.get("userspace_overlay_contract_id") == P326_STOCK_OVERLAY_CONTRACT_ID
            else "p325_stock"
            if item.get("userspace_overlay_contract_id") == P325_STOCK_OVERLAY_CONTRACT_ID
            else "p324_stock"
            if item.get("userspace_overlay_contract_id") == P324_STOCK_OVERLAY_CONTRACT_ID
            else "p323_stock"
            if item.get("userspace_overlay_contract_id") == P323_STOCK_OVERLAY_CONTRACT_ID
            else
            "p322_stock"
            if item.get("userspace_overlay_contract_id") == P322_STOCK_OVERLAY_CONTRACT_ID
            else "p321_stock"
            if item.get("userspace_overlay_contract_id") == P321_STOCK_OVERLAY_CONTRACT_ID
            else "p320_stock"
        )
        row_key = "p331_stock" if stock_key == "p331_stock" else "p320_stock"
        stock_rows = [
            row.get(row_key, row.get("p320_stock"))
            for row in decoded.get("records", ())
            if isinstance(row, dict)
            and (row_key in row or (row_key == "p331_stock" and "p320_stock" in row))
        ]
        result[stock_key] = stock_rows
        if item.get("userspace_overlay_contract_id") in {
            P342_STOCK_OVERLAY_CONTRACT_ID,
            P341_STOCK_OVERLAY_CONTRACT_ID,
            P340_STOCK_OVERLAY_CONTRACT_ID,
            P339_STOCK_OVERLAY_CONTRACT_ID,
            P338_STOCK_OVERLAY_CONTRACT_ID,
            P337_STOCK_OVERLAY_CONTRACT_ID,
            P336_STOCK_OVERLAY_CONTRACT_ID,
            P335_STOCK_OVERLAY_CONTRACT_ID,
            P334_STOCK_OVERLAY_CONTRACT_ID,
            P333_STOCK_OVERLAY_CONTRACT_ID,
            P332_STOCK_OVERLAY_CONTRACT_ID,
            P331_STOCK_OVERLAY_CONTRACT_ID,
            P323_STOCK_OVERLAY_CONTRACT_ID,
            P324_STOCK_OVERLAY_CONTRACT_ID,
            P325_STOCK_OVERLAY_CONTRACT_ID,
            P326_STOCK_OVERLAY_CONTRACT_ID,
            P327_STOCK_OVERLAY_CONTRACT_ID,
            P328_STOCK_OVERLAY_CONTRACT_ID,
            P329_STOCK_OVERLAY_CONTRACT_ID,
            P330_STOCK_OVERLAY_CONTRACT_ID,
        }:
            for name in (
                "producer_failure",
                "stock_encoder_failure",
                "stock_encoder_failed_before_bridge",
                "candidate_native_arrival_supported",
                "carrier_supplemental",
                "acm_primary",
                "acm_bidirectional_primary",
                "busybox_shell_primary",
                "framed_fixed_command_primary",
                "acm_required_for_arrival_proof",
                "max77705_scientific_result",
                "exact_encoder_predicate",
            ):
                if name in decoded:
                    result[name] = decoded[name]
    if item.get("userspace_overlay_contract_id") in {
        P342_STOCK_OVERLAY_CONTRACT_ID,
        P341_STOCK_OVERLAY_CONTRACT_ID,
        P340_STOCK_OVERLAY_CONTRACT_ID,
        P339_STOCK_OVERLAY_CONTRACT_ID,
        P338_STOCK_OVERLAY_CONTRACT_ID,
        P337_STOCK_OVERLAY_CONTRACT_ID,
        P336_STOCK_OVERLAY_CONTRACT_ID,
        P335_STOCK_OVERLAY_CONTRACT_ID,
        P334_STOCK_OVERLAY_CONTRACT_ID,
        P333_STOCK_OVERLAY_CONTRACT_ID,
        P332_STOCK_OVERLAY_CONTRACT_ID,
        P331_STOCK_OVERLAY_CONTRACT_ID,
        P328_STOCK_OVERLAY_CONTRACT_ID,
        P329_STOCK_OVERLAY_CONTRACT_ID,
        P330_STOCK_OVERLAY_CONTRACT_ID,
    }:
        p342 = item.get("userspace_overlay_contract_id") == P342_STOCK_OVERLAY_CONTRACT_ID
        p341 = item.get("userspace_overlay_contract_id") == P341_STOCK_OVERLAY_CONTRACT_ID
        p340 = item.get("userspace_overlay_contract_id") == P340_STOCK_OVERLAY_CONTRACT_ID
        p339 = item.get("userspace_overlay_contract_id") == P339_STOCK_OVERLAY_CONTRACT_ID
        p338 = item.get("userspace_overlay_contract_id") == P338_STOCK_OVERLAY_CONTRACT_ID
        p337 = item.get("userspace_overlay_contract_id") == P337_STOCK_OVERLAY_CONTRACT_ID
        p336 = item.get("userspace_overlay_contract_id") == P336_STOCK_OVERLAY_CONTRACT_ID
        p335 = item.get("userspace_overlay_contract_id") == P335_STOCK_OVERLAY_CONTRACT_ID
        p334 = item.get("userspace_overlay_contract_id") == P334_STOCK_OVERLAY_CONTRACT_ID
        p333 = item.get("userspace_overlay_contract_id") == P333_STOCK_OVERLAY_CONTRACT_ID
        p332 = item.get("userspace_overlay_contract_id") == P332_STOCK_OVERLAY_CONTRACT_ID
        p331 = item.get("userspace_overlay_contract_id") == P331_STOCK_OVERLAY_CONTRACT_ID
        p330 = item.get("userspace_overlay_contract_id") == P330_STOCK_OVERLAY_CONTRACT_ID
        p329 = item.get("userspace_overlay_contract_id") == P329_STOCK_OVERLAY_CONTRACT_ID
        expected_authentication = {
            "authenticated_exec": True,
            "authentication_required": True,
            "auth_algorithm": P328_AUTH_EXEC_AUTH_ALGORITHM,
            "auth_tag_size": P328_AUTH_EXEC_AUTH_TAG_SIZE,
            "auth_key_schema": P328_AUTH_EXEC_AUTH_KEY_SCHEMA,
            "auth_key_size": P328_AUTH_EXEC_AUTH_KEY_SIZE,
            "auth_key_path_published": False,
            "per_session_random_nonce": True,
            "caller_selected_command": False if p342 or p341 or p340 or p339 or p338 or p337 or p336 or p335 or p334 or p333 or p332 or p331 else True,
            "interactive_pty": False,
        }
        for name, expected in expected_authentication.items():
            if name in decoded and decoded[name] != expected:
                raise EvidenceError(
                    f"P3.{42 if p342 else 41 if p341 else 40 if p340 else 39 if p339 else 38 if p338 else 37 if p337 else 36 if p336 else 35 if p335 else 34 if p334 else 33 if p333 else 32 if p332 else 31 if p331 else 30 if p330 else 29 if p329 else 28} classifier authentication field {name} differs"
                )
            result[name] = expected
        result["auth_key"] = dict(
            P341_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p342
            else P341_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p341
            else P340_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p340
            else
            P339_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p339
            else P338_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p338
            else P337_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p337
            else P336_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p336
            else
            P335_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p335
            else P334_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p334
            else P333_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p333
            else P332_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p332
            else P331_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p331
            else P330_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p330
            else P329_AUTH_EXEC_AUTH_KEY_IDENTITY
            if p329
            else P328_AUTH_EXEC_AUTH_KEY_IDENTITY
        )
        result["observer_contract"] = (
            P342_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p342
            else P341_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p341
            else P340_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p340
            else
            P339_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p339
            else P338_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p338
            else P337_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p337
            else P336_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p336
            else
            P335_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p335
            else P334_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p334
            else P333_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p333
            else P332_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p332
            else P331_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p331
            else P330_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p330
            else P329_AUTH_EXEC_OBSERVER_CONTRACT_ID
            if p329
            else P328_AUTH_EXEC_OBSERVER_CONTRACT_ID
        )
        if p329 or p330 or p331 or p332 or p333 or p334 or p335 or p336 or p337 or p338 or p339 or p340 or p341 or p342:
            result["udev_guard_settle_bounded"] = True
        if p330:
            result["preauth_diagnostics_bounded"] = True
        if p331:
            result["preauth_diagnostics_bounded"] = True
            result["resident_sessions_bounded"] = True
            result["resident_reconnect_bounded"] = True
            result["fixed_heartbeat_only"] = True
        if p332:
            result["preauth_diagnostics_bounded"] = True
            result["logical_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 0
            result["fixed_p330_commands"] = True
        if p333:
            result["preauth_diagnostics_bounded"] = True
            result["logical_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 0
            result["fixed_p330_commands"] = True
            result["entry_diagnostic_stage"] = 0
            result["entry_diagnostic_before_console"] = True
        if p334:
            result["preauth_diagnostics_bounded"] = True
            result["logical_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 0
            result["fixed_p330_commands"] = True
            result["entry_diagnostic_stage"] = 0
            result["entry_diagnostic_before_console"] = True
            result["first_console_return_checkpoint_only"] = True
            result["first_console_return_detail_prefix"] = P334_AUTH_EXEC_DETAIL_PREFIX
            result["first_console_return_detail_sentinel"] = P334_AUTH_EXEC_DETAIL_SENTINEL
            result["first_read_attribution_requires_stage0_without_stage1"] = True
            for name in (
                "first_console_return",
                "first_console_return_receipt_present",
                "first_console_return_code_valid",
            ):
                if name in decoded:
                    result[name] = decoded[name]
        if p335:
            result["preauth_diagnostics_bounded"] = True
            result["initial_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 1
            result["per_boot_identity_required"] = True
            result["listener_wait_after_proof"] = True
        if p336:
            result["preauth_diagnostics_bounded"] = True
            result["initial_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 1
            result["per_boot_identity_required"] = True
            result["long_idle_host_resync"] = True
            result["later_action_open_before_resync"] = True
            result["listener_wait_after_proof"] = True
        if p337:
            result["preauth_diagnostics_bounded"] = True
            result["initial_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 1
            result["per_boot_identity_required"] = True
            result["long_idle_host_resync"] = True
            result["later_action_open_before_resync"] = True
            result["listener_wait_after_proof"] = True
            result["first_open_failure_diagnostic"] = True
            result["open_read_diagnostic_stage"] = p337_open_read_diag_runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT
            result["open_read_failure_diagnostic_best_effort"] = True
        if p338:
            result["preauth_diagnostics_bounded"] = True
            result["initial_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 1
            result["per_boot_identity_required"] = True
            result["long_idle_host_resync"] = True
            result["later_action_open_before_resync"] = True
            result["listener_wait_after_proof"] = True
            result["first_open_failure_diagnostic"] = True
            result["open_read_diagnostic_stage"] = p338_open_read_branch_runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT
            result["open_read_failure_diagnostic_best_effort"] = True
            result["open_read_branch_ordinals"] = dict(P338_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS)
            result["open_read_branch_count"] = P338_AUTH_EXEC_OPEN_READ_BRANCH_COUNT
            result["original_errno_returned_unchanged"] = True
        if p339:
            result["preauth_diagnostics_bounded"] = True
            result["initial_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 1
            result["per_boot_identity_required"] = True
            result["long_idle_host_resync"] = True
            result["later_action_open_before_resync"] = True
            result["listener_wait_after_proof"] = True
            result["first_open_failure_diagnostic"] = True
            result["open_read_diagnostic_stage"] = p339_open_read_branch_runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT
            result["open_read_failure_diagnostic_best_effort"] = True
            result["open_read_branch_ordinals"] = dict(P339_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS)
            result["open_read_branch_count"] = P339_AUTH_EXEC_OPEN_READ_BRANCH_COUNT
            result["open_header_word_stages"] = list(P339_AUTH_EXEC_OPEN_HEADER_WORD_STAGES)
            result["open_header_size"] = P339_AUTH_EXEC_OPEN_HEADER_SIZE
            result["open_header_capture_best_effort"] = True
            result["original_errno_returned_unchanged"] = True
        if p342:
            result["preauth_diagnostics_bounded"] = True
            result["initial_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 1
            result["per_boot_identity_required"] = True
            result["long_idle_host_resync"] = True
            result["later_action_open_before_resync"] = True
            result["listener_wait_after_proof"] = True
            result["first_open_failure_diagnostic"] = True
            result["open_read_diagnostic_stage"] = p342_open_read_branch_runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT
            result["open_read_failure_diagnostic_best_effort"] = True
            result["open_read_branch_ordinals"] = dict(P342_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS)
            result["open_read_branch_count"] = P342_AUTH_EXEC_OPEN_READ_BRANCH_COUNT
            result["open_header_word_stages"] = list(P342_AUTH_EXEC_OPEN_HEADER_WORD_STAGES)
            result["open_header_size"] = P342_AUTH_EXEC_OPEN_HEADER_SIZE
            result["open_header_capture_best_effort"] = True
            result["original_errno_returned_unchanged"] = True
            result["host_first_open"] = True
            result["host_open_before_banner"] = True
            result["stage_zero_after_banner"] = True
            result["open_parsed_after_stage_zero"] = True
            result["no_unsolicited_device_tx"] = True
            result["silent_no_peer_no_proof"] = True
            result["consumed_partial_open_no_replay"] = True
            result["same_fd_session_count"] = P342_SAME_FD_SESSION_COUNT
            result["idle_seconds"] = P342_IDLE_REUSE_REQUESTED_SECONDS
            result["total_session_count"] = P342_TOTAL_SESSION_COUNT
            result["total_command_count"] = P342_TOTAL_COMMAND_COUNT
        if p341:
            result["preauth_diagnostics_bounded"] = True
            result["initial_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 1
            result["per_boot_identity_required"] = True
            result["long_idle_host_resync"] = True
            result["later_action_open_before_resync"] = True
            result["listener_wait_after_proof"] = True
            result["first_open_failure_diagnostic"] = True
            result["open_read_diagnostic_stage"] = p341_open_read_branch_runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT
            result["open_read_failure_diagnostic_best_effort"] = True
            result["open_read_branch_ordinals"] = dict(P341_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS)
            result["open_read_branch_count"] = P341_AUTH_EXEC_OPEN_READ_BRANCH_COUNT
            result["open_header_word_stages"] = list(P341_AUTH_EXEC_OPEN_HEADER_WORD_STAGES)
            result["open_header_size"] = P341_AUTH_EXEC_OPEN_HEADER_SIZE
            result["open_header_capture_best_effort"] = True
            result["original_errno_returned_unchanged"] = True
            result["host_first_open"] = True
            result["host_open_before_banner"] = True
            result["device_banner_after_open"] = True
            result["stage_zero_after_banner"] = True
            result["open_parsed_after_stage_zero"] = True
            result["no_unsolicited_device_tx"] = True
            result["silent_no_peer_no_proof"] = True
            result["consumed_partial_open_no_replay"] = True
        if p340:
            result["preauth_diagnostics_bounded"] = True
            result["initial_sessions_bounded"] = True
            result["same_tty_fd_required"] = True
            result["physical_reopen_count"] = 1
            result["per_boot_identity_required"] = True
            result["long_idle_host_resync"] = True
            result["later_action_open_before_resync"] = True
            result["listener_wait_after_proof"] = True
            result["first_open_failure_diagnostic"] = True
            result["open_read_diagnostic_stage"] = p340_open_read_branch_runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT
            result["open_read_failure_diagnostic_best_effort"] = True
            result["open_read_branch_ordinals"] = dict(P340_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS)
            result["open_read_branch_count"] = P340_AUTH_EXEC_OPEN_READ_BRANCH_COUNT
            result["open_header_word_stages"] = list(P340_AUTH_EXEC_OPEN_HEADER_WORD_STAGES)
            result["open_header_size"] = P340_AUTH_EXEC_OPEN_HEADER_SIZE
            result["open_header_capture_best_effort"] = True
            result["original_errno_returned_unchanged"] = True
            result["initial_failure_suffix_capture"] = True
            result["maximum_failure_suffix_bytes"] = 96
    if item.get("userspace_overlay_contract_id") in {
        P303_OVERLAY_CONTRACT_ID,
        P304_OVERLAY_CONTRACT_ID,
        P305_OVERLAY_CONTRACT_ID,
    }:
        stock = _p303_bound_stock_baseline(item)
        comparisons = []
        if stock is not None:
            for record in decoded["records"]:
                pair = record.get("p303_pair")
                if pair is None:
                    continue
                try:
                    comparisons.append(
                        p303_decoder.compare_stock_baseline(
                            int(pair["b"]["detail"]), stock["baseline"]
                        )
                    )
                except p303_decoder.DecodeError as exc:
                    raise EvidenceError(str(exc)) from exc
            result["p303_stock_baseline"] = {
                "available": True,
                "causal_attribution_permitted": True,
                "raw": stock["raw"],
                "boot_window_complete": stock["boot_window_complete"],
                "comparisons": comparisons,
                "comparison_count": len(comparisons),
            }
        else:
            result["p303_stock_baseline"] = {
                "available": False,
                "causal_attribution_permitted": False,
                "comparisons": [],
                "comparison_count": 0,
            }
    return result


def p318_candidate_causal_ready(classified: dict[str, Any]) -> bool:
    if (
        not isinstance(classified, dict)
        or classified.get("policy_id") != p318_max77705_decoder.POLICY_ID
        or classified.get("profile") != p318_max77705_decoder.PROFILE
    ):
        raise EvidenceError("P3.18 retained classification identity differs")
    records = [
        row for row in classified.get("records", ())
        if isinstance(row, dict) and isinstance(row.get("max77705"), dict)
    ]
    return (
        len(records) == 1
        and records[0]["max77705"].get(
            "diagnostic_causal_prerequisites_ready"
        )
        is True
    )


def correlate_p318_candidate_topology(
    classified: dict[str, Any], phase_record: dict[str, Any]
) -> dict[str, Any]:
    try:
        phase_record = p318_topology_receipt.validate_phase_record(phase_record)
    except p318_topology_receipt.TopologyReceiptError as exc:
        raise EvidenceError(str(exc)) from exc
    if (
        not isinstance(classified, dict)
        or classified.get("policy_id") != p318_max77705_decoder.POLICY_ID
        or classified.get("profile") != p318_max77705_decoder.PROFILE
        or phase_record.get("phase") != "candidate_end"
        or phase_record.get("authority_state") != "candidate_approved_exact"
        or phase_record.get("relationship_to_start")
        not in p318_topology_receipt.transition.TOPOLOGY_RELATIONSHIPS
        or not isinstance(phase_record.get("observation_window_complete"), bool)
    ):
        raise EvidenceError("P3.18 candidate topology correlation input differs")
    try:
        correlated = p318_max77705_decoder.correlate_candidate_receipt(
            classified,
            relationship=phase_record["relationship_to_start"],
            authority_state=phase_record["authority_state"],
            observation_complete=phase_record["observation_window_complete"],
        )
    except p318_max77705_decoder.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc
    causal_ready = p318_candidate_causal_ready(classified)
    if phase_record.get("causal_terminal_ready") is not causal_ready:
        raise EvidenceError("P3.18 topology and retained causal readiness differ")
    return correlated


def classify_clean_baseline(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] == E1_LATEST_STAGE_KIND:
        selected_decoder = _latest_stage_observation_decoder(
            item.get("source_contract_id"),
            item["profile"],
            item.get("userspace_overlay_contract_id"),
        )
        try:
            baseline = selected_decoder.classify_clean_baseline(
                payload,
                expected_profile=item["profile"],
                expected_run_id=bytes.fromhex(item["run_id"]),
            )
        except ValueError as exc:
            overlay = item.get("userspace_overlay_contract_id")
            if overlay not in {
                P339_STOCK_OVERLAY_CONTRACT_ID,
                P338_STOCK_OVERLAY_CONTRACT_ID,
                P334_STOCK_OVERLAY_CONTRACT_ID,
                P333_STOCK_OVERLAY_CONTRACT_ID,
                P332_STOCK_OVERLAY_CONTRACT_ID,
                P323_STOCK_OVERLAY_CONTRACT_ID,
                P324_STOCK_OVERLAY_CONTRACT_ID,
                P325_STOCK_OVERLAY_CONTRACT_ID,
                P331_STOCK_OVERLAY_CONTRACT_ID,
            }:
                raise
            raw_identity = {
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            if overlay == P339_STOCK_OVERLAY_CONTRACT_ID:
                if raw_identity != P339_CONSUMED_P338_BASELINE_IDENTITY:
                    raise EvidenceError(
                        "P3.39 predecessor baseline raw identity differs"
                    ) from exc
                predecessor_run = bytes.fromhex(P338_RUN_ID)
                if (
                    payload.count(predecessor_run) != 1
                    or payload.find(predecessor_run) != P339_CONSUMED_P338_RUN_OFFSET
                    or bytes.fromhex(P339_RUN_ID) in payload
                ):
                    raise EvidenceError(
                        "P3.39 predecessor baseline placement differs"
                    )
                try:
                    predecessor = p338_stock_adapter.classify_observation(
                        payload,
                        expected_profile=p338_stock_adapter.PROFILE,
                        expected_run_id=p338_stock_adapter.P338_RUN_ID,
                    )
                except ValueError as predecessor_exc:
                    raise EvidenceError(
                        "P3.39 baseline is not the exact consumed P3.38 receipt"
                    ) from predecessor_exc
                if (
                    predecessor.get("classification")
                    != "P320_STOCK_WITNESS_BASE_SHAPE_FAILURE"
                    or predecessor.get("accepted") is not False
                    or predecessor.get("integrity_issue") is not True
                    or predecessor.get("integrity_issues")
                    != ["foreign-or-malformed-v2-long-record"]
                    or predecessor.get("exact_record_count") != 0
                    or predecessor.get("long_record_count") != 0
                    or predecessor.get("family_count") != 1
                    or predecessor.get("foreign_count") != 1
                    or predecessor.get("candidate_success") is not False
                    or predecessor.get("proof_class") != "NO_PROOF_OBSERVER"
                    or predecessor.get("run_id") != P338_RUN_ID
                ):
                    raise EvidenceError(
                        "P3.39 predecessor baseline semantics differ"
                    )
                return {
                    "classification": (
                        "P339_CURRENT_RUN_ABSENT_P338_PREDECESSOR_EXACT"
                    ),
                    "exact_record_count": 0,
                    "family_count": 1,
                    "integrity_issue": False,
                    "baseline_clean": True,
                }
            if overlay == P338_STOCK_OVERLAY_CONTRACT_ID:
                if raw_identity != P338_CONSUMED_P337_BASELINE_IDENTITY:
                    raise EvidenceError(
                        "P3.38 predecessor baseline raw identity differs"
                    ) from exc
                try:
                    predecessor = p337_stock_adapter.classify_observation(
                        payload,
                        expected_profile=p337_stock_adapter.PROFILE,
                        expected_run_id=p337_stock_adapter.P337_RUN_ID,
                    )
                except ValueError as predecessor_exc:
                    raise EvidenceError(
                        "P3.38 baseline is not the exact consumed P3.37 receipt"
                    ) from predecessor_exc
                records = predecessor.get("records")
                if (
                    predecessor.get("classification")
                    != "AMBIGUOUS_INTEGRITY_FAILURE"
                    or predecessor.get("accepted") is not False
                    or predecessor.get("integrity_issue") is not True
                    or predecessor.get("integrity_issues")
                    != ["p320-stock-envelope-shape"]
                    or predecessor.get("exact_record_count") != 1
                    or predecessor.get("long_record_count") != 1
                    or predecessor.get("family_count") != 1
                    or predecessor.get("foreign_count") != 0
                    or predecessor.get("candidate_success") is not False
                    or predecessor.get("proof_class") != "NO_PROOF_OBSERVER"
                    or predecessor.get("run_id") != p337_stock_adapter.P337_RUN_ID_HEX
                    or not isinstance(records, list)
                    or len(records) != 1
                    or records[0].get("observer_offset")
                    != P338_CONSUMED_P337_RECORD_OFFSET
                    or records[0].get("run_id")
                    != p337_stock_adapter.P337_RUN_ID_HEX
                    or records[0].get("slot_status") != ["valid", "valid"]
                ):
                    raise EvidenceError(
                        "P3.38 predecessor baseline placement or semantics differ"
                    )
                return {
                    "classification": (
                        "P338_CURRENT_RUN_ABSENT_P337_PREDECESSOR_EXACT"
                    ),
                    "exact_record_count": 0,
                    "family_count": 1,
                    "integrity_issue": False,
                    "baseline_clean": True,
                }
            if overlay == P334_STOCK_OVERLAY_CONTRACT_ID:
                if raw_identity != P334_CONSUMED_P333_BASELINE_IDENTITY:
                    raise EvidenceError(
                        "P3.34 predecessor baseline raw identity differs"
                    ) from exc
                try:
                    predecessor = p333_stock_adapter.classify_observation(
                        payload,
                        expected_profile=p333_stock_adapter.PROFILE,
                        expected_run_id=p333_stock_adapter.P333_RUN_ID,
                    )
                except ValueError as predecessor_exc:
                    raise EvidenceError(
                        "P3.34 baseline is neither empty nor the exact consumed P3.33 receipt"
                    ) from predecessor_exc
                records = predecessor.get("records")
                if (
                    predecessor.get("classification")
                    != "P320_STOCK_WITNESS_AMBIGUOUS_NO_PROOF"
                    or predecessor.get("accepted") is not False
                    or predecessor.get("integrity_issue") is not False
                    or predecessor.get("integrity_issues") != []
                    or predecessor.get("exact_record_count") != 1
                    or predecessor.get("long_record_count") != 1
                    or predecessor.get("foreign_count") != 0
                    or predecessor.get("candidate_success") is not False
                    or predecessor.get("proof_class") != "NO_PROOF_OBSERVER"
                    or not isinstance(records, list)
                    or len(records) != 1
                    or records[0].get("observer_offset")
                    != P334_CONSUMED_P333_RECORD_OFFSET
                    or records[0].get("run_id")
                    != p333_stock_adapter.P333_RUN_ID_HEX
                    or records[0].get("slot_status") != ["valid", "valid"]
                ):
                    raise EvidenceError(
                        "P3.34 predecessor baseline placement or semantics differ"
                    )
                return {
                    "classification": (
                        "P334_CURRENT_RUN_ABSENT_P333_PREDECESSOR_EXACT"
                    ),
                    "exact_record_count": 0,
                    "family_count": 1,
                    "integrity_issue": False,
                    "baseline_clean": True,
                }
            if overlay == P333_STOCK_OVERLAY_CONTRACT_ID:
                if raw_identity != P333_CONSUMED_P332_BASELINE_IDENTITY:
                    raise EvidenceError(
                        "P3.33 predecessor baseline raw identity differs"
                    ) from exc
                try:
                    predecessor = p332_stock_adapter.classify_observation(
                        payload,
                        expected_profile=p332_stock_adapter.PROFILE,
                        expected_run_id=p332_stock_adapter.P332_RUN_ID,
                    )
                except ValueError as predecessor_exc:
                    raise EvidenceError(
                        "P3.33 baseline is neither empty nor the exact consumed P3.32 receipt"
                    ) from predecessor_exc
                records = predecessor.get("records")
                if (
                    predecessor.get("classification")
                    != "P320_STOCK_WITNESS_AMBIGUOUS_NO_PROOF"
                    or predecessor.get("accepted") is not False
                    or predecessor.get("integrity_issue") is not False
                    or predecessor.get("integrity_issues") != []
                    or predecessor.get("exact_record_count") != 1
                    or predecessor.get("long_record_count") != 1
                    or predecessor.get("foreign_count") != 0
                    or predecessor.get("candidate_success") is not False
                    or predecessor.get("proof_class") != "NO_PROOF_OBSERVER"
                    or not isinstance(records, list)
                    or len(records) != 1
                    or records[0].get("observer_offset")
                    != P333_CONSUMED_P332_RECORD_OFFSET
                    or records[0].get("run_id")
                    != p332_stock_adapter.P332_RUN_ID_HEX
                    or records[0].get("slot_status") != ["valid", "valid"]
                ):
                    raise EvidenceError(
                        "P3.33 predecessor baseline placement or semantics differ"
                    )
                return {
                    "classification": (
                        "P333_CURRENT_RUN_ABSENT_P332_PREDECESSOR_EXACT"
                    ),
                    "exact_record_count": 0,
                    "family_count": 1,
                    "integrity_issue": False,
                    "baseline_clean": True,
                }
            if overlay == P332_STOCK_OVERLAY_CONTRACT_ID:
                if raw_identity != P332_CONSUMED_P331_BASELINE_IDENTITY:
                    raise EvidenceError(
                        "P3.32 predecessor baseline raw identity differs"
                    ) from exc
                try:
                    predecessor = p331_stock_adapter.classify_observation(
                        payload,
                        expected_profile=p331_stock_adapter.PROFILE,
                        expected_run_id=p331_stock_adapter.P331_RUN_ID,
                    )
                except ValueError as predecessor_exc:
                    raise EvidenceError(
                        "P3.32 baseline is neither empty nor the exact consumed P3.31 receipt"
                    ) from predecessor_exc
                records = predecessor.get("records")
                if (
                    predecessor.get("classification")
                    != "P320_STOCK_WITNESS_AMBIGUOUS_NO_PROOF"
                    or predecessor.get("accepted") is not False
                    or predecessor.get("integrity_issue") is not False
                    or predecessor.get("integrity_issues") != []
                    or predecessor.get("exact_record_count") != 1
                    or predecessor.get("long_record_count") != 1
                    or predecessor.get("foreign_count") != 0
                    or predecessor.get("candidate_success") is not False
                    or predecessor.get("proof_class") != "NO_PROOF_OBSERVER"
                    or not isinstance(records, list)
                    or len(records) != 1
                    or records[0].get("observer_offset")
                    != P332_CONSUMED_P331_RECORD_OFFSET
                    or records[0].get("run_id")
                    != p331_stock_adapter.P331_RUN_ID_HEX
                    or records[0].get("slot_status") != ["valid", "valid"]
                ):
                    raise EvidenceError(
                        "P3.32 predecessor baseline placement or semantics differ"
                    )
                return {
                    "classification": (
                        "P332_CURRENT_RUN_ABSENT_P331_PREDECESSOR_EXACT"
                    ),
                    "exact_record_count": 0,
                    "family_count": 1,
                    "integrity_issue": False,
                    "baseline_clean": True,
                }
            if overlay == P331_STOCK_OVERLAY_CONTRACT_ID:
                if raw_identity != P331_CONSUMED_P330_BASELINE_IDENTITY:
                    raise EvidenceError(
                        "P3.31 predecessor baseline raw identity differs"
                    ) from exc
                try:
                    predecessor = p330_stock_adapter.classify_observation(
                        payload,
                        expected_profile=p330_stock_adapter.PROFILE,
                        expected_run_id=p330_stock_adapter.P330_RUN_ID,
                    )
                except ValueError as predecessor_exc:
                    raise EvidenceError(
                        "P3.31 baseline is neither empty nor the exact consumed P3.30 receipt"
                    ) from predecessor_exc
                records = predecessor.get("records")
                if (
                    predecessor.get("classification")
                    != "P320_STOCK_WITNESS_AMBIGUOUS_NO_PROOF"
                    or predecessor.get("accepted") is not False
                    or predecessor.get("integrity_issue") is not False
                    or predecessor.get("integrity_issues") != []
                    or predecessor.get("exact_record_count") != 1
                    or predecessor.get("long_record_count") != 1
                    or predecessor.get("foreign_count") != 0
                    or predecessor.get("candidate_success") is not False
                    or predecessor.get("proof_class") != "NO_PROOF_OBSERVER"
                    or not isinstance(records, list)
                    or len(records) != 1
                    or records[0].get("observer_offset")
                    != P331_CONSUMED_P330_RECORD_OFFSET
                    or records[0].get("run_id")
                    != p330_stock_adapter.P330_RUN_ID_HEX
                    or records[0].get("slot_status") != ["valid", "valid"]
                ):
                    raise EvidenceError(
                        "P3.31 predecessor baseline placement or semantics differ"
                    )
                return {
                    "classification": (
                        "P331_CURRENT_RUN_ABSENT_P330_PREDECESSOR_EXACT"
                    ),
                    "exact_record_count": 0,
                    "family_count": 1,
                    "integrity_issue": False,
                    "baseline_clean": True,
                }
            if overlay == P325_STOCK_OVERLAY_CONTRACT_ID:
                if raw_identity != P325_CONSUMED_P324_BASELINE_IDENTITY:
                    raise EvidenceError(
                        "P3.25 predecessor baseline raw identity differs"
                    ) from exc
                try:
                    predecessor = p324_stock_adapter.classify_observation(
                        payload,
                        expected_profile=p324_stock_adapter.PROFILE,
                        expected_run_id=p324_stock_adapter.P324_RUN_ID,
                    )
                except ValueError as predecessor_exc:
                    raise EvidenceError(
                        "P3.25 baseline is neither empty nor the exact consumed P3.24 receipt"
                    ) from predecessor_exc
                records = predecessor.get("records")
                if (
                    predecessor.get("classification")
                    != "P320_STOCK_WITNESS_AMBIGUOUS_NO_PROOF"
                    or predecessor.get("accepted") is not False
                    or predecessor.get("integrity_issue") is not False
                    or predecessor.get("integrity_issues") != []
                    or predecessor.get("exact_record_count") != 1
                    or predecessor.get("long_record_count") != 1
                    or predecessor.get("foreign_count") != 0
                    or predecessor.get("candidate_success") is not False
                    or predecessor.get("proof_class") != "NO_PROOF_OBSERVER"
                    or not isinstance(records, list)
                    or len(records) != 1
                    or records[0].get("observer_offset")
                    != P325_CONSUMED_P324_RECORD_OFFSET
                    or records[0].get("run_id") != p324_stock_adapter.P324_RUN_ID_HEX
                    or records[0].get("slot_status") != ["valid", "valid"]
                ):
                    raise EvidenceError(
                        "P3.25 predecessor baseline placement or semantics differ"
                    )
                return {
                    "classification": (
                        "P325_CURRENT_RUN_ABSENT_P324_PREDECESSOR_EXACT"
                    ),
                    "exact_record_count": 0,
                    "family_count": 1,
                    "integrity_issue": False,
                    "baseline_clean": True,
                }
            if overlay == P324_STOCK_OVERLAY_CONTRACT_ID:
                if raw_identity != P324_CONSUMED_P323_BASELINE_IDENTITY:
                    raise EvidenceError(
                        "P3.24 predecessor baseline raw identity differs"
                    ) from exc
                try:
                    predecessor = p323_stock_adapter.classify_observation(
                        payload,
                        expected_profile=p323_stock_adapter.PROFILE,
                        expected_run_id=p323_stock_adapter.P323_RUN_ID,
                    )
                except ValueError as predecessor_exc:
                    raise EvidenceError(
                        "P3.24 baseline is neither empty nor the exact consumed P3.23 receipt"
                    ) from predecessor_exc
                records = predecessor.get("records")
                if (
                    predecessor.get("classification")
                    != "P320_STOCK_WITNESS_AMBIGUOUS_NO_PROOF"
                    or predecessor.get("accepted") is not False
                    or predecessor.get("integrity_issue") is not False
                    or predecessor.get("integrity_issues") != []
                    or predecessor.get("exact_record_count") != 1
                    or predecessor.get("long_record_count") != 1
                    or predecessor.get("foreign_count") != 0
                    or predecessor.get("candidate_success") is not False
                    or predecessor.get("proof_class") != "NO_PROOF_OBSERVER"
                    or not isinstance(records, list)
                    or len(records) != 1
                    or records[0].get("observer_offset")
                    != P324_CONSUMED_P323_RECORD_OFFSET
                    or records[0].get("run_id") != p323_stock_adapter.P323_RUN_ID_HEX
                    or records[0].get("slot_status") != ["valid", "valid"]
                ):
                    raise EvidenceError(
                        "P3.24 predecessor baseline placement or semantics differ"
                    )
                return {
                    "classification": (
                        "P324_CURRENT_RUN_ABSENT_P323_PREDECESSOR_EXACT"
                    ),
                    "exact_record_count": 0,
                    "family_count": 1,
                    "integrity_issue": False,
                    "baseline_clean": True,
                }
            if raw_identity != P323_CONSUMED_P322_BASELINE_IDENTITY:
                raise EvidenceError(
                    "P3.23 predecessor baseline raw identity differs"
                ) from exc
            try:
                predecessor = p323_predecessor_baseline.reanalyze(payload)
            except p323_predecessor_baseline.ReanalysisError as predecessor_exc:
                raise EvidenceError(
                    "P3.23 baseline is neither empty nor the exact consumed P3.22 receipt"
                ) from predecessor_exc
            if (
                predecessor.get("raw_observer")
                != P323_CONSUMED_P322_BASELINE_IDENTITY
                or predecessor.get("carrier_record_offset")
                != P323_CONSUMED_P322_RECORD_OFFSET
            ):
                raise EvidenceError(
                    "P3.23 predecessor baseline placement differs"
                )
            return {
                "classification": "P323_CURRENT_RUN_ABSENT_P322_PREDECESSOR_EXACT",
                "exact_record_count": 0,
                "family_count": 1,
                "integrity_issue": False,
                "baseline_clean": True,
            }
        return {
            "classification": baseline["classification"],
            "exact_record_count": 0,
            "family_count": 0 if baseline["baseline_clean"] else 1,
            "integrity_issue": baseline["integrity_issue"],
            "baseline_clean": baseline["baseline_clean"],
        }
    if item["kind"] in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        result = (
            classify_same_ring_multiboot(payload, item)
            if item["kind"] == SAME_RING_MULTIBOOT_KIND
            else classify_same_ring(payload, item)
        )
        exact_count = result["exact_record_count"]
        family_count = result["family_count"]
        clean = (
            result["classification"] == "ZERO_AMBIGUOUS"
            and result["integrity_issue"] is False
            and exact_count == 0
            and family_count == 0
        )
        return {
            "classification": result["classification"],
            "exact_record_count": exact_count,
            "family_count": family_count,
            "integrity_issue": result["integrity_issue"],
            "baseline_clean": clean,
        }

    marker = item["marker"].encode("ascii")
    family = item["family"].encode("ascii")
    exact_count = payload.count(marker)
    family_count = payload.count(family)
    return {
        "classification": (
            "BASELINE_CLEAN"
            if exact_count == 0 and family_count == 0
            else "BASELINE_FAMILY_PRESENT"
        ),
        "exact_record_count": exact_count,
        "family_count": family_count,
        "integrity_issue": False,
        "baseline_clean": exact_count == 0 and family_count == 0,
    }
