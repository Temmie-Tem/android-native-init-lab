#!/usr/bin/env python3
"""V758 host-only kernel/source/boot-image instrumentation feasibility.

V757 selected rollback-safe kernel/source/boot-image log instrumentation as the
next route, but no patch should be attempted until source availability, build
tooling, boot image artifacts, and rollback controls are classified. This
classifier is host-only and performs no device action.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v758-kernel-instrumentation-feasibility")
DEFAULT_V757_MANIFEST = Path("tmp/wifi/v757-android-native-hdd-pld-diff/manifest.json")

LOCAL_SOURCE_CANDIDATES = (
    Path("SM-A908N_KOR_12_Opensource"),
    Path("kernel"),
    Path("android_kernel_samsung"),
    Path("drivers/staging/qcacld-3.0"),
    Path("drivers/net/wireless/cnss2"),
    Path("drivers/net/wireless"),
)

TARGET_SOURCE_PATHS = (
    "drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
    "drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c",
    "drivers/net/wireless/cnss2/main.c",
    "drivers/net/wireless/cnss2/qmi.c",
)

BOOT_IMAGE_CANDIDATES = (
    Path("stage3/boot_linux_v724.img"),
    Path("stage3/boot_linux_v319.img"),
    Path("stage3/boot_linux_v261.img"),
    Path("stage3/boot_linux_v48.img"),
)

TOOLING_CANDIDATES = (
    Path("scripts/revalidation/build_native_init_boot_v724.py"),
    Path("scripts/revalidation/native_init_flash.py"),
    Path("mkbootimg/unpack_bootimg.py"),
    Path("mkbootimg/mkbootimg.py"),
    Path("mkbootimg/repack_bootimg.py"),
    Path("docs/reports/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_2026-05-13.md"),
    Path("docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md"),
)

EXTERNAL_SOURCE_REFS = [
    {
        "name": "samsung-open-source-release-center",
        "url": "https://opensource.samsung.com/?method=search",
        "signal": "official Samsung release center search is the primary source acquisition route",
    },
    {
        "name": "samfw-a908n-ewa3-firmware",
        "url": "https://samfw.com/firmware/SM-A908N/KOO/A908NKSU5EWA3",
        "signal": "exact device firmware is SM-A908N KOO A908NKSU5EWA3 Android 12",
    },
    {
        "name": "sammobile-a908n-firmware-list",
        "url": "https://www.sammobile.com/samsung/galaxy-a90-5g/firmware/SM-A908N/KOO/",
        "signal": "A908NKSU5EWA3 appears in the SM-A908N Korea Android 12 firmware sequence",
    },
]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v757-manifest", type=Path, default=DEFAULT_V757_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def file_info(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    return {
        "path": str(resolved),
        "exists": True,
        "is_file": resolved.is_file(),
        "is_dir": resolved.is_dir(),
        "size": resolved.stat().st_size if resolved.is_file() else None,
    }


def search_one_level(patterns: tuple[str, ...]) -> list[str]:
    root = repo_path(".")
    hits: list[str] = []
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.exists():
                hits.append(str(path.relative_to(root)))
    return sorted(set(hits))


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    v757 = load_json(args.v757_manifest)
    source_candidates = {str(path): file_info(path) for path in LOCAL_SOURCE_CANDIDATES}
    target_sources = {path: file_info(Path(path)) for path in TARGET_SOURCE_PATHS}
    boot_images = {str(path): file_info(path) for path in BOOT_IMAGE_CANDIDATES}
    tooling = {str(path): file_info(path) for path in TOOLING_CANDIDATES}
    source_archive_hints = search_one_level((
        "SM-A908N*",
        "*A908N*",
        "*Opensource*",
        "../SM-A908N*",
        "../*A908N*",
        "../*Opensource*",
    ))
    local_kernel_source_present = any(item["exists"] and item.get("is_dir") for item in source_candidates.values())
    target_source_present = any(item["exists"] for item in target_sources.values())
    boot_image_ready = file_info(Path("stage3/boot_linux_v724.img"))["exists"] and file_info(Path("stage3/boot_linux_v319.img"))["exists"]
    rollback_ready = file_info(Path("stage3/boot_linux_v261.img"))["exists"] and file_info(Path("stage3/boot_linux_v48.img"))["exists"]
    tooling_ready = all(tooling[str(path)]["exists"] for path in TOOLING_CANDIDATES)
    return {
        "v757": {
            "manifest": str(repo_path(args.v757_manifest)),
            "decision": v757.get("decision", ""),
            "pass": bool(v757.get("pass")),
            "device_mutations": bool(v757.get("device_mutations")),
        },
        "local_source": {
            "candidates": source_candidates,
            "target_sources": target_sources,
            "archive_hints": source_archive_hints,
            "kernel_source_present": local_kernel_source_present,
            "target_source_present": target_source_present,
        },
        "boot_images": {
            "candidates": boot_images,
            "current_native_ready": file_info(Path("stage3/boot_linux_v724.img"))["exists"],
            "v319_ready": file_info(Path("stage3/boot_linux_v319.img"))["exists"],
            "rollback_v261_ready": file_info(Path("stage3/boot_linux_v261.img"))["exists"],
            "known_good_v48_ready": file_info(Path("stage3/boot_linux_v48.img"))["exists"],
            "boot_image_ready": boot_image_ready,
            "rollback_ready": rollback_ready,
        },
        "tooling": {
            "candidates": tooling,
            "ready": tooling_ready,
        },
        "external_source_refs": EXTERNAL_SOURCE_REFS,
        "route": {
            "can_patch_kernel_now": local_kernel_source_present and target_source_present and boot_image_ready and rollback_ready and tooling_ready,
            "source_acquisition_required": not (local_kernel_source_present and target_source_present),
            "boot_image_handoff_safe_after_source": boot_image_ready and rollback_ready and tooling_ready,
        },
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(analysis: dict[str, Any] | None) -> list[Check]:
    if not analysis:
        return []
    v757 = analysis["v757"]
    source = analysis["local_source"]
    boot_images = analysis["boot_images"]
    tooling = analysis["tooling"]
    route = analysis["route"]
    checks: list[Check] = []
    add_check(
        checks,
        "v757-input",
        "pass" if v757["decision"] == "v757-boot-image-log-instrumentation-selected" and v757["pass"] else "blocked",
        "blocker",
        f"decision={v757['decision']} pass={v757['pass']} mutations={v757['device_mutations']}",
        [v757["manifest"]],
        "complete V757 before V758 feasibility",
    )
    add_check(
        checks,
        "local-kernel-source",
        "pass" if source["kernel_source_present"] and source["target_source_present"] else "blocked",
        "blocker",
        f"kernel_source_present={source['kernel_source_present']} target_source_present={source['target_source_present']} archive_hints={source['archive_hints']}",
        [],
        "acquire exact SM-A908N/A908NKSU5EWA3-compatible Samsung kernel source before patching",
    )
    add_check(
        checks,
        "boot-image-and-rollback",
        "pass" if boot_images["boot_image_ready"] and boot_images["rollback_ready"] else "blocked",
        "blocker",
        f"current={boot_images['current_native_ready']} v319={boot_images['v319_ready']} rollback_v261={boot_images['rollback_v261_ready']} known_good_v48={boot_images['known_good_v48_ready']}",
        [],
        "restore required current and rollback boot images before live patch tests",
    )
    add_check(
        checks,
        "host-tooling",
        "pass" if tooling["ready"] else "blocked",
        "blocker",
        f"ready={tooling['ready']}",
        list(tooling["candidates"].keys()),
        "restore mkbootimg/build/flash/rollback tooling before patch tests",
    )
    add_check(
        checks,
        "patch-now-route",
        "pass" if route["can_patch_kernel_now"] else "review",
        "finding",
        f"can_patch_kernel_now={route['can_patch_kernel_now']} source_required={route['source_acquisition_required']} handoff_safe_after_source={route['boot_image_handoff_safe_after_source']}",
        [],
        "if review, do not patch yet; acquire/verify source first",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v758-kernel-instrumentation-feasibility-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only feasibility classifier",
        )
    blockers = blocking(checks)
    if not analysis:
        return (
            "v758-kernel-instrumentation-feasibility-missing-analysis",
            False,
            "analysis missing",
            "rerun V758",
        )
    route = analysis["route"]
    if route["can_patch_kernel_now"]:
        return (
            "v758-local-kernel-instrumentation-feasible",
            True,
            "local source, boot images, rollback images, and tooling are all present",
            "V759 can create a minimal source patch plan with no live flash until review",
        )
    if blockers == ["local-kernel-source"] and route["boot_image_handoff_safe_after_source"]:
        return (
            "v758-source-acquisition-required-before-kernel-instrumentation",
            True,
            "boot image tooling and rollback are present, but exact kernel/QCACLD source is not local",
            "V759 should acquire or stage exact compatible Samsung kernel source before any instrumentation patch",
        )
    if blockers:
        return (
            "v758-kernel-instrumentation-feasibility-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear blockers before instrumentation patch planning",
        )
    return (
        "v758-kernel-instrumentation-feasibility-review",
        True,
        "feasibility classified but needs manual review",
        "inspect manifest before V759",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    route = analysis.get("route") or {}
    return "\n".join([
        "# V758 Kernel Instrumentation Feasibility",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- boot_image_write_executed: `{manifest['boot_image_write_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- plan only",
        "",
        "## Route",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in route.items()]) if route else "- plan only",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis: dict[str, Any] | None = None
    if args.command != "plan":
        analysis = build_analysis(args)
    checks = build_checks(analysis)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v758",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "analysis": analysis or {},
        "checks": [asdict(check) for check in checks],
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v758-kernel-instrumentation-feasibility.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"boot_image_write_executed: {manifest['boot_image_write_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
