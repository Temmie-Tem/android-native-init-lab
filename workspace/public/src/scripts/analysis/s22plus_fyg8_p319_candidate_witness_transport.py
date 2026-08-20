#!/usr/bin/env python3
"""Audit the candidate path from live printk witnesses to retained Carrier.

Host-only.  The stock corpus proves several useful driver messages exist, but
the current P3.18 candidate intentionally omits sec_log_buf and writes its
Carrier directly into the reserved ring.  This audit binds that discontinuity,
the existing loss-detecting /dev/kmsg reader, and the successor transport rule.
It grants no device or live authority.
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
KERNEL = PRIVATE / (
    "work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/"
    "msm-kernel"
)
OUTPUT_ROOT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/candidate-witness-transport-20260820-02"
)
INPUT_ROOT = OUTPUT_ROOT / "inputs"
OUTPUT = OUTPUT_ROOT / "result.json"

SCHEMA = "s22plus-fyg8-p319-candidate-witness-transport-v1"
VERDICT = "PASS_P319_CANDIDATE_WITNESS_TRANSPORT_H0"
TARGET = {
    "model": "SM-S906N",
    "codename": "g0q",
    "build": "S906NKSS7FYG8",
}


class AuditError(RuntimeError):
    """An exact input, publication property, or semantic seam differs."""


_BOUND_AUDITOR_SOURCE = globals().get("_P319_WITNESS_TRANSPORT_BOUND_SOURCE")


@dataclass(frozen=True)
class InputSpec:
    source: Path
    snapshot: str
    size: int
    sha256: str
    maximum: int


SPECS: dict[str, InputSpec] = {
    "p318_static": InputSpec(
        P318 / "static-check-result.json",
        "p318-static-check-result.json",
        554_578,
        "2a4d639b55aa21cf8f52dba505e9bc2d9dfd33f20cd3b217a7c482906aeea4df",
        1024 * 1024,
    ),
    "candidate_patch": InputSpec(
        P318 / "intent/candidate.patch",
        "p318-candidate.patch",
        42_020,
        "d839850e6e95cea4b199e3bb8217a3112012bf845279d7557d6792aa745662a5",
        128 * 1024,
    ),
    "plan": InputSpec(
        P318 / "intent/materialized-sources/s22plus_fyg8_p286_e3_plan.h",
        "p318-effective-plan.h",
        5_142,
        "682f18fb470b0e538eb463db5d2a865864b8aaa4681b41230e7c20cc134e70d7",
        32 * 1024,
    ),
    "runtime_wrapper": InputSpec(
        P318 / "intent/materialized-sources/s22plus_fyg8_p290_e3_runtime.c",
        "p318-runtime-wrapper.c",
        30_664,
        "8c0bf6a4765aa2a27bfe420de6c8599366267e546422378a21f586a8beeb9b7b",
        128 * 1024,
    ),
    "runtime_include": InputSpec(
        P318 / "intent/materialized-sources/s22plus_fyg8_p290_e3_runtime.inc.c",
        "p318-runtime-include.c",
        397_669,
        "050a8eb0deeb755540e9ca860b0ab50a6e9d69c02a644805f7cfd6eae644e42e",
        512 * 1024,
    ),
    "sec_log_main": InputSpec(
        KERNEL / "drivers/samsung/debug/log_buf/sec_log_buf_main.c",
        "sec_log_buf_main.c",
        16_972,
        "296f4fc175d958feb35b92c8736faf6361ade2e7c447d9a9af5a93f59bdb97b8",
        64 * 1024,
    ),
    "sec_log_console": InputSpec(
        KERNEL / "drivers/samsung/debug/log_buf/sec_log_buf_console.c",
        "sec_log_buf_console.c",
        1_225,
        "8a1dd1559b55481935691604132898353f6933e6c9655e5ebbe0f3311af21588",
        16 * 1024,
    ),
    "sec_log_header": InputSpec(
        KERNEL / "include/linux/samsung/debug/sec_log_buf.h",
        "sec_log_buf.h",
        748,
        "5ed73be105e4984f3b4767229094af3f1a2e0f7258df9f648f7d32abc545d46e",
        16 * 1024,
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
        raise AuditError("candidate witness transport output already exists")
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
    result = {}
    for key, spec in SPECS.items():
        result[key] = stable_bytes(
            INPUT_ROOT / spec.snapshot,
            label=f"preserved {key}",
            maximum=spec.maximum,
            expected_size=spec.size,
            expected_sha256=spec.sha256,
            required_mode=0o400,
            required_nlink=1,
        )
    return result


def publish_result(payload: bytes) -> None:
    _write_exclusive(OUTPUT, payload)
    _fsync_directory(OUTPUT_ROOT)
    existing = stable_bytes(
        OUTPUT,
        label="candidate witness transport receipt",
        maximum=256 * 1024,
        expected_size=len(payload),
        expected_sha256=sha256(payload),
        required_mode=0o400,
        required_nlink=1,
    )
    if existing != payload:
        raise AuditError("candidate witness transport publication differs")


def load_bound_auditor() -> Any:
    payload = stable_bytes(AUDITOR, label="auditor bootstrap", maximum=1024 * 1024)
    module = types.ModuleType("s22plus_fyg8_p319_candidate_witness_transport_bound")
    module.__file__ = str(AUDITOR)
    module.__package__ = ""
    module.__dict__["_P319_WITNESS_TRANSPORT_BOUND_SOURCE"] = payload
    sys.modules[module.__name__] = module
    try:
        code = compile(payload.decode("utf-8"), str(AUDITOR), "exec", dont_inherit=True)
        exec(code, module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("auditor bound execution failed") from exc
    return module


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise AuditError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("ascii"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                AuditError(f"{label} non-finite number: {token}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict ASCII JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} root differs")
    return value


def _ordered_once(data: bytes, tokens: tuple[bytes, ...], label: str) -> None:
    positions = []
    for token in tokens:
        if data.count(token) != 1:
            raise AuditError(f"{label} token multiplicity differs")
        positions.append(data.index(token))
    if positions != sorted(positions):
        raise AuditError(f"{label} token order differs")


def _c_function_body(source: bytes, name: str) -> bytes:
    token = name.encode("ascii") + b"("
    offset = 0
    while True:
        start = source.find(token, offset)
        if start < 0:
            raise AuditError(f"exact C function is absent: {name}")
        open_paren = start + len(name)
        depth = 0
        close_paren = -1
        for index in range(open_paren, len(source)):
            if source[index] == ord("("):
                depth += 1
            elif source[index] == ord(")"):
                depth -= 1
                if depth == 0:
                    close_paren = index
                    break
        if close_paren < 0:
            raise AuditError(f"exact C signature is truncated: {name}")
        cursor = close_paren + 1
        while cursor < len(source) and chr(source[cursor]).isspace():
            cursor += 1
        if cursor < len(source) and source[cursor] == ord("{"):
            depth = 1
            end = cursor + 1
            while end < len(source) and depth:
                if source[end] == ord("{"):
                    depth += 1
                elif source[end] == ord("}"):
                    depth -= 1
                end += 1
            if depth:
                raise AuditError(f"exact C body is truncated: {name}")
            return source[start:end]
        offset = close_paren + 1


def _exact_function(
    source: bytes, name: str, expected_size: int, expected_sha256: str
) -> bytes:
    body = _c_function_body(source, name)
    if len(body) != expected_size or sha256(body) != expected_sha256:
        raise AuditError(f"exact C function identity differs: {name}")
    return body


def audit_static_closure(payload: bytes) -> dict[str, Any]:
    value = strict_json(payload, "P3.18 static closure")
    try:
        closure = value["candidate"]["module_closure"]
        rows = closure["modules"]
    except (KeyError, TypeError) as exc:
        raise AuditError("P3.18 module closure path differs") from exc
    if (
        closure.get("schema") != "s22plus_fyg8_p317_stock_closure_h0_v1"
        or closure.get("sec_log_buf_absent") is not True
        or not isinstance(rows, list)
        or len(rows) != 69
        or any(not isinstance(row, dict) for row in rows)
        or any(row.get("file") == "sec_log_buf.ko" for row in rows)
    ):
        raise AuditError("P3.18 sec_log_buf absence differs")
    return {
        "stock_module_closure_count": len(rows),
        "sec_log_buf_absent": True,
        "candidate_printk_has_no_sec_log_buf_retained_sink": True,
    }


def audit_effective_plan(plan: bytes) -> dict[str, Any]:
    rows = re.findall(
        rb'^    \{"([^"]+)", "([^"]+)", "([^"]*)"\},$', plan, re.MULTILINE
    )
    if (
        len(rows) != 70
        or rows[0]
        != (b"s22plus_dwc3_event_latch.ko", b"s22plus_dwc3_event_latch", b"")
        or rows[-1] != (b"i2c-msm-geni.ko", b"i2c_msm_geni", b"")
        or any(b"sec_log_buf" in field for row in rows for field in row)
    ):
        raise AuditError("P3.18 effective plan shape differs")
    names = [row[0].decode("ascii") for row in rows]
    if "mfd_max77705.ko" in names or "pdic_max77705.ko" in names:
        raise AuditError("P3.18 unexpectedly carries stock MAX77705 modules")
    return {
        "effective_early_module_count": len(rows),
        "sec_log_buf_in_plan": False,
        "mfd_max77705_in_plan": False,
        "pdic_max77705_in_plan": False,
        "current_p318_can_emit_stock_pdic_witnesses": False,
    }


def audit_direct_carrier(patch: bytes) -> dict[str, Any]:
    tokens = (
        b"+#define S22_FYG8_E1_LOG_SIZE\t\t0x200000U",
        b"+\tseed_idx = READ_ONCE(head->idx);",
        b"+\ts22_fyg8_e1_state.seed_idx = seed_idx;",
        b"+\tcursor = seed_idx % payload_size;",
        b"+\ts22_fyg8_e1_state.proof_pos = cursor >= sizeof(record) ?",
    )
    _ordered_once(patch, tokens, "direct Carrier seed")
    stable = (
        b"+\t\tREAD_ONCE(head->idx) == s22_fyg8_e1_state.seed_idx &&"
    )
    if patch.count(stable) != 1 or patch.count(b"s22_fyg8_e1_header_matches(head)") < 6:
        raise AuditError("direct Carrier idx-stability gate differs")
    if b"__log_buf_write" in patch or b"sec_log_buf_get_header" in patch:
        raise AuditError("direct Carrier unexpectedly uses the Samsung logger API")
    if patch.count(b"&head->buf[s22_fyg8_e1_state.proof_pos]") != 3:
        raise AuditError("direct Carrier reserved-byte stores differ")
    return {
        "reserved_region_total_bytes": 2_097_152,
        "reserved_region_header_bytes": 16,
        "reserved_region_payload_bytes": 2_097_136,
        "carrier_seed_is_reserved_header_idx": True,
        "carrier_writes_reserved_bytes_directly": True,
        "carrier_does_not_advance_header_idx": True,
        "every_carrier_update_requires_idx_equal_seed": True,
    }


def audit_live_kmsg_transport(wrapper: bytes, runtime: bytes) -> dict[str, Any]:
    load = _exact_function(
        wrapper,
        "p241_load_and_verify_module",
        627,
        "cff3faef659e0cecca7699d40ce0a7149e6e9cf3dafda1a53b5390d9331f712e",
    )
    run = _exact_function(
        wrapper,
        "p241_run",
        7_199,
        "002878abf56c20ee94ecd2d8b96505cdcd50911b85809725733ba7e40a8c2b6c",
    )
    begin = _exact_function(
        runtime,
        "p303_kmsg_begin",
        650,
        "881184bdc5642ab22d1d44af55e518c1d7a2c90c5c3aaec5bce15974bc1f63b1",
    )
    record = _exact_function(
        runtime,
        "p303_kmsg_record",
        3_087,
        "68b4a4eb7d1e4c0653d3873b4f2b651de1b25f87f1742abfc42e46a47659d45f",
    )
    drain = _exact_function(
        runtime,
        "p303_kmsg_drain",
        623,
        "2a33c2a7a68703eb938012b228f791c0365514066ed00aebecff20d234c1deb8",
    )
    finish = _exact_function(
        runtime,
        "p303_kmsg_finish",
        301,
        "a680e581a5f931827590ac2d8423ed03158e1bf43e439a9ae27c304e68cf822b",
    )
    _ordered_once(
        begin,
        (
            b'"/dev/kmsg", S_IFCHR | 0600U, make_dev(1U, 11U)',
            b'"/dev/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC, 0',
            b"p303_lseek((int)fd, 0, P303_SEEK_END)",
            b"g_p303_kmsg.started = 1U;",
        ),
        "live kmsg begin",
    )
    _ordered_once(
        run,
        (
            b"long p303_kmsg_begin_rc = p303_kmsg_begin();",
            b"for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index)",
            b"for (size_t index = P305_FOLDED_MODULE_INDEX;",
            b"long p303_kmsg_module_rc = p303_kmsg_drain();",
        ),
        "kmsg acquisition around module loop",
    )
    if (
        drain.count(b"amount == -P303_EPIPE") != 1
        or drain.count(b"P303_DETAIL_KMSG_RING_LOSS") != 1
        or record.count(b"sequence != g_p303_kmsg.previous_sequence + 1U") != 1
        or record.count(b"P303_DETAIL_KMSG_SEQUENCE_CONTRADICTION") < 2
        or finish.count(b"p303_kmsg_drain()") != 1
    ):
        raise AuditError("live kmsg loss/sequence gate differs")
    if b"bytes_read" in runtime or b"total_bytes" in runtime:
        raise AuditError("P3.18 unexpectedly retains a kmsg byte counter")
    if b"p303_kmsg_drain" in load:
        raise AuditError("P3.18 unexpectedly drains after each module")
    return {
        "opens_dev_kmsg_before_module_loop": True,
        "starts_at_live_tail": True,
        "drains_after_complete_module_loop": True,
        "drains_after_each_module": False,
        "epipe_ring_loss_is_fail_closed": True,
        "sequence_gap_is_fail_closed": True,
        "record_capacity_bytes": 4_096,
        "cumulative_bytes_counted": False,
        "raw_kmsg_persisted": False,
        "existing_parser_can_be_extended_without_sec_log_buf": True,
    }


def audit_sec_log_writer(main: bytes, console: bytes, header: bytes) -> dict[str, Any]:
    write = _exact_function(
        main,
        "__log_buf_write",
        416,
        "ffcd711fa19134011019931b46b2617e022393d4bd369493430a8476ae7dc0a9",
    )
    early = _exact_function(
        main,
        "__log_buf_pull_early_buffer",
        479,
        "22c267894ce4b1fac881f9c9cc276e46212dc7947cfaa82669658204f8b5ad8c",
    )
    con = _exact_function(
        console,
        "sec_log_buf_write_console",
        171,
        "08dde5ca5cf85d175afe0528ede728819775a08788658e7605faf3d037d0f20c",
    )
    _ordered_once(
        write,
        (
            b"idx = s_log_buf->idx % sec_log_buf_size;",
            b"__log_buf_memcpy_toio(&(s_log_buf->buf[idx]), s, f_len);",
            b"s_log_buf->idx += (uint32_t)count;",
        ),
        "Samsung retained writer",
    )
    _ordered_once(
        early,
        (b"copied = __pull_early_buffer", b"__log_buf_write(buf, copied);"),
        "Samsung early-buffer import",
    )
    _ordered_once(
        con,
        (b"__log_buf_is_acceptable(s, count)", b"__log_buf_write(s, count);"),
        "Samsung console writer",
    )
    _ordered_once(
        main,
        (
            b"DEVICE_BUILDER(__last_kmsg_pull_last_log, NULL)",
            b"DEVICE_BUILDER(__log_buf_pull_early_buffer, NULL)",
            b"DEVICE_BUILDER(__log_buf_logger_init, __log_buf_logger_exit)",
        ),
        "Samsung logger probe order",
    )
    for token in (
        b"uint32_t boot_cnt;",
        b"uint32_t magic;",
        b"uint32_t idx;",
        b"uint32_t prev_idx;",
    ):
        if header.count(token) != 1:
            raise AuditError("Samsung retained header differs")
    return {
        "positive_write_advances_header_idx_by_count": True,
        "probe_imports_early_printk_before_registering_live_logger": True,
        "accepted_console_printk_routes_to_retained_writer": True,
        "adding_logger_after_carrier_seed_can_invalidate_idx_stability": True,
    }


def build_result(inputs: dict[str, bytes]) -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise AuditError("result must execute from the bound auditor source")
    static = audit_static_closure(inputs["p318_static"])
    plan = audit_effective_plan(inputs["plan"])
    carrier = audit_direct_carrier(inputs["candidate_patch"])
    kmsg = audit_live_kmsg_transport(
        inputs["runtime_wrapper"], inputs["runtime_include"]
    )
    logger = audit_sec_log_writer(
        inputs["sec_log_main"], inputs["sec_log_console"], inputs["sec_log_header"]
    )
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "scope": {
            "tier": "H0",
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
        "candidate_static_closure": static,
        "effective_plan": plan,
        "direct_carrier": carrier,
        "existing_live_kmsg_transport": kmsg,
        "samsung_retained_logger": logger,
        "conclusion": {
            "stock_pr_info_survival_proves_candidate_retention": False,
            "current_p318_printk_witnesses_reach_retained_carrier": False,
            "current_p318_can_reach_stock_pdic_emitters": False,
            "two_mib_sec_log_byte_budget_applies_to_current_direct_carrier": False,
            "adding_sec_log_buf_without_carrier_redesign_is_allowed": False,
            "reuse_existing_live_kmsg_reader": True,
            "drain_after_each_relevant_module": True,
            "count_cumulative_kmsg_record_bytes": True,
            "fail_closed_on_epipe_or_sequence_gap": True,
            "publish_structured_witness_summary_through_direct_carrier": True,
            "persist_raw_printk_lines_as_authority": False,
            "next_h0_unit": (
                "qualify a bounded P319 parser over the existing live /dev/kmsg "
                "reader and an external positive corpus before changing candidate bytes"
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
            label="candidate witness transport receipt",
            maximum=256 * 1024,
            expected_size=len(payload),
            expected_sha256=sha256(payload),
            required_mode=0o400,
            required_nlink=1,
        )
        if existing != payload:
            raise AuditError("candidate witness transport receipt differs")
    print(f"{VERDICT} {len(payload)} {sha256(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
