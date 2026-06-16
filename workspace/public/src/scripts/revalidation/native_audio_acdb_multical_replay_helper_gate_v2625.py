#!/usr/bin/env python3
"""V2625 host-only gate for the native ACDB multi-cal replay helper.

This unit does not run native replay and does not touch the device.  It builds
an execute-capable private helper scaffold so the next live replay can consume
an ordered Gate-2 accepted manifest, but it keeps live replay blocked until the
operator explicitly accepts the V2624 manifest and VOL-negative boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2625"
BUILD_TAG = "v2625-audio-acdb-multical-replay-helper-gate"
TOOL_NAME = "a90_acdb_multical_replay_execute_v2625"
HELPER_SOURCE_REL = "workspace/public/src/native-init/helpers/a90_acdb_multical_replay_scaffold_v2625.c"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2625_AUDIO_ACDB_MULTICAL_REPLAY_HELPER_GATE_2026-06-16.md"
DEFAULT_V2624_MANIFEST = ROOT / "workspace/private/builds/audio/v2624-audio-acdb-multical-replay-gate/multical-replay-gate-manifest.json"
DEFAULT_HOLD_SEC = 10
FUTURE_LIVE_GATE = (
    "AUD-5P-native-acdb-multical-replay go: one-shot Gate-2 accepted "
    "multi-cal ACDB replay, no smart-amp gain changes, bounded PCM probe, "
    "reverse deallocate cleanup, rollback to V2321"
)
CFLAGS = (
    "-static",
    "-Os",
    "-Wall",
    "-Wextra",
    "-DA90_ENABLE_NATIVE_MULTICAL_EXECUTE",
)
REQUIRED_SOURCE_TOKENS = {
    "execute_guard": "#ifdef A90_ENABLE_NATIVE_MULTICAL_EXECUTE",
    "entry_parser": "parse_entry(optarg, &entries[entry_count])",
    "multi_entry_bound": "A90_MAX_REPLAY_ENTRIES 8",
    "payload_zero_guard": "buffer_is_all_zero",
    "ion_alloc": "ion_alloc_dmabuf(state->payload_len",
    "allocate_ioctl": "AUDIO_ALLOCATE_CALIBRATION",
    "set_ioctl": "AUDIO_SET_CALIBRATION",
    "reverse_cleanup": "for (index = entry_count; index > 0; index--)",
    "deallocate_marker": "A90_ACDB_MULTICAL_DEALLOCATE_OK",
    "done_marker": "A90_ACDB_MULTICAL_REPLAY_DONE",
}


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path = ROOT, timeout: float = 180.0) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return {
        "command": command,
        "cwd": rel(cwd),
        "rc": completed.returncode,
        "ok": completed.returncode == 0,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def helper_source_state() -> dict[str, Any]:
    source = ROOT / HELPER_SOURCE_REL
    text = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
    tokens = {name: token in text for name, token in REQUIRED_SOURCE_TOKENS.items()}
    prohibited = {
        "hardcoded_private_payload_path": "workspace/private/" in text,
        "speaker_route_write": any(token in text for token in ("tinymix", "tinyplay", "AudioTrack")),
        "persistent_magisk": "magisk --install-module" in text,
    }
    return {
        "source": HELPER_SOURCE_REL,
        "exists": source.exists(),
        "required_tokens": tokens,
        "prohibited_tokens": prohibited,
        "ready": source.exists() and all(tokens.values()) and not any(prohibited.values()),
    }


def redacted_replay_entry(entry: dict[str, Any]) -> dict[str, Any]:
    raw = dict(entry.get("raw") or {})
    raw.pop("path_private", None)
    return {key: value for key, value in entry.items() if key != "raw"} | {"raw": raw}


def v2624_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False, "ready": False, "reason": "missing-v2624-manifest"}
    payload = read_json(path)
    topology = payload.get("topology", {})
    candidates = payload.get("per_device_candidates", [])
    replay_entries = [topology, *candidates]
    replay_args = []
    for entry in replay_entries:
        raw = entry.get("raw", {})
        path_private = raw.get("path_private")
        cal_type = entry.get("cal_type") or entry.get("proposed_cal_type")
        buffer_number = entry.get("buffer_number", 0)
        if path_private and cal_type is not None:
            replay_args.append(f"{cal_type}:{buffer_number}:{path_private}")
    return {
        "path": rel(path),
        "exists": True,
        "source_run_id": payload.get("run_id"),
        "source_build_tag": payload.get("build_tag"),
        "operator_gate2_accepted": payload.get("operator_gate2_accepted"),
        "operator_accept_vol_negative": payload.get("operator_accept_vol_negative"),
        "gate2_accepted_for_manifest": payload.get("gate2_accepted_for_manifest"),
        "native_replay_ready": payload.get("native_replay_ready"),
        "safe_to_run_native_replay": payload.get("safe_to_run_native_replay"),
        "replay_blockers": payload.get("replay_blockers", []),
        "redacted_entries": [redacted_replay_entry(entry) for entry in replay_entries],
        "private_entry_count": len(replay_args),
        "future_private_entry_args": replay_args,
        "ready": bool(payload.get("ok") and len(replay_args) >= 4),
    }


def build_helper(build_root: Path, *, cc: str, strip: str | None) -> dict[str, Any]:
    source_state = helper_source_state()
    if not source_state["ready"]:
        raise RuntimeError(f"helper source guard failed: {source_state}")

    source = ROOT / HELPER_SOURCE_REL
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    output = bin_dir / TOOL_NAME
    command = [cc, *CFLAGS, "-o", str(output), str(source)]
    build = run(command, timeout=180.0)
    (log_dir / f"{TOOL_NAME}.build.stdout.txt").write_text(build["stdout"], encoding="utf-8", errors="replace")
    (log_dir / f"{TOOL_NAME}.build.stderr.txt").write_text(build["stderr"], encoding="utf-8", errors="replace")
    if not build["ok"]:
        raise RuntimeError(f"build failed; see {rel(log_dir / f'{TOOL_NAME}.build.stderr.txt')}")

    strip_record: dict[str, Any] | None = None
    if strip:
        strip_result = run([strip, str(output)], timeout=30.0)
        (log_dir / f"{TOOL_NAME}.strip.stdout.txt").write_text(strip_result["stdout"], encoding="utf-8", errors="replace")
        (log_dir / f"{TOOL_NAME}.strip.stderr.txt").write_text(strip_result["stderr"], encoding="utf-8", errors="replace")
        strip_record = {key: value for key, value in strip_result.items() if key not in {"stdout", "stderr"}}
        if not strip_result["ok"]:
            raise RuntimeError("strip failed")

    output.chmod(0o700)
    file_result = run(["file", str(output)], timeout=30.0)
    strings_result = run(["strings", str(output)], timeout=30.0)
    strings_text = strings_result["stdout"] if strings_result["ok"] else ""
    return {
        "built": True,
        "bin_dir": rel(bin_dir),
        "logs": rel(log_dir),
        "compile_defines": {"A90_ENABLE_NATIVE_MULTICAL_EXECUTE": True},
        "cflags": list(CFLAGS),
        "build_record": {key: value for key, value in build.items() if key not in {"stdout", "stderr"}},
        "strip_record": strip_record,
        "tool": {
            "name": TOOL_NAME,
            "path": rel(output),
            "sha256": sha256_file(output),
            "size": output.stat().st_size,
            "mode": oct(output.stat().st_mode & 0o777),
            "file": file_result["stdout"].strip(),
            "execute_compiled_in": True,
            "private_only": True,
            "committable": False,
        },
        "static_probe": {
            "strings_has_start_marker": "A90_ACDB_MULTICAL_REPLAY_START" in strings_text,
            "strings_has_set_marker": "A90_ACDB_MULTICAL_SET_OK" in strings_text,
            "strings_has_reverse_dealloc_marker": "A90_ACDB_MULTICAL_DEALLOCATE_OK" in strings_text,
            "strings_has_blocked_default_message": "execute mode is blocked in this scaffold build" in strings_text,
        },
    }


def future_live_plan(v2624: dict[str, Any], hold_sec: int) -> dict[str, Any]:
    safe_to_run = bool(v2624.get("gate2_accepted_for_manifest") and v2624.get("safe_to_run_native_replay"))
    return {
        "exact_gate_phrase": FUTURE_LIVE_GATE,
        "safe_to_run_now": False,
        "blocked_until_gate2_acceptance": not safe_to_run,
        "planned_command_shape_private": [
            "a90_acdb_multical_replay_execute_v2625",
            "--execute",
            "--entry CAL_TYPE:BUFFER:/private/payload.bin",
            f"--hold-sec {hold_sec}",
        ],
        "sequence": [
            "validate Gate-2 accepted ordered manifest",
            "stage helper and private raw payloads to runtime temp dir",
            "verify payload SHA-256 on device before execution",
            "start helper and wait for all A90_ACDB_MULTICAL_SET_OK markers",
            "run bounded PCM probe only while helper holds all fds",
            "allow reverse AUDIO_DEALLOCATE_CALIBRATION cleanup",
            "remove staged files, rollback to V2321, require selftest fail=0",
        ],
        "abort_conditions": [
            "operator Gate-2 acceptance missing",
            "any staged payload SHA-256 mismatch",
            "any payload is all-zero or exceeds helper bounds",
            "ION/dma-buf allocation or mmap fails",
            "any AUDIO_ALLOCATE_CALIBRATION or AUDIO_SET_CALIBRATION fails",
            "any reverse AUDIO_DEALLOCATE_CALIBRATION cleanup fails",
            "rollback health is not clean",
        ],
    }


def make_manifest(args: argparse.Namespace) -> dict[str, Any]:
    source = helper_source_state()
    upstream = v2624_state(args.v2624_manifest)
    build_state: dict[str, Any]
    if args.build_helper:
        build_state = build_helper(args.build_root, cc=args.cc, strip=None if args.no_strip else args.strip)
    else:
        build_state = {"built": False, "reason": "pass --build-helper to compile private AArch64 helper"}

    payload = {
        "decision": "v2625-acdb-multical-replay-helper-gate-host-only",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "audio_playback_run": False,
        "source": {
            "helper": HELPER_SOURCE_REL,
            "basis_reports": [
                "docs/reports/NATIVE_INIT_V2552_AUDIO_ACDB_TOPOLOGY_REPLAY_ION_LIVE_HANDOFF_2026-06-16.md",
                "docs/reports/NATIVE_INIT_V2624_AUDIO_ACDB_MULTICAL_REPLAY_GATE_2026-06-16.md",
            ],
        },
        "helper_source_state": source,
        "v2624_manifest": upstream,
        "helper_contract": {
            "entry_format": "CAL_TYPE:BUFFER:PATH",
            "max_entries": 8,
            "max_payload_len": 131072,
            "rejects_all_zero_payloads": True,
            "keeps_all_fds_open_across_probe": True,
            "deallocates_in_reverse_order": True,
            "execute_define": "A90_ENABLE_NATIVE_MULTICAL_EXECUTE",
        },
        "safety": {
            "host_only_v2625": True,
            "native_replay_blocked_in_this_unit": True,
            "helper_binary_private_only": True,
            "raw_payload_private_only": True,
            "future_live_requires_operator_gate2": True,
        },
        "future_live_plan": future_live_plan(upstream, args.hold_sec),
        "build_root": rel(args.build_root),
        "build": build_state,
    }
    payload["ok"] = bool(source.get("ready") and upstream.get("ready") and (not args.build_helper or build_state.get("built")))
    payload["manifest_path"] = rel(args.manifest_path)
    write_json(args.manifest_path, payload, mode=0o600)
    if args.write_report:
        write_report(args.report_path, payload)
    return payload


def write_report(path: Path, payload: dict[str, Any]) -> None:
    upstream = payload.get("v2624_manifest", {})
    build = payload.get("build", {})
    tool = build.get("tool", {})
    entries = upstream.get("redacted_entries", [])
    lines = [
        "# NATIVE_INIT V2625 — ACDB multi-cal replay helper gate",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only build gate for the future native multi-cal replay helper. No device action, no flash, no ACDB ioctl execution, no PCM probe, and no raw payload publication occurred.",
        "",
        "## Decision",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- native_calibration_ioctls_run: `{payload.get('native_calibration_ioctls_run')}`",
        f"- source_v2624_manifest: `{upstream.get('path')}`",
        f"- gate2_accepted_for_manifest: `{upstream.get('gate2_accepted_for_manifest')}`",
        f"- safe_to_run_native_replay: `{upstream.get('safe_to_run_native_replay')}`",
        "",
        "## Helper",
        "",
        f"- source: `{payload.get('source', {}).get('helper')}`",
        f"- built: `{build.get('built')}`",
        f"- private_tool: `{tool.get('path')}`",
        f"- private_tool_sha256: `{tool.get('sha256')}`",
        f"- private_tool_file: `{tool.get('file')}`",
        "",
        "The helper accepts repeated `--entry CAL_TYPE:BUFFER:PATH`, allocates one dma-buf per entry, keeps `/dev/msm_audio_cal` and all dma-buf fds open across the future PCM probe window, then deallocates entries in reverse order on every exit path.",
        "",
        "## Redacted Replay Entries",
        "",
        "| order | kind | cal_type | buffer | size | sha256 | status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        raw = entry.get("raw", {})
        cal_type = entry.get("cal_type") or entry.get("proposed_cal_type")
        buffer_number = entry.get("buffer_number", 0)
        status = entry.get("gate2_status")
        lines.append(
            f"| {entry.get('order')} | `{entry.get('kind')}` | `{cal_type}` | `{buffer_number}` | "
            f"{raw.get('size')} | `{raw.get('sha256')}` | `{status}` |"
        )
    lines.extend(
        [
            "",
            "## Blockers",
            "",
            "- Native replay remains blocked until operator Gate-2 accepts the current V2624 manifest and VOL-negative boundary.",
            "- This unit only removes the local topology-only helper gap; it does not authorize live replay.",
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_multical_replay_helper_gate_v2625.py tests/test_native_audio_acdb_multical_replay_helper_gate_v2625.py`",
            "- `PYTHONPATH=tests python3 -m unittest tests.test_native_audio_acdb_multical_replay_helper_gate_v2625`",
            "- `python3 workspace/public/src/scripts/revalidation/native_audio_acdb_multical_replay_helper_gate_v2625.py --build-helper --write-report --no-strip`",
            "- `git diff --check`",
            "",
            "## Next",
            "",
            "After operator Gate-2 acceptance, wire this private helper into a checked live runner that stages the accepted payload set, verifies hashes on-device, waits for all `A90_ACDB_MULTICAL_SET_OK` markers, runs one bounded PCM probe while fds are held, then requires reverse cleanup and V2321 rollback health.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--build-helper", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--v2624-manifest", type=Path, default=DEFAULT_V2624_MANIFEST)
    parser.add_argument("--hold-sec", type=int, default=DEFAULT_HOLD_SEC)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--no-strip", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run and not args.build_helper:
        args.dry_run = True
    if args.build_helper and not shutil.which(args.cc):
        raise SystemExit(f"missing compiler: {args.cc}")
    payload = make_manifest(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
