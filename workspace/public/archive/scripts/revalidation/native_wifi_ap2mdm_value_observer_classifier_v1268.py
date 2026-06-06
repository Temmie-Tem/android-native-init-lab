#!/usr/bin/env python3
"""V1268 host-only classifier for the next AP2MDM value/power observer."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v1268-ap2mdm-value-observer-classifier")
DEFAULT_V1267 = Path("tmp/wifi/v1267-ext-mdm-ap2mdm-observer-live/manifest.json")
DEFAULT_V1262 = Path("tmp/wifi/v1262-gpiochip-line-info-live/manifest.json")
DEFAULT_V1255 = Path("tmp/wifi/v1255-pmic-power-mapping-preflight-live/manifest.json")
DEFAULT_V1251 = Path("tmp/wifi/v1251-pmic-soft-reset-debugfs-preflight-live/manifest.json")


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1267", type=Path, default=DEFAULT_V1267)
    parser.add_argument("--v1262", type=Path, default=DEFAULT_V1262)
    parser.add_argument("--v1255", type=Path, default=DEFAULT_V1255)
    parser.add_argument("--v1251", type=Path, default=DEFAULT_V1251)
    parser.add_argument("command", choices=("run", "plan"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        return {"_exists": False, "_path": str(path)}
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"_exists": True, "_path": str(path), "_json_error": str(exc)}
    if not isinstance(data, dict):
        return {"_exists": True, "_path": str(path), "_json_error": "not an object"}
    data["_exists"] = True
    data["_path"] = str(path)
    return data


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "pass"}
    return bool(value)


def analyze(v1267: dict[str, Any], v1262: dict[str, Any], v1255: dict[str, Any], v1251: dict[str, Any]) -> dict[str, Any]:
    sampler = v1267.get("response_sampler") if isinstance(v1267.get("response_sampler"), dict) else {}
    samples = sampler.get("samples") if isinstance(sampler.get("samples"), list) else []
    v1262_analysis = v1262.get("analysis") if isinstance(v1262.get("analysis"), dict) else {}
    v1255_analysis = v1255.get("analysis") if isinstance(v1255.get("analysis"), dict) else {}
    v1251_analysis = v1251.get("analysis") if isinstance(v1251.get("analysis"), dict) else {}

    line_flags = Counter(str(row.get("gpiochip_lineinfo_line_flags", "")) for row in samples)
    line_consumers = Counter(str(row.get("gpiochip_lineinfo_line_consumer", "")) for row in samples)
    mdm3_states = Counter(str(row.get("mdm3_state", "")) for row in samples)
    pcie1_lines = Counter(str(row.get("pcie1_gdsc_line", "")) for row in samples)

    v1267_ready = (
        v1267.get("decision") == "v1267-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required"
        and as_bool(v1267.get("pass"))
        and as_bool(sampler.get("gpiochip_lineinfo_seen"))
        and as_bool(sampler.get("gpiochip_lineinfo_kernel_owned_seen"))
        and as_bool(sampler.get("gpiochip_lineinfo_ap2mdm_consumer_seen"))
        and as_bool(sampler.get("gpiochip_lineinfo_zero_action_ok"))
    )
    v1267_output_state = bool(samples) and set(line_flags) == {"0x3"}
    v1267_no_response = (
        sampler.get("max_mdm_status_count_total") == 0
        and sampler.get("max_pci_dev_count") == 0
        and sampler.get("max_mhi_bus_count") == 0
        and not as_bool(sampler.get("mhi_pipe_seen"))
        and not as_bool(sampler.get("wlan0_seen"))
    )
    v1262_idle_kernel_input = (
        v1262.get("decision") == "v1262-gpiochip-line-info-pass"
        and as_bool(v1262.get("pass"))
        and str(v1262_analysis.get("line_flags")) == "0x1"
        and str(v1262_analysis.get("line_flag_kernel")) == "1"
        and str(v1262_analysis.get("line_flag_is_out")) == "0"
    )
    debugfs_gpio_mapping = (
        v1255.get("decision") == "v1255-pmic-gpio-mapping-incomplete"
        and as_bool(v1255.get("pass"))
        and as_bool(v1255_analysis.get("gpiochip_debugfs_line_seen"))
        and str(v1255_analysis.get("gpiochip_global_base")) == "1263"
        and str(v1255_analysis.get("gpiochip_expected_offset")) == "7"
        and as_bool(v1255_analysis.get("gpiochip_identity_match"))
    )
    debugfs_power_surface = (
        v1251.get("decision") == "v1251-pmic-debugfs-native-reproduction-candidate"
        and as_bool(v1251.get("pass"))
        and as_bool(v1251_analysis.get("debugfs_pinctrl_present"))
        and as_bool(v1251_analysis.get("debugfs_regulator_present"))
        and as_bool(v1251_analysis.get("pmic_soft_reset_seen"))
        and as_bool(v1251_analysis.get("pcie1_gdsc_seen"))
    )

    selected_next_gate = (
        "V1269 source/build-only helper v265: extend the V1267 response sampler "
        "with read-only debugfs gpio value/pinconf/regulator snapshots for PMIC GPIO9, "
        "TLMM GPIO135/142, and PCIe GDSC in the same PM-service esoc0 window"
    )
    return {
        "v1267_path": v1267.get("_path", ""),
        "v1262_path": v1262.get("_path", ""),
        "v1255_path": v1255.get("_path", ""),
        "v1251_path": v1251.get("_path", ""),
        "v1267_decision": v1267.get("decision", "missing"),
        "v1262_decision": v1262.get("decision", "missing"),
        "v1255_decision": v1255.get("decision", "missing"),
        "v1251_decision": v1251.get("decision", "missing"),
        "v1267_ready": v1267_ready,
        "v1267_sample_count": len(samples),
        "v1267_line_flags": dict(line_flags),
        "v1267_line_consumers": dict(line_consumers),
        "v1267_output_state": v1267_output_state,
        "v1267_mdm3_states": dict(mdm3_states),
        "v1267_pcie1_gdsc_lines": dict(pcie1_lines),
        "v1267_no_response": v1267_no_response,
        "v1262_idle_kernel_input": v1262_idle_kernel_input,
        "v1262_idle_line_flags": v1262_analysis.get("line_flags", ""),
        "v1262_idle_line_is_out": v1262_analysis.get("line_flag_is_out", ""),
        "debugfs_gpio_mapping": debugfs_gpio_mapping,
        "debugfs_power_surface": debugfs_power_surface,
        "selected_next_gate": selected_next_gate,
        "observer_requirements": {
            "must_sample": [
                "/sys/kernel/debug/gpio line for global GPIO1270 if present",
                "PMIC GPIO9 pinmux/pinconf lines from PM8150L pinctrl debugfs",
                "TLMM GPIO135/AP2MDM and GPIO142/MDM2AP pinmux/pinconf lines",
                "PCIe GDSC regulator_summary lines and PCIe RC1 readonly state",
                "existing GPIO142 IRQ, mdm3 state, PCI/MHI/wlan0 counters",
            ],
            "must_not_execute": [
                "GPIO line request or hold",
                "PMIC/debugfs/regulator writes",
                "direct eSoC ioctl",
                "new daemon/HAL start beyond existing bounded PM-service path",
                "Wi-Fi scan/connect, credentials, DHCP/routes, external ping",
                "flash, boot image write, partition write",
            ],
        },
    }


def build_checks(command: str, analysis: dict[str, Any], manifests: dict[str, dict[str, Any]]) -> list[Check]:
    if command == "plan":
        return [Check("plan-only", "pass", "info", "no evidence mutation or live command", "run V1268 classifier")]
    return [
        Check("v1267-input", "pass" if manifests["v1267"].get("_exists") and analysis["v1267_ready"] else "blocked", "blocker", f"decision={analysis['v1267_decision']} ready={analysis['v1267_ready']}", "rerun V1267 if missing"),
        Check("line-output-state", "pass" if analysis["v1267_output_state"] else "blocked", "blocker", f"flags={analysis['v1267_line_flags']}", "do not select value observer until line-info output state is proven"),
        Check("no-downstream-response", "pass" if analysis["v1267_no_response"] else "warn", "warning", f"mdm3={analysis['v1267_mdm3_states']} pcie1={analysis['v1267_pcie1_gdsc_lines']}", "if response exists, classify progress instead"),
        Check("idle-vs-window-delta", "pass" if analysis["v1262_idle_kernel_input"] else "warn", "warning", f"idle_flags={analysis['v1262_idle_line_flags']} idle_is_out={analysis['v1262_idle_line_is_out']}", "refresh idle line-info only if stale"),
        Check("debugfs-gpio-mapping", "pass" if analysis["debugfs_gpio_mapping"] else "blocked", "blocker", f"v1255={analysis['v1255_decision']}", "restore debugfs gpio mapping before value observer"),
        Check("debugfs-power-surface", "pass" if analysis["debugfs_power_surface"] else "blocked", "blocker", f"v1251={analysis['v1251_decision']}", "restore debugfs pinctrl/regulator evidence before value observer"),
    ]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return ("v1268-ap2mdm-value-observer-plan-ready", True, "plan-only; no live command executed", "run V1268 classifier")
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return ("v1268-ap2mdm-value-observer-blocked", False, "blocked by " + ", ".join(blockers), "refresh missing evidence")
    return (
        "v1268-ap2mdm-value-observer-selected",
        True,
        "AP2MDM soft-reset line is kernel-owned output in-window but SDX50M remains silent; next observer must read value/power state",
        analysis["selected_next_gate"],
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [
        ["decision", manifest["decision"]],
        ["pass", manifest["pass"]],
        ["v1267_sample_count", analysis["v1267_sample_count"]],
        ["v1267_line_flags", analysis["v1267_line_flags"]],
        ["v1267_line_consumers", analysis["v1267_line_consumers"]],
        ["v1267_output_state", analysis["v1267_output_state"]],
        ["v1267_no_response", analysis["v1267_no_response"]],
        ["v1262_idle_line_flags", analysis["v1262_idle_line_flags"]],
        ["v1262_idle_line_is_out", analysis["v1262_idle_line_is_out"]],
        ["debugfs_gpio_mapping", analysis["debugfs_gpio_mapping"]],
        ["debugfs_power_surface", analysis["debugfs_power_surface"]],
        ["selected_next_gate", analysis["selected_next_gate"]],
    ]
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    contract = analysis["observer_requirements"]
    return "\n".join([
        "# V1268 AP2MDM Value Observer Classifier",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## V1269 Required Observer",
        "",
        "### Must sample",
        "",
        *[f"- {item}" for item in contract["must_sample"]],
        "",
        "### Must not execute",
        "",
        *[f"- {item}" for item in contract["must_not_execute"]],
        "",
        "## Evidence",
        "",
        f"- V1267: `{analysis['v1267_path']}`",
        f"- V1262: `{analysis['v1262_path']}`",
        f"- V1255: `{analysis['v1255_path']}`",
        f"- V1251: `{analysis['v1251_path']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    store = EvidenceStore(repo_path(args.out_dir))
    manifests = {
        "v1267": load_json(args.v1267),
        "v1262": load_json(args.v1262),
        "v1255": load_json(args.v1255),
        "v1251": load_json(args.v1251),
    }
    analysis = analyze(manifests["v1267"], manifests["v1262"], manifests["v1255"], manifests["v1251"])
    checks = build_checks(args.command, analysis, manifests)
    decision, pass_ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "device_mutations": False,
        "live_command_executed": False,
        "gpio_line_request_executed": False,
        "pmic_write_executed": False,
        "esoc_ioctl_executed": False,
        "wifi_bringup_executed": False,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"gpio_line_request_executed: {manifest['gpio_line_request_executed']}")
    print(f"pmic_write_executed: {manifest['pmic_write_executed']}")
    print(f"esoc_ioctl_executed: {manifest['esoc_ioctl_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {repo_path(args.out_dir)}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
