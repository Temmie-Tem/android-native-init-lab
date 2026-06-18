#!/usr/bin/env python3
"""Build V2668 init-time direct-real-common custom-topology ACDB SET capture artifacts.

Host-only build unit. V2667 proved the init-time common hook is the right
control point, but the V2666 RTLD_NEXT resolver reentered the interposed common
export and emitted no SET rows. V2668 keeps the init-time call site but invokes
libacdbloader's real implementation by base+0x8cf0|1 instead of by symbol
lookup.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

import analyze_audio_acdb_custom_topology_common_path_v2663 as v2663
import build_android_acdb_custom_topology_phase_common_setcal_capture_v2659 as v2659

ROOT = v2659.ROOT
RUN_ID = "V2668"
BUILD_TAG = "v2668-acdb-direct-real-common-setcal-capture-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2668_AUDIO_ACDB_DIRECT_REAL_COMMON_SETCAL_CAPTURE_BUILD_2026-06-18.md"

HELPER_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_common_only_exec_linked_v2664.c"
PREINIT_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdb_phase_common_direct_v2668.c"
HELPER_ARTIFACT_NAME = "a90_acdb_direct_real_common_setcal_capture_exec_linked_v2668"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_direct_real_common_setcal_capture_combined_preload_v2668.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)
TARGET_CAL_TYPES = [10, 14, 24]


def rel(path: Path | str) -> str:
    return v2659.rel(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


@contextlib.contextmanager
def patched_v2659_constants() -> Iterator[None]:
    old = {
        "helper_source": v2659.HELPER_SOURCE_REL,
        "helper_artifact": v2659.HELPER_ARTIFACT_NAME,
        "preload_artifact": v2659.PRELOAD_ARTIFACT_NAME,
        "preload_ldflags": v2659.PRELOAD_LDFLAGS,
        "preinit_source": v2659.PREINIT_SOURCE_REL,
    }
    v2659.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2659.PREINIT_SOURCE_REL = PREINIT_SOURCE_REL
    v2659.HELPER_ARTIFACT_NAME = HELPER_ARTIFACT_NAME
    v2659.PRELOAD_ARTIFACT_NAME = PRELOAD_ARTIFACT_NAME
    v2659.PRELOAD_LDFLAGS = PRELOAD_LDFLAGS
    try:
        yield
    finally:
        v2659.HELPER_SOURCE_REL = old["helper_source"]
        v2659.PREINIT_SOURCE_REL = old["preinit_source"]
        v2659.HELPER_ARTIFACT_NAME = old["helper_artifact"]
        v2659.PRELOAD_ARTIFACT_NAME = old["preload_artifact"]
        v2659.PRELOAD_LDFLAGS = old["preload_ldflags"]


def common_path_state(args: argparse.Namespace) -> dict[str, Any]:
    try:
        analysis, _ = v2663.analyze(args.lib, args.objdump)
        paths = [p for p in analysis.cal_paths if p.cal_type in TARGET_CAL_TYPES]
        return {
            "ok": bool(analysis.ok and analysis.target_custom_cals_complete),
            "decision": analysis.decision,
            "lib_sha256": analysis.lib_sha256,
            "target_paths": [p.__dict__ for p in paths],
        }
    except Exception as error:  # pragma: no cover - surfaced in payload/report
        return {"ok": False, "error": str(error)}


def source_state(args: argparse.Namespace) -> dict[str, Any]:
    helper_path = ROOT / HELPER_SOURCE_REL
    preinit_path = ROOT / PREINIT_SOURCE_REL
    ioctl_path = ROOT / v2659.v2630.IOCTL_SOURCE_REL
    acdbtap_path = ROOT / v2659.v2630.ACDBTAP_SOURCE_REL
    helper = _read(helper_path)
    preinit = _read(preinit_path)
    ioctl = _read(ioctl_path)
    acdbtap = _read(acdbtap_path)
    combined = "\n".join([helper, preinit, ioctl, acdbtap])

    init_pos = helper.find("init_ret = acdb_loader_init_v3")
    arm_pos = helper.find("a90_arm_capture()")
    common_pos = helper.find("topology_ret = acdb_loader_send_common_custom_topology()")
    send_call_pos = helper.find("acdb_loader_send_audio_cal_v5(")
    common_state = common_path_state(args)

    required = {
        "helper_source_exists": helper_path.exists(),
        "phase_common_source_exists": preinit_path.exists(),
        "setcal_ioctl_source_exists": ioctl_path.exists(),
        "acdbtap_source_exists": acdbtap_path.exists(),
        "v2663_common_path_targets_ok": bool(common_state.get("ok")),
        "helper_imports_init_v3": "extern int32_t acdb_loader_init_v3" in helper,
        "helper_imports_common_topology": "extern int32_t acdb_loader_send_common_custom_topology(void);" in helper,
        "helper_does_not_import_send_audio_cal_v5": "extern int32_t acdb_loader_send_audio_cal_v5" not in helper,
        "helper_calls_init_v3_open_audconf": 'A90_ACDB_FILES_PATH "/vendor/etc/audconf/OPEN"' in helper,
        "helper_arms_after_init": init_pos >= 0 and arm_pos > init_pos,
        "helper_postinit_common_is_unreached_fallback": common_pos > arm_pos,
        "helper_skips_send_audio_cal_v5": send_call_pos < 0,
        "helper_logs_common_return": "send_common_custom_topology_return" in helper,
        "helper_exits_zero_after_common": "Non-zero common return is still useful" in helper and "a90_exit(0);" in helper,
        "phase_hook_init_real_event_path_v2668": "acdb-v2668-direct-real-common-events.jsonl" in preinit,
        "phase_hook_init_common_enter": "init_common_enter" in preinit,
        "phase_hook_calls_real_common_during_init": "init_before_real_common" in preinit and "init_real_common_return" in preinit,
        "phase_hook_exits_after_init_real": "init_exit_after_real_common" in preinit and "a90_exit_group(0)" in preinit,
        "phase_hook_fails_closed_on_patch_failure": "init_patch_failed_exit" in preinit and "a90_exit_group(40)" in preinit,
        "phase_hook_neutralizes_reentry": "common_reentry_neutralized" in preinit and "return 0;" in preinit,
        "phase_hook_patches_init_flag": "A90_LOADER_INIT_FLAG_OFF" in preinit and "*flag = 1U" in preinit,
        "phase_hook_direct_common_offset": "A90_LOADER_SEND_COMMON_TOPOLOGY_OFF 0x00008cf0UL" in preinit,
        "phase_hook_direct_common_address_event": "direct_real_common_addr" in preinit,
        "phase_hook_avoids_rtld_next_common_lookup": 'dlsym(A90_RTLD_NEXT, "acdb_loader_send_common_custom_topology")' not in preinit,
        "ioctl_always_fakes_audio_set": (
            "always fake AUDIO_SET_CALIBRATION" in ioctl
            and "if (request == A90_AUDIO_SET_CALIBRATION)\n        return 1;" in ioctl
            and "fake-set-always" in ioctl
        ),
        "ioctl_dumps_arg_and_dmabuf": (
            "Dump exactly arg[0:data_size]" in ioctl
            and "mmap(0, header.cal_size, A90_PROT_READ, A90_MAP_SHARED" in ioctl
            and "arg_sha" in ioctl
            and "dmabuf_sha" in ioctl
        ),
    }
    prohibited = {
        "helper_opens_msm_audio_cal": "/dev/msm_audio_cal" in helper,
        "helper_issues_ioctl": "ioctl(" in helper or "A90_NR_IOCTL" in helper,
        "helper_calls_send_audio_cal_v5": "acdb_loader_send_audio_cal_v5" in helper,
        "ioctl_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in ioctl or "open('/dev/msm_audio_cal" in ioctl,
        "combined_native_speaker_write": any(token in combined for token in ("tinyplay", "tinymix", "AudioTrack")),
        "combined_persistent_magisk_install": "magisk --install-module" in combined,
        "combined_global_pthread_hooks": "pthread_mutex_lock" in combined or "pthread_mutex_unlock" in combined,
        "combined_android_log_hook": "__android_log_print" in combined,
    }
    return {
        "sources": [HELPER_SOURCE_REL, PREINIT_SOURCE_REL, v2659.v2630.ACDBTAP_SOURCE_REL, v2659.v2630.IOCTL_SOURCE_REL],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
        "common_path_state": common_state,
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    with patched_v2659_constants():
        build_state = v2659.build(build_root, clang=clang, lld=lld, readelf=readelf, file_cmd=file_cmd)
    artifacts = build_state.get("artifacts", {}) if isinstance(build_state, dict) else {}
    helper = artifacts.get("helper", {}) if isinstance(artifacts, dict) else {}
    preload = artifacts.get("preload", {}) if isinstance(artifacts, dict) else {}
    helper_symbols = helper.get("symbols", {}).get("stdout", "") if isinstance(helper, dict) else ""
    preload_symbols = preload.get("symbols", {}).get("stdout", "") if isinstance(preload, dict) else ""

    if isinstance(helper, dict):
        checks = helper.setdefault("checks", {})
        if isinstance(checks, dict):
            checks.pop("undefined_send_audio_cal_v5", None)
            checks["undefined_common_topology"] = " UND acdb_loader_send_common_custom_topology" in helper_symbols
            checks["no_undefined_send_audio_cal_v5"] = " UND acdb_loader_send_audio_cal_v5" not in helper_symbols
            checks["undefined_arm_capture"] = " UND a90_arm_capture" in helper_symbols
            checks["needed_libacdbloader"] = "Shared library: [libacdbloader.so]" in helper.get("dynamic", {}).get("stdout", "")
            helper["ok"] = bool(
                helper.get("exists")
                and checks["undefined_common_topology"]
                and checks["no_undefined_send_audio_cal_v5"]
                and checks["undefined_arm_capture"]
                and checks["needed_libacdbloader"]
            )
    if isinstance(preload, dict):
        checks = preload.setdefault("checks", {})
        if isinstance(checks, dict):
            if "soname_v2659" in checks:
                checks["soname_v2668"] = checks.pop("soname_v2659")
            checks["exports_phase_common_hook"] = " acdb_loader_send_common_custom_topology" in preload_symbols
            checks["exports_acdb_ioctl"] = " acdb_ioctl" in preload_symbols
            checks["exports_ioctl"] = " ioctl" in preload_symbols
            checks["exports_a90_arm_capture"] = " a90_arm_capture" in preload_symbols
            preload["ok"] = bool(preload.get("exists") and all(checks.values()))
    build_state["ok"] = bool(helper.get("ok") and preload.get("ok"))
    return build_state


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state(args)
    vendor = v2659.v2630.v2613.v2611.v2608.v2572.vendor_lib_state(args.readelf)
    if args.build:
        build_state = build(args.build_root, clang=args.clang, lld=args.lld, readelf=args.readelf, file_cmd=args.file)
    else:
        build_state = {"ok": True, "built": False, "reason": "pass --build to materialize private ARM32 artifacts"}
    artifacts = build_state.get("artifacts", {}) if isinstance(build_state, dict) else {}
    helper = artifacts.get("helper", {}) if isinstance(artifacts, dict) else {}
    preload = artifacts.get("preload", {}) if isinstance(artifacts, dict) else {}
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
            "no_real_audio_set": "V2630 ioctl shim fake-successes every AUDIO_SET_CALIBRATION after dumping arg/payload data",
        },
        "capture_contract": {
            "call_order": "acdb_loader_init_v3 -> init-time common hook -> patch initialized flag -> real common topology -> exit_group(0)",
            "target_cal_types": TARGET_CAL_TYPES,
            "removed_from_v2659": "send_audio_cal_v5 is intentionally not imported or called",
            "v2667_delta": "real common is called by libacdbloader base+0x8cf0|1 to avoid RTLD_NEXT resolving back to the interposed export",
            "success_discriminator": "future live run must capture byte-exact SET records for cal_types 10/14/24 before process exit; init_v3 return is no longer required",
            "phase_common_policy": "init call patches initialized flag, invokes real common once, exits 0; nested real-common entries return 0",
            "set_capture": "AUDIO_SET_CALIBRATION arg[0:data_size] plus same-process dma-buf when cal_size>0",
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
        and (not args.build or (helper.get("ok") and preload.get("ok")))
    )
    return payload


def write_report(payload: dict[str, Any], report_path: Path) -> None:
    helper = payload.get("build", {}).get("artifacts", {}).get("helper", {})
    preload = payload.get("build", {}).get("artifacts", {}).get("preload", {})
    build_state = payload.get("build", {})
    lines = [
        "# NATIVE_INIT V2668 — ACDB init-time direct-real-common SET capture build",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only build-only unit. No Android handoff, device flash, native replay, real",
        "`AUDIO_SET_CALIBRATION`, mixer write, PCM write, or speaker playback occurred.",
        "Raw ACDB bytes remain private-only.",
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
        "V2667 proved the init-time common hook is the right control point, but",
        "the V2666 `RTLD_NEXT` resolver still reentered the interposed common",
        "export: `common_reentry_neutralized` appeared and no SET rows were emitted.",
        "V2668 therefore keeps the init-time hook but calls the stock implementation",
        "by direct `libacdbloader.so` text offset `base+0x8cf0|1`, derived from",
        "`acdb_loader_is_initialized`, avoiding symbol interposition for this call.",
        "",
        "## Capture Contract",
        "",
        "- helper remains common-only and does not import or call `send_audio_cal_v5`.",
        "- first/init common hook patches `acdb_loader_is_initialized` state.",
        "- the same init-time hook calls the real `acdb_loader_send_common_custom_topology()` once by direct text address.",
        "- direct-call metadata logs `direct_loader_base` and `direct_real_common_addr`.",
        "- nested real-common reentry logs `common_reentry_neutralized` and returns `0`.",
        "- V2630 SET shim preserves exact `AUDIO_SET_CALIBRATION` arg bytes and same-process dma-buf payloads before fake success.",
        "- future live success is byte-exact SET records for cal_types `10`, `14`, and `24`.",
        "- the hook exits the process with `exit_group(0)` after real-common returns, because dumped SET rows are the evidence and `init_v3` return is not required.",
        "",
        "## Boundary",
        "",
        "- no direct `/dev/msm_audio_cal` open by the helper or shim",
        "- no real `AUDIO_SET_CALIBRATION` pass-through",
        "- no `send_audio_cal_v5`, native ACDB replay, route mixer write, PCM write, AudioTrack, or speaker playback",
        "- no persistent Magisk install and no raw ACDB bytes in public paths",
        "",
        "## Build Evidence",
        "",
        f"- source_required_ok: `{payload.get('sources', {}).get('required_ok')}`",
        f"- source_prohibited_ok: `{payload.get('sources', {}).get('prohibited_ok')}`",
        f"- v2663_common_path_ok: `{payload.get('sources', {}).get('common_path_state', {}).get('ok')}`",
        f"- helper_compile_ok: `{build_state.get('compile', {}).get('helper', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- tap_compile_ok: `{build_state.get('compile', {}).get('acdbtap_v2600', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- ioctl_compile_ok: `{build_state.get('compile', {}).get('ioctl_trace', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- phase_common_compile_ok: `{build_state.get('compile', {}).get('preinit_no_send', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- helper_checks: `{helper.get('checks')}`",
        f"- preload_checks: `{preload.get('checks')}`",
        "",
        "## Next Unit",
        "",
        "A V2669 live Android-good handoff can stage the V2668 helper/preload, run with",
        "`A90_ACDB_FAKE_ALLOCATE=1`, pull `acdb-common-only-events.jsonl`,",
        "`acdb-v2668-direct-real-common-events.jsonl`, `setcal-events.jsonl`, and private",
        "`setcal-*` raw files, then rollback to V2321. It should stop after capture and",
        "report ordered metadata for cal_types `10`, `14`, and `24`.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_common_direct_real_setcal_capture_v2668.py tests/test_build_android_acdb_common_direct_real_setcal_capture_v2668.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_common_direct_real_setcal_capture_v2668 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_common_direct_real_setcal_capture_v2668.py --build --write-report`",
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
    parser.add_argument("--clang", type=Path, default=v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    parser.add_argument("--lib", type=Path, default=v2663.DEFAULT_LIB)
    parser.add_argument("--objdump", type=Path, default=v2663.DEFAULT_OBJDUMP)
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
