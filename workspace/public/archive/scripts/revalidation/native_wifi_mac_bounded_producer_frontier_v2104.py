#!/usr/bin/env python3
"""V2104 host-only frontier: bound MAC and keep focus on the TFTP producer branch."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CYCLE = "V2104"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2104-mac-bounded-producer-frontier"
MANIFEST_PATH = OUT_DIR / "manifest.json"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2104_MAC_BOUNDED_PRODUCER_FRONTIER_2026-06-05.md"
)

V2053_SUMMARY = REPO_ROOT / "tmp" / "wifi" / "v2053-pre-wlanmdsp-trigger-event-diff" / "summary.json"
V2091_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v2091-macloader-property-service-handoff" / "manifest.json"
V2094_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v2094-mac-closed-post-server-check-timing" / "manifest.json"
V2103_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v2103-tftp-process-namespace-audit-handoff" / "manifest.json"
HELPER_SOURCE = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def intish(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if value is None:
        return 0
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    def cell(value: object) -> str:
        return str(value).replace("\n", " ").replace("|", "\\|")

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell(value) for value in row) + " |")
    return "\n".join(lines)


def first_event(events: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for event in events:
        if event.get("name") == name:
            return event
    return {}


def event_delta_ms(event: dict[str, Any], base: dict[str, Any]) -> int | str:
    if not event or not base:
        return ""
    try:
        return int(round((float(event["timestamp"]) - float(base["timestamp"])) * 1000.0))
    except (KeyError, TypeError, ValueError):
        return ""


def short_line(event: dict[str, Any], limit: int = 140) -> str:
    line = str(event.get("line", ""))
    return line if len(line) <= limit else line[: limit - 1] + "…"


def trace_ts(line: str) -> float | None:
    match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
    return float(match.group(1)) if match else None


def dmesg_assign_count(manifest: dict[str, Any]) -> int:
    handoff_manifest = Path(str(manifest.get("handoff_manifest", "")))
    if not handoff_manifest.is_absolute():
        handoff_manifest = REPO_ROOT / handoff_manifest
    dmesg_path = handoff_manifest.parent / "test-v1393-dmesg.stdout.txt"
    if not dmesg_path.exists():
        return 0
    return sum(
        1
        for line in dmesg_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if "icnss: Assigning MAC from Macloader" in line
    )


def source_identity_contract() -> dict[str, Any]:
    text = HELPER_SOURCE.read_text(encoding="utf-8", errors="replace")
    required = {
        "identity_function": "apply_macloader_identity_contract",
        "uid_wifi": '"macloader",\n                                             A90_AID_WIFI',
        "gid_wifi": "A90_AID_WIFI,\n                                             groups",
        "groups": "A90_AID_WIFI, A90_AID_INET, A90_AID_NET_RAW, A90_AID_NET_ADMIN",
        "caps": "CAP_NET_ADMIN, CAP_NET_RAW, CAP_SYS_MODULE",
        "dispatch": "child->identity == COMPOSITE_ID_MACLOADER",
    }
    hits = {name: token in text for name, token in required.items()}
    return {
        "source": rel(HELPER_SOURCE),
        "ok": all(hits.values()),
        "hits": hits,
    }


def collect_mac(v2091: dict[str, Any], v2094: dict[str, Any]) -> dict[str, Any]:
    source = nested(v2091, "details", "mac_source_bridge", default={})
    trace = nested(v2091, "details", "macloader_syscall_trace", default={})
    mac_addr = source.get("mac_addr") if isinstance(source, dict) else {}
    mac_info = source.get("mac_info") if isinstance(source, dict) else {}
    if not isinstance(mac_addr, dict):
        mac_addr = {}
    if not isinstance(mac_info, dict):
        mac_info = {}
    return {
        "aggregate": v2094.get("mac", {}),
        "source_identity": source_identity_contract(),
        "real_sysfs_mac_addr": boolish(source.get("real_sysfs_mac_addr")) if isinstance(source, dict) else False,
        "mac_addr": {
            "absolute": mac_addr.get("absolute", ""),
            "exists": intish(mac_addr.get("exists")),
            "writable": intish(mac_addr.get("writable")),
            "mode": mac_addr.get("mode", ""),
            "uid": intish(mac_addr.get("uid")),
            "gid": intish(mac_addr.get("gid")),
            "fs_type": mac_addr.get("fs_type_text", ""),
        },
        "mac_info": {
            "absolute": mac_info.get("absolute", ""),
            "exists": intish(mac_info.get("exists")),
            "readable": intish(mac_info.get("readable")),
            "writable": intish(mac_info.get("writable")),
            "bytes": intish(mac_info.get("bytes")),
            "mode": mac_info.get("mode", ""),
            "uid": intish(mac_info.get("uid")),
            "gid": intish(mac_info.get("gid")),
            "fs_type": mac_info.get("fs_type_text", ""),
        },
        "trace": {
            "runtime_traced": intish(trace.get("runtime_traced")),
            "runtime_target": trace.get("runtime_target", ""),
            "runtime_pgid": intish(trace.get("runtime_pgid")),
            "records_seen": intish(trace.get("records_seen")),
            "connect_count": intish(trace.get("connect_count")),
            "mac_info_open": boolish(trace.get("mac_info_open")),
            "mac_info_read": boolish(trace.get("mac_info_read")),
            "mac_addr_open": boolish(trace.get("mac_addr_open")),
            "mac_addr_write": boolish(trace.get("mac_addr_write")),
            "mac_addr_write_shape": boolish(trace.get("mac_addr_write_shape")),
            "raw_mac_payload": intish(trace.get("raw_mac_payload")),
        },
        "kernel_assign_count": dmesg_assign_count(v2091),
        "mac_assigned": boolish(nested(v2091, "classification", "mac_assigned", default=False)),
    }


def collect_android(v2053: dict[str, Any]) -> dict[str, Any]:
    android = v2053.get("android") if isinstance(v2053.get("android"), dict) else {}
    events = android.get("events") if isinstance(android.get("events"), list) else []
    dmesg_events = android.get("dmesg_events") if isinstance(android.get("dmesg_events"), list) else []
    tftp_start = first_event(events, "tftp_start")
    names = [
        "server_check_wrq",
        "ota_firewall_rrq",
        "wlfw_start",
        "per_mgr_add_client",
        "per_mgr_vote",
        "wlfw_service_request",
        "first_wlanmdsp_rrq",
    ]
    order = [
        {
            "name": name,
            "delta_from_tftp_start_ms": event_delta_ms(first_event(events, name), tftp_start),
            "line": short_line(first_event(events, name)),
        }
        for name in names
    ]
    up = first_event(dmesg_events, "wlan_pd_up")
    return {
        "label": v2053.get("label", ""),
        "decision": v2053.get("decision", ""),
        "order": order,
        "wlan_pd_up_ts": up.get("timestamp", ""),
        "wlan_pd_up_line": short_line(up),
    }


def collect_native(v2103: dict[str, Any]) -> dict[str, Any]:
    cls = v2103.get("classification") if isinstance(v2103.get("classification"), dict) else {}
    details = v2103.get("details") if isinstance(v2103.get("details"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    readwrite = nested(details, "readwrite_transition", "summary", default={})
    tftp_logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    tftp_summary = details.get("tftp_summary_fields") if isinstance(details.get("tftp_summary_fields"), dict) else {}
    tftp_branch = details.get("tftp_tombstone_branch") if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    wlfw_events = details.get("events") if isinstance(details.get("events"), dict) else {}
    wlfw_service = wlfw_events.get("wlfw_service_request") if isinstance(wlfw_events.get("wlfw_service_request"), dict) else {}
    wlfw_start = wlfw_events.get("wlfw_start") if isinstance(wlfw_events.get("wlfw_start"), dict) else {}
    wlanmdsp_trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    return {
        "label": v2103.get("label", ""),
        "decision": v2103.get("decision", ""),
        "tftp_ready_gate_open": boolish(cls.get("tftp_ready_gate_open")),
        "tftp_ready_safe": boolish(cls.get("tftp_ready_safe")),
        "per_mgr_register_vote": boolish(cls.get("per_mgr_register_vote")),
        "saw_msg21": boolish(cls.get("saw_msg21")),
        "wlan_pd_up": intish(cascade.get("wlan_pd_up")),
        "wlan_pd_up_ts": cascade.get("wlan_pd_up_ts", ""),
        "icnss_qmi_connected": intish(cascade.get("icnss_qmi_connected")),
        "fw_ready": intish(cascade.get("fw_ready")),
        "wlan0": intish(cascade.get("wlan0")),
        "server_check_file_seen": boolish(cls.get("server_check_file_seen")),
        "server_check_payload": cls.get("server_check_payload", ""),
        "server_after_wlan_pd_ms": intish(cls.get("server_after_wlan_pd_ms")),
        "ota_file_seen": boolish(cls.get("ota_ruleset_file_seen")),
        "ota_logdw_seen": boolish(cls.get("ota_firewall_seen")),
        "wlanmdsp_logdw_seen": boolish(cls.get("wlanmdsp_seen")),
        "mcfg_seen": boolish(cls.get("mcfg_seen")),
        "readwrite_summary": readwrite,
        "tftp_logdw_summary": {
            "record_count": intish(tftp_logdw.get("record_count")),
            "server_check": intish(nested(tftp_logdw, "summary", "server_check", default=0)),
            "ota_firewall": intish(nested(tftp_logdw, "summary", "ota_firewall", default=0)),
            "wlanmdsp": intish(nested(tftp_logdw, "summary", "wlanmdsp", default=0)),
            "mcfg": intish(nested(tftp_logdw, "summary", "mcfg", default=0)),
        },
        "legacy_firmware_serve_summary": {
            "label": tftp_summary.get("label", ""),
            "requested_any": intish(tftp_summary.get("requested_any")),
            "requested_server_check": intish(tftp_summary.get("requested_server_check")),
            "requested_ota_firewall": intish(tftp_summary.get("requested_ota_firewall")),
            "requested_wlanmdsp": intish(tftp_summary.get("requested_wlanmdsp")),
            "requested_mcfg": intish(tftp_summary.get("requested_mcfg")),
        },
        "wlfw_start_ts": trace_ts(str(wlfw_start.get("first_hit_line", ""))),
        "wlfw_service_request_ts": trace_ts(str(wlfw_service.get("first_hit_line", ""))),
        "first_wlanmdsp_lines": wlanmdsp_trace.get("first_wlanmdsp_lines", []),
        "first_pd_load_lines": cascade.get("first_pd_load_lines", []),
        "first_wlan_pd_up_lines": cascade.get("first_wlan_pd_up_lines", []),
        "tftp_branch": tftp_branch,
    }


def classify(mac: dict[str, Any], native: dict[str, Any]) -> tuple[str, bool, str]:
    mac_bounded = (
        boolish(mac.get("real_sysfs_mac_addr"))
        and intish(nested(mac, "mac_addr", "writable", default=0)) == 1
        and intish(nested(mac, "mac_info", "bytes", default=0)) == 17
        and not boolish(nested(mac, "trace", "mac_addr_write", default=False))
        and not boolish(nested(mac, "trace", "mac_addr_write_shape", default=False))
        and intish(mac.get("kernel_assign_count")) == 0
    )
    native_frontier = (
        boolish(native.get("tftp_ready_gate_open"))
        and boolish(native.get("per_mgr_register_vote"))
        and intish(native.get("wlan_pd_up")) == 1
        and boolish(native.get("server_check_file_seen"))
        and not boolish(native.get("ota_logdw_seen"))
        and not boolish(native.get("wlanmdsp_logdw_seen"))
        and intish(native.get("fw_ready")) == 0
        and intish(native.get("wlan0")) == 0
    )
    stale_summary_corrected = (
        intish(nested(native, "legacy_firmware_serve_summary", "requested_wlanmdsp", default=0)) > 0
        and not boolish(native.get("wlanmdsp_logdw_seen"))
        and not native.get("first_wlanmdsp_lines")
    )
    if not mac_bounded:
        return (
            "mac-falsifier-not-bounded",
            False,
            "MAC evidence is incomplete; do not use it to steer the producer gate yet",
        )
    if not native_frontier:
        return (
            "native-frontier-incomplete",
            False,
            "V2103 does not contain the full native producer frontier expected by this host-only pass",
        )
    if stale_summary_corrected:
        return (
            "mac-bounded-native-skips-android-order-tftp-bootstrap",
            True,
            "MAC is bounded as downstream/cosmetic; native reaches AP-side prerequisites but skips Android-order ota_firewall/wlanmdsp transfer evidence",
        )
    return (
        "mac-bounded-native-transfer-summary-consistent",
        True,
        "MAC is bounded; native frontier is preserved without a stale firmware-serve-summary contradiction",
    )


def render_report(manifest: dict[str, Any]) -> str:
    mac = manifest["mac"]
    native = manifest["native"]
    android = manifest["android"]
    source = mac["source_identity"]
    android_rows = [
        [item["name"], item["delta_from_tftp_start_ms"], item["line"]]
        for item in android["order"]
    ]
    native_rows = [
        ["tftp_ready", native["tftp_ready_gate_open"], f"safe={native['tftp_ready_safe']}"],
        ["per_mgr_vote", native["per_mgr_register_vote"], f"wlfw_service_request_ts={native['wlfw_service_request_ts']}"],
        ["wlan_pd_up", native["wlan_pd_up"], f"ts={native['wlan_pd_up_ts']} icnss_qmi={native['icnss_qmi_connected']} msg21={native['saw_msg21']}"],
        ["server_check_file", native["server_check_file_seen"], f"payload={native['server_check_payload']} after_wlan_pd_ms={native['server_after_wlan_pd_ms']}"],
        ["ota_firewall", native["ota_logdw_seen"], f"file={native['ota_file_seen']}"],
        ["wlanmdsp_transfer", native["wlanmdsp_logdw_seen"], f"first_lines={len(native['first_wlanmdsp_lines'])} fw_ready={native['fw_ready']} wlan0={native['wlan0']}"],
        ["mcfg", native["mcfg_seen"], "late/noise; Android requests wlanmdsp before mcfg"],
    ]
    return "\n".join([
        "# Native Init V2104 MAC Bounded Producer Frontier",
        "",
        "## Summary",
        "",
        "- Cycle: `V2104`",
        "- Type: host-only refinement over committed rollback-verified captures; no device boot or mutation.",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## MAC Bound",
        "",
        markdown_table(
            ["field", "value", "detail"],
            [
                ["identity_source", source["ok"], f"{source['source']} uid/gid wifi groups wifi/inet/net_raw/net_admin"],
                ["real_sysfs_mac_addr", mac["real_sysfs_mac_addr"], f"{mac['mac_addr']['absolute']} mode={mac['mac_addr']['mode']} fs={mac['mac_addr']['fs_type']} uid={mac['mac_addr']['uid']} gid={mac['mac_addr']['gid']}"],
                ["mac_info", mac["mac_info"]["exists"], f"bytes={mac['mac_info']['bytes']} readable={mac['mac_info']['readable']} writable={mac['mac_info']['writable']} uid={mac['mac_info']['uid']} gid={mac['mac_info']['gid']}"],
                ["macloader_trace", mac["trace"]["runtime_traced"], f"target={mac['trace']['runtime_target']} records={mac['trace']['records_seen']}"],
                ["mac_write", mac["trace"]["mac_addr_write"], f"open={mac['trace']['mac_addr_open']} shape={mac['trace']['mac_addr_write_shape']} raw_payload={mac['trace']['raw_mac_payload']}"],
                ["kernel_assign", mac["kernel_assign_count"], "proof line `icnss: Assigning MAC from Macloader`"],
            ],
        ),
        "",
        "## Android Producer Order",
        "",
        markdown_table(["event", "delta_from_tftp_start_ms", "line"], android_rows),
        "",
        "## Native Frontier",
        "",
        markdown_table(["area", "value", "detail"], native_rows),
        "",
        "## Corrected Request Semantics",
        "",
        "- V2103 legacy `wlan_pd_firmware_serve_gate.requested_wlanmdsp=1` is not transfer proof: `tftp_logdw` has no `wlanmdsp`, `first_wlanmdsp_lines=[]`, and `classification.wlanmdsp_seen=False`.",
        "- Treat visible transfer/request evidence as the `tftp_logdw` records, dmesg lines, and first-line lists; those remain zero for native `ota_firewall/ruleset` and `wlanmdsp.mbn`.",
        "- Native only shows a `server_check.txt=hello` file transition after `wlan_pd` UP, plus later `mcfg`; it does not enter Android's pre-UP `server_check -> ota_firewall -> wlanmdsp` bootstrap order.",
        "",
        "## Next Unit",
        "",
        "- Do not rerun MAC/macloader unless a new unit directly proves a kernel store and immediately falsifies producer impact.",
        "- Do not rerun AP-side RIL/cnss/pm-service strace, QRTR matrix, mcfg readback, server-check reachability, or SDX50M/eSoC/PCIe/GDSC paths.",
        "- Next live measurement should target the modem-internal branch that chooses Android's pre-UP TFTP bootstrap path after AP-side `wlfw_service_request` is already reproduced.",
        "",
        "## Inputs",
        "",
        markdown_table(
            ["input", "path"],
            [
                ["android_order", rel(V2053_SUMMARY)],
                ["mac_runtime", rel(V2091_MANIFEST)],
                ["mac_aggregate", rel(V2094_MANIFEST)],
                ["native_frontier", rel(V2103_MANIFEST)],
            ],
        ),
        "",
        "## Safety",
        "",
        "- Host-only parse/report generation; no flash, reboot, adb mutation, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, tftp ptrace, eSoC/PCIe/GDSC/PMIC/GPIO path, firmware/partition write, or `sda29` write.",
        "",
    ])


def main() -> int:
    v2053 = load_json(V2053_SUMMARY)
    v2091 = load_json(V2091_MANIFEST)
    v2094 = load_json(V2094_MANIFEST)
    v2103 = load_json(V2103_MANIFEST)
    android = collect_android(v2053)
    mac = collect_mac(v2091, v2094)
    native = collect_native(v2103)
    label, passed, reason = classify(mac, native)
    manifest = {
        "cycle": CYCLE,
        "decision": f"v2104-{label}-host-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "report": rel(REPORT_PATH),
        "android": android,
        "mac": mac,
        "native": native,
        "inputs": {
            "v2053_summary": rel(V2053_SUMMARY),
            "v2091_manifest": rel(V2091_MANIFEST),
            "v2094_manifest": rel(V2094_MANIFEST),
            "v2103_manifest": rel(V2103_MANIFEST),
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(json.dumps({"manifest": rel(MANIFEST_PATH), "report": rel(REPORT_PATH), "label": label, "pass": passed}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
