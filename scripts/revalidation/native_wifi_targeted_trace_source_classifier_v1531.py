#!/usr/bin/env python3
"""V1531 host-only targeted source classifier after V1529/V1530 tracefs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_msm_pcie_test11_static_analysis_v1498 as v1498


DEFAULT_OUT_DIR = Path("tmp/wifi/v1531-targeted-trace-source-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1531_TARGETED_TRACE_SOURCE_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1531-targeted-trace-source-classifier.txt")

V1530_MANIFEST = Path("tmp/wifi/v1530-android-tracefs-native-no-l0-classifier/manifest.json")
V1529_EVIDENCE = Path(
    "tmp/wifi/v1529-android-tracefs-rc1-event-handoff/"
    "android-postfs-evidence/a90-v1529-tracefs-rc1-sampler"
)
ICNSS_C = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c")
ICNSS_QMI_C = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss_qmi.c")
ICNSS_PRIVATE_H = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss_private.h")
LOCAL_PCI_MSM_C = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c")
PM_SERVICE = Path("tmp/wifi/v1073-host-only/vendor-extract/files/pm-service")
PM_SERVICE_STRINGS_FILTER = Path("tmp/wifi/v1081-pm-service-early-path-classifier/analysis/pm-service-strings-filter.txt")


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


def line_number(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return index
    return None


def source_lines(text: str, needles: tuple[str, ...], limit: int = 32) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), 1):
        if any(needle in line for needle in needles):
            rows.append({"line": index, "text": line.strip()})
            if len(rows) >= limit:
                break
    return rows


def function_summary(text: str, signature_re: str, needles: tuple[str, ...] = ()) -> dict[str, Any]:
    start, end, body = v1498.extract_function(text, signature_re)
    return {
        "line_start": start,
        "line_end": end,
        "found": bool(body),
        "contains": {needle: needle in body for needle in needles},
        "key_lines": source_lines(body, needles, 24) if start is None else [
            {"line": start + item["line"] - 1, "text": item["text"]}
            for item in source_lines(body, needles, 24)
        ],
    }


def extract_cases(body: str) -> list[str]:
    cases: list[str] = []
    for line in body.splitlines():
        match = re.search(r"case\s+(ICNSS_DRIVER_EVENT_[A-Z0-9_]+)\s*:", line)
        if match:
            cases.append(match.group(1))
    return cases


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.I)
    return sum(1 for line in text.splitlines() if regex.search(line))


def first_trace_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
        if match:
            return float(match.group(1))
    return None


def first_dmesg_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
        if match:
            return float(match.group(1))
    return None


def matching_lines(text: str, pattern: str, limit: int = 12) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def delta_ms(later: float | None, earlier: float | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round((later - earlier) * 1000, 3)


def read_pci_source() -> tuple[str, dict[str, Any]]:
    local = repo_path(LOCAL_PCI_MSM_C)
    if local.exists():
        text = local.read_text(encoding="utf-8", errors="replace")
        return text, {
            "kind": "local-osrc-build-copy",
            "path": rel(LOCAL_PCI_MSM_C),
            "sha256": v1498.sha256_text(text),
        }
    class Args:
        pcie_source: Path | None = None
        pcie_source_url: str = v1498.DEFAULT_PCIE_SOURCE_URL
        fetch_timeout: int = 20

    text, meta = v1498.read_pcie_source(Args())
    return text, meta


def analyze_icnss_source() -> dict[str, Any]:
    icnss = read_text(ICNSS_C)
    qmi = read_text(ICNSS_QMI_C)
    private_h = read_text(ICNSS_PRIVATE_H)
    event_work_start, event_work_end, event_work_body = v1498.extract_function(
        icnss,
        r"\bstatic\s+void\s+icnss_driver_event_work\s*\(",
    )
    post_start, post_end, post_body = v1498.extract_function(
        icnss,
        r"\bint\s+icnss_driver_event_post\s*\(",
    )
    return {
        "inputs": {
            "icnss_c": rel(ICNSS_C),
            "icnss_qmi_c": rel(ICNSS_QMI_C),
            "icnss_private_h": rel(ICNSS_PRIVATE_H),
        },
        "event_enum": {
            "line_start": line_number(private_h, "enum icnss_driver_event_type"),
            "events": re.findall(r"\b(ICNSS_DRIVER_EVENT_[A-Z0-9_]+)\b", private_h),
        },
        "event_post": {
            "line_start": post_start,
            "line_end": post_end,
            "queues_single_work_item": "queue_work(penv->event_wq, &penv->event_work)" in post_body,
            "debug_print_has_event_type": "Posting event:" in post_body,
            "key_lines": source_lines(
                post_body,
                (
                    "icnss_pr_dbg(\"Posting event:",
                    "event->type = type",
                    "list_add_tail",
                    "queue_work(penv->event_wq, &penv->event_work)",
                ),
            ),
        },
        "event_work": {
            "line_start": event_work_start,
            "line_end": event_work_end,
            "found": bool(event_work_body),
            "dispatch_cases": extract_cases(event_work_body),
            "dispatches_multiple_event_types": len(extract_cases(event_work_body)) > 1,
            "key_lines": source_lines(
                event_work_body,
                (
                    "icnss_pr_dbg(\"Processing event:",
                    "case ICNSS_DRIVER_EVENT_SERVER_ARRIVE",
                    "case ICNSS_DRIVER_EVENT_FW_READY_IND",
                    "case ICNSS_DRIVER_EVENT_REGISTER_DRIVER",
                    "icnss_driver_event_server_arrive",
                    "icnss_driver_event_fw_ready_ind",
                    "icnss_driver_event_register_driver",
                ),
            ),
        },
        "wlfw_new_server": function_summary(
            qmi,
            r"\bstatic\s+int\s+wlfw_new_server\s*\(",
            (
                "icnss_driver_event_post(ICNSS_DRIVER_EVENT_SERVER_ARRIVE",
                "event_data->node = service->node",
                "event_data->port = service->port",
            ),
        ),
        "fw_ready_cb": function_summary(
            qmi,
            r"\bstatic\s+void\s+fw_ready_ind_cb\s*\(",
            ("icnss_driver_event_post(ICNSS_DRIVER_EVENT_FW_READY_IND",),
        ),
        "register_driver": function_summary(
            icnss,
            r"\bint\s+__icnss_register_driver\s*\(",
            ("icnss_driver_event_post(ICNSS_DRIVER_EVENT_REGISTER_DRIVER",),
        ),
        "probe_event_work_init": {
            "alloc_workqueue_line": line_number(icnss, 'alloc_workqueue("icnss_driver_event"'),
            "init_work_line": line_number(icnss, "INIT_WORK(&priv->event_work, icnss_driver_event_work)"),
        },
    }


def analyze_pci_source() -> dict[str, Any]:
    pcie, meta = read_pci_source()
    enumerate = function_summary(
        pcie,
        r"\bint\s+msm_pcie_enumerate\s*\(",
        ("msm_pcie_enable(dev, PM_ALL)", "pci_scan_root_bus", "pci_bus_add_devices", "dev->enumerated = true"),
    )
    enable = function_summary(
        pcie,
        r"\bstatic\s+int\s+msm_pcie_enable\s*\(",
        ("msm_pcie_config_controller", "msm_pcie_write_mask", "LTSSM_STATE", "link initialization failed"),
    )
    wake_func = function_summary(
        pcie,
        r"\bstatic\s+void\s+handle_wake_func\s*\(",
        ("msm_pcie_enumerate(dev->rc_idx)", "Start enumeration"),
    )
    wake_irq = function_summary(
        pcie,
        r"\bstatic\s+irqreturn_t\s+handle_wake_irq\s*\(",
        ("MSM_PCIE_NO_WAKE_ENUMERATION", "schedule_work(&dev->handle_wake_work)"),
    )
    probe = function_summary(
        pcie,
        r"\bstatic\s+int\s+msm_pcie_probe\s*\(",
        ("qcom,boot-option", "MSM_PCIE_NO_PROBE_ENUMERATION", "msm_pcie_enumerate(rc_idx)"),
    )
    return {
        "source": meta,
        "test11_case_line": line_number(pcie, "case MSM_PCIE_ENUMERATION:"),
        "ltssm_l0_value_line": line_number(pcie, "MSM_PCIE_LTSSM_L0 = 0x11"),
        "poll_compliance_value_line": line_number(pcie, "MSM_PCIE_LTSSM_POLL_COMPLIANCE = 0x03"),
        "enumerate": enumerate,
        "enable": enable,
        "wake_irq": wake_irq,
        "wake_func": wake_func,
        "probe": probe,
        "callsite_classification": {
            "debugfs_test11_converges_on_enumerate": line_number(pcie, "case MSM_PCIE_ENUMERATION:") is not None
            and "msm_pcie_enumerate(dev->rc_idx)" in pcie,
            "wake_path_converges_on_enumerate": wake_irq["contains"].get("schedule_work(&dev->handle_wake_work)", False)
            and wake_func["contains"].get("msm_pcie_enumerate(dev->rc_idx)", False),
            "probe_can_be_deferred_by_boot_option": probe["contains"].get("MSM_PCIE_NO_PROBE_ENUMERATION", False),
        },
    }


def analyze_pm_service() -> dict[str, Any]:
    strings_filter = read_text(PM_SERVICE_STRINGS_FILTER)
    binary_present = repo_path(PM_SERVICE).exists()
    generated = ""
    if binary_present:
        import subprocess

        result = subprocess.run(
            ["strings", "-a", str(repo_path(PM_SERVICE))],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        generated = "\n".join(
            line
            for line in result.stdout.splitlines()
            if re.search(r"subsys|esoc|modem|peripheral|voter|SDX|QMI|vendor\.qcom", line, re.I)
        )
    combined = "\n".join(part for part in (strings_filter, generated) if part)
    return {
        "binary": rel(PM_SERVICE),
        "binary_present": binary_present,
        "strings_source": rel(PM_SERVICE_STRINGS_FILTER) if read_text(PM_SERVICE_STRINGS_FILTER) else "generated",
        "has_vendor_peripheral_manager_service": "vendor.qcom.PeripheralManager" in combined,
        "has_qmi_restart_strings": "QMI service system restart request" in combined,
        "has_voter_strings": "voter" in combined,
        "supported_peripherals": sorted(set(re.findall(r"\b(?:modem|SDX50M|SDX55M|SDXPRAIRIE)\b", combined))),
        "key_lines": [
            line.strip()
            for line in combined.splitlines()
            if re.search(r"vendor\.qcom\.PeripheralManager|QMI service system restart request|voter|SDX50M|modem", line)
        ][:24],
    }


def analyze_v1529_timing() -> dict[str, Any]:
    v1530 = read_json(V1530_MANIFEST)
    v1530_timeline = (((v1530.get("analysis") or {}).get("v1529") or {}).get("timeline") or {})
    trace = read_text(V1529_EVIDENCE / "tracefs-events.txt")
    dmesg = "\n".join(
        part
        for part in (
            read_text(V1529_EVIDENCE / "dmesg-filtered.txt"),
            read_text(V1529_EVIDENCE.parent / "host-dmesg-filtered.txt"),
        )
        if part
    )
    timeline = {
        "modem_pil_notif": first_trace_ts(trace, r"\bpil_notif:.*fw=modem"),
        "icnss_driver_event_work": first_trace_ts(trace, r"workqueue_execute_start:.*icnss_driver_event_work"),
        "pm_service_exec": first_trace_ts(trace, r"sched_process_exec: filename=/vendor/bin/pm-service"),
        "pm_service_modem_get": first_dmesg_ts(dmesg, r"Binder:.*__subsystem_get:\s+modem count:1"),
        "wlfw_start": first_dmesg_ts(dmesg, r"wlfw_start: Starting"),
        "pm_service_esoc0_get": first_dmesg_ts(dmesg, r"Binder:.*__subsystem_get:\s+esoc0 count:0"),
        "qmi_server_connected": first_dmesg_ts(dmesg, r"QMI Server Connected"),
        "fw_ready": first_dmesg_ts(dmesg, r"FW ready|WLAN FW is ready"),
        "wlan0": first_dmesg_ts(dmesg, r"\bwlan0\b"),
    }
    if v1530_timeline:
        for key, value in v1530_timeline.items():
            timeline.setdefault(key, value)
    return {
        "manifest": rel(V1530_MANIFEST),
        "evidence": rel(V1529_EVIDENCE),
        "timeline": timeline,
        "deltas_ms": {
            "modem_pil_to_icnss_work": delta_ms(timeline["icnss_driver_event_work"], timeline["modem_pil_notif"]),
            "icnss_work_to_pm_service_exec": delta_ms(timeline["pm_service_exec"], timeline["icnss_driver_event_work"]),
            "pm_service_exec_to_modem_get": delta_ms(timeline["pm_service_modem_get"], timeline["pm_service_exec"]),
            "pm_service_exec_to_esoc0_get": delta_ms(timeline["pm_service_esoc0_get"], timeline["pm_service_exec"]),
            "wlfw_start_to_esoc0_get": delta_ms(timeline["pm_service_esoc0_get"], timeline["wlfw_start"]),
            "esoc0_get_to_qmi": delta_ms(timeline["qmi_server_connected"], timeline["pm_service_esoc0_get"]),
            "qmi_to_fw_ready": delta_ms(timeline["fw_ready"], timeline["qmi_server_connected"]),
            "fw_ready_to_wlan0": delta_ms(timeline["wlan0"], timeline["fw_ready"]),
        },
        "counts": {
            "icnss_driver_event_work": count_lines(trace, r"icnss_driver_event_work"),
            "pil_modem": count_lines(trace, r"\bpil_notif:.*fw=modem"),
            "pil_esoc_sdx": count_lines(trace, r"\bpil_notif:.*fw=(?:esoc0|SDX|sdx)"),
            "pm_service_exec": count_lines(trace, r"filename=/vendor/bin/pm-service"),
            "rc1_ltssm_text": count_lines(dmesg, r"RC1|LTSSM"),
        },
        "excerpts": {
            "icnss_work": matching_lines(trace, r"icnss_driver_event_work", 8),
            "pm_service": matching_lines(trace + "\n" + dmesg, r"pm-service|Binder:.*__subsystem_get", 12),
            "lower": matching_lines(dmesg, r"wlfw_start|__subsystem_get|QMI Server Connected|FW ready|\bwlan0\b", 16),
        },
    }


def build_analysis() -> dict[str, Any]:
    source = {
        "icnss": analyze_icnss_source(),
        "pci_msm": analyze_pci_source(),
        "pm_service": analyze_pm_service(),
    }
    timing = analyze_v1529_timing()
    checks = {
        "v1530_pass": read_json(V1530_MANIFEST).get("pass") is True,
        "icnss_event_work_is_generic_dispatcher": source["icnss"]["event_work"]["dispatches_multiple_event_types"],
        "wlfw_new_server_posts_server_arrive": source["icnss"]["wlfw_new_server"]["contains"].get(
            "icnss_driver_event_post(ICNSS_DRIVER_EVENT_SERVER_ARRIVE",
            False,
        ),
        "fw_ready_posts_fw_ready_event": source["icnss"]["fw_ready_cb"]["contains"].get(
            "icnss_driver_event_post(ICNSS_DRIVER_EVENT_FW_READY_IND",
            False,
        ),
        "register_driver_posts_register_event": source["icnss"]["register_driver"]["contains"].get(
            "icnss_driver_event_post(ICNSS_DRIVER_EVENT_REGISTER_DRIVER",
            False,
        ),
        "pm_service_is_proprietary_binder_qmi_voter_actor": source["pm_service"]["has_vendor_peripheral_manager_service"]
        and source["pm_service"]["has_qmi_restart_strings"]
        and source["pm_service"]["has_voter_strings"],
        "pci_wake_path_converges_on_enumerate": source["pci_msm"]["callsite_classification"][
            "wake_path_converges_on_enumerate"
        ],
        "pci_debugfs_test11_converges_on_enumerate": source["pci_msm"]["callsite_classification"][
            "debugfs_test11_converges_on_enumerate"
        ],
        "android_trace_has_icnss_work_but_no_event_type": timing["counts"]["icnss_driver_event_work"] > 0
        and timing["counts"]["pil_esoc_sdx"] == 0,
        "android_trace_still_has_no_rc1_ltssm_text": timing["counts"]["rc1_ltssm_text"] == 0,
    }
    pass_ok = all(checks.values())
    decision = (
        "v1531-targeted-trace-source-classifies-visible-signals-not-trigger"
        if pass_ok
        else "v1531-targeted-trace-source-incomplete"
    )
    reason = (
        "ICNSS workqueue trace is a generic dispatcher, pm-service is the proprietary Binder/QMI voter actor, "
        "and pci-msm initial L0 still needs a targeted callsite/trigger observer rather than firmware/MHI work"
        if pass_ok
        else "Required ICNSS/PM/pci-msm source or V1529/V1530 evidence is incomplete"
    )
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "checks": checks,
        "timing": timing,
        "source": source,
        "classification": {
            "icnss_driver_event_work_meaning": (
                "tracefs workqueue_execute_start proves the shared ICNSS event worker ran, "
                "but source shows that worker dispatches SERVER_ARRIVE, FW_READY, REGISTER_DRIVER, "
                "and other events through the same function; workqueue trace alone cannot identify event type"
            ),
            "pm_service_meaning": (
                "pm-service is the proprietary vendor.qcom.PeripheralManager actor. V1529 sees it exec, then "
                "Binder thread subsystem_get(modem), WLFW start, subsystem_get(esoc0), QMI server, BDF, FW-ready, wlan0"
            ),
            "pci_msm_meaning": (
                "pci-msm TEST:11, wake IRQ work, sysfs enumerate, and probe paths converge on msm_pcie_enumerate; "
                "native already reaches the enable/LTSSM path but fails before L0"
            ),
            "current_blocker": (
                "identify or reproduce Android's first-L0 trigger/readiness edge before native TEST:11/enable, "
                "not firmware/MHI/WLFW after L0"
            ),
        },
        "next_gate": {
            "primary": "V1532 targeted Android tracefs design for queue_work/execute pairing plus pm-service Binder subsystem_get timing",
            "rationale": (
                "V1531 shows the existing `workqueue_execute_start` signal is useful but too generic. "
                "The next read-only Android reference should add `workqueue_queue_work` if available, keep "
                "`workqueue_execute_start/end`, `sched_process_exec`, and `printk/console`, then classify "
                "the work item pointer for `icnss_driver_event_work` and the pm-service Binder subsystem_get "
                "sequence without enabling broad IRQ tracing."
            ),
            "do_not_do_yet": [
                "native firmware/MHI/WLFW deep dive",
                "Wi-Fi HAL start",
                "scan/connect/credentials",
                "DHCP/routes/external ping",
                "PMIC/GPIO/GDSC direct writes",
                "blind eSoC notify or BOOT_DONE spoof",
                "global PCI rescan",
                "platform bind/unbind",
            ],
        },
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    timing = analysis["timing"]
    source = analysis["source"]
    return "\n".join(
        [
            "# Native Init V1531 Targeted Trace Source Classifier",
            "",
            f"- Generated: `{manifest['generated_at']}`",
            f"- Decision: `{manifest['decision']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Checks",
            "",
            markdown_table(["check", "value"], [[key, value] for key, value in analysis["checks"].items()]),
            "",
            "## Timing",
            "",
            markdown_table(["event", "timestamp_s"], [[key, value] for key, value in timing["timeline"].items()]),
            "",
            "## Timing Deltas",
            "",
            markdown_table(["delta", "ms"], [[key, value] for key, value in timing["deltas_ms"].items()]),
            "",
            "## ICNSS Source Mapping",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["event_work_lines", f"{source['icnss']['event_work']['line_start']}..{source['icnss']['event_work']['line_end']}"],
                    ["dispatch_cases", json.dumps(source["icnss"]["event_work"]["dispatch_cases"])],
                    ["wlfw_new_server", json.dumps(source["icnss"]["wlfw_new_server"]["contains"], sort_keys=True)],
                    ["fw_ready_cb", json.dumps(source["icnss"]["fw_ready_cb"]["contains"], sort_keys=True)],
                    ["register_driver", json.dumps(source["icnss"]["register_driver"]["contains"], sort_keys=True)],
                ],
            ),
            "",
            "## PM Service Mapping",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["binary", source["pm_service"]["binary"]],
                    ["binary_present", source["pm_service"]["binary_present"]],
                    ["supported_peripherals", json.dumps(source["pm_service"]["supported_peripherals"])],
                    ["binder_service", source["pm_service"]["has_vendor_peripheral_manager_service"]],
                    ["qmi_restart_strings", source["pm_service"]["has_qmi_restart_strings"]],
                    ["voter_strings", source["pm_service"]["has_voter_strings"]],
                ],
            ),
            "",
            "## PCIe Source Mapping",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["source", json.dumps(source["pci_msm"]["source"], sort_keys=True)],
                    ["test11_case_line", source["pci_msm"]["test11_case_line"]],
                    ["enumerate_lines", f"{source['pci_msm']['enumerate']['line_start']}..{source['pci_msm']['enumerate']['line_end']}"],
                    ["enable_lines", f"{source['pci_msm']['enable']['line_start']}..{source['pci_msm']['enable']['line_end']}"],
                    ["wake_irq_lines", f"{source['pci_msm']['wake_irq']['line_start']}..{source['pci_msm']['wake_irq']['line_end']}"],
                    ["wake_func_lines", f"{source['pci_msm']['wake_func']['line_start']}..{source['pci_msm']['wake_func']['line_end']}"],
                    ["callsite_classification", json.dumps(source["pci_msm"]["callsite_classification"], sort_keys=True)],
                ],
            ),
            "",
            "## Interpretation",
            "",
            f"- ICNSS: {analysis['classification']['icnss_driver_event_work_meaning']}",
            f"- PM service: {analysis['classification']['pm_service_meaning']}",
            f"- PCIe: {analysis['classification']['pci_msm_meaning']}",
            f"- Current blocker: {analysis['classification']['current_blocker']}",
            "",
            "## Evidence Excerpts",
            "",
            "### ICNSS Work",
            "",
            "\n".join(f"- `{line}`" for line in timing["excerpts"]["icnss_work"][:8]),
            "",
            "### PM Service",
            "",
            "\n".join(f"- `{line}`" for line in timing["excerpts"]["pm_service"][:8]),
            "",
            "### Lower Wi-Fi Markers",
            "",
            "\n".join(f"- `{line}`" for line in timing["excerpts"]["lower"][:10]),
            "",
            "## Next Gate",
            "",
            f"- Primary: {analysis['next_gate']['primary']}",
            f"- Rationale: {analysis['next_gate']['rationale']}",
            "- Do not do yet: " + ", ".join(f"`{item}`" for item in analysis["next_gate"]["do_not_do_yet"]),
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = build_analysis()
    manifest = {
        "cycle": "V1531",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "v1530_manifest": rel(V1530_MANIFEST),
            "v1529_evidence": rel(V1529_EVIDENCE),
            "icnss_c": rel(ICNSS_C),
            "icnss_qmi_c": rel(ICNSS_QMI_C),
            "icnss_private_h": rel(ICNSS_PRIVATE_H),
            "pci_msm_c": rel(LOCAL_PCI_MSM_C),
            "pm_service": rel(PM_SERVICE),
        },
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
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), report)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
