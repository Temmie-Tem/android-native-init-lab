#!/usr/bin/env python3
"""V1272 host-only classifier for the next AP2MDM block sampler."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1272-ap2mdm-block-sampler-classifier")
DEFAULT_V1271 = Path("tmp/wifi/v1271-ap2mdm-value-power-observer-live/manifest.json")
DEFAULT_V1267 = Path("tmp/wifi/v1267-ext-mdm-ap2mdm-observer-live/manifest.json")
LATEST_POINTER = Path("tmp/wifi/latest-v1272-ap2mdm-block-sampler-classifier.txt")


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
    parser.add_argument("--v1271", type=Path, default=DEFAULT_V1271)
    parser.add_argument("--v1267", type=Path, default=DEFAULT_V1267)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
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
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "pass"}
    return bool(value)


def counter(samples: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(Counter(str(row.get(field, "")) for row in samples))


def unique_values(samples: list[dict[str, Any]], field: str) -> list[str]:
    values = sorted({str(row.get(field, "")) for row in samples if str(row.get(field, ""))})
    return values


def analyze(v1271: dict[str, Any], v1267: dict[str, Any]) -> dict[str, Any]:
    sampler = v1271.get("response_sampler") if isinstance(v1271.get("response_sampler"), dict) else {}
    samples = sampler.get("samples") if isinstance(sampler.get("samples"), list) else []
    sample_count = len(samples)
    v1267_sampler = v1267.get("response_sampler") if isinstance(v1267.get("response_sampler"), dict) else {}

    value_lines_absent = (
        not as_bool(sampler.get("pmic_gpio1270_debugfs_seen"))
        and not as_bool(sampler.get("tlmm_gpio135_debugfs_seen"))
        and not as_bool(sampler.get("tlmm_gpio142_debugfs_seen"))
    )
    pinctrl_surface_seen = (
        as_bool(sampler.get("debugfs_pinctrl_seen"))
        and as_bool(sampler.get("pmic9_pinconf_seen"))
        and as_bool(sampler.get("pin135_pinconf_seen"))
        and as_bool(sampler.get("pin142_pinconf_seen"))
    )
    gpio_surface_seen = as_bool(sampler.get("debugfs_gpio_seen"))
    regulator_surface_seen = as_bool(sampler.get("debugfs_regulator_seen"))
    lineinfo_output = (
        as_bool(sampler.get("gpiochip_lineinfo_seen"))
        and as_bool(sampler.get("gpiochip_lineinfo_kernel_owned_seen"))
        and as_bool(sampler.get("gpiochip_lineinfo_ap2mdm_consumer_seen"))
        and set(counter(samples, "gpiochip_lineinfo_line_flags")) == {"0x3"}
    )
    zero_action_ok = as_bool(sampler.get("gpiochip_lineinfo_zero_action_ok"))
    no_downstream_response = (
        sampler.get("max_mdm_status_count_total") == 0
        and sampler.get("max_pci_dev_count") == 0
        and sampler.get("max_mhi_bus_count") == 0
        and not as_bool(sampler.get("mhi_pipe_seen"))
        and not as_bool(sampler.get("wlan0_seen"))
    )
    v1271_ready = (
        v1271.get("decision") == "v1271-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required"
        and as_bool(v1271.get("pass"))
        and sample_count > 0
        and lineinfo_output
        and zero_action_ok
        and gpio_surface_seen
        and pinctrl_surface_seen
        and regulator_surface_seen
        and no_downstream_response
    )
    v1267_consistent = (
        v1267.get("decision") == "v1267-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required"
        and as_bool(v1267.get("pass"))
        and as_bool(v1267_sampler.get("gpiochip_lineinfo_seen"))
        and not as_bool(v1267_sampler.get("wlan0_seen"))
    )

    selected_next_gate = (
        "V1273 source/build-only helper v266: extend the late PM-service response "
        "sampler with compact read-only debugfs GPIO/pinconf block capture around "
        "PM8150L GPIO9/global GPIO1270, TLMM GPIO135/GPIO142, and PCIe RC1/GDSC state"
    )
    return {
        "v1271_path": v1271.get("_path", ""),
        "v1267_path": v1267.get("_path", ""),
        "v1271_decision": v1271.get("decision", "missing"),
        "v1267_decision": v1267.get("decision", "missing"),
        "v1271_ready": v1271_ready,
        "v1267_consistent": v1267_consistent,
        "sample_count": sample_count,
        "lineinfo_output": lineinfo_output,
        "lineinfo_flags": counter(samples, "gpiochip_lineinfo_line_flags"),
        "lineinfo_consumers": counter(samples, "gpiochip_lineinfo_line_consumer"),
        "zero_action_ok": zero_action_ok,
        "gpio_surface_seen": gpio_surface_seen,
        "pinctrl_surface_seen": pinctrl_surface_seen,
        "regulator_surface_seen": regulator_surface_seen,
        "value_lines_absent": value_lines_absent,
        "pmic_gpio1270_debugfs_seen": as_bool(sampler.get("pmic_gpio1270_debugfs_seen")),
        "tlmm_gpio135_debugfs_seen": as_bool(sampler.get("tlmm_gpio135_debugfs_seen")),
        "tlmm_gpio142_debugfs_seen": as_bool(sampler.get("tlmm_gpio142_debugfs_seen")),
        "pmic9_pinconf_values": unique_values(samples, "pmic9_pinconf_line"),
        "pin135_pinconf_values": unique_values(samples, "pin135_pinconf_line"),
        "pin142_pinconf_values": unique_values(samples, "pin142_pinconf_line"),
        "pmic_soft_reset_lines": unique_values(samples, "pmic_soft_reset_line"),
        "pin135_pinmux_lines": unique_values(samples, "pin135_line"),
        "pin142_pinmux_lines": unique_values(samples, "pin142_line"),
        "pcie0_gdsc_lines": counter(samples, "pcie0_gdsc_line"),
        "pcie1_gdsc_lines": counter(samples, "pcie1_gdsc_line"),
        "no_downstream_response": no_downstream_response,
        "selected_next_gate": selected_next_gate,
        "v1273_contract": {
            "must_sample_read_only_blocks": [
                "/sys/kernel/debug/gpio block for gpiochip ranges containing PM8150L global GPIO1270",
                "/sys/kernel/debug/gpio block for TLMM GPIO135 and GPIO142 if exposed",
                "PM8150L GPIO9 pinmux and pinconf block with surrounding lines",
                "TLMM GPIO135/GPIO142 pinmux and pinconf block with surrounding lines",
                "PCIe RC1 debug/power/runtime state and pcie_0_gdsc/pcie_1_gdsc regulator lines",
                "existing GPIO142 IRQ, mdm3 state, PCI/MHI/MHI-pipe/wlan0 counters",
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


def build_checks(command: str, analysis: dict[str, Any]) -> list[Check]:
    if command == "plan":
        return [Check("plan-only", "pass", "info", "no evidence mutation or live command", "run V1272 classifier")]
    return [
        Check("v1271-input", "pass" if analysis["v1271_ready"] else "blocked", "blocker", f"decision={analysis['v1271_decision']} samples={analysis['sample_count']}", "rerun V1271 if missing"),
        Check("v1267-consistency", "pass" if analysis["v1267_consistent"] else "warn", "warning", f"decision={analysis['v1267_decision']}", "refresh V1267 only if V1271 contradicts it"),
        Check("lineinfo-output", "pass" if analysis["lineinfo_output"] else "blocked", "blocker", f"flags={analysis['lineinfo_flags']} consumers={analysis['lineinfo_consumers']}", "do not build block sampler until output ownership is proven"),
        Check("read-only-surfaces", "pass" if analysis["gpio_surface_seen"] and analysis["pinctrl_surface_seen"] and analysis["regulator_surface_seen"] else "blocked", "blocker", f"gpio={analysis['gpio_surface_seen']} pinctrl={analysis['pinctrl_surface_seen']} regulator={analysis['regulator_surface_seen']}", "restore debugfs surface before block sampler"),
        Check("value-lines-absent", "pass" if analysis["value_lines_absent"] else "warn", "warning", f"pmic1270={analysis['pmic_gpio1270_debugfs_seen']} tlmm135={analysis['tlmm_gpio135_debugfs_seen']} tlmm142={analysis['tlmm_gpio142_debugfs_seen']}", "if value lines exist, parse them before adding block sampler"),
        Check("no-downstream-response", "pass" if analysis["no_downstream_response"] else "warn", "warning", "GPIO142/PCI/MHI/wlan0 remain absent", "if response exists, classify progress instead"),
    ]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return ("v1272-ap2mdm-block-sampler-plan-ready", True, "plan-only; no live command executed", "run V1272 classifier")
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return ("v1272-ap2mdm-block-sampler-blocked", False, "blocked by " + ", ".join(blockers), "refresh missing evidence")
    return (
        "v1272-ap2mdm-block-sampler-selected",
        True,
        "V1271 proved read-only surfaces are present but exact value lines are missing; next observer should capture compact surrounding blocks",
        analysis["selected_next_gate"],
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [
        ["decision", manifest["decision"]],
        ["pass", manifest["pass"]],
        ["v1271_sample_count", analysis["sample_count"]],
        ["lineinfo_flags", analysis["lineinfo_flags"]],
        ["lineinfo_consumers", analysis["lineinfo_consumers"]],
        ["gpio_surface_seen", analysis["gpio_surface_seen"]],
        ["pinctrl_surface_seen", analysis["pinctrl_surface_seen"]],
        ["regulator_surface_seen", analysis["regulator_surface_seen"]],
        ["value_lines_absent", analysis["value_lines_absent"]],
        ["no_downstream_response", analysis["no_downstream_response"]],
        ["selected_next_gate", analysis["selected_next_gate"]],
    ]
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    contract = analysis["v1273_contract"]
    return "\n".join([
        "# V1272 AP2MDM Block Sampler Classifier",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## V1273 Required Observer",
        "",
        "### Must sample read-only blocks",
        "",
        *[f"- {item}" for item in contract["must_sample_read_only_blocks"]],
        "",
        "### Must not execute",
        "",
        *[f"- {item}" for item in contract["must_not_execute"]],
        "",
        "## Evidence",
        "",
        f"- V1271: `{analysis['v1271_path']}`",
        f"- V1267: `{analysis['v1267_path']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    store = EvidenceStore(repo_path(args.out_dir))
    v1271 = load_json(args.v1271)
    v1267 = load_json(args.v1267)
    analysis = analyze(v1271, v1267)
    checks = build_checks(args.command, analysis)
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
    LATEST_POINTER.write_text(str(repo_path(args.out_dir / "manifest.json")) + "\n", encoding="utf-8")
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
