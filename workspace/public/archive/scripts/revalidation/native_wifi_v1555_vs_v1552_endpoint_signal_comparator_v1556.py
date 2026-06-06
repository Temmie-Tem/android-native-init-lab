#!/usr/bin/env python3
"""V1556 host-only comparator for Android-good V1555 vs native V1552.

The comparator consumes existing evidence only.  It does not run device
commands, mount tracefs/debugfs, reboot, flash, write partitions, start Wi-Fi
HAL, scan/connect, use credentials, configure DHCP/routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1556-v1555-vs-v1552-endpoint-signal-comparator")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1556_V1555_VS_V1552_ENDPOINT_SIGNAL_COMPARATOR_2026-06-02.md"
)
DEFAULT_NATIVE_V1552_MANIFEST = Path("tmp/wifi/v1552-rc1-endpoint-response-tracefs-live/manifest.json")
DEFAULT_ANDROID_V1555_MANIFEST = Path("tmp/wifi/v1555-android-good-minimal-trace-reference/manifest.json")
LATEST_POINTER = Path("tmp/wifi/latest-v1556-v1555-vs-v1552-endpoint-signal-comparator.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--native-v1552-manifest", type=Path, default=DEFAULT_NATIVE_V1552_MANIFEST)
    parser.add_argument("--android-v1555-manifest", type=Path, default=DEFAULT_ANDROID_V1555_MANIFEST)
    parser.add_argument("--write-report", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    return json.loads(resolved.read_text(encoding="utf-8"))


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def yes(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value > 0
    return bool(value)


def build_analysis(native_manifest: dict[str, Any], android_manifest: dict[str, Any]) -> dict[str, Any]:
    native_analysis = native_manifest.get("analysis") or {}
    native_counts = native_analysis.get("target_counts") or {}
    native_irq_delta = native_analysis.get("interrupt_delta") or {}
    android_analysis = nested(android_manifest, "context", "analysis", default={}) or {}
    android_tracefs = android_analysis.get("tracefs_analysis") or {}
    android_counts = android_tracefs.get("trace_counts") or {}
    android_dmesg = android_analysis.get("dmesg") or {}
    native_ap_side_ok = all(
        yes(native_counts.get(name))
        for name in ("pcie1_gdsc_enable", "pcie1_clock", "refclk_enable", "pipe_clk_enable", "gpio102_set0", "gpio102_set1")
    )
    native_endpoint_silent = not any(
        yes(native_counts.get(name)) or yes(native_irq_delta.get(delta_name))
        for name, delta_name in (
            ("gpio104", "pcie_wake"),
            ("gpio142", "mdm_status"),
            ("irq_pcie_wake", "pcie_wake"),
            ("irq_mdm_status", "mdm_status"),
            ("irq_mdm_errfatal", "mdm_errfatal"),
        )
    )
    android_lower_ok = bool(android_analysis.get("android_lower_ok")) or all(
        android_dmesg.get(name) is not None for name in ("wlfw_time", "bdf_time", "fw_ready_time", "wlan0_time")
    )
    android_endpoint_positive = (
        yes(android_counts.get("gpio104"))
        and yes(android_counts.get("gpio142"))
        and yes(android_counts.get("gpio135"))
        and yes(android_counts.get("gpio102"))
    )
    timing_caveat = (
        android_dmesg.get("pcie_l0_time") is not None
        and android_dmesg.get("wlan0_time") is not None
        and android_dmesg["pcie_l0_time"] > android_dmesg["wlan0_time"]
    )
    comparison_rows = [
        ["AP-side pcie1 power/refclk/PERST", native_ap_side_ok, "not traced in V1555 minimal set", "native preconditions are already proven by V1552"],
        ["GPIO135/AP2MDM", native_counts.get("gpio135", 0), android_counts.get("gpio135", 0), "Android-good has AP2MDM activity; V1552 sysfs-enumerate window does not"],
        ["GPIO102/PERST", f"{native_counts.get('gpio102_set0', 0)}/{native_counts.get('gpio102_set1', 0)}", android_counts.get("gpio102", 0), "both paths can toggle PERST-like GPIO102"],
        ["GPIO104/pcie wake", native_counts.get("gpio104", 0), android_counts.get("gpio104", 0), "positive Android endpoint wake signal is absent in native"],
        ["IRQ252/msm_pcie_wake", native_irq_delta.get("pcie_wake", 0), android_counts.get("gpio104", 0), "native wake IRQ delta stays zero"],
        ["GPIO142/MDM2AP", native_counts.get("gpio142", 0), android_counts.get("gpio142", 0), "positive Android mdm status level is absent in native"],
        ["IRQ290/mdm status", native_irq_delta.get("mdm_status", 0), android_counts.get("gpio142", 0), "native mdm status IRQ delta stays zero"],
        ["L0/MHI/lower Wi-Fi", f"{native_analysis.get('l0_seen')}/{native_analysis.get('mhi_seen')}/False", f"{android_dmesg.get('pcie_l0_time')}/{android_dmesg.get('wlan0_time')}", "Android lower path is proven; late L0 timing needs caution"],
    ]
    if native_ap_side_ok and native_endpoint_silent and android_lower_ok and android_endpoint_positive:
        decision = "v1556-stable-gap-android-endpoint-signals-native-zero"
        pass_ok = True
        reason = "host-only comparison fixes the stable delta: Android-good has wake/status endpoint signals while native V1552 remains endpoint-silent after AP-side power/refclk/PERST"
    else:
        decision = "v1556-comparison-incomplete-review"
        pass_ok = False
        reason = "input evidence does not prove both native endpoint silence and Android-good endpoint-positive reference"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "native": {
            "decision": native_manifest.get("decision"),
            "pass": native_manifest.get("pass"),
            "target_counts": native_counts,
            "interrupt_delta": native_irq_delta,
            "ap_side_ok": native_ap_side_ok,
            "endpoint_silent": native_endpoint_silent,
        },
        "android": {
            "decision": android_manifest.get("decision"),
            "pass": android_manifest.get("pass"),
            "android_lower_ok": android_lower_ok,
            "endpoint_positive": android_endpoint_positive,
            "trace_counts": android_counts,
            "dmesg": android_dmesg,
            "timing_caveat_l0_after_wlan0": timing_caveat,
        },
        "comparison_rows": comparison_rows,
        "next_gate": "v1557-native-provider-plus-minimal-endpoint-hold-or-dmesg-only-timing-clarifier",
        "guardrail": "no Wi-Fi HAL/scan/connect/credentials/DHCP/routes/external ping or direct PMIC/GPIO/GDSC/eSoC notify until native first-L0 cause is narrowed",
    }


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    native = analysis["native"]
    android = analysis["android"]
    return "\n".join(
        [
            "# V1556 V1555-vs-V1552 Endpoint Signal Comparator",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- evidence: `{manifest['out_dir']}`",
            "",
            "## Inputs",
            "",
            markdown_table(
                ["input", "decision", "pass", "path"],
                [
                    ["native_v1552", native.get("decision"), native.get("pass"), manifest["native_v1552_manifest"]],
                    ["android_v1555", android.get("decision"), android.get("pass"), manifest["android_v1555_manifest"]],
                ],
            ),
            "",
            "## Comparison",
            "",
            markdown_table(["signal", "native_v1552", "android_v1555", "interpretation"], analysis["comparison_rows"]),
            "",
            "## Interpretation",
            "",
            "V1556 fixes the stable signal delta without running the device.  V1552 already proves native AP-side pcie1 GDSC/refclk/pipe-clock/PERST activity, but endpoint response remains zero: no GPIO104/pcie wake, no GPIO142/MDM2AP, no mdm status IRQ, and no L0.  V1555 preserves Android lower Wi-Fi under a lower-impact observer and shows the missing positive endpoint signals: GPIO104/IRQ252 and GPIO142/IRQ290.",
            "",
            "The Android timing still has a caveat: retained RC1 L0/MHI excerpts appear after the first WLFW/BDF/FW-ready/`wlan0` lines.  Therefore the next gate should compare stable signal presence/absence, not claim the late L0 excerpt is the first enabling L0.",
            "",
            "## Next",
            "",
            "- V1557 should either run a native provider+minimal endpoint hold aligned to V1555's positive signals, or first perform a dmesg-only Android timing clarifier if first-L0 ordering is needed.",
            "- Keep firmware/MHI/WLFW/connect work parked until native RC1 L0 and PCI enumeration exist.",
            "",
            "## Safety",
            "",
            "Host-only classifier. No device command, tracefs/debugfs/sysfs write, reboot, flash, partition write, Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping, direct PMIC/GPIO/GDSC write, eSoC notify, PCI rescan, or platform bind/unbind is performed.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    native_manifest = load_json(args.native_v1552_manifest)
    android_manifest = load_json(args.android_v1555_manifest)
    analysis = build_analysis(native_manifest, android_manifest)
    manifest = {
        "cycle": "V1556",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "out_dir": str(store.run_dir),
        "native_v1552_manifest": str(repo_path(args.native_v1552_manifest)),
        "android_v1555_manifest": str(repo_path(args.android_v1555_manifest)),
        "host": collect_host_metadata(),
        "analysis": analysis,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "blind_esoc_notify_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
