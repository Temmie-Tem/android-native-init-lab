#!/usr/bin/env python3
"""Build V2568 ARM32 pre-init-tail ACDB per-device capture artifacts.

Host-only unit.  The private outputs are:

- a 32-bit Android PIE helper that calls acdb_loader_init_v3();
- a single 32-bit preload exporting acdb_ioctl(), ioctl(), and
  acdb_loader_send_common_custom_topology().

The preload keeps acdb_ioctl quiet until ACDB_CMD_INITIALIZE_V2 has succeeded,
captures the real common-topology GETs, patches the known init flag, then calls
acdb_loader_send_audio_cal_v5() before returning to the crashing init_v4 tail.
The ioctl hook keeps AUDIO_ALLOCATE/DEALLOCATE/SET fake-success when
A90_ACDB_FAKE_ALLOCATE=1, so the unit remains measurement-only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_android_acdb_armed_topology_exec_linked_v2540 as helper_base
import build_android_acdb_combined_preload_v2538 as preload_base

ROOT = helper_base.ROOT
RUN_ID = "V2568"
BUILD_TAG = "v2568-acdb-preinit-perdevice-capture-host-only"
HELPER_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_init_drive_exec_linked_v2568.c"
ACDBTAP_SOURCE_REL = preload_base.ACDBTAP_SOURCE_REL
IOCTL_SOURCE_REL = preload_base.IOCTL_SOURCE_REL
PREINIT_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdb_preinit_perdevice_v2568.c"
TOOLCHAIN_ROOT = preload_base.TOOLCHAIN_ROOT
VENDOR_LIB_DIR = helper_base.VENDOR_LIB_DIR
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
HELPER_ARTIFACT_NAME = "a90_acdb_preinit_perdevice_exec_linked_v2568"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_preinit_perdevice_capture_v2568.so"
HELPER_CFLAGS = helper_base.CFLAGS
HELPER_LDFLAGS = helper_base.LDFLAGS
PRELOAD_CFLAGS = preload_base.CFLAGS
PRELOAD_TAP_CFLAGS = (
    "-DA90_ACDBTAP_ARMED_CAPTURE=1",
    "-DA90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=1",
    "-DA90_ACDBTAP_CUSTOM_TOPOLOGY_ONLY=0",
    "-DA90_ACDBTAP_LOG_ENTER=0",
    "-DA90_ACDBTAP_EXIT_ON_TARGET=0",
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
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def compile_object(
    source: Path,
    obj: Path,
    *,
    clang: Path,
    env: dict[str, str],
    log_dir: Path,
    cflags: tuple[str, ...],
    extra: tuple[str, ...] = (),
) -> dict[str, Any]:
    command = [str(clang), *cflags, *extra, "-c", str(source), "-o", str(obj)]
    result = preload_base.run(command, env=env)
    (log_dir / f"{obj.stem}.compile.stdout.txt").write_text(result["stdout"], encoding="utf-8", errors="replace")
    (log_dir / f"{obj.stem}.compile.stderr.txt").write_text(result["stderr"], encoding="utf-8", errors="replace")
    return {k: v for k, v in result.items() if k not in {"stdout", "stderr"}}


def source_state() -> dict[str, Any]:
    paths = {
        "helper": ROOT / HELPER_SOURCE_REL,
        "tap": ROOT / ACDBTAP_SOURCE_REL,
        "ioctl": ROOT / IOCTL_SOURCE_REL,
        "preinit": ROOT / PREINIT_SOURCE_REL,
    }
    texts = {
        name: path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        for name, path in paths.items()
    }
    combined = "\n".join(texts.values())
    required = {
        "helper_source_exists": paths["helper"].exists(),
        "tap_source_exists": paths["tap"].exists(),
        "ioctl_source_exists": paths["ioctl"].exists(),
        "preinit_source_exists": paths["preinit"].exists(),
        "helper_calls_init_v3": "acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U)" in texts["helper"],
        "preinit_exports_common_topology": "int32_t acdb_loader_send_common_custom_topology(void)" in texts["preinit"],
        "preinit_calls_real_common_topology": "a90_real_common_topology()" in texts["preinit"],
        "preinit_patches_init_flag": "A90_LOADER_INIT_FLAG_OFF" in texts["preinit"] and "*flag = 1U" in texts["preinit"],
        "preinit_calls_send_audio_cal_v5": "a90_real_send_audio_cal_v5(A90_SPEAKER_ACDB_ID" in texts["preinit"],
        "preinit_exits_before_init_tail": "exit_before_init_tail" in texts["preinit"] and "a90_exit_group(0)" in texts["preinit"],
        "tap_has_manual_arm": "void a90_arm_capture(void)" in texts["tap"],
        "tap_has_initialize_auto_arm": "A90_ACDBTAP_AUTO_ARM_ON_INITIALIZE" in texts["tap"],
        "tap_has_nonzero_guard": "a90_is_all_zero" in texts["tap"] and "all_zero" in texts["tap"],
        "ioctl_fake_allocate_set": (
            "A90_AUDIO_ALLOCATE_CALIBRATION" in texts["ioctl"]
            and "A90_AUDIO_DEALLOCATE_CALIBRATION" in texts["ioctl"]
            and "A90_AUDIO_SET_CALIBRATION" in texts["ioctl"]
            and "fake-success" in texts["ioctl"]
        ),
    }
    prohibited = {
        "helper_issues_ioctl": "ioctl(" in texts["helper"] or "A90_NR_IOCTL" in texts["helper"],
        "preinit_opens_msm_audio_cal": "/dev/msm_audio_cal" in texts["preinit"],
        "helper_opens_msm_audio_cal": "/dev/msm_audio_cal" in texts["helper"],
        "persistent_magisk_install": "magisk --install-module" in combined,
        "native_speaker_write": any(token in combined for token in ("tinyplay", "tinymix", "AudioTrack")),
    }
    return {
        "sources": [HELPER_SOURCE_REL, ACDBTAP_SOURCE_REL, IOCTL_SOURCE_REL, PREINIT_SOURCE_REL],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
    }


def binary_state(path: Path, *, readelf: str, file_cmd: str, kind: str) -> dict[str, Any]:
    state: dict[str, Any] = {"path": rel(path), "exists": path.exists(), "kind": kind}
    if not path.exists():
        state["ok"] = False
        return state
    symbols = preload_base.run([readelf, "-Ws", str(path)], timeout=30.0)
    dynamic = preload_base.run([readelf, "-d", str(path)], timeout=30.0)
    header = preload_base.run([readelf, "-h", str(path)], timeout=30.0)
    file_result = preload_base.run([file_cmd, str(path)], timeout=30.0)
    state.update(
        {
            "sha256": preload_base.sha256_file(path),
            "size": path.stat().st_size,
            "mode": oct(path.stat().st_mode & 0o777),
            "file": {k: v for k, v in file_result.items() if k not in {"stdout", "stderr"}},
            "symbols": {"readelf_ok": symbols["ok"], "stdout": symbols["stdout"]},
            "dynamic": {"readelf_ok": dynamic["ok"], "stdout": dynamic["stdout"]},
            "header": {"readelf_ok": header["ok"], "stdout": header["stdout"]},
        }
    )
    sym = symbols["stdout"]
    dyn = dynamic["stdout"]
    hdr = header["stdout"]
    if kind == "helper":
        checks = {
            "is_pie": "DYN (Shared object file)" in hdr,
            "entry_start": "_start" in sym,
            "undefined_init_v3": " UND acdb_loader_init_v3" in sym,
            "needed_libacdbloader": "Shared library: [libacdbloader.so]" in dyn,
            "needed_libaudcal": "Shared library: [libaudcal.so]" in dyn,
        }
    else:
        checks = {
            "exports_acdb_ioctl": " acdb_ioctl" in sym,
            "exports_ioctl": " ioctl" in sym,
            "exports_common_topology": " acdb_loader_send_common_custom_topology" in sym,
            "exports_a90_arm_capture": " a90_arm_capture" in sym,
            "undefined_dlsym": " UND dlsym" in sym,
            "undefined_errno": " UND __errno" in sym,
            "soname": f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in dyn,
        }
    state["checks"] = checks
    state["ok"] = bool(file_result.get("ok") and all(checks.values()))
    return state


def vendor_lib_state(readelf: str) -> dict[str, Any]:
    state = helper_base.base.vendor_lib_state(readelf)
    loader = VENDOR_LIB_DIR / "libacdbloader.so"
    loader_symbol_text = ""
    if loader.exists():
        symbols = preload_base.run([readelf, "-Ws", str(loader)], timeout=30.0)
        loader_symbol_text = symbols["stdout"] if symbols["ok"] else ""
    flags = state.get("libacdbloader_symbols", {})
    required = {
        "has_acdb_loader_init_v3": flags.get("has_acdb_loader_init_v3"),
        "has_acdb_loader_is_initialized": " acdb_loader_is_initialized" in loader_symbol_text,
        "has_acdb_loader_send_common_custom_topology": " acdb_loader_send_common_custom_topology" in loader_symbol_text,
        "has_acdb_loader_send_audio_cal_v5": " acdb_loader_send_audio_cal_v5" in loader_symbol_text,
        "imports_acdb_ioctl": flags.get("imports_acdb_ioctl"),
    }
    state["required_for_v2568"] = required
    state["required_for_v2568_ok"] = all(required.values())
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

    helper_obj = obj_dir / "a90_acdb_init_drive_exec_linked_v2568.o"
    tap_obj = obj_dir / "libacdbtap_v2475_v2568.o"
    ioctl_obj = obj_dir / "a90_ioctl_trace_preload_v2531.o"
    preinit_obj = obj_dir / "libacdb_preinit_perdevice_v2568.o"
    helper_out = bin_dir / HELPER_ARTIFACT_NAME
    preload_out = bin_dir / PRELOAD_ARTIFACT_NAME

    helper_compile = compile_object(ROOT / HELPER_SOURCE_REL, helper_obj, clang=clang, env=env, log_dir=log_dir, cflags=HELPER_CFLAGS)
    tap_compile = compile_object(ROOT / ACDBTAP_SOURCE_REL, tap_obj, clang=clang, env=env, log_dir=log_dir, cflags=PRELOAD_CFLAGS, extra=PRELOAD_TAP_CFLAGS)
    ioctl_compile = compile_object(ROOT / IOCTL_SOURCE_REL, ioctl_obj, clang=clang, env=env, log_dir=log_dir, cflags=PRELOAD_CFLAGS)
    preinit_compile = compile_object(ROOT / PREINIT_SOURCE_REL, preinit_obj, clang=clang, env=env, log_dir=log_dir, cflags=PRELOAD_CFLAGS)

    if helper_compile["ok"]:
        helper_link = preload_base.run(
            [
                str(lld),
                *HELPER_LDFLAGS,
                "-L",
                str(VENDOR_LIB_DIR),
                "-o",
                str(helper_out),
                str(helper_obj),
                *LINK_LIBS,
            ],
            env=env,
        )
        (log_dir / "helper.link.stdout.txt").write_text(helper_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "helper.link.stderr.txt").write_text(helper_link["stderr"], encoding="utf-8", errors="replace")
        helper_link = {k: v for k, v in helper_link.items() if k not in {"stdout", "stderr"}}
        if helper_link["ok"] and helper_out.exists():
            helper_out.chmod(0o600)
    else:
        helper_link = {"ok": False, "skipped": True, "reason": "helper compile failed"}

    preload_compile_ok = tap_compile["ok"] and ioctl_compile["ok"] and preinit_compile["ok"]
    if preload_compile_ok:
        preload_link = preload_base.run(
            [str(lld), *PRELOAD_LDFLAGS, "-o", str(preload_out), str(tap_obj), str(ioctl_obj), str(preinit_obj)],
            env=env,
        )
        (log_dir / "preload.link.stdout.txt").write_text(preload_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "preload.link.stderr.txt").write_text(preload_link["stderr"], encoding="utf-8", errors="replace")
        preload_link = {k: v for k, v in preload_link.items() if k not in {"stdout", "stderr"}}
        if preload_link["ok"] and preload_out.exists():
            preload_out.chmod(0o600)
    else:
        preload_link = {"ok": False, "skipped": True, "reason": "preload compile failed"}

    helper_state = binary_state(helper_out, readelf=readelf, file_cmd=file_cmd, kind="helper")
    preload_state = binary_state(preload_out, readelf=readelf, file_cmd=file_cmd, kind="preload")
    return {
        "host_libraries": host_libraries,
        "compile": {
            "helper": helper_compile,
            "acdbtap": tap_compile,
            "ioctl_trace": ioctl_compile,
            "preinit_perdevice": preinit_compile,
        },
        "link": {"helper": helper_link, "preload": preload_link},
        "artifacts": {"helper": helper_state, "preload": preload_state},
        "ok": bool(helper_state.get("ok") and preload_state.get("ok")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--clang", type=Path, default=TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    args = parser.parse_args()

    source = source_state()
    vendor = vendor_lib_state(args.readelf)
    if args.build:
        build_state = build(args.build_root, clang=args.clang, lld=args.lld, readelf=args.readelf, file_cmd=args.file)
    else:
        build_state = {"built": False, "reason": "pass --build to materialize private ARM32 artifacts"}

    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "host_only_build": True,
        "measurement_boundary": {
            "no_native_replay": True,
            "no_speaker_write": True,
            "raw_payload_private_only": True,
            "fake_audio_cal_env": "A90_ACDB_FAKE_ALLOCATE=1",
            "no_real_audio_set": "ioctl preload fake-successes AUDIO_SET_CALIBRATION in fake mode",
        },
        "capture_contract": {
            "arm_policy": "silent until ACDB_CMD_INITIALIZE_V2 succeeds; capture all armed out_len>0 records",
            "common_topology_policy": "call real common-topology first to preserve topology GET capture",
            "preinit_perdevice_policy": "patch initialized flag, call send_audio_cal_v5, exit before libacdbloader init-tail",
            "success_discriminator": "future live success requires ret==0 and non-all-zero buffers, not requested out_len alone",
        },
        "sources": source,
        "vendor_libs": vendor,
        "build": build_state,
        "build_root": rel(args.build_root),
    }
    payload["ok"] = bool(source["required_ok"] and source["prohibited_ok"] and vendor["required_for_v2568_ok"] and build_state.get("ok", True))

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
