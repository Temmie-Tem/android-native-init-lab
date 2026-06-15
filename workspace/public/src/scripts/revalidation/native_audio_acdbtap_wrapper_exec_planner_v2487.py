#!/usr/bin/env python3
"""V2487 host-only planner for a wrapper-exec ACDB tap Magisk capsule.

V2486 proved the service-env rc overlay path is blocked on this device: init
sees the overlaid rc but ignores the duplicate vendor.audio-hal service.  This
planner prepares the next injection route without touching the device: replace
`/vendor/bin/hw/android.hardware.audio.service` with a tiny wrapper executable
that sets LD_PRELOAD and execs a private copy of the original vendor HAL binary.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_android_acdbtap_v2475 as v2475
import native_audio_acdbtap_live_planner_v2476 as v2476


RUN_ID = "V2487"
BUILD_TAG = "v2487-audio-acdbtap-wrapper-exec-planner"
ROOT = v2476.ROOT
MODULE_ID = "a90_acdbtap_wrapper_exec_v2487"
SOURCE_REL = "workspace/public/src/android/acdb_payload_capture/a90_audio_hal_preload_wrapper_v2487.c"
DEFAULT_MODULE_OUT_DIR = ROOT / "workspace/private/builds/audio/v2487-acdbtap-wrapper-exec-module"
DEFAULT_MANIFEST = DEFAULT_MODULE_OUT_DIR / "manifest.json"
ORIGINAL_HAL = ROOT / "workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/bin/hw/android.hardware.audio.service"
ORIGINAL_HAL_SHA256 = "c57d939fc6eb5c68f81d9d890dabdadb88c9ae10bdc7c9db853fb64e9294da81"
WRAPPER_REL = "system/vendor/bin/hw/android.hardware.audio.service"
ORIGINAL_REL = "system/vendor/bin/hw/android.hardware.audio.service.a90orig"
TAP_REL = "system/vendor/lib/libacdbtap.so"
REMOTE_DIR = "/data/local/tmp/a90-acdbtap-v2487"
REMOTE_STAGE_DIR = f"{REMOTE_DIR}/module-stage"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_ID}"
REMOTE_MODULE_UPDATE_DIR = f"/data/adb/modules_update/{MODULE_ID}"
WRAPPER_PATH = "/vendor/bin/hw/android.hardware.audio.service"
ORIGINAL_PATH = "/vendor/bin/hw/android.hardware.audio.service.a90orig"
TAP_PATH = "/vendor/lib/libacdbtap.so"
CAPTURE_DIR = v2476.REMOTE_CAPTURE_DIR
TOOLCHAIN_ROOT = v2475.TOOLCHAIN_ROOT
TARGET = "armv7a-linux-androideabi29"
CFLAGS = (
    "--target=armv7a-linux-androideabi29",
    "-fPIE",
    "-ffreestanding",
    "-fno-builtin",
    "-fno-stack-protector",
    "-fvisibility=hidden",
    "-marm",
    "-Os",
    "-Wall",
    "-Wextra",
)
LDFLAGS = (
    "-pie",
    "--dynamic-linker",
    "/system/bin/linker",
    "-e",
    "_start",
    "--build-id=sha1",
)


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return v2475.sha256_file(path)


def run(command: list[str], *, env: dict[str, str] | None = None, timeout: float = 180.0) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return {
        "command": command,
        "rc": completed.returncode,
        "ok": completed.returncode == 0,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def file_state(path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {"path": rel(path), "exists": path.exists()}
    if not path.exists():
        state["ok"] = False
        return state
    state["size"] = path.stat().st_size
    state["mode"] = oct(path.stat().st_mode & 0o777)
    state["sha256"] = sha256(path)
    if expected_sha256 is not None:
        state["expected_sha256"] = expected_sha256
        state["sha256_ok"] = state["sha256"] == expected_sha256
        state["ok"] = state["sha256_ok"]
    else:
        state["ok"] = True
    return state


def source_state() -> dict[str, Any]:
    source = ROOT / SOURCE_REL
    text = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
    required = {
        "injects_ld_preload": "A90_ENV_LD_PRELOAD" in text and TAP_PATH in text,
        "injects_capture_dir": "A90_ENV_CAPTURE_DIR" in text and CAPTURE_DIR in text,
        "execs_original_hal": f"#define A90_REAL_HAL \"{ORIGINAL_PATH}\"" in text and "A90_NR_EXECVE" in text and "A90_REAL_HAL" in text,
        "kmsg_error_marker": "A90_ACDBTAP_WRAPPER" in text,
        "raw_syscalls_only": "A90_NR_EXECVE" in text and "svc #0" in text,
        "no_libc_headers": "#include <" not in text,
    }
    prohibited = {
        "opens_msm_audio_cal": "/dev/msm_audio_cal" in text,
        "calibration_ioctl": "AUDIO_SET_CALIBRATION" in text or "AUDIO_ALLOCATE_CALIBRATION" in text,
        "speaker_playback": "tinyplay" in text or "tinymix" in text,
        "silent_permissive": "setenforce" in text,
        "libc_setenv": "setenv(" in text,
    }
    return {
        "source": SOURCE_REL,
        "exists": source.exists(),
        "required": required,
        "required_ok": all(required.values()),
        "prohibited": prohibited,
        "prohibited_ok": not any(prohibited.values()),
    }


def build_wrapper(out_dir: Path, *, clang: Path, lld: Path, file_cmd: str) -> dict[str, Any]:
    source = ROOT / SOURCE_REL
    build_dir = out_dir / "wrapper-build"
    obj_dir = build_dir / "obj"
    bin_dir = build_dir / "bin"
    log_dir = build_dir / "logs"
    obj_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    host_libraries = v2475.prepare_host_libraries(build_dir)
    env = v2475.tool_env(host_libraries)
    obj = obj_dir / "a90_audio_hal_preload_wrapper_v2487.o"
    wrapper = bin_dir / "android.hardware.audio.service"
    compile_cmd = [str(clang), *CFLAGS, "-c", str(source), "-o", str(obj)]
    compile_result = run(compile_cmd, env=env)
    (log_dir / "compile.stdout.txt").write_text(compile_result["stdout"])
    (log_dir / "compile.stderr.txt").write_text(compile_result["stderr"])
    if not compile_result["ok"]:
        raise RuntimeError(f"wrapper build failed; see {rel(log_dir / 'compile.stderr.txt')}")
    link_cmd = [str(lld), *LDFLAGS, "-o", str(wrapper), str(obj)]
    link_result = run(link_cmd, env=env)
    (log_dir / "link.stdout.txt").write_text(link_result["stdout"])
    (log_dir / "link.stderr.txt").write_text(link_result["stderr"])
    if not link_result["ok"]:
        raise RuntimeError(f"wrapper link failed; see {rel(log_dir / 'link.stderr.txt')}")
    os.chmod(wrapper, 0o755)
    file_result = run([file_cmd, str(wrapper)], timeout=10.0)
    if not file_result["ok"]:
        raise RuntimeError(file_result["stderr"] or file_result["stdout"] or "file failed")
    return {
        "host_libraries": host_libraries,
        "commands": {
            "compile": {k: v for k, v in compile_result.items() if k not in {"stdout", "stderr"}},
            "link": {k: v for k, v in link_result.items() if k not in {"stdout", "stderr"}},
        },
        "logs": rel(log_dir),
        "artifact": {
            "path": rel(wrapper),
            "sha256": sha256(wrapper),
            "size": wrapper.stat().st_size,
            "mode": oct(wrapper.stat().st_mode & 0o777),
            "file": file_result["stdout"].strip(),
            "target": TARGET,
            "private_generated": True,
        },
    }


def write_private(path: Path, text: str, mode: int) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    os.chmod(path, mode)
    return {"path": rel(path), "mode": oct(mode), "size": path.stat().st_size, "sha256": sha256(path)}


def module_prop() -> str:
    return f"""id={MODULE_ID}
name=A90 ACDB Tap Wrapper Exec V2487
version=0.1
versionCode=2487
author=A90 native-init project
description=Temporary measurement-only Magisk capsule replacing the vendor audio HAL binary with an LD_PRELOAD exec wrapper.
"""


def readme() -> str:
    return f"""# A90 ACDB Tap Wrapper Exec V2487

Private temporary Magisk measurement capsule.

This module avoids the V2486 blocked service-rc route. Android init keeps the
stock `vendor.audio-hal` service definition, but the service path is overlaid:

- `{WRAPPER_PATH}`: public wrapper built by this unit
- `{ORIGINAL_PATH}`: private copy of the stock vendor HAL binary
- `{TAP_PATH}`: V2475 `libacdbtap.so`

The wrapper sets `LD_PRELOAD={TAP_PATH}` and `A90_ACDBTAP_DIR={CAPTURE_DIR}` and
then execs `{ORIGINAL_PATH}`. It contains no `service.sh`, `post-fs-data.sh`,
`system.prop`, `sepolicy.rule`, native calibration replay, or speaker playback.
"""


def forbidden_files_absent(out_dir: Path) -> dict[str, Any]:
    forbidden = ["service.sh", "post-fs-data.sh", "system.prop", "sepolicy.rule"]
    present = [name for name in forbidden if (out_dir / name).exists()]
    return {"ok": not present, "forbidden": forbidden, "present": present}


def materialize_module(out_dir: Path, *, clang: Path, lld: Path, file_cmd: str) -> dict[str, Any]:
    source = source_state()
    original = file_state(ORIGINAL_HAL, expected_sha256=ORIGINAL_HAL_SHA256)
    tap = file_state(v2476.TAP_SO, expected_sha256=v2476.TAP_SHA256)
    if not source.get("required_ok") or not source.get("prohibited_ok"):
        return {"ok": False, "reason": "wrapper source boundary failed", "source_state": source}
    if not original.get("ok"):
        return {"ok": False, "reason": "stock vendor HAL binary missing or SHA invalid", "source_state": source, "original_hal": original}
    if not tap.get("ok"):
        return {"ok": False, "reason": "V2475 libacdbtap artifact missing or SHA invalid", "source_state": source, "tap": tap}
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    os.chmod(out_dir, 0o700)
    wrapper_build = build_wrapper(out_dir, clang=clang, lld=lld, file_cmd=file_cmd)

    files = [
        write_private(out_dir / "module.prop", module_prop(), 0o600),
        write_private(out_dir / "README.md", readme(), 0o600),
    ]
    wrapper_target = out_dir / WRAPPER_REL
    wrapper_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out_dir / "wrapper-build/bin/android.hardware.audio.service", wrapper_target)
    os.chmod(wrapper_target, 0o755)
    files.append({"path": rel(wrapper_target), "mode": oct(0o755), "size": wrapper_target.stat().st_size, "sha256": sha256(wrapper_target)})

    original_target = out_dir / ORIGINAL_REL
    shutil.copy2(ORIGINAL_HAL, original_target)
    os.chmod(original_target, 0o755)
    files.append({"path": rel(original_target), "mode": oct(0o755), "size": original_target.stat().st_size, "sha256": sha256(original_target)})

    tap_target = out_dir / TAP_REL
    tap_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(v2476.TAP_SO, tap_target)
    os.chmod(tap_target, 0o644)
    files.append({"path": rel(tap_target), "mode": oct(0o644), "size": tap_target.stat().st_size, "sha256": sha256(tap_target)})

    for directory in [out_dir, *(path for path in out_dir.rglob("*") if path.is_dir())]:
        os.chmod(directory, 0o700)

    manifest = {
        "generated_at": now_iso(),
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "module_id": MODULE_ID,
        "module_out_dir": rel(out_dir),
        "remote_module_dir": REMOTE_MODULE_DIR,
        "wrapper_rel": WRAPPER_REL,
        "original_rel": ORIGINAL_REL,
        "tap_rel": TAP_REL,
        "wrapper_path": WRAPPER_PATH,
        "original_path": ORIGINAL_PATH,
        "tap_path": TAP_PATH,
        "capture_dir": CAPTURE_DIR,
        "source_state": source,
        "original_hal": original,
        "tap_source": tap,
        "wrapper_build": wrapper_build,
        "files": files,
        "forbidden_files_absent": forbidden_files_absent(out_dir),
        "private_only": True,
    }
    manifest["ok"] = bool(
        manifest["forbidden_files_absent"]["ok"]
        and file_state(wrapper_target).get("ok")
        and file_state(original_target, expected_sha256=ORIGINAL_HAL_SHA256).get("ok")
        and file_state(tap_target, expected_sha256=v2476.TAP_SHA256).get("ok")
    )
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.chmod(out_dir / "manifest.json", 0o600)
    return manifest


def command_plan(module_out_dir: Path) -> dict[str, Any]:
    files = {
        "module.prop": module_out_dir / "module.prop",
        "README.md": module_out_dir / "README.md",
        WRAPPER_REL: module_out_dir / WRAPPER_REL,
        ORIGINAL_REL: module_out_dir / ORIGINAL_REL,
        TAP_REL: module_out_dir / TAP_REL,
    }
    install_script = f"""
set -eu
MODULE_DIR={shlex.quote(REMOTE_MODULE_DIR)}
MODULE_UPDATE_DIR={shlex.quote(REMOTE_MODULE_UPDATE_DIR)}
STAGE_DIR={shlex.quote(REMOTE_STAGE_DIR)}
echo A90_ACDBTAP_V2487_INSTALL_BEGIN
for path in "$MODULE_DIR" "$MODULE_UPDATE_DIR"; do
  if [ -e "$path" ]; then
    echo A90_ACDBTAP_V2487_RESIDUE_PRESENT "$path"
    exit 70
  fi
done
mkdir -p "$MODULE_DIR/system/vendor/bin/hw" "$MODULE_DIR/system/vendor/lib"
cp "$STAGE_DIR/module.prop" "$MODULE_DIR/module.prop"
cp "$STAGE_DIR/README.md" "$MODULE_DIR/README.md"
cp "$STAGE_DIR/{WRAPPER_REL}" "$MODULE_DIR/{WRAPPER_REL}"
cp "$STAGE_DIR/{ORIGINAL_REL}" "$MODULE_DIR/{ORIGINAL_REL}"
cp "$STAGE_DIR/{TAP_REL}" "$MODULE_DIR/{TAP_REL}"
rm -f "$MODULE_DIR/disable" "$MODULE_DIR/remove"
chown -R 0:0 "$MODULE_DIR"
chmod 755 "$MODULE_DIR" "$MODULE_DIR/system" "$MODULE_DIR/system/vendor" "$MODULE_DIR/system/vendor/bin" "$MODULE_DIR/system/vendor/bin/hw" "$MODULE_DIR/system/vendor/lib"
chmod 755 "$MODULE_DIR/{WRAPPER_REL}" "$MODULE_DIR/{ORIGINAL_REL}"
chmod 644 "$MODULE_DIR/{TAP_REL}"
chmod 600 "$MODULE_DIR/module.prop" "$MODULE_DIR/README.md"
sha256sum "$MODULE_DIR/{WRAPPER_REL}" "$MODULE_DIR/{ORIGINAL_REL}" "$MODULE_DIR/{TAP_REL}" 2>/dev/null || toybox sha256sum "$MODULE_DIR/{WRAPPER_REL}" "$MODULE_DIR/{ORIGINAL_REL}" "$MODULE_DIR/{TAP_REL}"
find "$MODULE_DIR" -maxdepth 7 \\( -type f -o -type d \\) | sort | xargs ls -ldZ
echo A90_ACDBTAP_V2487_INSTALL_OK
""".strip()
    verify_script = f"""
set -eu
echo A90_ACDBTAP_V2487_VERIFY_BEGIN
for path in {shlex.quote(WRAPPER_PATH)} {shlex.quote(ORIGINAL_PATH)} {shlex.quote(TAP_PATH)}; do
  if [ ! -e "$path" ]; then
    echo A90_ACDBTAP_V2487_MISSING "$path"
    exit 71
  fi
  ls -lZ "$path"
  sha256sum "$path" 2>/dev/null || toybox sha256sum "$path"
done
echo A90_ACDBTAP_V2487_VERIFY_OK
""".strip()
    cleanup_script = f"""
set -eu
MODULE_DIR={shlex.quote(REMOTE_MODULE_DIR)}
MODULE_UPDATE_DIR={shlex.quote(REMOTE_MODULE_UPDATE_DIR)}
RUN_DIR={shlex.quote(REMOTE_DIR)}
echo A90_ACDBTAP_V2487_CLEANUP_BEGIN
rm -f "$MODULE_DIR/{WRAPPER_REL}" "$MODULE_DIR/{ORIGINAL_REL}" "$MODULE_DIR/{TAP_REL}" "$MODULE_DIR/module.prop" "$MODULE_DIR/README.md" "$MODULE_DIR/disable" "$MODULE_DIR/remove" 2>/dev/null || true
rmdir "$MODULE_DIR/system/vendor/bin/hw" "$MODULE_DIR/system/vendor/bin" "$MODULE_DIR/system/vendor/lib" "$MODULE_DIR/system/vendor" "$MODULE_DIR/system" "$MODULE_DIR" 2>/dev/null || true
rm -rf "$MODULE_UPDATE_DIR" "$RUN_DIR"
if [ -e "$MODULE_DIR" ] || [ -e "$MODULE_UPDATE_DIR" ]; then
  echo A90_ACDBTAP_V2487_CLEANUP_RESIDUE_PRESENT
  ls -la "$MODULE_DIR" "$MODULE_UPDATE_DIR" 2>&1 || true
  exit 72
fi
echo A90_ACDBTAP_V2487_CLEANUP_OK
""".strip()
    return {
        "stage_setup": ["adb", "shell", f"su -mm -c {shlex.quote(f'rm -rf {REMOTE_DIR}; mkdir -p {REMOTE_STAGE_DIR}/system/vendor/bin/hw {REMOTE_STAGE_DIR}/system/vendor/lib; chmod 755 {REMOTE_DIR}; chmod -R 777 {REMOTE_STAGE_DIR}')}"] ,
        "push_files": [["adb", "push", rel(path), f"{REMOTE_STAGE_DIR}/{name}"] for name, path in files.items()],
        "install_module_direct": ["adb", "shell", f"su -mm -c {shlex.quote(install_script)}"],
        "android_reboot_for_magisk_mount": ["adb", "reboot"],
        "verify_wrapper_after_reboot": ["adb", "shell", f"su -c {shlex.quote(verify_script)}"],
        "cleanup_exact_module": ["adb", "shell", f"su -mm -c {shlex.quote(cleanup_script)}"],
    }


def command_safety(payload: dict[str, Any]) -> dict[str, Any]:
    flat = json.dumps(payload.get("command_plan", payload), sort_keys=True)
    findings = []
    forbidden = {
        "native_cal_set_symbol": "AUDIO_SET_CALIBRATION",
        "native_cal_allocate_symbol": "AUDIO_ALLOCATE_CALIBRATION",
        "native_tinyplay": "tinyplay",
        "native_tinymix_set": "tinymix set",
        "fastboot": "fastboot",
        "raw_dd": " dd ",
        "silent_permissive": "setenforce 0",
        "magisk_install_module": "magisk --install-module",
        "service_script": "service.sh",
        "post_fs_data": "post-fs-data.sh",
        "sepolicy_rule": "sepolicy.rule",
        "rc_override": "android.hardware.audio.service.rc",
        "own_process_loader_guess": "acdb_loader_init_v4",
    }
    for name, needle in forbidden.items():
        if needle in flat:
            findings.append({"name": name, "needle": needle})
    required = [MODULE_ID, WRAPPER_REL, ORIGINAL_REL, TAP_REL, WRAPPER_PATH, ORIGINAL_PATH, TAP_PATH, "A90_ACDBTAP_V2487_VERIFY_OK", "A90_ACDBTAP_V2487_CLEANUP_OK"]
    missing = [needle for needle in required if needle not in json.dumps(payload, sort_keys=True)]
    return {"ok": not findings and not missing, "findings": findings, "missing_required_needles": missing, "forbidden": sorted(forbidden), "required": required}


def payload(args: argparse.Namespace) -> dict[str, Any]:
    module = materialize_module(args.module_out_dir, clang=args.clang, lld=args.lld, file_cmd=args.file) if args.materialize_module else {"ok": False, "reason": "not materialized"}
    plan = command_plan(args.module_out_dir)
    data: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2487-acdbtap-wrapper-exec-planner-host-only",
        "generated_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "android_action": "none",
        "module": module,
        "command_plan": plan,
        "command_safety": {},
        "future_live_gate": {
            "step": "wrapper-exec preflight only",
            "must_verify_before_playback": [
                "visible wrapper/original/tap paths and SHA-256",
                "wrapper path SELinux context and init exec success",
                "new audio HAL PID exe points to the preserved original path",
                "new audio HAL PID maps libacdbtap.so",
                "capture any linker/SELinux denial and stop",
            ],
            "no_playback_until_maps_confirmed": True,
        },
        "boundaries": {
            "no_native_msm_audio_cal_ioctls": True,
            "no_native_speaker_write": True,
            "no_service_rc_override": True,
            "no_policy_relaxation": True,
            "raw_bytes_private_only": True,
        },
    }
    data["command_safety"] = command_safety(data)
    data["ok"] = bool(module.get("ok") and data["command_safety"].get("ok"))
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module-out-dir", type=Path, default=DEFAULT_MODULE_OUT_DIR)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--clang", type=Path, default=TOOLCHAIN_ROOT / "bin/clang")
    parser.add_argument("--lld", type=Path, default=TOOLCHAIN_ROOT / "bin/ld.lld")
    parser.add_argument("--file", default="file")
    parser.add_argument("--materialize-module", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = payload(args)
    print(json.dumps({
        "decision": data["decision"],
        "ok": data["ok"],
        "module_out_dir": rel(args.module_out_dir),
        "wrapper_sha256": data.get("module", {}).get("wrapper_build", {}).get("artifact", {}).get("sha256"),
        "command_safety": data["command_safety"],
    }, indent=2, sort_keys=True))
    return 0 if data.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
