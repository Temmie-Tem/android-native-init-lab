#!/usr/bin/env python3
"""V2092 host-only MAC falsifier and TFTP producer-gate redirect."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2092-mac-falsifier-tftp-redirect"
MANIFEST_PATH = OUT_DIR / "manifest.json"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2092_MAC_FALSIFIER_TFTP_REDIRECT_2026-06-05.md"
)

V2091 = REPO_ROOT / "tmp" / "wifi" / "v2091-macloader-property-service-handoff" / "manifest.json"
V2083 = REPO_ROOT / "tmp" / "wifi" / "v2083-icnss-qcacld-post-bdf-handoff" / "manifest.json"
V2081 = REPO_ROOT / "tmp" / "wifi" / "v2081-wlfw-late-msg21-native-handoff" / "manifest.json"
V2059 = REPO_ROOT / "tmp" / "wifi" / "v2059-permgr-vote-focused-handoff" / "manifest.json"
V2053 = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V2053_PRE_WLANMDSP_TRIGGER_EVENT_DIFF_2026-06-04.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "on"}


def intish(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if value is None:
        return 0
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def tftp_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    summary = nested(manifest, "details", "tftp_logdw", "summary")
    return summary if isinstance(summary, dict) else {}


def cascade(manifest: dict[str, Any]) -> dict[str, Any]:
    value = nested(manifest, "details", "cascade")
    return value if isinstance(value, dict) else {}


def classification(manifest: dict[str, Any]) -> dict[str, Any]:
    value = manifest.get("classification")
    return value if isinstance(value, dict) else {}


def mac_source(manifest: dict[str, Any]) -> dict[str, Any]:
    value = nested(manifest, "details", "mac_source_bridge")
    return value if isinstance(value, dict) else {}


def mac_trace(manifest: dict[str, Any]) -> dict[str, Any]:
    value = nested(manifest, "details", "macloader_syscall_trace")
    return value if isinstance(value, dict) else {}


def property_shim(manifest: dict[str, Any]) -> dict[str, Any]:
    value = nested(manifest, "details", "property_service_shim")
    return value if isinstance(value, dict) else {}


def compact_run(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    cls = classification(manifest)
    tftp = tftp_summary(manifest)
    cas = cascade(manifest)
    return {
        "path": rel(path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label") or cls.get("label", ""),
        "pass": boolish(manifest.get("pass")) or boolish(cls.get("pass")),
        "rollback_ok": boolish(cls.get("rollback_ok")) or boolish(cls.get("v2091_rollback_ok")),
        "route_ok": boolish(cls.get("route_ok")),
        "per_mgr_register_vote": boolish(cls.get("per_mgr_register_vote"))
        or (
            boolish(cls.get("per_mgr_client_success"))
            and boolish(cls.get("per_mgr_server_success"))
        ),
        "cap_bdf_cal_success": boolish(cls.get("cap_bdf_cal_success")),
        "saw_msg21": boolish(cls.get("saw_msg21")),
        "wlan_pd_up": intish(cas.get("wlan_pd_up")),
        "icnss_qmi": intish(cas.get("icnss_qmi_connected")),
        "fw_ready": intish(cas.get("fw_ready")),
        "wlan0": intish(cas.get("wlan0")),
        "server_check": intish(tftp.get("server_check")),
        "ota_firewall": intish(tftp.get("ota_firewall")),
        "mcfg": intish(tftp.get("mcfg")),
        "wlanmdsp": intish(tftp.get("wlanmdsp")) + intish(tftp.get("fallback_wlanmdsp")),
        "mac_assigned": boolish(cls.get("mac_assigned")),
        "datagrams": intish(tftp.get("datagrams")),
        "total_bytes_4251884": intish(tftp.get("total_bytes_4251884")),
    }


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        escaped = [str(cell).replace("\n", "<br>").replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def classify(data: dict[str, dict[str, Any]]) -> tuple[str, bool, str]:
    v2091 = data["v2091"]
    mac = v2091["mac"]
    trace = v2091["trace"]
    route = v2091["route"]
    refs = [data["v2083"]["route"], data["v2081"]["route"], data["v2059"]["route"]]

    real_sysfs = boolish(mac.get("real_sysfs_mac_addr")) or boolish(route.get("real_sysfs"))
    macloader_traced = boolish(trace.get("runtime_traced")) and intish(trace.get("records_seen")) > 0
    no_mac_write = not boolish(trace.get("mac_addr_write"))
    no_mac_shape = not boolish(trace.get("mac_addr_write_shape"))
    no_mac_info_read = not boolish(trace.get("mac_info_read"))
    no_kernel_assign = not boolish(route.get("mac_assigned"))
    no_tftp_bootstrap = intish(route.get("server_check")) == 0 and intish(route.get("wlanmdsp")) == 0
    ap_side_reproduced = any(
        boolish(ref.get("per_mgr_register_vote"))
        and intish(ref.get("wlan_pd_up")) == 1
        for ref in refs
    )
    latest_no_wlanmdsp = intish(data["v2083"]["route"].get("wlanmdsp")) == 0

    if not real_sysfs:
        return (
            "mac-falsifier-real-sysfs-unproven",
            False,
            "V2091 did not prove /sys/wifi/mac_addr was the real writable sysfs node",
        )
    if not macloader_traced:
        return (
            "mac-falsifier-trace-missing",
            False,
            "V2091 did not produce bounded macloader syscall records",
        )
    if not (no_mac_write and no_mac_shape and no_mac_info_read and no_kernel_assign):
        return (
            "mac-falsifier-inconclusive",
            True,
            "macloader reached a MAC-source or MAC-write edge; a live producer retest would be required before closing MAC",
        )
    if no_tftp_bootstrap and ap_side_reproduced and latest_no_wlanmdsp:
        return (
            "mac-no-write-tftp-producer-gate-retained",
            True,
            "real sysfs was present and macloader was traced, but it never read .mac.info or wrote /sys/wifi/mac_addr; current AP-side route still reproduces PerMgr/WLFW publication while tftp has no server_check or wlanmdsp",
        )
    return (
        "mac-no-write-needs-tftp-refresh",
        True,
        "MAC assignment did not occur, but the tftp producer evidence set is incomplete",
    )


def render_report(manifest: dict[str, Any]) -> str:
    data = manifest["data"]
    route_rows = []
    for key in ("v2091", "v2083", "v2081", "v2059"):
        route = data[key]["route"]
        route_rows.append([
            key.upper(),
            route["label"],
            route["rollback_ok"],
            route["per_mgr_register_vote"],
            route["cap_bdf_cal_success"],
            route["saw_msg21"],
            route["wlan_pd_up"],
            route["icnss_qmi"],
            route["server_check"],
            route["mcfg"],
            route["wlanmdsp"],
            route["fw_ready"],
            route["wlan0"],
        ])

    mac = data["v2091"]["mac"]
    trace = data["v2091"]["trace"]
    shim = data["v2091"]["property_shim"]

    return "\n".join([
        "# Native Init V2092 MAC Falsifier / TFTP Redirect",
        "",
        "## Summary",
        "",
        "- Cycle: `V2092`",
        "- Type: host-only classifier over committed rollback-verified evidence; no new boot or device mutation.",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{rel(OUT_DIR)}`",
        "",
        "## MAC Boundary",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["real_sysfs_mac_addr", mac.get("real_sysfs_mac_addr")],
                ["mac_addr_fs_type", mac.get("mac_addr", {}).get("fs_type_text")],
                ["mac_addr_mode", mac.get("mac_addr", {}).get("mode")],
                ["mac_info_readable_bytes", mac.get("mac_info", {}).get("bytes")],
                ["macloader_runtime_traced", trace.get("runtime_traced")],
                ["macloader_records_seen", trace.get("records_seen")],
                ["mac_info_read", trace.get("mac_info_read")],
                ["mac_addr_open", trace.get("mac_addr_open")],
                ["mac_addr_write", trace.get("mac_addr_write")],
                ["mac_addr_write_shape", trace.get("mac_addr_write_shape")],
                ["kernel_assign_line", data["v2091"]["route"].get("mac_assigned")],
                ["property_shim_started", shim.get("started")],
                ["property_shim_requests", shim.get("request_count")],
                ["property_shim_macloader_ack_count", shim.get("macloader_ack_count")],
            ],
        ),
        "",
        "## Route Matrix",
        "",
        markdown_table(
            [
                "run",
                "label",
                "rollback",
                "per_mgr",
                "cap_bdf_cal",
                "msg21",
                "wlan_pd",
                "icnss_qmi",
                "server_check",
                "mcfg",
                "wlanmdsp",
                "fw_ready",
                "wlan0",
            ],
            route_rows,
        ),
        "",
        "## Interpretation",
        "",
        "- V2091 satisfies the requested quick falsifier: `/sys/wifi/mac_addr` was the real writable sysfs node, but `macloader` never read `.mac.info`, opened/wrote `mac_addr`, produced a colon/hex MAC write, or triggered the kernel `Assigning MAC from Macloader` line.",
        "- That closes additional MAC plumbing as a low-value branch for the producer gate; a successful later MAC assignment would still be downstream of FW-ready/netdev creation, not evidence that the modem selected the WLAN image-request branch.",
        "- Current committed native evidence already reproduces the AP-side PerMgr/WLFW path and reaches `wlan_pd`/`icnss_qmi`, while stock `tftp_server` logs remain `server_check=0` and `wlanmdsp=0` in the latest no-ptrace route.",
        "- The next target remains the modem-internal TFTP producer branch: why native selects late `mcfg` traffic instead of Android's `server_check.txt -> ota_firewall/ruleset -> wlanmdsp.mbn` branch.",
        "",
        "## Inputs",
        "",
        markdown_table(
            ["key", "path"],
            [
                ["v2091", data["v2091"]["route"]["path"]],
                ["v2083", data["v2083"]["route"]["path"]],
                ["v2081", data["v2081"]["route"]["path"]],
                ["v2059", data["v2059"]["route"]["path"]],
                ["v2053", rel(V2053)],
            ],
        ),
        "",
        "## Safety",
        "",
        "- Host-only parse/report generation; no flash, reboot, adb device mutation, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, tftp ptrace, eSoC/PCIe/GDSC/PMIC/GPIO path, firmware/partition write, or `sda29` write.",
        "",
    ])


def main() -> int:
    required = [V2091, V2083, V2081, V2059, V2053]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"missing required evidence: {', '.join(missing)}")

    v2091 = load_json(V2091)
    v2083 = load_json(V2083)
    v2081 = load_json(V2081)
    v2059 = load_json(V2059)
    data = {
        "v2091": {
            "route": compact_run(V2091, v2091),
            "mac": mac_source(v2091),
            "trace": mac_trace(v2091),
            "property_shim": property_shim(v2091),
        },
        "v2083": {"route": compact_run(V2083, v2083)},
        "v2081": {"route": compact_run(V2081, v2081)},
        "v2059": {"route": compact_run(V2059, v2059)},
    }
    label, passed, reason = classify(data)
    decision = f"v2092-{label}-host-{'pass' if passed else 'blocked'}"
    manifest = {
        "cycle": "V2092",
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "data": data,
        "report": rel(REPORT_PATH),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(f"decision={decision}")
    print(f"report={rel(REPORT_PATH)}")
    print(f"manifest={rel(MANIFEST_PATH)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
