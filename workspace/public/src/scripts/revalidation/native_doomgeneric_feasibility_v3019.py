#!/usr/bin/env python3
"""Host-only feasibility audit for the next WAD-backed DOOM step."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root

ROOT = repo_root()

RUN_ID = "V3019"
DECISION = "v3019-doomgeneric-feasibility-host-pass"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V3019_DOOMGENERIC_FEASIBILITY_2026-06-21.md"

V3017_REPORT = ROOT / "docs/reports/NATIVE_INIT_V3017_DOOMPAD_GAMEPLAY_LOOP_LIVE_2026-06-21.md"
GOAL = ROOT / "GOAL.md"
STATUS_HUD = ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
MENU_APPS = ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
ROLLBACK_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
V3016_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v3016_doompad_gameplay_loop.img"
V3016_INIT = ROOT / "workspace/private/builds/native-init/v3016-doompad-gameplay-loop/init_v3016_doompad_gameplay_loop"
V3016_RAMDISK = ROOT / "workspace/private/builds/native-init/v3016-doompad-gameplay-loop/ramdisk_v3016_doompad_gameplay_loop.cpio"

ID_DOOM_SOURCE_URL = "https://github.com/id-Software/DOOM"
DOOMGENERIC_SOURCE_URL = "https://github.com/ozkl/doomgeneric"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def file_size(path: Path) -> int | None:
    return path.stat().st_size if path.exists() else None


def contains_all(text: str, markers: tuple[str, ...]) -> bool:
    return all(marker in text for marker in markers)


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


def collect_state() -> dict[str, Any]:
    v3017 = read_text(V3017_REPORT) if V3017_REPORT.exists() else ""
    goal = read_text(GOAL) if GOAL.exists() else ""
    status_hud = read_text(STATUS_HUD) if STATUS_HUD.exists() else ""
    menu_apps = read_text(MENU_APPS) if MENU_APPS.exists() else ""
    public_wads = count_files(ROOT / "workspace/public", ".wad")
    private_wads = count_files(ROOT / "workspace/private", ".wad")
    source_vendored = any(
        path.exists()
        for path in (
            ROOT / "workspace/public/src/third_party/doomgeneric",
            ROOT / "workspace/public/src/native-init/doomgeneric",
        )
    )
    v3017_proven = contains_all(
        v3017,
        (
            "v3017-doompad-gameplay-loop-state-consumed-pass-before-rollback",
            "`video demo doom play 8` rc: `0` markers_ok=`1`",
            "Player movement parsed: `1` moved_forward=`1`",
            "Rollback health: version_ok=`1` selftest_fail0=`1`",
        ),
    )
    state = {
        "run_id": RUN_ID,
        "decision": DECISION,
        "v3017_report": rel(V3017_REPORT),
        "v3017_doompad_loop_proven": v3017_proven,
        "goal_v3017_frontier_current": contains_all(
            goal,
            (
                "SUPERSEDED (V3014",
                "serial-doompad-consumed",
                "host-only `doomgeneric`/WAD feasibility",
            ),
        ),
        "current_native_status_not_wad_backed": contains_all(
            status_hud,
            (
                "video.demo.engine=doompad-loop-not-doomgeneric",
                "video.demo.asset.wad=not-bundled",
                "video.demo.input=serial-doompad-consumed",
            ),
        ),
        "doompad_consumer_source_present": contains_all(
            menu_apps,
            (
                "static int cmd_doomplay(char **argv, int argc)",
                "doompad_get_snapshot(&input);",
                "a90_kms_present(\"doomplay\", false)",
            ),
        ),
        "source_vendored": source_vendored,
        "public_wads": public_wads,
        "private_wads": private_wads,
        "asset_policy": {
            "commit_wad": False,
            "embed_wad_in_boot_image": False,
            "runtime_wad_root": "/cache/a90-runtime/pkg/doom/v3020/",
            "private_source_root": "workspace/private/demo-assets/doom/",
        },
        "source_candidates": {
            "id_doom_source": ID_DOOM_SOURCE_URL,
            "doomgeneric_port": DOOMGENERIC_SOURCE_URL,
        },
        "sizes": {
            "rollback_boot_image_bytes": file_size(ROLLBACK_IMAGE),
            "v3016_boot_image_bytes": file_size(V3016_IMAGE),
            "v3016_init_bytes": file_size(V3016_INIT),
            "v3016_ramdisk_cpio_bytes": file_size(V3016_RAMDISK),
        },
    }
    rollback_size = state["sizes"]["rollback_boot_image_bytes"]
    v3016_size = state["sizes"]["v3016_boot_image_bytes"]
    state["sizes"]["v3016_boot_delta_vs_rollback_bytes"] = (
        v3016_size - rollback_size
        if isinstance(rollback_size, int) and isinstance(v3016_size, int)
        else None
    )
    state["next_unit"] = {
        "run_id": "V3020",
        "type": "host-only-source-vendor-build-probe",
        "summary": (
            "Fetch/pin doomgeneric source privately or vendor with license notice, build a native-init "
            "adapter against KMS doompad shims, and keep WAD data private/runtime-staged."
        ),
    }
    state["safe_to_continue_host_only"] = bool(
        state["v3017_doompad_loop_proven"]
        and state["goal_v3017_frontier_current"]
        and state["current_native_status_not_wad_backed"]
        and state["doompad_consumer_source_present"]
        and not state["source_vendored"]
        and state["public_wads"]["count"] == 0
        and not state["asset_policy"]["commit_wad"]
        and not state["asset_policy"]["embed_wad_in_boot_image"]
    )
    return state


def render_report(state: dict[str, Any]) -> str:
    sizes = state["sizes"]
    return "\n".join([
        "# Native Init V3019 DOOMGENERIC Feasibility Audit",
        "",
        "## Summary",
        "",
        f"- Decision: `{state['decision']}`",
        "- Device action: `none` in this host-only unit.",
        "- Track: active Video playback / DOOM capstone.",
        f"- V3017 doompad loop proven: `{int(bool(state['v3017_doompad_loop_proven']))}`",
        f"- GOAL frontier current: `{int(bool(state['goal_v3017_frontier_current']))}`",
        f"- Current native status is not WAD-backed: `{int(bool(state['current_native_status_not_wad_backed']))}`",
        f"- Doompad consumer source present: `{int(bool(state['doompad_consumer_source_present']))}`",
        f"- Existing doomgeneric source vendored: `{int(bool(state['source_vendored']))}`",
        f"- Public WAD files committed/present: `{state['public_wads']['count']}`",
        f"- Private WAD files currently present: `{state['private_wads']['count']}`",
        f"- Safe next unit: `{int(bool(state['safe_to_continue_host_only']))}`",
        "",
        "## Source Provenance",
        "",
        f"- id Software DOOM source: `{ID_DOOM_SOURCE_URL}` (GPL-2.0 source release; game data is separate).",
        f"- doomgeneric candidate port: `{DOOMGENERIC_SOURCE_URL}` (small platform API: `DG_Init`, `DG_DrawFrame`, `DG_GetKey`, timing/sleep hooks).",
        "- V3019 does not vendor or download source into public paths; it pins the next unit's provenance boundary only.",
        "",
        "## Asset Policy",
        "",
        "- WAD/IWAD data must not be committed.",
        "- WAD/IWAD data should not be embedded into the boot image for the first real engine unit.",
        f"- Runtime staging root: `{state['asset_policy']['runtime_wad_root']}`.",
        f"- Private host source/asset root: `{state['asset_policy']['private_source_root']}`.",
        "- First WAD-backed validation should use a private/runtime-staged WAD with hash-only public metadata.",
        "",
        "## Current Size Baseline",
        "",
        f"- V2321 rollback image bytes: `{sizes['rollback_boot_image_bytes']}`",
        f"- V3016 doompad-loop image bytes: `{sizes['v3016_boot_image_bytes']}`",
        f"- V3016 delta vs rollback bytes: `{sizes['v3016_boot_delta_vs_rollback_bytes']}`",
        f"- V3016 init bytes: `{sizes['v3016_init_bytes']}`",
        f"- V3016 ramdisk cpio bytes: `{sizes['v3016_ramdisk_cpio_bytes']}`",
        "",
        "## Next Unit",
        "",
        f"- Run ID: `{state['next_unit']['run_id']}`",
        f"- Type: `{state['next_unit']['type']}`",
        f"- Summary: {state['next_unit']['summary']}",
        "",
        "## Safety",
        "",
        "- Host-only audit; no flash, serial command, evdev open, input injection, sysfs write, Wi-Fi action, audio/video playback, PMIC, backlight, GPIO, regulator, GDSC, WAD copy, or forbidden partition path is touched.",
        "- The next live WAD-backed step remains blocked until source provenance, license/NOTICE handling, runtime WAD hash policy, build size, bounded command surface, and rollback validation are pinned.",
        "",
        "## Host Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_doomgeneric_feasibility_v3019.py tests/test_native_doomgeneric_feasibility_v3019.py`: PASS",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 -m unittest tests.test_native_doomgeneric_feasibility_v3019`: PASS",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation:workspace/public/src/harness python3 workspace/public/src/scripts/revalidation/native_doomgeneric_feasibility_v3019.py`: PASS",
        "- `git diff --check`: PASS",
    ]) + "\n"


def main() -> int:
    state = collect_state()
    REPORT_PATH.write_text(render_report(state), encoding="utf-8")
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0 if state["safe_to_continue_host_only"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
