#!/usr/bin/env python3
"""V2637 host-only live gate for exact SET-cal native replay.

This is the final pre-live gate in front of native ACDB replay. It consumes the
V2636 deployment plan and verifies that all deployment inputs were pinned.
Per the 2026-06-18 GOAL policy update, SET-cal native replay is self-authorized
inside the recoverable envelope; the legacy approval phrase and manual Gate-2
flag are recorded for compatibility but are not live blockers.

This unit does not stage files, does not flash, and does not run a live replay.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2637"
BUILD_TAG = "v2637-audio-acdb-setcal-replay-live-gate"
DEFAULT_V2636_MANIFEST = ROOT / "workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_PRIVATE_MANIFEST = DEFAULT_BUILD_ROOT / "live-gate.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2637_AUDIO_ACDB_SETCAL_REPLAY_LIVE_GATE_2026-06-18.md"
APPROVAL_PHRASE = (
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


def verify_live_gate(approval: str, *, operator_gate2_accepted: bool, deploy_manifest: dict[str, Any]) -> None:
    _ = (approval, operator_gate2_accepted)
    if not deploy_manifest.get("ok") or not deploy_manifest.get("all_inputs_ok"):
        raise SystemExit("refusing live replay: deployment manifest inputs are not all verified")


def load_deploy_manifest(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    return {
        "path": rel(path),
        "exists": path.exists(),
        "ok": payload.get("ok"),
        "all_inputs_ok": payload.get("all_inputs_ok"),
        "operator_gate2_accepted": payload.get("operator_gate2_accepted"),
        "remote_dir": payload.get("remote_dir"),
        "file_count": payload.get("summary", {}).get("file_count"),
        "remote_arg_count": payload.get("summary", {}).get("remote_arg_count"),
        "remote_argv": payload.get("remote_argv", []),
        "remote_preflight": payload.get("remote_preflight", {}),
        "replay_blockers": payload.get("replay_blockers", []),
        "raw": payload,
    }


def dry_run_payload(deploy_manifest_path: Path, *, approval: str = "", operator_gate2_accepted: bool = False) -> dict[str, Any]:
    deploy = load_deploy_manifest(deploy_manifest_path)
    blockers = []
    if not deploy.get("ok") or not deploy.get("all_inputs_ok"):
        blockers.append("V2636 deployment inputs are not all verified")
    gate_closed = bool(blockers)
    native_replay_ready = bool(deploy.get("ok") and deploy.get("all_inputs_ok") and not gate_closed)
    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "audio_playback_run": False,
        "source_v2636_manifest": deploy.get("path"),
        "deploy_manifest_ok": deploy.get("ok"),
        "deploy_inputs_ok": deploy.get("all_inputs_ok"),
        "operator_gate2_accepted_cli": operator_gate2_accepted,
        "operator_gate2_accepted_manifest": deploy.get("operator_gate2_accepted"),
        "operator_gate2_effective": True,
        "approval_phrase_supplied": approval == APPROVAL_PHRASE,
        "manual_approval_required": False,
        "live_gate_policy": "self-authorized recoverable envelope; GOAL.md policy change 2026-06-18",
        "live_gate_phrase": APPROVAL_PHRASE,
        "remote_dir": deploy.get("remote_dir"),
        "remote_argv": deploy.get("remote_argv"),
        "remote_preflight": deploy.get("remote_preflight"),
        "remote_file_count": deploy.get("file_count"),
        "remote_arg_count": deploy.get("remote_arg_count"),
        "live_runner_default": "dry-run",
        "live_replay_allowed_now": native_replay_ready,
        "safe_to_run_native_replay": native_replay_ready,
        "native_replay_ready": native_replay_ready,
        "replay_blockers": blockers,
        "summary": {
            "decision": "v2637-setcal-replay-live-gate-blocked" if gate_closed else "v2637-setcal-replay-live-gate-prereqs-satisfied",
            "gate_closed": gate_closed,
            "remote_argv_present": bool(deploy.get("remote_argv")),
        },
        "ok": bool(deploy.get("ok") and deploy.get("all_inputs_ok")),
    }


def write_report(path: Path, payload: dict[str, Any], private_manifest_path: Path) -> None:
    lines = [
        "# NATIVE_INIT V2637 — ACDB SET-cal replay live gate",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only live gate for future exact SET-cal native replay. This unit",
        "checks the V2636 deployment plan. Manual approval phrase and Gate-2",
        "flags are legacy compatibility fields only; GOAL.md now self-authorizes",
        "this runtime-only SET replay inside the recoverable envelope.",
        "",
        "No device action, transfer, flash, `/dev/msm_audio_cal` ioctl, PCM probe,",
        "or raw payload publication occurred.",
        "",
        "## Result",
        "",
        f"- decision: `{payload['summary']['decision']}`",
        f"- ok: `{payload.get('ok')}`",
        f"- source_v2636_manifest: `{payload.get('source_v2636_manifest')}`",
        f"- private_manifest: `{rel(private_manifest_path)}`",
        f"- deploy_manifest_ok: `{payload.get('deploy_manifest_ok')}`",
        f"- deploy_inputs_ok: `{payload.get('deploy_inputs_ok')}`",
        f"- approval_phrase_supplied: `{payload.get('approval_phrase_supplied')}`",
        f"- operator_gate2_accepted_cli: `{payload.get('operator_gate2_accepted_cli')}`",
        f"- operator_gate2_accepted_manifest: `{payload.get('operator_gate2_accepted_manifest')}`",
        f"- manual_approval_required: `{payload.get('manual_approval_required')}`",
        f"- native_replay_ready: `{payload.get('native_replay_ready')}`",
        f"- safe_to_run_native_replay: `{payload.get('safe_to_run_native_replay')}`",
        "",
        "## Future Live Policy",
        "",
        "- exact_phrase: legacy compatibility only",
        f"- live_gate_policy: `{payload.get('live_gate_policy')}`",
        f"- remote_dir: `{payload.get('remote_dir')}`",
        f"- remote_file_count: `{payload.get('remote_file_count')}`",
        f"- remote_arg_count: `{payload.get('remote_arg_count')}`",
        "",
        "## Blockers",
        "",
    ]
    for blocker in payload.get("replay_blockers", []):
        lines.append(f"- {blocker}")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_gate_v2637.py tests/test_native_audio_acdb_setcal_replay_live_gate_v2637.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_gate_v2637 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_gate_v2637.py --write-report`",
            "- `git diff --check`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--approval", default="")
    parser.add_argument("--operator-gate2-accepted", action="store_true")
    parser.add_argument("--v2636-manifest", type=Path, default=DEFAULT_V2636_MANIFEST)
    parser.add_argument("--private-manifest", type=Path, default=DEFAULT_PRIVATE_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    payload = dry_run_payload(
        args.v2636_manifest,
        approval=args.approval,
        operator_gate2_accepted=args.operator_gate2_accepted,
    )
    payload["private_manifest_path"] = rel(args.private_manifest)
    write_json(args.private_manifest, payload, mode=0o600)
    if args.write_report:
        write_report(args.report, payload, args.private_manifest)
    if args.run_live:
        verify_live_gate(
            args.approval,
            operator_gate2_accepted=args.operator_gate2_accepted,
            deploy_manifest=load_deploy_manifest(args.v2636_manifest)["raw"],
        )
        raise SystemExit("live replay execution is not implemented in V2637; gate passed unexpectedly")
    print(json.dumps({
        "decision": payload["summary"]["decision"],
        "ok": payload["ok"],
        "private_manifest": rel(args.private_manifest),
        "report": rel(args.report) if args.write_report else None,
        "safe_to_run_native_replay": payload["safe_to_run_native_replay"],
        "replay_blockers": payload["replay_blockers"],
    }, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
