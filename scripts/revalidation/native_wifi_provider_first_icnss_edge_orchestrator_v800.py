#!/usr/bin/env python3
"""V800 current-boot orchestrator for helper v124 provider-first ICNSS edge replay."""

from __future__ import annotations

from typing import Any

import native_wifi_provider_first_icnss_edge_orchestrator_v712 as v712
from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore


v700 = v712.v700

v700.v673.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
v700.DEFAULT_OUT_DIR = v700.Path("tmp/wifi/v800-provider-first-icnss-edge-v124-orchestrated")
v700.V700_SCRIPT = "scripts/revalidation/native_wifi_provider_first_icnss_edge_v800.py"
v700.V700_APPROVAL = (
    "approve v800 provider-first ICNSS edge v124 replay proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)
v700.HELPER_SHA256 = "d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6"
v700.HELPER_MARKER = "a90_android_execns_probe v124"
v700.ALLOWED_LIVE_ACTIONS = (
    "V641 one-shot clean-DSP reboot",
    "V401 SELinuxfs mount surface",
    "V490 Android SELinux policy-load proof",
    "bounded helper v124 provider-first ICNSS edge replay proof",
    "read-only ICNSS/QCA6390 focused captures",
    "WLFW QRTR nameservice readback without QMI payload",
    "runner-owned reboot cleanup",
)

_v712_build_manifest = v700.build_manifest
_v712_render_summary = v700.render_summary


def _rewrite(value: object) -> object:
    if isinstance(value, str):
        return (
            value.replace("v712", "v800")
            .replace("V712", "V800")
            .replace("v121", "v124")
            .replace("helper v121", "helper v124")
            .replace("a90_android_execns_probe v121", "a90_android_execns_probe v124")
        )
    if isinstance(value, dict):
        return {key: _rewrite(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_rewrite(item) for item in value]
    return value


def build_manifest(args: v700.argparse.Namespace,
                   prep: dict[str, Any] | None,
                   arm: dict[str, Any] | None) -> dict[str, Any]:
    manifest = _v712_build_manifest(args, prep, arm)
    manifest = _rewrite(manifest)
    assert isinstance(manifest, dict)
    live = (arm or {}).get("live") or {}
    edge_surface = live.get("v800_icnss_edge_surface") or live.get("v712_icnss_edge_surface")
    arm_summary = manifest.get("arm_v700")
    if isinstance(arm_summary, dict) and arm:
        arm_summary["manifest"] = arm.get("manifest", "")
        arm_summary["decision"] = _rewrite(str(arm.get("decision", arm_summary.get("decision", ""))))
        arm_summary["reason"] = _rewrite(str(arm.get("reason", arm_summary.get("reason", ""))))
        arm_summary["next_step"] = _rewrite(str(arm.get("next_step", arm_summary.get("next_step", ""))))
    manifest["cycle"] = "v800"
    manifest["helper_marker"] = v700.HELPER_MARKER
    manifest["helper_sha256"] = v700.HELPER_SHA256
    manifest["icnss_edge_captured"] = bool(live.get("v800_icnss_edge_captured") or live.get("v712_icnss_edge_captured"))
    manifest["icnss_edge_surface"] = edge_surface if isinstance(edge_surface, dict) else {}
    arm_decision = _rewrite(str((arm or {}).get("decision") or ""))
    if isinstance(arm_decision, str) and arm_decision.startswith("v800-provider-first-icnss-edge-"):
        manifest["decision"] = arm_decision
        manifest["reason"] = _rewrite(str((arm or {}).get("reason") or manifest.get("reason", "")))
        manifest["next_step"] = _rewrite(str((arm or {}).get("next_step") or manifest.get("next_step", "")))
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    text = _rewrite(_v712_render_summary(manifest))
    assert isinstance(text, str)
    edge = manifest.get("icnss_edge_surface") or {}
    if not isinstance(edge, dict):
        edge = {}
    preferred_keys = [
        key for key in sorted(edge)
        if key.endswith(".icnss_edge_captured")
        or key.endswith(".begin")
        or key.endswith(".end")
        or key.endswith(".icnss_driver_link.exists")
        or key.endswith(".qca6390_driver_link.exists")
        or key.endswith(".wlan0_netdev.exists")
        or key.endswith(".shutdown_wlan.exists")
        or key.endswith(".value_captures")
    ]
    rows = [[key, str(edge.get(key, ""))] for key in preferred_keys]
    return "\n".join([
        text,
        "",
        "## V800 v124 Current-boot Replay",
        "",
        f"- helper_marker: `{v700.HELPER_MARKER}`",
        f"- expect_version: `{v700.v673.DEFAULT_EXPECT_VERSION}`",
        f"- icnss_edge_captured: `{manifest.get('icnss_edge_captured')}`",
        "",
        v700.markdown_table(["key", "value"], rows) if rows else "- not captured",
        "",
    ])


v700.build_manifest = build_manifest
v700.render_summary = render_summary


def main() -> int:
    args = v700.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    prep: dict[str, Any] | None = None
    arm: dict[str, Any] | None = None
    if args.command == "run":
        root = store.run_dir
        arm_root = root / "arm-v800-v124-provider-first-icnss-edge"
        prep = v700.v673.prep_current_boot(args, store, "v800", arm_root)
        if prep.get("ready"):
            arm = v700.v673.run_arm(
                args,
                store,
                "v800",
                v700.V700_SCRIPT,
                v700.V700_APPROVAL,
                arm_root / "live",
                v700.Path(str(prep["v490"]["manifest"])),
            )
    manifest = build_manifest(args, prep, arm)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
