#!/usr/bin/env python3
"""V1757 host-only libperipheral service-lookup branch classifier."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_V1756 = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1756-wlan-pd-pm-register-trace-classifier"
    / "manifest.json"
)
DEFAULT_LIB = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v226-vendor-root-live-export"
    / "vendor-source"
    / "lib64"
    / "libperipheral_client.so"
)
DEFAULT_DISASM = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1717-cnss-pm-client-register-static"
    / "pm_register_connect.disasm.txt"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1757-wlan-pd-peripheral-interface-branch-classifier"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1757_WLAN_PD_PERIPHERAL_INTERFACE_BRANCH_CLASSIFIER_2026-06-03.md"
)


OFFSETS = {
    "service_manager_get_call": 0x61C4,
    "returned_binder_load": 0x6208,
    "returned_binder_null_branch": 0x620C,
    "as_interface_call": 0x6218,
    "get_service_fail_log": 0x629C,
    "get_service_fail_tag": 0x4A78,
    "get_service_fail_format": 0x4A82,
    "get_interface_fail_format": 0x4A96,
    "service_name": 0x4C2D,
}


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path, limit: int = 6_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def read_c_string(path: Path, offset: int) -> str:
    data = path.read_bytes()
    if offset >= len(data):
        return ""
    end = data.find(b"\0", offset)
    if end < 0:
        end = len(data)
    return data[offset:end].decode("utf-8", errors="replace")


def parse_disasm(disasm_text: str) -> dict[int, str]:
    lines: dict[int, str] = {}
    for line in disasm_text.splitlines():
        match = re.match(r"\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{8})\s+(.+)$", line)
        if not match:
            continue
        lines[int(match.group(1), 16)] = line.strip()
    return lines


def peripheral_hit(v1756: dict[str, Any], event: str) -> int:
    try:
        return int(v1756["v1736"]["peripheral_hits"].get(event, 0))
    except (KeyError, TypeError, ValueError):
        return 0


def gate_value(v1756: dict[str, Any], key: str) -> Any:
    try:
        return v1756["v1736"]["gate"].get(key)
    except (KeyError, TypeError):
        return None


def classify(v1756: dict[str, Any], disasm: dict[int, str], strings: dict[str, str]) -> tuple[str, bool, str, str]:
    if v1756.get("label") != "peripheral-manager-interface-conversion-gap":
        return (
            "v1757-prerequisite-v1756-label-mismatch",
            False,
            "V1756 did not classify the peripheral-manager interface-conversion gap",
            "prerequisite-mismatch",
        )

    branch_line = disasm.get(OFFSETS["returned_binder_null_branch"], "")
    as_interface_line = disasm.get(OFFSETS["as_interface_call"], "")
    failure_log_line = disasm.get(OFFSETS["get_service_fail_log"], "")
    branch_is_null_check = "cbz" in branch_line and "x8" in branch_line and "629c" in branch_line.lower()
    as_interface_is_next_call = "bl" in as_interface_line and "asInterface" in as_interface_line
    failure_log_is_get_service = strings.get("get_service_fail_format") == "%s get service fail"
    service_name_ok = strings.get("service_name") == "vendor.qcom.PeripheralManager"

    trace_reaches_check_not_interface = (
        peripheral_hit(v1756, "periph_service_manager_get_call") > 0
        and peripheral_hit(v1756, "periph_binder_object_present_check") > 0
        and peripheral_hit(v1756, "periph_as_interface_call") == 0
        and peripheral_hit(v1756, "periph_pm_register_connect_return") > 0
    )
    downstream_still_blocked = str(gate_value(v1756, "requested_wlanmdsp")) == "0"

    if (
        branch_is_null_check
        and as_interface_is_next_call
        and failure_log_is_get_service
        and service_name_ok
        and trace_reaches_check_not_interface
        and downstream_still_blocked
    ):
        return (
            "v1757-peripheral-manager-service-get-null-host-pass",
            True,
            "Static branch at 0x620c is cbz x8 to the `%s get service fail` path; V1736 hits that check, skips asInterface, returns from pm_register_connect, and never requests wlanmdsp.mbn",
            "peripheral-manager-service-object-null",
        )

    return (
        "v1757-peripheral-manager-branch-classification-incomplete",
        False,
        "Static branch and retained V1736 trace did not match the supported null service-object classification",
        "incomplete",
    )


def render_report(result: dict[str, Any]) -> str:
    branch = result["branch"]
    trace = result["trace"]
    strings = result["strings"]
    return "\n".join([
        "# Native Init V1757 WLAN-PD Peripheral Interface Branch Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1757`",
        "- Type: host/source-only `libperipheral_client.so` branch classifier",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Static Branch Evidence",
        "",
        "| Point | Offset | Instruction / String | Meaning |",
        "| --- | ---: | --- | --- |",
        f"| service-manager get call | `0x{OFFSETS['service_manager_get_call']:x}` | `{branch['service_manager_get_call']}` | lookup `vendor.qcom.PeripheralManager` |",
        f"| returned binder load | `0x{OFFSETS['returned_binder_load']:x}` | `{branch['returned_binder_load']}` | load returned binder strong pointer from stack |",
        f"| null branch | `0x{OFFSETS['returned_binder_null_branch']:x}` | `{branch['returned_binder_null_branch']}` | branch away from `asInterface` when returned pointer is null |",
        f"| asInterface call | `0x{OFFSETS['as_interface_call']:x}` | `{branch['as_interface_call']}` | only reachable when returned pointer is non-null |",
        f"| get-service-fail log | `0x{OFFSETS['get_service_fail_log']:x}` | `{branch['get_service_fail_log']}` | null-service failure path |",
        f"| log tag | `0x{OFFSETS['get_service_fail_tag']:x}` | `{strings['get_service_fail_tag']}` | Android log tag |",
        f"| fail format | `0x{OFFSETS['get_service_fail_format']:x}` | `{strings['get_service_fail_format']}` | branch target message |",
        f"| interface fail format | `0x{OFFSETS['get_interface_fail_format']:x}` | `{strings['get_interface_fail_format']}` | not reached in V1736 |",
        f"| service name | `0x{OFFSETS['service_name']:x}` | `{strings['service_name']}` | requested service object |",
        "",
        "## Retained V1736 Trace Alignment",
        "",
        "| Event | Hit Count | Interpretation |",
        "| --- | ---: | --- |",
        f"| `periph_service_manager_get_call` | `{trace['periph_service_manager_get_call']}` | service-manager lookup was attempted |",
        f"| `periph_binder_object_present_check` | `{trace['periph_binder_object_present_check']}` | code reached the `0x620c` returned-binder null check |",
        f"| `periph_as_interface_call` | `{trace['periph_as_interface_call']}` | skipped because the branch condition was true |",
        f"| `periph_manager_register_tx_call` | `{trace['periph_manager_register_tx_call']}` | no PeripheralManager register transaction occurred |",
        f"| `periph_pm_register_connect_return` | `{trace['periph_pm_register_connect_return']}` | function returned after failure path |",
        f"| `wlfw_service_request` | `{trace['wlfw_service_request']}` | CNSS still reaches the WLFW worker/request path |",
        f"| requested `wlanmdsp.mbn` | `{trace['requested_wlanmdsp']}` | modem still does not request WLAN-PD firmware |",
        "",
        "## Interpretation",
        "",
        "- V1756's broad `interface-conversion-gap` is now narrowed to a null service-object lookup.",
        "- `libperipheral_client.so` calls service-manager lookup for `vendor.qcom.PeripheralManager`, then loads the returned binder pointer and immediately tests it at `0x620c`.",
        "- The only path that skips `IPeripheralManager::asInterface` at `0x6218` is `cbz x8, 0x629c`, which logs `%s get service fail`.",
        "- Because V1736 hits the check, does not hit `asInterface`, and returns, the native route has no visible `vendor.qcom.PeripheralManager` binder service object in that service-manager context.",
        "- This does not justify adding broad PM actors. The next target is the narrow service-object registration/visibility contract for `vendor.qcom.PeripheralManager`.",
        "",
        "## Next Candidate",
        "",
        "- V1758 should stay host/source-only first: classify how `/vendor/bin/pm-service` registers `vendor.qcom.PeripheralManager`, which service manager/context it uses, and why prior native PM-trio attempts did not expose that object to `libperipheral_client.so`.",
        "- A later live gate, if approved, should repair only the service-object visibility/registration condition and measure PM vote plus `wlanmdsp.mbn` request.",
        "- Keep blocked: broad PM actor march, eSoC/RC1, `/dev/subsys_esoc0`, `boot_wlan`, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping until `wlanmdsp.mbn` request or WLFW service 69 appears.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host/source-only. It reads retained V1756 evidence, a staged vendor library, existing disassembly, and constant strings. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or new actor start.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1756-manifest", type=Path, default=DEFAULT_V1756)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIB)
    parser.add_argument("--disasm", type=Path, default=DEFAULT_DISASM)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    v1756 = load_json(args.v1756_manifest)
    disasm = parse_disasm(read_text(args.disasm))
    strings = {
        "get_service_fail_tag": read_c_string(args.library, OFFSETS["get_service_fail_tag"]),
        "get_service_fail_format": read_c_string(args.library, OFFSETS["get_service_fail_format"]),
        "get_interface_fail_format": read_c_string(args.library, OFFSETS["get_interface_fail_format"]),
        "service_name": read_c_string(args.library, OFFSETS["service_name"]),
    }
    decision, pass_ok, reason, label = classify(v1756, disasm, strings)
    trace = {
        "periph_service_manager_get_call": peripheral_hit(v1756, "periph_service_manager_get_call"),
        "periph_binder_object_present_check": peripheral_hit(v1756, "periph_binder_object_present_check"),
        "periph_as_interface_call": peripheral_hit(v1756, "periph_as_interface_call"),
        "periph_manager_register_tx_call": peripheral_hit(v1756, "periph_manager_register_tx_call"),
        "periph_pm_register_connect_return": peripheral_hit(v1756, "periph_pm_register_connect_return"),
        "wlfw_service_request": gate_value(v1756, "wlfw_service_request_hit_count"),
        "requested_wlanmdsp": gate_value(v1756, "requested_wlanmdsp"),
    }
    branch = {
        "service_manager_get_call": disasm.get(OFFSETS["service_manager_get_call"], ""),
        "returned_binder_load": disasm.get(OFFSETS["returned_binder_load"], ""),
        "returned_binder_null_branch": disasm.get(OFFSETS["returned_binder_null_branch"], ""),
        "as_interface_call": disasm.get(OFFSETS["as_interface_call"], ""),
        "get_service_fail_log": disasm.get(OFFSETS["get_service_fail_log"], ""),
    }
    result = {
        "cycle": "V1757",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "label": label,
        "v1756": {
            "manifest": display_path(args.v1756_manifest),
            "decision": v1756.get("decision"),
            "label": v1756.get("label"),
            "pass": bool(v1756.get("pass")),
        },
        "library": display_path(args.library),
        "disasm": display_path(args.disasm),
        "branch": branch,
        "strings": strings,
        "trace": trace,
        "out_dir": display_path(args.out_dir),
        "report_path": display_path(args.report_path),
        "safety": {
            "host_source_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credentials": False,
            "dhcp_routes": False,
            "external_ping": False,
        },
    }
    store.write_json("manifest.json", result)
    report = render_report(result)
    write_private_text(store.path("summary.md"), report)
    write_private_text(args.report_path, report)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
