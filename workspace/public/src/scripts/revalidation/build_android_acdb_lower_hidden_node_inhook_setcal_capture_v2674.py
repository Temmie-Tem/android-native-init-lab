#!/usr/bin/env python3
"""Build V2674 in-hook lower hidden-node ACDB SET capture artifacts.

Host-only build unit. V2673 proved the V2672 post-init helper path can SIGSEGV
after the common-topology hook returns but before the helper can arm capture and
call the lower runner. V2674 keeps the same V2671 lower-node sequence, but moves
arm + lower-node execution into the common-topology hook itself and exits the
process after the fake SET capture has had a chance to write artifacts.

* create_cal_node at base+0xfd45;
* allocate_cal_block at base+0xfbbd;
* pinned acdb_ioctl GET commands for cal_types 24/10/14; and
* fake AUDIO_SET_CALIBRATION through the existing V2630 shim.

No Android handoff, device flash, native replay, real audio SET, mixer, PCM, or
speaker write happens in this build unit.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

import build_android_acdb_custom_topology_phase_common_setcal_capture_v2659 as v2659

ROOT = v2659.ROOT
RUN_ID = "V2674"
BUILD_TAG = "v2674-acdb-lower-hidden-node-inhook-setcal-capture-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2674_AUDIO_ACDB_LOWER_HIDDEN_NODE_INHOOK_CAPTURE_BUILD_2026-06-18.md"

HELPER_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_lower_hidden_node_inhook_exec_linked_v2674.c"
PREINIT_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdb_lower_hidden_node_inhook_v2674.c"
HELPER_ARTIFACT_NAME = "a90_acdb_lower_hidden_node_inhook_setcal_capture_exec_linked_v2674"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_lower_hidden_node_inhook_setcal_capture_combined_preload_v2674.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)
TARGET_CAL_TYPES = [24, 10, 14]
TARGET_GET_COMMANDS = {24: "0x000130da", 10: "0x00011394", 14: "0x00012e01"}


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


def source_state() -> dict[str, Any]:
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
    arm_pos = preinit.find("a90_arm_capture()")
    lower_pos = preinit.find("a90_run_lower_hidden_nodes()")
    patch_pos = preinit.find("patch_initialized_flag_return")
    exit_pos = preinit.find("exit_after_inhook_lower_hidden_nodes")

    required = {
        "helper_source_exists": helper_path.exists(),
        "lower_preload_source_exists": preinit_path.exists(),
        "setcal_ioctl_source_exists": ioctl_path.exists(),
        "acdbtap_source_exists": acdbtap_path.exists(),
        "helper_imports_init_v3": "extern int32_t acdb_loader_init_v3" in helper,
        "helper_calls_init_v3_open_audconf": 'A90_ACDB_FILES_PATH "/vendor/etc/audconf/OPEN"' in helper,
        "helper_does_not_arm_after_init": "a90_arm_capture()" not in helper,
        "helper_does_not_call_lower_after_init": "a90_run_lower_hidden_nodes()" not in helper,
        "helper_records_unexpected_init_return": "init_returned_unexpectedly_after_inhook_capture" in helper,
        "helper_does_not_import_common_topology": "acdb_loader_send_common_custom_topology" not in helper,
        "helper_does_not_import_send_audio_cal_v5": "acdb_loader_send_audio_cal_v5" not in helper,
        "preload_exports_common_skip_hook": "int32_t acdb_loader_send_common_custom_topology(void)" in preinit,
        "preload_imports_arm_capture": "extern void a90_arm_capture" in preinit,
        "preload_patches_initialized_flag": "A90_LOADER_INIT_FLAG_OFF" in preinit and "*flag = 1U" in preinit,
        "preload_arms_inside_common_hook": patch_pos >= 0 and arm_pos > patch_pos,
        "preload_runs_lower_inside_common_hook": arm_pos >= 0 and lower_pos > arm_pos,
        "preload_exits_after_inhook_lower": exit_pos > lower_pos and "a90_exit(0)" in preinit,
        "preload_exports_lower_runner": "int32_t a90_run_lower_hidden_nodes(void)" in preinit,
        "preload_uses_hidden_create_offset": "A90_CREATE_CAL_NODE_OFF 0x0000fd44UL" in preinit,
        "preload_uses_hidden_allocate_offset": "A90_ALLOCATE_CAL_BLOCK_OFF 0x0000fbbcUL" in preinit,
        "preload_targets_all_custom_cal_types": all(f"{{{cal}U," in preinit for cal in TARGET_CAL_TYPES),
        "preload_targets_pinned_get_commands": all(cmd in preinit for cmd in TARGET_GET_COMMANDS.values()),
        "preload_builds_32_byte_set_arg": "set_arg[0] = 32U" in preinit and "set_arg[3] = 16U" in preinit,
        "preload_sets_cal_type_size_and_mem_handle": "set_arg[2] = target->cal_type" in preinit and "set_arg[7] = (uint32_t)block->mem_handle" in preinit,
        "preload_calls_acdb_ioctl_get": "acdb_ioctl(target->get_cmd" in preinit,
        "preload_calls_fake_set_ioctl": "ioctl(-1, A90_AUDIO_SET_CALIBRATION, set_arg)" in preinit,
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
        "helper_opens_msm_audio_cal": "/dev/msm_audio_cal" in helper,
        "helper_issues_ioctl": "ioctl(" in helper or "A90_AUDIO_SET_CALIBRATION" in helper,
        "helper_calls_common_topology": "acdb_loader_send_common_custom_topology" in helper,
        "helper_calls_send_audio_cal_v5": "acdb_loader_send_audio_cal_v5" in helper,
        "preload_real_audio_set_syscall": "A90_NR_IOCTL" in preinit,
        "preload_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in preinit or "/dev/msm_audio_cal" in preinit,
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
        "v2674_contract": {
            "basis": "V2673 showed post-init helper continuation is unstable; run V2671 lower sequence inside the common hook instead",
            "hidden_offsets": {"create_cal_node": "base+0xfd45", "allocate_cal_block": "base+0xfbbd"},
            "targets": TARGET_GET_COMMANDS,
            "set_boundary": "AUDIO_SET_CALIBRATION is called only through the linked V2630 fake-set shim; no real kernel SET is allowed",
        },
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    with patched_v2659_constants():
        build_state = v2659.build(build_root, clang=clang, lld=lld, readelf=readelf, file_cmd=file_cmd)
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
            checks["no_helper_lower_runner_dependency"] = "a90_run_lower_hidden_nodes" not in helper_symbols
            checks["no_helper_arm_capture_dependency"] = "a90_arm_capture" not in helper_symbols
            checks["needed_libacdbloader"] = "Shared library: [libacdbloader.so]" in helper.get("dynamic", {}).get("stdout", "")
            helper["ok"] = bool(
                helper.get("exists")
                and checks["no_undefined_common_topology"]
                and checks["no_undefined_send_audio_cal_v5"]
                and checks["no_helper_lower_runner_dependency"]
                and checks["no_helper_arm_capture_dependency"]
                and checks["needed_libacdbloader"]
            )
    if isinstance(preload, dict):
        checks = preload.setdefault("checks", {})
        if isinstance(checks, dict):
            checks.pop("soname_v2668", None)
            checks.pop("soname_v2659", None)
            checks["soname_v2674"] = f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in preload_dynamic
            checks["exports_common_skip_hook"] = " acdb_loader_send_common_custom_topology" in preload_symbols
            checks["exports_lower_runner"] = " a90_run_lower_hidden_nodes" in preload_symbols
            checks["exports_acdb_ioctl"] = " acdb_ioctl" in preload_symbols
            checks["exports_ioctl"] = " ioctl" in preload_symbols
            checks["exports_a90_arm_capture"] = " a90_arm_capture" in preload_symbols
            preload["ok"] = bool(preload.get("exists") and all(checks.values()))
    build_state["ok"] = bool(helper.get("ok") and preload.get("ok"))
    return build_state


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state()
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
            "call_order": "acdb_loader_init_v3 -> init common skip hook -> patch initialized -> a90_arm_capture -> a90_run_lower_hidden_nodes -> exit_group(0)",
            "hidden_offsets": {"create_cal_node": "0x0000fd44|1", "allocate_cal_block": "0x0000fbbc|1"},
            "target_cal_types": TARGET_CAL_TYPES,
            "get_commands": TARGET_GET_COMMANDS,
            "set_capture": "generated 32-byte AUDIO_SET_CALIBRATION arg plus same-process dma-buf through V2630 fake SET shim",
            "success_discriminator": "future live run must capture fake SET rows for cal_types 24/10/14; no real SET pass-through permitted",
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
        "# NATIVE_INIT V2674 — ACDB lower hidden-node in-hook SET capture build",
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
        "V2673 reached the common hook, skipped the real common topology, resolved the",
        "loader base, and patched the initialized flag, but the helper then SIGSEGVed",
        "before it could arm capture and call the post-init lower runner. V2674 removes",
        "that unstable post-init continuation: the common hook itself arms capture, runs",
        "the lower hidden-node sequence, fake-captures generated SET args/dma-bufs",
        "through the V2630 shim, then exits the process.",
        "",
        "## Capture Contract",
        "",
        "- helper call order: `init_v3` only; returning from init is unexpected and logged.",
        "- preload common hook: skip real common, patch initialized flag, arm capture, run lower nodes, exit.",
        "- lower runner resolves libacdbloader base from `acdb_loader_is_initialized`.",
        "- lower runner calls `create_cal_node(base+0xfd45)` and `allocate_cal_block(base+0xfbbd)`.",
        "- lower runner targets cal_types `24`, `10`, and `14` with GET cmds `0x130da`, `0x11394`, and `0x12e01`.",
        "- lower runner calls `AUDIO_SET_CALIBRATION` only through the linked V2630 fake SET shim.",
        "",
        "## Boundary",
        "",
        "- no helper `/dev/msm_audio_cal` open and no helper ioctl",
        "- no real `AUDIO_SET_CALIBRATION` pass-through",
        "- no direct jump to `0x90ea`, `0x924a`, or `0x93f6` interior common blocks",
        "- no native replay, mixer, PCM, AudioTrack, speaker write, or persistent Magisk install",
        "- raw ACDB bytes remain private-only and are not committed",
        "",
        "## Build Evidence",
        "",
        f"- source_required_ok: `{payload.get('sources', {}).get('required_ok')}`",
        f"- source_prohibited_ok: `{payload.get('sources', {}).get('prohibited_ok')}`",
        f"- helper_compile_ok: `{build_state.get('compile', {}).get('helper', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- tap_compile_ok: `{build_state.get('compile', {}).get('acdbtap_v2600', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- ioctl_compile_ok: `{build_state.get('compile', {}).get('ioctl_trace', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- lower_preload_compile_ok: `{build_state.get('compile', {}).get('preinit_no_send', {}).get('ok') if isinstance(build_state, dict) else None}`",
        f"- helper_checks: `{helper.get('checks')}`",
        f"- preload_checks: `{preload.get('checks')}`",
        "",
        "## Next Unit",
        "",
        "A bounded Android-good live handoff can stage the V2674 helper/preload, force",
        "`A90_ACDB_FAKE_ALLOCATE=1`, pull `acdb-v2674-lower-hidden-inhook-events.jsonl`,",
        "`setcal-events.jsonl`, and private `setcal-*` raw files, then rollback to V2321.",
        "The live unit must classify any real kernel SET pass-through as a boundary violation.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674.py tests/test_build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674.py --build --write-report`",
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
