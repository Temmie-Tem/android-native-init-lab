#!/usr/bin/env python3
"""V1135 host-only classifier for the post-V1134 lower WLFW publication gap."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1135-lower-publication-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1135-lower-publication-gap-classifier.txt")
DEFAULT_V1134 = Path("tmp/wifi/v1134-outer-holder-post-policy-cnss-live-run/manifest.json")
DEFAULT_V968 = Path("tmp/wifi/v968-android-dmesg-esoc-gpio-timing/manifest.json")
DEFAULT_V1093 = Path("tmp/wifi/v1093-pm-post-provider-surface-live/manifest.json")
DEFAULT_V1108 = Path("tmp/wifi/v1108-pm-ordering-no-pre-cnss-per-proxy-live/manifest.json")
DEFAULT_V1109 = Path("tmp/wifi/v1109-pm-connect-subsystem-get-classifier/manifest.json")
DEFAULT_V884 = Path("tmp/wifi/v884-esoc-req-registered-subsys-hold-live/manifest.json")
DEFAULT_V891 = Path("tmp/wifi/v891-esoc-conditional-response-live-v142/manifest.json")
DEFAULT_V895 = Path("tmp/wifi/v895-mdm2ap-irq-snapshot-live/manifest.json")
DEFAULT_V904 = Path("tmp/wifi/v904-mdm-helper-runtime-input-parity/manifest.json")
DEFAULT_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path, limit: int = 16_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    cur: Any = data
    for item in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(item)
    return default if cur is None else cur


def flat_get(data: dict[str, Any], key: str, default: Any = None) -> Any:
    return data.get(key, default) if isinstance(data, dict) else default


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass", "online"}


def intish(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def listish(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def summarize_v1134(data: dict[str, Any]) -> dict[str, Any]:
    fw = nested_get(data, ("analysis", "global_firmware"), {})
    markers = nested_get(data, ("analysis", "global_firmware", "markers", "counts"), {})
    services = fw.get("qrtr_services_after_observer") if isinstance(fw, dict) else {}
    tracefs = nested_get(data, ("analysis", "tracefs_uprobe"), {})
    counts = tracefs.get("counts") if isinstance(tracefs, dict) else {}
    contract = tracefs.get("pm_contract") if isinstance(tracefs, dict) else {}
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "firmware_mounts_executed": boolish(data.get("firmware_mounts_executed")),
        "global_modem_holder_opened": boolish(data.get("global_modem_holder_opened")),
        "helper_private_holder_requested": boolish(data.get("helper_private_holder_requested")),
        "cnss_daemon_start_executed": boolish(data.get("cnss_daemon_start_executed")),
        "wifi_hal_start_executed": boolish(data.get("wifi_hal_start_executed")),
        "wifi_bringup_executed": boolish(data.get("wifi_bringup_executed")),
        "external_ping_executed": boolish(data.get("external_ping_executed")),
        "mss_after_holder": fw.get("mss_after_holder", "") if isinstance(fw, dict) else "",
        "mss_after_observer": fw.get("mss_after_observer", "") if isinstance(fw, dict) else "",
        "mdm3_after_holder": fw.get("mdm3_after_holder", "") if isinstance(fw, dict) else "",
        "mdm3_after_observer": fw.get("mdm3_after_observer", "") if isinstance(fw, dict) else "",
        "qrtr_rx": intish(markers.get("qrtr_rx")) if isinstance(markers, dict) else 0,
        "qrtr_tx": intish(markers.get("qrtr_tx")) if isinstance(markers, dict) else 0,
        "sysmon_qmi": intish(markers.get("sysmon_qmi")) if isinstance(markers, dict) else 0,
        "service_notifier": intish(markers.get("service_notifier")) if isinstance(markers, dict) else 0,
        "wlan_pd": intish(markers.get("wlan_pd")) if isinstance(markers, dict) else 0,
        "wlfw": intish(markers.get("wlfw")) if isinstance(markers, dict) else 0,
        "bdf": intish(markers.get("bdf")) if isinstance(markers, dict) else 0,
        "mhi": intish(markers.get("mhi")) if isinstance(markers, dict) else 0,
        "qca6390": intish(markers.get("qca6390")) if isinstance(markers, dict) else 0,
        "wlan0": intish(markers.get("wlan0")) if isinstance(markers, dict) else 0,
        "kernel_warning": intish(markers.get("kernel_warning")) if isinstance(markers, dict) else 0,
        "service69": intish(services.get("69")) if isinstance(services, dict) else 0,
        "service74": intish(services.get("74")) if isinstance(services, dict) else 0,
        "service180": intish(services.get("180")) if isinstance(services, dict) else 0,
        "pm_client_register_ret_hits": intish(counts.get("pm_client_register_ret")) if isinstance(counts, dict) else 0,
        "pm_client_connect_ret_hits": intish(counts.get("pm_client_connect_ret")) if isinstance(counts, dict) else 0,
        "pm_server_register_ret_hits": intish(counts.get("pm_server_register_ret")) if isinstance(counts, dict) else 0,
        "pm_server_connect_ret_hits": intish(counts.get("pm_server_connect_ret")) if isinstance(counts, dict) else 0,
        "per_mgr_subsys_modem_seen": boolish(contract.get("per_mgr_subsys_modem_seen")) if isinstance(contract, dict) else False,
        "pm_proxy_helper_subsys_modem_seen": boolish(contract.get("pm_proxy_helper_subsys_modem_seen")) if isinstance(contract, dict) else False,
    }


def summarize_v968(data: dict[str, Any]) -> dict[str, Any]:
    events = nested_get(data, ("classification", "events"), {})
    answers = nested_get(data, ("classification", "answers"), {})
    subsys = nested_get(data, ("classification", "subsys"), {})
    return {
        "decision": data.get("decision", ""),
        "wlfw_start_present": boolish(nested_get(events, ("wlfw_start", "present"), False)),
        "wlfw_service_request_present": boolish(nested_get(events, ("wlfw_service_request", "present"), False)),
        "esoc0_subsystem_get_present": boolish(nested_get(events, ("esoc0_subsystem_get", "present"), False)),
        "wlan0_present": boolish(nested_get(events, ("wlan0_event", "present"), False)),
        "wlfw_start_time": nested_get(events, ("wlfw_start", "time"), None),
        "esoc0_subsystem_get_time": nested_get(events, ("esoc0_subsystem_get", "time"), None),
        "wlan0_time": nested_get(events, ("wlan0_event", "time"), None),
        "wlfw_start_to_esoc0_get_ms": answers.get("wlfw_start_to_esoc0_get_ms") if isinstance(answers, dict) else None,
        "wlfw_start_to_wlan_pd_ms": answers.get("wlfw_start_to_wlan_pd_ms") if isinstance(answers, dict) else None,
        "wlfw_start_to_fw_ready_ms": answers.get("wlfw_start_to_fw_ready_ms") if isinstance(answers, dict) else None,
        "fw_ready_to_wlan0_ms": answers.get("fw_ready_to_wlan0_ms") if isinstance(answers, dict) else None,
        "subsys9_name": subsys.get("subsys9_name", "") if isinstance(subsys, dict) else "",
        "subsys9_firmware_name": subsys.get("subsys9_firmware_name", "") if isinstance(subsys, dict) else "",
        "esoc0_driver": subsys.get("esoc0_driver", "") if isinstance(subsys, dict) else "",
        "esoc0_compatible": subsys.get("esoc0_compatible", "") if isinstance(subsys, dict) else "",
    }


def summarize_v1093(data: dict[str, Any]) -> dict[str, Any]:
    contract = nested_get(data, ("analysis", "helper", "contract"), {})
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "provider_seen": boolish(flat_get(contract, "vndservice_provider_seen")),
        "mdm3_state": flat_get(contract, "post_provider_surface.after_provider.mdm3_state", ""),
        "wlan0_exists": boolish(flat_get(contract, "post_provider_surface.after_provider.wlan0_exists")),
        "service74_count": intish(flat_get(contract, "post_provider_surface.after_provider.klog_count_service74")),
        "sysmon_count": intish(flat_get(contract, "post_provider_surface.after_provider.klog_count_sysmon_qmi")),
        "subsys_esoc0_open_attempted": boolish(flat_get(contract, "post_provider_surface.after_provider.subsys_esoc0_open_attempted")),
    }


def summarize_v1108(data: dict[str, Any]) -> dict[str, Any]:
    tracefs = nested_get(data, ("analysis", "tracefs_uprobe"), {})
    counts = tracefs.get("counts") if isinstance(tracefs, dict) else {}
    contract = tracefs.get("pm_contract") if isinstance(tracefs, dict) else {}
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "pm_client_register_ret_hits": intish(counts.get("pm_client_register_ret")) if isinstance(counts, dict) else 0,
        "pm_client_connect_ret_hits": intish(counts.get("pm_client_connect_ret")) if isinstance(counts, dict) else 0,
        "mdm3_state": flat_get(contract, "post_provider_surface.after_cnss_daemon.mdm3_state", ""),
        "wlan0_exists": boolish(flat_get(contract, "post_provider_surface.after_cnss_daemon.wlan0_exists")),
        "subsys_esoc0_open_attempted": boolish(flat_get(contract, "post_provider_surface.after_cnss_daemon.subsys_esoc0_open_attempted")),
    }


def summarize_v1109(data: dict[str, Any]) -> dict[str, Any]:
    reason = str(data.get("reason", ""))
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "owner_wchan_mentions_subsystem_get": "__subsystem_get" in reason,
        "owner_wchan_mentions_request_firmware": "_request_firmware" in reason,
        "mdm3_state_offlining": "mdm3_state=OFFLINING" in reason,
    }


def summarize_esoc_history(v884: dict[str, Any], v891: dict[str, Any], v895: dict[str, Any], v904: dict[str, Any]) -> dict[str, Any]:
    v884_contract = nested_get(v884, ("analysis", "helper", "keys"), {})
    v891_conditional = nested_get(v891, ("analysis", "helper", "conditional"), {})
    v895_irq = v895.get("v895_irq_snapshot") if isinstance(v895.get("v895_irq_snapshot"), dict) else {}
    return {
        "v884_decision": v884.get("decision", ""),
        "v884_req_eng_registered": boolish(v884_contract.get("reg_req_eng_rc") == "0" or v884_contract.get("req_fd_held")),
        "v884_subsys_open_attempted": boolish(v884_contract.get("subsys_esoc0_open_attempted")),
        "v884_timed_out": boolish(v884_contract.get("timed_out")),
        "v891_decision": v891.get("decision", ""),
        "v891_req_img_observed": boolish(v891_conditional.get("request_observed")),
        "v891_img_xfer_sent": boolish(v891_conditional.get("img_xfer_sent")),
        "v891_status_ready": boolish(v891_conditional.get("status_ready")),
        "v891_boot_done_sent": boolish(v891_conditional.get("boot_done_sent")),
        "v895_decision": v895.get("decision", ""),
        "v895_irq_fired": boolish(v895_irq.get("irq_fired")),
        "v895_delta_total": intish(v895_irq.get("delta_total")),
        "v904_decision": v904.get("decision", ""),
        "v904_direct_mdm_helper_missing_runtime": v904.get("decision") == "v904-mdm-helper-runtime-input-parity-classified",
    }


def summarize_research(text: str) -> dict[str, Any]:
    return {
        "present": bool(text),
        "android_chain_documented": "완전한 Android mdm3 bring-up 체인" in text,
        "mdm_helper_state_machine": "mdm-helper (state machine 모드)" in text,
        "pm_proxy_helper_subsys_esoc0": "pm_proxy_helper" in text and "/dev/subsys_esoc0" in text,
        "req_eng_required": "REG_REQ_ENG" in text and "req_eng_wait" in text,
        "mdm2ap_gpio142": "GPIO 142" in text,
        "wlfw_service69_after_mdm3_online": "WLFW service 69" in text and "mdm3 ONLINE" in text,
    }


def classify(analysis: dict[str, Any]) -> dict[str, Any]:
    v1134 = analysis["v1134"]
    v968 = analysis["v968_android"]
    v1093 = analysis["v1093"]
    v1108 = analysis["v1108"]
    v1109 = analysis["v1109"]
    esoc = analysis["esoc_history"]
    research = analysis["research"]
    flags = {
        "v1134_upper_pm_success": (
            v1134["pass"]
            and v1134["firmware_mounts_executed"]
            and v1134["global_modem_holder_opened"]
            and v1134["mss_after_observer"] == "ONLINE"
            and v1134["pm_client_register_ret_hits"] > 0
            and v1134["pm_client_connect_ret_hits"] > 0
            and v1134["pm_server_register_ret_hits"] > 0
            and v1134["pm_server_connect_ret_hits"] > 0
        ),
        "v1134_lower_wlfw_absent": (
            v1134["mdm3_after_observer"] == "OFFLINING"
            and v1134["service69"] == 0
            and v1134["service74"] == 0
            and v1134["service180"] == 0
            and v1134["wlfw"] == 0
            and v1134["wlan0"] == 0
        ),
        "android_has_complete_publication_path": (
            v968["wlfw_start_present"]
            and v968["wlfw_service_request_present"]
            and v968["esoc0_subsystem_get_present"]
            and v968["wlan0_present"]
        ),
        "provider_only_was_insufficient": (
            v1093["pass"]
            and v1093["provider_seen"]
            and v1093["mdm3_state"] == "OFFLINING"
            and not v1093["wlan0_exists"]
        ),
        "pm_connect_without_esoc_was_insufficient": (
            v1108["pass"]
            and v1108["pm_client_register_ret_hits"] > 0
            and v1108["pm_client_connect_ret_hits"] > 0
            and v1108["mdm3_state"] == "OFFLINING"
            and not v1108["subsys_esoc0_open_attempted"]
        ),
        "pm_connect_reached_lower_subsystem_get_before": (
            v1109["pass"]
            and v1109["owner_wchan_mentions_subsystem_get"]
            and v1109["owner_wchan_mentions_request_firmware"]
            and v1109["mdm3_state_offlining"]
        ),
        "esoc_state_machine_partially_known": (
            esoc["v884_req_eng_registered"]
            and esoc["v884_subsys_open_attempted"]
            and esoc["v891_req_img_observed"]
            and esoc["v891_img_xfer_sent"]
            and not esoc["v891_status_ready"]
            and not esoc["v895_irq_fired"]
        ),
        "direct_mdm_helper_needs_runtime_contract": esoc["v904_direct_mdm_helper_missing_runtime"],
        "research_chain_supports_esoc_route": (
            research["present"]
            and research["android_chain_documented"]
            and research["req_eng_required"]
            and research["mdm2ap_gpio142"]
            and research["wlfw_service69_after_mdm3_online"]
        ),
        "guardrails_preserved": (
            not v1134["helper_private_holder_requested"]
            and not v1134["wifi_hal_start_executed"]
            and not v1134["wifi_bringup_executed"]
            and not v1134["external_ping_executed"]
        ),
    }
    missing = [name for name, ok in flags.items() if not ok]
    if not missing:
        return {
            "decision": "v1135-pm-success-lower-esoc-publication-gap-classified",
            "pass": True,
            "reason": (
                "V1134 proves the upper PM/CNSS path succeeds under the outer holder, "
                "but mdm3/service69/WLFW/wlan0 remain absent; Android and eSoC history "
                "point the next blocker at the eSoC/MDM2AP readiness state machine below PM"
            ),
            "next_step": (
                "plan V1136 as a host-only/live-preflight design for the smallest safe "
                "post-PM eSoC/MDM2AP observer or state-machine gate; do not retry Wi-Fi HAL, "
                "scan/connect, credentials, DHCP, or external ping until service69/WLFW appears"
            ),
            "flags": flags,
            "missing": [],
        }
    return {
        "decision": "v1135-lower-publication-gap-incomplete",
        "pass": False,
        "reason": "missing=" + ",".join(missing),
        "next_step": "refresh missing evidence before selecting another live gate",
        "flags": flags,
        "missing": missing,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    cls = analysis["classification"]
    rows = [
        ["V1134 upper PM/CNSS", str(cls["flags"]["v1134_upper_pm_success"]), analysis["v1134"]["decision"]],
        ["V1134 lower WLFW absent", str(cls["flags"]["v1134_lower_wlfw_absent"]), f"mdm3={analysis['v1134']['mdm3_after_observer']} service69={analysis['v1134']['service69']} wlan0={analysis['v1134']['wlan0']}"],
        ["Android publication path", str(cls["flags"]["android_has_complete_publication_path"]), f"wlfw={analysis['v968_android']['wlfw_start_present']} wlan0={analysis['v968_android']['wlan0_present']}"],
        ["Provider-only insufficient", str(cls["flags"]["provider_only_was_insufficient"]), analysis["v1093"]["decision"]],
        ["PM connect insufficient", str(cls["flags"]["pm_connect_without_esoc_was_insufficient"]), analysis["v1108"]["decision"]],
        ["Lower subsystem_get seen", str(cls["flags"]["pm_connect_reached_lower_subsystem_get_before"]), analysis["v1109"]["decision"]],
        ["eSoC history known", str(cls["flags"]["esoc_state_machine_partially_known"]), analysis["esoc_history"]["v891_decision"]],
        ["mdm_helper runtime gap", str(cls["flags"]["direct_mdm_helper_needs_runtime_contract"]), analysis["esoc_history"]["v904_decision"]],
    ]
    state_rows = [
        ["V1134 mss_after_observer", analysis["v1134"]["mss_after_observer"]],
        ["V1134 mdm3_after_observer", analysis["v1134"]["mdm3_after_observer"]],
        ["V1134 PM ret hits", f"client_reg={analysis['v1134']['pm_client_register_ret_hits']} client_conn={analysis['v1134']['pm_client_connect_ret_hits']}"],
        ["V1134 QRTR services", f"69={analysis['v1134']['service69']} 74={analysis['v1134']['service74']} 180={analysis['v1134']['service180']}"],
        ["Android wlfw->esoc0_get ms", str(analysis["v968_android"]["wlfw_start_to_esoc0_get_ms"])],
        ["Android fw_ready->wlan0 ms", str(analysis["v968_android"]["fw_ready_to_wlan0_ms"])],
        ["V891 status_ready", str(analysis["esoc_history"]["v891_status_ready"])],
        ["V895 irq_fired", str(analysis["esoc_history"]["v895_irq_fired"])],
    ]
    return "\n".join([
        "# V1135 Lower Publication Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Classification Evidence",
        "",
        markdown_table(["evidence", "ok", "detail"], rows),
        "",
        "## State Evidence",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## Missing",
        "",
        json.dumps(cls["missing"], indent=2, sort_keys=True),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1134", type=Path, default=DEFAULT_V1134)
    parser.add_argument("--v968", type=Path, default=DEFAULT_V968)
    parser.add_argument("--v1093", type=Path, default=DEFAULT_V1093)
    parser.add_argument("--v1108", type=Path, default=DEFAULT_V1108)
    parser.add_argument("--v1109", type=Path, default=DEFAULT_V1109)
    parser.add_argument("--v884", type=Path, default=DEFAULT_V884)
    parser.add_argument("--v891", type=Path, default=DEFAULT_V891)
    parser.add_argument("--v895", type=Path, default=DEFAULT_V895)
    parser.add_argument("--v904", type=Path, default=DEFAULT_V904)
    parser.add_argument("--research", type=Path, default=DEFAULT_RESEARCH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = {
        "v1134": summarize_v1134(load_json(args.v1134)),
        "v968_android": summarize_v968(load_json(args.v968)),
        "v1093": summarize_v1093(load_json(args.v1093)),
        "v1108": summarize_v1108(load_json(args.v1108)),
        "v1109": summarize_v1109(load_json(args.v1109)),
        "esoc_history": summarize_esoc_history(
            load_json(args.v884),
            load_json(args.v891),
            load_json(args.v895),
            load_json(args.v904),
        ),
        "research": summarize_research(read_text(args.research)),
    }
    classification = classify(analysis)
    analysis["classification"] = classification
    manifest = {
        "cycle": "v1135",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1134": str(repo_path(args.v1134)),
            "v968": str(repo_path(args.v968)),
            "v1093": str(repo_path(args.v1093)),
            "v1108": str(repo_path(args.v1108)),
            "v1109": str(repo_path(args.v1109)),
            "v884": str(repo_path(args.v884)),
            "v891": str(repo_path(args.v891)),
            "v895": str(repo_path(args.v895)),
            "v904": str(repo_path(args.v904)),
            "research": str(repo_path(args.research)),
        },
        "analysis": analysis,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
