#!/usr/bin/env python3
"""V1264 host-only ext-mdm/AP2MDM observer plan classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v1264-ext-mdm-ap2mdm-observer-plan")
DEFAULT_V1263 = Path("tmp/wifi/v1263-ap2mdm-soft-reset-contract-classifier/manifest.json")
DEFAULT_V1262 = Path("tmp/wifi/v1262-gpiochip-line-info-live/manifest.json")
DEFAULT_V1243 = Path("tmp/wifi/v1243-sdx50m-power-prereq-response-live/manifest.json")
DEFAULT_V1239 = Path("tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json")


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
    parser.add_argument("--v1263", type=Path, default=DEFAULT_V1263)
    parser.add_argument("--v1262", type=Path, default=DEFAULT_V1262)
    parser.add_argument("--v1243", type=Path, default=DEFAULT_V1243)
    parser.add_argument("--v1239", type=Path, default=DEFAULT_V1239)
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
        return {"_exists": True, "_path": str(path), "_json_error": "top-level JSON is not an object"}
    data["_exists"] = True
    data["_path"] = str(path)
    return data


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "pass"}
    return bool(value)


def intish(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sampler_sample_lines(samples: list[dict[str, Any]]) -> dict[str, str]:
    if not samples:
        return {}
    first = samples[0]
    return {
        "first_phase": str(first.get("phase", "")),
        "pin135_line": str(first.get("pin135_line", "")),
        "pin142_line": str(first.get("pin142_line", "")),
        "pmic_soft_reset_line": str(first.get("pmic_soft_reset_line", "")),
        "pcie1_gdsc_line": str(first.get("pcie1_gdsc_line", "")),
    }


def analyze(v1263: dict[str, Any], v1262: dict[str, Any], v1243: dict[str, Any], v1239: dict[str, Any]) -> dict[str, Any]:
    v1263_analysis = v1263.get("analysis") if isinstance(v1263.get("analysis"), dict) else {}
    v1262_analysis = v1262.get("analysis") if isinstance(v1262.get("analysis"), dict) else {}
    sampler = v1243.get("response_sampler") if isinstance(v1243.get("response_sampler"), dict) else {}
    pm_observer = v1243.get("pm_service_trigger_observer") if isinstance(v1243.get("pm_service_trigger_observer"), dict) else {}
    samples = sampler.get("samples") if isinstance(sampler.get("samples"), list) else []

    v1263_rejects_line_request = (
        v1263.get("decision") == "v1263-kernel-owned-soft-reset-line-request-rejected"
        and as_bool(v1263.get("pass"))
        and as_bool(v1263_analysis.get("direct_line_request_rejected"))
    )
    v1262_line_kernel_owned = (
        v1262.get("decision") == "v1262-gpiochip-line-info-pass"
        and as_bool(v1262.get("pass"))
        and str(v1262_analysis.get("line_flag_kernel")) == "1"
        and str(v1262_analysis.get("line_consumer")) == "AP2MDM_SOFT_RESET"
    )
    v1243_has_response_window = (
        v1243.get("decision") == "v1243-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required"
        and as_bool(v1243.get("pass"))
        and as_bool(pm_observer.get("pm_service_actor_esoc0_attempt"))
        and as_bool(sampler.get("emitted"))
        and intish(sampler.get("sample_count"), 0) > 0
    )
    v1243_no_downstream_response = (
        intish(sampler.get("max_mdm_status_count_total"), -1) == 0
        and intish(sampler.get("max_mhi_bus_count"), -1) == 0
        and intish(sampler.get("max_pci_dev_count"), -1) == 0
        and not as_bool(sampler.get("mhi_pipe_seen"))
        and not as_bool(sampler.get("wlan0_seen"))
    )
    v1243_has_surface_inputs = (
        as_bool(sampler.get("debugfs_pinctrl_seen"))
        and as_bool(sampler.get("debugfs_regulator_seen"))
        and as_bool(sampler.get("pmic_soft_reset_seen"))
        and as_bool(sampler.get("pcie1_gdsc_seen"))
    )
    v1239_gap_fixed = (
        v1239.get("decision") == "v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw"
        and as_bool(v1239.get("pass"))
    )

    current_helper_gap = (
        "v1243 samples PMIC soft-reset pinctrl text, but not gpiochip line-info flags "
        "during the same PM-service /dev/subsys_esoc0 response window"
    )
    selected_next_gate = (
        "V1265 source/build-only helper v264: extend the late per_proxy response sampler "
        "with read-only PMIC GPIO9 GPIO_GET_LINEINFO_IOCTL snapshots before/during/after "
        "the PM-service esoc0 window"
    )

    return {
        "v1263_path": v1263.get("_path", ""),
        "v1262_path": v1262.get("_path", ""),
        "v1243_path": v1243.get("_path", ""),
        "v1239_path": v1239.get("_path", ""),
        "v1263_decision": v1263.get("decision", "missing"),
        "v1262_decision": v1262.get("decision", "missing"),
        "v1243_decision": v1243.get("decision", "missing"),
        "v1239_decision": v1239.get("decision", "missing"),
        "v1263_rejects_line_request": v1263_rejects_line_request,
        "v1262_line_kernel_owned": v1262_line_kernel_owned,
        "v1262_line_flags": v1262_analysis.get("line_flags", ""),
        "v1262_line_flag_kernel": v1262_analysis.get("line_flag_kernel", ""),
        "v1262_line_consumer": v1262_analysis.get("line_consumer", ""),
        "v1243_has_response_window": v1243_has_response_window,
        "v1243_no_downstream_response": v1243_no_downstream_response,
        "v1243_has_surface_inputs": v1243_has_surface_inputs,
        "v1243_sample_count": intish(sampler.get("sample_count"), 0),
        "v1243_max_gpio142_count": intish(sampler.get("max_mdm_status_count_total"), -1),
        "v1243_max_pci_dev_count": intish(sampler.get("max_pci_dev_count"), -1),
        "v1243_max_mhi_bus_count": intish(sampler.get("max_mhi_bus_count"), -1),
        "v1243_mhi_pipe_seen": as_bool(sampler.get("mhi_pipe_seen")),
        "v1243_wlan0_seen": as_bool(sampler.get("wlan0_seen")),
        "v1243_debugfs_pinctrl_seen": as_bool(sampler.get("debugfs_pinctrl_seen")),
        "v1243_debugfs_regulator_seen": as_bool(sampler.get("debugfs_regulator_seen")),
        "v1243_pmic_soft_reset_seen": as_bool(sampler.get("pmic_soft_reset_seen")),
        "v1243_sample_lines": sampler_sample_lines(samples),
        "v1239_gap_after_esoc0_before_response": v1239_gap_fixed,
        "current_helper_gap": current_helper_gap,
        "selected_next_gate": selected_next_gate,
        "observer_contract": {
            "must_sample": [
                "PMIC GPIO9 line-info flags/name/consumer via GPIO_GET_LINEINFO_IOCTL",
                "GPIO142 interrupt count and mdm3 state",
                "PCIe RC1 readonly link/runtime surface",
                "MHI bus count and /dev/mhi_0305_01.01.00_pipe_10 existence",
                "pm-service /dev/subsys_esoc0 attempt and mdm_subsys_powerup timing evidence",
            ],
            "must_not_execute": [
                "GPIO line request or hold",
                "PMIC write or debugfs control write",
                "direct eSoC ioctl such as ESOC_NOTIFY or ESOC_BOOT_DONE",
                "new daemon/HAL start beyond the existing bounded PM-service response path",
                "Wi-Fi scan/connect, credentials, DHCP/routes, external ping",
                "flash, boot image write, partition write",
            ],
        },
    }


def build_checks(command: str, analysis: dict[str, Any], manifests: dict[str, dict[str, Any]]) -> list[Check]:
    if command == "plan":
        return [Check("plan-only", "pass", "info", "no evidence mutation or live command", "run V1264 classifier")]
    return [
        Check(
            "v1263-input",
            "pass" if manifests["v1263"].get("_exists") and analysis["v1263_rejects_line_request"] else "blocked",
            "blocker",
            f"decision={analysis['v1263_decision']} reject_line_request={analysis['v1263_rejects_line_request']}",
            "rerun V1263 before selecting the next observer",
        ),
        Check(
            "kernel-owned-line",
            "pass" if manifests["v1262"].get("_exists") and analysis["v1262_line_kernel_owned"] else "blocked",
            "blocker",
            f"flags={analysis['v1262_line_flags']} kernel={analysis['v1262_line_flag_kernel']} consumer={analysis['v1262_line_consumer']}",
            "do not plan any line request until line ownership is proven",
        ),
        Check(
            "pm-esoc0-window",
            "pass" if manifests["v1243"].get("_exists") and analysis["v1243_has_response_window"] else "blocked",
            "blocker",
            f"decision={analysis['v1243_decision']} samples={analysis['v1243_sample_count']}",
            "restore late per_proxy response sampler evidence",
        ),
        Check(
            "downstream-still-missing",
            "pass" if analysis["v1243_no_downstream_response"] else "warn",
            "warning",
            f"gpio142={analysis['v1243_max_gpio142_count']} pci={analysis['v1243_max_pci_dev_count']} mhi={analysis['v1243_max_mhi_bus_count']} wlan0={analysis['v1243_wlan0_seen']}",
            "if downstream response exists, classify that progress instead of building a new observer",
        ),
        Check(
            "surface-inputs-visible",
            "pass" if analysis["v1243_has_surface_inputs"] else "blocked",
            "blocker",
            f"pinctrl={analysis['v1243_debugfs_pinctrl_seen']} regulator={analysis['v1243_debugfs_regulator_seen']} pmic_soft_reset={analysis['v1243_pmic_soft_reset_seen']}",
            "restore read-only debugfs mount/cleanup observer before extending it",
        ),
        Check(
            "gap-location",
            "pass" if manifests["v1239"].get("_exists") and analysis["v1239_gap_after_esoc0_before_response"] else "blocked",
            "blocker",
            f"decision={analysis['v1239_decision']}",
            "refresh V1239 if the blocker location changed",
        ),
    ]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v1264-ext-mdm-ap2mdm-observer-plan-ready",
            True,
            "plan-only; no live command, PM actor, GPIO request, PMIC write, eSoC ioctl, or Wi-Fi action executed",
            "run V1264 host-only classifier",
        )
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return (
            "v1264-ext-mdm-ap2mdm-observer-plan-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh missing evidence before source/build work",
        )
    return (
        "v1264-ext-mdm-ap2mdm-observer-plan-pass",
        True,
        analysis["current_helper_gap"],
        analysis["selected_next_gate"],
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [
        ["decision", manifest["decision"]],
        ["pass", manifest["pass"]],
        ["line_flags", analysis["v1262_line_flags"]],
        ["line_flag_kernel", analysis["v1262_line_flag_kernel"]],
        ["line_consumer", analysis["v1262_line_consumer"]],
        ["response_samples", analysis["v1243_sample_count"]],
        ["max_gpio142_count", analysis["v1243_max_gpio142_count"]],
        ["max_pci_dev_count", analysis["v1243_max_pci_dev_count"]],
        ["max_mhi_bus_count", analysis["v1243_max_mhi_bus_count"]],
        ["mhi_pipe_seen", analysis["v1243_mhi_pipe_seen"]],
        ["wlan0_seen", analysis["v1243_wlan0_seen"]],
        ["current_helper_gap", analysis["current_helper_gap"]],
        ["selected_next_gate", analysis["selected_next_gate"]],
    ]
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    contract = analysis["observer_contract"]
    return "\n".join([
        "# V1264 ext-mdm/AP2MDM Observer Plan",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Required Observer Contract",
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
        f"- V1263: `{analysis['v1263_path']}`",
        f"- V1262: `{analysis['v1262_path']}`",
        f"- V1243: `{analysis['v1243_path']}`",
        f"- V1239: `{analysis['v1239_path']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    store = EvidenceStore(repo_path(args.out_dir))
    manifests = {
        "v1263": load_json(args.v1263),
        "v1262": load_json(args.v1262),
        "v1243": load_json(args.v1243),
        "v1239": load_json(args.v1239),
    }
    analysis = analyze(manifests["v1263"], manifests["v1262"], manifests["v1243"], manifests["v1239"])
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
        "pm_actor_executed": False,
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
