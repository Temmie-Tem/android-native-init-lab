#!/usr/bin/env python3
"""v278 read-only QCA6390 driver-match and WLAN parameter classifier."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v278-qca6390-driver-param")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_V277_MANIFEST = Path("tmp/wifi/v277-icnss-platform-surface/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"

QCA6390_NODE = "/sys/devices/platform/soc/a0000000.qcom,cnss-qca6390"
QCA6390_DRIVER = f"{QCA6390_NODE}/driver"
WLAN_PARAM_ROOT = "/sys/module/wlan/parameters"
WLAN_PARAMS = (
    "fwpath",
    "con_mode",
    "country_code",
    "enable_11d",
    "enable_dfs_chan_scan",
    "con_mode_ftm",
    "con_mode_epping",
    "prealloc_disabled",
    "timer_multiplier",
)

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

BASE_COMMANDS: tuple[tuple[str, tuple[str, ...], float, bool], ...] = (
    ("version", ("version",), 10.0, True),
    ("status", ("status",), 15.0, True),
    ("cat-qca6390-uevent", ("cat", f"{QCA6390_NODE}/uevent"), 10.0, True),
    ("cat-qca6390-modalias", ("cat", f"{QCA6390_NODE}/modalias"), 10.0, True),
    ("stat-qca6390-driver", ("stat", QCA6390_DRIVER), 10.0, False),
    ("find-platform-driver-candidates", ("run", DEFAULT_TOYBOX, "find", "/sys/bus/platform/drivers", "-maxdepth", "2", "-name", "*cnss*", "-o", "-name", "*qca*", "-o", "-name", "*wlan*", "-o", "-name", "*icnss*"), 30.0, False),
    ("ls-sys-class-net", ("ls", "/sys/class/net"), 10.0, True),
    ("ls-sys-class-ieee80211", ("ls", "/sys/class/ieee80211"), 10.0, False),
    ("cat-rfkill0-name", ("cat", "/sys/class/rfkill/rfkill0/name"), 10.0, False),
    ("cat-rfkill0-type", ("cat", "/sys/class/rfkill/rfkill0/type"), 10.0, False),
    ("cat-rfkill1-name", ("cat", "/sys/class/rfkill/rfkill1/name"), 10.0, False),
    ("cat-rfkill1-type", ("cat", "/sys/class/rfkill/rfkill1/type"), 10.0, False),
    ("ps-A-pid-stat-comm", ("run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm"), 20.0, True),
    ("cat-proc-net-dev", ("cat", "/proc/net/dev"), 10.0, True),
)


def parameter_commands() -> tuple[tuple[str, tuple[str, ...], float, bool], ...]:
    return tuple((f"cat-wlan-param-{name}", ("cat", f"{WLAN_PARAM_ROOT}/{name}"), 10.0, False) for name in WLAN_PARAMS)


def all_commands() -> tuple[tuple[str, tuple[str, ...], float, bool], ...]:
    return BASE_COMMANDS + parameter_commands()


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
    text = "\n".join(" ".join(replace_defaults(command, args)) for _, command, _, _ in all_commands())
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def capture_commands(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("captures")
    records: list[dict[str, Any]] = []
    for name, command, timeout, required in all_commands():
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


def clean_scalar(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("a90:/#", "A90P1 ", "[done]", "[err]", "[exit", "run: pid=")):
            continue
        lines.append(line)
    return " ".join(lines).strip()


def parse_uevent(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip().replace("<NULL>", "")
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def text_has_wlan_netdev(text: str) -> bool:
    return bool(re.search(r"^\s*wlan\S*:", text, re.MULTILINE) or re.search(r"(^|\s)(wlan\S*|swlan\S*|p2p\S*|wifi-aware\S*)(\s|$)", text))


def rfkill_wifi_present(captures: dict[str, dict[str, Any]]) -> bool:
    names = "\n".join(
        capture_text(captures, name)
        for name in ("cat-rfkill0-name", "cat-rfkill0-type", "cat-rfkill1-name", "cat-rfkill1-type")
    ).lower()
    return "wlan" in names or "wifi" in names or "wireless" in names


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


def build_classification(captures: dict[str, dict[str, Any]], v277: dict[str, Any]) -> dict[str, Any]:
    qca_uevent = parse_uevent(capture_text(captures, "cat-qca6390-uevent"))
    qca_modalias = clean_scalar(capture_text(captures, "cat-qca6390-modalias")).replace("<NULL>", "")
    sys_class_net = capture_text(captures, "ls-sys-class-net")
    proc_net_dev = capture_text(captures, "cat-proc-net-dev")
    ieee80211 = capture_text(captures, "ls-sys-class-ieee80211")
    process_text = capture_text(captures, "ps-A-pid-stat-comm")
    process_summary = summarize_cnss_processes(parse_ps_stat_comm(process_text)) if process_text else None
    params: dict[str, str] = {}
    readable_params: list[str] = []
    missing_params: list[str] = []
    for param in WLAN_PARAMS:
        cap_name = f"cat-wlan-param-{param}"
        if capture_ok(captures, cap_name):
            readable_params.append(param)
            params[param] = clean_scalar(capture_text(captures, cap_name))
        else:
            missing_params.append(param)
    driver_candidates = non_noise_lines(capture_text(captures, "find-platform-driver-candidates"))
    return {
        "v277_decision": v277.get("decision"),
        "v277_pass": v277.get("pass") is True,
        "qca_uevent": qca_uevent,
        "qca_modalias": qca_modalias,
        "qca_compatible": qca_uevent.get("OF_COMPATIBLE_0") == "qcom,cnss-qca6390" or "qcom,cnss-qca6390" in qca_modalias,
        "qca_driver_present": capture_ok(captures, "stat-qca6390-driver"),
        "driver_candidates": driver_candidates,
        "driver_candidate_count": len(driver_candidates),
        "wlan_params": params,
        "wlan_param_readable_count": len(readable_params),
        "wlan_param_missing": missing_params,
        "wlan_netdev_present": text_has_wlan_netdev(sys_class_net) or text_has_wlan_netdev(proc_net_dev),
        "wiphy_present": bool(re.search(r"(^|\s)phy\d+(\s|$)", ieee80211)),
        "wifi_rfkill_present": rfkill_wifi_present(captures),
        "process_summary": process_summary,
    }


def build_checks(args: argparse.Namespace,
                 captures: dict[str, dict[str, Any]],
                 classification: dict[str, Any]) -> list[dict[str, Any]]:
    version_text = capture_text(captures, "version")
    required_failed = [name for name, _, _, required in all_commands() if required and not capture_ok(captures, name)]
    process_summary = classification.get("process_summary") or {}
    return [
        {"name": "expected-version", "pass": args.expect_version in version_text, "severity": "critical", "detail": args.expect_version},
        {"name": "required-live-captures", "pass": not required_failed, "severity": "critical", "detail": "failed=" + json.dumps(required_failed)},
        {"name": "v277-prerequisite", "pass": classification["v277_pass"] and classification["v277_decision"] == "icnss-platform-present-no-wlan-netdev", "severity": "critical", "detail": str(classification["v277_decision"])},
        {"name": "qca-compatible-visible", "pass": classification["qca_compatible"], "severity": "critical", "detail": json.dumps({"uevent": classification["qca_uevent"], "modalias": classification["qca_modalias"]}, sort_keys=True)},
        {"name": "wlan-params-readable", "pass": classification["wlan_param_readable_count"] >= 4, "severity": "critical", "detail": json.dumps({"readable": classification["wlan_param_readable_count"], "missing": classification["wlan_param_missing"]}, sort_keys=True)},
        {"name": "cnss-process-clean", "pass": bool(process_summary.get("clean")), "severity": "critical", "detail": json.dumps({"target_process_count": process_summary.get("target_process_count"), "target_running_count": process_summary.get("target_running_count"), "target_zombie_count": process_summary.get("target_zombie_count")}, sort_keys=True)},
        {"name": "no-wlan-readiness-surface", "pass": not classification["wlan_netdev_present"] and not classification["wiphy_present"] and not classification["wifi_rfkill_present"], "severity": "critical", "detail": json.dumps({"netdev": classification["wlan_netdev_present"], "wiphy": classification["wiphy_present"], "wifi_rfkill": classification["wifi_rfkill_present"]}, sort_keys=True)},
        {"name": "platform-driver-candidates-collected", "pass": classification["driver_candidate_count"] > 0, "severity": "warning", "detail": f"candidates={classification['driver_candidate_count']}"},
    ]


def classify(checks: list[dict[str, Any]], classification: dict[str, Any]) -> tuple[bool, str, str]:
    critical_failed = [item["name"] for item in checks if item.get("severity") == "critical" and not item.get("pass")]
    if critical_failed:
        return False, "qca6390-driver-param-incomplete", "critical driver/parameter checks failed: " + ", ".join(critical_failed)
    if classification["wlan_netdev_present"] or classification["wiphy_present"] or classification["wifi_rfkill_present"]:
        return True, "qca6390-wlan-readiness-visible", "read-only state exposes wlan/wiphy/rfkill readiness surfaces"
    if classification["qca_driver_present"]:
        return True, "qca6390-driver-bound-no-netdev", "QCA6390 driver link exists but no wlan netdev/wiphy/rfkill is visible"
    return True, "qca6390-match-visible-driver-unbound", "QCA6390 OF match is visible, but the platform node has no driver link and no WLAN readiness surface"


def render_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    param_rows = [[name, value] for name, value in sorted(c["wlan_params"].items())]
    driver_rows = [[line] for line in c["driver_candidates"]]
    lines = [
        "# QCA6390 Driver / WLAN Parameter Classifier\n\n",
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
                ["qca_compatible", str(c["qca_compatible"])],
                ["qca_modalias", c["qca_modalias"]],
                ["qca_driver_present", str(c["qca_driver_present"])],
                ["driver_candidate_count", str(c["driver_candidate_count"])],
                ["wlan_param_readable_count", str(c["wlan_param_readable_count"])],
                ["wlan_param_missing", ",".join(c["wlan_param_missing"])],
                ["wlan_netdev_present", str(c["wlan_netdev_present"])],
                ["wiphy_present", str(c["wiphy_present"])],
                ["wifi_rfkill_present", str(c["wifi_rfkill_present"])],
            ],
        ),
        "\n\n## WLAN Module Parameters\n\n",
        markdown_table(["parameter", "value"], param_rows),
        "\n\n## Platform Driver Candidates\n\n",
        markdown_table(["path"], driver_rows[:40] if driver_rows else [["none"]]),
        "\n\n## Guardrails\n\n",
    ])
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def run(args: argparse.Namespace) -> int:
    validate_no_denied_commands(args)
    store = EvidenceStore(repo_path(args.out_dir))
    v277 = load_json(args.v277_manifest)
    captures_list = capture_commands(args, store)
    captures = by_name(captures_list)
    classification = build_classification(captures, v277)
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
        "inputs": {"v277_manifest": str(repo_path(args.v277_manifest))},
        "classification": classification,
        "checks": checks,
        "captures": captures_list,
        "guardrails": [
            "no module/sysfs/control writes",
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
    parser.add_argument("--v277-manifest", type=Path, default=DEFAULT_V277_MANIFEST)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "run":
        return run(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
