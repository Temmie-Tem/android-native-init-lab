#!/usr/bin/env python3
"""Derive the P3.19 successor module-plan capacity and EUD identity contract.

Host-only.  This consumes the exact P3.18 effective plan/runtime and the
retained FYG8 modules.dep.  It derives the smallest stock-MAX77705 plan delta,
checks the folded stage representation, and proves why the inherited literal
EUD index is stale.  It does not materialize candidate bytes or choose a new
module-symbol provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
AUDITOR = Path(__file__).resolve()
PRIVATE = ROOT / "workspace/private"
P318 = PRIVATE / "outputs/s22plus_fyg8_p318"
OUTPUT_ROOT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/successor-module-plan-v2-20260820-02"
)
INPUT_ROOT = OUTPUT_ROOT / "inputs"
OUTPUT = OUTPUT_ROOT / "result.json"

SCHEMA = "s22plus-fyg8-p319-successor-module-plan-v2"
VERDICT = "PASS_P319_SUCCESSOR_MODULE_PLAN_V2_H0"
TARGET = {
    "model": "SM-S906N",
    "codename": "g0q",
    "build": "S906NKSS7FYG8",
}
EUD_IDENTITY = ("eud.ko", "eud", "")
SUCCESSOR_ADDITIONS = (
    ("spu_verify.ko", "spu_verify", ""),
    ("mfd_max77705.ko", "mfd_max77705", ""),
    ("pdic_max77705.ko", "pdic_max77705", ""),
)
EXPECTED_CLOSURE_BY_DEPTH = {
    0: (
        "if_cb_manager.ko",
        "redriver.ko",
        "spu_verify.ko",
        "switch_class.ko",
        "usb_notify_layer.ko",
        "vbus_notifier.ko",
    ),
    1: (
        "common_muic.ko",
        "mfd_max77705.ko",
        "pdic_notifier_module.ko",
        "qc_usb_audio.ko",
    ),
    2: ("usb_typec_manager.ko",),
    3: ("usb_f_ss_mon_gadget.ko",),
    4: ("dwc3-msm.ko",),
    5: ("pdic_max77705.ko",),
}


class AuditError(RuntimeError):
    """An exact input, derivation, or publication invariant differs."""


_BOUND_AUDITOR_SOURCE = globals().get("_P319_SUCCESSOR_PLAN_BOUND_SOURCE")


@dataclass(frozen=True)
class InputSpec:
    source: Path
    snapshot: str
    size: int
    sha256: str
    maximum: int


SPECS: dict[str, InputSpec] = {
    "p318_plan": InputSpec(
        P318 / "intent/materialized-sources/s22plus_fyg8_p286_e3_plan.h",
        "p318-effective-plan.h",
        5_142,
        "682f18fb470b0e538eb463db5d2a865864b8aaa4681b41230e7c20cc134e70d7",
        32 * 1024,
    ),
    "p318_wrapper": InputSpec(
        P318 / "intent/materialized-sources/s22plus_fyg8_p290_e3_runtime.c",
        "p318-runtime-wrapper.c",
        30_664,
        "8c0bf6a4765aa2a27bfe420de6c8599366267e546422378a21f586a8beeb9b7b",
        128 * 1024,
    ),
    "p318_runtime": InputSpec(
        P318 / "intent/materialized-sources/s22plus_fyg8_p290_e3_runtime.inc.c",
        "p318-runtime-include.c",
        397_669,
        "050a8eb0deeb755540e9ca860b0ab50a6e9d69c02a644805f7cfd6eae644e42e",
        512 * 1024,
    ),
    "modules_dep": InputSpec(
        PRIVATE / "p319_stock_userspace/vendor_dlkm/modules.dep",
        "vendor-dlkm-modules.dep",
        53_241,
        "4687ecc3000fda31a8ba63a757e665c6e8d33a0a44d8e5da337d0c38d39d4bb5",
        128 * 1024,
    ),
    "p318_transport_auditor": InputSpec(
        ROOT
        / "workspace/public/src/scripts/analysis/"
        "s22plus_fyg8_p319_candidate_witness_transport.py",
        "p318-transport-auditor.py",
        24_025,
        "13f226348a5953aac8f4913358a2215ea3cc7a155d9dc8b11f816873fb2e76f7",
        128 * 1024,
    ),
}


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def stable_bytes(
    path: Path,
    *,
    label: str,
    maximum: int,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
    required_mode: int | None = None,
    required_nlink: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink < 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or _stat_identity(before) != _stat_identity(inside)
        or _stat_identity(before) != _stat_identity(after)
        or (expected_size is not None and len(payload) != expected_size)
        or (expected_sha256 is not None and sha256(payload) != expected_sha256)
        or (required_mode is not None and stat.S_IMODE(before.st_mode) != required_mode)
        or (required_nlink is not None and before.st_nlink != required_nlink)
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_exclusive(path: Path, payload: bytes, mode: int = 0o400) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        mode,
    )
    try:
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise AuditError(f"short write: {path.name}")
            offset += written
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or stat.S_IMODE(state.st_mode) != mode
            or state.st_nlink != 1
            or state.st_size != len(payload)
        ):
            raise AuditError(f"published file metadata differs: {path.name}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _create_output_dirs() -> None:
    if OUTPUT_ROOT.exists() or OUTPUT_ROOT.is_symlink():
        raise AuditError("successor module-plan output already exists")
    os.mkdir(OUTPUT_ROOT, 0o700)
    os.chmod(OUTPUT_ROOT, 0o700)
    os.mkdir(INPUT_ROOT, 0o700)
    os.chmod(INPUT_ROOT, 0o700)
    _fsync_directory(INPUT_ROOT)
    _fsync_directory(OUTPUT_ROOT)
    _fsync_directory(OUTPUT_ROOT.parent)


def load_inputs(materialize: bool) -> dict[str, bytes]:
    if materialize:
        source_payloads = {
            key: stable_bytes(
                spec.source,
                label=f"source {key}",
                maximum=spec.maximum,
                expected_size=spec.size,
                expected_sha256=spec.sha256,
            )
            for key, spec in SPECS.items()
        }
        _create_output_dirs()
        for key, spec in SPECS.items():
            _write_exclusive(INPUT_ROOT / spec.snapshot, source_payloads[key])
        _fsync_directory(INPUT_ROOT)
    return {
        key: stable_bytes(
            INPUT_ROOT / spec.snapshot,
            label=f"preserved {key}",
            maximum=spec.maximum,
            expected_size=spec.size,
            expected_sha256=spec.sha256,
            required_mode=0o400,
            required_nlink=1,
        )
        for key, spec in SPECS.items()
    }


def publish_result(payload: bytes) -> None:
    _write_exclusive(OUTPUT, payload)
    _fsync_directory(OUTPUT_ROOT)
    existing = stable_bytes(
        OUTPUT,
        label="successor module-plan receipt",
        maximum=256 * 1024,
        expected_size=len(payload),
        expected_sha256=sha256(payload),
        required_mode=0o400,
        required_nlink=1,
    )
    if existing != payload:
        raise AuditError("successor module-plan publication differs")


def load_bound_auditor() -> Any:
    payload = stable_bytes(AUDITOR, label="auditor bootstrap", maximum=1024 * 1024)
    module = types.ModuleType("s22plus_fyg8_p319_successor_module_plan_v2_bound")
    module.__file__ = str(AUDITOR)
    module.__package__ = ""
    module.__dict__["_P319_SUCCESSOR_PLAN_BOUND_SOURCE"] = payload
    sys.modules[module.__name__] = module
    try:
        code = compile(payload.decode("utf-8"), str(AUDITOR), "exec", dont_inherit=True)
        exec(code, module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("auditor bound execution failed") from exc
    return module


def parse_plan(payload: bytes) -> list[tuple[str, str, str]]:
    begin = b"static const struct s22plus_o2_module_plan_entry s22plus_o2_module_plan[] = {\n"
    end = b"};\n\n#define S22PLUS_O2_MODULE_PLAN_COUNT"
    if payload.count(begin) != 1 or payload.count(end) != 1:
        raise AuditError("effective plan array boundary differs")
    body = payload.split(begin, 1)[1].split(end, 1)[0]
    pattern = re.compile(rb'^    \{"([^"\\]+)", "([^"\\]+)", "([^"\\]*)"\},$')
    rows: list[tuple[str, str, str]] = []
    for line in body.splitlines():
        match = pattern.fullmatch(line)
        if match is None:
            raise AuditError("effective plan row grammar differs")
        rows.append(tuple(item.decode("ascii") for item in match.groups()))
    if not rows or len({row[0] for row in rows}) != len(rows):
        raise AuditError("effective plan filenames are empty or duplicated")
    if len({row[1] for row in rows}) != len(rows) or any(row[2] for row in rows):
        raise AuditError("effective plan runtime names or parameters differ")
    return rows


def parse_modules_dep(payload: bytes) -> dict[str, tuple[str, ...]]:
    prefix = "/vendor/lib/modules/"
    graph: dict[str, tuple[str, ...]] = {}
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise AuditError("modules.dep is not UTF-8") from exc
    for line in lines:
        if not line or line.count(":") != 1:
            raise AuditError("modules.dep line grammar differs")
        left, right = line.split(":", 1)
        if not left.startswith(prefix):
            raise AuditError("modules.dep module path differs")
        name = left[len(prefix):]
        dependencies = []
        for item in right.split():
            if not item.startswith(prefix):
                raise AuditError("modules.dep dependency path differs")
            dependencies.append(item[len(prefix):])
        if name in graph or len(set(dependencies)) != len(dependencies):
            raise AuditError("modules.dep duplicates a module or dependency")
        graph[name] = tuple(dependencies)
    return graph


def dependency_closure(
    graph: dict[str, tuple[str, ...]], target: str
) -> set[str]:
    complete: set[str] = set()
    active: set[str] = set()

    def visit(name: str) -> None:
        if name in complete:
            return
        if name in active:
            raise AuditError(f"dependency cycle at {name}")
        if name not in graph:
            raise AuditError(f"dependency graph lacks {name}")
        active.add(name)
        for dependency in graph[name]:
            visit(dependency)
        active.remove(name)
        complete.add(name)

    visit(target)
    return complete


def dependency_depths(
    graph: dict[str, tuple[str, ...]], members: set[str]
) -> dict[str, int]:
    cache: dict[str, int] = {}

    def depth(name: str) -> int:
        if name in cache:
            return cache[name]
        children = [item for item in graph[name] if item in members]
        value = 0 if not children else 1 + max(depth(item) for item in children)
        cache[name] = value
        return value

    for name in members:
        depth(name)
    return cache


def derive_eud_index(rows: list[tuple[str, str, str]]) -> int:
    matches = [index for index, row in enumerate(rows) if row == EUD_IDENTITY]
    if len(matches) != 1:
        raise AuditError("effective plan must contain one exact EUD identity")
    return matches[0]


def stage_model(count: int, wrapper: bytes) -> dict[str, int]:
    def define(name: bytes) -> int:
        match = re.search(
            rb"^#define " + name + rb" (0x[0-9a-f]+|[0-9]+)[UL]$",
            wrapper,
            re.MULTILINE,
        )
        if match is None:
            raise AuditError(f"stage define differs: {name.decode()}")
        return int(match.group(1), 0)

    module_base = define(b"S22_P241_MODULE_STAGE_BASE")
    gate_base = define(b"S22_P241_GATE_STAGE_BASE")
    detail_max = define(b"S22_P248_DETAIL_ERRNO_MAX")
    compact = re.sub(rb"\s+", b" ", wrapper)
    required_once = (
        b"P305_MODULE_STAGE_CAPACITY = S22_P241_GATE_STAGE_BASE - S22_P241_MODULE_STAGE_BASE,",
        b"P305_FOLDED_MODULE_INDEX = P305_MODULE_STAGE_CAPACITY - 1U,",
        b"const char *names[S22PLUS_O2_MODULE_PLAN_COUNT];",
        b"unsigned char found[S22PLUS_O2_MODULE_PLAN_COUNT];",
        b"for (size_t index = P305_FOLDED_MODULE_INDEX; index < S22PLUS_O2_MODULE_PLAN_COUNT; ++index)",
        b"P305_FOLDED_FAILURE_BASE + index",
    )
    if (
        any(compact.count(token) != 1 for token in required_once)
        or compact.count(b"S22PLUS_O2_MODULE_PLAN_COUNT <= 256U,") != 2
    ):
        raise AuditError("folded module stage consumer differs")
    failure_match = re.search(
        rb"P305_FOLDED_FAILURE_BASE = (0x[0-9a-f]+)U,", wrapper
    )
    if failure_match is None:
        raise AuditError("folded failure base differs")
    failure_base = int(failure_match.group(1), 0)
    capacity = gate_base - module_base
    folded_index = capacity - 1
    if capacity <= 0 or count < capacity or count > 256:
        raise AuditError("module count is outside the folded stage representation")
    last_index = count - 1
    last_failure = failure_base + last_index
    if last_failure > detail_max or last_index > 0xFF:
        raise AuditError("folded module detail exceeds retained fields")
    if failure_base + 255 != detail_max:
        raise AuditError("plan-count and folded-detail maxima do not coincide")
    return {
        "module_stage_base": module_base,
        "gate_stage_base": gate_base,
        "module_stage_capacity": capacity,
        "direct_module_count": folded_index,
        "folded_module_index": folded_index,
        "folded_tail_count": count - folded_index,
        "last_module_index": last_index,
        "last_module_item_index": last_index,
        "last_folded_failure_detail": last_failure,
        "last_direct_stage": module_base + folded_index - 1,
        "folded_stage": module_base + folded_index,
        "maximum_supported_plan_count": 256,
        "retained_detail_max": detail_max,
        "maximum_supported_folded_failure_detail": failure_base + 255,
    }


def audit_current_eud_consumer(
    rows: list[tuple[str, str, str]], wrapper: bytes, runtime: bytes
) -> dict[str, Any]:
    derived = derive_eud_index(rows)
    match = re.search(rb"^#define P307_EUD_MODULE_INDEX ([0-9]+)U$", runtime, re.MULTILINE)
    if match is None:
        raise AuditError("inherited EUD literal differs")
    inherited = int(match.group(1))
    condition = b"if (index == P307_EUD_MODULE_INDEX) {"
    if wrapper.count(condition) != 1 or wrapper.count(b"p307_read_eud_cache();") != 1:
        raise AuditError("inherited EUD trigger consumer differs")
    direct_loop = wrapper.find(
        b"for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {"
    )
    load = wrapper.find(b"p241_load_and_verify_module(index));", direct_loop)
    trigger = wrapper.find(condition)
    folded_loop = wrapper.find(
        b"for (size_t index = P305_FOLDED_MODULE_INDEX;"
    )
    if not (0 <= direct_loop < load < trigger < folded_loop):
        raise AuditError("inherited EUD trigger is not inside the direct post-load seam")
    return {
        "identity": {
            "filename": EUD_IDENTITY[0],
            "runtime_name": EUD_IDENTITY[1],
            "params": EUD_IDENTITY[2],
        },
        "derived_index": derived,
        "inherited_literal_index": inherited,
        "inherited_literal_matches_effective_plan": inherited == derived,
        "current_consumer_is_after_successful_module_load": True,
        "current_consumer_exists_only_in_direct_stage_loop": True,
        "successor_requires_same-plan-derived_index": True,
        "successor_requires_post-load_trigger_in_direct_and_folded_loops": True,
        "independent_runtime_index_literal_allowed": False,
    }


def audit_successor_plan(
    plan: bytes, modules_dep: bytes, wrapper: bytes, runtime: bytes
) -> dict[str, Any]:
    rows = parse_plan(plan)
    if (
        len(rows) != 70
        or rows[0] != ("s22plus_dwc3_event_latch.ko", "s22plus_dwc3_event_latch", "")
        or rows[-1] != ("i2c-msm-geni.ko", "i2c_msm_geni", "")
    ):
        raise AuditError("P3.18 base plan shape differs")
    graph = parse_modules_dep(modules_dep)
    closure = dependency_closure(graph, "pdic_max77705.ko")
    depths = dependency_depths(graph, closure)
    by_depth = {
        level: tuple(sorted(name for name, value in depths.items() if value == level))
        for level in sorted(set(depths.values()))
    }
    if by_depth != EXPECTED_CLOSURE_BY_DEPTH or len(closure) != 14:
        raise AuditError("MAX77705 dependency closure or depth differs")
    if graph.get("mfd_max77705.ko") != ("usb_notify_layer.ko",):
        raise AuditError("MFD direct dependency differs")
    base_names = [row[0] for row in rows]
    missing = sorted(closure - set(base_names))
    expected_missing = sorted(row[0] for row in SUCCESSOR_ADDITIONS)
    if missing != expected_missing:
        raise AuditError("successor marginal module set differs")
    successor = rows + list(SUCCESSOR_ADDITIONS)
    names = [row[0] for row in successor]
    if len(successor) != 73 or len(set(names)) != len(names):
        raise AuditError("successor plan count or uniqueness differs")
    positions = {name: index for index, name in enumerate(names)}
    violations = []
    for name in closure:
        for dependency in graph[name]:
            if dependency in closure and positions[dependency] > positions[name]:
                violations.append({"module": name, "needs": dependency})
    if violations:
        raise AuditError("successor plan violates dependency order")
    if positions["s22plus_dwc3_event_latch.ko"] != 0 or positions["dwc3-msm.ko"] != 59:
        raise AuditError("custom latch and stock DWC3 coexistence differs")
    eud = audit_current_eud_consumer(successor, wrapper, runtime)
    stage = stage_model(len(successor), wrapper)
    return {
        "base_plan_count": len(rows),
        "closure_count": len(closure),
        "base_overlap_count": len(closure & set(base_names)),
        "incremental_count": len(SUCCESSOR_ADDITIONS),
        "incremental_entries": [
            {"filename": row[0], "runtime_name": row[1], "params": row[2]}
            for row in SUCCESSOR_ADDITIONS
        ],
        "successor_plan_count": len(successor),
        "successor_plan_rows": [
            {"index": index, "filename": row[0], "runtime_name": row[1], "params": row[2]}
            for index, row in enumerate(successor)
        ],
        "dependency_depths": {
            str(level): list(names_at_level) for level, names_at_level in by_depth.items()
        },
        "dependency_order_violations": [],
        "custom_latch_index": positions["s22plus_dwc3_event_latch.ko"],
        "stock_dwc3_msm_index": positions["dwc3-msm.ko"],
        "custom_latch_replaces_stock_dwc3_msm": False,
        "new_dwc3_plan_row_required": False,
        "dwc3_symbol_provider_identity_qualified_for_successor": False,
        "stage_capacity": stage,
        "eud_trigger": eud,
    }


def audit_p318_negative_auditor(source: bytes) -> dict[str, Any]:
    required = (
        b"def audit_effective_plan(plan: bytes)",
        b'raise AuditError("P3.18 unexpectedly carries stock MAX77705 modules")',
        b'"mfd_max77705_in_plan": False',
        b'"pdic_max77705_in_plan": False',
    )
    if any(source.count(token) != 1 for token in required):
        raise AuditError("P3.18 negative auditor seam differs")
    return {
        "p318_absence_assertion_retained": True,
        "successor_plan_uses_separate_derivation": True,
        "p318_auditor_is_not_weakened": True,
    }


def build_result(inputs: dict[str, bytes]) -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise AuditError("unbound auditor cannot build an authoritative result")
    plan = audit_successor_plan(
        inputs["p318_plan"],
        inputs["modules_dep"],
        inputs["p318_wrapper"],
        inputs["p318_runtime"],
    )
    negative = audit_p318_negative_auditor(inputs["p318_transport_auditor"])
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": "IMPLEMENTED_REVIEW_PENDING",
        "target": TARGET,
        "scope": {
            "host_only": True,
            "device_contact": False,
            "adb_commands": 0,
            "usb_actions": 0,
            "odin_invocations": 0,
            "candidate_transfers": 0,
            "rollback_transfers": 0,
            "recovery_actions": 0,
            "replay": False,
            "live_authority_created": False,
        },
        "inputs": {key: identity(value) for key, value in sorted(inputs.items())},
        "implementation": {"auditor": identity(_BOUND_AUDITOR_SOURCE)},
        "p318_negative_boundary": negative,
        "successor_plan": plan,
        "conclusion": {
            "fourteen_new_rows_required": False,
            "three_new_rows_required": True,
            "successor_plan_count": 73,
            "current_folded_stage_representation_is_sufficient": True,
            "current_eud_literal_is_stale": True,
            "successor_eud_trigger_must_be_derived_from_exact_plan_identity": True,
            "successor_plan_header_materialized": False,
            "successor_runtime_implemented": False,
            "module_binary_identities_frozen_for_successor": False,
            "dwc3_symbol_provider_identity_qualified_for_successor": False,
            "candidate_build_qualified": False,
            "symbol_stub_authorized": False,
            "next_h0_unit": (
                "materialize the 73-row plan and a shared post-load EUD identity "
                "consumer, then bind exact module bytes before parser qualification"
            ),
        },
    }
    if stable_bytes(AUDITOR, label="post-run auditor", maximum=1024 * 1024) != _BOUND_AUDITOR_SOURCE:
        raise AuditError("auditor changed during execution")
    return result


def encode(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def run(materialize: bool) -> tuple[dict[str, Any], bytes]:
    inputs = load_inputs(materialize)
    result = build_result(inputs)
    return result, encode(result)


def main() -> int:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        return load_bound_auditor().main()
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit-only", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    _, payload = run(materialize=args.write)
    if args.write:
        publish_result(payload)
    else:
        existing = stable_bytes(
            OUTPUT,
            label="successor module-plan receipt",
            maximum=256 * 1024,
            expected_size=len(payload),
            expected_sha256=sha256(payload),
            required_mode=0o400,
            required_nlink=1,
        )
        if existing != payload:
            raise AuditError("successor module-plan receipt differs")
    print(f"{VERDICT} {len(payload)} {sha256(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
