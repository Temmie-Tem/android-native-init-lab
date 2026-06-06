#!/usr/bin/env python3
"""v280 no-start CNSS/QCA6390 probe expectation comparator.

The tool compares source-derived CNSS2 driver expectations against current
read-only live sysfs/kernel state.  It does not start daemons, transmit QRTR/QMI
packets, or write sysfs/control paths.
"""

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
import wifi_qca6390_driver_param_classifier as qca  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v280-cnss-qca6390-probe-expectation")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_TOYBOX = "/cache/bin/toybox"

QCA6390_NODE = qca.QCA6390_NODE
QCA6390_DRIVER = qca.QCA6390_DRIVER
CNSS2_DRIVER = "/sys/bus/platform/drivers/cnss2"
ICNSS_DRIVER = "/sys/bus/platform/drivers/icnss"
KERNEL_CNSS_LINK = "/sys/kernel/cnss"
KERNEL_SHUTDOWN_WLAN_LINK = "/sys/kernel/shutdown_wlan"

SOURCE_EXPECTATIONS = {
    "source": "android.googlesource.com/kernel/msm.git cnss2/main.c",
    "driver_name": "cnss2",
    "of_compatible": "qcom,cnss-qca6390",
    "device_id_name": "qca6390",
    "probe_steps": [
        "of_match_device(cnss_of_match_table)",
        "cnss_get_resources",
        "cnss_power_on_device",
        "cnss_bus_init",
        "cnss_create_sysfs",
        "cnss_event_work_init",
        "cnss_qmi_init",
        "cnss_misc_init",
    ],
    "expected_sysfs_after_probe": [
        KERNEL_CNSS_LINK,
        KERNEL_SHUTDOWN_WLAN_LINK,
        f"{QCA6390_NODE}/driver",
    ],
}

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
)

COMMANDS: tuple[tuple[str, tuple[str, ...], float, bool], ...] = (
    ("version", ("version",), 10.0, True),
    ("status", ("status",), 20.0, True),
    ("cat-qca6390-uevent", ("cat", f"{QCA6390_NODE}/uevent"), 10.0, True),
    ("cat-qca6390-modalias", ("cat", f"{QCA6390_NODE}/modalias"), 10.0, True),
    ("stat-qca6390-driver", ("stat", QCA6390_DRIVER), 10.0, False),
    ("stat-qca6390-driver-override", ("stat", f"{QCA6390_NODE}/driver_override"), 10.0, False),
    ("cat-qca6390-driver-override", ("cat", f"{QCA6390_NODE}/driver_override"), 10.0, False),
    ("stat-cnss2-driver", ("stat", CNSS2_DRIVER), 10.0, False),
    ("stat-icnss-driver", ("stat", ICNSS_DRIVER), 10.0, True),
    ("stat-kernel-cnss", ("stat", KERNEL_CNSS_LINK), 10.0, False),
    ("stat-kernel-shutdown-wlan", ("stat", KERNEL_SHUTDOWN_WLAN_LINK), 10.0, False),
    ("ls-platform-drivers", ("ls", "/sys/bus/platform/drivers"), 20.0, True),
    ("find-qca6390-nodes", ("run", DEFAULT_TOYBOX, "find", "/sys", "-maxdepth", "8", "-name", "*qca6390*"), 30.0, False),
    ("find-cnss-nodes", ("run", DEFAULT_TOYBOX, "find", "/sys", "-maxdepth", "8", "-name", "*cnss*"), 30.0, False),
    ("cat-proc-net-dev", ("cat", "/proc/net/dev"), 10.0, True),
    ("ls-sys-class-net", ("ls", "/sys/class/net"), 10.0, True),
    ("ls-sys-class-ieee80211", ("ls", "/sys/class/ieee80211"), 10.0, False),
    ("run-ps-cnss", ("run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm"), 20.0, True),
    ("run-zcat-proc-config", ("run", DEFAULT_TOYBOX, "zcat", "/proc/config.gz"), 20.0, False),
    ("run-dmesg", ("run", DEFAULT_TOYBOX, "dmesg"), 30.0, False),
)

CONFIG_KEYS = (
    "CONFIG_CNSS2",
    "CONFIG_CNSS2_QMI",
    "CONFIG_CNSS_QCA6390",
    "CONFIG_CNSS_ASYNC",
    "CONFIG_CNSS_QMI_SVC",
    "CONFIG_CNSS_UTILS",
    "CONFIG_WLAN",
    "CONFIG_QCA_CLD_WLAN",
    "CONFIG_QCA_WIFI_CLD3",
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def replace_defaults(command: tuple[str, ...], args: argparse.Namespace) -> list[str]:
    return [args.toybox if part == DEFAULT_TOYBOX else part for part in command]


def validate_no_denied_commands(args: argparse.Namespace) -> None:
    text = "\n".join(" ".join(replace_defaults(command, args)) for _, command, _, _ in COMMANDS)
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


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


def ls_entry_name(line: str) -> str:
    parts = line.split()
    if len(parts) >= 3 and parts[0] in {"d", "-", "l"}:
        return parts[-1]
    return line


def parse_config(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$", line)
        if match:
            result[match.group(1)] = match.group(2).strip('"')
            continue
        match = re.match(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$", line)
        if match:
            result[match.group(1)] = "n"
    return {key: result.get(key, "unset") for key in CONFIG_KEYS}


def filter_log_lines(text: str) -> list[str]:
    wanted = re.compile(r"(cnss|qca6390|qca|wlan|icnss|ath11k|qmi)", re.IGNORECASE)
    lines = []
    for line in clean_lines(text):
        if wanted.search(line):
            lines.append(line)
    return lines[-80:]


def text_has_wlan_netdev(text: str) -> bool:
    return bool(re.search(r"^\s*wlan\S*:", text, re.MULTILINE) or re.search(r"(^|\s)(wlan\S*|swlan\S*|p2p\S*|wifi-aware\S*)(\s|$)", text))


def build_classification(args: argparse.Namespace,
                         captures: dict[str, dict[str, Any]],
                         raw_texts: dict[str, str]) -> dict[str, Any]:
    qca_uevent = qca.parse_uevent(capture_text(raw_texts, "cat-qca6390-uevent"))
    modalias = " ".join(clean_lines(capture_text(raw_texts, "cat-qca6390-modalias")))
    platform_drivers = clean_lines(capture_text(raw_texts, "ls-platform-drivers"))
    qca_nodes = clean_lines(capture_text(raw_texts, "find-qca6390-nodes"))
    cnss_nodes = clean_lines(capture_text(raw_texts, "find-cnss-nodes"))
    config = parse_config(capture_text(raw_texts, "run-zcat-proc-config"))
    dmesg_lines = filter_log_lines(capture_text(raw_texts, "run-dmesg"))
    proc_net = capture_text(raw_texts, "cat-proc-net-dev")
    sys_net = capture_text(raw_texts, "ls-sys-class-net")
    ieee80211 = capture_text(raw_texts, "ls-sys-class-ieee80211")
    process_text = capture_text(raw_texts, "run-ps-cnss")
    process_summary = summarize_cnss_processes(parse_ps_stat_comm(process_text)) if process_text else None
    qca_compatible = qca_uevent.get("OF_COMPATIBLE_0") == "qcom,cnss-qca6390" or "qcom,cnss-qca6390" in modalias
    cnss_like_drivers = [
        ls_entry_name(line)
        for line in platform_drivers
        if re.search(r"(cnss|icnss|qca|wlan)", line, re.IGNORECASE)
    ]
    return {
        "source_expectations": SOURCE_EXPECTATIONS,
        "qca_uevent": qca_uevent,
        "qca_modalias": modalias,
        "qca_compatible": qca_compatible,
        "qca_driver_present": capture_ok(captures, "stat-qca6390-driver"),
        "qca_driver_override_present": capture_ok(captures, "stat-qca6390-driver-override"),
        "qca_driver_override_value": " ".join(clean_lines(capture_text(raw_texts, "cat-qca6390-driver-override"))),
        "cnss2_driver_present": capture_ok(captures, "stat-cnss2-driver"),
        "icnss_driver_present": capture_ok(captures, "stat-icnss-driver"),
        "kernel_cnss_link_present": capture_ok(captures, "stat-kernel-cnss"),
        "kernel_shutdown_wlan_link_present": capture_ok(captures, "stat-kernel-shutdown-wlan"),
        "platform_driver_candidates": cnss_like_drivers,
        "platform_driver_candidate_count": len(cnss_like_drivers),
        "qca_nodes": qca_nodes,
        "qca_node_count": len(qca_nodes),
        "cnss_nodes_sample": cnss_nodes[:80],
        "cnss_node_count": len(cnss_nodes),
        "config": config,
        "dmesg_relevant_tail": dmesg_lines,
        "dmesg_relevant_count": len(dmesg_lines),
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
        {"name": "source-expectation-has-qca6390", "pass": SOURCE_EXPECTATIONS["of_compatible"] == "qcom,cnss-qca6390", "severity": "critical", "detail": SOURCE_EXPECTATIONS["driver_name"]},
        {"name": "qca-compatible-visible", "pass": classification["qca_compatible"], "severity": "critical", "detail": json.dumps({"uevent": classification["qca_uevent"], "modalias": classification["qca_modalias"]}, sort_keys=True)},
        {"name": "cnss-process-clean", "pass": bool(process_summary.get("clean")), "severity": "critical", "detail": json.dumps({"target_process_count": process_summary.get("target_process_count"), "target_running_count": process_summary.get("target_running_count"), "target_zombie_count": process_summary.get("target_zombie_count")}, sort_keys=True)},
        {"name": "no-wlan-readiness-surface", "pass": not classification["wlan_netdev_present"] and not classification["wiphy_present"], "severity": "critical", "detail": json.dumps({"netdev": classification["wlan_netdev_present"], "wiphy": classification["wiphy_present"]}, sort_keys=True)},
        {"name": "platform-driver-candidates-visible", "pass": classification["platform_driver_candidate_count"] > 0, "severity": "warning", "detail": f"candidates={classification['platform_driver_candidate_count']}"},
        {"name": "kernel-config-readable", "pass": any(value != "unset" for value in classification["config"].values()), "severity": "warning", "detail": json.dumps(classification["config"], sort_keys=True)},
        {"name": "kernel-log-readable", "pass": capture_ok(captures, "run-dmesg"), "severity": "warning", "detail": f"filtered_lines={classification['dmesg_relevant_count']}"},
    ]


def classify(checks: list[dict[str, Any]], classification: dict[str, Any]) -> tuple[bool, str, str]:
    critical_failed = [item["name"] for item in checks if item.get("severity") == "critical" and not item.get("pass")]
    if critical_failed:
        return False, "cnss-qca6390-probe-expectation-incomplete", "critical checks failed: " + ", ".join(critical_failed)
    if classification["wlan_netdev_present"] or classification["wiphy_present"]:
        return True, "cnss-qca6390-readiness-visible", "WLAN netdev/wiphy readiness surface is visible"
    if classification["qca_driver_present"]:
        return True, "cnss-qca6390-driver-bound-no-readiness", "QCA6390 driver link exists but no wlan/wiphy readiness is visible"
    if not classification["cnss2_driver_present"]:
        return True, "cnss2-driver-dir-missing-qca-unbound", "source expects cnss2 driver binding, but live sysfs has no cnss2 platform driver directory and QCA6390 remains unbound"
    return True, "cnss2-driver-dir-present-qca-unbound", "cnss2 driver directory exists but QCA6390 remains unbound; probe failure or deferred binding should be investigated"


def render_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    config_rows = [[key, value] for key, value in sorted(c["config"].items())]
    driver_rows = [[item] for item in c["platform_driver_candidates"]]
    dmesg_rows = [[line] for line in c["dmesg_relevant_tail"][-30:]]
    lines = [
        "# CNSS QCA6390 Probe Expectation Comparator\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: {manifest['reason']}\n",
        f"- packet_transmission: `{manifest['packet_transmission']}`\n",
        f"- daemon_execution: `{manifest['daemon_execution']}`\n",
        f"- sysfs_write: `{manifest['sysfs_write']}`\n\n",
        "## Source Expectation vs Live State\n\n",
        markdown_table(
            ["field", "value"],
            [
                ["source driver", c["source_expectations"]["driver_name"]],
                ["source compatible", c["source_expectations"]["of_compatible"]],
                ["live qca compatible", str(c["qca_compatible"])],
                ["live qca driver link", str(c["qca_driver_present"])],
                ["live cnss2 driver dir", str(c["cnss2_driver_present"])],
                ["live icnss driver dir", str(c["icnss_driver_present"])],
                ["kernel cnss link", str(c["kernel_cnss_link_present"])],
                ["kernel shutdown_wlan link", str(c["kernel_shutdown_wlan_link_present"])],
                ["wlan netdev", str(c["wlan_netdev_present"])],
                ["wiphy", str(c["wiphy_present"])],
            ],
        ),
        "\n\n## Checks\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}` ({item['severity']}): {item['detail']}\n")
    lines.extend([
        "\n## Kernel Config Sample\n\n",
        markdown_table(["key", "value"], config_rows),
        "\n\n## Platform Driver Candidates\n\n",
        markdown_table(["path"], driver_rows if driver_rows else [["none"]]),
        "\n\n## Relevant Kernel Log Tail\n\n",
        markdown_table(["line"], dmesg_rows if dmesg_rows else [["none"]]),
        "\n\n## Guardrails\n\n",
    ])
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def run(args: argparse.Namespace) -> int:
    validate_no_denied_commands(args)
    store = EvidenceStore(repo_path(args.out_dir))
    captures_list, raw_texts = capture_commands(args, store)
    captures = by_name(captures_list)
    classification = build_classification(args, captures, raw_texts)
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
        "host_metadata": collect_host_metadata(),
        "source_references": [
            "https://android.googlesource.com/kernel/msm.git/+/28ec0fbdef41e99b01d87e5d4d267f72dddf1dec/drivers/net/wireless/cnss2/main.c",
            "https://android.googlesource.com/kernel/msm.git/+/89594f79eb3779e02c47b5fd47427c55497cd5c9/drivers/net/wireless/cnss2/Kconfig",
            "https://docs.kernel.org/driver-api/driver-model/binding.html",
        ],
        "classification": classification,
        "checks": checks,
        "captures": captures_list,
        "guardrails": [
            "no daemon/service start",
            "no QRTR nameservice packet or QMI payload",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill unblock, ICNSS bind/unbind, driver_override, recovery, ramdump, or assert controls",
            "no sysfs/control writes",
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
