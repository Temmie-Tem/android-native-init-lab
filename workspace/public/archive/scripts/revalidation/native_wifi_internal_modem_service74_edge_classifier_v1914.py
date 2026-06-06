#!/usr/bin/env python3
"""V1914 host-only classifier for the internal-modem service74 publication edge."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


CYCLE = "V1914"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1914-internal-modem-service74-edge-classifier")
DEFAULT_REPORT = Path("docs/reports/NATIVE_INIT_V1914_INTERNAL_MODEM_SERVICE74_EDGE_CLASSIFIER_2026-06-03.md")
DEFAULT_V1908 = Path("tmp/wifi/v1908-servloc-domain-list-live-handoff/manifest.json")
DEFAULT_V1910 = Path("tmp/wifi/v1910-android-early-servloc-domain-handoff-live-20260603-214749/manifest.json")
DEFAULT_V1911 = Path("tmp/wifi/v1911-service74-caller-boundary-classifier/manifest.json")
DEFAULT_V1912 = Path("tmp/wifi/v1912-android-service-notifier-symbol-owner-handoff-live-20260603-220803/manifest.json")
DEFAULT_V1913 = Path("tmp/wifi/v1913-android-pm-service-qmi-msgid-uprobe-handoff-live-20260603-221820/manifest.json")
DEFAULT_V1888 = Path("tmp/wifi/v1888-pm-msgid-capture-diff-classifier-v1913/manifest.json")
DEFAULT_V1894 = Path("tmp/wifi/v1894-android-pending-client-msg22-parser-v1913/manifest.json")

DMESG_TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
TRACE_ARMED_RE = re.compile(r"A90_V1913_TRACE_ARMED uptime=(?P<uptime>\d+(?:\.\d+)?)")


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


def parse_trace_armed_uptime(samples_text: str) -> float | None:
    match = TRACE_ARMED_RE.search(samples_text or "")
    return float(match.group("uptime")) if match else None


def counts_zero(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and all(part == "0" for part in parts)


def base_manifest_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    return {
        "manifest": rel(repo_path(path)),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "label": manifest.get("label", ""),
        "reason": manifest.get("reason", ""),
    }


def native_servloc_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    gate = manifest.get("gate") or {}
    return {
        **base_manifest_summary(path),
        "label": gate.get("servloc_live_label", manifest.get("label", "")),
        "servloc_result": gate.get("servloc_domain_result", ""),
        "servloc_name": gate.get("servloc_domain0_name", ""),
        "servloc_instance": gate.get("servloc_domain0_instance_id", ""),
        "service180_counts": gate.get("raw_service180_text_counts", ""),
        "service74_counts": gate.get("raw_service74_text_counts", ""),
        "wlan_pd_counts": gate.get("raw_wlan_pd_text_counts", ""),
        "servnotif_early_state": gate.get("servnotif_early_state", ""),
        "servnotif_late_state": gate.get("servnotif_late_listener_state", ""),
        "wlfw_service69_seen": gate.get("wlfw_service69_seen", ""),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp", ""),
        "wlan0_present": gate.get("wlan0_present", ""),
        "rollback_ok": boolish((manifest.get("rollback") or {}).get("ok")),
    }


def android_early_servloc_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    early = next((item for item in analysis.get("query_success_examples", []) if item.get("name") == "query-early.txt"), {})
    return {
        **base_manifest_summary(path),
        "query_instances": analysis.get("query_instances") or [],
        "query_domain74_seen": boolish(analysis.get("query_domain74_seen")),
        "query_domain180_seen": boolish(analysis.get("query_domain180_seen")),
        "early_response_s": float(early.get("response_ms") or 0) / 1000.0 if early else 0.0,
        "service180_time_s": dmesg_time(analysis.get("first_service180_line", "")),
        "service74_time_s": dmesg_time(analysis.get("first_service74_line", "")),
        "wlan_pd_time_s": dmesg_time(analysis.get("first_wlan_pd_line", "")),
        "wlan0_time_s": dmesg.get("wlan0_time_s"),
        "pcie_mhi_before_wlan0": intish(dmesg.get("pcie_mhi_before_wlan0")),
        "esoc_failed_before_wlan0": intish(dmesg.get("esoc_boot_failed_before_wlan0")),
        "degraded_257s_like": boolish(dmesg.get("degraded_257s_like")),
    }


def android_owner_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    owners = analysis.get("service_notif_register_notifier_owners") or []
    return {
        **base_manifest_summary(path),
        "base": analysis.get("base", ""),
        "service74_count": intish(analysis.get("service74_count")),
        "service180_count": intish(analysis.get("service180_count")),
        "wlan_pd_indication_count": intish(analysis.get("wlan_pd_indication_count")),
        "wlanmdsp_count": intish(analysis.get("wlanmdsp_count")),
        "wlfw_service_request_count": intish(analysis.get("wlfw_service_request_count")),
        "wlan0_time_s": dmesg.get("wlan0_time_s"),
        "pcie_mhi_before_wlan0": intish(dmesg.get("pcie_mhi_before_wlan0")),
        "esoc_failed_before_wlan0": intish(dmesg.get("esoc_boot_failed_before_wlan0")),
        "degraded_257s_like": boolish(dmesg.get("degraded_257s_like")),
        "owners": owners,
        "owner_builtin_only": bool(owners) and set(owners) == {"builtin"},
        "proc_modules_line_count": intish(analysis.get("proc_modules_line_count")),
        "sys_modules": analysis.get("sys_modules") or [],
    }


def android_pm_uprobe_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    base = Path(str(analysis.get("base") or ""))
    samples_text = read_text(base / "samples.log") if base else ""
    setup_excerpt = analysis.get("setup_excerpt") or []
    trace_armed_uptime = parse_trace_armed_uptime(samples_text)
    service74_time = dmesg_time(analysis.get("first_service74_line", ""))
    return {
        **base_manifest_summary(path),
        "base": str(base),
        "trace_armed_uptime_s": trace_armed_uptime,
        "trace_armed_before_service74": trace_armed_uptime is not None and service74_time is not None and trace_armed_uptime < service74_time,
        "service74_time_s": service74_time,
        "wlan_pd_time_s": dmesg_time(analysis.get("first_wlan_pd_line", "")),
        "wlan0_time_s": dmesg.get("wlan0_time_s"),
        "pcie_mhi_before_wlan0": intish(dmesg.get("pcie_mhi_before_wlan0")),
        "esoc_failed_before_wlan0": intish(dmesg.get("esoc_boot_failed_before_wlan0")),
        "degraded_257s_like": boolish(dmesg.get("degraded_257s_like")),
        "dispatch_count": intish(analysis.get("dispatch_count")),
        "msg20_entry_count": intish(analysis.get("msg20_entry_count")),
        "msg21_entry_count": intish(analysis.get("msg21_entry_count")),
        "msg22_entry_count": intish(analysis.get("msg22_entry_count")),
        "dispatch_msgid_0x20": intish(analysis.get("dispatch_msgid_0x20")),
        "dispatch_msgid_0x21": intish(analysis.get("dispatch_msgid_0x21")),
        "dispatch_msgid_0x22": intish(analysis.get("dispatch_msgid_0x22")),
        "trace_line_count": intish(analysis.get("trace_line_count")),
        "trace_msgids": analysis.get("trace_msgids") or [],
        "setup_register_ok_count": sum(1 for line in setup_excerpt if ".register=ok" in str(line)),
        "setup_enable_ok_count": sum(1 for line in setup_excerpt if ".enable=ok" in str(line)),
        "service74_count": intish(analysis.get("service74_count")),
        "wlan_pd_indication_count": intish(analysis.get("wlan_pd_indication_count")),
        "wlanmdsp_count": intish(analysis.get("wlanmdsp_count")),
        "wlfw_service_request_count": intish(analysis.get("wlfw_service_request_count")),
    }


def msgid_diff_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    android = manifest.get("android_capture") or {}
    native = manifest.get("native_post_open") or {}
    return {
        **base_manifest_summary(path),
        "android_pm_msg20_hits": intish(android.get("pm_msg20_hits")),
        "android_pm_msg21_hits": intish(android.get("pm_msg21_hits")),
        "android_pm_msg22_hits": intish(android.get("pm_msg22_hits")),
        "android_wlan0_time_s": android.get("wlan0_time_s"),
        "android_wlanmdsp_count": intish(android.get("wlanmdsp_count")),
        "android_wlan_pd_indication_count": intish(android.get("wlan_pd_indication_count")),
        "native_open_context_path": native.get("open_context_path", ""),
        "native_open_context_fd": native.get("open_context_fd", ""),
        "native_pm_client_register_rc": native.get("pm_client_register_rc", ""),
        "native_pm_client_connect_rc": native.get("pm_client_connect_rc", ""),
        "native_post_ack_open_call_hits": intish(native.get("post_ack_open_call_hits")),
        "native_post_ack_msg22_ind_hits": intish(native.get("post_ack_msg22_ind_hits")),
        "native_wlfw_service69_seen": native.get("wlfw_service69_seen", ""),
        "native_requested_wlanmdsp": native.get("requested_wlanmdsp", ""),
        "native_wlan0_present": native.get("wlan0_present", ""),
        "native_late_servnotif_state": native.get("late_servnotif_state", ""),
    }


def pending_client_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    android = manifest.get("android") or {}
    return {
        **base_manifest_summary(path),
        "pm_qmi_client_count": intish(android.get("pm_qmi_client_count")),
        "pm_msg22_count": intish(android.get("pm_msg22_count")),
        "pm_restart_ind_count": intish(android.get("pm_restart_ind_count")),
        "pending_client_msg22_observed": boolish(android.get("pending_client_msg22_observed")),
        "android_wlan0_time_s": android.get("wlan0_time_s"),
        "android_wlanmdsp_count": intish(android.get("wlanmdsp_count")),
        "android_wlan_pd_indication_count": intish(android.get("wlan_pd_indication_count")),
    }


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    native = manifest["native_servloc"]
    early = manifest["android_early_servloc"]
    caller = manifest["caller_boundary"]
    owner = manifest["android_owner"]
    pm_uprobe = manifest["android_pm_uprobe"]
    msgid = manifest["msgid_diff"]
    pending = manifest["pending_client"]

    native_gap = (
        native["pass"]
        and native["servloc_result"] == "domain-list-response-success"
        and native["servloc_instance"] == "180"
        and counts_zero(native["service74_counts"])
        and counts_zero(native["wlan_pd_counts"])
        and native["servnotif_late_state"] == "uninit"
        and native["wlfw_service69_seen"] == "0"
        and native["requested_wlanmdsp"] == "0"
        and native["wlan0_present"] == "0"
    )
    native_post_open_gap = (
        msgid["pass"]
        and msgid["native_open_context_path"] == "/dev/subsys_modem"
        and msgid["native_pm_client_register_rc"] == "0"
        and msgid["native_pm_client_connect_rc"] == "0"
        and msgid["native_post_ack_open_call_hits"] > 0
        and msgid["native_post_ack_msg22_ind_hits"] == 0
        and msgid["native_wlfw_service69_seen"] == "0"
        and msgid["native_requested_wlanmdsp"] == "0"
        and msgid["native_wlan0_present"] == "0"
        and msgid["native_late_servnotif_state"] == "uninit"
    )
    android_normal = (
        owner["pass"]
        and pm_uprobe["pass"]
        and owner["service74_count"] > 0
        and owner["wlan_pd_indication_count"] > 0
        and owner["wlanmdsp_count"] > 0
        and owner["wlan0_time_s"] is not None
        and owner["pcie_mhi_before_wlan0"] == 0
        and owner["esoc_failed_before_wlan0"] == 0
        and not owner["degraded_257s_like"]
        and pm_uprobe["service74_count"] > 0
        and pm_uprobe["wlan_pd_indication_count"] > 0
        and pm_uprobe["wlanmdsp_count"] > 0
        and pm_uprobe["wlan0_time_s"] is not None
        and pm_uprobe["pcie_mhi_before_wlan0"] == 0
        and pm_uprobe["esoc_failed_before_wlan0"] == 0
        and not pm_uprobe["degraded_257s_like"]
    )
    locator_excludes_service74 = (
        early["pass"]
        and early["query_domain180_seen"]
        and not early["query_domain74_seen"]
        and early["query_instances"] == [180]
        and early["service74_time_s"] is not None
        and early["wlan_pd_time_s"] is not None
        and early["service74_time_s"] < early["wlan_pd_time_s"]
        and caller["pass"]
        and caller["label"] == "service74-pre-wlanpd-caller-boundary"
    )
    pm_service_excluded = (
        pm_uprobe["trace_armed_before_service74"]
        and pm_uprobe["setup_register_ok_count"] >= 7
        and pm_uprobe["setup_enable_ok_count"] >= 7
        and pm_uprobe["dispatch_count"] == 0
        and pm_uprobe["msg20_entry_count"] == 0
        and pm_uprobe["msg21_entry_count"] == 0
        and pm_uprobe["msg22_entry_count"] == 0
        and pm_uprobe["dispatch_msgid_0x20"] == 0
        and pm_uprobe["dispatch_msgid_0x21"] == 0
        and pm_uprobe["dispatch_msgid_0x22"] == 0
        and msgid["android_pm_msg20_hits"] == 0
        and msgid["android_pm_msg21_hits"] == 0
        and msgid["android_pm_msg22_hits"] == 0
        and pending["pm_msg22_count"] == 0
        and pending["pm_restart_ind_count"] == 0
        and not pending["pending_client_msg22_observed"]
    )
    builtin_edge = (
        owner["owner_builtin_only"]
        and "icnss" in owner["sys_modules"]
        and "service_locator" in owner["sys_modules"]
        and "wlan" in owner["sys_modules"]
    )
    manifest["gates"] = {
        "native_servloc_180_only_gap": native_gap,
        "native_post_subsys_modem_open_gap": native_post_open_gap,
        "android_normal_internal_modem_stateup": android_normal,
        "locator_query_excludes_instance74": locator_excludes_service74,
        "pm_service_msgid_edge_excluded": pm_service_excluded,
        "service_notifier_builtin_edge": builtin_edge,
    }
    if all(manifest["gates"].values()):
        return (
            "v1914-internal-service74-built-in-publication-edge-host-pass",
            True,
            "normal Android reaches internal-modem service74/wlan_pd/wlanmdsp/wlan0 without PCIe/MHI, while native post-/dev/subsys_modem open remains service74 absent; the wlan/fw locator is 180-only and pm-service msg20/21/22 dispatch is not the observed trigger",
            "internal-modem-service74-built-in-publication-edge",
        )
    return (
        "v1914-internal-service74-edge-evidence-incomplete",
        False,
        "one or more required retained-evidence gates are missing or contaminated",
        "internal-modem-service74-edge-evidence-incomplete",
    )


def render_report(manifest: dict[str, Any]) -> str:
    native = manifest["native_servloc"]
    early = manifest["android_early_servloc"]
    caller = manifest["caller_boundary"]
    owner = manifest["android_owner"]
    pm_uprobe = manifest["android_pm_uprobe"]
    msgid = manifest["msgid_diff"]
    pending = manifest["pending_client"]
    gates = manifest["gates"]
    return "\n".join([
        "# Native Init V1914 Internal Modem Service74 Edge Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only retained-evidence classifier for the internal-modem guest-PD-load trigger boundary",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Gate Results",
        "",
        markdown_table(
            ["gate", "pass", "meaning"],
            [
                ["native servloc 180-only gap", gates["native_servloc_180_only_gap"], "native sees `msm/modem/wlan_pd` instance 180 but no service74/wlan_pd/WLFW69/wlan0"],
                ["native post-open gap", gates["native_post_subsys_modem_open_gap"], "`/dev/subsys_modem` open and PM-client success do not start wlan_pd"],
                ["Android normal state-up", gates["android_normal_internal_modem_stateup"], "normal Android reaches service74, wlan_pd, wlanmdsp, and wlan0 with no PCIe/MHI contamination"],
                ["locator excludes service74", gates["locator_query_excludes_instance74"], "early Android `wlan/fw` service-locator response is instance 180 only after service74 and before wlan_pd"],
                ["pm-service excluded", gates["pm_service_msgid_edge_excluded"], "pm-service msg20/21/22 and pending-client/msg22 observability are zero through normal state-up"],
                ["built-in edge", gates["service_notifier_builtin_edge"], "`service_notif_register_notifier` is built into the kernel with ICNSS/service_locator/wlan present"],
            ],
        ),
        "",
        "## Native Evidence",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["V1908 manifest", native["manifest"]],
                ["decision/pass/label", f"{native['decision']}/{native['pass']}/{native['label']}"],
                ["servloc result/name/instance", f"{native['servloc_result']}/{native['servloc_name']}/{native['servloc_instance']}"],
                ["service180/service74/wlan_pd counts", f"{native['service180_counts']}/{native['service74_counts']}/{native['wlan_pd_counts']}"],
                ["servnotif states", f"{native['servnotif_early_state']}->{native['servnotif_late_state']}"],
                ["WLFW69/wlanmdsp/wlan0", f"{native['wlfw_service69_seen']}/{native['requested_wlanmdsp']}/{native['wlan0_present']}"],
                ["V1888 native open path/fd", f"{msgid['native_open_context_path']}/{msgid['native_open_context_fd']}"],
                ["PM register/connect/open hits/msg22 hits", f"{msgid['native_pm_client_register_rc']}/{msgid['native_pm_client_connect_rc']}/{msgid['native_post_ack_open_call_hits']}/{msgid['native_post_ack_msg22_ind_hits']}"],
            ],
        ),
        "",
        "## Android Evidence",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["V1910 locator decision", f"{early['decision']}/{early['pass']}/{early['label']}"],
                ["V1910 query instances/domain74/domain180", f"{json.dumps(early['query_instances'])}/{early['query_domain74_seen']}/{early['query_domain180_seen']}"],
                ["V1910 time service74/query/wlan_pd/wlan0", f"{early['service74_time_s']}/{early['early_response_s']}/{early['wlan_pd_time_s']}/{early['wlan0_time_s']}"],
                ["V1912 owner decision", f"{owner['decision']}/{owner['pass']}/{owner['label']}"],
                ["V1912 owners/modules", f"{json.dumps(owner['owners'])}/{json.dumps(owner['sys_modules'])}"],
                ["V1912 service74/wlan_pd/wlanmdsp/wlan0", f"{owner['service74_count']}/{owner['wlan_pd_indication_count']}/{owner['wlanmdsp_count']}/{owner['wlan0_time_s']}"],
                ["V1913 service74/wlan_pd/wlanmdsp/wlan0", f"{pm_uprobe['service74_count']}/{pm_uprobe['wlan_pd_indication_count']}/{pm_uprobe['wlanmdsp_count']}/{pm_uprobe['wlan0_time_s']}"],
                ["V1913 contamination pcie-mhi/esoc/degraded257", f"{pm_uprobe['pcie_mhi_before_wlan0']}/{pm_uprobe['esoc_failed_before_wlan0']}/{pm_uprobe['degraded_257s_like']}"],
            ],
        ),
        "",
        "## pm-service Exclusion",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["trace armed/service74/wlan_pd", f"{pm_uprobe['trace_armed_uptime_s']}/{pm_uprobe['service74_time_s']}/{pm_uprobe['wlan_pd_time_s']}"],
                ["register-ok/enable-ok", f"{pm_uprobe['setup_register_ok_count']}/{pm_uprobe['setup_enable_ok_count']}"],
                ["dispatch/msg20/msg21/msg22", f"{pm_uprobe['dispatch_count']}/{pm_uprobe['msg20_entry_count']}/{pm_uprobe['msg21_entry_count']}/{pm_uprobe['msg22_entry_count']}"],
                ["dispatch msgid 0x20/0x21/0x22", f"{pm_uprobe['dispatch_msgid_0x20']}/{pm_uprobe['dispatch_msgid_0x21']}/{pm_uprobe['dispatch_msgid_0x22']}"],
                ["V1888 Android msg20/msg21/msg22", f"{msgid['android_pm_msg20_hits']}/{msgid['android_pm_msg21_hits']}/{msgid['android_pm_msg22_hits']}"],
                ["V1894 qmi-client/msg22/restart-ind", f"{pending['pm_qmi_client_count']}/{pending['pm_msg22_count']}/{pending['pm_restart_ind_count']}"],
            ],
        ),
        "",
        "## Source Boundary",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["V1911 decision", f"{caller['decision']}/{caller['pass']}/{caller['label']}"],
                ["source non-header callers", json.dumps((caller.get("source") or {}).get("non_header_callers") or [])],
                ["exported symbol", (caller.get("source") or {}).get("exported_symbol")],
                ["trace capability kprobe/function", f"{(caller.get('trace_capability') or {}).get('kprobes')}/{(caller.get('trace_capability') or {}).get('function_tracer')}"],
            ],
        ),
        "",
        "## Selected Diff",
        "",
        "- Label: `internal-modem-service74-built-in-publication-edge`.",
        "- `/dev/subsys_modem` is confirmed as a PM-client/subsys-get step on an already-online modem; it does not cause wlan_pd state-up by itself.",
        "- The normal Android guest-PD-load trigger is now bounded before `wlan_pd` and outside pm-service msg20/21/22 dispatch observability.",
        "- The remaining useful target is the built-in internal-modem service-notifier/service-locator path that creates the instance74 lookup/publication before WLFW service69 appears.",
        "- Do not use the degraded 257s PCIe/MHI boot, SDX50M, eSoC, pcie1, or GDSC evidence for this path.",
        "",
        "## Safety Scope",
        "",
        "V1914 is host-only. It reads retained manifests and evidence text only. It executes no live device command, reboot, flash, tracefs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.",
        "",
        "## Next",
        "",
        "- Next live gate: read-only/bounded internal-modem kernel/servreg observer for the service74 lookup/publication edge, armed before ~7s and stopped before Wi-Fi HAL/scan/connect.",
        "- If only static work is allowed, use a bounded stock-kernel image/kallsyms string/xref pass focused on `service_notif_register_notifier`, `SERVREG_NOTIF_SERVICE_ID`, instance `74`, ICNSS, and service-locator built-in code.",
        "- Do not attempt Wi-Fi credentials/connect/ping until native proves WLFW service69 and `wlan0`.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--v1908-manifest", type=Path, default=DEFAULT_V1908)
    parser.add_argument("--v1910-manifest", type=Path, default=DEFAULT_V1910)
    parser.add_argument("--v1911-manifest", type=Path, default=DEFAULT_V1911)
    parser.add_argument("--v1912-manifest", type=Path, default=DEFAULT_V1912)
    parser.add_argument("--v1913-manifest", type=Path, default=DEFAULT_V1913)
    parser.add_argument("--v1888-manifest", type=Path, default=DEFAULT_V1888)
    parser.add_argument("--v1894-manifest", type=Path, default=DEFAULT_V1894)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest: dict[str, Any] = {
        "cycle": CYCLE,
        "out_dir": rel(repo_path(args.out_dir)),
        "native_servloc": native_servloc_summary(args.v1908_manifest),
        "android_early_servloc": android_early_servloc_summary(args.v1910_manifest),
        "caller_boundary": read_json(args.v1911_manifest),
        "android_owner": android_owner_summary(args.v1912_manifest),
        "android_pm_uprobe": android_pm_uprobe_summary(args.v1913_manifest),
        "msgid_diff": msgid_diff_summary(args.v1888_manifest),
        "pending_client": pending_client_summary(args.v1894_manifest),
        "safety": {
            "device_commands_executed": False,
            "tracefs_write_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "restart_pd_request_executed": False,
            "subsys_esoc0_open_executed": False,
            "pmic_gpio_gdsc_regulator_write_executed": False,
            "pcie_rescan_executed": False,
            "platform_bind_unbind_executed": False,
        },
    }
    decision, passed, reason, label = classify(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "label": label, "report": rel(repo_path(args.report))})
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    write_private_text(repo_path(args.report), report)
    print(json.dumps({"decision": decision, "pass": passed, "label": label, "out_dir": manifest["out_dir"], "report": manifest["report"]}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
