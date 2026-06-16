#!/usr/bin/env python3
"""Build V2626 ARM32 ACDB AFE-topology probe artifacts.

This host-only unit builds a future live helper that reuses the proven V2611
meta-list init path and V2613 acdb_ioctl tap, then calls only the AFE topology
ID/table GET commands.  It does not invoke send_audio_cal_v5, native calibration
SET, speaker playback, or device action.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

import build_android_acdb_meta_list_indirect_layout_capture_v2613 as v2613

ROOT = v2613.ROOT
RUN_ID = "V2626"
BUILD_TAG = "v2626-acdb-afe-topology-probe-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2626_AUDIO_ACDB_AFE_TOPOLOGY_PROBE_BUILD_2026-06-16.md"

HELPER_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_afe_topology_probe_exec_linked_v2626.c"
HELPER_ARTIFACT_NAME = "a90_acdb_afe_topology_probe_exec_linked_v2626"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_afe_topology_probe_combined_preload_v2626.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)


def rel(path: Path | str) -> str:
    return v2613.rel(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


@contextlib.contextmanager
def patched_v2613_constants() -> Iterator[None]:
    old = {
        "HELPER_SOURCE_REL": v2613.HELPER_SOURCE_REL,
        "HELPER_ARTIFACT_NAME": v2613.HELPER_ARTIFACT_NAME,
        "PRELOAD_ARTIFACT_NAME": v2613.PRELOAD_ARTIFACT_NAME,
        "PRELOAD_LDFLAGS": v2613.PRELOAD_LDFLAGS,
    }
    v2613.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2613.HELPER_ARTIFACT_NAME = HELPER_ARTIFACT_NAME
    v2613.PRELOAD_ARTIFACT_NAME = PRELOAD_ARTIFACT_NAME
    v2613.PRELOAD_LDFLAGS = PRELOAD_LDFLAGS
    try:
        yield
    finally:
        v2613.HELPER_SOURCE_REL = old["HELPER_SOURCE_REL"]
        v2613.HELPER_ARTIFACT_NAME = old["HELPER_ARTIFACT_NAME"]
        v2613.PRELOAD_ARTIFACT_NAME = old["PRELOAD_ARTIFACT_NAME"]
        v2613.PRELOAD_LDFLAGS = old["PRELOAD_LDFLAGS"]


def source_state() -> dict[str, Any]:
    helper_path = ROOT / HELPER_SOURCE_REL
    preinit_path = ROOT / v2613.PREINIT_SOURCE_REL
    tap_path = ROOT / v2613.ACDBTAP_SOURCE_REL
    ioctl_path = ROOT / v2613.v2611.v2608.v2572.IOCTL_SOURCE_REL
    helper = _read(helper_path)
    preinit = _read(preinit_path)
    tap = _read(tap_path)
    ioctl = _read(ioctl_path)
    combined = "\n".join([helper, preinit, tap, ioctl])
    tap_extra_cflags = tuple(v2613.v2611.v2608.v2600.TAP_EXTRA_CFLAGS)

    init_pos = helper.find("init_ret = acdb_loader_init_v3")
    arm_pos = helper.find("a90_arm_capture()")
    probe_pos = helper.find("a90_run_afe_topology_probe()")
    required = {
        "helper_source_exists": helper_path.exists(),
        "preinit_source_exists": preinit_path.exists(),
        "tap_source_exists": tap_path.exists(),
        "ioctl_source_exists": ioctl_path.exists(),
        "helper_prepares_empty_meta_list": "a90_prepare_empty_meta_list" in helper,
        "helper_calls_init_v3_with_meta_head": "acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, meta_head)" in helper,
        "helper_arms_after_init_before_probe": init_pos >= 0 and arm_pos > init_pos and probe_pos > arm_pos,
        "helper_declares_direct_acdb_ioctl": "extern int32_t acdb_ioctl" in helper,
        "helper_does_not_call_send_audio_cal_v5": "acdb_loader_send_audio_cal_v5" not in helper,
        "helper_has_afe_topology_id_cmd": "0x000130d8U" in helper,
        "helper_has_afe_topologies_cmd": "0x00013262U" in helper,
        "helper_has_capacity_sweep": all(token in helper for token in ("afe-topology-cap4", "afe-topology-cap256", "afe-topology-cap4096")),
        "helper_omits_crashing_tail_meta": "0x00012eebU" not in helper,
        "helper_omits_vol_sweep": "0x0001326dU" not in helper and "0x0001326eU" not in helper,
        "preinit_still_no_send": "return_to_init_v3_no_arm_no_send" in preinit and "a90_real_send_audio_cal_v5" not in preinit,
        "preinit_still_patches_init_flag": "A90_LOADER_INIT_FLAG_OFF" in preinit and "*flag = 1U" in preinit,
        "tap_manual_arm_exported": "void a90_arm_capture(void)" in tap,
        "tap_unarmed_real_only_path": "if (!a90_armed)" in tap and "return ret;" in tap,
        "tap_auto_arm_disabled_by_build_flags": "-DA90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=0" in tap_extra_cflags,
        "tap_exit_on_target_disabled_by_build_flags": "-DA90_ACDBTAP_EXIT_ON_TARGET=0" in tap_extra_cflags,
        "tap_has_afe_topology_cmd": "A90_CMD_AFE_TOPOLOGIES 0x00013262U" in tap,
        "tap_has_afe_topology_indirect_layout": '"ind-afe-topology", 1U, 0U' in tap,
        "tap_capture_inbuf_capable": "A90_ACDBTAP_CAPTURE_INBUF" in tap and '"in"' in tap,
        "ioctl_fake_allocate_env": "A90_ACDB_FAKE_ALLOCATE" in ioctl,
        "ioctl_fakes_set_in_fake_mode": "A90_AUDIO_SET_CALIBRATION" in ioctl and "fake-success" in ioctl,
    }
    prohibited = {
        "helper_passes_zero_arg3": "acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U)" in helper,
        "helper_calls_send_audio_cal_v5": "acdb_loader_send_audio_cal_v5" in helper,
        "helper_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in helper or "open('/dev/msm_audio_cal" in helper,
        "helper_audio_set_literal": "0xC00461CB" in helper or "AUDIO_SET_CALIBRATION" in helper,
        "helper_calls_tail_meta": "0x00012eebU" in helper,
        "helper_calls_vol_getters": "0x0001326dU" in helper or "0x0001326eU" in helper,
        "preinit_exits_process": "exit_group" in preinit or "A90_NR_EXIT_GROUP" in preinit,
        "combined_global_pthread_hooks": "pthread_mutex_lock" in combined or "pthread_mutex_unlock" in combined,
        "combined_android_log_hook": "__android_log_print" in combined,
        "native_speaker_write": any(token in combined for token in ("tinyplay", "tinymix", "AudioTrack")),
        "persistent_magisk_install": "magisk --install-module" in combined,
    }
    return {
        "sources": [HELPER_SOURCE_REL, v2613.PREINIT_SOURCE_REL, v2613.ACDBTAP_SOURCE_REL, v2613.v2611.v2608.v2572.IOCTL_SOURCE_REL],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
        "probe_matrix": {
            "direct_commands": ["0x130d8", "0x13262"],
            "afe_topology_capacity_sweep": [4, 256, 4096],
            "tap_indirect_layout": {"cmd": "0x13262", "kind": "ind-afe-topology", "ptr_word": 1, "cap_word": 0},
            "live_boundary": "future Android-good own-process run only; no native replay SET",
        },
        "armed_capture_contract": {
            "unarmed": "all init-time acdb_ioctl calls pass through with no dump/hash/file I/O",
            "arm_point": "helper calls a90_arm_capture only after acdb_loader_init_v3 returns 0",
            "auto_arm_on_initialize": False,
            "exit_on_first_4916": False,
            "reason_exit_disabled": "V2626 is an AFE-topology probe; it must preserve all 0x13262 records",
        },
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    with patched_v2613_constants():
        build_state = v2613.build(build_root, clang=clang, lld=lld, readelf=readelf, file_cmd=file_cmd)

    artifacts = build_state.get("artifacts", {}) if isinstance(build_state, dict) else {}
    helper = artifacts.get("helper", {}) if isinstance(artifacts, dict) else {}
    preload = artifacts.get("preload", {}) if isinstance(artifacts, dict) else {}
    helper_sym = helper.get("symbols", {}).get("stdout", "") if isinstance(helper, dict) else ""
    preload_dyn = preload.get("dynamic", {}).get("stdout", "") if isinstance(preload, dict) else ""

    helper_checks = helper.setdefault("checks", {}) if isinstance(helper, dict) else {}
    helper_checks.pop("undefined_send_audio_cal_v5", None)
    helper_checks.update(
        {
            "undefined_acdb_ioctl": " UND acdb_ioctl" in helper_sym,
            "undefined_init_v3": " UND acdb_loader_init_v3" in helper_sym,
            "undefined_or_weak_a90_arm_capture": " a90_arm_capture" in helper_sym,
            "does_not_reference_send_audio_cal_v5": "acdb_loader_send_audio_cal_v5" not in helper_sym,
        }
    )
    if isinstance(helper, dict):
        helper["ok"] = bool(helper.get("file", {}).get("ok") and all(helper_checks.values()))

    preload_checks = preload.setdefault("checks", {}) if isinstance(preload, dict) else {}
    preload_checks.pop("soname_v2613", None)
    preload_checks.update({"soname_v2626": f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in preload_dyn})
    if isinstance(preload, dict):
        preload["ok"] = bool(preload.get("file", {}).get("ok") and all(preload_checks.values()))

    build_state["ok"] = bool(helper.get("ok") and preload.get("ok")) if isinstance(build_state, dict) else False
    return build_state


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state()
    vendor = v2613.v2611.v2608.v2572.vendor_lib_state(args.readelf)
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
            "no_real_audio_set": "direct helper does not open /dev/msm_audio_cal; preload still fake-successes any accidental SET in fake mode",
        },
        "capture_contract": {
            "base": "V2611 meta-list init + V2608 no-send preinit + V2613 indirect-layout tap",
            "postinit": "init_v3 return -> a90_arm_capture -> AFE topology ID/table direct GET probe",
            "does_not_call": "acdb_loader_send_audio_cal_v5",
            "success_discriminator": "future live ACDB captures require ret==0 plus non-all-zero indirect payloads",
            "purpose": "capture or falsify the missing AFE topology 8/9 payload path before native multi-cal replay",
            "armed_dump_policy": "pre-init acdb_ioctl is passthrough only; post-init armed capture dumps out_len>0 and indirect buffers",
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


def write_report(payload: dict[str, Any], path: Path) -> None:
    helper = payload.get("build", {}).get("artifacts", {}).get("helper", {})
    preload = payload.get("build", {}).get("artifacts", {}).get("preload", {})
    source = payload.get("sources", {})
    probe = source.get("probe_matrix", {})
    lines = [
        "# NATIVE_INIT V2626 — ACDB AFE topology probe build",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only build-only unit. It builds a future Android-good own-process",
        "helper/preload pair that calls only the AFE topology ID/table GET path.",
        "No device handoff, flash, native replay `SET`, speaker write, or ACDB command execution occurred.",
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
        "## Why This Unit Exists",
        "",
        "Gate-2 verification superseded the old post-init topology-capture handover:",
        "topology cal_type 39 is already captured, while the native replay manifest",
        "still lacks AFE topology cal_type 8/9. V2547 showed command `0x13262`",
        "during the successful topology path, but the old tap only preserved the direct",
        "4-byte out buffer. V2626 adds a command-specific indirect capture for that path.",
        "",
        "## Probe Contract",
        "",
        f"- direct_commands: `{probe.get('direct_commands')}`",
        f"- capacity_sweep: `{probe.get('afe_topology_capacity_sweep')}`",
        f"- tap_indirect_layout: `{probe.get('tap_indirect_layout')}`",
        "- helper omits `0x12eeb`, VOL sweep, `send_audio_cal_v5`, `/dev/msm_audio_cal`, and native SET.",
        "- raw captures remain private-only and require future live Gate-2 operator verification before replay.",
        "",
        "## Static Gates",
        "",
        f"- required_ok: `{source.get('required_ok')}`",
        f"- prohibited_ok: `{source.get('prohibited_ok')}`",
        f"- vendor_libs_ok: `{payload.get('vendor_libs', {}).get('required_for_v2572_ok')}`",
        f"- build_ok: `{payload.get('build', {}).get('ok')}`",
        "",
        "## Next",
        "",
        "Run a bounded Android-good own-process live handoff with these artifacts, pull the",
        "complete tap directory privately, and classify any `ind-afe-topology` records as",
        "payload candidates only after `ret==0` and non-zero-buffer checks. Native replay remains blocked.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="materialize private ARM32 artifacts")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--clang", type=Path, default=v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld")
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
    print(json.dumps({"ok": payload.get("ok"), "manifest": rel(args.manifest), "report": rel(args.report) if args.write_report else None}, indent=2))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
