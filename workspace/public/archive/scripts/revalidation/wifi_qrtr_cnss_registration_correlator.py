#!/usr/bin/env python3
"""v276 QRTR/CNSS registration-state correlator.

This is a no-packet, no-daemon collector. It correlates prior bounded QRTR
nameservice readback evidence with current read-only native state so the next
Wi-Fi step is based on registration/runtime evidence rather than another blind
service-id retry.
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
from wifi_qrtr_socket_probe import DEFAULT_HELPER_SHA256 as QRTR_PROBE_SHA256  # noqa: E402
from wifi_qrtr_socket_probe import parse_probe_keys  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v276-qrtr-cnss-registration-correlation")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_V273_MANIFEST = Path("tmp/wifi/v273-qrtr-readback-matrix-live-20260519-110229/manifest.json")
DEFAULT_V274_MANIFEST = Path("tmp/wifi/v274-wlfw-service-locator/manifest.json")
DEFAULT_V275_MANIFEST = Path("tmp/wifi/v275-wlfw-qrtr-readback-live-20260519-111529/manifest.json")
DEFAULT_QRTR_PROBE = "/cache/bin/a90_qrtr_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"

REFERENCE_URLS = {
    "linux_qrtr_af": "https://codebrowser.dev/linux/linux/net/qrtr/af_qrtr.c.html",
    "android_common_qrtr_af": "https://android.googlesource.com/kernel/common/+/aef3a58b06fa9d452ba863999ac34be1d0c65172/net/qrtr/af_qrtr.c",
}

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
    re.compile(r"\bsetprop\b|\bctl\.start\b|\bclass_start\b", re.IGNORECASE),
)

COMMANDS: tuple[tuple[str, tuple[str, ...], float, bool], ...] = (
    ("version", ("version",), 10.0, True),
    ("status", ("status",), 15.0, True),
    ("netservice-status", ("netservice", "status"), 10.0, True),
    ("selftest-verbose", ("selftest", "verbose"), 20.0, True),
    ("cat-proc-net-protocols", ("cat", "/proc/net/protocols"), 10.0, True),
    ("cat-proc-net-dev", ("cat", "/proc/net/dev"), 10.0, True),
    ("cat-proc-net-netlink", ("cat", "/proc/net/netlink"), 10.0, False),
    ("cat-proc-net-qrtr", ("cat", "/proc/net/qrtr"), 10.0, False),
    ("ls-proc-net", ("ls", "/proc/net"), 10.0, True),
    ("ls-sys-class-net", ("ls", "/sys/class/net"), 10.0, True),
    ("ls-sys-class-rfkill", ("ls", "/sys/class/rfkill"), 10.0, False),
    ("ls-sys-class-ieee80211", ("ls", "/sys/class/ieee80211"), 10.0, False),
    ("find-dev-qmi-qrtr-cnss", ("run", DEFAULT_TOYBOX, "find", "/dev", "-maxdepth", "4", "-name", "*qmi*", "-o", "-name", "*qrtr*", "-o", "-name", "*cnss*", "-o", "-name", "*diag*", "-o", "-name", "*ipa*", "-o", "-name", "*wlan*"), 30.0, False),
    ("find-sys-qmi-qrtr-cnss", ("run", DEFAULT_TOYBOX, "find", "/sys", "-maxdepth", "7", "-name", "*qmi*", "-o", "-name", "*qrtr*", "-o", "-name", "*cnss*", "-o", "-name", "*wlan*", "-o", "-name", "*icnss*"), 40.0, False),
    ("ps-A-pid-stat-comm", ("run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm"), 20.0, True),
    ("stat-qrtr-probe", ("stat", DEFAULT_QRTR_PROBE), 10.0, False),
    ("sha-qrtr-probe", ("run", DEFAULT_TOYBOX, "sha256sum", DEFAULT_QRTR_PROBE), 10.0, False),
    ("qrtr-probe-no-send", ("run", DEFAULT_QRTR_PROBE), 15.0, False),
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
    output: list[str] = []
    for part in command:
        if part == DEFAULT_QRTR_PROBE:
            output.append(args.qrtr_probe)
        elif part == DEFAULT_TOYBOX:
            output.append(args.toybox)
        else:
            output.append(part)
    return output


def validate_no_denied_commands(args: argparse.Namespace) -> None:
    text = "\n".join(" ".join(replace_defaults(command, args)) for _, command, _, _ in COMMANDS)
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def capture_commands(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("captures")
    captures: list[dict[str, Any]] = []
    for name, command, timeout, required in COMMANDS:
        actual = replace_defaults(command, args)
        capture = run_capture(args, name, actual, timeout=timeout)
        text = capture.text if capture.text else capture.error + "\n"
        store.write_text(f"captures/{safe_name(name)}.txt", text)
        if name == "qrtr-probe-no-send":
            store.write_text("qrtr-probe-no-send.txt", text)
        item = capture_to_manifest(capture)
        item["required"] = required
        captures.append(item)
    return captures


def by_name(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in captures}


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return bool(item.get("ok")) and item.get("rc") == 0 and item.get("status") == "ok"


def capture_rc(captures: dict[str, dict[str, Any]], name: str) -> int | None:
    value = captures.get(name, {}).get("rc")
    return value if isinstance(value, int) else None


def capture_text(captures: dict[str, dict[str, Any]], name: str) -> str:
    item = captures.get(name, {})
    if not item.get("text"):
        return ""
    return strip_cmdv1_text(str(item.get("text", "")))


def has_wlan_interface(text: str) -> bool:
    return bool(re.search(r"^\s*wlan\S*:", text, re.MULTILINE) or re.search(r"(^|\s)wlan\S*(\s|$)", text, re.MULTILINE))


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


def extract_endpoint_lines(text: str) -> list[str]:
    keywords = ("qrtr", "qmi", "cnss", "icnss", "wlan", "diag", "ipa")
    return [line for line in non_noise_lines(text) if any(token in line.lower() for token in keywords)]


def summarize_prior_matrix(manifest: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for raw in manifest.get("matrix_results", []):
        if not isinstance(raw, dict):
            continue
        keys = raw.get("helper_keys", {}) if isinstance(raw.get("helper_keys"), dict) else {}
        cases.append(
            {
                "name": raw.get("name"),
                "service": raw.get("service"),
                "instance": raw.get("instance"),
                "classification": raw.get("classification"),
                "events": keys.get("readback.events"),
                "service_events": keys.get("readback.service_events"),
                "timeout": keys.get("readback.timeout"),
                "end_of_list": keys.get("readback.end_of_list"),
                "qmi_attempted": keys.get("qmi_attempted"),
                "send_attempted": keys.get("send_attempted"),
            }
        )
    return {
        "path": manifest.get("_manifest_path"),
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass") is True,
        "case_count": len(cases),
        "cases": cases,
        "all_timeout": bool(cases) and all(item.get("classification") == "timeout" for item in cases),
        "all_zero_events": bool(cases) and all(str(item.get("events")) == "0" and str(item.get("service_events")) == "0" for item in cases),
        "all_qmi_zero": bool(cases) and all(str(item.get("qmi_attempted")) == "0" for item in cases),
    }


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
        "proc_net_qrtr_rc": capture_rc(captures, "cat-proc-net-qrtr"),
        "proc_net_qrtr_ok": capture_ok(captures, "cat-proc-net-qrtr"),
        "wlan_in_proc_net_dev": has_wlan_interface(proc_net_dev),
        "wlan_in_sys_class_net": has_wlan_interface(sys_class_net),
        "dev_endpoint_lines": extract_endpoint_lines(find_dev),
        "sys_endpoint_lines": extract_endpoint_lines(find_sys),
        "process_summary": process_summary,
        "qrtr_probe_present": capture_ok(captures, "stat-qrtr-probe"),
        "qrtr_probe_sha_ok": QRTR_PROBE_SHA256 in capture_text(captures, "sha-qrtr-probe"),
        "qrtr_probe_status": probe_keys.get("status", "missing"),
        "qrtr_probe_socket_rc": probe_keys.get("socket.rc", "missing"),
        "qrtr_probe_send_attempted": probe_keys.get("send_attempted", "missing"),
        "qrtr_probe_connect_attempted": probe_keys.get("connect_attempted", "missing"),
    }


def build_checks(args: argparse.Namespace,
                 v273_summary: dict[str, Any],
                 v274: dict[str, Any],
                 v275_summary: dict[str, Any],
                 captures: dict[str, dict[str, Any]],
                 inventory: dict[str, Any]) -> list[dict[str, Any]]:
    version_text = capture_text(captures, "version")
    required_failed = [name for name, _, _, required in COMMANDS if required and not capture_ok(captures, name)]
    process_summary = inventory.get("process_summary") or {}
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
            "name": "v273-wds-dms-timeout-evidence",
            "pass": v273_summary["pass"] and v273_summary["all_timeout"] and v273_summary["all_zero_events"] and v273_summary["all_qmi_zero"],
            "severity": "critical",
            "detail": json.dumps({k: v273_summary[k] for k in ("decision", "case_count", "all_timeout", "all_zero_events", "all_qmi_zero")}, sort_keys=True),
        },
        {
            "name": "v274-wlfw-source-backed",
            "pass": v274.get("pass") is True and v274.get("decision") == "wlfw-service-id-source-backed",
            "severity": "critical",
            "detail": str(v274.get("decision")),
        },
        {
            "name": "v275-wlfw-timeout-evidence",
            "pass": v275_summary["pass"] and v275_summary["all_timeout"] and v275_summary["all_zero_events"] and v275_summary["all_qmi_zero"],
            "severity": "critical",
            "detail": json.dumps({k: v275_summary[k] for k in ("decision", "case_count", "all_timeout", "all_zero_events", "all_qmi_zero")}, sort_keys=True),
        },
        {
            "name": "qipcrtr-protocol-present",
            "pass": bool(inventory["qipcrtr_protocol_present"]),
            "severity": "critical",
            "detail": "QIPCRTR listed in /proc/net/protocols",
        },
        {
            "name": "qrtr-probe-no-send-connect",
            "pass": inventory["qrtr_probe_socket_rc"] == "0" and inventory["qrtr_probe_send_attempted"] == "0" and inventory["qrtr_probe_connect_attempted"] == "0",
            "severity": "critical",
            "detail": json.dumps({
                "present": inventory["qrtr_probe_present"],
                "sha_ok": inventory["qrtr_probe_sha_ok"],
                "socket_rc": inventory["qrtr_probe_socket_rc"],
                "send_attempted": inventory["qrtr_probe_send_attempted"],
                "connect_attempted": inventory["qrtr_probe_connect_attempted"],
                "status": inventory["qrtr_probe_status"],
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
            "name": "no-wlan-interface",
            "pass": not inventory["wlan_in_proc_net_dev"] and not inventory["wlan_in_sys_class_net"],
            "severity": "critical",
            "detail": json.dumps({
                "proc_net_dev": inventory["wlan_in_proc_net_dev"],
                "sys_class_net": inventory["wlan_in_sys_class_net"],
            }, sort_keys=True),
        },
        {
            "name": "endpoint-inventory-read",
            "pass": bool(capture_ok(captures, "find-dev-qmi-qrtr-cnss") or capture_ok(captures, "find-sys-qmi-qrtr-cnss")),
            "severity": "warning",
            "detail": json.dumps({
                "dev_matches": len(inventory["dev_endpoint_lines"]),
                "sys_matches": len(inventory["sys_endpoint_lines"]),
                "proc_net_qrtr_ok": inventory["proc_net_qrtr_ok"],
                "proc_net_qrtr_rc": inventory["proc_net_qrtr_rc"],
            }, sort_keys=True),
        },
    ]


def classify(checks: list[dict[str, Any]], inventory: dict[str, Any]) -> tuple[bool, str, str]:
    critical_failed = [item["name"] for item in checks if item.get("severity") == "critical" and not item.get("pass")]
    if critical_failed:
        return False, "qrtr-cnss-state-incomplete", "critical correlation checks failed: " + ", ".join(critical_failed)
    if inventory["wlan_in_proc_net_dev"] or inventory["wlan_in_sys_class_net"]:
        return False, "qrtr-cnss-safety-regression", "wlan interface appeared during no-payload correlation"
    active_lines = list(inventory["dev_endpoint_lines"])
    if inventory["proc_net_qrtr_ok"]:
        active_lines.append("/proc/net/qrtr")
    if active_lines:
        return True, "qrtr-cnss-registration-visible", "active QRTR/device endpoint surfaces are visible for follow-up"
    platform_lines = [line for line in inventory["sys_endpoint_lines"] if "wlan" in line.lower() or "cnss" in line.lower() or "icnss" in line.lower() or "qrtr" in line.lower()]
    if platform_lines:
        return True, "qrtr-cnss-platform-surface-visible", "static CNSS/WLAN/QRTR platform surfaces exist but no active QRTR service notifications were observed"
    return True, "qrtr-cnss-registration-gap-classified", "QRTR socket is ready but WDS/DMS/WLFW nameservice notifications remain absent in native state"


def render_prior_rows(summary: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in summary.get("cases", []):
        rows.append([
            str(item.get("name")),
            str(item.get("service")),
            str(item.get("instance")),
            str(item.get("classification")),
            str(item.get("events")),
            str(item.get("service_events")),
            str(item.get("qmi_attempted")),
        ])
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# QRTR/CNSS Registration Correlation\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: {manifest['reason']}\n",
        f"- packet_transmission: `{manifest['packet_transmission']}`\n",
        f"- daemon_execution: `{manifest['daemon_execution']}`\n\n",
        "## Checks\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}` ({item['severity']}): {item['detail']}\n")
    lines.extend([
        "\n## Prior Matrix Evidence\n\n",
        "### V273 WDS/DMS\n\n",
        markdown_table(["name", "service", "instance", "classification", "events", "service_events", "qmi_attempted"], render_prior_rows(manifest["prior_evidence"]["v273"])),
        "\n\n### V275 WLFW\n\n",
        markdown_table(["name", "service", "instance", "classification", "events", "service_events", "qmi_attempted"], render_prior_rows(manifest["prior_evidence"]["v275"])),
        "\n\n## Live Inventory\n\n",
        markdown_table(
            ["field", "value"],
            [
                ["qipcrtr_protocol_present", str(manifest["inventory"]["qipcrtr_protocol_present"])],
                ["proc_net_qrtr_ok", str(manifest["inventory"]["proc_net_qrtr_ok"])],
                ["qrtr_probe_status", str(manifest["inventory"]["qrtr_probe_status"])],
                ["qrtr_probe_socket_rc", str(manifest["inventory"]["qrtr_probe_socket_rc"])],
                ["qrtr_probe_send_attempted", str(manifest["inventory"]["qrtr_probe_send_attempted"])],
                ["qrtr_probe_connect_attempted", str(manifest["inventory"]["qrtr_probe_connect_attempted"])],
                ["wlan_in_proc_net_dev", str(manifest["inventory"]["wlan_in_proc_net_dev"])],
                ["wlan_in_sys_class_net", str(manifest["inventory"]["wlan_in_sys_class_net"])],
                ["dev_endpoint_lines", str(len(manifest["inventory"]["dev_endpoint_lines"]))],
                ["sys_endpoint_lines", str(len(manifest["inventory"]["sys_endpoint_lines"]))],
            ],
        ),
        "\n\n## Guardrails\n\n",
    ])
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def run(args: argparse.Namespace) -> int:
    validate_no_denied_commands(args)
    store = EvidenceStore(repo_path(args.out_dir))
    v273 = load_json(args.v273_manifest)
    v274 = load_json(args.v274_manifest)
    v275 = load_json(args.v275_manifest)
    v273_summary = summarize_prior_matrix(v273)
    v275_summary = summarize_prior_matrix(v275)
    captures_list = capture_commands(args, store)
    captures = by_name(captures_list)
    probe_text = capture_text(captures, "qrtr-probe-no-send")
    probe_keys = parse_probe_keys(probe_text) if probe_text else {}
    inventory = build_inventory(captures, probe_keys)
    checks = build_checks(args, v273_summary, v274, v275_summary, captures, inventory)
    pass_ok, decision, reason = classify(checks, inventory)
    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(repo_path(args.out_dir)),
        "packet_transmission": False,
        "daemon_execution": False,
        "host_metadata": collect_host_metadata(),
        "references": REFERENCE_URLS,
        "inputs": {
            "v273_manifest": str(repo_path(args.v273_manifest)),
            "v274_manifest": str(repo_path(args.v274_manifest)),
            "v275_manifest": str(repo_path(args.v275_manifest)),
        },
        "prior_evidence": {
            "v273": v273_summary,
            "v274": {
                "path": v274.get("_manifest_path"),
                "decision": v274.get("decision"),
                "pass": v274.get("pass") is True,
                "wlfw": v274.get("wlfw", {}),
            },
            "v275": v275_summary,
        },
        "inventory": inventory,
        "probe_keys": probe_keys,
        "checks": checks,
        "captures": captures_list,
        "guardrails": [
            "no QRTR nameservice packet transmission",
            "no QMI request payload",
            "no cnss-daemon/cnss_diag/HAL/supplicant/wificond/hostapd start",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write, ICNSS bind/unbind, firmware mutation, Android partition write, or reboot",
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
    parser.add_argument("--v273-manifest", type=Path, default=DEFAULT_V273_MANIFEST)
    parser.add_argument("--v274-manifest", type=Path, default=DEFAULT_V274_MANIFEST)
    parser.add_argument("--v275-manifest", type=Path, default=DEFAULT_V275_MANIFEST)
    parser.add_argument("--qrtr-probe", default=DEFAULT_QRTR_PROBE)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "run":
        return run(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
