#!/usr/bin/env python3
"""Host-only V1689 classifier for the V1688 cnss-daemon property visibility gap."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1689"
DEFAULT_V1688_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1688-wlan-pd-cnss-output-visibility-handoff"
    / "manifest.json"
)
DEFAULT_V1688_HELPER_OUTPUT = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1688-wlan-pd-cnss-output-visibility-handoff"
    / "test-v1393-helper-result.stdout.txt"
)
DEFAULT_V1687_PROPERTY_ROOT = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1687-wlan-pd-cnss-output-visibility-test-boot"
    / "property-runtime"
    / "layout"
    / "dev"
    / "__properties__"
)
DEFAULT_HELPER_SOURCE = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1689-cnss-property-visibility-gap"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1689_CNSS_PROPERTY_VISIBILITY_GAP_2026-06-02.md"
)
EXPECTED_KEYS = (
    "persist.vendor.cnss-daemon.kmsg_logging",
    "persist.vendor.cnss-daemon.debug_level",
)
EXPECTED_LOOKUP_VALUES = {
    "persist.vendor.cnss-daemon.kmsg_logging": "1",
    "persist.vendor.cnss-daemon.debug_level": "4",
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def direct_lookup_lines(text: str, key: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if key not in line:
            continue
        if ".expected_property." in line:
            continue
        if "property_lookup" in line or "getprop" in line or "actual_property" in line:
            lines.append(line)
    return lines


def generic_non_expected_key_lines(text: str, key: str) -> list[str]:
    return [line for line in text.splitlines() if key in line and ".expected_property." not in line]


def property_area_contains_keys(property_root: Path) -> dict[str, bool]:
    result = {key: False for key in EXPECTED_KEYS}
    if not property_root.exists():
        return result
    for path in property_root.iterdir():
        if not path.is_file():
            continue
        data = path.read_bytes()
        for key in EXPECTED_KEYS:
            if key.encode("utf-8") in data:
                result[key] = True
    return result


def is_one(value: Any) -> bool:
    return value is True or value == 1 or value == "1"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1688 = read_json(args.v1688_manifest)
    helper_output = read_text(args.v1688_helper_output)
    helper_source = read_text(args.helper_source)
    gate = v1688.get("gate", {})
    property_deploy = v1688.get("property_deploy", {})
    rollback = v1688.get("rollback", {})

    allowlist = {key: key in helper_source for key in EXPECTED_KEYS}
    expected_lines = {
        key: f"wlan_pd_cnss_output_visibility.expected_property.{key}={EXPECTED_LOOKUP_VALUES[key]}" in helper_output
        for key in EXPECTED_KEYS
    }
    lookup_lines = {key: direct_lookup_lines(helper_output, key) for key in EXPECTED_KEYS}
    non_expected_lines = {key: generic_non_expected_key_lines(helper_output, key) for key in EXPECTED_KEYS}
    property_area_keys = property_area_contains_keys(args.property_root)
    safety = {key: is_one(gate.get(key)) for key in SAFETY_KEYS}

    v1688_ok = (
        v1688.get("decision") == "v1688-cnss-output-still-invisible-rollback-pass"
        and v1688.get("pass") is True
        and gate.get("label") == "cnss-output-still-invisible"
        and rollback.get("ok") is True
    )
    property_deploy_ok = (
        property_deploy.get("property_info_sha_ok") is True
        and property_deploy.get("vendor_default_sha_ok") is True
    )
    output_visibility_attempted = (
        is_one(gate.get("cnss_daemon_running"))
        and is_one(gate.get("syslog_available"))
        and (gate.get("syslog_errno") == 0 or gate.get("syslog_errno") == "0")
        and all(expected_lines.values())
    )
    lookup_proven = all(bool(lookup_lines[key]) for key in EXPECTED_KEYS)
    keys_allowlisted = all(allowlist.values())
    keys_in_property_area = all(property_area_keys.values())
    safety_ok = all(safety.values())
    pass_ok = (
        v1688_ok
        and property_deploy_ok
        and output_visibility_attempted
        and keys_allowlisted
        and keys_in_property_area
        and safety_ok
        and not lookup_proven
    )
    decision = (
        "v1689-cnss-property-consumption-unproven-pass"
        if pass_ok
        else "v1689-cnss-property-visibility-gap-incomplete"
    )

    return {
        "cycle": CYCLE,
        "decision": decision,
        "pass": pass_ok,
        "reason": (
            "V1688 staged and mapped cnss logging properties, but captured no direct property lookup or consumption proof"
            if pass_ok
            else "V1688 evidence is insufficient or inconsistent for the cnss property visibility gap classifier"
        ),
        "inputs": {
            "v1688_manifest": display_path(args.v1688_manifest),
            "v1688_helper_output": display_path(args.v1688_helper_output),
            "property_root": display_path(args.property_root),
            "helper_source": display_path(args.helper_source),
        },
        "v1688": {
            "decision": v1688.get("decision"),
            "pass": v1688.get("pass"),
            "rollback_ok": rollback.get("ok"),
            "label": gate.get("label"),
            "legacy_firmware_serve_label": gate.get("old_firmware_serve_label"),
            "cnss_daemon_running": gate.get("cnss_daemon_running"),
            "syslog_available": gate.get("syslog_available"),
            "syslog_errno": gate.get("syslog_errno"),
            "syslog_filtered_count": gate.get("syslog_filtered_count"),
            "wlfw_start_seen": gate.get("wlfw_start_seen"),
            "first_failure_slug": gate.get("first_failure_slug"),
        },
        "property_runtime": {
            "property_info_sha_ok": property_deploy.get("property_info_sha_ok"),
            "vendor_default_sha_ok": property_deploy.get("vendor_default_sha_ok"),
            "remote_property_root": property_deploy.get("remote_property_root"),
            "file_count": property_deploy.get("file_count"),
            "bytes": property_deploy.get("bytes"),
            "keys_in_property_area": property_area_keys,
        },
        "visibility_gap": {
            "keys_allowlisted": allowlist,
            "expected_property_lines_seen": expected_lines,
            "direct_lookup_lines": lookup_lines,
            "non_expected_key_lines": non_expected_lines,
            "lookup_proven": lookup_proven,
            "label": "cnss-property-consumption-unproven",
        },
        "safety": safety,
        "next_gate": {
            "cycle": "V1690",
            "type": "source/build-only then one rollbackable live proof",
            "intent": "add direct same-namespace property lookup evidence for cnss-daemon logging keys before interpreting missing cnss output",
            "required_keys": dict(EXPECTED_LOOKUP_VALUES),
            "forbidden": [
                "new PM/service-window actors",
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


def write_report(manifest: dict[str, Any], path: Path) -> None:
    gap = manifest["visibility_gap"]
    v1688 = manifest["v1688"]
    runtime = manifest["property_runtime"]
    lines = [
        "# Native Init V1689 CNSS Property Visibility Gap",
        "",
        "## Summary",
        "",
        f"- Cycle: `{manifest['cycle']}`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- Reason: {manifest['reason']}",
        "",
        "## V1688 Basis",
        "",
        f"- V1688 decision: `{v1688['decision']}`",
        f"- V1688 label: `{v1688['label']}`",
        f"- Rollback OK: `{v1688['rollback_ok']}`",
        f"- cnss-daemon running: `{v1688['cnss_daemon_running']}`",
        f"- syslog available/errno: `{v1688['syslog_available']}` / `{v1688['syslog_errno']}`",
        f"- syslog filtered count: `{v1688['syslog_filtered_count']}`",
        f"- wlfw_start seen: `{v1688['wlfw_start_seen']}`",
        f"- first failure slug: `{v1688['first_failure_slug']}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{runtime['remote_property_root']}`",
        f"- Uploaded files/bytes: `{runtime['file_count']}` / `{runtime['bytes']}`",
        f"- property_info SHA verified: `{runtime['property_info_sha_ok']}`",
        f"- vendor_default_prop SHA verified: `{runtime['vendor_default_sha_ok']}`",
        "",
        "## Visibility Gap",
        "",
        "- The helper source allowlists both cnss logging keys.",
        "- The private property area contains both cnss logging key names.",
        "- V1688 helper output contains only `expected_property` lines for these keys.",
        "- V1688 helper output does not contain direct `getprop`, `property_lookup`, or actual property-consumption lines for these keys.",
        "- Therefore `cnss-output-still-invisible` is not yet proof that `cnss-daemon` consumed `persist.vendor.cnss-daemon.kmsg_logging=1`.",
        "",
        "| Key | allowlisted | in property area | expected line | direct lookup proven |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key in EXPECTED_KEYS:
        lines.append(
            f"| `{key}` | `{gap['keys_allowlisted'][key]}` | "
            f"`{runtime['keys_in_property_area'][key]}` | "
            f"`{gap['expected_property_lines_seen'][key]}` | "
            f"`{bool(gap['direct_lookup_lines'][key])}` |"
        )
    lines.extend([
        "",
        "## Next Gate",
        "",
        "- V1690 should add direct same-namespace lookup evidence for the two cnss logging keys before reinterpreting missing cnss output.",
        "- Keep the V1680 internal-modem firmware-serve route and do not add PM/service-window actors.",
        "- Keep `boot_wlan` out of scope as a WLFW trigger; ICNSS driver registration waits for FW_READY and does not publish WLFW service 69.",
        "- Keep `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping disabled.",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1688-manifest", type=Path, default=DEFAULT_V1688_MANIFEST)
    parser.add_argument("--v1688-helper-output", type=Path, default=DEFAULT_V1688_HELPER_OUTPUT)
    parser.add_argument("--property-root", type=Path, default=DEFAULT_V1687_PROPERTY_ROOT)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    write_report(manifest, args.report)
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "report": display_path(args.report),
        "manifest": display_path(args.out_dir / "manifest.json"),
    }, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
