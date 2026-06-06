#!/usr/bin/env python3
"""V1369 host-only pcie1 enumerate-vs-shim decision."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1369-pcie1-enumerate-decision")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1369_PCIE1_ENUMERATE_DECISION_2026-06-01.md")
PCI_MSM_SOURCE = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c")

INPUTS = {
    "pci_msm_source": PCI_MSM_SOURCE,
    "v1368_manifest": Path("tmp/wifi/v1368-pci-msm-corrected-rc1-status-live/manifest.json"),
    "v1366_manifest": Path("tmp/wifi/v1366-pci-msm-case-path-classifier/manifest.json"),
    "v1362_report": Path("docs/reports/NATIVE_INIT_V1362_PCI_MSM_MUTATION_RISK_CLASSIFIER_2026-06-01.md"),
    "v1354_report": Path("docs/reports/NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def line_no(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return index
    return None


def classify() -> dict[str, Any]:
    missing = [str(path) for path in INPUTS.values() if not repo_path(path).exists()]
    if missing:
        return {
            "cycle": "V1369",
            "type": "host-only decision",
            "generated_at": now_iso(),
            "decision": "v1369-inputs-missing",
            "pass": False,
            "reason": "required prior evidence is missing",
            "next_step": "restore inputs before choosing an enumerate path",
            "missing": missing,
        }

    source = read_text(INPUTS["pci_msm_source"])
    v1368 = read_json(INPUTS["v1368_manifest"])
    v1366 = read_json(INPUTS["v1366_manifest"])
    v1362_report = read_text(INPUTS["v1362_report"])
    v1354_report = read_text(INPUTS["v1354_report"])
    checks = {
        "v1368_status_path_clean": v1368.get("decision") == "v1368-corrected-rc1-status-proof-clean",
        "v1368_rc1_values_observed": (v1368.get("analysis") or {}).get("rc1_status_seen") is True,
        "v1366_correct_selector_bitmask": (v1366.get("facts") or {}).get("pcie1_correct_rc_sel_bitmask") == 2,
        "case11_calls_msm_pcie_enumerate": "msm_pcie_enumerate(dev->rc_idx)" in source,
        "enumerate_calls_msm_pcie_enable_pm_all": "ret = msm_pcie_enable(dev, PM_ALL);" in source,
        "enumerate_scans_root_bus": "pci_scan_root_bus_bridge(bridge)" in source
        and "pci_bus_add_devices(bus)" in source,
        "broad_bind_rescan_rejected": "v1362-no-safe-userspace-pci-msm-mutation" in v1362_report,
        "current_route_keeps_pcie1_off": "v1354-current-route-pcie1-rc-stayed-off" in v1354_report,
    }
    pass_condition = all(checks.values())
    selected_path = "corrected-debugfs-case11-enumerate" if pass_condition else "no-selection"
    decision = (
        "v1369-select-corrected-debugfs-rc1-enumerate-design"
        if pass_condition
        else "v1369-enumerate-decision-incomplete"
    )
    reason = (
        "The corrected pci-msm debugfs path is now narrower than a new kernel shim: "
        "V1368 proved rc_sel=2 reaches RC1 safely for status, and source shows case=11 "
        "calls msm_pcie_enumerate(dev->rc_idx), which performs msm_pcie_enable(PM_ALL) "
        "then PCI root-bus scan/add. A bounded rc_sel=2 case=11 enumerate proof is the "
        "next direct blocker test; it must still exclude Wi-Fi HAL/scan/connect and treat "
        "transport loss or unexpected health/link side effects as failure."
        if pass_condition
        else "one or more enumerate decision assumptions are not proven"
    )
    next_step = (
        "V1370 bounded live corrected-RC1 enumerate proof: rc_sel=2 then case=11, no Wi-Fi HAL or network bring-up"
        if pass_condition
        else "repair V1369 inputs before selecting any live enumerate path"
    )
    return {
        "cycle": "V1369",
        "type": "host-only decision",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "selected_path": selected_path,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "checks": checks,
        "source_lines": {
            "debugfs_case_select": line_no(source, "static ssize_t msm_pcie_debugfs_case_select"),
            "case11": line_no(source, "case MSM_PCIE_ENUMERATION:"),
            "msm_pcie_enumerate": line_no(source, "int msm_pcie_enumerate(u32 rc_idx)"),
            "msm_pcie_enable_pm_all": line_no(source, "ret = msm_pcie_enable(dev, PM_ALL);"),
            "pci_scan_root_bus_bridge": line_no(source, "pci_scan_root_bus_bridge(bridge)"),
            "pci_bus_add_devices": line_no(source, "pci_bus_add_devices(bus)"),
        },
        "v1370_design": {
            "candidate_commands": [
                "mount debugfs only if not already mounted",
                "printf '2\\n' > /sys/kernel/debug/pci-msm/rc_sel",
                "printf '11\\n' > /sys/kernel/debug/pci-msm/case",
            ],
            "preflight": [
                "native version/status/selftest fail=0",
                "V1368-style rc_sel=2 case=26 status path already clean",
                "debugfs mount state captured",
                "PCI/MHI devices absent before enumerate",
                "pcie1 regulator/clock/gpio/dmesg snapshots captured before enumerate",
            ],
            "success_signals": [
                "command returns without transport loss",
                "dmesg includes RC1 enumerate attempt",
                "pcie1 GDSC/clock/PERST/link or PCI/MHI state changes are captured",
                "post selftest fail=0",
            ],
            "failure_signals": [
                "transport loss/reboot",
                "post selftest fail>0",
                "unexpected non-RC1 PCI changes",
                "debugfs cleanup failure",
            ],
            "hard_stops": [
                "do not start Wi-Fi HAL",
                "do not scan/connect/use credentials",
                "do not run DHCP/routes/external ping",
                "do not use PERST assert/deassert debug cases",
                "do not write PMIC/GPIO/GDSC directly",
                "do not write boot image or partitions",
            ],
        },
        "rejected_paths": [
            {
                "path": "new kernel shim before debugfs enumerate",
                "reason": "more invasive than an existing source-proven case=11 path after V1368 selector proof",
            },
            {
                "path": "platform bind/unbind or PCI rescan",
                "reason": "already rejected as broad/non-RC1-specific by V1362",
            },
            {
                "path": "Wi-Fi HAL or connect now",
                "reason": "pcie1 enumerate/WLFW/MHI prerequisite is not proven yet",
            },
        ],
        "hard_exclusions": [
            "host-only; no live command in V1369",
            "no V1370 execution in this classifier",
            "no PERST assert/deassert cases",
            "no MMIO write cases or boot_option write",
            "no platform bind/unbind or generic PCI rescan",
            "no PMIC/GPIO/GDSC direct write",
            "no eSoC notify or BOOT_DONE",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
    }


def check_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, bool_text(bool(value))] for key, value in sorted((manifest.get("checks") or {}).items())]


def source_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    return [[key, value] for key, value in (manifest.get("source_lines") or {}).items()]


def design_rows(manifest: dict[str, Any]) -> list[list[str]]:
    design = manifest.get("v1370_design") or {}
    return [[key, "<br>".join(value if isinstance(value, list) else [str(value)])] for key, value in design.items()]


def rejected_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[row["path"], row["reason"]] for row in manifest.get("rejected_paths") or []]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1369 pcie1 Enumerate Decision",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- selected_path: `{manifest.get('selected_path')}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)) if manifest.get("checks") else "",
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1369 pcie1 Enumerate Decision",
        "",
        "## Summary",
        "",
        "- Cycle: `V1369`",
        "- Type: host-only decision",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        f"- Selected Path: `{manifest.get('selected_path')}`",
        "- Script: `scripts/revalidation/native_wifi_pcie1_enumerate_decision_v1369.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1369-pcie1-enumerate-decision/manifest.json`",
        "  - `tmp/wifi/v1369-pcie1-enumerate-decision/summary.md`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)) if manifest.get("checks") else "inputs missing",
        "",
        "## Source Lines",
        "",
        markdown_table(["symbol", "line"], source_rows(manifest)) if manifest.get("source_lines") else "inputs missing",
        "",
        "## V1370 Design",
        "",
        markdown_table(["field", "value"], design_rows(manifest)) if manifest.get("v1370_design") else "inputs missing",
        "",
        "## Rejected Paths",
        "",
        markdown_table(["path", "reason"], rejected_rows(manifest)) if manifest.get("rejected_paths") else "none",
        "",
        "## Safety",
        "",
        "- V1369 is host-only and executes no device command.",
        "- The selected next proof still excludes Wi-Fi HAL, scan/connect,",
        "  credential handling, DHCP/routes, external ping, PERST assert/deassert,",
        "  PMIC/GPIO/GDSC direct writes, eSoC notify/`BOOT_DONE`, flash, boot image",
        "  write, and partition write.",
        "",
        "## Next",
        "",
        manifest["next_step"],
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = classify()
    out_dir = repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_summary(manifest))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(out_dir)}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
