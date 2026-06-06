#!/usr/bin/env python3
"""V1684 host-only classifier for the WLAN-PD pre-CNSS PM surface gap."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table
from a90harness.evidence import write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1684-wlan-pd-pm-surface-classifier"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1684_WLAN_PD_PM_SURFACE_CLASSIFIER_2026-06-02.md"
NEXT_WORK = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

V1681 = REPO_ROOT / "tmp" / "wifi" / "v1681-wlan-pd-wlfw-trigger-delta-classifier" / "manifest.json"
V1683 = REPO_ROOT / "tmp" / "wifi" / "v1683-wlan-pd-service-window-handoff"


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


def write_text(path: Path, text: str) -> None:
    write_private_text(path, text)


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text.strip():
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def positive_count(value: Any) -> bool:
    try:
        return int(str(value)) > 0
    except (TypeError, ValueError):
        return boolish(value)


def match(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is not None


def extract_v1681() -> dict[str, Any]:
    manifest = load_json(V1681)
    android = manifest.get("android_good") if isinstance(manifest.get("android_good"), dict) else {}
    boottime = android.get("boottime_s") if isinstance(android.get("boottime_s"), dict) else {}
    pre_cnss = android.get("pre_cnss_order") if isinstance(android.get("pre_cnss_order"), dict) else {}
    counts = android.get("counts") if isinstance(android.get("counts"), dict) else {}

    required_pm_keys = {
        "ro.boottime.vendor.per_proxy_helper": "pm_proxy_helper",
        "ro.boottime.vendor.per_mgr": "per_mgr",
        "ro.boottime.vendor.per_proxy": "per_proxy",
    }
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "android_positive_wlfw_chain": positive_count(counts.get("cnss_wlfw_start"))
        and positive_count(counts.get("cnss_wlfw_service_request"))
        and positive_count(counts.get("wlan0")),
        "android_pm_pre_cnss": {name: bool(pre_cnss.get(key)) for key, name in required_pm_keys.items()},
        "android_pm_boottime_s": {name: boottime.get(key) for key, name in required_pm_keys.items()},
        "cnss_daemon_boottime_s": boottime.get("ro.boottime.cnss-daemon"),
        "android_required_pm_all_before_cnss": all(bool(pre_cnss.get(key)) for key in required_pm_keys),
        "evidence": rel(V1681),
    }


def extract_v1683() -> dict[str, Any]:
    manifest = load_json(V1683 / "manifest.json")
    gate = manifest.get("gate") if isinstance(manifest.get("gate"), dict) else {}
    helper = read_text(V1683 / "test-v1393-helper-result.stdout.txt")

    pm_proxy_helper_started = match(helper, r"wifi_hal_composite_start\.child\.per_proxy_helper\.child_started=1")
    per_mgr_started = match(helper, r"wifi_hal_composite_start\.child\.per_mgr\.child_started=1")
    per_proxy_started = match(helper, r"wifi_hal_composite_start\.child\.per_proxy\.child_started=1")
    mdm_helper_started = match(helper, r"wifi_hal_composite_start\.child\.mdm_helper\.child_started=1")
    wifi_hal_started = match(helper, r"wifi_hal_composite_start\.child\.wifi_hal_(legacy|ext)\.child_started=1")
    wificond_started = match(helper, r"wifi_hal_composite_start\.child\.wificond\.child_started=1")
    esoc_subsys = "subsys_esoc0_open_attempted=1" in helper
    forced_rc1 = any(
        marker in helper
        for marker in (
            "forced_rc1_attempted=1",
            "corrected_rc1_enumerate.attempted=1",
            "pid1_rc1_watcher_requested=1",
            "pid1_rc1_window_sampler_requested=1",
        )
    )
    property_requests = re.findall(r"wifi_hal_composite_start\.property_service_shim\.request\.\d+\.name=([^\n]+)", helper)

    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "label": gate.get("label", ""),
        "old_firmware_serve_label": gate.get("old_firmware_serve_label", ""),
        "rollback_ok": bool(gate.get("rollback_ok")),
        "subsys_modem_holder_opened": gate.get("subsys_modem_holder_opened") == "1",
        "tftp_running": gate.get("tftp_running") == "1",
        "cnss_daemon_started": gate.get("cnss_daemon_started") == "1",
        "wlfw_start_seen": gate.get("wlfw_start_seen") == "1",
        "wlfw_service_request_seen": gate.get("wlfw_service_request_seen") == "1",
        "wlfw_service69_seen": gate.get("wlfw_service69_seen") == "1",
        "requested_wlanmdsp": gate.get("requested_wlanmdsp") == "1",
        "pm_proxy_helper_started": pm_proxy_helper_started,
        "per_mgr_started": per_mgr_started,
        "per_proxy_started": per_proxy_started,
        "pm_trio_absent": not (pm_proxy_helper_started or per_mgr_started or per_proxy_started),
        "mdm_helper_started": mdm_helper_started,
        "wifi_hal_started": wifi_hal_started,
        "wificond_started": wificond_started,
        "esoc_subsys_or_manual_rc1_seen": esoc_subsys or forced_rc1,
        "property_requests": property_requests,
        "evidence": rel(V1683),
    }


def decide(v1681: dict[str, Any], v1683: dict[str, Any]) -> tuple[str, bool, str, str, dict[str, bool]]:
    checks = {
        "v1681_positive_android_wlfw_chain": v1681["pass"] and v1681["android_positive_wlfw_chain"],
        "android_pm_trio_before_cnss": v1681["android_required_pm_all_before_cnss"],
        "v1683_valid_single_label": v1683["pass"] and v1683["label"] == "service-window-still-no-wlfw",
        "v1683_internal_modem_route_intact": v1683["subsys_modem_holder_opened"] and v1683["tftp_running"],
        "v1683_cnss_started_no_wlfw": v1683["cnss_daemon_started"]
        and not v1683["wlfw_start_seen"]
        and not v1683["wlfw_service_request_seen"]
        and not v1683["wlfw_service69_seen"],
        "v1683_pm_trio_absent": v1683["pm_trio_absent"],
        "v1683_no_esoc_or_rc1": not v1683["esoc_subsys_or_manual_rc1_seen"],
        "v1683_no_hal_wificond_mdm_helper": not v1683["wifi_hal_started"]
        and not v1683["wificond_started"]
        and not v1683["mdm_helper_started"],
    }
    if all(checks.values()):
        return (
            "v1684-select-wlan-pd-pm-trio-source-build",
            True,
            "V1683 preserved the internal-modem firmware-serve route and started cnss-daemon, but still lacked wlfw_start; Android-good has pm_proxy_helper, per_mgr, and per_proxy before cnss-daemon, and V1683 did not start that PM trio.",
            "Build the next rollbackable test-boot source unit with the V1683 internal-modem route plus pm_proxy_helper/per_mgr/per_proxy before cnss-daemon, while keeping mdm_helper, /dev/subsys_esoc0, forced RC1, Wi-Fi HAL, wificond, scan/connect, credentials, DHCP/routes, and external ping disabled.",
            checks,
        )
    return (
        "v1684-input-evidence-incomplete",
        False,
        "Required V1681/V1683 predicates did not all hold; do not design a live PM-surface gate from weak evidence.",
        "Repair host evidence selection before any new build or live mutation.",
        checks,
    )


def render(result: dict[str, Any]) -> str:
    v1681 = result["v1681"]
    v1683 = result["v1683"]
    pm_rows = [
        [name, v1681["android_pm_boottime_s"].get(name), v1681["android_pm_pre_cnss"].get(name)]
        for name in ("pm_proxy_helper", "per_mgr", "per_proxy")
    ]
    native_rows = [
        ["label", v1683["label"]],
        ["legacy firmware-serve label", v1683["old_firmware_serve_label"]],
        ["subsys_modem holder opened", v1683["subsys_modem_holder_opened"]],
        ["tftp running", v1683["tftp_running"]],
        ["cnss-daemon started", v1683["cnss_daemon_started"]],
        ["wlfw_start seen", v1683["wlfw_start_seen"]],
        ["wlfw_service_request seen", v1683["wlfw_service_request_seen"]],
        ["WLFW service 69 seen", v1683["wlfw_service69_seen"]],
        ["requested wlanmdsp", v1683["requested_wlanmdsp"]],
        ["pm_proxy_helper started", v1683["pm_proxy_helper_started"]],
        ["per_mgr started", v1683["per_mgr_started"]],
        ["per_proxy started", v1683["per_proxy_started"]],
        ["mdm_helper started", v1683["mdm_helper_started"]],
        ["Wi-Fi HAL started", v1683["wifi_hal_started"]],
        ["wificond started", v1683["wificond_started"]],
        ["eSoC/forced RC1 marker", v1683["esoc_subsys_or_manual_rc1_seen"]],
        ["property requests", ", ".join(v1683["property_requests"])],
    ]
    check_rows = [[key, value] for key, value in result["checks"].items()]
    return "\n".join(
        [
            "# Native Init V1684 WLAN-PD PM Surface Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1684`",
            "- Type: host-only classifier",
            f"- Decision: `{result['decision']}`",
            f"- Result: {'PASS' if result['pass'] else 'FAIL'}",
            f"- Reason: {result['reason']}",
            f"- Next: {result['next_step']}",
            f"- Evidence: `{rel(OUT_DIR)}`",
            "",
            "## Android-good PM Surface",
            "",
            markdown_table(["service", "boottime_s", "before cnss-daemon"], pm_rows),
            "",
            "## Native V1683 Surface",
            "",
            markdown_table(["signal", "value"], native_rows),
            "",
            "## Checks",
            "",
            markdown_table(["check", "value"], check_rows),
            "",
            "## Interpretation",
            "",
            "- V1683 closed the service-manager-only experiment: service managers plus the internal-modem holder were not sufficient for `cnss-daemon wlfw_start`.",
            "- Android-good starts `pm_proxy_helper`, `per_mgr`, and `per_proxy` before `cnss-daemon`; V1683 did not start any of them.",
            "- The next aligned source/build unit is therefore PM-trio-only augmentation of the V1683 route, not MSA/BDF, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or the stopped eSoC/RC1 track.",
            "",
            "## Next Gate Contract",
            "",
            "- Source/build-only first.",
            "- Preserve the V1683 internal-modem WLAN-PD firmware-serve route and `/dev/subsys_modem` holder.",
            "- Add `pm_proxy_helper`, `per_mgr`, and `per_proxy` before `cnss-daemon`; classify whether this reaches `wlfw_start` or only changes PM lifecycle evidence.",
            "- Keep `mdm_helper`, `/dev/subsys_esoc0`, raw eSoC ioctls, forced RC1, fake-ONLINE, Wi-Fi HAL, `wificond`, scan/connect, credentials, DHCP/routes, and external ping disabled.",
            "- Stop after one live label if the source/build unit is later approved/run.",
            "",
            "## Inputs",
            "",
            f"- V1681: `{v1681['evidence']}`",
            f"- V1683: `{v1683['evidence']}`",
            "",
            "## Safety",
            "",
            "- Host-only classifier. No device command, daemon start, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, boot image write, firmware write, or partition write occurred.",
            "",
        ]
    )


def append_next_work(result: dict[str, Any]) -> None:
    marker = "## V1684 WLAN-PD PM Surface Classifier (2026-06-02)"
    section = f"""

{marker}

- V1684 completed a host-only classifier after V1683.

  Result:

  - decision: `{result['decision']}`;
  - V1683 service-manager + internal-modem route remained valid but did not
    reach `wlfw_start`, `wlfw_service_request`, WLFW service 69, or
    `wlanmdsp.mbn` request;
  - Android-good evidence has `pm_proxy_helper`, `per_mgr`, and `per_proxy`
    before `cnss-daemon`;
  - V1683 did not start `pm_proxy_helper`, `per_mgr`, or `per_proxy`;
  - no `mdm_helper`, `/dev/subsys_esoc0`, forced RC1, Wi-Fi HAL, `wificond`,
    scan/connect, credentials, DHCP/routes, or external ping appeared in V1683.

  Next work:

  - V1685 should be source/build-only first;
  - preserve the V1683 WLAN-PD internal-modem route and `/dev/subsys_modem`
    holder;
  - add only `pm_proxy_helper`, `per_mgr`, and `per_proxy` before
    `cnss-daemon`;
  - keep `mdm_helper`, `/dev/subsys_esoc0`, raw eSoC ioctl, forced RC1,
    fake-ONLINE, Wi-Fi HAL, `wificond`, scan/connect, credentials, DHCP/routes,
    and external ping disabled.

  Report:
  `docs/reports/NATIVE_INIT_V1684_WLAN_PD_PM_SURFACE_CLASSIFIER_2026-06-02.md`.
"""
    existing = read_text(NEXT_WORK)
    if marker in existing:
        prefix = existing[: existing.index(marker)].rstrip()
        write_text(NEXT_WORK, prefix + "\n" + section)
    else:
        write_text(NEXT_WORK, existing.rstrip() + "\n" + section)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    v1681 = extract_v1681()
    v1683 = extract_v1683()
    decision, passed, reason, next_step, checks = decide(v1681, v1683)
    result = {
        "cycle": "V1684",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "v1681": v1681,
        "v1683": v1683,
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
    write_text(OUT_DIR / "manifest.json", manifest)
    write_text(OUT_DIR / "summary.md", report)
    write_text(REPORT_PATH, report)
    append_next_work(result)
    print(json.dumps({"decision": decision, "pass": passed, "report": rel(REPORT_PATH)}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
