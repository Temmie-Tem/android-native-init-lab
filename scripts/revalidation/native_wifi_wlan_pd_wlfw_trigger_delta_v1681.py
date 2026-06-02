#!/usr/bin/env python3
"""V1681 host-only WLAN-PD WLFW-trigger delta classifier."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table
from a90harness.evidence import write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1681-wlan-pd-wlfw-trigger-delta-classifier"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1681_WLAN_PD_WLFW_TRIGGER_DELTA_CLASSIFIER_2026-06-02.md"
NEXT_WORK = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

V1680 = REPO_ROOT / "tmp" / "wifi" / "v1680-wlan-pd-firmware-serve-modem-holder-handoff"
V1331 = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1331-android-sdx50m-timing-handoff"
    / "v1331-android-sdx50m-timing-recapture-run"
    / "manifest.json"
)
V661 = REPO_ROOT / "tmp" / "wifi" / "v661-binder-registration-context-classifier" / "manifest.json"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_bool(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def positive_count(value: Any) -> bool:
    try:
        return int(str(value)) > 0
    except (TypeError, ValueError):
        return as_bool(value)


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def prop_ns_to_seconds(props: dict[str, str], key: str) -> float | None:
    raw = props.get(key)
    if raw is None or not str(raw).isdigit():
        return None
    return int(str(raw)) / 1_000_000_000.0


def before(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left < right


def extract_v1680() -> dict[str, Any]:
    manifest = load_json(V1680 / "manifest.json")
    gate = manifest.get("gate") if isinstance(manifest.get("gate"), dict) else {}
    helper = read_text(V1680 / "test-v1393-helper-result.stdout.txt")
    dmesg = read_text(V1680 / "test-v1393-dmesg.stdout.txt")
    summary = read_text(V1680 / "summary.md")

    cnss_started = (
        "wifi_hal_composite_start.child.cnss_daemon.child_started=1" in helper
        or "wifi_companion_start.child.cnss_daemon" in helper
    )
    cnss_alive_polling = all(
        marker in helper
        for marker in (
            "capture.wifi_hal_composite_cnss_daemon.stall_tasks.count=3",
            "do_sys_poll",
        )
    )
    cnss_vndbinder = "/dev/vndbinder" in helper or "root/dev/vndbinder" in helper
    service_surface_absent = all(
        marker in helper
        for marker in (
            "wifi_companion_start.with_service_manager=0",
            "wifi_companion_start.service_manager_started=0",
            "wifi_companion_start.wificond=0",
        )
    )
    wifi_hal_absent = not first_bool(helper, r"wifi_hal_(legacy|ext).*child_started=1")
    per_mgr_absent = not first_bool(helper, r"child\.per_mgr\.(child_started|exec_attempted)=1")
    per_proxy_absent = not first_bool(helper, r"child\.per_proxy\.(child_started|exec_attempted)=1")

    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "label": gate.get("label", ""),
        "tftp_running": gate.get("tftp_running") == "1",
        "subsys_modem_holder_started": gate.get("subsys_modem_holder_started") == "1",
        "subsys_modem_holder_opened": gate.get("subsys_modem_holder_opened") == "1",
        "requested_wlanmdsp": gate.get("requested_wlanmdsp") == "1",
        "requested_modem": gate.get("requested_modem") == "1",
        "served_wlanmdsp_nonzero": gate.get("served_wlanmdsp_nonzero") == "1",
        "wlfw_service69_seen": gate.get("wlfw_service69_seen") == "1",
        "wlan_pd_uninit": gate.get("wlan_pd_uninit") == "1",
        "mss_loading_seen": first_bool(dmesg, r"4080000\.qcom,mss: modem: loading|modem: loading"),
        "mss_reset_seen": first_bool(dmesg, r"modem: Brought out of reset"),
        "rmt_storage_efs_seen": first_bool(dmesg, r"rmt_storage_open_cb: Processing: Open Request.*modem_fs"),
        "native_wlfw_start_seen": first_bool(dmesg + "\n" + helper, r"wlfw_start: Starting"),
        "native_wlfw_service_request_seen": first_bool(dmesg + "\n" + helper, r"wlfw_service_request"),
        "cnss_daemon_started": cnss_started,
        "cnss_daemon_alive_polling": cnss_alive_polling,
        "cnss_daemon_vndbinder_fd": cnss_vndbinder,
        "service_surface_absent": service_surface_absent,
        "wifi_hal_absent": wifi_hal_absent,
        "wificond_absent": "wifi_companion_start.wificond=0" in helper,
        "per_mgr_absent": per_mgr_absent,
        "per_proxy_absent": per_proxy_absent,
        "summary_has_no_variants_warning": "Do not spin timing/window variants" in summary,
        "evidence": rel(V1680),
    }


def extract_android() -> dict[str, Any]:
    v1331 = load_json(V1331)
    v661 = load_json(V661)
    android_summary = v1331.get("android_summary") if isinstance(v1331.get("android_summary"), dict) else {}
    props = {str(k): str(v) for k, v in (android_summary.get("props") or {}).items()}
    first_times_v1331 = android_summary.get("first_times") if isinstance(android_summary.get("first_times"), dict) else {}
    android_ref = v661.get("android_reference") if isinstance(v661.get("android_reference"), dict) else {}
    first_times_v661 = android_ref.get("first_times") if isinstance(android_ref.get("first_times"), dict) else {}
    counts = android_ref.get("counts") if isinstance(android_ref.get("counts"), dict) else {}
    deltas = android_ref.get("deltas_ms") if isinstance(android_ref.get("deltas_ms"), dict) else {}

    boottime_keys = (
        "ro.boottime.vendor.per_proxy_helper",
        "ro.boottime.vendor.qrtr-ns",
        "ro.boottime.vendor.pd_mapper",
        "ro.boottime.vendor.per_mgr",
        "ro.boottime.vendor.rmt_storage",
        "ro.boottime.vendor.tftp_server",
        "ro.boottime.vendor.per_proxy",
        "ro.boottime.cnss_diag",
        "ro.boottime.vendor.mdm_helper",
        "ro.boottime.cnss-daemon",
    )
    boottime_s = {key: prop_ns_to_seconds(props, key) for key in boottime_keys}
    cnss_daemon_s = boottime_s.get("ro.boottime.cnss-daemon")
    pre_cnss_keys = (
        "ro.boottime.vendor.per_proxy_helper",
        "ro.boottime.vendor.qrtr-ns",
        "ro.boottime.vendor.pd_mapper",
        "ro.boottime.vendor.per_mgr",
        "ro.boottime.vendor.rmt_storage",
        "ro.boottime.vendor.tftp_server",
        "ro.boottime.vendor.per_proxy",
        "ro.boottime.cnss_diag",
    )
    pre_cnss_order = {key: before(boottime_s.get(key), cnss_daemon_s) for key in pre_cnss_keys}
    wlfw_start = as_float(first_times_v661.get("cnss_wlfw_start"))
    wlfw_request = as_float(first_times_v661.get("cnss_wlfw_service_request"))
    wlan_pd = as_float(first_times_v661.get("wlan_pd"))
    qmi_connected = as_float(first_times_v661.get("qmi_server_connected"))
    bdf_regdb = as_float(first_times_v661.get("bdf_regdb"))

    return {
        "decision_v1331": v1331.get("decision", ""),
        "decision_v661": v661.get("decision", ""),
        "pass_v1331": bool(v1331.get("pass")),
        "pass_v661": bool(v661.get("pass")),
        "counts": counts,
        "first_times_v661": first_times_v661,
        "first_times_v1331": first_times_v1331,
        "deltas_ms": deltas,
        "boottime_s": boottime_s,
        "pre_cnss_order": pre_cnss_order,
        "all_pre_cnss_order": all(pre_cnss_order.values()),
        "wlfw_start_before_wlan_pd": before(wlfw_start, wlan_pd),
        "wlfw_start_before_qmi": before(wlfw_start, qmi_connected),
        "wlfw_start_before_bdf": before(wlfw_start, bdf_regdb),
        "wlfw_request_before_wlan_pd": before(wlfw_request, wlan_pd),
        "wlan_pd_before_qmi": before(wlan_pd, qmi_connected),
        "cnss_daemon_to_wlfw_ms": deltas.get("cnss_daemon_netlink_to_wlfw_start"),
        "wlfw_to_wlan_pd_ms": deltas.get("wlfw_start_to_wlan_pd"),
        "evidence_v1331": rel(V1331),
        "evidence_v661": rel(V661),
    }


def decide(native: dict[str, Any], android: dict[str, Any]) -> tuple[str, bool, str, str, dict[str, Any]]:
    v1680_valid = (
        native["pass"]
        and native["label"] == "firmware-not-requested"
        and native["tftp_running"]
        and native["subsys_modem_holder_opened"]
        and native["mss_loading_seen"]
        and native["mss_reset_seen"]
        and native["rmt_storage_efs_seen"]
    )
    native_no_request_no_wlfw = (
        not native["requested_wlanmdsp"]
        and not native["requested_modem"]
        and not native["native_wlfw_start_seen"]
        and not native["native_wlfw_service_request_seen"]
        and not native["wlfw_service69_seen"]
    )
    android_positive_chain = (
        android["pass_v1331"]
        and android["pass_v661"]
        and positive_count(android["counts"].get("cnss_wlfw_start"))
        and positive_count(android["counts"].get("cnss_wlfw_service_request"))
        and positive_count(android["counts"].get("wlan_pd"))
        and positive_count(android["counts"].get("qmi_server_connected"))
        and positive_count(android["counts"].get("bdf_regdb"))
        and positive_count(android["counts"].get("wlan0"))
    )
    android_wlfw_is_upstream = (
        android["wlfw_start_before_wlan_pd"]
        and android["wlfw_start_before_qmi"]
        and android["wlfw_start_before_bdf"]
        and android["wlfw_request_before_wlan_pd"]
    )
    native_cnss_alive_but_trigger_absent = (
        native["cnss_daemon_started"]
        and native["cnss_daemon_alive_polling"]
        and native["cnss_daemon_vndbinder_fd"]
        and not native["native_wlfw_start_seen"]
    )
    v1680_omitted_android_trigger_surface = (
        native["service_surface_absent"]
        and native["wifi_hal_absent"]
        and native["wificond_absent"]
        and native["per_mgr_absent"]
        and native["per_proxy_absent"]
    )
    checks = {
        "v1680_valid_internal_modem_trigger": v1680_valid,
        "native_no_request_no_wlfw": native_no_request_no_wlfw,
        "android_positive_wlfw_chain": android_positive_chain,
        "android_wlfw_upstream_of_wlan_pd": android_wlfw_is_upstream,
        "native_cnss_alive_but_wlfw_trigger_absent": native_cnss_alive_but_trigger_absent,
        "v1680_omitted_android_trigger_surface": v1680_omitted_android_trigger_surface,
        "android_pre_cnss_order_available": android["all_pre_cnss_order"],
    }
    if all(checks.values()):
        return (
            "v1681-cnss-wlfw-start-trigger-surface-selected",
            True,
            "V1680 validly triggers the internal modem and tftp companion path, but Android-good emits cnss-daemon wlfw_start/wlfw_service_request before WLAN-PD/QMI/BDF while V1680's live cnss-daemon never emits those markers.",
            "Next work is a source/build-only no-eSoC WLFW-start trigger-surface gate: preserve the V1680 internal-modem firmware-serve route, add bounded Android pre-CNSS service/provider surface only as needed, and classify cnss-daemon wlfw_start before any firmware/MSA/BDF/scan/connect work.",
            checks,
        )
    return (
        "v1681-input-evidence-incomplete",
        False,
        "One or more required V1680/Android-good evidence predicates were missing; do not design a live gate from weak evidence.",
        "Repair host evidence selection before any live mutation.",
        checks,
    )


def render(result: dict[str, Any]) -> str:
    native = result["native_v1680"]
    android = result["android_good"]
    checks = result["checks"]
    boot_rows = [
        [key, "" if value is None else f"{value:.6f}", "before cnss-daemon" if android["pre_cnss_order"].get(key) else ""]
        for key, value in sorted(android["boottime_s"].items(), key=lambda item: (item[1] is None, item[1] or 0.0))
    ]
    marker_rows = [
        ["cnss_wlfw_start", android["counts"].get("cnss_wlfw_start", 0), android["first_times_v661"].get("cnss_wlfw_start", "")],
        [
            "cnss_wlfw_service_request",
            android["counts"].get("cnss_wlfw_service_request", 0),
            android["first_times_v661"].get("cnss_wlfw_service_request", ""),
        ],
        ["wlan_pd", android["counts"].get("wlan_pd", 0), android["first_times_v661"].get("wlan_pd", "")],
        ["qmi_server_connected", android["counts"].get("qmi_server_connected", 0), android["first_times_v661"].get("qmi_server_connected", "")],
        ["bdf_regdb", android["counts"].get("bdf_regdb", 0), android["first_times_v661"].get("bdf_regdb", "")],
        ["wlan_fw_ready", android["counts"].get("wlan_fw_ready", 0), android["first_times_v661"].get("wlan_fw_ready", "")],
        ["wlan0", android["counts"].get("wlan0", 0), android["first_times_v661"].get("wlan0", "")],
    ]
    native_rows = [
        ["label", native["label"]],
        ["tftp_running", native["tftp_running"]],
        ["subsys_modem_holder_opened", native["subsys_modem_holder_opened"]],
        ["mss_loading_seen", native["mss_loading_seen"]],
        ["mss_reset_seen", native["mss_reset_seen"]],
        ["rmt_storage_efs_seen", native["rmt_storage_efs_seen"]],
        ["requested_wlanmdsp", native["requested_wlanmdsp"]],
        ["requested_modem", native["requested_modem"]],
        ["native_wlfw_start_seen", native["native_wlfw_start_seen"]],
        ["native_wlfw_service_request_seen", native["native_wlfw_service_request_seen"]],
        ["wlfw_service69_seen", native["wlfw_service69_seen"]],
        ["cnss_daemon_started", native["cnss_daemon_started"]],
        ["cnss_daemon_alive_polling", native["cnss_daemon_alive_polling"]],
        ["service_surface_absent", native["service_surface_absent"]],
        ["wifi_hal_absent", native["wifi_hal_absent"]],
        ["wificond_absent", native["wificond_absent"]],
        ["per_mgr_absent", native["per_mgr_absent"]],
        ["per_proxy_absent", native["per_proxy_absent"]],
    ]
    check_rows = [[key, value] for key, value in checks.items()]
    return "\n".join(
        [
            "# Native Init V1681 WLAN-PD WLFW Trigger Delta Classifier",
            "",
            "## Summary",
            "",
            f"- Cycle: `V1681`",
            "- Type: host-only classifier",
            f"- Decision: `{result['decision']}`",
            f"- Result: {'PASS' if result['pass'] else 'FAIL'}",
            f"- Reason: {result['reason']}",
            f"- Next: {result['next_step']}",
            f"- Evidence: `{rel(OUT_DIR)}`",
            "",
            "## Native V1680",
            "",
            markdown_table(["signal", "value"], native_rows),
            "",
            "## Android-good WLFW Chain",
            "",
            markdown_table(["marker", "count", "first_s"], marker_rows),
            "",
            "## Android Pre-CNSS Service Order",
            "",
            markdown_table(["property", "seconds", "classification"], boot_rows),
            "",
            "## Checks",
            "",
            markdown_table(["check", "value"], check_rows),
            "",
            "## Interpretation",
            "",
            "- V1680 is now a valid internal-modem trigger: mss loads, comes out of reset, and `rmt_storage` handles modem EFS.",
            "- The missing request is upstream of tftp serving: no `wlanmdsp.mbn` request appears because native never reaches `cnss-daemon wlfw_start` / `wlfw_service_request`.",
            "- Android-good evidence places `cnss-daemon wlfw_start` before WLAN-PD indication, ICNSS QMI, BDF, FW-ready, and `wlan0`.",
            "- Therefore the next blocker is the pre-WLFW `cnss-daemon` trigger surface, not MSA, BDF, firmware-file mutation, tftp timing, or the stopped eSoC/RC1/MDM2AP track.",
            "",
            "## Next Gate Contract",
            "",
            "- Start source/build-only first.",
            "- Preserve the V1680 internal modem route and companion firmware-serve observation.",
            "- Add only the minimum Android pre-CNSS service/provider surface needed to classify `cnss-daemon wlfw_start`.",
            "- Keep `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, scan/connect, credentials, DHCP/routes, and external ping disabled.",
            "- Do not investigate MSA/BDF or run Wi-Fi connectivity until WLFW service 69 or `wlfw_start` appears.",
            "",
            "## Inputs",
            "",
            f"- V1680: `{native['evidence']}`",
            f"- V1331: `{android['evidence_v1331']}`",
            f"- V661: `{android['evidence_v661']}`",
            "",
            "## Safety",
            "",
            "- Host-only classifier. No device command, live mutation, daemon start, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, boot image write, firmware write, or partition write occurred.",
            "",
        ]
    )


def append_next_work(result: dict[str, Any]) -> None:
    marker = "## V1681 WLAN-PD WLFW Trigger Delta Classifier (2026-06-02)"
    section = f"""

{marker}

- V1681 completed a host-only classifier after the valid V1680 corrected
  firmware-serve gate.

  Result:

  - decision: `{result['decision']}`;
  - V1680 internal modem trigger remains valid: mss loading/reset and
    `rmt_storage` modem EFS activity were present;
  - V1680 `cnss-daemon` was alive/polling but had no `wlfw_start` or
    `wlfw_service_request`;
  - Android-good evidence has `cnss-daemon wlfw_start` before WLAN-PD, ICNSS QMI,
    BDF, FW-ready, and `wlan0`;
  - therefore `firmware-not-requested` is now interpreted as an upstream
    `cnss-daemon` WLFW-start trigger-surface gap, not a tftp timing or MSA/BDF
    problem.

  Next work:

  - V1682 should be source/build-only first;
  - preserve the V1680 internal-modem WLAN-PD route;
  - add only the minimum Android pre-CNSS service/provider surface needed to
    classify `cnss-daemon wlfw_start`;
  - keep `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes,
    eSoC notify, BOOT_DONE spoof, scan/connect, credentials, DHCP/routes, and
    external ping disabled.

  Report:
  `docs/reports/NATIVE_INIT_V1681_WLAN_PD_WLFW_TRIGGER_DELTA_CLASSIFIER_2026-06-02.md`.
"""
    existing = read_text(NEXT_WORK)
    if marker in existing:
        prefix = existing[: existing.index(marker)].rstrip()
        write_private_text(NEXT_WORK, prefix + "\n" + section)
    else:
        write_private_text(NEXT_WORK, existing.rstrip() + "\n" + section)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    native = extract_v1680()
    android = extract_android()
    decision, passed, reason, next_step, checks = decide(native, android)
    result = {
        "cycle": "V1681",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "native_v1680": native,
        "android_good": android,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "firmware_write_executed": False,
        "partition_write_executed": False,
    }
    manifest = json.dumps(result, indent=2, sort_keys=True) + "\n"
    report = render(result)
    write_private_text(OUT_DIR / "manifest.json", manifest)
    write_private_text(OUT_DIR / "summary.md", report)
    write_private_text(REPORT_PATH, report)
    append_next_work(result)
    print(json.dumps({"decision": decision, "pass": passed, "report": rel(REPORT_PATH)}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
