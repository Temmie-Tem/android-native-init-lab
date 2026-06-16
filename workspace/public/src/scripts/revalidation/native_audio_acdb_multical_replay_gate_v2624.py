#!/usr/bin/env python3
"""V2624 host-only ACDB multi-cal replay gate builder.

Consumes the private V2622 Gate-2 VOL-status manifest plus the operator-verified
V2547 topology payload and emits a private, non-executable replay-staging
manifest.  It deliberately does not authorize or run native replay: the current
V2474/V2549 helper is topology-only, and Gate-2 has not accepted the VOL-negative
per-device set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2624"
BUILD_TAG = "v2624-audio-acdb-multical-replay-gate"
TOPOLOGY_SHA256 = "7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89"
TOPOLOGY_LEN = 4916
DEFAULT_TOPOLOGY_PAYLOAD = ROOT / "workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin"
DEFAULT_AUDIO_RUNS = ROOT / "workspace/private/runs/audio"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_PRIVATE_MANIFEST = DEFAULT_BUILD_ROOT / "multical-replay-gate-manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2624_AUDIO_ACDB_MULTICAL_REPLAY_GATE_2026-06-16.md"

CATEGORY_TO_CAL_HINT = {
    "AUDPROC_COMMON_CANDIDATE": {"proposed_cal_type": 11, "name": "ADM_AUDPROC_CAL_TYPE"},
    "AUDPROC_STREAM_CANDIDATE": {"proposed_cal_type": 15, "name": "ASM_AUDSTRM_CAL_TYPE"},
    "AFE_COMMON_CANDIDATE": {"proposed_cal_type": 16, "name": "AFE_COMMON_RX_CAL_TYPE"},
}


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT.resolve()))
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


def write_json(path: Path, payload: dict[str, Any], mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_v2622_manifest(audio_runs: Path = DEFAULT_AUDIO_RUNS) -> Path:
    candidates = sorted(audio_runs.glob("v2621-acdb-vol-isolated-*/v2622-acdb-gate2-vol-status-manifest.json"))
    if not candidates:
        raise FileNotFoundError(f"no V2622 Gate-2 VOL-status manifest under {rel(audio_runs)}")
    return candidates[-1]


def zero_sha256(length: int) -> str:
    return sha256_bytes(b"\x00" * max(0, length))


def payload_state(path: Path, *, expected_len: int | None = None, expected_sha256: str | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {"path_private": rel(path), "exists": path.exists(), "private_only": True}
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
    state.update({
        "ok": all(checks.values()),
        "reason": "ok" if all(checks.values()) else "payload-validation-failed",
        "size": length,
        "sha256": digest,
        "expected_len": expected_len,
        "expected_sha256": expected_sha256,
        "all_zero": all_zero,
        "zero_sha256": zero_sha256(length),
        "checks": checks,
    })
    return state


def topology_entry(topology_payload: Path) -> dict[str, Any]:
    state = payload_state(topology_payload, expected_len=TOPOLOGY_LEN, expected_sha256=TOPOLOGY_SHA256)
    return {
        "order": 0,
        "kind": "topology",
        "category": "CORE_CUSTOM_TOPOLOGIES",
        "cal_type": 39,
        "cal_type_name": "CORE_CUSTOM_TOPOLOGIES_CAL_TYPE",
        "buffer_number": 0,
        "source": "V2547 operator-verified topology payload",
        "gate2_status": "operator-verified",
        "raw": state,
        "ok": state.get("ok") is True,
    }


def candidate_entry(candidate: dict[str, Any]) -> dict[str, Any]:
    category = str(candidate.get("category") or "")
    hint = CATEGORY_TO_CAL_HINT.get(category, {})
    return {
        "order": candidate.get("order"),
        "kind": "per_device_candidate",
        "category": category,
        "cmd": candidate.get("cmd"),
        "seq": candidate.get("seq"),
        "buffer": candidate.get("buffer"),
        "proposed_cal_type": hint.get("proposed_cal_type"),
        "proposed_cal_type_name": hint.get("name"),
        "operator_mapping_required": True,
        "gate2_status": "pending-operator-mapping",
        "raw": {
            "path_private": candidate.get("raw_path_private"),
            "size": candidate.get("raw_size") or candidate.get("out_len"),
            "sha256": candidate.get("sha256"),
            "nonzero": candidate.get("nonzero"),
            "hash_matches_event": candidate.get("hash_matches_event"),
            "verified_for_gate2_handoff": candidate.get("verified_for_gate2"),
            "private_only": True,
        },
        "ok": bool(candidate.get("verified_for_gate2") and candidate.get("nonzero") and candidate.get("sha256")),
    }


def redacted_entry(entry: dict[str, Any]) -> dict[str, Any]:
    raw = dict(entry.get("raw") or {})
    raw.pop("path_private", None)
    return {key: value for key, value in entry.items() if key != "raw"} | {"raw": raw}


def helper_gap_state() -> dict[str, Any]:
    helper = ROOT / "workspace/public/src/native-init/helpers/a90_acdb_replay_scaffold_v2474.c"
    text = helper.read_text(encoding="utf-8", errors="replace") if helper.exists() else ""
    single_topology_only = all(token in text for token in [
        "A90_CORE_CUSTOM_TOPOLOGIES_CAL_TYPE",
        "A90_EXPECTED_TOPOLOGY_PAYLOAD_LEN",
        "fill_cal_packet",
    ]) and "manifest" not in text.lower()
    return {
        "source": rel(helper),
        "exists": helper.exists(),
        "current_helper_single_topology_only": single_topology_only,
        "required_future_delta": [
            "read a private ordered multi-cal manifest",
            "allocate one dma-buf per replay entry and keep fds open across the PCM probe",
            "issue AUDIO_ALLOCATE_CALIBRATION/AUDIO_SET_CALIBRATION for each Gate-2 accepted entry",
            "deallocate in reverse order and close all fds on every exit path",
        ],
    }


def build_gate_manifest(
    v2622_manifest_path: Path,
    topology_payload: Path,
    *,
    operator_gate2_accepted: bool = False,
    operator_accept_vol_negative: bool = False,
) -> dict[str, Any]:
    v2622 = read_json(v2622_manifest_path)
    topology = topology_entry(topology_payload)
    candidates = [candidate_entry(candidate) for candidate in v2622.get("payload_candidates", [])]
    verified_candidates = [entry for entry in candidates if entry.get("ok")]
    vol_status = v2622.get("vol_status", {}) if isinstance(v2622.get("vol_status"), dict) else {}
    vol_negative_pinned = bool(vol_status.get("vol_direct_get_exhausted_for_current_tuple"))
    helper_gap = helper_gap_state()
    gate2_accepted_for_manifest = bool(
        operator_gate2_accepted
        and operator_accept_vol_negative
        and v2622.get("ok")
        and topology.get("ok")
        and len(verified_candidates) == len(candidates) == 3
        and vol_negative_pinned
    )
    blockers: list[str] = []
    if not operator_gate2_accepted:
        blockers.append("operator Gate-2 has not accepted the per-device AUDPROC/AFE candidate mapping")
    if not operator_accept_vol_negative:
        blockers.append("operator has not accepted the VOL-negative replay boundary")
    if not topology.get("ok"):
        blockers.append("topology payload validation failed")
    if len(verified_candidates) != len(candidates) or len(candidates) != 3:
        blockers.append("expected three verified AUDPROC/AFE candidates")
    if not vol_negative_pinned:
        blockers.append("VOL-negative status is not pinned")
    if helper_gap.get("current_helper_single_topology_only"):
        blockers.append("current native replay helper is topology-only and must be extended before live replay")

    payload = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "source_v2622_manifest": rel(v2622_manifest_path),
        "source_v2622_decision": v2622.get("summary", {}).get("vol_status_source_decision") or v2622.get("source_gate2_run_id"),
        "operator_gate2_accepted": operator_gate2_accepted,
        "operator_accept_vol_negative": operator_accept_vol_negative,
        "gate2_accepted_for_manifest": gate2_accepted_for_manifest,
        "native_replay_ready": False,
        "safe_to_run_native_replay": False,
        "replay_blockers": blockers,
        "topology": topology,
        "per_device_candidates": candidates,
        "vol_status": {
            "source_decision": vol_status.get("source_decision"),
            "classification": vol_status.get("classification"),
            "vol_direct_get_exhausted_for_current_tuple": vol_negative_pinned,
            "vol_payload_count": vol_status.get("vol_payload_count"),
            "vol_size_ret_values": vol_status.get("vol_size_ret_values"),
            "vol_data_ret_values": vol_status.get("vol_data_ret_values"),
            "operator_acceptance_required": True,
        },
        "helper_gap": helper_gap,
        "redacted_public": {
            "topology": redacted_entry(topology),
            "per_device_candidates": [redacted_entry(entry) for entry in candidates],
        },
        "next_gate_phrase": "operator-gate2-accepts-v2622-vol-negative-manifest-and-authorizes-v2624-helper-extension",
        "ok": bool(v2622.get("ok") and topology.get("ok") and len(verified_candidates) == 3 and vol_negative_pinned),
    }
    return payload


def write_report(path: Path, manifest: dict[str, Any], private_manifest_path: Path) -> None:
    redacted = manifest.get("redacted_public", {})
    topology = redacted.get("topology", {})
    candidates = redacted.get("per_device_candidates", [])
    vol = manifest.get("vol_status", {})
    lines = [
        "# NATIVE_INIT V2624 — ACDB multi-cal replay gate",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only replay-gate manifest after V2622/V2623. This unit creates a private",
        "ordered staging manifest for the already verified topology payload plus the three",
        "AUDPROC/AFE per-device candidates, but it does not run native replay, copy raw",
        "payload bytes to tracked paths, or mark the device ready for replay.",
        "",
        "## Result",
        "",
        f"- decision: `v2624-multical-replay-gate-{'ready-for-operator' if manifest.get('ok') else 'needs-review'}`",
        f"- ok: `{manifest.get('ok')}`",
        f"- private_manifest: `{rel(private_manifest_path)}`",
        f"- gate2_accepted_for_manifest: `{manifest.get('gate2_accepted_for_manifest')}`",
        f"- native_replay_ready: `{manifest.get('native_replay_ready')}`",
        f"- safe_to_run_native_replay: `{manifest.get('safe_to_run_native_replay')}`",
        f"- source_v2622_manifest: `{manifest.get('source_v2622_manifest')}`",
        "",
        "## Replay Entries",
        "",
        "| entry | category | cal hint | bytes | sha256 | gate |",
        "| --- | --- | --- | ---: | --- | --- |",
        f"| topology | `{topology.get('category')}` | `{topology.get('cal_type')}` | {topology.get('raw', {}).get('size')} | `{topology.get('raw', {}).get('sha256')}` | `{topology.get('gate2_status')}` |",
    ]
    for item in candidates:
        raw = item.get("raw", {})
        cal_hint = item.get("proposed_cal_type")
        lines.append(
            f"| per-device | `{item.get('category')}` | `{cal_hint}` | {raw.get('size')} | "
            f"`{raw.get('sha256')}` | `{item.get('gate2_status')}` |"
        )
    lines.extend([
        "",
        "## VOL Boundary",
        "",
        f"- classification: `{vol.get('classification')}`",
        f"- vol_direct_get_exhausted_for_current_tuple: `{vol.get('vol_direct_get_exhausted_for_current_tuple')}`",
        f"- vol_payload_count: `{vol.get('vol_payload_count')}`",
        f"- vol_size_ret_values: `{vol.get('vol_size_ret_values')}`",
        f"- vol_data_ret_values: `{vol.get('vol_data_ret_values')}`",
        "- replay without VOL remains blocked until the operator explicitly accepts this negative boundary.",
        "",
        "## Hard Blockers",
        "",
    ])
    for blocker in manifest.get("replay_blockers", []):
        lines.append(f"- {blocker}")
    lines.extend([
        "",
        "## Helper Gap",
        "",
        f"- current_helper_single_topology_only: `{manifest.get('helper_gap', {}).get('current_helper_single_topology_only')}`",
        "- Required future helper delta: ordered multi-cal manifest parsing, one dma-buf per entry, keep fds open across PCM probe, reverse deallocate cleanup.",
        "",
        "## Boundary",
        "",
        "- This is **not** a live replay approval and not an executable replay run.",
        "- Public report contains only size/SHA/category metadata; raw paths stay in the private manifest only.",
        "- Native replay stays blocked until operator Gate-2 accepts the per-device mapping and VOL-negative status, then a separate helper-extension/build unit lands.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_multical_replay_gate_v2624.py tests/test_native_audio_acdb_multical_replay_gate_v2624.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_multical_replay_gate_v2624 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_multical_replay_gate_v2624.py --write-report`",
        "- `git diff --check`",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-runs", type=Path, default=DEFAULT_AUDIO_RUNS)
    parser.add_argument("--v2622-manifest", type=Path)
    parser.add_argument("--topology-payload", type=Path, default=DEFAULT_TOPOLOGY_PAYLOAD)
    parser.add_argument("--private-manifest-path", type=Path, default=DEFAULT_PRIVATE_MANIFEST)
    parser.add_argument("--operator-gate2-accepted", action="store_true")
    parser.add_argument("--operator-accept-vol-negative", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    v2622_manifest = args.v2622_manifest or latest_v2622_manifest(args.audio_runs)
    if not v2622_manifest.is_absolute():
        v2622_manifest = ROOT / v2622_manifest
    topology_payload = args.topology_payload if args.topology_payload.is_absolute() else ROOT / args.topology_payload
    private_manifest = args.private_manifest_path if args.private_manifest_path.is_absolute() else ROOT / args.private_manifest_path
    report_path = args.report_path if args.report_path.is_absolute() else ROOT / args.report_path
    manifest = build_gate_manifest(
        v2622_manifest,
        topology_payload,
        operator_gate2_accepted=args.operator_gate2_accepted,
        operator_accept_vol_negative=args.operator_accept_vol_negative,
    )
    write_json(private_manifest, manifest, mode=0o600)
    if args.write_report:
        write_report(report_path, manifest, private_manifest)
    summary = {
        "decision": f"v2624-multical-replay-gate-{'ready-for-operator' if manifest.get('ok') else 'needs-review'}",
        "ok": manifest.get("ok"),
        "private_manifest": rel(private_manifest),
        "gate2_accepted_for_manifest": manifest.get("gate2_accepted_for_manifest"),
        "native_replay_ready": manifest.get("native_replay_ready"),
        "safe_to_run_native_replay": manifest.get("safe_to_run_native_replay"),
        "blocker_count": len(manifest.get("replay_blockers", [])),
    }
    if args.json:
        public = dict(manifest)
        public["topology"] = redacted_entry(manifest["topology"])
        public["per_device_candidates"] = [redacted_entry(entry) for entry in manifest["per_device_candidates"]]
        print(json.dumps(public, indent=2, sort_keys=True))
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if manifest.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
