#!/usr/bin/env python3
"""Build V2531 ARM32 ioctl trace preload for own-process ACDB init diagnosis.

Host-only unit.  The output is a private 32-bit Android shared object that
interposes libc ioctl() for the already-running own-process helper.  It logs
request, return value, and errno for existing libacdbloader ioctls.  It does
not open /dev/msm_audio_cal and does not issue any extra calibration ioctl.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2531"
BUILD_TAG = "v2531-acdb-ioctl-trace-preload-host-only"
SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_ioctl_trace_preload_v2531.c"
TOOLCHAIN_ROOT = ROOT / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
ARTIFACT_NAME = "liba90_ioctl_trace_v2531.so"
TARGET = "armv7a-linux-androideabi29"
CFLAGS = (
    "--target=armv7a-linux-androideabi29",
    "-fPIC",
    "-ffreestanding",
    "-fno-builtin",
    "-fno-stack-protector",
    "-fvisibility=hidden",
    "-marm",
    "-Os",
    "-Wall",
    "-Wextra",
)
LDFLAGS = (
    "-shared",
    "--allow-shlib-undefined",
    "-soname",
    ARTIFACT_NAME,
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


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None, timeout: float = 180.0) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
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


def find_host_libxml2() -> Path | None:
    for path in (Path("/usr/lib/x86_64-linux-gnu/libxml2.so.16"), Path("/lib/x86_64-linux-gnu/libxml2.so.16")):
        if path.exists():
            return path
    return None


def prepare_host_libraries(build_root: Path) -> dict[str, Any]:
    host_lib_dir = build_root / "host-libs"
    host_lib_dir.mkdir(parents=True, exist_ok=True)
    linked: dict[str, str] = {}

    libtinfo = ROOT / "workspace/private/inputs/toolchains/compat-libs/libtinfo.so.5"
    if not libtinfo.exists():
        fallback = ROOT / "tmp/relibs/libtinfo.so.5"
        if fallback.exists():
            libtinfo = fallback
    if libtinfo.exists():
        target = host_lib_dir / "libtinfo.so.5"
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to(libtinfo)
        linked["libtinfo.so.5"] = rel(libtinfo)

    libxml2 = find_host_libxml2()
    if libxml2 is not None:
        target = host_lib_dir / "libxml2.so.2"
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to(libxml2)
        linked["libxml2.so.2"] = str(libxml2)

    return {
        "path": rel(host_lib_dir),
        "linked": linked,
        "ready": {"libtinfo.so.5", "libxml2.so.2"}.issubset(linked.keys()),
    }


def tool_env(host_libraries: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    ld_paths = [str(ROOT / host_libraries["path"])]
    existing = env.get("LD_LIBRARY_PATH")
    if existing:
        ld_paths.append(existing)
    env["LD_LIBRARY_PATH"] = ":".join(ld_paths)
    return env


def source_state() -> dict[str, Any]:
    source = ROOT / SOURCE_REL
    text = source.read_text(encoding="utf-8", errors="replace")
    required = {
        "exports_ioctl": 'int ioctl(int fd, unsigned long request, ...)' in text,
        "default_visibility_ioctl": '__attribute__((visibility("default")))' in text,
        "uses_raw_ioctl_syscall": "A90_NR_IOCTL 54" in text and "a90_syscall3(A90_NR_IOCTL" in text,
        "logs_errno": '\\"errno\\":' in text and "a90_set_errno(err)" in text,
        "logs_audio_allocate_name": "AUDIO_ALLOCATE_CALIBRATION" in text and "0xc00461c8UL" in text,
        "logs_deallocate_name": "AUDIO_DEALLOCATE_CALIBRATION" in text and "0xc00461c9UL" in text,
        "logs_set_name_only": "AUDIO_SET_CALIBRATION" in text and "0xc00461cbUL" in text,
        "trace_path_private_tmp": "/data/local/tmp/a90-acdb-ownget/ioctl-trace-events.jsonl" in text,
        "no_libc_headers": "#include <" not in text,
    }
    prohibited = {
        "opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in text or "open('/dev/msm_audio_cal" in text,
        "calls_acdb_ioctl": "acdb_ioctl(" in text,
        "calls_acdb_loader_init": "acdb_loader_init" in text,
        "native_speaker_write": "tinyplay" in text or "tinymix" in text or "AudioTrack" in text,
        "persistent_magisk_install": "magisk --install-module" in text,
    }
    return {
        "source": SOURCE_REL,
        "exists": source.exists(),
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    source = ROOT / SOURCE_REL
    obj_dir = build_root / "obj"
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    obj_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    host_libraries = prepare_host_libraries(build_root)
    env = tool_env(host_libraries)
    obj = obj_dir / "a90_ioctl_trace_preload_v2531.o"
    out = bin_dir / ARTIFACT_NAME

    compile_cmd = [str(clang), *CFLAGS, "-c", str(source), "-o", str(obj)]
    compile_result = run(compile_cmd, env=env)
    link_result: dict[str, Any]
    if compile_result["ok"]:
        link_cmd = [str(lld), *LDFLAGS, "-o", str(out), str(obj)]
        link_result = run(link_cmd, env=env)
        if link_result["ok"] and out.exists():
            out.chmod(0o600)
    else:
        link_result = {"ok": False, "skipped": True, "reason": "compile failed"}

    binary: dict[str, Any] = {"path": rel(out), "exists": out.exists()}
    if out.exists():
        binary["sha256"] = sha256_file(out)
        binary["size"] = out.stat().st_size
        binary["mode"] = oct(out.stat().st_mode & 0o777)
        binary["file"] = run([file_cmd, str(out)], timeout=30.0)
        symbols = run([readelf, "-Ws", str(out)], env=env, timeout=30.0)
        binary["symbols"] = {
            "readelf_ok": symbols["ok"],
            "exports_ioctl": " ioctl" in symbols["stdout"],
            "undefined_errno": " UND __errno" in symbols["stdout"],
            "does_not_import_acdb": "acdb_" not in symbols["stdout"],
        }
        dyn = run([readelf, "-d", str(out)], env=env, timeout=30.0)
        binary["dynamic"] = {
            "readelf_ok": dyn["ok"],
            "soname": f"Library soname: [{ARTIFACT_NAME}]" in dyn["stdout"],
        }
    return {
        "host_libraries": host_libraries,
        "compile": compile_result,
        "link": link_result,
        "binary": binary,
        "ok": bool(compile_result.get("ok") and link_result.get("ok") and binary.get("exists")),
    }


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    clang = Path(args.clang) if args.clang else TOOLCHAIN_ROOT / "bin/clang"
    lld = Path(args.lld) if args.lld else TOOLCHAIN_ROOT / "bin/ld.lld"
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "source": source_state(),
        "toolchain": {
            "clang": rel(clang),
            "lld": rel(lld),
            "target": TARGET,
            "cflags": list(CFLAGS),
            "ldflags": list(LDFLAGS),
        },
        "boundaries": {
            "observes_existing_ioctl_calls_only": True,
            "does_not_open_msm_audio_cal": True,
            "does_not_issue_extra_ioctl": True,
            "does_not_call_audio_set_calibration": True,
            "raw_bytes_private": True,
        },
    }
    if args.build:
        payload["build"] = build(args.build_root, clang=clang, lld=lld, readelf=args.readelf, file_cmd=args.file)
    payload["ok"] = bool(
        payload["source"]["exists"]
        and payload["source"]["required_ok"]
        and payload["source"]["prohibited_ok"]
        and (not args.build or payload.get("build", {}).get("ok"))
    )
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--clang")
    parser.add_argument("--lld", type=Path, default=TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--readelf", default=str(TOOLCHAIN_ROOT / "bin/llvm-readelf"))
    parser.add_argument("--file", default="file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.build_root.mkdir(parents=True, exist_ok=True)
    payload = manifest(args)
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
