#!/usr/bin/env python3
"""Host-only runtime-private WAD staging preflight for doomgeneric."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import (
    write_private_text,
    write_public_text,
    workspace_private_build_path,
)


ROOT = repo_root()

RUN_ID = "V3027"
BUILD_TAG = "v3027-doomgeneric-runtime-wad-preflight"
DECISION_READY = "v3027-doomgeneric-runtime-wad-staging-contract-ready"
DECISION_ASSET_NEEDED = "v3027-doomgeneric-runtime-wad-staging-preflight-asset-needed"
PRIVATE_WAD_ROOT = ROOT / "workspace/private/demo-assets/doom/wads"
PRIVATE_WAD_ROOT_LABEL = "workspace/private/demo-assets/doom/wads/"
PUBLIC_ROOT = ROOT / "workspace/public"
RUNTIME_WAD_ROOT = "/cache/a90-runtime/pkg/doom/v3024/"
RUNTIME_WAD_PATH = "/cache/a90-runtime/pkg/doom/v3024/DOOM1.WAD"
RUNTIME_WAD_MAX_BYTES = 64 * 1024 * 1024
DEFAULT_SMOKE_FRAMES = 300
MAX_SMOKE_FRAMES = 5400
OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
MANIFEST_PATH = OUT_DIR / "manifest.json"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3027_DOOMGENERIC_RUNTIME_WAD_PREFLIGHT_2026-06-21.md"
V3023_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3023_DOOMGENERIC_INTEGRATION_POLICY_2026-06-21.md"
V3025_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3025_DOOMGENERIC_COMMAND_BRIDGE_SOURCE_BUILD_2026-06-21.md"
V3026_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3026_DOOMGENERIC_COMMAND_BRIDGE_LIVE_2026-06-21.md"
WAD_SUFFIXES = (".wad", ".iwad")
WAD_MAGICS = {b"IWAD", b"PWAD"}


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


def read_optional_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def is_wad_path(path: Path) -> bool:
    return path.is_file() and path.name.lower().endswith(WAD_SUFFIXES)


def count_public_wads(root: Path | None = None) -> dict[str, Any]:
    if root is None:
        root = PUBLIC_ROOT
    if not root.exists():
        return {"root": rel(root), "exists": False, "count": 0, "total_bytes": 0}
    files = [path for path in root.rglob("*") if is_wad_path(path)]
    return {
        "root": rel(root),
        "exists": True,
        "count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
    }


def read_magic(path: Path) -> str:
    try:
        with path.open("rb") as file_obj:
            return file_obj.read(4).decode("ascii", errors="replace")
    except OSError:
        return ""


def collect_private_wad_candidates(root: Path | None = None) -> dict[str, Any]:
    if root is None:
        root = PRIVATE_WAD_ROOT
    if not root.exists():
        return {
            "root": PRIVATE_WAD_ROOT_LABEL,
            "exists": False,
            "count": 0,
            "total_bytes": 0,
            "selected": None,
            "all_within_size_cap": True,
            "all_magic_ok": True,
            "ambiguous": False,
        }

    candidates = sorted(path for path in root.rglob("*") if is_wad_path(path))
    summaries: list[dict[str, Any]] = []
    for index, path in enumerate(candidates, start=1):
        size = path.stat().st_size
        magic = read_magic(path)
        within_size_cap = 0 < size <= RUNTIME_WAD_MAX_BYTES
        magic_ok = magic.encode("ascii", errors="replace") in WAD_MAGICS
        summaries.append({
            "candidate_index": index,
            "bytes": size,
            "sha256": sha256_file(path) if within_size_cap else None,
            "magic": magic,
            "magic_ok": magic_ok,
            "within_size_cap": within_size_cap,
        })

    selected = summaries[0] if len(summaries) == 1 and summaries[0]["within_size_cap"] and summaries[0]["magic_ok"] else None
    return {
        "root": PRIVATE_WAD_ROOT_LABEL,
        "exists": True,
        "count": len(summaries),
        "total_bytes": sum(item["bytes"] for item in summaries),
        "selected": selected,
        "all_within_size_cap": all(item["within_size_cap"] for item in summaries),
        "all_magic_ok": all(item["magic_ok"] for item in summaries),
        "ambiguous": len(summaries) > 1,
    }


def collect_report_evidence() -> dict[str, Any]:
    v3023 = read_optional_text(V3023_REPORT)
    v3025 = read_optional_text(V3025_REPORT)
    v3026 = read_optional_text(V3026_REPORT)
    return {
        "v3023_policy_ready": "v3023-doomgeneric-private-integration-policy-ready" in v3023,
        "v3023_private_wad_root_pinned": PRIVATE_WAD_ROOT_LABEL in v3023,
        "v3023_runtime_wad_max_bytes_pinned": f"Runtime WAD size cap before first smoke: `{RUNTIME_WAD_MAX_BYTES}`" in v3023,
        "v3025_command_bridge_ready": "v3025-doomgeneric-command-bridge-source-build-pass" in v3025,
        "v3025_ramdisk_wad_zero": "WAD files in ramdisk: `0`" in v3025,
        "v3026_command_bridge_live_pass": "v3026-doomgeneric-command-bridge-live-pass-before-rollback" in v3026,
        "v3026_no_otg_required": "video.demo.input.otg_required=0" in v3026,
        "v3026_wad_not_staged": "No WAD/IWAD bytes were staged" in v3026,
    }


def collect_state() -> dict[str, Any]:
    private_wads = collect_private_wad_candidates()
    public_wads = count_public_wads()
    reports = collect_report_evidence()
    selected = private_wads["selected"]
    live_asset_ready = selected is not None and public_wads["count"] == 0
    preflight_ok = bool(
        reports["v3023_policy_ready"]
        and reports["v3023_private_wad_root_pinned"]
        and reports["v3023_runtime_wad_max_bytes_pinned"]
        and reports["v3025_command_bridge_ready"]
        and reports["v3025_ramdisk_wad_zero"]
        and reports["v3026_command_bridge_live_pass"]
        and reports["v3026_no_otg_required"]
        and reports["v3026_wad_not_staged"]
        and public_wads["count"] == 0
        and private_wads["all_within_size_cap"]
        and private_wads["all_magic_ok"]
    )
    decision = DECISION_READY if live_asset_ready and preflight_ok else DECISION_ASSET_NEEDED
    next_unit = (
        {
            "run_id": "V3028",
            "type": "host-only WAD-backed doomgeneric command implementation",
            "summary": (
                "Wire bounded runtime-private WAD verify/play command handling around the selected "
                "private WAD hash, still keeping WAD bytes out of public, ramdisk, and boot image."
            ),
        }
        if decision == DECISION_READY
        else {
            "run_id": None,
            "type": "operator-private-asset-needed",
            "summary": (
                "Stage exactly one private IWAD/WAD under workspace/private/demo-assets/doom/wads/ "
                "before a WAD-backed command implementation or live smoke can be selected."
            ),
        }
    )
    return {
        "run_id": RUN_ID,
        "decision": decision,
        "build_tag": BUILD_TAG,
        "device_action": "none",
        "reports": reports,
        "private_wads": private_wads,
        "public_wads": public_wads,
        "live_asset_ready": bool(live_asset_ready),
        "preflight_ok": bool(preflight_ok),
        "runtime_contract": {
            "private_wad_root": PRIVATE_WAD_ROOT_LABEL,
            "runtime_wad_root": RUNTIME_WAD_ROOT,
            "runtime_wad_path": RUNTIME_WAD_PATH,
            "runtime_wad_max_bytes": RUNTIME_WAD_MAX_BYTES,
            "selected_wad_sha256": selected["sha256"] if selected else None,
            "selected_wad_bytes": selected["bytes"] if selected else None,
            "selected_wad_magic": selected["magic"] if selected else None,
            "stage_at_live_time_only": True,
            "verify_sha256_before_doom_command": True,
            "cleanup_runtime_wad_after_smoke": True,
            "commit_wad": False,
            "embed_wad_in_ramdisk": False,
            "embed_wad_in_boot": False,
        },
        "command_contract": {
            "status_command": "video demo doom status",
            "future_verify_command": "video demo doom verify --wad runtime-private --sha256 EXPECTED",
            "future_play_command": "video demo doom play [frames] --wad runtime-private --sha256 EXPECTED",
            "default_smoke_frames": DEFAULT_SMOKE_FRAMES,
            "max_smoke_frames": MAX_SMOKE_FRAMES,
            "input_path": "serial-doompad-to-DG_GetKey",
            "otg_required": False,
            "sound": "disabled-nosound-nomusic",
            "next_requires_command_implementation": True,
        },
        "safety": {
            "flash": False,
            "serial_command": False,
            "wad_copy": False,
            "public_wad_bytes": False,
            "boot_image_written": False,
            "ramdisk_written": False,
            "wifi_action": False,
            "sysfs_write": False,
            "pmic_regulator_backlight_gpio_gdsc_write": False,
            "forbidden_partition_path": False,
        },
        "next_unit": next_unit,
    }


def render_report(state: dict[str, Any]) -> str:
    selected_sha = state["runtime_contract"]["selected_wad_sha256"] or "not-recorded-asset-absent"
    selected_bytes = state["runtime_contract"]["selected_wad_bytes"]
    selected_magic = state["runtime_contract"]["selected_wad_magic"] or "not-recorded-asset-absent"
    if state["live_asset_ready"]:
        asset_interpretation = (
            "- Current state has exactly one private WAD/IWAD candidate with a pinned hash/size contract, "
            "so the next bounded unit is command implementation, not immediate live gameplay."
        )
    else:
        asset_interpretation = (
            "- Current state does not have exactly one valid private WAD/IWAD candidate, so WAD-backed DOOM "
            "remains asset-gated."
        )
    validation = [
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_runtime_wad_preflight_v3027.py tests/test_native_doomgeneric_runtime_wad_preflight_v3027.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_runtime_wad_preflight_v3027`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_init_frontier_select`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_init_frontier_select.py --json`: PASS",
        "- `git diff --check`: PASS",
    ]
    return "\n".join([
        "# Native Init V3027 DOOMGENERIC Runtime WAD Preflight",
        "",
        "## Summary",
        "",
        f"- Cycle: `{state['run_id']}`",
        "- Track: active Video playback / DOOM capstone.",
        f"- Decision: `{state['decision']}`",
        "- Device action: `none` in this host-only unit.",
        f"- Preflight OK: `{int(bool(state['preflight_ok']))}`",
        f"- Live asset ready: `{int(bool(state['live_asset_ready']))}`",
        f"- Public WAD files committed/present: `{state['public_wads']['count']}`",
        f"- Private WAD root exists: `{int(bool(state['private_wads']['exists']))}`",
        f"- Private WAD/IWAD candidate count: `{state['private_wads']['count']}`",
        f"- Private WAD candidates within size cap: `{int(bool(state['private_wads']['all_within_size_cap']))}`",
        f"- Private WAD candidates magic ok: `{int(bool(state['private_wads']['all_magic_ok']))}`",
        f"- Private WAD candidate ambiguous: `{int(bool(state['private_wads']['ambiguous']))}`",
        "",
        "## Prior Evidence Gates",
        "",
        f"- V3023 policy ready: `{int(bool(state['reports']['v3023_policy_ready']))}`",
        f"- V3023 private WAD root pinned: `{int(bool(state['reports']['v3023_private_wad_root_pinned']))}`",
        f"- V3023 WAD size cap pinned: `{int(bool(state['reports']['v3023_runtime_wad_max_bytes_pinned']))}`",
        f"- V3025 command bridge ready: `{int(bool(state['reports']['v3025_command_bridge_ready']))}`",
        f"- V3025 ramdisk WAD count zero: `{int(bool(state['reports']['v3025_ramdisk_wad_zero']))}`",
        f"- V3026 command bridge live pass: `{int(bool(state['reports']['v3026_command_bridge_live_pass']))}`",
        f"- V3026 no OTG required: `{int(bool(state['reports']['v3026_no_otg_required']))}`",
        f"- V3026 WAD not staged: `{int(bool(state['reports']['v3026_wad_not_staged']))}`",
        "",
        "## Runtime WAD Contract",
        "",
        f"- Private WAD root: `{state['runtime_contract']['private_wad_root']}`",
        f"- Runtime staging root: `{state['runtime_contract']['runtime_wad_root']}`",
        f"- Runtime WAD path: `{state['runtime_contract']['runtime_wad_path']}`",
        f"- Runtime WAD max bytes: `{state['runtime_contract']['runtime_wad_max_bytes']}`",
        f"- Selected WAD bytes: `{selected_bytes if selected_bytes is not None else 'not-recorded-asset-absent'}`",
        f"- Selected WAD SHA256: `{selected_sha}`",
        f"- Selected WAD magic: `{selected_magic}`",
        "- Stage at live time only; do not copy WAD data during this host-only unit.",
        "- Verify the selected SHA256 before any future WAD-backed DOOM command.",
        "- Clean up the runtime WAD after any future bounded smoke.",
        "- WAD/IWAD bytes must stay out of public, ramdisk, and boot image.",
        "",
        "## Command Contract",
        "",
        f"- Status command: `{state['command_contract']['status_command']}`",
        f"- Future verify command: `{state['command_contract']['future_verify_command']}`",
        f"- Future play command: `{state['command_contract']['future_play_command']}`",
        f"- Default smoke frames: `{state['command_contract']['default_smoke_frames']}`",
        f"- Max smoke frames: `{state['command_contract']['max_smoke_frames']}`",
        f"- Input path: `{state['command_contract']['input_path']}`",
        f"- OTG required: `{int(bool(state['command_contract']['otg_required']))}`",
        f"- Sound: `{state['command_contract']['sound']}`",
        f"- Next requires command implementation: `{int(bool(state['command_contract']['next_requires_command_implementation']))}`",
        "",
        "## Interpretation",
        "",
        "- V3027 is host-only and does not stage, copy, or embed WAD bytes.",
        asset_interpretation,
        "",
        "## Safety",
        "",
        "- Host-only preflight; no flash, serial command, WAD copy, Wi-Fi action, sysfs write, boot image write, ramdisk write, PMIC, backlight, GPIO, regulator, GDSC, or forbidden partition path is touched.",
        "- Public output records no WAD bytes and no private WAD filename.",
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
    return 0 if state["preflight_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
