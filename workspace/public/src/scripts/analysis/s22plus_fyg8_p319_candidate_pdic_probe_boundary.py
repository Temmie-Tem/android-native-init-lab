#!/usr/bin/env python3
"""Audit the FYG8 candidate PDIC load, probe, init-detect, and unmask boundary.

This is a host-only P3.19 analysis.  It binds the surviving S7A2 candidate AP,
the historical loader source used to build it, the exact shipped PDIC module
and source, five historical live reports, and the complete manifest-defined
retained stock corpus.  It does not contact a device and grants no D0/D1/F1,
recovery, replay, or live authority.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import os
import re
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
AUDITOR = Path(__file__).resolve()
PRIVATE = ROOT / "workspace/private"
IRQ_AUDIT_INPUTS = PRIVATE / (
    "outputs/s22plus_fyg8_p319/max77705-irq-dt-audit-20260820-05/inputs"
)
OUTPUT_V4_ROOT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/candidate-pdic-probe-boundary-20260820-04"
)
OUTPUT_V4 = OUTPUT_V4_ROOT / "result.json"
OUTPUT_ROOT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/candidate-pdic-probe-boundary-20260820-05"
)
OUTPUT = OUTPUT_ROOT / "result.json"
INPUT_ROOT = OUTPUT_V4_ROOT / "inputs"
HISTORICAL_SOURCE = INPUT_ROOT / "s22plus_init_m34_runtime_gadget_split.c"

SCHEMA = "s22plus-fyg8-p319-candidate-pdic-probe-boundary-v3"
VERDICT = "PASS_P319_CANDIDATE_PDIC_PROBE_BOUNDARY_V3_H0"
HISTORICAL_COMMIT = "4df34885de6425b72789830d0d42d9d17f3ca1e2"
HISTORICAL_SOURCE_PATH = (
    "workspace/public/src/native-init/s22plus_init_m34_runtime_gadget_split.c"
)
S7A2_AP = PRIVATE / (
    "outputs/s22plus_native_init/m34_runtime_gadget_split_v0_7/"
    "S7A2/odin4/AP.tar.md5"
)
S7A2_GATE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_m34_s7a2_geni_i2c_live_gate.py"
)
CORPUS_MANIFEST = PRIVATE / "outputs/s22plus_fyg8_p319/abl-capture-manifest.json"
PDIC_MODULE = IRQ_AUDIT_INPUTS / "pdic_max77705.ko"
MUIC_SOURCE = IRQ_AUDIT_INPUTS / "max77705-muic.c"
USBC_SOURCE = IRQ_AUDIT_INPUTS / "max77705_usbc.c"
MAGISKBOOT = PRIVATE / "tools/magisk-v30.7/magiskboot"
LZ4 = Path("/usr/bin/lz4")


class AuditError(RuntimeError):
    """An exact input or a claimed semantic boundary differs."""


_BOUND_AUDITOR_SOURCE = globals().get("_P319_PDIC_PROBE_BOUND_SOURCE")


@dataclass(frozen=True)
class InputSpec:
    size: int
    sha256: str
    path: Path
    maximum: int
    mode: int | None = None
    nlink: int | None = 1


REPORTS = {
    "s7a2": ROOT
    / "docs/reports/S22PLUS_NATIVE_INIT_M34_S7A2_GENI_I2C_LIVE_RESULT_2026-07-09.md",
    "m7": ROOT
    / "docs/reports/S22PLUS_NATIVE_INIT_M7_USB_SUBSET_LIVE_RESULT_2026-07-07.md",
    "m11": ROOT
    / "docs/reports/S22PLUS_NATIVE_INIT_M11_PARK_USB_LIVE_RESULT_2026-07-07.md",
    "m12": ROOT
    / "docs/reports/S22PLUS_NATIVE_INIT_M12_M5_FLOOR_LIVE_RESULT_2026-07-07.md",
    "m18": ROOT / "docs/reports/S22PLUS_M18_CAPTURE_POSTMORTEM_2026-07-08.md",
}

INPUTS: dict[str, InputSpec] = {
    "s7a2_ap": InputSpec(
        100_669_481,
        "cb89ccf9c8c5481938ddd415930c78a23e1a679d45fdc57f95e6d1b48776bd59",
        S7A2_AP,
        101 * 1024 * 1024,
        0o600,
    ),
    "s7a2_gate": InputSpec(
        58_446,
        "9d3f37d40784a7b406435c04010b311342b2b17b11a03a07483c3ab8e7b69628",
        S7A2_GATE,
        128 * 1024,
    ),
    "pdic_module": InputSpec(
        423_456,
        "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db",
        PDIC_MODULE,
        512 * 1024,
        0o400,
    ),
    "muic_source": InputSpec(
        76_141,
        "bfdb034d7571ca233202221cdc8cdfe68bab3e837afea9c4b5a37378ed7acbab",
        MUIC_SOURCE,
        128 * 1024,
        0o400,
    ),
    "usbc_source": InputSpec(
        124_569,
        "4dabc4b25e99e26c662748934a6a98775073683832f08652e15762f4689a3e3d",
        USBC_SOURCE,
        192 * 1024,
        0o400,
    ),
    "magiskboot": InputSpec(
        943_848,
        "a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e",
        MAGISKBOOT,
        1024 * 1024,
        0o700,
    ),
    "lz4": InputSpec(
        115_032,
        "4be960d6f6b0d7ef69e01a9e1a056591c17b8687e9851db128018b2ac5f01da0",
        LZ4,
        256 * 1024,
        0o755,
    ),
    "report_s7a2": InputSpec(
        4_930,
        "98a3cef48e77d0a2f7a845fa082b15cde05a43362dbd4b80a28fb162f02f7bfd",
        REPORTS["s7a2"],
        16 * 1024,
    ),
    "report_m7": InputSpec(
        5_164,
        "3354be61df763d37e8d867da7d5bf4726b930114494f6e839d6db43fc9d04026",
        REPORTS["m7"],
        16 * 1024,
    ),
    "report_m11": InputSpec(
        5_441,
        "f4f46697daedef62b7e3ca3b1778ad0b453d0f7cc3c8fb4a5d32ec761d1854e3",
        REPORTS["m11"],
        16 * 1024,
    ),
    "report_m12": InputSpec(
        5_386,
        "cdca0187e4ff4d8d8304599469eb4b80971a8e14e348f3a58a8b54b7dfd5afb4",
        REPORTS["m12"],
        16 * 1024,
    ),
    "report_m18": InputSpec(
        6_069,
        "31bf76115c1f0205aded40c66762102b8e4dbb30fa67f9758e56c106e16772ec",
        REPORTS["m18"],
        16 * 1024,
    ),
}

CORPUS_SEMANTIC_IDENTITY = {
    "size": 47_799,
    "sha256": "c1c75743fcdb06a3b3180e6a1d091a620969922ac2209d9169d21922a6d7b6a3",
}

HISTORICAL_SOURCE_IDENTITY = {
    "size": 28_694,
    "sha256": "ce12ea11a6c0f73f5f042801435b419637b473eff6631155f45d4ad382d8a80a",
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


def load_bound_auditor() -> Any:
    payload = stable_bytes(AUDITOR, label="P3.19 probe auditor bootstrap", maximum=1 << 20)
    module = types.ModuleType("s22plus_fyg8_p319_candidate_pdic_probe_boundary_bound")
    module.__file__ = str(AUDITOR)
    module.__package__ = ""
    module.__dict__["_P319_PDIC_PROBE_BOUND_SOURCE"] = payload
    sys.modules[module.__name__] = module
    try:
        code = compile(payload.decode("utf-8"), str(AUDITOR), "exec", dont_inherit=True)
        exec(code, module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P3.19 probe bound-source execution failed") from exc
    return module


def _write_all(fd: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        try:
            count = os.write(fd, payload[offset:])
        except InterruptedError:
            continue
        if count <= 0:
            raise AuditError("P3.19 probe publication did not progress")
        offset += count


def publish_exclusive(path: Path, payload: bytes, mode: int = 0o400) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    if path.exists() or path.is_symlink():
        existing = stable_bytes(
            path,
            label=f"existing {path.name}",
            maximum=max(len(payload), 1),
            expected_size=len(payload),
            expected_sha256=sha256(payload),
            required_mode=mode,
            required_nlink=1,
        )
        if existing != payload:
            raise AuditError(f"existing {path.name} differs")
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, mode)
    try:
        os.fchmod(fd, mode)
        _write_all(fd, payload)
        os.fsync(fd)
        state = os.fstat(fd)
        if (
            not stat.S_ISREG(state.st_mode)
            or stat.S_IMODE(state.st_mode) != mode
            or state.st_nlink != 1
            or state.st_size != len(payload)
        ):
            raise AuditError(f"{path.name} publication metadata differs")
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    stable_bytes(
        path,
        label=f"published {path.name}",
        maximum=max(len(payload), 1),
        expected_size=len(payload),
        expected_sha256=sha256(payload),
        required_mode=mode,
        required_nlink=1,
    )


def historical_source(materialize: bool) -> bytes:
    if HISTORICAL_SOURCE.exists() or HISTORICAL_SOURCE.is_symlink():
        return stable_bytes(
            HISTORICAL_SOURCE,
            label="S7A2 historical loader source",
            maximum=64 * 1024,
            expected_size=HISTORICAL_SOURCE_IDENTITY["size"],
            expected_sha256=HISTORICAL_SOURCE_IDENTITY["sha256"],
            required_mode=0o400,
            required_nlink=1,
        )
    if not materialize:
        raise AuditError("S7A2 historical loader source snapshot is absent")
    completed = subprocess.run(
        ["git", "show", f"{HISTORICAL_COMMIT}:{HISTORICAL_SOURCE_PATH}"],
        cwd=ROOT,
        env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0 or completed.stderr:
        raise AuditError("S7A2 historical source extraction failed")
    if identity(completed.stdout) != HISTORICAL_SOURCE_IDENTITY:
        raise AuditError("S7A2 historical source identity differs")
    publish_exclusive(HISTORICAL_SOURCE, completed.stdout)
    return stable_bytes(
        HISTORICAL_SOURCE,
        label="S7A2 historical loader source",
        maximum=64 * 1024,
        expected_size=HISTORICAL_SOURCE_IDENTITY["size"],
        expected_sha256=HISTORICAL_SOURCE_IDENTITY["sha256"],
        required_mode=0o400,
        required_nlink=1,
    )


def load_inputs(materialize: bool) -> dict[str, bytes]:
    result = {
        name: stable_bytes(
            spec.path,
            label=name,
            maximum=spec.maximum,
            expected_size=spec.size,
            expected_sha256=spec.sha256,
            required_mode=spec.mode,
            required_nlink=spec.nlink,
        )
        for name, spec in INPUTS.items()
    }
    result["historical_loader_source"] = historical_source(materialize)
    return result


def load_corpus_manifest() -> bytes:
    return stable_bytes(
        CORPUS_MANIFEST,
        label="P3.19 regenerable corpus manifest",
        maximum=256 * 1024,
        required_nlink=1,
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise AuditError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json(payload: bytes, label: str) -> Any:
    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                AuditError(f"{label} contains non-finite {token}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc


CAPTURE_KEYS = {
    "bc_ctrl1_reads",
    "boot_segments",
    "candidate_markers",
    "download_mode",
    "has_abl_stage",
    "has_max7770x_irq_thread",
    "mission_mode",
    "muic_notifier_tags",
    "muic_opcodes",
    "paths",
    "setpath_occurrences",
    "setpath_values",
    "sha256",
    "stock_daemons",
}


def parse_corpus_manifest(payload: bytes) -> dict[str, Any]:
    value = strict_json(payload, "P3.19 capture manifest")
    required = {
        "bc_ctrl1_value_counts",
        "bc_ctrl1_value_counts_download",
        "bc_ctrl1_value_counts_normal",
        "schema",
        "inclusion_criterion",
        "matching_files",
        "unreadable_or_short_files",
        "distinct_captures",
        "duplicate_files_collapsed",
        "kernel_side",
        "counts",
        "muic_opcode_counts",
        "setpath_values_observed",
        "captures",
    }
    if type(value) is not dict or set(value) != required:
        raise AuditError("capture manifest key set differs")
    if value["schema"] != "s22plus-fyg8-p319-abl-capture-manifest-v3":
        raise AuditError("capture manifest schema differs")
    if value["inclusion_criterion"] != {
        "root": "workspace/private",
        "exact_size_bytes": 2_097_136,
        "selected_by_name_or_run": False,
    }:
        raise AuditError("capture inclusion criterion differs")
    for key in (
        "matching_files",
        "unreadable_or_short_files",
        "distinct_captures",
        "duplicate_files_collapsed",
    ):
        if type(value[key]) is not int or value[key] < 0:
            raise AuditError("capture manifest scalar differs")
    if (
        value["unreadable_or_short_files"] != 0
        or value["matching_files"] < value["distinct_captures"]
        or value["duplicate_files_collapsed"]
        != value["matching_files"] - value["distinct_captures"]
    ):
        raise AuditError("capture manifest population arithmetic differs")
    captures = value["captures"]
    if type(captures) is not list or len(captures) != value["distinct_captures"]:
        raise AuditError("capture manifest population differs")
    seen: set[str] = set()
    for index, capture in enumerate(captures):
        if type(capture) is not dict or set(capture) != CAPTURE_KEYS:
            raise AuditError(f"capture manifest entry differs: {index}")
        digest = capture["sha256"]
        paths = capture["paths"]
        if (
            type(digest) is not str
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or digest in seen
            or type(paths) is not list
            or not paths
            or any(type(path) is not str or not path for path in paths)
        ):
            raise AuditError(f"capture manifest identity differs: {index}")
        seen.add(digest)
    return value


def corpus_semantic_projection(manifest: dict[str, Any]) -> bytes:
    top_level = set(manifest) - {
        "matching_files",
        "duplicate_files_collapsed",
        "captures",
    }
    projection = {key: manifest[key] for key in sorted(top_level)}
    projection["captures"] = [
        {
            key: capture[key]
            for key in sorted(CAPTURE_KEYS - {"paths"})
        }
        for capture in sorted(manifest["captures"], key=lambda item: item["sha256"])
    ]
    return (
        json.dumps(
            projection,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def audit_corpus_manifest_semantics(manifest: dict[str, Any]) -> dict[str, Any]:
    semantic = corpus_semantic_projection(manifest)
    if identity(semantic) != CORPUS_SEMANTIC_IDENTITY:
        raise AuditError("P3.19 corpus semantic projection differs")
    return {
        "schema": manifest["schema"],
        "semantic_projection": identity(semantic),
        "distinct_captures": manifest["distinct_captures"],
        "counts": manifest["counts"],
        "kernel_side": manifest["kernel_side"],
        "muic_opcode_counts": manifest["muic_opcode_counts"],
        "setpath_values_observed": manifest["setpath_values_observed"],
        "regenerable_manifest_bytes_are_not_authority": True,
        "volatile_population_fields_excluded": [
            "matching_files",
            "duplicate_files_collapsed",
            "captures[].paths",
        ],
    }


def load_corpus(manifest: dict[str, Any]) -> dict[str, bytes]:
    expected = {capture["sha256"]: capture for capture in manifest["captures"]}
    corpus: dict[str, bytes] = {}
    observed_paths: dict[str, list[str]] = collections.defaultdict(list)
    matching = 0
    for path in sorted(PRIVATE.rglob("*")):
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size != 2_097_136:
                continue
        except OSError as exc:
            raise AuditError(f"capture population stat failed: {path}") from exc
        payload = stable_bytes(
            path,
            label="P3.19 current retained capture",
            maximum=3 * 1024 * 1024,
            expected_size=2_097_136,
        )
        digest = sha256(payload)
        matching += 1
        observed_paths[digest].append(str(path.relative_to(ROOT)))
        corpus.setdefault(digest, payload)
    if (
        matching != manifest["matching_files"]
        or set(corpus) != set(expected)
        or len(corpus) != manifest["distinct_captures"]
    ):
        raise AuditError("current capture population differs from manifest")
    for digest, capture in expected.items():
        if observed_paths[digest] != capture["paths"]:
            raise AuditError(f"capture path inventory differs: {digest}")
    return corpus


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


def _exact_functions(
    source: bytes, expected: dict[str, tuple[int, str]], label: str
) -> dict[str, dict[str, Any]]:
    result = {}
    for name, (size, digest) in expected.items():
        body = _c_function_body(source, name)
        if identity(body) != {"size": size, "sha256": digest}:
            raise AuditError(f"{label} critical function differs: {name}")
        result[name] = identity(body)
    return result


def _ordered_once(body: bytes, tokens: tuple[bytes, ...], label: str) -> None:
    cursor = -1
    for token in tokens:
        if body.count(token) != 1:
            raise AuditError(f"{label} token multiplicity differs: {token!r}")
        position = body.index(token)
        if position <= cursor:
            raise AuditError(f"{label} token order differs: {token!r}")
        cursor = position


def audit_candidate_loader(source: bytes) -> dict[str, Any]:
    functions = _exact_functions(
        source,
        {
            "emit_buf": (221, "ec6c81e896830da4c3b7e02a9d2fae1f1e2ecd05ecef7e10fcc3643b38016a59"),
            "load_one_module": (348, "a6318db4b2d3d9cade463cc08665b27a1c32b2b2dbf7e3860d1dfa348361d52f"),
            "emit_module_result": (284, "4883cf53a66d4d6addffc4670af70dd8adfcf0ba51a855babc655bb85026b996"),
            "load_modules_from_list": (1_335, "be4e22aaf6b7ff7b5ad8b110632d516a9cc9a122a9cc652f200ea012584f9221"),
            "_start": (936, "1f9305c85da9d806710eadd8e748a0ad9cafefacb8e4ebdfdd4175c7c56fe9c3"),
        },
        "S7A2 loader",
    )
    one = _c_function_body(source, "load_one_module")
    loop = _c_function_body(source, "load_modules_from_list")
    emit = _c_function_body(source, "emit_buf")
    _ordered_once(
        one,
        (
            b"sys_openat(AT_FDCWD, path, O_RDONLY | O_CLOEXEC, 0)",
            b'sys_finit_module((int)fd, "", 0)',
            b"sys_close((int)fd)",
            b"return rc;",
        ),
        "S7A2 one-module loader",
    )
    _ordered_once(
        loop,
        (
            b"long rc = load_one_module(name);",
            b"emit_module_result(name, rc);",
            b"++loaded;",
            b'" phase=modules_load_done loaded="',
        ),
        "S7A2 module loop",
    )
    if b"if (rc" in loop or b"return rc" in loop:
        raise AuditError("S7A2 module loop unexpectedly stops on module failure")
    if b'"/dev/kmsg"' not in emit or b"sys_fsync" in emit:
        raise AuditError("S7A2 module evidence sink differs")
    return {
        "historical_commit": HISTORICAL_COMMIT,
        "functions": functions,
        "finit_module_rc_emitted_for_each_attempt": True,
        "failure_does_not_stop_later_attempts": True,
        "attempt_counter_is_not_success_counter": True,
        "module_evidence_sink": "/dev/kmsg only",
        "durable_candidate_module_receipt": False,
    }


@dataclass(frozen=True)
class Section:
    name: str
    kind: int
    address: int
    offset: int
    size: int
    link: int
    info: int
    entry_size: int


@dataclass(frozen=True)
class Symbol:
    name: str
    section_index: int
    value: int
    size: int


@dataclass(frozen=True)
class Relocation:
    target_section: str
    offset: int
    kind: int
    symbol: str
    addend: int


class Elf64:
    def __init__(self, data: bytes, label: str):
        self.data = data
        self.label = label
        if len(data) < 64 or data[:20] != b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8 + b"\x01\x00\xb7\x00":
            raise AuditError(f"{label} is not an AArch64 relocatable object")
        header = struct.unpack_from("<16sHHIQQQIHHHHHH", data, 0)
        section_offset, section_size, section_count, string_index = (
            header[6],
            header[11],
            header[12],
            header[13],
        )
        if section_size != 64 or not section_count or string_index >= section_count:
            raise AuditError(f"{label} ELF section header differs")
        raw = [
            struct.unpack_from("<IIQQQQIIQQ", data, section_offset + i * 64)
            for i in range(section_count)
        ]
        names_raw = raw[string_index]
        names = self._slice(names_raw[4], names_raw[5], "section names")
        self.sections = tuple(
            Section(
                self._cstring_bytes(names, item[0]),
                item[1], item[3], item[4], item[5], item[6], item[7], item[9],
            )
            for item in raw
        )
        self.symbols = self._symbols()
        self.relocations = self._relocations()

    def _slice(self, offset: int, size: int, what: str) -> bytes:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise AuditError(f"{self.label} {what} bounds differ")
        return self.data[offset : offset + size]

    @staticmethod
    def _cstring_bytes(data: bytes, offset: int) -> str:
        if offset < 0 or offset >= len(data):
            raise AuditError("ELF string offset differs")
        end = data.find(b"\0", offset)
        if end < 0:
            raise AuditError("ELF string is unterminated")
        return data[offset:end].decode("utf-8", "strict")

    def section(self, name: str) -> Section:
        matches = [item for item in self.sections if item.name == name]
        if len(matches) != 1:
            raise AuditError(f"{self.label} section cardinality differs: {name}")
        return matches[0]

    def section_bytes(self, name: str) -> bytes:
        item = self.section(name)
        return self._slice(item.offset, item.size, name)

    def _symbols(self) -> tuple[Symbol, ...]:
        table = self.section(".symtab")
        if table.entry_size != 24 or table.link >= len(self.sections):
            raise AuditError(f"{self.label} symbol table differs")
        strings = self.sections[table.link]
        string_data = self._slice(strings.offset, strings.size, "symbol strings")
        body = self._slice(table.offset, table.size, "symbol table")
        if len(body) % 24:
            raise AuditError(f"{self.label} symbol table is truncated")
        result = []
        for cursor in range(0, len(body), 24):
            name, _, _, section_index, value, size = struct.unpack_from(
                "<IBBHQQ", body, cursor
            )
            result.append(Symbol(self._cstring_bytes(string_data, name), section_index, value, size))
        return tuple(result)

    def symbol(self, name: str) -> Symbol:
        matches = [item for item in self.symbols if item.name == name]
        if len(matches) != 1:
            raise AuditError(f"{self.label} symbol cardinality differs: {name}")
        item = matches[0]
        if item.section_index == 0 or item.section_index >= len(self.sections):
            raise AuditError(f"{self.label} symbol is undefined: {name}")
        return item

    def symbol_bytes(self, name: str) -> bytes:
        item = self.symbol(name)
        section = self.sections[item.section_index]
        relative = item.value - section.address
        if relative < 0 or relative + item.size > section.size or item.size <= 0:
            raise AuditError(f"{self.label} symbol bounds differ: {name}")
        return self._slice(section.offset + relative, item.size, f"symbol {name}")

    def _relocations(self) -> tuple[Relocation, ...]:
        result = []
        for section in self.sections:
            if section.kind != 4:
                continue
            if section.entry_size != 24 or section.info >= len(self.sections):
                raise AuditError(f"{self.label} relocation section differs")
            body = self._slice(section.offset, section.size, "relocations")
            if len(body) % 24:
                raise AuditError(f"{self.label} relocations are truncated")
            target = self.sections[section.info].name
            for cursor in range(0, len(body), 24):
                offset, info, addend = struct.unpack_from("<QQq", body, cursor)
                symbol_index = info >> 32
                if symbol_index >= len(self.symbols):
                    raise AuditError(f"{self.label} relocation symbol differs")
                result.append(
                    Relocation(
                        target,
                        offset,
                        info & 0xFFFFFFFF,
                        self.symbols[symbol_index].name,
                        addend,
                    )
                )
        return tuple(result)

    def relocation(self, target: str, offset: int) -> Relocation:
        matches = [
            item
            for item in self.relocations
            if item.target_section == target and item.offset == offset
        ]
        if len(matches) != 1:
            raise AuditError(f"{self.label} relocation cardinality differs at {offset:#x}")
        return matches[0]

    def word(self, address: int) -> int:
        text = self.section(".text")
        relative = address - text.address
        if relative < 0 or relative + 4 > text.size or relative % 4:
            raise AuditError(f"{self.label} text address differs: {address:#x}")
        return struct.unpack_from("<I", self.data, text.offset + relative)[0]


def audit_pdic_binary(data: bytes) -> dict[str, Any]:
    elf = Elf64(data, "pdic_max77705.ko")
    expected_symbols = {
        "max77705_init_irq_handler": (
            0xC1F4,
            712,
            "9d5dddeb11820a194347f8a1a1667c333ae5068007d0661a8cd1ba9576c86e0d",
        ),
        "max77705_usbc_probe": (
            0xCF0C,
            2_676,
            "f13b266d1fc5225417003df568775ff0c1b2612128dfe93ebc083e53b91c26d6",
        ),
        "max77705_muic_probe": (
            0x16264,
            3_076,
            "06c944761850866f80ecf5f9d4732b84f0566a87bc53de3880c4dbd098ebc525",
        ),
        "max77705_muic_detect_dev": (
            0x177C4,
            4_024,
            "7677a9e3227ec22d17ded3ae6994f8095e18bd778fbabbac12bbc6d500add3b3",
        ),
    }
    symbols: dict[str, Any] = {}
    for name, (address, size, digest) in expected_symbols.items():
        item = elf.symbol(name)
        body = elf.symbol_bytes(name)
        if (item.value, item.size, sha256(body)) != (address, size, digest):
            raise AuditError(f"PDIC binary symbol identity differs: {name}")
        symbols[name] = {"address": address, **identity(body)}
    for offset, symbol, addend in (
        (0xD4E8, "max77705_init_irq_handler", 0),
        (0xD4F0, "max77705_muic_probe", 0),
        (0xD890, "max77705_read_reg", 0),
        (0xD8AC, "max77705_write_reg", 0),
    ):
        if elf.relocation(".text", offset) != Relocation(
            ".text", offset, 283, symbol, addend
        ):
            raise AuditError(f"PDIC binary relocation differs: {symbol}")
    for address, word, label in (
        (0xD4EC, 0xAA1303E0, "USBC IRQ-handler return value discarded"),
        (0xD4F4, 0xAA1303E0, "MUIC return value discarded before CC init"),
        (0xD878, 0x52800028, "cc_booting_complete value"),
        (0xD87C, 0x39054B28, "cc_booting_complete store"),
        (0xD894, 0x35000100, "unmask read failure branch"),
        (0xD8A4, 0x121C7902, "parent mask bit three clear"),
        (0xD978, 0x2A1F03E0, "platform probe zero return"),
    ):
        if elf.word(address) != word:
            raise AuditError(f"{label} differs")
    return {
        "symbols": symbols,
        "usbc_irq_handler_return_value_discarded": True,
        "muic_probe_return_value_discarded": True,
        "cc_booting_complete_published_after_muic_probe_call": True,
        "parent_mask_read_failure_skips_bit_clear": True,
        "parent_mask_write_return_value_discarded": True,
        "platform_probe_still_returns_zero_after_unmask_read_failure": True,
    }


def audit_probe_sources(muic: bytes, usbc: bytes) -> dict[str, Any]:
    functions = {}
    functions.update(
        _exact_functions(
            muic,
            {
                "max77705_muic_irq_init": (1_126, "058cfa6a924135af3395b3673c0a9d9f5b9a03ea5bbccbc4c8d621f3c92149c0"),
                "max77705_muic_init_regs": (332, "ca288c14706998f8819bdd3f542bedf354b9c03c1cff384176d82a2453d47b47"),
                "max77705_muic_init_detect": (318, "45ae40c173a21764e1531bfeaa1be1db8465195c89624f6c4c4d6cf3319234fc"),
                "max77705_muic_probe": (5_669, "628307f37a472cb34bc1389745bbdee6bb6ab636eaeeccabe8ec609c42ab904e"),
                "max77705_muic_detect_dev": (5_863, "4b14abdd8cbd65d9d88aa01b912323e4a2321311cb9a88e5b9201dedd2e42ade"),
            },
            "MUIC source",
        )
    )
    functions.update(
        _exact_functions(
            usbc,
            {
                "max77705_init_irq_handler": (3_485, "fb0ba4ccd17703bf0230f6f152dbdfed7b059ae296fca82b940dca46469af42e"),
                "max77705_usbc_umask_irq": (392, "03d71661e3024aadc532049053d1885800dc8e85f40a29307cd073f481566bd6"),
                "max77705_usbc_probe": (8_802, "f5f6f0778da341b17d2381ae7bf0f2b9cac2c2f31c992383ab01671844648425"),
            },
            "USBC source",
        )
    )
    init_detect = _c_function_body(muic, "max77705_muic_init_detect")
    muic_irq_init = _c_function_body(muic, "max77705_muic_irq_init")
    muic_init_regs = _c_function_body(muic, "max77705_muic_init_regs")
    muic_probe = _c_function_body(muic, "max77705_muic_probe")
    detect = _c_function_body(muic, "max77705_muic_detect_dev")
    usbc_irq_init = _c_function_body(usbc, "max77705_init_irq_handler")
    usbc_probe = _c_function_body(usbc, "max77705_usbc_probe")
    unmask = _c_function_body(usbc, "max77705_usbc_umask_irq")
    macro_start = muic.find(b"#define REQUEST_IRQ")
    macro_end = muic.find(b"static int max77705_muic_irq_init", macro_start)
    if macro_start < 0 or macro_end < 0:
        raise AuditError("MUIC REQUEST_IRQ macro span is absent")
    request_macro = muic[macro_start:macro_end].rstrip() + b"\n"
    if identity(request_macro) != {
        "size": 307,
        "sha256": "98eabe8ff1233a303b3d6f778871037601d9e82b3c129d74ee9b240d8768e7c7",
    }:
        raise AuditError("MUIC REQUEST_IRQ macro differs")
    _ordered_once(
        request_macro,
        (
            b"ret = request_threaded_irq(_irq, NULL, max77705_muic_irq,",
            b"if (ret < 0)",
            b"_irq = 0;",
        ),
        "MUIC REQUEST_IRQ macro",
    )
    if b"return" in request_macro:
        raise AuditError("MUIC REQUEST_IRQ unexpectedly returns on failure")
    _ordered_once(
        muic_irq_init,
        (
            b'REQUEST_IRQ(muic_data->irq_uiadc, muic_data, "muic-uiadc");',
            b'REQUEST_IRQ(muic_data->irq_chgtyp, muic_data, "muic-chgtyp");',
            b'REQUEST_IRQ(muic_data->irq_dcdtmo, muic_data, "muic-dcdtmo");',
            b'REQUEST_IRQ(muic_data->irq_vbadc, muic_data, "muic-vbadc");',
            b'REQUEST_IRQ(muic_data->irq_vbusdet, muic_data, "muic-vbusdet");',
            b"return ret;",
        ),
        "MUIC nested IRQ registration",
    )
    _ordered_once(
        muic_init_regs,
        (
            b"ret = max77705_muic_irq_init(muic_data);",
            b"if (ret < 0)",
            b"max77705_muic_free_irqs(muic_data);",
            b"return ret;",
        ),
        "MUIC register initialization",
    )
    _ordered_once(
        init_detect,
        (
            b"muic_data->is_muic_ready = true;",
            b"max77705_muic_detect_dev(muic_data, MUIC_IRQ_INIT_DETECT);",
        ),
        "MUIC initial detect",
    )
    _ordered_once(
        muic_probe,
        (
            b"ret = max77705_muic_init_regs(muic_data);",
            b'pr_err("%s Failed to initialize MUIC irq:%d\\n",',
            b"goto fail_init_irq;",
            b"max77705_muic_init_detect(muic_data);",
            b"return 0;",
        ),
        "MUIC probe",
    )
    _ordered_once(
        detect,
        (
            b"ret = max77705_bulk_read(i2c,",
            b'pr_err("%s fail to read muic reg(%d)\\n",',
            b"new_dev = max77705_muic_check_new_dev(muic_data, &intr, irq);",
            b"max77705_muic_handle_attach(muic_data, new_dev, irq);",
        ),
        "MUIC status classification",
    )
    _ordered_once(
        usbc_probe,
        (
            b"max77705_init_irq_handler(usbc_data);",
            b"max77705_muic_probe(usbc_data);",
            b"max77705->cc_booting_complete = 1;",
            b"max77705_usbc_umask_irq(usbc_data);",
            b'msg_maxim("probing Complete..");',
            b"return 0;",
        ),
        "USBC platform probe",
    )
    if b"ret = max77705_muic_probe" in usbc_probe:
        raise AuditError("MUIC probe return is unexpectedly consumed")
    if b"ret = max77705_init_irq_handler" in usbc_probe:
        raise AuditError("USBC IRQ-handler return is unexpectedly consumed")
    if usbc.count(b"max77705_usbc_umask_irq(usbc_data);") != 3:
        raise AuditError("USBC unmask source call-site count differs")
    if usbc_probe.count(b"max77705_usbc_umask_irq(usbc_data);") != 1:
        raise AuditError("USBC probe unmask call-site count differs")
    if b"int max77705_init_irq_handler(" not in usbc or usbc_irq_init.count(
        b"request_threaded_irq("
    ) != 10:
        raise AuditError("USBC IRQ-handler registration family differs")
    _ordered_once(
        unmask,
        (
            b"max77705_read_reg(usbc_data->i2c, 0x23,",
            b"if (ret)",
            b"return;",
            b"i2c_data &= ~((1 << 3));",
            b"max77705_write_reg(usbc_data->i2c, 0x23,",
        ),
        "parent USBC unmask",
    )
    return {
        "functions": functions,
        "initial_detect_sets_ready_then_reads_and_classifies_status": True,
        "initial_detect_precedes_cc_booting_complete": True,
        "initial_detect_precedes_parent_usbc_unmask": True,
        "pre_muic_usbc_irq_handler_return_discarded": True,
        "pre_muic_usbc_irq_handler_families": [
            "APC",
            "SYSMSG",
            "VDM0-VDM6",
            "VIR0",
        ],
        "pre_muic_usbc_irq_failure_does_not_block_initial_detect_call": True,
        "muic_nested_irq_order": [
            "UIDADC",
            "CHGT",
            "DCD",
            "VBADC",
            "VBUSDET",
        ],
        "muic_nested_irq_shared_ret_is_overwritten_per_request": True,
        "nonfinal_muic_irq_failure_can_be_masked_by_later_success": True,
        "final_vbusdet_irq_failure_blocks_initial_detect": True,
        "muic_probe_error_is_not_propagated_by_usbc_probe": True,
        "unmask_read_failure_is_not_propagated_by_usbc_probe": True,
        "unmask_write_result_is_not_checked": True,
        "probing_complete_is_not_an_unmask_write_success_receipt": True,
        "unmask_source_call_sites_total": 3,
        "unmask_probe_call_sites_audited": 1,
        "unmask_recovery_call_sites_out_of_scope": 2,
    }


def _run_tool(command: list[str], cwd: Path, label: str) -> None:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AuditError(f"{label} execution failed") from exc
    if completed.returncode != 0:
        raise AuditError(f"{label} returned {completed.returncode}")


def audit_s7a2_ap(ap: bytes, magiskboot: bytes, lz4: bytes) -> dict[str, Any]:
    try:
        with tarfile.open(fileobj=io.BytesIO(ap), mode="r:") as archive:
            members = archive.getmembers()
            if (
                len(members) != 1
                or members[0].name != "boot.img.lz4"
                or not members[0].isfile()
                or members[0].size != 100_663_699
            ):
                raise AuditError("S7A2 AP member set differs")
            stream = archive.extractfile(members[0])
            if stream is None:
                raise AuditError("S7A2 compressed boot member is unavailable")
            compressed = stream.read()
    except (tarfile.TarError, OSError) as exc:
        raise AuditError("S7A2 AP tar is malformed") from exc
    if identity(compressed) != {
        "size": 100_663_699,
        "sha256": "97f9ea1b002954ccc65599a4e688451ab307d9964e347e19309dba58d9dbee12",
    }:
        raise AuditError("S7A2 compressed boot identity differs")
    with tempfile.TemporaryDirectory(prefix="p319-pdic-probe-") as directory:
        work = Path(directory)
        compressed_path = work / "boot.img.lz4"
        boot = work / "boot.img"
        lz4_path = work / "lz4"
        magiskboot_path = work / "magiskboot"
        compressed_path.write_bytes(compressed)
        lz4_path.write_bytes(lz4)
        magiskboot_path.write_bytes(magiskboot)
        os.chmod(compressed_path, 0o400)
        os.chmod(lz4_path, 0o500)
        os.chmod(magiskboot_path, 0o500)
        _run_tool([str(lz4_path), "-d", "-f", str(compressed_path), str(boot)], work, "S7A2 lz4")
        boot_payload = stable_bytes(
            boot,
            label="S7A2 decompressed boot",
            maximum=101 * 1024 * 1024,
            expected_size=100_663_296,
            expected_sha256="b9a4d4c2170da2ed6125aa44734005303d81d874b72402513def97b2f8406a54",
            required_nlink=1,
        )
        _run_tool([str(magiskboot_path), "unpack", str(boot)], work, "S7A2 boot unpack")
        ramdisk = work / "ramdisk.cpio"
        ramdisk_payload = stable_bytes(
            ramdisk,
            label="S7A2 ramdisk",
            maximum=2 * 1024 * 1024,
            expected_size=1_302_960,
            expected_sha256="3da7c61e22bd0a3daee41f6f55d933b944b98d03a9b478b98571aae94c5af449",
            required_nlink=1,
        )
        init = work / "candidate-init"
        module_list = work / "candidate-modules"
        _run_tool(
            [str(magiskboot_path), "cpio", str(ramdisk), f"extract init {init}"],
            work,
            "S7A2 init extraction",
        )
        _run_tool(
            [
                str(magiskboot_path),
                "cpio",
                str(ramdisk),
                "extract s22plus_m34_s7a2_runtime_gadget_split.modules " + str(module_list),
            ],
            work,
            "S7A2 module-list extraction",
        )
        init_payload = stable_bytes(
            init,
            label="S7A2 candidate init",
            maximum=16 * 1024,
            expected_size=8_904,
            expected_sha256="8f8eb4a6f4d94bc552ec61819b9c2b4ea4ec4de7fb7aa097fab7193c6f117e5a",
            required_nlink=1,
        )
        modules_payload = stable_bytes(
            module_list,
            label="S7A2 candidate module list",
            maximum=4 * 1024,
            expected_size=1_378,
            expected_sha256="c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998",
            required_nlink=1,
        )
        if stable_bytes(
            ramdisk,
            label="S7A2 ramdisk after extraction",
            maximum=2 * 1024 * 1024,
            expected_size=len(ramdisk_payload),
            expected_sha256=sha256(ramdisk_payload),
            required_nlink=1,
        ) != ramdisk_payload:
            raise AuditError("S7A2 ramdisk changed during extraction")
    rows = modules_payload.decode("ascii", "strict").splitlines()
    if len(rows) != 86 or len(rows) != len(set(rows)) or any(not row.endswith(".ko") for row in rows):
        raise AuditError("S7A2 module plan shape differs")
    expected_positions = {
        "msm-geni-se.ko": 30,
        "gpi.ko": 31,
        "i2c-msm-geni.ko": 62,
        "mfd_max77705.ko": 82,
        "spu_verify.ko": 83,
        "pdic_max77705.ko": 84,
    }
    actual_positions = {name: rows.index(name) + 1 for name in expected_positions}
    if actual_positions != expected_positions:
        raise AuditError("S7A2 MAX77705 module positions differ")
    strings = {
        b"phase=module name=": 1,
        b"phase=modules_load_done loaded=": 1,
        b"/s22plus_m34_s7a2_runtime_gadget_split.modules": 2,
    }
    if any(init_payload.count(token) != count for token, count in strings.items()):
        raise AuditError("S7A2 init loader strings differ")
    return {
        "ap": identity(ap),
        "compressed_boot": identity(compressed),
        "boot": identity(boot_payload),
        "ramdisk": identity(ramdisk_payload),
        "init": identity(init_payload),
        "module_list": identity(modules_payload),
        "module_count": len(rows),
        "module_positions_one_based": actual_positions,
        "plan_contains_transport_mfd_and_pdic_in_order": True,
        "plan_presence_is_not_live_load_proof": True,
    }


PROBE = b"pdic_max77705: max77705_muic_probe\n"
INIT_DETECT = b"pdic_max77705: max77705_muic_init_detect\n"
STATUS = b"pdic_max77705: max77705_muic_detect_dev USBC1:0x27, USBC2:0x05, BC:0x82"
ATTACHED = b"pdic_max77705: max77705_muic_detect_dev ATTACHED"
AP_PATH = b"pdic_max77705: com_to_usb_ap"
OPCODE_0609 = b"opcode_write: 00000000: 06 09"
NOTIFIER_CDP = b"muic_notifier_attach_attached_dev: (2)"
COMPLETE = b"max77705: max77705_usbc_probe: probing Complete.."
CHGT_IRQ = b"(muic-chgtyp)"
DETECT_READ_FAIL = b"max77705_muic_detect_dev fail to read muic reg"
UNMASK_READ_FAIL = b"max77705_usbc_umask_irq fail to read muic reg"


def audit_stock_initial_probe(corpus: dict[str, bytes]) -> dict[str, Any]:
    probe = {digest for digest, body in corpus.items() if PROBE in body}
    ap = {digest for digest, body in corpus.items() if AP_PATH in body}
    chgt = {digest for digest, body in corpus.items() if CHGT_IRQ in body}
    if len(probe) < 2 or probe != ap - chgt:
        raise AuditError("IRQ-free initial-probe capture set differs")
    per_capture: dict[str, Any] = {}
    sequence = (
        PROBE,
        INIT_DETECT,
        STATUS,
        ATTACHED,
        AP_PATH,
        OPCODE_0609,
        NOTIFIER_CDP,
        COMPLETE,
    )
    for digest in sorted(probe):
        body = corpus[digest]
        positions = []
        for token in sequence:
            if body.count(token) != 1:
                raise AuditError(f"stock initial-probe multiplicity differs: {digest}")
            positions.append(body.index(token))
        if positions != sorted(positions) or CHGT_IRQ in body:
            raise AuditError(f"stock initial-probe order/context differs: {digest}")
        selected_lines = [
            line
            for line in body.splitlines()
            if any(line.endswith(token.rstrip(b"\n")) for token in sequence)
        ]
        if len(selected_lines) != len(sequence) or any(b"modprobe" not in line for line in selected_lines):
            raise AuditError(f"stock initial-probe process attribution differs: {digest}")
        if DETECT_READ_FAIL in body or UNMASK_READ_FAIL in body:
            raise AuditError(f"stock probe read failure is present: {digest}")
        per_capture[digest] = {
            "sequence_count": 1,
            "process": "modprobe",
            "status": {"usbc1": "0x27", "usbc2": "0x05", "bc": "0x82"},
            "attached_dev": 2,
            "chgtyp_irq_lines": 0,
        }
    return {
        "corpus_distinct_captures": len(corpus),
        "captures_with_ap_path": len(ap),
        "captures_with_chgtyp_irq": len(chgt),
        "captures_with_irq_free_initial_probe": len(probe),
        "irq_free_initial_probe_set_equals_ap_without_chgtyp_set": True,
        "sequence": [
            "max77705_muic_probe",
            "max77705_muic_init_detect",
            "status 0x27/0x05/0x82",
            "ATTACHED",
            "com_to_usb_ap",
            "opcode 06 09",
            "notifier CDP 2",
            "probing Complete",
        ],
        "per_capture": per_capture,
        "initial_attach_requires_chgtyp_irq": False,
    }


def audit_historical_reports(inputs: dict[str, bytes]) -> dict[str, Any]:
    required = {
        "s7a2": (
            b"S7A2 marker found: `0`",
            b"no host-visible USB endpoint",
        ),
        "m7": (
            b"does not prove whether M7 reached the module loop",
            b"M7 marker in retained    no",
        ),
        "m11": (
            b"does not prove whether M11\nreached its `/dev/kmsg` marker",
            b"post_rollback_retained_marker_found=0",
        ),
        "m12": (
            b"does not prove whether M12\nreached its `/dev/kmsg` marker",
            b"post_rollback_retained_marker_found=0",
        ),
        "m18": (
            b"missing retained markers do not prove M18 died before the marker",
            b"The retained evidence does not localize the failure inside M18.",
        ),
    }
    result = {}
    for name, tokens in required.items():
        body = inputs[f"report_{name}"]
        if any(body.count(token) != 1 for token in tokens):
            raise AuditError(f"historical {name} evidence boundary differs")
        result[name] = {
            "retained_marker_proves_module_loop_reached": False,
            "actual_pdic_finit_module_rc_known": False,
            "platform_bind_proven": False,
            "initial_detect_proven": False,
            "unmask_write_success_proven": False,
        }
    return {
        "campaigns": result,
        "prior_wording_that_all_five_did_load_pdic_is_not_supported": True,
        "supported_wording": (
            "their candidate plans included pdic_max77705, while their retained "
            "evidence did not prove that the module loop reached or that pdic loaded"
        ),
    }


def audit_gate(gate: bytes) -> dict[str, Any]:
    tokens = (
        b'EXPECTED_M34_AP_SHA256 = "cb89ccf9c8c5481938ddd415930c78a23e1a679d45fdc57f95e6d1b48776bd59"',
        b'EXPECTED_M34_BOOT_SHA256 = "b9a4d4c2170da2ed6125aa44734005303d81d874b72402513def97b2f8406a54"',
        b'EXPECTED_M34_INIT_SHA256 = "8f8eb4a6f4d94bc552ec61819b9c2b4ea4ec4de7fb7aa097fab7193c6f117e5a"',
        b'EXPECTED_M34_MODULE_LIST_SHA256 = "c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998"',
        b'EXPECTED_M34_TEMPLATE_SOURCE_SHA256 = "ce12ea11a6c0f73f5f042801435b419637b473eff6631155f45d4ad382d8a80a"',
    )
    if any(gate.count(token) != 1 for token in tokens):
        raise AuditError("S7A2 gate identity chain differs")
    return {
        "ap_boot_init_module_list_and_source_identities_co_bound": True,
        "gate": identity(gate),
    }


def build_result(
    inputs: dict[str, bytes],
    manifest: dict[str, Any],
    corpus: dict[str, bytes],
) -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise AuditError("P3.19 probe build must execute from bound source")
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": {
            "model": "SM-S906N",
            "codename": "g0q",
            "build": "S906NKSS7FYG8",
        },
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
        "inputs": {name: identity(payload) for name, payload in sorted(inputs.items())},
        "corpus_manifest_semantics": audit_corpus_manifest_semantics(manifest),
        "implementation": {"auditor": identity(_BOUND_AUDITOR_SOURCE)},
        "s7a2_gate": audit_gate(inputs["s7a2_gate"]),
        "s7a2_candidate_ap": audit_s7a2_ap(
            inputs["s7a2_ap"], inputs["magiskboot"], inputs["lz4"]
        ),
        "s7a2_loader": audit_candidate_loader(inputs["historical_loader_source"]),
        "pdic_binary": audit_pdic_binary(inputs["pdic_module"]),
        "probe_source": audit_probe_sources(inputs["muic_source"], inputs["usbc_source"]),
        "stock_initial_probe": audit_stock_initial_probe(corpus),
        "historical_candidate_evidence": audit_historical_reports(inputs),
        "conclusion": {
            "stock_initial_attach_occurs_inside_probe_without_chgtyp_irq": True,
            "parent_usbc_unmask_is_not_a_precondition_for_initial_classification": True,
            "pre_muic_usbc_irq_registration_failure_blocks_initial_mux": False,
            "nonfinal_muic_irq_failure_can_be_masked_by_later_success": True,
            "final_vbusdet_irq_failure_can_block_initial_detect": True,
            "all_muic_irq_registration_failure_is_nonblocking": False,
            "absence_of_chgtyp_interrupt_delivery_explains_initial_mux_silence": False,
            "successful_platform_probe_or_complete_log_does_not_prove_muic_init_success": True,
            "successful_platform_probe_or_complete_log_does_not_prove_unmask_write_success": True,
            "s7a2_ap_contains_the_required_module_plan": True,
            "s7a2_live_module_load_bind_probe_and_unmask_remain_unproven": True,
            "old_claim_that_s7a2_m7_m11_m12_m18_did_load_pdic_with_live_proof": False,
            "next_candidate_witness_order": [
                "durable per-module finit_module result for i2c-msm-geni, mfd_max77705 and pdic_max77705",
                "exact max77705-usbc platform bind identity",
                "MUIC initial five-byte status read and classified device",
                "parent INTSRC mask register readback with bit 3 clear",
            ],
            "acm_is_not_a_required_evidence_channel": True,
            "retained_ring_should_carry_the_candidate_witness": True,
        },
    }
    if stable_bytes(AUDITOR, label="post-run P3.19 probe auditor", maximum=1 << 20) != _BOUND_AUDITOR_SOURCE:
        raise AuditError("P3.19 probe auditor changed during execution")
    return result


def encode(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def run(materialize: bool) -> tuple[dict[str, Any], bytes]:
    inputs = load_inputs(materialize)
    manifest = parse_corpus_manifest(load_corpus_manifest())
    corpus = load_corpus(manifest)
    value = build_result(inputs, manifest, corpus)
    return value, encode(value)


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
        publish_exclusive(OUTPUT, payload)
    else:
        existing = stable_bytes(
            OUTPUT,
            label="P3.19 candidate PDIC probe receipt",
            maximum=256 * 1024,
            expected_size=len(payload),
            expected_sha256=sha256(payload),
            required_mode=0o400,
            required_nlink=1,
        )
        if existing != payload:
            raise AuditError("P3.19 candidate PDIC probe receipt differs")
    print(f"{VERDICT} {len(payload)} {sha256(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
