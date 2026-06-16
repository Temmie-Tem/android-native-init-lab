#!/usr/bin/env python3
"""Build V2595 ARM32 ACDB direct 0x1122e metadata probe artifacts.

Host-only unit after V2594.  The private outputs are:

- the existing 32-bit Android PIE helper that starts acdb_loader_init_v3();
- a single 32-bit preload exporting ioctl() and
  acdb_loader_send_common_custom_topology().

The preload intercepts the common-topology entry during init, skips the already
pinned topology public call, patches the initialized flag, calls exactly one
pure-read acdb_ioctl(0x1122e, &0x11135, 4, out, 4), logs metadata, and exits
before the known init-tail crash.  It does not call send_audio_cal_v5() or issue
native replay/speaker SETs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import build_android_acdb_combined_preload_v2538 as preload_base
import build_android_acdb_perdevice_indirect_capture_v2572 as v2572

ROOT = v2572.ROOT
RUN_ID = "V2595"
BUILD_TAG = "v2595-acdb-direct-preget-probe-build-only"
HELPER_SOURCE_REL = v2572.HELPER_SOURCE_REL
IOCTL_SOURCE_REL = v2572.IOCTL_SOURCE_REL
PREGET_SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/libacdb_preget_probe_v2595.c"
TOOLCHAIN_ROOT = v2572.TOOLCHAIN_ROOT
VENDOR_LIB_DIR = v2572.VENDOR_LIB_DIR
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2595_AUDIO_ACDB_DIRECT_PREGET_PROBE_BUILD_2026-06-16.md"
HELPER_ARTIFACT_NAME = "a90_acdb_direct_preget_exec_linked_v2595"
PRELOAD_ARTIFACT_NAME = "liba90_acdb_direct_preget_probe_v2595.so"
HELPER_CFLAGS = v2572.HELPER_CFLAGS
HELPER_LDFLAGS = v2572.HELPER_LDFLAGS
PRELOAD_CFLAGS = v2572.PRELOAD_CFLAGS
PRELOAD_LDFLAGS = (
    "-shared",
    "--allow-shlib-undefined",
    "-soname",
    PRELOAD_ARTIFACT_NAME,
)
LINK_LIBS = v2572.LINK_LIBS
REQUIRED_NEEDED = v2572.REQUIRED_NEEDED


def rel(path: Path | str) -> str:
    return v2572.rel(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def source_state() -> dict[str, Any]:
    paths = {
        "helper": ROOT / HELPER_SOURCE_REL,
        "ioctl": ROOT / IOCTL_SOURCE_REL,
        "preget": ROOT / PREGET_SOURCE_REL,
    }
    texts = {name: read_text(path) for name, path in paths.items()}
    combined = "\n".join(texts.values())
    required = {
        "helper_source_exists": paths["helper"].exists(),
        "ioctl_source_exists": paths["ioctl"].exists(),
        "preget_source_exists": paths["preget"].exists(),
        "helper_calls_init_v3": "acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U)" in texts["helper"],
        "preget_exports_common_topology": "int32_t acdb_loader_send_common_custom_topology(void)" in texts["preget"],
        "preget_skips_real_common_topology_by_default": (
            "#define A90_V2595_CALL_REAL_COMMON_TOPOLOGY 0" in texts["preget"]
            and "skip_real_common_topology" in texts["preget"]
        ),
        "preget_patches_init_flag": "A90_LOADER_INIT_FLAG_OFF" in texts["preget"] and "*flag = 1U" in texts["preget"],
        "preget_cmd_0x1122e": "A90_ACDB_CMD_PREGET_METADATA 0x0001122eU" in texts["preget"],
        "preget_app_id_0x11135": "A90_APP_TYPE_MEDIA 0x00011135U" in texts["preget"],
        "preget_geometry_4_4": "A90_PREGET_IN_LEN 4U" in texts["preget"] and "A90_PREGET_OUT_LEN 4U" in texts["preget"],
        "preget_direct_acdb_ioctl_call": "a90_real_acdb_ioctl(A90_ACDB_CMD_PREGET_METADATA" in texts["preget"],
        "preget_logs_out_word": "\\\"out_word\\\":" in texts["preget"] and "\\\"out_nonzero\\\":" in texts["preget"],
        "preget_exits_before_init_tail": "exit_before_init_tail" in texts["preget"] and "a90_exit_group(0)" in texts["preget"],
        "ioctl_fake_allocate_set": (
            "A90_AUDIO_ALLOCATE_CALIBRATION" in texts["ioctl"]
            and "A90_AUDIO_DEALLOCATE_CALIBRATION" in texts["ioctl"]
            and "A90_AUDIO_SET_CALIBRATION" in texts["ioctl"]
            and "fake-success" in texts["ioctl"]
        ),
    }
    prohibited = {
        "preget_calls_send_audio_cal": (
            "acdb_loader_send_audio_cal_v5(" in texts["preget"]
            or "a90_real_send_audio_cal_v5" in texts["preget"]
        ),
        "preget_opens_msm_audio_cal": "/dev/msm_audio_cal" in texts["preget"],
        "helper_opens_msm_audio_cal": "/dev/msm_audio_cal" in texts["helper"],
        "native_speaker_write": any(token in combined for token in ("tinyplay", "tinymix", "AudioTrack")),
        "persistent_magisk_install": "magisk --install-module" in combined,
    }
    return {
        "sources": [HELPER_SOURCE_REL, IOCTL_SOURCE_REL, PREGET_SOURCE_REL],
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
            "exports_common_topology": " acdb_loader_send_common_custom_topology" in sym,
            "exports_ioctl": " ioctl" in sym,
            "undefined_dlsym": " UND dlsym" in sym,
            "undefined_dlopen": " UND dlopen" in sym,
            "undefined_errno": " UND __errno" in sym,
            "soname_v2595": f"Library soname: [{PRELOAD_ARTIFACT_NAME}]" in dyn,
            "does_not_export_acdb_ioctl": " acdb_ioctl" not in sym,
            "does_not_import_send_audio_cal": "acdb_loader_send_audio_cal_v5" not in sym,
            "mode_0600": (path.stat().st_mode & 0o777) == 0o600,
        }
    state["checks"] = checks
    state["ok"] = bool(file_result.get("ok") and all(checks.values()))
    return state


def vendor_lib_state(readelf: str) -> dict[str, Any]:
    state = v2572.vendor_lib_state(readelf)
    loader = VENDOR_LIB_DIR / "libacdbloader.so"
    loader_symbol_text = ""
    if loader.exists():
        symbols = preload_base.run([readelf, "-Ws", str(loader)], timeout=30.0)
        loader_symbol_text = symbols["stdout"] if symbols["ok"] else ""
    flags = state.get("libacdbloader_symbols", {})
    required = {
        "has_acdb_loader_init_v3": flags.get("has_acdb_loader_init_v3"),
        "has_acdb_loader_is_initialized": " acdb_loader_is_initialized" in loader_symbol_text,
        "has_acdb_loader_send_common_custom_topology": " acdb_loader_send_common_custom_topology" in loader_symbol_text,
        "imports_acdb_ioctl": flags.get("imports_acdb_ioctl"),
        "has_libaudcal": (VENDOR_LIB_DIR / "libaudcal.so").exists(),
    }
    state["required_for_v2595"] = required
    state["required_for_v2595_ok"] = all(required.values())
    return state


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    obj_dir = build_root / "obj"
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    obj_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    missing = [name for name in REQUIRED_NEEDED if not (VENDOR_LIB_DIR / name).exists()]
    if missing:
        return {"ok": False, "error": f"missing private ACDB closure libs: {', '.join(missing)}"}

    host_libraries = preload_base.prepare_host_libraries(build_root)
    env = preload_base.tool_env(host_libraries)

    helper_obj = obj_dir / "a90_acdb_init_drive_exec_linked_v2572.o"
    ioctl_obj = obj_dir / "a90_ioctl_trace_preload_v2531.o"
    preget_obj = obj_dir / "libacdb_preget_probe_v2595.o"
    helper_out = bin_dir / HELPER_ARTIFACT_NAME
    preload_out = bin_dir / PRELOAD_ARTIFACT_NAME

    helper_compile = v2572.compile_object(
        ROOT / HELPER_SOURCE_REL,
        helper_obj,
        clang=clang,
        env=env,
        log_dir=log_dir,
        cflags=HELPER_CFLAGS,
    )
    ioctl_compile = v2572.compile_object(
        ROOT / IOCTL_SOURCE_REL,
        ioctl_obj,
        clang=clang,
        env=env,
        log_dir=log_dir,
        cflags=PRELOAD_CFLAGS,
    )
    preget_compile = v2572.compile_object(
        ROOT / PREGET_SOURCE_REL,
        preget_obj,
        clang=clang,
        env=env,
        log_dir=log_dir,
        cflags=PRELOAD_CFLAGS,
    )

    if helper_compile["ok"]:
        helper_link = preload_base.run(
            [
                str(lld),
                *HELPER_LDFLAGS,
                "-L",
                str(VENDOR_LIB_DIR),
                "-o",
                str(helper_out),
                str(helper_obj),
                *LINK_LIBS,
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

    preload_compile_ok = ioctl_compile["ok"] and preget_compile["ok"]
    if preload_compile_ok:
        preload_link = preload_base.run(
            [str(lld), *PRELOAD_LDFLAGS, "-o", str(preload_out), str(ioctl_obj), str(preget_obj)],
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
            "ioctl_trace": ioctl_compile,
            "direct_preget": preget_compile,
        },
        "link": {"helper": helper_link, "preload": preload_link},
        "artifacts": {"helper": helper_state, "preload": preload_state},
        "ok": bool(helper_state.get("ok") and preload_state.get("ok")),
    }


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    source = source_state()
    vendor = vendor_lib_state(args.readelf)
    if args.build:
        build_state = build(args.build_root, clang=args.clang, lld=args.lld, readelf=args.readelf, file_cmd=args.file)
    else:
        build_state = {"built": False, "reason": "pass --build to materialize private ARM32 artifacts"}
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
            "no_real_audio_set": "ioctl preload fake-successes AUDIO_SET_CALIBRATION in fake mode; V2595 preget source issues no SET",
        },
        "capture_contract": {
            "route": "common-topology hook -> patch initialized flag -> direct acdb_ioctl metadata query -> exit_group",
            "skips_send_audio_cal_v5": True,
            "direct_query": "acdb_ioctl(0x1122e, &0x11135, 4, &out_word, 4)",
            "operator_re_basis": "V2594 Thumb RE pinned the first send_audio_cal_v5 dispatcher row geometry",
            "success_discriminator": "future live result is metadata-only: ret==0 and out_word/nonzero classification; requested length alone is not success",
        },
        "sources": source,
        "vendor_libs": vendor,
        "build": build_state,
        "build_root": rel(args.build_root),
    }
    payload["ok"] = bool(
        source.get("required_ok")
        and source.get("prohibited_ok")
        and vendor.get("required_for_v2595_ok")
        and build_state.get("ok", True)
    )
    return payload


def write_report(path: Path, payload: dict[str, Any]) -> None:
    artifacts = payload.get("build", {}).get("artifacts", {})
    helper = artifacts.get("helper", {})
    preload = artifacts.get("preload", {})
    lines = [
        "# NATIVE_INIT V2595 — ACDB direct pre-GET probe build",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only build unit after V2594. No Android handoff, native replay `SET`, speaker write,",
        "ACDB command execution, or raw payload publication was performed.",
        "",
        "## Decision",
        "",
        f"- decision: `v2595-acdb-direct-0x1122e-probe-build-ready`",
        f"- ok: `{payload.get('ok')}`",
        "- V2594 pinned the first `send_audio_cal_v5` dispatcher row as `acdb_ioctl(0x1122e, &0x11135, 4, out, 4)`.",
        "- V2595 builds a narrower probe that bypasses the hanging `send_audio_cal_v5` local setup and calls that metadata row directly.",
        "",
        "## Built Artifacts",
        "",
        f"- helper: `{helper.get('path')}`",
        f"  - sha256: `{helper.get('sha256')}`",
        f"  - ok: `{helper.get('ok')}`",
        f"- preload: `{preload.get('path')}`",
        f"  - sha256: `{preload.get('sha256')}`",
        f"  - ok: `{preload.get('ok')}`",
        "",
        "Private binaries remain under `workspace/private/builds/audio/` and are not committed.",
        "",
        "## Probe Contract",
        "",
        "- intercept `acdb_loader_send_common_custom_topology()` during `acdb_loader_init_v3()`;",
        "- skip the real common-topology public call because topology cal_type 39 is already pinned;",
        "- patch `acdb_loader_is_initialized`'s backing flag using the established V2572 offsets;",
        "- call exactly `acdb_ioctl(0x1122e, &0x11135, 4, &out_word, 4)`;",
        "- log `{ret,out_word,out_nonzero}` to `/data/local/tmp/a90-acdb-ownget/acdb-v2595-direct-preget-events.jsonl`; and",
        "- `exit_group(0)` before libacdbloader's known init-tail crash.",
        "",
        "The preget interposer does not import or call `acdb_loader_send_audio_cal_v5`, does not open",
        "`/dev/msm_audio_cal`, and relies on the existing fake-allocate ioctl preload only to keep the",
        "ACDB init transport measurement-only.",
        "",
        "## Next Unit",
        "",
        "Run V2596 as the recoverable Android-good live handoff for these V2595 artifacts:",
        "",
        "1. stage the helper/preload/dependency closure under `/data/local/tmp/a90-acdb-ownget`;",
        "2. set `LD_PRELOAD` to the V2595 preload and `A90_ACDB_FAKE_ALLOCATE=1`;",
        "3. execute the helper once;",
        "4. pull `acdb-v2595-direct-preget-events.jsonl` and `ioctl-trace-events.jsonl` privately;",
        "5. classify whether `ret==0` and whether `out_word` is non-zero; and",
        "6. rollback to V2321 and verify `selftest fail=0`.",
        "",
        "If the direct `0x1122e` metadata probe succeeds, derive subsequent per-device pure-read request",
        "structs from the returned word. If it fails or hangs, fall back to a more granular import-call tracer",
        "around the two local pre-`0x1122e` helpers identified in V2594.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_direct_preget_probe_v2595.py tests/test_build_android_acdb_direct_preget_probe_v2595.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_direct_preget_probe_v2595`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -p 'test_build_android_acdb_direct_preget_probe_v2595.py'`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_direct_preget_probe_v2595.py --build --write-report`",
        "- `file`/`readelf` artifact checks embedded in the manifest",
        "- `git diff --check`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--clang", type=Path, default=TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--file", default="file")
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = make_payload(args)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_report:
        write_report(args.report_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
