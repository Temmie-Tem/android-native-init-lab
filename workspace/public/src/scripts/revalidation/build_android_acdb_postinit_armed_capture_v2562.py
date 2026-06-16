#!/usr/bin/env python3
"""Build V2562 ARM32 post-init armed ACDB capture artifacts.

Host-only unit.  The private outputs are:

- a 32-bit Android PIE helper that calls acdb_loader_init_v3(), then explicitly
  calls a90_arm_capture(), then calls acdb_loader_send_common_custom_topology();
- a single 32-bit combined preload that exports acdb_ioctl(), ioctl(), and
  a90_arm_capture().

The key V2562 delta is that the acdb_ioctl wrapper is manual-arm only:
init-time calls pass through without dump/hash/file I/O.  The helper arms
capture only after acdb_loader_init_v3() returns and before the common-topology
GET sequence.  The preload still fakes the audio calibration allocate/dealloc/
SET ioctl path when A90_ACDB_FAKE_ALLOCATE=1, so this remains measurement-only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_android_acdb_armed_topology_exec_linked_v2540 as helper_base
import build_android_acdb_combined_preload_v2538 as preload_base

ROOT = helper_base.ROOT
RUN_ID = "V2562"
BUILD_TAG = "v2562-acdb-postinit-armed-capture-host-only"
HELPER_SOURCE_REL = helper_base.SOURCE_REL
ACDBTAP_SOURCE_REL = preload_base.ACDBTAP_SOURCE_REL
IOCTL_SOURCE_REL = preload_base.IOCTL_SOURCE_REL
TOOLCHAIN_ROOT = preload_base.TOOLCHAIN_ROOT
VENDOR_LIB_DIR = helper_base.VENDOR_LIB_DIR
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
HELPER_ARTIFACT_NAME = "a90_acdb_postinit_armed_topology_exec_linked_v2562"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_postinit_armed_capture_v2562.so"
TARGET = preload_base.TARGET
HELPER_CFLAGS = helper_base.CFLAGS
HELPER_LDFLAGS = helper_base.LDFLAGS
PRELOAD_CFLAGS = preload_base.CFLAGS
PRELOAD_TAP_CFLAGS = (
    "-DA90_ACDBTAP_ARMED_CAPTURE=1",
    "-DA90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=0",
    "-DA90_ACDBTAP_LOG_ENTER=0",
    "-DA90_ACDBTAP_EXIT_ON_TARGET=1",
)
PRELOAD_LDFLAGS = (
    "-shared",
    "--allow-shlib-undefined",
    "-soname",
    PRELOAD_ARTIFACT_NAME,
)
LINK_LIBS = helper_base.LINK_LIBS
REQUIRED_NEEDED = helper_base.REQUIRED_NEEDED


def rel(path: Path | str) -> str:
    return preload_base.rel(Path(path) if not isinstance(path, Path) else path)


def source_state() -> dict[str, Any]:
    helper_source = ROOT / HELPER_SOURCE_REL
    tap_source = ROOT / ACDBTAP_SOURCE_REL
    ioctl_source = ROOT / IOCTL_SOURCE_REL
    helper_text = helper_source.read_text(encoding="utf-8", errors="replace") if helper_source.exists() else ""
    tap_text = tap_source.read_text(encoding="utf-8", errors="replace") if tap_source.exists() else ""
    ioctl_text = ioctl_source.read_text(encoding="utf-8", errors="replace") if ioctl_source.exists() else ""
    required = {
        "helper_source_exists": helper_source.exists(),
        "tap_source_exists": tap_source.exists(),
        "ioctl_source_exists": ioctl_source.exists(),
        "helper_calls_init_v3": "acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U)" in helper_text,
        "helper_arms_after_init": "a90_arm_capture();" in helper_text and "armed_before_common_topology" in helper_text,
        "helper_calls_common_topology_after_arm": "acdb_loader_send_common_custom_topology()" in helper_text,
        "tap_exports_acdb_ioctl": "acdb_ioctl(uint32_t cmd" in tap_text,
        "tap_exports_arm_capture": "void a90_arm_capture(void)" in tap_text,
        "tap_armed_capture_macro": "A90_ACDBTAP_ARMED_CAPTURE" in tap_text,
        "tap_auto_arm_macro": "A90_ACDBTAP_AUTO_ARM_ON_INITIALIZE" in tap_text,
        "tap_unarmed_passthrough": "if (!a90_armed)" in tap_text and "return ret;" in tap_text,
        "tap_all_zero_guard": "a90_is_all_zero" in tap_text and "all_zero" in tap_text,
        "tap_exit_after_target": "a90_exit_group(0)" in tap_text,
        "ioctl_exports_ioctl": "int ioctl(int fd, unsigned long request, ...)" in ioctl_text,
        "ioctl_fake_allocate_mode": "A90_ACDB_FAKE_ALLOCATE" in ioctl_text and "fake-success" in ioctl_text,
        "ioctl_fakes_allocate_deallocate_set": (
            "A90_AUDIO_ALLOCATE_CALIBRATION" in ioctl_text
            and "A90_AUDIO_DEALLOCATE_CALIBRATION" in ioctl_text
            and "A90_AUDIO_SET_CALIBRATION" in ioctl_text
        ),
    }
    prohibited = {
        "helper_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in helper_text or "open('/dev/msm_audio_cal" in helper_text,
        "helper_issues_ioctl": "ioctl(" in helper_text or "A90_NR_IOCTL" in helper_text,
        "tap_opens_msm_audio_cal": "/dev/msm_audio_cal" in tap_text,
        "ioctl_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in ioctl_text or "open('/dev/msm_audio_cal" in ioctl_text,
        "native_speaker_write": any(token in (helper_text + tap_text + ioctl_text) for token in ("tinyplay", "tinymix", "AudioTrack")),
        "persistent_magisk_install": "magisk --install-module" in (helper_text + tap_text + ioctl_text),
    }
    return {
        "sources": [HELPER_SOURCE_REL, ACDBTAP_SOURCE_REL, IOCTL_SOURCE_REL],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
    }


def compile_object(source: Path, obj: Path, *, clang: Path, env: dict[str, str], log_dir: Path, cflags: tuple[str, ...], extra: tuple[str, ...] = ()) -> dict[str, Any]:
    command = [str(clang), *cflags, *extra, "-c", str(source), "-o", str(obj)]
    result = preload_base.run(command, env=env)
    (log_dir / f"{obj.stem}.compile.stdout.txt").write_text(result["stdout"], encoding="utf-8", errors="replace")
    (log_dir / f"{obj.stem}.compile.stderr.txt").write_text(result["stderr"], encoding="utf-8", errors="replace")
    return {k: v for k, v in result.items() if k not in {"stdout", "stderr"}}


def binary_state(path: Path, *, readelf: str, file_cmd: str, kind: str) -> dict[str, Any]:
    state: dict[str, Any] = {"path": rel(path), "exists": path.exists(), "kind": kind}
    if not path.exists():
        state["ok"] = False
        return state
    symbols = preload_base.run([readelf, "-Ws", str(path)], timeout=30.0)
    dynamic = preload_base.run([readelf, "-d", str(path)], timeout=30.0)
    header = preload_base.run([readelf, "-h", str(path)], timeout=30.0)
    file_result = preload_base.run([file_cmd, str(path)], timeout=30.0)
    state.update({
        "sha256": preload_base.sha256_file(path),
        "size": path.stat().st_size,
        "mode": oct(path.stat().st_mode & 0o777),
        "file": file_result,
        "symbols": {"readelf_ok": symbols["ok"], "stdout": symbols["stdout"]},
        "dynamic": {"readelf_ok": dynamic["ok"], "stdout": dynamic["stdout"]},
        "header": {"readelf_ok": header["ok"], "stdout": header["stdout"]},
    })
    sym = symbols["stdout"]
    dyn = dynamic["stdout"]
    hdr = header["stdout"]
    if kind == "helper":
        state["checks"] = {
            "is_pie": "DYN (Shared object file)" in hdr,
            "entry_start": "_start" in sym,
            "undefined_init_v3": " UND acdb_loader_init_v3" in sym,
            "undefined_common_topology": " UND acdb_loader_send_common_custom_topology" in sym,
            "weak_undefined_arm_capture": " WEAK" in sym and " UND a90_arm_capture" in sym,
            "needed_libacdbloader": "Shared library: [libacdbloader.so]" in dyn,
            "needed_libaudcal": "Shared library: [libaudcal.so]" in dyn,
        }
    else:
        state["checks"] = {
            "exports_acdb_ioctl": " acdb_ioctl" in sym,
            "exports_ioctl": " ioctl" in sym,
            "exports_a90_arm_capture": " a90_arm_capture" in sym,
            "undefined_dlsym": " UND dlsym" in sym,
            "undefined_errno": " UND __errno" in sym,
            "soname": f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in dyn,
        }
    state["ok"] = bool(file_result.get("ok") and all(state["checks"].values()))
    return state


def vendor_lib_state(readelf: str) -> dict[str, Any]:
    state = helper_base.base.vendor_lib_state(readelf)
    loader = VENDOR_LIB_DIR / "libacdbloader.so"
    loader_symbol_text = ""
    if loader.exists():
        symbols = preload_base.run([readelf, "-Ws", str(loader)], timeout=30.0)
        loader_symbol_text = symbols["stdout"] if symbols["ok"] else ""
    loader_symbol_flags = state.get("libacdbloader_symbols", {})
    state["required_for_v2562"] = {
        "has_acdb_loader_init_v3": loader_symbol_flags.get("has_acdb_loader_init_v3"),
        "has_acdb_loader_send_common_custom_topology": " acdb_loader_send_common_custom_topology" in loader_symbol_text,
        "imports_acdb_ioctl": loader_symbol_flags.get("imports_acdb_ioctl"),
    }
    state["required_for_v2562_ok"] = all(state["required_for_v2562"].values())
    return state


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    obj_dir = build_root / "obj"
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    obj_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    missing = [name for name in REQUIRED_NEEDED if not (VENDOR_LIB_DIR / name).exists()]
    if missing:
        return {"ok": False, "error": f"missing private ACDB closure libs: {', '.join(missing)}"}

    host_libraries = preload_base.prepare_host_libraries(build_root)
    env = preload_base.tool_env(host_libraries)

    helper_obj = obj_dir / "a90_acdb_postinit_armed_topology_exec_linked_v2562.o"
    tap_obj = obj_dir / "libacdbtap_v2475_postinit_manual.o"
    ioctl_obj = obj_dir / "a90_ioctl_trace_preload_v2531.o"
    helper_out = bin_dir / HELPER_ARTIFACT_NAME
    preload_out = bin_dir / PRELOAD_ARTIFACT_NAME

    helper_compile = compile_object(ROOT / HELPER_SOURCE_REL, helper_obj, clang=clang, env=env, log_dir=log_dir, cflags=HELPER_CFLAGS)
    tap_compile = compile_object(ROOT / ACDBTAP_SOURCE_REL, tap_obj, clang=clang, env=env, log_dir=log_dir, cflags=PRELOAD_CFLAGS, extra=PRELOAD_TAP_CFLAGS)
    ioctl_compile = compile_object(ROOT / IOCTL_SOURCE_REL, ioctl_obj, clang=clang, env=env, log_dir=log_dir, cflags=PRELOAD_CFLAGS)

    if helper_compile["ok"]:
        helper_link_cmd = [
            str(lld),
            *HELPER_LDFLAGS,
            "-L",
            str(VENDOR_LIB_DIR),
            "-o",
            str(helper_out),
            str(helper_obj),
            *LINK_LIBS,
        ]
        helper_link = preload_base.run(helper_link_cmd, env=env)
        (log_dir / "helper.link.stdout.txt").write_text(helper_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "helper.link.stderr.txt").write_text(helper_link["stderr"], encoding="utf-8", errors="replace")
        helper_link = {k: v for k, v in helper_link.items() if k not in {"stdout", "stderr"}}
        if helper_link["ok"] and helper_out.exists():
            helper_out.chmod(0o600)
    else:
        helper_link = {"ok": False, "skipped": True, "reason": "helper compile failed"}

    if tap_compile["ok"] and ioctl_compile["ok"]:
        preload_link_cmd = [str(lld), *PRELOAD_LDFLAGS, "-o", str(preload_out), str(tap_obj), str(ioctl_obj)]
        preload_link = preload_base.run(preload_link_cmd, env=env)
        (log_dir / "preload.link.stdout.txt").write_text(preload_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "preload.link.stderr.txt").write_text(preload_link["stderr"], encoding="utf-8", errors="replace")
        preload_link = {k: v for k, v in preload_link.items() if k not in {"stdout", "stderr"}}
        if preload_link["ok"] and preload_out.exists():
            preload_out.chmod(0o600)
    else:
        preload_link = {"ok": False, "skipped": True, "reason": "preload compile failed"}

    helper = binary_state(helper_out, readelf=readelf, file_cmd=file_cmd, kind="helper")
    preload = binary_state(preload_out, readelf=readelf, file_cmd=file_cmd, kind="preload")
    return {
        "host_libraries": host_libraries,
        "compile": {"helper": helper_compile, "acdbtap_postinit_manual": tap_compile, "ioctl_trace": ioctl_compile},
        "link": {"helper": helper_link, "preload": preload_link},
        "logs": rel(log_dir),
        "helper": helper,
        "preload": preload,
        "ok": bool(
            helper_compile.get("ok")
            and tap_compile.get("ok")
            and ioctl_compile.get("ok")
            and helper_link.get("ok")
            and preload_link.get("ok")
            and helper.get("ok")
            and preload.get("ok")
        ),
    }


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    clang = Path(args.clang) if args.clang else TOOLCHAIN_ROOT / "bin/clang"
    lld = Path(args.lld) if args.lld else TOOLCHAIN_ROOT / "bin/ld.lld"
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": preload_base.now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "android_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "source_state": source_state(),
        "vendor_lib_state": vendor_lib_state(args.readelf),
        "capture_contract": {
            "helper": HELPER_ARTIFACT_NAME,
            "preload": PRELOAD_ARTIFACT_NAME,
            "abi": "32-bit armeabi-v7a",
            "unarmed_policy": "all acdb_ioctl calls pass through with no dump/hash/file I/O; no auto-arm on INITIALIZE_V2",
            "arm_point": "helper calls a90_arm_capture immediately after acdb_loader_init_v3 returns and before acdb_loader_send_common_custom_topology",
            "armed_policy": "dump every out_len>0; exit immediately after first ret==0 non-all-zero 4916-byte buffer",
            "fake_audio_cal_allocate_env": "A90_ACDB_FAKE_ALLOCATE=1",
            "raw_output_private_only": True,
        },
        "boundaries": {
            "host_only_build": True,
            "no_live_device_action": True,
            "no_native_msm_audio_cal_open": True,
            "no_extra_ioctl_issuance": True,
            "no_speaker_write": True,
            "raw_output_private_only": True,
        },
        "toolchain": {
            "clang": str(clang),
            "lld": str(lld),
            "readelf": args.readelf,
            "file": args.file,
            "helper_cflags": list(HELPER_CFLAGS),
            "preload_cflags": [*PRELOAD_CFLAGS, *PRELOAD_TAP_CFLAGS],
            "target": TARGET,
        },
        "build_root": rel(args.build_root),
    }
    if args.build:
        payload["build"] = build(args.build_root, clang=clang, lld=lld, readelf=args.readelf, file_cmd=args.file)
    else:
        payload["build"] = {"built": False, "reason": "pass --build to materialize private ARM32 artifacts"}
    payload["ok"] = bool(
        payload["source_state"]["required_ok"]
        and payload["source_state"]["prohibited_ok"]
        and payload["vendor_lib_state"].get("required_for_v2562_ok")
        and (not args.build or payload.get("build", {}).get("ok"))
    )
    payload["manifest_path"] = rel(args.manifest_path)
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--clang", type=Path, default=TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    payload = manifest(parse_args(argv))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
