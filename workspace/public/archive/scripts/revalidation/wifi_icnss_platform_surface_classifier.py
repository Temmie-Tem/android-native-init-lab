#!/usr/bin/env python3
"""v277 read-only ICNSS/CNSS platform surface classifier."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v277-icnss-platform-surface")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_V276_MANIFEST = Path("tmp/wifi/v276-qrtr-cnss-registration-correlation/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"

ICNSS_NODE = "/sys/devices/platform/soc/18800000.qcom,icnss"
ICNSS_DRIVER = "/sys/bus/platform/drivers/icnss"
ICNSS_DRIVER_DEVICE = f"{ICNSS_DRIVER}/18800000.qcom,icnss"
QCA6390_NODE = "/sys/devices/platform/soc/a0000000.qcom,cnss-qca6390"
QCA6390_DRIVER = f"{QCA6390_NODE}/driver"
WLAN_MODULE = "/sys/module/wlan"
FIRMWARE_PATH = "/sys/module/firmware_class/parameters/path"
DT_ICNSS = "/sys/firmware/devicetree/base/soc/qcom,icnss@18800000"
DT_QCA6390 = "/sys/firmware/devicetree/base/soc/qcom,cnss-qca6390@a0000000"

DENIED_COMMAND_PATTERNS = (
    re.compile(r"\b/vendor/bin/cnss-daemon\b", re.IGNORECASE),
    re.compile(r"\bcnss_diag\b", re.IGNORECASE),
    re.compile(r"--allow-qrtr-ns-transmit", re.IGNORECASE),
    re.compile(r"\ba90_qrtr_ns_probe\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|android\.hardware\.wifi)\b", re.IGNORECASE),
    re.compile(r"\b(?:dhcpcd|udhcpc|dnsmasq)\b", re.IGNORECASE),
    re.compile(r"\b/sys/bus/platform/drivers/icnss/(?:bind|unbind)\b", re.IGNORECASE),
    re.compile(r"\bdriver_override\b", re.IGNORECASE),
    re.compile(r"\bsetprop\b|\bctl\.start\b|\bclass_start\b", re.IGNORECASE),
    re.compile(r">\s*/sys/|\btee\b.*\s/sys/|\becho\b.*\s/sys/", re.IGNORECASE),
)

COMMANDS: tuple[tuple[str, tuple[str, ...], float, bool], ...] = (
    ("version", ("version",), 10.0, True),
    ("status", ("status",), 15.0, True),
    ("selftest-verbose", ("selftest", "verbose"), 20.0, True),
    ("stat-icnss-node", ("stat", ICNSS_NODE), 10.0, True),
    ("cat-icnss-uevent", ("cat", f"{ICNSS_NODE}/uevent"), 10.0, False),
    ("cat-icnss-modalias", ("cat", f"{ICNSS_NODE}/modalias"), 10.0, False),
    ("stat-icnss-driver", ("stat", ICNSS_DRIVER), 10.0, True),
    ("stat-icnss-driver-device", ("stat", ICNSS_DRIVER_DEVICE), 10.0, False),
    ("find-icnss-node", ("run", DEFAULT_TOYBOX, "find", ICNSS_NODE, "-maxdepth", "4"), 30.0, False),
    ("find-icnss-driver", ("run", DEFAULT_TOYBOX, "find", ICNSS_DRIVER, "-maxdepth", "3"), 30.0, False),
    ("stat-qca6390-node", ("stat", QCA6390_NODE), 10.0, False),
    ("cat-qca6390-uevent", ("cat", f"{QCA6390_NODE}/uevent"), 10.0, False),
    ("cat-qca6390-modalias", ("cat", f"{QCA6390_NODE}/modalias"), 10.0, False),
    ("stat-qca6390-driver", ("stat", QCA6390_DRIVER), 10.0, False),
    ("find-qca6390-node", ("run", DEFAULT_TOYBOX, "find", QCA6390_NODE, "-maxdepth", "4"), 30.0, False),
    ("stat-wlan-module", ("stat", WLAN_MODULE), 10.0, False),
    ("find-wlan-module", ("run", DEFAULT_TOYBOX, "find", WLAN_MODULE, "-maxdepth", "3"), 30.0, False),
    ("cat-proc-modules", ("run", DEFAULT_TOYBOX, "cat", "/proc/modules"), 20.0, True),
    ("cat-firmware-path", ("cat", FIRMWARE_PATH), 10.0, False),
    ("ls-sys-class-net", ("ls", "/sys/class/net"), 10.0, True),
    ("ls-sys-class-rfkill", ("ls", "/sys/class/rfkill"), 10.0, False),
    ("cat-rfkill0-name", ("cat", "/sys/class/rfkill/rfkill0/name"), 10.0, False),
    ("cat-rfkill0-type", ("cat", "/sys/class/rfkill/rfkill0/type"), 10.0, False),
    ("cat-rfkill1-name", ("cat", "/sys/class/rfkill/rfkill1/name"), 10.0, False),
    ("cat-rfkill1-type", ("cat", "/sys/class/rfkill/rfkill1/type"), 10.0, False),
    ("ls-sys-class-ieee80211", ("ls", "/sys/class/ieee80211"), 10.0, False),
    ("find-dt-icnss", ("run", DEFAULT_TOYBOX, "find", DT_ICNSS, "-maxdepth", "3"), 30.0, False),
    ("find-dt-qca6390", ("run", DEFAULT_TOYBOX, "find", DT_QCA6390, "-maxdepth", "3"), 30.0, False),
    ("ps-A-pid-stat-comm", ("run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm"), 20.0, True),
    ("cat-proc-net-dev", ("cat", "/proc/net/dev"), 10.0, True),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        return {"missing": True, "path": str(full), "pass": False, "decision": "missing"}
    payload = json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"missing": True, "path": str(full), "pass": False, "decision": "not-object"}
    payload["_manifest_path"] = str(full)
    return payload


def replace_defaults(command: tuple[str, ...], args: argparse.Namespace) -> list[str]:
    return [args.toybox if part == DEFAULT_TOYBOX else part for part in command]


def validate_no_denied_commands(args: argparse.Namespace) -> None:
    text = "\n".join(" ".join(replace_defaults(command, args)) for _, command, _, _ in COMMANDS)
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def capture_commands(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("captures")
    records: list[dict[str, Any]] = []
    for name, command, timeout, required in COMMANDS:
        actual = replace_defaults(command, args)
        capture = run_capture(args, name, actual, timeout=timeout)
        text = capture.text if capture.text else capture.error + "\n"
        store.write_text(f"captures/{safe_name(name)}.txt", text)
        item = capture_to_manifest(capture)
        item["required"] = required
        records.append(item)
    return records


def by_name(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in captures}


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return bool(item.get("ok")) and item.get("rc") == 0 and item.get("status") == "ok"


def capture_text(captures: dict[str, dict[str, Any]], name: str) -> str:
    item = captures.get(name, {})
    if not item.get("text"):
        return ""
    return strip_cmdv1_text(str(item.get("text", "")))


def non_noise_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("a90:/#", "A90P1 ", "[done]", "[err]", "[exit", "run: pid=")):
            continue
        lines.append(line)
    return lines


def text_has_wlan_netdev(text: str) -> bool:
    return bool(re.search(r"^\s*wlan\S*:", text, re.MULTILINE) or re.search(r"(^|\s)(wlan\S*|swlan\S*|p2p\S*|wifi-aware\S*)(\s|$)", text))


def module_loaded(proc_modules: str, module_name: str) -> bool:
    return bool(re.search(rf"^{re.escape(module_name)}\s", proc_modules, re.MULTILINE))


def rfkill_wifi_present(captures: dict[str, dict[str, Any]]) -> bool:
    names = "\n".join(
        capture_text(captures, name)
        for name in ("cat-rfkill0-name", "cat-rfkill0-type", "cat-rfkill1-name", "cat-rfkill1-type")
    ).lower()
    return "wlan" in names or "wifi" in names or "wireless" in names


def build_classification(captures: dict[str, dict[str, Any]], v276: dict[str, Any]) -> dict[str, Any]:
    sys_class_net = capture_text(captures, "ls-sys-class-net")
    proc_net_dev = capture_text(captures, "cat-proc-net-dev")
    ieee80211 = capture_text(captures, "ls-sys-class-ieee80211")
    proc_modules = capture_text(captures, "cat-proc-modules")
    process_text = capture_text(captures, "ps-A-pid-stat-comm")
    process_summary = summarize_cnss_processes(parse_ps_stat_comm(process_text)) if process_text else None
    icnss_lines = non_noise_lines(capture_text(captures, "find-icnss-node"))
    qca_lines = non_noise_lines(capture_text(captures, "find-qca6390-node"))
    wlan_module_lines = non_noise_lines(capture_text(captures, "find-wlan-module"))
    dt_lines = non_noise_lines(capture_text(captures, "find-dt-icnss")) + non_noise_lines(capture_text(captures, "find-dt-qca6390"))
    return {
        "v276_decision": v276.get("decision"),
        "v276_pass": v276.get("pass") is True,
        "icnss_node_present": capture_ok(captures, "stat-icnss-node"),
        "icnss_driver_present": capture_ok(captures, "stat-icnss-driver"),
        "icnss_driver_device_present": capture_ok(captures, "stat-icnss-driver-device"),
        "qca6390_node_present": capture_ok(captures, "stat-qca6390-node"),
        "qca6390_driver_present": capture_ok(captures, "stat-qca6390-driver"),
        "wlan_module_sysfs_present": capture_ok(captures, "stat-wlan-module"),
        "wlan_module_loaded": module_loaded(proc_modules, "wlan"),
        "firmware_path": " ".join(non_noise_lines(capture_text(captures, "cat-firmware-path"))),
        "wlan_netdev_present": text_has_wlan_netdev(sys_class_net) or text_has_wlan_netdev(proc_net_dev),
        "wiphy_present": bool(re.search(r"(^|\s)phy\d+(\s|$)", ieee80211)),
        "wifi_rfkill_present": rfkill_wifi_present(captures),
        "process_summary": process_summary,
        "icnss_line_count": len(icnss_lines),
        "qca6390_line_count": len(qca_lines),
        "wlan_module_line_count": len(wlan_module_lines),
        "dt_line_count": len(dt_lines),
        "icnss_sample": icnss_lines[:30],
        "qca6390_sample": qca_lines[:30],
        "wlan_module_sample": wlan_module_lines[:30],
        "dt_sample": dt_lines[:30],
    }


def build_checks(args: argparse.Namespace,
                 captures: dict[str, dict[str, Any]],
                 classification: dict[str, Any]) -> list[dict[str, Any]]:
    version_text = capture_text(captures, "version")
    required_failed = [name for name, _, _, required in COMMANDS if required and not capture_ok(captures, name)]
    process_summary = classification.get("process_summary") or {}
    return [
        {
            "name": "expected-version",
            "pass": args.expect_version in version_text,
            "severity": "critical",
            "detail": args.expect_version,
        },
        {
            "name": "required-live-captures",
            "pass": not required_failed,
            "severity": "critical",
            "detail": "failed=" + json.dumps(required_failed),
        },
        {
            "name": "v276-prerequisite",
            "pass": classification["v276_pass"] and classification["v276_decision"] == "qrtr-cnss-platform-surface-visible",
            "severity": "critical",
            "detail": str(classification["v276_decision"]),
        },
        {
            "name": "icnss-platform-present",
            "pass": classification["icnss_node_present"] and classification["icnss_driver_present"],
            "severity": "critical",
            "detail": json.dumps({
                "node": classification["icnss_node_present"],
                "driver": classification["icnss_driver_present"],
                "driver_device": classification["icnss_driver_device_present"],
            }, sort_keys=True),
        },
        {
            "name": "qca6390-surface-present",
            "pass": classification["qca6390_node_present"],
            "severity": "critical",
            "detail": json.dumps({
                "node": classification["qca6390_node_present"],
                "driver": classification["qca6390_driver_present"],
            }, sort_keys=True),
        },
        {
            "name": "wlan-module-surface-present",
            "pass": classification["wlan_module_sysfs_present"] or classification["wlan_module_loaded"],
            "severity": "critical",
            "detail": json.dumps({
                "sysfs": classification["wlan_module_sysfs_present"],
                "proc_modules": classification["wlan_module_loaded"],
            }, sort_keys=True),
        },
        {
            "name": "cnss-process-clean",
            "pass": bool(process_summary.get("clean")),
            "severity": "critical",
            "detail": json.dumps({
                "target_process_count": process_summary.get("target_process_count"),
                "target_running_count": process_summary.get("target_running_count"),
                "target_zombie_count": process_summary.get("target_zombie_count"),
            }, sort_keys=True),
        },
        {
            "name": "no-wlan-readiness-surface",
            "pass": not classification["wlan_netdev_present"] and not classification["wiphy_present"] and not classification["wifi_rfkill_present"],
            "severity": "critical",
            "detail": json.dumps({
                "netdev": classification["wlan_netdev_present"],
                "wiphy": classification["wiphy_present"],
                "wifi_rfkill": classification["wifi_rfkill_present"],
            }, sort_keys=True),
        },
        {
            "name": "devicetree-surface-collected",
            "pass": classification["dt_line_count"] > 0,
            "severity": "warning",
            "detail": f"dt_lines={classification['dt_line_count']}",
        },
    ]


def classify(checks: list[dict[str, Any]], classification: dict[str, Any]) -> tuple[bool, str, str]:
    critical_failed = [item["name"] for item in checks if item.get("severity") == "critical" and not item.get("pass")]
    if critical_failed:
        return False, "icnss-platform-incomplete", "critical platform checks failed: " + ", ".join(critical_failed)
    if classification["wlan_netdev_present"] or classification["wiphy_present"] or classification["wifi_rfkill_present"]:
        return True, "icnss-wlan-readiness-visible", "read-only state exposes wlan/wiphy/rfkill readiness surfaces"
    if classification["icnss_driver_device_present"] and classification["wlan_module_loaded"]:
        return True, "icnss-platform-bound-no-wlan-netdev", "ICNSS platform is bound and wlan module is loaded, but no wlan netdev/wiphy/rfkill is visible"
    return True, "icnss-platform-present-no-wlan-netdev", "ICNSS/QCA platform surfaces are present, but no wlan netdev/wiphy/rfkill is visible"


def render_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    lines = [
        "# ICNSS/CNSS Platform Surface Classifier\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: {manifest['reason']}\n",
        f"- packet_transmission: `{manifest['packet_transmission']}`\n",
        f"- daemon_execution: `{manifest['daemon_execution']}`\n",
        f"- sysfs_write: `{manifest['sysfs_write']}`\n\n",
        "## Checks\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}` ({item['severity']}): {item['detail']}\n")
    lines.extend([
        "\n## Classification\n\n",
        markdown_table(
            ["field", "value"],
            [
                ["icnss_node_present", str(c["icnss_node_present"])],
                ["icnss_driver_present", str(c["icnss_driver_present"])],
                ["icnss_driver_device_present", str(c["icnss_driver_device_present"])],
                ["qca6390_node_present", str(c["qca6390_node_present"])],
                ["qca6390_driver_present", str(c["qca6390_driver_present"])],
                ["wlan_module_sysfs_present", str(c["wlan_module_sysfs_present"])],
                ["wlan_module_loaded", str(c["wlan_module_loaded"])],
                ["wlan_netdev_present", str(c["wlan_netdev_present"])],
                ["wiphy_present", str(c["wiphy_present"])],
                ["wifi_rfkill_present", str(c["wifi_rfkill_present"])],
                ["firmware_path", c["firmware_path"]],
                ["icnss_line_count", str(c["icnss_line_count"])],
                ["qca6390_line_count", str(c["qca6390_line_count"])],
                ["wlan_module_line_count", str(c["wlan_module_line_count"])],
                ["dt_line_count", str(c["dt_line_count"])],
            ],
        ),
        "\n\n## Sample Surfaces\n\n",
    ])
    for name in ("icnss_sample", "qca6390_sample", "wlan_module_sample", "dt_sample"):
        lines.append(f"### {name}\n\n")
        sample = c.get(name, [])
        if not sample:
            lines.append("- none\n\n")
        else:
            for item in sample:
                lines.append(f"- `{item}`\n")
            lines.append("\n")
    lines.append("## Guardrails\n\n")
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def run(args: argparse.Namespace) -> int:
    validate_no_denied_commands(args)
    store = EvidenceStore(repo_path(args.out_dir))
    v276 = load_json(args.v276_manifest)
    captures_list = capture_commands(args, store)
    captures = by_name(captures_list)
    classification = build_classification(captures, v276)
    checks = build_checks(args, captures, classification)
    pass_ok, decision, reason = classify(checks, classification)
    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(repo_path(args.out_dir)),
        "packet_transmission": False,
        "daemon_execution": False,
        "sysfs_write": False,
        "host_metadata": collect_host_metadata(),
        "inputs": {"v276_manifest": str(repo_path(args.v276_manifest))},
        "classification": classification,
        "checks": checks,
        "captures": captures_list,
        "guardrails": [
            "no sysfs/control writes",
            "no ICNSS bind/unbind/driver_override/recovery/ramdump/assert controls",
            "no daemon/service start",
            "no QRTR nameservice packet or QMI payload",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
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
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v276-manifest", type=Path, default=DEFAULT_V276_MANIFEST)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "run":
        return run(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
