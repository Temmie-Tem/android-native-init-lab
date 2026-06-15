#!/usr/bin/env python3
"""Build V2539 ARM32 combined ACDB enter-trace + ioctl fake preload.

Host-only unit.  The output is one private 32-bit Android shared object that
exports both acdb_ioctl() and ioctl().  Unlike V2538, the acdb_ioctl wrapper is
compiled with A90_ACDBTAP_LOG_ENTER=1 so it writes a lightweight enter/before_real
row before calling the real acdb_ioctl.  That distinguishes "wrapper never ran"
from "wrapper entered and the real ACDB_CMD_INITIALIZE_V2 call never returned".
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
RUN_ID = "V2539"
BUILD_TAG = "v2539-acdb-enter-combined-preload-host-only"
ACDBTAP_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdbtap_v2475.c"
IOCTL_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_ioctl_trace_preload_v2531.c"
TOOLCHAIN_ROOT = ROOT / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
ARTIFACT_NAME = "liba90_acdb_enter_combined_preload_v2539.so"
TARGET = "armv7a-linux-androideabi29"
COMMON_CFLAGS = (
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
    return {"path": rel(host_lib_dir), "linked": linked, "ready": {"libtinfo.so.5", "libxml2.so.2"}.issubset(linked.keys())}


def tool_env(host_libraries: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    ld_paths = [str(ROOT / host_libraries["path"])]
    if env.get("LD_LIBRARY_PATH"):
        ld_paths.append(env["LD_LIBRARY_PATH"])
    env["LD_LIBRARY_PATH"] = ":".join(ld_paths)
    return env


def source_state() -> dict[str, Any]:
    tap = ROOT / ACDBTAP_SOURCE_REL
    ioctl = ROOT / IOCTL_SOURCE_REL
    tap_text = tap.read_text(encoding="utf-8", errors="replace") if tap.exists() else ""
    ioctl_text = ioctl.read_text(encoding="utf-8", errors="replace") if ioctl.exists() else ""
    required = {
        "tap_source_exists": tap.exists(),
        "ioctl_source_exists": ioctl.exists(),
        "tap_enter_macro": "A90_ACDBTAP_LOG_ENTER" in tap_text,
        "tap_enter_event": "acdb_ioctl_call" in tap_text and "before_real" in tap_text,
        "tap_exports_acdb_ioctl": "acdb_ioctl(uint32_t cmd" in tap_text,
        "tap_dlsym_next": 'dlsym(A90_RTLD_NEXT, "acdb_ioctl")' in tap_text,
        "ioctl_exports_ioctl": "int ioctl(int fd, unsigned long request, ...)" in ioctl_text,
        "ioctl_fake_allocate_mode": "A90_ACDB_FAKE_ALLOCATE" in ioctl_text and "fake-success" in ioctl_text,
    }
    prohibited = {
        "tap_opens_msm_audio_cal": "/dev/msm_audio_cal" in tap_text,
        "ioctl_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in ioctl_text or "open('/dev/msm_audio_cal" in ioctl_text,
        "native_speaker_write": any(token in (tap_text + ioctl_text) for token in ("tinyplay", "tinymix", "AudioTrack")),
        "persistent_magisk_install": "magisk --install-module" in (tap_text + ioctl_text),
    }
    return {
        "sources": [ACDBTAP_SOURCE_REL, IOCTL_SOURCE_REL],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
    }


def compile_object(source: Path, obj: Path, *, clang: Path, env: dict[str, str], log_dir: Path, extra_cflags: tuple[str, ...] = ()) -> dict[str, Any]:
    command = [str(clang), *COMMON_CFLAGS, *extra_cflags, "-c", str(source), "-o", str(obj)]
    result = run(command, env=env)
    (log_dir / f"{obj.stem}.compile.stdout.txt").write_text(result["stdout"], encoding="utf-8", errors="replace")
    (log_dir / f"{obj.stem}.compile.stderr.txt").write_text(result["stderr"], encoding="utf-8", errors="replace")
    return {k: v for k, v in result.items() if k not in {"stdout", "stderr"}}


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    obj_dir = build_root / "obj"
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    obj_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    host_libraries = prepare_host_libraries(build_root)
    env = tool_env(host_libraries)
    tap_obj = obj_dir / "libacdbtap_enter_v2539.o"
    ioctl_obj = obj_dir / "a90_ioctl_trace_preload_v2531.o"
    out = bin_dir / ARTIFACT_NAME
    tap_compile = compile_object(ROOT / ACDBTAP_SOURCE_REL, tap_obj, clang=clang, env=env, log_dir=log_dir, extra_cflags=("-DA90_ACDBTAP_LOG_ENTER=1",))
    ioctl_compile = compile_object(ROOT / IOCTL_SOURCE_REL, ioctl_obj, clang=clang, env=env, log_dir=log_dir)
    if tap_compile["ok"] and ioctl_compile["ok"]:
        link_result = run([str(lld), *LDFLAGS, "-o", str(out), str(tap_obj), str(ioctl_obj)], env=env)
        (log_dir / "link.stdout.txt").write_text(link_result["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "link.stderr.txt").write_text(link_result["stderr"], encoding="utf-8", errors="replace")
        link_result = {k: v for k, v in link_result.items() if k not in {"stdout", "stderr"}}
        if link_result["ok"] and out.exists():
            out.chmod(0o600)
    else:
        link_result = {"ok": False, "skipped": True, "reason": "compile failed"}
    binary: dict[str, Any] = {"path": rel(out), "exists": out.exists()}
    if out.exists():
        symbols = run([readelf, "-Ws", str(out)], env=env, timeout=30.0)
        dyn = run([readelf, "-d", str(out)], env=env, timeout=30.0)
        binary.update({
            "sha256": sha256_file(out),
            "size": out.stat().st_size,
            "mode": oct(out.stat().st_mode & 0o777),
            "file": run([file_cmd, str(out)], timeout=30.0),
            "symbols": {
                "readelf_ok": symbols["ok"],
                "exports_acdb_ioctl": " acdb_ioctl" in symbols["stdout"],
                "exports_ioctl": " ioctl" in symbols["stdout"],
                "undefined_dlsym": " UND dlsym" in symbols["stdout"],
                "undefined_errno": " UND __errno" in symbols["stdout"],
            },
            "dynamic": {"readelf_ok": dyn["ok"], "soname": f"Library soname: [{ARTIFACT_NAME}]" in dyn["stdout"]},
        })
    return {
        "host_libraries": host_libraries,
        "compile": {"acdbtap_enter": tap_compile, "ioctl_trace": ioctl_compile},
        "link": link_result,
        "binary": binary,
        "ok": bool(tap_compile.get("ok") and ioctl_compile.get("ok") and link_result.get("ok") and binary.get("exists")),
    }


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    clang = Path(args.clang) if args.clang else TOOLCHAIN_ROOT / "bin/clang"
    lld = Path(args.lld) if args.lld else TOOLCHAIN_ROOT / "bin/ld.lld"
    payload: dict[str, Any] = {
        "decision": "v2539-acdb-enter-combined-preload-build-host-only",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "ok": True,
        "host_only": True,
        "artifact_name": ARTIFACT_NAME,
        "source_state": source_state(),
        "toolchain": {"root": rel(TOOLCHAIN_ROOT), "clang": rel(clang), "lld": rel(lld), "target": TARGET},
        "v2538_delta": "adds pre-return acdb_ioctl enter/before_real events to distinguish wrapper-not-called from real-acdb_ioctl-hung",
        "boundaries": {
            "single_preload_library": True,
            "logs_enter_before_real_acdb_ioctl": True,
            "fake_mode_requires_A90_ACDB_FAKE_ALLOCATE": True,
            "no_extra_msm_audio_cal_open": True,
            "no_speaker_write": True,
            "raw_payload_private_only": True,
        },
    }
    blockers: list[str] = []
    for name, path in {"clang": clang, "lld": lld}.items():
        if not path.exists():
            blockers.append(f"missing {name}: {rel(path)}")
    if not payload["source_state"]["required_ok"]:
        blockers.append("source required checks failed")
    if not payload["source_state"]["prohibited_ok"]:
        blockers.append("source prohibited checks failed")
    if blockers:
        payload["ok"] = False
        payload["blockers"] = blockers
    if args.build and not blockers:
        build_result = build(args.build_root, clang=clang, lld=lld, readelf=args.readelf, file_cmd=args.file_cmd)
        payload["build"] = build_result
        payload["ok"] = bool(build_result.get("ok"))
        if not payload["ok"]:
            payload.setdefault("blockers", []).append("build failed")
    if args.manifest_path:
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--clang", type=Path)
    parser.add_argument("--lld", type=Path)
    parser.add_argument("--readelf", default=str(TOOLCHAIN_ROOT / "bin/llvm-readelf"))
    parser.add_argument("--file-cmd", default="file")
    args = parser.parse_args()
    payload = manifest(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
