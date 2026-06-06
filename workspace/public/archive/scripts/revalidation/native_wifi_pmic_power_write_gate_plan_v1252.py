#!/usr/bin/env python3
"""V1252 host-only PMIC/power-surface write-gate plan classifier.

V1251 proved that the native debugfs read contract is complete and that the
current native path is a reproduction candidate: PM8150L soft-reset remains
unclaimed, PCIe GDSC lines remain at 0mV, mdm3 remains OFFLINING, and GPIO142
does not fire.  This classifier turns that evidence into the next bounded
source/build gate without executing device commands or mutating device state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1252-pmic-power-write-gate-plan")
LATEST_POINTER = Path("tmp/wifi/latest-v1252-pmic-power-write-gate-plan.txt")
DEFAULT_V1251_MANIFEST = Path("tmp/wifi/v1251-pmic-soft-reset-debugfs-preflight-live/manifest.json")
DEFAULT_V1244_REPORT = Path("docs/reports/NATIVE_INIT_V1244_ANDROID_POWER_SURFACE_CLASSIFIER_2026-05-31.md")
DEFAULT_V1247_REPORT = Path("docs/reports/NATIVE_INIT_V1247_PMIC_PINCTRL_REPRO_PLAN_2026-05-31.md")
DEFAULT_V1251_REPORT = Path("docs/reports/NATIVE_INIT_V1251_PMIC_SOFT_RESET_DEBUGFS_PREFLIGHT_LIVE_2026-05-31.md")
DEFAULT_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1251-manifest", type=Path, default=DEFAULT_V1251_MANIFEST)
    parser.add_argument("--v1244-report", type=Path, default=DEFAULT_V1244_REPORT)
    parser.add_argument("--v1247-report", type=Path, default=DEFAULT_V1247_REPORT)
    parser.add_argument("--v1251-report", type=Path, default=DEFAULT_V1251_REPORT)
    parser.add_argument("--research", type=Path, default=DEFAULT_RESEARCH)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    return parser.parse_args()


def read_text(path: Path, limit: int = 8 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def has_all(text: str, needles: tuple[str, ...]) -> bool:
    return all(needle in text for needle in needles)


def first_line(text: str, *needles: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if all(needle in line for needle in needles):
            return line
    return ""


def selected_next_gate() -> dict[str, Any]:
    return {
        "cycle": "v1253",
        "kind": "source-build-only",
        "helper_version": "v261",
        "mode": "wifi-companion-pmic-power-surface-write-gate-preflight",
        "purpose": "add a fail-closed two-stage PMIC GPIO9 line-hold proof before any subsystem trigger",
        "stage_1": [
            "verify the complete V1251 read contract with debugfs mounted by the host runner",
            "locate a PM8150L gpiochip candidate without writing",
            "map PMIC GPIO9 to the observed global line 1270 / chip offset 7 only if chip identity is unambiguous",
            "print all intended line-hold parameters and exit without mutation unless a later live gate supplies the write flag",
        ],
        "stage_2_later_live": [
            "request PMIC GPIO9 as output-low using the kernel GPIO chardev only if identity and offset are exact",
            "hold the line fd for a bounded window and sample debugfs pinctrl/regulator/IRQ state",
            "close the fd for cleanup and verify the read surface returns to a safe post-state",
            "do not open /dev/subsys_esoc0, start PM actors, or start CNSS/HAL in the first write proof",
        ],
        "explicit_rejections": [
            "no /sys/class/gpio export/write",
            "no debugfs pinctrl write",
            "no debugfs regulator write",
            "no direct PCIe GDSC enable",
            "no blind /dev/subsys_esoc0 retry",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
        ],
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1251 = load_json(args.v1251_manifest)
    v1244_report = read_text(args.v1244_report)
    v1247_report = read_text(args.v1247_report)
    v1251_report = read_text(args.v1251_report)
    research = read_text(args.research)
    helper_source = read_text(args.helper_source)

    v1251_analysis = v1251.get("analysis") if isinstance(v1251.get("analysis"), dict) else {}
    preflight_values = v1251_analysis.get("preflight_values") if isinstance(v1251_analysis.get("preflight_values"), dict) else {}
    zero_markers = v1251_analysis.get("zero_markers") if isinstance(v1251_analysis.get("zero_markers"), dict) else {}

    evidence_checks = {
        "v1251_manifest_pass": bool(v1251.get("pass")),
        "v1251_decision_candidate": v1251.get("decision") == "v1251-pmic-debugfs-native-reproduction-candidate",
        "v1251_cleanup_ok": bool(v1251_analysis.get("cleanup_ok")),
        "v1251_read_contract_ready": bool(v1251_analysis.get("read_contract_ready")),
        "v1251_native_candidate": bool(v1251_analysis.get("native_reproduction_candidate")),
        "v1251_zero_markers_ok": bool(v1251_analysis.get("all_zero_markers_ok")) and all(bool(value) for value in zero_markers.values()),
        "pmic_line_unclaimed": "MUX UNCLAIMED" in str(preflight_values.get("pmic_soft_reset_line", "")),
        "pcie_gdsc_zero": "0mV" in str(preflight_values.get("pcie1_gdsc_line", "")) and "0mV" in str(preflight_values.get("pcie0_gdsc_line", "")),
        "mdm3_offlining": preflight_values.get("mdm3_state") == "OFFLINING",
        "gpio142_silent": str(preflight_values.get("mdm_status_count_total")) == "0",
        "android_delta_documented": has_all(v1244_report, ("PM8150L soft-reset GPIO", "Native V1243", "GPIO142", "wlan0")),
        "prior_rejections_documented": has_all(v1247_report, ("Direct `/sys/class/gpio` export/write", "Debugfs pinctrl/regulator write", "Blind `/dev/subsys_esoc0` retry")),
        "v1251_report_documents_candidate": has_all(v1251_report, ("native_reproduction_candidate", "read_contract_ready", "zero-action markers")),
        "research_maps_soft_reset_gpio": has_all(research, ("qcom,ap2mdm-soft-reset-gpio", "PMIC pm8150l GPIO 9", "sdx50m_toggle_soft_reset")),
        "helper_write_flag_reserved": has_all(helper_source, ("allow_pmic_soft_reset_write", "reserved fail-closed gate", "write_gate_implemented=0")),
    }

    hard_preconditions = {
        "debugfs_read_contract": [
            "debugfs_pinctrl_present=1",
            "debugfs_regulator_present=1",
            "pmic_soft_reset_seen=1",
            "pcie1_gdsc_seen=1",
            "pcie0_gdsc_seen=1",
        ],
        "native_gap_contract": [
            "PMIC soft-reset line contains MUX UNCLAIMED",
            "pcie_1_gdsc and pcie_0_gdsc lines contain 0mV",
            "mdm3_state=OFFLINING",
            "mdm_status_count_total=0",
            "wlan0 absent before any later write gate",
        ],
        "write_contract": [
            "operator supplies a separate write approval phrase in the later live cycle",
            "helper prints resolved gpiochip, line offset, initial sample, action, hold duration, and cleanup sample",
            "first write proof does not start PM actors and does not open /dev/subsys_esoc0",
            "postflight selftest fail=0 and debugfs cleanup verified",
        ],
    }

    checks = [
        {
            "name": name,
            "status": "pass" if passed else "blocked",
            "detail": str(passed),
        }
        for name, passed in evidence_checks.items()
    ]
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    passed = not blockers
    decision = "v1252-bounded-pmic-power-write-gate-plan-ready" if passed else "v1252-pmic-power-write-gate-plan-blocked"
    reason = (
        "V1251 proves a complete native reproduction candidate; next source/build gate can add a fail-closed PMIC GPIO9 line-hold proof"
        if passed else
        "blocked by missing or contradictory evidence: " + ", ".join(blockers)
    )

    return {
        "evidence_checks": evidence_checks,
        "checks": checks,
        "blockers": blockers,
        "hard_preconditions": hard_preconditions,
        "selected_next_gate": selected_next_gate(),
        "summary_fields": {
            "pmic_soft_reset_line": preflight_values.get("pmic_soft_reset_line", ""),
            "pcie1_gdsc_line": preflight_values.get("pcie1_gdsc_line", ""),
            "pcie0_gdsc_line": preflight_values.get("pcie0_gdsc_line", ""),
            "mdm3_state": preflight_values.get("mdm3_state", ""),
            "mdm_status_count_total": preflight_values.get("mdm_status_count_total", ""),
        },
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": (
            "V1253 source/build-only helper v261 with fail-closed PMIC GPIO9 line-hold preflight"
            if passed else
            "repair evidence inputs before designing the write gate"
        ),
    }


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    gate = analysis["selected_next_gate"]
    fields = analysis["summary_fields"]
    preconditions = analysis["hard_preconditions"]
    return "\n".join([
        "# V1252 PMIC/Power-surface Write-gate Plan",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Evidence Checks",
        "",
        markdown_table(["check", "status", "detail"], [[c["name"], c["status"], c["detail"]] for c in analysis["checks"]]),
        "",
        "## Current Blocker Surface",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in fields.items()]),
        "",
        "## Selected Next Gate",
        "",
        markdown_table(["field", "value"], [
            ["cycle", gate["cycle"]],
            ["kind", gate["kind"]],
            ["helper_version", gate["helper_version"]],
            ["mode", gate["mode"]],
            ["purpose", gate["purpose"]],
        ]),
        "",
        "## Hard Preconditions",
        "",
        markdown_table(["group", "items"], [[group, "; ".join(items)] for group, items in preconditions.items()]),
        "",
        "## Explicit Rejections",
        "",
        "\n".join(f"- {item}" for item in gate["explicit_rejections"]),
        "",
        "## Safety",
        "",
        "- host-only classifier; no device command, live write, daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, reboot, flash, boot image write, or partition write",
        "- V1253 must remain source/build-only; the first later live write proof must hold only PMIC GPIO9 and must not open `/dev/subsys_esoc0`",
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    analysis = analyze(args)
    return {
        "cycle": "v1252",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "next_step": analysis["next_step"],
        "host": collect_host_metadata(),
        "inputs": {
            "v1251_manifest": str(repo_path(args.v1251_manifest)),
            "v1244_report": str(repo_path(args.v1244_report)),
            "v1247_report": str(repo_path(args.v1247_report)),
            "v1251_report": str(repo_path(args.v1251_report)),
            "research": str(repo_path(args.research)),
            "helper_source": str(repo_path(args.helper_source)),
        },
        "analysis": analysis,
        "device_commands_executed": False,
        "live_write_executed": False,
        "pmic_write_executed": False,
        "debugfs_write_executed": False,
        "regulator_write_executed": False,
        "gpio_write_executed": False,
        "esoc_ioctl_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "reboot_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
