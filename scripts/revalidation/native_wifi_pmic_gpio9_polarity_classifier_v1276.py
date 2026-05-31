#!/usr/bin/env python3
"""V1276 host-only PMIC GPIO9 polarity/value classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v1276-pmic-gpio9-polarity-classifier")
DEFAULT_V1275 = Path("tmp/wifi/v1275-ap2mdm-block-sampler-live/manifest.json")
DEFAULT_V919_REPORT = Path("docs/reports/NATIVE_INIT_V919_SDX50M_SOFT_RESET_BLOCKER_CLASSIFIER_2026-05-26.md")
DEFAULT_V1239_REPORT = Path("docs/reports/NATIVE_INIT_V1239_POST_ESOC0_POWERUP_GAP_CLASSIFIER_2026-05-31.md")
DEFAULT_V968_REPORT = Path("docs/reports/NATIVE_INIT_V968_ANDROID_DMESG_ESOC_GPIO_TIMING_2026-05-26.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1276-pmic-gpio9-polarity-classifier.txt")


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
    parser.add_argument("--v1275", type=Path, default=DEFAULT_V1275)
    parser.add_argument("--v919-report", type=Path, default=DEFAULT_V919_REPORT)
    parser.add_argument("--v1239-report", type=Path, default=DEFAULT_V1239_REPORT)
    parser.add_argument("--v968-report", type=Path, default=DEFAULT_V968_REPORT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        return {"_exists": False, "_path": str(path)}
    data = json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"_exists": True, "_path": str(path), "_json_error": "not an object"}
    data["_exists"] = True
    data["_path"] = str(path)
    return data


def load_text(path: Path) -> str:
    full = repo_path(path)
    if not full.exists():
        return ""
    return full.read_text(encoding="utf-8", errors="replace")


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "pass"}
    return bool(value)


def first_sample_value(samples: list[dict[str, Any]], field: str) -> str:
    for sample in samples:
        value = str(sample.get(field, ""))
        if value:
            return value
    return ""


def line_has_pmic_gpio9_out_high(line: str) -> bool:
    return "gpio9" in line and "out" in line and "high" in line


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1275 = load_json(args.v1275)
    sampler = v1275.get("response_sampler") if isinstance(v1275.get("response_sampler"), dict) else {}
    samples = sampler.get("samples") if isinstance(sampler.get("samples"), list) else []
    pmic_block = first_sample_value(samples, "pmic_gpio1270_debugfs_block")
    v919_text = load_text(args.v919_report)
    v1239_text = load_text(args.v1239_report)
    v968_text = load_text(args.v968_report)

    v1275_ready = (
        v1275.get("decision") == "v1275-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required"
        and as_bool(v1275.get("pass"))
        and sampler.get("sample_count") == 14
        and as_bool(sampler.get("pmic_gpio1270_debugfs_block_seen"))
        and as_bool(sampler.get("gpiochip_lineinfo_ap2mdm_consumer_seen"))
        and not as_bool(sampler.get("wlan0_seen"))
    )
    native_pmic_out_high = line_has_pmic_gpio9_out_high(pmic_block)
    android_pmic_out_high = "pmic_gpio9_snapshot" in v919_text and line_has_pmic_gpio9_out_high(v919_text)
    pmic_matches_android = native_pmic_out_high and android_pmic_out_high
    downstream_absent = (
        sampler.get("max_mdm_status_count_total") == 0
        and sampler.get("max_pci_dev_count") == 0
        and sampler.get("max_mhi_bus_count") == 0
        and not as_bool(sampler.get("mhi_pipe_seen"))
        and not as_bool(sampler.get("wlan0_seen"))
    )
    android_downstream_positive = (
        "GPIO142 IRQ `1`" in v1239_text
        and "PCIe RC1" in v1239_text
        and "sysmon esoc0" in v1239_text
    )
    android_tlmm_readable = (
        "GPIO135 and GPIO142 readable" in v968_text
        or "GPIO135/GPIO142" in v968_text
    )
    native_tlmm_block_absent = (
        not as_bool(sampler.get("tlmm_gpio135_debugfs_block_seen"))
        and not as_bool(sampler.get("tlmm_gpio142_debugfs_block_seen"))
    )

    return {
        "v1275_path": str(args.v1275),
        "v919_report": str(args.v919_report),
        "v1239_report": str(args.v1239_report),
        "v968_report": str(args.v968_report),
        "v1275_ready": v1275_ready,
        "sample_count": sampler.get("sample_count"),
        "native_pmic_gpio9_out_high": native_pmic_out_high,
        "android_pmic_gpio9_out_high": android_pmic_out_high,
        "pmic_gpio9_matches_android_reference": pmic_matches_android,
        "pmic_gpio9_block_excerpt": pmic_block[:900],
        "downstream_absent": downstream_absent,
        "android_downstream_positive": android_downstream_positive,
        "android_tlmm_readable": android_tlmm_readable,
        "native_tlmm_block_absent": native_tlmm_block_absent,
        "max_mdm_status_count_total": sampler.get("max_mdm_status_count_total"),
        "max_pci_dev_count": sampler.get("max_pci_dev_count"),
        "max_mhi_bus_count": sampler.get("max_mhi_bus_count"),
        "pcie1_gdsc_seen": sampler.get("pcie1_gdsc_seen"),
        "pcie0_gdsc_seen": sampler.get("pcie0_gdsc_seen"),
        "selected_next_gate": (
            "V1277 source/build-only helper v267: add read-only TLMM GPIO range-slice "
            "capture around GPIO135/GPIO142 plus AP2MDM/MDM2AP pinmux/pinconf and PCIe RC1/GDSC snapshots"
        ),
        "rejected_next_steps": [
            "PMIC GPIO9 write or hold",
            "userspace GPIO line request",
            "direct eSoC ioctl retry",
            "service-manager/HAL/scan/connect expansion",
            "DHCP/routes/external ping",
            "flash or boot image write",
        ],
    }


def checks(command: str, analysis: dict[str, Any]) -> list[Check]:
    if command == "plan":
        return [Check("plan-only", "pass", "info", "no evidence mutation or live command", "run V1276 classifier")]
    return [
        Check("v1275-input", "pass" if analysis["v1275_ready"] else "blocked", "blocker", f"samples={analysis['sample_count']}", "rerun V1275 if missing"),
        Check("pmic-native-value", "pass" if analysis["native_pmic_gpio9_out_high"] else "blocked", "blocker", "native PMIC GPIO9 debugfs line contains out/high", "refresh PMIC GPIO block capture"),
        Check("pmic-android-reference", "pass" if analysis["android_pmic_gpio9_out_high"] else "blocked", "blocker", "V919 Android/reference report contains out/high", "refresh Android PMIC reference"),
        Check("pmic-match", "pass" if analysis["pmic_gpio9_matches_android_reference"] else "blocked", "blocker", "native PMIC GPIO9 state matches Android reference", "do not demote PMIC until states match"),
        Check("downstream-still-absent", "pass" if analysis["downstream_absent"] else "warn", "warning", f"gpio142={analysis['max_mdm_status_count_total']} pci={analysis['max_pci_dev_count']} mhi={analysis['max_mhi_bus_count']}", "if response exists, classify progress"),
        Check("android-positive-contrast", "pass" if analysis["android_downstream_positive"] else "warn", "warning", "Android contrast has GPIO142/PCIe/sysmon positive markers", "refresh Android contrast if stale"),
        Check("tlmm-gap", "pass" if analysis["native_tlmm_block_absent"] and analysis["android_tlmm_readable"] else "warn", "warning", f"native_absent={analysis['native_tlmm_block_absent']} android_readable={analysis['android_tlmm_readable']}", "capture TLMM range slices before writes"),
    ]


def decide(command: str, check_rows: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return ("v1276-pmic-gpio9-polarity-plan-ready", True, "plan-only", "run V1276 classifier")
    blockers = [row.name for row in check_rows if row.severity == "blocker" and row.status != "pass"]
    if blockers:
        return ("v1276-pmic-gpio9-polarity-blocked", False, "blocked by " + ", ".join(blockers), "refresh missing references")
    return (
        "v1276-pmic-gpio9-matches-android-tlmm-gate-selected",
        True,
        "PMIC GPIO9 now matches Android out/high reference; remaining blocker is downstream TLMM/PCIe/SDX50M response",
        analysis["selected_next_gate"],
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [
        ["decision", manifest["decision"]],
        ["pass", manifest["pass"]],
        ["native_pmic_gpio9_out_high", analysis["native_pmic_gpio9_out_high"]],
        ["android_pmic_gpio9_out_high", analysis["android_pmic_gpio9_out_high"]],
        ["pmic_gpio9_matches_android_reference", analysis["pmic_gpio9_matches_android_reference"]],
        ["downstream_absent", analysis["downstream_absent"]],
        ["android_downstream_positive", analysis["android_downstream_positive"]],
        ["native_tlmm_block_absent", analysis["native_tlmm_block_absent"]],
        ["android_tlmm_readable", analysis["android_tlmm_readable"]],
        ["selected_next_gate", analysis["selected_next_gate"]],
    ]
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    return "\n".join([
        "# V1276 PMIC GPIO9 Polarity Classifier",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Rejected Next Steps",
        "",
        *[f"- {item}" for item in analysis["rejected_next_steps"]],
        "",
        "## Evidence",
        "",
        f"- V1275: `{analysis['v1275_path']}`",
        f"- V919 report: `{analysis['v919_report']}`",
        f"- V1239 report: `{analysis['v1239_report']}`",
        f"- V968 report: `{analysis['v968_report']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = analyze(args)
    check_rows = checks(args.command, analysis)
    decision, pass_ok, reason, next_step = decide(args.command, check_rows, analysis)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "device_commands_executed": False,
        "live_command_executed": False,
        "gpio_line_request_executed": False,
        "pmic_write_executed": False,
        "esoc_ioctl_executed": False,
        "wifi_bringup_executed": False,
        "analysis": analysis,
        "checks": [asdict(row) for row in check_rows],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    LATEST_POINTER.write_text(str(store.run_dir / "manifest.json") + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"pmic_write_executed: {manifest['pmic_write_executed']}")
    print(f"esoc_ioctl_executed: {manifest['esoc_ioctl_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {repo_path(args.out_dir)}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
