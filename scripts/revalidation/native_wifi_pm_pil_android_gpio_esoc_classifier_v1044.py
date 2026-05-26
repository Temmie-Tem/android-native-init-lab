#!/usr/bin/env python3
"""V1044 host-only classifier for the PM/PIL blocker with Android GPIO/eSoC timing."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1044-pm-pil-android-gpio-esoc-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1044-pm-pil-android-gpio-esoc-classifier.txt")
DEFAULT_V1043_MANIFEST = Path("tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live/manifest.json")
DEFAULT_V1043_TRANSCRIPT = Path(
    "tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live/native/"
    "mdm-helper-cnss-before-esoc.txt"
)
DEFAULT_V968_MANIFEST = Path("tmp/wifi/v968-android-dmesg-esoc-gpio-timing/manifest.json")
DEFAULT_V1024_MANIFEST = Path("tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json")
DEFAULT_V852_DMESG = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt"
)
DEFAULT_V852_INTERRUPTS = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/interrupts-focus.txt"
)
DEFAULT_V852_GPIO = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/gpio-pinctrl-surface.txt"
)

TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
IRQ_RE = re.compile(
    r"^\s*(?P<irq>\d+):(?P<counts>(?:\s+\d+)+)\s+(?P<controller>\S+)\s+"
    r"(?P<hwirq>\d+)\s+(?P<trigger>\S+)\s+(?P<name>.+?)\s*$"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1043-manifest", type=Path, default=DEFAULT_V1043_MANIFEST)
    parser.add_argument("--v1043-transcript", type=Path, default=DEFAULT_V1043_TRANSCRIPT)
    parser.add_argument("--v968-manifest", type=Path, default=DEFAULT_V968_MANIFEST)
    parser.add_argument("--v1024-manifest", type=Path, default=DEFAULT_V1024_MANIFEST)
    parser.add_argument("--v852-dmesg", type=Path, default=DEFAULT_V852_DMESG)
    parser.add_argument("--v852-interrupts", type=Path, default=DEFAULT_V852_INTERRUPTS)
    parser.add_argument("--v852-gpio", type=Path, default=DEFAULT_V852_GPIO)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"_missing": True, "_path": str(path)}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {"_invalid": True, "_path": str(path)}
    if not isinstance(value, dict):
        return {"_invalid": True, "_path": str(path)}
    value["_path"] = str(path)
    return value


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "pass"}
    return False


def intish(value: Any, default: int = -1) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def dmesg_time(line: str) -> float | None:
    match = TIME_RE.search(line.strip())
    return float(match.group("time")) if match else None


def first_line(text: str, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("$ "):
            continue
        if regex.search(line):
            return {
                "present": True,
                "line_number": line_number,
                "time": dmesg_time(line),
                "line": line,
            }
    return {"present": False, "line_number": None, "time": None, "line": ""}


def selected_lines(text: str, pattern: str, limit: int = 12) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$ "):
            continue
        if regex.search(line):
            lines.append(line)
            if len(lines) >= limit:
                break
    return lines


def first_text_line(text: str, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and regex.search(line):
            return line
    return ""


def key_lines(text: str, patterns: list[str]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        line = first_text_line(text, pattern)
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return lines


def parse_irq(text: str, name_pattern: str) -> dict[str, Any]:
    regex = re.compile(name_pattern, re.IGNORECASE)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not regex.search(line):
            continue
        match = IRQ_RE.search(line)
        if not match:
            continue
        counts = [int(item) for item in match.group("counts").split()]
        return {
            "present": True,
            "irq": int(match.group("irq")),
            "controller": match.group("controller"),
            "hwirq": int(match.group("hwirq")),
            "trigger": match.group("trigger"),
            "name": match.group("name").strip(),
            "count_total": sum(counts),
            "line": line,
        }
    return {"present": False, "count_total": 0, "line": ""}


def contract_from_manifest(manifest: dict[str, Any]) -> dict[str, str]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    contract = helper.get("contract") or {}
    return {str(key): str(value) for key, value in contract.items()}


def extract_v1043(manifest: dict[str, Any], transcript: str) -> dict[str, Any]:
    contract = contract_from_manifest(manifest)
    pm_proxy_helper_lines = key_lines(
        transcript,
        [
            r"Name:\s*pm_proxy_helper",
            r"State:\s*D",
            r"flush_work",
            r"pil_boot",
            r"subsys_powerup",
            r"capture\.wifi_hal_composite_pm_proxy_helper\.fd_links\.count=",
            r"cnss_before_esoc\.pm_proxy_helper_subsys_modem_fd_count=",
            r"cnss_before_esoc\.pm_full_contract_poll_count=",
            r"cnss_before_esoc\.runtime_domain_guard_matched_count=",
        ],
    )
    per_mgr_lines = selected_lines(
        transcript,
        r"Name:\s*pm-service|State:\s*S|per_mgr_subsys_modem_fd_count|vendor_per_mgr",
        limit=10,
    )
    domains = {
        "blocked": boolish(manifest.get("runtime_domain_guard_blocked"))
        or boolish(contract.get("runtime_domain_guard_blocked")),
        "matched_count": intish(
            manifest.get("runtime_domain_guard_matched_count", contract.get("runtime_domain_guard_matched_count"))
        ),
        "pm_proxy_helper": "u:r:per_proxy_helper:s0" in transcript,
        "per_mgr": "u:r:vendor_per_mgr:s0" in transcript,
        "pm_proxy": "u:r:vendor_per_proxy:s0" in transcript,
        "mdm_helper": "u:r:vendor_mdm_helper:s0" in transcript,
    }
    guardrails = {
        "service_manager_start_executed": boolish(manifest.get("service_manager_start_executed"))
        or boolish(contract.get("service_manager_start_executed")),
        "cnss_diag_start_executed": boolish(manifest.get("cnss_diag_start_executed"))
        or boolish(contract.get("cnss_diag_started")),
        "cnss_daemon_start_executed": boolish(manifest.get("cnss_daemon_start_executed"))
        or boolish(contract.get("cnss_daemon_started")),
        "subsys_esoc0_open_attempted": boolish(manifest.get("subsys_esoc0_open_attempted"))
        or boolish(contract.get("subsys_esoc0_open_attempted")),
        "wifi_hal_start_executed": boolish(manifest.get("wifi_hal_start_executed"))
        or boolish(contract.get("wifi_hal_start_executed")),
        "scan_connect_executed": boolish(manifest.get("scan_connect_executed"))
        or boolish(contract.get("scan_connect_linkup")),
        "credential_use_executed": boolish(manifest.get("credential_use_executed"))
        or boolish(contract.get("credentials")),
        "dhcp_route_executed": boolish(manifest.get("dhcp_route_executed"))
        or boolish(contract.get("dhcp_routing")),
        "external_ping_executed": boolish(manifest.get("external_ping_executed"))
        or boolish(contract.get("external_ping")),
        "boot_image_write_executed": boolish(manifest.get("boot_image_write_executed")),
    }
    return {
        "manifest_path": manifest.get("_path", str(DEFAULT_V1043_MANIFEST)),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "cleanup_reboot_executed": boolish(manifest.get("cleanup_reboot_executed")),
        "domains": domains,
        "guardrails": guardrails,
        "pm_actor_starts": {
            "pm_proxy_helper": boolish(manifest.get("pm_proxy_helper_start_executed"))
            or boolish(contract.get("pm_proxy_helper_start_executed")),
            "per_mgr_light": boolish(manifest.get("per_mgr_light_start_executed"))
            or boolish(contract.get("per_mgr_start_attempted")),
            "pm_proxy": boolish(manifest.get("pm_proxy_start_executed"))
            or boolish(contract.get("pm_proxy_start_attempted")),
            "mdm_helper": boolish(manifest.get("mdm_helper_start_executed"))
            or boolish(contract.get("mdm_helper_start_attempted")),
        },
        "fd_contract": {
            "pm_full_contract_seen": boolish(manifest.get("pm_full_contract_seen"))
            or boolish(contract.get("pm_full_contract_seen")),
            "pm_proxy_helper_subsys_modem_fd_count": intish(contract.get("pm_proxy_helper_subsys_modem_fd_count")),
            "per_mgr_subsys_modem_fd_count": intish(contract.get("per_mgr_subsys_modem_fd_count")),
            "mdm_helper_esoc0_fd_seen": boolish(contract.get("mdm_helper_esoc0_fd_seen")),
            "mdm_helper_esoc0_fd_count": intish(contract.get("mdm_helper_esoc0_fd_count")),
            "pm_full_contract_poll_count": intish(contract.get("pm_full_contract_poll_count")),
        },
        "pil_block": {
            "pm_proxy_helper_d_state": "Name:\tpm_proxy_helper" in transcript and "State:\tD" in transcript,
            "wchan_flush_work": "flush_work" in transcript,
            "stack_pil_boot": "pil_boot" in transcript,
            "stack_subsys_powerup": "subsys_powerup" in transcript,
            "postflight_safe": boolish(contract.get("pm_proxy_helper.postflight_safe")),
            "result": contract.get("result", ""),
            "selected_lines": pm_proxy_helper_lines,
        },
        "per_mgr_selected_lines": per_mgr_lines,
    }


def event_from_v968(classification: dict[str, Any], name: str) -> dict[str, Any]:
    value = ((classification.get("events") or {}).get(name) or {})
    if not isinstance(value, dict):
        return {"present": False, "time": None, "line": ""}
    return {
        "present": boolish(value.get("present")),
        "time": value.get("time"),
        "line": value.get("line", ""),
    }


def extract_android(v968: dict[str, Any], v1024: dict[str, Any], v852_dmesg: str, v852_interrupts: str, v852_gpio: str) -> dict[str, Any]:
    v968_classification = v968.get("classification") or {}
    v1024_classification = v1024.get("classification") or {}
    early_fd = ((v1024_classification.get("early") or {}).get("fd") or {})
    late_chain = ((v1024_classification.get("late") or {}).get("chain") or {})
    events = {
        name: event_from_v968(v968_classification, name)
        for name in (
            "ext_mdm_probe",
            "gpio135_request",
            "gpio142_request",
            "mdm_helper_start",
            "cnss_daemon_start",
            "wlfw_start",
            "esoc0_subsystem_get",
            "wlan_pd_indication",
            "icnss_qmi_connected",
            "bdf_regdb",
            "bdf_bdwlan",
            "fw_ready",
            "wlan0_event",
        )
    }
    answers = v968_classification.get("answers") or {}
    gpio = v968_classification.get("gpio") or {}
    v852_events = {
        "pcie_link_initialized": first_line(v852_dmesg, r"msm_pcie_enable: PCIe RC1 link initialized"),
        "wlan_pd_indication": first_line(v852_dmesg, r"msm/modem/wlan_pd"),
        "bdf_regdb": first_line(v852_dmesg, r"BDF file\s*:\s*regdb\.bin"),
        "bdf_bdwlan": first_line(v852_dmesg, r"BDF file\s*:\s*bdwlan\.bin"),
        "sysmon_esoc0": first_line(v852_dmesg, r"esoc0's SSCTL service"),
    }
    gpio_lines = selected_lines(v852_gpio, r"gpio135|gpio142|gpio9|pin 135|pin 142|pin 7|GPIO_DEBUG readable", limit=18)
    return {
        "v968_manifest_path": v968.get("_path", str(DEFAULT_V968_MANIFEST)),
        "v968_decision": v968_classification.get("decision", ""),
        "v968_pass": boolish(v968_classification.get("pass")),
        "v1024_manifest_path": v1024.get("_path", str(DEFAULT_V1024_MANIFEST)),
        "v1024_decision": v1024.get("decision", ""),
        "v1024_pass": boolish(v1024.get("pass")),
        "pm_fd_contract": {
            "pm_proxy_helper_subsys_modem_fd": boolish(early_fd.get("pm_proxy_helper_subsys_modem_fd")),
            "pm_service_subsys_modem_fd": boolish(early_fd.get("pm_service_subsys_modem_fd")),
            "mdm_helper_esoc0_fd": boolish(early_fd.get("mdm_helper_esoc0_fd")),
            "wlfw_chain": boolish(late_chain.get("wlfw_chain")),
        },
        "events": events,
        "v852_events": v852_events,
        "gpio": {
            "gpio135_level_snapshot": gpio.get("gpio135_level_snapshot"),
            "gpio142_level_snapshot": gpio.get("gpio142_level_snapshot"),
            "ap2mdm_gpio135_assert_time": answers.get("ap2mdm_gpio135_assert_time"),
            "pmic_gpio9_deassert_time": answers.get("pmic_gpio9_deassert_time"),
            "pcie_marker_time": answers.get("pcie_marker_time"),
            "mdm2ap_irq_v852": parse_irq(v852_interrupts, r"\bmdm status\b"),
            "selected_lines": gpio_lines,
        },
        "selected_dmesg_lines": selected_lines(
            v852_dmesg,
            r"__subsystem_get.*esoc0|msm_pcie_enable|wlan_pd|BDF file|sysmon-qmi|wlfw_start|wlan0",
            limit=22,
        ),
    }


def all_values_true(values: dict[str, bool]) -> bool:
    return all(values.values())


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1043_manifest = load_json(args.v1043_manifest)
    v1043_transcript = read_text(args.v1043_transcript)
    v968_manifest = load_json(args.v968_manifest)
    v1024_manifest = load_json(args.v1024_manifest)
    v852_dmesg = read_text(args.v852_dmesg)
    v852_interrupts = read_text(args.v852_interrupts)
    v852_gpio = read_text(args.v852_gpio)

    native = extract_v1043(v1043_manifest, v1043_transcript)
    android = extract_android(v968_manifest, v1024_manifest, v852_dmesg, v852_interrupts, v852_gpio)

    native_domain_parity_fixed = (
        native["pass"]
        and native["decision"] == "v1041-pm-full-contract-missing-no-open"
        and not native["domains"]["blocked"]
        and native["domains"]["matched_count"] == 4
        and all(
            native["domains"][name]
            for name in ("pm_proxy_helper", "per_mgr", "pm_proxy", "mdm_helper")
        )
    )
    native_pm_actor_order_executed = all_values_true(native["pm_actor_starts"])
    native_pm_fd_missing = (
        not native["fd_contract"]["pm_full_contract_seen"]
        and native["fd_contract"]["pm_proxy_helper_subsys_modem_fd_count"] == 0
        and native["fd_contract"]["per_mgr_subsys_modem_fd_count"] == 0
        and native["fd_contract"]["mdm_helper_esoc0_fd_seen"]
        and native["fd_contract"]["pm_full_contract_poll_count"] > 0
    )
    native_pil_stack_block = (
        native["pil_block"]["pm_proxy_helper_d_state"]
        and native["pil_block"]["wchan_flush_work"]
        and native["pil_block"]["stack_pil_boot"]
        and native["pil_block"]["stack_subsys_powerup"]
        and not native["pil_block"]["postflight_safe"]
        and native["pil_block"]["result"] == "reboot-required"
        and native["cleanup_reboot_executed"]
    )
    native_guardrails_clean = not any(native["guardrails"].values())

    android_pm_fd_contract_positive = (
        android["v1024_pass"]
        and android["v1024_decision"] == "v1024-android-pm-esoc-fd-contract-captured"
        and all(android["pm_fd_contract"].values())
    )
    android_gpio_esoc_order_positive = (
        android["v968_pass"]
        and boolish(android["events"]["ext_mdm_probe"]["present"])
        and boolish(android["events"]["gpio135_request"]["present"])
        and boolish(android["events"]["gpio142_request"]["present"])
        and boolish(android["events"]["esoc0_subsystem_get"]["present"])
        and boolish(android["events"]["wlan_pd_indication"]["present"])
        and boolish(android["events"]["icnss_qmi_connected"]["present"])
        and boolish(android["events"]["bdf_regdb"]["present"])
        and boolish(android["events"]["bdf_bdwlan"]["present"])
        and boolish(android["events"]["fw_ready"]["present"])
        and boolish(android["events"]["wlan0_event"]["present"])
    )
    android_pcie_positive = boolish(android["v852_events"]["pcie_link_initialized"]["present"])
    gpio_transition_timing_unproven = (
        android["gpio"]["ap2mdm_gpio135_assert_time"] is None
        and android["gpio"]["pmic_gpio9_deassert_time"] is None
    )

    checks = {
        "v1043_input_present": not v1043_manifest.get("_missing") and not v1043_manifest.get("_invalid"),
        "v1043_transcript_present": bool(v1043_transcript),
        "v968_input_present": not v968_manifest.get("_missing") and not v968_manifest.get("_invalid"),
        "v1024_input_present": not v1024_manifest.get("_missing") and not v1024_manifest.get("_invalid"),
        "native_domain_parity_fixed": native_domain_parity_fixed,
        "native_pm_actor_order_executed": native_pm_actor_order_executed,
        "native_pm_fd_missing": native_pm_fd_missing,
        "native_pil_stack_block": native_pil_stack_block,
        "native_guardrails_clean": native_guardrails_clean,
        "android_pm_fd_contract_positive": android_pm_fd_contract_positive,
        "android_gpio_esoc_order_positive": android_gpio_esoc_order_positive,
        "android_pcie_positive": android_pcie_positive,
        "gpio_transition_timing_unproven": gpio_transition_timing_unproven,
    }

    required = {key: value for key, value in checks.items() if key != "gpio_transition_timing_unproven"}
    if all_values_true(required):
        decision = "v1044-pm-pil-blocker-android-gpio-esoc-classified"
        passed = True
        reason = (
            "V1043 fixed PM SELinux context parity but pm_proxy_helper blocks in "
            "flush_work/pil_boot/subsys_powerup before /dev/subsys_modem fd formation; "
            "Android evidence proves the PM fd, eSoC GPIO, PCIe, WLAN-PD, BDF, FW-ready, and wlan0 positive path."
        )
        route = "v1045-pm-pil-prerequisite-delta"
        next_step = (
            "Classify the Android-only prerequisite that lets pm_proxy_helper complete PIL/subsys_powerup. "
            "Do not blind-retry PM full-contract; use a bounded Android dmesg/Magisk sampler only if exact GPIO level timing becomes required."
        )
    else:
        missing = ", ".join(name for name, ok in required.items() if not ok)
        decision = "v1044-pm-pil-android-gpio-esoc-inputs-incomplete"
        passed = False
        reason = f"required evidence missing or contradictory: {missing}"
        route = "repair-existing-evidence-or-run-bounded-android-capture"
        next_step = (
            "Repair the missing host-only evidence first; if Android GPIO transition timing is the missing piece, "
            "run a bounded adb/Magisk sampler before native live retry."
        )

    return {
        "decision": decision,
        "pass": passed,
        "route": route,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "native": native,
        "android": android,
        "guardrails": {
            "device_contact_executed": False,
            "device_mutations": False,
            "actor_start_executed": False,
            "daemon_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_image_write_executed": False,
        },
    }


def render_event_rows(android: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for name, event in android["events"].items():
        rows.append([name, event["present"], event["time"], event["line"][:120]])
    rows.append(
        [
            "v852_pcie_link_initialized",
            android["v852_events"]["pcie_link_initialized"]["present"],
            android["v852_events"]["pcie_link_initialized"]["time"],
            android["v852_events"]["pcie_link_initialized"]["line"][:120],
        ]
    )
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    native = classification["native"]
    android = classification["android"]
    checks = classification["checks"]
    native_rows = [
        ["decision", native["decision"]],
        ["runtime_domain_guard_blocked", native["domains"]["blocked"]],
        ["runtime_domain_guard_matched_count", native["domains"]["matched_count"]],
        ["pm_actor_starts", native["pm_actor_starts"]],
        ["pm_full_contract_seen", native["fd_contract"]["pm_full_contract_seen"]],
        ["pm_proxy_helper_subsys_modem_fd_count", native["fd_contract"]["pm_proxy_helper_subsys_modem_fd_count"]],
        ["per_mgr_subsys_modem_fd_count", native["fd_contract"]["per_mgr_subsys_modem_fd_count"]],
        ["mdm_helper_esoc0_fd_seen", native["fd_contract"]["mdm_helper_esoc0_fd_seen"]],
        ["pm_proxy_helper_d_state", native["pil_block"]["pm_proxy_helper_d_state"]],
        ["wchan_flush_work", native["pil_block"]["wchan_flush_work"]],
        ["stack_pil_boot", native["pil_block"]["stack_pil_boot"]],
        ["stack_subsys_powerup", native["pil_block"]["stack_subsys_powerup"]],
        ["cleanup_reboot_executed", native["cleanup_reboot_executed"]],
    ]
    android_rows = [
        ["v1024_decision", android["v1024_decision"]],
        ["pm_proxy_helper_subsys_modem_fd", android["pm_fd_contract"]["pm_proxy_helper_subsys_modem_fd"]],
        ["pm_service_subsys_modem_fd", android["pm_fd_contract"]["pm_service_subsys_modem_fd"]],
        ["mdm_helper_esoc0_fd", android["pm_fd_contract"]["mdm_helper_esoc0_fd"]],
        ["wlfw_chain", android["pm_fd_contract"]["wlfw_chain"]],
        ["v968_decision", android["v968_decision"]],
        ["gpio135_snapshot", android["gpio"]["gpio135_level_snapshot"]],
        ["gpio142_snapshot", android["gpio"]["gpio142_level_snapshot"]],
        ["gpio135_assert_time", android["gpio"]["ap2mdm_gpio135_assert_time"]],
        ["pmic_gpio9_deassert_time", android["gpio"]["pmic_gpio9_deassert_time"]],
        ["v852_mdm_status_irq_total", android["gpio"]["mdm2ap_irq_v852"]["count_total"]],
    ]
    return "\n".join(
        [
            "# V1044 PM/PIL Android GPIO/eSoC Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- route: `{classification['route']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "value"], [[key, value] for key, value in checks.items()]),
            "",
            "## Native V1043",
            "",
            markdown_table(["item", "value"], native_rows),
            "",
            "## Android Positive Controls",
            "",
            markdown_table(["item", "value"], android_rows),
            "",
            "## Android Timeline",
            "",
            markdown_table(["event", "present", "time", "line"], render_event_rows(android)),
            "",
            "## Native Selected Lines",
            "",
            "\n".join(f"- `{line}`" for line in native["pil_block"]["selected_lines"]) or "- none",
            "",
            "## Android Selected Dmesg Lines",
            "",
            "\n".join(f"- `{line}`" for line in android["selected_dmesg_lines"]) or "- none",
            "",
            "## Android GPIO Lines",
            "",
            "\n".join(f"- `{line}`" for line in android["gpio"]["selected_lines"]) or "- none",
            "",
        ]
    )


def plan_classification() -> dict[str, Any]:
    return {
        "decision": "v1044-pm-pil-android-gpio-esoc-classifier-plan-ready",
        "pass": True,
        "route": "host-only-v1043-v968-v1024-v852-comparison",
        "reason": "plan-only; no live device contact required",
        "next_step": "run classifier over existing native and Android evidence",
        "checks": {},
        "native": {
            "decision": "",
            "domains": {"blocked": False, "matched_count": 0},
            "pm_actor_starts": {},
            "fd_contract": {
                "pm_full_contract_seen": False,
                "pm_proxy_helper_subsys_modem_fd_count": 0,
                "per_mgr_subsys_modem_fd_count": 0,
                "mdm_helper_esoc0_fd_seen": False,
            },
            "pil_block": {
                "pm_proxy_helper_d_state": False,
                "wchan_flush_work": False,
                "stack_pil_boot": False,
                "stack_subsys_powerup": False,
                "selected_lines": [],
            },
            "cleanup_reboot_executed": False,
        },
        "android": {
            "events": {},
            "v852_events": {"pcie_link_initialized": {"present": False, "time": None, "line": ""}},
            "pm_fd_contract": {},
            "gpio": {
                "gpio135_level_snapshot": None,
                "gpio142_level_snapshot": None,
                "ap2mdm_gpio135_assert_time": None,
                "pmic_gpio9_deassert_time": None,
                "mdm2ap_irq_v852": {"count_total": 0},
                "selected_lines": [],
            },
            "selected_dmesg_lines": [],
            "v1024_decision": "",
            "v968_decision": "",
        },
        "guardrails": {"device_contact_executed": False, "device_mutations": False},
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    classification = plan_classification() if args.command == "plan" else classify(args)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "classification": classification,
        "device_commands_executed": False,
        "device_mutations": False,
        "actor_start_executed": False,
        "daemon_start_executed": False,
        "wifi_command_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
