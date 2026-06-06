#!/usr/bin/env python3
"""v248 no-start CNSS runtime primitive preflight.

This collector is read-only with respect to Wi-Fi/CNSS state. It does not pass
--allow-cnss-start-only and does not start cnss-daemon or cnss_diag.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import DEFAULT_EXPECT_VERSION, capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore
from wifi_cnss_start_only_runner import DEFAULT_HELPER_SHA256, parse_cnss_start_keys

DEFAULT_OUT_DIR = Path("tmp/wifi/v248-cnss-runtime-primitives-preflight")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_V242_MANIFEST = Path("tmp/wifi/v242-cnss-runtime-inventory-live2/manifest.json")
DEFAULT_V243_MANIFEST = Path("tmp/wifi/v243-cnss-launcher-contract-plan/manifest.json")
DEFAULT_V244_MANIFEST = Path("tmp/wifi/v244-cnss-identity-probe-live4/manifest.json")
DEFAULT_V247_REPORT = Path("docs/reports/NATIVE_INIT_V247_CNSS_START_OBSERVE_STOP_BODY_2026-05-19.md")

REQUIRED_MANIFESTS = {
    "v242": (DEFAULT_V242_MANIFEST, "cnss-runtime-inventory-ready-for-launcher-contract-plan"),
    "v243": (DEFAULT_V243_MANIFEST, "cnss-launcher-contract-ready"),
    "v244": (DEFAULT_V244_MANIFEST, "cnss-identity-probe-pass"),
}

DENIED_COMMAND_PATTERNS = (
    re.compile(r"\b/vendor/bin/cnss-daemon\b.*\b(?:-n|-l)\b", re.IGNORECASE),
    re.compile(r"\bcnss_diag\b.*\b(?:-q|-f|-t)\b", re.IGNORECASE),
    re.compile(r"--allow-cnss-start-only", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\b(?:wpa_supplicant|wificond|hostapd|android\.hardware\.wifi)\b", re.IGNORECASE),
    re.compile(r"\b(?:dhcpcd|udhcpc|dnsmasq)\b", re.IGNORECASE),
    re.compile(r"\b/sys/bus/platform/drivers/icnss/(?:bind|unbind)\b", re.IGNORECASE),
    re.compile(r"\bsetprop\b|\bctl\.start\b|\bclass_start\b", re.IGNORECASE),
)

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float, bool], ...] = (
    ("version", ["version"], 10.0, True),
    ("status", ["status"], 10.0, True),
    ("bootstatus", ["bootstatus"], 10.0, False),
    ("selftest-verbose", ["selftest", "verbose"], 20.0, False),
    ("netservice-status", ["netservice", "status"], 10.0, True),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0, True),
    ("wifiinv-full", ["wifiinv", "full"], 20.0, False),
    ("kernelinv-summary", ["kernelinv", "summary"], 20.0, False),
    ("cat-proc-mounts", ["cat", "/proc/mounts"], 10.0, False),
    ("cat-proc-net-dev", ["cat", "/proc/net/dev"], 10.0, True),
    ("cat-proc-net-netlink", ["cat", "/proc/net/netlink"], 10.0, False),
    ("cat-firmware-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0, False),
    ("ls-sys-class-net", ["ls", "/sys/class/net"], 10.0, True),
    ("ls-sys-class-rfkill", ["ls", "/sys/class/rfkill"], 10.0, False),
    ("ls-sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 10.0, False),
    ("stat-helper", ["stat", "/cache/bin/a90_android_execns_probe"], 10.0, True),
    ("sha-helper", ["run", "/cache/bin/toybox", "sha256sum", "/cache/bin/a90_android_execns_probe"], 10.0, True),
    ("stat-real-ld-config", ["stat", "/cache/bin/a90_real_ld.config.txt"], 10.0, True),
    ("stat-real-apex-libraries", ["stat", "/cache/bin/a90_real_apex.libraries.config.txt"], 10.0, False),
    ("stat-mnt-cnss-daemon", ["stat", "/mnt/system/vendor/bin/cnss-daemon"], 10.0, False),
    ("stat-mnt-cnss-diag", ["stat", "/mnt/system/vendor/bin/cnss_diag"], 10.0, False),
    ("stat-mnt-linker64", ["stat", "/mnt/system/system/bin/linker64"], 10.0, True),
    ("stat-system-cnss-daemon", ["stat", "/system/vendor/bin/cnss-daemon"], 10.0, False),
    ("stat-vendor-cnss-daemon", ["stat", "/vendor/bin/cnss-daemon"], 10.0, False),
    ("stat-dev-null", ["stat", "/dev/null"], 10.0, True),
    ("stat-dev-socket", ["stat", "/dev/socket"], 10.0, False),
    ("stat-property-socket", ["stat", "/dev/socket/property_service"], 10.0, False),
    ("stat-properties-area", ["stat", "/dev/__properties__"], 10.0, False),
    ("ls-dev-socket", ["run", "/cache/bin/toybox", "ls", "-l", "/dev/socket"], 10.0, False),
    ("stat-selinux", ["stat", "/sys/fs/selinux"], 10.0, False),
    ("stat-selinux-null", ["stat", "/sys/fs/selinux/null"], 10.0, False),
    ("cat-selinux-enforce", ["cat", "/sys/fs/selinux/enforce"], 10.0, False),
    ("stat-dev-diag", ["stat", "/dev/diag"], 10.0, False),
    ("stat-dev-qrtr", ["stat", "/dev/qrtr"], 10.0, False),
    ("stat-dev-ipa", ["stat", "/dev/ipa"], 10.0, False),
    ("stat-dev-wlan", ["stat", "/dev/wlan"], 10.0, False),
    ("find-dev-diag", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "3", "-name", "*diag*"], 20.0, False),
    ("find-dev-qrtr", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "3", "-name", "*qrtr*"], 20.0, False),
    ("find-dev-ipa", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "3", "-name", "*ipa*"], 20.0, False),
    ("find-dev-wlan", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "3", "-name", "*wlan*"], 20.0, False),
    ("find-dev-cnss", ["run", "/cache/bin/toybox", "find", "/dev", "-maxdepth", "3", "-name", "*cnss*"], 20.0, False),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_manifest(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        return {"missing": True, "path": str(full), "decision": "missing", "pass": False}
    data = json.loads(full.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full)
    return data


def manifest_ok(manifest: dict[str, Any], expected: str) -> bool:
    return bool(manifest.get("pass")) and manifest.get("decision") == expected and not manifest.get("missing")


def validate_command_allowlist() -> None:
    text = "\n".join(" ".join(argv) for _, argv, _, _ in READ_ONLY_COMMANDS)
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"denied command pattern present: {pattern.pattern}")


def helper_noallow_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        "cnss-start-only",
        "--null-device-mode",
        "dev-null",
        "--vndk-apex-alias-mode",
        "v30-to-current",
        "--linkerconfig-mode",
        "copy-real",
        "--linkerconfig-source",
        "/cache/bin/a90_real_ld.config.txt",
        "--apex-libraries-source",
        "/cache/bin/a90_real_apex.libraries.config.txt",
        "--timeout-sec",
        str(args.helper_timeout_sec),
    ]


def validate_helper_noallow_command(args: argparse.Namespace) -> None:
    text = " ".join(helper_noallow_command(args))
    for pattern in DENIED_COMMAND_PATTERNS:
        if pattern.search(text):
            raise AssertionError(f"denied helper noallow pattern present: {pattern.pattern}")


def capture_commands(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    store.mkdir("captures")
    for name, command, timeout, required in READ_ONLY_COMMANDS:
        capture = run_capture(args, name, command, timeout=timeout)
        store.write_text(f"captures/{safe_name(name)}.txt", capture.text if capture.text else capture.error + "\n")
        item = capture_to_manifest(capture)
        item["required"] = required
        captures.append(item)
    helper_capture = run_capture(args, "helper-noallow", helper_noallow_command(args), timeout=args.timeout + args.helper_timeout_sec + 10.0)
    store.write_text("helper-noallow.txt", helper_capture.text if helper_capture.text else helper_capture.error + "\n")
    helper_item = capture_to_manifest(helper_capture)
    helper_item["required"] = True
    helper_item["cnss_start"] = parse_cnss_start_keys(helper_capture.text)
    captures.append(helper_item)
    return captures


def by_name(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in captures}


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return bool(item.get("ok")) and item.get("rc") == 0 and item.get("status") == "ok"


def capture_text(captures: dict[str, dict[str, Any]], name: str) -> str:
    item = captures.get(name, {})
    return strip_cmdv1_text(str(item.get("text", ""))) if item.get("text") else ""


def build_prereq_checks(manifests: dict[str, dict[str, Any]], v247_report: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for name, (_, expected) in REQUIRED_MANIFESTS.items():
        manifest = manifests[name]
        checks.append(
            {
                "name": name,
                "expected": expected,
                "actual": manifest.get("decision", "missing"),
                "pass": manifest_ok(manifest, expected),
                "path": manifest.get("_manifest_path", manifest.get("path", "")),
            }
        )
    report_path = repo_path(v247_report)
    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    checks.append(
        {
            "name": "v247-report",
            "expected": "v247-safe-body-ready-live-approval-required",
            "actual": "present" if report_text else "missing",
            "pass": "v247-safe-body-ready-live-approval-required" in report_text,
            "path": str(report_path),
        }
    )
    return checks


def build_primitive_checks(args: argparse.Namespace, captures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    helper_keys = captures.get("helper-noallow", {}).get("cnss_start", {})
    helper_text = str(captures.get("helper-noallow", {}).get("text", ""))
    helper_sha_text = capture_text(captures, "sha-helper")
    netdev = capture_text(captures, "cat-proc-net-dev")
    checks = [
        {"name": "helper-sha", "pass": args.helper_sha256 in helper_sha_text, "detail": args.helper_sha256},
        {"name": "helper-noallow-namespace", "pass": "helper_status=namespace-ready" in helper_text, "detail": "namespace-ready"},
        {"name": "helper-noallow-blocked", "pass": helper_keys.get("result") == "start-only-blocked" and helper_keys.get("exec_attempted") == "0", "detail": json.dumps(helper_keys, sort_keys=True)},
        {"name": "cnss-daemon-private-namespace-evidence", "pass": "context.target.exists=1" in helper_text and "context.target.access_x=1" in helper_text, "detail": "helper private /vendor/bin/cnss-daemon exists and is executable"},
        {"name": "linker64-mounted-evidence", "pass": capture_ok(captures, "stat-mnt-linker64"), "detail": "mounted system linker64"},
        {"name": "no-active-wlan-netdev", "pass": not re.search(r"^\s*wlan\S*:", netdev, re.MULTILINE), "detail": "wlan absent from /proc/net/dev"},
    ]
    return checks


def build_gap_matrix(captures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": "property-service-socket",
            "state": "present" if capture_ok(captures, "stat-property-socket") else "missing",
            "severity": "expected-runtime-gap",
            "live_start_effect": "daemon may fail if it requires Android property service",
        },
        {
            "name": "property-area",
            "state": "present" if capture_ok(captures, "stat-properties-area") else "missing",
            "severity": "expected-runtime-gap",
            "live_start_effect": "bionic/libcutils property reads may differ from Android",
        },
        {
            "name": "selinux-null",
            "state": "present" if capture_ok(captures, "stat-selinux-null") else "missing",
            "severity": "known-gap",
            "live_start_effect": "Android service domain transition is not recreated",
        },
        {
            "name": "diag-device",
            "state": "present" if capture_ok(captures, "stat-dev-diag") else "missing",
            "severity": "phase2-blocker",
            "live_start_effect": "cnss_diag remains blocked; primary daemon start-only may still be attempted with approval",
        },
        {
            "name": "qrtr-device",
            "state": "present" if capture_ok(captures, "stat-dev-qrtr") else "missing",
            "severity": "runtime-risk",
            "live_start_effect": "QMI/PDR expectations may cause immediate daemon exit",
        },
        {
            "name": "global-vendor-path",
            "state": "present" if capture_ok(captures, "stat-vendor-cnss-daemon") else "missing",
            "severity": "expected-private-namespace-only",
            "live_start_effect": "approved start-only must use helper private namespace, not global native root",
        },
    ]


def classify(prereq_checks: list[dict[str, Any]], primitive_checks: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> tuple[bool, str, str]:
    if not all(item["pass"] for item in prereq_checks):
        return False, "cnss-runtime-primitives-blocked", "required prior evidence is missing or mismatched"
    if not all(item["pass"] for item in primitive_checks):
        return False, "cnss-runtime-primitives-blocked", "required live no-start primitive check failed"
    unexpected = [item for item in gaps if item["state"] == "present" and item["name"] in {"property-service-socket", "property-area"}]
    if unexpected:
        return False, "cnss-runtime-primitives-manual-review", "unexpected Android runtime primitive is present in native root"
    return True, "cnss-runtime-primitives-ready-for-live-approval", "known gaps are documented and no-start helper/control evidence is current"


def render_summary(manifest: dict[str, Any]) -> str:
    prereq_rows = [[i["name"], "PASS" if i["pass"] else "FAIL", i["expected"], i["actual"]] for i in manifest["prerequisite_checks"]]
    primitive_rows = [[i["name"], "PASS" if i["pass"] else "FAIL", i["detail"]] for i in manifest["primitive_checks"]]
    gap_rows = [[i["name"], i["state"], i["severity"], i["live_start_effect"]] for i in manifest["gap_matrix"]]
    return "".join(
        [
            "# v248 CNSS Runtime Primitive Preflight\n\n",
            f"- generated: `{manifest['created']}`\n",
            f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
            f"- decision: `{manifest['decision']}`\n",
            f"- reason: `{manifest['reason']}`\n",
            "- daemon start: `not executed`\n",
            f"- output: `{manifest['out_dir']}`\n\n",
            "## Prerequisites\n\n",
            markdown_table(["check", "result", "expected", "actual"], prereq_rows),
            "\n\n## Required No-Start Checks\n\n",
            markdown_table(["check", "result", "detail"], primitive_rows),
            "\n\n## Runtime Gap Matrix\n\n",
            markdown_table(["primitive", "state", "severity", "live start effect"], gap_rows),
            "\n\n## Guardrails\n\n",
            "- No `--allow-cnss-start-only` was passed.\n",
            "- No `cnss-daemon` or `cnss_diag` process was started.\n",
            "- No Wi-Fi scan/connect/link-up/credential/DHCP/routing action was attempted.\n",
            "- Next step remains explicit operator approval for the first bounded live start-only run.\n",
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
    parser.add_argument("--helper-timeout-sec", type=int, default=10)
    parser.add_argument("--v247-report", type=Path, default=DEFAULT_V247_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_command_allowlist()
    validate_helper_noallow_command(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifests = {name: load_manifest(path) for name, (path, _) in REQUIRED_MANIFESTS.items()}
    captures_list = capture_commands(args, store)
    captures = by_name(captures_list)
    prereq_checks = build_prereq_checks(manifests, args.v247_report)
    primitive_checks = build_primitive_checks(args, captures)
    gap_matrix = build_gap_matrix(captures)
    pass_ok, decision, reason = classify(prereq_checks, primitive_checks, gap_matrix)
    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(repo_path(args.out_dir)),
        "daemon_start_executed": False,
        "host_metadata": collect_host_metadata(),
        "prerequisite_checks": prereq_checks,
        "primitive_checks": primitive_checks,
        "gap_matrix": gap_matrix,
        "captures": captures_list,
        "guardrails": [
            "no --allow-cnss-start-only",
            "no cnss-daemon execution",
            "no cnss_diag execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write, ICNSS bind/unbind, firmware mutation, or Android partition write",
        ],
    }
    store.write_json("live-captures.json", {"captures": captures_list})
    store.write_json("runtime-primitives.json", {"primitive_checks": primitive_checks, "gap_matrix": gap_matrix})
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {repo_path(args.out_dir)}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
