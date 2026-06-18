#!/usr/bin/env python3
"""V2705 host-only deploy plan adding V2704 subsystem topology payloads.

This unit consumes the existing V2636 SET-cal replay deployment manifest and
the V2704 Android-good large-buffer lower custom-topology capture.  It stages
the V2704 cal_type 10/14/24 raw payloads into stable private replay inputs and
emits a V2638/V2639-compatible deployment manifest whose argv prepends those
three subsystem custom-topology definitions before the captured SET-layer
records.

No device action, no native replay, no mixer write, and no PCM probe happen in
this unit.  Raw bytes remain under workspace/private.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_setcal_replay_deploy_plan_v2636 as v2636

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2705"
BUILD_TAG = "v2705-audio-acdb-subsystem-topology-replay-deploy-plan"
DEFAULT_BASE_DEPLOY = ROOT / "workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_PRIVATE_MANIFEST = DEFAULT_BUILD_ROOT / "deploy-plan.json"
DEFAULT_STABLE_PAYLOAD_DIR = ROOT / "workspace/private/inputs/audio/acdb_replay/payloads"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2705_AUDIO_ACDB_SUBSYSTEM_TOPOLOGY_REPLAY_DEPLOY_PLAN_2026-06-18.md"
DEFAULT_REMOTE_DIR = "/cache/a90-acdb-setcal-replay-v2705"

TARGET_ORDER = [24, 10, 14]
TARGET_ROLES = {
    24: "AFE_CUSTOM_TOPOLOGY",
    10: "ADM_CUSTOM_TOPOLOGY",
    14: "ASM_CUSTOM_TOPOLOGY",
}
TARGET_REMOTE_NAMES = {
    24: "01-subsystem-custom-topology-cal24-afe.bin",
    10: "02-subsystem-custom-topology-cal10-adm.bin",
    14: "03-subsystem-custom-topology-cal14-asm.bin",
}
TARGET_STABLE_NAMES = {
    24: "afe_custom_topology_cal24_v2704.bin",
    10: "adm_custom_topology_cal10_v2704.bin",
    14: "asm_custom_topology_cal14_v2704.bin",
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


def is_all_zero(path: Path) -> bool:
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if any(chunk):
                return False
    return True


def latest_v2704_result() -> Path:
    candidates = sorted((ROOT / "workspace/private/runs/audio").glob("v2704-acdb-large-buffer-topology-get-*/v2704-result.json"))
    if not candidates:
        raise FileNotFoundError("no V2704 result found under workspace/private/runs/audio")
    return candidates[-1]


def local_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def file_state(path: Path, *, expected_size: int | None = None, expected_sha256: str | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {
        "local_path_private": rel(path),
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
    nonzero = not is_all_zero(path)
    state.update(
        {
            "size": size,
            "sha256": digest,
            "nonzero": nonzero,
            "size_matches": expected_size is None or size == expected_size,
            "sha256_matches": expected_sha256 is None or digest == expected_sha256,
            "mode": oct(path.stat().st_mode & 0o777),
        }
    )
    state["ok"] = bool(state["nonzero"] and state["size_matches"] and state["sha256_matches"])
    return state


def redacted_file(entry: dict[str, Any]) -> dict[str, Any]:
    output = dict(entry)
    local = dict(output.get("local") or {})
    local.pop("local_path_private", None)
    output["local"] = local
    return output


def load_v2704_targets(path: Path) -> dict[int, dict[str, Any]]:
    payload = read_json(path)
    summary = payload.get("large_get_summary", {}) if isinstance(payload.get("large_get_summary"), dict) else {}
    if not payload.get("success") or not summary.get("success"):
        raise RuntimeError(f"V2704 result is not a successful capture: {rel(path)}")
    rows: dict[int, dict[str, Any]] = {}
    for row in summary.get("target_rows") or []:
        cal_type = row.get("target_cal_type")
        if cal_type in TARGET_ROLES and row.get("success"):
            raw = row.get("raw_status") if isinstance(row.get("raw_status"), dict) else {}
            source = local_path(raw.get("local_path"))
            if source is None:
                raise RuntimeError(f"V2704 row lacks local_path for cal_type {cal_type}")
            rows[int(cal_type)] = {
                "cal_type": int(cal_type),
                "role": TARGET_ROLES[int(cal_type)],
                "cmd": row.get("cmd"),
                "out_len": row.get("out_len"),
                "sha256": row.get("sha256"),
                "source_path_private": rel(source),
                "source_state": file_state(source, expected_size=row.get("out_len"), expected_sha256=row.get("sha256")),
            }
    missing = [cal_type for cal_type in TARGET_ORDER if cal_type not in rows]
    if missing:
        raise RuntimeError(f"V2704 result missing successful cal_types: {missing}")
    for cal_type, row in rows.items():
        if not row["source_state"].get("ok"):
            raise RuntimeError(f"V2704 raw payload validation failed for cal_type {cal_type}: {row['source_state']}")
    return rows


def stage_targets(targets: dict[int, dict[str, Any]], stable_dir: Path, *, stage: bool) -> dict[int, dict[str, Any]]:
    staged: dict[int, dict[str, Any]] = {}
    stable_dir.mkdir(parents=True, exist_ok=True)
    for cal_type in TARGET_ORDER:
        row = targets[cal_type]
        source = local_path(row["source_path_private"])
        assert source is not None
        target = stable_dir / TARGET_STABLE_NAMES[cal_type]
        if stage:
            shutil.copyfile(source, target)
            target.chmod(0o600)
        state = file_state(target, expected_size=row["out_len"], expected_sha256=row["sha256"])
        staged[cal_type] = row | {
            "stable_path_private": rel(target),
            "stable_state": state,
        }
        if not state.get("ok"):
            raise RuntimeError(f"stable payload validation failed for cal_type {cal_type}: {state}")
    return staged


def rewrite_base_file(entry: dict[str, Any], remote_dir: str) -> dict[str, Any]:
    output = dict(entry)
    remote_name = Path(str(entry.get("remote_path"))).name
    output["remote_path"] = v2636.remote_join(remote_dir, remote_name)
    if output.get("remote_sha256_command"):
        output["remote_sha256_command"] = f"sha256sum {output['remote_path']}"
    return output


def deploy_file(kind: str, local: dict[str, Any], remote_path: str, *, executable: bool = False) -> dict[str, Any]:
    return {
        "kind": kind,
        "local": local,
        "remote_path": remote_path,
        "remote_mode": "0700" if executable else "0600",
        "remote_sha256_command": f"sha256sum {remote_path}",
        "ok": bool(local.get("ok")),
    }


def build_manifest(base_deploy_path: Path,
                   v2704_result_path: Path,
                   stable_dir: Path,
                   *,
                   remote_dir: str = DEFAULT_REMOTE_DIR,
                   stage_payloads: bool = True) -> dict[str, Any]:
    base = read_json(base_deploy_path)
    if not base.get("ok") or not base.get("all_inputs_ok"):
        raise RuntimeError(f"base V2636 deploy manifest is not ready: {rel(base_deploy_path)}")
    targets = stage_targets(load_v2704_targets(v2704_result_path), stable_dir, stage=stage_payloads)

    files = [rewrite_base_file(entry, remote_dir) for entry in base.get("files") or []]
    custom_files: list[dict[str, Any]] = []
    for cal_type in TARGET_ORDER:
        target = targets[cal_type]
        local = target["stable_state"]
        remote_path = v2636.remote_join(remote_dir, TARGET_REMOTE_NAMES[cal_type])
        file_entry = deploy_file("subsystem_custom_topology", local, remote_path)
        file_entry["cal_type"] = cal_type
        file_entry["role"] = target["role"]
        custom_files.append(file_entry)
    files.extend(custom_files)

    helper_file = next((entry for entry in files if entry.get("kind") == "helper"), None)
    topology_file = next((entry for entry in files if Path(str(entry.get("remote_path"))).name == "00-core_custom_topologies.bin"), None)
    if not helper_file or not topology_file:
        raise RuntimeError("base manifest did not expose helper and core topology files")

    remote_argv = [
        helper_file["remote_path"],
        "--execute",
        "--basic-payload",
        f"39:0:{topology_file['remote_path']}",
    ]
    replay_entries = [
        {"kind": "basic-payload", "cal_type": 39, "buffer_number": 0, "role": "CORE_CUSTOM_TOPOLOGIES"},
    ]
    for entry in custom_files:
        cal_type = int(entry["cal_type"])
        remote_argv.extend(["--basic-payload", f"{cal_type}:0:{entry['remote_path']}"])
        replay_entries.append(
            {
                "kind": "basic-payload",
                "cal_type": cal_type,
                "buffer_number": 0,
                "role": entry["role"],
                "source": "V2704 lower custom-topology GET",
                "payload_size": entry["local"].get("size"),
                "payload_sha256": entry["local"].get("sha256"),
            }
        )

    for item in base.get("set_args") or []:
        arg_remote = str(item["arg_remote"]).replace(str(base.get("remote_dir")), remote_dir)
        payload_remote = item.get("payload_remote")
        if payload_remote:
            payload_remote = str(payload_remote).replace(str(base.get("remote_dir")), remote_dir)
        value = arg_remote if not payload_remote else f"{arg_remote}:{payload_remote}"
        remote_argv.extend(["--exact-set", value])
        replay_entries.append(
            {
                "kind": "exact-set",
                "cal_type": item.get("cal_type"),
                "role": item.get("role"),
                "dmabuf_expected": bool(item.get("dmabuf_expected")),
            }
        )
    remote_argv.extend(["--hold-sec", str(int(base.get("hold_sec") or 10))])

    all_inputs_ok = bool(all(entry.get("ok") for entry in files))
    payload_file_count = sum(1 for entry in files if entry.get("kind") in {"payload", "subsystem_custom_topology"})
    manifest = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "audio_playback_run": False,
        "source_v2636_manifest": rel(base_deploy_path),
        "source_v2704_result": rel(v2704_result_path),
        "base_source_v2634_manifest": base.get("source_v2634_manifest"),
        "base_source_v2635_manifest": base.get("source_v2635_manifest"),
        "operator_gate2_effective": True,
        "manual_approval_required": False,
        "live_gate_policy": "self-authorized recoverable envelope; GOAL.md policy change 2026-06-18",
        "all_inputs_ok": all_inputs_ok,
        "ok": all_inputs_ok,
        "native_replay_ready": all_inputs_ok,
        "safe_to_run_native_replay": all_inputs_ok,
        "replay_blockers": [] if all_inputs_ok else ["one or more V2705 deployment inputs failed local validation"],
        "remote_dir": remote_dir,
        "hold_sec": int(base.get("hold_sec") or 10),
        "files": files,
        "files_redacted": [redacted_file(entry) for entry in files],
        "replay_entries": replay_entries,
        "subsystem_topology_payloads": [
            {
                "cal_type": cal_type,
                "role": targets[cal_type]["role"],
                "cmd": targets[cal_type]["cmd"],
                "size": targets[cal_type]["stable_state"].get("size"),
                "sha256": targets[cal_type]["stable_state"].get("sha256"),
                "stable_path_private": targets[cal_type]["stable_path_private"],
            }
            for cal_type in TARGET_ORDER
        ],
        "subsystem_topology_payloads_redacted": [
            {
                "cal_type": cal_type,
                "role": targets[cal_type]["role"],
                "cmd": targets[cal_type]["cmd"],
                "size": targets[cal_type]["stable_state"].get("size"),
                "sha256": targets[cal_type]["stable_state"].get("sha256"),
            }
            for cal_type in TARGET_ORDER
        ],
        "set_args": base.get("set_args") or [],
        "remote_argv": remote_argv,
        "remote_preflight": {
            "mkdir": f"mkdir -p {remote_dir}",
            "chmod_helper": f"chmod 0700 {helper_file['remote_path']}",
            "verify_sha256_count": len(files),
            "cleanup": f"rm -rf {remote_dir}",
        },
        "summary": {
            "decision": "v2705-subsystem-topology-deploy-plan-ready" if all_inputs_ok else "v2705-subsystem-topology-deploy-plan-blocked",
            "file_count": len(files),
            "payload_file_count": payload_file_count,
            "custom_topology_file_count": len(custom_files),
            "set_arg_count": len(base.get("set_args") or []),
            "replay_entry_count": len(replay_entries),
            "remote_arg_count": len(remote_argv),
            "prepended_cal_types": TARGET_ORDER,
        },
    }
    return manifest


def write_report(path: Path, manifest: dict[str, Any], private_manifest_path: Path) -> None:
    lines = [
        "# NATIVE_INIT V2705 — ACDB subsystem topology replay deploy plan",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only deployment plan that combines the V2636 SET-cal replay package with",
        "the V2704 lower custom-topology payloads for cal_types `24`, `10`, and `14`.",
        "No device action, `/dev/msm_audio_cal` ioctl, mixer write, PCM probe, or raw",
        "payload publication occurred.",
        "",
        "## Result",
        "",
        f"- decision: `{manifest['summary']['decision']}`",
        f"- ok: `{manifest.get('ok')}`",
        f"- private_manifest: `{rel(private_manifest_path)}`",
        f"- source_v2636_manifest: `{manifest.get('source_v2636_manifest')}`",
        f"- source_v2704_result: `{manifest.get('source_v2704_result')}`",
        f"- native_replay_ready: `{manifest.get('native_replay_ready')}`",
        f"- safe_to_run_native_replay: `{manifest.get('safe_to_run_native_replay')}`",
        f"- remote_dir: `{manifest.get('remote_dir')}`",
        f"- file_count: `{manifest['summary'].get('file_count')}`",
        f"- replay_entry_count: `{manifest['summary'].get('replay_entry_count')}`",
        f"- remote_arg_count: `{manifest['summary'].get('remote_arg_count')}`",
        f"- prepended_cal_types: `{manifest['summary'].get('prepended_cal_types')}`",
        "",
        "## Subsystem Topology Payloads (metadata only)",
        "",
        "| order | cal_type | role | cmd | size | sha256 |",
        "| ---: | ---: | --- | --- | ---: | --- |",
    ]
    for index, row in enumerate(manifest.get("subsystem_topology_payloads_redacted") or [], start=1):
        lines.append(
            f"| {index} | {row.get('cal_type')} | `{row.get('role')}` | "
            f"`0x{int(row.get('cmd') or 0):08x}` | {row.get('size')} | `{row.get('sha256')}` |"
        )
    lines.extend(
        [
            "",
            "The V2705 remote argv prepends `--basic-payload 24:0`, `10:0`, and `14:0`",
            "after the existing core topology `39:0` payload and before the eight captured",
            "SET-layer `--exact-set` records. Raw bytes and private local paths are present",
            "only in the private manifest.",
            "",
            "## Replay Contract",
            "",
            "- use V2635 execute helper unchanged;",
            "- stage all files into a runtime temp dir and verify SHA-256 on-device before execution;",
            "- run one-shot replay only under V2639-style rollback/health machinery;",
            "- keep reverse deallocate cleanup for all payload-backed entries;",
            "- keep bounded low-amplitude PCM probe and route reset policy from V2639; and",
            "- no smart-amp gain/boost changes beyond the already observed route plan.",
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_subsystem_topology_replay_deploy_plan_v2705.py tests/test_native_audio_acdb_subsystem_topology_replay_deploy_plan_v2705.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_subsystem_topology_replay_deploy_plan_v2705 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_subsystem_topology_replay_deploy_plan_v2705.py --write-report`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --v2636-manifest workspace/private/builds/audio/v2705-audio-acdb-subsystem-topology-replay-deploy-plan/deploy-plan.json --manifest-path /tmp/v2639-v2705-manifest.json --dry-run`",
            "- `git diff --check`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-deploy", type=Path, default=DEFAULT_BASE_DEPLOY)
    parser.add_argument("--v2704-result", type=Path)
    parser.add_argument("--stable-payload-dir", type=Path, default=DEFAULT_STABLE_PAYLOAD_DIR)
    parser.add_argument("--private-manifest", type=Path, default=DEFAULT_PRIVATE_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--no-stage-payloads", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    v2704_result = args.v2704_result or latest_v2704_result()
    manifest = build_manifest(
        args.base_deploy,
        v2704_result,
        args.stable_payload_dir,
        remote_dir=args.remote_dir,
        stage_payloads=not args.no_stage_payloads,
    )
    manifest["private_manifest_path"] = rel(args.private_manifest)
    write_json(args.private_manifest, manifest, mode=0o600)
    if args.write_report:
        write_report(args.report, manifest, args.private_manifest)
    print(json.dumps({
        "decision": manifest["summary"]["decision"],
        "ok": manifest["ok"],
        "private_manifest": rel(args.private_manifest),
        "report": rel(args.report) if args.write_report else None,
        "safe_to_run_native_replay": manifest["safe_to_run_native_replay"],
        "replay_entry_count": manifest["summary"]["replay_entry_count"],
        "prepended_cal_types": manifest["summary"]["prepended_cal_types"],
    }, indent=2, sort_keys=True))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
