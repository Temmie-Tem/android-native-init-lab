#!/usr/bin/env python3
"""V1367 host-only corrected-RC1 pci-msm action design."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1367-pci-msm-corrected-rc1-design")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1367_PCI_MSM_CORRECTED_RC1_DESIGN_2026-06-01.md")

INPUTS = {
    "v1366_manifest": Path("tmp/wifi/v1366-pci-msm-case-path-classifier/manifest.json"),
    "v1365_manifest": Path("tmp/wifi/v1365-pci-msm-status-case-live/manifest.json"),
    "v1354_report": Path("docs/reports/NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md"),
    "v1355_report": Path("docs/reports/NATIVE_INIT_V1355_PMIC_GPIO9_PON_PARITY_CLASSIFIER_2026-06-01.md"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def classify() -> dict[str, Any]:
    missing = [str(path) for path in INPUTS.values() if not repo_path(path).exists()]
    if missing:
        return {
            "cycle": "V1367",
            "type": "host-only design",
            "generated_at": now_iso(),
            "decision": "v1367-inputs-missing",
            "pass": False,
            "reason": "required prior evidence is missing",
            "next_step": "restore inputs before choosing a live pcie1 action",
            "missing": missing,
        }

    v1366 = read_json(INPUTS["v1366_manifest"])
    v1365 = read_json(INPUTS["v1365_manifest"])
    v1354_report = read_text(INPUTS["v1354_report"])
    v1355_report = read_text(INPUTS["v1355_report"])
    checks = {
        "v1366_corrected_rc_selector": v1366.get("decision") == "v1366-pci-msm-case-path-corrected-rc-selector-no-live-write"
        and (v1366.get("facts") or {}).get("pcie1_correct_rc_sel_bitmask") == 2,
        "v1365_transport_loss_known": v1365.get("decision") == "v1365-case26-transport-reset-reboot-risk",
        "case26_source_read_only": bool((v1366.get("checks") or {}).get("case26_has_no_direct_mutating_call")),
        "case11_source_enumerates": bool((v1366.get("checks") or {}).get("case11_calls_msm_pcie_enumerate")),
        "pcie1_current_route_stayed_off": "v1354-current-route-pcie1-rc-stayed-off" in v1354_report,
        "pon_parity_closed": "v1355-pon-parity-closed-pcie1-rc-next" in v1355_report,
    }
    pass_condition = all(checks.values())
    selected_path = "corrected-rc1-status-read" if pass_condition else "no-selection"
    decision = (
        "v1367-corrected-rc1-status-read-design-ready"
        if pass_condition
        else "v1367-corrected-rc1-design-incomplete"
    )
    reason = (
        "V1366 proves the previous live write targeted RC0 and that pcie1 requires "
        "rc_sel=2; it also proves case=26 is source-intended as a PERST/WAKE "
        "GPIO readout while case=11 is enumerate. The next live action can be "
        "a single corrected RC1 status-read proof only if it is treated as "
        "reboot-risky and bounded; enumerate, PERST toggle, PCI rescan, and "
        "Wi-Fi bring-up remain excluded."
        if pass_condition
        else "one or more corrected-RC1 design assumptions are not proven"
    )
    next_step = (
        "V1368 bounded live corrected-RC1 status-read proof: rc_sel=2 then case=26, with reboot-risk handling and no enumerate"
        if pass_condition
        else "repair V1367 inputs before any live pci-msm action"
    )
    return {
        "cycle": "V1367",
        "type": "host-only design",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "checks": checks,
        "selected_path": selected_path,
        "rejected_paths": [
            {
                "path": "case=11 enumerate",
                "reason": "source calls msm_pcie_enumerate(dev->rc_idx); not a status proof",
            },
            {
                "path": "PERST assert/deassert debug cases",
                "reason": "source performs gpio_set_value; direct reset mutation",
            },
            {
                "path": "platform bind/unbind or PCI rescan",
                "reason": "broader than pcie1 and previously rejected by V1362",
            },
            {
                "path": "kernel-side shim now",
                "reason": "more invasive than one corrected source-read status proof; keep as fallback if V1368 fails",
            },
        ],
        "v1368_design": {
            "intent": "read pcie1/RC1 PERST and WAKE status through pci-msm debugfs only",
            "candidate_commands": [
                "mount debugfs only if not already mounted",
                "printf '2\\n' > /sys/kernel/debug/pci-msm/rc_sel",
                "printf '26\\n' > /sys/kernel/debug/pci-msm/case",
            ],
            "preflight": [
                "native version/status/selftest fail=0",
                "debugfs mount state captured",
                "/sys/kernel/debug/pci-msm/case lists 26 and 11",
                "pcie1 PCI/MHI devices absent before proof",
                "focused dmesg and gpio/regulator/clock snapshots captured before proof",
            ],
            "success_criteria": [
                "write returns without transport loss",
                "after-captures complete",
                "no PCI/MHI/link-up transition",
                "debugfs mount state restored",
                "post selftest fail=0",
            ],
            "failure_criteria": [
                "cmdv1 transport loss or reboot",
                "PCI/MHI/link state transition",
                "debugfs cleanup failure",
                "post selftest fail>0",
            ],
            "transport_loss_handling": [
                "classify as reboot-risk failure, not pass",
                "wait for bridge/device recovery before any further action",
                "run status/selftest after recovery and record as out-of-window recovery evidence",
            ],
        },
        "hard_exclusions": [
            "host-only design; no device command in V1367",
            "V1368 would still exclude case=11 enumerate",
            "no PERST assert/deassert cases",
            "no MMIO write cases or boot_option write",
            "no platform bind/unbind or PCI rescan",
            "no PMIC/GPIO/GDSC direct write",
            "no eSoC notify or BOOT_DONE",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
    }


def check_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[key, bool_text(bool(value))] for key, value in sorted((manifest.get("checks") or {}).items())]


def rejected_rows(manifest: dict[str, Any]) -> list[list[str]]:
    return [[row["path"], row["reason"]] for row in manifest.get("rejected_paths") or []]


def list_rows(values: list[str]) -> str:
    return "<br>".join(values)


def design_rows(manifest: dict[str, Any]) -> list[list[str]]:
    design = manifest.get("v1368_design") or {}
    return [
        ["intent", str(design.get("intent", ""))],
        ["candidate_commands", list_rows(design.get("candidate_commands") or [])],
        ["preflight", list_rows(design.get("preflight") or [])],
        ["success_criteria", list_rows(design.get("success_criteria") or [])],
        ["failure_criteria", list_rows(design.get("failure_criteria") or [])],
        ["transport_loss_handling", list_rows(design.get("transport_loss_handling") or [])],
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1367 Corrected-RC1 pci-msm Design",
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
        "# Native Init V1367 Corrected-RC1 pci-msm Design",
        "",
        "## Summary",
        "",
        "- Cycle: `V1367`",
        "- Type: host-only design",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        f"- Selected Path: `{manifest.get('selected_path')}`",
        "- Script: `scripts/revalidation/native_wifi_pci_msm_corrected_rc1_design_v1367.py`",
        "- Evidence:",
        "  - `tmp/wifi/v1367-pci-msm-corrected-rc1-design/manifest.json`",
        "  - `tmp/wifi/v1367-pci-msm-corrected-rc1-design/summary.md`",
        "",
        "## Decision",
        "",
        manifest["reason"],
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass"], check_rows(manifest)) if manifest.get("checks") else "inputs missing",
        "",
        "## V1368 Design",
        "",
        markdown_table(["field", "value"], design_rows(manifest)) if manifest.get("v1368_design") else "inputs missing",
        "",
        "## Rejected Paths",
        "",
        markdown_table(["path", "reason"], rejected_rows(manifest)) if manifest.get("rejected_paths") else "none",
        "",
        "## Safety",
        "",
        "- V1367 is host-only and executes no device command.",
        "- The selected next proof remains status-read only and keeps `case=11`",
        "  enumerate, PERST assert/deassert, MMIO write, boot option write,",
        "  platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC direct write, eSoC",
        "  notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential handling,",
        "  DHCP/routes, external ping, flash, boot image write, and partition",
        "  write excluded.",
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
