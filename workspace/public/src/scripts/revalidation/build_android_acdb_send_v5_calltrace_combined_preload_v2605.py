#!/usr/bin/env python3
"""Build V2605 ARM32 ACDB send_audio_cal_v5 calltrace combined preload.

Host-only unit after V2604. V2604 proved the V2603 composition was fixed but
`send_audio_cal_v5()` still timed out before any armed acdb_ioctl row. This
build keeps the V2603 combined preload and adds a metadata-only imported-call
tracer for calls made from the send_audio_cal_v5 address range.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_android_acdb_indirect_buffer_tap_v2600 as v2600
import build_android_acdb_perdevice_indirect_capture_v2572 as v2572
import build_android_acdb_perdevice_rx_capmask_argorder_v2591 as v2591
import build_android_acdb_v2600_perdevice_combined_preload_v2603 as v2603
import build_android_acdb_combined_preload_v2538 as preload_base

ROOT = v2572.ROOT
RUN_ID = "V2605"
BUILD_TAG = "v2605-acdb-send-v5-calltrace-combined-preload-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2605_AUDIO_ACDB_SEND_V5_CALLTRACE_COMBINED_PRELOAD_BUILD_2026-06-16.md"

CALLTRACE_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdb_send_v5_calltrace_v2605.c"
HELPER_ARTIFACT_NAME = "a90_acdb_perdevice_rx_capmask_argorder_exec_linked_v2605"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_send_v5_calltrace_combined_preload_v2605.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)


def rel(path: Path | str) -> str:
    return v2572.rel(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def source_state() -> dict[str, Any]:
    base = v2603.source_state()
    calltrace_path = ROOT / CALLTRACE_SOURCE_REL
    calltrace_text = _read(calltrace_path)
    combined_sources = "\n".join(
        _read(ROOT / source)
        for source in [v2600.ACDBTAP_SOURCE_REL, v2572.IOCTL_SOURCE_REL, v2572.PREINIT_SOURCE_REL, CALLTRACE_SOURCE_REL]
    )
    required = dict(base.get("required", {}))
    required.update(
        {
            "calltrace_source_exists": calltrace_path.exists(),
            "calltrace_exports_mutex_lock": "int pthread_mutex_lock(void *mutex)" in calltrace_text,
            "calltrace_exports_mutex_unlock": "int pthread_mutex_unlock(void *mutex)" in calltrace_text,
            "calltrace_exports_android_log_print": "int __android_log_print(" in calltrace_text,
            "calltrace_filters_send_v5_offsets": "A90_SEND_AUDIO_CAL_V5_RANGE_START" in calltrace_text and "a90_is_send_v5_offset" in calltrace_text,
            "calltrace_uses_send_symbol_base": "acdb_loader_send_audio_cal_v5" in calltrace_text and "A90_SEND_AUDIO_CAL_V5_OFF" in calltrace_text,
            "calltrace_logs_metadata_only": "caller_offset" in calltrace_text and "ret" in calltrace_text,
            "v2603_base_required_ok": base.get("required_ok"),
            "v2603_base_prohibited_ok": base.get("prohibited_ok"),
        }
    )
    prohibited = dict(base.get("prohibited", {}))
    prohibited.update(
        {
            "calltrace_opens_msm_audio_cal": "/dev/msm_audio_cal" in calltrace_text,
            "calltrace_calls_acdb_ioctl": "acdb_ioctl(" in calltrace_text,
            "calltrace_calls_audio_set": "AUDIO_SET_CALIBRATION" in calltrace_text or "0xc00461cb" in calltrace_text.lower(),
            "calltrace_speaker_write": any(token in calltrace_text for token in ("tinyplay", "tinymix", "AudioTrack")),
            "combined_persistent_magisk_install": "magisk --install-module" in combined_sources,
        }
    )
    return {
        "sources": [
            v2572.HELPER_SOURCE_REL,
            v2600.ACDBTAP_SOURCE_REL,
            v2572.IOCTL_SOURCE_REL,
            v2572.PREINIT_SOURCE_REL,
            CALLTRACE_SOURCE_REL,
        ],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
        "v2605_delta": {
            "reason": "V2604 reached before_send_audio_cal_v5 but no acdb_ioctl rows; trace imported calls before the first GET",
            "calltrace_event_path": "/data/local/tmp/a90-acdb-ownget/acdb-v2605-send-v5-calltrace-events.jsonl",
            "traced_hooks": ["pthread_mutex_lock", "pthread_mutex_unlock", "__android_log_print"],
            "offset_filter": "libacdbloader acdb_loader_send_audio_cal_v5 range 0x9d30..0xa100",
            "no_payload_dump": True,
        },
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    obj_dir = build_root / "obj"
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    obj_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    missing = [name for name in v2572.REQUIRED_NEEDED if not (v2572.VENDOR_LIB_DIR / name).exists()]
    if missing:
        return {"ok": False, "error": f"missing private ACDB closure libs: {', '.join(missing)}"}

    host_libraries = preload_base.prepare_host_libraries(build_root)
    env = preload_base.tool_env(host_libraries)

    helper_obj = obj_dir / "a90_acdb_init_drive_exec_linked_v2572_v2605.o"
    tap_obj = obj_dir / "libacdbtap_v2475_v2600.o"
    ioctl_obj = obj_dir / "a90_ioctl_trace_preload_v2531.o"
    preinit_obj = obj_dir / "libacdb_preinit_perdevice_v2572_rx_capmask_argorder.o"
    calltrace_obj = obj_dir / "libacdb_send_v5_calltrace_v2605.o"
    helper_out = bin_dir / HELPER_ARTIFACT_NAME
    preload_out = bin_dir / PRELOAD_ARTIFACT_NAME

    helper_compile = v2572.compile_object(ROOT / v2572.HELPER_SOURCE_REL, helper_obj, clang=clang, env=env, log_dir=log_dir, cflags=v2572.HELPER_CFLAGS)
    tap_compile = v2572.compile_object(ROOT / v2600.ACDBTAP_SOURCE_REL, tap_obj, clang=clang, env=env, log_dir=log_dir, cflags=v2600.COMMON_CFLAGS, extra=v2600.TAP_EXTRA_CFLAGS)
    ioctl_compile = v2572.compile_object(ROOT / v2572.IOCTL_SOURCE_REL, ioctl_obj, clang=clang, env=env, log_dir=log_dir, cflags=v2572.PRELOAD_CFLAGS)
    preinit_compile = v2572.compile_object(ROOT / v2572.PREINIT_SOURCE_REL, preinit_obj, clang=clang, env=env, log_dir=log_dir, cflags=v2572.PRELOAD_CFLAGS, extra=(v2591.CAP_MASK_CFLAG, v2591.ARG_ORDER_CFLAG))
    calltrace_compile = v2572.compile_object(ROOT / CALLTRACE_SOURCE_REL, calltrace_obj, clang=clang, env=env, log_dir=log_dir, cflags=v2572.PRELOAD_CFLAGS)

    if helper_compile["ok"]:
        helper_link = preload_base.run([str(lld), *v2572.HELPER_LDFLAGS, "-L", str(v2572.VENDOR_LIB_DIR), "-o", str(helper_out), str(helper_obj), *v2572.LINK_LIBS], env=env)
        (log_dir / "helper.link.stdout.txt").write_text(helper_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "helper.link.stderr.txt").write_text(helper_link["stderr"], encoding="utf-8", errors="replace")
        helper_link = {k: value for k, value in helper_link.items() if k not in {"stdout", "stderr"}}
        if helper_link["ok"] and helper_out.exists():
            helper_out.chmod(0o600)
    else:
        helper_link = {"ok": False, "skipped": True, "reason": "helper compile failed"}

    preload_compile_ok = all(item["ok"] for item in [tap_compile, ioctl_compile, preinit_compile, calltrace_compile])
    if preload_compile_ok:
        preload_link = preload_base.run([str(lld), *PRELOAD_LDFLAGS, "-o", str(preload_out), str(tap_obj), str(ioctl_obj), str(preinit_obj), str(calltrace_obj)], env=env)
        (log_dir / "preload.link.stdout.txt").write_text(preload_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "preload.link.stderr.txt").write_text(preload_link["stderr"], encoding="utf-8", errors="replace")
        preload_link = {k: value for k, value in preload_link.items() if k not in {"stdout", "stderr"}}
        if preload_link["ok"] and preload_out.exists():
            preload_out.chmod(0o600)
    else:
        preload_link = {"ok": False, "skipped": True, "reason": "preload compile failed"}

    helper_state = v2603.binary_state(helper_out, readelf=readelf, file_cmd=file_cmd, kind="helper")
    preload_state = v2603.binary_state(preload_out, readelf=readelf, file_cmd=file_cmd, kind="preload")
    sym = preload_state.get("symbols", {}).get("stdout", "")
    dyn = preload_state.get("dynamic", {}).get("stdout", "")
    checks = preload_state.setdefault("checks", {})
    checks.pop("soname_v2603", None)
    extra_checks = {
        "soname_v2605": f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in dyn,
        "exports_pthread_mutex_lock": " pthread_mutex_lock" in sym,
        "exports_pthread_mutex_unlock": " pthread_mutex_unlock" in sym,
        "exports_android_log_print": " __android_log_print" in sym,
        "does_not_export_audio_set_helper": "AUDIO_SET_CALIBRATION" not in sym,
    }
    checks.update(extra_checks)
    preload_state["ok"] = bool(preload_state.get("file", {}).get("ok") and all(checks.values()))

    return {
        "host_libraries": host_libraries,
        "compile": {
            "helper": helper_compile,
            "acdbtap_v2600": tap_compile,
            "ioctl_trace": ioctl_compile,
            "preinit_perdevice_rx_capmask_argorder": preinit_compile,
            "send_v5_calltrace": calltrace_compile,
        },
        "link": {"helper": helper_link, "preload": preload_link},
        "artifacts": {"helper": helper_state, "preload": preload_state},
        "ok": bool(helper_state.get("ok") and preload_state.get("ok")),
    }


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state()
    vendor = v2572.vendor_lib_state(args.readelf)
    if args.build:
        build_state = build(args.build_root, clang=args.clang, lld=args.lld, readelf=args.readelf, file_cmd=args.file)
    else:
        build_state = {"ok": True, "built": False, "reason": "pass --build to materialize private ARM32 artifacts"}
    artifacts = build_state.get("artifacts", {}) if isinstance(build_state, dict) else {}
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "host_only_build": True,
        "measurement_boundary": {
            "no_live_default": True,
            "no_native_replay": True,
            "no_speaker_write": True,
            "raw_payload_private_only": True,
            "fake_audio_cal_env": "A90_ACDB_FAKE_ALLOCATE=1",
            "no_real_audio_set": "ioctl preload fake-successes AUDIO_SET_CALIBRATION in fake mode",
        },
        "capture_contract": {
            "base": "V2603 combined preload",
            "new_trace": "metadata-only imported-call trace for send_audio_cal_v5 pre-GET localization",
            "traced_hooks": source["v2605_delta"]["traced_hooks"],
            "event_path": source["v2605_delta"]["calltrace_event_path"],
            "per_device_call": "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
            "success_discriminator": "future live ACDB captures still require ret==0 plus non-all-zero buffers",
        },
        "sources": source,
        "vendor_libs": vendor,
        "build": build_state,
        "build_root": rel(args.build_root),
    }
    payload["ok"] = bool(
        source.get("required_ok")
        and source.get("prohibited_ok")
        and vendor.get("required_for_v2572_ok")
        and (not args.build or (artifacts.get("helper", {}).get("ok") and artifacts.get("preload", {}).get("ok")))
    )
    return payload


def write_report(payload: dict[str, Any], report_path: Path) -> None:
    helper = payload.get("build", {}).get("artifacts", {}).get("helper", {})
    preload = payload.get("build", {}).get("artifacts", {}).get("preload", {})
    build = payload.get("build", {})
    calltrace_compile = build.get("compile", {}).get("send_v5_calltrace", {}) if isinstance(build, dict) else {}
    lines = [
        "# NATIVE_INIT V2605 — ACDB send_audio_cal_v5 calltrace combined preload build",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only build-only unit after V2604. No Android handoff, device flash, native replay SET,",
        "speaker write, ACDB command execution, or raw ACDB payload publication was performed.",
        "",
        "## Decision",
        "",
        f"- decision: `{BUILD_TAG}`",
        f"- ok: `{payload.get('ok')}`",
        f"- build_root: `{payload.get('build_root')}`",
        f"- helper: `{helper.get('path')}`",
        f"- helper_sha256: `{helper.get('sha256')}`",
        f"- preload: `{preload.get('path')}`",
        f"- preload_sha256: `{preload.get('sha256')}`",
        "",
        "## Why This Unit",
        "",
        "V2604 proved the V2603 combined preload arms capture and reaches `before_send_audio_cal_v5`,",
        "but the helper then times out before the first armed `acdb_ioctl` row. Another unchanged live",
        "run would be low-information. V2605 adds import-call telemetry around the pre-first-GET region",
        "so the next live run can classify whether the stop is at the initial mutex, at an Android log",
        "call boundary after local setup, or deeper in an internal helper before the dispatcher GET.",
        "",
        "## Contract",
        "",
        "- base artifact: V2603 combined preload behavior is preserved.",
        "- new hooks: `pthread_mutex_lock`, `pthread_mutex_unlock`, and `__android_log_print`.",
        "- filter: only caller offsets in `acdb_loader_send_audio_cal_v5` range `0x9d30..0xa100` are logged.",
        "- logged data: hook name, enter/return phase, pid/tid, caller address, caller offset, first argument pointer, and return code.",
        "- no payload data, ACDB request buffers, speaker writes, or real `AUDIO_SET_CALIBRATION` are introduced.",
        "- future live success remains `ret==0` plus non-all-zero ACDB buffers; this unit only localizes pre-GET control flow.",
        "",
        "## Build Evidence",
        "",
        f"- calltrace_compile_ok: `{calltrace_compile.get('ok')}`",
        f"- calltrace_command_contains_source: `{str(payload.get('sources', {}).get('v2605_delta', {}).get('traced_hooks', []))}`",
        f"- helper_checks: `{helper.get('checks')}`",
        f"- preload_checks: `{preload.get('checks')}`",
        "",
        "## Next Unit",
        "",
        "Use the existing V2592 Android-good handoff with the V2605 preload override. The analysis should",
        "read both `acdb-v2605-send-v5-calltrace-events.jsonl` and the existing `acdbtap` events. If",
        "`pthread_mutex_lock enter` appears with no return, the stop is the initial mutex. If mutex returns",
        "and Android-log call offsets advance but no `0x1122e` row appears, the stop is inside the local",
        "pre-dispatch helper region. Do not proceed to native replay until operator-verified per-device bytes exist.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_send_v5_calltrace_combined_preload_v2605.py tests/test_build_android_acdb_send_v5_calltrace_combined_preload_v2605.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_send_v5_calltrace_combined_preload_v2605 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_send_v5_calltrace_combined_preload_v2605.py --build --write-report`",
        "- `git diff --check`",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--clang", type=Path, default=v2572.TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=v2572.TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = make_payload(args)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_report:
        write_report(payload, args.report)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
