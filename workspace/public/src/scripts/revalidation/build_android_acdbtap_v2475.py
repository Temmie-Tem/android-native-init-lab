#!/usr/bin/env python3
"""Build V2475 ARM32 libacdbtap.so for ACDB ioctl interposition.

Host-only unit.  The output is a private 32-bit Android shared object intended
for a future transient Magisk/Android measurement capsule.  This script does not
boot Android, stage Magisk files, restart the audio HAL, or run playback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2475"
BUILD_TAG = "v2475-acdbtap-interposer-build"
SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdbtap_v2475.c"
TOOLCHAIN_ROOT = ROOT / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
SO_NAME = "libacdbtap.so"
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
    "-soname",
    SO_NAME,
    "--allow-shlib-undefined",
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
    candidates = [
        Path("/usr/lib/x86_64-linux-gnu/libxml2.so.16"),
        Path("/lib/x86_64-linux-gnu/libxml2.so.16"),
    ]
    for path in candidates:
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
        "exports_acdb_ioctl": "acdb_ioctl(uint32_t cmd" in text,
        "uses_dlsym_next": 'dlsym(A90_RTLD_NEXT, "acdb_ioctl")' in text,
        "target_out_len_4916": "A90_TARGET_OUT_LEN 4916U" in text,
        "size_query_out_len_4": "A90_SIZE_QUERY_OUT_LEN 4U" in text,
        "private_capture_dir": "/data/local/tmp/a90-acdb-tap" in text,
        "sha256_implemented": "a90_sha256_final" in text,
        "raw_syscalls_only": "A90_NR_OPENAT" in text and "A90_NR_WRITE" in text,
        "no_libc_headers": "#include <" not in text,
        "auto_arm_default_off": "#define A90_ACDBTAP_AUTO_ARM_ON_INITIALIZE 0" in text,
    }
    prohibited = {
        "opens_msm_audio_cal": "/dev/msm_audio_cal" in text,
        "audio_calibration_ioctl": "AUDIO_SET_CALIBRATION" in text or "AUDIO_ALLOCATE_CALIBRATION" in text,
        "native_speaker_write": "tinyplay" in text or "tinymix" in text,
        "persistent_magisk_install": "magisk --install-module" in text,
        "raw_payload_committed": "4916-byte payload bytes" in text,
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
    obj = obj_dir / "libacdbtap_v2475.o"
    out = bin_dir / SO_NAME

    compile_cmd = [str(clang), *CFLAGS, "-c", str(source), "-o", str(obj)]
    compile_result = run(compile_cmd, env=env, timeout=180.0)
    (log_dir / "compile.stdout.txt").write_text(compile_result["stdout"], encoding="utf-8", errors="replace")
    (log_dir / "compile.stderr.txt").write_text(compile_result["stderr"], encoding="utf-8", errors="replace")
    if not compile_result["ok"]:
        raise RuntimeError(f"compile failed; see {rel(log_dir / 'compile.stderr.txt')}")

    link_cmd = [str(lld), *LDFLAGS, "-o", str(out), str(obj)]
    link_result = run(link_cmd, env=env, timeout=180.0)
    (log_dir / "link.stdout.txt").write_text(link_result["stdout"], encoding="utf-8", errors="replace")
    (log_dir / "link.stderr.txt").write_text(link_result["stderr"], encoding="utf-8", errors="replace")
    if not link_result["ok"]:
        raise RuntimeError(f"link failed; see {rel(log_dir / 'link.stderr.txt')}")

    file_result = run([file_cmd, str(out)], timeout=10.0)
    readelf_result = run([readelf, "-Ws", str(out)], timeout=30.0)
    (log_dir / "readelf.symbols.txt").write_text(readelf_result["stdout"], encoding="utf-8", errors="replace")
    if not file_result["ok"]:
        raise RuntimeError(file_result["stderr"] or file_result["stdout"] or "file failed")
    if not readelf_result["ok"]:
        raise RuntimeError(readelf_result["stderr"] or readelf_result["stdout"] or "readelf failed")

    symbols = readelf_result["stdout"]
    return {
        "host_libraries": host_libraries,
        "commands": {
            "compile": {k: v for k, v in compile_result.items() if k not in {"stdout", "stderr"}},
            "link": {k: v for k, v in link_result.items() if k not in {"stdout", "stderr"}},
        },
        "logs": rel(log_dir),
        "artifact": {
            "path": rel(out),
            "sha256": sha256_file(out),
            "size": out.stat().st_size,
            "file": file_result["stdout"].strip(),
            "readelf_symbols": rel(log_dir / "readelf.symbols.txt"),
            "exports_acdb_ioctl": " acdb_ioctl" in symbols,
            "undefined_dlsym": " UND dlsym" in symbols,
            "target": TARGET,
            "private_generated": True,
        },
    }


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "decision": "v2475-acdbtap-interposer-build-host-only",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "ok": True,
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "android_action": "none",
        "source_state": source_state(),
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "capture_contract": {
            "shared_object": SO_NAME,
            "abi": "32-bit armeabi-v7a",
            "interposed_symbol": "acdb_ioctl",
            "real_symbol_resolution": "dlsym(RTLD_NEXT, \"acdb_ioctl\")",
            "capture_dir": "/data/local/tmp/a90-acdb-tap",
            "target_out_len": 4916,
            "size_query_out_len": 4,
            "public_output": "metadata and SHA-256 only",
            "raw_output": "private /data/local/tmp then workspace/private only",
        },
        "boundaries": {
            "no_native_msm_audio_cal_ioctls": True,
            "no_native_speaker_write": True,
            "no_android_live_staging": True,
            "no_hal_restart": True,
            "future_live_requires_recoverable_android_handoff": True,
        },
        "toolchain": {
            "clang": str(args.clang),
            "lld": str(args.lld),
            "readelf": args.readelf,
            "file": args.file,
            "cflags": list(CFLAGS),
            "ldflags": list(LDFLAGS),
        },
        "build_root": rel(args.build_root),
    }
    if args.build:
        payload["build"] = build(
            args.build_root,
            clang=args.clang,
            lld=args.lld,
            readelf=args.readelf,
            file_cmd=args.file,
        )
    else:
        payload["build"] = {"built": False, "reason": "pass --build to materialize private libacdbtap.so"}
    payload["manifest_path"] = rel(args.manifest_path)
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--clang", type=Path, default=TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run and not args.build:
        args.dry_run = True
    print(json.dumps(manifest(args), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
