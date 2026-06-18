#!/usr/bin/env python3
"""Build V2659 phase-aware custom-topology ACDB SET capture artifacts.

This host-only build wrapper keeps the V2553 full-manifest own-process helper
and V2630 fake-success AUDIO_SET_CALIBRATION capture shim, but replaces the
V2608/V2656 common-topology hook with a phase-aware hook:

* the init-time common-topology call is short-circuited and only patches the
  initialized flag so acdb_loader_init_v3 can return;
* the helper's post-init common-topology call invokes the real loader path;
* nested/reentrant common-topology calls during that real path are neutralized
  with return 0 instead of the old -92 sentinel.

No Android handoff, device flash, native replay, real audio SET, mixer, PCM, or
speaker write happens in this build unit.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

import build_android_acdb_setcal_capture_v2630 as v2630

ROOT = v2630.ROOT
RUN_ID = "V2659"
BUILD_TAG = "v2659-acdb-custom-topology-phase-common-setcal-capture-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2659_AUDIO_ACDB_CUSTOM_TOPOLOGY_PHASE_COMMON_SETCAL_CAPTURE_BUILD_2026-06-18.md"

HELPER_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_full_manifest_exec_linked_v2553.c"
PREINIT_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdb_phase_common_v2659.c"
HELPER_ARTIFACT_NAME = "a90_acdb_custom_topology_phase_common_setcal_capture_exec_linked_v2659"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_custom_topology_phase_common_setcal_capture_combined_preload_v2659.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)


def rel(path: Path | str) -> str:
    return v2630.rel(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


@contextlib.contextmanager
def patched_v2630_constants() -> Iterator[None]:
    v2613 = v2630.v2613
    v2608 = v2613.v2611.v2608
    old = {
        "v2630_helper_source": v2630.HELPER_SOURCE_REL,
        "v2630_preinit_source": v2630.PREINIT_SOURCE_REL,
        "v2630_helper_artifact": v2630.HELPER_ARTIFACT_NAME,
        "v2630_preload_artifact": v2630.PRELOAD_ARTIFACT_NAME,
        "v2630_preload_ldflags": v2630.PRELOAD_LDFLAGS,
        "v2613_helper_source": v2613.HELPER_SOURCE_REL,
        "v2613_preinit_source": v2613.PREINIT_SOURCE_REL,
        "v2608_helper_source": v2608.HELPER_SOURCE_REL,
        "v2608_preinit_source": v2608.PREINIT_SOURCE_REL,
    }
    v2630.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2630.PREINIT_SOURCE_REL = PREINIT_SOURCE_REL
    v2630.HELPER_ARTIFACT_NAME = HELPER_ARTIFACT_NAME
    v2630.PRELOAD_ARTIFACT_NAME = PRELOAD_ARTIFACT_NAME
    v2630.PRELOAD_LDFLAGS = PRELOAD_LDFLAGS
    v2613.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2613.PREINIT_SOURCE_REL = PREINIT_SOURCE_REL
    v2608.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2608.PREINIT_SOURCE_REL = PREINIT_SOURCE_REL
    try:
        yield
    finally:
        v2630.HELPER_SOURCE_REL = old["v2630_helper_source"]
        v2630.PREINIT_SOURCE_REL = old["v2630_preinit_source"]
        v2630.HELPER_ARTIFACT_NAME = old["v2630_helper_artifact"]
        v2630.PRELOAD_ARTIFACT_NAME = old["v2630_preload_artifact"]
        v2630.PRELOAD_LDFLAGS = old["v2630_preload_ldflags"]
        v2613.HELPER_SOURCE_REL = old["v2613_helper_source"]
        v2613.PREINIT_SOURCE_REL = old["v2613_preinit_source"]
        v2608.HELPER_SOURCE_REL = old["v2608_helper_source"]
        v2608.PREINIT_SOURCE_REL = old["v2608_preinit_source"]


def source_state() -> dict[str, Any]:
    helper_path = ROOT / HELPER_SOURCE_REL
    preinit_path = ROOT / PREINIT_SOURCE_REL
    acdbtap_path = ROOT / v2630.ACDBTAP_SOURCE_REL
    ioctl_path = ROOT / v2630.IOCTL_SOURCE_REL
    helper = _read(helper_path)
    preinit = _read(preinit_path)
    acdbtap = _read(acdbtap_path)
    ioctl = _read(ioctl_path)
    combined = "\n".join([helper, preinit, acdbtap, ioctl])

    init_pos = helper.find("init_ret = acdb_loader_init_v3")
    arm_pos = helper.find("a90_arm_capture()")
    common_pos = helper.find("topology_ret = acdb_loader_send_common_custom_topology()")
    send_pos = helper.find("audio_cal_ret = acdb_loader_send_audio_cal_v5")
    preinit_init_pos = preinit.find("init_common_return_success")
    preinit_real_pos = preinit.find("postinit_real_common_return")
    preinit_reentry_pos = preinit.find("common_reentry_neutralized")

    required = {
        "helper_source_exists": helper_path.exists(),
        "phase_common_source_exists": preinit_path.exists(),
        "acdbtap_source_exists": acdbtap_path.exists(),
        "ioctl_source_exists": ioctl_path.exists(),
        "helper_imports_common_topology": "extern int32_t acdb_loader_send_common_custom_topology(void);" in helper,
        "helper_imports_send_audio_cal_v5": "extern int32_t acdb_loader_send_audio_cal_v5" in helper,
        "helper_calls_init_v3_open_audconf": 'A90_ACDB_FILES_PATH "/vendor/etc/audconf/OPEN"' in helper,
        "helper_arms_after_init": init_pos >= 0 and arm_pos > init_pos,
        "helper_calls_common_topology_before_send_v5": common_pos > arm_pos and send_pos > common_pos,
        "helper_records_common_topology_return": "send_common_custom_topology_return" in helper,
        "helper_records_send_v5_return": "send_audio_cal_v5_return" in helper,
        "phase_hook_exports_common_topology": "acdb_loader_send_common_custom_topology(void)" in preinit,
        "phase_hook_init_short_success": preinit_init_pos >= 0,
        "phase_hook_calls_real_common_postinit": "a90_real_common_topology()" in preinit and preinit_real_pos > preinit_init_pos,
        "phase_hook_neutralizes_real_common_reentry": preinit_reentry_pos >= 0 and "return 0;" in preinit[preinit_reentry_pos:preinit_reentry_pos + 220],
        "phase_hook_keeps_unexpected_reentry_sentinel": "common_reentry_unexpected" in preinit and "return -92;" in preinit,
        "phase_hook_patches_init_flag": "A90_LOADER_INIT_FLAG_OFF" in preinit and "*flag = 1U" in preinit,
        "phase_hook_event_path_v2659": "acdb-v2659-phase-common-events.jsonl" in preinit,
        "phase_hook_no_compile_flag_dependency": "A90_V2608_CALL_REAL_COMMON_TOPOLOGY" not in preinit,
        "ioctl_setcal_events_path": "A90_SETCAL_EVENTS_PATH" in ioctl and "setcal-events.jsonl" in ioctl,
        "ioctl_always_fakes_audio_set": (
            "always fake AUDIO_SET_CALIBRATION" in ioctl
            and "if (request == A90_AUDIO_SET_CALIBRATION)\n        return 1;" in ioctl
            and "fake-set-always" in ioctl
        ),
        "ioctl_dumps_arg_data_size": (
            "Dump exactly arg[0:data_size]" in ioctl
            and "header.data_size" in ioctl
            and "A90_MAX_SET_ARG_BYTES" in ioctl
        ),
        "ioctl_dumps_same_process_dmabuf": (
            "mmap(0, header.cal_size, A90_PROT_READ, A90_MAP_SHARED" in ioctl
            and "munmap(mapping, header.cal_size)" in ioctl
            and "A90_MAX_DMABUF_BYTES" in ioctl
        ),
        "ioctl_header_only_ok": "dmabuf_status = \"header-only\"" in ioctl,
        "ioctl_hashes_arg_and_dmabuf": "arg_sha" in ioctl and "dmabuf_sha" in ioctl,
    }
    prohibited = {
        "helper_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in helper or "open('/dev/msm_audio_cal" in helper,
        "ioctl_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in ioctl or "open('/dev/msm_audio_cal" in ioctl,
        "phase_hook_uses_old_real_common_flag": "A90_V2608_CALL_REAL_COMMON_TOPOLOGY" in preinit,
        "phase_hook_exits_process": "exit_group" in preinit or "A90_NR_EXIT_GROUP" in preinit,
        "combined_native_speaker_write": any(token in combined for token in ("tinyplay", "tinymix", "AudioTrack")),
        "combined_persistent_magisk_install": "magisk --install-module" in combined,
        "combined_global_pthread_hooks": "pthread_mutex_lock" in combined or "pthread_mutex_unlock" in combined,
        "combined_android_log_hook": "__android_log_print" in combined,
    }
    return {
        "sources": [HELPER_SOURCE_REL, PREINIT_SOURCE_REL, v2630.ACDBTAP_SOURCE_REL, v2630.IOCTL_SOURCE_REL],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
        "v2659_delta": {
            "basis": "V2657 returned -92 from the real-common path; V2658 identified that as the hook reentry sentinel, not payload progress.",
            "phase_policy": "init-time common call short-circuits and patches initialized; post-init helper call invokes real common; nested real-common entries return 0.",
            "helper": "V2553 full-manifest helper still drives common topology before send_audio_cal_v5.",
            "preload": "V2630 fake SET capture preload still dumps exact arg bytes and same-process dma-buf, then fake-successes AUDIO_SET_CALIBRATION.",
            "acceptance": "future live capture must show init_common_return_success, postinit_real_common_return, and byte-exact SET records for cal_types 10, 14, and 24.",
        },
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    with patched_v2630_constants():
        build_state = v2630.build(build_root, clang=clang, lld=lld, readelf=readelf, file_cmd=file_cmd)
    artifacts = build_state.get("artifacts", {}) if isinstance(build_state, dict) else {}
    helper = artifacts.get("helper", {}) if isinstance(artifacts, dict) else {}
    preload = artifacts.get("preload", {}) if isinstance(artifacts, dict) else {}
    helper_symbols = helper.get("symbols", {}).get("stdout", "") if isinstance(helper, dict) else ""
    preload_symbols = preload.get("symbols", {}).get("stdout", "") if isinstance(preload, dict) else ""
    preload_checks = preload.get("checks", {}) if isinstance(preload, dict) else {}
    if isinstance(preload_checks, dict) and "soname_v2630" in preload_checks:
        preload_checks["soname_v2659"] = preload_checks.pop("soname_v2630")
        preload_checks["exports_phase_common_hook"] = " acdb_loader_send_common_custom_topology" in preload_symbols
        preload_checks["exports_acdb_ioctl"] = " acdb_ioctl" in preload_symbols
        preload_checks["exports_ioctl"] = " ioctl" in preload_symbols
        preload_checks["exports_a90_arm_capture"] = " a90_arm_capture" in preload_symbols
        preload["ok"] = bool(preload.get("ok") and all(preload_checks.values()))
    compile_state = build_state.get("compile", {}) if isinstance(build_state, dict) else {}
    preinit_compile = compile_state.get("preinit_no_send", {}) if isinstance(compile_state, dict) else {}
    if isinstance(preinit_compile, dict):
        preinit_compile["phase_common_hook_enabled"] = True
        preinit_compile["source_rel"] = PREINIT_SOURCE_REL
    if isinstance(helper, dict):
        checks = helper.setdefault("checks", {})
        if isinstance(checks, dict):
            checks["undefined_common_topology"] = " UND acdb_loader_send_common_custom_topology" in helper_symbols
            checks["undefined_send_audio_cal_v5"] = " UND acdb_loader_send_audio_cal_v5" in helper_symbols
            helper["ok"] = bool(helper.get("ok") and checks["undefined_common_topology"] and checks["undefined_send_audio_cal_v5"])
    return build_state


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state()
    vendor = v2630.v2613.v2611.v2608.v2572.vendor_lib_state(args.readelf)
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
            "call_order": "acdb_loader_init_v3 -> init-short common hook -> a90_arm_capture -> post-init real common topology -> send_audio_cal_v5",
            "target_cal_types": [10, 14, 24],
            "supplemental_cal_types": [20, 39],
            "success_discriminator": "future live run must capture byte-exact SET records for 10/14/24; common_reentry_neutralized proves the old -92 sentinel was bypassed",
            "phase_common_policy": "init call returns 0 after initialized-flag patch; post-init call invokes real common; nested real-common entries return 0",
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
        "# NATIVE_INIT V2659 — ACDB phase-aware common-topology SET capture build",
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
        f"- `decision`: `{BUILD_TAG}`",
        f"- `ok`: `{payload.get('ok')}`",
        f"- `build_root`: `{payload.get('build_root')}`",
        f"- helper: `{helper.get('path')}`",
        f"- helper_sha256: `{helper.get('sha256')}`",
        f"- preload: `{preload.get('path')}`",
        f"- preload_sha256: `{preload.get('sha256')}`",
        "",
        "## Why This Unit",
        "",
        "V2657 returned `-92` from the attempted real common-topology path. V2658 traced",
        "that value to the old common-hook reentry sentinel, not to useful topology SET",
        "progress. V2659 therefore changes only the common-topology hook phase behavior:",
        "short-circuit the init-time call, call the real common path post-init, and",
        "neutralize nested real-common reentry with `0` instead of `-92`.",
        "",
        "## Capture Contract",
        "",
        "- helper call order remains `init_v3 -> arm -> common_topology -> send_audio_cal_v5`.",
        "- first/init common hook patches `acdb_loader_is_initialized` state and returns `0`.",
        "- post-init common hook calls the real `acdb_loader_send_common_custom_topology()` once.",
        "- nested real-common reentry logs `common_reentry_neutralized` and returns `0`.",
        "- V2630 SET shim preserves exact `AUDIO_SET_CALIBRATION` arg bytes and same-process dma-buf payloads before fake success.",
        "- future live success is byte-exact SET records for cal_types `10`, `14`, and `24`.",
        "",
        "## Boundary",
        "",
        "- no direct `/dev/msm_audio_cal` open by the helper or shim",
        "- no real `AUDIO_SET_CALIBRATION` pass-through",
        "- no native ACDB replay, route mixer write, PCM write, AudioTrack, or speaker playback",
        "- no persistent Magisk install and no raw ACDB bytes in public paths",
        "",
        "## Build Evidence",
        "",
        f"- source_required_ok: `{payload.get('sources', {}).get('required_ok')}`",
        f"- source_prohibited_ok: `{payload.get('sources', {}).get('prohibited_ok')}`",
        f"- helper_compile_ok: `{build_state.get('compile', {}).get('helper', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- tap_compile_ok: `{build_state.get('compile', {}).get('acdbtap_v2600', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- ioctl_compile_ok: `{build_state.get('compile', {}).get('ioctl_trace', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- phase_common_compile_ok: `{build_state.get('compile', {}).get('preinit_no_send', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- helper_checks: `{helper.get('checks')}`",
        f"- preload_checks: `{preload.get('checks')}`",
        "",
        "## Next Unit",
        "",
        "A live Android-good handoff can stage the V2659 helper/preload, run with",
        "`A90_ACDB_FAKE_ALLOCATE=1`, pull `acdb-v2659-phase-common-events.jsonl`,",
        "`setcal-events.jsonl`, and private `setcal-*` raw files, then rollback to V2321.",
        "The live unit must stop after capture and wait for operator Gate-2 mapping.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_custom_topology_phase_common_setcal_capture_v2659.py tests/test_build_android_acdb_custom_topology_phase_common_setcal_capture_v2659.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests/test_build_android_acdb_custom_topology_phase_common_setcal_capture_v2659.py -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_custom_topology_phase_common_setcal_capture_v2659.py --build --write-report`",
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
    parser.add_argument("--clang", type=Path, default=v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld")
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
