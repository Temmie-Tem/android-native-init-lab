#!/usr/bin/env python3
"""V2480 host-only planner for a temporary Magisk vendor-path ACDB tap capsule."""

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


RUN_ID = "V2480"
BUILD_TAG = "v2480-audio-acdbtap-vendor-preload-planner"
ROOT = v2476.ROOT
MODULE_ID = "a90_acdbtap_vendor_preload_v2480"
DEFAULT_MODULE_OUT_DIR = ROOT / "workspace/private/builds/audio/v2480-acdbtap-vendor-preload-module"
REMOTE_DIR = "/data/local/tmp/a90-acdbtap-v2480"
REMOTE_STAGE_DIR = f"{REMOTE_DIR}/module-stage"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_ID}"
REMOTE_MODULE_UPDATE_DIR = f"/data/adb/modules_update/{MODULE_ID}"
MODULE_LIB_REL = "system/vendor/lib/libacdbtap.so"
PRELOAD_CANDIDATES = [
    "/vendor/lib/libacdbtap.so",
    "/system/vendor/lib/libacdbtap.so",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    return v2476.rel(path)


def file_state(path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    return v2396.file_state(path, expected_sha256=expected_sha256)


def write_private(path: Path, data: bytes, mode: int) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chmod(path, mode)
    return {"path": rel(path), "mode": oct(mode), "size": path.stat().st_size, "sha256": v2396.sha256(path)}


def module_prop() -> str:
    return f"""id={MODULE_ID}
name=A90 ACDB Tap Vendor Preload V2480
version=0.1
versionCode=2480
author=A90 native-init project
description=Temporary measurement-only Magisk capsule exposing libacdbtap under a vendor linker namespace path.
"""


def readme() -> str:
    return """# A90 ACDB Tap Vendor Preload V2480

Private temporary Magisk measurement capsule.

Purpose: expose the V2475 32-bit `libacdbtap.so` under a vendor namespace-accessible path so
`android.hardware.audio.service` can be manually re-execed with `LD_PRELOAD` without using
`/data/local/tmp`, which Android's vendor linker namespace rejects.

This module contains no `service.sh`, `post-fs-data.sh`, `system.prop`, `sepolicy.rule`, or native
calibration replay logic. It is not a runtime dependency and must be removed before rollback.
"""


def materialize_module(out_dir: Path) -> dict[str, Any]:
    tap = v2476.TAP_SO
    tap_state = file_state(tap, expected_sha256=v2476.TAP_SHA256)
    if not tap_state.get("ok"):
        return {"ok": False, "reason": "V2475 libacdbtap artifact missing or SHA invalid", "tap": tap_state}
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    os.chmod(out_dir, 0o700)
    written = [
        write_private(out_dir / "module.prop", module_prop().encode(), 0o600),
        write_private(out_dir / "README.md", readme().encode(), 0o600),
    ]
    lib_target = out_dir / MODULE_LIB_REL
    lib_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tap, lib_target)
    os.chmod(lib_target, 0o644)
    written.append({"path": rel(lib_target), "mode": oct(0o644), "size": lib_target.stat().st_size, "sha256": v2396.sha256(lib_target)})
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
        "preload_candidates": PRELOAD_CANDIDATES,
        "tap_source": tap_state,
        "files": written,
        "forbidden_files_absent": forbidden_files_absent(out_dir),
        "private_only": True,
    }
    manifest["ok"] = bool(manifest["forbidden_files_absent"]["ok"] and file_state(lib_target, expected_sha256=v2476.TAP_SHA256).get("ok"))
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.chmod(out_dir / "manifest.json", 0o600)
    return manifest


def forbidden_files_absent(out_dir: Path) -> dict[str, Any]:
    forbidden = ["service.sh", "post-fs-data.sh", "system.prop", "sepolicy.rule"]
    present = [name for name in forbidden if (out_dir / name).exists()]
    return {"ok": not present, "forbidden": forbidden, "present": present}


def command_plan(module_out_dir: Path) -> dict[str, Any]:
    files = {
        "module.prop": module_out_dir / "module.prop",
        "README.md": module_out_dir / "README.md",
        MODULE_LIB_REL: module_out_dir / MODULE_LIB_REL,
    }
    install_script = f"""
set -eu
MODULE_DIR={REMOTE_MODULE_DIR!r}
MODULE_UPDATE_DIR={REMOTE_MODULE_UPDATE_DIR!r}
STAGE_DIR={REMOTE_STAGE_DIR!r}
LIB_REL={MODULE_LIB_REL!r}
echo A90_ACDBTAP_V2480_INSTALL_BEGIN
for path in "$MODULE_DIR" "$MODULE_UPDATE_DIR"; do
  if [ -e "$path" ]; then
    echo A90_ACDBTAP_V2480_RESIDUE_PRESENT "$path"
    exit 60
  fi
done
mkdir -p "$MODULE_DIR/system/vendor/lib"
cp "$STAGE_DIR/module.prop" "$MODULE_DIR/module.prop"
cp "$STAGE_DIR/README.md" "$MODULE_DIR/README.md"
cp "$STAGE_DIR/$LIB_REL" "$MODULE_DIR/$LIB_REL"
rm -f "$MODULE_DIR/disable" "$MODULE_DIR/remove"
chown -R 0:0 "$MODULE_DIR"
chmod 755 "$MODULE_DIR" "$MODULE_DIR/system" "$MODULE_DIR/system/vendor" "$MODULE_DIR/system/vendor/lib"
chmod 600 "$MODULE_DIR/module.prop" "$MODULE_DIR/README.md"
chmod 644 "$MODULE_DIR/$LIB_REL"
find "$MODULE_DIR" -maxdepth 5 -type f -o -type d | sort | xargs ls -ldZ
sha256sum "$MODULE_DIR/$LIB_REL" 2>/dev/null || toybox sha256sum "$MODULE_DIR/$LIB_REL"
echo A90_ACDBTAP_V2480_INSTALL_OK
""".strip()
    cleanup_script = f"""
set -eu
MODULE_DIR={REMOTE_MODULE_DIR!r}
MODULE_UPDATE_DIR={REMOTE_MODULE_UPDATE_DIR!r}
RUN_DIR={REMOTE_DIR!r}
echo A90_ACDBTAP_V2480_CLEANUP_BEGIN
rm -f "$MODULE_DIR/{MODULE_LIB_REL}" "$MODULE_DIR/module.prop" "$MODULE_DIR/README.md" \
  "$MODULE_DIR/disable" "$MODULE_DIR/remove" 2>/dev/null || true
rmdir "$MODULE_DIR/system/vendor/lib" "$MODULE_DIR/system/vendor" "$MODULE_DIR/system" "$MODULE_DIR" 2>/dev/null || true
rm -rf "$MODULE_UPDATE_DIR" "$RUN_DIR"
if [ -e "$MODULE_DIR" ] || [ -e "$MODULE_UPDATE_DIR" ]; then
  echo A90_ACDBTAP_V2480_CLEANUP_RESIDUE_PRESENT
  ls -la "$MODULE_DIR" "$MODULE_UPDATE_DIR" 2>&1 || true
  exit 61
fi
echo A90_ACDBTAP_V2480_CLEANUP_OK
""".strip()
    verify_script = f"""
set -eu
echo A90_ACDBTAP_V2480_VERIFY_BEGIN
for path in {' '.join(PRELOAD_CANDIDATES)}; do
  if [ -e "$path" ]; then
    ls -lZ "$path"
    sha256sum "$path" 2>/dev/null || toybox sha256sum "$path"
  else
    echo A90_ACDBTAP_V2480_PRELOAD_CANDIDATE_MISSING "$path"
  fi
done
echo A90_ACDBTAP_V2480_VERIFY_OK
""".strip()
    return {
        "stage_setup": ["adb", "shell", f"su -mm -c 'rm -rf {REMOTE_DIR!s}; mkdir -p {REMOTE_STAGE_DIR!s}/system/vendor/lib; chmod 755 {REMOTE_DIR!s}; chmod -R 777 {REMOTE_STAGE_DIR!s}'"],
        "push_files": [["adb", "push", rel(path), f"{REMOTE_STAGE_DIR}/{name}"] for name, path in files.items()],
        "install_module_direct": ["adb", "shell", f"su -mm -c {shlex.quote(install_script)}"],
        "android_reboot_for_magisk_mount": ["adb", "reboot"],
        "verify_vendor_visible_after_reboot": ["adb", "shell", f"su -c {shlex.quote(verify_script)}"],
        "cleanup_exact_module": ["adb", "shell", f"su -mm -c {shlex.quote(cleanup_script)}"],
        "retry_acdbtap_live_after_module": "reuse V2477 runner but replace LD_PRELOAD with first verified candidate path; no playback unless maps confirms libacdbtap",
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
    required = [MODULE_ID, MODULE_LIB_REL, "/vendor/lib/libacdbtap.so", "/system/vendor/lib/libacdbtap.so", "cleanup_exact_module"]
    missing = [needle for needle in required if needle not in required_flat]
    return {"ok": not findings and not missing, "findings": findings, "missing_required_needles": missing}


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    module = materialize_module(args.module_out_dir) if args.materialize_module else {"ok": False, "reason": "not materialized"}
    payload = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2480-acdbtap-vendor-preload-planner",
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
    parser.add_argument("--materialize-module", action="store_true", default=True)
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
