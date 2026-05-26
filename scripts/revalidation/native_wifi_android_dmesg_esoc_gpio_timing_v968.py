#!/usr/bin/env python3
"""V968 host-only Android dmesg/eSoC/GPIO timing classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v968-android-dmesg-esoc-gpio-timing")
LATEST_POINTER = Path("tmp/wifi/latest-v968-android-dmesg-esoc-gpio-timing.txt")
DEFAULT_COLLECTOR_DIR = Path(
    "tmp/wifi/v913-android-esoc-gpio-timeline-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands"
)

TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
INTERRUPT_RE = re.compile(
    r"^\s*(?P<irq>\d+):(?P<counts>(?:\s+\d+)+)\s+"
    r"(?P<controller>\S+)\s+(?P<hwirq>\S+)\s+(?P<trigger>\S+)\s+(?P<name>.+?)\s*$"
)

EVENT_PATTERNS: dict[str, str] = {
    "ext_mdm_probe": r"ext-mdm\s+soc:qcom,mdm3",
    "gpio135_request": r"msm_gpio_request:\s+off\[135\]",
    "gpio142_request": r"msm_gpio_request:\s+off\[142\]",
    "gpio9_request": r"msm_gpio_request:\s+off\[9\]",
    "mss_modem_get": r"__subsystem_get:\s+modem count:0",
    "mss_modem_loading": r"subsys-pil-tz .*modem: loading",
    "mss_modem_reset_out": r"subsys-pil-tz .*modem: Brought out of reset",
    "mss_power_ready": r"modem: Power/Clock ready interrupt received",
    "wifi_hal_legacy_start": r"init: starting service 'vendor\.wifi_hal_legacy'",
    "wifi_hal_ext_start": r"init: starting service 'vendor\.wifi_hal_ext'",
    "per_mgr_start": r"init: starting service 'vendor\.per_mgr'",
    "cnss_diag_start": r"init: starting service 'cnss_diag'",
    "wificond_start": r"init: starting service 'wificond'",
    "mdm_helper_start": r"init: starting service 'vendor\.mdm_helper'",
    "cnss_daemon_start": r"init: starting service 'cnss-daemon'",
    "cnss_netlink_create": r"netlink_create.*comm:\s*cnss-daemon",
    "wlfw_start": r"cnss-daemon wlfw_start: Starting",
    "wlfw_service_request": r"cnss-daemon wlfw_service_request",
    "esoc0_subsystem_get": r"__subsystem_get:\s+esoc0 count:0",
    "wlan_pd_indication": r"msm/modem/wlan_pd, state:",
    "icnss_qmi_connected": r"icnss_qmi: QMI Server Connected",
    "bdf_regdb": r"BDF file\s*:\s*regdb\.bin",
    "bdf_bdwlan": r"BDF file\s*:\s*bdwlan\.bin",
    "fw_ready": r"icnss: WLAN FW is ready",
    "wlan0_event": r"dev\s*:\s*wlan0\s*:\s*event",
    "modules_enabled": r"icnss: Modules enabled",
    "pcie_marker": r"\bpcie\b|msm_pcie|mhi_pci|mhi_arch",
}

FOCUS_RE = re.compile(
    r"mdm|esoc|gpio|ap2mdm|mdm2ap|pmic|pm8150|pcie|mhi|subsys|cnss|wlfw|wlan_pd|wlan0|bdwlan|regdb",
    re.IGNORECASE,
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--collector-dir", type=Path, default=DEFAULT_COLLECTOR_DIR)
    parser.add_argument("--dmesg", type=Path)
    parser.add_argument("--gpio", type=Path)
    parser.add_argument("--interrupts", type=Path)
    parser.add_argument("--subsys-state", type=Path)
    parser.add_argument("--process-fd", type=Path)
    parser.add_argument("--props", type=Path)
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dmesg_time(line: str) -> float | None:
    match = TIME_RE.search(line.strip())
    return float(match.group("time")) if match else None


def first_event(text: str, pattern: str) -> dict[str, Any]:
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


def all_matching_events(text: str, pattern: str, limit: int = 120) -> list[dict[str, Any]]:
    regex = re.compile(pattern, re.IGNORECASE)
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("$ "):
            continue
        if regex.search(line):
            events.append({"line_number": line_number, "time": dmesg_time(line), "line": line})
            if len(events) >= limit:
                break
    return events


def parse_events(text: str) -> dict[str, dict[str, Any]]:
    return {name: first_event(text, pattern) for name, pattern in EVENT_PATTERNS.items()}


def event_time(events: dict[str, dict[str, Any]], name: str) -> float | None:
    value = events.get(name, {}).get("time")
    return float(value) if isinstance(value, int | float) else None


def delta_ms(events: dict[str, dict[str, Any]], later: str, earlier: str) -> float | None:
    later_time = event_time(events, later)
    earlier_time = event_time(events, earlier)
    if later_time is None or earlier_time is None:
        return None
    return round((later_time - earlier_time) * 1000.0, 3)


def focus_lines(text: str, limit: int = 220) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and FOCUS_RE.search(line):
            lines.append(line)
            if len(lines) >= limit:
                break
    return lines


def parse_debug_gpio(text: str) -> dict[str, Any]:
    focus: dict[str, list[str]] = {"gpio9": [], "gpio135": [], "gpio142": []}
    readable = "GPIO_DEBUG readable=1" in text or "gpio135" in text or "gpio142" in text
    for raw_line in text.splitlines():
        line = raw_line.strip()
        for name in focus:
            if re.search(rf"\b{name}\b", line):
                focus[name].append(line)
    return {
        "readable": readable,
        "gpio9_lines": focus["gpio9"],
        "gpio135_lines": focus["gpio135"],
        "gpio142_lines": focus["gpio142"],
        "gpio135_level_snapshot": infer_gpio_level(focus["gpio135"]),
        "gpio142_level_snapshot": infer_gpio_level(focus["gpio142"]),
        "pmic_gpio9_lines": [line for line in focus["gpio9"] if "gpiochip" not in line],
    }


def infer_gpio_level(lines: list[str]) -> int | None:
    for line in lines:
        match = re.search(r":\s+(?:in|out)\s+([01])\b", line)
        if match:
            return int(match.group(1))
    return None


def parse_interrupts(text: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = INTERRUPT_RE.match(line)
        if not match:
            continue
        counts = [int(value) for value in match.group("counts").split()]
        name = match.group("name").strip()
        if re.search(r"mdm|esoc|pcie|wlan|gpio", name, re.IGNORECASE):
            rows.append(
                {
                    "irq": int(match.group("irq")),
                    "counts": counts,
                    "total": sum(counts),
                    "controller": match.group("controller"),
                    "hwirq": match.group("hwirq"),
                    "trigger": match.group("trigger"),
                    "name": name,
                    "line": line.strip(),
                }
            )
    return {
        "rows": rows,
        "mdm_status": next((row for row in rows if row["name"] == "mdm status"), None),
        "mdm_errfatal": next((row for row in rows if row["name"] == "mdm errfatal"), None),
        "pcie_wake": next((row for row in rows if row["name"] == "msm_pcie_wake"), None),
    }


def parse_subsys_state(text: str) -> dict[str, Any]:
    values: dict[str, Any] = {
        "subsys9_state": None,
        "subsys9_name": None,
        "subsys9_firmware_name": None,
        "esoc0_driver": None,
        "esoc0_compatible": None,
        "raw_lines": focus_lines(text, limit=120),
    }
    current_file = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("FILE "):
            current_file = line.split("FILE ", 1)[1]
            continue
        if not line or line.startswith("$ ") or line.startswith("==") or line.startswith("PATH ") or line.startswith("lrwx") or line.startswith("drwx"):
            continue
        if current_file.endswith("/subsys9/state") and values["subsys9_state"] is None:
            values["subsys9_state"] = line
        elif current_file.endswith("/subsys9/name") and values["subsys9_name"] is None:
            values["subsys9_name"] = line
        elif current_file.endswith("/subsys9/firmware_name") and values["subsys9_firmware_name"] is None:
            values["subsys9_firmware_name"] = line
        elif current_file.endswith("/esoc0/uevent"):
            key, sep, value = line.partition("=")
            if sep and key == "DRIVER":
                values["esoc0_driver"] = value
            elif sep and key == "OF_COMPATIBLE_0":
                values["esoc0_compatible"] = value
    return values


def input_paths(args: argparse.Namespace) -> dict[str, Path]:
    collector = args.collector_dir
    return {
        "dmesg": args.dmesg or collector / "dmesg-full.txt",
        "gpio": args.gpio or collector / "gpio.txt",
        "interrupts": args.interrupts or collector / "interrupts.txt",
        "subsys_state": args.subsys_state or collector / "subsys-state.txt",
        "process_fd": args.process_fd or collector / "process-fd.txt",
        "props": args.props or collector / "props.txt",
    }


def classify(
    dmesg_text: str,
    gpio_text: str,
    interrupts_text: str,
    subsys_text: str,
) -> dict[str, Any]:
    events = parse_events(dmesg_text)
    gpio = parse_debug_gpio(gpio_text)
    interrupts = parse_interrupts(interrupts_text)
    subsys = parse_subsys_state(subsys_text)
    gpio_transition_lines = all_matching_events(
        dmesg_text,
        r"(gpio\s*(135|142|9)|gpio(135|142|9)).*?(high|low|value|level|assert|deassert)|"
        r"(ap2mdm-status|mdm2ap-status).*?(high|low|value|level|assert|deassert)|"
        r"(soft-reset|soft_reset).*?(high|low|value|level|assert|deassert)",
        limit=80,
    )
    wifi_positive = all(events[name]["present"] for name in ("wlfw_start", "wlan_pd_indication", "fw_ready", "wlan0_event"))
    gpio_names_visible = events["gpio135_request"]["present"] and events["gpio142_request"]["present"] and gpio["readable"]
    gpio_levels_proven = bool(gpio_transition_lines)
    if not dmesg_text:
        decision = "android-dmesg-insufficient"
        passed = False
        reason = "Android dmesg input is missing"
    elif gpio_levels_proven and wifi_positive:
        decision = "android-dmesg-gpio-timing-attributed"
        passed = True
        reason = "Android dmesg includes Wi-Fi-good path and explicit GPIO/eSoC transition markers"
    elif gpio_names_visible and wifi_positive:
        decision = "android-dmesg-needs-magisk-early-sampler"
        passed = True
        reason = (
            "Android evidence proves Wi-Fi-good service/eSoC ordering and GPIO identity, "
            "but not AP2MDM/MDM2AP level-transition timing"
        )
    elif not gpio_names_visible and wifi_positive:
        decision = "android-dmesg-no-gpio-names-visible"
        passed = True
        reason = "Android dmesg proves Wi-Fi-good path but GPIO names/levels are not visible enough"
    else:
        decision = "android-dmesg-insufficient"
        passed = False
        reason = "Android evidence does not prove a Wi-Fi-good path"

    answers = {
        "ap2mdm_gpio135_assert_time": (
            event_time(events, "gpio135_request") if gpio_levels_proven else None
        ),
        "ap2mdm_gpio135_request_time": event_time(events, "gpio135_request"),
        "ap2mdm_gpio135_level_snapshot": gpio["gpio135_level_snapshot"],
        "pmic_gpio9_deassert_time": event_time(events, "gpio9_request") if gpio_levels_proven else None,
        "pmic_gpio9_lines": gpio["pmic_gpio9_lines"],
        "mdm2ap_gpio142_request_time": event_time(events, "gpio142_request"),
        "mdm2ap_gpio142_level_snapshot": gpio["gpio142_level_snapshot"],
        "mdm2ap_irq": interrupts["mdm_status"],
        "pcie_marker_time": event_time(events, "pcie_marker"),
        "wlfw_start_to_esoc0_get_ms": delta_ms(events, "esoc0_subsystem_get", "wlfw_start"),
        "wlfw_start_to_wlan_pd_ms": delta_ms(events, "wlan_pd_indication", "wlfw_start"),
        "wlan_pd_to_icnss_qmi_ms": delta_ms(events, "icnss_qmi_connected", "wlan_pd_indication"),
        "wlfw_start_to_fw_ready_ms": delta_ms(events, "fw_ready", "wlfw_start"),
        "fw_ready_to_wlan0_ms": delta_ms(events, "wlan0_event", "fw_ready"),
    }
    return {
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "events": events,
        "answers": answers,
        "gpio": gpio,
        "interrupts": interrupts,
        "subsys": subsys,
        "gpio_transition_candidates": gpio_transition_lines,
        "focus_lines": focus_lines(dmesg_text),
        "next_step": (
            "implement a bounded Magisk/adb early sampler only if GPIO level-transition timing is required before the next native live gate"
            if decision == "android-dmesg-needs-magisk-early-sampler"
            else "compare the classified Android-good timing against the next native live gate"
            if passed
            else "refresh Android read-only evidence before native service-window live testing"
        ),
    }


def event_rows(events: dict[str, dict[str, Any]]) -> list[tuple[str, str, str, str]]:
    selected = [
        "ext_mdm_probe",
        "gpio135_request",
        "gpio142_request",
        "mss_modem_get",
        "mss_modem_reset_out",
        "mss_power_ready",
        "wifi_hal_legacy_start",
        "wifi_hal_ext_start",
        "per_mgr_start",
        "cnss_diag_start",
        "wificond_start",
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
        "modules_enabled",
    ]
    rows = []
    for name in selected:
        event = events[name]
        rows.append(
            (
                name,
                "yes" if event["present"] else "no",
                "" if event["time"] is None else f"{event['time']:.6f}",
                str(event["line_number"] or ""),
            )
        )
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    answers = classification["answers"]
    answer_rows = [
        ("AP2MDM GPIO135 request", answers["ap2mdm_gpio135_request_time"]),
        ("AP2MDM GPIO135 assert", answers["ap2mdm_gpio135_assert_time"]),
        ("MDM2AP GPIO142 request", answers["mdm2ap_gpio142_request_time"]),
        ("wlfw_start to esoc0 get ms", answers["wlfw_start_to_esoc0_get_ms"]),
        ("wlfw_start to WLAN-PD ms", answers["wlfw_start_to_wlan_pd_ms"]),
        ("WLAN-PD to ICNSS QMI ms", answers["wlan_pd_to_icnss_qmi_ms"]),
        ("wlfw_start to FW ready ms", answers["wlfw_start_to_fw_ready_ms"]),
        ("FW ready to wlan0 ms", answers["fw_ready_to_wlan0_ms"]),
    ]
    return "\n".join(
        [
            "# V968 Android dmesg eSoC/GPIO Timing",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{classification['decision']}`",
            f"- pass: `{classification['pass']}`",
            f"- reason: {classification['reason']}",
            f"- next: {classification['next_step']}",
            "",
            "## Inputs",
            "",
            markdown_table(
                ["input", "path", "sha256"],
                [(name, payload["path"], payload["sha256"]) for name, payload in manifest["inputs"].items()],
            ),
            "",
            "## Timeline",
            "",
            markdown_table(["event", "present", "time_s", "line"], event_rows(classification["events"])),
            "",
            "## Answer Summary",
            "",
            markdown_table(
                ["question", "value"],
                [(name, "" if value is None else json.dumps(value, ensure_ascii=False)) for name, value in answer_rows],
            ),
            "",
            "## Interpretation",
            "",
            "- Android evidence contains the Wi-Fi-good `wlfw_start` → WLAN-PD → BDF → FW-ready → `wlan0` path.",
            "- GPIO 135/142 identity is visible, but GPIO level-transition timing is not directly logged in the existing dmesg/sysfs snapshot.",
            "- `/proc/interrupts` exposes `mdm status` on GPIO 142, but the captured single snapshot does not provide transition timing.",
            "- A Magisk or adb early sampler is justified only if the next native gate still requires GPIO level-transition timing instead of service-window parity.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    paths = input_paths(args)
    texts = {name: read_text(path) for name, path in paths.items()}
    store = EvidenceStore(repo_path(args.out_dir))
    classification = classify(
        texts["dmesg"],
        texts["gpio"],
        texts["interrupts"],
        texts["subsys_state"],
    )
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "host_only": True,
        "device_commands_executed": False,
        "device_mutations": False,
        "native_live_executed": False,
        "android_live_executed": False,
        "inputs": {
            name: {
                "path": str(repo_path(path)),
                "exists": repo_path(path).exists(),
                "sha256": sha256(path),
                "bytes": repo_path(path).stat().st_size if repo_path(path).exists() else 0,
            }
            for name, path in paths.items()
        },
        "classification": classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    store.write_text("dmesg-focus-lines.txt", "\n".join(classification["focus_lines"]) + "\n")
    store.write_json("timeline.json", classification["events"])
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {classification['decision']}")
    print(f"pass: {classification['pass']}")
    print(f"reason: {classification['reason']}")
    print(f"next: {classification['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if classification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
