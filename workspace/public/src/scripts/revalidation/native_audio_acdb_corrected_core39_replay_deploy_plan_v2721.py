#!/usr/bin/env python3
"""V2721 host-only deploy plan for corrected ACDB core-39 SET replay.

Current GOAL.md correction says the cal_type 10/14/24 chase is stale: the stock
HAL SET trace does not issue those subsystem custom topology records. The next
native replay should use the byte-exact CORE_CUSTOM_TOPOLOGIES SET record from
V2669, the real-HAL cal_type 20 header SET records recovered from ptrace, and
the already captured per-device exact SET sequence from V2636.

This script writes only a private staging manifest and private cal20 arg files.
It does not flash, stage, run native replay, issue audio calibration ioctls, or
play audio.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import analyze_audio_acdb_real_set_bytes_v2652 as v2652
import native_audio_acdb_subsystem_topology_replay_deploy_plan_v2707 as v2707

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2721"
BUILD_TAG = "v2721-audio-acdb-corrected-core39-replay-deploy-plan"
DEFAULT_V2636_MANIFEST = ROOT / "workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json"
DEFAULT_V2669_RUN = ROOT / "workspace/private/runs/audio/v2669-acdb-direct-real-common-setcal-capture-20260618-134245"
DEFAULT_HELPER = ROOT / "workspace/private/builds/audio/v2679-acdb-setcal-helper-entry-cap/bin/a90_acdb_setcal_replay_execute_v2635"
DEFAULT_REAL_HAL_RUN = "v2466-acdb-dmabuf-live-20260615-200643"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_PRIVATE_MANIFEST = DEFAULT_BUILD_ROOT / "deploy-plan.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2721_AUDIO_ACDB_CORRECTED_CORE39_REPLAY_DEPLOY_PLAN_2026-06-18.md"
DEFAULT_REMOTE_DIR = "/cache/a90-acdb-setcal-replay-v2721"
EXPECTED_REPLAY_ORDER = [39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21]
FORBIDDEN_STALE_CAL_TYPES = {10, 14, 24}
PER_DEVICE_SOURCE_ORDER = [13, 9, 11, 12, 15, 23, 16, 21]


def rel(path: Path | str | None) -> str | None:
    if path is None:
        return None
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_all_zero(path: Path) -> bool:
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if any(chunk):
                return False
    return True


def local_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def verify_private_file(path: Path | None, *, expected_size: int | None = None, expected_sha256: str | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {
        "local_path_private": rel(path) if path else None,
        "exists": bool(path and path.exists()),
        "ok": False,
        "size": None,
        "sha256": None,
        "nonzero": False,
        "size_matches": False,
        "sha256_matches": False,
        "private_only": True,
    }
    if path is None or not path.exists() or not path.is_file():
        return state
    size = path.stat().st_size
    digest = sha256_file(path)
    nonzero = not is_all_zero(path)
    size_matches = expected_size is None or size == expected_size
    sha256_matches = expected_sha256 is None or digest == expected_sha256
    state.update(
        {
            "ok": bool(nonzero and size_matches and sha256_matches),
            "size": size,
            "sha256": digest,
            "nonzero": nonzero,
            "size_matches": size_matches,
            "sha256_matches": sha256_matches,
            "mode": oct(path.stat().st_mode & 0o777),
        }
    )
    return state


def remote_join(remote_dir: str, name: str) -> str:
    return remote_dir.rstrip("/") + "/" + name


def deploy_file(kind: str, local: dict[str, Any], remote_path: str, *, executable: bool = False) -> dict[str, Any]:
    return {
        "kind": kind,
        "local": local,
        "remote_path": remote_path,
        "remote_mode": "0700" if executable else "0600",
        "remote_sha256_command": f"sha256sum {remote_path}",
        "ok": bool(local.get("ok")),
    }


def redacted_file(entry: dict[str, Any]) -> dict[str, Any]:
    output = copy.deepcopy(entry)
    local = dict(output.get("local") or {})
    local.pop("local_path_private", None)
    output["local"] = local
    return output


def file_by_remote(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("remote_path")): item for item in manifest.get("files") or [] if item.get("remote_path")}


def verify_from_existing_file_entry(entry: dict[str, Any]) -> dict[str, Any]:
    local = entry.get("local") or {}
    path = local_path(local.get("local_path_private"))
    return verify_private_file(path, expected_size=local.get("size"), expected_sha256=local.get("sha256"))


def load_v2669_core39(run_dir: Path, remote_dir: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    events_path = run_dir / "ownget-device-artifacts/setcal-events.jsonl"
    if not events_path.exists():
        raise FileNotFoundError(f"missing V2669 setcal events: {events_path}")
    candidates: list[dict[str, Any]] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event") == "setcal_capture" and int(event.get("cal_type", -1)) == 39:
            candidates.append(event)
    if len(candidates) != 1:
        raise RuntimeError(f"expected exactly one V2669 cal39 SET event, found {len(candidates)}")
    event = candidates[0]
    artifacts = run_dir / "ownget-device-artifacts"
    arg_name = Path(str((event.get("set_arg") or {}).get("path") or "")).name
    payload_name = Path(str((event.get("dmabuf") or {}).get("path") or "")).name
    arg_meta = event.get("set_arg") or {}
    payload_meta = event.get("dmabuf") or {}
    arg_file = deploy_file(
        "set_arg",
        verify_private_file(artifacts / arg_name, expected_size=int(arg_meta.get("len")), expected_sha256=str(arg_meta.get("sha256"))),
        remote_join(remote_dir, "00-set-arg-cal39-core-custom-topologies.bin"),
    )
    payload_file = deploy_file(
        "payload",
        verify_private_file(artifacts / payload_name, expected_size=int(payload_meta.get("len")), expected_sha256=str(payload_meta.get("sha256"))),
        remote_join(remote_dir, "00-payload-cal39-core-custom-topologies.bin"),
    )
    replay = {
        "sequence": 0,
        "kind": "exact-set",
        "cal_type": 39,
        "role": "CORE_CUSTOM_TOPOLOGIES_BYTE_EXACT_SET",
        "source": "V2669 acdb_loader_send_common_custom_topology real SET capture",
        "arg_remote": arg_file["remote_path"],
        "payload_remote": payload_file["remote_path"],
        "dmabuf_expected": True,
        "ok": bool(arg_file.get("ok") and payload_file.get("ok")),
        "capture": {
            "data_size": event.get("data_size"),
            "cal_size": event.get("cal_size"),
            "mem_handle_captured": event.get("mem_handle"),
            "arg_sha256": arg_file["local"].get("sha256"),
            "payload_sha256": payload_file["local"].get("sha256"),
        },
    }
    return [arg_file, payload_file], replay


def iter_real_hal_set_records(run_name: str) -> list[tuple[Path, dict[str, Any], v2652.SetArgRecord]]:
    runs_root = ROOT / "workspace/private/runs/audio"
    run_dir = runs_root / run_name
    records: list[tuple[Path, dict[str, Any], v2652.SetArgRecord]] = []
    for path in sorted(run_dir.glob("**/msm-audio-cal-*.jsonl")):
        for row in v2652.iter_jsonl(path):
            record = v2652.row_to_set_record(path, row, runs_root)
            if record is not None:
                records.append((path, row, record))
    return records


def materialize_cal20_args(run_name: str, build_root: Path, remote_dir: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    all_records = iter_real_hal_set_records(run_name)
    cal20: list[tuple[Path, dict[str, Any], v2652.SetArgRecord]] = [item for item in all_records if item[2].cal_type == 20]
    unique: dict[str, tuple[Path, dict[str, Any], v2652.SetArgRecord]] = {}
    for item in cal20:
        unique.setdefault(item[2].arg_sha256, item)
    selected = [unique[key] for key in sorted(unique)]
    # Keep real-HAL order from one run if it has two distinct cal20 records.
    ordered: list[tuple[Path, dict[str, Any], v2652.SetArgRecord]] = []
    seen: set[str] = set()
    for item in cal20:
        digest = item[2].arg_sha256
        if digest not in seen:
            ordered.append(item)
            seen.add(digest)
    selected = ordered
    files: list[dict[str, Any]] = []
    replays: list[dict[str, Any]] = []
    for index, (source_path, row, record) in enumerate(selected, start=1):
        bytes_hex = row.get("bytes_hex")
        if not isinstance(bytes_hex, str) or not bytes_hex:
            raise RuntimeError(f"cal20 record lacks bytes_hex: {source_path}")
        blob = bytes.fromhex(bytes_hex)[: record.data_size]
        out_path = build_root / "cal20" / f"cal20-realhal-{index:02d}-{record.arg_sha256[:12]}.bin"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(blob)
        out_path.chmod(0o600)
        digest = sha256_bytes(blob)
        if digest != record.arg_sha256:
            raise RuntimeError(f"cal20 digest mismatch for {source_path}: {digest} != {record.arg_sha256}")
        remote = remote_join(remote_dir, f"{index:02d}-set-arg-cal20-realhal-{index:02d}.bin")
        file_entry = deploy_file("set_arg", verify_private_file(out_path, expected_size=record.data_size, expected_sha256=record.arg_sha256), remote)
        files.append(file_entry)
        replays.append(
            {
                "sequence": index,
                "kind": "exact-set",
                "cal_type": 20,
                "role": f"AFE_FB_SPKR_PROT_HEADER_REAL_HAL_{index}",
                "source": f"{record.run_dir}:{record.source}:seq{record.sequence}",
                "arg_remote": remote,
                "payload_remote": None,
                "dmabuf_expected": False,
                "ok": bool(file_entry.get("ok")),
                "capture": {
                    "data_size": record.data_size,
                    "cal_size": record.cal_size,
                    "mem_handle_captured": record.mem_handle,
                    "arg_sha256": record.arg_sha256,
                    "scalar_words": record.scalar_words,
                },
            }
        )
    return files, replays, {
        "run_name": run_name,
        "decoded_cal20_count": len(cal20),
        "unique_cal20_arg_count": len(selected),
        "selected_arg_sha256": [item[2].arg_sha256 for item in selected],
        "ok": len(selected) >= 1,
    }


def per_device_entries(v2636: dict[str, Any], *, first_sequence: int, remote_dir: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files_by_remote = file_by_remote(v2636)
    files: list[dict[str, Any]] = []
    replays: list[dict[str, Any]] = []
    by_cal_type = {int(item.get("cal_type")): item for item in v2636.get("set_args") or []}
    missing = [cal_type for cal_type in PER_DEVICE_SOURCE_ORDER if cal_type not in by_cal_type]
    if missing:
        raise RuntimeError(f"V2636 manifest missing per-device cal types: {missing}")
    for offset, cal_type in enumerate(PER_DEVICE_SOURCE_ORDER):
        item = by_cal_type[cal_type]
        sequence = first_sequence + offset
        arg_source = files_by_remote[str(item["arg_remote"])]
        arg_file = deploy_file(
            "set_arg",
            verify_from_existing_file_entry(arg_source),
            remote_join(remote_dir, f"{sequence:02d}-set-arg-cal{cal_type:02d}.bin"),
        )
        files.append(arg_file)
        payload_file: dict[str, Any] | None = None
        if item.get("payload_remote"):
            payload_source = files_by_remote[str(item["payload_remote"])]
            payload_file = deploy_file(
                "payload",
                verify_from_existing_file_entry(payload_source),
                remote_join(remote_dir, f"{sequence:02d}-payload-cal{cal_type:02d}.bin"),
            )
            files.append(payload_file)
        replays.append(
            {
                "sequence": sequence,
                "kind": "exact-set",
                "cal_type": cal_type,
                "role": item.get("role"),
                "source": "V2636 per-device SET capture manifest",
                "arg_remote": arg_file["remote_path"],
                "payload_remote": payload_file["remote_path"] if payload_file else None,
                "dmabuf_expected": bool(payload_file),
                "ok": bool(arg_file.get("ok") and (payload_file is None or payload_file.get("ok"))),
            }
        )
    return files, replays


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v2636 = read_json(Path(args.v2636_manifest))
    if not v2636.get("ok") or not v2636.get("all_inputs_ok"):
        raise RuntimeError(f"V2636 deploy manifest is not ready: {rel(args.v2636_manifest)}")
    remote_dir = str(args.remote_dir)
    build_root = Path(args.build_root)
    helper = v2707.helper_state(Path(args.helper), expected_sha256=v2707.EXPECTED_HELPER_SHA256)
    helper_file = deploy_file(
        "helper",
        {
            "local_path_private": rel(args.helper),
            "exists": helper.get("exists"),
            "ok": helper.get("ok"),
            "size": helper.get("size"),
            "sha256": helper.get("sha256"),
            "nonzero": bool((helper.get("size") or 0) > 0),
            "size_matches": True,
            "sha256_matches": helper.get("sha256_matches"),
            "private_only": True,
            "mode": helper.get("mode"),
        },
        remote_join(remote_dir, "a90_acdb_setcal_replay_execute_v2635"),
        executable=True,
    )
    files: list[dict[str, Any]] = [helper_file]
    core_files, core_replay = load_v2669_core39(Path(args.v2669_run), remote_dir)
    files.extend(core_files)
    cal20_files, cal20_replays, cal20_summary = materialize_cal20_args(str(args.real_hal_run), build_root, remote_dir)
    files.extend(cal20_files)
    perdev_files, perdev_replays = per_device_entries(v2636, first_sequence=1 + len(cal20_replays), remote_dir=remote_dir)
    files.extend(perdev_files)
    replay_entries = [core_replay] + cal20_replays + perdev_replays
    replay_order = [int(item["cal_type"]) for item in replay_entries]
    stale_entries = [item for item in replay_entries if int(item["cal_type"]) in FORBIDDEN_STALE_CAL_TYPES]

    argv = [helper_file["remote_path"], "--execute"]
    for entry in replay_entries:
        value = str(entry["arg_remote"])
        if entry.get("payload_remote"):
            value += f":{entry['payload_remote']}"
        argv.extend(["--exact-set", value])
    argv.extend(["--hold-sec", str(int(args.hold_sec))])

    all_inputs_ok = bool(all(item.get("ok") for item in files) and all(item.get("ok") for item in replay_entries))
    order_ok = replay_order == EXPECTED_REPLAY_ORDER
    no_stale = not stale_entries and not any("--basic-payload" == item for item in argv)
    entry_count_fits = len(replay_entries) <= v2707.EXPECTED_HELPER_MAX_REPLAY_ENTRIES
    safe_to_run = bool(all_inputs_ok and order_ok and no_stale and helper.get("ok") and entry_count_fits)
    blockers: list[str] = []
    if not all_inputs_ok:
        blockers.append("one or more deployment inputs failed local validation")
    if not order_ok:
        blockers.append(f"replay order {replay_order} does not match expected {EXPECTED_REPLAY_ORDER}")
    if not no_stale:
        blockers.append("manifest includes stale cal_type 10/14/24 or a legacy --basic-payload entry")
    if not helper.get("ok"):
        blockers.append("entry-cap helper artifact validation failed")
    if not entry_count_fits:
        blockers.append("replay entry count exceeds helper cap")

    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "audio_playback_run": False,
        "source_v2636_manifest": rel(args.v2636_manifest),
        "source_v2669_run": rel(args.v2669_run),
        "source_real_hal_trace_run": str(args.real_hal_run),
        "remote_dir": remote_dir,
        "hold_sec": int(args.hold_sec),
        "all_inputs_ok": all_inputs_ok,
        "native_replay_ready": safe_to_run,
        "safe_to_run_native_replay": safe_to_run,
        "replay_blockers": blockers,
        "files": files,
        "files_redacted": [redacted_file(item) for item in files],
        "replay_entries": replay_entries,
        "remote_argv": argv,
        "helper_contract": {
            "helper_ok": helper.get("ok"),
            "helper_sha256": helper.get("sha256"),
            "expected_helper_sha256": v2707.EXPECTED_HELPER_SHA256,
            "max_replay_entries": v2707.EXPECTED_HELPER_MAX_REPLAY_ENTRIES,
            "declared_replay_entries": len(replay_entries),
            "entry_count_fits": entry_count_fits,
        },
        "corrected_manifest_contract": {
            "uses_byte_exact_v2669_cal39_set": core_replay.get("ok"),
            "uses_legacy_basic_payload_cal39": False,
            "includes_real_hal_cal20_headers": len(cal20_replays),
            "includes_perdevice_sequence": PER_DEVICE_SOURCE_ORDER,
            "forbidden_stale_cal_types": sorted(FORBIDDEN_STALE_CAL_TYPES),
            "stale_cal_types_present": sorted({int(item["cal_type"]) for item in stale_entries}),
            "replay_order": replay_order,
            "expected_replay_order": EXPECTED_REPLAY_ORDER,
            "order_ok": order_ok,
            "no_basic_payload_argv": "--basic-payload" not in argv,
        },
        "cal20_source_summary": cal20_summary,
        "summary": {
            "decision": "v2721-corrected-core39-replay-deploy-plan-ready" if safe_to_run else "v2721-corrected-core39-replay-deploy-plan-blocked",
            "file_count": len(files),
            "replay_entry_count": len(replay_entries),
            "payload_file_count": sum(1 for item in files if item.get("kind") == "payload"),
            "cal20_record_count": len(cal20_replays),
            "remote_arg_count": len(argv),
        },
        "ok": safe_to_run,
    }


def write_report(path: Path, manifest: dict[str, Any], private_manifest_path: Path) -> None:
    contract = manifest["corrected_manifest_contract"]

    def public_source(source: object) -> str:
        text = str(source or "")
        if "workspace/private/" in text or "/device-artifacts/" in text or text.endswith(".jsonl"):
            if ":seq" in text:
                return f"V2466 real-HAL ptrace metadata {text.rsplit(':seq', 1)[1]}"
            return "private source metadata"
        return text

    lines = [
        "# NATIVE_INIT V2721 — corrected ACDB core-39 replay deploy plan",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only deployment-plan update for the current GOAL correction: stop chasing",
        "cal_type 10/14/24 subsystem custom topology payloads and stage the faithful",
        "stock-HAL replay set instead. No device action, flash, native calibration ioctl,",
        "or audio playback occurred.",
        "",
        "## Decision",
        "",
        f"- decision: `{manifest['summary']['decision']}`",
        f"- ok: `{manifest['ok']}`",
        f"- safe_to_run_native_replay: `{manifest['safe_to_run_native_replay']}`",
        f"- replay_blockers: `{manifest['replay_blockers']}`",
        f"- private_manifest: `{rel(private_manifest_path)}`",
        f"- remote_dir: `{manifest['remote_dir']}`",
        f"- replay_order: `{contract['replay_order']}`",
        f"- expected_replay_order: `{contract['expected_replay_order']}`",
        f"- order_ok: `{contract['order_ok']}`",
        f"- stale_cal_types_present: `{contract['stale_cal_types_present']}`",
        f"- no_basic_payload_argv: `{contract['no_basic_payload_argv']}`",
        f"- includes_real_hal_cal20_headers: `{contract['includes_real_hal_cal20_headers']}`",
        f"- declared_replay_entries: `{manifest['helper_contract']['declared_replay_entries']}`",
        f"- helper_entry_count_fits: `{manifest['helper_contract']['entry_count_fits']}`",
        "",
        "## Replay Entries",
        "",
        "| seq | cal_type | role | kind | payload | source | ok |",
        "| ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for entry in manifest["replay_entries"]:
        lines.append(
            f"| {entry.get('sequence')} | {entry.get('cal_type')} | `{entry.get('role')}` | "
            f"`{entry.get('kind')}` | `{bool(entry.get('payload_remote'))}` | `{public_source(entry.get('source'))}` | `{entry.get('ok')}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The old V2636/V2707 `--basic-payload 39` path is removed; cal_type 39 is",
            "  now replayed as the byte-exact V2669 `AUDIO_SET_CALIBRATION` arg + dma-buf.",
            "- Two real-HAL cal_type 20 header SET args are materialized privately from the",
            "  V2466 ptrace bytes and included before the V2636 per-device sequence.",
            "- Stale cal_type 10/14/24 entries are explicitly forbidden because current GOAL",
            "  evidence says the stock HAL never SETs them and prior replay made them self-inflicted.",
            "- This plan is ready for a later V2639-style live handoff if the operator wants",
            "  the corrected replay attempt; this unit itself is host-only.",
            "",
            "## Validation",
            "",
            "- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec.",
            "- Verified V2669 cal39 arg/payload hashes and non-zero payload bytes.",
            "- Materialized cal20 private arg files from existing V2466 real-HAL ptrace metadata.",
            "- Verified V2636 per-device arg/payload hashes and V2707 entry-cap helper cap.",
            "- `py_compile`, focused unittest, dry-run/write-report, and `git diff --check` passed.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2636-manifest", type=Path, default=DEFAULT_V2636_MANIFEST)
    parser.add_argument("--v2669-run", type=Path, default=DEFAULT_V2669_RUN)
    parser.add_argument("--helper", type=Path, default=DEFAULT_HELPER)
    parser.add_argument("--real-hal-run", default=DEFAULT_REAL_HAL_RUN)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_PRIVATE_MANIFEST)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--hold-sec", type=int, default=10)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    write_json(Path(args.manifest_path), manifest, mode=0o600)
    if args.write_report:
        write_report(Path(args.report_path), manifest, Path(args.manifest_path))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
