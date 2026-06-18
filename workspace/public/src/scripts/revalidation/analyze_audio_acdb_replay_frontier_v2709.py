#!/usr/bin/env python3
"""V2709 host-only frontier audit after V2708 SET replay.

This audit reconciles V2704 captured subsystem topology GET metadata, the V2707
replay manifest shape, and the V2708 live replay result.  It does not read raw
ACDB payload bytes, run a device step, issue calibration ioctls, or modify any
private artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2709"
DEFAULT_V2704_RESULT = ROOT / "workspace/private/runs/audio/v2704-acdb-large-buffer-topology-get-20260618-190151/v2704-result.json"
DEFAULT_V2707_MANIFEST = ROOT / "workspace/private/builds/audio/v2707-audio-acdb-subsystem-topology-entrycap-deploy-plan/deploy-plan.json"
DEFAULT_V2708_RESULT = ROOT / "workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-193253/result.json"
DEFAULT_V2708_DMESG = ROOT / "workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-193253/63_dmesg-after-setcal-playback-failure-before-reset.txt"
DEFAULT_V2708_HELPER_LOG = ROOT / "workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-193253/64_acdb-setcal-helper-deallocate-check.txt"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2709_AUDIO_ACDB_REPLAY_FRONTIER_AUDIT_2026-06-18.md"
TARGET_CAL_TYPES = (24, 10, 14)
TARGET_ROLES = {
    24: "AFE_CUSTOM_TOPOLOGY",
    10: "ADM_CUSTOM_TOPOLOGY",
    14: "ASM_CUSTOM_TOPOLOGY",
}
TARGET_CMDS = {
    24: "0x000130da",
    10: "0x00011394",
    14: "0x00012e01",
}


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(errors="ignore") if path.exists() else ""


def load_v2704_targets(path: Path) -> dict[int, dict[str, Any]]:
    payload = read_json(path)
    summary = payload.get("large_get_summary") if isinstance(payload.get("large_get_summary"), dict) else {}
    rows: dict[int, dict[str, Any]] = {}
    for row in summary.get("target_rows") or []:
        cal_type = row.get("target_cal_type")
        if cal_type not in TARGET_CAL_TYPES:
            continue
        rows[int(cal_type)] = {
            "cal_type": int(cal_type),
            "role": TARGET_ROLES[int(cal_type)],
            "cmd": f"0x{int(row.get('cmd') or 0):08x}" if isinstance(row.get("cmd"), int) else str(row.get("cmd")),
            "ret": row.get("ret"),
            "out_len": row.get("out_len"),
            "sha256": row.get("sha256"),
            "success": bool(row.get("success")),
            "raw_ok": bool((row.get("raw_status") or {}).get("exists") and (row.get("raw_status") or {}).get("nonzero") and (row.get("raw_status") or {}).get("sha_ok") and (row.get("raw_status") or {}).get("size_ok")),
        }
    return rows


def load_manifest_basic_payloads(path: Path) -> dict[int, dict[str, Any]]:
    manifest = read_json(path)
    out: dict[int, dict[str, Any]] = {}
    for entry in manifest.get("replay_entries") or []:
        try:
            cal_type = int(entry.get("cal_type"))
        except (TypeError, ValueError):
            continue
        if cal_type not in TARGET_CAL_TYPES:
            continue
        entry_kind = str(entry.get("entry_kind") or entry.get("kind") or "")
        out[cal_type] = {
            "cal_type": cal_type,
            "role": str(entry.get("role") or TARGET_ROLES[cal_type]),
            "entry_kind": entry_kind,
            "has_payload": bool(entry.get("has_payload")),
            "arg_remote": entry.get("arg_remote"),
            "payload_remote": entry.get("payload_remote"),
            "payload_size": entry.get("payload_size"),
            "payload_sha256": entry.get("payload_sha256"),
            "basic_payload": entry_kind == "basic-payload",
            "exact_set": entry_kind == "exact-set",
        }
    return out


def parse_setcal_log(text: str) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    alloc_re = re.compile(r"A90_ACDB_SETCAL_ALLOCATE_OK index=(\d+) cal_type=(\d+) size=(\d+)")
    set_re = re.compile(r"A90_ACDB_SETCAL_SET_OK index=(\d+) cal_type=(\d+) kind=(\d+) has_payload=(\d+)")
    dealloc_re = re.compile(r"A90_ACDB_SETCAL_DEALLOCATE_OK index=(\d+) cal_type=(\d+)")
    for match in alloc_re.finditer(text):
        index, cal_type, size = map(int, match.groups())
        if cal_type in TARGET_CAL_TYPES:
            out.setdefault(cal_type, {"cal_type": cal_type})
            out[cal_type].update({"index": index, "allocated_size": size, "allocated": True})
    for match in set_re.finditer(text):
        index, cal_type, kind, has_payload = map(int, match.groups())
        if cal_type in TARGET_CAL_TYPES:
            out.setdefault(cal_type, {"cal_type": cal_type})
            out[cal_type].update({"index": index, "set_ok": True, "kind": kind, "has_payload": bool(has_payload)})
    for match in dealloc_re.finditer(text):
        index, cal_type = map(int, match.groups())
        if cal_type in TARGET_CAL_TYPES:
            out.setdefault(cal_type, {"cal_type": cal_type})
            out[cal_type].update({"deallocated": True, "deallocate_index": index})
    return out


def dmesg_markers(text: str) -> dict[str, bool]:
    return {
        "q6asm_error_0x2": "q6asm_callback: cmd = 0x10dbe returned error = 0x2" in text,
        "asm_custom_topology_ebadparam": "send_asm_custom_topology: DSP returned error[ADSP_EBADPARAM]" in text,
        "pcm_open_enomem": "msm_pcm_open: Could not allocate memory" in text,
        "frontend_failed_minus12": "ASoC: failed to start FE -12" in text,
        "afe_timeout_secondary": "AFE" in text and "timeout" in text.lower(),
    }


def classify(v2704: dict[int, dict[str, Any]], manifest: dict[int, dict[str, Any]], replay: dict[int, dict[str, Any]], markers: dict[str, bool], result: dict[str, Any]) -> dict[str, Any]:
    captured_all = all(v2704.get(cal_type, {}).get("success") and v2704.get(cal_type, {}).get("raw_ok") for cal_type in TARGET_CAL_TYPES)
    manifest_basic_all = all(manifest.get(cal_type, {}).get("basic_payload") for cal_type in TARGET_CAL_TYPES)
    set_all_ok = all(replay.get(cal_type, {}).get("set_ok") for cal_type in TARGET_CAL_TYPES)
    dealloc_all = all(replay.get(cal_type, {}).get("deallocated") for cal_type in TARGET_CAL_TYPES)
    live_result = result.get("live") if isinstance(result.get("live"), dict) else {}
    acdb_replay_result = result.get("acdb_setcal_replay") if isinstance(result.get("acdb_setcal_replay"), dict) else {}
    pcm_attempted = (
        bool(result.get("playback_attempted"))
        or bool(live_result.get("playback_attempted"))
        or bool(live_result.get("playback"))
        or bool(acdb_replay_result.get("playback_attempted"))
        or bool(acdb_replay_result.get("playback"))
    )
    asm_rejected = bool(markers.get("asm_custom_topology_ebadparam"))
    replay_mechanism_proven = captured_all and manifest_basic_all and set_all_ok and dealloc_all and pcm_attempted
    get_payload_replay_exhausted = replay_mechanism_proven and asm_rejected
    decision = "v2709-frontier-unknown"
    recommended_next = "inspect-missing-evidence-before-replay"
    if get_payload_replay_exhausted:
        decision = "v2709-get-payload-replay-exhausted-need-byte-exact-topology-set-capture"
        recommended_next = "capture-or-reconstruct-byte-exact-android-good-custom-topology-set-geometry-for-cal10-14-24"
    elif replay_mechanism_proven:
        decision = "v2709-replay-mechanism-proven-dsp-marker-missing"
        recommended_next = "collect-stronger-dmesg-before-new-replay"
    return {
        "decision": decision,
        "recommended_next": recommended_next,
        "captured_all_v2704_targets": captured_all,
        "manifest_uses_basic_payload_for_all_targets": manifest_basic_all,
        "set_all_targets_ok": set_all_ok,
        "deallocated_all_targets": dealloc_all,
        "pcm_attempted": pcm_attempted,
        "asm_rejected_ebadparam": asm_rejected,
        "get_payload_replay_exhausted": get_payload_replay_exhausted,
        "native_replay_should_remain_parked_until_new_capture": get_payload_replay_exhausted,
        "same_manifest_rerun_low_value": get_payload_replay_exhausted,
    }


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    v2704 = load_v2704_targets(args.v2704_result)
    manifest = load_manifest_basic_payloads(args.v2707_manifest)
    result = read_json(args.v2708_result)
    helper_log = read_text(args.v2708_helper_log)
    dmesg = read_text(args.v2708_dmesg)
    replay = parse_setcal_log(helper_log)
    markers = dmesg_markers(dmesg)
    classification = classify(v2704, manifest, replay, markers, result)
    return {
        "run_id": RUN_ID,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": False,
        "raw_payload_read": False,
        "inputs": {
            "v2704_result": rel(args.v2704_result),
            "v2707_manifest": rel(args.v2707_manifest),
            "v2708_result": rel(args.v2708_result),
            "v2708_dmesg": rel(args.v2708_dmesg),
            "v2708_helper_log": rel(args.v2708_helper_log),
        },
        "v2704_targets": {str(k): v for k, v in sorted(v2704.items())},
        "v2707_manifest_targets": {str(k): v for k, v in sorted(manifest.items())},
        "v2708_replay_targets": {str(k): v for k, v in sorted(replay.items())},
        "v2708_dmesg_markers": markers,
        "classification": classification,
        "missing_evidence": missing_evidence(v2704, manifest, replay, markers),
        "next_capture_requirements": next_capture_requirements(),
    }


def missing_evidence(v2704: dict[int, dict[str, Any]], manifest: dict[int, dict[str, Any]], replay: dict[int, dict[str, Any]], markers: dict[str, bool]) -> list[str]:
    missing: list[str] = []
    for cal_type in TARGET_CAL_TYPES:
        if cal_type not in v2704 or not v2704[cal_type].get("success"):
            missing.append(f"V2704 successful GET metadata for cal_type {cal_type}")
        if cal_type not in manifest:
            missing.append(f"V2707 replay manifest target entry for cal_type {cal_type}")
        if cal_type not in replay or not replay[cal_type].get("set_ok"):
            missing.append(f"V2708 SET_OK marker for cal_type {cal_type}")
    if not markers.get("asm_custom_topology_ebadparam"):
        missing.append("V2708 dmesg ASM ADSP_EBADPARAM marker")
    return missing


def next_capture_requirements() -> list[dict[str, Any]]:
    return [
        {
            "requirement": "capture exact Android-good SET event for cal_type 14",
            "why": "V2708 fails at send_asm_custom_topology with ADSP_EBADPARAM after generic cal14 SET succeeds",
            "acceptance": "AUDIO_SET_CALIBRATION arg bytes, payload bytes/SHA, ret, mem_handle lifetime, and dmesg context captured privately; public report only metadata",
        },
        {
            "requirement": "capture exact Android-good SET event for cal_type 10",
            "why": "ADM custom topology is required for topology 0x10004000 and was only replayed from V2704 GET bytes with a generic SET header",
            "acceptance": "byte-exact SET arg + payload with non-zero SHA and replay ordering before stream open",
        },
        {
            "requirement": "capture exact Android-good SET event for cal_type 24",
            "why": "AFE comparator already succeeds, but exact arg/payload pairing is needed as a control for the custom-topology SET capture method",
            "acceptance": "exact SET record matches or explains the V2704 1180-byte AFE payload",
        },
        {
            "requirement": "do not rerun V2639 with the V2707 manifest unchanged",
            "why": "V2708 already proved that GET payload replay plus generic basic SET headers reaches DSP and is rejected",
            "acceptance": "next replay manifest must contain new capture evidence or a documented byte-exact reconstruction, not only the same V2704 payloads",
        },
    ]


def write_report(summary: dict[str, Any], path: Path) -> None:
    c = summary["classification"]
    lines = [
        "# NATIVE_INIT V2709 — ACDB replay frontier audit after V2708",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only audit after the V2708 live replay. This unit reads only metadata/result logs from V2704, V2707, and V2708; it does not read raw ACDB payload bytes, run a device step, issue `/dev/msm_audio_cal` ioctls, change mixer state, or perform a PCM probe.",
        "",
        "## Result",
        "",
        f"- decision: `{c['decision']}`",
        f"- recommended_next: `{c['recommended_next']}`",
        f"- captured_all_v2704_targets: `{c['captured_all_v2704_targets']}`",
        f"- manifest_uses_basic_payload_for_all_targets: `{c['manifest_uses_basic_payload_for_all_targets']}`",
        f"- set_all_targets_ok: `{c['set_all_targets_ok']}`",
        f"- deallocated_all_targets: `{c['deallocated_all_targets']}`",
        f"- pcm_attempted: `{c['pcm_attempted']}`",
        f"- asm_rejected_ebadparam: `{c['asm_rejected_ebadparam']}`",
        f"- get_payload_replay_exhausted: `{c['get_payload_replay_exhausted']}`",
        f"- native_replay_should_remain_parked_until_new_capture: `{c['native_replay_should_remain_parked_until_new_capture']}`",
        "",
        "## Evidence Matrix",
        "",
        "| cal_type | role | V2704 GET ret/len/SHA | V2707 replay kind | V2708 SET | V2708 dealloc |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for cal_type in TARGET_CAL_TYPES:
        v2704 = summary["v2704_targets"].get(str(cal_type), {})
        manifest = summary["v2707_manifest_targets"].get(str(cal_type), {})
        replay = summary["v2708_replay_targets"].get(str(cal_type), {})
        sha = str(v2704.get("sha256") or "")
        sha_short = sha[:12] + "..." if sha else "missing"
        get_cell = f"ret={v2704.get('ret')} len={v2704.get('out_len')} sha={sha_short}"
        lines.append(
            "| {cal_type} | `{role}` | `{get_cell}` | `{kind}` | `{set_ok}` | `{dealloc}` |".format(
                cal_type=cal_type,
                role=TARGET_ROLES[cal_type],
                get_cell=get_cell,
                kind=manifest.get("entry_kind", "missing"),
                set_ok=replay.get("set_ok", False),
                dealloc=replay.get("deallocated", False),
            )
        )
    lines.extend([
        "",
        "## Dmesg Classification",
        "",
    ])
    for key, value in summary["v2708_dmesg_markers"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "V2708 closes the low-information replay loop. The V2704 lower custom-topology GET outputs for cal_types 24, 10, and 14 were all present and replayed through the V2707 entry-cap manifest as generic `basic-payload` records. V2708 then proved that all three target SET ioctls returned OK and were deallocated cleanly, yet `pcm_open` still failed because the DSP rejected ASM custom topology with `ADSP_EBADPARAM`.",
        "",
        "Therefore the next useful work is not another replay of the same V2704 GET bytes. The next capture must produce new byte-exact Android-good custom-topology SET evidence, or a byte-exact reconstruction that changes the replay contract. The highest-priority target is cal_type 14 because the current failure is in `send_asm_custom_topology`; cal_type 10 remains required for ADM topology 0x10004000; cal_type 24 should be kept as the AFE control.",
        "",
        "## Next Capture Requirements",
        "",
    ])
    for item in summary["next_capture_requirements"]:
        lines.extend([
            f"- requirement: {item['requirement']}",
            f"  - why: {item['why']}",
            f"  - acceptance: {item['acceptance']}",
        ])
    lines.extend([
        "",
        "## Missing Evidence",
        "",
    ])
    if summary["missing_evidence"]:
        lines.extend(f"- {item}" for item in summary["missing_evidence"])
    else:
        lines.append("- none for this audit; the remaining gap is new byte-exact SET evidence, not missing V2708 replay metadata.")
    lines.extend([
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_replay_frontier_v2709.py tests/test_analyze_audio_acdb_replay_frontier_v2709.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_replay_frontier_v2709 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_replay_frontier_v2709.py --write-report --json`",
        "- `git diff --check`",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2704-result", type=Path, default=DEFAULT_V2704_RESULT)
    parser.add_argument("--v2707-manifest", type=Path, default=DEFAULT_V2707_MANIFEST)
    parser.add_argument("--v2708-result", type=Path, default=DEFAULT_V2708_RESULT)
    parser.add_argument("--v2708-dmesg", type=Path, default=DEFAULT_V2708_DMESG)
    parser.add_argument("--v2708-helper-log", type=Path, default=DEFAULT_V2708_HELPER_LOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(args)
    if args.write_report:
        write_report(summary, args.report)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif not args.write_report:
        print(summary["classification"]["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
