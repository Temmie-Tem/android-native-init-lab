#!/usr/bin/env python3
"""Build V2603 ARM32 ACDB per-device combined preload.

Host-only unit after V2602. V2602 proved that passing the V2600 tap-only
artifact as an override preload omits the preinit hook, so capture never arms
and `send_audio_cal_v5()` is never driven. This build produces the missing
single combined preload:

- V2600 tap behavior: manual post-init arm, full in_buf dump, bounded indirect
  {length,pointer} candidate capture;
- V2531 ioctl shim: fake AUDIO_ALLOCATE/DEALLOCATE/SET while
  A90_ACDB_FAKE_ALLOCATE=1;
- V2572 preinit per-device hook, compiled with the V2591 RX cap-mask and fixed
  stack-order overrides.

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
import build_android_acdb_perdevice_rx_capmask_argorder_v2591 as v2591
import build_android_acdb_combined_preload_v2538 as preload_base

ROOT = v2572.ROOT
RUN_ID = "V2603"
BUILD_TAG = "v2603-acdb-v2600-perdevice-combined-preload-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2603_AUDIO_ACDB_V2600_PERDEVICE_COMBINED_PRELOAD_BUILD_2026-06-16.md"

HELPER_ARTIFACT_NAME = "a90_acdb_perdevice_rx_capmask_argorder_exec_linked_v2603"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_v2600_perdevice_combined_preload_v2603.so"
PRELOAD_LDFLAGS = (
    "-shared",
    "--allow-shlib-undefined",
    "-soname",
    PRELOAD_ARTIFACT_NAME,
)


def rel(path: Path | str) -> str:
    return v2572.rel(path)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def source_state() -> dict[str, Any]:
    base = v2591.source_state()
    tap2600 = v2600.source_state()
    tap_path = ROOT / v2600.ACDBTAP_SOURCE_REL
    preinit_path = ROOT / v2572.PREINIT_SOURCE_REL
    tap_text = _read(tap_path)
    preinit_text = _read(preinit_path)

    required = dict(base.get("required", {}))
    required.update(
        {
            "v2600_tap_source_selected": v2600.ACDBTAP_SOURCE_REL.endswith("libacdbtap_v2475.c"),
            "v2600_tap_required_ok": tap2600.get("required_ok"),
            "v2600_tap_prohibited_ok": tap2600.get("prohibited_ok"),
            "v2600_tap_capture_inbuf_macro": "A90_ACDBTAP_CAPTURE_INBUF" in tap_text,
            "v2600_tap_capture_indirect_macro": "A90_ACDBTAP_CAPTURE_INDIRECT_CANDIDATES" in tap_text,
            "v2600_tap_kind_raw_paths": "a90_build_raw_path_kind" in tap_text,
            "v2600_tap_default_auto_arm_off": "#define A90_ACDBTAP_AUTO_ARM_ON_INITIALIZE 0" in tap_text,
            "preinit_calls_a90_arm_capture": "a90_arm_capture" in preinit_text,
            "preinit_calls_send_audio_cal_v5": "a90_real_send_audio_cal_v5" in preinit_text,
            "compile_override_capmask": v2591.CAP_MASK_CFLAG == "-DA90_SPEAKER_RX_PATH=1",
            "compile_override_fixed_order": v2591.ARG_ORDER_CFLAG == "-DA90_SEND_AUDIO_CAL_V5_FIXED_STACK_ORDER=1",
        }
    )

    prohibited = dict(base.get("prohibited", {}))
    prohibited.update(
        {
            "tap_opens_msm_audio_cal": "/dev/msm_audio_cal" in tap_text,
            "tap_or_preinit_speaker_write": any(token in (tap_text + preinit_text) for token in ("tinyplay", "tinymix", "AudioTrack")),
        }
    )

    return {
        "sources": [
            v2572.HELPER_SOURCE_REL,
            v2600.ACDBTAP_SOURCE_REL,
            v2572.IOCTL_SOURCE_REL,
            v2572.PREINIT_SOURCE_REL,
        ],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
        "v2603_delta": {
            "reason": "V2602 used V2600 tap-only as override preload; this combines V2600 tap with the V2572/V2591 preinit sender hook",
            "tap_extra_cflags": list(v2600.TAP_EXTRA_CFLAGS),
            "preinit_extra_cflags": [v2591.CAP_MASK_CFLAG, v2591.ARG_ORDER_CFLAG],
            "send_audio_cal_v5_call": "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
        },
    }


def binary_state(path: Path, *, readelf: str, file_cmd: str, kind: str) -> dict[str, Any]:
    state: dict[str, Any] = {"path": rel(path), "exists": path.exists(), "kind": kind}
    if not path.exists():
        state["ok"] = False
        return state

    symbols = preload_base.run([readelf, "-Ws", str(path)], timeout=30.0)
    dynamic = preload_base.run([readelf, "-d", str(path)], timeout=30.0)
    header = preload_base.run([readelf, "-h", str(path)], timeout=30.0)
    file_result = preload_base.run([file_cmd, str(path)], timeout=30.0)
    sym = symbols["stdout"] if symbols["ok"] else ""
    dyn = dynamic["stdout"] if dynamic["ok"] else ""
    hdr = header["stdout"] if header["ok"] else ""

    state.update(
        {
            "sha256": preload_base.sha256_file(path),
            "size": path.stat().st_size,
            "mode": oct(path.stat().st_mode & 0o777),
            "file": file_result,
            "symbols": {"readelf_ok": symbols["ok"], "stdout": sym},
            "dynamic": {"readelf_ok": dynamic["ok"], "stdout": dyn},
            "header": {"readelf_ok": header["ok"], "stdout": hdr},
        }
    )

    if kind == "helper":
        checks = {
            "is_pie": "DYN (Shared object file)" in hdr,
            "entry_start": "_start" in sym,
            "undefined_init_v3": " UND acdb_loader_init_v3" in sym,
            "needed_libacdbloader": "Shared library: [libacdbloader.so]" in dyn,
            "needed_libaudcal": "Shared library: [libaudcal.so]" in dyn,
            "mode_0600": (path.stat().st_mode & 0o777) == 0o600,
        }
    else:
        checks = {
            "exports_acdb_ioctl": " acdb_ioctl" in sym,
            "exports_ioctl": " ioctl" in sym,
            "exports_common_topology": " acdb_loader_send_common_custom_topology" in sym,
            "exports_a90_arm_capture": " a90_arm_capture" in sym,
            "undefined_dlsym": " UND dlsym" in sym,
            "undefined_errno": " UND __errno" in sym,
            "soname_v2603": f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in dyn,
            "mode_0600": (path.stat().st_mode & 0o777) == 0o600,
        }
    state["checks"] = checks
    state["ok"] = bool(file_result.get("ok") and all(checks.values()))
    return state


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

    helper_obj = obj_dir / "a90_acdb_init_drive_exec_linked_v2572_v2603.o"
    tap_obj = obj_dir / "libacdbtap_v2475_v2600.o"
    ioctl_obj = obj_dir / "a90_ioctl_trace_preload_v2531.o"
    preinit_obj = obj_dir / "libacdb_preinit_perdevice_v2572_rx_capmask_argorder.o"
    helper_out = bin_dir / HELPER_ARTIFACT_NAME
    preload_out = bin_dir / PRELOAD_ARTIFACT_NAME

    helper_compile = v2572.compile_object(
        ROOT / v2572.HELPER_SOURCE_REL,
        helper_obj,
        clang=clang,
        env=env,
        log_dir=log_dir,
        cflags=v2572.HELPER_CFLAGS,
    )
    tap_compile = v2572.compile_object(
        ROOT / v2600.ACDBTAP_SOURCE_REL,
        tap_obj,
        clang=clang,
        env=env,
        log_dir=log_dir,
        cflags=v2600.COMMON_CFLAGS,
        extra=v2600.TAP_EXTRA_CFLAGS,
    )
    ioctl_compile = v2572.compile_object(
        ROOT / v2572.IOCTL_SOURCE_REL,
        ioctl_obj,
        clang=clang,
        env=env,
        log_dir=log_dir,
        cflags=v2572.PRELOAD_CFLAGS,
    )
    preinit_compile = v2572.compile_object(
        ROOT / v2572.PREINIT_SOURCE_REL,
        preinit_obj,
        clang=clang,
        env=env,
        log_dir=log_dir,
        cflags=v2572.PRELOAD_CFLAGS,
        extra=(v2591.CAP_MASK_CFLAG, v2591.ARG_ORDER_CFLAG),
    )

    if helper_compile["ok"]:
        helper_link = preload_base.run(
            [
                str(lld),
                *v2572.HELPER_LDFLAGS,
                "-L",
                str(v2572.VENDOR_LIB_DIR),
                "-o",
                str(helper_out),
                str(helper_obj),
                *v2572.LINK_LIBS,
            ],
            env=env,
        )
        (log_dir / "helper.link.stdout.txt").write_text(helper_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "helper.link.stderr.txt").write_text(helper_link["stderr"], encoding="utf-8", errors="replace")
        helper_link = {k: value for k, value in helper_link.items() if k not in {"stdout", "stderr"}}
        if helper_link["ok"] and helper_out.exists():
            helper_out.chmod(0o600)
    else:
        helper_link = {"ok": False, "skipped": True, "reason": "helper compile failed"}

    preload_compile_ok = tap_compile["ok"] and ioctl_compile["ok"] and preinit_compile["ok"]
    if preload_compile_ok:
        preload_link = preload_base.run(
            [str(lld), *PRELOAD_LDFLAGS, "-o", str(preload_out), str(tap_obj), str(ioctl_obj), str(preinit_obj)],
            env=env,
        )
        (log_dir / "preload.link.stdout.txt").write_text(preload_link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "preload.link.stderr.txt").write_text(preload_link["stderr"], encoding="utf-8", errors="replace")
        preload_link = {k: value for k, value in preload_link.items() if k not in {"stdout", "stderr"}}
        if preload_link["ok"] and preload_out.exists():
            preload_out.chmod(0o600)
    else:
        preload_link = {"ok": False, "skipped": True, "reason": "preload compile failed"}

    helper_state = binary_state(helper_out, readelf=readelf, file_cmd=file_cmd, kind="helper")
    preload_state = binary_state(preload_out, readelf=readelf, file_cmd=file_cmd, kind="preload")
    return {
        "host_libraries": host_libraries,
        "compile": {
            "helper": helper_compile,
            "acdbtap_v2600": tap_compile,
            "ioctl_trace": ioctl_compile,
            "preinit_perdevice_rx_capmask_argorder": preinit_compile,
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
            "reason": "combined artifact required because V2600 tap-only preload cannot arm or drive send_audio_cal_v5",
            "tap": "V2600 full in_buf plus bounded indirect candidate capture",
            "ioctl": "V2531 fake allocate/deallocate/SET when A90_ACDB_FAKE_ALLOCATE=1",
            "preinit": "V2572 hook compiled with V2591 RX cap-mask and fixed stack-order overrides",
            "per_device_call": "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
            "arm_policy": "preinit hook patches initialized flag, calls a90_arm_capture(), drives send_audio_cal_v5, then exits before init tail",
            "success_discriminator": "future live success requires ret==0 plus non-all-zero direct or indirect buffers, not requested length alone",
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
    tap_compile = build.get("compile", {}).get("acdbtap_v2600", {}) if isinstance(build, dict) else {}
    preinit_compile = build.get("compile", {}).get("preinit_perdevice_rx_capmask_argorder", {}) if isinstance(build, dict) else {}
    lines = [
        "# NATIVE_INIT V2603 — ACDB V2600 per-device combined preload build",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only build-only unit after V2602. No Android handoff, device flash, native replay SET,",
        "speaker write, or raw ACDB payload publication was performed.",
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
        "V2602 used the V2600 tap-only shared object as the live override preload. That omitted",
        "the preinit hook that arms capture and drives `send_audio_cal_v5`, so the run emitted",
        "zero `acdbtap` events before the known own-process helper SIGSEGV. This build creates",
        "the missing single preload with all three required pieces linked together.",
        "",
        "## Contract",
        "",
        "- tap: V2600 full `in_buf` dump plus bounded indirect `{length,pointer}` candidate capture.",
        "- ioctl shim: V2531 fake allocate/deallocate/SET when `A90_ACDB_FAKE_ALLOCATE=1`; no real SET passthrough.",
        "- preinit hook: V2572 per-device hook with V2591 `A90_SPEAKER_RX_PATH=1` and fixed stack-order compile flags.",
        "- future per-device call: `acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)`.",
        "- success remains `ret==0` plus non-all-zero direct/indirect payload, never requested length alone.",
        "- native calibration replay SET and speaker playback remain blocked.",
        "",
        "## Build Evidence",
        "",
        f"- tap_compile_ok: `{tap_compile.get('ok')}`",
        f"- tap_compile_has_inbuf_flag: `{'-DA90_ACDBTAP_CAPTURE_INBUF=1' in ' '.join(tap_compile.get('command', []))}`",
        f"- tap_compile_has_indirect_flag: `{'-DA90_ACDBTAP_CAPTURE_INDIRECT_CANDIDATES=1' in ' '.join(tap_compile.get('command', []))}`",
        f"- preinit_compile_ok: `{preinit_compile.get('ok')}`",
        f"- preinit_compile_has_rx_flag: `{v2591.CAP_MASK_CFLAG in ' '.join(preinit_compile.get('command', []))}`",
        f"- preinit_compile_has_fixed_order_flag: `{v2591.ARG_ORDER_CFLAG in ' '.join(preinit_compile.get('command', []))}`",
        f"- helper_checks: `{helper.get('checks')}`",
        f"- preload_checks: `{preload.get('checks')}`",
        "",
        "## Next Unit",
        "",
        "Run the V2592 Android-good handoff with the V2591 helper and this V2603 combined preload",
        "as the preload override. Do not use the V2600 tap-only shared object as the live preload again.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_v2600_perdevice_combined_preload_v2603.py tests/test_build_android_acdb_v2600_perdevice_combined_preload_v2603.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_v2600_perdevice_combined_preload_v2603 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_v2600_perdevice_combined_preload_v2603.py --build --write-report`",
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
