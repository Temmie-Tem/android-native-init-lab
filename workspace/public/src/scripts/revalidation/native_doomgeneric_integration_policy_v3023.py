#!/usr/bin/env python3
"""Host-only doomgeneric integration policy gate after the V3020 port probe."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import (
    write_private_text,
    write_public_text,
    workspace_private_build_path,
)


ROOT = repo_root()

RUN_ID = "V3023"
BUILD_TAG = "v3023-doomgeneric-integration-policy"
DECISION = "v3023-doomgeneric-private-integration-policy-ready"
SOURCE_URL = "https://github.com/ozkl/doomgeneric"
PINNED_COMMIT = "dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284"
SOURCE_ROOT = ROOT / "workspace/private/demo-assets/doom/doomgeneric-v3020"
SOURCE_DIR = SOURCE_ROOT / "doomgeneric"
PRIVATE_DOOM_ROOT = ROOT / "workspace/private/demo-assets/doom"
PRIVATE_WAD_ROOT_LABEL = "workspace/private/demo-assets/doom/wads/"
RUNTIME_WAD_ROOT = "/cache/a90-runtime/pkg/doom/v3024/"
OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
MANIFEST_PATH = OUT_DIR / "manifest.json"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3023_DOOMGENERIC_INTEGRATION_POLICY_2026-06-21.md"
V3020_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3020_DOOMGENERIC_PORT_PROBE_2026-06-21.md"
V3022_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3022_DEMO_CHECKPOINT_BADAPPLE_NYAN_LIVE_2026-06-21.md"
STATUS_SOURCE = ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
MENU_SOURCE = ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"

ENGINE_ONLY_BOOT_DELTA_CAP_BYTES = 2 * 1024 * 1024
RUNTIME_WAD_MAX_BYTES = 64 * 1024 * 1024
DEFAULT_PLAY_FRAMES = 300
MAX_PLAY_FRAMES = 5400


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(argv: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd) if cwd is not None else str(ROOT),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def git_output(args: list[str]) -> str | None:
    if not (SOURCE_ROOT / ".git").is_dir():
        return None
    result = run(["git", "-C", str(SOURCE_ROOT), *args])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def read_optional_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else None


def count_files(root: Path, suffix: str) -> dict[str, Any]:
    if not root.exists():
        return {"root": rel(root), "exists": False, "count": 0, "total_bytes": 0}
    normalized_suffix = suffix.lower()
    files = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.name.lower().endswith(normalized_suffix)
    ]
    return {
        "root": rel(root),
        "exists": True,
        "count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
    }


def collect_source_state() -> dict[str, Any]:
    source_files = [path for path in SOURCE_DIR.rglob("*") if path.is_file()] if SOURCE_DIR.exists() else []
    head = git_output(["rev-parse", "HEAD"])
    status = git_output(["status", "--short"]) if head else None
    return {
        "source_url": SOURCE_URL,
        "source_root": rel(SOURCE_ROOT),
        "source_exists": SOURCE_DIR.is_dir(),
        "git_head": head,
        "git_head_matches_pin": head == PINNED_COMMIT,
        "git_status_clean": status == "",
        "git_commit_date": git_output(["log", "-1", "--format=%cs"]) if head else None,
        "git_commit_subject": git_output(["log", "-1", "--format=%s"]) if head else None,
        "source_file_count": len(source_files),
        "license_sha256": sha256_file(SOURCE_ROOT / "LICENSE") if (SOURCE_ROOT / "LICENSE").exists() else None,
    }


def collect_report_evidence() -> dict[str, Any]:
    v3020 = read_optional_text(V3020_REPORT) or ""
    v3022 = read_optional_text(V3022_REPORT) or ""
    return {
        "v3020_report_present": bool(v3020),
        "v3020_port_probe_pass": "v3020-doomgeneric-private-source-build-probe-pass" in v3020,
        "v3020_aarch64_probe_linked": "AArch64 probe linked: `1`" in v3020,
        "v3020_no_public_wad": "Public WAD files committed/present: `0`" in v3020,
        "v3022_report_present": bool(v3022),
        "v3022_demo_checkpoint_pass": "v3022-demo-checkpoint-badapple-nyan-same-image-live-pass-before-rollback" in v3022,
        "v3022_rollback_health_ok": "Rollback health: version_ok=`1` selftest_fail0=`1`" in v3022,
    }


def collect_native_doom_status() -> dict[str, Any]:
    status_text = read_optional_text(STATUS_SOURCE) or ""
    menu_text = read_optional_text(MENU_SOURCE) or ""
    combined = status_text + "\n" + menu_text
    return {
        "status_source": rel(STATUS_SOURCE),
        "menu_source": rel(MENU_SOURCE),
        "doom_stub_marker_present": "video.status.doom_stub=1" in combined,
        "doompad_input_marker_present": "video.status.doom_input=serial-doompad-staged" in combined,
        "not_wad_backed_marker_present": "video.demo.engine=doompad-loop-not-doomgeneric" in combined,
        "wad_not_bundled_marker_present": "video.demo.asset.wad=not-bundled" in combined,
        "doom_play_command_present": "video demo doom play" in combined,
    }


def collect_state() -> dict[str, Any]:
    source = collect_source_state()
    reports = collect_report_evidence()
    native_status = collect_native_doom_status()
    public_wads = count_files(ROOT / "workspace/public", ".wad")
    private_wads = count_files(PRIVATE_DOOM_ROOT, ".wad")
    state: dict[str, Any] = {
        "run_id": RUN_ID,
        "decision": DECISION,
        "build_tag": BUILD_TAG,
        "source": source,
        "reports": reports,
        "native_status": native_status,
        "public_wads": public_wads,
        "private_wads": private_wads,
        "source_handling_policy": {
            "next_step": "private-build-only-native-init-integration",
            "public_vendoring_deferred": True,
            "third_party_source_commit_allowed_now": False,
            "public_vendoring_requirement": "GPL/NOTICE review before any third-party source enters workspace/public",
        },
        "asset_policy": {
            "commit_wad": False,
            "embed_wad_in_boot_image": False,
            "boot_image_wad_byte_limit": 0,
            "runtime_wad_root": RUNTIME_WAD_ROOT,
            "private_wad_root": PRIVATE_WAD_ROOT_LABEL,
            "runtime_wad_max_bytes": RUNTIME_WAD_MAX_BYTES,
            "runtime_wad_metadata_only_public": True,
        },
        "build_policy": {
            "next_run_id": "V3024",
            "next_build_type": "private-source native-init source integration without WAD",
            "engine_only_boot_delta_cap_bytes": ENGINE_ONLY_BOOT_DELTA_CAP_BYTES,
            "must_report_init_binary_delta": True,
            "must_report_boot_image_delta": True,
            "abort_if_any_wad_enters_ramdisk_or_boot": True,
        },
        "command_surface_policy": {
            "status": "video demo doom status",
            "verify": "video demo doom verify --wad runtime-private --sha256 EXPECTED",
            "play": "video demo doom play [frames] --wad runtime-private --sha256 EXPECTED",
            "default_play_frames": DEFAULT_PLAY_FRAMES,
            "max_play_frames": MAX_PLAY_FRAMES,
            "interruptible": True,
            "restore_menu_on_exit": True,
            "wad_path_allowlist_root": RUNTIME_WAD_ROOT,
        },
        "port_policy": {
            "frame_path": "doomgeneric DG_DrawFrame -> existing a90_kms_present/pageflip path",
            "input_path": "serial doompad snapshot edges -> doomgeneric DG_GetKey queue",
            "touch_or_otg_required": False,
            "evdev_injection": False,
            "sound_path": "disabled in first native engine integration; audio can be added later",
        },
        "safety": {
            "device_action": "none",
            "flash": False,
            "boot_image_written": False,
            "serial_command": False,
            "wad_copy": False,
            "wifi_action": False,
            "sysfs_write": False,
            "pmic_regulator_backlight_gpio_gdsc_write": False,
            "forbidden_partition_path": False,
        },
    }
    state["live_wad_ready"] = private_wads["count"] > 0
    state["safe_to_continue_host_only"] = bool(
        source["source_exists"]
        and source["git_head_matches_pin"]
        and source["git_status_clean"]
        and reports["v3020_port_probe_pass"]
        and reports["v3020_aarch64_probe_linked"]
        and reports["v3022_demo_checkpoint_pass"]
        and reports["v3022_rollback_health_ok"]
        and native_status["not_wad_backed_marker_present"]
        and native_status["doompad_input_marker_present"]
        and public_wads["count"] == 0
        and not state["asset_policy"]["commit_wad"]
        and not state["asset_policy"]["embed_wad_in_boot_image"]
    )
    state["next_unit"] = {
        "run_id": "V3024",
        "type": "private-source native-init integration build",
        "summary": (
            "Build a host-only/native-init source integration around the pinned private doomgeneric source, "
            "keeping WAD data runtime-private and absent from the boot image."
        ),
    }
    return state


def render_report(state: dict[str, Any]) -> str:
    source = state["source"]
    reports = state["reports"]
    native = state["native_status"]
    validation = [
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_integration_policy_v3023.py tests/test_native_doomgeneric_integration_policy_v3023.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_integration_policy_v3023`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doomgeneric_integration_policy_v3023.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_init_frontier_select`: PASS",
        "- `git diff --check`: PASS",
    ]
    return "\n".join([
        "# Native Init V3023 DOOMGENERIC Integration Policy",
        "",
        "## Summary",
        "",
        f"- Decision: `{state['decision']}`",
        "- Device action: `none` in this host-only unit.",
        "- Track: active Video playback / DOOM capstone.",
        "- Policy choice: keep the pinned doomgeneric source private for the next build-only native-init integration step.",
        f"- Private doomgeneric source pinned: `{int(bool(source['git_head_matches_pin']))}`",
        f"- Private source clean: `{int(bool(source['git_status_clean']))}`",
        f"- V3020 port probe pass: `{int(bool(reports['v3020_port_probe_pass']))}`",
        f"- V3020 AArch64 probe linked: `{int(bool(reports['v3020_aarch64_probe_linked']))}`",
        f"- V3022 checkpoint live pass retained: `{int(bool(reports['v3022_demo_checkpoint_pass']))}`",
        f"- Public WAD files committed/present: `{state['public_wads']['count']}`",
        f"- Runtime WAD currently staged: `{int(bool(state['live_wad_ready']))}`",
        f"- Safe next host-only unit: `{int(bool(state['safe_to_continue_host_only']))}`",
        "",
        "## Source Handling",
        "",
        f"- Source URL: `{source['source_url']}`",
        f"- Private source root: `{source['source_root']}`",
        f"- Pinned commit: `{PINNED_COMMIT}`",
        f"- Current commit: `{source['git_head']}`",
        f"- Commit date: `{source['git_commit_date']}`",
        f"- Commit subject: `{source['git_commit_subject']}`",
        f"- Source file count: `{source['source_file_count']}`",
        f"- LICENSE SHA256: `{source['license_sha256']}`",
        "- Public vendoring is deferred until a later GPL/NOTICE review; V3024 should only integrate from the private pinned source.",
        "",
        "## Current Native DOOM State",
        "",
        f"- Status source: `{native['status_source']}`",
        f"- Menu source: `{native['menu_source']}`",
        f"- DOOM stub marker present: `{int(bool(native['doom_stub_marker_present']))}`",
        f"- Doompad serial input marker present: `{int(bool(native['doompad_input_marker_present']))}`",
        f"- Current engine explicitly not WAD-backed: `{int(bool(native['not_wad_backed_marker_present']))}`",
        f"- WAD not-bundled marker present: `{int(bool(native['wad_not_bundled_marker_present']))}`",
        f"- `video demo doom play` command present: `{int(bool(native['doom_play_command_present']))}`",
        "",
        "## Asset Policy",
        "",
        "- WAD/IWAD data must not be committed.",
        "- WAD/IWAD data must not be embedded into a boot image or ramdisk.",
        f"- Runtime staging allowlist root: `{state['asset_policy']['runtime_wad_root']}`.",
        f"- Private WAD root for operator staging: `{state['asset_policy']['private_wad_root']}`.",
        f"- Runtime WAD size cap before first smoke: `{state['asset_policy']['runtime_wad_max_bytes']}` bytes.",
        "- Public reports may record WAD size and SHA256 only after a private WAD is intentionally staged.",
        "",
        "## Build Gate For V3024",
        "",
        f"- Build type: `{state['build_policy']['next_build_type']}`.",
        f"- Engine-only boot-image delta cap: `{state['build_policy']['engine_only_boot_delta_cap_bytes']}` bytes.",
        "- The V3024 build must report native-init binary delta and boot-image delta.",
        "- Abort V3024 if any `.wad` data appears in the ramdisk, boot image, or public tree.",
        "- Do not flash merely because the source integrates; first produce a host build/report and keep live validation rollback-gated.",
        "",
        "## Runtime Command Surface",
        "",
        f"- Status command: `{state['command_surface_policy']['status']}`.",
        f"- Verify command target: `{state['command_surface_policy']['verify']}`.",
        f"- Play command target: `{state['command_surface_policy']['play']}`.",
        f"- Default smoke frames: `{state['command_surface_policy']['default_play_frames']}`.",
        f"- Hard frame cap: `{state['command_surface_policy']['max_play_frames']}`.",
        "- The player must remain interruptible and restore the menu/HUD on exit.",
        "",
        "## Port Policy",
        "",
        f"- Frame path: {state['port_policy']['frame_path']}.",
        f"- Input path: {state['port_policy']['input_path']}.",
        "- OTG keyboard and touch are not required for this path; serial doompad remains the controller bridge.",
        "- Sound is disabled for the first native doomgeneric engine integration.",
        "",
        "## Safety",
        "",
        "- Host-only policy gate; no flash, serial command, WAD copy, Wi-Fi action, sysfs write, boot image write, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- The current runtime WAD is not staged, so a live WAD-backed DOOM smoke remains blocked until private WAD staging and hash metadata exist.",
        "",
        "## Host Validation",
        "",
        *validation,
        "",
        "## Next Unit",
        "",
        f"- Run ID: `{state['next_unit']['run_id']}`",
        f"- Type: `{state['next_unit']['type']}`",
        f"- Summary: {state['next_unit']['summary']}",
    ]) + "\n"


def main() -> int:
    state = collect_state()
    write_private_text(MANIFEST_PATH, json.dumps(state, indent=2, sort_keys=True) + "\n")
    write_public_text(REPORT_PATH, render_report(state))
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0 if state["safe_to_continue_host_only"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
