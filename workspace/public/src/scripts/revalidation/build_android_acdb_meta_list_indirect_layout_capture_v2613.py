#!/usr/bin/env python3
"""Build V2613 ARM32 ACDB meta-list post-init indirect-layout capture artifacts.

Host-only build-only unit after V2612.  V2612 proved the V2611 helper can
initialize ACDB and drive send_audio_cal_v5, but the direct acdb_ioctl out_buf
records are four-byte size/status words.  The real per-device cal bytes live in
command-specific indirect buffers pointed to by the input request structs.

V2613 keeps the V2611 helper/preinit/fake-audio-cal boundary and swaps only the
ACDB tap source for a command-layout-aware version that dumps those indirect
buffers after successful GET returns.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

import build_android_acdb_meta_list_postinit_send_v5_combined_preload_v2611 as v2611

ROOT = v2611.ROOT
RUN_ID = "V2613"
BUILD_TAG = "v2613-acdb-meta-list-indirect-layout-capture-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2613_AUDIO_ACDB_META_LIST_INDIRECT_LAYOUT_CAPTURE_BUILD_2026-06-16.md"

HELPER_SOURCE_REL = v2611.HELPER_SOURCE_REL
PREINIT_SOURCE_REL = v2611.PREINIT_SOURCE_REL
ACDBTAP_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdbtap_indirect_layout_v2613.c"
HELPER_ARTIFACT_NAME = "a90_acdb_meta_list_indirect_layout_capture_exec_linked_v2613"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_meta_list_indirect_layout_capture_combined_preload_v2613.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)


def rel(path: Path | str) -> str:
    return v2611.rel(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


@contextlib.contextmanager
def patched_v2608_constants() -> Iterator[None]:
    v2608 = v2611.v2608
    old = {
        "HELPER_SOURCE_REL": v2608.HELPER_SOURCE_REL,
        "HELPER_ARTIFACT_NAME": v2608.HELPER_ARTIFACT_NAME,
        "PRELOAD_ARTIFACT_NAME": v2608.PRELOAD_ARTIFACT_NAME,
        "PRELOAD_LDFLAGS": v2608.PRELOAD_LDFLAGS,
        "ACDBTAP_SOURCE_REL": v2608.v2600.ACDBTAP_SOURCE_REL,
    }
    v2608.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2608.HELPER_ARTIFACT_NAME = HELPER_ARTIFACT_NAME
    v2608.PRELOAD_ARTIFACT_NAME = PRELOAD_ARTIFACT_NAME
    v2608.PRELOAD_LDFLAGS = PRELOAD_LDFLAGS
    v2608.v2600.ACDBTAP_SOURCE_REL = ACDBTAP_SOURCE_REL
    try:
        yield
    finally:
        v2608.HELPER_SOURCE_REL = old["HELPER_SOURCE_REL"]
        v2608.HELPER_ARTIFACT_NAME = old["HELPER_ARTIFACT_NAME"]
        v2608.PRELOAD_ARTIFACT_NAME = old["PRELOAD_ARTIFACT_NAME"]
        v2608.PRELOAD_LDFLAGS = old["PRELOAD_LDFLAGS"]
        v2608.v2600.ACDBTAP_SOURCE_REL = old["ACDBTAP_SOURCE_REL"]


def source_state() -> dict[str, Any]:
    helper_path = ROOT / HELPER_SOURCE_REL
    preinit_path = ROOT / PREINIT_SOURCE_REL
    tap_path = ROOT / ACDBTAP_SOURCE_REL
    ioctl_path = ROOT / v2611.v2608.v2572.IOCTL_SOURCE_REL
    helper = _read(helper_path)
    preinit = _read(preinit_path)
    tap = _read(tap_path)
    ioctl = _read(ioctl_path)
    combined = "\n".join([helper, preinit, tap, ioctl])

    init_pos = helper.find("init_ret = acdb_loader_init_v3")
    arm_pos = helper.find("a90_arm_capture()")
    send_pos = helper.find("cal_ret = acdb_loader_send_audio_cal_v5")
    layout_pos = tap.find("a90_log_command_layout_indirect_captures")
    generic_pos = tap.find("a90_log_indirect_candidate_captures")

    required = {
        "helper_source_exists": helper_path.exists(),
        "preinit_source_exists": preinit_path.exists(),
        "tap_source_exists": tap_path.exists(),
        "ioctl_source_exists": ioctl_path.exists(),
        "helper_prepares_empty_meta_list": "a90_prepare_empty_meta_list" in helper,
        "helper_calls_init_v3_with_meta_head": "acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, meta_head)" in helper,
        "helper_arms_after_init_before_send": init_pos >= 0 and arm_pos > init_pos and send_pos > arm_pos,
        "helper_calls_send_v5_corrected_order": "acdb_loader_send_audio_cal_v5(A90_SPEAKER_ACDB_ID" in helper and "A90_SPEAKER_RX_PATH" in helper,
        "preinit_still_no_send": "return_to_init_v3_no_arm_no_send" in preinit and "a90_real_send_audio_cal_v5" not in preinit,
        "tap_manual_arm_exported": "void a90_arm_capture(void)" in tap,
        "tap_unarmed_real_only_path": "if (!a90_armed)" in tap and "return ret;" in tap,
        "tap_layout_dump_before_generic_scan": layout_pos >= 0 and generic_pos >= 0 and layout_pos < generic_pos,
        "tap_allows_high_android32_user_va": "0xffff0000U" in tap and "a90_is_probable_android32_read_ptr" in tap,
        "tap_audproc_common_layout": "A90_CMD_AUDPROC_INSTANCE_COMMON_TABLE" in tap and '"ind-ap-common", 4U, 3U' in tap,
        "tap_audproc_stream_layout": "A90_CMD_AUDPROC_INSTANCE_STREAM_TABLE" in tap and '"ind-ap-stream", 2U, 1U' in tap,
        "tap_gain_dep_layout": "A90_CMD_AUDPROC_GAIN_DEP_STEP_TABLE" in tap and '"ind-ap-gain", 4U, 3U' in tap,
        "tap_afe_common_layout": "A90_CMD_AFE_INSTANCE_COMMON_TABLE" in tap and '"ind-afe-common", 3U, 2U' in tap,
        "tap_length_from_out_word0_and_cap_guard": "dump_len = a90_out_word0(out, out_len)" in tap and "dump_len > cap_len" in tap,
        "tap_ret0_only_indirect_dump": "if (ret != 0 || !in || !out || out_len < 4U)" in tap,
        "tap_zero_buffer_guard_preserved": "ret == 0 && buf_len == A90_TARGET_OUT_LEN && !all_zero" in tap,
        "ioctl_fake_allocate_env": "A90_ACDB_FAKE_ALLOCATE" in ioctl,
        "ioctl_fakes_set_in_fake_mode": "A90_AUDIO_SET_CALIBRATION" in ioctl and "fake-success" in ioctl,
    }
    prohibited = {
        "helper_passes_zero_arg3": "acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U)" in helper,
        "preinit_exits_process": "exit_group" in preinit or "A90_NR_EXIT_GROUP" in preinit,
        "tap_opens_msm_audio_cal": "/dev/msm_audio_cal" in tap,
        "ioctl_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in ioctl or "open('/dev/msm_audio_cal" in ioctl,
        "combined_global_pthread_hooks": "pthread_mutex_lock" in combined or "pthread_mutex_unlock" in combined,
        "combined_android_log_hook": "__android_log_print" in combined,
        "native_speaker_write": any(token in combined for token in ("tinyplay", "tinymix", "AudioTrack")),
        "persistent_magisk_install": "magisk --install-module" in combined,
    }
    return {
        "sources": [HELPER_SOURCE_REL, PREINIT_SOURCE_REL, ACDBTAP_SOURCE_REL, v2611.v2608.v2572.IOCTL_SOURCE_REL],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
        "v2613_delta": {
            "basis": "V2612 showed ret==0 per-device GETs return four-byte direct out buffers while payload pointers live in command-specific in_buf words",
            "layout_map": {
                "0x13265": "AUDPROC common: ptr=in_word4, cap=in_word3, len=out_word0",
                "0x13269": "AUDPROC stream: ptr=in_word2, cap=in_word1, len=out_word0",
                "0x1326e": "AUDPROC gain/VOL: ptr=in_word4, cap=in_word3, len=out_word0 when ret==0",
                "0x1326f": "AFE common: ptr=in_word3, cap=in_word2, len=out_word0",
            },
        },
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    with patched_v2608_constants():
        build_state = v2611.v2608.build(build_root, clang=clang, lld=lld, readelf=readelf, file_cmd=file_cmd)
    preload = build_state.get("artifacts", {}).get("preload", {}) if isinstance(build_state, dict) else {}
    checks = preload.get("checks", {}) if isinstance(preload, dict) else {}
    if "soname_v2608" in checks:
        checks["soname_v2613"] = checks.pop("soname_v2608")
    return build_state


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state()
    vendor = v2611.v2608.v2572.vendor_lib_state(args.readelf)
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
            "base": "V2611 meta-list helper + V2608 post-init arm/send + V2531 fake audio-cal ioctl shim",
            "preinit": "skip common topology, patch initialized flag, return to acdb_loader_init_v3 without arm/send/exit",
            "postinit": "helper arms capture after init_v3 returns, then calls send_audio_cal_v5",
            "per_device_call": "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
            "direct_outbuf_policy": "still dumps every out_len>0 direct out_buf",
            "indirect_policy": "after ret==0, dump command-specific in_buf pointer payloads using out_word0 length and cap guards",
            "success_discriminator": "future live ACDB captures require ret==0 plus non-all-zero buffers; requested length alone is failure",
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
    delta = payload.get("sources", {}).get("v2613_delta", {})
    layout_map = delta.get("layout_map", {}) if isinstance(delta, dict) else {}
    lines = [
        "# NATIVE_INIT V2613 — ACDB meta-list indirect-layout capture build",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only build-only unit after V2612. No Android handoff, device flash, native replay SET,",
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
        "V2612 reached `init_v3_return` and `send_audio_cal_v5_return` cleanly, but every direct",
        "`acdb_ioctl` `out_buf` record was a four-byte size/status word. The useful per-device",
        "payloads are indirect buffers whose pointers are embedded in the input structs for the",
        "successful GET commands.",
        "",
        "## Indirect Layout Contract",
        "",
    ]
    for cmd, desc in layout_map.items():
        lines.append(f"- `{cmd}`: {desc}")
    lines.extend(
        [
            "",
            "The V2613 tap dumps these only after the real `acdb_ioctl` returns `ret==0`, uses",
            "`out_word0` as the payload length, rejects zero length, rejects `len > cap`, and allows",
            "high ARM32 Android user VAs such as the `0xeb...` pointers observed in V2612.",
            "",
            "## Boundary",
            "",
            "- no new helper behavior beyond the V2611 init/meta-list/send path",
            "- no real `/dev/msm_audio_cal` allocate/deallocate/SET in fake mode",
            "- no native replay, mixer, PCM, AudioTrack, or speaker write",
            "- raw ACDB bytes remain private-only and are not committed",
            "",
            "## Build Evidence",
            "",
            f"- source_required_ok: `{payload.get('sources', {}).get('required_ok')}`",
            f"- source_prohibited_ok: `{payload.get('sources', {}).get('prohibited_ok')}`",
            f"- helper_compile_ok: `{build.get('compile', {}).get('helper', {}).get('ok') if isinstance(build, dict) else None}`",
            f"- tap_compile_ok: `{build.get('compile', {}).get('acdbtap_v2600', {}).get('ok') if isinstance(build, dict) else None}`",
            f"- preinit_compile_ok: `{build.get('compile', {}).get('preinit_no_send', {}).get('ok') if isinstance(build, dict) else None}`",
            f"- helper_checks: `{helper.get('checks')}`",
            f"- preload_checks: `{preload.get('checks')}`",
            "",
            "## Next Unit",
            "",
            "Run a bounded Android-good live handoff with the V2613 helper/preload override. The expected",
            "win is private `ind-ap-common`, `ind-ap-stream`, and `ind-afe-common` raw files with",
            "`ret==0` and non-all-zero payloads. A no-4916 result remains partial success if these",
            "per-device payloads are captured.",
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_meta_list_indirect_layout_capture_v2613.py tests/test_build_android_acdb_meta_list_indirect_layout_capture_v2613.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_meta_list_indirect_layout_capture_v2613 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_meta_list_indirect_layout_capture_v2613.py --build --write-report`",
            "- `git diff --check`",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--clang", type=Path, default=v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld")
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
