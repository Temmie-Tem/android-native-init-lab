#!/usr/bin/env python3
"""V1351 current-route CNSS/WLFW precondition observer.

Extends the V1345 current SDX50M private-cnss route with a compact helper-side
``cnss_wlfw_pre.*`` summary. This remains a lower readiness classifier only:
no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO
mutation, direct eSoC ioctl, or boot image write.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import native_wifi_current_route_mdm2ap_timing_sampler_live_v1345 as current
import native_wifi_late_per_proxy_response_sampler_live_v1242 as base
import native_wifi_mdm2ap_timing_sampler_live_v1328 as timing

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1351-current-route-cnss-wlfw-precondition-observer-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1351-current-route-cnss-wlfw-precondition-observer-live.txt")
PLAN_OUT_DIR = Path("tmp/wifi/v1351-current-route-cnss-wlfw-precondition-observer-plan")
PLAN_LATEST_POINTER = Path("tmp/wifi/latest-v1351-current-route-cnss-wlfw-precondition-observer-plan.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1351_CURRENT_ROUTE_CNSS_WLFW_PRECONDITION_OBSERVER_LIVE_2026-06-01.md")

HELPER_MARKER = "a90_android_execns_probe v280"
HELPER_SHA256 = "509f7bb1eb599883d337afb167b29e271c3fe238e1bb1205fb9a93229263c278"
PRECONDITION_FLAG = "--pm-observer-current-route-cnss-wlfw-precondition-summary"
PRECONDITION_PREFIX = "cnss_wlfw_pre."


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _int_value(value: Any, fallback: int = 0) -> int:
    return base._int_value(value, fallback)


def _parse_prefixed_lines(text: str, prefix: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        line = raw_line.strip()
        if line.startswith(prefix) and "=" in line:
            key, value = line[len(prefix):].split("=", 1)
            result[key] = value
    return result


def _force_v1351_child_command(original):
    wrapped = current._force_current_route_child_command(original)

    def command(args: Any) -> list[str]:
        result = wrapped(args)
        if PRECONDITION_FLAG not in result:
            result.append(PRECONDITION_FLAG)
        return result

    return command


def configure() -> None:
    current.configure()
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.LATEST_POINTER = LATEST_POINTER
    base.HELPER_MARKER = HELPER_MARKER
    base.HELPER_SHA256 = HELPER_SHA256
    base.CYCLE_LABEL = "v1351"
    base.CYCLE_NAME = "V1351"
    base.SUMMARY_HEADING = "V1351 Current Route CNSS/WLFW Precondition Observer"
    base.EVIDENCE_FILE_PREFIX = "v1351"
    base._force_response_sampler_child_command = _force_v1351_child_command


def _manifest_path() -> Path:
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        return repo_path(PLAN_OUT_DIR / "manifest.json")
    return repo_path(DEFAULT_OUT_DIR / "manifest.json")


def _run_dir() -> Path:
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        return repo_path(PLAN_OUT_DIR)
    return repo_path(DEFAULT_OUT_DIR)


def _read_run_text(manifest: dict[str, Any]) -> str:
    if manifest.get("command") == "plan":
        return ""
    return base._read_run_text(manifest)


def _read_child_script_text(manifest: dict[str, Any]) -> str:
    run_dir = Path(str(manifest.get("_run_dir") or _run_dir()))
    candidate = run_dir / "host/pm-cnss-voter-child-script.txt"
    try:
        return candidate.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _precondition_summary(pre: dict[str, str]) -> dict[str, Any]:
    safety_keys = (
        "safety_wifi_hal_start",
        "safety_scan_connect",
        "safety_credentials",
        "safety_dhcp_route",
        "safety_external_ping",
        "safety_pmic_write",
        "safety_gpio_request",
        "safety_direct_esoc_ioctl",
    )
    return {
        "emitted": bool(pre),
        "begin": _int_value(pre.get("begin"), 0) == 1,
        "end": _int_value(pre.get("end"), 0) == 1,
        "mode": pre.get("mode", ""),
        "sample_interval_ms": _int_value(pre.get("sample_interval_ms"), 0),
        "sample_count": _int_value(pre.get("sample_count"), 0),
        "cnss_daemon_started": _int_value(pre.get("cnss_daemon_started"), 0) == 1,
        "cnss_diag_started": _int_value(pre.get("cnss_diag_started"), 0) == 1,
        "cld80211_seen": _int_value(pre.get("cld80211_seen"), 0) == 1,
        "pm_register_ret": pre.get("pm_register_ret", ""),
        "pm_register_ret_observed": _int_value(pre.get("pm_register_ret_observed"), 0) == 1,
        "pm_connect_ret": pre.get("pm_connect_ret", ""),
        "pm_connect_ret_observed": _int_value(pre.get("pm_connect_ret_observed"), 0) == 1,
        "wlfw_start_seen": _int_value(pre.get("wlfw_start_seen"), 0) == 1,
        "wlfw_service_request_seen": _int_value(pre.get("wlfw_service_request_seen"), 0) == 1,
        "icnss_qmi_seen": _int_value(pre.get("icnss_qmi_seen"), 0) == 1,
        "bdf_seen": _int_value(pre.get("bdf_seen"), 0) == 1,
        "fw_ready_seen": _int_value(pre.get("fw_ready_seen"), 0) == 1,
        "wlan0_seen": _int_value(pre.get("wlan0_seen"), 0) == 1,
        "last_checkpoint": pre.get("last_checkpoint", ""),
        "safety_clear": all(_int_value(pre.get(key), -1) == 0 for key in safety_keys),
        "raw": pre,
    }


def _decide_v1351(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1351-current-route-cnss-wlfw-precondition-plan-ready",
            True,
            "plan-only; no device command or live action executed",
            "deploy helper v280, then run V1351 bounded live precondition observer",
        )

    sampler = manifest.get("response_sampler") or {}
    pre = manifest.get("cnss_wlfw_precondition") or {}
    route = manifest.get("current_route") or {}
    private_cnss = manifest.get("private_cnss_daemon") or {}

    if route.get("precondition_flag_in_child_script") != 1:
        return (
            "v1351-current-route-precondition-flag-missing",
            False,
            "child command did not include the V1351 CNSS/WLFW precondition flag",
            "repair V1351 command injection before live retry",
        )
    if route.get("private_flag_in_child_script") != 1:
        return (
            "v1351-current-route-private-cnss-missing",
            False,
            "child command did not include private cnss-daemon SDX50M flag",
            "repair current-route command injection before live retry",
        )
    if private_cnss.get("bind_rc") != "0" or private_cnss.get("expected_c_string") != "SDX50M":
        return (
            "v1351-current-route-private-cnss-missing",
            False,
            f"private_cnss={private_cnss}",
            "verify /cache/bin/cnss-daemon.sdx50m identity and private bind markers",
        )
    if not sampler.get("timing_emitted") or not sampler.get("timing_end"):
        return (
            "v1351-current-route-timing-missing",
            False,
            "mdm2ap_timing summary did not emit a complete begin/end block",
            "inspect helper stdout before retrying",
        )
    if _int_value(sampler.get("timing_sample_count"), 0) < timing.EXPECTED_MIN_TIMING_SAMPLE_COUNT:
        return (
            "v1351-current-route-short-window",
            False,
            f"timing sample_count={sampler.get('timing_sample_count')}",
            "inspect helper timing window before retrying",
        )
    if not pre.get("emitted") or not pre.get("begin") or not pre.get("end"):
        return (
            "v1351-current-route-cnss-wlfw-precondition-missing",
            False,
            "cnss_wlfw_pre summary did not emit a complete begin/end block",
            "verify helper v280 deploy and V1351 flag injection",
        )
    if not pre.get("safety_clear"):
        return (
            "v1351-current-route-safety-violation",
            False,
            "cnss_wlfw_pre summary reports a forbidden Wi-Fi/network/lower mutation action",
            "stop and audit helper output",
        )

    checkpoint = str(pre.get("last_checkpoint") or "unknown")
    if checkpoint == "wlan0-present":
        return (
            "v1351-current-route-wlan0-present",
            True,
            "current route reached wlan0 inside the bounded precondition observer",
            "capture Wi-Fi active-session surface before scan/connect or external ping",
        )
    return (
        f"v1351-current-route-{checkpoint}",
        True,
        f"current route precondition observer stopped at checkpoint={checkpoint}",
        "classify the next missing prerequisite before PMIC/GPIO/GDSC/eSoC mutation or Wi-Fi HAL bring-up",
    )


def augment_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    run_text = _read_run_text(manifest)
    child_script = _read_child_script_text(manifest)
    private_cnss = _parse_prefixed_lines(run_text, "private_cnss_daemon.")
    pre = _precondition_summary(_parse_prefixed_lines(run_text, PRECONDITION_PREFIX))
    sampler = manifest.get("response_sampler") or {}
    current_route = {
        "private_flag_in_child_script": 1 if current.PRIVATE_CNSS_FLAG in child_script else 0,
        "private_path_in_child_script": 1 if current.PRIVATE_CNSS_PATH in child_script else 0,
        "esoc_dev_node_flag_in_child_script": 1 if current.ESOC_DEV_NODE_FLAG in child_script else 0,
        "precondition_flag_in_child_script": 1 if PRECONDITION_FLAG in child_script else 0,
        "helper_marker": HELPER_MARKER,
        "helper_sha256": HELPER_SHA256,
        "private_cnss_path": current.PRIVATE_CNSS_PATH,
        "private_cnss_sha256": current.PRIVATE_CNSS_SHA256,
        "timing_progress": current._timing_progress(sampler),
        "timing_safety_clear": current._timing_safety_clear(sampler),
    }
    manifest["cycle"] = "v1351"
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["private_cnss_daemon"] = private_cnss
    manifest["cnss_wlfw_precondition"] = pre
    manifest["current_route"] = current_route
    manifest["wifi_hal_start_executed"] = False
    manifest["scan_connect_executed"] = False
    manifest["credential_use_executed"] = False
    manifest["dhcp_route_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["flash_executed"] = False
    manifest["partition_write_executed"] = False
    manifest["reclassified_at"] = _now_iso()
    decision, passed, reason, next_step = _decide_v1351(manifest)
    manifest.update({
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
    })
    return manifest


def _key_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    sampler = manifest.get("response_sampler") or {}
    pre = manifest.get("cnss_wlfw_precondition") or {}
    route = manifest.get("current_route") or {}
    return [
        ["private_flag_in_child_script", route.get("private_flag_in_child_script")],
        ["precondition_flag_in_child_script", route.get("precondition_flag_in_child_script")],
        ["timing_sample_count", sampler.get("timing_sample_count")],
        ["timing_pm_service_powerup_seen", sampler.get("timing_pm_service_powerup_seen")],
        ["pre_emitted", pre.get("emitted")],
        ["pre_sample_count", pre.get("sample_count")],
        ["cnss_daemon_started", pre.get("cnss_daemon_started")],
        ["cnss_diag_started", pre.get("cnss_diag_started")],
        ["cld80211_seen", pre.get("cld80211_seen")],
        ["pm_register_ret", pre.get("pm_register_ret")],
        ["pm_connect_ret", pre.get("pm_connect_ret")],
        ["wlfw_start_seen", pre.get("wlfw_start_seen")],
        ["wlfw_service_request_seen", pre.get("wlfw_service_request_seen")],
        ["icnss_qmi_seen", pre.get("icnss_qmi_seen")],
        ["bdf_seen", pre.get("bdf_seen")],
        ["fw_ready_seen", pre.get("fw_ready_seen")],
        ["wlan0_seen", pre.get("wlan0_seen")],
        ["last_checkpoint", pre.get("last_checkpoint")],
        ["safety_clear", pre.get("safety_clear")],
    ]


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1351 Current Route CNSS/WLFW Precondition Observer Live",
        "",
        "## Summary",
        "",
        "- Cycle: `V1351`",
        "- Type: bounded live lower-readiness precondition observer",
        f"- Decision: `{manifest.get('decision', '')}`",
        f"- Result: {'PASS' if manifest.get('pass') else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1351-current-route-cnss-wlfw-precondition-observer-live/manifest.json`",
        "  - `tmp/wifi/v1351-current-route-cnss-wlfw-precondition-observer-live/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_current_route_cnss_wlfw_precondition_observer_live_v1351.py`",
        f"- Helper: `/cache/bin/a90_android_execns_probe` (`{HELPER_MARKER}`)",
        "",
        "## Key Observations",
        "",
        markdown_table(["field", "value"], _key_rows(manifest)),
        "",
        "## Decision",
        "",
        str(manifest.get("reason", "")),
        "",
        "V1351 remains below Wi-Fi bring-up. It does not start Wi-Fi HAL, scan,",
        "connect, credential handling, DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        str(manifest.get("next_step", "")),
        "",
    ])


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1351 Current Route CNSS/WLFW Precondition Observer",
        "",
        f"- decision: `{manifest.get('decision', '')}`",
        f"- pass: `{manifest.get('pass')}`",
        f"- reason: {manifest.get('reason', '')}",
        f"- next_step: {manifest.get('next_step', '')}",
        "",
        markdown_table(["field", "value"], _key_rows(manifest)),
        "",
    ])


def write_augmented_outputs(manifest: dict[str, Any]) -> None:
    out_dir = _run_dir()
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_summary(manifest))
    if manifest.get("command") == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))


def print_v1351_result(manifest: dict[str, Any]) -> None:
    print(f"v1351_decision: {manifest.get('decision')}")
    print(f"v1351_pass: {manifest.get('pass')}")
    print(f"v1351_reason: {manifest.get('reason')}")
    print(f"v1351_next: {manifest.get('next_step')}")
    print(f"v1351_manifest: {_run_dir() / 'manifest.json'}")


def main() -> int:
    configure()
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        base.DEFAULT_OUT_DIR = PLAN_OUT_DIR
        base.LATEST_POINTER = PLAN_LATEST_POINTER
    base_rc = base.main()
    manifest_path = _manifest_path()
    if not manifest_path.exists():
        return base_rc if base_rc != 0 else 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        return 1
    manifest = augment_manifest(manifest)
    write_augmented_outputs(manifest)
    print_v1351_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
