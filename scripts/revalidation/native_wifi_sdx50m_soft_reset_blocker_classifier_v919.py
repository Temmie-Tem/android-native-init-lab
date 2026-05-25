#!/usr/bin/env python3
"""V919 host-only classifier for the SDX50M soft-reset blocker.

This classifier consumes existing Android positive-control evidence and V918
native negative-control evidence. It deliberately does not contact the device,
run ADB, start actors, open eSoC/subsystem nodes, or mutate any live state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v919-sdx50m-soft-reset-blocker-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v919-sdx50m-soft-reset-blocker-classifier.txt")
DEFAULT_V913_RUN = Path("tmp/wifi/v913-android-esoc-gpio-timeline-handoff-live/v913-android-esoc-gpio-timeline-run")
DEFAULT_V918_DIR = Path("tmp/wifi/v918-mdm-helper-subsys-trigger-capture-live")
DEFAULT_MDM_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_PM_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")


TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v913-run", type=Path, default=DEFAULT_V913_RUN)
    parser.add_argument("--v918-dir", type=Path, default=DEFAULT_V918_DIR)
    parser.add_argument("--mdm-research", type=Path, default=DEFAULT_MDM_RESEARCH)
    parser.add_argument("--pm-research", type=Path, default=DEFAULT_PM_RESEARCH)
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.replace("\0", "\n").splitlines():
        if "=" not in line:
            continue
        key, value = line.strip().split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.:-]+", key):
            values[key] = value
    return values


def dmesg_time(line: str) -> float | None:
    match = TIME_RE.search(line)
    return float(match.group("time")) if match else None


def first_line(text: str, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    for index, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if regex.search(line):
            return {"present": True, "line_no": index, "time": dmesg_time(line), "line": line}
    return {"present": False, "line_no": 0, "time": None, "line": ""}


def grep_lines(text: str, pattern: str, limit: int = 32) -> list[str]:
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


def proc_block(text: str, label: str) -> str:
    pattern = re.compile(
        rf"A90_EXECNS_CNSS_PROC_{re.escape(label)}_BEGIN[^\n]*\n(.*?)\nA90_EXECNS_CNSS_PROC_{re.escape(label)}_END",
        re.S,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def status_state(status_text: str) -> str:
    match = re.search(r"^State:\s*(.+)$", status_text, re.M)
    return match.group(1).strip() if match else ""


def extract_v918(v918_dir: Path) -> dict[str, Any]:
    manifest_path = repo_path(v918_dir / "manifest.json")
    transcript_path = repo_path(v918_dir / "native/mdm-helper-subsys-trigger.txt")
    manifest = load_json(v918_dir / "manifest.json")
    transcript = read_text(v918_dir / "native/mdm-helper-subsys-trigger.txt")
    keys = key_values(transcript)
    contract = (manifest.get("analysis") or {}).get("helper", {}).get("contract", {})
    child_wchan = proc_block(transcript, "mdm_helper_subsys_trigger_child_wchan")
    child_status = proc_block(transcript, "mdm_helper_subsys_trigger_child_status")
    return {
        "manifest": str(manifest_path),
        "transcript": str(transcript_path),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "cleanup_reboot_executed": bool(manifest.get("cleanup_reboot_executed")),
        "post_cleanup_healthy": bool(((manifest.get("analysis") or {}).get("reboot_cleanup") or {}).get("healthy")),
        "mdm_helper_observable": contract.get("mdm_helper_observable", ""),
        "fd_esoc0_gate": contract.get("fd_esoc0_count.gate", ""),
        "subsys_open_attempted": contract.get("subsys_esoc0_open_attempted", ""),
        "subsys_trigger_started": contract.get("subsys_trigger.started", ""),
        "subsys_trigger_exited": contract.get("subsys_trigger.exited", ""),
        "subsys_trigger_reaped": contract.get("subsys_trigger.reaped", ""),
        "subsys_trigger_timed_out": contract.get("timed_out", ""),
        "subsys_trigger_result": contract.get("result", ""),
        "all_postflight_safe": contract.get("all_postflight_safe", ""),
        "wchan": keys.get("capture.mdm_helper_subsys_trigger.subsys_trigger.blocker_snapshot.wchan", "") or child_wchan,
        "state": keys.get("capture.mdm_helper_subsys_trigger.subsys_trigger.blocker_snapshot.state", "") or status_state(child_status),
        "mdm3_state_before": keys.get("wifi_companion_start.subsys_hold.subsys_trigger_before.mdm3_state", ""),
        "mdm3_state_after": keys.get("wifi_companion_start.subsys_hold.subsys_trigger_after.mdm3_state", ""),
        "wlan0_before": keys.get("wifi_companion_start.cnss2_focus_subsys_trigger_before.wlan0_captured", ""),
        "wlan0_after": keys.get("wifi_companion_start.cnss2_focus_subsys_trigger_after.wlan0_captured", ""),
        "ks_final": contract.get("ks_count.final", ""),
        "mhi_final": contract.get("fd_mhi_pipe_count.final", ""),
        "forbidden": {
            "service_manager": bool(manifest.get("service_manager_start_executed")),
            "cnss": bool(manifest.get("cnss_start_executed")),
            "wifi_hal": bool(manifest.get("wifi_hal_start_executed")),
            "scan_connect": bool(manifest.get("scan_connect_executed")),
            "credentials": bool(manifest.get("credential_use_executed")),
            "dhcp_route": bool(manifest.get("dhcp_route_executed")),
            "external_ping": bool(manifest.get("external_ping_executed")),
            "notify": bool(manifest.get("notify_attempted")),
            "boot_done": bool(manifest.get("boot_done_attempted")),
        },
        "stack_hits": grep_lines(transcript, r"sdx50m_toggle_soft_reset|mdm4x_do_first_power_on|mdm_cmd_exe|mdm_subsys_powerup|__subsystem_get|subsys_device_open", 16),
    }


def extract_android(v913_run: Path) -> dict[str, Any]:
    manifest = load_json(v913_run / "manifest.json")
    dmesg = read_text(v913_run / "android/commands/dmesg-full.txt")
    gpio = read_text(v913_run / "android/commands/gpio.txt")
    interrupts = read_text(v913_run / "android/commands/interrupts.txt")
    process_fd = read_text(v913_run / "android/commands/process-fd.txt")
    props = read_text(v913_run / "android/commands/props.txt")
    timeline = {
        "mdm3_config": first_line(dmesg, r"ext-mdm.*qcom,mdm3"),
        "vendor_mdm_helper_start": first_line(dmesg, r"starting service 'vendor\.mdm_helper'"),
        "cnss_wlfw_start": first_line(dmesg, r"cnss-daemon wlfw_start: Starting"),
        "esoc0_subsystem_get": first_line(dmesg, r"__subsystem_get\(\): __subsystem_get: esoc0 count:0"),
        "wlan_pd": first_line(dmesg, r"msm/modem/wlan_pd"),
        "bdf_regdb": first_line(dmesg, r"BDF file : regdb\.bin"),
        "bdf_bdwlan": first_line(dmesg, r"BDF file : bdwlan\.bin"),
        "wlan0": first_line(dmesg, r"dev : wlan0 : event"),
    }
    return {
        "manifest": str(repo_path(v913_run / "manifest.json")),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "timeline": timeline,
        "gpio_debug_readable": "GPIO_DEBUG readable=1" in gpio,
        "gpio135_snapshot": first_line(gpio, r"^\s*gpio135\s*:"),
        "gpio142_snapshot": first_line(gpio, r"^\s*gpio142\s*:"),
        "pmic_gpio9_snapshot": first_line(gpio, r"^\s*gpio9\s*:.*(?:vin-|push-pull|pull-down)"),
        "mdm_status_irq": first_line(interrupts, r"msmgpio-dc\s+142\s+Edge\s+mdm status"),
        "mdm_helper_esoc_fd": first_line(process_fd, r"mdm_helper.*|/dev/esoc-0"),
        "pm_service_subsys_modem_fd": first_line(process_fd, r"pm-service|/dev/subsys_modem"),
        "vendor_mdm_helper_running": "init.svc.vendor.mdm_helper=running" in props,
        "selected_dmesg_lines": grep_lines(
            dmesg,
            r"ext-mdm|vendor\.mdm_helper|cnss-daemon wlfw_start|__subsystem_get.*esoc0|wlan_pd|BDF file|wlan0",
            24,
        ),
        "selected_gpio_lines": grep_lines(gpio, r"GPIO_DEBUG readable|gpio135|gpio142|gpio9.*pm8150", 16),
        "selected_process_lines": grep_lines(process_fd, r"mdm_helper|/dev/esoc-0|pm-service|/dev/subsys_modem|/dev/subsys_esoc0|/vendor/bin/ks|mhi_0305", 24),
    }


def extract_research(mdm_research: Path, pm_research: Path) -> dict[str, Any]:
    mdm = read_text(mdm_research)
    pm = read_text(pm_research)
    return {
        "mdm_research": str(repo_path(mdm_research)),
        "pm_research": str(repo_path(pm_research)),
        "soft_reset_mentions": grep_lines(mdm, r"sdx50m_toggle_soft_reset|PMIC pm8150l GPIO 9|GPIO 135|GPIO 142|wait_for_err_ready", 16),
        "pm_contract_mentions": grep_lines(pm, r"mdm_helper|REQ_ENG|CMD_ENG|ESOC_PWR_ON|ESOC_REQ_IMG|/dev/subsys_esoc0|/dev/esoc-0|GPIO 142|ks", 20),
    }


def classify(v918: dict[str, Any], android: dict[str, Any], research: dict[str, Any]) -> dict[str, Any]:
    android_upper_positive = all(
        android["timeline"][key]["present"]
        for key in ("cnss_wlfw_start", "esoc0_subsystem_get", "wlan_pd", "bdf_regdb", "bdf_bdwlan", "wlan0")
    )
    native_soft_reset_block = (
        v918["subsys_open_attempted"] == "1"
        and v918["subsys_trigger_started"] == "1"
        and v918["subsys_trigger_exited"] == "0"
        and v918["subsys_trigger_timed_out"] == "1"
        and v918["subsys_trigger_result"] == "reboot-required"
        and v918["wchan"] == "sdx50m_toggle_soft_reset"
    )
    android_precondition_gap = (
        android["timeline"]["vendor_mdm_helper_start"]["present"]
        and android["timeline"]["cnss_wlfw_start"]["present"]
        and android["timeline"]["esoc0_subsystem_get"]["present"]
        and v918["forbidden"]["cnss"] is False
    )
    research_support = bool(research["soft_reset_mentions"] and research["pm_contract_mentions"])
    pass_ok = android_upper_positive and native_soft_reset_block and android_precondition_gap and research_support
    return {
        "decision": "v919-sdx50m-soft-reset-blocker-classified" if pass_ok else "v919-sdx50m-soft-reset-blocker-review",
        "pass": pass_ok,
        "reason": (
            "existing Android dmesg/IRQ/GPIO evidence is sufficient; V918 blocks in SDX50M soft-reset after mdm_helper fd gating, while Android orders vendor.mdm_helper and cnss-daemon wlfw_start before esoc0 subsystem_get and then reaches WLAN-PD/BDF/wlan0"
            if pass_ok else
            "evidence did not fully prove both Android positive ordering and V918 native soft-reset block"
        ),
        "next_step": (
            "plan V920 as host-only design for a bounded cnss-daemon/WLFW-request-before-esoc0 trigger gate; do not repeat /dev/subsys_esoc0 open or boot Android solely for Magisk-style evidence"
            if pass_ok else
            "review V913/V918 evidence; if Android reset/status timing is still missing, run a focused Android read-only recapture before any native live retry"
        ),
        "android_upper_positive": android_upper_positive,
        "native_soft_reset_block": native_soft_reset_block,
        "android_precondition_gap": android_precondition_gap,
        "research_support": research_support,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    v918 = manifest["v918_native_negative"]
    android = manifest["android_positive"]
    research = manifest["research"]
    android_rows = [
        [key, value["present"], value.get("time"), value.get("line", "")]
        for key, value in android["timeline"].items()
    ]
    v918_rows = [
        ["decision", v918["decision"]],
        ["cleanup_reboot_executed", v918["cleanup_reboot_executed"]],
        ["post_cleanup_healthy", v918["post_cleanup_healthy"]],
        ["mdm_helper_observable", v918["mdm_helper_observable"]],
        ["fd_esoc0_gate", v918["fd_esoc0_gate"]],
        ["subsys_open_attempted", v918["subsys_open_attempted"]],
        ["subsys_trigger_started", v918["subsys_trigger_started"]],
        ["subsys_trigger_exited", v918["subsys_trigger_exited"]],
        ["timed_out", v918["subsys_trigger_timed_out"]],
        ["result", v918["subsys_trigger_result"]],
        ["wchan", v918["wchan"]],
        ["state", v918["state"]],
        ["mdm3_state_before", v918["mdm3_state_before"]],
        ["mdm3_state_after", v918["mdm3_state_after"]],
        ["ks_final", v918["ks_final"]],
        ["mhi_final", v918["mhi_final"]],
        ["wlan0_after", v918["wlan0_after"]],
    ]
    guard_rows = [[key, value] for key, value in v918["forbidden"].items()]
    return "\n".join(
        [
            "# V919 SDX50M Soft-Reset Blocker Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            "## Classification",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["android_upper_positive", classification["android_upper_positive"]],
                    ["native_soft_reset_block", classification["native_soft_reset_block"]],
                    ["android_precondition_gap", classification["android_precondition_gap"]],
                    ["research_support", classification["research_support"]],
                ],
            ),
            "",
            "## Android Positive Ordering",
            "",
            markdown_table(["marker", "present", "time", "line"], android_rows),
            "",
            "## Android Lower Snapshots",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["gpio_debug_readable", android["gpio_debug_readable"]],
                    ["gpio135_snapshot", android["gpio135_snapshot"].get("line", "")],
                    ["gpio142_snapshot", android["gpio142_snapshot"].get("line", "")],
                    ["pmic_gpio9_snapshot", android["pmic_gpio9_snapshot"].get("line", "")],
                    ["mdm_status_irq", android["mdm_status_irq"].get("line", "")],
                    ["vendor_mdm_helper_running", android["vendor_mdm_helper_running"]],
                ],
            ),
            "",
            "## V918 Native Negative Control",
            "",
            markdown_table(["field", "value"], v918_rows),
            "",
            "## V918 Guardrails",
            "",
            markdown_table(["forbidden path", "executed"], guard_rows),
            "",
            "## Research Anchors",
            "",
            "- `sdx50m_toggle_soft_reset()` de-asserts PMIC GPIO9 and does not wait for GPIO142 inside the function.",
            "- `wait_for_err_ready()` is not the observed wait location; V918 captured the block inside the proprietary SDX50M power-up path.",
            "- Android positive control already has enough after-the-fact dmesg/GPIO/IRQ evidence for this gate; a Magisk module is not required before the next host-only design step.",
            "",
            "### Selected Android Lines",
            "",
            *[f"- {line}" for line in android["selected_dmesg_lines"][:12]],
            "",
            "### Selected V918 Stack Lines",
            "",
            *[f"- {line}" for line in v918["stack_hits"][:12]],
            "",
            "## Guardrails",
            "",
            "- Host-only classifier: no device contact, no ADB command, no Android boot, and no Magisk module.",
            "- No actor start, eSoC ioctl, `/dev/subsys_esoc0` open, CNSS daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, GPIO/sysfs/debugfs write, boot image write, partition write, or firmware mutation.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v918 = extract_v918(args.v918_dir)
    android = extract_android(args.v913_run)
    research = extract_research(args.mdm_research, args.pm_research)
    classification = classify(v918, android, research)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "inputs": {
            "v913_run": str(repo_path(args.v913_run)),
            "v918_dir": str(repo_path(args.v918_dir)),
            "mdm_research": str(repo_path(args.mdm_research)),
            "pm_research": str(repo_path(args.pm_research)),
        },
        "classification": classification,
        "android_positive": android,
        "v918_native_negative": v918,
        "research": research,
        "device_contact": False,
        "adb_executed": False,
        "android_boot_executed": False,
        "magisk_module_created": False,
        "live_esoc_ioctl_executed": False,
        "subsys_esoc0_open_attempted": False,
        "cnss_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
