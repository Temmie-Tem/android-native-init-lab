#!/usr/bin/env python3
"""V2677 host-only deploy plan for ACDB custom-topology replay overlay.

This unit consumes the already verified V2636 SET-cal replay deployment
manifest and the V2675 custom-topology SET capture, then emits a V2639-compatible
deployment manifest that replays:

  1. existing CORE_CUSTOM_TOPOLOGIES cal_type 39 basic payload,
  2. V2675 custom topology cal_type 24 then 14,
  3. the original V2632/V2636 per-device SET sequence.

It does not touch the device, issue calibration ioctls, or run audio playback.
Private raw payload paths remain in the private manifest only.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2677"
BUILD_TAG = "v2677-audio-acdb-custom-topology-replay-deploy-plan"
DEFAULT_V2636_MANIFEST = ROOT / "workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json"
DEFAULT_V2675_RUN = ROOT / "workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431"
DEFAULT_PRIVATE_MANIFEST = ROOT / "workspace/private/builds/audio" / BUILD_TAG / "deploy-plan.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2677_AUDIO_ACDB_CUSTOM_TOPOLOGY_REPLAY_DEPLOY_PLAN_2026-06-18.md"
DEFAULT_REMOTE_DIR = "/cache/a90-acdb-setcal-replay-v2677"
CUSTOM_SEQUENCE = (24, 14)
CAL10_POLICY = "absent-not-capture-gap-per-v2676"


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


def local_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def verify_private_file(path: Path, *, expected_size: int | None = None, expected_sha256: str | None = None) -> dict[str, Any]:
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


def remote_basename_for_legacy(sequence: int, kind: str, cal_type: int) -> str:
    if kind == "set_arg":
        return f"{sequence:02d}-set-arg-cal{cal_type:02d}.bin"
    if kind == "payload":
        return f"{sequence:02d}-payload-cal{cal_type:02d}.bin"
    raise ValueError(f"unsupported legacy kind: {kind}")


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


def verified_from_existing(entry: dict[str, Any]) -> dict[str, Any]:
    local = entry.get("local") or {}
    path = local_path(local.get("local_path_private"))
    if path is None:
        return {
            "local_path_private": None,
            "exists": False,
            "ok": False,
            "size": None,
            "sha256": None,
            "nonzero": False,
            "size_matches": False,
            "sha256_matches": False,
            "private_only": True,
        }
    return verify_private_file(path, expected_size=local.get("size"), expected_sha256=local.get("sha256"))


def helper_entry_from_manifest(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    tool = payload.get("build", {}).get("tool", {})
    helper_path = local_path(tool.get("path"))
    if helper_path is None:
        raise ValueError(f"helper manifest lacks build.tool.path: {path}")
    return {
        "kind": "helper",
        "local": {
            "local_path_private": rel(helper_path),
            "size": tool.get("size"),
            "sha256": tool.get("sha256"),
            "private_only": True,
            "ok": True,
        },
        "remote_path": "",
        "ok": True,
        "source_helper_manifest": rel(path),
    }


def load_v2675_events(run_dir: Path) -> dict[int, dict[str, Any]]:
    events_path = run_dir / "ownget-device-artifacts/setcal-events.jsonl"
    events: dict[int, dict[str, Any]] = {}
    if not events_path.exists():
        return events
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        cal_type = int(event.get("cal_type", -1))
        if cal_type in CUSTOM_SEQUENCE:
            events[cal_type] = event
    return events


def custom_paths(run_dir: Path, event: dict[str, Any]) -> tuple[Path, Path]:
    artifacts = run_dir / "ownget-device-artifacts"
    arg_name = Path(str((event.get("set_arg") or {}).get("path") or "")).name
    payload_name = Path(str((event.get("dmabuf") or {}).get("path") or "")).name
    return artifacts / arg_name, artifacts / payload_name


def custom_entry(run_dir: Path, event: dict[str, Any], *, sequence: int, remote_dir: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cal_type = int(event["cal_type"])
    arg_path, payload_path = custom_paths(run_dir, event)
    arg_meta = event.get("set_arg") or {}
    payload_meta = event.get("dmabuf") or {}
    arg_file = deploy_file(
        "set_arg",
        verify_private_file(arg_path, expected_size=int(arg_meta.get("len")), expected_sha256=str(arg_meta.get("sha256"))),
        remote_join(remote_dir, f"{sequence:02d}-custom-set-arg-cal{cal_type:02d}.bin"),
    )
    payload_file = deploy_file(
        "payload",
        verify_private_file(payload_path, expected_size=int(payload_meta.get("len")), expected_sha256=str(payload_meta.get("sha256"))),
        remote_join(remote_dir, f"{sequence:02d}-custom-payload-cal{cal_type:02d}.bin"),
    )
    set_arg = {
        "sequence": sequence,
        "cal_type": cal_type,
        "role": "AFE_CUSTOM_TOPOLOGY_PAYLOAD" if cal_type == 24 else "ASM_CUSTOM_TOPOLOGY_PAYLOAD",
        "source": "V2675 acdb_loader_send_common_custom_topology SET capture",
        "dmabuf_expected": True,
        "arg_remote": arg_file["remote_path"],
        "payload_remote": payload_file["remote_path"],
        "ok": bool(arg_file.get("ok") and payload_file.get("ok")),
        "capture": {
            "request": event.get("request"),
            "data_size": event.get("data_size"),
            "cal_size": event.get("cal_size"),
            "mem_handle_captured": event.get("mem_handle"),
            "arg_sha256": arg_file["local"].get("sha256"),
            "payload_sha256": payload_file["local"].get("sha256"),
        },
    }
    return [arg_file, payload_file], set_arg


def legacy_entries(v2636: dict[str, Any], *, first_sequence: int, remote_dir: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files_by_remote = file_by_remote(v2636)
    files: list[dict[str, Any]] = []
    set_args: list[dict[str, Any]] = []
    for offset, item in enumerate(v2636.get("set_args") or [], start=0):
        sequence = first_sequence + offset
        cal_type = int(item.get("cal_type"))
        arg_source = files_by_remote[str(item["arg_remote"])]
        arg_file = deploy_file(
            "set_arg",
            verified_from_existing(arg_source),
            remote_join(remote_dir, remote_basename_for_legacy(sequence, "set_arg", cal_type)),
        )
        files.append(arg_file)
        payload_file: dict[str, Any] | None = None
        if item.get("payload_remote"):
            payload_source = files_by_remote[str(item["payload_remote"])]
            payload_file = deploy_file(
                "payload",
                verified_from_existing(payload_source),
                remote_join(remote_dir, remote_basename_for_legacy(sequence, "payload", cal_type)),
            )
            files.append(payload_file)
        set_args.append(
            {
                "sequence": sequence,
                "cal_type": cal_type,
                "role": item.get("role"),
                "source": "V2636 per-device SET replay manifest",
                "dmabuf_expected": bool(item.get("dmabuf_expected")),
                "arg_remote": arg_file["remote_path"],
                "payload_remote": payload_file["remote_path"] if payload_file else None,
                "ok": bool(arg_file.get("ok") and (payload_file is None or payload_file.get("ok"))),
            }
        )
    return files, set_args


def build_deploy_plan(
    v2636_manifest_path: Path,
    v2675_run_dir: Path,
    *,
    remote_dir: str = DEFAULT_REMOTE_DIR,
    helper_manifest_path: Path | None = None,
) -> dict[str, Any]:
    v2636 = read_json(v2636_manifest_path)
    old_files = file_by_remote(v2636)
    old_helper = next((item for item in v2636.get("files") or [] if item.get("kind") == "helper"), None)
    old_topology = next((item for item in v2636.get("files") or [] if item.get("kind") == "topology"), None)
    if not old_helper or not old_topology:
        raise ValueError("source V2636 manifest lacks helper or topology entries")
    helper_source_entry = helper_entry_from_manifest(helper_manifest_path) if helper_manifest_path else old_helper

    files: list[dict[str, Any]] = []
    helper_file = deploy_file(
        "helper",
        verified_from_existing(helper_source_entry),
        remote_join(remote_dir, "a90_acdb_setcal_replay_execute_v2635"),
        executable=True,
    )
    topology_file = deploy_file(
        "topology",
        verified_from_existing(old_topology),
        remote_join(remote_dir, "00-core_custom_topologies.bin"),
    )
    files.extend([helper_file, topology_file])

    events = load_v2675_events(v2675_run_dir)
    custom_set_args: list[dict[str, Any]] = []
    for sequence, cal_type in enumerate(CUSTOM_SEQUENCE, start=1):
        event = events.get(cal_type)
        if event is None:
            custom_set_args.append(
                {
                    "sequence": sequence,
                    "cal_type": cal_type,
                    "role": "MISSING_CUSTOM_TOPOLOGY_CAPTURE",
                    "source": "V2675 acdb_loader_send_common_custom_topology SET capture",
                    "dmabuf_expected": True,
                    "arg_remote": None,
                    "payload_remote": None,
                    "ok": False,
                }
            )
            continue
        custom_files, custom_arg = custom_entry(v2675_run_dir, event, sequence=sequence, remote_dir=remote_dir)
        files.extend(custom_files)
        custom_set_args.append(custom_arg)

    legacy_files, legacy_set_args = legacy_entries(v2636, first_sequence=len(CUSTOM_SEQUENCE) + 1, remote_dir=remote_dir)
    files.extend(legacy_files)
    set_args = custom_set_args + legacy_set_args

    argv = [helper_file["remote_path"], "--execute", "--basic-payload", f"39:0:{topology_file['remote_path']}"]
    for item in set_args:
        if not item.get("arg_remote"):
            continue
        spec = str(item["arg_remote"])
        if item.get("payload_remote"):
            spec += f":{item['payload_remote']}"
        argv.extend(["--exact-set", spec])
    argv.extend(["--hold-sec", str(int(v2636.get("hold_sec") or 10))])

    all_inputs_ok = bool(v2636.get("ok") and v2636.get("all_inputs_ok") and all(item.get("ok") for item in files) and all(item.get("ok") for item in set_args))
    expected_remote_args = 4 + (2 * len(set_args)) + 2
    blockers: list[str] = []
    if not all_inputs_ok:
        blockers.append("one or more source/custom topology inputs failed local size/hash/nonzero validation")
    if [item.get("cal_type") for item in custom_set_args] != list(CUSTOM_SEQUENCE):
        blockers.append("custom topology cal_type order is not 24 then 14")
    if len(argv) != expected_remote_args:
        blockers.append("remote argv does not include every custom and legacy SET entry")
    if 10 in [int(item.get("cal_type")) for item in set_args if item.get("cal_type") is not None]:
        blockers.append("cal_type 10 unexpectedly present despite V2676 absent-not-capture-gap policy")

    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "audio_playback_run": False,
        "source_v2636_manifest": rel(v2636_manifest_path),
        "source_helper_manifest": rel(helper_manifest_path) if helper_manifest_path else None,
        "source_v2675_run": rel(v2675_run_dir),
        "source_v2676_report": "docs/reports/NATIVE_INIT_V2676_AUDIO_ACDB_ADM_CUSTOM_TOPOLOGY_GET_RECON_2026-06-18.md",
        "custom_topology_overlay_cal_types": list(CUSTOM_SEQUENCE),
        "custom_topology_overlay_order": list(CUSTOM_SEQUENCE),
        "cal_type_10_policy": CAL10_POLICY,
        "operator_gate2_accepted": bool(v2636.get("operator_gate2_accepted")),
        "all_inputs_ok": all_inputs_ok,
        "native_replay_ready": False,
        "safe_to_run_native_replay": False,
        "replay_blockers": blockers + ["V2677 is a host-only deployment manifest overlay, not a live replay run"],
        "remote_dir": remote_dir,
        "hold_sec": int(v2636.get("hold_sec") or 10),
        "files": files,
        "files_redacted": [redacted_file(item) for item in files],
        "set_args": set_args,
        "remote_argv": argv,
        "remote_preflight": {
            "mkdir": f"mkdir -p {remote_dir}",
            "verify_sha256_count": len(files),
            "cleanup": f"rm -rf {remote_dir}",
        },
        "summary": {
            "decision": "v2677-custom-topology-replay-deploy-plan-ready" if all_inputs_ok and not blockers else "v2677-custom-topology-replay-deploy-plan-blocked",
            "file_count": len(files),
            "set_arg_count": len(set_args),
            "payload_file_count": sum(1 for item in files if item.get("kind") == "payload"),
            "remote_arg_count": len(argv),
            "replay_entry_count": 1 + len(set_args),
            "final_set_index": len(set_args),
            "custom_topology_overlay_cal_types": list(CUSTOM_SEQUENCE),
        },
        "ok": bool(all_inputs_ok and not blockers),
    }


def write_report(path: Path, manifest: dict[str, Any], private_manifest_path: Path) -> None:
    lines = [
        "# NATIVE_INIT V2677 — ACDB custom-topology replay deploy plan",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only construction of a V2639-compatible replay deployment manifest",
        "that prepends the V2675 custom-topology SET captures before the existing",
        "V2636 per-device SET sequence. No device action, flash, calibration ioctl,",
        "or PCM probe occurred.",
        "",
        "## Result",
        "",
        f"- decision: `{manifest['summary']['decision']}`",
        f"- ok: `{manifest.get('ok')}`",
        f"- all_inputs_ok: `{manifest.get('all_inputs_ok')}`",
        f"- private_manifest: `{rel(private_manifest_path)}`",
        f"- source_v2636_manifest: `{manifest.get('source_v2636_manifest')}`",
        f"- source_helper_manifest: `{manifest.get('source_helper_manifest')}`",
        f"- source_v2675_run: `{manifest.get('source_v2675_run')}`",
        f"- source_v2676_report: `{manifest.get('source_v2676_report')}`",
        f"- remote_dir: `{manifest.get('remote_dir')}`",
        f"- file_count: `{manifest['summary'].get('file_count')}`",
        f"- replay_entry_count: `{manifest['summary'].get('replay_entry_count')}`",
        f"- final_set_index: `{manifest['summary'].get('final_set_index')}`",
        f"- custom_topology_overlay_cal_types: `{manifest.get('custom_topology_overlay_cal_types')}`",
        f"- cal_type_10_policy: `{manifest.get('cal_type_10_policy')}`",
        "",
        "## Replay Order",
        "",
        "| entry | cal_type | role | payload | source | ok |",
        "| ---: | ---: | --- | --- | --- | --- |",
        "| 0 | 39 | CORE_CUSTOM_TOPOLOGIES basic payload | yes | V2547/V2636 | true |",
    ]
    for index, item in enumerate(manifest.get("set_args") or [], start=1):
        lines.append(
            f"| {index} | {item.get('cal_type')} | `{item.get('role')}` | "
            f"`{bool(item.get('payload_remote'))}` | `{item.get('source')}` | `{item.get('ok')}` |"
        )
    lines.extend(
        [
            "",
            "## Redacted Files",
            "",
            "| kind | remote | size | sha256 | ok |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for item in manifest.get("files_redacted", []):
        local = item.get("local") or {}
        lines.append(
            f"| `{item.get('kind')}` | `{item.get('remote_path')}` | {local.get('size')} | "
            f"`{local.get('sha256')}` | `{item.get('ok')}` |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Cal_type 24 and 14 are replayed in the exact V2675 capture order.",
            "- Cal_type 10 is intentionally absent per V2676: Android-good V2461 did not emit a SET record for 10, and V2675 lower GET returned `-12` for 10 while 24/14 returned `0`.",
            "- The next live unit can pass this private manifest to the V2639 runner after V2638 accepts variable replay counts.",
            "",
            "## Blockers",
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
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_custom_topology_replay_deploy_plan_v2677.py tests/test_native_audio_acdb_custom_topology_replay_deploy_plan_v2677.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_custom_topology_replay_deploy_plan_v2677 tests.test_native_audio_acdb_setcal_replay_live_runner_plan_v2638 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_custom_topology_replay_deploy_plan_v2677.py --write-report`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py --v2636-manifest workspace/private/builds/audio/v2677-audio-acdb-custom-topology-replay-deploy-plan/deploy-plan.json --write-report --private-manifest workspace/private/builds/audio/v2677-audio-acdb-custom-topology-replay-deploy-plan/runner-plan.json --report workspace/private/builds/audio/v2677-audio-acdb-custom-topology-replay-deploy-plan/runner-plan-report.md`",
            "- `git diff --check`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2636-manifest", type=Path, default=DEFAULT_V2636_MANIFEST)
    parser.add_argument("--helper-manifest", type=Path)
    parser.add_argument("--v2675-run", type=Path, default=DEFAULT_V2675_RUN)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--private-manifest", type=Path, default=DEFAULT_PRIVATE_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_deploy_plan(
        args.v2636_manifest,
        args.v2675_run,
        remote_dir=args.remote_dir,
        helper_manifest_path=args.helper_manifest,
    )
    manifest["private_manifest_path"] = rel(args.private_manifest)
    write_json(args.private_manifest, manifest, mode=0o600)
    if args.write_report:
        write_report(args.report, manifest, args.private_manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
