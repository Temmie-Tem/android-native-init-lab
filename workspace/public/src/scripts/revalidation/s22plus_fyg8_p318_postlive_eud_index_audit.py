#!/usr/bin/env python3
"""Recover the committed P3.18 pre-Max77705 failure, host-only.

This tool has no subprocess, ADB, USB, Odin, transfer, or device-action path.
It binds the exact candidate intent, materialized plan/runtime/checkpoint bytes,
and both retained reads before correcting the frozen decoder's semantic view.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
POSTLIVE_MODEL = SCRIPT_DIR / "s22plus_fyg8_p318_postlive_carrier_model.py"
POSTLIVE_DECODER = SCRIPT_DIR / "s22plus_fyg8_p318_postlive_decoder.py"
POSTLIVE_AUDITOR = Path(__file__).resolve()
FROZEN_DECODER = SCRIPT_DIR / "s22plus_fyg8_p318_max77705_telemetry_decoder.py"
FROZEN_CARRIER_MODULE = "s22plus_fyg8_p310_carrier_model"
POSTLIVE_CARRIER_MODULE = "s22plus_fyg8_p318_postlive_carrier_model"
POSTLIVE_DECODER_MODULE = "s22plus_fyg8_p318_postlive_decoder"
INTENT = ROOT / "workspace/private/outputs/s22plus_fyg8_p318/intent/overlay-intent.json"
MATERIALIZED = INTENT.parent / "materialized-sources"
RUNTIME_WRAPPER = MATERIALIZED / "s22plus_fyg8_p290_e3_runtime.c"
RUNTIME_INCLUDE = MATERIALIZED / "s22plus_fyg8_p290_e3_runtime.inc.c"
LEGACY_RUNTIME = MATERIALIZED / "s22plus_r4w1e_e1_runtime.c"
PLAN_HEADER = MATERIALIZED / "s22plus_fyg8_p286_e3_plan.h"
CHECKPOINT = MATERIALIZED / "s22plus_fyg8_p290_checkpoint.c"
CHECKPOINT_HEADER = MATERIALIZED / "s22plus_r4w1e_checkpoint.h"
CLASSIFIER_INCLUDE = MATERIALIZED / "s22plus_fyg8_p282_classifier.inc.c"
P260_RUNTIME_INCLUDE = MATERIALIZED / "s22plus_fyg8_p260_e3_runtime.inc.c"
P286_CLASSIFIER_INCLUDE = MATERIALIZED / "s22plus_fyg8_p286_classifier.inc.c"
P288_CLASSIFIER_INCLUDE = MATERIALIZED / "s22plus_fyg8_p288_classifier.inc.c"
POSITION_HEADER = MATERIALIZED / "s22plus_fyg8_p290_positions.h"
TRACE_DESCRIPTOR_HEADER = MATERIALIZED / "s22plus_fyg8_p286_trace_descriptor.h"
CANDIDATE_PATCH = INTENT.parent / "candidate.patch"
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "s22plus-fyg8-p318-live-1"
)
RETAINED = (RUN_DIR / "rollback-observer-1.bin", RUN_DIR / "rollback-observer-2.bin")
OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "postlive-eud-index-recovery-20260817-01.json"
)

INTENT_SIZE = 126815
INTENT_SHA256 = "375db867fb55fc6d558c32e7b8fae8a704221cb6d4d4d3c40a3490c494669d3e"
RETAINED_SIZE = 2097136
RETAINED_SHA256 = "4a0d9db45040fca213c9d2a6c730e28217d360809ed8c19c4748d682509cdd5e"
RECORD_OFFSET = 1649274
SCHEMA = "s22plus_fyg8_p318_postlive_eud_index_audit_v2"
VERDICT = "PASS_P318_POSTLIVE_EUD_INDEX_RECOVERY_H0"


class AuditError(RuntimeError):
    """The exact retained evidence or its producer closure differs."""


_BOUND_AUDITOR_SOURCE = globals().get("_P318_BOUND_AUDITOR_SOURCE")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def stable_bytes(
    path: Path,
    size: int,
    digest: str,
    label: str,
    *,
    required_mode: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(size + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    identity = lambda value: (
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
    if (
        direct != resolved
        or not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or before.st_nlink != 1
        or (
            required_mode is not None
            and stat.S_IMODE(before.st_mode) != required_mode
        )
        or len(payload) != size
        or sha256(payload) != digest
        or identity(before) != identity(inside)
        or identity(before) != identity(after)
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def current_regular_bytes(path: Path, label: str) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        if before.st_size > 1_048_576:
            raise AuditError(f"{label} is oversized")
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(1_048_577)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    identity_tuple = lambda value: (
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
    if (
        direct != resolved
        or not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or before.st_nlink != 1
        or len(payload) != before.st_size
        or identity_tuple(before) != identity_tuple(inside)
        or identity_tuple(before) != identity_tuple(after)
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def load_bound_auditor() -> Any:
    payload = current_regular_bytes(POSTLIVE_AUDITOR, "post-live auditor bootstrap")
    module = types.ModuleType("s22plus_fyg8_p318_postlive_eud_index_audit_bound")
    module.__file__ = str(POSTLIVE_AUDITOR)
    module.__package__ = ""
    module.__dict__["_P318_BOUND_AUDITOR_SOURCE"] = payload
    try:
        code = compile(
            payload.decode("utf-8"),
            str(POSTLIVE_AUDITOR),
            "exec",
            dont_inherit=True,
        )
        exec(code, module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("post-live auditor bound-source execution failed") from exc
    return module


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise AuditError("candidate intent contains a duplicate JSON key")
        value[key] = item
    return value


def load_intent(payload: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                AuditError(f"candidate intent contains {token}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError("candidate intent is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AuditError("candidate intent root differs")
    return value


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def _materialized_inputs(intent: dict[str, Any]) -> dict[str, bytes]:
    declared = intent.get("generated_artifacts")
    if not isinstance(declared, dict):
        raise AuditError("candidate generated-artifact receipts are unavailable")
    paths = {
        "runtime_wrapper": RUNTIME_WRAPPER,
        "p290_e3_runtime_include": RUNTIME_INCLUDE,
        "p288_legacy_runtime": LEGACY_RUNTIME,
        "plan_header": PLAN_HEADER,
        "checkpoint_client": CHECKPOINT,
        "classifier_include": CLASSIFIER_INCLUDE,
        "p260_e3_runtime_include": P260_RUNTIME_INCLUDE,
        "p286_classifier_include": P286_CLASSIFIER_INCLUDE,
        "p288_classifier_include": P288_CLASSIFIER_INCLUDE,
        "p290_checkpoint_header": CHECKPOINT_HEADER,
        "p290_position_header": POSITION_HEADER,
        "trace_descriptor_header": TRACE_DESCRIPTOR_HEADER,
        "candidate_patch": CANDIDATE_PATCH,
    }
    if set(paths) != set(declared):
        raise AuditError("candidate generated-artifact key set differs")
    result: dict[str, bytes] = {}
    for key, path in paths.items():
        expected = declared.get(key)
        if (
            not isinstance(expected, dict)
            or type(expected.get("size")) is not int
            or not isinstance(expected.get("sha256"), str)
        ):
            raise AuditError(f"candidate {key} receipt differs")
        result[key] = stable_bytes(
            path,
            expected["size"],
            expected["sha256"],
            f"candidate {key}",
        )
    return result


def _local_imports(payload: bytes, label: str) -> tuple[str, ...]:
    try:
        tree = ast.parse(payload.decode("utf-8"), filename=label)
    except (UnicodeError, SyntaxError) as exc:
        raise AuditError(f"{label} is not exact Python source") from exc
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(
                alias.name
                for alias in node.names
                if alias.name.startswith("s22plus_fyg8_")
            )
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.startswith("s22plus_fyg8_")
        ):
            names.add(node.module)
    return tuple(sorted(names))


def _semantic_inputs(intent: dict[str, Any]) -> dict[str, bytes]:
    source_receipts = intent.get("source_receipts")
    if not isinstance(source_receipts, dict):
        raise AuditError("candidate source receipts are unavailable")
    frozen_expected = source_receipts.get("p318_decoder")
    if (
        not isinstance(frozen_expected, dict)
        or type(frozen_expected.get("size")) is not int
        or not isinstance(frozen_expected.get("sha256"), str)
    ):
        raise AuditError("frozen P3.18 decoder receipt differs")
    result = {
        "p318_frozen_decoder": stable_bytes(
            FROZEN_DECODER,
            frozen_expected["size"],
            frozen_expected["sha256"],
            "frozen P3.18 decoder",
        )
    }

    try:
        parent_sources = intent["parent_contract"]["parent_candidate_contract"][
            "identity_preimage"
        ]["sources"]
    except (KeyError, TypeError) as exc:
        raise AuditError("frozen parent semantic receipts are unavailable") from exc
    if not isinstance(parent_sources, dict):
        raise AuditError("frozen parent semantic receipts differ")
    pending = [FROZEN_CARRIER_MODULE]
    seen: set[str] = set()
    while pending:
        module_name = pending.pop()
        if module_name in seen:
            continue
        seen.add(module_name)
        path = SCRIPT_DIR / f"{module_name}.py"
        key = (
            "p310_carrier_model"
            if module_name == FROZEN_CARRIER_MODULE
            else f"p310_semantic__{module_name}"
        )
        expected = parent_sources.get(key)
        if (
            not isinstance(expected, dict)
            or type(expected.get("size")) is not int
            or not isinstance(expected.get("sha256"), str)
        ):
            raise AuditError(f"frozen semantic receipt differs: {module_name}")
        payload = stable_bytes(
            path,
            expected["size"],
            expected["sha256"],
            f"frozen semantic source {module_name}",
        )
        result[f"frozen_import__{module_name}"] = payload
        pending.extend(_local_imports(payload, module_name))
    if len(seen) != 35:
        raise AuditError("frozen Carrier recursive import count differs")
    return result


def _semantic_module_payloads(
    semantic_inputs: dict[str, bytes],
) -> dict[str, bytes]:
    prefix = "frozen_import__"
    return {
        key[len(prefix) :]: payload
        for key, payload in semantic_inputs.items()
        if key.startswith(prefix)
    }


def _module_order(payloads: dict[str, bytes]) -> tuple[str, ...]:
    dependencies = {
        name: tuple(
            dependency
            for dependency in _local_imports(payload, name)
            if dependency in payloads
        )
        for name, payload in payloads.items()
    }
    order: list[str] = []
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(name: str) -> None:
        if name in permanent:
            return
        if name in temporary:
            raise AuditError("frozen Carrier import graph contains a cycle")
        temporary.add(name)
        for dependency in dependencies[name]:
            visit(dependency)
        temporary.remove(name)
        permanent.add(name)
        order.append(name)

    for name in sorted(payloads):
        visit(name)
    return tuple(order)


def _load_bound_decoders(
    semantic_inputs: dict[str, bytes], implementation: dict[str, bytes]
) -> tuple[Any, Any, Any]:
    payloads = _semantic_module_payloads(semantic_inputs)
    if set(payloads) != set(_module_order(payloads)):
        raise AuditError("frozen Carrier import graph differs")
    loaded: dict[str, Any] = {}
    missing = object()
    previous: dict[str, Any] = {}

    def execute(name: str, payload: bytes, path: Path) -> None:
        if name not in previous:
            previous[name] = sys.modules.get(name, missing)
        module = types.ModuleType(name)
        module.__file__ = str(path)
        module.__package__ = ""
        sys.modules[name] = module
        try:
            code = compile(payload.decode("utf-8"), str(path), "exec")
            exec(code, module.__dict__)  # noqa: S102
        except Exception as exc:
            raise AuditError(f"bound Python module failed to load: {name}") from exc
        loaded[name] = module

    try:
        for name in _module_order(payloads):
            execute(name, payloads[name], SCRIPT_DIR / f"{name}.py")
        execute(POSTLIVE_CARRIER_MODULE, implementation["carrier_model"], POSTLIVE_MODEL)
        execute(POSTLIVE_DECODER_MODULE, implementation["decoder"], POSTLIVE_DECODER)
    finally:
        for name, old in previous.items():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
    try:
        return (
            loaded[FROZEN_CARRIER_MODULE],
            loaded[POSTLIVE_CARRIER_MODULE],
            loaded[POSTLIVE_DECODER_MODULE],
        )
    except KeyError as exc:
        raise AuditError("bound decoder module set differs") from exc


def _ordered(source: str, tokens: tuple[str, ...], label: str) -> None:
    cursor = -1
    for token in tokens:
        position = source.find(token, cursor + 1)
        if position < 0:
            raise AuditError(f"{label} source seam differs")
        cursor = position


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


def _exact_c_function(
    source: bytes,
    name: str,
    size: int,
    digest: str,
) -> bytes:
    body = _c_function_body(source, name)
    if len(body) != size or sha256(body) != digest:
        raise AuditError(f"exact C function body differs: {name}")
    return body


def _exact_c_block(
    source: bytes,
    token: bytes,
    size: int,
    digest: str,
    label: str,
) -> bytes:
    try:
        start = source.index(token)
        cursor = source.index(b"{", start) + 1
    except ValueError as exc:
        raise AuditError(f"{label} is absent") from exc
    depth = 1
    while cursor < len(source) and depth:
        if source[cursor] == ord("{"):
            depth += 1
        elif source[cursor] == ord("}"):
            depth -= 1
        cursor += 1
    if depth:
        raise AuditError(f"{label} is truncated")
    body = source[start:cursor]
    if len(body) != size or sha256(body) != digest:
        raise AuditError(f"{label} differs")
    return body


def _exact_span(
    source: bytes,
    start_token: bytes,
    end_token: bytes,
    size: int,
    digest: str,
    label: str,
) -> bytes:
    try:
        start = source.index(start_token)
        end = source.index(end_token, start) + len(end_token)
    except ValueError as exc:
        raise AuditError(f"{label} is absent") from exc
    body = source[start:end]
    if len(body) != size or sha256(body) != digest:
        raise AuditError(f"{label} differs")
    return body


def _return_expressions(body: bytes) -> tuple[bytes, ...]:
    return tuple(
        re.sub(rb"\s+", b" ", expression.strip())
        for expression in re.findall(rb"\breturn\s+([^;]+);", body)
    )


def _compact_c(body: bytes) -> bytes:
    return re.sub(rb"\s+", b" ", body.strip())


def audit_publication_detail_alias(inputs: dict[str, bytes]) -> dict[str, Any]:
    patch = inputs["candidate_patch"]
    patch_source = b"\n".join(
        line[1:] if line.startswith(b"+") and not line.startswith(b"+++") else line
        for line in patch.splitlines()
    )
    checkpoint = inputs["checkpoint_client"]
    checkpoint_header = inputs["p290_checkpoint_header"]
    wrapper = inputs["runtime_wrapper"]

    kernel_write = _exact_c_function(
        patch_source,
        "s22_fyg8_e1_write",
        3276,
        "16e9f75ad5ff30557c0ad478ab4cd077060aa67765baef342101e3b6669ce88d",
    )
    request_allowed = _exact_c_function(
        patch_source,
        "s22_fyg8_e1_request_allowed",
        611,
        "7e5831dc7d3dc8b5378b8a9c12883ebcadefa985d94b8425e7898bbc806fbaca",
    )
    try:
        proc_ops_start = patch_source.index(
            b"static const struct proc_ops s22_fyg8_e1_ops = {"
        )
        proc_ops_end = patch_source.index(b"\n};", proc_ops_start) + len(b"\n};")
    except ValueError as exc:
        raise AuditError("candidate checkpoint proc_ops differs") from exc
    proc_ops = patch_source[proc_ops_start:proc_ops_end]
    if (
        patch_source.count(b"static const struct proc_ops s22_fyg8_e1_ops = {") != 1
        or re.findall(
            rb"^\s*\.(proc_[a-z0-9_]+)\s*=", proc_ops, flags=re.MULTILINE
        )
        != [b"proc_write"]
        or proc_ops.count(b"s22_fyg8_e1_write") != 1
        or patch_source.count(
            b'proc_create("s22_checkpoint", 0200, NULL, &s22_fyg8_e1_ops)'
        )
        != 1
    ):
        raise AuditError("candidate checkpoint proc writer differs")
    kernel_order = (
        b"if (s22_fyg8_e1_state.terminal)",
        b"if (!s22_fyg8_e1_request_allowed(&request))",
        b"memcpy(&record->slots[next_slot].commit_crc, &next.commit_crc,",
        b"s22_fyg8_e1_state.active_slot = next_slot;",
        b"memcpy(&s22_fyg8_e1_state.active, &next,",
        b"s22_fyg8_e1_state.terminal =",
        b"*position += count;",
        b"return count;",
    )
    if tuple(kernel_write.index(token) for token in kernel_order) != tuple(
        sorted(kernel_write.index(token) for token in kernel_order)
    ):
        raise AuditError("candidate kernel slot commit order differs")
    if (
        b"return -EALREADY;" not in kernel_write
        or b"generation = s22_fyg8_e1_state.active.generation + 1U;"
        not in kernel_write
        or b"request.outcome != S22_FYG8_E1_PROGRESS;" not in kernel_write
        or b"size_t ordinal = s22_fyg8_e1_state.active.generation;"
        not in request_allowed
        or b"request->stage != sequence[ordinal]" not in request_allowed
        or b"request->item_index != expected_item" not in request_allowed
        or kernel_write.count(b"s22_fyg8_e1_state.active.generation") != 2
        or kernel_write.count(b"s22_fyg8_e1_state.terminal") != 2
        or kernel_write.count(b"s22_fyg8_e1_state.active_slot = next_slot;") != 1
        or kernel_write.count(b"memcpy(&s22_fyg8_e1_state.active, &next,") != 1
        or kernel_write.count(b"*position += count;") != 1
        or kernel_write.count(b"return count;") != 1
        or request_allowed.count(
            b"size_t ordinal = s22_fyg8_e1_state.active.generation;"
        )
        != 1
        or not _compact_c(kernel_write).endswith(
            b"s22_fyg8_e1_state.active_slot = next_slot; "
            b"memcpy(&s22_fyg8_e1_state.active, &next, "
            b"sizeof(s22_fyg8_e1_state.active)); "
            b"s22_fyg8_e1_state.terminal = "
            b"request.outcome != S22_FYG8_E1_PROGRESS; "
            b"*position += count; return count; }"
        )
    ):
        raise AuditError("candidate kernel stale-request rejection differs")

    publication_detail = _exact_c_function(
        checkpoint,
        "p292_publication_error_detail",
        676,
        "9877b4e4affea5124698d0f901bb667fb4d0a93816dd982915d489266d67d032",
    )
    normalize_failure = _exact_c_function(
        checkpoint,
        "p288_normalize_failure_detail",
        564,
        "526918fefade3e1926b28992abfd3a79161ca5b623245e07ada02d0d6c64c2d3",
    )
    publish_next = _exact_c_function(
        checkpoint,
        "p288_publish_next",
        2212,
        "940410e47465b3c6b12099d434ea5693f0e3479a0e4228478411efc60a4fad58",
    )
    fallback = _exact_c_function(
        checkpoint,
        "s22_p292_checkpoint_publication_failure_next",
        356,
        "e4ec6957a1083e2a583343d937727a30e4ea8b5d036cd25935002675ce065153",
    )
    failure_next = _exact_c_function(
        checkpoint,
        "s22_p290_checkpoint_failure_next",
        330,
        "a5c596e08a3226aab200f4b97323915c7cabc5d189c545d76519fe6f371b876a",
    )
    legacy_failure = _exact_c_function(
        checkpoint,
        "s22_r4w1e_checkpoint_failure",
        654,
        "2d6dca70ae77c545c2bbe32a446af8cd402a6b9780bacbf857b3593cdb09b6e7",
    )
    park = _exact_c_function(
        wrapper,
        "p292_park_after_checkpoint_error",
        631,
        "88a3cad833fe4f1382b6a25fea60a047be54ae6e222b3e6853cd1885b90b4e1f",
    )
    if (
        checkpoint_header.count(
            b"#define S22_P292_PUBLICATION_OPERATION_CLOSE 3U"
        )
        != 1
        or checkpoint_header.count(
            b"#define S22_P292_PUBLICATION_CLOSE_BASE 0x6000U"
        )
        != 1
        or b"operation == S22_P292_PUBLICATION_OPERATION_CLOSE" not in publication_detail
        or b"base = S22_P292_PUBLICATION_CLOSE_BASE;" not in publication_detail
        or b"*detail = (uint16_t)(base + (uint16_t)(-error));"
        not in publication_detail
        or tuple(
            publish_next.index(token)
            for token in (
                b"long written = sys_write(",
                b"long closed = sys_close(",
                b"if (written != (long)sizeof(request))",
                b"if (closed != 0)",
                b"client->generation = (uint8_t)(ordinal + 1U);",
            )
        )
        != tuple(
            sorted(
                publish_next.index(token)
                for token in (
                    b"long written = sys_write(",
                    b"long closed = sys_close(",
                    b"if (written != (long)sizeof(request))",
                    b"if (closed != 0)",
                    b"client->generation = (uint8_t)(ordinal + 1U);",
                )
            )
        )
        or b"p292_publication_error_detail(operation, error, &detail)" not in fallback
        or b"p288_normalize_failure_detail(operation_error, &detail)"
        not in failure_next
        or b"p288_normalize_failure_detail(operation_error, &detail)"
        not in legacy_failure
        or b"client, S22_P233_OUTCOME_FAILURE, detail, 0, 0U" not in fallback
        or b"s22_p292_checkpoint_last_publication_error(" not in park
        or b"s22_p292_checkpoint_publication_failure_next(" not in park
        or b"client->terminal = outcome != S22_P233_OUTCOME_PROGRESS;"
        not in publish_next
        or wrapper.count(
            b"static __attribute__((noreturn))\n"
            b"void p292_park_after_checkpoint_error(long triggering_rc)"
        )
        != 1
    ):
        raise AuditError("checkpoint close-error fallback model differs")
    if 0x6000 + 16 != 0x6010:
        raise AuditError("checkpoint close-error alias arithmetic differs")
    return {
        "candidate_checkpoint_proc_fields": ["proc_write"],
        "kernel_slot_commit_precedes_sys_write_success_return": True,
        "client_close_follows_successful_kernel_write": True,
        "kernel_active_generation_advances_before_client_close": True,
        "kernel_failure_terminal_advances_before_client_close": True,
        "stale_failure_retry_rejected_by_terminal": True,
        "stale_progress_retry_rejected_by_generation_position": True,
        "close_minus_16_aliases_0x6010": True,
        "close_minus_16_fallback_structurally_reachable": True,
        "close_minus_16_fallback_can_replace_retained_slot": False,
        "base_vfs_close_return_provenance_required": False,
        "failure_detail_uniquely_attributed_to_eud_reader": True,
        "failure_publication_is_terminal": True,
        "failure_publication_path_is_noreturn": True,
    }


def _module_plan(source: str) -> tuple[tuple[str, str, str], ...]:
    start_token = (
        "static const struct s22plus_o2_module_plan_entry "
        "s22plus_o2_module_plan[] = {"
    )
    try:
        start = source.index(start_token) + len(start_token)
        end = source.index("\n};", start)
    except ValueError as exc:
        raise AuditError("candidate module-plan extent differs") from exc
    rows = tuple(
        re.fullmatch(
            r'\s*\{"([^"]+)",\s*"([^"]+)",\s*"([^"]*)"\},\s*',
            line,
        )
        for line in source[start:end].splitlines()
        if line.strip()
    )
    if any(row is None for row in rows):
        raise AuditError("candidate module-plan row grammar differs")
    return tuple(row.groups() for row in rows if row is not None)


def _checkpoint_steps(source: str) -> tuple[tuple[int, int, str], ...]:
    try:
        start = source.index("static const struct s22_p248_step k_p248_e2_steps[] = {")
        end = source.index("\n};", start)
    except ValueError as exc:
        raise AuditError("candidate checkpoint step table differs") from exc
    rows = re.findall(
        r"\{0x([0-9a-f]{2})U, ([0-9]+)U, (S22_P248_STEP_[A-Z]+)\}",
        source[start:end],
    )
    if len(rows) != 107:
        raise AuditError("candidate checkpoint step count differs")
    return tuple((int(stage, 16), int(item), kind) for stage, item, kind in rows)


def audit_source_chain(
    inputs: dict[str, bytes],
    semantic_inputs: dict[str, bytes],
) -> dict[str, Any]:
    wrapper = inputs["runtime_wrapper"].decode("utf-8")
    runtime = inputs["p290_e3_runtime_include"].decode("utf-8")
    legacy_runtime = inputs["p288_legacy_runtime"].decode("utf-8")
    plan_source = inputs["plan_header"].decode("utf-8")
    checkpoint = inputs["checkpoint_client"].decode("utf-8")
    checkpoint_header = inputs["p290_checkpoint_header"].decode("utf-8")
    frozen_decoder_source = semantic_inputs["p318_frozen_decoder"].decode("utf-8")
    inherited_carrier_source = semantic_inputs[
        f"frozen_import__{FROZEN_CARRIER_MODULE}"
    ].decode("utf-8")
    publication_alias = audit_publication_detail_alias(inputs)
    if (
        frozen_decoder_source.count(
            "import s22plus_fyg8_p310_carrier_model as model"
        )
        != 1
        or inherited_carrier_source.count(
            "import s22plus_fyg8_p308_telemetry_spec as spec"
        )
        != 1
    ):
        raise AuditError("frozen decoder semantic inheritance differs")
    _ordered(
        frozen_decoder_source,
        (
            "def classify_observation(",
            "result = model.classify_observation(",
            "for row in result.get(\"records\", ()):",
        ),
        "frozen decoder Carrier delegation",
    )

    if wrapper.count('#include "s22plus_r4w1e_e1_runtime.c"') != 1:
        raise AuditError("candidate E1 macro include differs")
    _exact_span(
        inputs["p288_legacy_runtime"],
        b"#define E1_REQUIRE(stage, item_index, operation)",
        b"} while (0)",
        785,
        "baec1f41f6fcb929bd65dcd3bed3d27726027aca1458b873241f1951ded8bc4d",
        "candidate E1 load/checkpoint macro",
    )
    if legacy_runtime.count("#define E1_REQUIRE(stage, item_index, operation)") != 1:
        raise AuditError("candidate E1 macro authority differs")
    _ordered(
        legacy_runtime,
        (
            "#define E1_REQUIRE(stage, item_index, operation)",
            "long e1_operation_result = (operation);",
            "if (e1_operation_result != 0)",
            "fail_at((stage), (item_index), e1_operation_result);",
            "long e1_checkpoint_result =",
            "s22_r4w1e_checkpoint_progress(",
            "&g_checkpoint, (stage), (item_index));",
            "if (e1_checkpoint_result != 0)",
            "quiet_park();",
            "} while (0)",
        ),
        "candidate E1 load/checkpoint macro",
    )

    plan = _module_plan(plan_source)
    if (
        len(plan) != 70
        or plan[0][:2]
        != ("s22plus_dwc3_event_latch.ko", "s22plus_dwc3_event_latch")
        or plan[37][:2] != ("qmi_helpers.ko", "qmi_helpers")
        or plan[38][:2] != ("eud.ko", "eud")
        or sum(row[1] == "eud" for row in plan) != 1
    ):
        raise AuditError("candidate EUD module-plan index differs")

    if runtime.count("#define P307_EUD_MODULE_INDEX 37U") != 1:
        raise AuditError("candidate EUD cache index constant differs")
    if runtime.count('#define P307_EUD_CACHE_PATH "/sys/module/eud/parameters/enable"') != 1:
        raise AuditError("candidate EUD cache path differs")
    if runtime.count("#define P307_DETAIL_EUD_CACHE_READ_FAILED 0x6010U") != 1:
        raise AuditError("candidate EUD cache failure detail differs")
    if sum(payload.count(b"0x6010") for payload in inputs.values()) != 1:
        raise AuditError("candidate 0x6010 producer literal is not unique")
    eud_cache_reader = _exact_c_function(
        inputs["p290_e3_runtime_include"],
        "p307_read_eud_cache",
        784,
        "d5a28e55bf55821e9816b72ddea9c5ab9224de7478f9c1d811cc3c0266389d4f",
    )
    _ordered(
        runtime,
        (
            "static long p307_read_eud_cache(void)",
            "g_p307_attr.cache_attempted = 1U;",
            "sys_openat(P307_EUD_CACHE_PATH, O_RDONLY | O_CLOEXEC, 0)",
            "if (fd < 0) return P307_DETAIL_EUD_CACHE_READ_FAILED;",
            "long amount = sys_read((int)fd, value, sizeof(value));",
            "long close_rc = sys_close((int)fd);",
            "return P307_DETAIL_EUD_CACHE_READ_FAILED;",
        ),
        "candidate EUD cache reader",
    )
    _ordered(
        wrapper,
        (
            "static long p241_load_and_verify_module(size_t index)",
            "s22plus_o2_module_plan[index].filename",
            "sys_openat(path, O_RDONLY | O_CLOEXEC, 0)",
            "p241_finit_module(",
            "s22plus_o2_module_plan[index].params",
            "long close_rc = sys_close((int)fd);",
            "if (finit_rc != 0)",
            "if (close_rc != 0)",
            "return p241_verify_module_prefix(index + 1U);",
        ),
        "candidate exact module loader",
    )
    path_builder = _exact_c_function(
        inputs["runtime_wrapper"],
        "p241_build_module_path",
        600,
        "71816382c1e4b319111e867458eb19340fbd945c540901489a21fb3c5d4af0ea",
    )
    finit_module = _exact_c_function(
        inputs["runtime_wrapper"],
        "p241_finit_module",
        137,
        "8cf2c7bfa96bd146038f6cf4f0539355be34ec09d102de414f895263dfc24244",
    )
    loader = _exact_c_function(
        inputs["runtime_wrapper"],
        "p241_load_and_verify_module",
        627,
        "cff3faef659e0cecca7699d40ce0a7149e6e9cf3dafda1a53b5390d9331f712e",
    )
    verifier = _exact_c_function(
        inputs["runtime_wrapper"],
        "p241_verify_module_prefix",
        1184,
        "0b4f45b2819672e3ce81b63a948e03cede8dc119f457c3abba73d7913ff722f6",
    )
    syscall6 = _exact_c_function(
        inputs["p288_legacy_runtime"],
        "syscall6",
        516,
        "ee2c16c81a4dd26227fffed33daa7964af4a7312fdf8034889138b6f103e8ee6",
    )
    if (
        _return_expressions(path_builder) != (b"-EINVAL", b"0")
        or _return_expressions(finit_module)
        != (
            b"syscall6( NR_FINIT_MODULE, fd, (long)(uintptr_t)params, "
            b"0, 0, 0, 0)",
        )
        or _return_expressions(loader)
        != (
            b"path_rc",
            b"fd",
            b"finit_rc",
            b"close_rc",
            b"p241_verify_module_prefix(index + 1U)",
        )
        or _return_expressions(verifier)
        != (
            b"fd",
            b"scan_rc == S22PLUS_O2_ERR_READ ? -EIO : -ENODEV",
            b"close_rc",
            b"-ENODEV",
            b"-ENODEV",
            b"0",
        )
        or _return_expressions(syscall6) != (b"x0",)
        or syscall6.count(b'"svc #0"') != 1
    ):
        raise AuditError("candidate module-loader result domain differs")
    if (
        wrapper.count("#define S22_P241_MODULE_STAGE_BASE 0x40U") != 1
        or wrapper.count("#define S22_P241_GATE_STAGE_BASE 0x7cU") != 1
        or wrapper.count(
            "P305_FOLDED_MODULE_INDEX = P305_MODULE_STAGE_CAPACITY - 1U"
        )
        != 1
    ):
        raise AuditError("candidate first module-loop extent differs")
    _ordered(
        wrapper,
        (
            "for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index)",
            "p241_load_and_verify_module(index)",
            "if (index == P307_EUD_MODULE_INDEX)",
            "long p307_eud_cache_rc = p307_read_eud_cache();",
            "if (p307_eud_cache_rc != 0) p290_fail_next(p307_eud_cache_rc);",
        ),
        "candidate module-load/cache-read order",
    )
    _exact_c_block(
        inputs["runtime_wrapper"],
        b"for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index)",
        418,
        "20cfc76fac0c9c7aa8f3e4a0e1ec747d9f425eadc7050c5dedcf96e430ef3504",
        "candidate first module loop",
    )
    diagnostic_entry_body = (
        "static __attribute__((noreturn)) void p290_e3_run(void) {\n"
        "    p318_run();\n"
        "}"
    )
    if (
        wrapper.count("p290_e3_run();") != 1
        or wrapper.count("p318_run();") != 0
        or runtime.count("p318_run();") != 1
        or runtime.count(diagnostic_entry_body) != 1
    ):
        raise AuditError("candidate Max77705 diagnostic entry differs")
    _ordered(
        wrapper,
        (
            "for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index)",
            "p241_load_and_verify_module(index)",
            "if (index == P307_EUD_MODULE_INDEX)",
            "if (p307_eud_cache_rc != 0) p290_fail_next(p307_eud_cache_rc);",
            "p290_e3_run();",
        ),
        "candidate cache failure before Max77705 diagnostic entry",
    )
    _ordered(
        runtime,
        (
            "static __attribute__((noreturn)) void p290_fail_next(long detail)",
            "s22_p290_checkpoint_failure_next(",
            "&g_checkpoint, detail",
            "if (primary_rc == 0)",
            "p290_park_after_confirmed_publication();",
            "p292_park_after_checkpoint_error(primary_rc);",
        ),
        "candidate nonreturning failure publisher",
    )
    _exact_c_function(
        inputs["p290_e3_runtime_include"],
        "p290_fail_next",
        251,
        "d8e7fa144b08851f857dd656db8cab7a0dcb48d9fbe904a6b259d9015e448892",
    )
    _exact_c_function(
        inputs["p290_e3_runtime_include"],
        "p290_e3_run",
        37,
        "18535c89b719ce310a1faca975dd992ae3d9ca92d1ef5b88727c7414376ea027",
    )
    fail_at = _exact_c_function(
        inputs["runtime_wrapper"],
        "fail_at",
        490,
        "f48b353a661981f728dac1ec838be00910154cced04290583442b58082c92a8f",
    )
    if (
        inputs["runtime_wrapper"].count(
            b"__attribute__((noreturn)) static void fail_at("
        )
        != 2
        or b"s22_r4w1e_checkpoint_failure(" not in fail_at
        or b"p290_park_after_confirmed_publication();" not in fail_at
        or b"p292_park_after_checkpoint_error(primary_rc);" not in fail_at
    ):
        raise AuditError("candidate module failure publisher differs")

    steps = _checkpoint_steps(checkpoint)
    if (
        steps[45] != (0x65, 37, "S22_P248_STEP_NORMAL")
        or steps[46] != (0x66, 38, "S22_P248_STEP_NORMAL")
    ):
        raise AuditError("candidate generation 46/47 position pair differs")
    _ordered(
        checkpoint,
        (
            "long s22_p290_checkpoint_failure_next(",
            "p288_normalize_failure_detail(operation_error, &detail)",
            "p288_publish_next(",
            "client, S22_P233_OUTCOME_FAILURE, detail, 0, 0U",
        ),
        "candidate failure-next publisher",
    )
    if (
        checkpoint_header.count(
            "#define S22_P292_PUBLICATION_ERRNO_MAX 0xfffL"
        )
        != 1
        or checkpoint_header.count(
            "#define S22_P292_PUBLICATION_CLOSE_BASE 0x6000U"
        )
        != 1
    ):
        raise AuditError("candidate checkpoint detail-domain authority differs")
    _ordered(
        checkpoint,
        (
            "static int p288_detail_allowed(",
            "detail > S22_P292_PUBLICATION_CLOSE_BASE",
            "detail <= S22_P292_PUBLICATION_CLOSE_BASE +",
            "S22_P292_PUBLICATION_ERRNO_MAX",
            "return 1;",
        ),
        "candidate checkpoint detail-domain acceptance",
    )
    return {
        "module_plan_count": len(plan),
        "latch_index": 0,
        "runtime_eud_cache_index": 37,
        "first_module_loop_last_index": 58,
        "runtime_index_37_module": plan[37][1],
        "explicit_eud_module_index": 38,
        "progress_generation": 46,
        "progress_position": {"stage": 0x65, "item_index": 37},
        "failure_generation": 47,
        "failure_position": {"stage": 0x66, "item_index": 38},
        "failure_detail": "0x6010",
        "failure_detail_publication_collision_range": "0x6001..0x6fff",
        "failure_detail_was_publishable": True,
        "failure_detail_literal_unique_in_materialized_execution_sources": True,
        "cache_path": "/sys/module/eud/parameters/enable",
        "cache_read_precedes_explicit_eud_load": True,
        "cache_failure_publisher_is_noreturn": True,
        "module_load_precedes_progress_checkpoint": True,
        "progress_checkpoint_precedes_cache_read": True,
        "max77705_entry_follows_cache_failure_site": True,
        "publication_close_alias_exclusion": publication_alias,
        "frozen_decoder_semantic_authority": "P3.10-carrier/P3.08-slot-semantics",
    }


def _record_result(
    payload: bytes,
    run_id: bytes,
    frozen_carrier: Any,
    recovered_carrier: Any,
    recovered_decoder: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    frozen_result = frozen_carrier.classify_observation(
        payload, expected_profile="E2", expected_run_id=run_id
    )
    recovered = recovered_decoder.classify_observation(
        payload, expected_profile="E2", expected_run_id=run_id
    )
    if (
        frozen_result.get("classification") != "E2_PROGRESS_OBSERVED"
        or frozen_result.get("integrity_issue") is not False
        or len(frozen_result.get("records", ())) != 1
        or frozen_result["records"][0].get("observer_offset") != RECORD_OFFSET
        or frozen_result["records"][0].get("slot_status") != ["valid", "bad-body"]
        or frozen_result["records"][0].get("fallback_used") is not True
        or frozen_result["records"][0].get("active", {}).get("generation") != 46
    ):
        raise AuditError("frozen P3.18 decoder incident signature differs")
    row = recovered["records"][0]
    active = row["active"]
    if (
        recovered.get("classification") != recovered_decoder.CLASSIFICATION
        or recovered.get("integrity_issue") is not False
        or recovered.get("foreign_count") != 0
        or recovered.get("precondition_failure_count") != 1
        or recovered.get("causal_result_allowed") is not False
        or row.get("observer_offset") != RECORD_OFFSET
        or row.get("slot_status") != ["valid", "valid"]
        or row.get("fallback_used") is not False
        or active.get("generation") != recovered_carrier.FAILURE_GENERATION
        or active.get("stage") != recovered_carrier.FAILURE_STAGE
        or active.get("outcome") != recovered_carrier.OUTCOME_FAILURE
        or active.get("item_index") != recovered_carrier.FAILURE_ITEM_INDEX
        or active.get("detail") != recovered_carrier.FAILURE_DETAIL
        or active.get("payload_kind") != recovered_carrier.PAYLOAD_NONE
        or active.get("payload")
        not in (b"", "", {"encoding": "hex", "value": ""})
    ):
        raise AuditError("recovered P3.18 EUD failure differs")
    return frozen_result, recovered


def build_receipt() -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise AuditError("post-live auditor requires bound-source execution")
    if (
        current_regular_bytes(POSTLIVE_AUDITOR, "bound post-live auditor")
        != _BOUND_AUDITOR_SOURCE
    ):
        raise AuditError("executed post-live auditor bytes differ from receipt bytes")
    intent_payload = stable_bytes(INTENT, INTENT_SIZE, INTENT_SHA256, "P3.18 intent")
    intent = load_intent(intent_payload)
    if (
        intent.get("contract_id")
        != "s22plus-fyg8-p318-topology-timing-max77705-envelope-v4"
        or intent.get("profile") != "E2"
        or not isinstance(intent.get("run_id"), str)
        or re.fullmatch(r"[0-9a-f]{32}", intent["run_id"]) is None
    ):
        raise AuditError("P3.18 intent identity differs")
    run_id = bytes.fromhex(intent["run_id"])
    inputs = _materialized_inputs(intent)
    semantic_inputs = _semantic_inputs(intent)
    source_chain = audit_source_chain(inputs, semantic_inputs)
    implementation = {
        "carrier_model": current_regular_bytes(
            POSTLIVE_MODEL, "post-live carrier model"
        ),
        "decoder": current_regular_bytes(POSTLIVE_DECODER, "post-live decoder"),
        "auditor": _BOUND_AUDITOR_SOURCE,
    }
    frozen_carrier, recovered_carrier, recovered_decoder = _load_bound_decoders(
        semantic_inputs, implementation
    )

    retained = tuple(
        stable_bytes(path, RETAINED_SIZE, RETAINED_SHA256, f"retained read {index}")
        for index, path in enumerate(RETAINED, 1)
    )
    if retained[0] != retained[1]:
        raise AuditError("retained P3.18 reads differ")
    frozen_result, recovered = _record_result(
        retained[0],
        run_id,
        frozen_carrier,
        recovered_carrier,
        recovered_decoder,
    )
    active = recovered["records"][0]["active"]

    receipt = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": {
            "model": "SM-S906N",
            "device": "g0q",
            "firmware": "S906NKSS7FYG8",
        },
        "inputs": {
            "intent": identity(intent_payload),
            "materialized_sources": {
                key: identity(payload) for key, payload in sorted(inputs.items())
            },
            "frozen_semantic_sources": {
                key: identity(payload)
                for key, payload in sorted(semantic_inputs.items())
            },
            "postlive_implementation": {
                key: identity(payload)
                for key, payload in sorted(implementation.items())
            },
            "retained_read_count": 2,
            "retained_read_identity": {
                "size": RETAINED_SIZE,
                "sha256": RETAINED_SHA256,
            },
            "retained_reads_byte_identical": True,
        },
        "frozen_decoder_incident": {
            "classification": frozen_result["classification"],
            "slot_status": ["valid", "bad-body"],
            "fallback_used": True,
            "fallback_generation": 46,
            "record_offset": RECORD_OFFSET,
        },
        "source_chain": source_chain,
        "recovered_record": {
            "slot_status": ["valid", "valid"],
            "fallback_used": False,
            "record_offset": RECORD_OFFSET,
            "generation": active["generation"],
            "stage": active["stage"],
            "outcome": active["outcome"],
            "item_index": active["item_index"],
            "detail": f"0x{active['detail']:04x}",
            "payload_kind": active["payload_kind"],
            "payload_length": 0,
            "header_crc_valid": True,
            "both_slot_crcs_valid": True,
        },
        "conclusion": {
            "effective_campaign_proof": recovered_decoder.CLASSIFICATION,
            "candidate_precondition_failure": "eud-cache-read-before-explicit-eud-load",
            "eud_cache_failure_uniquely_proved": True,
            "checkpoint_close_alias_can_replace_retained_slot": False,
            "max77705_diagnostic_reached": False,
            "max77705_result_count": 0,
            "causal_result_allowed": False,
            "closed_health_and_transfers_unchanged": True,
            "historical_live_result_rewritten": False,
        },
        "scope": {
            "host_only": True,
            "device_contact": False,
            "device_actions": False,
            "adb_commands": 0,
            "usb_actions": 0,
            "odin_invocations": 0,
            "candidate_transfers": 0,
            "rollback_transfers": 0,
            "replay": False,
            "live_authority_created": False,
        },
    }
    if (
        current_regular_bytes(POSTLIVE_AUDITOR, "post-run bound post-live auditor")
        != _BOUND_AUDITOR_SOURCE
    ):
        raise AuditError("post-live auditor bytes changed during execution")
    return receipt


def encode_receipt(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _write_all(fd: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        try:
            amount = os.write(fd, payload[offset:])
        except InterruptedError:
            continue
        if amount <= 0:
            raise AuditError("post-live receipt write did not progress")
        offset += amount


def write_receipt(value: dict[str, Any]) -> None:
    payload = encode_receipt(value)
    OUTPUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if OUTPUT.exists() or OUTPUT.is_symlink():
        existing = stable_bytes(
            OUTPUT,
            len(payload),
            sha256(payload),
            "post-live recovery receipt",
            required_mode=0o400,
        )
        if existing != payload:
            raise AuditError("post-live recovery receipt mode differs")
        return
    fd = os.open(OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o400)
    try:
        os.fchmod(fd, 0o400)
        _write_all(fd, payload)
        os.fsync(fd)
        state = os.fstat(fd)
        if (
            not stat.S_ISREG(state.st_mode)
            or stat.S_IMODE(state.st_mode) != 0o400
            or state.st_nlink != 1
            or state.st_size != len(payload)
        ):
            raise AuditError("post-live recovery receipt publication differs")
    finally:
        os.close(fd)
    directory_fd = os.open(OUTPUT.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    stable_bytes(
        OUTPUT,
        len(payload),
        sha256(payload),
        "post-live recovery receipt",
        required_mode=0o400,
    )


def main() -> int:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        return load_bound_auditor().main()
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit-only", action="store_true")
    group.add_argument("--write", action="store_true")
    args = parser.parse_args()
    value = build_receipt()
    if args.write:
        write_receipt(value)
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
