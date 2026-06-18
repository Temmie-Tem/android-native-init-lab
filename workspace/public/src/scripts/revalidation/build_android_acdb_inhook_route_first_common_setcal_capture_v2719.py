#!/usr/bin/env python3
"""Build V2719 in-hook route-first common-topology ACDB SET capture artifacts.

V2718 repeated the known init-tail failure: after the init-time common-topology
short-circuit, acdb_loader_init_v3 progressed far enough to allocate cal_types
10/14/24 but SIGSEGVed before the helper regained control and could run the
route-first public calls. V2719 combines the useful pieces that are still on the
frontier:

* V2674's in-hook process model, which avoids returning through the unstable
  init tail; and
* the route-specific public send_audio_cal_v5 edge before asking for real common
  custom topology.

The result is still host-only/build-only. Live use must stage the produced
helper/preload through the checked Android handoff and classify before replay.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

import build_android_acdb_setcal_capture_v2630 as v2630

ROOT = v2630.ROOT
RUN_ID = "V2719"
BUILD_TAG = "v2719-acdb-inhook-route-first-common-setcal-capture-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2719_AUDIO_ACDB_INHOOK_ROUTE_FIRST_COMMON_SETCAL_CAPTURE_BUILD_2026-06-18.md"

HELPER_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_inhook_route_first_common_exec_linked_v2719.c"
PREINIT_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdb_inhook_route_first_common_v2719.c"
HELPER_ARTIFACT_NAME = "a90_acdb_inhook_route_first_common_setcal_capture_exec_linked_v2719"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_inhook_route_first_common_setcal_capture_combined_preload_v2719.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)
TARGET_CAL_TYPES = [10, 14, 24]


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

    patch_pos = preinit.find("inhook_patch_initialized_flag_return")
    arm_pos = preinit.find("a90_arm_capture()")
    send_pos = preinit.find("a90_real_send_audio_cal_v5(A90_SPEAKER_ACDB_ID")
    common_pos = preinit.find("common_ret = a90_real_common_topology()")
    exit_pos = preinit.find("inhook_exit_after_route_first_common")

    required = {
        "helper_source_exists": helper_path.exists(),
        "preload_source_exists": preinit_path.exists(),
        "acdbtap_source_exists": acdbtap_path.exists(),
        "ioctl_source_exists": ioctl_path.exists(),
        "helper_imports_only_init_v3": "extern int32_t acdb_loader_init_v3" in helper,
        "helper_calls_init_v3_open_audconf": 'A90_ACDB_FILES_PATH "/vendor/etc/audconf/OPEN"' in helper,
        "helper_event_path_v2719": "acdb-v2719-inhook-route-first-helper-events.jsonl" in helper,
        "helper_records_unexpected_init_return": "init_returned_unexpectedly_after_inhook_route_first" in helper,
        "helper_does_not_call_send_v5": "acdb_loader_send_audio_cal_v5" not in helper,
        "helper_does_not_call_common_topology": "acdb_loader_send_common_custom_topology" not in helper,
        "preload_exports_common_topology_hook": "int32_t acdb_loader_send_common_custom_topology(void)" in preinit,
        "preload_event_path_v2719": "acdb-v2719-inhook-route-first-common-events.jsonl" in preinit,
        "preload_dlsyms_send_audio_cal_v5": "dlsym(A90_RTLD_DEFAULT, \"acdb_loader_send_audio_cal_v5\")" in preinit,
        "preload_dlsyms_real_common": "dlsym(A90_RTLD_NEXT, \"acdb_loader_send_common_custom_topology\")" in preinit,
        "preload_patches_initialized_flag": "A90_LOADER_INIT_FLAG_OFF" in preinit and "*flag = 1U" in preinit,
        "preload_arms_then_send_v5_then_real_common": patch_pos >= 0 and patch_pos < arm_pos < send_pos < common_pos < exit_pos,
        "preload_uses_corrected_send_v5_args": (
            "A90_SPEAKER_RX_CAPMASK 1" in preinit
            and "A90_AFE_SAMPLE_RATE_INIT 0" in preinit
            and "A90_SESSION_TYPE_48K 48000" in preinit
            and "A90_INSTANCE_FLAG_DEFAULT 1" in preinit
        ),
        "preload_neutralizes_reentry": "common_reentry_neutralized" in preinit and "return 0;" in preinit[preinit.find("common_reentry_neutralized"):preinit.find("common_reentry_neutralized") + 180],
        "preload_exits_inside_hook": "a90_exit(0)" in preinit and "A90_NR_EXIT_GROUP" in preinit,
        "ioctl_always_fakes_audio_set": (
            "always fake AUDIO_SET_CALIBRATION" in ioctl
            and "if (request == A90_AUDIO_SET_CALIBRATION)\n        return 1;" in ioctl
            and "fake-set-always" in ioctl
        ),
        "ioctl_dumps_arg_and_dmabuf": (
            "Dump exactly arg[0:data_size]" in ioctl
            and "mmap(0, header.cal_size, A90_PROT_READ, A90_MAP_SHARED" in ioctl
            and "dmabuf_sha" in ioctl
        ),
    }
    prohibited = {
        "helper_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in helper or "open('/dev/msm_audio_cal" in helper,
        "helper_issues_ioctl": "ioctl(" in helper or "A90_AUDIO_SET_CALIBRATION" in helper,
        "helper_imports_arm_capture": "a90_arm_capture" in helper,
        "preload_real_audio_set_syscall": "A90_NR_IOCTL" in preinit,
        "preload_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in preinit or "/dev/msm_audio_cal" in preinit,
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
        "v2719_delta": {
            "basis": "V2718 showed post-init helper continuation SIGSEGVs before send_v5; V2719 moves route-first send_v5 and real common into the init-time hook.",
            "new_call_order": "init_v3 -> common hook -> patch initialized -> arm capture -> send_audio_cal_v5(15,1,0x11135,48000,0,48000,1) -> real common topology -> exit",
            "anti_churn": "This is not another post-init route-first retry; it reuses the V2674 in-hook model that already avoids init-tail continuation.",
            "success_discriminator": "future live run must emit in-hook send_v5/common markers and byte-exact fake SET records for cal_types 10, 14, and 24.",
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
    preload_dynamic = preload.get("dynamic", {}).get("stdout", "") if isinstance(preload, dict) else ""

    if isinstance(helper, dict):
        checks = helper.setdefault("checks", {})
        if isinstance(checks, dict):
            checks.pop("undefined_common_topology", None)
            checks.pop("undefined_send_audio_cal_v5", None)
            checks.pop("undefined_or_weak_a90_arm_capture", None)
            checks["no_undefined_common_topology"] = " UND acdb_loader_send_common_custom_topology" not in helper_symbols
            checks["no_undefined_send_audio_cal_v5"] = " UND acdb_loader_send_audio_cal_v5" not in helper_symbols
            checks["no_helper_arm_capture_dependency"] = "a90_arm_capture" not in helper_symbols
            checks["needed_libacdbloader"] = "Shared library: [libacdbloader.so]" in helper.get("dynamic", {}).get("stdout", "")
            helper["ok"] = bool(helper.get("exists") and all(checks.values()))
    if isinstance(preload, dict):
        checks = preload.setdefault("checks", {})
        if isinstance(checks, dict):
            for key in ("soname_v2630", "soname_v2717"):
                checks.pop(key, None)
            checks["soname_v2719"] = f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in preload_dynamic
            checks["exports_phase_common_hook"] = " acdb_loader_send_common_custom_topology" in preload_symbols
            checks["exports_acdb_ioctl"] = " acdb_ioctl" in preload_symbols
            checks["exports_ioctl"] = " ioctl" in preload_symbols
            checks["exports_a90_arm_capture"] = " a90_arm_capture" in preload_symbols
            checks["undefined_dlsym"] = " UND dlsym" in preload_symbols
            preload["ok"] = bool(preload.get("exists") and all(checks.values()))
    build_state["ok"] = bool(helper.get("ok") and preload.get("ok"))
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
            "call_order": "init_v3 -> common hook -> patch initialized -> arm capture -> send_audio_cal_v5 -> real common topology -> exit",
            "send_audio_cal_v5_args": [15, 1, "0x11135", 48000, 0, 48000, 1],
            "target_cal_types": TARGET_CAL_TYPES,
            "set_capture": "AUDIO_SET_CALIBRATION arg[0:data_size] plus same-process dma-buf when cal_size>0",
            "success_discriminator": "future live run must capture cal_types 10, 14, and 24 without real AUDIO_SET_CALIBRATION pass-through",
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
    lines = [
        "# NATIVE_INIT V2719 — ACDB in-hook route-first common-topology SET capture build",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only build-only unit. No Android handoff, device flash, native replay, real",
        "`AUDIO_SET_CALIBRATION`, mixer write, PCM write, speaker playback, or raw ACDB",
        "payload publication occurred. Private build artifacts stay under `workspace/private`.",
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
        "V2718 confirmed the post-init route-first helper path is still blocked by the",
        "same init-tail SIGSEGV pattern seen earlier: `acdb_loader_init_v3` fake-allocates",
        "cal_types `10`, `14`, and `24`, then crashes before the helper can regain control.",
        "V2719 therefore does not retry that continuation. It moves the route-specific",
        "`send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)` edge and the real common",
        "custom-topology call into the init-time common hook itself, then exits the process.",
        "",
        "## Capture Contract",
        "",
        "- helper calls only `acdb_loader_init_v3`; returning from init is unexpected and logged",
        "- preload common hook patches `acdb_loader_is_initialized` state, arms capture, runs route-first `send_audio_cal_v5`, calls the real common topology, then exits",
        "- reentrant common-topology calls are neutralized with return `0` and logged",
        "- V2630 SET shim preserves exact `AUDIO_SET_CALIBRATION` arg bytes and same-process dma-buf payloads before fake success",
        "- future live success is byte-exact SET records for cal_types `10`, `14`, and `24`",
        "",
        "## Boundary",
        "",
        "- no helper `/dev/msm_audio_cal` open and no helper ioctl",
        "- no real `AUDIO_SET_CALIBRATION` pass-through",
        "- no native replay, mixer, PCM, AudioTrack, or speaker write",
        "- no persistent Magisk install and no raw ACDB bytes in public paths",
        "",
        "## Build Evidence",
        "",
        f"- source_required_ok: `{payload.get('sources', {}).get('required_ok')}`",
        f"- source_prohibited_ok: `{payload.get('sources', {}).get('prohibited_ok')}`",
        f"- helper_checks: `{helper.get('checks')}`",
        f"- preload_checks: `{preload.get('checks')}`",
        "",
        "## Next Unit",
        "",
        "A bounded Android-good live handoff can stage the V2719 helper/preload, force",
        "`A90_ACDB_FAKE_ALLOCATE=1`, pull `acdb-v2719-inhook-route-first-common-events.jsonl`,",
        "`acdb-v2719-inhook-route-first-helper-events.jsonl`, `setcal-events.jsonl`, and private",
        "`setcal-*` raw files, then rollback to V2321. The live unit must stop after capture",
        "and classify before any replay.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_inhook_route_first_common_setcal_capture_v2719.py tests/test_build_android_acdb_inhook_route_first_common_setcal_capture_v2719.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_inhook_route_first_common_setcal_capture_v2719 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_inhook_route_first_common_setcal_capture_v2719.py --build --write-report`",
        "- `git diff --check`",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    v2572 = v2630.v2613.v2611.v2608.v2572
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="materialize private ARM32 helper/preload artifacts")
    parser.add_argument("--write-report", action="store_true", help="write the public report")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--clang", type=Path, default=v2572.TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=v2572.TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = make_payload(args)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_report:
        write_report(payload, args.report)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
