#!/usr/bin/env python3
"""V1553 host-only classifier for the post-PERST endpoint silence blocker.

V1552 proves the native RC1 attempt turns on the AP-side pcie1 power/refclk/
pipe/PERST sequence, then fails before L0 with no WAKE/status/errfatal IRQ.
This classifier reconciles that result with the prior PM/eSoC, sysfs enumerate,
and Android-good evidence to choose the next useful gate without another blind
native enumerate retry.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1553-endpoint-silence-next-gate-classifier")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1553_ENDPOINT_SILENCE_NEXT_GATE_CLASSIFIER_2026-06-02.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1553-endpoint-silence-next-gate-classifier.txt")

INPUTS = {
    "v1552": Path("tmp/wifi/v1552-rc1-endpoint-response-tracefs-live/manifest.json"),
    "v1551": Path("tmp/wifi/v1551-pcie1-tracefs-enumerate-live/manifest.json"),
    "v1496": Path("tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/manifest.json"),
    "v1530": Path("tmp/wifi/v1530-android-tracefs-native-no-l0-classifier/manifest.json"),
    "v1534_report": Path("docs/reports/NATIVE_INIT_V1534_PM_ROUTE_FIRST_L0_FOCUS_CLASSIFIER_2026-06-02.md"),
    "v1540_report": Path("docs/reports/NATIVE_INIT_V1540_ENDPOINT_READINESS_CLASSIFIER_2026-06-02.md"),
    "pci_msm": Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c"),
    "mhi_arch": Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c"),
    "mhi_qcom": Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_qcom.c"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def line_hits(path: Path, patterns: list[str], context: int = 0) -> list[dict[str, Any]]:
    text = read_text(path)
    lines = text.splitlines()
    hits: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        if any(re.search(pattern, line) for pattern in patterns):
            begin = max(1, index - context)
            end = min(len(lines), index + context)
            hits.append(
                {
                    "path": rel(path),
                    "line": index,
                    "text": line.strip(),
                    "context": [
                        {"line": n, "text": lines[n - 1].strip()}
                        for n in range(begin, end + 1)
                    ],
                }
            )
    return hits


def truth(value: Any) -> bool:
    return bool(value)


def classify() -> dict[str, Any]:
    v1552 = load_json(INPUTS["v1552"])
    v1551 = load_json(INPUTS["v1551"])
    v1496 = load_json(INPUTS["v1496"])
    v1530 = load_json(INPUTS["v1530"])
    v1534_text = read_text(INPUTS["v1534_report"])
    v1540_text = read_text(INPUTS["v1540_report"])

    v1552_analysis = v1552["analysis"]
    v1552_target = v1552_analysis["target_counts"]
    v1496_progress = v1496.get("wifi_progress", {})
    v1530_analysis = v1530.get("analysis", {})
    v1530_checks = v1530_analysis.get("checks", {})
    v1530_classification = v1530_analysis.get("classification", {})

    source_hits = {
        "pcie_enable": line_hits(
            INPUTS["pci_msm"],
            [
                r"static int msm_pcie_enable",
                r"Assert the reset of endpoint",
                r"msm_pcie_vreg_init",
                r"msm_pcie_clk_init",
                r"msm_pcie_pipe_clk_init",
                r"Release the reset of endpoint",
                r"PCIE20_PARF_LTSSM",
                r"link initialization failed",
                r"is_esoc0_online",
            ],
        )[:24],
        "mhi_position": line_hits(
            INPUTS["mhi_arch"],
            [
                r"mhi_arch_esoc_ops_power_on",
                r"mhi_dev->pci_dev",
                r"MSM_PCIE_RESUME",
                r"mhi_pci_probe",
                r"esoc_link_power_on",
            ],
        )[:24],
        "mhi_probe": line_hits(
            INPUTS["mhi_qcom"],
            [
                r"int mhi_pci_probe",
                r"PCI_DEVICE\\(MHI_PCIE_VENDOR_ID, 0x0305\\)",
                r"mhi_qcom_power_up",
            ],
        )[:16],
    }

    checks = {
        "v1552_pass": truth(v1552.get("pass")),
        "v1552_ap_side_power_refclk_perst": (
            v1552_target.get("pcie1_gdsc_enable", 0) > 0
            and v1552_target.get("refclk_enable", 0) > 0
            and v1552_target.get("pipe_clk_enable", 0) > 0
            and v1552_target.get("gpio102_set1", 0) > 0
        ),
        "v1552_endpoint_irq_silent": (
            v1552_target.get("irq_pcie_wake", 0) == 0
            and v1552_target.get("irq_mdm_status", 0) == 0
            and v1552_target.get("irq_mdm_errfatal", 0) == 0
            and all(value == 0 for value in v1552_analysis.get("interrupt_delta", {}).values())
        ),
        "v1552_no_l0": not v1552_analysis.get("l0_seen"),
        "v1552_no_mhi_wlfw_wlan0": (
            not v1552_analysis.get("mhi_seen")
            and not v1552_analysis.get("wlfw_or_wlan_seen")
        ),
        "v1551_gdsc_timing_gap_closed": v1551.get("decision") == "v1551-pcie1-gdsc-enable-captured-no-l0",
        "v1496_provider_plus_rc1_already_no_l0": (
            bool(v1496_progress.get("provider_trigger"))
            and bool(v1496_progress.get("rc1_progress"))
            and not bool(v1496_progress.get("rc1_l0"))
        ),
        "v1530_android_good_lower_reaches_wlan": bool(v1530_checks.get("android_good_lower_path_reached")),
        "v1530_rc1_text_opaque": bool(v1530_checks.get("android_rc1_text_still_absent")),
        "v1530_mhi_pm_resume_downstream": bool(v1530_checks.get("mhi_pm_resume_downstream")),
        "v1534_current_pm_route_reaches_powerup": "current_sdx50m_route_reaches_pm_esoc0 | True" in v1534_text
        or "current_route_reaches_powerup | True" in v1534_text,
        "v1540_endpoint_readiness_gap": "v1540-endpoint-readiness-gap-after-sysfs-enumerate" in v1540_text,
        "source_pcie_enable_order_visible": len(source_hits["pcie_enable"]) >= 8,
        "source_mhi_pm_resume_downstream_visible": (
            any("mhi_dev->pci_dev" in hit["text"] for hit in source_hits["mhi_position"])
            and any("mhi_pci_probe" in hit["text"] for hit in source_hits["mhi_position"])
        ),
    }

    pass_all = all(checks.values())
    decision = (
        "v1553-next-gate-android-good-power-trace-reference"
        if pass_all
        else "v1553-endpoint-silence-next-gate-needs-review"
    )
    reason = (
        "native AP-side RC1 power/refclk/PERST is proven and endpoint IRQs stay silent; PM/eSoC and MHI leads are already classified, so the next useful gate is an Android-good regulator/clk/gpio/irq trace reference for the successful first-L0 window"
        if pass_all
        else "one or more fixed-point checks failed; review inputs before selecting the next live gate"
    )
    next_step = (
        "V1554 Android-good tracefs reference: capture regulator/clk/gpio/irq events around the first successful RC1 L0/WLFW window, then compare against V1552 native trace before any new native mutation"
        if pass_all
        else "repair classifier inputs or rerun missing evidence before live work"
    )

    return {
        "cycle": "V1553",
        "type": "host-only endpoint-silence next-gate classifier",
        "created_at": now_iso(),
        "host": collect_host_metadata(),
        "decision": decision,
        "pass": pass_all,
        "reason": reason,
        "next_step": next_step,
        "inputs": {key: rel(path) for key, path in INPUTS.items()},
        "checks": checks,
        "v1552_summary": {
            "decision": v1552.get("decision"),
            "target_counts": v1552_target,
            "interrupt_delta": v1552_analysis.get("interrupt_delta"),
            "link_failed": v1552_analysis.get("link_failed"),
            "l0_seen": v1552_analysis.get("l0_seen"),
            "mhi_seen": v1552_analysis.get("mhi_seen"),
            "wlfw_or_wlan_seen": v1552_analysis.get("wlfw_or_wlan_seen"),
        },
        "v1496_summary": {
            "provider_trigger": v1496_progress.get("provider_trigger"),
            "rc1_progress": v1496_progress.get("rc1_progress"),
            "rc1_l0": v1496_progress.get("rc1_l0"),
            "rc1_link_failed": v1496_progress.get("rc1_link_failed"),
            "mhi_progress": v1496_progress.get("mhi_progress"),
            "wlfw_progress": v1496_progress.get("wlfw_progress"),
            "wlan0_present": v1496_progress.get("wlan0_present"),
        },
        "v1530_classification": v1530_classification,
        "source_hits": source_hits,
        "not_next": [
            "another blind sysfs/debugfs enumerate retry",
            "MHI PM-resume as first-L0 trigger",
            "firmware/WLFW/BDF/scan/connect before native L0",
            "PM-service dependency repair as the primary blocker unless current route regresses",
            "PMIC/GPIO/GDSC direct writes or global PCI rescan",
        ],
        "recommended_v1554_gate": {
            "kind": "Android-good bounded tracefs reference",
            "events": [
                "regulator.regulator_enable/disable/set_voltage",
                "clk.clk_prepare/enable/disable",
                "gpio.gpio_value/direction",
                "irq.irq_handler_entry/exit",
                "printk.console if volume is bounded",
            ],
            "window": "from pm-service/modem or first lower-Wi-Fi marker through WLFW/BDF/wlan0, with rollback to native",
            "compare_against": [
                "V1552 native pcie_1_gdsc/refclk/pipe/PERST timestamps",
                "WAKE/status/errfatal IRQ deltas",
                "L0/MHI/WLFW/BDF/wlan0 markers",
            ],
        },
        "safety": {
            "host_only": True,
            "device_command_executed": False,
            "tracefs_write_executed": False,
            "sysfs_debugfs_write_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "flash_executed": False,
            "partition_write_executed": False,
        },
    }


def render_report(manifest: dict[str, Any]) -> str:
    checks = manifest["checks"]
    v1552 = manifest["v1552_summary"]
    v1496 = manifest["v1496_summary"]
    gate = manifest["recommended_v1554_gate"]
    source_rows: list[list[Any]] = []
    for group, hits in manifest["source_hits"].items():
        for hit in hits[:10]:
            source_rows.append([group, f"{hit['path']}:{hit['line']}", hit["text"]])

    return "\n".join(
        [
            "# Native Init V1553 Endpoint Silence Next Gate Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1553`",
            "- Type: host-only endpoint-silence next-gate classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{rel(Path(manifest['out_dir']) / 'manifest.json')}`",
            "",
            "V1553 reconciles V1552 with the prior PM/eSoC, sysfs-enumerate, Android-good, and MHI-position classifiers. It performs no device command or live mutation.",
            "",
            "## Checks",
            "",
            markdown_table(["check", "value"], [[key, value] for key, value in checks.items()]),
            "",
            "## Native Fixed Point",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["V1552 decision", v1552["decision"]],
                    ["V1552 target counts", json.dumps(v1552["target_counts"], sort_keys=True)],
                    ["V1552 interrupt delta", json.dumps(v1552["interrupt_delta"], sort_keys=True)],
                    ["V1552 link/L0/MHI/WLFW", f"{v1552['link_failed']} / {v1552['l0_seen']} / {v1552['mhi_seen']} / {v1552['wlfw_or_wlan_seen']}"],
                    ["V1496 provider/RC1/L0/linkfail", f"{v1496['provider_trigger']} / {v1496['rc1_progress']} / {v1496['rc1_l0']} / {v1496['rc1_link_failed']}"],
                ],
            ),
            "",
            "## Source Anchors",
            "",
            markdown_table(["group", "source", "line"], source_rows[:36]),
            "",
            "## Not Next",
            "",
            "\n".join(f"- {item}" for item in manifest["not_next"]),
            "",
            "## Recommended V1554 Gate",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["kind", gate["kind"]],
                    ["events", "<br>".join(gate["events"])],
                    ["window", gate["window"]],
                    ["compare against", "<br>".join(gate["compare_against"])],
                ],
            ),
            "",
            "## Safety",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in manifest["safety"].items()]),
            "",
            "## Next",
            "",
            manifest["next_step"],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = classify()
    manifest["out_dir"] = str(store.run_dir)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_report(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(args.report_path), render_report(manifest))
    print(json.dumps({"decision": manifest["decision"], "out_dir": str(store.run_dir), "pass": manifest["pass"]}, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
