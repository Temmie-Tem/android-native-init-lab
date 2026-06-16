#!/usr/bin/env python3
"""V2615 host-only ACDB per-device replay-manifest candidate builder.

Consumes the private V2614 own-process ACDB capture and emits a private manifest
candidate containing only metadata, paths, sizes and SHA-256 digests.  It does
not copy or print raw ACDB bytes, does not touch a device, and does not authorize
native replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2615"
BUILD_TAG = "v2615-audio-acdb-perdevice-manifest-candidate"
RUNS_ROOT = ROOT / "workspace/private/runs/audio"
DEFAULT_TOPOLOGY_PAYLOAD = ROOT / "workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2615_AUDIO_ACDB_PERDEVICE_MANIFEST_CANDIDATE_2026-06-16.md"
ZERO_SHA256_BY_LEN = {
    0: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}


@dataclass(frozen=True)
class ExpectedCapture:
    buffer: str
    command: str
    candidate_cal_type: int
    candidate_name: str
    reason: str


EXPECTED_CAPTURES: tuple[ExpectedCapture, ...] = (
    ExpectedCapture(
        buffer="ind-ap-common",
        command="0x00013265",
        candidate_cal_type=11,
        candidate_name="ADM_AUDPROC_CAL_TYPE",
        reason="V2614 AUDPROC instance common table; Android-good logs show AUDIO_SET_AUDPROC_CAL cal_type[11]",
    ),
    ExpectedCapture(
        buffer="ind-ap-stream",
        command="0x00013269",
        candidate_cal_type=15,
        candidate_name="ASM_AUDSTRM_CAL_TYPE",
        reason="V2614 AUDPROC stream table; V2393 showed q6asm_send_cal cal_block NULL on prepare",
    ),
    ExpectedCapture(
        buffer="ind-afe-common",
        command="0x0001326f",
        candidate_cal_type=16,
        candidate_name="AFE_COMMON_RX_CAL_TYPE",
        reason="V2614 AFE instance common table; Android-good logs show AUDIO_SET_AFE_CAL cal_type[16]",
    ),
)


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def latest_v2614_run(runs_root: Path = RUNS_ROOT) -> Path | None:
    candidates = sorted(runs_root.glob("v2614-acdb-meta-list-indirect-layout-live-*"))
    return candidates[-1] if candidates else None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def zero_sha256(length: int) -> str:
    if length not in ZERO_SHA256_BY_LEN:
        ZERO_SHA256_BY_LEN[length] = sha256_bytes(b"\x00" * length)
    return ZERO_SHA256_BY_LEN[length]


def payload_file_state(path: Path, *, expected_len: int | None = None, expected_sha256: str | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "private_only": True,
    }
    if not path.exists():
        state.update({"ok": False, "reason": "missing"})
        return state
    data = path.read_bytes()
    digest = sha256_bytes(data)
    length = len(data)
    all_zero = all(byte == 0 for byte in data)
    checks = {
        "length_matches": expected_len is None or length == expected_len,
        "sha256_matches": expected_sha256 is None or digest == expected_sha256,
        "not_all_zero": not all_zero,
        "not_zero_sha256": digest != zero_sha256(length),
    }
    state.update(
        {
            "ok": all(checks.values()),
            "reason": "ok" if all(checks.values()) else "payload-validation-failed",
            "size": length,
            "sha256": digest,
            "expected_len": expected_len,
            "expected_sha256": expected_sha256,
            "zero_sha256": zero_sha256(length),
            "all_zero": all_zero,
            "checks": checks,
        }
    )
    return state


def local_raw_path(run_dir: Path, row: dict[str, Any]) -> Path:
    raw_path_value = str(row.get("raw_path") or "")
    raw_name = Path(raw_path_value).name
    return run_dir / "ownget-device-artifacts" / "acdbtap" / raw_name


def candidate_from_row(run_dir: Path, row: dict[str, Any], expected: ExpectedCapture) -> dict[str, Any]:
    length = parse_int(row.get("out_len"))
    ret = parse_int(row.get("ret"))
    raw_path = local_raw_path(run_dir, row)
    raw = payload_file_state(raw_path, expected_len=length, expected_sha256=str(row.get("sha256") or ""))
    row_all_zero = row.get("all_zero")
    checks = {
        "buffer_matches": row.get("buffer") == expected.buffer,
        "command_matches": str(row.get("cmd")) == expected.command,
        "ret_zero": ret == 0,
        "row_not_all_zero": row_all_zero is False or row_all_zero == "False" or row_all_zero == "false",
        "length_positive": bool(length and length > 0),
        "raw_ok": raw.get("ok") is True,
    }
    return {
        "buffer": expected.buffer,
        "command": expected.command,
        "candidate_cal_type": expected.candidate_cal_type,
        "candidate_name": expected.candidate_name,
        "reason": expected.reason,
        "row": {
            "seq": row.get("seq"),
            "cmd": row.get("cmd"),
            "buffer": row.get("buffer"),
            "out_len": row.get("out_len"),
            "ret": row.get("ret"),
            "all_zero": row.get("all_zero"),
            "sha256": row.get("sha256"),
        },
        "raw": raw,
        "checks": checks,
        "ok": all(checks.values()),
    }


def v2614_capture_state(run_dir: Path) -> dict[str, Any]:
    result_path = run_dir / "result.json"
    if not result_path.exists():
        return {"ok": False, "reason": "missing-result-json", "run_dir": rel(run_dir)}
    result = load_json(result_path)
    summary = result.get("ownget_summary", {}) if isinstance(result.get("ownget_summary"), dict) else {}
    rows = summary.get("acdbtap_rows", []) if isinstance(summary.get("acdbtap_rows"), list) else []
    found: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("buffer"), str):
            found.setdefault(row["buffer"], row)

    entries = []
    missing = []
    for expected in EXPECTED_CAPTURES:
        row = found.get(expected.buffer)
        if row is None:
            missing.append(expected.buffer)
            entries.append(
                {
                    "buffer": expected.buffer,
                    "command": expected.command,
                    "candidate_cal_type": expected.candidate_cal_type,
                    "candidate_name": expected.candidate_name,
                    "ok": False,
                    "reason": "missing-row",
                }
            )
        else:
            entries.append(candidate_from_row(run_dir, row, expected))

    checks = {
        "runner_ok": result.get("ok") is True,
        "partial_success": result.get("partial_success") is True,
        "counts_toward_fails_twice_false": result.get("counts_toward_fails_twice") is False,
        "rolled_back": result.get("rolled_back") is True,
        "target_4916_absent": result.get("target_4916_success") is False,
        "all_expected_entries_ok": all(entry.get("ok") for entry in entries),
    }
    return {
        "ok": all(checks.values()),
        "reason": "ok" if all(checks.values()) else "capture-validation-failed",
        "run_dir": rel(run_dir),
        "result_path": rel(result_path),
        "decision": result.get("decision"),
        "checks": checks,
        "missing_buffers": missing,
        "entries": entries,
        "row_count": summary.get("acdbtap_row_count"),
        "raw_file_count": summary.get("acdbtap_raw_file_count"),
    }


def topology_state(path: Path) -> dict[str, Any]:
    state = payload_file_state(path, expected_len=4916)
    state.update(
        {
            "candidate_cal_type": 39,
            "candidate_name": "CORE_CUSTOM_TOPOLOGIES_CAL_TYPE",
            "source": "V2547 operator-verified topology payload in workspace/private inputs",
        }
    )
    return state


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.run_dir or latest_v2614_run()
    if run_dir is None:
        payload = {
            "run_id": RUN_ID,
            "build_tag": BUILD_TAG,
            "created_at": now_iso(),
            "ok": False,
            "decision": "v2615-blocked-no-v2614-run",
            "reason": "no V2614 private run found",
        }
    else:
        capture = v2614_capture_state(run_dir)
        topology = topology_state(args.topology_payload)
        replay_inputs = {
            "topology": topology,
            "per_device": capture.get("entries", []),
        }
        required_operator_items = [
            "verify candidate cal_type mapping from command order and V2461/V2462 AUDIO_SET sequence",
            "decide whether missing VOL cal_type 12 is required for speaker prepare",
            "decide whether AFE cal_type 8/9 topology ids require separate payload replay or are covered by topology/common tables",
            "pin native replay ordering and mem_handle lifetime before any live SET",
        ]
        complete_payload_set = bool(capture.get("ok") and topology.get("ok"))
        payload = {
            "run_id": RUN_ID,
            "build_tag": BUILD_TAG,
            "created_at": now_iso(),
            "ok": complete_payload_set,
            "decision": (
                "v2615-perdevice-manifest-candidate-ready-for-operator-verification"
                if complete_payload_set
                else "v2615-perdevice-manifest-candidate-incomplete"
            ),
            "host_only": True,
            "device_action": "none",
            "raw_bytes_private_only": True,
            "no_raw_payload_committed": True,
            "native_replay_ready": False,
            "native_replay_blocked_reason": "operator mapping, replay order, mem_handle policy, and cleanup semantics are not pinned",
            "capture": capture,
            "replay_inputs": replay_inputs,
            "candidate_sequence": [
                {"candidate_cal_type": 39, "candidate_name": "CORE_CUSTOM_TOPOLOGIES_CAL_TYPE", "source": "topology"},
                {"candidate_cal_type": 11, "candidate_name": "ADM_AUDPROC_CAL_TYPE", "source": "ind-ap-common"},
                {"candidate_cal_type": 15, "candidate_name": "ASM_AUDSTRM_CAL_TYPE", "source": "ind-ap-stream"},
                {"candidate_cal_type": 16, "candidate_name": "AFE_COMMON_RX_CAL_TYPE", "source": "ind-afe-common"},
            ],
            "known_gaps": {
                "vol_cal_type_12": "V2614 gain/VOL commands returned -19 and no non-zero payload",
                "afe_topology_types_8_9": "V2393 dmesg mentions AFE cal types 8/9 not initialized; V2614 captured AFE common cal_type 16 only",
                "operator_gate2_required": True,
            },
            "required_operator_verification": required_operator_items,
            "manifest_path": rel(args.manifest_path),
        }
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def report_lines(payload: dict[str, Any]) -> list[str]:
    capture = payload.get("capture", {}) if isinstance(payload.get("capture"), dict) else {}
    replay_inputs = payload.get("replay_inputs", {}) if isinstance(payload.get("replay_inputs"), dict) else {}
    per_device = replay_inputs.get("per_device", []) if isinstance(replay_inputs.get("per_device"), list) else []
    topology = replay_inputs.get("topology", {}) if isinstance(replay_inputs.get("topology"), dict) else {}
    lines = [
        "# NATIVE_INIT V2615 — ACDB per-device replay manifest candidate",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only reconciliation after V2614. The script reads private ACDB payload files only to",
        "validate size/SHA/non-zero properties and writes a private manifest candidate. It does not",
        "copy raw bytes into public files, touch the device, issue native calibration `SET`, or mark",
        "native replay ready.",
        "",
        "## Decision",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- native_replay_ready: `{payload.get('native_replay_ready')}`",
        f"- native_replay_blocked_reason: `{payload.get('native_replay_blocked_reason')}`",
        f"- private_manifest: `{payload.get('manifest_path')}`",
        f"- source_run: `{capture.get('run_dir')}`",
        "",
        "## Candidate Payloads",
        "",
        "| source | candidate cal_type | bytes | sha256 | ok |",
        "| --- | ---: | ---: | --- | --- |",
        f"| topology | 39 | {topology.get('size')} | `{topology.get('sha256')}` | `{topology.get('ok')}` |",
    ]
    for entry in per_device:
        raw = entry.get("raw", {}) if isinstance(entry.get("raw"), dict) else {}
        lines.append(
            f"| {entry.get('buffer')} | {entry.get('candidate_cal_type')} | {raw.get('size')} | `{raw.get('sha256')}` | `{entry.get('ok')}` |"
        )
    lines.extend(
        [
            "",
            "## Validation Summary",
            "",
            f"- v2614_capture_ok: `{capture.get('ok')}`",
            f"- v2614_checks: `{capture.get('checks')}`",
            f"- row_count: `{capture.get('row_count')}`",
            f"- raw_file_count: `{capture.get('raw_file_count')}`",
            "- every per-device entry requires `ret==0`, non-zero row, matching raw file size, and matching SHA-256.",
            "- topology payload is the private V2547 4916-byte operator-verified file; only metadata is recorded here.",
            "",
            "## Known Gaps / Operator Gate",
            "",
        ]
    )
    gaps = payload.get("known_gaps", {}) if isinstance(payload.get("known_gaps"), dict) else {}
    for key, value in gaps.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "Native replay remains blocked until the operator maps candidate cal types/order against the",
            "V2461/V2462 `AUDIO_SET_CALIBRATION` sequence and pins mem_handle lifetime and cleanup semantics.",
            "",
            "## Validation Commands",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_perdevice_manifest_v2615.py tests/test_analyze_audio_acdb_perdevice_manifest_v2615.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_perdevice_manifest_v2615 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_perdevice_manifest_v2615.py --write-report`",
            "- `git diff --check`",
            "",
        ]
    )
    return lines


def write_report(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(report_lines(payload)), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, help="private V2614 run directory; defaults to latest")
    parser.add_argument("--topology-payload", type=Path, default=DEFAULT_TOPOLOGY_PAYLOAD)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = manifest(args)
    if args.write_report:
        write_report(payload, args.report_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
