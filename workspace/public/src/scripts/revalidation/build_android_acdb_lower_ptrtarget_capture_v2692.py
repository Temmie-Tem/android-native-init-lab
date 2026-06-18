#!/usr/bin/env python3
"""Build V2692 ACDB lower custom-topology pointer-target capture artifacts.

Host-only build unit. V2691 showed that the useful missing evidence is the
same-process memory behind the lower hidden-node GET tuple's pointer-like
``in_word1`` value. V2692 therefore keeps the V2674 in-hook lower-node path, but
adds:

* lower block metadata snapshots at the hidden-node call site; and
* an ACDB tap that maps-verifies and privately dumps the in_word1 pointee for
  lower custom-topology GET commands before the real acdb_ioctl call.

No Android handoff, device flash, real audio SET, native replay, mixer, PCM, or
speaker write happens in this build unit.
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

import build_android_acdb_lower_hidden_node_inhook_setcal_capture_v2674 as v2674


ROOT = v2674.ROOT
RUN_ID = "V2692"
BUILD_TAG = "v2692-acdb-lower-ptrtarget-capture-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2692_AUDIO_ACDB_LOWER_PTRTARGET_CAPTURE_BUILD_2026-06-18.md"

HELPER_SOURCE_REL = v2674.HELPER_SOURCE_REL
PREINIT_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdb_lower_hidden_node_ptrtarget_inhook_v2692.c"
ACDBTAP_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdbtap_lower_ptrtarget_v2692.c"
HELPER_ARTIFACT_NAME = "a90_acdb_lower_ptrtarget_capture_exec_linked_v2692"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_lower_ptrtarget_capture_combined_preload_v2692.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)
TARGET_CAL_TYPES = v2674.TARGET_CAL_TYPES
TARGET_GET_COMMANDS = v2674.TARGET_GET_COMMANDS | {25: "0x000130dc"}


def rel(path: Path | str) -> str:
    return v2674.rel(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


@contextlib.contextmanager
def patched_v2674_constants() -> Iterator[None]:
    v2630 = v2674.v2659.v2630
    v2613 = v2630.v2613
    old = {
        "v2674_helper_source": v2674.HELPER_SOURCE_REL,
        "v2674_preinit_source": v2674.PREINIT_SOURCE_REL,
        "v2674_helper_artifact": v2674.HELPER_ARTIFACT_NAME,
        "v2674_preload_artifact": v2674.PRELOAD_ARTIFACT_NAME,
        "v2674_preload_ldflags": v2674.PRELOAD_LDFLAGS,
        "v2659_helper_source": v2674.v2659.HELPER_SOURCE_REL,
        "v2659_preinit_source": v2674.v2659.PREINIT_SOURCE_REL,
        "v2630_acdbtap_source": v2630.ACDBTAP_SOURCE_REL,
        "v2613_acdbtap_source": v2613.ACDBTAP_SOURCE_REL,
    }
    v2674.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2674.PREINIT_SOURCE_REL = PREINIT_SOURCE_REL
    v2674.HELPER_ARTIFACT_NAME = HELPER_ARTIFACT_NAME
    v2674.PRELOAD_ARTIFACT_NAME = PRELOAD_ARTIFACT_NAME
    v2674.PRELOAD_LDFLAGS = PRELOAD_LDFLAGS
    v2674.v2659.HELPER_SOURCE_REL = HELPER_SOURCE_REL
    v2674.v2659.PREINIT_SOURCE_REL = PREINIT_SOURCE_REL
    v2630.ACDBTAP_SOURCE_REL = ACDBTAP_SOURCE_REL
    v2613.ACDBTAP_SOURCE_REL = ACDBTAP_SOURCE_REL
    try:
        yield
    finally:
        v2674.HELPER_SOURCE_REL = old["v2674_helper_source"]
        v2674.PREINIT_SOURCE_REL = old["v2674_preinit_source"]
        v2674.HELPER_ARTIFACT_NAME = old["v2674_helper_artifact"]
        v2674.PRELOAD_ARTIFACT_NAME = old["v2674_preload_artifact"]
        v2674.PRELOAD_LDFLAGS = old["v2674_preload_ldflags"]
        v2674.v2659.HELPER_SOURCE_REL = old["v2659_helper_source"]
        v2674.v2659.PREINIT_SOURCE_REL = old["v2659_preinit_source"]
        v2630.ACDBTAP_SOURCE_REL = old["v2630_acdbtap_source"]
        v2613.ACDBTAP_SOURCE_REL = old["v2613_acdbtap_source"]


def source_state() -> dict[str, Any]:
    helper_path = ROOT / HELPER_SOURCE_REL
    preinit_path = ROOT / PREINIT_SOURCE_REL
    tap_path = ROOT / ACDBTAP_SOURCE_REL
    ioctl_path = ROOT / v2674.v2659.v2630.IOCTL_SOURCE_REL
    helper = _read(helper_path)
    preinit = _read(preinit_path)
    tap = _read(tap_path)
    ioctl = _read(ioctl_path)
    combined = "\n".join([helper, preinit, tap, ioctl])
    snapshot_call_pos = preinit.find("a90_write_block_snapshot(target->cal_type")
    get_in_pos = preinit.find("get_in[0] = block->get_arg0")
    ptrtarget_call_pos = tap.find("(void)a90_log_lower_custom_ptrtarget_pre")
    real_ioctl_pos = tap.find("ret = a90_real_acdb_ioctl", ptrtarget_call_pos)

    base = v2674.source_state()
    required = {
        "base_v2674_required_ok": bool(base.get("required_ok")),
        "base_v2674_prohibited_ok": bool(base.get("prohibited_ok")),
        "helper_source_exists": helper_path.exists(),
        "preinit_source_exists": preinit_path.exists(),
        "tap_source_exists": tap_path.exists(),
        "ioctl_source_exists": ioctl_path.exists(),
        "preinit_writes_block_snapshot": "v2692_lower_block_snapshot" in preinit,
        "preinit_snapshot_fields": all(
            token in preinit
            for token in [
                "node_word0",
                "node_word4",
                "get_arg0",
                "get_arg1",
                "mem_handle",
                "word16",
                "word20",
            ]
        ),
        "preinit_snapshot_before_get": snapshot_call_pos >= 0 and get_in_pos > snapshot_call_pos,
        "preinit_keeps_v2674_inhook_exit": "exit_after_inhook_lower_hidden_nodes" in preinit and "a90_exit(0)" in preinit,
        "tap_declares_lower_custom_cmds": all(cmd in tap for cmd in ["0x000130da", "0x00011394", "0x00012e01", "0x000130dc"]),
        "tap_reads_proc_self_maps": "/proc/self/maps" in tap and "A90_NR_READ" in tap,
        "tap_maps_verifies_before_copy": "a90_maps_range_readable(ptr, dump_len" in tap,
        "tap_logs_ptrtarget_status": "ptrtarget_status" in tap and "ptrtarget_unmapped" in tap and "ptrtarget_maps_verified" in tap,
        "tap_dumps_ptrtarget_pre": "ptrtarget-pre" in tap and "a90_log_lower_custom_ptrtarget_pre" in tap,
        "tap_ptrtarget_before_real_ioctl": ptrtarget_call_pos >= 0 and real_ioctl_pos > ptrtarget_call_pos,
        "tap_keeps_sha256_raw_capture": "a90_sha256_update(&sha, buf, buf_len)" in tap and "raw_path" in tap,
        "tap_caps_ptrtarget_window": "A90_PTRTARGET_MAX_BYTES 4096U" in tap,
        "tap_retains_existing_indirect_layouts": "A90_CMD_AUDPROC_INSTANCE_COMMON_TABLE" in tap and "a90_log_command_layout_indirect_captures" in tap,
        "ioctl_still_fakes_audio_set": (
            "always fake AUDIO_SET_CALIBRATION" in ioctl
            and "if (request == A90_AUDIO_SET_CALIBRATION)\n        return 1;" in ioctl
        ),
    }
    prohibited = {
        "helper_opens_msm_audio_cal": "/dev/msm_audio_cal" in helper,
        "preinit_opens_msm_audio_cal": "/dev/msm_audio_cal" in preinit,
        "tap_opens_msm_audio_cal": "/dev/msm_audio_cal" in tap,
        "combined_native_speaker_write": any(token in combined for token in ("tinyplay", "tinymix", "AudioTrack")),
        "combined_persistent_magisk_install": "magisk --install-module" in combined,
        "combined_global_pthread_hooks": "pthread_mutex_lock" in combined or "pthread_mutex_unlock" in combined,
        "combined_android_log_hook": "__android_log_print" in combined,
    }
    return {
        "sources": [HELPER_SOURCE_REL, PREINIT_SOURCE_REL, ACDBTAP_SOURCE_REL, v2674.v2659.v2630.IOCTL_SOURCE_REL],
        "base_v2674": base,
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
        "v2692_delta": {
            "basis": "V2691 identified the same-process in_word1 pointee as the missing ACDB selector evidence",
            "block_snapshot": "emit v2692_lower_block_snapshot before each lower GET",
            "ptrtarget": "maps-verify in_word1 and dump ptrtarget-pre raw bytes privately before real acdb_ioctl",
            "privacy": "commit only metadata; raw pointer-target bytes remain under workspace/private after a live run",
        },
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    with patched_v2674_constants():
        build_state = v2674.build(build_root, clang=clang, lld=lld, readelf=readelf, file_cmd=file_cmd)
    artifacts = build_state.get("artifacts", {}) if isinstance(build_state, dict) else {}
    preload = artifacts.get("preload", {}) if isinstance(artifacts, dict) else {}
    helper = artifacts.get("helper", {}) if isinstance(artifacts, dict) else {}
    preload_symbols = preload.get("symbols", {}).get("stdout", "") if isinstance(preload, dict) else ""
    preload_dynamic = preload.get("dynamic", {}).get("stdout", "") if isinstance(preload, dict) else ""

    if isinstance(preload, dict):
        checks = preload.setdefault("checks", {})
        if isinstance(checks, dict):
            checks.pop("soname_v2674", None)
            checks["soname_v2692"] = f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in preload_dynamic
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
    vendor = v2674.v2659.v2630.v2613.v2611.v2608.v2572.vendor_lib_state(args.readelf)
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
            "call_order": "acdb_loader_init_v3 -> init common skip hook -> patch initialized -> a90_arm_capture -> a90_run_lower_hidden_nodes -> ptrtarget-pre -> fake SET -> exit_group(0)",
            "target_cal_types": TARGET_CAL_TYPES,
            "get_commands": TARGET_GET_COMMANDS,
            "block_snapshot": "v2692_lower_block_snapshot rows record node/block/get_arg/mem_handle metadata",
            "ptrtarget": "lower custom GET in_word1 is maps-verified and dumped as ptrtarget-pre privately before real acdb_ioctl",
            "success_discriminator": "future live run must produce block snapshots and either ptrtarget-pre raw files or ptrtarget_unmapped rows for cal_types 24/10/14",
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
        "# NATIVE_INIT V2692 — ACDB lower pointer-target capture build",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only build-only unit. No Android handoff, device flash, real",
        "`AUDIO_SET_CALIBRATION`, native replay, mixer write, PCM write, speaker",
        "playback, or raw ACDB payload publication occurred. Private build artifacts",
        "stay under `workspace/private`.",
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
        "V2690/V2691 showed that replay synthesis is exhausted and the missing useful",
        "evidence is the same-process memory behind the lower hidden-node GET tuple's",
        "`in_word1`. V2692 preserves the V2674 in-hook lower-node route but adds block",
        "snapshots and maps-verified `ptrtarget-pre` raw dumps before the real GET.",
        "",
        "## Capture Contract",
        "",
        "- block metadata: `v2692_lower_block_snapshot` rows before each lower GET",
        "- pointer metadata: `ptrtarget_status` rows for `0x130da`, `0x11394`, `0x12e01`, and `0x130dc`",
        "- pointer raw: private `ptrtarget-pre` raw files capped at 4096 bytes after `/proc/self/maps` coverage check",
        "- privacy: public report may include size/SHA/marker offsets only; raw bytes remain private",
        "- boundary: V2630 fake SET remains active; no real SET, PCM, route, or speaker write",
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
        "A future live Android-good handoff may stage the V2692 helper/preload through",
        "the existing V2675 engine, keep `A90_ACDB_FAKE_ALLOCATE=1`, pull the full",
        "`acdbtap` and lower-block private artifacts, roll back to V2321, and report",
        "only hashes/lengths/marker offsets for the pointer-target windows.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_lower_ptrtarget_capture_v2692.py tests/test_build_android_acdb_lower_ptrtarget_capture_v2692.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_lower_ptrtarget_capture_v2692 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_lower_ptrtarget_capture_v2692.py --build --write-report`",
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
    parser.add_argument("--clang", type=Path, default=v2674.v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=v2674.v2659.v2630.v2613.v2611.v2608.v2572.TOOLCHAIN_ROOT / "bin/ld.lld")
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
