#!/usr/bin/env python3
"""Host-only V1696 classifier for cnss-daemon kmsg logging thresholds."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1696"
DEFAULT_CNSS_DAEMON = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v226-vendor-root-live-export"
    / "vendor-source"
    / "bin"
    / "cnss-daemon"
)
DEFAULT_V1695_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1695-wlan-pd-cnss-output-visibility-handoff"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1696-cnss-kmsg-threshold-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1696_CNSS_KMSG_THRESHOLD_CLASSIFIER_2026-06-02.md"
)

EXPECTED_BINARY_SHA = "bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc"

EXPECTED_STRINGS = {
    "persist.vendor.cnss-daemon.debug_level": 0x3510,
    "persist.vendor.cnss-daemon.kmsg_logging": 0x59A0,
    "echo %s %s > /dev/kmsg": 0x4215,
    "%s: Starting": 0x5F96,
    "wlfw_start": 0x5AB9,
    "Failed to init nl_loop": 0x711D,
    "Failed to init netlink common": 0x4C4C,
    "Failed to init interop issues ap": 0x5D03,
    "Failed to init hang issues ap": 0x5D24,
    "Failed to init gw update loop": 0x41C5,
    "Failed to init user interface": 0x59C8,
    "Failed to start wlan service": 0x41E3,
    "Failed to start wlan datapath service": 0x6DDE,
}

EXPECTED_PATTERNS = {
    "debug_property_get": "9128:\t94002b4a \tbl\t13e50 <property_get_int32@plt>",
    "kmsg_property_get": "9140:\t94002b44 \tbl\t13e50 <property_get_int32@plt>",
    "logging_helper_entry": "a21c:\ta9bd7bfd \tstp\tx29, x30, [sp, #-48]!",
    "debug_threshold_compare": "a270:\t6b00011f \tcmp\tw8, w0",
    "debug_threshold_skip": "a274:\t54000e2b \tb.lt\ta438",
    "kmsg_threshold_compare": "a2a8:\t6b00019f \tcmp\tw12, w0",
    "kmsg_threshold_skip": "a2b4:\t540007eb \tb.lt\ta3b0",
    "kmsg_system_call": "a3ac:\t9400274d \tbl\t140e0 <system@plt>",
    "android_log_call": "a434:\t9400272f \tbl\t140f0 <__android_log_print@plt>",
    "wlfw_start_entry": "ec00:\ta9be7bfd \tstp\tx29, x30, [sp, #-32]!",
    "wlfw_start_severity": "ec20:\t52800040 \tmov\tw0, #0x2",
    "wlfw_start_log_call": "ec24:\t97ffed7e \tbl\ta21c",
    "wlfw_ready_thread_log_severity": "edb8:\t52800080 \tmov\tw0, #0x4",
}

PRE_WLFW_FAILURE_SITES = {
    "nl-loop": {"site": "924c", "severity": 1},
    "netlink-common": {"site": "929c", "severity": 1},
    "interop-issues-ap": {"site": "92b0", "severity": 1},
    "hang-issues-ap": {"site": "92c4", "severity": 1},
    "gw-update-loop": {"site": "92d8", "severity": 1},
    "user-interface": {"site": "92ec", "severity": 1},
    "wlan-service": {"site": "9300", "severity": 1},
    "wlan-datapath-service": {"site": "930c", "severity": 1},
}


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_text(command: list[str]) -> str:
    return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)


def objdump_text(binary: Path) -> str:
    try:
        return run_text(["aarch64-linux-gnu-objdump", "-d", str(binary)])
    except (FileNotFoundError, subprocess.CalledProcessError):
        return run_text(["objdump", "-d", str(binary)])


def parse_strings(binary: Path) -> dict[str, int]:
    output = run_text(["strings", "-a", "-t", "x", str(binary)])
    found: dict[str, int] = {}
    for line in output.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        try:
            offset = int(parts[0], 16)
        except ValueError:
            continue
        text = parts[1]
        if text in EXPECTED_STRINGS:
            found[text] = offset
    return found


def intish(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def boolish(value: Any) -> bool:
    return value is True or value == 1 or value == "1"


def pattern_checks(disassembly: str) -> dict[str, bool]:
    return {name: pattern in disassembly for name, pattern in EXPECTED_PATTERNS.items()}


def string_checks(found: dict[str, int]) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    for text, expected_offset in EXPECTED_STRINGS.items():
        actual_offset = found.get(text)
        checks[text] = {
            "expected_offset": f"0x{expected_offset:x}",
            "actual_offset": f"0x{actual_offset:x}" if actual_offset is not None else None,
            "match": actual_offset == expected_offset,
        }
    return checks


def failure_site_checks(disassembly: str) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    for slug, model in PRE_WLFW_FAILURE_SITES.items():
        site = str(model["site"])
        checks[slug] = {
            "site": "0x" + site,
            "severity": model["severity"],
            "site_present": f"{site}:" in disassembly,
        }
    return checks


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1695 = read_json(args.v1695_manifest)
    gate = v1695.get("gate", {})
    disassembly = objdump_text(args.cnss_daemon)
    found_strings = parse_strings(args.cnss_daemon)
    binary_sha = sha256_file(args.cnss_daemon)
    patterns = pattern_checks(disassembly)
    strings = string_checks(found_strings)
    failures = failure_site_checks(disassembly)

    kmsg_logging = intish(gate.get("property_lookup_kmsg_value"), -1)
    debug_level = intish(gate.get("property_lookup_debug_value"), -1)
    wlfw_start_severity = 2
    pre_wlfw_failure_severity = 1
    wlfw_kmsg_visible_by_threshold = (
        debug_level >= wlfw_start_severity and kmsg_logging >= wlfw_start_severity
    )
    failure_kmsg_visible_by_threshold = (
        debug_level >= pre_wlfw_failure_severity and kmsg_logging >= pre_wlfw_failure_severity
    )

    v1695_ready = (
        v1695.get("decision") == "v1695-cnss-output-still-invisible-rollback-pass"
        and bool(v1695.get("pass"))
        and boolish(gate.get("property_lookup_seen"))
        and str(gate.get("property_lookup_all_match")) == "1"
        and str(gate.get("label")) == "cnss-output-still-invisible"
        and str(gate.get("wlfw_start_seen")) == "0"
        and str(gate.get("first_failure_slug")) == "none"
        and str(gate.get("cnss_daemon_running")) == "1"
    )
    static_ready = (
        binary_sha == EXPECTED_BINARY_SHA
        and all(item["match"] for item in strings.values())
        and all(patterns.values())
        and all(item["site_present"] for item in failures.values())
    )
    decision = (
        "v1696-cnss-kmsg-threshold-gap-classified"
        if v1695_ready and static_ready and not wlfw_kmsg_visible_by_threshold
        else "v1696-cnss-kmsg-threshold-classifier-blocked"
    )
    pass_ok = decision == "v1696-cnss-kmsg-threshold-gap-classified"

    return {
        "cycle": CYCLE,
        "decision": decision,
        "pass": pass_ok,
        "reason": (
            "wlfw_start logs at severity 2, but V1695 used kmsg_logging=1; "
            "therefore V1695 could not expose wlfw_start through /dev/kmsg"
            if pass_ok
            else "required V1695/static cnss-daemon evidence was incomplete"
        ),
        "cnss_daemon": {
            "path": display_path(args.cnss_daemon),
            "sha256": binary_sha,
            "sha256_ok": binary_sha == EXPECTED_BINARY_SHA,
        },
        "v1695": {
            "manifest": display_path(args.v1695_manifest),
            "decision": v1695.get("decision"),
            "pass": bool(v1695.get("pass")),
            "output_label": gate.get("label"),
            "property_lookup_all_match": gate.get("property_lookup_all_match"),
            "kmsg_logging": kmsg_logging,
            "debug_level": debug_level,
            "wlfw_start_seen": gate.get("wlfw_start_seen"),
            "first_failure_slug": gate.get("first_failure_slug"),
            "cnss_daemon_running": gate.get("cnss_daemon_running"),
            "syslog_available": gate.get("syslog_available"),
            "syslog_filtered_count": gate.get("syslog_filtered_count"),
            "nonlog_label": gate.get("nonlog_label"),
            "nonlog_kmsg_fd_count": gate.get("nonlog_kmsg_count"),
            "rollback_ok": (v1695.get("rollback") or {}).get("ok"),
        },
        "static_model": {
            "logging_helper": "cnss-daemon+0xa21c",
            "debug_level_threshold": "message emitted only when debug_level >= message_severity",
            "kmsg_threshold": "system('echo ... > /dev/kmsg') only when kmsg_logging >= message_severity",
            "android_log_path": "__android_log_print still runs when debug_level threshold passes",
            "wlfw_start": {
                "entry": "cnss-daemon+0xec00",
                "log_call": "cnss-daemon+0xec24",
                "severity": wlfw_start_severity,
                "format_string": "%s: Starting",
                "name_string": "wlfw_start",
                "kmsg_visible_with_v1695_thresholds": wlfw_kmsg_visible_by_threshold,
            },
            "pre_wlfw_failures": {
                "severity": pre_wlfw_failure_severity,
                "kmsg_visible_with_v1695_thresholds": failure_kmsg_visible_by_threshold,
                "sites": failures,
            },
        },
        "checks": {
            "v1695_ready": v1695_ready,
            "static_ready": static_ready,
            "patterns": patterns,
            "strings": strings,
        },
        "next_gate": {
            "cycle": "V1697",
            "action": "source/build-only private property runtime with persist.vendor.cnss-daemon.kmsg_logging >= 2, preferably 4",
            "then": "one rollbackable V1698 output-visibility live handoff on the same internal-modem route",
            "forbidden": [
                "PM/service-window actors",
                "boot_wlan",
                "/dev/subsys_esoc0",
                "forced RC1",
                "fake-ONLINE",
                "Wi-Fi HAL",
                "scan/connect",
                "credentials",
                "DHCP/routes",
                "external ping",
            ],
        },
        "out_dir": display_path(args.out_dir),
    }


def render_report(manifest: dict[str, Any]) -> str:
    static_model = manifest["static_model"]
    v1695 = manifest["v1695"]
    next_gate = manifest["next_gate"]
    return "\n".join([
        "# Native Init V1696 CNSS kmsg Threshold Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1696`",
        "- Type: host-only stock `cnss-daemon` kmsg/logging threshold classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'BLOCKED'}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Binary: `{manifest['cnss_daemon']['path']}`",
        f"- Binary SHA256: `{manifest['cnss_daemon']['sha256']}`",
        "",
        "## V1695 Basis",
        "",
        f"- decision/pass: `{v1695['decision']}` / `{v1695['pass']}`",
        f"- output label: `{v1695['output_label']}`",
        f"- property lookup all_match: `{v1695['property_lookup_all_match']}`",
        f"- `kmsg_logging` / `debug_level`: `{v1695['kmsg_logging']}` / `{v1695['debug_level']}`",
        f"- `wlfw_start_seen`: `{v1695['wlfw_start_seen']}`",
        f"- first failure slug: `{v1695['first_failure_slug']}`",
        f"- cnss-daemon running: `{v1695['cnss_daemon_running']}`",
        f"- syslog available/filtered: `{v1695['syslog_available']}` / `{v1695['syslog_filtered_count']}`",
        f"- non-log label / kmsg fd count: `{v1695['nonlog_label']}` / `{v1695['nonlog_kmsg_fd_count']}`",
        "",
        "## Static Logging Model",
        "",
        f"- logging helper: `{static_model['logging_helper']}`",
        f"- debug threshold: {static_model['debug_level_threshold']}",
        f"- kmsg threshold: {static_model['kmsg_threshold']}",
        f"- Android log path: {static_model['android_log_path']}",
        f"- `wlfw_start` entry/log call: `{static_model['wlfw_start']['entry']}` / `{static_model['wlfw_start']['log_call']}`",
        f"- `wlfw_start` severity: `{static_model['wlfw_start']['severity']}`",
        f"- `wlfw_start` kmsg-visible under V1695 thresholds: `{static_model['wlfw_start']['kmsg_visible_with_v1695_thresholds']}`",
        f"- pre-`wlfw_start` failure severity: `{static_model['pre_wlfw_failures']['severity']}`",
        f"- pre-`wlfw_start` failures kmsg-visible under V1695 thresholds: `{static_model['pre_wlfw_failures']['kmsg_visible_with_v1695_thresholds']}`",
        "",
        "## Interpretation",
        "",
        "- V1695 `cnss-output-still-invisible` does not prove that stock `cnss-daemon` skipped `wlfw_start`.",
        "- `wlfw_start: Starting` is a severity-2 log, while V1695 used `persist.vendor.cnss-daemon.kmsg_logging=1`; the `/dev/kmsg` `system('echo ...')` path is therefore statically gated off for that entry log.",
        "- The eight pre-`wlfw_start` failure logs are severity 1, so V1695 thresholds were sufficient for those specific failure strings. Their absence remains useful evidence that no named pre-wlfw init failure was observed.",
        "- `/dev/kmsg` fd count `0` is not decisive because the kmsg path is a transient `system('echo ... > /dev/kmsg')` path, not a persistent daemon fd.",
        "",
        "## Next Gate",
        "",
        f"- Cycle: `{next_gate['cycle']}`",
        f"- Action: {next_gate['action']}",
        f"- Then: {next_gate['then']}",
        "- Keep forbidden: " + ", ".join(f"`{item}`" for item in next_gate["forbidden"]),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnss-daemon", type=Path, default=DEFAULT_CNSS_DAEMON)
    parser.add_argument("--v1695-manifest", type=Path, default=DEFAULT_V1695_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(args)
    manifest_path = args.out_dir / "manifest.json"
    report = render_report(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(report, encoding="utf-8")
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "report": display_path(args.report_path),
        "manifest": display_path(manifest_path),
    }, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
