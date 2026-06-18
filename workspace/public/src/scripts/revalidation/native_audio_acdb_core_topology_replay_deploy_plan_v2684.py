#!/usr/bin/env python3
"""V2684 host-only deploy plan for core-derived ACDB topology replay.

Builds a V2639-compatible replay manifest using V2683 private candidate
payloads generated from the 4916-byte CORE_CUSTOM_TOPOLOGIES graph:

  entry 0: existing cal_type 39 core payload
  entry 1: generated cal_type 10 ADM topology 0x10004000 via --basic-payload
  entry 2: generated cal_type 14 ASM topology 0x10005000 via --basic-payload
  entry 3: existing captured cal_type 24 AFE custom-topology SET
  entries 4+: existing V2679 per-device SET sequence, excluding the stale cal14

No device action occurs here.
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
RUN_ID = "V2684"
BUILD_TAG = "v2684-acdb-core-topology-replay-deploy-plan"
DEFAULT_BASE_MANIFEST = ROOT / "workspace/private/builds/audio/v2679-acdb-custom-topology-replay-deploy-plan/deploy-plan.json"
DEFAULT_CANDIDATE_DIR = ROOT / "workspace/private/builds/audio/v2683-acdb-core-topology-candidates"
DEFAULT_PRIVATE_MANIFEST = ROOT / "workspace/private/builds/audio" / BUILD_TAG / "deploy-plan.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2684_AUDIO_ACDB_CORE_TOPOLOGY_REPLAY_DEPLOY_PLAN_2026-06-18.md"
DEFAULT_REMOTE_DIR = "/cache/a90-acdb-setcal-replay-v2684"
CANDIDATES = {
    10: {
        "role": "ADM_CUSTOM_TOPOLOGY_FROM_CORE_SELECTED_0x10004000",
        "filename": "cal10-topology-0x10004000-from-core-fixed.bin",
        "topology_id": 0x10004000,
        "expected_sha256": "4fbf08cad1e937fa20c15268e6af2e2e459f872a5daeb53f3dbe9590d3eb9f35",
        "expected_size": 396,
    },
    14: {
        "role": "ASM_CUSTOM_TOPOLOGY_FROM_CORE_SELECTED_0x10005000",
        "filename": "cal14-topology-0x10005000-from-core-fixed.bin",
        "topology_id": 0x10005000,
        "expected_sha256": "984b31dd690f51e10697e4356830bbc3bf9a5db944470d1d62accc190d196487",
        "expected_size": 396,
    },
}
STALE_REPLACED_CAL_TYPES = {14}
CAPTURED_KEEP_CAL_TYPES = {24}


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


def local_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def verify_file(path: Path, *, expected_size: int | None = None, expected_sha256: str | None = None) -> dict[str, Any]:
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
    state.update({
        "size": size,
        "sha256": digest,
        "nonzero": not is_all_zero(path),
        "size_matches": expected_size is None or size == expected_size,
        "sha256_matches": expected_sha256 is None or digest == expected_sha256,
        "mode": oct(path.stat().st_mode & 0o777),
    })
    state["ok"] = bool(state["nonzero"] and state["size_matches"] and state["sha256_matches"])
    return state


def verify_existing_local(entry: dict[str, Any]) -> dict[str, Any]:
    local = entry.get("local") or {}
    path = local_path(local.get("local_path_private"))
    if path is None:
        return verify_file(Path("/nonexistent/a90-missing"))
    return verify_file(path, expected_size=local.get("size"), expected_sha256=local.get("sha256"))


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


def remote_join(remote_dir: str, name: str) -> str:
    return remote_dir.rstrip("/") + "/" + name


def file_by_remote(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item.get("remote_path")): item for item in manifest.get("files") or [] if item.get("remote_path")}


def basic_payload_arg(cal_type: int, buffer_number: int, remote_payload: str) -> str:
    return f"{cal_type}:{buffer_number}:{remote_payload}"


def exact_arg_spec(arg_remote: str, payload_remote: str | None) -> str:
    return f"{arg_remote}:{payload_remote}" if payload_remote else arg_remote


def copy_exact_set_entry(base: dict[str, Any], files_by_remote: dict[str, dict[str, Any]], item: dict[str, Any], *, sequence: int, remote_dir: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _ = base
    cal_type = int(item["cal_type"])
    arg_source = files_by_remote[str(item["arg_remote"])]
    arg_file = deploy_file(
        "set_arg",
        verify_existing_local(arg_source),
        remote_join(remote_dir, f"{sequence:02d}-set-arg-cal{cal_type:02d}.bin"),
    )
    files = [arg_file]
    payload_file = None
    if item.get("payload_remote"):
        payload_source = files_by_remote[str(item["payload_remote"])]
        payload_file = deploy_file(
            "payload",
            verify_existing_local(payload_source),
            remote_join(remote_dir, f"{sequence:02d}-payload-cal{cal_type:02d}.bin"),
        )
        files.append(payload_file)
    copied = {
        "sequence": sequence,
        "entry_kind": "exact-set",
        "cal_type": cal_type,
        "role": item.get("role"),
        "source": item.get("source"),
        "dmabuf_expected": bool(item.get("dmabuf_expected")),
        "arg_remote": arg_file["remote_path"],
        "payload_remote": payload_file["remote_path"] if payload_file else None,
        "ok": bool(arg_file.get("ok") and (payload_file is None or payload_file.get("ok"))),
    }
    return files, copied


def build_deploy_plan(base_manifest_path: Path, candidate_dir: Path, *, remote_dir: str = DEFAULT_REMOTE_DIR) -> dict[str, Any]:
    base = read_json(base_manifest_path)
    files_by = file_by_remote(base)
    old_helper = next((item for item in base.get("files") or [] if item.get("kind") == "helper"), None)
    old_topology = next((item for item in base.get("files") or [] if item.get("kind") == "topology"), None)
    if not old_helper or not old_topology:
        raise ValueError("base manifest lacks helper/topology file entries")

    files: list[dict[str, Any]] = []
    replay_entries: list[dict[str, Any]] = []

    helper_file = deploy_file(
        "helper",
        verify_existing_local(old_helper),
        remote_join(remote_dir, "a90_acdb_setcal_replay_execute_v2635"),
        executable=True,
    )
    core_file = deploy_file(
        "topology",
        verify_existing_local(old_topology),
        remote_join(remote_dir, "00-core_custom_topologies.bin"),
    )
    files.extend([helper_file, core_file])
    replay_entries.append({
        "sequence": 0,
        "entry_kind": "basic-payload",
        "cal_type": 39,
        "role": "CORE_CUSTOM_TOPOLOGIES",
        "source": "V2547/V2679 core custom topology payload",
        "payload_remote": core_file["remote_path"],
        "ok": bool(core_file.get("ok")),
    })

    sequence = 1
    for cal_type in (10, 14):
        meta = CANDIDATES[cal_type]
        candidate_path = candidate_dir / str(meta["filename"])
        candidate_file = deploy_file(
            "payload",
            verify_file(candidate_path, expected_size=int(meta["expected_size"]), expected_sha256=str(meta["expected_sha256"])),
            remote_join(remote_dir, f"{sequence:02d}-core-derived-payload-cal{cal_type:02d}-topo{meta['topology_id']:08x}.bin"),
        )
        files.append(candidate_file)
        replay_entries.append({
            "sequence": sequence,
            "entry_kind": "basic-payload",
            "cal_type": cal_type,
            "role": meta["role"],
            "source": "V2683 core-to-fixed generated private candidate",
            "topology_id": meta["topology_id"],
            "payload_remote": candidate_file["remote_path"],
            "ok": bool(candidate_file.get("ok")),
        })
        sequence += 1

    base_set_args = list(base.get("set_args") or [])
    for wanted in (24,):
        item = next((entry for entry in base_set_args if int(entry.get("cal_type")) == wanted), None)
        if item is None:
            replay_entries.append({"sequence": sequence, "entry_kind": "missing", "cal_type": wanted, "role": "MISSING_CAPTURED_AFE_CUSTOM_TOPOLOGY", "ok": False})
            sequence += 1
            continue
        copied_files, copied = copy_exact_set_entry(base, files_by, item, sequence=sequence, remote_dir=remote_dir)
        copied["source"] = "V2679 captured cal24 retained; V2683 proved it matches selected AFE topology"
        files.extend(copied_files)
        replay_entries.append(copied)
        sequence += 1

    for item in base_set_args:
        cal_type = int(item.get("cal_type"))
        if cal_type in STALE_REPLACED_CAL_TYPES or cal_type in CAPTURED_KEEP_CAL_TYPES:
            continue
        copied_files, copied = copy_exact_set_entry(base, files_by, item, sequence=sequence, remote_dir=remote_dir)
        files.extend(copied_files)
        replay_entries.append(copied)
        sequence += 1

    argv = [helper_file["remote_path"], "--execute"]
    for item in replay_entries:
        if item.get("entry_kind") == "basic-payload":
            argv.extend(["--basic-payload", basic_payload_arg(int(item["cal_type"]), 0, str(item["payload_remote"]))])
        elif item.get("entry_kind") == "exact-set":
            argv.extend(["--exact-set", exact_arg_spec(str(item["arg_remote"]), item.get("payload_remote"))])
    argv.extend(["--hold-sec", str(int(base.get("hold_sec") or 10))])

    cal_order = [int(item.get("cal_type")) for item in replay_entries if item.get("cal_type") is not None]
    blockers: list[str] = []
    if cal_order[:4] != [39, 10, 14, 24]:
        blockers.append(f"unexpected leading topology cal order: {cal_order[:4]}")
    if 14 in [int(item.get("cal_type")) for item in base_set_args[:2]] and any(item.get("source") == "V2675 acdb_loader_send_common_custom_topology SET capture" and int(item.get("cal_type")) == 14 for item in replay_entries):
        blockers.append("stale V2675 cal14 exact payload was not removed")
    all_inputs_ok = bool(base.get("ok") and base.get("all_inputs_ok") and all(item.get("ok") for item in files) and all(item.get("ok") for item in replay_entries))
    if not all_inputs_ok:
        blockers.append("one or more deployment inputs failed local validation")

    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "audio_playback_run": False,
        "source_base_manifest": rel(base_manifest_path),
        "source_v2683_candidate_dir": rel(candidate_dir),
        "variant": "minimal-core-selected-topologies",
        "all_inputs_ok": all_inputs_ok,
        "native_replay_ready": bool(all_inputs_ok and not blockers),
        "safe_to_run_native_replay": bool(all_inputs_ok and not blockers),
        "replay_blockers": blockers,
        "operator_gate2_accepted": True,
        "remote_dir": remote_dir,
        "hold_sec": int(base.get("hold_sec") or 10),
        "files": files,
        "files_redacted": [redacted_file(item) for item in files],
        "replay_entries": replay_entries,
        "set_args": [item for item in replay_entries if item.get("entry_kind") == "exact-set"],
        "basic_payloads": [item for item in replay_entries if item.get("entry_kind") == "basic-payload"],
        "remote_argv": argv,
        "remote_preflight": {
            "mkdir": f"mkdir -p {remote_dir}",
            "verify_sha256_count": len(files),
            "cleanup": f"rm -rf {remote_dir}",
        },
        "summary": {
            "decision": "v2684-core-topology-replay-deploy-plan-ready" if all_inputs_ok and not blockers else "v2684-core-topology-replay-deploy-plan-blocked",
            "file_count": len(files),
            "remote_arg_count": len(argv),
            "replay_entry_count": len(replay_entries),
            "final_set_index": len(replay_entries) - 1,
            "cal_order": cal_order,
        },
        "ok": bool(all_inputs_ok and not blockers),
    }


def write_report(path: Path, manifest: dict[str, Any], private_manifest_path: Path) -> None:
    lines = [
        "# NATIVE_INIT V2684 — ACDB core-topology replay deploy plan",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only construction of a V2639-compatible replay manifest using V2683 core-derived fixed topology candidates. No device action, flash, calibration ioctl, or PCM probe occurred.",
        "",
        "## Result",
        "",
        f"- decision: `{manifest['summary']['decision']}`",
        f"- ok: `{manifest.get('ok')}`",
        f"- all_inputs_ok: `{manifest.get('all_inputs_ok')}`",
        f"- native_replay_ready: `{manifest.get('native_replay_ready')}`",
        f"- private_manifest: `{rel(private_manifest_path)}`",
        f"- source_base_manifest: `{manifest.get('source_base_manifest')}`",
        f"- source_v2683_candidate_dir: `{manifest.get('source_v2683_candidate_dir')}`",
        f"- remote_dir: `{manifest.get('remote_dir')}`",
        f"- cal_order: `{manifest['summary'].get('cal_order')}`",
        f"- final_set_index: `{manifest['summary'].get('final_set_index')}`",
        "",
        "## Replay Order",
        "",
        "| entry | kind | cal_type | role | payload | source | ok |",
        "| ---: | --- | ---: | --- | --- | --- | --- |",
    ]
    for item in manifest.get("replay_entries") or []:
        lines.append(
            f"| {item.get('sequence')} | `{item.get('entry_kind')}` | {item.get('cal_type')} | `{item.get('role')}` | "
            f"`{bool(item.get('payload_remote'))}` | `{item.get('source')}` | `{item.get('ok')}` |"
        )
    lines.extend([
        "",
        "## Redacted Files",
        "",
        "| kind | remote | size | sha256 | ok |",
        "| --- | --- | ---: | --- | --- |",
    ])
    for item in manifest.get("files_redacted") or []:
        local = item.get("local") or {}
        lines.append(f"| `{item.get('kind')}` | `{item.get('remote_path')}` | {local.get('size')} | `{local.get('sha256')}` | `{item.get('ok')}` |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "This plan replaces the stale V2675 lower-hidden cal_type `14` payload with a V2683 core-derived fixed payload defining the selected ASM topology `0x10005000`, and adds the missing ADM custom topology cal_type `10` for selected topology `0x10004000`. The captured cal_type `24` payload is retained because V2683 proved it already matches selected AFE topology `0x1001025d`.",
        "",
        "The manifest is ready for one V2639 live replay under the existing recoverable-envelope policy. It is not itself a device action.",
        "",
        "## Blockers",
        "",
    ])
    for blocker in manifest.get("replay_blockers") or []:
        lines.append(f"- {blocker}")
    if not manifest.get("replay_blockers"):
        lines.append("- none")
    lines.extend([
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_core_topology_replay_deploy_plan_v2684.py tests/test_native_audio_acdb_core_topology_replay_deploy_plan_v2684.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_core_topology_replay_deploy_plan_v2684 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_core_topology_replay_deploy_plan_v2684.py --write-report`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`",
        "- `git diff --check`",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE_MANIFEST)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--private-manifest", type=Path, default=DEFAULT_PRIVATE_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_deploy_plan(args.base_manifest, args.candidate_dir, remote_dir=args.remote_dir)
    manifest["private_manifest_path"] = rel(args.private_manifest)
    write_json(args.private_manifest, manifest, mode=0o600)
    if args.write_report:
        write_report(args.report, manifest, args.private_manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
