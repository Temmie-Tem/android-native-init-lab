#!/usr/bin/env python3
"""V2484 host-only planner for init-managed audio HAL ACDB tap preload.

V2481 proved that a parallel manual `android.hardware.audio.service` process can
map `libacdbtap.so` without becoming the process that handles Android audio. This
planner builds the next, stricter temporary Magisk capsule: expose the tap under
the vendor namespace and replace the vendor audio HAL init rc with an otherwise
identical service definition plus `setenv LD_PRELOAD`.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_android_measurement_planner_v2396 as v2396
import native_audio_acdbtap_live_planner_v2476 as v2476


RUN_ID = "V2484"
BUILD_TAG = "v2484-audio-acdbtap-service-env-planner"
ROOT = v2476.ROOT
MODULE_ID = "a90_acdbtap_service_env_v2484"
DEFAULT_MODULE_OUT_DIR = ROOT / "workspace/private/builds/audio/v2484-acdbtap-service-env-module"
REMOTE_DIR = "/data/local/tmp/a90-acdbtap-v2484"
REMOTE_STAGE_DIR = f"{REMOTE_DIR}/module-stage"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_ID}"
REMOTE_MODULE_UPDATE_DIR = f"/data/adb/modules_update/{MODULE_ID}"
MODULE_LIB_REL = "system/vendor/lib/libacdbtap.so"
MODULE_RC_REL = "system/vendor/etc/init/android.hardware.audio.service.rc"
VENDOR_LIB_PATH = "/vendor/lib/libacdbtap.so"
VENDOR_RC_PATH = "/vendor/etc/init/android.hardware.audio.service.rc"
CAPTURE_DIR = v2476.REMOTE_CAPTURE_DIR
RC_MARKER = "A90_ACDBTAP_V2484_RC_OVERRIDE"
PRELOAD_CANDIDATES = [VENDOR_LIB_PATH, "/system/vendor/lib/libacdbtap.so"]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    return v2476.rel(path)


def file_state(path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    return v2396.file_state(path, expected_sha256=expected_sha256)


def sha256(path: Path) -> str:
    return v2396.sha256(path)


def write_private(path: Path, text: str, mode: int) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    os.chmod(path, mode)
    return {"path": rel(path), "mode": oct(mode), "size": path.stat().st_size, "sha256": sha256(path)}


def module_prop() -> str:
    return f"""id={MODULE_ID}
name=A90 ACDB Tap Service Env V2484
version=0.1
versionCode=2484
author=A90 native-init project
description=Temporary measurement-only Magisk capsule adding LD_PRELOAD to the init-managed vendor audio HAL service.
"""


def readme() -> str:
    return f"""# A90 ACDB Tap Service Env V2484

Private temporary Magisk measurement capsule.

This module is stricter than V2480: it does not start a parallel HAL process.
Instead it exposes V2475 `libacdbtap.so` under the vendor linker namespace and
overlays the vendor audio HAL init rc so init starts `vendor.audio-hal` with:

- `LD_PRELOAD={VENDOR_LIB_PATH}`
- `A90_ACDBTAP_DIR={CAPTURE_DIR}`

It contains no `service.sh`, `post-fs-data.sh`, `system.prop`, `sepolicy.rule`,
or native calibration replay logic. It must be removed before rollback.
"""


def audio_hal_rc() -> str:
    return f"""# {RC_MARKER}
service vendor.audio-hal /vendor/bin/hw/android.hardware.audio.service
    class hal
    user audioserver
    # media gid needed for /dev/fm (radio) and for /data/misc/media (tee)
    group audio camera drmrpc inet media mediadrm net_bt net_bt_admin net_bw_acct wakelock
    capabilities BLOCK_SUSPEND
    setenv LD_PRELOAD {VENDOR_LIB_PATH}
    setenv A90_ACDBTAP_DIR {CAPTURE_DIR}
    ioprio rt 4
    task_profiles ProcessCapacityHigh HighPerformance
    onrestart restart audioserver
"""


def forbidden_files_absent(out_dir: Path) -> dict[str, Any]:
    forbidden = ["service.sh", "post-fs-data.sh", "system.prop", "sepolicy.rule"]
    present = [name for name in forbidden if (out_dir / name).exists()]
    return {"ok": not present, "forbidden": forbidden, "present": present}


def materialize_module(out_dir: Path) -> dict[str, Any]:
    tap = v2476.TAP_SO
    tap_state = file_state(tap, expected_sha256=v2476.TAP_SHA256)
    if not tap_state.get("ok"):
        return {"ok": False, "reason": "V2475 libacdbtap artifact missing or SHA invalid", "tap": tap_state}
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    os.chmod(out_dir, 0o700)

    files = [
        write_private(out_dir / "module.prop", module_prop(), 0o600),
        write_private(out_dir / "README.md", readme(), 0o600),
        write_private(out_dir / MODULE_RC_REL, audio_hal_rc(), 0o644),
    ]

    lib_target = out_dir / MODULE_LIB_REL
    lib_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tap, lib_target)
    os.chmod(lib_target, 0o644)
    files.append({"path": rel(lib_target), "mode": oct(0o644), "size": lib_target.stat().st_size, "sha256": sha256(lib_target)})

    for directory in [out_dir, *(path for path in out_dir.rglob("*") if path.is_dir())]:
        os.chmod(directory, 0o700)

    manifest = {
        "generated_at": now_iso(),
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "module_id": MODULE_ID,
        "module_out_dir": rel(out_dir),
        "remote_module_dir": REMOTE_MODULE_DIR,
        "module_lib_rel": MODULE_LIB_REL,
        "module_rc_rel": MODULE_RC_REL,
        "vendor_lib_path": VENDOR_LIB_PATH,
        "vendor_rc_path": VENDOR_RC_PATH,
        "capture_dir": CAPTURE_DIR,
        "rc_marker": RC_MARKER,
        "preload_candidates": PRELOAD_CANDIDATES,
        "tap_source": tap_state,
        "files": files,
        "forbidden_files_absent": forbidden_files_absent(out_dir),
        "private_only": True,
    }
    manifest["ok"] = bool(
        manifest["forbidden_files_absent"]["ok"]
        and file_state(lib_target, expected_sha256=v2476.TAP_SHA256).get("ok")
        and RC_MARKER in (out_dir / MODULE_RC_REL).read_text()
    )
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.chmod(out_dir / "manifest.json", 0o600)
    return manifest


def command_plan(module_out_dir: Path) -> dict[str, Any]:
    files = {
        "module.prop": module_out_dir / "module.prop",
        "README.md": module_out_dir / "README.md",
        MODULE_LIB_REL: module_out_dir / MODULE_LIB_REL,
        MODULE_RC_REL: module_out_dir / MODULE_RC_REL,
    }
    install_script = f"""
set -eu
MODULE_DIR={shlex.quote(REMOTE_MODULE_DIR)}
MODULE_UPDATE_DIR={shlex.quote(REMOTE_MODULE_UPDATE_DIR)}
STAGE_DIR={shlex.quote(REMOTE_STAGE_DIR)}
LIB_REL={shlex.quote(MODULE_LIB_REL)}
RC_REL={shlex.quote(MODULE_RC_REL)}
echo A90_ACDBTAP_V2484_INSTALL_BEGIN
for path in "$MODULE_DIR" "$MODULE_UPDATE_DIR"; do
  if [ -e "$path" ]; then
    echo A90_ACDBTAP_V2484_RESIDUE_PRESENT "$path"
    exit 60
  fi
done
mkdir -p "$MODULE_DIR/system/vendor/lib" "$MODULE_DIR/system/vendor/etc/init"
cp "$STAGE_DIR/module.prop" "$MODULE_DIR/module.prop"
cp "$STAGE_DIR/README.md" "$MODULE_DIR/README.md"
cp "$STAGE_DIR/$LIB_REL" "$MODULE_DIR/$LIB_REL"
cp "$STAGE_DIR/$RC_REL" "$MODULE_DIR/$RC_REL"
rm -f "$MODULE_DIR/disable" "$MODULE_DIR/remove"
chown -R 0:0 "$MODULE_DIR"
chmod 755 "$MODULE_DIR" "$MODULE_DIR/system" "$MODULE_DIR/system/vendor" "$MODULE_DIR/system/vendor/lib" "$MODULE_DIR/system/vendor/etc" "$MODULE_DIR/system/vendor/etc/init"
chmod 600 "$MODULE_DIR/module.prop" "$MODULE_DIR/README.md"
chmod 644 "$MODULE_DIR/$LIB_REL" "$MODULE_DIR/$RC_REL"
grep -q {shlex.quote(RC_MARKER)} "$MODULE_DIR/$RC_REL"
find "$MODULE_DIR" -maxdepth 6 \\( -type f -o -type d \\) | sort | xargs ls -ldZ
sha256sum "$MODULE_DIR/$LIB_REL" 2>/dev/null || toybox sha256sum "$MODULE_DIR/$LIB_REL"
echo A90_ACDBTAP_V2484_INSTALL_OK
""".strip()
    verify_script = f"""
set -eu
echo A90_ACDBTAP_V2484_VERIFY_BEGIN
for path in {' '.join(PRELOAD_CANDIDATES)}; do
  if [ -e "$path" ]; then
    ls -lZ "$path"
    sha256sum "$path" 2>/dev/null || toybox sha256sum "$path"
  else
    echo A90_ACDBTAP_V2484_PRELOAD_CANDIDATE_MISSING "$path"
  fi
done
if [ -e {shlex.quote(VENDOR_RC_PATH)} ]; then
  ls -lZ {shlex.quote(VENDOR_RC_PATH)}
  grep -n {shlex.quote(RC_MARKER)} {shlex.quote(VENDOR_RC_PATH)}
  grep -n 'setenv LD_PRELOAD' {shlex.quote(VENDOR_RC_PATH)}
  grep -n 'setenv A90_ACDBTAP_DIR' {shlex.quote(VENDOR_RC_PATH)}
else
  echo A90_ACDBTAP_V2484_RC_MISSING {shlex.quote(VENDOR_RC_PATH)}
  exit 62
fi
echo A90_ACDBTAP_V2484_VERIFY_OK
""".strip()
    cleanup_script = f"""
set -eu
MODULE_DIR={shlex.quote(REMOTE_MODULE_DIR)}
MODULE_UPDATE_DIR={shlex.quote(REMOTE_MODULE_UPDATE_DIR)}
RUN_DIR={shlex.quote(REMOTE_DIR)}
echo A90_ACDBTAP_V2484_CLEANUP_BEGIN
rm -f "$MODULE_DIR/{MODULE_LIB_REL}" "$MODULE_DIR/{MODULE_RC_REL}" \
  "$MODULE_DIR/module.prop" "$MODULE_DIR/README.md" \
  "$MODULE_DIR/disable" "$MODULE_DIR/remove" 2>/dev/null || true
rmdir "$MODULE_DIR/system/vendor/etc/init" "$MODULE_DIR/system/vendor/etc" \
  "$MODULE_DIR/system/vendor/lib" "$MODULE_DIR/system/vendor" \
  "$MODULE_DIR/system" "$MODULE_DIR" 2>/dev/null || true
rm -rf "$MODULE_UPDATE_DIR" "$RUN_DIR"
if [ -e "$MODULE_DIR" ] || [ -e "$MODULE_UPDATE_DIR" ]; then
  echo A90_ACDBTAP_V2484_CLEANUP_RESIDUE_PRESENT
  ls -la "$MODULE_DIR" "$MODULE_UPDATE_DIR" 2>&1 || true
  exit 61
fi
echo A90_ACDBTAP_V2484_CLEANUP_OK
""".strip()
    return {
        "stage_setup": [
            "adb",
            "shell",
            f"su -mm -c {shlex.quote(f'rm -rf {REMOTE_DIR}; mkdir -p {REMOTE_STAGE_DIR}/system/vendor/lib {REMOTE_STAGE_DIR}/system/vendor/etc/init; chmod 755 {REMOTE_DIR}; chmod -R 777 {REMOTE_STAGE_DIR}')}",
        ],
        "push_files": [["adb", "push", rel(path), f"{REMOTE_STAGE_DIR}/{name}"] for name, path in files.items()],
        "install_module_direct": ["adb", "shell", f"su -mm -c {shlex.quote(install_script)}"],
        "android_reboot_for_magisk_mount": ["adb", "reboot"],
        "verify_service_env_after_reboot": ["adb", "shell", f"su -c {shlex.quote(verify_script)}"],
        "cleanup_exact_module": ["adb", "shell", f"su -mm -c {shlex.quote(cleanup_script)}"],
    }


def command_safety(payload: dict[str, Any]) -> dict[str, Any]:
    command_flat = json.dumps(payload.get("command_plan", payload), sort_keys=True)
    required_flat = json.dumps(payload, sort_keys=True)
    forbidden = {
        "native_calibration": "AUDIO_SET_CALIBRATION",
        "native_playback": "tinyplay",
        "silent_permissive": "setenforce 0",
        "broad_modules_delete": "rm -rf /data/adb/modules",
        "magisk_install_module": "magisk --install-module",
        "post_fs_data": "post-fs-data.sh",
        "service_script": "service.sh",
        "sepolicy_rule": "sepolicy.rule",
    }
    findings = [{"name": name, "needle": needle} for name, needle in forbidden.items() if needle in command_flat]
    required = [
        MODULE_ID,
        MODULE_LIB_REL,
        MODULE_RC_REL,
        VENDOR_LIB_PATH,
        VENDOR_RC_PATH,
        RC_MARKER,
        "setenv LD_PRELOAD",
        "setenv A90_ACDBTAP_DIR",
        "cleanup_exact_module",
    ]
    missing = [needle for needle in required if needle not in required_flat]
    return {"ok": not findings and not missing, "findings": findings, "missing_required_needles": missing}


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    module = materialize_module(args.module_out_dir) if args.materialize_module else {"ok": False, "reason": "not materialized"}
    payload = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2484-acdbtap-service-env-planner-host-only",
        "generated_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "module": module,
        "command_plan": command_plan(args.module_out_dir),
        "live_boundary": "future Android handoff only; this unit does not install module or run playback",
        "partial_success_policy": "captured-acdbtap-full-outbuf-set-no-4916 remains operator-valuable partial success",
    }
    payload["command_safety"] = command_safety(payload)
    payload["ok"] = bool(payload["command_safety"]["ok"] and (not args.materialize_module or module.get("ok")))
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module-out-dir", type=Path, default=DEFAULT_MODULE_OUT_DIR)
    parser.add_argument("--materialize-module", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    print(json.dumps({
        "decision": payload["decision"],
        "ok": payload["ok"],
        "module_ok": payload["module"].get("ok"),
        "module_out_dir": payload["module"].get("module_out_dir"),
        "command_safety": payload["command_safety"],
    }, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
