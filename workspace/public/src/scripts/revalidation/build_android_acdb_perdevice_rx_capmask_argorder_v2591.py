#!/usr/bin/env python3
"""Build V2591 ARM32 ACDB per-device capture with corrected send_audio_cal_v5 stack args.

Host-only unit.  V2588 proved the arg2=1 RX cap-mask route reaches send_audio_cal_v5 but then
hangs before the first real ACDB row. V2590 RE of the v2/v3/v4 wrappers shows
the v5 stack arg order used by V2586 was wrong: arg5 is the session/internal
selector and arg6 is the AFE sample-rate-like value. This build enables both
`A90_SPEAKER_RX_PATH=1` and `A90_SEND_AUDIO_CAL_V5_FIXED_STACK_ORDER=1`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_android_acdb_perdevice_indirect_capture_v2572 as v2572
import build_android_acdb_combined_preload_v2538 as preload_base

ROOT = v2572.ROOT
RUN_ID = "V2591"
BUILD_TAG = "v2591-acdb-perdevice-rx-capmask-argorder-build-only"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2591_AUDIO_ACDB_PERDEVICE_RX_CAPMASK_ARGORDER_BUILD_2026-06-16.md"
HELPER_ARTIFACT_NAME = "a90_acdb_perdevice_rx_capmask_argorder_exec_linked_v2591"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_perdevice_rx_capmask_argorder_capture_v2591.so"
CAP_MASK_CFLAG = "-DA90_SPEAKER_RX_PATH=1"
ARG_ORDER_CFLAG = "-DA90_SEND_AUDIO_CAL_V5_FIXED_STACK_ORDER=1"
PRELOAD_LDFLAGS = (
    "-shared",
    "--allow-shlib-undefined",
    "-soname",
    PRELOAD_ARTIFACT_NAME,
)


def rel(path: Path | str) -> str:
    return v2572.rel(path)


def source_state() -> dict[str, Any]:
    base = v2572.source_state()
    preinit_path = ROOT / v2572.PREINIT_SOURCE_REL
    preinit_text = preinit_path.read_text(encoding="utf-8", errors="replace") if preinit_path.exists() else ""
    required = dict(base.get("required", {}))
    required.update(
        {
            "preinit_rx_path_default_zero": "#define A90_SPEAKER_RX_PATH 0" in preinit_text,
            "preinit_rx_path_compile_override_guard": "#ifndef A90_SPEAKER_RX_PATH" in preinit_text,
            "operator_cap_mask_cflag": CAP_MASK_CFLAG == "-DA90_SPEAKER_RX_PATH=1",
            "preinit_fixed_stack_order_default_zero": "#define A90_SEND_AUDIO_CAL_V5_FIXED_STACK_ORDER 0" in preinit_text,
            "preinit_fixed_stack_order_compile_override_guard": "#ifndef A90_SEND_AUDIO_CAL_V5_FIXED_STACK_ORDER" in preinit_text,
            "operator_arg_order_cflag": ARG_ORDER_CFLAG == "-DA90_SEND_AUDIO_CAL_V5_FIXED_STACK_ORDER=1",
        }
    )
    base["required"] = required
    base["required_ok"] = all(required.values())
    base["v2591_delta"] = {
        "send_audio_cal_v5_arg2": 1,
        "send_audio_cal_v5_stack_args_5_6_7": [0, 48000, 1],
        "compile_overrides": [CAP_MASK_CFLAG, ARG_ORDER_CFLAG],
        "reason": "V2590 RE: v5 arg5 is session/internal selector and arg6 is the AFE sample-rate-like value",
    }
    return base


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
            "file": {k: value for k, value in file_result.items() if k not in {"stdout", "stderr"}},
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
            "soname_v2591": f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in dyn,
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

    helper_obj = obj_dir / "a90_acdb_init_drive_exec_linked_v2572.o"
    tap_obj = obj_dir / "libacdbtap_v2572.o"
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
        ROOT / v2572.ACDBTAP_SOURCE_REL,
        tap_obj,
        clang=clang,
        env=env,
        log_dir=log_dir,
        cflags=v2572.PRELOAD_CFLAGS,
        extra=v2572.PRELOAD_TAP_CFLAGS,
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
        extra=(CAP_MASK_CFLAG, ARG_ORDER_CFLAG),
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

    return {
        "host_libraries": host_libraries,
        "compile": {
            "helper": helper_compile,
            "acdbtap": tap_compile,
            "ioctl_trace": ioctl_compile,
            "preinit_perdevice_rx_capmask": preinit_compile,
        },
        "link": {"helper": helper_link, "preload": preload_link},
        "artifacts": {
            "helper": binary_state(helper_out, readelf=readelf, file_cmd=file_cmd, kind="helper"),
            "preload": binary_state(preload_out, readelf=readelf, file_cmd=file_cmd, kind="preload"),
        },
    }


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state()
    vendor = v2572.vendor_lib_state(args.readelf)
    if args.build:
        build_state = build(args.build_root, clang=args.clang, lld=args.lld, readelf=args.readelf, file_cmd=args.file)
    else:
        build_state = {"built": False, "reason": "pass --build to materialize private ARM32 artifacts"}
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
            "delta_from_v2586": "send_audio_cal_v5 stack args are compiled as (0, 48000, 1) instead of (48000, 0, 1)",
            "per_device_call": "acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)",
            "operator_re_basis": "V2590 wrapper RE: arg5 is session/internal selector and arg6 is the AFE sample-rate-like value",
            "arm_policy": "manual arm only from preinit hook after initialized-flag patch; no init-time acdb_ioctl dumping",
            "common_topology_policy": "skip the real public common-topology call by default; V2547 topology is already pinned",
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
    preinit_compile = build.get("compile", {}).get("preinit_perdevice_rx_capmask", {}) if isinstance(build, dict) else {}
    lines = [
        "# NATIVE_INIT V2591 — ACDB per-device RX cap-mask corrected-arg-order build",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only build-only unit after V2590. No Android handoff, device flash, native replay SET,",
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
        "V2588 proved the RX cap-mask route reaches `send_audio_cal_v5`, then hangs before the first",
        "real armed ACDB row. V2590 wrapper/prologue RE shows the prior build passed the trailing",
        "stack args in the wrong semantic order. This unit creates the same V2572 generic direct/",
        "indirect capture shape, compiles the second argument as RX cap mask `1`, and compiles the",
        "v5 stack args as `(session/default=0, afe_sample_rate=48000, instance=1)`.",
        "",
        "## Contract",
        "",
        "- future per-device call: `acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)`",
        "- real common-topology public call stays skipped; V2547 already pinned topology.",
        "- capture arms only after the initialized-flag patch inside the pre-init hook.",
        "- `A90_ACDB_FAKE_ALLOCATE=1` remains required for any future live run.",
        "- success remains `ret==0` plus non-all-zero direct/indirect payload, never requested length alone.",
        "- native calibration replay SET and speaker playback remain blocked.",
        "",
        "## Build Evidence",
        "",
        f"- preinit_compile_ok: `{preinit_compile.get('ok')}`",
        f"- preinit_compile_command_contains_capmask: `{CAP_MASK_CFLAG in ' '.join(preinit_compile.get('command', []))}`",
        f"- preinit_compile_command_contains_fixed_order: `{ARG_ORDER_CFLAG in ' '.join(preinit_compile.get('command', []))}`",
        f"- helper_checks: `{helper.get('checks')}`",
        f"- preload_checks: `{preload.get('checks')}`",
        "",
        "## Next Unit",
        "",
        "Add a V2592 live runner wrapper that selects these V2591 private artifacts and reuses the V2587",
        "classification logic. The live unit should be a single rollbackable Android handoff and must",
        "stop after preserving ordered ACDB tap records for operator Gate-2 mapping.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_perdevice_rx_capmask_argorder_v2591.py tests/test_build_android_acdb_perdevice_rx_capmask_argorder_v2591.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_perdevice_rx_capmask_argorder_v2591`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_perdevice_rx_capmask_argorder_v2591.py --build --write-report`",
        "- `git diff --check`",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
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
    args = parser.parse_args()

    payload = make_payload(args)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_report:
        write_report(payload, args.report)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
