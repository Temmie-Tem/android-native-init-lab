#!/usr/bin/env python3
"""Build V2600 ARM32 ACDB indirect-buffer tap artifacts.

Host-only unit after V2599.  It materializes one private 32-bit combined
preload that keeps the V2538/V2556 post-init arming/fake-allocate contract, but
adds default-off-at-source compile-time capture of:

- full acdb_ioctl input buffers; and
- bounded candidate {length,pointer} indirect buffers found in those inputs.

No Android handoff, ACDB execution, native replay SET, or speaker write happens
in this build unit.  The live use of this preload remains a separate exact-gated
unit after operator review of the build contract.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_android_acdb_combined_preload_v2538 as base

ROOT = base.ROOT
RUN_ID = "V2600"
BUILD_TAG = "v2600-acdb-indirect-buffer-tap-build-only"
ACDBTAP_SOURCE_REL = base.ACDBTAP_SOURCE_REL
IOCTL_SOURCE_REL = base.IOCTL_SOURCE_REL
TOOLCHAIN_ROOT = base.TOOLCHAIN_ROOT
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2600_AUDIO_ACDB_INDIRECT_BUFFER_TAP_BUILD_2026-06-16.md"
ARTIFACT_NAME = "liba90_acdb_indirect_buffer_tap_v2600.so"
TARGET = base.TARGET
COMMON_CFLAGS = base.CFLAGS
TAP_EXTRA_CFLAGS = (
    "-DA90_ACDBTAP_ARMED_CAPTURE=1",
    "-DA90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=0",
    "-DA90_ACDBTAP_CUSTOM_TOPOLOGY_ONLY=0",
    "-DA90_ACDBTAP_LOG_ENTER=1",
    "-DA90_ACDBTAP_EXIT_ON_TARGET=0",
    "-DA90_ACDBTAP_CAPTURE_INBUF=1",
    "-DA90_ACDBTAP_CAPTURE_INDIRECT_CANDIDATES=1",
    "-DA90_ACDBTAP_INDIRECT_SCAN_WORDS=16",
)
LDFLAGS = (
    "-shared",
    "--allow-shlib-undefined",
    "-soname",
    ARTIFACT_NAME,
)


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def source_state() -> dict[str, Any]:
    tap_path = ROOT / ACDBTAP_SOURCE_REL
    ioctl_path = ROOT / IOCTL_SOURCE_REL
    tap = read_text(tap_path)
    ioctl = read_text(ioctl_path)
    combined = f"{tap}\n{ioctl}"
    required = {
        "tap_source_exists": tap_path.exists(),
        "ioctl_source_exists": ioctl_path.exists(),
        "tap_manual_arm_exported": "void a90_arm_capture(void)" in tap,
        "tap_unarmed_real_only_path": "if (!a90_armed)" in tap and "return ret;" in tap,
        "tap_auto_arm_default_off": "#define A90_ACDBTAP_AUTO_ARM_ON_INITIALIZE 0" in tap,
        "tap_capture_inbuf_macro": "A90_ACDBTAP_CAPTURE_INBUF" in tap,
        "tap_capture_indirect_macro": "A90_ACDBTAP_CAPTURE_INDIRECT_CANDIDATES" in tap,
        "tap_scan_word_bound_macro": "A90_ACDBTAP_INDIRECT_SCAN_WORDS" in tap,
        "tap_kinded_raw_paths": "a90_build_raw_path_kind" in tap and "buffer" in tap,
        "tap_input_buffer_kind": "\"in\"" in tap and "A90_ACDBTAP_CAPTURE_INBUF" in tap,
        "tap_indirect_candidate_kind": "indirect0" in tap and "a90_log_indirect_candidate_captures" in tap,
        "tap_probable_user_ptr_guard": "a90_is_probable_user_read_ptr" in tap and "0x10000000U" in tap,
        "tap_zero_buffer_guard": "ret == 0 && buf_len == A90_TARGET_OUT_LEN && !all_zero" in tap,
        "ioctl_fake_allocate_env": "A90_ACDB_FAKE_ALLOCATE" in ioctl,
        "ioctl_noops_allocate_deallocate_set": (
            "A90_AUDIO_ALLOCATE_CALIBRATION" in ioctl
            and "A90_AUDIO_DEALLOCATE_CALIBRATION" in ioctl
            and "A90_AUDIO_SET_CALIBRATION" in ioctl
            and "fake-success" in ioctl
        ),
    }
    prohibited = {
        "tap_opens_msm_audio_cal": "/dev/msm_audio_cal" in tap,
        "ioctl_opens_msm_audio_cal": 'open("/dev/msm_audio_cal' in ioctl or "open('/dev/msm_audio_cal" in ioctl,
        "native_speaker_write": any(token in combined for token in ("tinyplay", "tinymix", "AudioTrack")),
        "persistent_magisk_install": "magisk --install-module" in combined,
    }
    return {
        "sources": [ACDBTAP_SOURCE_REL, IOCTL_SOURCE_REL],
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
    }


def compile_object(source: Path, obj: Path, *, clang: Path, env: dict[str, str], log_dir: Path, extra: tuple[str, ...] = ()) -> dict[str, Any]:
    command = [str(clang), *COMMON_CFLAGS, *extra, "-c", str(source), "-o", str(obj)]
    result = base.run(command, env=env)
    (log_dir / f"{obj.stem}.compile.stdout.txt").write_text(result["stdout"], encoding="utf-8", errors="replace")
    (log_dir / f"{obj.stem}.compile.stderr.txt").write_text(result["stderr"], encoding="utf-8", errors="replace")
    return {k: value for k, value in result.items() if k not in {"stdout", "stderr"}}


def build(build_root: Path, *, clang: Path, lld: Path, readelf: str, file_cmd: str) -> dict[str, Any]:
    obj_dir = build_root / "obj"
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    obj_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    host_libraries = base.prepare_host_libraries(build_root)
    env = base.tool_env(host_libraries)
    tap_obj = obj_dir / "libacdbtap_v2475_indirect_v2600.o"
    ioctl_obj = obj_dir / "a90_ioctl_trace_preload_v2531.o"
    out = bin_dir / ARTIFACT_NAME

    tap_compile = compile_object(ROOT / ACDBTAP_SOURCE_REL, tap_obj, clang=clang, env=env, log_dir=log_dir, extra=TAP_EXTRA_CFLAGS)
    ioctl_compile = compile_object(ROOT / IOCTL_SOURCE_REL, ioctl_obj, clang=clang, env=env, log_dir=log_dir)
    if tap_compile["ok"] and ioctl_compile["ok"]:
        link = base.run([str(lld), *LDFLAGS, "-o", str(out), str(tap_obj), str(ioctl_obj)], env=env)
        (log_dir / "link.stdout.txt").write_text(link["stdout"], encoding="utf-8", errors="replace")
        (log_dir / "link.stderr.txt").write_text(link["stderr"], encoding="utf-8", errors="replace")
        link = {k: value for k, value in link.items() if k not in {"stdout", "stderr"}}
        if link["ok"] and out.exists():
            out.chmod(0o600)
    else:
        link = {"ok": False, "skipped": True, "reason": "compile failed"}

    binary: dict[str, Any] = {"path": rel(out), "exists": out.exists()}
    if out.exists():
        symbols = base.run([readelf, "-Ws", str(out)], env=env, timeout=30.0)
        dyn = base.run([readelf, "-d", str(out)], env=env, timeout=30.0)
        file_result = base.run([file_cmd, str(out)], timeout=30.0)
        sym = symbols["stdout"] if symbols["ok"] else ""
        dynamic = dyn["stdout"] if dyn["ok"] else ""
        binary.update(
            {
                "sha256": base.sha256_file(out),
                "size": out.stat().st_size,
                "mode": oct(out.stat().st_mode & 0o777),
                "file": file_result,
                "symbols": {
                    "readelf_ok": symbols["ok"],
                    "exports_acdb_ioctl": " acdb_ioctl" in sym,
                    "exports_ioctl": " ioctl" in sym,
                    "exports_a90_arm_capture": " a90_arm_capture" in sym,
                    "undefined_dlsym": " UND dlsym" in sym,
                    "undefined_errno": " UND __errno" in sym,
                },
                "dynamic": {
                    "readelf_ok": dyn["ok"],
                    "soname": f"Library soname: [{ARTIFACT_NAME}]" in dynamic,
                },
            }
        )
    return {
        "host_libraries": host_libraries,
        "compile": {"acdbtap": tap_compile, "ioctl_trace": ioctl_compile},
        "link": link,
        "logs": rel(log_dir),
        "binary": binary,
        "ok": bool(
            tap_compile.get("ok")
            and ioctl_compile.get("ok")
            and link.get("ok")
            and binary.get("exists")
            and binary.get("symbols", {}).get("exports_acdb_ioctl")
            and binary.get("symbols", {}).get("exports_ioctl")
            and binary.get("symbols", {}).get("exports_a90_arm_capture")
            and binary.get("dynamic", {}).get("soname")
        ),
    }


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    clang = Path(args.clang) if args.clang else TOOLCHAIN_ROOT / "bin/clang"
    lld = Path(args.lld) if args.lld else TOOLCHAIN_ROOT / "bin/ld.lld"
    source = source_state()
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "android_action": "none",
        "source": source,
        "toolchain": {
            "clang": rel(clang),
            "lld": rel(lld),
            "target": TARGET,
            "common_cflags": list(COMMON_CFLAGS),
            "tap_extra_cflags": list(TAP_EXTRA_CFLAGS),
            "ldflags": list(LDFLAGS),
        },
        "capture_contract": {
            "manual_post_init_arm_required": True,
            "unarmed_acdb_ioctl_path_has_no_file_io": True,
            "dumps_full_inbuf_when_compiled": True,
            "scans_bounded_len_ptr_candidates": True,
            "scan_words": 16,
            "success_requires_ret0_nonzero_4916": True,
            "fake_allocate_env_required": "A90_ACDB_FAKE_ALLOCATE=1",
            "future_live_requires_separate_gate": True,
        },
        "boundaries": {
            "no_live_default": True,
            "no_native_replay": True,
            "no_speaker_write": True,
            "raw_bytes_private_only": True,
            "does_not_open_msm_audio_cal": True,
            "does_not_issue_extra_ioctl": True,
            "no_real_audio_set_calibration": True,
        },
        "v2599_delta": "adds full in_buf dumps plus bounded indirect {len,ptr} candidate scans for table-backed per-device rows whose visible out_buf is only four bytes",
    }
    if args.build:
        payload["build"] = build(args.build_root, clang=clang, lld=lld, readelf=args.readelf, file_cmd=args.file)
    else:
        payload["build"] = {"ok": True, "skipped": True, "reason": "pass --build to materialize private ARM32 artifact"}
    payload["ok"] = bool(source["required_ok"] and source["prohibited_ok"] and payload["build"].get("ok"))
    return payload


def render_report(payload: dict[str, Any]) -> str:
    build = payload.get("build", {})
    binary = build.get("binary", {})
    source = payload.get("source", {})
    lines = [
        "# NATIVE_INIT V2600 — ACDB indirect buffer tap build",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only build unit after V2599. No Android handoff, ACDB execution, native replay `SET`, speaker write, or raw payload publication was performed.",
        "",
        "## Decision",
        "",
        "- decision: `v2600-acdb-indirect-buffer-tap-build-ready`" if payload.get("ok") else "- decision: `v2600-acdb-indirect-buffer-tap-build-blocked`",
        f"- ok: `{payload.get('ok')}`",
        f"- build tag: `{payload.get('build_tag')}`",
        f"- artifact: `{binary.get('path')}`",
        f"- artifact sha256: `{binary.get('sha256')}`",
        "",
        "## Capture Contract",
        "",
        "- The tap remains silent while unarmed: init-time `acdb_ioctl` calls only call the real symbol.",
        "- The future helper must call `a90_arm_capture()` after `acdb_loader_init_v3` returns and before driving the target getter/send path.",
        "- With V2600 compile flags, armed calls dump full `in_buf` records and scan the first 16 input words for bounded `{length,pointer}` candidate buffers.",
        "- A successful target still requires `ret==0`, `out_len==4916`, and non-all-zero bytes; requested length alone is not success.",
        "- Fake allocation remains opt-in through `A90_ACDB_FAKE_ALLOCATE=1`; no new `/dev/msm_audio_cal` open or ioctl is introduced by this tap.",
        "",
        "## Source State",
        "",
        f"- required_ok: `{source.get('required_ok')}`",
        f"- prohibited_ok: `{source.get('prohibited_ok')}`",
        "- sources:",
    ]
    for item in source.get("sources", []):
        lines.append(f"  - `{item}`")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_indirect_buffer_tap_v2600.py tests/test_build_android_acdb_indirect_buffer_tap_v2600.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_indirect_buffer_tap_v2600`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_indirect_buffer_tap_v2600.py --build --write-report`",
            "- `git diff --check`",
            "",
            "## Next Unit",
            "",
            "Use this artifact only in a separately gated Android-good live handoff. The live unit must pull raw bytes privately and classify per-call records by `{cmd, buffer, in_len, out_len, ret, sha256, all_zero}` before any replay-manifest use.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--clang")
    parser.add_argument("--lld", type=Path, default=TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--readelf", default=str(TOOLCHAIN_ROOT / "bin/llvm-readelf"))
    parser.add_argument("--file", default="file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.build_root.mkdir(parents=True, exist_ok=True)
    payload = make_payload(args)
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_report:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
