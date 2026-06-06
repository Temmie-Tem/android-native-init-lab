#!/usr/bin/env python3
"""V1911 host-only classifier for the service74 caller boundary."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


CYCLE = "V1911"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1911-service74-caller-boundary-classifier")
DEFAULT_REPORT = Path("docs/reports/NATIVE_INIT_V1911_SERVICE74_CALLER_BOUNDARY_CLASSIFIER_2026-06-03.md")
DEFAULT_V1910 = Path("tmp/wifi/v1910-android-early-servloc-domain-handoff-live-20260603-214749/manifest.json")
DEFAULT_V1908 = Path("tmp/wifi/v1908-servloc-domain-list-live-handoff/manifest.json")
KERNEL_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')
ICNSS = KERNEL_ROOT / "drivers/soc/qcom/icnss.c"
SERVICE_NOTIFIER = KERNEL_ROOT / "drivers/soc/qcom/service-notifier.c"
SERVICE_NOTIFIER_H = KERNEL_ROOT / "include/soc/qcom/service-notifier.h"
DEFCONFIG = KERNEL_ROOT / "arch/arm64/configs/r3q_kor_single_defconfig"


DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def dmesg_time(line: str) -> float | None:
    match = DMESG_TIME_RE.search(line or "")
    return float(match.group("time")) if match else None


def line_number(text: str, pattern: str) -> int:
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return 0


def source_summary() -> dict[str, Any]:
    icnss = read_text(ICNSS)
    notifier = read_text(SERVICE_NOTIFIER)
    header = read_text(SERVICE_NOTIFIER_H)
    non_header_callers = []
    for path in (ICNSS, SERVICE_NOTIFIER):
        text = read_text(path)
        for index, line in enumerate(text.splitlines(), start=1):
            if "service_notif_register_notifier(" in line and not line.lstrip().startswith(("/*", "*")):
                if path == SERVICE_NOTIFIER and re.search(r"void \*service_notif_register_notifier", line):
                    continue
                non_header_callers.append(f"{rel(path)}:{index}")
    return {
        "icnss_notify_line": f"{rel(ICNSS)}:{line_number(icnss, r'icnss_get_service_location_notify')}",
        "icnss_register_line": f"{rel(ICNSS)}:{line_number(icnss, r'service_notif_register_notifier\(pd->domain_list\[i\]\.name')}",
        "notifier_export_line": f"{rel(SERVICE_NOTIFIER)}:{line_number(notifier, r'EXPORT_SYMBOL\(service_notif_register_notifier\)')}",
        "notifier_qmi_lookup_line": f"{rel(SERVICE_NOTIFIER)}:{line_number(notifier, r'qmi_add_lookup\(&qmi_data->clnt_handle')}",
        "notifier_new_server_line": f"{rel(SERVICE_NOTIFIER)}:{line_number(notifier, r'service_notifier_new_server')}",
        "header_decl_line": f"{rel(SERVICE_NOTIFIER_H)}:{line_number(header, r'service_notif_register_notifier')}",
        "non_header_callers": non_header_callers,
        "non_header_caller_count": len(non_header_callers),
        "exported_symbol": "EXPORT_SYMBOL(service_notif_register_notifier)" in notifier,
    }


def trace_capability_summary() -> dict[str, Any]:
    config = read_text(DEFCONFIG)
    return {
        "defconfig": rel(DEFCONFIG),
        "kprobes": "CONFIG_KPROBES=y" in config,
        "kprobe_events": "CONFIG_KPROBE_EVENTS=y" in config,
        "function_tracer": "CONFIG_FUNCTION_TRACER=y" in config,
        "function_graph": "CONFIG_FUNCTION_GRAPH_TRACER=y" in config,
        "uprobes": "CONFIG_UPROBE_EVENTS=y" in config,
        "kallsyms": "CONFIG_KALLSYMS=y" in config,
    }


def v1910_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    early = next((item for item in analysis.get("query_success_examples", []) if item.get("name") == "query-early.txt"), {})
    return {
        "manifest": rel(repo_path(path)),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "label": manifest.get("label", ""),
        "query_instances": analysis.get("query_instances") or [],
        "query_domain74_seen": boolish(analysis.get("query_domain74_seen")),
        "query_domain180_seen": boolish(analysis.get("query_domain180_seen")),
        "early_send_s": float(early.get("send_ms") or 0) / 1000.0 if early else 0.0,
        "early_response_s": float(early.get("response_ms") or 0) / 1000.0 if early else 0.0,
        "service74_time_s": dmesg_time(analysis.get("first_service74_line", "")),
        "service180_time_s": dmesg_time(analysis.get("first_service180_line", "")),
        "wlan_pd_time_s": dmesg_time(analysis.get("first_wlan_pd_line", "")),
        "wlfw_request_count": intish(analysis.get("wlfw_service_request_count")),
        "wlanmdsp_count": intish(analysis.get("wlanmdsp_count")),
        "wlan0_time_s": dmesg.get("wlan0_time_s"),
        "pcie_mhi_before_wlan0": intish(dmesg.get("pcie_mhi_before_wlan0")),
        "esoc_failed_before_wlan0": intish(dmesg.get("esoc_boot_failed_before_wlan0")),
        "degraded_257s_like": boolish(dmesg.get("degraded_257s_like")),
    }


def v1908_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    gate = manifest.get("gate") or {}
    return {
        "manifest": rel(repo_path(path)),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "label": gate.get("servloc_live_label", ""),
        "servloc_instance": gate.get("servloc_domain0_instance_id", ""),
        "service74_counts": gate.get("raw_service74_text_counts", ""),
        "wlan_pd_counts": gate.get("raw_wlan_pd_text_counts", ""),
    }


def classify(v1910: dict[str, Any], v1908: dict[str, Any], source: dict[str, Any], trace: dict[str, Any]) -> tuple[str, bool, str, str]:
    normal_android = (
        v1910["pass"]
        and v1910["query_domain180_seen"]
        and not v1910["query_domain74_seen"]
        and v1910["service74_time_s"] is not None
        and v1910["wlan_pd_time_s"] is not None
        and v1910["wlan0_time_s"] is not None
        and v1910["pcie_mhi_before_wlan0"] == 0
        and v1910["esoc_failed_before_wlan0"] == 0
        and not v1910["degraded_257s_like"]
    )
    native_gap = (
        v1908["pass"]
        and v1908["label"] == "servloc-domain-list-180-only-service74-missing"
        and str(v1908["servloc_instance"]) == "180"
        and str(v1908["service74_counts"]) == "0,0,0"
    )
    source_boundary = (
        source["non_header_caller_count"] == 1
        and source["exported_symbol"]
        and not trace["kprobes"]
        and not trace["function_tracer"]
    )
    if not normal_android:
        return (
            "v1911-android-normal-evidence-not-ready",
            False,
            "V1910 Android-good early service-locator evidence is missing or contaminated",
            "android-normal-evidence-not-ready",
        )
    if not native_gap:
        return (
            "v1911-native-service74-gap-not-ready",
            False,
            "V1908 native service74 gap baseline is missing",
            "native-service74-gap-not-ready",
        )
    if source_boundary:
        return (
            "v1911-service74-pre-wlanpd-caller-boundary-host-pass",
            True,
            "service74 publishes before wlan_pd while early wlan/fw locator response is 180-only; OSRC exposes only the ICNSS domain-list caller plus an exported notifier API, and stock kernel tracing cannot capture a kernel caller stack",
            "service74-pre-wlanpd-caller-boundary",
        )
    return (
        "v1911-service74-caller-boundary-incomplete",
        False,
        "source or trace capability boundary is incomplete",
        "service74-caller-boundary-incomplete",
    )


def render_report(manifest: dict[str, Any]) -> str:
    v1910 = manifest["v1910"]
    v1908 = manifest["v1908"]
    source = manifest["source"]
    trace = manifest["trace_capability"]
    return "\n".join([
        "# Native Init V1911 Service74 Caller Boundary Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only source/evidence classifier for service-notifier instance 74 caller boundary",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Android-good Edge",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["manifest", v1910["manifest"]],
                ["decision/pass/label", f"{v1910['decision']}/{v1910['pass']}/{v1910['label']}"],
                ["early query instances/domain74/domain180", f"{json.dumps(v1910['query_instances'])}/{v1910['query_domain74_seen']}/{v1910['query_domain180_seen']}"],
                ["time service180/service74/query/wlan_pd/wlan0", f"{v1910['service180_time_s']}/{v1910['service74_time_s']}/{v1910['early_response_s']}/{v1910['wlan_pd_time_s']}/{v1910['wlan0_time_s']}"],
                ["contamination pcie-mhi/esoc/degraded257", f"{v1910['pcie_mhi_before_wlan0']}/{v1910['esoc_failed_before_wlan0']}/{v1910['degraded_257s_like']}"],
            ],
        ),
        "",
        "## Native Baseline",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["manifest", v1908["manifest"]],
                ["decision/pass/label", f"{v1908['decision']}/{v1908['pass']}/{v1908['label']}"],
                ["servloc instance/service74/wlan_pd", f"{v1908['servloc_instance']}/{v1908['service74_counts']}/{v1908['wlan_pd_counts']}"],
            ],
        ),
        "",
        "## Source Boundary",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["icnss notify/register", f"{source['icnss_notify_line']} / {source['icnss_register_line']}"],
                ["service-notifier lookup/new-server", f"{source['notifier_qmi_lookup_line']} / {source['notifier_new_server_line']}"],
                ["export/header", f"{source['notifier_export_line']} / {source['header_decl_line']}"],
                ["non-header callers", json.dumps(source["non_header_callers"])],
                ["exported symbol", source["exported_symbol"]],
            ],
        ),
        "",
        "## Trace Capability",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["defconfig", trace["defconfig"]],
                ["kprobes/kprobe-events", f"{trace['kprobes']}/{trace['kprobe_events']}"],
                ["function/function-graph", f"{trace['function_tracer']}/{trace['function_graph']}"],
                ["uprobes/kallsyms", f"{trace['uprobes']}/{trace['kallsyms']}"],
            ],
        ),
        "",
        "## Selected Diff",
        "",
        "- Label: `service74-pre-wlanpd-caller-boundary`.",
        "- V1910 corrects the service-locator hypothesis: the earliest successful Android user-space `wlan/fw` query is 180-only, and it occurs before `wlan_pd` state-up but just after service74 publication.",
        "- Android service74 is before `cnss-daemon` WLFW start and before `wlan_pd`; native V1908 remains service74=0 with the same 180-only locator baseline.",
        "- OSRC has only the ICNSS domain-list caller, but the notifier API is exported; a closed/binary caller or transient in-kernel registration cannot be ruled out from source alone.",
        "- Stock-kernel kprobe/function-tracer caller-stack capture is unavailable, so do not spend another live run on kprobe/function ftrace for this edge.",
        "",
        "## Safety Scope",
        "",
        "V1911 is host-only. It reads retained manifests, local source, and defconfig text. It performs no live device command, flash, reboot, tracefs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.",
        "",
        "## Next",
        "",
        "- Next useful action should avoid SDX50M/PCIe/GDSC and either collect read-only Android `/proc/kallsyms` plus module ownership for `service_notif_register_notifier`, or build a native service66/instance18945 readback gate if the goal is to test whether instance74 is externally visible without sending restart-PD.",
        "- Do not attempt Wi-Fi credentials/connect/ping until native proves WLFW service69 and `wlan0`.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--v1910-manifest", type=Path, default=DEFAULT_V1910)
    parser.add_argument("--v1908-manifest", type=Path, default=DEFAULT_V1908)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v1910 = v1910_summary(args.v1910_manifest)
    v1908 = v1908_summary(args.v1908_manifest)
    source = source_summary()
    trace = trace_capability_summary()
    decision, pass_ok, reason, label = classify(v1910, v1908, source, trace)
    manifest = {
        "cycle": CYCLE,
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "reason": reason,
        "out_dir": rel(repo_path(args.out_dir)),
        "v1910": v1910,
        "v1908": v1908,
        "source": source,
        "trace_capability": trace,
        "device_commands_executed": False,
        "tracefs_write_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "restart_pd_request_executed": False,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    write_private_text(repo_path(args.report), report)
    print(json.dumps({"decision": decision, "pass": pass_ok, "label": label, "out_dir": manifest["out_dir"], "report": rel(repo_path(args.report))}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
