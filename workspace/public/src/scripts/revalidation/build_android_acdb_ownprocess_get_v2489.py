#!/usr/bin/env python3
"""Build V2489 ARM32 own-process ACDB pure-read GET helper.

Host-only unit.  The output is a private 32-bit Android PIE intended for a
future bounded Android run.  This script does not boot Android, stage files, run
AudioTrack, or issue any native calibration ioctl.
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
RUN_ID = "V2489"
BUILD_TAG = "v2489-acdb-ownprocess-get-host-only"
SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_ownprocess_get_v2489.c"
TOOLCHAIN_ROOT = ROOT / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0"
VENDOR_DUMP = ROOT / "workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/lib"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
ARTIFACT_NAME = "a90_acdb_ownprocess_get_v2489"
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
    "-pie",
    "-e",
    "_start",
    "--allow-shlib-undefined",
    "-dynamic-linker",
    "/system/bin/linker",
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
    return next((path for path in candidates if path.exists()), None)


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
        "custom_start": "void _start(void)" in text,
        "uses_dlopen_libaudcal": 'dlopen("libaudcal.so"' in text,
        "uses_dlopen_libacdbloader": 'dlopen("libacdbloader.so"' in text,
        "uses_dlsym_init_v3": 'dlsym(loader, "acdb_loader_init_v3")' in text,
        "uses_dlsym_acdb_ioctl": 'dlsym(audcal, "acdb_ioctl")' in text,
        "uses_dlerror_detail": "dlerror()" in text and '\\"detail\\":' in text,
        "calls_init_v3": "init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U)" in text,
        "has_operator_get_cmd_11394": "0x00011394U" in text,
        "has_operator_get_cmd_12e01": "0x00012e01U" in text,
        "has_operator_get_cmd_130da": "0x000130daU" in text,
        "has_operator_get_cmd_130dc": "0x000130dcU" in text,
        "target_out_len_4916": "A90_TARGET_OUT_LEN 4916U" in text,
        "size_query_out_len_4": "A90_SIZE_QUERY_OUT_LEN 4U" in text,
        "private_capture_dir": "/data/local/tmp/a90-acdb-ownget" in text,
        "sha256_implemented": "a90_sha256_final" in text,
        "raw_syscalls_only": "A90_NR_OPENAT" in text and "A90_NR_WRITE" in text,
        "no_libc_headers": "#include <" not in text,
    }
    prohibited = {
        "opens_msm_audio_cal": "/dev/msm_audio_cal" in text,
        "forbidden_set_ioctl_constant": "0xC00461CB" in text or "0xc00461cb" in text,
        "audio_calibration_ioctl": "AUDIO_SET_CALIBRATION" in text or "AUDIO_ALLOCATE_CALIBRATION" in text,
        "loader_topology_send_path": "acdb_loader_send_common_custom_topology" in text,
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
        "bounded_matrix": {
            "commands": ["0x11394", "0x12e01", "0x130da", "0x130dc"],
            "in_lens": [0, 4, 8, 16, 32],
            "out_lens": [4, 4916],
            "max_calls": 40,
        },
    }


def vendor_symbol_state(readelf: str) -> dict[str, Any]:
    libs = {
        "libacdbloader.so": VENDOR_DUMP / "libacdbloader.so",
        "libaudcal.so": VENDOR_DUMP / "libaudcal.so",
        "libacdb-fts.so": VENDOR_DUMP / "libacdb-fts.so",
        "libacdbrtac.so": VENDOR_DUMP / "libacdbrtac.so",
        "libadiertac.so": VENDOR_DUMP / "libadiertac.so",
    }
    state: dict[str, Any] = {"vendor_dump": rel(VENDOR_DUMP), "libs": {}}
    for name, path in libs.items():
        state["libs"][name] = {"path": rel(path), "exists": path.exists()}
    if libs["libacdbloader.so"].exists():
        loader = run([readelf, "-Ws", str(libs["libacdbloader.so"])], timeout=30.0)
        out = loader["stdout"]
        state["libacdbloader_symbols"] = {
            "readelf_ok": loader["ok"],
            "has_acdb_loader_init_v3": " acdb_loader_init_v3" in out,
            "has_acdb_loader_init_v4": " acdb_loader_init_v4" in out,
            "has_acdb_loader_send_common_custom_topology": " acdb_loader_send_common_custom_topology" in out,
            "imports_acdb_ioctl": " UND acdb_ioctl" in out,
        }
    if libs["libaudcal.so"].exists():
        audcal = run([readelf, "-Ws", str(libs["libaudcal.so"])], timeout=30.0)
        out = audcal["stdout"]
        state["libaudcal_symbols"] = {
            "readelf_ok": audcal["ok"],
            "exports_acdb_ioctl": " acdb_ioctl" in out,
        }
    return state


def build_libdl_stub(build_root: Path, *, clang: Path, lld: Path, env: dict[str, str], log_dir: Path) -> dict[str, Any]:
    stub_dir = build_root / "stub-libdl"
    stub_dir.mkdir(parents=True, exist_ok=True)
    source = stub_dir / "libdl_stub.c"
    obj = stub_dir / "libdl_stub.o"
    so = stub_dir / "libdl.so"
    source.write_text(
        "__attribute__((visibility(\"default\"))) void *dlopen(const char *name, int flags) { (void)name; (void)flags; return (void *)0; }\n"
        "__attribute__((visibility(\"default\"))) void *dlsym(void *handle, const char *name) { (void)handle; (void)name; return (void *)0; }\n"
        "__attribute__((visibility(\"default\"))) char *dlerror(void) { return (char *)0; }\n",
        encoding="utf-8",
    )
    compile_result = run([str(clang), *CFLAGS, "-c", str(source), "-o", str(obj)], env=env, timeout=180.0)
    (log_dir / "libdl_stub.compile.stderr.txt").write_text(compile_result["stderr"], encoding="utf-8", errors="replace")
    if not compile_result["ok"]:
        raise RuntimeError(f"libdl stub compile failed; see {rel(log_dir / 'libdl_stub.compile.stderr.txt')}")
    link_result = run([str(lld), "-shared", "-soname", "libdl.so", "-o", str(so), str(obj)], env=env, timeout=180.0)
    (log_dir / "libdl_stub.link.stderr.txt").write_text(link_result["stderr"], encoding="utf-8", errors="replace")
    if not link_result["ok"]:
        raise RuntimeError(f"libdl stub link failed; see {rel(log_dir / 'libdl_stub.link.stderr.txt')}")
    return {
        "path": rel(so),
        "sha256": sha256_file(so),
        "private_generated": True,
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
    stub = build_libdl_stub(build_root, clang=clang, lld=lld, env=env, log_dir=log_dir)
    obj = obj_dir / "a90_acdb_ownprocess_get_v2489.o"
    out = bin_dir / ARTIFACT_NAME

    compile_cmd = [str(clang), *CFLAGS, "-c", str(source), "-o", str(obj)]
    compile_result = run(compile_cmd, env=env, timeout=180.0)
    (log_dir / "compile.stdout.txt").write_text(compile_result["stdout"], encoding="utf-8", errors="replace")
    (log_dir / "compile.stderr.txt").write_text(compile_result["stderr"], encoding="utf-8", errors="replace")
    if not compile_result["ok"]:
        raise RuntimeError(f"compile failed; see {rel(log_dir / 'compile.stderr.txt')}")

    stub_dir = ROOT / stub["path"]
    stub_dir = stub_dir.parent
    link_cmd = [
        str(lld),
        *LDFLAGS,
        "-L",
        str(stub_dir),
        "-o",
        str(out),
        str(obj),
        "-ldl",
    ]
    link_result = run(link_cmd, env=env, timeout=180.0)
    (log_dir / "link.stdout.txt").write_text(link_result["stdout"], encoding="utf-8", errors="replace")
    (log_dir / "link.stderr.txt").write_text(link_result["stderr"], encoding="utf-8", errors="replace")
    if not link_result["ok"]:
        raise RuntimeError(f"link failed; see {rel(log_dir / 'link.stderr.txt')}")

    file_result = run([file_cmd, str(out)], timeout=10.0)
    readelf_header = run([readelf, "-h", str(out)], timeout=30.0)
    readelf_dynamic = run([readelf, "-d", str(out)], timeout=30.0)
    readelf_symbols = run([readelf, "-Ws", str(out)], timeout=30.0)
    (log_dir / "readelf.header.txt").write_text(readelf_header["stdout"], encoding="utf-8", errors="replace")
    (log_dir / "readelf.dynamic.txt").write_text(readelf_dynamic["stdout"], encoding="utf-8", errors="replace")
    (log_dir / "readelf.symbols.txt").write_text(readelf_symbols["stdout"], encoding="utf-8", errors="replace")
    for result, name in (
        (file_result, "file"),
        (readelf_header, "readelf header"),
        (readelf_dynamic, "readelf dynamic"),
        (readelf_symbols, "readelf symbols"),
    ):
        if not result["ok"]:
            raise RuntimeError(result["stderr"] or result["stdout"] or f"{name} failed")

    symbols = readelf_symbols["stdout"]
    dynamic = readelf_dynamic["stdout"]
    header = readelf_header["stdout"]
    return {
        "host_libraries": host_libraries,
        "stub_libdl": stub,
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
            "target": TARGET,
            "private_generated": True,
            "entry_start": "_start" in symbols,
            "needed_libdl": "Shared library: [libdl.so]" in dynamic,
            "undefined_dlopen": " UND dlopen" in symbols,
            "undefined_dlsym": " UND dlsym" in symbols,
            "undefined_dlerror": " UND dlerror" in symbols,
            "interpreter_system_linker": "/system/bin/linker" in file_result["stdout"]
            or "Requesting program interpreter: /system/bin/linker" in header
            or "/system/bin/linker" in dynamic,
            "readelf_header": rel(log_dir / "readelf.header.txt"),
            "readelf_dynamic": rel(log_dir / "readelf.dynamic.txt"),
            "readelf_symbols": rel(log_dir / "readelf.symbols.txt"),
        },
    }


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "decision": "v2489-acdb-ownprocess-get-host-only",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "ok": True,
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "android_action": "none",
        "source_state": source_state(),
        "vendor_symbol_state": vendor_symbol_state(args.readelf),
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "capture_contract": {
            "artifact": ARTIFACT_NAME,
            "abi": "32-bit armeabi-v7a PIE",
            "load_strategy": "dlopen libaudcal.so and libacdbloader.so, then dlsym acdb_loader_init_v3/acdb_ioctl",
            "acdb_init": {
                "function": "acdb_loader_init_v3",
                "acdb_files_path": "/vendor/etc/acdbdata",
                "delta_file_path": "/data/local/tmp/a90-acdb-ownget/delta",
                "meta_info_type": 0,
            },
            "capture_dir": "/data/local/tmp/a90-acdb-ownget",
            "commands": ["0x11394", "0x12e01", "0x130da", "0x130dc"],
            "in_lens": [0, 4, 8, 16, 32],
            "out_lens": [4, 4916],
            "max_acdb_ioctl_calls": 40,
            "public_output": "metadata and SHA-256 only",
            "raw_output": "private /data/local/tmp then workspace/private only",
        },
        "boundaries": {
            "no_native_msm_audio_cal_ioctls": True,
            "no_forbidden_set_ioctl": True,
            "no_loader_send_common_custom_topology": True,
            "no_native_speaker_write": True,
            "no_android_live_staging": True,
            "live_execution_blocked_in_this_unit": True,
        },
        "toolchain": {
            "clang": str(args.clang),
            "lld": str(args.lld),
            "readelf": args.readelf,
            "file": args.file,
            "cflags": list(CFLAGS),
            "ldflags": list(LDFLAGS),
            "target": TARGET,
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
        payload["build"] = {"built": False, "reason": "pass --build to materialize private ARM32 helper"}
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
