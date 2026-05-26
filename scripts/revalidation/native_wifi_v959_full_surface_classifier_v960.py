#!/usr/bin/env python3
"""V960 host-only classifier for V959 full-surface pm-proxy matrix evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v960-v959-full-surface-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v960-v959-full-surface-classifier.txt")
DEFAULT_V959_MANIFEST = Path("tmp/wifi/v959-pm-proxy-full-surface-live/manifest.json")
DEFAULT_V959_HELPER_TEXT = Path("tmp/wifi/v959-pm-proxy-full-surface-live/native/mdm-helper-cnss-before-esoc.txt")
DEFAULT_V959_DMESG = Path("tmp/wifi/v959-pm-proxy-full-surface-live/native/post-dmesg-wifi-esoc-tail.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v959-manifest", type=Path, default=DEFAULT_V959_MANIFEST)
    parser.add_argument("--v959-helper-text", type=Path, default=DEFAULT_V959_HELPER_TEXT)
    parser.add_argument("--v959-dmesg", type=Path, default=DEFAULT_V959_DMESG)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def helper(manifest: dict[str, Any]) -> dict[str, Any]:
    return (manifest.get("analysis") or {}).get("helper") or {}


def provider(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("provider_readiness") or {}


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("contract") or {}


def wifi_surface(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("wifi_surface") or {}


def val(data: dict[str, str], phase: str, suffix: str) -> str:
    return data.get(f"mdm_helper_provider_readiness.{phase}.{suffix}", "")


def classify(v959: dict[str, Any], helper_text: str, dmesg: str) -> dict[str, Any]:
    c959 = contract(v959)
    p959 = provider(v959)
    surface = wifi_surface(v959)
    post_provider_phases = (
        "cnss_before_esoc_after_service_manager_start",
        "cnss_before_esoc_after_cnss_daemon_start",
    )
    provider_persisted = all(
        val(p959, phase, "pm_service_count") == "1"
        and val(p959, phase, "pm_proxy_count") == "1"
        and val(p959, phase, "per_mgr_vndbinder_count") == "1"
        for phase in post_provider_phases
    )
    full_surface = c959.get("surface_mode") == "full" and int(c959.get("surface_poll_count") or "0") >= 1
    cnss_netlink_reached = "found  w/o mod res: cld80211" in dmesg and "comm:cnss-daemon" in dmesg
    mhi_devices_empty = "mhi_devices_END count=0" in helper_text
    mdm3_still_offlining = "mdm3_state=OFFLINING" in helper_text
    wlan0_absent = all(
        value == "0"
        for key, value in surface.items()
        if key.endswith(".wlan0_captured")
    ) and "wlan0_netdev.exists=0" in helper_text
    positive_wlfw_markers = (
        "wlfw_start",
        "WLAN-PD",
        "wlan_pd state indication",
        "BDF file",
        "regdb.bin",
        "bdwlan.bin",
        "fw_ready",
    )
    wlfw_absent = (
        c959.get("wlfw_precondition_observed") == "0"
        and not any(marker in helper_text for marker in positive_wlfw_markers)
        and not any(marker in dmesg for marker in positive_wlfw_markers)
    )
    fail_closed = (
        c959.get("subsys_esoc0_open_attempted") == "0"
        and c959.get("pm_proxy_helper_start_executed") == "0"
        and c959.get("wifi_hal_start_executed") == "0"
        and c959.get("scan_connect_linkup") == "0"
        and c959.get("credentials") == "0"
        and c959.get("dhcp_routing") == "0"
        and c959.get("external_ping") == "0"
        and bool(v959.get("pass"))
    )
    if (
        full_surface
        and provider_persisted
        and cnss_netlink_reached
        and mhi_devices_empty
        and mdm3_still_offlining
        and wlan0_absent
        and wlfw_absent
        and fail_closed
    ):
        decision = "v960-full-surface-confirms-post-provider-wlfw-gap"
        pass_ok = True
        reason = (
            "full-surface capture shows provider and CNSS netlink are present, but MHI devices, WLFW/BDF, and wlan0 remain absent"
        )
        next_step = (
            "plan a host-only trigger-gate redesign around the circular WLFW precondition; do not open /dev/subsys_esoc0 or start HAL/scan until the new gate is explicit"
        )
    else:
        decision = "v960-full-surface-needs-review"
        pass_ok = bool(v959.get("pass"))
        reason = "V959 full-surface evidence is incomplete or ambiguous"
        next_step = "inspect V959 helper text and dmesg manually before another live action"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "provider_keys": len(p959),
        "surface_keys": len(surface),
        "full_surface": full_surface,
        "provider_persisted": provider_persisted,
        "cnss_netlink_reached": cnss_netlink_reached,
        "mhi_devices_empty": mhi_devices_empty,
        "mdm3_still_offlining": mdm3_still_offlining,
        "wlan0_absent": wlan0_absent,
        "wlfw_absent": wlfw_absent,
        "fail_closed": fail_closed,
        "guardrails": {
            "host_only": True,
            "device_commands_executed": False,
            "device_mutations": False,
            "actor_start_executed": False,
            "subsys_esoc0_open_executed": False,
            "esoc_ioctl_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credentials_used": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_image_write": False,
            "partition_write": False,
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    rows = [
        ["provider_keys", str(c["provider_keys"])],
        ["surface_keys", str(c["surface_keys"])],
        ["full_surface", str(c["full_surface"])],
        ["provider_persisted", str(c["provider_persisted"])],
        ["cnss_netlink_reached", str(c["cnss_netlink_reached"])],
        ["mhi_devices_empty", str(c["mhi_devices_empty"])],
        ["mdm3_still_offlining", str(c["mdm3_still_offlining"])],
        ["wlan0_absent", str(c["wlan0_absent"])],
        ["wlfw_absent", str(c["wlfw_absent"])],
        ["fail_closed", str(c["fail_closed"])],
    ]
    return "\n".join(
        [
            "# V960 V959 Full-Surface Classifier Summary",
            "",
            f"decision: {c['decision']}",
            f"pass: {c['pass']}",
            f"reason: {c['reason']}",
            f"next: {c['next_step']}",
            "",
            markdown_table(["marker", "value"], rows),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v959 = load_json(args.v959_manifest)
    helper_text = read_text(args.v959_helper_text)
    dmesg = read_text(args.v959_dmesg)
    classification = classify(v959, helper_text, dmesg)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "v959_manifest": str(repo_path(args.v959_manifest)),
        "v959_helper_text": str(repo_path(args.v959_helper_text)),
        "v959_dmesg": str(repo_path(args.v959_dmesg)),
        "classification": classification,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {classification['decision']}")
    print(f"pass: {classification['pass']}")
    print(f"reason: {classification['reason']}")
    print(f"next: {classification['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if classification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
