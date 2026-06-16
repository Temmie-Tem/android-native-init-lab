#!/usr/bin/env python3
"""Build V2608 ARM32 ACDB post-init send_audio_cal_v5 combined preload.

Host-only build-only unit after V2607.  V2607 localized the V2604 timeout to a
likely init-time loader mutex window: the preinit hook called
send_audio_cal_v5() from inside the common-topology call reached during
acdb_loader_init_v3().

This build changes the split:

- the preload still combines V2600 acdbtap and the V2531 fake audio-cal ioctl
  shim, but replaces the V2572 sender hook with a no-send common-topology hook;
- the helper calls acdb_loader_init_v3(), arms capture only after init returns,
  and then calls send_audio_cal_v5() outside the init-time hook.

No Android handoff, ACDB execution, native replay SET, speaker write, or raw
payload publication happens in this build unit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_android_acdb_indirect_buffer_tap_v2600 as v2600
import build_android_acdb_perdevice_indirect_capture_v2572 as v2572
import build_android_acdb_v2600_perdevice_combined_preload_v2603 as v2603
import build_android_acdb_combined_preload_v2538 as preload_base

ROOT = v2572.ROOT
RUN_ID = "V2608"
BUILD_TAG = "v2608-acdb-postinit-send-v5-combined-preload-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2608_AUDIO_ACDB_POSTINIT_SEND_V5_COMBINED_PRELOAD_BUILD_2026-06-16.md"

HELPER_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_acdb_postinit_send_v5_exec_linked_v2608.c"
PREINIT_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdb_preinit_no_send_v2608.c"
HELPER_ARTIFACT_NAME = "a90_acdb_postinit_send_v5_exec_linked_v2608"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_postinit_send_v5_combined_preload_v2608.so"
PRELOAD_LDFLAGS = ("-shared", "--allow-shlib-undefined", "-soname", PRELOAD_ARTIFACT_NAME)


def rel(path: Path | str) -> str:
    return v2572.rel(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def source_state() -> dict[str, Any]:
    helper_path = ROOT / HELPER_SOURCE_REL
    preinit_path = ROOT / PREINIT_SOURCE_REL
    tap_path = ROOT / v2600.ACDBTAP_SOURCE_REL
    ioctl_path = ROOT / v2572.IOCTL_SOURCE_REL
    helper = _read(helper_path)
    preinit = _read(preinit_path)
    tap = _read(tap_path)
    ioctl = _read(ioctl_path)
    combined = "\n".join([helper, preinit, tap, ioctl])

    init_pos = helper.find("init_ret = acdb_loader_init_v3")
    arm_pos = helper.find("a90_arm_capture()")
    send_pos = helper.find("cal_ret = acdb_loader_send_audio_cal_v5")
    preinit_patch_pos = preinit.find("patch_initialized_flag_return")
    preinit_return_pos = preinit.find("return_to_init_v3_no_arm_no_send")

    required = {
        "helper_source_exists": helper_path.exists(),
        "preinit_source_exists": preinit_path.exists(),
        "tap_source_exists": tap_path.exists(),
        "ioctl_source_exists": ioctl_path.exists(),
        "helper_calls_init_v3": "acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U)" in helper,
        "helper_arms_after_init_before_send": init_pos >= 0 and arm_pos > init_pos and send_pos > arm_pos,
        "helper_calls_send_v5_postinit": "acdb_loader_send_audio_cal_v5(A90_SPEAKER_ACDB_ID" in helper,
        "helper_uses_rx_capmask_fixed_order": (
            "#define A90_SPEAKER_RX_PATH 1" in helper
            and "A90_SESSION_TYPE_DEFAULT" in helper
            and "A90_AFE_SAMPLE_RATE_48K" in helper
        ),
        "preinit_exports_common_topology": "int32_t acdb_loader_send_common_custom_topology(void)" in preinit,
        "preinit_skips_real_common_topology_by_default": (
            "#define A90_V2608_CALL_REAL_COMMON_TOPOLOGY 0" in preinit
            and "skip_real_common_topology" in preinit
        ),
        "preinit_patches_init_flag": "A90_LOADER_INIT_FLAG_OFF" in preinit and "*flag = 1U" in preinit,
        "preinit_returns_after_patch": preinit_patch_pos >= 0 and preinit_return_pos > preinit_patch_pos,
        "tap_unarmed_real_only_path": "if (!a90_armed)" in tap and "return ret;" in tap,
        "tap_manual_arm_exported": "void a90_arm_capture(void)" in tap,
        "ioctl_fake_allocate_env": "A90_ACDB_FAKE_ALLOCATE" in ioctl,
        "ioctl_fakes_set_in_fake_mode": "A90_AUDIO_SET_CALIBRATION" in ioctl and "fake-success" in ioctl,
    }
    prohibited = {
        "preinit_calls_send_audio_cal_v5": "a90_real_send_audio_cal_v5" in preinit,
        "preinit_arms_capture": "a90_arm_capture" in preinit,
        "preinit_exits_process": "exit_group" in preinit or "A90_NR_EXIT_GROUP" in preinit,
        "combined_global_pthread_hooks": "pthread_mutex_lock" in combined or "pthread_mutex_unlock" in combined,
        "combined_android_log_hook": "__android_log_print" in combined,
        "native_speaker_write": any(token in combined for token in ("tinyplay", "tinymix", "AudioTrack")),
        "persistent_magisk_install": "magisk --install-module" in combined,
    }
    return {
        "sources": [
            HELPER_SOURCE_REL,
            v2600.ACDBTAP_SOURCE_REL,
            v2572.IOCTL_SOURCE_REL,
            PREINIT_SOURCE_REL,
        ],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
        "v2608_delta": {
            "reason": "Move send_audio_cal_v5 out of the init-time common-topology hook/mutex window",
            "preinit_event_path": "/data/local/tmp/a90-acdb-ownget/acdb-v2608-preinit-no-send-events.jsonl",
            "helper_event_path": "/data/local/tmp/a90-acdb-ownget/acdb-v2608-postinit-send-v5-events.jsonl",
            "tap_event_path": "/data/local/tmp/a90-acdb-tap/acdbtap-events.jsonl",
            "preinit_policy": "skip common topology, patch initialized flag, return to init_v3 without arm/send/exit",
            "postinit_policy": "init_v3 return -> a90_arm_capture -> send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
        },
    }


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    obj_dir = build_root / "obj"
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    obj_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    missing = [name for name in v2572.REQUIRED_NEEDED if not (v2572.VENDOR_LIB_DIR / name).exists()]
    if missing:
        return {"ok": False, "error": f"missing private ACDB closure libs: {', '.join(missing)}"}

    host_libraries = preload_base.prepare_host_libraries(build_root)
    env = preload_base.tool_env(host_libraries)

    helper_obj = obj_dir / "a90_acdb_postinit_send_v5_exec_linked_v2608.o"
    tap_obj = obj_dir / "libacdbtap_v2475_v2600.o"
    ioctl_obj = obj_dir / "a90_ioctl_trace_preload_v2531.o"
    preinit_obj = obj_dir / "libacdb_preinit_no_send_v2608.o"
    helper_out = bin_dir / HELPER_ARTIFACT_NAME
    preload_out = bin_dir / PRELOAD_ARTIFACT_NAME

    helper_compile = v2572.compile_object(ROOT / HELPER_SOURCE_REL, helper_obj, clang=clang, env=env, log_dir=log_dir, cflags=v2572.HELPER_CFLAGS)
    tap_compile = v2572.compile_object(ROOT / v2600.ACDBTAP_SOURCE_REL, tap_obj, clang=clang, env=env, log_dir=log_dir, cflags=v2600.COMMON_CFLAGS, extra=v2600.TAP_EXTRA_CFLAGS)
    ioctl_compile = v2572.compile_object(ROOT / v2572.IOCTL_SOURCE_REL, ioctl_obj, clang=clang, env=env, log_dir=log_dir, cflags=v2572.PRELOAD_CFLAGS)
    preinit_compile = v2572.compile_object(ROOT / PREINIT_SOURCE_REL, preinit_obj, clang=clang, env=env, log_dir=log_dir, cflags=v2572.PRELOAD_CFLAGS)

    if helper_compile["ok"]:
        helper_link = preload_base.run([str(lld), *v2572.HELPER_LDFLAGS, "-L", str(v2572.VENDOR_LIB_DIR), "-o", str(helper_out), str(helper_obj), *v2572.LINK_LIBS], env=env)
        (log_dir / "helper.link.stdout.txt").write_text(helper_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "helper.link.stderr.txt").write_text(helper_link["stderr"], encoding="utf-8", errors="replace")
        helper_link = {k: value for k, value in helper_link.items() if k not in {"stdout", "stderr"}}
        if helper_link["ok"] and helper_out.exists():
            helper_out.chmod(0o600)
    else:
        helper_link = {"ok": False, "skipped": True, "reason": "helper compile failed"}

    preload_compile_ok = all(item["ok"] for item in [tap_compile, ioctl_compile, preinit_compile])
    if preload_compile_ok:
        preload_link = preload_base.run([str(lld), *PRELOAD_LDFLAGS, "-o", str(preload_out), str(tap_obj), str(ioctl_obj), str(preinit_obj)], env=env)
        (log_dir / "preload.link.stdout.txt").write_text(preload_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "preload.link.stderr.txt").write_text(preload_link["stderr"], encoding="utf-8", errors="replace")
        preload_link = {k: value for k, value in preload_link.items() if k not in {"stdout", "stderr"}}
        if preload_link["ok"] and preload_out.exists():
            preload_out.chmod(0o600)
    else:
        preload_link = {"ok": False, "skipped": True, "reason": "preload compile failed"}

    helper_state = v2603.binary_state(helper_out, readelf=readelf, file_cmd=file_cmd, kind="helper")
    preload_state = v2603.binary_state(preload_out, readelf=readelf, file_cmd=file_cmd, kind="preload")
    helper_sym = helper_state.get("symbols", {}).get("stdout", "")
    preload_sym = preload_state.get("symbols", {}).get("stdout", "")
    preload_dyn = preload_state.get("dynamic", {}).get("stdout", "")

    helper_checks = helper_state.setdefault("checks", {})
    helper_checks.update(
        {
            "undefined_send_audio_cal_v5": " UND acdb_loader_send_audio_cal_v5" in helper_sym,
            "undefined_or_weak_a90_arm_capture": " a90_arm_capture" in helper_sym,
        }
    )
    helper_state["ok"] = bool(helper_state.get("file", {}).get("ok") and all(helper_checks.values()))

    preload_checks = preload_state.setdefault("checks", {})
    preload_checks.pop("soname_v2603", None)
    preload_checks.update(
        {
            "soname_v2608": f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in preload_dyn,
            "does_not_export_pthread_mutex_lock": " pthread_mutex_lock" not in preload_sym,
            "does_not_export_pthread_mutex_unlock": " pthread_mutex_unlock" not in preload_sym,
            "does_not_export_android_log_print": " __android_log_print" not in preload_sym,
        }
    )
    preload_state["ok"] = bool(preload_state.get("file", {}).get("ok") and all(preload_checks.values()))

    return {
        "host_libraries": host_libraries,
        "compile": {
            "helper": helper_compile,
            "acdbtap_v2600": tap_compile,
            "ioctl_trace": ioctl_compile,
            "preinit_no_send": preinit_compile,
        },
        "link": {"helper": helper_link, "preload": preload_link},
        "artifacts": {"helper": helper_state, "preload": preload_state},
        "ok": bool(helper_state.get("ok") and preload_state.get("ok")),
    }


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state()
    vendor = v2572.vendor_lib_state(args.readelf)
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
            "base": "V2600 acdbtap + V2531 fake audio-cal ioctl shim",
            "preinit": "skip common topology, patch initialized flag, return to acdb_loader_init_v3 without arm/send/exit",
            "postinit": "helper arms capture after init_v3 returns, then calls send_audio_cal_v5",
            "per_device_call": "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
            "success_discriminator": "future live ACDB captures require ret==0 plus non-all-zero buffers",
            "expected_discriminator": "if init_v3 returns and send_v5 now emits acdbtap rows, V2604 was init-time self-deadlock; if init still crashes before return, direct pure-read getters remain the fallback",
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
    preinit_compile = build.get("compile", {}).get("preinit_no_send", {}) if isinstance(build, dict) else {}
    helper_compile = build.get("compile", {}).get("helper", {}) if isinstance(build, dict) else {}
    lines = [
        "# NATIVE_INIT V2608 — ACDB post-init send_audio_cal_v5 combined preload build",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only build-only unit after V2607. No Android handoff, device flash, native replay SET,",
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
        "V2604 reached `before_send_audio_cal_v5` from the V2603 preinit hook and then timed out",
        "without any armed `acdb_ioctl` rows. V2607 static RE showed `send_audio_cal_v5` begins with",
        "the loader mutex before the initialized gate, making a self-deadlock plausible when called",
        "from inside the init-time common-topology hook. V2605 global imported-call tracing regressed",
        "with a linker-recursion SIGSEGV, so V2608 removes that unsafe tracing path and instead moves",
        "`send_audio_cal_v5` into the helper after `acdb_loader_init_v3` returns.",
        "",
        "## Contract",
        "",
        "- preload keeps V2600 acdbtap and V2531 fake allocate/deallocate/SET behavior.",
        "- preinit hook skips real common-topology by default, patches the initialized flag, and returns to init.",
        "- preinit hook does not call `a90_arm_capture`, does not call `send_audio_cal_v5`, and does not exit.",
        "- helper calls `a90_arm_capture()` only after `acdb_loader_init_v3` returns `0`.",
        "- helper then calls `acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)`.",
        "- future live success remains `ret==0` plus non-all-zero ACDB buffers; requested length alone is failure.",
        "",
        "## Build Evidence",
        "",
        f"- helper_compile_ok: `{helper_compile.get('ok')}`",
        f"- preinit_compile_ok: `{preinit_compile.get('ok')}`",
        f"- helper_checks: `{helper.get('checks')}`",
        f"- preload_checks: `{preload.get('checks')}`",
        "",
        "## Next Unit",
        "",
        "Use the existing Android-good own-process runner with the V2608 helper/preload override.",
        "If `init_v3_return` appears and `send_audio_cal_v5` emits acdbtap rows, V2604 was the",
        "init-time call-site problem. If init never returns or still crashes before the helper can arm,",
        "stop this route and continue the direct pure-read getter fallback rather than reintroducing",
        "global pthread/log interposition.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_postinit_send_v5_combined_preload_v2608.py tests/test_build_android_acdb_postinit_send_v5_combined_preload_v2608.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_postinit_send_v5_combined_preload_v2608 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_postinit_send_v5_combined_preload_v2608.py --build --write-report`",
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
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
