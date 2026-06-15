#!/usr/bin/env python3
"""V2549 host-only gate for an execute-enabled native ACDB replay helper.

This unit does not touch the device and does not issue calibration ioctls.  It
verifies the pinned V2547 CORE_CUSTOM_TOPOLOGIES payload, builds a private
AArch64 helper from the V2474 scaffold with A90_ENABLE_NATIVE_CALIBRATION_EXECUTE,
and emits the exact-gated future live plan for the minimal topology replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2549"
BUILD_TAG = "v2549-audio-acdb-replay-execute-helper-gate"
TOOL_NAME = "a90_acdb_replay_execute_v2549"
HELPER_SOURCE_REL = "workspace/public/src/native-init/helpers/a90_acdb_replay_scaffold_v2474.c"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
STABLE_PAYLOAD = ROOT / "workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin"
EXPECTED_PAYLOAD_SHA256 = "7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89"
EXPECTED_PAYLOAD_LEN = 4916
EXPECTED_CAL_TYPE = 39
EXPECTED_BUFFER_NUMBER = 0
DEFAULT_HOLD_SEC = 10
FUTURE_LIVE_GATE = (
    "AUD-5N-native-acdb-topology-replay go: one-shot V2549 execute-enabled ACDB "
    "topology replay with pinned V2547 payload, no smart-amp gain changes, "
    "bounded PCM probe, explicit deallocate, rollback to V2321"
)
CFLAGS = (
    "-static",
    "-Os",
    "-Wall",
    "-Wextra",
    "-DA90_ENABLE_NATIVE_CALIBRATION_EXECUTE",
)
REQUIRED_SOURCE_TOKENS = {
    "execute_guard": "#ifdef A90_ENABLE_NATIVE_CALIBRATION_EXECUTE",
    "execute_function": "static int execute_replay(",
    "ion_alloc": "ion_alloc_dmabuf(payload_len",
    "payload_length_check": "payload_len != A90_EXPECTED_TOPOLOGY_PAYLOAD_LEN",
    "msm_audio_cal_open": "open(A90_MSM_AUDIO_CAL_PATH, O_RDWR | O_CLOEXEC)",
    "allocate_ioctl": "ioctl_cal(cal_fd, A90_AUDIO_ALLOCATE_CALIBRATION",
    "set_ioctl": "ioctl_cal(cal_fd, A90_AUDIO_SET_CALIBRATION",
    "deallocate_ioctl": "ioctl_cal(cal_fd, A90_AUDIO_DEALLOCATE_CALIBRATION",
    "cleanup_deallocate": "AUDIO_DEALLOCATE_CALIBRATION_cleanup",
    "cal_type_39": "A90_CORE_CUSTOM_TOPOLOGIES_CAL_TYPE 39",
    "payload_len_4916": "A90_EXPECTED_TOPOLOGY_PAYLOAD_LEN 4916U",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
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


def is_all_zero(path: Path) -> bool:
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if any(chunk):
                return False
    return True


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


def tool_file(path: Path) -> str:
    result = run(["file", str(path)], timeout=10.0)
    if not result["ok"]:
        raise RuntimeError(result["stderr"] or result["stdout"] or "file failed")
    return str(result["stdout"]).strip()


def payload_state(path: Path = STABLE_PAYLOAD) -> dict[str, Any]:
    exists = path.exists()
    state: dict[str, Any] = {
        "path": rel(path),
        "exists": exists,
        "expected_len": EXPECTED_PAYLOAD_LEN,
        "expected_sha256": EXPECTED_PAYLOAD_SHA256,
        "private_only": True,
        "committable": False,
    }
    if not exists:
        state.update({"ready": False, "reason": "missing-pinned-private-payload"})
        return state
    stat = path.stat()
    digest = sha256_file(path)
    all_zero = is_all_zero(path)
    state.update(
        {
            "size": stat.st_size,
            "sha256": digest,
            "mode": oct(stat.st_mode & 0o777),
            "all_zero": all_zero,
            "ready": stat.st_size == EXPECTED_PAYLOAD_LEN
            and digest == EXPECTED_PAYLOAD_SHA256
            and not all_zero,
        }
    )
    if not state["ready"]:
        state["reason"] = "payload-size-sha-or-zero-check-failed"
    return state


def assert_payload_ready(path: Path = STABLE_PAYLOAD) -> dict[str, Any]:
    state = payload_state(path)
    if not state.get("ready"):
        raise RuntimeError(f"stable payload not ready: {state}")
    return state


def helper_source_state() -> dict[str, Any]:
    source = ROOT / HELPER_SOURCE_REL
    exists = source.exists()
    text = source.read_text(encoding="utf-8", errors="replace") if exists else ""
    token_state = {name: token in text for name, token in REQUIRED_SOURCE_TOKENS.items()}
    return {
        "source": HELPER_SOURCE_REL,
        "exists": exists,
        "required_tokens": token_state,
        "ready": exists and all(token_state.values()),
        "scaffold_run_id": "V2474",
        "execute_define_for_this_gate": "A90_ENABLE_NATIVE_CALIBRATION_EXECUTE",
    }


def build_execute_helper(build_root: Path, *, cc: str, strip: str | None) -> dict[str, Any]:
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
        raise RuntimeError(f"build failed for {TOOL_NAME}; see {rel(log_dir / f'{TOOL_NAME}.build.stderr.txt')}")

    stripped = False
    strip_record: dict[str, Any] | None = None
    if strip:
        strip_command = [strip, str(output)]
        strip_result = run(strip_command, timeout=30.0)
        (log_dir / f"{TOOL_NAME}.strip.stdout.txt").write_text(strip_result["stdout"], encoding="utf-8", errors="replace")
        (log_dir / f"{TOOL_NAME}.strip.stderr.txt").write_text(strip_result["stderr"], encoding="utf-8", errors="replace")
        strip_record = {key: value for key, value in strip_result.items() if key not in {"stdout", "stderr"}}
        strip_record.update(
            {
                "stdout_log": rel(log_dir / f"{TOOL_NAME}.strip.stdout.txt"),
                "stderr_log": rel(log_dir / f"{TOOL_NAME}.strip.stderr.txt"),
            }
        )
        if not strip_result["ok"]:
            raise RuntimeError(f"strip failed for {TOOL_NAME}")
        stripped = True

    output.chmod(output.stat().st_mode | 0o111)
    strings_probe = run(["strings", str(output)], timeout=10.0)
    strings_text = strings_probe["stdout"] if strings_probe["ok"] else ""
    return {
        "built": True,
        "bin_dir": rel(bin_dir),
        "logs": rel(log_dir),
        "compile_defines": {
            "A90_ENABLE_NATIVE_CALIBRATION_EXECUTE": True,
        },
        "cflags": list(CFLAGS),
        "build_record": {
            key: value for key, value in build.items() if key not in {"stdout", "stderr"}
        }
        | {
            "stdout_log": rel(log_dir / f"{TOOL_NAME}.build.stdout.txt"),
            "stderr_log": rel(log_dir / f"{TOOL_NAME}.build.stderr.txt"),
        },
        "strip_record": strip_record,
        "tool": {
            "name": TOOL_NAME,
            "path": rel(output),
            "sha256": sha256_file(output),
            "size": output.stat().st_size,
            "mode": oct(output.stat().st_mode & 0o777),
            "file": tool_file(output),
            "stripped": stripped,
            "execute_compiled_in": True,
            "private_only": True,
            "committable": False,
        },
        "static_probe": {
            key: value for key, value in strings_probe.items() if key not in {"stdout", "stderr"}
        }
        | {
            "strings_has_execute_format": "execute_compiled_in" in strings_text,
            "strings_has_execute_ioctl_marker": "AUDIO_SET_CALIBRATION" in strings_text,
            "strings_has_blocked_default_message": "execute mode is blocked in this host-only scaffold build" in strings_text,
            "stderr_len": len(strings_probe["stderr"]),
        },
    }


def future_live_plan(hold_sec: int) -> dict[str, Any]:
    return {
        "exact_gate_phrase": FUTURE_LIVE_GATE,
        "host_only_in_v2549": True,
        "future_run_id_placeholder": "V2550+",
        "steps": [
            "confirm V2321 rollback image, v48 fallback, recovery/TWRP, bridge health, and selftest fail=0",
            "flash the existing audio materialization image if required and verify candidate health",
            "materialize ADSP, /dev/snd, /dev/ion, and /dev/msm_audio_cal using the already-gated audio path",
            "stage the private V2549 execute helper and V2547 payload to an ephemeral runtime directory",
            "verify payload SHA-256 on device before execution",
            f"start helper with --execute --payload <staged_payload> --hold-sec {hold_sec}",
            "wait for helper stderr marker AUDIO_SET_CALIBRATION ok before starting the bounded PCM probe",
            "run the bounded low-amplitude PCM probe only inside the helper hold window",
            "allow helper to issue AUDIO_DEALLOCATE_CALIBRATION and close /dev/msm_audio_cal, dma-buf, and /dev/ion",
            "collect redacted metadata only, remove staged files, rollback to V2321, and require selftest fail=0",
        ],
        "abort_conditions": [
            "payload size or SHA mismatch on host or device",
            "helper describe output does not report execute_compiled_in=true",
            "ADSP, /dev/snd, /dev/ion, or /dev/msm_audio_cal is missing",
            "ION allocation or dma-buf mmap fails",
            "AUDIO_ALLOCATE_CALIBRATION or AUDIO_SET_CALIBRATION fails",
            "helper does not emit AUDIO_SET_CALIBRATION ok before the PCM probe window",
            "AUDIO_DEALLOCATE_CALIBRATION cleanup fails or rollback health is not clean",
        ],
        "live_boundaries": {
            "no_speaker_gain_or_boost_changes": True,
            "no_blind_route_writes": True,
            "no_raw_payload_commit": True,
            "only_runtime_temp_files": True,
            "rollback_to_v2321_required": True,
        },
    }


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    payload = payload_state(args.payload)
    if args.require_payload and not payload.get("ready"):
        raise RuntimeError(f"required payload is not ready: {payload}")

    source = helper_source_state()
    manifest_payload: dict[str, Any] = {
        "decision": "v2549-acdb-replay-execute-helper-gate-host-only",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "ok": True,
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "audio_playback_run": False,
        "source": {
            "helper": HELPER_SOURCE_REL,
            "basis_reports": [
                "docs/reports/NATIVE_INIT_V2474_AUDIO_ACDB_REPLAY_SCAFFOLD_2026-06-15.md",
                "docs/reports/NATIVE_INIT_V2547_AUDIO_ACDB_INDIRECT_TOPOLOGY_CAPTURE_2026-06-16.md",
                "docs/reports/NATIVE_INIT_V2548_AUDIO_ACDB_REPLAY_REAL_PAYLOAD_GATE_2026-06-16.md",
            ],
        },
        "stable_payload": payload,
        "helper_source_state": source,
        "replay_contract": {
            "cal_type": EXPECTED_CAL_TYPE,
            "buffer_number": EXPECTED_BUFFER_NUMBER,
            "payload_len": EXPECTED_PAYLOAD_LEN,
            "payload_sha256": EXPECTED_PAYLOAD_SHA256,
            "fresh_native_dmabuf_required": True,
            "do_not_reuse_android_mem_handle_37": True,
            "sequence": [
                "ION_IOC_ALLOC fresh native dma-buf",
                "copy payload into dma-buf and msync",
                "AUDIO_ALLOCATE_CALIBRATION",
                "AUDIO_SET_CALIBRATION",
                "hold fds across bounded PCM probe",
                "AUDIO_DEALLOCATE_CALIBRATION",
                "munmap and close all fds",
            ],
        },
        "safety": {
            "host_only_v2549": True,
            "native_calibration_ioctls_blocked_in_this_unit": True,
            "helper_binary_private_only": True,
            "raw_payload_private_only": True,
            "future_live_requires_exact_gate": True,
        },
        "future_live_plan": future_live_plan(args.hold_sec),
        "toolchain": {
            "cc": args.cc,
            "strip": None if args.no_strip else args.strip,
            "cflags": list(CFLAGS),
            "linkage": "static",
        },
        "build_root": rel(args.build_root),
    }

    if args.build_helper:
        if not payload.get("ready"):
            raise RuntimeError(f"refusing to build execute helper without pinned payload: {payload}")
        manifest_payload["build"] = build_execute_helper(
            args.build_root,
            cc=args.cc,
            strip=None if args.no_strip else args.strip,
        )
    else:
        manifest_payload["build"] = {
            "built": False,
            "reason": "pass --build-helper to compile the private execute-enabled AArch64 helper",
        }

    manifest_payload["ok"] = bool(
        payload.get("ready")
        and source.get("ready")
        and (not args.build_helper or manifest_payload["build"].get("built"))
    )
    manifest_payload["manifest_path"] = rel(args.manifest_path)
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--build-helper", action="store_true")
    parser.add_argument("--require-payload", action="store_true")
    parser.add_argument("--payload", type=Path, default=STABLE_PAYLOAD)
    parser.add_argument("--hold-sec", type=int, default=DEFAULT_HOLD_SEC)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--no-strip", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run and not args.build_helper:
        args.dry_run = True
    print(json.dumps(manifest(args), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
