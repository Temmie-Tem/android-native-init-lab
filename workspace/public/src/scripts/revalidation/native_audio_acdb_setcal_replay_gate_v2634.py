#!/usr/bin/env python3
"""V2634 host-only gate for SET-layer ACDB native replay readiness.

Consumes the V2633 private SET-calibration Gate-2 handoff package plus the
operator-verified topology payload, validates all private raw artifacts, and
writes a private replay-staging manifest.  This unit deliberately does not run
native replay and does not authorize it: the V2633 package still needs operator
Gate-2 acceptance and the existing replay helper cannot yet consume exact
SET-layer argument records.
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
RUN_ID = "V2634"
BUILD_TAG = "v2634-audio-acdb-setcal-replay-gate"
TOPOLOGY_SHA256 = "7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89"
TOPOLOGY_LEN = 4916
EXPECTED_SET_ORDER = [13, 9, 11, 12, 15, 23, 16, 21]
PAYLOAD_CAL_TYPES = {11, 15, 16}
DEFAULT_AUDIO_RUNS = ROOT / "workspace/private/runs/audio"
DEFAULT_TOPOLOGY_PAYLOAD = ROOT / "workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_PRIVATE_MANIFEST = DEFAULT_BUILD_ROOT / "setcal-replay-gate-manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2634_AUDIO_ACDB_SETCAL_REPLAY_GATE_2026-06-18.md"
MULTICAL_HELPER_SOURCE = ROOT / "workspace/public/src/native-init/helpers/a90_acdb_multical_replay_scaffold_v2625.c"

ROLE_BY_CAL_TYPE = {
    9: "AFE_TOPOLOGY_HEADER",
    11: "AUDPROC_COMMON_PAYLOAD",
    12: "VOL_HEADER_NO_PAYLOAD",
    13: "APP_META_HEADER",
    15: "ASM_STREAM_PAYLOAD",
    16: "AFE_COMMON_PAYLOAD",
    21: "SPEAKER_VI_HEADER",
    23: "AFE_TOPOLOGY_ID_HEADER",
    39: "CORE_CUSTOM_TOPOLOGIES",
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


def write_json(path: Path, payload: dict[str, Any], *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def all_zero(path: Path) -> bool:
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if any(chunk):
                return False
    return True


def latest_v2633_manifest(audio_runs: Path = DEFAULT_AUDIO_RUNS) -> Path:
    candidates = sorted(audio_runs.glob("v2632-acdb-setcal-capture-*/v2633-acdb-setcal-gate2-handoff-manifest.json"))
    if not candidates:
        raise FileNotFoundError(f"no V2633 SET-cal Gate-2 manifest under {rel(audio_runs)}")
    return candidates[-1]


def file_state(path_value: str | None, *, expected_size: int | None, expected_sha256: str | None) -> dict[str, Any]:
    if not path_value:
        return {
            "path_private": None,
            "exists": False,
            "ok": False,
            "size": None,
            "sha256": None,
            "nonzero": False,
            "size_matches": False,
            "sha256_matches": False,
            "private_only": True,
        }
    path = ROOT / path_value if not Path(path_value).is_absolute() else Path(path_value)
    state: dict[str, Any] = {
        "path_private": rel(path),
        "exists": path.exists(),
        "ok": False,
        "size": None,
        "sha256": None,
        "nonzero": False,
        "size_matches": False,
        "sha256_matches": False,
        "private_only": True,
    }
    if not path.exists() or not path.is_file():
        return state
    size = path.stat().st_size
    digest = sha256_file(path)
    nonzero = not all_zero(path)
    size_matches = expected_size is None or size == expected_size
    sha256_matches = expected_sha256 is None or digest == expected_sha256
    state.update(
        {
            "ok": bool(size_matches and sha256_matches and nonzero),
            "size": size,
            "sha256": digest,
            "nonzero": nonzero,
            "size_matches": size_matches,
            "sha256_matches": sha256_matches,
            "mode": oct(path.stat().st_mode & 0o777),
        }
    )
    return state


def topology_state(path: Path) -> dict[str, Any]:
    return file_state(str(path), expected_size=TOPOLOGY_LEN, expected_sha256=TOPOLOGY_SHA256) | {
        "cal_type": 39,
        "role": ROLE_BY_CAL_TYPE[39],
        "operator_verified": True,
        "source": "V2547 operator-verified topology payload",
    }


def set_record_state(record: dict[str, Any]) -> dict[str, Any]:
    cal_type = int(record.get("cal_type"))
    cal_size = int(record.get("cal_size") or 0)
    data_size = int(record.get("data_size") or 0)
    dmabuf_expected = bool(record.get("dmabuf_expected"))
    arg = record.get("arg") if isinstance(record.get("arg"), dict) else {}
    dmabuf = record.get("dmabuf") if isinstance(record.get("dmabuf"), dict) else {}
    arg_state = file_state(
        arg.get("raw_path_private"),
        expected_size=arg.get("size") or data_size,
        expected_sha256=arg.get("sha256"),
    )
    dmabuf_state = file_state(
        dmabuf.get("raw_path_private"),
        expected_size=dmabuf.get("size") or (cal_size if dmabuf_expected else None),
        expected_sha256=dmabuf.get("sha256"),
    )
    if not dmabuf_expected:
        dmabuf_state["ok"] = not bool(dmabuf.get("raw_path_private"))
        dmabuf_state["not_required"] = True
    record_ok = bool(record.get("verified_for_gate2") and record.get("header_valid") and arg_state.get("ok") and dmabuf_state.get("ok"))
    return {
        "sequence": record.get("sequence"),
        "cal_type": cal_type,
        "role": record.get("role") or ROLE_BY_CAL_TYPE.get(cal_type, "UNKNOWN"),
        "data_size": data_size,
        "cal_type_size": record.get("cal_type_size"),
        "cal_size": cal_size,
        "mem_handle": record.get("mem_handle"),
        "dmabuf_expected": dmabuf_expected,
        "dmabuf_status": record.get("dmabuf_status"),
        "header_valid": bool(record.get("header_valid")),
        "verified_for_gate2": bool(record.get("verified_for_gate2")),
        "arg": arg_state,
        "dmabuf": dmabuf_state,
        "ok": record_ok,
        "replay_policy": replay_policy_for_record(cal_type, cal_size, dmabuf_expected),
    }


def replay_policy_for_record(cal_type: int, cal_size: int, dmabuf_expected: bool) -> dict[str, Any]:
    if dmabuf_expected:
        return {
            "kind": "payload_backed_set_arg_template",
            "requires_fresh_dmabuf": True,
            "requires_mem_handle_patch": True,
            "operator_gate2_required": True,
            "note": "Use captured SET arg as template; replace stale mem_handle with fresh ION fd before AUDIO_SET_CALIBRATION.",
        }
    return {
        "kind": "header_only_exact_set_arg",
        "requires_fresh_dmabuf": False,
        "requires_mem_handle_patch": False,
        "operator_gate2_required": True,
        "note": f"Replay exact captured SET arg only if operator accepts cal_type {cal_type} header semantics.",
    }


def redacted_file_state(state: dict[str, Any]) -> dict[str, Any]:
    output = dict(state)
    output.pop("path_private", None)
    return output


def redacted_record(record: dict[str, Any]) -> dict[str, Any]:
    output = dict(record)
    output["arg"] = redacted_file_state(dict(record.get("arg") or {}))
    output["dmabuf"] = redacted_file_state(dict(record.get("dmabuf") or {}))
    return output


def helper_gap_state() -> dict[str, Any]:
    text = MULTICAL_HELPER_SOURCE.read_text(encoding="utf-8", errors="replace") if MULTICAL_HELPER_SOURCE.exists() else ""
    supports_exact_set_args = "set_arg" in text or "exact_set_arg" in text
    reconstructs_basic_packet = "fill_cal_packet" in text and "packet->data_size = (int32_t)sizeof(*packet)" in text
    return {
        "source": rel(MULTICAL_HELPER_SOURCE),
        "exists": MULTICAL_HELPER_SOURCE.exists(),
        "supports_exact_set_arg_replay": supports_exact_set_args,
        "reconstructs_basic_audio_cal_packet": reconstructs_basic_packet,
        "current_gap": "existing helper replays payload-only entries by reconstructing a basic packet; V2633 requires exact SET-arg replay including header-only records",
        "required_future_delta": [
            "consume the V2634 private SET-layer manifest, not the old cal_type:buffer:path argv list",
            "send captured SET arg bytes for header-only records without allocating a dmabuf",
            "for payload-backed records, allocate fresh ION dmabuf, copy payload bytes, patch mem_handle in the captured SET arg, then SET",
            "keep all payload dmabuf fds open across the bounded PCM probe and deallocate/close in cleanup",
        ],
    }


def build_manifest(
    v2633_manifest_path: Path,
    topology_payload: Path,
    *,
    operator_gate2_accepted: bool = False,
) -> dict[str, Any]:
    v2633 = read_json(v2633_manifest_path)
    topology = topology_state(topology_payload)
    records = [set_record_state(record) for record in v2633.get("records", [])]
    ordered_cal_types = [record.get("cal_type") for record in records]
    helper_gap = helper_gap_state()
    inputs_ok = bool(
        v2633.get("ok")
        and v2633.get("source_rolled_back")
        and topology.get("ok")
        and ordered_cal_types == EXPECTED_SET_ORDER
        and len(records) == len(EXPECTED_SET_ORDER)
        and all(record.get("ok") for record in records)
    )
    replay_blockers: list[str] = []
    if not operator_gate2_accepted:
        replay_blockers.append("operator Gate-2 has not accepted the V2633 SET-layer package")
    if not helper_gap.get("supports_exact_set_arg_replay"):
        replay_blockers.append("current native replay helper does not support exact SET-arg/header-only replay")
    replay_blockers.append("V2634 is a host-only staging gate, not a live native replay approval")
    if not v2633.get("source_rolled_back"):
        replay_blockers.append("source live capture rollback proof is missing")
    if ordered_cal_types != EXPECTED_SET_ORDER:
        replay_blockers.append("captured SET order does not match V2633 expected order")
    if not topology.get("ok"):
        replay_blockers.append("operator-verified topology payload is missing or failed validation")
    if not all(record.get("ok") for record in records):
        replay_blockers.append("one or more SET records failed private raw artifact validation")

    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "source_v2633_manifest": rel(v2633_manifest_path),
        "source_v2633_ok": bool(v2633.get("ok")),
        "source_v2633_decision": v2633.get("source_decision"),
        "source_capture_rolled_back": bool(v2633.get("source_rolled_back")),
        "operator_gate2_accepted": operator_gate2_accepted,
        "inputs_ok": inputs_ok,
        "native_replay_ready": False,
        "safe_to_run_native_replay": False,
        "replay_blockers": replay_blockers,
        "topology": topology,
        "captured_set_order": ordered_cal_types,
        "expected_set_order": EXPECTED_SET_ORDER,
        "payload_cal_types": sorted(PAYLOAD_CAL_TYPES),
        "header_or_no_payload_cal_types": [record["cal_type"] for record in records if record["cal_type"] not in PAYLOAD_CAL_TYPES],
        "set_records": records,
        "set_records_redacted": [redacted_record(record) for record in records],
        "helper_gap": helper_gap,
        "summary": {
            "decision": "v2634-setcal-replay-gate-ready" if inputs_ok else "v2634-setcal-replay-gate-blocked",
            "record_count": len(records),
            "validated_record_count": sum(1 for record in records if record.get("ok")),
            "payload_record_count": sum(1 for record in records if record.get("dmabuf_expected")),
            "header_record_count": sum(1 for record in records if not record.get("dmabuf_expected")),
            "topology_ok": topology.get("ok"),
            "helper_supports_exact_set_arg_replay": helper_gap.get("supports_exact_set_arg_replay"),
        },
        "ok": inputs_ok,
    }


def write_report(path: Path, manifest: dict[str, Any], private_manifest_path: Path) -> None:
    lines = [
        "# NATIVE_INIT V2634 — ACDB SET-cal replay gate",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only staging gate for native ACDB replay after the V2633 SET-layer",
        "handoff. This unit validates the private SET arg/dma-buf artifacts and",
        "the operator-verified topology payload, then writes a private manifest for",
        "future replay-helper work.",
        "",
        "It does **not** run native replay, does not issue `/dev/msm_audio_cal` ioctls,",
        "does not flash or boot the device, and does not copy raw ACDB bytes into tracked paths.",
        "",
        "## Result",
        "",
        f"- decision: `{manifest['summary']['decision']}`",
        f"- ok: `{manifest.get('ok')}`",
        f"- inputs_ok: `{manifest.get('inputs_ok')}`",
        f"- source_v2633_manifest: `{manifest.get('source_v2633_manifest')}`",
        f"- private_manifest: `{rel(private_manifest_path)}`",
        f"- topology_ok: `{manifest['summary'].get('topology_ok')}`",
        f"- record_count: `{manifest['summary'].get('record_count')}`",
        f"- validated_record_count: `{manifest['summary'].get('validated_record_count')}`",
        f"- captured_set_order: `{manifest.get('captured_set_order')}`",
        f"- native_replay_ready: `{manifest.get('native_replay_ready')}`",
        f"- safe_to_run_native_replay: `{manifest.get('safe_to_run_native_replay')}`",
        "",
        "## Redacted Replay Inputs",
        "",
        "| seq | cal_type | role | data_size | cal_size | dmabuf | arg_sha256 | dmabuf_sha256 | status |",
        "| ---: | ---: | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for record in manifest.get("set_records_redacted", []):
        arg = record.get("arg", {})
        dmabuf = record.get("dmabuf", {})
        dmabuf_label = "payload" if record.get("dmabuf_expected") else "header/no-payload"
        lines.append(
            f"| {record.get('sequence')} | {record.get('cal_type')} | `{record.get('role')}` | "
            f"{record.get('data_size')} | {record.get('cal_size')} | `{dmabuf_label}` | "
            f"`{arg.get('sha256')}` | `{dmabuf.get('sha256')}` | `{record.get('ok')}` |"
        )
    lines.extend(
        [
            "",
            "## Replay Gate",
            "",
            "- V2634 packages replay inputs only; it is **not** a live replay approval.",
            "- Native replay remains blocked until operator Gate-2 accepts the V2633 SET-layer package.",
            "- The current V2625 native helper reconstructs payload-only packets and does not support",
            "  exact SET-arg/header-only replay required by V2633.",
            "- Future helper work must consume the private manifest, preserve exact header-only SET args,",
            "  and patch fresh dmabuf handles only for payload-backed records.",
            "",
            "### Blockers",
            "",
        ]
    )
    for blocker in manifest.get("replay_blockers", []):
        lines.append(f"- {blocker}")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_gate_v2634.py tests/test_native_audio_acdb_setcal_replay_gate_v2634.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_gate_v2634 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_gate_v2634.py --write-report`",
            "- `git diff --check`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2633-manifest", type=Path, default=None)
    parser.add_argument("--topology-payload", type=Path, default=DEFAULT_TOPOLOGY_PAYLOAD)
    parser.add_argument("--private-manifest", type=Path, default=DEFAULT_PRIVATE_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--operator-gate2-accepted", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    v2633_manifest = args.v2633_manifest or latest_v2633_manifest()
    manifest = build_manifest(
        v2633_manifest,
        args.topology_payload,
        operator_gate2_accepted=args.operator_gate2_accepted,
    )
    manifest["private_manifest_path"] = rel(args.private_manifest)
    write_json(args.private_manifest, manifest, mode=0o600)
    if args.write_report:
        write_report(args.report, manifest, args.private_manifest)
    print(json.dumps({
        "decision": manifest["summary"]["decision"],
        "ok": manifest["ok"],
        "inputs_ok": manifest["inputs_ok"],
        "private_manifest": rel(args.private_manifest),
        "report": rel(args.report) if args.write_report else None,
        "safe_to_run_native_replay": manifest["safe_to_run_native_replay"],
        "replay_blockers": manifest["replay_blockers"],
    }, indent=2, sort_keys=True))
    return 0 if manifest["inputs_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
