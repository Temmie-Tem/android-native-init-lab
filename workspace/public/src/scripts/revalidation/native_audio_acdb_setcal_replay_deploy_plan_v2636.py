#!/usr/bin/env python3
"""V2636 host-only deployment plan for exact SET-cal native replay.

Consumes the V2635 helper-gate manifest and the V2634 SET-layer replay gate,
verifies every private local input, and emits a deterministic private staging
manifest: helper, topology payload, exact SET args, payload dmabufs, remote
runtime paths, remote SHA checks, and the future helper argv.

This does not run the device, does not stage files, and does not authorize live
native replay. Operator Gate-2 acceptance remains required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2636"
BUILD_TAG = "v2636-audio-acdb-setcal-replay-deploy-plan"
DEFAULT_V2635_MANIFEST = ROOT / "workspace/private/builds/audio/v2635-audio-acdb-setcal-replay-helper-gate/manifest.json"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_PRIVATE_MANIFEST = DEFAULT_BUILD_ROOT / "deploy-plan.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2636_AUDIO_ACDB_SETCAL_REPLAY_DEPLOY_PLAN_2026-06-18.md"
DEFAULT_REMOTE_DIR = "/cache/a90-acdb-setcal-replay-v2636"
DEFAULT_HOLD_SEC = 10
FUTURE_LIVE_GATE = (
    "AUD-5Q-native-acdb-setcal-replay go: one-shot Gate-2 accepted SET-layer "
    "ACDB replay, exact captured SET args, no smart-amp gain changes, bounded "
    "PCM probe, reverse deallocate cleanup, rollback to V2321"
)


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


def verify_file(path_value: str | None, *, expected_size: int | None, expected_sha256: str | None) -> dict[str, Any]:
    path = local_path(path_value)
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
    output = dict(entry)
    local = dict(output.get("local") or {})
    local.pop("local_path_private", None)
    output["local"] = local
    return output


def build_deploy_plan(v2635_manifest_path: Path, *, remote_dir: str = DEFAULT_REMOTE_DIR, hold_sec: int = DEFAULT_HOLD_SEC) -> dict[str, Any]:
    v2635 = read_json(v2635_manifest_path)
    v2634_path_value = v2635.get("v2634_manifest", {}).get("path")
    v2634_path = local_path(v2634_path_value)
    if v2634_path is None:
        raise FileNotFoundError("V2635 manifest does not point to a V2634 manifest")
    v2634 = read_json(v2634_path)

    files: list[dict[str, Any]] = []
    helper = v2635.get("build", {}).get("tool", {})
    helper_file = deploy_file(
        "helper",
        verify_file(helper.get("path"), expected_size=helper.get("size"), expected_sha256=helper.get("sha256")),
        remote_join(remote_dir, "a90_acdb_setcal_replay_execute_v2635"),
        executable=True,
    )
    files.append(helper_file)

    topology = v2634.get("topology", {})
    topology_file = deploy_file(
        "topology",
        verify_file(topology.get("path_private"), expected_size=topology.get("size"), expected_sha256=topology.get("sha256")),
        remote_join(remote_dir, "00-core_custom_topologies.bin"),
    )
    files.append(topology_file)

    set_args: list[dict[str, Any]] = []
    for record in v2634.get("set_records", []):
        sequence = int(record.get("sequence"))
        cal_type = int(record.get("cal_type"))
        arg = record.get("arg", {}) if isinstance(record.get("arg"), dict) else {}
        dmabuf = record.get("dmabuf", {}) if isinstance(record.get("dmabuf"), dict) else {}
        arg_file = deploy_file(
            "set_arg",
            verify_file(arg.get("path_private"), expected_size=arg.get("size"), expected_sha256=arg.get("sha256")),
            remote_join(remote_dir, f"{sequence:02d}-set-arg-cal{cal_type:02d}.bin"),
        )
        files.append(arg_file)
        payload_file: dict[str, Any] | None = None
        if record.get("dmabuf_expected"):
            payload_file = deploy_file(
                "payload",
                verify_file(dmabuf.get("path_private"), expected_size=dmabuf.get("size"), expected_sha256=dmabuf.get("sha256")),
                remote_join(remote_dir, f"{sequence:02d}-payload-cal{cal_type:02d}.bin"),
            )
            files.append(payload_file)
        set_args.append(
            {
                "sequence": sequence,
                "cal_type": cal_type,
                "role": record.get("role"),
                "dmabuf_expected": bool(record.get("dmabuf_expected")),
                "arg_remote": arg_file["remote_path"],
                "payload_remote": payload_file["remote_path"] if payload_file else None,
                "ok": bool(arg_file.get("ok") and (payload_file is None or payload_file.get("ok"))),
            }
        )

    helper_remote = helper_file["remote_path"]
    argv = [helper_remote, "--execute", "--basic-payload", f"39:0:{topology_file['remote_path']}"]
    for item in set_args:
        value = item["arg_remote"] if not item["payload_remote"] else f"{item['arg_remote']}:{item['payload_remote']}"
        argv.extend(["--exact-set", value])
    argv.extend(["--hold-sec", str(int(hold_sec))])

    all_inputs_ok = bool(v2635.get("ok") and v2634.get("ok") and all(item.get("ok") for item in files) and all(item.get("ok") for item in set_args))
    operator_accepted = bool(v2635.get("v2634_manifest", {}).get("operator_gate2_accepted") or v2634.get("operator_gate2_accepted"))
    blockers = []
    if not operator_accepted:
        blockers.append("operator Gate-2 has not accepted the V2633/V2634 SET-layer package")
    blockers.append("V2636 is a host-only deployment plan, not a live native replay approval")
    if not all_inputs_ok:
        blockers.append("one or more deployment inputs failed local hash/size/nonzero validation")

    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "audio_playback_run": False,
        "source_v2635_manifest": rel(v2635_manifest_path),
        "source_v2634_manifest": rel(v2634_path),
        "operator_gate2_accepted": operator_accepted,
        "all_inputs_ok": all_inputs_ok,
        "native_replay_ready": False,
        "safe_to_run_native_replay": False,
        "replay_blockers": blockers,
        "remote_dir": remote_dir,
        "hold_sec": int(hold_sec),
        "files": files,
        "files_redacted": [redacted_file(item) for item in files],
        "set_args": set_args,
        "remote_argv": argv,
        "future_live_gate": FUTURE_LIVE_GATE,
        "remote_preflight": {
            "mkdir": f"mkdir -p {remote_dir}",
            "chmod_helper": f"chmod 0700 {helper_remote}",
            "verify_sha256_count": len(files),
            "cleanup": f"rm -rf {remote_dir}",
        },
        "summary": {
            "decision": "v2636-setcal-replay-deploy-plan-ready" if all_inputs_ok else "v2636-setcal-replay-deploy-plan-blocked",
            "file_count": len(files),
            "set_arg_count": len(set_args),
            "payload_file_count": sum(1 for item in files if item.get("kind") == "payload"),
            "remote_arg_count": len(argv),
        },
        "ok": all_inputs_ok,
    }


def write_report(path: Path, manifest: dict[str, Any], private_manifest_path: Path) -> None:
    lines = [
        "# NATIVE_INIT V2636 — ACDB SET-cal replay deployment plan",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only deployment plan for the future exact SET-cal native replay. This",
        "unit verifies private local helper/payload inputs and fixes deterministic",
        "remote runtime paths plus the future helper argv.",
        "",
        "No device action, transfer, flash, `/dev/msm_audio_cal` ioctl, PCM probe,",
        "or raw payload publication occurred.",
        "",
        "## Result",
        "",
        f"- decision: `{manifest['summary']['decision']}`",
        f"- ok: `{manifest.get('ok')}`",
        f"- all_inputs_ok: `{manifest.get('all_inputs_ok')}`",
        f"- source_v2635_manifest: `{manifest.get('source_v2635_manifest')}`",
        f"- source_v2634_manifest: `{manifest.get('source_v2634_manifest')}`",
        f"- private_manifest: `{rel(private_manifest_path)}`",
        f"- remote_dir: `{manifest.get('remote_dir')}`",
        f"- file_count: `{manifest['summary'].get('file_count')}`",
        f"- set_arg_count: `{manifest['summary'].get('set_arg_count')}`",
        f"- payload_file_count: `{manifest['summary'].get('payload_file_count')}`",
        f"- native_replay_ready: `{manifest.get('native_replay_ready')}`",
        f"- safe_to_run_native_replay: `{manifest.get('safe_to_run_native_replay')}`",
        "",
        "## Redacted Deployment Files",
        "",
        "| kind | remote | size | sha256 | ok |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for item in manifest.get("files_redacted", []):
        local = item.get("local", {})
        lines.append(
            f"| `{item.get('kind')}` | `{item.get('remote_path')}` | {local.get('size')} | "
            f"`{local.get('sha256')}` | `{item.get('ok')}` |"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "- V2636 is a deployment plan only; it is not a live replay approval.",
            "- Native replay remains blocked until operator Gate-2 accepts the V2633/V2634 SET-layer package.",
            "- The future live runner must stage these files, verify SHA-256 on-device, run the helper,",
            "  run one bounded PCM probe while fds are held, then clean up and roll back to V2321.",
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
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_deploy_plan_v2636.py tests/test_native_audio_acdb_setcal_replay_deploy_plan_v2636.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_deploy_plan_v2636 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_deploy_plan_v2636.py --write-report`",
            "- `git diff --check`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2635-manifest", type=Path, default=DEFAULT_V2635_MANIFEST)
    parser.add_argument("--private-manifest", type=Path, default=DEFAULT_PRIVATE_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--hold-sec", type=int, default=DEFAULT_HOLD_SEC)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    manifest = build_deploy_plan(args.v2635_manifest, remote_dir=args.remote_dir, hold_sec=args.hold_sec)
    manifest["private_manifest_path"] = rel(args.private_manifest)
    write_json(args.private_manifest, manifest, mode=0o600)
    if args.write_report:
        write_report(args.report, manifest, args.private_manifest)
    print(json.dumps({
        "decision": manifest["summary"]["decision"],
        "ok": manifest["ok"],
        "private_manifest": rel(args.private_manifest),
        "report": rel(args.report) if args.write_report else None,
        "file_count": manifest["summary"]["file_count"],
        "remote_arg_count": manifest["summary"]["remote_arg_count"],
        "safe_to_run_native_replay": manifest["safe_to_run_native_replay"],
        "replay_blockers": manifest["replay_blockers"],
    }, indent=2, sort_keys=True))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
