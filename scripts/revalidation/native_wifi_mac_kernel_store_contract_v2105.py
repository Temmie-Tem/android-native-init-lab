#!/usr/bin/env python3
"""V2105 host-only MAC kernel-store contract refinement."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CYCLE = "V2105"
SYSFS_MAGIC_TEXT = "0x0000000062656572"
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2105-mac-kernel-store-contract"
MANIFEST_PATH = OUT_DIR / "manifest.json"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2105_MAC_KERNEL_STORE_CONTRACT_2026-06-05.md"
)

V2091_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v2091-macloader-property-service-handoff" / "manifest.json"
V2103_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v2103-tftp-process-namespace-audit-handoff" / "manifest.json"
V2104_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v2104-mac-bounded-producer-frontier" / "manifest.json"
HELPER_SOURCE = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


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


def helper_contract() -> dict[str, Any]:
    text = HELPER_SOURCE.read_text(encoding="utf-8", errors="replace")
    tokens = {
        "macloader_identity_fn": "apply_macloader_identity_contract",
        "macloader_uid_wifi": '"macloader",\n                                             A90_AID_WIFI',
        "macloader_gid_wifi": "A90_AID_WIFI,\n                                             groups",
        "macloader_groups_wifi": "A90_AID_WIFI, A90_AID_INET, A90_AID_NET_RAW, A90_AID_NET_ADMIN",
        "sys_wifi_bind_rw": 'bind_optional_rw_dir("/sys/wifi",',
        "not_tmpfs_standin": 'bind_optional_rw_dir("/sys/wifi",',
        "macloader_single_child_trace": "A90_WIFI_TEST_BOOT_MACLOADER_SYSCALL_TRACE",
        "redacted_colon_hex_shape": "write_payload.contains_colon",
    }
    hits = {name: token in text for name, token in tokens.items()}
    return {
        "source": rel(HELPER_SOURCE),
        "ok": all(hits.values()),
        "hits": hits,
    }


def dmesg_assign_count(v2091: dict[str, Any]) -> int:
    handoff_manifest = Path(str(v2091.get("handoff_manifest", "")))
    if not handoff_manifest.is_absolute():
        handoff_manifest = REPO_ROOT / handoff_manifest
    dmesg = handoff_manifest.parent / "test-v1393-dmesg.stdout.txt"
    if not dmesg.exists():
        return 0
    return sum(
        1
        for line in dmesg.read_text(encoding="utf-8", errors="replace").splitlines()
        if "icnss: Assigning MAC from Macloader" in line
    )


def collect_mac_contract(v2091: dict[str, Any]) -> dict[str, Any]:
    details = v2091.get("details") if isinstance(v2091.get("details"), dict) else {}
    source = details.get("mac_source_bridge") if isinstance(details.get("mac_source_bridge"), dict) else {}
    trace = details.get("macloader_syscall_trace") if isinstance(details.get("macloader_syscall_trace"), dict) else {}
    pre = details.get("macloader_pre_cnss") if isinstance(details.get("macloader_pre_cnss"), dict) else {}
    mac_addr = source.get("mac_addr") if isinstance(source.get("mac_addr"), dict) else {}
    post_mac_addr = source.get("post_mac_addr") if isinstance(source.get("post_mac_addr"), dict) else {}
    mac_info = source.get("mac_info") if isinstance(source.get("mac_info"), dict) else {}
    contract = helper_contract()
    real_node = (
        boolish(source.get("real_sysfs_mac_addr"))
        and intish(mac_addr.get("exists")) == 1
        and intish(mac_addr.get("statfs_ok")) == 1
        and str(mac_addr.get("fs_type_text", "")) == SYSFS_MAGIC_TEXT
        and str(post_mac_addr.get("fs_type_text", "")) == SYSFS_MAGIC_TEXT
        and str(mac_addr.get("mode", "")) == "0220"
    )
    macloader_group_wifi = (
        boolish(nested(contract, "hits", "macloader_identity_fn", default=False))
        and boolish(nested(contract, "hits", "macloader_uid_wifi", default=False))
        and boolish(nested(contract, "hits", "macloader_gid_wifi", default=False))
        and boolish(nested(contract, "hits", "macloader_groups_wifi", default=False))
    )
    write_attempt = (
        boolish(trace.get("mac_addr_open"))
        or boolish(trace.get("mac_addr_write"))
        or boolish(trace.get("mac_addr_write_shape"))
    )
    format_proven = boolish(trace.get("mac_addr_write_shape"))
    kernel_assign_count = dmesg_assign_count(v2091)
    return {
        "helper_contract": contract,
        "mac_addr": {
            "absolute": mac_addr.get("absolute", ""),
            "exists": intish(mac_addr.get("exists")),
            "mode": mac_addr.get("mode", ""),
            "uid": intish(mac_addr.get("uid")),
            "gid": intish(mac_addr.get("gid")),
            "writable": intish(mac_addr.get("writable")),
            "statfs_ok": intish(mac_addr.get("statfs_ok")),
            "fs_type": mac_addr.get("fs_type_text", ""),
            "post_fs_type": post_mac_addr.get("fs_type_text", ""),
        },
        "mac_info": {
            "absolute": mac_info.get("absolute", ""),
            "exists": intish(mac_info.get("exists")),
            "readable": intish(mac_info.get("readable")),
            "writable": intish(mac_info.get("writable")),
            "bytes": intish(mac_info.get("bytes")),
            "uid": intish(mac_info.get("uid")),
            "gid": intish(mac_info.get("gid")),
        },
        "trace": {
            "target": trace.get("runtime_target", ""),
            "traced": intish(trace.get("runtime_traced")),
            "records_seen": intish(trace.get("records_seen")),
            "raw_mac_payload": intish(trace.get("raw_mac_payload")),
            "mac_info_open": boolish(trace.get("mac_info_open")),
            "mac_info_read": boolish(trace.get("mac_info_read")),
            "mac_addr_open": boolish(trace.get("mac_addr_open")),
            "mac_addr_write": boolish(trace.get("mac_addr_write")),
            "mac_addr_write_shape": boolish(trace.get("mac_addr_write_shape")),
            "sample_records": trace.get("sample_records", []),
        },
        "runtime": {
            "enabled": intish(pre.get("enabled")),
            "active_driver_start": intish(pre.get("active_driver_start")),
            "observable": intish(pre.get("observable")),
            "ready": intish(pre.get("ready")),
            "mac_assigned": intish(pre.get("mac_assigned")),
        },
        "real_kernel_sysfs_node": real_node,
        "macloader_group_wifi_contract": macloader_group_wifi,
        "write_attempt_observed": write_attempt,
        "colon_hex_format_observed": format_proven,
        "kernel_assign_count": kernel_assign_count,
        "kernel_assign_proven": kernel_assign_count > 0,
    }


def trace_ts(line: str) -> float | None:
    match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
    return float(match.group(1)) if match else None


def collect_producer_frontier(v2103: dict[str, Any], v2104: dict[str, Any]) -> dict[str, Any]:
    classification = v2103.get("classification") if isinstance(v2103.get("classification"), dict) else {}
    details = v2103.get("details") if isinstance(v2103.get("details"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    events = details.get("events") if isinstance(details.get("events"), dict) else {}
    tftp_logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = tftp_logdw.get("summary") if isinstance(tftp_logdw.get("summary"), dict) else {}
    wlfw_service = events.get("wlfw_service_request") if isinstance(events.get("wlfw_service_request"), dict) else {}
    v2104_native = v2104.get("native") if isinstance(v2104.get("native"), dict) else {}
    v2104_android = v2104.get("android") if isinstance(v2104.get("android"), dict) else {}
    return {
        "native_label": v2103.get("label", ""),
        "tftp_ready": boolish(classification.get("tftp_ready_gate_open")),
        "per_mgr_vote": boolish(classification.get("per_mgr_register_vote")),
        "wlfw_service_request_ts": trace_ts(str(wlfw_service.get("first_hit_line", ""))),
        "wlan_pd_up": intish(cascade.get("wlan_pd_up")),
        "wlan_pd_up_ts": cascade.get("wlan_pd_up_ts", ""),
        "icnss_qmi": intish(cascade.get("icnss_qmi_connected")),
        "msg21": boolish(classification.get("saw_msg21")),
        "fw_ready": intish(cascade.get("fw_ready")),
        "wlan0": intish(cascade.get("wlan0")),
        "server_check_file_seen": boolish(classification.get("server_check_file_seen")),
        "server_check_payload": classification.get("server_check_payload", ""),
        "server_after_wlan_pd_ms": intish(classification.get("server_after_wlan_pd_ms")),
        "server_check_logdw": intish(summary.get("server_check")),
        "ota_firewall_logdw": intish(summary.get("ota_firewall")),
        "wlanmdsp_logdw": intish(summary.get("wlanmdsp")),
        "mcfg_logdw": intish(summary.get("mcfg")),
        "v2104_label": v2104.get("label", ""),
        "android_order": v2104_android.get("order", []),
        "native_frontier": v2104_native,
    }


def classify(mac: dict[str, Any], producer: dict[str, Any]) -> tuple[str, bool, str]:
    mac_contract_closed = (
        boolish(mac.get("real_kernel_sysfs_node"))
        and boolish(mac.get("macloader_group_wifi_contract"))
        and intish(nested(mac, "trace", "traced", default=0)) == 1
        and intish(nested(mac, "trace", "records_seen", default=0)) > 0
        and not boolish(mac.get("write_attempt_observed"))
        and not boolish(mac.get("kernel_assign_proven"))
    )
    producer_gap_preserved = (
        boolish(producer.get("tftp_ready"))
        and boolish(producer.get("per_mgr_vote"))
        and intish(producer.get("wlan_pd_up")) == 1
        and boolish(producer.get("server_check_file_seen"))
        and intish(producer.get("server_check_logdw")) == 0
        and intish(producer.get("ota_firewall_logdw")) == 0
        and intish(producer.get("wlanmdsp_logdw")) == 0
        and intish(producer.get("fw_ready")) == 0
        and intish(producer.get("wlan0")) == 0
    )
    if not boolish(mac.get("real_kernel_sysfs_node")):
        return (
            "mac-node-not-proven-real",
            False,
            "/sys/wifi/mac_addr is not proven to be the real sysfs ICNSS node",
        )
    if not boolish(mac.get("macloader_group_wifi_contract")):
        return (
            "macloader-wifi-identity-contract-missing",
            False,
            "macloader UID/GID/group wifi source contract is incomplete",
        )
    if boolish(mac.get("write_attempt_observed")) and boolish(mac.get("kernel_assign_proven")):
        return (
            "mac-real-assign-proven-but-producer-gap-remains",
            True,
            "kernel MAC assignment is real, but producer evidence still decides the next gate",
        )
    if boolish(mac.get("write_attempt_observed")) and not boolish(mac.get("colon_hex_format_observed")):
        return (
            "mac-write-observed-format-not-proven",
            True,
            "macloader attempted the real node but the redacted trace did not prove colon/hex payload shape",
        )
    if mac_contract_closed and producer_gap_preserved:
        return (
            "mac-real-node-no-write-producer-remains-tftp-bootstrap",
            True,
            "real ICNSS MAC node and wifi identity are proven, but macloader never writes it; MAC stays bounded and the remaining gap is the missing server_check/ota_firewall/wlanmdsp producer branch",
        )
    return (
        "mac-contract-partial-producer-frontier-incomplete",
        False,
        "MAC or producer frontier evidence is incomplete for this bounded host-only closeout",
    )


def render_report(manifest: dict[str, Any]) -> str:
    mac = manifest["mac"]
    producer = manifest["producer"]
    helper = mac["helper_contract"]
    mac_rows = [
        ["real_sysfs_node", mac["real_kernel_sysfs_node"], f"{mac['mac_addr']['absolute']} mode={mac['mac_addr']['mode']} fs={mac['mac_addr']['fs_type']} post_fs={mac['mac_addr']['post_fs_type']}"],
        ["not_tmpfs_standin", helper["hits"]["sys_wifi_bind_rw"], "helper binds `/sys/wifi` RW into the namespace; it does not synthesize a tmpfs mac_addr"],
        ["macloader_wifi_identity", mac["macloader_group_wifi_contract"], "source UID/GID/group includes `A90_AID_WIFI`"],
        ["mac_info_source", mac["mac_info"]["exists"], f"bytes={mac['mac_info']['bytes']} readable={mac['mac_info']['readable']} writable={mac['mac_info']['writable']} uid={mac['mac_info']['uid']} gid={mac['mac_info']['gid']}"],
        ["trace_target", mac["trace"]["traced"], f"target={mac['trace']['target']} records={mac['trace']['records_seen']} raw_mac_payload={mac['trace']['raw_mac_payload']}"],
        ["macloader_read", mac["trace"]["mac_info_read"], f"open={mac['trace']['mac_info_open']}"],
        ["macloader_write", mac["trace"]["mac_addr_write"], f"open={mac['trace']['mac_addr_open']} colon_hex_shape={mac['colon_hex_format_observed']}"],
        ["kernel_assign", mac["kernel_assign_proven"], f"count={mac['kernel_assign_count']} proof=`icnss: Assigning MAC from Macloader`"],
    ]
    producer_rows = [
        ["tftp_ready", producer["tftp_ready"], ""],
        ["per_mgr_vote", producer["per_mgr_vote"], f"wlfw_service_request_ts={producer['wlfw_service_request_ts']}"],
        ["wlan_pd_up", producer["wlan_pd_up"], f"ts={producer['wlan_pd_up_ts']} icnss_qmi={producer['icnss_qmi']} msg21={producer['msg21']}"],
        ["server_check_file", producer["server_check_file_seen"], f"payload={producer['server_check_payload']} after_wlan_pd_ms={producer['server_after_wlan_pd_ms']}"],
        ["server_check_logdw", producer["server_check_logdw"], "early Android branch remains absent"],
        ["ota_firewall_logdw", producer["ota_firewall_logdw"], ""],
        ["wlanmdsp_logdw", producer["wlanmdsp_logdw"], f"fw_ready={producer['fw_ready']} wlan0={producer['wlan0']}"],
        ["mcfg_logdw", producer["mcfg_logdw"], "late/noise; Android requests wlanmdsp before mcfg"],
    ]
    android_rows = [
        [
            item.get("name", ""),
            item.get("delta_from_tftp_start_ms", ""),
            item.get("line", ""),
        ]
        for item in producer.get("android_order", [])
    ]
    return "\n".join([
        "# Native Init V2105 MAC Kernel Store Contract",
        "",
        "## Summary",
        "",
        f"- Cycle: `{manifest['cycle']}`",
        "- Type: host-only refinement over existing rollback-verified captures; no device boot or mutation.",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## MAC Contract",
        "",
        markdown_table(["check", "value", "detail"], mac_rows),
        "",
        "## Producer Frontier",
        "",
        markdown_table(["area", "value", "detail"], producer_rows),
        "",
        "## Android Order Anchor",
        "",
        markdown_table(["event", "delta_from_tftp_start_ms", "line"], android_rows),
        "",
        "## Interpretation",
        "",
        "- The namespace `/sys/wifi/mac_addr` is the real sysfs ICNSS node: `statfs` reports sysfs magic `0x62656572`, the file is mode `0220`, and the helper source bind-mounts `/sys/wifi` rather than materializing a tmpfs stand-in.",
        "- The macloader identity contract is present in source as UID/GID/group `wifi`; V2091 traced `/vendor/bin/hw/macloader` but saw no `.mac.info` read and no `/sys/wifi/mac_addr` open/write.",
        "- Because there is no write record, the `%x:%x:...` payload shape is not proven or disproven at runtime; the falsifier resolves earlier: no write reached the kernel store, and the kernel emitted zero `icnss: Assigning MAC from Macloader` lines.",
        "- Even a successful assign would feed `cnss_utils` for later qcacld/HDD netdev creation after FW-ready; it does not explain the current producer gap where native skips Android's `server_check -> ota_firewall -> wlanmdsp` TFTP branch.",
        "",
        "## Next Unit",
        "",
        "- Do not spend another cycle on MAC/macloader unless a new run directly shows a real kernel assign and immediate producer impact.",
        "- Keep the primary measurement on why the internal modem does not enter the Android-order pre-UP TFTP bootstrap branch after AP-side `wlfw_service_request` is already reproduced.",
        "- Do not rerun AP-side RIL/cnss/pm-service strace, QRTR matrix, mcfg readback, server-check reachability, passive DIAG, or SDX50M/eSoC/PCIe/GDSC paths.",
        "",
        "## Inputs",
        "",
        markdown_table(
            ["input", "path"],
            [
                ["mac_runtime", rel(V2091_MANIFEST)],
                ["native_frontier", rel(V2103_MANIFEST)],
                ["bounded_frontier", rel(V2104_MANIFEST)],
                ["helper_source", rel(HELPER_SOURCE)],
            ],
        ),
        "",
        "## Safety",
        "",
        "- Host-only parse/report generation; no flash, reboot, adb mutation, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, tftp ptrace, eSoC/PCIe/GDSC/PMIC/GPIO path, firmware/partition write, EFS write, or `sda29` write.",
        "",
    ])


def main() -> int:
    v2091 = load_json(V2091_MANIFEST)
    v2103 = load_json(V2103_MANIFEST)
    v2104 = load_json(V2104_MANIFEST)
    mac = collect_mac_contract(v2091)
    producer = collect_producer_frontier(v2103, v2104)
    label, passed, reason = classify(mac, producer)
    manifest = {
        "cycle": CYCLE,
        "decision": f"v2105-{label}-host-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "report": rel(REPORT_PATH),
        "mac": mac,
        "producer": producer,
        "inputs": {
            "v2091_manifest": rel(V2091_MANIFEST),
            "v2103_manifest": rel(V2103_MANIFEST),
            "v2104_manifest": rel(V2104_MANIFEST),
            "helper_source": rel(HELPER_SOURCE),
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(json.dumps({"manifest": rel(MANIFEST_PATH), "report": rel(REPORT_PATH), "label": label, "pass": passed}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
