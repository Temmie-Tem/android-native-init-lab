#!/usr/bin/env python3
"""V1587 host-only lower-marker next-gate classifier.

This reconciles the older V1496 RC1/LTSSM failure model with the latest V1586
service-window firmware handoff.  V1496 and the follow-up msm_pcie classifiers
remain valid for the forced RC1 enumerate path, but V1586 is now the freshest
active route: firmware mounts and modem PIL progress exist, while RC1/L0, MHI,
BDF, FW-ready, and wlan0 remain absent.  The next unit should therefore preserve
V1586 parity and add focused lower-marker sampling instead of repeating the old
RC1-only dossier or moving to credentials/connect.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1587-lower-marker-next-gate-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1587_LOWER_MARKER_NEXT_GATE_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1587-lower-marker-next-gate-classifier.txt")

V1496_MANIFEST = Path("tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/manifest.json")
V1496_DMESG = Path("tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/test-v1393-dmesg.stdout.txt")
V1535_MANIFEST = Path("tmp/wifi/v1535-first-l0-trigger-candidate-classifier/manifest.json")
V1560_MANIFEST = Path("tmp/wifi/v1560-android-order-vs-native-route-classifier/manifest.json")
V1586_MANIFEST = Path(
    "tmp/wifi/v1586-service-window-pm-proxy-contract-devnode-fwoverlay-handoff/manifest.json"
)
V1586_DMESG = Path(
    "tmp/wifi/v1586-service-window-pm-proxy-contract-devnode-fwoverlay-handoff"
    "/test-v1393-dmesg.stdout.txt"
)
V1586_HELPER = Path(
    "tmp/wifi/v1586-service-window-pm-proxy-contract-devnode-fwoverlay-handoff"
    "/test-v1393-helper-result.stdout.txt"
)

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
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
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


def count_lines(text: str, *needles: str) -> int:
    return sum(1 for line in text.splitlines() if all(needle in line for needle in needles))


def count_regex(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.I)
    return sum(1 for line in text.splitlines() if regex.search(line))


def helper_value(text: str, key: str) -> str | None:
    prefix = key + "="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def falsy(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    if value is None:
        return True
    return str(value).strip().lower() in {"", "0", "false", "none", "no", "n", "off"}


def classify() -> dict[str, Any]:
    v1496 = read_json(V1496_MANIFEST)
    v1535 = read_json(V1535_MANIFEST)
    v1560 = read_json(V1560_MANIFEST)
    v1586 = read_json(V1586_MANIFEST)
    v1496_dmesg = read_text(V1496_DMESG)
    v1586_dmesg = read_text(V1586_DMESG)
    v1586_helper = read_text(V1586_HELPER)
    v1586_progress = v1586.get("wifi_progress") if isinstance(v1586.get("wifi_progress"), dict) else {}

    v1496_rc1_fixed = (
        truthy(v1496.get("pass"))
        and truthy(v1496.get("wifi_progress", {}).get("rc1_progress") if isinstance(v1496.get("wifi_progress"), dict) else None)
        and falsy(v1496.get("wifi_progress", {}).get("rc1_l0") if isinstance(v1496.get("wifi_progress"), dict) else None)
    ) or (
        first_time(v1496_dmesg, "PCIe RC1 PHY is ready") is not None
        and first_time(v1496_dmesg, "PCIe RC1 link initialization failed") is not None
        and first_time(v1496_dmesg, "LTSSM_L0") is None
    )
    v1535_static_done = (
        truthy(v1535.get("pass"))
        and str(v1535.get("decision", "")).startswith("v1535-first-l0-candidates")
    )
    v1560_order_done = (
        truthy(v1560.get("pass"))
        and str(v1560.get("decision", "")).startswith("v1560-android-wlfw-before-ap2mdm")
    )
    v1586_current = (
        truthy(v1586.get("pass"))
        and str(v1586_progress.get("final_decision")) == "firmware-progress-no-wlan0"
        and truthy(v1586_progress.get("provider_trigger"))
        and truthy(v1586_progress.get("modem_trigger"))
        and truthy(v1586_progress.get("firmware_mounts_requested"))
        and truthy(v1586_progress.get("helper_result_subsys_open_attempted"))
        and truthy(v1586_progress.get("helper_result_mdm_helper_esoc0_fd_count"))
        and falsy(v1586_progress.get("mhi_progress"))
        and falsy(v1586_progress.get("bdf_progress"))
        and falsy(v1586_progress.get("fw_ready_progress"))
        and falsy(v1586_progress.get("wlan0_present"))
    )

    v1586_times = {
        "pm_proxy_helper_subsys_modem": first_time(v1586_dmesg, "pm_proxy_helper", "__subsystem_get: modem"),
        "modem_loading": first_time(v1586_dmesg, "subsys-pil-tz", "modem: loading"),
        "modem_brought_out_of_reset": first_time(v1586_dmesg, "subsys-pil-tz", "modem: Brought out of reset"),
        "cnss_diag_netlink": first_time(v1586_dmesg, "cnss_diag", "__netlink_sendskb"),
        "cnss_daemon_netlink": first_time(v1586_dmesg, "cnss-daemon", "__netlink_sendskb"),
        "subsys_esoc0": first_time(v1586_dmesg, "__subsystem_get: esoc0"),
        "bdf": first_time(v1586_dmesg, "BDF file"),
        "fw_ready": first_time(v1586_dmesg, "FW ready"),
        "wlan0": first_time(v1586_dmesg, "wlan0"),
    }
    marker_counts = {
        "rc1": count_lines(v1586_dmesg, "PCIe RC1"),
        "ltssm_l0": count_lines(v1586_dmesg, "LTSSM_L0"),
        "mhi_runtime": count_regex(v1586_dmesg, r"\bmhi\s+[0-9a-f:.]+|mhi_bl|/dev/mhi|mhi_[a-z].*probe"),
        "wlfw_start": count_lines(v1586_dmesg, "wlfw_start"),
        "icnss_qmi": count_lines(v1586_dmesg, "icnss_qmi"),
        "bdf": count_lines(v1586_dmesg, "BDF file"),
        "fw_ready": count_lines(v1586_dmesg, "FW ready"),
        "wlan0": count_lines(v1586_dmesg, "wlan0"),
    }
    helper_contract = {
        "mode": helper_value(v1586_helper, "android_wifi_service_window.mode"),
        "pm_proxy_contract": helper_value(v1586_helper, "android_wifi_service_window.pm_proxy_contract"),
        "pm_full_contract_seen": helper_value(v1586_helper, "android_wifi_service_window.pm_full_contract_seen"),
        "pm_proxy_helper_subsys_modem_initial_count": helper_value(
            v1586_helper, "android_wifi_service_window.pm_proxy_helper_subsys_modem_initial_count"
        ),
        "pm_proxy_helper_subsys_modem_final_count": helper_value(
            v1586_helper, "android_wifi_service_window.pm_proxy_helper_subsys_modem_fd_count"
        ),
        "per_mgr_subsys_modem_initial_count": helper_value(
            v1586_helper, "android_wifi_service_window.per_mgr_subsys_modem_initial_count"
        ),
        "per_mgr_subsys_modem_final_count": helper_value(
            v1586_helper, "android_wifi_service_window.per_mgr_subsys_modem_fd_count"
        ),
        "mdm_helper_esoc0_gate_count": helper_value(
            v1586_helper, "android_wifi_service_window.fd_match.mdm_helper_esoc0_gate.count"
        ),
        "subsys_trigger_gate": helper_value(v1586_helper, "android_wifi_service_window.subsys_trigger_gate"),
        "subsys_trigger_gate_open": helper_value(
            v1586_helper, "android_wifi_service_window.subsys_trigger_gate_open"
        ),
        "subsys_trigger_started": helper_value(v1586_helper, "android_wifi_service_window.subsys_trigger_started"),
        "result": helper_value(v1586_helper, "android_wifi_service_window.result"),
        "reason": helper_value(v1586_helper, "android_wifi_service_window.reason"),
    }

    pass_ = v1496_rc1_fixed and v1535_static_done and v1560_order_done and v1586_current
    decision = (
        "v1587-v1586-current-lower-marker-gate-required"
        if pass_
        else "v1587-input-evidence-incomplete-review-required"
    )
    reason = (
        "V1496 RC1/LTSSM and msm_pcie static work are already classified; V1586 is the current active route and needs focused RC1/MHI/WLFW request-state sampling before any connect work"
        if pass_
        else "one or more required V1496/V1535/V1560/V1586 predicates did not hold"
    )
    return {
        "decision": decision,
        "pass": pass_,
        "reason": reason,
        "predicates": {
            "v1496_rc1_link_failed_no_l0_fixed": v1496_rc1_fixed,
            "v1535_msm_pcie_static_candidate_done": v1535_static_done,
            "v1560_android_order_vs_native_route_done": v1560_order_done,
            "v1586_current_firmware_progress_no_wlan0": v1586_current,
        },
        "v1586_times": v1586_times,
        "v1586_marker_counts": marker_counts,
        "v1586_helper_contract": helper_contract,
        "v1586_progress_subset": {
            "final_decision": v1586_progress.get("final_decision"),
            "provider_trigger": v1586_progress.get("provider_trigger"),
            "modem_trigger": v1586_progress.get("modem_trigger"),
            "firmware_mounts_requested": v1586_progress.get("firmware_mounts_requested"),
            "helper_result_subsys_open_attempted": v1586_progress.get("helper_result_subsys_open_attempted"),
            "helper_result_subsys_trigger_started": v1586_progress.get("helper_result_subsys_trigger_started"),
            "helper_result_mdm_helper_esoc0_fd_count": v1586_progress.get("helper_result_mdm_helper_esoc0_fd_count"),
            "helper_result_pm_proxy_contract": v1586_progress.get("helper_result_pm_proxy_contract"),
            "helper_result_pm_full_contract_seen": v1586_progress.get("helper_result_pm_full_contract_seen"),
            "rc1_progress": v1586_progress.get("rc1_progress"),
            "mhi_progress": v1586_progress.get("mhi_progress"),
            "wlfw_progress": v1586_progress.get("wlfw_progress"),
            "bdf_progress": v1586_progress.get("bdf_progress"),
            "fw_ready_progress": v1586_progress.get("fw_ready_progress"),
            "wlan0_present": v1586_progress.get("wlan0_present"),
        },
        "next_gate": {
            "recommended_cycle": "V1588",
            "type": "source/build-only focused lower-marker sampler design",
            "focus": "preserve V1586 service-window firmware parity, then sample missing RC1/MHI/WLFW request-state boundaries",
            "requirements": [
                "do not repeat V1496 RC1 dossier or V1535 msm_pcie static analysis unless new input appears",
                "preserve V1586 firmware-only global vendor overlay and helper private sda29 vendor namespace",
                "sample process lifetimes and compact fd counts for pm_proxy_helper, pm-service, pm-proxy, mdm_helper, cnss_diag, cnss-daemon, and wificond",
                "sample subsystem states, RC1/LTSSM, MHI bus/pipe, QRTR/WLFW, BDF, FW-ready, and wlan0 markers in one bounded window",
                "keep scan/connect, credentials, DHCP/routes, external ping, blind eSoC notify/BOOT_DONE, PMIC/GPIO/GDSC direct writes, global PCI rescan, and platform bind/unbind blocked",
            ],
        },
    }


def yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    predicates = analysis["predicates"]
    progress = analysis["v1586_progress_subset"]
    times = analysis["v1586_times"]
    markers = analysis["v1586_marker_counts"]
    helper = analysis["v1586_helper_contract"]
    next_gate = analysis["next_gate"]
    return "\n".join(
        [
            "# Native Init V1587 Lower-Marker Next-Gate Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1587`",
            "- Type: host-only current-route reconciliation classifier",
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
                    ["native_v1496", rel(V1496_MANIFEST)],
                    ["v1535_first_l0_classifier", rel(V1535_MANIFEST)],
                    ["v1560_order_classifier", rel(V1560_MANIFEST)],
                    ["v1586_current_handoff", rel(V1586_MANIFEST)],
                    ["v1586_dmesg", rel(V1586_DMESG)],
                    ["v1586_helper_result", rel(V1586_HELPER)],
                ],
            ),
            "",
            "## Fixed Predicates",
            "",
            markdown_table(["predicate", "value"], [[key, yes_no(value)] for key, value in predicates.items()]),
            "",
            "## V1586 Current Route",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in progress.items()]),
            "",
            "## V1586 Timing Markers",
            "",
            markdown_table(
                ["marker", "first_time"],
                [[key, "missing" if value is None else f"{value:.6f}"] for key, value in times.items()],
            ),
            "",
            "## V1586 Marker Counts",
            "",
            markdown_table(["marker", "count"], [[key, value] for key, value in markers.items()]),
            "",
            "## V1586 Helper Contract Snapshot",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in helper.items()]),
            "",
            "## Interpretation",
            "",
            "V1496 remains a valid forced-RC1 failure: it reaches RC1 PHY/LTSSM progress and fails before L0.  However, the repository already contains the follow-up `msm_pcie` static and first-L0 candidate classifiers, so repeating a V1496-only dossier is not the best next unit.",
            "",
            "V1560 also adds an ordering caveat: Android-good evidence reaches `cnss-daemon wlfw_start` and BDF/FW-ready/`wlan0`, while the native RC1 route only sees generic CNSS/netlink plus forced enumerate.  The active latest evidence is V1586, which advances firmware mounts, modem PIL, private devnodes, `mdm_helper` `/dev/esoc-0`, and `subsys_esoc0` trigger coverage, but still has no RC1/L0, MHI, BDF, FW-ready, or `wlan0`.",
            "",
            "Therefore the next gate should not use credentials or attempt scan/connect.  It should preserve V1586 parity and add compact lower-marker sampling to determine whether the remaining gap is PM contract lifetime, missing WLFW request-state transition, no RC1 attempt on the current route, or post-RC1/MHI absence.",
            "",
            "## Next Gate",
            "",
            f"- Recommended cycle: `{next_gate['recommended_cycle']}`",
            f"- Type: {next_gate['type']}",
            f"- Focus: {next_gate['focus']}",
            "",
            "### Requirements",
            "",
            *[f"- {item}" for item in next_gate["requirements"]],
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
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
        "cycle": "V1587",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "host": collect_host_metadata(),
        "input_paths": {
            "native_v1496": rel(V1496_MANIFEST),
            "v1535_first_l0_classifier": rel(V1535_MANIFEST),
            "v1560_order_classifier": rel(V1560_MANIFEST),
            "v1586_current_handoff": rel(V1586_MANIFEST),
            "v1586_dmesg": rel(V1586_DMESG),
            "v1586_helper_result": rel(V1586_HELPER),
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
