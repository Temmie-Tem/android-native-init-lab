#!/usr/bin/env python3
"""V1764 source/build-only helper support for WLAN-PD service-object visibility.

This source/build gate adds a bounded helper mode that preserves the V1736
service-manager WLAN-PD route, starts only the minimum PeripheralManager service
object surface (`pm_proxy_helper` + `pm-service`, no `pm-proxy`), and records
whether that changes the no-request blocker.  It does not deploy or run on the
device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
SOURCE = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "revalidation" / "build_android_execns_probe_helper.sh"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1764-wlan-pd-service-object-visible-helper-build"
HELPER = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe_v330"
REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1764_WLAN_PD_SERVICE_OBJECT_VISIBLE_HELPER_BUILD_2026-06-03.md"
)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(args: list[str], cwd: Path = REPO_ROOT) -> dict[str, Any]:
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return {
        "args": args,
        "rc": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def source_checks(text: str) -> dict[str, bool]:
    new_order = (
        "servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,"
        "rmt_storage,tftp_server,pm_proxy_helper,per_mgr,vndservice_query,"
        "subsys_modem_holder,cnss_diag,cnss_daemon,service-object-visible-summary"
    )
    return {
        "version_v330": 'EXECNS_VERSION "a90_android_execns_probe v330"' in text,
        "mode_present": "wifi-companion-wlan-pd-service-object-visible-trigger-start-only" in text,
        "allow_flag_present": "--allow-wlan-pd-service-object-visible-trigger" in text,
        "config_bool_present": "allow_wlan_pd_service_object_visible_trigger" in text,
        "summary_function_present": "append_wlan_pd_service_object_visible_trigger_summary" in text,
        "new_order_present": new_order in text,
        "new_order_excludes_per_proxy": new_order in text and "per_mgr,per_proxy" not in new_order,
        "child_pm_proxy_helper_present": '"pm_proxy_helper",\n                                 "/vendor/bin/pm_proxy_helper"' in text,
        "child_per_mgr_present": '"per_mgr",\n                                 "/vendor/bin/pm-service"' in text,
        "conditional_per_proxy_only_for_broad_pm": "if (wlan_pd_pm_service_window_trigger) {\n                composite_child_init(&children[child_count++],\n                                     \"per_proxy\"" in text,
        "provider_query_present": "wlan_pd_service_object_visible_after_per_mgr" in text,
        "provider_seen_key_present": "wlan_pd_service_object_visible_trigger.provider_seen=%d" in text,
        "no_per_proxy_key_present": "wlan_pd_service_object_visible_trigger.no_per_proxy=1" in text,
        "requested_wlanmdsp_key_present": "wlan_pd_service_object_visible_trigger.requested_wlanmdsp=%d" in text,
        "wlfw_service69_key_present": "wlan_pd_service_object_visible_trigger.wlfw_service69_seen=%d" in text,
        "wlan0_key_present": "wlan_pd_service_object_visible_trigger.wlan0_present=%d" in text,
        "no_wifi_hal_key_present": "wlan_pd_service_object_visible_trigger.no_wifi_hal=1" in text,
        "no_scan_connect_key_present": "wlan_pd_service_object_visible_trigger.no_scan_connect=1" in text,
        "no_credentials_key_present": "wlan_pd_service_object_visible_trigger.no_credentials=1" in text,
        "no_dhcp_routes_key_present": "wlan_pd_service_object_visible_trigger.no_dhcp_routes=1" in text,
        "no_external_ping_key_present": "wlan_pd_service_object_visible_trigger.no_external_ping=1" in text,
        "no_esoc_rc1_keys_present": "wlan_pd_service_object_visible_trigger.no_esoc0=1" in text
        and "wlan_pd_service_object_visible_trigger.no_forced_rc1=1" in text,
        "no_restart_pd_literal_absent": "restart-PD" not in text,
    }


def classify(checks: dict[str, bool], build: dict[str, Any], file_info: str, marker_seen: bool, readelf_dynamic: str) -> tuple[str, bool, str]:
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        return (
            "v1764-service-object-helper-source-check-failed",
            False,
            f"missing source checks: {', '.join(failed)}",
        )
    if build["rc"] != 0:
        return (
            "v1764-service-object-helper-build-failed",
            False,
            "aarch64 static build returned non-zero",
        )
    if "statically linked" not in file_info or not marker_seen or "There is no dynamic section" not in readelf_dynamic:
        return (
            "v1764-service-object-helper-artifact-sanity-failed",
            False,
            "helper artifact is not proven static aarch64 with v330 marker",
        )
    return (
        "v1764-service-object-visible-helper-build-pass",
        True,
        "helper v330 adds bounded service-object-visible WLAN-PD mode and static artifact sanity passed",
    )


def render_report(manifest: dict[str, Any]) -> str:
    checks = manifest["source_checks"]
    failed = [name for name, ok in checks.items() if not ok]
    return "\n".join(
        [
            "# Native Init V1764 WLAN-PD Service-object-visible Helper Build",
            "",
            "## Summary",
            "",
            "- Cycle: `V1764`",
            "- Type: source/build-only helper mode",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: {'PASS' if manifest['pass'] else 'BLOCKED'}",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            f"- Helper: `{manifest['helper_path']}`",
            f"- Helper SHA256: `{manifest['helper_sha256']}`",
            "",
            "## New Mode",
            "",
            "- Mode: `wifi-companion-wlan-pd-service-object-visible-trigger-start-only`",
            "- Allow flag: `--allow-wlan-pd-service-object-visible-trigger`",
            "- Preserved route: V1736 service-manager WLAN-PD route with `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
            "- Added narrow surface: `pm_proxy_helper` plus `pm-service` and `vndservice list` provider query.",
            "- Explicitly excluded: broad `pm-proxy`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, eSoC/RC1, restart-PD, PMIC/GPIO/GDSC writes, PCI rescan, platform bind/unbind, firmware writes, and partition writes.",
            "",
            "## Required Output Keys",
            "",
            "- `wlan_pd_service_object_visible_trigger.provider_seen`",
            "- `wlan_pd_service_object_visible_trigger.requested_wlanmdsp`",
            "- `wlan_pd_service_object_visible_trigger.wlfw_service69_seen`",
            "- `wlan_pd_service_object_visible_trigger.wlan0_present`",
            "- `wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.*` for null branch, `asInterface`, manager register TX, and success path.",
            "- Safety keys: `no_wifi_hal`, `no_scan_connect`, `no_credentials`, `no_dhcp_routes`, `no_external_ping`, `no_esoc0`, `no_forced_rc1`, `no_per_proxy`.",
            "",
            "## Artifact Sanity",
            "",
            f"- `file`: `{manifest['file']}`",
            f"- Marker seen: `{manifest['marker_seen']}`",
            f"- Dynamic section: `{manifest['readelf_dynamic_summary']}`",
            f"- Build rc: `{manifest['build']['rc']}`",
            "",
            "## Source Checks",
            "",
            *[f"- `{key}`: `{value}`" for key, value in sorted(checks.items())],
            "",
            "## Classification",
            "",
            f"- Failed checks: `{failed}`",
            "- Live/deploy remains a separate gate. This unit only creates the bounded helper artifact needed for the next rollbackable discriminator.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--helper", type=Path, default=HELPER)
    parser.add_argument("--report-path", type=Path, default=REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    text = SOURCE.read_text(encoding="utf-8")
    checks = source_checks(text)
    build = run_cmd([str(BUILD_SCRIPT), str(args.helper)])
    store.write_text("build.stdout.txt", build["stdout"])
    store.write_text("build.stderr.txt", build["stderr"])
    file_result = run_cmd(["file", str(args.helper)])
    readelf_result = run_cmd(["aarch64-linux-gnu-readelf", "-d", str(args.helper)])
    strings_result = run_cmd(["strings", str(args.helper)])
    marker_seen = "a90_android_execns_probe v330" in strings_result["stdout"]
    helper_sha = sha256(args.helper) if args.helper.exists() else ""
    decision, pass_ok, reason = classify(
        checks,
        build,
        file_result["stdout"],
        marker_seen,
        readelf_result["stdout"] + readelf_result["stderr"],
    )
    manifest = {
        "cycle": "V1764",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "out_dir": display_path(args.out_dir),
        "source": display_path(SOURCE),
        "helper_path": display_path(args.helper),
        "helper_sha256": helper_sha,
        "build": build,
        "file": file_result["stdout"].strip(),
        "marker_seen": marker_seen,
        "readelf_dynamic_summary": (readelf_result["stdout"] + readelf_result["stderr"]).strip(),
        "source_checks": checks,
        "device_command_executed": False,
        "deploy_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "wifi_hal_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "esoc_rc1_executed": False,
        "firmware_write_executed": False,
        "partition_write_executed": False,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({"decision": decision, "pass": pass_ok, "helper_sha256": helper_sha, "out_dir": manifest["out_dir"]}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
