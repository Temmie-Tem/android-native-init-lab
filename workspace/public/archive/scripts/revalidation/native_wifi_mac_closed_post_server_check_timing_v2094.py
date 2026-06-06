#!/usr/bin/env python3
"""V2094 host-only refinement: close MAC and time the post-server_check TFTP gap."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2094-mac-closed-post-server-check-timing"
MANIFEST_PATH = OUT_DIR / "manifest.json"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2094_MAC_CLOSED_POST_SERVER_CHECK_TIMING_2026-06-05.md"
)

INPUTS = {
    "v2059": REPO_ROOT / "tmp" / "wifi" / "v2059-permgr-vote-focused-handoff" / "manifest.json",
    "v2081": REPO_ROOT / "tmp" / "wifi" / "v2081-wlfw-late-msg21-native-handoff" / "manifest.json",
    "v2083": REPO_ROOT / "tmp" / "wifi" / "v2083-icnss-qcacld-post-bdf-handoff" / "manifest.json",
    "v2091": REPO_ROOT / "tmp" / "wifi" / "v2091-macloader-property-service-handoff" / "manifest.json",
}
ANDROID_DIFF = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V2053_PRE_WLANMDSP_TRIGGER_EVENT_DIFF_2026-06-04.md"
V2091_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V2091_MACLOADER_PROPERTY_SERVICE_HANDOFF_2026-06-05.md"
V2093_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V2093_SERVER_CHECK_POST_BRANCH_2026-06-05.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def intish(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if value is None:
        return 0
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def floatish(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def trace_time(line: str) -> float | None:
    match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
    if not match:
        return None
    return floatish(match.group(1))


def helper_path(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    handoff_manifest = Path(str(manifest.get("handoff_manifest", "")))
    if not handoff_manifest.is_absolute():
        handoff_manifest = REPO_ROOT / handoff_manifest
    candidate = handoff_manifest.parent / "test-v1393-helper-result.stdout.txt"
    if candidate.exists():
        return candidate
    return manifest_path.parent / "test-v1393-helper-result.stdout.txt"


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key] = value
    return fields


def first_sample(fields: dict[str, str], item: str, predicate: Any) -> dict[str, Any]:
    for index in range(64):
        prefix = f"tftp_readwrite_transition.sample_{index:03d}"
        if f"{prefix}.{item}.exists" not in fields:
            continue
        if not predicate(prefix):
            continue
        return {
            "index": index,
            "phase": fields.get(f"{prefix}.phase", ""),
            "monotonic_ms": intish(fields.get(f"{prefix}.monotonic_ms")),
            "delta_ms": intish(fields.get(f"{prefix}.delta_ms")),
            "exists": intish(fields.get(f"{prefix}.{item}.exists")),
            "is_reg": intish(fields.get(f"{prefix}.{item}.is_reg")),
            "size": intish(fields.get(f"{prefix}.{item}.size")),
            "mode": fields.get(f"{prefix}.{item}.mode", ""),
            "payload": fields.get(f"{prefix}.{item}.payload", ""),
        }
    return {
        "index": -1,
        "phase": "",
        "monotonic_ms": 0,
        "delta_ms": 0,
        "exists": 0,
        "is_reg": 0,
        "size": 0,
        "mode": "",
        "payload": "",
    }


def collect_run(key: str, manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    helper = helper_path(manifest_path, manifest)
    fields = parse_fields(helper.read_text(encoding="utf-8", errors="replace"))
    cls = manifest.get("classification")
    if not isinstance(cls, dict):
        cls = {}
    details = manifest.get("details")
    if not isinstance(details, dict):
        details = {}
    cascade = details.get("cascade")
    if not isinstance(cascade, dict):
        cascade = {}
    tftp_summary = nested(manifest, "details", "tftp_logdw", "summary")
    if not isinstance(tftp_summary, dict):
        tftp_summary = {}

    server_check = first_sample(
        fields,
        "server_check",
        lambda prefix: fields.get(f"{prefix}.server_check.payload") == "hello",
    )
    mcfg = first_sample(fields, "mcfg", lambda prefix: fields.get(f"{prefix}.mcfg.exists") == "1")
    ota = first_sample(fields, "ota_ruleset", lambda prefix: fields.get(f"{prefix}.ota_ruleset.exists") == "1")
    per_mgr_ts = trace_time(
        fields.get("per_mgr_vote_focused.cnss.pm_client_connect_retcheck.first_hit_line", "")
        or fields.get("per_mgr_vote_focused.cnss.pm_client_register_retcheck.first_hit_line", "")
    )
    wlan_pd_up_ts = floatish(cascade.get("wlan_pd_up_ts"))
    server_check_s = server_check["monotonic_ms"] / 1000.0 if server_check["monotonic_ms"] else None
    mcfg_s = mcfg["monotonic_ms"] / 1000.0 if mcfg["monotonic_ms"] else None
    return {
        "key": key,
        "manifest": rel(manifest_path),
        "helper": rel(helper),
        "label": manifest.get("label") or cls.get("label", ""),
        "rollback_ok": boolish(cls.get("rollback_ok")) or boolish(cls.get("v2091_rollback_ok")),
        "per_mgr_ok": boolish(cls.get("per_mgr_register_vote"))
        or (
            boolish(cls.get("per_mgr_client_success"))
            and boolish(cls.get("per_mgr_server_success"))
        ),
        "wlan_pd_up": intish(cascade.get("wlan_pd_up")),
        "wlan_pd_up_ts": wlan_pd_up_ts,
        "icnss_qmi": intish(cascade.get("icnss_qmi_connected")),
        "fw_ready": intish(cascade.get("fw_ready")),
        "wlan0": intish(cascade.get("wlan0")),
        "per_mgr_ts": per_mgr_ts,
        "server_check": server_check,
        "server_after_per_mgr_ms": delta_ms(server_check_s, per_mgr_ts),
        "server_after_wlan_pd_ms": delta_ms(server_check_s, wlan_pd_up_ts),
        "mcfg": mcfg,
        "mcfg_after_server_ms": delta_ms(mcfg_s, server_check_s),
        "ota": ota,
        "tftp_ota": intish(tftp_summary.get("ota_firewall")),
        "tftp_mcfg": intish(tftp_summary.get("mcfg")),
        "tftp_wlanmdsp": intish(tftp_summary.get("wlanmdsp")) + intish(tftp_summary.get("fallback_wlanmdsp")),
    }


def delta_ms(later_s: float | None, earlier_s: float | None) -> int | None:
    if later_s is None or earlier_s is None:
        return None
    return int(round((later_s - earlier_s) * 1000.0))


def mac_summary(v2091_manifest: dict[str, Any]) -> dict[str, Any]:
    mac_source = nested(v2091_manifest, "details", "mac_source_bridge")
    trace = nested(v2091_manifest, "details", "macloader_syscall_trace")
    cls = v2091_manifest.get("classification")
    if not isinstance(mac_source, dict):
        mac_source = {}
    if not isinstance(trace, dict):
        trace = {}
    if not isinstance(cls, dict):
        cls = {}
    mac_addr = mac_source.get("mac_addr")
    if not isinstance(mac_addr, dict):
        mac_addr = {}
    mac_info = mac_source.get("mac_info")
    if not isinstance(mac_info, dict):
        mac_info = {}
    return {
        "real_sysfs": boolish(mac_source.get("real_sysfs_mac_addr")) or boolish(cls.get("real_sysfs")),
        "mac_addr_exists": intish(mac_addr.get("exists")),
        "mac_addr_writable": intish(mac_addr.get("writable")),
        "mac_addr_mode": mac_addr.get("mode", ""),
        "mac_addr_fs_type": mac_addr.get("fs_type_text", ""),
        "mac_info_exists": intish(mac_info.get("exists")),
        "mac_info_bytes": intish(mac_info.get("bytes")),
        "mac_info_readable": intish(mac_info.get("readable")),
        "mac_info_writable": intish(mac_info.get("writable")),
        "runtime_traced": intish(trace.get("runtime_traced")),
        "records_seen": intish(trace.get("records_seen")),
        "mac_info_read": boolish(trace.get("mac_info_read")),
        "mac_addr_open": boolish(trace.get("mac_addr_open")),
        "mac_addr_write": boolish(trace.get("mac_addr_write")),
        "mac_addr_write_shape": boolish(trace.get("mac_addr_write_shape")),
        "mac_assigned": boolish(cls.get("mac_assigned")),
    }


def classify(runs: dict[str, dict[str, Any]], mac: dict[str, Any]) -> tuple[str, bool, str]:
    checked = [runs[key] for key in ("v2059", "v2081", "v2083", "v2091")]
    mac_closed = (
        mac["real_sysfs"]
        and mac["mac_info_exists"] == 1
        and mac["mac_info_readable"] == 1
        and not mac["mac_addr_write"]
        and not mac["mac_addr_write_shape"]
        and not mac["mac_assigned"]
    )
    post_up_server_check = all(
        run["server_check"]["payload"] == "hello"
        and run["server_after_wlan_pd_ms"] is not None
        and run["server_after_wlan_pd_ms"] > 0
        for run in checked
    )
    no_ota_wlanmdsp = all(
        run["ota"]["index"] < 0
        and run["tftp_ota"] == 0
        and run["tftp_wlanmdsp"] == 0
        for run in checked
    )
    ap_publication_ok = all(
        run["per_mgr_ok"] and run["wlan_pd_up"] == 1 and run["icnss_qmi"] == 1
        for run in checked
    )
    if mac_closed and post_up_server_check and no_ota_wlanmdsp and ap_publication_ok:
        return (
            "mac-closed-post-up-server-check-no-ota-wlanmdsp",
            True,
            "MAC assignment is closed as a bounded downstream falsifier; native server_check.txt appears only after wlan_pd UP and never advances into Android's ota_firewall/wlanmdsp producer branch",
        )
    return (
        "mac-post-server-check-timing-review",
        False,
        "MAC or post-server_check timing evidence is mixed; inspect per-run rows before any live mutation",
    )


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        escaped = [str(cell).replace("\n", "<br>").replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def render_report(manifest: dict[str, Any]) -> str:
    runs: dict[str, dict[str, Any]] = manifest["runs"]
    mac = manifest["mac"]
    rows: list[list[object]] = []
    for key in ("v2059", "v2081", "v2083", "v2091"):
        run = runs[key]
        server = run["server_check"]
        mcfg = run["mcfg"]
        rows.append([
            key.upper(),
            run["label"],
            run["rollback_ok"],
            run["per_mgr_ok"],
            run["wlan_pd_up_ts"],
            server["monotonic_ms"],
            server["payload"],
            run["server_after_per_mgr_ms"],
            run["server_after_wlan_pd_ms"],
            run["ota"]["index"] >= 0,
            run["tftp_ota"],
            mcfg["monotonic_ms"],
            mcfg["payload"],
            run["mcfg_after_server_ms"],
            run["tftp_wlanmdsp"],
            run["fw_ready"],
            run["wlan0"],
        ])
    return "\n".join([
        "# Native Init V2094 MAC Closed Post-Server-Check Timing",
        "",
        "## Summary",
        "",
        "- Cycle: `V2094`",
        "- Type: host-only refinement over existing rollback-verified native captures.",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{rel(OUT_DIR)}`",
        "",
        "## MAC Falsifier",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["real_sysfs_mac_addr", mac["real_sysfs"]],
                ["mac_addr", f"exists={mac['mac_addr_exists']} writable={mac['mac_addr_writable']} mode={mac['mac_addr_mode']} fs={mac['mac_addr_fs_type']}"],
                [".mac.info", f"exists={mac['mac_info_exists']} readable={mac['mac_info_readable']} writable={mac['mac_info_writable']} bytes={mac['mac_info_bytes']}"],
                ["macloader_trace", f"runtime_traced={mac['runtime_traced']} records={mac['records_seen']}"],
                ["macloader_access", f"mac_info_read={mac['mac_info_read']} mac_addr_open={mac['mac_addr_open']} mac_addr_write={mac['mac_addr_write']} shape={mac['mac_addr_write_shape']}"],
                ["kernel_assign", f"icnss_assigning_mac_line={mac['mac_assigned']}"],
            ],
        ),
        "",
        "## TFTP Timing",
        "",
        markdown_table(
            [
                "run",
                "label",
                "rollback",
                "per_mgr",
                "wlan_pd_s",
                "server_ms",
                "server_payload",
                "server_after_per_mgr_ms",
                "server_after_wlan_pd_ms",
                "ota_file",
                "ota_log",
                "mcfg_ms",
                "mcfg_payload",
                "mcfg_after_server_ms",
                "wlanmdsp",
                "fw_ready",
                "wlan0",
            ],
            rows,
        ),
        "",
        "## Interpretation",
        "",
        "- `/sys/wifi/mac_addr` is the real sysfs node and `.mac.info` is readable, but `macloader` never reads the MAC source or writes the kernel node; there is no `icnss: Assigning MAC from Macloader` proof.",
        "- This closes MAC as a bounded falsifier for this producer gate. Even a later successful MAC assign feeds `cnss_utils`/HDD at netdev creation after `FW_READY`, so it is downstream of the missing `wlanmdsp` producer branch.",
        "- The native `server_check.txt=hello` transition is real, but in these current captures it is first visible after `wlan_pd` UP, not in Android's pre-`wlanmdsp` bootstrap order.",
        "- Native then never shows `ota_firewall/ruleset` or `wlanmdsp.mbn`; `mcfg.tmp` remains later/noise, not the initial WLAN-PD firmware-fetch trigger.",
        "",
        "## Next Gate",
        "",
        "- Do not spend more cycles on MAC/macloader, `server_check` reachability, AP PerMgr/pm-service/rild, mcfg readback, or SDX50M/PCIe/eSoC.",
        "- Next live unit should target the modem-internal state before Android's pre-spawn TFTP branch: why native reaches a post-UP `server_check` write but never issues the Android-order `ota_firewall/ruleset` and `wlanmdsp.mbn` requests.",
        "",
        "## Inputs",
        "",
        markdown_table(["run", "manifest", "helper"], [[key, runs[key]["manifest"], runs[key]["helper"]] for key in ("v2059", "v2081", "v2083", "v2091")]),
        "",
        "## Related Reports",
        "",
        f"- Android ordering reference: `{rel(ANDROID_DIFF)}`",
        f"- MAC source proof: `{rel(V2091_REPORT)}`",
        f"- Server-check correction: `{rel(V2093_REPORT)}`",
        "",
        "## Safety",
        "",
        "- Host-only parse/report generation; no flash, reboot, adb mutation, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, DIAG, strace, QRTR matrix, QMI send, tftp ptrace, eSoC/PCIe/GDSC/PMIC/GPIO path, firmware/partition write, or `sda29` write.",
        "",
    ])


def main() -> int:
    required = [*INPUTS.values(), ANDROID_DIFF, V2091_REPORT, V2093_REPORT]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"missing required evidence: {', '.join(missing)}")
    runs = {key: collect_run(key, path) for key, path in INPUTS.items()}
    mac = mac_summary(load_json(INPUTS["v2091"]))
    label, passed, reason = classify(runs, mac)
    manifest = {
        "cycle": "V2094",
        "decision": f"v2094-{label}-host-{'pass' if passed else 'review'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "mac": mac,
        "runs": runs,
        "report": rel(REPORT_PATH),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(f"decision={manifest['decision']}")
    print(f"report={rel(REPORT_PATH)}")
    print(f"manifest={rel(MANIFEST_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
