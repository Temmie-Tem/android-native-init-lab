#!/usr/bin/env python3
"""Build V2728 ARM32 ACDB vi-feedback SET-calibration capture artifacts.

V2727 identified a concrete gap after V2726: Android-good sends a preceding
vi-feedback ACDB path (`acdb_id=102`, `app_type=0x11132`, 8000 Hz, cal_type 17)
that native replay has never byte-captured or replayed.  V2728 is host-only and
build-only.  It reuses the V2630 fake-SET capture shim and swaps only the
own-process helper call tuple to the vi-feedback edge.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

import build_android_acdb_setcal_capture_v2630 as v2630

ROOT = v2630.ROOT
RUN_ID = "V2728"
BUILD_TAG = "v2728-acdb-vi-feedback-setcal-capture-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2728_AUDIO_ACDB_VI_FEEDBACK_SETCAL_CAPTURE_BUILD_2026-06-18.md"

HELPER_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_vi_feedback_setcal_exec_linked_v2728.c"
HELPER_ARTIFACT_NAME = "a90_acdb_vi_feedback_setcal_capture_exec_linked_v2728"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_vi_feedback_setcal_capture_combined_preload_v2728.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)

VI_FEEDBACK_CALL = {
    "acdb_id": 102,
    "path": 1,
    "app_type": "0x11132",
    "sample_rate": 8000,
    "stack_arg5": 0,
    "afe_sample_rate": 8000,
    "instance": 1,
}
EXPECTED_CAL_TYPES = [11, 17]


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
        "v2630_helper_artifact": v2630.HELPER_ARTIFACT_NAME,
        "v2630_preload_artifact": v2630.PRELOAD_ARTIFACT_NAME,
        "v2630_preload_ldflags": v2630.PRELOAD_LDFLAGS,
        "v2613_helper_source": v2613.HELPER_SOURCE_REL,
        "v2608_helper_source": v2608.HELPER_SOURCE_REL,
    }
    v2630.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2630.HELPER_ARTIFACT_NAME = HELPER_ARTIFACT_NAME
    v2630.PRELOAD_ARTIFACT_NAME = PRELOAD_ARTIFACT_NAME
    v2630.PRELOAD_LDFLAGS = PRELOAD_LDFLAGS
    v2613.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2608.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    try:
        yield
    finally:
        v2630.HELPER_SOURCE_REL = old["v2630_helper_source"]
        v2630.HELPER_ARTIFACT_NAME = old["v2630_helper_artifact"]
        v2630.PRELOAD_ARTIFACT_NAME = old["v2630_preload_artifact"]
        v2630.PRELOAD_LDFLAGS = old["v2630_preload_ldflags"]
        v2613.HELPER_SOURCE_REL = old["v2613_helper_source"]
        v2608.HELPER_SOURCE_REL = old["v2608_helper_source"]


def source_state() -> dict[str, Any]:
    helper_path = ROOT / HELPER_SOURCE_REL
    ioctl_path = ROOT / v2630.IOCTL_SOURCE_REL
    helper = _read(helper_path)
    ioctl = _read(ioctl_path)
    with patched_v2630_constants():
        base = v2630.source_state()

    init_pos = helper.find("init_ret = acdb_loader_init_v3")
    arm_pos = helper.find("a90_arm_capture()")
    send_pos = helper.find("cal_ret = acdb_loader_send_audio_cal_v5")
    required = {
        "helper_source_exists": helper_path.exists(),
        "base_v2630_required_ok": bool(base.get("required_ok")),
        "base_v2630_prohibited_ok": bool(base.get("prohibited_ok")),
        "helper_prepares_empty_meta_list": "a90_prepare_empty_meta_list" in helper,
        "helper_calls_init_v3_with_meta_head": "acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, meta_head)" in helper,
        "helper_arms_after_init_before_send": init_pos >= 0 and arm_pos > init_pos and send_pos > arm_pos,
        "helper_event_identity_v2728": "v2728_vi_feedback_setcal" in helper and "acdb-v2728-vi-feedback-setcal-events.jsonl" in helper,
        "helper_vi_feedback_tuple": all(
            token in helper
            for token in [
                "#define A90_SPEAKER_ACDB_ID 102",
                "#define A90_SPEAKER_RX_PATH 1",
                "#define A90_APP_TYPE_MEDIA 0x11132",
                "#define A90_SAMPLE_RATE_48K 8000",
                "#define A90_SESSION_TYPE_DEFAULT 0",
                "#define A90_AFE_SAMPLE_RATE_48K 8000",
                "#define A90_INSTANCE_FLAG_DEFAULT 1",
            ]
        ),
        "helper_stage_names_show_vi_feedback": "before_send_audio_cal_v5_vi_feedback" in helper,
        "ioctl_fake_setcal_capture_reused": (
            "always fake AUDIO_SET_CALIBRATION" in ioctl
            and "setcal-events.jsonl" in ioctl
            and "mmap(0, header.cal_size, A90_PROT_READ, A90_MAP_SHARED" in ioctl
        ),
    }
    prohibited = {
        "helper_opens_msm_audio_cal": "/dev/msm_audio_cal" in helper,
        "helper_issues_ioctl": "ioctl(" in helper or "A90_AUDIO_SET_CALIBRATION" in helper,
        "helper_native_speaker_write": any(token in helper for token in ("tinyplay", "tinymix", "AudioTrack")),
        "helper_persistent_magisk_install": "magisk --install-module" in helper,
        "helper_uses_speaker_tuple_values": "0x11135" in helper or "#define A90_SPEAKER_ACDB_ID 15" in helper or "#define A90_SAMPLE_RATE_48K 48000" in helper,
    }
    return {
        "sources": [HELPER_SOURCE_REL, v2630.PREINIT_SOURCE_REL, v2630.ACDBTAP_SOURCE_REL, v2630.IOCTL_SOURCE_REL],
        "base_v2630": base,
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
        "v2728_delta": {
            "basis": "V2727: Android-good sends vi-feedback ACDB before speaker RX; native replay lacks acdb_id 102 / cal_type 17",
            "helper_call": "acdb_loader_send_audio_cal_v5(102, 1, 0x11132, 8000, 0, 8000, 1)",
            "expected_cal_types": EXPECTED_CAL_TYPES,
            "measurement_boundary": "reuse V2630 fake AUDIO_SET_CALIBRATION arg+dmabuf capture; no real SET in Android-good capture",
        },
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    with patched_v2630_constants():
        build_state = v2630.build(build_root, clang=clang, lld=lld, readelf=readelf, file_cmd=file_cmd)
    preload = build_state.get("artifacts", {}).get("preload", {}) if isinstance(build_state, dict) else {}
    checks = preload.get("checks", {}) if isinstance(preload, dict) else {}
    if "soname_v2630" in checks:
        checks["soname_v2728"] = checks.pop("soname_v2630")
    return build_state


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state()
    vendor = v2630.v2613.v2611.v2608.v2572.vendor_lib_state(args.readelf)
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
            "no_real_audio_set": "V2630 ioctl shim fake-successes AUDIO_SET_CALIBRATION after dumping SET metadata/raw bytes",
        },
        "capture_contract": {
            "base": "V2630 SET arg + same-process dma-buf capture",
            "postinit": "init_v3 return -> a90_arm_capture -> vi-feedback send_audio_cal_v5",
            "vi_feedback_call": VI_FEEDBACK_CALL,
            "expected_live_records": "future live capture should include cal_type 17 / acdb_id 102, plus any paired cal_type 11/header records",
            "success_discriminator": "ret==0 plus non-all-zero payload for payload-backed records; requested size alone is failure",
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
    lines = [
        "# NATIVE_INIT V2728 — vi-feedback ACDB SET capture build",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only build-only unit. No Android handoff, device flash, native replay SET,",
        "mixer write, PCM write, AudioTrack, or speaker write was performed. Raw ACDB bytes",
        "remain private-only.",
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
        "V2726 proved the corrected native speaker ACDB SET sequence reaches the kernel",
        "successfully but PCM prepare still fails at AFE/q6asm/ADM. V2727 re-read Android-good",
        "evidence and identified a preceding `vi-feedback` ACDB path that native has not",
        "captured or replayed: `acdb_id=102`, `path=1`, `app_type=0x11132`, 8000 Hz, and",
        "`AUDIO_SET_AFE_CAL cal_type[17]`.",
        "",
        "## Capture Contract",
        "",
        "- reuses the V2630 fake `AUDIO_SET_CALIBRATION` arg + dma-buf capture shim",
        "- keeps the V2611/V2613 meta-list init path so `acdb_loader_init_v3` can return cleanly",
        "- arms capture only after `init_v3` returns",
        "- calls `acdb_loader_send_audio_cal_v5(102, 1, 0x11132, 8000, 0, 8000, 1)`",
        "- future live success requires byte-captured vi-feedback SET records, especially `cal_type=17` / `acdb_id=102`",
        "- guessed geometry from this report must not be replayed natively before live capture verification",
        "",
        "## Boundary",
        "",
        "- no helper `/dev/msm_audio_cal` open and no helper ioctl",
        "- no real `AUDIO_SET_CALIBRATION` pass-through",
        "- no native replay, mixer, PCM, AudioTrack, or speaker write",
        "- no raw payloads or proprietary libraries in public paths",
        "",
        "## Build Evidence",
        "",
        f"- source_required_ok: `{payload.get('sources', {}).get('required_ok')}`",
        f"- source_prohibited_ok: `{payload.get('sources', {}).get('prohibited_ok')}`",
        f"- helper_checks: `{helper.get('checks')}`",
        f"- preload_checks: `{preload.get('checks')}`",
        f"- helper_compile_ok: `{build.get('compile', {}).get('helper', {}).get('ok') if isinstance(build, dict) else None}`",
        f"- preload_compile_ok: `{preload.get('ok')}`",
        "",
        "## Next Unit",
        "",
        "Run the rollbackable Android-good own-process capture handoff with these artifacts,",
        "force `A90_ACDB_FAKE_ALLOCATE=1`, pull `acdb-v2728-vi-feedback-setcal-events.jsonl`,",
        "`setcal-events.jsonl`, `ioctl-trace-events.jsonl`, and private `setcal-*` raw files,",
        "then rollback to V2321. Classify before any native replay extension.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_vi_feedback_setcal_capture_v2728.py tests/test_build_android_acdb_vi_feedback_setcal_capture_v2728.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_vi_feedback_setcal_capture_v2728 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_vi_feedback_setcal_capture_v2728.py --build --write-report`",
        "- `git diff --check`",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = make_payload(args)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_report:
        write_report(payload, args.report)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
