#!/usr/bin/env python3
"""V2635 host-only build gate for exact SET-cal native replay helper.

Builds a private AArch64 helper that can replay the operator-verified topology
payload as a basic payload entry and the V2633 SET-layer records as exact
SET-arg entries. This removes the local helper capability gap identified in
V2634, but it still does not run native replay.
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
RUN_ID = "V2635"
BUILD_TAG = "v2635-audio-acdb-setcal-replay-helper-gate"
TOOL_NAME = "a90_acdb_setcal_replay_execute_v2635"
HELPER_SOURCE_REL = "workspace/public/src/native-init/helpers/a90_acdb_setcal_replay_scaffold_v2635.c"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2635_AUDIO_ACDB_SETCAL_REPLAY_HELPER_GATE_2026-06-18.md"
DEFAULT_V2634_MANIFEST = ROOT / "workspace/private/builds/audio/v2634-audio-acdb-setcal-replay-gate/setcal-replay-gate-manifest.json"
DEFAULT_HOLD_SEC = 10
FUTURE_LIVE_GATE = (
    "AUD-5Q-native-acdb-setcal-replay go: one-shot Gate-2 accepted SET-layer "
    "ACDB replay, exact captured SET args, no smart-amp gain changes, bounded "
    "PCM probe, reverse deallocate cleanup, rollback to V2321"
)
CFLAGS = (
    "-static",
    "-Os",
    "-Wall",
    "-Wextra",
    "-DA90_ENABLE_NATIVE_SETCAL_REPLAY_EXECUTE",
)
REQUIRED_SOURCE_TOKENS = {
    "execute_guard": "#ifdef A90_ENABLE_NATIVE_SETCAL_REPLAY_EXECUTE",
    "entry_cap_16": "#define A90_MAX_REPLAY_ENTRIES 16",
    "basic_payload_entry": "--basic-payload CAL_TYPE:BUFFER:PAYLOAD",
    "exact_set_entry": "--exact-set ARG[:PAYLOAD]",
    "exact_arg_replay": "exact_set_arg_replay",
    "header_only_replay": "header_only_set_arg_replay",
    "header_only_nonzero_cal_size": "header_only_exact_arg_preserves_nonzero_cal_size",
    "header_only_marker": "A90_ACDB_SETCAL_HEADER_ONLY_EXACT_ARG",
    "header_mem_handle_neutralize": "A90_ACDB_SETCAL_HEADER_MEM_HANDLE_NEUTRALIZED",
    "header_zero_cal_mem_handle_policy": "header_only_zero_cal_size_neutralizes_positive_mem_handle",
    "mem_handle_patch": "A90_OFF_MEM_HANDLE",
    "set_ok_marker": "A90_ACDB_SETCAL_SET_OK",
    "ioctl_result_marker": "A90_ACDB_SETCAL_IOCTL_RESULT",
    "reverse_cleanup_marker": "A90_ACDB_SETCAL_DEALLOCATE_OK",
    "done_marker": "A90_ACDB_SETCAL_REPLAY_DONE",
}
PROHIBITED_SOURCE_TOKENS = {
    "hardcoded_private_path": "workspace/private/",
    "speaker_route_write": "tinymix",
    "playback_tool": "tinyplay",
    "persistent_magisk": "magisk --install-module",
    "requires_payload_for_nonzero_cal_size": "exact arg requires payload but none supplied",
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


def helper_source_state() -> dict[str, Any]:
    source = ROOT / HELPER_SOURCE_REL
    text = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
    required = {name: token in text for name, token in REQUIRED_SOURCE_TOKENS.items()}
    prohibited = {name: token in text for name, token in PROHIBITED_SOURCE_TOKENS.items()}
    return {
        "source": HELPER_SOURCE_REL,
        "exists": source.exists(),
        "required_tokens": required,
        "prohibited_tokens": prohibited,
        "ready": source.exists() and all(required.values()) and not any(prohibited.values()),
    }


def v2634_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False, "ready": False, "reason": "missing-v2634-manifest"}
    payload = read_json(path)
    topology = payload.get("topology", {})
    set_records = payload.get("set_records", [])
    future_args: list[str] = []
    topology_path = topology.get("path_private")
    if topology_path:
        future_args.extend(["--basic-payload", f"39:0:{topology_path}"])
    for record in set_records:
        arg = record.get("arg", {}) if isinstance(record.get("arg"), dict) else {}
        dmabuf = record.get("dmabuf", {}) if isinstance(record.get("dmabuf"), dict) else {}
        arg_path = arg.get("path_private")
        if not arg_path:
            continue
        if record.get("dmabuf_expected"):
            dmabuf_path = dmabuf.get("path_private")
            if dmabuf_path:
                future_args.extend(["--exact-set", f"{arg_path}:{dmabuf_path}"])
        else:
            future_args.extend(["--exact-set", str(arg_path)])
    return {
        "path": rel(path),
        "exists": True,
        "source_run_id": payload.get("run_id"),
        "source_build_tag": payload.get("build_tag"),
        "inputs_ok": payload.get("inputs_ok"),
        "operator_gate2_accepted": payload.get("operator_gate2_accepted"),
        "native_replay_ready": payload.get("native_replay_ready"),
        "safe_to_run_native_replay": payload.get("safe_to_run_native_replay"),
        "replay_blockers": payload.get("replay_blockers", []),
        "set_order": payload.get("captured_set_order"),
        "set_record_count": len(set_records),
        "future_private_args": future_args,
        "future_entry_count": len(future_args) // 2,
        "ready": bool(payload.get("ok") and payload.get("inputs_ok") and topology_path and len(set_records) == 8 and len(future_args) == 18),
        "redacted_set_records": payload.get("set_records_redacted", []),
        "topology_redacted": {key: value for key, value in topology.items() if key != "path_private"},
    }


def build_helper(build_root: Path, *, cc: str, strip: str | None) -> dict[str, Any]:
    source_state = helper_source_state()
    if not source_state["ready"]:
        raise RuntimeError(f"helper source guard failed: {source_state}")
    if not shutil.which(cc):
        raise RuntimeError(f"missing compiler: {cc}")
    source = ROOT / HELPER_SOURCE_REL
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    output = bin_dir / TOOL_NAME
    build = run([cc, *CFLAGS, "-o", str(output), str(source)], timeout=180.0)
    (log_dir / f"{TOOL_NAME}.build.stdout.txt").write_text(build["stdout"], encoding="utf-8", errors="replace")
    (log_dir / f"{TOOL_NAME}.build.stderr.txt").write_text(build["stderr"], encoding="utf-8", errors="replace")
    if not build["ok"]:
        raise RuntimeError(f"build failed; see {rel(log_dir / f'{TOOL_NAME}.build.stderr.txt')}")
    strip_record = None
    if strip:
        strip_result = run([strip, str(output)], timeout=30.0)
        (log_dir / f"{TOOL_NAME}.strip.stdout.txt").write_text(strip_result["stdout"], encoding="utf-8", errors="replace")
        (log_dir / f"{TOOL_NAME}.strip.stderr.txt").write_text(strip_result["stderr"], encoding="utf-8", errors="replace")
        strip_record = {key: value for key, value in strip_result.items() if key not in {"stdout", "stderr"}}
        if not strip_result["ok"]:
            raise RuntimeError("strip failed")
    output.chmod(0o700)
    file_result = run(["file", str(output)], timeout=30.0)
    file_text = file_result["stdout"].strip()
    if ": " in file_text:
        file_text = f"{rel(output)}: {file_text.split(': ', 1)[1]}"
    strings_result = run(["strings", str(output)], timeout=30.0)
    strings_text = strings_result["stdout"] if strings_result["ok"] else ""
    return {
        "built": True,
        "bin_dir": rel(bin_dir),
        "logs": rel(log_dir),
        "compile_defines": {"A90_ENABLE_NATIVE_SETCAL_REPLAY_EXECUTE": True},
        "cflags": list(CFLAGS),
        "build_record": {key: value for key, value in build.items() if key not in {"stdout", "stderr"}},
        "strip_record": strip_record,
        "tool": {
            "name": TOOL_NAME,
            "path": rel(output),
            "sha256": sha256_file(output),
            "size": output.stat().st_size,
            "mode": oct(output.stat().st_mode & 0o777),
            "file": file_text,
            "execute_compiled_in": True,
            "private_only": True,
            "committable": False,
        },
        "static_probe": {
            "strings_has_start_marker": "A90_ACDB_SETCAL_REPLAY_START" in strings_text,
            "strings_has_set_marker": "A90_ACDB_SETCAL_SET_OK" in strings_text,
            "strings_has_ioctl_result_marker": "A90_ACDB_SETCAL_IOCTL_RESULT" in strings_text,
            "strings_has_exact_set_format": "--exact-set ARG[:PAYLOAD]" in strings_text,
            "strings_has_basic_payload_format": "--basic-payload CAL_TYPE:BUFFER:PAYLOAD" in strings_text,
            "strings_has_default_block_message": "execute mode is blocked in this scaffold build" in strings_text,
        },
    }


def future_live_plan(v2634: dict[str, Any], hold_sec: int) -> dict[str, Any]:
    return {
        "exact_gate_phrase": FUTURE_LIVE_GATE,
        "safe_to_run_now": False,
        "blocked_until_operator_gate2_acceptance": not bool(v2634.get("operator_gate2_accepted")),
        "planned_command_shape_private": [
            TOOL_NAME,
            "--execute",
            "--basic-payload 39:0:/private/topology.bin",
            "--exact-set /private/set-arg-cal9.bin",
            "--exact-set /private/set-arg-cal11.bin:/private/payload-cal11.bin",
            f"--hold-sec {hold_sec}",
        ],
        "sequence": [
            "validate operator-accepted V2634 SET-layer manifest",
            "stage helper, topology payload, exact SET arg bytes, and payload bytes to runtime temp dir",
            "verify all staged SHA-256 values on device before execution",
            "run helper and wait for all A90_ACDB_SETCAL_SET_OK markers",
            "run one bounded PCM probe only while helper holds all fds",
            "allow reverse AUDIO_DEALLOCATE_CALIBRATION cleanup for payload-backed records",
            "remove staged files, rollback to V2321, require selftest fail=0",
        ],
        "abort_conditions": [
            "operator Gate-2 acceptance missing",
            "any staged SHA-256 mismatch",
            "any exact SET arg or payload is all-zero",
            "exact arg data_size does not match file length",
            "payload-backed exact arg cal_size does not match payload length",
            "ION/dma-buf allocation or mmap fails",
            "any AUDIO_ALLOCATE_CALIBRATION or AUDIO_SET_CALIBRATION fails",
            "any reverse AUDIO_DEALLOCATE_CALIBRATION cleanup fails",
            "rollback health is not clean",
        ],
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    source = helper_source_state()
    upstream = v2634_state(args.v2634_manifest)
    build = build_helper(args.build_root, cc=args.cc, strip=None if args.no_strip else args.strip) if args.build_helper else {"built": False}
    helper_ready = bool(build.get("built") and source.get("ready"))
    payload = {
        "decision": "v2635-setcal-replay-helper-gate-ready" if helper_ready and upstream.get("ready") else "v2635-setcal-replay-helper-gate-blocked",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "audio_playback_run": False,
        "helper_source_state": source,
        "v2634_manifest": upstream,
        "helper_contract": {
            "max_replay_entries": 16,
            "supports_basic_topology_payload": True,
            "supports_exact_set_arg_replay": True,
            "supports_header_only_set_arg_replay": True,
            "supports_header_only_nonzero_cal_size_exact_args": True,
            "neutralizes_header_only_zero_cal_size_positive_mem_handle": True,
            "patches_fresh_mem_handle_for_payload_records": True,
            "logs_uniform_ioctl_results": True,
            "keeps_all_payload_fds_open_across_probe": True,
            "reverse_deallocates_payload_records": True,
            "execute_define": "A90_ENABLE_NATIVE_SETCAL_REPLAY_EXECUTE",
        },
        "safety": {
            "host_only_v2635": True,
            "native_replay_blocked_in_this_unit": True,
            "helper_binary_private_only": True,
            "raw_payload_private_only": True,
            "future_live_requires_operator_gate2": True,
        },
        "future_live_plan": future_live_plan(upstream, args.hold_sec),
        "build_root": rel(args.build_root),
        "build": build,
        "native_replay_ready": False,
        "safe_to_run_native_replay": False,
        "replay_blockers": [
            "operator Gate-2 has not accepted the V2633/V2634 SET-layer package",
            "V2635 is a host-only helper gate, not a live native replay approval",
        ],
    }
    payload["ok"] = bool(helper_ready and upstream.get("ready"))
    return payload


def write_report(path: Path, payload: dict[str, Any]) -> None:
    upstream = payload.get("v2634_manifest", {})
    build = payload.get("build", {})
    tool = build.get("tool", {})
    lines = [
        "# NATIVE_INIT V2635 — ACDB exact SET-cal replay helper gate",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only build gate for the future native ACDB replay helper. This unit",
        "builds a private AArch64 helper capable of mixed replay: topology as a",
        "basic payload packet, and V2633 SET-layer records as exact SET-argument",
        "bytes with fresh dmabuf handle patching only for payload-backed records.",
        "",
        "No device action, flash, `/dev/msm_audio_cal` ioctl, PCM probe, or raw",
        "payload publication occurred.",
        "",
        "## Result",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- source_v2634_manifest: `{upstream.get('path')}`",
        f"- source_v2634_ready: `{upstream.get('ready')}`",
        f"- future_entry_count: `{upstream.get('future_entry_count')}`",
        f"- native_replay_ready: `{payload.get('native_replay_ready')}`",
        f"- safe_to_run_native_replay: `{payload.get('safe_to_run_native_replay')}`",
        "",
        "## Helper",
        "",
        f"- source: `{HELPER_SOURCE_REL}`",
        f"- built: `{build.get('built')}`",
        f"- private_tool: `{tool.get('path')}`",
        f"- private_tool_sha256: `{tool.get('sha256')}`",
        f"- private_tool_file: `{tool.get('file')}`",
        "",
        "## Contract",
        "",
        "- `--basic-payload CAL_TYPE:BUFFER:PAYLOAD` supports the operator-verified topology payload.",
        "- `--exact-set ARG` replays header-only SET records exactly.",
        "- Header-only exact SET records preserve captured non-zero `cal_size` fields without requiring a separate dma-buf payload.",
        "- Header-only exact SET records with `cal_size==0` neutralize stale positive captured `mem_handle` values to `-1`.",
        "- `--exact-set ARG:PAYLOAD` allocates a fresh ION dmabuf, copies the payload, patches `mem_handle`, then sends the captured SET arg.",
        "- Payload-backed records are deallocated in reverse order; header-only records are not deallocated.",
        "- The helper keeps `/dev/msm_audio_cal` and all payload fds open across the future bounded PCM probe window.",
        "- `A90_MAX_REPLAY_ENTRIES` is `16`, covering the V2677 custom-topology overlay's 11-entry replay sequence.",
        "",
        "## Gate",
        "",
        "- V2635 removes the local helper-format blocker from V2634.",
        "- Native replay remains blocked until operator Gate-2 accepts the V2633/V2634 SET-layer package.",
        "- Future live replay requires a separate checked runner, staged hash verification, bounded PCM probe, reverse cleanup, and V2321 rollback health.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_helper_gate_v2635.py tests/test_native_audio_acdb_setcal_replay_helper_gate_v2635.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_helper_gate_v2635 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_helper_gate_v2635.py --build-helper --write-report`",
        "- `git diff --check`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-helper", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--v2634-manifest", type=Path, default=DEFAULT_V2634_MANIFEST)
    parser.add_argument("--hold-sec", type=int, default=DEFAULT_HOLD_SEC)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--no-strip", action="store_true")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    payload = build_manifest(args)
    payload["manifest_path"] = rel(args.manifest_path)
    write_json(args.manifest_path, payload, mode=0o600)
    if args.write_report:
        write_report(args.report_path, payload)
    print(json.dumps({
        "decision": payload["decision"],
        "ok": payload["ok"],
        "private_manifest": rel(args.manifest_path),
        "report": rel(args.report_path) if args.write_report else None,
        "tool": payload.get("build", {}).get("tool", {}).get("path"),
        "safe_to_run_native_replay": payload["safe_to_run_native_replay"],
        "replay_blockers": payload["replay_blockers"],
    }, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
