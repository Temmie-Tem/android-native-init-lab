#!/usr/bin/env python3
"""Build V2654 custom-topology ACDB SET capture artifacts.

This is a host-only build wrapper that combines the existing V2553 full-manifest
own-process helper (common topology + send_audio_cal_v5) with the V2630
fake-success AUDIO_SET_CALIBRATION preload.  It does not run Android, issue a
real SET, or perform native replay.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

import build_android_acdb_setcal_capture_v2630 as v2630

ROOT = v2630.ROOT
RUN_ID = "V2654"
BUILD_TAG = "v2654-acdb-custom-topology-setcal-capture-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2654_AUDIO_ACDB_CUSTOM_TOPOLOGY_SETCAL_CAPTURE_BUILD_2026-06-18.md"

HELPER_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_full_manifest_exec_linked_v2553.c"
HELPER_ARTIFACT_NAME = "a90_acdb_custom_topology_setcal_capture_exec_linked_v2654"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_custom_topology_setcal_capture_combined_preload_v2654.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)


def rel(path: Path | str) -> str:
    return v2630.rel(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


@contextlib.contextmanager
def patched_v2630_constants() -> Iterator[None]:
    old = {
        "v2630_helper_source": v2630.HELPER_SOURCE_REL,
        "v2630_helper_artifact": v2630.HELPER_ARTIFACT_NAME,
        "v2630_preload_artifact": v2630.PRELOAD_ARTIFACT_NAME,
        "v2630_preload_ldflags": v2630.PRELOAD_LDFLAGS,
        "v2613_helper_source": v2630.v2613.HELPER_SOURCE_REL,
    }
    v2630.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2630.HELPER_ARTIFACT_NAME = HELPER_ARTIFACT_NAME
    v2630.PRELOAD_ARTIFACT_NAME = PRELOAD_ARTIFACT_NAME
    v2630.PRELOAD_LDFLAGS = PRELOAD_LDFLAGS
    v2630.v2613.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    try:
        yield
    finally:
        v2630.HELPER_SOURCE_REL = old["v2630_helper_source"]
        v2630.HELPER_ARTIFACT_NAME = old["v2630_helper_artifact"]
        v2630.PRELOAD_ARTIFACT_NAME = old["v2630_preload_artifact"]
        v2630.PRELOAD_LDFLAGS = old["v2630_preload_ldflags"]
        v2630.v2613.HELPER_SOURCE_REL = old["v2613_helper_source"]


def source_state() -> dict[str, Any]:
    helper_path = ROOT / HELPER_SOURCE_REL
    preinit_path = ROOT / v2630.PREINIT_SOURCE_REL
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

    required = {
        "helper_source_exists": helper_path.exists(),
        "preinit_source_exists": preinit_path.exists(),
        "acdbtap_source_exists": acdbtap_path.exists(),
        "ioctl_source_exists": ioctl_path.exists(),
        "helper_imports_common_topology": "extern int32_t acdb_loader_send_common_custom_topology(void);" in helper,
        "helper_imports_send_audio_cal_v5": "extern int32_t acdb_loader_send_audio_cal_v5" in helper,
        "helper_calls_init_v3_open_audconf": 'A90_ACDB_FILES_PATH "/vendor/etc/audconf/OPEN"' in helper,
        "helper_arms_after_init": init_pos >= 0 and arm_pos > init_pos,
        "helper_calls_common_topology_before_send_v5": common_pos > arm_pos and send_pos > common_pos,
        "helper_records_common_topology_return": "send_common_custom_topology_return" in helper,
        "helper_records_send_v5_return": "send_audio_cal_v5_return" in helper,
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
        "preinit_still_no_send": (
            "return_to_init_v3_no_arm_no_send" in preinit
            and "a90_real_send_audio_cal_v5" not in preinit
        ),
    }
    prohibited = {
        "helper_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in helper or "open('/dev/msm_audio_cal" in helper,
        "ioctl_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in ioctl or "open('/dev/msm_audio_cal" in ioctl,
        "combined_native_speaker_write": any(token in combined for token in ("tinyplay", "tinymix", "AudioTrack")),
        "combined_persistent_magisk_install": "magisk --install-module" in combined,
        "combined_global_pthread_hooks": "pthread_mutex_lock" in combined or "pthread_mutex_unlock" in combined,
        "combined_android_log_hook": "__android_log_print" in combined,
    }
    return {
        "sources": [HELPER_SOURCE_REL, v2630.PREINIT_SOURCE_REL, v2630.ACDBTAP_SOURCE_REL, v2630.IOCTL_SOURCE_REL],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
        "v2654_delta": {
            "basis": "V2653: cal20 is real but V2648 needs custom topology SETs 10/14/24",
            "helper": "V2553 full-manifest helper: init_v3 -> arm -> common topology -> send_audio_cal_v5",
            "preload": "V2630 fake SET capture preload: dump arg bytes and dma-buf, fake AUDIO_SET_CALIBRATION",
            "acceptance": "future live capture must include byte-exact cal_types 10, 14, and 24; cal20 alone is insufficient",
        },
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    with patched_v2630_constants():
        build_state = v2630.build(build_root, clang=clang, lld=lld, readelf=readelf, file_cmd=file_cmd)
    artifacts = build_state.get("artifacts", {}) if isinstance(build_state, dict) else {}
    helper = artifacts.get("helper", {}) if isinstance(artifacts, dict) else {}
    preload = artifacts.get("preload", {}) if isinstance(artifacts, dict) else {}
    helper_symbols = helper.get("symbols", {}).get("stdout", "") if isinstance(helper, dict) else ""
    preload_checks = preload.get("checks", {}) if isinstance(preload, dict) else {}
    if isinstance(preload_checks, dict) and "soname_v2630" in preload_checks:
        preload_checks["soname_v2654"] = preload_checks.pop("soname_v2630")
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
            "call_order": "acdb_loader_init_v3 -> a90_arm_capture -> acdb_loader_send_common_custom_topology -> acdb_loader_send_audio_cal_v5",
            "target_cal_types": [10, 14, 24],
            "supplemental_cal_types": [20],
            "success_discriminator": "future live run must capture byte-exact SET records for 10/14/24; cal20 alone is partial",
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
    lines = [
        "# NATIVE_INIT V2654 — ACDB custom-topology SET capture build",
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
        "## Capture Contract",
        "",
        "- helper call order: `init_v3 -> arm -> send_common_custom_topology -> send_audio_cal_v5`",
        "- preload is the V2630 fake-SET shim: dump SET arg bytes, mmap same-process dma-buf",
        "  if present, then fake-success the SET so no kernel SET is delivered during capture",
        "- target acceptance for the future live run: byte-exact SET records for cal_types",
        "  `10`, `14`, and `24`",
        "- cal_type `20` is retained as supplemental evidence, but cal20 alone is not success",
        "",
        "## Source Checks",
        "",
        f"- required_ok: `{payload.get('sources', {}).get('required_ok')}`",
        f"- prohibited_ok: `{payload.get('sources', {}).get('prohibited_ok')}`",
        f"- helper_checks: `{helper.get('checks')}`",
        f"- preload_checks: `{preload.get('checks')}`",
        "",
        "## Next Unit",
        "",
        "A future live handoff can stage these artifacts into the existing V2490/V2631 Android-good",
        "own-process runner. It must keep `A90_ACDB_FAKE_ALLOCATE=1`, pull the full private",
        "`setcal-events.jsonl` plus raw files, and classify success only if cal_types `10`, `14`,",
        "and `24` are captured byte-exact.",
        "",
        "## Validation",
        "",
        "- `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec were reread.",
        "- source checks verify common-topology call order and fake-SET boundary.",
        "- ARM32 build artifacts are private under `workspace/private/builds/audio/`.",
        "- `py_compile`, focused unittest, build invocation, `file`/symbol checks, and",
        "  `git diff --check` were run.",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
