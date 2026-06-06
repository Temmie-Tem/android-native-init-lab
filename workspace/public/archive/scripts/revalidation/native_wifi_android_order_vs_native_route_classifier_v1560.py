#!/usr/bin/env python3
"""V1560 host-only Android-order vs native-route classifier.

V1559 showed that Android's retained endpoint IRQ/L0 evidence is late relative
to the first retained wlan0 lines.  V1560 therefore compares the ordered lower
Wi-Fi sequence itself: Android reaches wlfw_start before esoc0/AP2MDM/BDF,
while the native V1496/V1557 auto-readiness route sees cnss-daemon netlink and
forces RC1 enumerate, but never reaches wlfw_start/BDF/FW-ready/wlan0.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1560-android-order-vs-native-route-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1560_ANDROID_ORDER_VS_NATIVE_ROUTE_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1560-android-order-vs-native-route-classifier.txt")

V1555_MANIFEST = Path("tmp/wifi/v1555-android-good-minimal-trace-reference/manifest.json")
V1557_MANIFEST = Path("tmp/wifi/v1557-native-endpoint-long-hold-handoff/manifest.json")
V1559_MANIFEST = Path("tmp/wifi/v1559-android-pre-endpoint-order-classifier/manifest.json")
ANDROID_DMESG = Path(
    "tmp/wifi/v1555-android-good-minimal-trace-reference"
    "/android-postfs-evidence/a90-v1555-android-min-trace-ref/dmesg-filtered.txt"
)
NATIVE_V1496_DMESG = Path("tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/test-v1393-dmesg.stdout.txt")
NATIVE_V1557_DMESG = Path("tmp/wifi/v1557-native-endpoint-long-hold-handoff/test-dmesg-filtered.stdout.txt")


TIME_RE = re.compile(r"\[\s*(?P<time>\d+\.\d+)\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_time(text: str, *needles: str) -> float | None:
    for line in text.splitlines():
        if all(needle in line for needle in needles):
            match = TIME_RE.search(line)
            if match:
                return float(match.group("time"))
    return None


def has_line(text: str, *needles: str) -> bool:
    return any(all(needle in line for needle in needles) for line in text.splitlines())


def fmt(value: Any) -> str:
    return "missing" if value is None else f"{float(value):.6f}"


def delta(after: Any, before: Any) -> str:
    if after is None or before is None:
        return "n/a"
    return f"{float(after) - float(before):+.6f}s"


def android_sequence() -> dict[str, Any]:
    dmesg = read_text(ANDROID_DMESG)
    return {
        "wlfw_start": first_time(dmesg, "cnss-daemon wlfw_start"),
        "wlfw_service_request": first_time(dmesg, "wlfw_service_request"),
        "esoc0_get": first_time(dmesg, "__subsystem_get: esoc0"),
        "icnss_qmi": first_time(dmesg, "icnss_qmi: QMI Server Connected"),
        "bdf_regdb": first_time(dmesg, "BDF file : regdb.bin"),
        "bdf_bdwlan": first_time(dmesg, "BDF file : bdwlan.bin"),
        "fw_ready": first_time(dmesg, "WLAN FW is ready"),
        "fw_ready_event": first_time(dmesg, "FW ready event received"),
        "wlan0": first_time(dmesg, "dev : wlan0"),
        "late_l0": first_time(dmesg, "LTSSM_L0"),
    }


def native_route(label: str, dmesg_path: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    dmesg = read_text(dmesg_path)
    manifest = read_json(manifest_path) if manifest_path else {}
    progress = manifest.get("progress") if isinstance(manifest.get("progress"), dict) else {}
    return {
        "label": label,
        "netlink": first_time(dmesg, "cnss-daemon", "__netlink_sendskb"),
        "ctrl_getfamily": first_time(dmesg, "cnss-daemon", "ctrl_getfamily"),
        "esoc0_get": first_time(dmesg, "__subsystem_get: esoc0"),
        "rc1_phy": first_time(dmesg, "PCIe RC1 PHY is ready"),
        "rc1_poll_compliance": first_time(dmesg, "LTSSM_POLL_COMPLIANCE"),
        "rc1_link_fail": first_time(dmesg, "PCIe RC1 link initialization failed"),
        "wlfw_start": first_time(dmesg, "wlfw_start"),
        "bdf": first_time(dmesg, "BDF file"),
        "fw_ready": first_time(dmesg, "FW ready"),
        "wlan0": first_time(dmesg, "wlan0"),
        "has_cnss_netlink": has_line(dmesg, "cnss-daemon", "__netlink_sendskb"),
        "has_esoc0": has_line(dmesg, "__subsystem_get: esoc0"),
        "has_rc1": has_line(dmesg, "PCIe RC1 PHY is ready"),
        "manifest_decision": manifest.get("decision"),
        "manifest_pass": manifest.get("pass"),
        "progress": progress,
    }


def classify() -> dict[str, Any]:
    v1555 = read_json(V1555_MANIFEST)
    v1557 = read_json(V1557_MANIFEST)
    v1559 = read_json(V1559_MANIFEST)
    android = android_sequence()
    native_v1496 = native_route("V1496", NATIVE_V1496_DMESG)
    native_v1557 = native_route("V1557", NATIVE_V1557_DMESG, V1557_MANIFEST)

    android_order_ok = all(
        android[key] is not None
        for key in ("wlfw_start", "esoc0_get", "bdf_regdb", "fw_ready", "wlan0")
    ) and android["wlfw_start"] < android["esoc0_get"] < android["bdf_regdb"] < android["wlan0"]
    native_route_lacks_wlfw = (
        native_v1496["has_cnss_netlink"]
        and native_v1496["has_esoc0"]
        and native_v1496["has_rc1"]
        and native_v1496["wlfw_start"] is None
        and native_v1557["has_cnss_netlink"]
        and native_v1557["has_esoc0"]
        and native_v1557["has_rc1"]
        and native_v1557["wlfw_start"] is None
        and not bool((v1557.get("progress") or {}).get("wlfw_progress"))
    )
    l0_order_caveat = android["late_l0"] is not None and android["wlan0"] is not None and android["late_l0"] > android["wlan0"]
    prerequisites_ok = (
        v1555.get("pass") is True
        and v1557.get("pass") is True
        and v1559.get("pass") is True
        and android_order_ok
        and native_route_lacks_wlfw
        and l0_order_caveat
    )
    decision = (
        "v1560-android-wlfw-before-ap2mdm-native-route-lacks-wlfw"
        if prerequisites_ok
        else "v1560-android-native-route-order-incomplete-review"
    )
    reason = (
        "Android lower sequence reaches wlfw_start before esoc0/AP2MDM/BDF, but native V1496/V1557 only reaches cnss-daemon netlink plus forced RC1 enumerate and never reaches wlfw_start/BDF/FW-ready/wlan0"
        if prerequisites_ok
        else "existing evidence does not fully prove Android ordered lower Wi-Fi sequence plus native route wlfw absence"
    )
    rows = [
        ["cnss/WLFW start", fmt(android["wlfw_start"]), fmt(native_v1496["wlfw_start"]), fmt(native_v1557["wlfw_start"]), "Android has explicit wlfw_start; native route does not"],
        ["wlfw service request", fmt(android["wlfw_service_request"]), "missing", "missing", "Android starts WLFW request thread before BDF"],
        ["cnss netlink", "not discriminating", fmt(native_v1496["netlink"]), fmt(native_v1557["netlink"]), "native watcher triggers on netlink, not on wlfw_start"],
        ["esoc0 get", fmt(android["esoc0_get"]), fmt(native_v1496["esoc0_get"]), fmt(native_v1557["esoc0_get"]), "both paths reach esoc0"],
        ["BDF", f"{fmt(android['bdf_regdb'])}/{fmt(android['bdf_bdwlan'])}", fmt(native_v1496["bdf"]), fmt(native_v1557["bdf"]), f"Android BDF is {delta(android['bdf_regdb'], android['wlfw_start'])} after wlfw_start"],
        ["FW-ready/wlan0", f"{fmt(android['fw_ready'])}/{fmt(android['wlan0'])}", f"{fmt(native_v1496['fw_ready'])}/{fmt(native_v1496['wlan0'])}", f"{fmt(native_v1557['fw_ready'])}/{fmt(native_v1557['wlan0'])}", "native never reaches lower Wi-Fi readiness"],
        ["RC1 forced enumerate", f"late L0={fmt(android['late_l0'])}", f"phy={fmt(native_v1496['rc1_phy'])} fail={fmt(native_v1496['rc1_link_fail'])}", f"phy={fmt(native_v1557['rc1_phy'])} fail={fmt(native_v1557['rc1_link_fail'])}", "native forced RC1 path fails before L0; Android retained L0 is late relative to wlan0"],
    ]
    next_gate = {
        "recommended_cycle": "V1561",
        "type": "host-only contract comparator before live",
        "focus": "cnss-daemon WLFW start/request contract, not credentials or connect",
        "requirements": [
            "compare Android cnss-daemon invocation/properties/sockets/service-manager context against native test-boot cnss-daemon context",
            "explain why native cnss-daemon emits generic netlink traffic but not wlfw_start/wlfw_service_request",
            "keep forced RC1 enumerate as diagnostic only; do not use it as the primary trigger for lower Wi-Fi",
            "do not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping until WLFW/BDF/FW-ready/wlan0 exist in native",
        ],
    }
    return {
        "decision": decision,
        "pass": prerequisites_ok,
        "reason": reason,
        "android": android,
        "native_v1496": native_v1496,
        "native_v1557": native_v1557,
        "derived": {
            "android_order_ok": android_order_ok,
            "native_route_lacks_wlfw": native_route_lacks_wlfw,
            "l0_order_caveat": l0_order_caveat,
        },
        "comparison_rows": rows,
        "next_gate": next_gate,
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    return "\n".join(
        [
            "# Native Init V1560 Android Order vs Native Route Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1560`",
            "- Type: host-only Android/native lower-sequence classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Inputs",
            "",
            markdown_table(
                ["input", "path"],
                [
                    ["android_v1555", rel(V1555_MANIFEST)],
                    ["native_v1496_dmesg", rel(NATIVE_V1496_DMESG)],
                    ["native_v1557", rel(V1557_MANIFEST)],
                    ["v1559_order_classifier", rel(V1559_MANIFEST)],
                ],
            ),
            "",
            "## Sequence Comparison",
            "",
            markdown_table(["signal", "android_v1555", "native_v1496", "native_v1557", "interpretation"], analysis["comparison_rows"]),
            "",
            "## Derived Checks",
            "",
            markdown_table(["check", "value"], [[key, value] for key, value in analysis["derived"].items()]),
            "",
            "## Interpretation",
            "",
            "The existing Android-good evidence shows the lower sequence starts with `cnss-daemon wlfw_start`, then reaches `esoc0`, BDF, FW-ready, and `wlan0`. The current native auto-readiness route does not reproduce that contract: it sees `cnss-daemon` generic netlink traffic, then forces RC1 enumerate and fails before L0, but no `wlfw_start`, BDF, FW-ready, or `wlan0` appears.",
            "",
            "Therefore the next useful unit is not a credentialed Wi-Fi connect attempt and not another blind RC1 enumerate retry. The immediate missing contract is the native `cnss-daemon` WLFW start/request path.",
            "",
            "## Next Gate",
            "",
            f"- Recommended cycle: `{analysis['next_gate']['recommended_cycle']}`",
            f"- Type: {analysis['next_gate']['type']}",
            f"- Focus: {analysis['next_gate']['focus']}",
            "",
            "### Requirements",
            "",
            *[f"- {item}" for item in analysis["next_gate"]["requirements"]],
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = classify()
    manifest = {
        "cycle": "V1560",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "host": collect_host_metadata(),
        "input_paths": {
            "android_v1555": rel(V1555_MANIFEST),
            "native_v1496_dmesg": rel(NATIVE_V1496_DMESG),
            "native_v1557": rel(V1557_MANIFEST),
            "v1559_order_classifier": rel(V1559_MANIFEST),
        },
        "analysis": analysis,
        "out_dir": rel(store.run_dir),
        "device_commands_executed": False,
        "device_mutations": False,
    }
    store.write_json("manifest.json", manifest)
    report = render_report(manifest)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    write_private_text(repo_path(LATEST_POINTER), rel(store.run_dir) + "\n")
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
