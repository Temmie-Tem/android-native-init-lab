#!/usr/bin/env python3
"""Host-only V1692 classifier for cnss-daemon non-log control-flow targets."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1692"
DEFAULT_CNSS_DAEMON = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v226-vendor-root-live-export"
    / "vendor-source"
    / "bin"
    / "cnss-daemon"
)
DEFAULT_OBJDUMP = REPO_ROOT / "tmp" / "wifi" / "cnss-daemon.objdump.txt"
DEFAULT_V1691_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1691-wlan-pd-cnss-property-lookup-handoff"
    / "manifest.json"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1692-cnss-nonlog-control-flow"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1692_CNSS_NONLOG_CONTROL_FLOW_2026-06-02.md"
)

EXPECTED_STRINGS = {
    "persist.vendor.cnss-daemon.debug_level": 0x3510,
    "persist.vendor.cnss-daemon.kmsg_logging": 0x59A0,
    "wlfw_start": 0x5AB9,
    "Failed to init nl_loop": 0x711D,
    "Failed to init netlink common": 0x4C4C,
    "Failed to init interop issues ap": 0x5D03,
    "Failed to init hang issues ap": 0x5D24,
    "Failed to init gw update loop": 0x41C5,
    "Failed to init user interface": 0x59C8,
    "Failed to start wlan service": 0x41E3,
    "Failed to start wlan datapath service": 0x6DDE,
    "Failed to start wlfw service": 0x3537,
    "echo %s %s > /dev/kmsg": 0x4215,
}

CONTROL_FLOW = [
    {
        "name": "debug_level_property_get",
        "call_site": "0x9128",
        "target": "property_get_int32@plt",
        "failure_site": None,
        "string": "persist.vendor.cnss-daemon.debug_level",
    },
    {
        "name": "kmsg_logging_property_get",
        "call_site": "0x9140",
        "target": "property_get_int32@plt",
        "failure_site": None,
        "string": "persist.vendor.cnss-daemon.kmsg_logging",
    },
    {
        "name": "nl_loop_init",
        "call_site": "0x91c0",
        "target": "0x939c",
        "failure_site": "0x924c",
        "string": "Failed to init nl_loop",
    },
    {
        "name": "netlink_common_init",
        "call_site": "0x91c8",
        "target": "0x12880",
        "failure_site": "0x929c",
        "string": "Failed to init netlink common",
    },
    {
        "name": "interop_issues_ap_init",
        "call_site": "0x91d0",
        "target": "0x1397c",
        "failure_site": "0x92b0",
        "string": "Failed to init interop issues ap",
    },
    {
        "name": "hang_issues_ap_init",
        "call_site": "0x91d8",
        "target": "0x13b8c",
        "failure_site": "0x92c4",
        "string": "Failed to init hang issues ap",
    },
    {
        "name": "gw_update_loop_init",
        "call_site": "0x91e0",
        "target": "0x11960",
        "failure_site": "0x92d8",
        "string": "Failed to init gw update loop",
    },
    {
        "name": "user_interface_init",
        "call_site": "0x91e8",
        "target": "0xfdc4",
        "failure_site": "0x92ec",
        "string": "Failed to init user interface",
    },
    {
        "name": "wlan_service_start",
        "call_site": "0x91f4",
        "target": "0xafdc",
        "failure_site": "0x9300",
        "string": "Failed to start wlan service",
    },
    {
        "name": "wlan_datapath_service_start",
        "call_site": "0x91fc",
        "target": "0xb2a4",
        "failure_site": "0x930c",
        "string": "Failed to start wlan datapath service",
    },
    {
        "name": "wlfw_start",
        "call_site": "0x9220",
        "target": "0xec00",
        "failure_site": "0x9318",
        "string": "Failed to start wlfw service",
    },
]

OBJDUMP_NEEDLES = {
    "property_get_debug": "9128:\t94002b4a \tbl\t13e50 <property_get_int32@plt>",
    "property_get_kmsg": "9140:\t94002b44 \tbl\t13e50 <property_get_int32@plt>",
    "main_to_wlfw_start": "9220:\t94001678 \tbl\tec00",
    "wlfw_start_entry": "ec00:\ta9be7bfd \tstp\tx29, x30, [sp, #-32]!",
    "wlfw_start_entry_log_ref": "ec1c:\t912ae442 \tadd\tx2, x2, #0xab9",
    "wlfw_start_second_log_ref": "edb4:\t912ae442 \tadd\tx2, x2, #0xab9",
    "logging_helper_entry": "a21c:\ta9bd7bfd \tstp\tx29, x30, [sp, #-48]!",
}

SAFETY_KEYS = (
    "no_service_manager",
    "no_pm_trio",
    "no_esoc0",
    "no_forced_rc1",
    "no_fake_online",
    "no_wifi_hal",
    "no_scan_connect",
    "no_credentials",
    "no_dhcp_routes",
    "no_external_ping",
)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
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


def ensure_objdump(binary: Path, objdump: Path) -> None:
    if objdump.exists():
        return
    objdump.parent.mkdir(parents=True, exist_ok=True)
    try:
        text = run_text(["aarch64-linux-gnu-objdump", "-d", str(binary)])
    except (FileNotFoundError, subprocess.CalledProcessError):
        text = run_text(["objdump", "-d", str(binary)])
    objdump.write_text(text, encoding="utf-8")


def parse_strings(binary: Path) -> dict[str, int]:
    output = run_text(["strings", "-a", "-t", "x", str(binary)])
    result: dict[str, int] = {}
    for line in output.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        try:
            offset = int(parts[0], 16)
        except ValueError:
            continue
        value = parts[1]
        if value in EXPECTED_STRINGS:
            result[value] = offset
    return result


def line_contains_address(text: str, address: str) -> bool:
    normalized = address.lower().removeprefix("0x")
    return f"{normalized}:" in text.lower()


def objdump_check(text: str, needle: str) -> bool:
    return needle in text


def is_one(value: Any) -> bool:
    return value is True or value == 1 or value == "1"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1691 = read_json(args.v1691_manifest)
    gate = v1691.get("gate", {})
    rollback = v1691.get("rollback", {})

    ensure_objdump(args.cnss_daemon, args.objdump)
    objdump_text = args.objdump.read_text(encoding="utf-8", errors="replace")
    strings_found = parse_strings(args.cnss_daemon)
    string_checks = {
        key: {
            "expected_offset": f"0x{expected:x}",
            "actual_offset": f"0x{strings_found[key]:x}" if key in strings_found else None,
            "match": strings_found.get(key) == expected,
        }
        for key, expected in EXPECTED_STRINGS.items()
    }
    objdump_checks = {name: objdump_check(objdump_text, needle) for name, needle in OBJDUMP_NEEDLES.items()}
    call_checks = {
        item["name"]: {
            "call_site_present": line_contains_address(objdump_text, item["call_site"]),
            "failure_site_present": (
                True if item["failure_site"] is None else line_contains_address(objdump_text, item["failure_site"])
            ),
            "string_offset": (
                f"0x{strings_found[item['string']]:x}" if item["string"] in strings_found else None
            ),
        }
        for item in CONTROL_FLOW
    }
    safety = {key: is_one(gate.get(key)) for key in SAFETY_KEYS}
    v1691_ok = (
        v1691.get("decision") == "v1691-cnss-output-still-invisible-rollback-pass"
        and v1691.get("pass") is True
        and gate.get("label") == "cnss-output-still-invisible"
        and gate.get("property_lookup_all_match") == "1"
        and gate.get("property_lookup_kmsg_value") == "1"
        and gate.get("property_lookup_debug_value") == "4"
        and rollback.get("ok") is True
    )
    static_map_ok = (
        all(check["match"] for check in string_checks.values())
        and all(objdump_checks.values())
        and all(check["call_site_present"] and check["failure_site_present"] for check in call_checks.values())
    )
    safety_ok = all(safety.values())
    pass_ok = v1691_ok and static_map_ok and safety_ok
    decision = (
        "v1692-cnss-nonlog-control-flow-map-pass"
        if pass_ok
        else "v1692-cnss-nonlog-control-flow-map-incomplete"
    )

    return {
        "cycle": CYCLE,
        "decision": decision,
        "pass": pass_ok,
        "reason": (
            "V1691 closed the property lookup gap; cnss-daemon static control-flow targets are mapped for bounded non-log live evidence"
            if pass_ok
            else "V1691 evidence or cnss-daemon static target mapping is incomplete"
        ),
        "inputs": {
            "v1691_manifest": display_path(args.v1691_manifest),
            "cnss_daemon": display_path(args.cnss_daemon),
            "objdump": display_path(args.objdump),
        },
        "binary": {
            "sha256": sha256_file(args.cnss_daemon),
            "size": args.cnss_daemon.stat().st_size,
        },
        "v1691": {
            "decision": v1691.get("decision"),
            "pass": v1691.get("pass"),
            "rollback_ok": rollback.get("ok"),
            "label": gate.get("label"),
            "property_lookup_all_match": gate.get("property_lookup_all_match"),
            "kmsg_logging": gate.get("property_lookup_kmsg_value"),
            "debug_level": gate.get("property_lookup_debug_value"),
            "cnss_daemon_running": gate.get("cnss_daemon_running"),
            "wlfw_start_seen": gate.get("wlfw_start_seen"),
            "first_failure_slug": gate.get("first_failure_slug"),
            "legacy_firmware_serve_label": gate.get("old_firmware_serve_label"),
        },
        "strings": string_checks,
        "objdump": objdump_checks,
        "control_flow": CONTROL_FLOW,
        "call_checks": call_checks,
        "static_targets": {
            "logging_helper_candidate": "cnss-daemon+0xa21c",
            "wlfw_start_entry": "cnss-daemon+0xec00",
            "wlfw_start_entry_log_ref": "cnss-daemon+0xec1c",
            "wlfw_start_success_log_ref": "cnss-daemon+0xedb4",
            "main_wlfw_start_call": "cnss-daemon+0x9220",
            "main_wlfw_start_failure_log": "cnss-daemon+0x9318",
        },
        "safety": safety,
        "next_gate": {
            "cycle": "V1693",
            "type": "one-run rollbackable read-only non-log cnss-daemon live classifier",
            "route": "reuse V1680/V1691 internal-modem firmware-serve route only",
            "targets": [
                "cnss-daemon load base plus 0xec00 wlfw_start entry",
                "cnss-daemon thread/liveness/wchan/fd/socket surface",
                "WLFW service 69 and firmware request absence/presence",
            ],
            "labels": [
                "cnss-wlfw-entry-hit-downstream-wait",
                "cnss-wlfw-entry-not-hit-init-stall",
                "cnss-process-exited-before-wlfw",
                "cnss-uprobe-unavailable-fallback-needed",
            ],
            "forbidden": [
                "service-manager",
                "PM trio",
                "boot_wlan as a WLFW trigger",
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
    }


def render_report(result: dict[str, Any]) -> str:
    status = "PASS" if result["pass"] else "FAIL"
    lines = [
        "# Native Init V1692 CNSS Non-log Control-flow Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{result['cycle']}`",
        "- Type: host-only cnss-daemon static control-flow classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: `{status}`",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{display_path(DEFAULT_OUT_DIR)}`",
        "",
        "## V1691 Basis",
        "",
        f"- V1691 decision: `{result['v1691']['decision']}`",
        f"- V1691 label: `{result['v1691']['label']}`",
        f"- Rollback OK: `{result['v1691']['rollback_ok']}`",
        f"- property lookup all_match: `{result['v1691']['property_lookup_all_match']}`",
        f"- kmsg/debug values: `{result['v1691']['kmsg_logging']}` / `{result['v1691']['debug_level']}`",
        f"- cnss-daemon running: `{result['v1691']['cnss_daemon_running']}`",
        f"- wlfw_start seen through logs: `{result['v1691']['wlfw_start_seen']}`",
        f"- first failure slug: `{result['v1691']['first_failure_slug']}`",
        "",
        "## Static Targets",
        "",
        f"- Binary: `{result['inputs']['cnss_daemon']}`",
        f"- SHA256: `{result['binary']['sha256']}`",
        f"- Size: `{result['binary']['size']}` bytes",
        f"- logging helper candidate: `{result['static_targets']['logging_helper_candidate']}`",
        f"- `wlfw_start` entry: `{result['static_targets']['wlfw_start_entry']}`",
        f"- main `wlfw_start` call: `{result['static_targets']['main_wlfw_start_call']}`",
        f"- main `wlfw_start` failure log: `{result['static_targets']['main_wlfw_start_failure_log']}`",
        "",
        "## Main Init Sequence",
        "",
        "| Step | call site | target | failure site | failure/log string |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in result["control_flow"]:
        failure_site = item["failure_site"] or "-"
        lines.append(
            f"| `{item['name']}` | `{item['call_site']}` | `{item['target']}` | `{failure_site}` | `{item['string']}` |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- V1691 already proves the private property namespace can read `persist.vendor.cnss-daemon.kmsg_logging=1` and `persist.vendor.cnss-daemon.debug_level=4`.",
        "- Missing `wlfw_start` in dmesg/syslog is therefore not explained by property lookup failure.",
        "- The stripped stock `cnss-daemon` contains a direct `wlfw_start` target at `cnss-daemon+0xec00`, called from the main init sequence at `+0x9220`.",
        "- The next proof should avoid Android log output entirely and observe process control flow, liveness, thread state, file descriptors, sockets, and WLFW service 69 directly.",
        "",
        "## V1693 Next Gate",
        "",
        "- Reuse the V1680/V1691 internal-modem firmware-serve route only: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.",
        "- Add bounded non-log evidence around `cnss-daemon+0xec00` using tracefs uprobe if available; otherwise use a documented fallback of maps/liveness/thread-state/fd/socket sampling.",
        "- Labels: `cnss-wlfw-entry-hit-downstream-wait`, `cnss-wlfw-entry-not-hit-init-stall`, `cnss-process-exited-before-wlfw`, `cnss-uprobe-unavailable-fallback-needed`.",
        "- Keep service-manager, PM trio, `boot_wlan` as a WLFW trigger, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping disabled.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cnss-daemon", type=Path, default=DEFAULT_CNSS_DAEMON)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--v1691-manifest", type=Path, default=DEFAULT_V1691_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args(argv)

    for path in (args.cnss_daemon, args.v1691_manifest):
        if not path.exists():
            raise SystemExit(f"missing required input: {display_path(path)}")

    result = build_manifest(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({
        "cycle": result["cycle"],
        "decision": result["decision"],
        "pass": result["pass"],
        "manifest": display_path(manifest_path),
        "report": display_path(args.report),
    }, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
