#!/usr/bin/env python3
"""v262 QRTR/QMI no-scan endpoint inventory probe.

This collector is intentionally read-only/no-scan. It may execute the existing
static a90_qrtr_probe helper, which opens/binds an AF_QIPCRTR socket but reports
no send/connect attempts. It must not start CNSS, issue QRTR nameservice packets,
or change Wi-Fi link state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore
from wifi_cnss_zombie_audit import parse_ps_stat_comm, summarize_cnss_processes
from wifi_qrtr_socket_probe import DEFAULT_HELPER_SHA256, parse_probe_keys


DEFAULT_OUT_DIR = Path("tmp/wifi/v262-qrtr-qmi-no-scan-probe")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_HELPER = "/cache/bin/a90_qrtr_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"

REFERENCE_URLS = {
    "linux_qrtr_kconfig": "https://sbexr.rabexc.org/latest/sources/a9/0605b7d2f4022b.html",
    "linux_qrtr_af": "https://codebrowser.dev/linux/linux/net/qrtr/af_qrtr.c.html",
    "libqmi": "https://github.com/linux-mobile-broadband/libqmi",
}

DENIED_COMMAND_PATTERNS = (
    re.compile(r"\b/vendor/bin/cnss-daemon\b", re.IGNORECASE),
    re.compile(r"\bcnss_diag\b", re.IGNORECASE),
    re.compile(r"--allow-cnss-start-only", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|android\.hardware\.wifi)\b", re.IGNORECASE),
    re.compile(r"\b(?:dhcpcd|udhcpc|dnsmasq)\b", re.IGNORECASE),
    re.compile(r"\b/sys/bus/platform/drivers/icnss/(?:bind|unbind)\b", re.IGNORECASE),
    re.compile(r"\bsetprop\b|\bctl\.start\b|\bclass_start\b", re.IGNORECASE),
)

# name, command, timeout, required
COMMANDS: tuple[tuple[str, tuple[str, ...], float, bool], ...] = (
    ("version", ("version",), 10.0, True),
    ("status", ("status",), 15.0, True),
    ("bootstatus", ("bootstatus",), 10.0, True),
    ("selftest-verbose", ("selftest", "verbose"), 20.0, True),
    ("netservice-status", ("netservice", "status"), 10.0, True),
    ("wifiinv-full", ("wifiinv", "full"), 30.0, True),
    ("wififeas-full", ("wififeas", "full"), 30.0, False),
    ("cat-proc-net-protocols", ("cat", "/proc/net/protocols"), 10.0, True),
    ("cat-proc-net-dev", ("cat", "/proc/net/dev"), 10.0, True),
    ("cat-proc-net-wireless", ("cat", "/proc/net/wireless"), 10.0, False),
    ("cat-proc-net-netlink", ("cat", "/proc/net/netlink"), 10.0, False),
    ("cat-proc-net-qrtr", ("cat", "/proc/net/qrtr"), 10.0, False),
    ("ls-proc-net", ("ls", "/proc/net"), 10.0, False),
    ("ls-sys-class-net", ("ls", "/sys/class/net"), 10.0, True),
    ("ls-sys-class-rfkill", ("ls", "/sys/class/rfkill"), 10.0, False),
    ("ls-sys-class-ieee80211", ("ls", "/sys/class/ieee80211"), 10.0, False),
    ("stat-dev-qrtr", ("stat", "/dev/qrtr"), 10.0, False),
    ("stat-dev-diag", ("stat", "/dev/diag"), 10.0, False),
    ("stat-dev-ipa", ("stat", "/dev/ipa"), 10.0, False),
    ("stat-dev-wlan", ("stat", "/dev/wlan"), 10.0, False),
    ("find-dev-qmi-qrtr-cnss", ("run", DEFAULT_TOYBOX, "find", "/dev", "-maxdepth", "4", "-name", "*qmi*", "-o", "-name", "*qrtr*", "-o", "-name", "*cnss*", "-o", "-name", "*diag*", "-o", "-name", "*ipa*", "-o", "-name", "*wlan*"), 30.0, False),
    ("find-sys-qmi-qrtr-cnss", ("run", DEFAULT_TOYBOX, "find", "/sys", "-maxdepth", "7", "-name", "*qmi*", "-o", "-name", "*qrtr*", "-o", "-name", "*cnss*", "-o", "-name", "*wlan*", "-o", "-name", "*icnss*"), 40.0, False),
    ("ps-A-pid-stat-comm", ("run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm"), 20.0, True),
    ("stat-helper", ("stat", DEFAULT_HELPER), 10.0, True),
    ("sha-helper", ("run", DEFAULT_TOYBOX, "sha256sum", DEFAULT_HELPER), 10.0, True),
    ("qrtr-probe", ("run", DEFAULT_HELPER), 15.0, True),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def replace_defaults(command: tuple[str, ...], args: argparse.Namespace) -> list[str]:
    output: list[str] = []
    for part in command:
        if part == DEFAULT_HELPER:
            output.append(args.helper)
        elif part == DEFAULT_TOYBOX:
            output.append(args.toybox)
        else:
            output.append(part)
    return output


def validate_no_denied_commands(args: argparse.Namespace) -> None:
    command_text = "\n".join(" ".join(replace_defaults(command, args)) for _, command, _, _ in COMMANDS)
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def capture_commands(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    store.mkdir("captures")
    for name, command, timeout, required in COMMANDS:
        actual_command = replace_defaults(command, args)
        capture = run_capture(args, name, actual_command, timeout=timeout)
        text = capture.text if capture.text else capture.error + "\n"
        store.write_text(f"captures/{safe_name(name)}.txt", text)
        if name == "qrtr-probe":
            store.write_text("qrtr-probe.txt", text)
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
    return strip_cmdv1_text(str(item.get("text", ""))) if item.get("text") else ""


def count_inventory_lines(text: str) -> int:
    count = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("a90:/#", "A90P1 ", "[done]", "run: pid=")):
            continue
        count += 1
    return count


def has_wlan_like(text: str) -> bool:
    return bool(re.search(r"(^|[\s/:])wlan\S*", text, re.IGNORECASE | re.MULTILINE))


def build_inventory(captures: dict[str, dict[str, Any]], probe_keys: dict[str, str]) -> dict[str, Any]:
    protocols = capture_text(captures, "cat-proc-net-protocols")
    proc_net_dev = capture_text(captures, "cat-proc-net-dev")
    sys_class_net = capture_text(captures, "ls-sys-class-net")
    find_dev = capture_text(captures, "find-dev-qmi-qrtr-cnss")
    find_sys = capture_text(captures, "find-sys-qmi-qrtr-cnss")
    ps_text = capture_text(captures, "ps-A-pid-stat-comm")
    process_summary = summarize_cnss_processes(parse_ps_stat_comm(ps_text)) if ps_text else None
    return {
        "qipcrtr_protocol_present": bool(re.search(r"^QIPCRTR\s", protocols, re.MULTILINE)),
        "proc_net_qrtr_present": capture_ok(captures, "cat-proc-net-qrtr"),
        "dev_qrtr_present": capture_ok(captures, "stat-dev-qrtr"),
        "dev_diag_present": capture_ok(captures, "stat-dev-diag"),
        "dev_ipa_present": capture_ok(captures, "stat-dev-ipa"),
        "dev_wlan_present": capture_ok(captures, "stat-dev-wlan"),
        "dev_inventory_matches": count_inventory_lines(find_dev),
        "sys_inventory_matches": count_inventory_lines(find_sys),
        "wlan_in_proc_net_dev": has_wlan_like(proc_net_dev),
        "wlan_in_sys_class_net": has_wlan_like(sys_class_net),
        "process_summary": process_summary,
        "qrtr_helper_status": probe_keys.get("status", "missing"),
        "qrtr_helper_socket_rc": probe_keys.get("socket.rc", "missing"),
        "qrtr_helper_send_attempted": probe_keys.get("send_attempted", "missing"),
        "qrtr_helper_connect_attempted": probe_keys.get("connect_attempted", "missing"),
    }


def build_checks(args: argparse.Namespace,
                 captures: dict[str, dict[str, Any]],
                 probe_keys: dict[str, str],
                 inventory: dict[str, Any]) -> list[dict[str, Any]]:
    version_text = capture_text(captures, "version")
    sha_text = capture_text(captures, "sha-helper")
    process_summary = inventory.get("process_summary") or {}
    required_names = [name for name, _, _, required in COMMANDS if required]
    required_failed = [name for name in required_names if not capture_ok(captures, name)]
    return [
        {
            "name": "expected-version",
            "pass": args.expect_version in version_text,
            "detail": args.expect_version,
        },
        {
            "name": "required-captures",
            "pass": not required_failed,
            "detail": "failed=" + json.dumps(required_failed),
        },
        {
            "name": "cnss-process-clean",
            "pass": bool(process_summary.get("clean")),
            "detail": json.dumps({
                "target_process_count": process_summary.get("target_process_count"),
                "target_running_count": process_summary.get("target_running_count"),
                "target_zombie_count": process_summary.get("target_zombie_count"),
            }, sort_keys=True),
        },
        {
            "name": "qipcrtr-protocol-listed",
            "pass": bool(inventory["qipcrtr_protocol_present"]),
            "detail": "QIPCRTR present in /proc/net/protocols",
        },
        {
            "name": "helper-sha",
            "pass": args.helper_sha256 in sha_text,
            "detail": args.helper_sha256,
        },
        {
            "name": "qrtr-helper-socket-open",
            "pass": probe_keys.get("socket.rc") == "0",
            "detail": json.dumps({k: probe_keys.get(k) for k in ("socket.rc", "status", "af")}, sort_keys=True),
        },
        {
            "name": "qrtr-helper-no-send-connect",
            "pass": probe_keys.get("send_attempted") == "0" and probe_keys.get("connect_attempted") == "0",
            "detail": json.dumps({
                "send_attempted": probe_keys.get("send_attempted"),
                "connect_attempted": probe_keys.get("connect_attempted"),
            }, sort_keys=True),
        },
        {
            "name": "no-wlan-link-surface",
            "pass": not inventory["wlan_in_proc_net_dev"] and not inventory["wlan_in_sys_class_net"],
            "detail": json.dumps({
                "proc_net_dev": inventory["wlan_in_proc_net_dev"],
                "sys_class_net": inventory["wlan_in_sys_class_net"],
            }, sort_keys=True),
        },
        {
            "name": "endpoint-inventory-collected",
            "pass": bool(capture_ok(captures, "find-dev-qmi-qrtr-cnss") or capture_ok(captures, "find-sys-qmi-qrtr-cnss")),
            "detail": json.dumps({
                "dev_matches": inventory["dev_inventory_matches"],
                "sys_matches": inventory["sys_inventory_matches"],
                "dev_qrtr": inventory["dev_qrtr_present"],
                "dev_diag": inventory["dev_diag_present"],
            }, sort_keys=True),
        },
    ]


def classify(checks: list[dict[str, Any]], inventory: dict[str, Any]) -> tuple[bool, str, str]:
    hard = {
        "expected-version",
        "required-captures",
        "cnss-process-clean",
        "qipcrtr-protocol-listed",
        "helper-sha",
        "qrtr-helper-socket-open",
        "qrtr-helper-no-send-connect",
    }
    failed_hard = [item["name"] for item in checks if item["name"] in hard and not item["pass"]]
    if failed_hard:
        return False, "qrtr-qmi-no-scan-blocked", "required no-scan QRTR/QMI check failed: " + ", ".join(failed_hard)
    if any(item["name"] == "no-wlan-link-surface" and not item["pass"] for item in checks):
        return False, "qrtr-qmi-no-scan-manual-review", "wlan-like network surface is visible; do not proceed without review"
    if inventory["qrtr_helper_status"] not in {"bind-pass", "open-only"}:
        return False, "qrtr-qmi-no-scan-manual-review", "QRTR helper status is ambiguous: " + str(inventory["qrtr_helper_status"])
    return True, "qrtr-qmi-no-scan-ready", "clean v261 baseline, QIPCRTR socket no-send probe, and read-only endpoint inventory are consistent"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], "PASS" if item["pass"] else "FAIL", item["detail"]] for item in manifest["checks"]]
    inventory_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)] for key, value in manifest["inventory"].items() if key != "process_summary"]
    reference_rows = [[key, value] for key, value in manifest["references"].items()]
    return "".join(
        [
            "# v262 QRTR/QMI No-Scan Probe\n\n",
            f"- generated: `{manifest['created']}`\n",
            f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
            f"- decision: `{manifest['decision']}`\n",
            f"- reason: `{manifest['reason']}`\n",
            f"- baseline: `{manifest['expect_version']}`\n",
            "- daemon start: `not executed`\n",
            "- QRTR send/connect/nameservice: `not executed`\n",
            f"- output: `{manifest['out_dir']}`\n\n",
            "## Checks\n\n",
            markdown_table(["check", "result", "detail"], check_rows),
            "\n\n## Inventory\n\n",
            markdown_table(["key", "value"], inventory_rows),
            "\n\n## References\n\n",
            markdown_table(["reference", "url"], reference_rows),
            "\n\n## Guardrails\n\n",
            "- No `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, or DHCP command was started.\n",
            "- QRTR helper reports no send/connect attempts.\n",
            "- No Wi-Fi scan/connect/link-up/credential/routing action was attempted.\n",
            "- No rfkill write, ICNSS bind/unbind, firmware mutation, Android partition write, or reboot was attempted.\n",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_no_denied_commands(args)
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    captures_list = capture_commands(args, store)
    captures = by_name(captures_list)
    probe_text = capture_text(captures, "qrtr-probe")
    probe_keys = parse_probe_keys(probe_text)
    inventory = build_inventory(captures, probe_keys)
    checks = build_checks(args, captures, probe_keys, inventory)
    pass_ok, decision, reason = classify(checks, inventory)
    manifest = {
        "created": now_iso(),
        "mode": "qrtr-qmi-no-scan-probe",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(out_dir),
        "expect_version": args.expect_version,
        "daemon_start_executed": False,
        "qrtr_send_connect_attempted": False,
        "host_metadata": collect_host_metadata(),
        "references": REFERENCE_URLS,
        "inventory": inventory,
        "probe_keys": probe_keys,
        "checks": checks,
        "captures": captures_list,
        "guardrails": [
            "no cnss-daemon execution",
            "no cnss_diag execution",
            "no QRTR send/connect/nameservice packet",
            "no QMI request command",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition write, or reboot",
        ],
    }
    store.write_json("live-captures.json", {"captures": captures_list})
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"out_dir: {out_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
