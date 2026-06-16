#!/usr/bin/env python3
"""Build V2561 ARM32 ACDB per-device capture with topology short-circuit.

Host-only unit.  It builds the V2559 helper plus a combined preload that exports
acdb_ioctl(), ioctl(), a90_arm_capture(), and a no-op
acdb_loader_send_common_custom_topology().  The short-circuit is intended to let
acdb_loader_init_v3() return after the already-pinned topology edge so the helper
can reach acdb_loader_send_audio_cal_v5().

No device action, no flash, no playback, and no raw payload is committed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_android_acdb_full_manifest_v2553 as v2553

base = v2553.base
linked = v2553.linked
ROOT = v2553.ROOT
RUN_ID = "V2561"
BUILD_TAG = "v2561-acdb-toposkip-per-device-capture-host-only"
HELPER_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_per_device_manifest_exec_linked_v2559.c"
TOPO_SKIP_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdb_topology_skip_v2561.c"
ACDBTAP_SOURCE_REL = v2553.ACDBTAP_SOURCE_REL
IOCTL_SOURCE_REL = v2553.IOCTL_SOURCE_REL
TOOLCHAIN_ROOT = v2553.TOOLCHAIN_ROOT
VENDOR_LIB_DIR = v2553.VENDOR_LIB_DIR
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
HELPER_ARTIFACT_NAME = "a90_acdb_per_device_manifest_exec_linked_v2561"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_toposkip_per_device_preload_v2561.so"
EXPECTED_TOPOLOGY_SHA256 = "7c5d45efa40944bc23dcc83af9f0046249499bb13d1a03c3470c287127992b89"
EXPECTED_TOPOLOGY_LEN = 4916
TARGET = v2553.TARGET
CFLAGS = v2553.CFLAGS
HELPER_LDFLAGS = v2553.HELPER_LDFLAGS
PRELOAD_LDFLAGS = (
    "-shared",
    "--allow-shlib-undefined",
    "-soname",
    PRELOAD_ARTIFACT_NAME,
)
PRELOAD_TAP_CFLAGS = v2553.PRELOAD_TAP_CFLAGS
LINK_LIBS = v2553.LINK_LIBS
REQUIRED_NEEDED = v2553.REQUIRED_NEEDED


def rel(path: Path) -> str:
    return base.rel(path)


def source_state() -> dict[str, Any]:
    helper_source = ROOT / HELPER_SOURCE_REL
    tap_source = ROOT / ACDBTAP_SOURCE_REL
    ioctl_source = ROOT / IOCTL_SOURCE_REL
    toposkip_source = ROOT / TOPO_SKIP_SOURCE_REL
    helper_text = helper_source.read_text(encoding="utf-8", errors="replace") if helper_source.exists() else ""
    tap_text = tap_source.read_text(encoding="utf-8", errors="replace") if tap_source.exists() else ""
    ioctl_text = ioctl_source.read_text(encoding="utf-8", errors="replace") if ioctl_source.exists() else ""
    toposkip_text = toposkip_source.read_text(encoding="utf-8", errors="replace") if toposkip_source.exists() else ""
    required = {
        "helper_source_exists": helper_source.exists(),
        "tap_source_exists": tap_source.exists(),
        "ioctl_source_exists": ioctl_source.exists(),
        "toposkip_source_exists": toposkip_source.exists(),
        "helper_custom_start": "void _start(void)" in helper_text,
        "helper_decl_init_v3": "extern int32_t acdb_loader_init_v3" in helper_text,
        "helper_decl_send_audio_cal_v5": "extern int32_t acdb_loader_send_audio_cal_v5" in helper_text,
        "helper_no_decl_common_topology": "acdb_loader_send_common_custom_topology" not in helper_text,
        "helper_calls_arm_capture": "a90_arm_capture();" in helper_text,
        "helper_skips_known_topology": "common_topology_skipped_known_payload" in helper_text,
        "helper_pins_topology_sha": EXPECTED_TOPOLOGY_SHA256 in helper_text,
        "helper_pins_topology_len": "A90_PINNED_TOPOLOGY_LEN 4916" in helper_text,
        "helper_calls_send_audio_cal_v5": "acdb_loader_send_audio_cal_v5(A90_SPEAKER_ACDB_ID" in helper_text,
        "helper_speaker_acdb_id_15": "A90_SPEAKER_ACDB_ID 15" in helper_text,
        "helper_app_type_69941": "A90_APP_TYPE_MEDIA 0x11135" in helper_text,
        "helper_rates_48000": "A90_SAMPLE_RATE_48K 48000" in helper_text and "A90_AFE_SAMPLE_RATE_48K 48000" in helper_text,
        "helper_private_event_path": "/data/local/tmp/a90-acdb-ownget/acdb-per-device-manifest-events.jsonl" in helper_text,
        "tap_exports_acdb_ioctl": "acdb_ioctl(uint32_t cmd" in tap_text,
        "tap_exports_arm_capture": "void a90_arm_capture(void)" in tap_text,
        "tap_post_initialize_auto_arm": "if (ret == 0 && cmd == A90_CMD_INITIALIZE_V2)" in tap_text and "a90_armed = 1;" in tap_text,
        "tap_unarmed_path_has_no_dump_before_real": "if (!a90_armed) {\n        ret = a90_real_acdb_ioctl(cmd, in, in_len, out, out_len);" in tap_text,
        "tap_no_exit_on_target_macro_available": "A90_ACDBTAP_EXIT_ON_TARGET" in tap_text,
        "tap_all_zero_guard": "a90_is_all_zero" in tap_text and "\\\"all_zero\\\":" in tap_text,
        "ioctl_exports_ioctl": "int ioctl(int fd, unsigned long request, ...)" in ioctl_text,
        "ioctl_fake_allocate_mode": "A90_ACDB_FAKE_ALLOCATE" in ioctl_text and "fake-success" in ioctl_text,
        "ioctl_fakes_audio_set_path": "A90_AUDIO_SET_CALIBRATION" in ioctl_text and "A90_AUDIO_ALLOCATE_CALIBRATION" in ioctl_text,
        "toposkip_exports_common_topology": "int32_t acdb_loader_send_common_custom_topology(void)" in toposkip_text,
        "toposkip_default_visibility": "__attribute__((visibility(\"default\"))) int32_t acdb_loader_send_common_custom_topology(void)" in toposkip_text,
        "toposkip_returns_success": "return 0;" in toposkip_text,
        "toposkip_logs_private_marker": "acdb-toposkip-events.jsonl" in toposkip_text,
        "toposkip_pins_topology_sha": EXPECTED_TOPOLOGY_SHA256 in toposkip_text,
    }
    prohibited = {
        "helper_calls_common_topology": "acdb_loader_send_common_custom_topology" in helper_text,
        "helper_opens_audio_cal_device": "open(\"/dev/msm_audio_cal" in helper_text or "open('/dev/msm_audio_cal" in helper_text,
        "helper_issues_ioctl": "ioctl(" in helper_text or "A90_NR_IOCTL" in helper_text,
        "helper_speaker_write": any(token in helper_text for token in ("tinyplay", "tinymix", "AudioTrack")),
        "helper_persistent_magisk": "magisk --install-module" in helper_text,
        "toposkip_calls_real_common_topology": "dlsym" in toposkip_text or "RTLD_NEXT" in toposkip_text,
        "tap_or_ioctl_speaker_write": any(token in (tap_text + ioctl_text + toposkip_text) for token in ("tinyplay", "tinymix", "AudioTrack")),
        "tap_or_ioctl_persistent_magisk": "magisk --install-module" in (tap_text + ioctl_text + toposkip_text),
    }
    return {
        "sources": [HELPER_SOURCE_REL, ACDBTAP_SOURCE_REL, IOCTL_SOURCE_REL, TOPO_SKIP_SOURCE_REL],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
    }


def binary_state(path: Path, *, readelf: str, file_cmd: str, kind: str) -> dict[str, Any]:
    state: dict[str, Any] = {"path": rel(path), "exists": path.exists(), "kind": kind}
    if not path.exists():
        state["ok"] = False
        return state
    symbols = base.run([readelf, "-Ws", str(path)], timeout=30.0)
    dynamic = base.run([readelf, "-d", str(path)], timeout=30.0)
    file_result = base.run([file_cmd, str(path)], timeout=30.0)
    state.update({
        "sha256": base.sha256_file(path),
        "size": path.stat().st_size,
        "mode": oct(path.stat().st_mode & 0o777),
        "file": file_result,
        "dynamic": {"readelf_ok": dynamic["ok"], "stdout": dynamic["stdout"]},
        "symbols": {"readelf_ok": symbols["ok"], "stdout": symbols["stdout"]},
    })
    if kind == "helper":
        sym = symbols["stdout"]
        dyn = dynamic["stdout"]
        header = base.run([readelf, "-h", str(path)], timeout=30.0)
        state["checks"] = {
            "is_pie": "DYN (Shared object file)" in header["stdout"],
            "undefined_init_v3": " UND acdb_loader_init_v3" in sym,
            "undefined_send_audio_cal_v5": " UND acdb_loader_send_audio_cal_v5" in sym,
            "undefined_arm_capture": " UND a90_arm_capture" in sym,
            "does_not_reference_common_topology": "acdb_loader_send_common_custom_topology" not in sym,
            "needed_libacdbloader": "Shared library: [libacdbloader.so]" in dyn,
            "needed_libaudcal": "Shared library: [libaudcal.so]" in dyn,
        }
    else:
        sym = symbols["stdout"]
        dyn = dynamic["stdout"]
        dynsym_lines = [
            line for line in sym.splitlines()
            if " acdb_loader_send_common_custom_topology" in line
        ]
        dynsym_exports_skip = any("GLOBAL" in line and "DEFAULT" in line for line in dynsym_lines)
        dynsym_hides_skip = any("LOCAL" in line or "HIDDEN" in line for line in dynsym_lines)
        state["checks"] = {
            "exports_acdb_ioctl": " acdb_ioctl" in sym,
            "exports_ioctl": " ioctl" in sym,
            "exports_a90_arm_capture": " a90_arm_capture" in sym,
            "exports_common_topology_skip": dynsym_exports_skip,
            "does_not_hide_common_topology_skip": not dynsym_hides_skip,
            "soname": f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in dyn,
        }
    state["ok"] = bool(state["file"].get("ok") and all(state["checks"].values()))
    return state


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    obj_dir = build_root / "obj"
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    obj_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    host_libraries = base.prepare_host_libraries(build_root)
    env = base.tool_env(host_libraries)

    helper_obj = obj_dir / "a90_acdb_per_device_manifest_exec_linked_v2559.o"
    tap_obj = obj_dir / "libacdbtap_v2475_noexit.o"
    ioctl_obj = obj_dir / "a90_ioctl_trace_preload_v2531.o"
    toposkip_obj = obj_dir / "libacdb_topology_skip_v2561.o"
    helper_out = bin_dir / HELPER_ARTIFACT_NAME
    preload_out = bin_dir / PRELOAD_ARTIFACT_NAME

    helper_compile = v2553.compile_object(ROOT / HELPER_SOURCE_REL, helper_obj, clang=clang, env=env, log_dir=log_dir)
    tap_compile = v2553.compile_object(ROOT / ACDBTAP_SOURCE_REL, tap_obj, clang=clang, env=env, log_dir=log_dir, extra=PRELOAD_TAP_CFLAGS)
    ioctl_compile = v2553.compile_object(ROOT / IOCTL_SOURCE_REL, ioctl_obj, clang=clang, env=env, log_dir=log_dir)
    toposkip_compile = v2553.compile_object(ROOT / TOPO_SKIP_SOURCE_REL, toposkip_obj, clang=clang, env=env, log_dir=log_dir)

    if helper_compile["ok"]:
        helper_link_cmd = [
            str(lld),
            *HELPER_LDFLAGS,
            "-L",
            str(VENDOR_LIB_DIR),
            "-o",
            str(helper_out),
            str(helper_obj),
            *LINK_LIBS,
        ]
        helper_link = base.run(helper_link_cmd, env=env)
        (log_dir / "helper.link.stdout.txt").write_text(helper_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "helper.link.stderr.txt").write_text(helper_link["stderr"], encoding="utf-8", errors="replace")
        helper_link = {k: v for k, v in helper_link.items() if k not in {"stdout", "stderr"}}
        if helper_link["ok"] and helper_out.exists():
            helper_out.chmod(0o600)
    else:
        helper_link = {"ok": False, "skipped": True, "reason": "helper compile failed"}

    if tap_compile["ok"] and ioctl_compile["ok"] and toposkip_compile["ok"]:
        preload_link_cmd = [str(lld), *PRELOAD_LDFLAGS, "-o", str(preload_out), str(tap_obj), str(ioctl_obj), str(toposkip_obj)]
        preload_link = base.run(preload_link_cmd, env=env)
        (log_dir / "preload.link.stdout.txt").write_text(preload_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "preload.link.stderr.txt").write_text(preload_link["stderr"], encoding="utf-8", errors="replace")
        preload_link = {k: v for k, v in preload_link.items() if k not in {"stdout", "stderr"}}
        if preload_link["ok"] and preload_out.exists():
            preload_out.chmod(0o600)
    else:
        preload_link = {"ok": False, "skipped": True, "reason": "preload compile failed"}

    helper = binary_state(helper_out, readelf=readelf, file_cmd=file_cmd, kind="helper")
    preload = binary_state(preload_out, readelf=readelf, file_cmd=file_cmd, kind="preload")

    return {
        "host_libraries": host_libraries,
        "compile": {"helper": helper_compile, "acdbtap_noexit": tap_compile, "ioctl_trace": ioctl_compile, "topology_skip": toposkip_compile},
        "link": {"helper": helper_link, "preload": preload_link},
        "logs": rel(log_dir),
        "helper": helper,
        "preload": preload,
        "ok": bool(
            helper_compile.get("ok")
            and tap_compile.get("ok")
            and ioctl_compile.get("ok")
            and toposkip_compile.get("ok")
            and helper_link.get("ok")
            and preload_link.get("ok")
            and helper.get("ok")
            and preload.get("ok")
        ),
    }


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    clang = Path(args.clang) if args.clang else TOOLCHAIN_ROOT / "bin/clang"
    lld = Path(args.lld) if args.lld else TOOLCHAIN_ROOT / "bin/ld.lld"
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": base.now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "android_action": "none",
        "operator_spec": "docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md",
        "source_state": source_state(),
        "vendor_lib_state": v2553.vendor_lib_state(args.readelf),
        "capture_contract": {
            "helper": HELPER_ARTIFACT_NAME,
            "preload": PRELOAD_ARTIFACT_NAME,
            "abi": "32-bit armeabi-v7a",
            "acdb_init_path": "/vendor/etc/audconf/OPEN",
            "pinned_topology_len": EXPECTED_TOPOLOGY_LEN,
            "pinned_topology_sha256": EXPECTED_TOPOLOGY_SHA256,
            "common_topology_call": "preload short-circuits acdb_loader_send_common_custom_topology to return 0 before real tail",
            "per_device_call": "acdb_loader_send_audio_cal_v5(15, 0, 0x11135, 48000, 48000, 0, 1)",
            "preload_policy": "silent post-INITIALIZE_V2 auto-arm plus helper manual-arm, common-topology short-circuit, no exit on 4916, fake audio calibration ioctls when A90_ACDB_FAKE_ALLOCATE=1",
            "raw_output_private_only": True,
        },
        "boundaries": {
            "host_only_build": True,
            "no_live_device_action": True,
            "helper_does_not_call_common_topology": True,
            "helper_does_not_issue_ioctl": True,
            "preload_fakes_audio_set_path": True,
            "no_native_speaker_write": True,
        },
        "toolchain": {
            "clang": str(clang),
            "lld": str(lld),
            "readelf": args.readelf,
            "file": args.file,
            "target": TARGET,
            "cflags": [*CFLAGS],
            "preload_tap_cflags": [*PRELOAD_TAP_CFLAGS],
        },
        "build_root": rel(args.build_root),
    }
    if args.build:
        payload["build"] = build(args.build_root, clang=clang, lld=lld, readelf=args.readelf, file_cmd=args.file)
    else:
        payload["build"] = {"built": False, "reason": "pass --build to materialize private ARM32 artifacts"}
    loader_symbols = payload["vendor_lib_state"].get("libacdbloader_symbols", {})
    payload["ok"] = bool(
        payload["source_state"]["required_ok"]
        and payload["source_state"]["prohibited_ok"]
        and payload["vendor_lib_state"].get("all_required_present")
        and loader_symbols.get("has_acdb_loader_init_v3")
        and loader_symbols.get("has_acdb_loader_send_audio_cal_v5")
        and payload.get("build", {}).get("ok", True)
    )
    payload["manifest_path"] = rel(args.manifest_path)
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--clang", type=Path, default=TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    payload = manifest(parse_args(argv))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
