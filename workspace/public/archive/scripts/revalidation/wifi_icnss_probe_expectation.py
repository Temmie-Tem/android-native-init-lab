#!/usr/bin/env python3
"""v281 read-only ICNSS probe expectation comparator."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v281-icnss-probe-expectation")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_TOYBOX = "/cache/bin/toybox"

ICNSS_NODE = "/sys/devices/platform/soc/18800000.qcom,icnss"
ICNSS_DRIVER = "/sys/bus/platform/drivers/icnss"
ICNSS_DRIVER_DEVICE = f"{ICNSS_DRIVER}/18800000.qcom,icnss"
QCA6390_NODE = "/sys/devices/platform/soc/a0000000.qcom,cnss-qca6390"
WLAN_MODULE = "/sys/module/wlan"
DT_ICNSS = "/sys/firmware/devicetree/base/soc/qcom,icnss@18800000"
DT_QCA6390 = "/sys/firmware/devicetree/base/soc/qcom,cnss-qca6390@a0000000"

SOURCE_EXPECTATIONS = {
    "driver_name": "icnss",
    "of_compatible": "qcom,icnss",
    "core_probe_expectations": [
        "ICNSS platform device binds to /sys/bus/platform/drivers/icnss",
        "probe reads regulators, clocks, MEM_BASE, IRQs, MSA memory, and SMMU resources",
        "probe registers WLFW firmware service/QMI event handling",
        "icnss_register_driver stores WLAN host-driver ops",
        "actual WLAN host-driver probe waits for FW_READY or SKIP_QMI",
    ],
    "safe_read_only_expected_surfaces": [
        ICNSS_NODE,
        ICNSS_DRIVER,
        ICNSS_DRIVER_DEVICE,
        WLAN_MODULE,
        DT_ICNSS,
        DT_QCA6390,
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
    ("stat-icnss-node", ("stat", ICNSS_NODE), 10.0, True),
    ("cat-icnss-uevent", ("cat", f"{ICNSS_NODE}/uevent"), 10.0, True),
    ("cat-icnss-modalias", ("cat", f"{ICNSS_NODE}/modalias"), 10.0, False),
    ("stat-icnss-driver", ("stat", ICNSS_DRIVER), 10.0, True),
    ("stat-icnss-driver-device", ("stat", ICNSS_DRIVER_DEVICE), 10.0, True),
    ("find-icnss-node", ("run", DEFAULT_TOYBOX, "find", ICNSS_NODE, "-maxdepth", "4"), 30.0, False),
    ("find-icnss-driver", ("run", DEFAULT_TOYBOX, "find", ICNSS_DRIVER, "-maxdepth", "3"), 30.0, False),
    ("stat-qca6390-node", ("stat", QCA6390_NODE), 10.0, True),
    ("cat-qca6390-uevent", ("cat", f"{QCA6390_NODE}/uevent"), 10.0, False),
    ("stat-qca6390-driver", ("stat", f"{QCA6390_NODE}/driver"), 10.0, False),
    ("stat-wlan-module", ("stat", WLAN_MODULE), 10.0, True),
    ("find-wlan-module-parameters", ("run", DEFAULT_TOYBOX, "find", f"{WLAN_MODULE}/parameters", "-maxdepth", "1"), 20.0, False),
    ("cat-wlan-fwpath", ("cat", f"{WLAN_MODULE}/parameters/fwpath"), 10.0, False),
    ("cat-wlan-con-mode", ("cat", f"{WLAN_MODULE}/parameters/con_mode"), 10.0, False),
    ("find-icnss-module", ("run", DEFAULT_TOYBOX, "find", "/sys/module/icnss", "-maxdepth", "3"), 20.0, False),
    ("cat-icnss-quirks", ("cat", "/sys/module/icnss/parameters/quirks"), 10.0, False),
    ("cat-icnss-dynamic-feature-mask", ("cat", "/sys/module/icnss/parameters/dynamic_feature_mask"), 10.0, False),
    ("stat-dt-icnss", ("stat", DT_ICNSS), 10.0, True),
    ("find-dt-icnss", ("run", DEFAULT_TOYBOX, "find", DT_ICNSS, "-maxdepth", "2"), 30.0, False),
    ("stat-dt-icnss-wlan-msa-memory", ("stat", f"{DT_ICNSS}/qcom,wlan-msa-memory"), 10.0, False),
    ("stat-dt-icnss-wlan-msa-fixed-region", ("stat", f"{DT_ICNSS}/qcom,wlan-msa-fixed-region"), 10.0, False),
    ("stat-dt-qca6390", ("stat", DT_QCA6390), 10.0, True),
    ("find-dt-qca6390", ("run", DEFAULT_TOYBOX, "find", DT_QCA6390, "-maxdepth", "2"), 30.0, False),
    ("cat-proc-modules", ("run", DEFAULT_TOYBOX, "cat", "/proc/modules"), 20.0, True),
    ("run-zcat-proc-config", ("run", DEFAULT_TOYBOX, "zcat", "/proc/config.gz"), 20.0, False),
    ("run-dmesg", ("run", DEFAULT_TOYBOX, "dmesg"), 30.0, False),
    ("cat-proc-net-dev", ("cat", "/proc/net/dev"), 10.0, True),
    ("ls-sys-class-net", ("ls", "/sys/class/net"), 10.0, True),
    ("ls-sys-class-ieee80211", ("ls", "/sys/class/ieee80211"), 10.0, False),
    ("ps-A-pid-stat-comm", ("run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm"), 20.0, True),
)

CONFIG_KEYS = (
    "CONFIG_ICNSS",
    "CONFIG_ICNSS_QMI",
    "CONFIG_ICNSS_DEBUG",
    "CONFIG_CNSS_UTILS",
    "CONFIG_WLAN",
    "CONFIG_QCA_CLD_WLAN",
    "CONFIG_CNSS2",
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
    return bool(re.search(r"^\s*wlan\S*:", text, re.MULTILINE) or re.search(r"(^|\s)(wlan\S*|swlan\S*|p2p\S*|wifi-aware\S*)(\s|$)", text))


def filter_log_lines(text: str) -> list[str]:
    wanted = re.compile(r"(icnss|qca6390|wlan|wlfw|fw_ready|fw is not ready|driver probe|qmi)", re.IGNORECASE)
    return [line for line in clean_lines(text) if wanted.search(line)][-100:]


def build_classification(captures: dict[str, dict[str, Any]], raw_texts: dict[str, str]) -> dict[str, Any]:
    icnss_uevent = parse_key_values(capture_text(raw_texts, "cat-icnss-uevent"))
    qca_uevent = parse_key_values(capture_text(raw_texts, "cat-qca6390-uevent"))
    proc_modules = capture_text(raw_texts, "cat-proc-modules")
    proc_net = capture_text(raw_texts, "cat-proc-net-dev")
    sys_net = capture_text(raw_texts, "ls-sys-class-net")
    ieee80211 = capture_text(raw_texts, "ls-sys-class-ieee80211")
    process_text = capture_text(raw_texts, "ps-A-pid-stat-comm")
    process_summary = summarize_cnss_processes(parse_ps_stat_comm(process_text)) if process_text else None
    config = parse_config(capture_text(raw_texts, "run-zcat-proc-config"))
    dmesg_lines = filter_log_lines(capture_text(raw_texts, "run-dmesg"))
    wlan_params = {
        "fwpath": " ".join(clean_lines(capture_text(raw_texts, "cat-wlan-fwpath"))),
        "con_mode": " ".join(clean_lines(capture_text(raw_texts, "cat-wlan-con-mode"))),
    }
    icnss_module_params = {
        "quirks": " ".join(clean_lines(capture_text(raw_texts, "cat-icnss-quirks"))),
        "dynamic_feature_mask": " ".join(clean_lines(capture_text(raw_texts, "cat-icnss-dynamic-feature-mask"))),
    }
    return {
        "source_expectations": SOURCE_EXPECTATIONS,
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
        "icnss_module_loaded": module_loaded(proc_modules, "icnss"),
        "dt_icnss_present": capture_ok(captures, "stat-dt-icnss"),
        "dt_qca6390_present": capture_ok(captures, "stat-dt-qca6390"),
        "dt_msa_memory_present": capture_ok(captures, "stat-dt-icnss-wlan-msa-memory"),
        "dt_msa_fixed_region_present": capture_ok(captures, "stat-dt-icnss-wlan-msa-fixed-region"),
        "wlan_params": wlan_params,
        "icnss_module_params": icnss_module_params,
        "icnss_node_sample": clean_lines(capture_text(raw_texts, "find-icnss-node"))[:60],
        "icnss_driver_sample": clean_lines(capture_text(raw_texts, "find-icnss-driver"))[:60],
        "wlan_module_sample": clean_lines(capture_text(raw_texts, "find-wlan-module-parameters"))[:60],
        "dt_icnss_sample": clean_lines(capture_text(raw_texts, "find-dt-icnss"))[:60],
        "dt_qca6390_sample": clean_lines(capture_text(raw_texts, "find-dt-qca6390"))[:60],
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
        {"name": "source-expectation-has-icnss", "pass": SOURCE_EXPECTATIONS["driver_name"] == "icnss", "severity": "critical", "detail": SOURCE_EXPECTATIONS["of_compatible"]},
        {"name": "icnss-core-bound", "pass": classification["icnss_node_present"] and classification["icnss_driver_present"] and classification["icnss_driver_device_present"], "severity": "critical", "detail": json.dumps({"node": classification["icnss_node_present"], "driver": classification["icnss_driver_present"], "driver_device": classification["icnss_driver_device_present"]}, sort_keys=True)},
        {"name": "icnss-compatible-visible", "pass": classification["icnss_compatible"], "severity": "critical", "detail": json.dumps(classification["icnss_uevent"], sort_keys=True)},
        {"name": "qca6390-context-visible", "pass": classification["qca6390_node_present"] and classification["qca6390_compatible"], "severity": "critical", "detail": json.dumps({"node": classification["qca6390_node_present"], "compatible": classification["qca6390_compatible"], "driver": classification["qca6390_driver_present"]}, sort_keys=True)},
        {"name": "wlan-module-surface", "pass": classification["wlan_module_sysfs_present"] or classification["wlan_module_loaded"], "severity": "critical", "detail": json.dumps({"sysfs": classification["wlan_module_sysfs_present"], "proc_modules": classification["wlan_module_loaded"]}, sort_keys=True)},
        {"name": "cnss-process-clean", "pass": bool(process_summary.get("clean")), "severity": "critical", "detail": json.dumps({"target_process_count": process_summary.get("target_process_count"), "target_running_count": process_summary.get("target_running_count"), "target_zombie_count": process_summary.get("target_zombie_count")}, sort_keys=True)},
        {"name": "no-wlan-readiness-surface", "pass": not classification["wlan_netdev_present"] and not classification["wiphy_present"], "severity": "critical", "detail": json.dumps({"netdev": classification["wlan_netdev_present"], "wiphy": classification["wiphy_present"]}, sort_keys=True)},
        {"name": "icnss-config-readable", "pass": any(value != "unset" for value in classification["config"].values()), "severity": "warning", "detail": json.dumps(classification["config"], sort_keys=True)},
        {"name": "icnss-dt-resources-visible", "pass": classification["dt_icnss_present"] and (classification["dt_msa_memory_present"] or classification["dt_msa_fixed_region_present"]), "severity": "warning", "detail": json.dumps({"dt_icnss": classification["dt_icnss_present"], "msa_memory": classification["dt_msa_memory_present"], "msa_fixed_region": classification["dt_msa_fixed_region_present"]}, sort_keys=True)},
        {"name": "kernel-log-readable", "pass": capture_ok(captures, "run-dmesg"), "severity": "warning", "detail": f"filtered_lines={classification['dmesg_relevant_count']}"},
    ]


def classify(checks: list[dict[str, Any]], classification: dict[str, Any]) -> tuple[bool, str, str]:
    critical_failed = [item["name"] for item in checks if item.get("severity") == "critical" and not item.get("pass")]
    if critical_failed:
        return False, "icnss-probe-expectation-incomplete", "critical checks failed: " + ", ".join(critical_failed)
    if classification["wlan_netdev_present"] or classification["wiphy_present"]:
        return True, "icnss-wlan-readiness-visible", "WLAN netdev/wiphy readiness surface is visible"
    if classification["qca6390_driver_present"]:
        return True, "icnss-qca6390-driver-bound-no-readiness", "QCA6390 driver link exists but no WLAN readiness is visible"
    if classification["icnss_driver_device_present"] and classification["wlan_module_sysfs_present"]:
        return True, "icnss-core-bound-host-driver-waits-fw", "ICNSS core is bound and WLAN host surface exists, but no firmware-ready/netdev surface is visible"
    return True, "icnss-core-present-no-host-readiness", "ICNSS core exists but expected WLAN host readiness surfaces are incomplete"


def render_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    config_rows = [[key, value] for key, value in sorted(c["config"].items())]
    dmesg_rows = [[line] for line in c["dmesg_relevant_tail"][-30:]]
    lines = [
        "# ICNSS Probe Expectation Comparator\n\n",
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
                ["live icnss compatible", str(c["icnss_compatible"])],
                ["live icnss driver-device", str(c["icnss_driver_device_present"])],
                ["live qca6390 compatible", str(c["qca6390_compatible"])],
                ["live qca6390 driver", str(c["qca6390_driver_present"])],
                ["wlan module sysfs", str(c["wlan_module_sysfs_present"])],
                ["wlan module loaded", str(c["wlan_module_loaded"])],
                ["wlan params", json.dumps(c["wlan_params"], sort_keys=True)],
                ["icnss params", json.dumps(c["icnss_module_params"], sort_keys=True)],
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
        "host_metadata": collect_host_metadata(),
        "source_references": [
            "https://android.googlesource.com/kernel/msm/+/c90c7feeca2f5839ad6824f816c0bd207602a2f4/drivers/soc/qcom/icnss.c",
            "https://android.googlesource.com/kernel/msm/+/15cf51a0f2ebde6529357685543e0b4170fb3b5c/drivers/soc/qcom/Kconfig",
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
