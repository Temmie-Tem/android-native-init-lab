#!/usr/bin/env python3
"""v282 read-only ICNSS/WLFW readiness surface observer."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402
from wifi_cnss_zombie_audit import parse_ps_stat_comm, summarize_cnss_processes  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v282-icnss-wlfw-readiness-surface")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_TOYBOX = "/cache/bin/toybox"

ICNSS_NODE = "/sys/devices/platform/soc/18800000.qcom,icnss"
ICNSS_DRIVER = "/sys/bus/platform/drivers/icnss"
ICNSS_DRIVER_DEVICE = f"{ICNSS_DRIVER}/18800000.qcom,icnss"
QCA6390_NODE = "/sys/devices/platform/soc/a0000000.qcom,cnss-qca6390"
WLAN_MODULE = "/sys/module/wlan"
ICNSS_MODULE = "/sys/module/icnss"
DEBUG_ROOT = "/sys/kernel/debug"
DEBUG_ICNSS = f"{DEBUG_ROOT}/icnss"
SHUTDOWN_WLAN = "/sys/kernel/shutdown_wlan"

SOURCE_REFERENCES = (
    "https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/icnss.c",
    "https://android.googlesource.com/kernel/msm/+/79a5a3af469e5d38c649dbe3dc7340d96990fd68/drivers/soc/qcom/icnss_qmi.c",
    "https://android.googlesource.com/kernel/msm/+/157ab4a1b7d2bf3275a20ee90d855bec184d742e/Documentation/devicetree/bindings/cnss/icnss.txt",
    "https://docs.kernel.org/filesystems/debugfs.html",
    "https://docs.kernel.org/driver-api/driver-model/binding.html",
)

DENIED_COMMAND_PATTERNS = (
    re.compile(r"\b/vendor/bin/cnss-daemon\b", re.IGNORECASE),
    re.compile(r"\bcnss_diag\b", re.IGNORECASE),
    re.compile(r"\ba90_qrtr_ns_probe\b", re.IGNORECASE),
    re.compile(r"\ba90_qrtr_probe\b", re.IGNORECASE),
    re.compile(r"--allow-qrtr-ns-transmit", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|android\.hardware\.wifi)\b", re.IGNORECASE),
    re.compile(r"\b(?:dhcpcd|udhcpc|dnsmasq)\b", re.IGNORECASE),
    re.compile(r"\b/sys/bus/platform/drivers/icnss/(?:bind|unbind)\b", re.IGNORECASE),
    re.compile(r"\bdriver_override\b.*(?:>|tee|write)", re.IGNORECASE),
    re.compile(r">\s*/sys/|\btee\b.*\s/sys/|\becho\b.*\s/sys/", re.IGNORECASE),
    re.compile(r"\bmount\s+-t\s+debugfs\b", re.IGNORECASE),
)

COMMANDS: tuple[tuple[str, tuple[str, ...], float, bool], ...] = (
    ("version", ("version",), 10.0, True),
    ("status", ("status",), 20.0, True),
    ("stat-icnss-node", ("stat", ICNSS_NODE), 10.0, True),
    ("cat-icnss-uevent", ("cat", f"{ICNSS_NODE}/uevent"), 10.0, True),
    ("stat-icnss-driver", ("stat", ICNSS_DRIVER), 10.0, True),
    ("stat-icnss-driver-device", ("stat", ICNSS_DRIVER_DEVICE), 10.0, True),
    ("find-icnss-node", ("run", DEFAULT_TOYBOX, "find", ICNSS_NODE, "-maxdepth", "5"), 30.0, False),
    ("find-icnss-driver", ("run", DEFAULT_TOYBOX, "find", ICNSS_DRIVER, "-maxdepth", "4"), 30.0, False),
    ("stat-qca6390-node", ("stat", QCA6390_NODE), 10.0, True),
    ("cat-qca6390-uevent", ("cat", f"{QCA6390_NODE}/uevent"), 10.0, False),
    ("stat-qca6390-driver", ("stat", f"{QCA6390_NODE}/driver"), 10.0, False),
    ("stat-wlan-module", ("stat", WLAN_MODULE), 10.0, True),
    ("find-wlan-module", ("run", DEFAULT_TOYBOX, "find", WLAN_MODULE, "-maxdepth", "3"), 30.0, False),
    ("cat-wlan-fwpath", ("cat", f"{WLAN_MODULE}/parameters/fwpath"), 10.0, False),
    ("cat-wlan-con-mode", ("cat", f"{WLAN_MODULE}/parameters/con_mode"), 10.0, False),
    ("cat-wlan-country-code", ("cat", f"{WLAN_MODULE}/parameters/country_code"), 10.0, False),
    ("stat-icnss-module", ("stat", ICNSS_MODULE), 10.0, True),
    ("find-icnss-module", ("run", DEFAULT_TOYBOX, "find", ICNSS_MODULE, "-maxdepth", "3"), 30.0, False),
    ("cat-icnss-quirks", ("cat", f"{ICNSS_MODULE}/parameters/quirks"), 10.0, False),
    ("cat-icnss-dynamic-feature-mask", ("cat", f"{ICNSS_MODULE}/parameters/dynamic_feature_mask"), 10.0, False),
    ("cat-proc-mounts", ("cat", "/proc/mounts"), 10.0, True),
    ("stat-debug-root", ("stat", DEBUG_ROOT), 10.0, False),
    ("find-debug-root", ("run", DEFAULT_TOYBOX, "find", DEBUG_ROOT, "-maxdepth", "2"), 30.0, False),
    ("stat-debug-icnss", ("stat", DEBUG_ICNSS), 10.0, False),
    ("find-debug-icnss", ("run", DEFAULT_TOYBOX, "find", DEBUG_ICNSS, "-maxdepth", "3"), 30.0, False),
    ("stat-shutdown-wlan", ("stat", SHUTDOWN_WLAN), 10.0, False),
    ("cat-shutdown-wlan", ("cat", SHUTDOWN_WLAN), 10.0, False),
    ("cat-proc-modules", ("run", DEFAULT_TOYBOX, "cat", "/proc/modules"), 20.0, True),
    ("run-zcat-proc-config", ("run", DEFAULT_TOYBOX, "zcat", "/proc/config.gz"), 20.0, False),
    ("run-dmesg", ("run", DEFAULT_TOYBOX, "dmesg"), 30.0, False),
    ("cat-proc-net-dev", ("cat", "/proc/net/dev"), 10.0, True),
    ("ls-sys-class-net", ("ls", "/sys/class/net"), 10.0, True),
    ("ls-sys-class-ieee80211", ("ls", "/sys/class/ieee80211"), 10.0, False),
    ("ls-sys-class-rfkill", ("ls", "/sys/class/rfkill"), 10.0, False),
    ("ps-A-pid-stat-comm", ("run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm"), 20.0, True),
)

CONFIG_KEYS = (
    "CONFIG_ICNSS",
    "CONFIG_ICNSS_QMI",
    "CONFIG_ICNSS_DEBUG",
    "CONFIG_DEBUG_FS",
    "CONFIG_CNSS_UTILS",
    "CONFIG_WLAN",
    "CONFIG_QCA_CLD_WLAN",
    "CONFIG_CNSS2",
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
READY_RE = re.compile(
    r"(fw_ready|fw ready|fw is not ready|firmware.*ready|wlfw|qmi server connected|"
    r"qmi service disconnected|driver probe|wlan driver|icnss_register_driver|msa ready)",
    re.IGNORECASE,
)
SURFACE_RE = re.compile(r"(ready|state|status|stats|fw|firmware|wlfw|qmi|msa|probe)", re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def replace_defaults(command: tuple[str, ...], args: argparse.Namespace) -> list[str]:
    return [args.toybox if part == DEFAULT_TOYBOX else part for part in command]


def validate_no_denied_commands(args: argparse.Namespace) -> None:
    text = "\n".join(" ".join(replace_defaults(command, args)) for _, command, _, _ in COMMANDS)
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def capture_commands(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, str]]:
    store.mkdir("captures")
    records: list[dict[str, Any]] = []
    raw_texts: dict[str, str] = {}
    for name, command, timeout, required in COMMANDS:
        actual = replace_defaults(command, args)
        capture = run_capture(args, name, actual, timeout=timeout)
        raw_text = capture.text if capture.text else capture.error + "\n"
        raw_texts[name] = raw_text
        store.write_text(f"captures/{safe_name(name)}.txt", raw_text)
        item = capture_to_manifest(capture)
        item["required"] = required
        records.append(item)
    return records, raw_texts


def by_name(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in captures}


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return bool(item.get("ok")) and item.get("rc") == 0 and item.get("status") == "ok"


def capture_text(raw_texts: dict[str, str], name: str) -> str:
    return strip_cmdv1_text(raw_texts.get(name, ""))


def clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = ANSI_RE.sub("", raw_line).strip().replace("<NULL>", "")
        if not line:
            continue
        if line.startswith(("a90:/#", "A90P1 ", "[done]", "[err]", "[exit", "run: pid=")):
            continue
        lines.append(line)
    return lines


def parse_key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip().replace("<NULL>", "")
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value
    return result


def parse_config(text: str) -> dict[str, str]:
    all_values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$", line)
        if match:
            all_values[match.group(1)] = match.group(2).strip('"')
            continue
        match = re.match(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$", line)
        if match:
            all_values[match.group(1)] = "n"
    return {key: all_values.get(key, "unset") for key in CONFIG_KEYS}


def module_loaded(proc_modules: str, module_name: str) -> bool:
    return bool(re.search(rf"^{re.escape(module_name)}\s", proc_modules, re.MULTILINE))


def text_has_wlan_netdev(text: str) -> bool:
    return bool(
        re.search(r"^\s*wlan\S*:", text, re.MULTILINE)
        or re.search(r"(^|\s)(wlan\S*|swlan\S*|p2p\S*|wifi-aware\S*)(\s|$)", text)
    )


def debugfs_mounted(proc_mounts: str) -> bool:
    return any(" /sys/kernel/debug " in line and " debugfs " in line for line in proc_mounts.splitlines())


def surface_candidates(*texts: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for line in clean_lines(text):
            if not SURFACE_RE.search(line):
                continue
            if line in seen:
                continue
            seen.add(line)
            candidates.append(line)
    return candidates[:80]


def filter_log_lines(text: str) -> tuple[list[str], list[str]]:
    relevant = []
    readiness = []
    wanted = re.compile(r"(icnss|qca6390|wlan|wlfw|fw_ready|fw is not ready|driver probe|qmi|msa)", re.IGNORECASE)
    for line in clean_lines(text):
        if wanted.search(line):
            relevant.append(line)
        if READY_RE.search(line):
            readiness.append(line)
    return relevant[-120:], readiness[-80:]


def build_classification(captures: dict[str, dict[str, Any]], raw_texts: dict[str, str]) -> dict[str, Any]:
    icnss_uevent = parse_key_values(capture_text(raw_texts, "cat-icnss-uevent"))
    qca_uevent = parse_key_values(capture_text(raw_texts, "cat-qca6390-uevent"))
    proc_modules = capture_text(raw_texts, "cat-proc-modules")
    proc_mounts = capture_text(raw_texts, "cat-proc-mounts")
    proc_net = capture_text(raw_texts, "cat-proc-net-dev")
    sys_net = capture_text(raw_texts, "ls-sys-class-net")
    ieee80211 = capture_text(raw_texts, "ls-sys-class-ieee80211")
    process_text = capture_text(raw_texts, "ps-A-pid-stat-comm")
    process_summary = summarize_cnss_processes(parse_ps_stat_comm(process_text)) if process_text else None
    config = parse_config(capture_text(raw_texts, "run-zcat-proc-config"))
    relevant_logs, readiness_logs = filter_log_lines(capture_text(raw_texts, "run-dmesg"))
    debug_root_lines = clean_lines(capture_text(raw_texts, "find-debug-root"))
    debug_icnss_lines = clean_lines(capture_text(raw_texts, "find-debug-icnss"))
    sysfs_candidates = surface_candidates(
        capture_text(raw_texts, "find-icnss-node"),
        capture_text(raw_texts, "find-icnss-driver"),
        capture_text(raw_texts, "find-icnss-module"),
        capture_text(raw_texts, "find-wlan-module"),
    )
    debug_candidates = surface_candidates(capture_text(raw_texts, "find-debug-icnss"))
    return {
        "icnss_uevent": icnss_uevent,
        "qca6390_uevent": qca_uevent,
        "icnss_compatible": icnss_uevent.get("OF_COMPATIBLE_0") == "qcom,icnss",
        "qca6390_compatible": qca_uevent.get("OF_COMPATIBLE_0") == "qcom,cnss-qca6390",
        "icnss_node_present": capture_ok(captures, "stat-icnss-node"),
        "icnss_driver_present": capture_ok(captures, "stat-icnss-driver"),
        "icnss_driver_device_present": capture_ok(captures, "stat-icnss-driver-device"),
        "qca6390_node_present": capture_ok(captures, "stat-qca6390-node"),
        "qca6390_driver_present": capture_ok(captures, "stat-qca6390-driver"),
        "wlan_module_sysfs_present": capture_ok(captures, "stat-wlan-module"),
        "wlan_module_loaded": module_loaded(proc_modules, "wlan"),
        "icnss_module_sysfs_present": capture_ok(captures, "stat-icnss-module"),
        "icnss_module_loaded": module_loaded(proc_modules, "icnss"),
        "wlan_params": {
            "fwpath": " ".join(clean_lines(capture_text(raw_texts, "cat-wlan-fwpath"))),
            "con_mode": " ".join(clean_lines(capture_text(raw_texts, "cat-wlan-con-mode"))),
            "country_code": " ".join(clean_lines(capture_text(raw_texts, "cat-wlan-country-code"))),
        },
        "icnss_module_params": {
            "quirks": " ".join(clean_lines(capture_text(raw_texts, "cat-icnss-quirks"))),
            "dynamic_feature_mask": " ".join(clean_lines(capture_text(raw_texts, "cat-icnss-dynamic-feature-mask"))),
        },
        "debugfs_mounted": debugfs_mounted(proc_mounts),
        "debug_root_present": capture_ok(captures, "stat-debug-root"),
        "debug_icnss_present": capture_ok(captures, "stat-debug-icnss"),
        "debug_root_sample": debug_root_lines[:80],
        "debug_icnss_sample": debug_icnss_lines[:80],
        "sysfs_readiness_candidates": sysfs_candidates,
        "debugfs_readiness_candidates": debug_candidates,
        "shutdown_wlan_present": capture_ok(captures, "stat-shutdown-wlan"),
        "shutdown_wlan_readable": capture_ok(captures, "cat-shutdown-wlan"),
        "shutdown_wlan_text": " ".join(clean_lines(capture_text(raw_texts, "cat-shutdown-wlan")))[:200],
        "config": config,
        "dmesg_relevant_tail": relevant_logs,
        "dmesg_readiness_tail": readiness_logs,
        "dmesg_relevant_count": len(relevant_logs),
        "dmesg_readiness_count": len(readiness_logs),
        "wlan_netdev_present": text_has_wlan_netdev(proc_net) or text_has_wlan_netdev(sys_net),
        "wiphy_present": bool(re.search(r"(^|\s)phy\d+(\s|$)", ieee80211)),
        "process_summary": process_summary,
    }


def build_checks(args: argparse.Namespace,
                 captures: dict[str, dict[str, Any]],
                 raw_texts: dict[str, str],
                 classification: dict[str, Any]) -> list[dict[str, Any]]:
    version_text = capture_text(raw_texts, "version")
    required_failed = [name for name, _, _, required in COMMANDS if required and not capture_ok(captures, name)]
    process_summary = classification.get("process_summary") or {}
    return [
        {"name": "expected-version", "pass": args.expect_version in version_text, "severity": "critical", "detail": args.expect_version},
        {"name": "required-live-captures", "pass": not required_failed, "severity": "critical", "detail": "failed=" + json.dumps(required_failed)},
        {"name": "icnss-core-bound", "pass": classification["icnss_node_present"] and classification["icnss_driver_present"] and classification["icnss_driver_device_present"], "severity": "critical", "detail": json.dumps({"node": classification["icnss_node_present"], "driver": classification["icnss_driver_present"], "driver_device": classification["icnss_driver_device_present"]}, sort_keys=True)},
        {"name": "icnss-compatible-visible", "pass": classification["icnss_compatible"], "severity": "critical", "detail": json.dumps(classification["icnss_uevent"], sort_keys=True)},
        {"name": "wlan-module-surface", "pass": classification["wlan_module_sysfs_present"] or classification["wlan_module_loaded"], "severity": "critical", "detail": json.dumps({"sysfs": classification["wlan_module_sysfs_present"], "proc_modules": classification["wlan_module_loaded"]}, sort_keys=True)},
        {"name": "cnss-process-clean", "pass": bool(process_summary.get("clean")), "severity": "critical", "detail": json.dumps({"target_process_count": process_summary.get("target_process_count"), "target_running_count": process_summary.get("target_running_count"), "target_zombie_count": process_summary.get("target_zombie_count")}, sort_keys=True)},
        {"name": "no-wlan-readiness-surface", "pass": not classification["wlan_netdev_present"] and not classification["wiphy_present"], "severity": "critical", "detail": json.dumps({"netdev": classification["wlan_netdev_present"], "wiphy": classification["wiphy_present"]}, sort_keys=True)},
        {"name": "debugfs-observed-readonly", "pass": classification["debug_root_present"], "severity": "warning", "detail": json.dumps({"mounted": classification["debugfs_mounted"], "icnss": classification["debug_icnss_present"]}, sort_keys=True)},
        {"name": "icnss-readiness-candidates", "pass": bool(classification["sysfs_readiness_candidates"] or classification["debugfs_readiness_candidates"] or classification["dmesg_readiness_count"]), "severity": "warning", "detail": json.dumps({"sysfs": len(classification["sysfs_readiness_candidates"]), "debugfs": len(classification["debugfs_readiness_candidates"]), "dmesg": classification["dmesg_readiness_count"]}, sort_keys=True)},
        {"name": "shutdown-wlan-surface", "pass": classification["shutdown_wlan_present"], "severity": "warning", "detail": json.dumps({"present": classification["shutdown_wlan_present"], "readable": classification["shutdown_wlan_readable"]}, sort_keys=True)},
        {"name": "kernel-log-readable", "pass": capture_ok(captures, "run-dmesg"), "severity": "warning", "detail": f"filtered_lines={classification['dmesg_relevant_count']}"},
    ]


def classify(checks: list[dict[str, Any]], classification: dict[str, Any]) -> tuple[bool, str, str]:
    critical_failed = [item["name"] for item in checks if item.get("severity") == "critical" and not item.get("pass")]
    if critical_failed:
        return False, "icnss-wlfw-readiness-incomplete", "critical checks failed: " + ", ".join(critical_failed)
    if classification["wlan_netdev_present"] or classification["wiphy_present"]:
        return True, "icnss-wlfw-readiness-surface-visible", "WLAN netdev/wiphy readiness surface is visible"
    if classification["debug_icnss_present"] and classification["debugfs_readiness_candidates"]:
        return True, "icnss-debugfs-readiness-candidates-visible", "ICNSS debugfs readiness-looking entries are visible without mounting debugfs"
    if classification["dmesg_readiness_count"]:
        return True, "icnss-wlfw-readiness-log-only", "read-only kernel log exposes ICNSS/WLFW readiness history but no stable state file"
    if classification["sysfs_readiness_candidates"]:
        return True, "icnss-readiness-sysfs-candidates-limited", "sysfs has state-looking ICNSS/WLAN paths but no direct firmware-ready state"
    return True, "icnss-readiness-surface-limited", "no-start read-only state exposes ICNSS binding but no direct WLFW firmware-ready state surface"


def render_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    overview_rows = [
        ["icnss compatible", str(c["icnss_compatible"])],
        ["icnss driver-device", str(c["icnss_driver_device_present"])],
        ["qca6390 compatible", str(c["qca6390_compatible"])],
        ["qca6390 driver", str(c["qca6390_driver_present"])],
        ["wlan module sysfs", str(c["wlan_module_sysfs_present"])],
        ["wlan params", json.dumps(c["wlan_params"], sort_keys=True)],
        ["icnss params", json.dumps(c["icnss_module_params"], sort_keys=True)],
        ["debugfs mounted", str(c["debugfs_mounted"])],
        ["debugfs icnss", str(c["debug_icnss_present"])],
        ["shutdown_wlan", json.dumps({"present": c["shutdown_wlan_present"], "readable": c["shutdown_wlan_readable"]}, sort_keys=True)],
        ["wlan netdev", str(c["wlan_netdev_present"])],
        ["wiphy", str(c["wiphy_present"])],
    ]
    config_rows = [[key, value] for key, value in sorted(c["config"].items())]
    candidate_rows = [[line] for line in (c["debugfs_readiness_candidates"] + c["sysfs_readiness_candidates"])[:40]]
    dmesg_rows = [[line] for line in c["dmesg_readiness_tail"][-40:]]
    lines = [
        "# ICNSS/WLFW Readiness Surface Observer\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: {manifest['reason']}\n",
        f"- packet_transmission: `{manifest['packet_transmission']}`\n",
        f"- qmi_payload: `{manifest['qmi_payload']}`\n",
        f"- daemon_execution: `{manifest['daemon_execution']}`\n",
        f"- sysfs_write: `{manifest['sysfs_write']}`\n\n",
        "## Overview\n\n",
        markdown_table(["field", "value"], overview_rows),
        "\n\n## Checks\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}` ({item['severity']}): {item['detail']}\n")
    lines.extend([
        "\n## Readiness Candidate Paths\n\n",
        markdown_table(["path"], candidate_rows if candidate_rows else [["none"]]),
        "\n\n## Readiness Kernel Log Tail\n\n",
        markdown_table(["line"], dmesg_rows if dmesg_rows else [["none"]]),
        "\n\n## Kernel Config Sample\n\n",
        markdown_table(["key", "value"], config_rows),
        "\n\n## Source References\n\n",
    ])
    for item in manifest["source_references"]:
        lines.append(f"- {item}\n")
    lines.append("\n## Guardrails\n\n")
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def run(args: argparse.Namespace) -> int:
    validate_no_denied_commands(args)
    store = EvidenceStore(repo_path(args.out_dir))
    captures_list, raw_texts = capture_commands(args, store)
    captures = by_name(captures_list)
    classification = build_classification(captures, raw_texts)
    checks = build_checks(args, captures, raw_texts, classification)
    pass_ok, decision, reason = classify(checks, classification)
    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(repo_path(args.out_dir)),
        "packet_transmission": False,
        "qmi_payload": False,
        "daemon_execution": False,
        "sysfs_write": False,
        "debugfs_mount": False,
        "host_metadata": collect_host_metadata(),
        "source_references": list(SOURCE_REFERENCES),
        "classification": classification,
        "checks": checks,
        "captures": captures_list,
        "guardrails": [
            "no daemon/service start",
            "no QRTR nameservice packet or QMI payload",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill unblock, ICNSS bind/unbind, driver_override, recovery, ramdump, or assert controls",
            "no sysfs/debugfs/configfs/control writes",
            "no debugfs mount by default",
            "no reboot or remount",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"out_dir: {repo_path(args.out_dir)}")
    return 0 if pass_ok else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "run":
        return run(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
