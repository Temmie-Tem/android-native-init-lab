#!/usr/bin/env python3
"""V1284 source/build-only gate for syslog/klogctl response sampler fallback."""

from __future__ import annotations

from pathlib import Path

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_response_sampler_value_support_v1269 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1284-execns-helper-v269-build")
base.DEFAULT_STAGE3_BINARY = Path("stage3/linux_init/helpers/a90_android_execns_probe_v269")
base.DEFAULT_V1268 = Path("tmp/wifi/v1283-pcie-kmsg-sampler-live/manifest.json")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1284-execns-helper-v269-build.txt")
base.HELPER_MARKER = "a90_android_execns_probe v269"
base.EXPECTED_V1268_DECISION = "v1283-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required"
base.REQUIRED_SOURCE_STRINGS = (
    'EXECNS_VERSION "a90_android_execns_probe v269"',
    "SYSLOG_ACTION_READ_ALL",
    "collect_response_syslog_markers",
    "syslog-read-all",
    "kmsg_source=%s",
    "kmsg_pcie_count=%d",
    "kmsg_wlfw_count=%d",
)
base.REQUIRED_BINARY_STRINGS = (
    base.HELPER_MARKER,
    "syslog-read-all",
    "kmsg_source=%s",
    "kmsg_open_ok=%d",
    "kmsg_pcie_count=%d",
    "kmsg_mhi_count=%d",
    "kmsg_wlfw_count=%d",
    "gpiochip_line_request_executed=0",
    "pmic_write_executed=0",
    "esoc_ioctl_executed=0",
)


def decide(command: str, rows: list[dict[str, str]], analysis: dict) -> tuple[str, bool, str, str]:
    if command == "plan":
        return ("v1284-klogctl-sampler-build-plan-ready", True, "plan-only", "run V1284 source/build-only gate")
    blockers = [row["name"] for row in rows if row["status"] != "pass"]
    if blockers:
        return ("v1284-klogctl-sampler-build-blocked", False, "blocked by " + ", ".join(blockers), "fix blockers before deploy")
    return (
        "v1284-klogctl-sampler-build-pass",
        True,
        f"helper v269 built sha256={analysis['build']['stage3']['sha256']}",
        "V1285 should deploy helper v269 only; V1286 should rerun the bounded PCIe/GDSC/klogctl sampler",
    )


def checks(command: str, analysis: dict) -> list[dict[str, str]]:
    rows = base.checks(command, analysis)
    for row in rows:
        if row.get("name") == "v1268-input":
            row["name"] = "v1283-input"
            row["next_step"] = "rerun V1283 before helper build"
        elif row.get("name") == "source-strings":
            row["next_step"] = "repair helper source syslog/klogctl fallback support"
        elif row.get("name") == "binary-strings":
            row["next_step"] = "repair built helper syslog/klogctl fallback strings"
    return rows


def render_summary(manifest: dict) -> str:
    rows = [[row["name"], row["status"], row["detail"], row["next_step"]] for row in manifest["checks"]]
    stage3 = (manifest["analysis"].get("build") or {}).get("stage3") or {}
    return "\n".join([
        "# V1284 syslog/klogctl Sampler Build",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{base.HELPER_MARKER}`",
        f"- stage3_sha256: `{stage3.get('sha256', '')}`",
        f"- output_size: `{stage3.get('size', 0)}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], rows),
        "",
    ])


base.decide = decide
base.render_summary = render_summary


def main() -> int:
    args = base.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = base.analyze(args, store)
    rows = checks(args.command, analysis)
    decision, passed, reason, next_step = decide(args.command, rows, analysis)
    manifest = {
        "cycle": "v1284",
        "generated_at": base.now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "analysis": analysis,
        "checks": rows,
        "device_commands_executed": False,
        "deploy_executed": False,
        "gpio_line_request_executed": False,
        "pmic_write_executed": False,
        "esoc_ioctl_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(base.LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
