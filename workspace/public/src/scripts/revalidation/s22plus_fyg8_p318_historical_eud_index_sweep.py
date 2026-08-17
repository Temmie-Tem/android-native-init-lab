#!/usr/bin/env python3
"""Audit historical S22+ EUD module ordinals and retained Carrier structure.

This is a bounded H0 tool.  It has no subprocess, ADB, USB, Odin, transfer,
recovery, or device-action path.  It proves the effective early-module ordinal
and the inherited EUD-cache trigger for P3.10, P3.11, P3.13, P3.14, P3.17, and
P3.18, then structurally audits the already-preserved final retained reads.
Prior campaign semantics are cited from their reviewed reports rather than
re-derived by this tool.
"""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
import re
import stat
import struct
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
AUDITOR = Path(__file__).resolve()
OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "historical-eud-index-sweep-20260817-02.json"
)
RUNS = ROOT / "workspace/private/runs/device-action-f1-live-v2"
SCHEMA = "s22plus_fyg8_p318_historical_eud_index_sweep_v2"
VERDICT = "PASS_P318_HISTORICAL_EUD_INDEX_AND_RETAINED_SWEEP_H0_V2"
RUN_ID = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")

LONG_FAMILY = b"S22E1L2|"
UNSAT_FAMILY = b"S22E1U2|"
LEGACY_FAMILIES = (b"S22E1L1|", b"S22E1U1|", b"[[S22P1U|", b"S22UNS1|")
HEADER = struct.Struct("<8sBBH16sI")
SLOT_BODY = struct.Struct("<BBBBBBBH67s")
HEADER_SIZE = 32
SLOT_SIZE = 80
RECORD_SIZE = 192
HEADER_CRC_DOMAIN = b"S22PLUS-FYG8-P310-HEADER-V2\0"
SLOT_CRC_DOMAIN = b"S22PLUS-FYG8-P310-SLOT-V2\0"


class SweepError(RuntimeError):
    """The exact historical artifact or retained evidence differs."""


_BOUND_AUDITOR_SOURCE = globals().get("_P318_EUD_SWEEP_BOUND_SOURCE")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def _file_identity(state: os.stat_result) -> tuple[int, ...]:
    return (
        state.st_dev,
        state.st_ino,
        state.st_mode,
        state.st_nlink,
        state.st_uid,
        state.st_gid,
        state.st_size,
        state.st_mtime_ns,
        state.st_ctime_ns,
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
        raise SweepError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(before.st_mode)
        or before.st_nlink < 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or _file_identity(before) != _file_identity(inside)
        or _file_identity(before) != _file_identity(after)
        or (expected_size is not None and len(payload) != expected_size)
        or (expected_sha256 is not None and sha256(payload) != expected_sha256)
        or (
            required_mode is not None
            and stat.S_IMODE(before.st_mode) != required_mode
        )
        or (required_nlink is not None and before.st_nlink != required_nlink)
    ):
        raise SweepError(f"{label} identity differs")
    return payload


def load_bound_auditor() -> Any:
    payload = stable_bytes(AUDITOR, label="historical EUD sweep bootstrap", maximum=1 << 20)
    module = types.ModuleType("s22plus_fyg8_p318_historical_eud_index_sweep_bound")
    module.__file__ = str(AUDITOR)
    module.__package__ = ""
    module.__dict__["_P318_EUD_SWEEP_BOUND_SOURCE"] = payload
    try:
        code = compile(payload.decode("utf-8"), str(AUDITOR), "exec", dont_inherit=True)
        exec(code, module.__dict__)  # noqa: S102
    except Exception as exc:
        raise SweepError("historical EUD sweep bound-source execution failed") from exc
    return module


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SweepError("historical JSON contains a duplicate key")
        value[key] = item
    return value


def strict_json(payload: bytes, label: str) -> Any:
    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                SweepError(f"{label} contains {token}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SweepError(f"{label} is not strict JSON") from exc


def _json_path(value: Any, path: tuple[str, ...], label: str) -> Any:
    current = value
    for key in path:
        if type(current) is not dict or key not in current:
            raise SweepError(f"{label} authoritative path differs")
        current = current[key]
    return current


def _require_identity_at_path(
    value: Any,
    path: tuple[str, ...],
    expected: dict[str, Any],
    label: str,
) -> None:
    actual = _json_path(value, path, label)
    if (
        type(actual) is not dict
        or set(actual) != set(expected)
        or type(actual.get("sha256")) is not str
        or type(actual.get("size")) is not int
        or ("path" in expected and type(actual.get("path")) is not str)
        or actual != expected
    ):
        raise SweepError(f"{label} authoritative identity differs")


def _source_identity_paths(campaign: str, key: str) -> tuple[tuple[str, ...], ...]:
    if campaign == "p310":
        primary = ("candidate_contract", "identity_preimage", "sources", key)
        secondary = {
            "plan_header": (("source_contract", "plan_header"),),
            "p290_e3_runtime_include": (),
            "runtime_wrapper": (("source_contract", "source", "runtime"),),
        }[key]
        return (primary, *secondary)
    return (
        ("candidate_contract", "generated_artifacts", key),
        ("source_contract", "generated_artifacts", key),
    )


def _artifact_userspace_paths(campaign: str) -> tuple[tuple[str, ...], ...]:
    paths = (("userspace_closure", "result"),)
    if campaign == "p310":
        return (
            *paths,
            ("kernel_closure", "pre_lto_qualification", "gate_result_receipts", "userspace"),
        )
    return paths


def _brace_block(source: str, token: str, label: str) -> str:
    if source.count(token) != 1:
        raise SweepError(f"{label} extent differs")
    start = source.index(token)
    opening = source.index("{", start + len(token) - 1)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise SweepError(f"{label} is unterminated")


def _module_plan(source: str) -> tuple[tuple[str, str, str], ...]:
    token = (
        "static const struct s22plus_o2_module_plan_entry "
        "s22plus_o2_module_plan[] = {"
    )
    try:
        start = source.index(token) + len(token)
        end = source.index("\n};", start)
    except ValueError as exc:
        raise SweepError("historical module-plan extent differs") from exc
    matches = tuple(
        re.fullmatch(r'\s*\{"([^"]+)",\s*"([^"]+)",\s*"([^"]*)"\},\s*', line)
        for line in source[start:end].splitlines()
        if line.strip()
    )
    if not matches or any(match is None for match in matches):
        raise SweepError("historical module-plan row grammar differs")
    return tuple(match.groups() for match in matches if match is not None)


CAMPAIGNS: tuple[dict[str, Any], ...] = (
    {
        "name": "p310", "plan_size": 4707,
        "plan_sha256": "d5ec1423cd47aba29c935512690c4e0b9af3302e4df1b91e50ed1cc816199005",
        "runtime_size": 174232,
        "runtime_sha256": "7ba9d8d54d9490a1cdd9027b9dbca678aa21dc40c4eb1e24e5e681f2b1fe661c",
        "wrapper_size": 29794,
        "wrapper_sha256": "9fcf28021bc2afbc20b372fa119ae65e29f1395272f054ef444fc31bc8f765da",
        "userspace_size": 59332,
        "userspace_sha256": "462b477880fbd6c46c982a321086a837173f9532e8ce2dc02ecccd58a88c779d",
        "artifact_size": 96364,
        "artifact_sha256": "6b6189bdb3c9a00332285915db7c9637238d8840f3909c0cd081c0e828379ad5",
        "live_result_size": 17385,
        "live_result_sha256": "85f610fbc6ca009ff9a85d8697c8ccb235f89b32741636d2cfa7b8f51e0bc680",
        "candidate_dirs": ("candidate-a-v6", "candidate-b-v6"),
        "plan_count": 61, "eud_index": 37,
        "run_dirs": ("p310-ready1-prepared-20260807-1", "p310-ready1-prepared-20260807-2"),
        "final_run": "p310-ready1-prepared-20260807-2",
        "observer_inventory": (
            "p310-ready1-prepared-20260807-1/preflight/baseline-observer.bin",
            "p310-ready1-prepared-20260807-2/execute-preflight-01/baseline-observer.bin",
            "p310-ready1-prepared-20260807-2/preflight/baseline-observer.bin",
            "p310-ready1-prepared-20260807-2/rollback-observer-1.bin",
            "p310-ready1-prepared-20260807-2/rollback-observer-2.bin",
        ),
        "raw_sha256": "3c17354904825260d74ad9093314c6f4740a9d9623c0051aee817861e0a303c7",
        "records": ((1648800, (106, 146, 0, 1, 0, 0, 0, 3355), (107, 147, 2, 0, 0, 0, 0, 16389)),),
        "prior_semantic": "normal-pair-no-bad-body",
    },
    {
        "name": "p311", "plan_size": 4707,
        "plan_sha256": "d5ec1423cd47aba29c935512690c4e0b9af3302e4df1b91e50ed1cc816199005",
        "runtime_size": 189822,
        "runtime_sha256": "375a6e7277aeda1cf305b35828a23da1186470a5c40e19294e6c41f96cbb77b2",
        "wrapper_size": 30350,
        "wrapper_sha256": "7621db9b54e3da9c2b6c0bd7a0491b543e66f71e65e3736451076ed2d434347e",
        "userspace_size": 211251,
        "userspace_sha256": "363efbc83888cb4216c2b8c4294885e4b2510ccd4e9ba055c40dd321c84e8f42",
        "artifact_size": 220017,
        "artifact_sha256": "25686e0a4e0f77b2af7680214345847d1dbed28c81490f23578cccf45c5bf731",
        "live_result_size": 13453,
        "live_result_sha256": "95b3e41e5da96ae0e072aef8f3bcaf4248623aa58ba26828329465275b824032",
        "candidate_dirs": ("candidate-a", "candidate-b"),
        "plan_count": 61, "eud_index": 37,
        "run_dirs": ("s22plus-fyg8-p311-run-1",),
        "final_run": "s22plus-fyg8-p311-run-1",
        "observer_inventory": (
            "s22plus-fyg8-p311-run-1/execute-preflight-01/baseline-observer.bin",
            "s22plus-fyg8-p311-run-1/preflight/baseline-observer.bin",
            "s22plus-fyg8-p311-run-1/rollback-observer-1.bin",
            "s22plus-fyg8-p311-run-1/rollback-observer-2.bin",
        ),
        "raw_sha256": "a9f1e7d8e516b3ba08a17aad6bb74f40f2c10082f4f799f3ae4983458441bab8",
        "records": ((1649810, (68, 123, 0, 59, 0, 0, 0, 0), (69, 124, 2, 0, 0, 0, 0, 26629)),),
        "prior_semantic": "carrier-v1-selection-recovered-0x6805",
    },
    {
        "name": "p313", "plan_size": 4707,
        "plan_sha256": "d5ec1423cd47aba29c935512690c4e0b9af3302e4df1b91e50ed1cc816199005",
        "runtime_size": 229827,
        "runtime_sha256": "db5d686d415f1a257cbff7cd013c030221899673cc6567f160e90b239bbb6177",
        "wrapper_size": 29794,
        "wrapper_sha256": "9fcf28021bc2afbc20b372fa119ae65e29f1395272f054ef444fc31bc8f765da",
        "userspace_size": 317226,
        "userspace_sha256": "3cd310807ee58787f7eceb24f623be67d1420f9cd369612fcdae290194d9a0f9",
        "artifact_size": 336253,
        "artifact_sha256": "7b9bee611719d0c31dea44fc8defd865daae5021ed08e8b222c746cb03440c05",
        "live_result_size": 12433,
        "live_result_sha256": "24d81819dba463ef3dccab9e5cc518defd275ddc1e6be466032944a59a05720a",
        "candidate_dirs": ("candidate-a", "candidate-b"),
        "plan_count": 61, "eud_index": 37,
        "run_dirs": ("p313-ready1-prepared-20260810-1", "p313-ready1-prepared-20260810-2"),
        "final_run": "p313-ready1-prepared-20260810-2",
        "observer_inventory": (
            "p313-ready1-prepared-20260810-1/preflight/baseline-observer.bin",
            "p313-ready1-prepared-20260810-2/execute-preflight-01/baseline-observer.bin",
            "p313-ready1-prepared-20260810-2/preflight/baseline-observer.bin",
            "p313-ready1-prepared-20260810-2/rollback-observer-1.bin",
            "p313-ready1-prepared-20260810-2/rollback-observer-2.bin",
        ),
        "raw_sha256": "52e5ab6af1fa5a5c8c03e2fea27ee5f3fe3276d3c6e920ae44c3c0efc9a5623f",
        "records": ((1648657, (96, 144, 0, 3, 0, 0, 0, 0), (97, 144, 2, 4, 0, 0, 0, 26386)),),
        "prior_semantic": "valid-bad-body-recovered-0x6712",
    },
    {
        "name": "p314", "plan_size": 4707,
        "plan_sha256": "d5ec1423cd47aba29c935512690c4e0b9af3302e4df1b91e50ed1cc816199005",
        "runtime_size": 234791,
        "runtime_sha256": "37db3603a32726f2dec1ce78e13591ffe25a479439faeaee9128bbdba738c2e6",
        "wrapper_size": 29794,
        "wrapper_sha256": "9fcf28021bc2afbc20b372fa119ae65e29f1395272f054ef444fc31bc8f765da",
        "userspace_size": 434617,
        "userspace_sha256": "ca99e2b1ef11766e792641050d6c93edbf86a3820c265755b2d5b724272cda2f",
        "artifact_size": 473153,
        "artifact_sha256": "96c0b169be4cc985e2b515e48837615bd56a87c1f35b05cd2f3eb3e3c4bb1aae",
        "live_result_size": 13664,
        "live_result_sha256": "d947c2a0fa4ef73ee8c2d64a0fb8d3ca499fbe8866fa0a29b788fbe01e34b1d5",
        "candidate_dirs": ("candidate-a", "candidate-b"),
        "plan_count": 61, "eud_index": 37,
        "run_dirs": ("p314-ready1-prepared-20260810-1", "p314-ready1-prepared-20260810-2"),
        "final_run": "p314-ready1-prepared-20260810-2",
        "observer_inventory": (
            "p314-ready1-prepared-20260810-1/preflight/baseline-observer.bin",
            "p314-ready1-prepared-20260810-2/execute-preflight-02/baseline-observer.bin",
            "p314-ready1-prepared-20260810-2/preflight/baseline-observer.bin",
            "p314-ready1-prepared-20260810-2/rollback-observer-1.bin",
            "p314-ready1-prepared-20260810-2/rollback-observer-2.bin",
        ),
        "raw_sha256": "1a7e316a9491ab0a2f63ddf259a9ee6a3143a3391cd61c685ea876b3bf25c310",
        "records": ((1642297, (96, 144, 0, 3, 0, 0, 0, 0), (97, 144, 2, 4, 0, 0, 0, 26373)),),
        "prior_semantic": "profile-deficit-no-bad-body",
    },
    {
        "name": "p317", "plan_size": 5073,
        "plan_sha256": "0315121512b40c5b0b087b8de913f9af9dc29182376f336221a2422ce90ce155",
        "runtime_size": 361424,
        "runtime_sha256": "ed2707396352c0cbae71cf4e282c8ba27e1abae36bbf8fc4042373c656d8adc2",
        "wrapper_size": 30664,
        "wrapper_sha256": "14ec73c72dd61621b24e9424c1d1069719d84a6f6983c7badc208e6e56fdbf96",
        "userspace_size": 2017356,
        "userspace_sha256": "1b00407b402563e5ed0bc0e31ab0541491c9ad565b74c85a709d329936670e37",
        "artifact_size": 2050478,
        "artifact_sha256": "3e030292d30a52c8465864de961a69219757510e781d41e56c314c8357659f7e",
        "live_result_size": 28908,
        "live_result_sha256": "5e02c3ed91f6b238d19b19763877d81585c540b0b474d0fa642bf4f244693b2a",
        "candidate_dirs": ("candidate-a", "candidate-b"),
        "plan_count": 69, "eud_index": 37,
        "run_dirs": ("f1-2026-08-12T165954582328Z-1786553994582372233",),
        "final_run": "f1-2026-08-12T165954582328Z-1786553994582372233",
        "observer_inventory": (
            "f1-2026-08-12T165954582328Z-1786553994582372233/execute-preflight-01/baseline-observer.bin",
            "f1-2026-08-12T165954582328Z-1786553994582372233/preflight/baseline-observer.bin",
            "f1-2026-08-12T165954582328Z-1786553994582372233/rollback-observer-1.bin",
            "f1-2026-08-12T165954582328Z-1786553994582372233/rollback-observer-2.bin",
        ),
        "raw_sha256": "758ad7360f43baa14ca2e5f4ad3d72b00c31ec829caeb365f1de91a6b67aefd8",
        "records": (
            (871173, (106, 146, 0, 1, 1, 64, 0, 3491), (107, 147, 2, 0, 1, 64, 0, 26384)),
            (1292824, (106, 146, 0, 1, 1, 64, 0, 3491), (107, 147, 2, 0, 1, 64, 0, 26384)),
            (1636994, (94, 144, 0, 1, 0, 0, 0, 0), (95, 144, 0, 2, 0, 0, 0, 0)),
        ),
        "prior_semantic": "multiplicity-no-bad-body",
    },
    {
        "name": "p318", "plan_size": 5142,
        "plan_sha256": "682f18fb470b0e538eb463db5d2a865864b8aaa4681b41230e7c20cc134e70d7",
        "runtime_size": 397669,
        "runtime_sha256": "050a8eb0deeb755540e9ca860b0ab50a6e9d69c02a644805f7cfd6eae644e42e",
        "wrapper_size": 30664,
        "wrapper_sha256": "8c0bf6a4765aa2a27bfe420de6c8599366267e546422378a21f586a8beeb9b7b",
        "userspace_size": 261101,
        "userspace_sha256": "bbc44e25086ca58c8cb32cc75577461b8a8d8a17e82530cc268dc52868399283",
        "artifact_size": 267768,
        "artifact_sha256": "344f3de1505318e85f36d72201c56a25ad1443676e1682cdb65c55e99bd064a1",
        "live_result_size": 14365,
        "live_result_sha256": "0af93d923086e0cc8f37615efca19ba6696b930f9ccaa68d529c41be13edaca9",
        "candidate_dirs": ("candidate-a", "candidate-b"),
        "plan_count": 70, "eud_index": 38,
        "run_dirs": ("s22plus-fyg8-p318-live-1",),
        "final_run": "s22plus-fyg8-p318-live-1",
        "observer_inventory": (
            "s22plus-fyg8-p318-live-1/execute-preflight-01/baseline-observer.bin",
            "s22plus-fyg8-p318-live-1/preflight/baseline-observer.bin",
            "s22plus-fyg8-p318-live-1/rollback-observer-1.bin",
            "s22plus-fyg8-p318-live-1/rollback-observer-2.bin",
        ),
        "raw_sha256": "4a0d9db45040fca213c9d2a6c730e28217d360809ed8c19c4748d682509cdd5e",
        "records": ((1649274, (46, 101, 0, 37, 0, 0, 0, 0), (47, 102, 2, 38, 0, 0, 0, 24592)),),
        "prior_semantic": "valid-bad-body-recovered-0x6010",
    },
)


REPORTS = {
    "p310": (
        "docs/reports/S22PLUS_FYG8_P310_CARRIER_V2_JSON_SERIALIZATION_INCIDENT_2026-08-09.md",
        ("one normal adjacent pair with clean", "Generation 107", "0x4005"),
    ),
    "p311": (
        "docs/reports/S22PLUS_FYG8_P311_PROFILE_WINDOW_AND_CARRIER_DECODER_INCIDENT_2026-08-09.md",
        ("selected Carrier-v1 semantics", "0x6805", "Carrier-v2 record"),
    ),
    "p313": (
        "docs/reports/S22PLUS_FYG8_P313_INTERMEDIATE_CONTRADICTION_DECODER_INCIDENT_2026-08-10.md",
        ("slot status `bad-body`", "0x6712", "P313_OBSERVER_CONTRADICTION"),
    ),
    "p314": (
        "docs/reports/S22PLUS_FYG8_P314_LIVE_PROFILE_SNAPSHOT_INCIDENT_2026-08-10.md",
        ("generation 97", "0x6705", "valid profile lower-bound"),
    ),
    "p317": (
        "docs/reports/S22PLUS_FYG8_P317_CDC_ACM_ENDPOINT_SELECTOR_CORRECTION_H0_2026-08-14.md",
        ("byte-identical retained records", "multiplicity", "campaign-level no-proof"),
    ),
    "p318": (
        "docs/reports/S22PLUS_FYG8_P318_POSTLIVE_EUD_INDEX_RECOVERY_H0_2026-08-17.md",
        ("[valid, bad-body]", "index 37", "index 38", "0x6010"),
    ),
}


def _campaign_paths(campaign: dict[str, Any]) -> dict[str, Path]:
    base = ROOT / f"workspace/private/outputs/s22plus_fyg8_{campaign['name']}"
    return {
        "plan": base / "intent/materialized-sources/s22plus_fyg8_p286_e3_plan.h",
        "runtime": base / "intent/materialized-sources/s22plus_fyg8_p290_e3_runtime.inc.c",
        "wrapper": base / "intent/materialized-sources/s22plus_fyg8_p290_e3_runtime.c",
        "userspace": base / "userspace/userspace-result.json",
        "candidate_a": base / campaign["candidate_dirs"][0] / "artifact-result.json",
        "candidate_b": base / campaign["candidate_dirs"][1] / "artifact-result.json",
    }


def audit_plan_runtime(
    plan: bytes, runtime: bytes, wrapper: bytes, campaign: dict[str, Any]
) -> dict[str, Any]:
    try:
        plan_text = plan.decode("utf-8")
        runtime_text = runtime.decode("utf-8")
        wrapper_text = wrapper.decode("utf-8")
    except UnicodeError as exc:
        raise SweepError(f"{campaign['name']} module source is not UTF-8") from exc
    rows = _module_plan(plan_text)
    eud = [
        index for index, row in enumerate(rows)
        if row == ("eud.ko", "eud", "")
    ]
    latch = [
        index for index, row in enumerate(rows)
        if row == (
            "s22plus_dwc3_event_latch.ko", "s22plus_dwc3_event_latch", ""
        )
    ]
    trigger = re.findall(r"#define P307_EUD_MODULE_INDEX ([0-9]+)U", runtime_text)
    loop_token = (
        "for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {"
    )
    plan_include = '#include "s22plus_fyg8_p286_e3_plan.h"'
    runtime_include = '#include "s22plus_fyg8_p290_e3_runtime.inc.c"'
    eud_condition = "if (index == P307_EUD_MODULE_INDEX)"
    eud_call = "long p307_eud_cache_rc = p307_read_eud_cache();"
    folded_definition = (
        "P305_MODULE_STAGE_CAPACITY =\n"
        "            S22_P241_GATE_STAGE_BASE - S22_P241_MODULE_STAGE_BASE,\n"
        "        P305_FOLDED_MODULE_INDEX = P305_MODULE_STAGE_CAPACITY - 1U,"
    )
    eud_block = (
        "        if (index == P307_EUD_MODULE_INDEX) {\n"
        "            long p307_eud_cache_rc = p307_read_eud_cache();\n"
        "            if (p307_eud_cache_rc != 0) p290_fail_next(p307_eud_cache_rc);\n"
        "        }"
    )
    first_loop = _brace_block(
        wrapper_text, loop_token, f"{campaign['name']} first module loop"
    )
    module_base = re.findall(
        r"#define S22_P241_MODULE_STAGE_BASE (0x[0-9a-fA-F]+)U", wrapper_text
    )
    gate_base = re.findall(
        r"#define S22_P241_GATE_STAGE_BASE (0x[0-9a-fA-F]+)U", wrapper_text
    )
    if (
        len(rows) != campaign["plan_count"]
        or eud != [campaign["eud_index"]]
        or trigger != ["37"]
        or runtime_text.count("P307_EUD_MODULE_INDEX") != 1
        or latch != ([] if campaign["name"] != "p318" else [0])
    ):
        raise SweepError(f"{campaign['name']} effective module index differs")
    if module_base != ["0x40"] or gate_base != ["0x7c"]:
        raise SweepError(f"{campaign['name']} first module loop bound differs")
    if (
        wrapper_text.count(plan_include) != 1
        or wrapper_text.count(runtime_include) != 1
        or wrapper_text.index(plan_include) >= wrapper_text.index(runtime_include)
        or wrapper_text.index(runtime_include) >= wrapper_text.index(loop_token)
    ):
        raise SweepError(f"{campaign['name']} materialized include chain differs")
    folded_index = int(gate_base[0], 16) - int(module_base[0], 16) - 1
    if (
        wrapper_text.count(folded_definition) != 1
        or folded_index != 59
        or int(trigger[0]) >= folded_index
        or wrapper_text.count("P307_EUD_MODULE_INDEX") != 1
        or wrapper_text.count(eud_condition) != 1
        or wrapper_text.count("p307_read_eud_cache") != 1
        or wrapper_text.count("p307_read_eud_cache()") != 1
        or first_loop.count(eud_block) != 1
        or first_loop.count(eud_call) != 1
        or first_loop.count("p241_load_and_verify_module(index));") != 1
        or first_loop.index("p241_load_and_verify_module(index));")
        >= first_loop.index(eud_block)
    ):
        raise SweepError(f"{campaign['name']} EUD cache consumer differs")
    return {
        "module_count": len(rows),
        "eud_index": eud[0],
        "cache_trigger_index": int(trigger[0]),
        "index_matches": eud[0] == int(trigger[0]),
        "latch_indices": latch,
        "cache_consumer_wrapper_bound": True,
        "cache_consumer_condition_count": 1,
        "cache_consumer_call_count": 1,
        "materialized_plan_and_runtime_includes_bound": True,
        "first_loop_upper_bound_exclusive": folded_index,
        "cache_trigger_reachable_in_first_loop": True,
    }


def audit_p317_p318_plan_delta(p317_plan: bytes, p318_plan: bytes) -> dict[str, Any]:
    try:
        p317_rows = _module_plan(p317_plan.decode("utf-8"))
        p318_rows = _module_plan(p318_plan.decode("utf-8"))
    except UnicodeError as exc:
        raise SweepError("P3.17/P3.18 module-plan delta is not UTF-8") from exc
    latch = ("s22plus_dwc3_event_latch.ko", "s22plus_dwc3_event_latch", "")
    if p318_rows != (latch, *p317_rows):
        raise SweepError("P3.18 plan is not the exact latch-prefixed P3.17 plan")
    return {
        "p317_inherited_row_count": len(p317_rows),
        "p318_row_count": len(p318_rows),
        "p318_exact_latch_prefix_plus_p317": True,
    }


def audit_package_chain(
    userspace: bytes,
    candidate: bytes,
    *,
    campaign: dict[str, Any],
    plan_identity: dict[str, Any],
    runtime_identity: dict[str, Any],
    wrapper_identity: dict[str, Any],
    userspace_identity: dict[str, Any],
) -> dict[str, Any]:
    userspace_json = strict_json(userspace, f"{campaign['name']} userspace receipt")
    candidate_json = strict_json(candidate, f"{campaign['name']} candidate receipt")
    source_identities = {
        "plan_header": plan_identity,
        "p290_e3_runtime_include": runtime_identity,
        "runtime_wrapper": wrapper_identity,
    }
    source_path_count = 0
    for key, expected in source_identities.items():
        paths = _source_identity_paths(campaign["name"], key)
        for path in paths:
            _require_identity_at_path(
                userspace_json,
                path,
                expected,
                f"{campaign['name']} userspace {key}",
            )
            source_path_count += 1
    if campaign["name"] == "p310":
        materialized_names = {
            "plan_header": "s22plus_fyg8_p286_e3_plan.h",
            "p290_e3_runtime_include": "s22plus_fyg8_p290_e3_runtime.inc.c",
            "runtime_wrapper": "s22plus_fyg8_p290_e3_runtime.c",
        }
        for key, filename in materialized_names.items():
            _require_identity_at_path(
                userspace_json,
                ("candidate_contract", "materialized_sources", key),
                {"path": f"materialized-sources/{filename}", **source_identities[key]},
                f"{campaign['name']} materialized {key}",
            )
            source_path_count += 1
    artifact_paths = _artifact_userspace_paths(campaign["name"])
    for path in artifact_paths:
        _require_identity_at_path(
            candidate_json,
            path,
            userspace_identity,
            f"{campaign['name']} candidate userspace",
        )
    return {
        "authoritative_source_identity_path_count": source_path_count,
        "authoritative_candidate_userspace_path_count": len(artifact_paths),
        "recursive_identity_existence_used": False,
    }


def audit_live_result_attribution(
    payload: bytes,
    *,
    campaign: dict[str, Any],
    final_run: Path,
) -> dict[str, Any]:
    value = strict_json(payload, f"{campaign['name']} live result")
    expected_manifest = (
        f"s22plus-fyg8-{campaign['name']}-process-v2-ready-1"
    )
    if (
        type(value) is not dict
        or type(value.get("schema")) is not str
        or value["schema"] != "device_action_f1_live_result_v2"
        or type(value.get("manifest_id")) is not str
        or value["manifest_id"] != expected_manifest
        or type(value.get("current_state")) is not str
        or value["current_state"] != "CLOSED"
    ):
        raise SweepError(f"{campaign['name']} live-result campaign identity differs")
    observer = _json_path(
        value,
        ("live_state", "final_evidence", "observer"),
        f"{campaign['name']} final observer",
    )
    if type(observer) is not dict:
        raise SweepError(f"{campaign['name']} final observer differs")
    reads = observer.get("reads")
    if (
        type(reads) is not list
        or len(reads) != 2
        or observer.get("byte_identical") is not True
        or type(observer.get("bytes")) is not int
        or observer["bytes"] != 2_097_136
        or type(observer.get("sha256")) is not str
        or observer["sha256"] != campaign["raw_sha256"]
    ):
        raise SweepError(f"{campaign['name']} final observer summary differs")
    receipts = []
    for index, read in enumerate(reads, 1):
        expected = final_run / f"rollback-observer-{index}.bin"
        if (
            type(read) is not dict
            or type(read.get("path")) is not str
            or read["path"] != str(expected.absolute())
            or type(read.get("bytes")) is not int
            or read["bytes"] != 2_097_136
            or type(read.get("sha256")) is not str
            or read["sha256"] != campaign["raw_sha256"]
            or read.get("read_to_eof") is not True
            or type(read.get("stderr_bytes")) is not int
            or read["stderr_bytes"] != 0
        ):
            raise SweepError(f"{campaign['name']} final observer read differs")
        receipts.append({
            "path": str(expected.relative_to(ROOT)),
            "bytes": read["bytes"],
            "sha256": read["sha256"],
            "read_to_eof": True,
            "stderr_bytes": 0,
        })
    return {
        "live_result_schema": "device_action_f1_live_result_v2",
        "live_result_manifest_id": expected_manifest,
        "live_result_state": "CLOSED",
        "final_observer_byte_identical": True,
        "final_observer_reads": receipts,
    }


def _read_campaign(campaign: dict[str, Any]) -> dict[str, Any]:
    paths = _campaign_paths(campaign)
    plan = stable_bytes(
        paths["plan"], label=f"{campaign['name']} materialized module plan",
        maximum=8192, expected_size=campaign["plan_size"],
        expected_sha256=campaign["plan_sha256"],
    )
    runtime = stable_bytes(
        paths["runtime"], label=f"{campaign['name']} materialized runtime",
        maximum=1 << 20, expected_size=campaign["runtime_size"],
        expected_sha256=campaign["runtime_sha256"],
    )
    wrapper = stable_bytes(
        paths["wrapper"], label=f"{campaign['name']} materialized runtime wrapper",
        maximum=1 << 20, expected_size=campaign["wrapper_size"],
        expected_sha256=campaign["wrapper_sha256"],
    )
    userspace = stable_bytes(
        paths["userspace"], label=f"{campaign['name']} userspace receipt",
        maximum=3 << 20, expected_size=campaign["userspace_size"],
        expected_sha256=campaign["userspace_sha256"],
    )
    candidate_a = stable_bytes(
        paths["candidate_a"], label=f"{campaign['name']} candidate A receipt",
        maximum=5 << 20, expected_size=campaign["artifact_size"],
        expected_sha256=campaign["artifact_sha256"],
    )
    candidate_b = stable_bytes(
        paths["candidate_b"], label=f"{campaign['name']} candidate B receipt",
        maximum=5 << 20, expected_size=campaign["artifact_size"],
        expected_sha256=campaign["artifact_sha256"],
    )
    if candidate_a != candidate_b:
        raise SweepError(f"{campaign['name']} candidate A/B receipts differ")

    plan_audit = audit_plan_runtime(plan, runtime, wrapper, campaign)
    plan_identity = identity(plan)
    runtime_identity = identity(runtime)
    wrapper_identity = identity(wrapper)
    userspace_identity = identity(userspace)
    package_audit = audit_package_chain(
        userspace,
        candidate_a,
        campaign=campaign,
        plan_identity=plan_identity,
        runtime_identity=runtime_identity,
        wrapper_identity=wrapper_identity,
        userspace_identity=userspace_identity,
    )

    expected_inventory = {RUNS / value for value in campaign["observer_inventory"]}
    actual_inventory: set[Path] = set()
    for run_dir in campaign["run_dirs"]:
        actual_inventory.update((RUNS / run_dir).glob("**/*observer*.bin"))
    if actual_inventory != expected_inventory:
        raise SweepError(f"{campaign['name']} retained observer inventory differs")
    inventory_receipts = []
    for path in sorted(actual_inventory):
        payload = stable_bytes(path, label=f"{campaign['name']} observer raw", maximum=2_097_136)
        inventory_receipts.append({
            "path": str(path.relative_to(ROOT)),
            **identity(payload),
        })

    final_run = RUNS / campaign["final_run"]
    live_result = stable_bytes(
        final_run / "live-result.json",
        label=f"{campaign['name']} live result",
        maximum=1 << 20,
        expected_size=campaign["live_result_size"],
        expected_sha256=campaign["live_result_sha256"],
    )
    live_attribution = audit_live_result_attribution(
        live_result,
        campaign=campaign,
        final_run=final_run,
    )
    final_reads = tuple(
        stable_bytes(
            final_run / f"rollback-observer-{index}.bin",
            label=f"{campaign['name']} final retained read {index}",
            maximum=2_097_136,
            expected_size=2_097_136,
            expected_sha256=campaign["raw_sha256"],
        )
        for index in (1, 2)
    )
    if final_reads[0] != final_reads[1]:
        raise SweepError(f"{campaign['name']} final retained reads differ")
    records = decode_structural_records(final_reads[0])
    expected_records = campaign["records"]
    comparable = tuple(
        (row["offset"], tuple(row["slots"][0]["fields"]), tuple(row["slots"][1]["fields"]))
        for row in records
    )
    if comparable != expected_records:
        raise SweepError(f"{campaign['name']} retained Carrier tuple differs")
    return {
        "campaign": campaign["name"],
        "materialized_plan": identity(plan),
        "materialized_runtime": identity(runtime),
        "materialized_runtime_wrapper": identity(wrapper),
        "userspace_receipt": identity(userspace),
        "candidate_receipt_ab": identity(candidate_a),
        "candidate_receipt_ab_byte_identical": True,
        **plan_audit,
        **package_audit,
        "observer_file_count": len(inventory_receipts),
        "observer_inventory": inventory_receipts,
        "live_result": identity(live_result),
        **live_attribution,
        "final_reads_byte_identical": True,
        "final_read_identity": identity(final_reads[0]),
        "carrier_records": records,
        "prior_semantic_history": campaign["prior_semantic"],
    }


def _crc32(payload: bytes) -> int:
    return binascii.crc32(payload) & 0xFFFFFFFF


def decode_structural_records(payload: bytes) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    position = 0
    while True:
        position = payload.find(LONG_FAMILY, position)
        if position < 0:
            break
        raw = payload[position : position + RECORD_SIZE]
        if len(raw) != RECORD_SIZE:
            raise SweepError("truncated Carrier-v2 record")
        header = raw[:HEADER_SIZE]
        family, format_profile, header_size, record_size, run_id, header_crc = HEADER.unpack(header)
        if (
            family != LONG_FAMILY
            or format_profile != 0x23
            or header_size != HEADER_SIZE
            or record_size != RECORD_SIZE
            or run_id != RUN_ID
            or header_crc == 0
            or header_crc != _crc32(HEADER_CRC_DOMAIN + header[:-4])
        ):
            raise SweepError("Carrier-v2 header differs")
        slots = []
        for slot_id in (0, 1):
            slot_raw = raw[
                HEADER_SIZE + slot_id * SLOT_SIZE : HEADER_SIZE + (slot_id + 1) * SLOT_SIZE
            ]
            body, encoded_crc = slot_raw[:-4], slot_raw[-4:]
            recorded_crc = int.from_bytes(encoded_crc, "little")
            expected_crc = _crc32(SLOT_CRC_DOMAIN + header + bytes([slot_id]) + body)
            fields = SLOT_BODY.unpack(body)
            generation, stage, outcome, item, kind, length, reserved, detail, padded = fields
            if (
                recorded_crc == 0
                or recorded_crc != expected_crc
                or generation % 2 != slot_id
                or kind not in (0, 1)
                or length > 64
                or reserved != 0
                or any(padded[length:])
            ):
                raise SweepError("Carrier-v2 structurally valid slot differs")
            slots.append({
                "slot_id": slot_id,
                "crc_valid": True,
                "fields": [generation, stage, outcome, item, kind, length, reserved, detail],
                "payload_sha256": sha256(padded[:length]),
            })
        records.append({"offset": position, "header_crc_valid": True, "slots": slots})
        position += 1
    if any(family in payload for family in (UNSAT_FAMILY, *LEGACY_FAMILIES)):
        raise SweepError("retained final read contains a foreign Carrier family")
    return records


def _reports() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for campaign, (relative, snippets) in REPORTS.items():
        path = ROOT / relative
        payload = stable_bytes(path, label=f"{campaign} reviewed report", maximum=1 << 20)
        text = payload.decode("utf-8")
        if any(snippet not in text for snippet in snippets):
            raise SweepError(f"{campaign} reviewed semantic history differs")
        result[campaign] = {"path": relative, **identity(payload)}
    return result


def build_receipt() -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise SweepError("historical EUD sweep requires bound-source execution")
    if stable_bytes(AUDITOR, label="bound historical EUD sweep", maximum=1 << 20) != _BOUND_AUDITOR_SOURCE:
        raise SweepError("executed historical EUD sweep differs from receipt source")
    campaigns = [_read_campaign(campaign) for campaign in CAMPAIGNS]
    p317_config = CAMPAIGNS[-2]
    p318_config = CAMPAIGNS[-1]
    p317_plan = stable_bytes(
        _campaign_paths(p317_config)["plan"],
        label="P3.17 cross-campaign module plan",
        maximum=8192,
        expected_size=p317_config["plan_size"],
        expected_sha256=p317_config["plan_sha256"],
    )
    p318_plan = stable_bytes(
        _campaign_paths(p318_config)["plan"],
        label="P3.18 cross-campaign module plan",
        maximum=8192,
        expected_size=p318_config["plan_size"],
        expected_sha256=p318_config["plan_sha256"],
    )
    plan_delta = audit_p317_p318_plan_delta(p317_plan, p318_plan)
    reports = _reports()
    historical = campaigns[:-1]
    p318 = campaigns[-1]
    if (
        sum(row["index_matches"] for row in historical) != 5
        or p318["index_matches"] is not False
        or p318["eud_index"] != 38
        or p318["cache_trigger_index"] != 37
    ):
        raise SweepError("historical EUD-index partition differs")
    receipt = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "auditor": identity(_BOUND_AUDITOR_SOURCE),
        "campaigns": campaigns,
        "p317_to_p318_plan_delta": plan_delta,
        "reviewed_semantic_reports": reports,
        "conclusion": {
            "historical_campaigns_checked": 5,
            "historical_index_matches": 5,
            "p318_only_index_mismatch": True,
            "p318_latch_insertion_shifted_eud_37_to_38": True,
            "p310_eud_index_correction_required": False,
            "p311_eud_index_correction_required": False,
            "p313_eud_index_correction_required": False,
            "p314_eud_index_correction_required": False,
            "p317_eud_index_correction_required": False,
            "known_prior_reviewed_semantic_mismatch_campaigns": [
                "p311", "p313", "p318"
            ],
            "known_prior_reviewed_semantic_mismatch_cases": 3,
            "known_prior_reviewed_semantic_mismatch_successes": 3,
            "frozen_decoder_exposed_bad_body_cases": 2,
            "frozen_decoder_exposed_bad_body_successes": 2,
            "p310_p314_p317_cross_version_agreement_audited": False,
            "separate_cross_version_audit_required": True,
            "p313_effective_class_remains": "NO_PROOF_OBSERVER",
            "p313_campaign_proof_correction_required": False,
            "diagnostic_bearing_yield_is_proof_class_metric": True,
            "diagnostic_bearing_yield_counts_p313_localization": False,
            "new_campaign_reclassifications": 0,
            "future_ordinal_trigger_requires_identity_binding": True,
        },
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
    }
    if stable_bytes(AUDITOR, label="post-run historical EUD sweep", maximum=1 << 20) != _BOUND_AUDITOR_SOURCE:
        raise SweepError("historical EUD sweep changed during execution")
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
            raise SweepError("historical EUD receipt write did not progress")
        offset += amount


def write_receipt(value: dict[str, Any]) -> None:
    payload = encode_receipt(value)
    OUTPUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if OUTPUT.exists() or OUTPUT.is_symlink():
        existing = stable_bytes(
            OUTPUT, label="historical EUD sweep receipt", maximum=1 << 20,
            expected_size=len(payload), expected_sha256=sha256(payload),
            required_mode=0o400, required_nlink=1,
        )
        if existing != payload:
            raise SweepError("historical EUD sweep receipt differs")
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
            raise SweepError("historical EUD sweep receipt publication differs")
    finally:
        os.close(fd)
    directory = os.open(OUTPUT.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    stable_bytes(
        OUTPUT, label="historical EUD sweep receipt", maximum=1 << 20,
        expected_size=len(payload), expected_sha256=sha256(payload),
        required_mode=0o400, required_nlink=1,
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
