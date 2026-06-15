#!/usr/bin/env python3
"""V2474 host-only scaffold for future native ACDB topology replay.

This unit deliberately does not touch the device.  It builds a default-disabled
AArch64 helper and materializes a deterministic placeholder payload under
workspace/private so the ION/dma-buf + AUDIO_ALLOCATE/SET/DEALLOCATE runner
shape can be reviewed before real ACDB bytes are available.

Native calibration ioctls remain blocked live until the real payload bytes,
length, SHA-256, mem-handle policy, and cleanup policy are pinned.
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
RUN_ID = "V2474"
BUILD_TAG = "v2474-audio-acdb-replay-scaffold"
TOOL_NAME = "a90_acdb_replay_scaffold_v2474"
SOURCE_REL = "workspace/public/src/native-init/helpers/a90_acdb_replay_scaffold_v2474.c"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_PLACEHOLDER = DEFAULT_BUILD_ROOT / "placeholder-core-custom-topologies-4916.bin"
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
EXPECTED_PAYLOAD_LEN = 4916
EXPECTED_CAL_TYPE = 39
EXPECTED_BUFFER_NUMBER = 0
EXPECTED_SEQUENCE = [
    "AUDIO_ALLOCATE_CALIBRATION",
    "AUDIO_SET_CALIBRATION",
    "AUDIO_DEALLOCATE_CALIBRATION",
]
ACDB_CROSS_VALIDATION_ROOT = ROOT / "workspace/private/inputs/audio/acdb_replay"
EXPECTED_PRIVATE_INPUTS = [
    ACDB_CROSS_VALIDATION_ROOT / "acdbdata",
    ACDB_CROSS_VALIDATION_ROOT / "libs/libaudcal.so",
    ACDB_CROSS_VALIDATION_ROOT / "libs/libacdb-fts.so",
    ACDB_CROSS_VALIDATION_ROOT / "libs/libacdbrtac.so",
    ACDB_CROSS_VALIDATION_ROOT / "libs/libadiertac.so",
]
CFLAGS = (
    "-static",
    "-Os",
    "-Wall",
    "-Wextra",
)


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


def placeholder_payload_bytes(size: int = EXPECTED_PAYLOAD_LEN) -> bytes:
    seed = (
        b"A90_V2474_PLACEHOLDER_CORE_CUSTOM_TOPOLOGIES_PAYLOAD_"
        b"NOT_REAL_ACDB_BYTES_DO_NOT_USE_FOR_LIVE_REPLAY\n"
    )
    body = bytearray()
    counter = 0
    while len(body) < size:
        body.extend(seed)
        body.extend(counter.to_bytes(4, "little"))
        counter += 1
    return bytes(body[:size])


def materialize_placeholder(path: Path = DEFAULT_PLACEHOLDER) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = placeholder_payload_bytes()
    path.write_bytes(data)
    path.chmod(0o600)
    return {
        "path": rel(path),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
        "mode": oct(path.stat().st_mode & 0o777),
        "synthetic_placeholder": True,
        "usable_for_live_replay": False,
    }


def helper_source_state() -> dict[str, Any]:
    source = ROOT / SOURCE_REL
    text = source.read_text(encoding="utf-8", errors="replace")
    required_tokens = {
        "compile_time_execute_guard": "A90_ENABLE_NATIVE_CALIBRATION_EXECUTE",
        "ion_allocation": "A90_ION_IOC_ALLOC",
        "ion_device": 'A90_ION_PATH "/dev/ion"',
        "msm_audio_cal_device": 'A90_MSM_AUDIO_CAL_PATH "/dev/msm_audio_cal"',
        "allocate_ioctl": "A90_AUDIO_ALLOCATE_CALIBRATION",
        "set_ioctl": "A90_AUDIO_SET_CALIBRATION",
        "deallocate_ioctl": "A90_AUDIO_DEALLOCATE_CALIBRATION",
        "expected_cal_type": "A90_CORE_CUSTOM_TOPOLOGIES_CAL_TYPE 39",
        "expected_payload_len": "A90_EXPECTED_TOPOLOGY_PAYLOAD_LEN 4916",
        "explicit_cleanup": "AUDIO_DEALLOCATE_CALIBRATION_cleanup",
    }
    return {
        "source": SOURCE_REL,
        "exists": source.exists(),
        "required_tokens": {
            name: token in text for name, token in required_tokens.items()
        },
        "execute_guard_default_disabled": "#ifdef A90_ENABLE_NATIVE_CALIBRATION_EXECUTE" in text,
        "default_refuses_execute": "execute mode is blocked in this host-only scaffold build" in text,
        "contains_live_ioctl_scaffold": all(
            token in text
            for token in (
                "ioctl_cal(cal_fd, A90_AUDIO_ALLOCATE_CALIBRATION",
                "ioctl_cal(cal_fd, A90_AUDIO_SET_CALIBRATION",
                "ioctl_cal(cal_fd, A90_AUDIO_DEALLOCATE_CALIBRATION",
            )
        ),
    }


def tool_file(path: Path) -> str:
    result = run(["file", str(path)], timeout=10.0)
    if not result["ok"]:
        raise RuntimeError(result["stderr"] or result["stdout"] or "file failed")
    return str(result["stdout"]).strip()


def build_helper(build_root: Path, *, cc: str, strip: str | None) -> dict[str, Any]:
    source = ROOT / SOURCE_REL
    if not source.exists():
        raise RuntimeError(f"missing helper source: {SOURCE_REL}")
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
    strip_command: list[str] | None = None
    if strip:
        strip_command = [strip, str(output)]
        strip_result = run(strip_command, timeout=30.0)
        (log_dir / f"{TOOL_NAME}.strip.stdout.txt").write_text(strip_result["stdout"], encoding="utf-8", errors="replace")
        (log_dir / f"{TOOL_NAME}.strip.stderr.txt").write_text(strip_result["stderr"], encoding="utf-8", errors="replace")
        if not strip_result["ok"]:
            raise RuntimeError(f"strip failed for {TOOL_NAME}")
        stripped = True
    output.chmod(output.stat().st_mode | 0o111)
    return {
        "bin_dir": rel(bin_dir),
        "logs": rel(log_dir),
        "compile_defines": {
            "A90_ENABLE_NATIVE_CALIBRATION_EXECUTE": False,
        },
        "build_record": {
            key: value for key, value in build.items() if key not in {"stdout", "stderr"}
        }
        | {
            "stdout_log": rel(log_dir / f"{TOOL_NAME}.build.stdout.txt"),
            "stderr_log": rel(log_dir / f"{TOOL_NAME}.build.stderr.txt"),
        },
        "tool": {
            "name": TOOL_NAME,
            "path": rel(output),
            "sha256": sha256_file(output),
            "size": output.stat().st_size,
            "file": tool_file(output),
            "stripped": stripped,
            "execute_compiled_in": False,
        }
        | ({"strip_command": strip_command} if strip_command else {}),
    }


def cross_validation_state() -> dict[str, Any]:
    entries = []
    for path in EXPECTED_PRIVATE_INPUTS:
        entries.append(
            {
                "path": rel(path),
                "exists": path.exists(),
                "kind": "directory" if path.is_dir() else "file" if path.is_file() else "missing",
                "private_only": True,
            }
        )
    return {
        "root": rel(ACDB_CROSS_VALIDATION_ROOT),
        "expected_private_inputs": entries,
        "ready": all(entry["exists"] for entry in entries),
        "committable": False,
    }


def safety_state() -> dict[str, Any]:
    source = helper_source_state()
    return {
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_blocked_live": True,
        "real_payload_required_before_live": True,
        "placeholder_payload_rejected_for_live": True,
        "execute_compiled_in_by_default": False,
        "source_guard_ok": (
            source["execute_guard_default_disabled"]
            and source["default_refuses_execute"]
            and all(source["required_tokens"].values())
        ),
        "blocked_until": [
            "real 4916-byte CORE_CUSTOM_TOPOLOGIES payload bytes available privately",
            "real payload SHA-256 pinned in a public redacted report",
            "chosen ION heap/mem_handle policy pinned",
            "AUDIO_DEALLOCATE cleanup and fd-close policy pinned",
            "bounded PCM probe ordering pinned",
        ],
    }


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "decision": "v2474-acdb-replay-scaffold-host-only",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "ok": True,
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "source": {
            "helper": SOURCE_REL,
            "kernel_uapi": [
                "techpack/audio/4.0/include/uapi/linux/msm_audio_calibration.h",
                "include/uapi/linux/ion.h",
                "include/uapi/linux/msm_ion.h",
            ],
            "basis_reports": [
                "docs/reports/NATIVE_INIT_V2414_AUDIO_ACDB_PAYLOAD_REPLAY_DESIGN_2026-06-15.md",
                "docs/reports/NATIVE_INIT_V2462_AUDIO_ACDB_PAYLOAD_DECODE_REPLAY_DESIGN_2026-06-15.md",
            ],
        },
        "replay_shape": {
            "cal_type": EXPECTED_CAL_TYPE,
            "buffer_number": EXPECTED_BUFFER_NUMBER,
            "expected_payload_len": EXPECTED_PAYLOAD_LEN,
            "sequence": EXPECTED_SEQUENCE,
            "keep_fds_open_across_pcm_probe": [
                "/dev/msm_audio_cal",
                "ION/dma-buf fd",
            ],
            "cleanup": [
                "AUDIO_DEALLOCATE_CALIBRATION for same cal_type/buffer/mem_handle",
                "close /dev/msm_audio_cal fd",
                "munmap and close dma-buf fd",
                "close /dev/ion fd",
            ],
        },
        "safety": safety_state(),
        "helper_source_state": helper_source_state(),
        "cross_validation": cross_validation_state(),
        "toolchain": {
            "cc": args.cc,
            "strip": None if args.no_strip else args.strip,
            "cflags": list(CFLAGS),
            "linkage": "static",
            "execute_define_intentionally_absent": True,
        },
        "build_root": rel(args.build_root),
    }
    if args.materialize_placeholder:
        payload["placeholder_payload"] = materialize_placeholder(args.placeholder_path)
    else:
        payload["placeholder_payload"] = {
            "path": rel(args.placeholder_path),
            "materialized": False,
            "expected_size": EXPECTED_PAYLOAD_LEN,
            "synthetic_placeholder": True,
            "usable_for_live_replay": False,
        }
    if args.build_helper:
        payload["build"] = build_helper(
            args.build_root,
            cc=args.cc,
            strip=None if args.no_strip else args.strip,
        )
    else:
        payload["build"] = {
            "built": False,
            "reason": "pass --build-helper to compile the private AArch64 scaffold binary",
        }
    payload["manifest_path"] = rel(args.manifest_path)
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="emit the host-only scaffold plan")
    parser.add_argument("--materialize-placeholder", action="store_true")
    parser.add_argument("--build-helper", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--placeholder-path", type=Path, default=DEFAULT_PLACEHOLDER)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--no-strip", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run and not args.materialize_placeholder and not args.build_helper:
        args.dry_run = True
    print(json.dumps(manifest(args), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
