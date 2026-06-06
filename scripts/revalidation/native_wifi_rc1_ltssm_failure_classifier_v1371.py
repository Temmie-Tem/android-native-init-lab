#!/usr/bin/env python3
"""V1371 host-only classifier for RC1 LTSSM no-L0 failure."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1371-rc1-ltssm-failure-classifier")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1371_RC1_LTSSM_FAILURE_CLASSIFIER_2026-06-01.md")
V1370_MANIFEST = Path("tmp/wifi/v1370-pci-msm-corrected-rc1-enumerate-live/manifest.json")
V1370_DMESG = Path("tmp/wifi/v1370-pci-msm-corrected-rc1-enumerate-live/native/after-dmesg-pcie-tail.txt")
V1370_GPIO = Path("tmp/wifi/v1370-pci-msm-corrected-rc1-enumerate-live/native/after-gpio-pcie.txt")
ANDROID_DMESG = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt"
)
PCI_MSM_SOURCE = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c")
PCIE_DTS = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'arch', 'arm64', 'boot', 'dts', 'qcom', 'sm8150-pcie.dtsi')
MHI_DTS = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'arch', 'arm64', 'boot', 'dts', 'qcom', 'sm8150-mhi.dtsi')
R3Q_OVERLAY = workspace_private_input_path(
    "kernel_source",
    "SM-A908N_KOR_12_Opensource",
    "Kernel",
    "arch",
    "arm64",
    "boot",
    "dts",
    "samsung",
    "renovation",
    "sm8150-sec-r3q-kor-overlay-r00.dts",
)
HOST_ANALYSIS = Path("docs/reports/ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md")

INPUTS = {
    "v1370_manifest": V1370_MANIFEST,
    "v1370_dmesg": V1370_DMESG,
    "v1370_gpio": V1370_GPIO,
    "android_dmesg": ANDROID_DMESG,
    "pci_msm_source": PCI_MSM_SOURCE,
    "pcie_dts": PCIE_DTS,
    "mhi_dts": MHI_DTS,
    "r3q_overlay": R3Q_OVERLAY,
    "host_analysis": HOST_ANALYSIS,
}

TIME_RE = re.compile(r"\[\s*(?P<time>\d+\.\d+)\]\s*(?P<line>.*)")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def line_no(text: str, needle: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return index
    return None


def event_rows(events: dict[str, Any]) -> list[list[Any]]:
    order = [
        "esoc0_get",
        "test11",
        "assert_reset",
        "int_mask",
        "phy_ready",
        "release_reset",
        "detect_quiet_first",
        "poll_active_first",
        "poll_compliance_first",
        "l0_first",
        "link_initialized",
        "current_gen",
        "link_failed",
    ]
    rows: list[list[Any]] = []
    for key in order:
        event = events.get(key)
        if not event:
            rows.append([key, "", ""])
            continue
        rows.append([key, event.get("time"), event.get("text")])
    return rows


def first_event(lines: list[dict[str, Any]], pattern: str, *, after: float | None = None) -> dict[str, Any] | None:
    regex = re.compile(pattern, re.I)
    for item in lines:
        if after is not None and item["time"] < after:
            continue
        if regex.search(item["text"]):
            return item
    return None


def parse_timed_lines(text: str) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for raw in text.splitlines():
        match = TIME_RE.search(raw)
        if not match:
            continue
        parsed.append({"time": float(match.group("time")), "text": match.group("line").strip(), "raw": raw})
    return parsed


def trim_native_window(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    starts = [item["time"] for item in lines if "PCIe: TEST: 11" in item["text"]]
    if not starts:
        return lines
    start = starts[-1]
    return [item for item in lines if item["time"] >= start]


def extract_events(text: str, *, native: bool) -> dict[str, Any]:
    lines = parse_timed_lines(text)
    if native:
        lines = trim_native_window(lines)
    events = {
        "esoc0_get": first_event(lines, r"__subsystem_get: esoc0 count:0"),
        "test11": first_event(lines, r"PCIe: TEST: 11"),
        "assert_reset": first_event(lines, r"PCIe: Assert the reset of endpoint of RC1"),
        "int_mask": first_event(lines, r"PCIE20_PARF_INT_ALL_MASK"),
        "phy_ready": first_event(lines, r"PCIe RC1 PHY is ready"),
        "release_reset": first_event(lines, r"PCIe: Release the reset of endpoint of RC1"),
        "detect_quiet_first": first_event(lines, r"PCIe RC1: LTSSM_STATE: LTSSM_DETECT_QUIET"),
        "poll_active_first": first_event(lines, r"PCIe RC1: LTSSM_STATE: LTSSM_POLL_ACTIVE"),
        "poll_compliance_first": first_event(lines, r"PCIe RC1: LTSSM_STATE: LTSSM_POLL_COMPLIANCE"),
        "l0_first": first_event(lines, r"PCIe RC1: LTSSM_STATE: LTSSM_L0"),
        "link_initialized": first_event(lines, r"PCIe RC1 link initialized"),
        "current_gen": first_event(lines, r"PCIe RC1 Current GEN"),
        "link_failed": first_event(lines, r"PCIe RC1 link initialization failed"),
    }
    return {key: value for key, value in events.items() if value is not None}


def delta(events: dict[str, Any], start: str, end: str) -> float | None:
    if start not in events or end not in events:
        return None
    return round(float(events[end]["time"]) - float(events[start]["time"]), 6)


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def check_rows(checks: dict[str, bool]) -> list[list[str]]:
    return [[key, bool_text(value)] for key, value in sorted(checks.items())]


def source_rows(source_lines: dict[str, int | None]) -> list[list[Any]]:
    return [[key, value] for key, value in source_lines.items()]


def dts_rows(facts: dict[str, Any]) -> list[list[Any]]:
    return [[key, value] for key, value in facts.items()]


def classify() -> dict[str, Any]:
    missing = [str(path) for path in INPUTS.values() if not repo_path(path).exists()]
    if missing:
        return {
            "cycle": "V1371",
            "type": "host-only RC1 LTSSM failure classifier",
            "generated_at": now_iso(),
            "decision": "v1371-inputs-missing",
            "pass": False,
            "reason": "required prior evidence is missing",
            "next_step": "restore V1371 inputs before selecting any next live gate",
            "missing": missing,
        }

    v1370_manifest = read_json(V1370_MANIFEST)
    native_dmesg = read_text(V1370_DMESG)
    native_gpio = read_text(V1370_GPIO)
    android_dmesg = read_text(ANDROID_DMESG)
    source = read_text(PCI_MSM_SOURCE)
    pcie_dts = read_text(PCIE_DTS)
    mhi_dts = read_text(MHI_DTS)
    overlay = read_text(R3Q_OVERLAY)
    host_analysis = read_text(HOST_ANALYSIS)

    native_events = extract_events(native_dmesg, native=True)
    android_events = extract_events(android_dmesg, native=False)
    v1370_analysis = v1370_manifest.get("analysis") or {}

    checks = {
        "v1370_passed": v1370_manifest.get("decision") == "v1370-corrected-rc1-link-training-no-l0-clean",
        "native_reached_rc1_enumerate": bool(v1370_analysis.get("rc1_enumerate_seen")),
        "native_reached_phy_ready": "phy_ready" in native_events,
        "native_released_perst": "release_reset" in native_events,
        "native_reached_poll_active_or_compliance": "poll_active_first" in native_events
        or "poll_compliance_first" in native_events,
        "native_failed_before_l0": "link_failed" in native_events and "l0_first" not in native_events,
        "native_created_no_pci_or_mhi": v1370_analysis.get("after_pci_count") == 0
        and v1370_analysis.get("after_mhi_present") is False,
        "native_device_health_clean": v1370_analysis.get("post_selftest_fail0") is True,
        "native_no_esoc_provider_held_in_v1370": "gpio135 : out 0" in native_gpio,
        "android_esoc0_precedes_rc1_enable": delta(android_events, "esoc0_get", "assert_reset") is not None
        and (delta(android_events, "esoc0_get", "assert_reset") or 0) > 0,
        "android_reached_l0": "l0_first" in android_events and "link_initialized" in android_events,
        "android_reached_current_gen": "current_gen" in android_events,
        "source_case11_is_enumerate": "msm_pcie_enumerate(dev->rc_idx)" in source,
        "source_enable_owns_pm_all": "ret = msm_pcie_vreg_init(dev);" in source
        and "ret = msm_pcie_clk_init(dev);" in source
        and "ret = msm_pcie_pipe_clk_init(dev);" in source,
        "source_enable_owns_perst_and_ltssm": "PCIe: Release the reset of endpoint of RC%d" in source
        and "PCIE20_PARF_LTSSM" in source
        and "PCIe RC%d link initialization failed" in source,
        "dts_pcie1_contract_present": "pcie1: qcom,pcie@1c08000" in pcie_dts
        and "perst-gpio = <&tlmm 102 0>;" in pcie_dts
        and "gdsc-vdd-supply = <&pcie_1_gdsc>;" in pcie_dts,
        "dts_mhi_esoc_link_present": "mhi_0: qcom,mhi@0" in mhi_dts and "esoc-0 =" in overlay,
        "host_analysis_parks_upper_track": "downstream of MDM2AP" in host_analysis
        and "Stop probing the upper eSoC" in host_analysis,
    }
    pass_condition = all(checks.values())
    decision = (
        "v1371-endpoint-readiness-gap-after-rc1-power-proven"
        if pass_condition
        else "v1371-rc1-ltssm-failure-classifier-incomplete"
    )
    reason = (
        "V1370 proves the AP-side pcie1 RC path can execute corrected RC1 enumerate, enable power/clocks/PERST, reach PHY-ready, release endpoint reset, and enter LTSSM; unlike Android, it then stops in poll/compliance before L0 and creates no PCI/MHI device. Android reaches L0 only after the esoc0/provider path has started, so the next blocker is endpoint/SDX50M readiness at PERST release, not a missing pci-msm enumerate entry or upper Wi-Fi HAL path."
        if pass_condition
        else "one or more RC1 LTSSM comparison assumptions are not proven"
    )
    next_step = (
        "V1372 design a bounded provider-held plus delayed corrected-RC1 enumerate proof; do not start Wi-Fi HAL or network bring-up"
        if pass_condition
        else "repair missing V1371 inputs before selecting a live mutation"
    )
    source_lines = {
        "case11_calls_msm_pcie_enumerate": line_no(source, "case MSM_PCIE_ENUMERATION:"),
        "msm_pcie_enumerate_calls_enable_pm_all": line_no(source, "ret = msm_pcie_enable(dev, PM_ALL);"),
        "msm_pcie_enable_entry": line_no(source, "static int msm_pcie_enable(struct msm_pcie_dev_t *dev, u32 options)"),
        "assert_perst": line_no(source, "PCIe: Assert the reset of endpoint of RC%d."),
        "vreg_init": line_no(source, "ret = msm_pcie_vreg_init(dev);"),
        "clk_init": line_no(source, "ret = msm_pcie_clk_init(dev);"),
        "pipe_clk_init": line_no(source, "ret = msm_pcie_pipe_clk_init(dev);"),
        "release_perst": line_no(source, "PCIe: Release the reset of endpoint of RC%d."),
        "enable_ltssm": line_no(source, "msm_pcie_write_mask(dev->parf + PCIE20_PARF_LTSSM"),
        "link_failed": line_no(source, "PCIe RC%d link initialization failed"),
        "link_fail_cleanup": line_no(source, "msm_pcie_pipe_clk_deinit(dev);"),
    }
    dts_facts = {
        "pcie1_node": "qcom,pcie@1c08000",
        "pcie1_perst_gpio": "TLMM102",
        "pcie1_wake_gpio": "TLMM104",
        "pcie1_gdsc": "pcie_1_gdsc",
        "pcie1_vregs": "pm8150l_l3, pm8150_l5, VDD_CX_LEVEL",
        "pcie1_clocks": "GCC_PCIE_1_* plus GCC_PCIE1_PHY_REFGEN_CLK",
        "pcie1_ep_latency_ms": 10 if "qcom,ep-latency = <10>;" in pcie_dts else None,
        "mdm3_provider": "qcom,ext-sdx50m",
        "mdm3_ap2mdm_status_gpio": "TLMM135",
        "mdm3_mdm2ap_status_gpio": "TLMM142",
        "mdm3_soft_reset_pon": "PM8150L GPIO9",
        "mhi_esoc_link": "mhi_0 esoc-0 -> mdm3",
    }
    deltas = {
        "android_esoc0_to_assert_sec": delta(android_events, "esoc0_get", "assert_reset"),
        "android_assert_to_release_sec": delta(android_events, "assert_reset", "release_reset"),
        "android_release_to_l0_sec": delta(android_events, "release_reset", "l0_first"),
        "native_assert_to_release_sec": delta(native_events, "assert_reset", "release_reset"),
        "native_release_to_link_failed_sec": delta(native_events, "release_reset", "link_failed"),
        "native_release_to_poll_active_sec": delta(native_events, "release_reset", "poll_active_first"),
        "native_release_to_poll_compliance_sec": delta(native_events, "release_reset", "poll_compliance_first"),
    }
    return {
        "cycle": "V1371",
        "type": "host-only RC1 LTSSM failure classifier",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "checks": checks,
        "deltas": deltas,
        "native_events": native_events,
        "android_events": android_events,
        "source_lines": source_lines,
        "dts_facts": dts_facts,
        "interpretation": {
            "rc_side_power_entry_missing": False,
            "endpoint_not_ready_at_perst_release": pass_condition,
            "upper_wifi_hal_still_downstream": True,
            "why": [
                "native V1370 reaches PHY ready, reset release, and LTSSM poll states",
                "native V1370 never reaches L0, Current GEN, PCI device, or MHI device",
                "Android reaches L0 shortly after esoc0 is requested and before WLAN-PD/BDF",
                "pci-msm case=11 already exercises msm_pcie_enable(PM_ALL), so a new shim would not solve endpoint readiness by itself",
            ],
        },
        "v1372_candidate": {
            "name": "provider-held-delayed-corrected-rc1-enumerate-proof",
            "scope": "bounded live design candidate, not executed by V1371",
            "rationale": "match Android ordering: start/hold SDX50M provider path first, then trigger corrected RC1 enumerate after a short Android-derived delay",
            "candidate_order": [
                "preflight native selftest fail=0 and debugfs mount state",
                "start existing lower/provider path that holds /dev/subsys_esoc0 and toggles AP2MDM/PON",
                "wait near Android esoc0-to-RC1 interval or poll AP2MDM/PON readable state",
                "write only rc_sel=2 then case=11",
                "capture GPIO142, pcie1 LTSSM/L0, PCI/MHI, dmesg, cleanup and post-selftest",
            ],
            "hard_stops": [
                "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
                "no PERST assert/deassert debug cases",
                "no PMIC/GPIO/GDSC direct writes",
                "no eSoC notify or BOOT_DONE spoof",
                "no flash, boot image write, or partition write",
            ],
        },
        "safety": {
            "host_only": True,
            "device_command_executed": False,
            "debugfs_write_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "flash_boot_partition_write_executed": False,
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V1371 RC1 LTSSM Failure Classifier",
            "",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            markdown_table(["check", "pass"], check_rows(manifest.get("checks") or {})),
            "",
        ]
    )


def render_report(manifest: dict[str, Any]) -> str:
    if manifest.get("missing"):
        details = "\n".join(f"- `{item}`" for item in manifest["missing"])
        return "\n".join(
            [
                "# Native Init V1371 RC1 LTSSM Failure Classifier",
                "",
                "## Summary",
                "",
                f"- Decision: `{manifest['decision']}`",
                f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
                "",
                "## Missing Inputs",
                "",
                details,
                "",
            ]
        )
    v1372 = manifest["v1372_candidate"]
    return "\n".join(
        [
            "# Native Init V1371 RC1 LTSSM Failure Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1371`",
            "- Type: host-only RC1 LTSSM failure classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
            "- Script: `scripts/revalidation/native_wifi_rc1_ltssm_failure_classifier_v1371.py`",
            "- Evidence:",
            "  - `tmp/wifi/v1371-rc1-ltssm-failure-classifier/manifest.json`",
            "  - `tmp/wifi/v1371-rc1-ltssm-failure-classifier/summary.md`",
            "",
            "## Decision",
            "",
            manifest["reason"],
            "",
            "## Checks",
            "",
            markdown_table(["check", "pass"], check_rows(manifest.get("checks") or {})),
            "",
            "## Timeline Deltas",
            "",
            markdown_table(["field", "seconds"], [[key, value] for key, value in manifest["deltas"].items()]),
            "",
            "## Native V1370 Events",
            "",
            markdown_table(["event", "time", "text"], event_rows(manifest["native_events"])),
            "",
            "## Android Reference Events",
            "",
            markdown_table(["event", "time", "text"], event_rows(manifest["android_events"])),
            "",
            "## pci-msm Source Map",
            "",
            markdown_table(["symbol", "line"], source_rows(manifest["source_lines"])),
            "",
            "## DTS Facts",
            "",
            markdown_table(["fact", "value"], dts_rows(manifest["dts_facts"])),
            "",
            "## V1372 Candidate",
            "",
            f"- Name: `{v1372['name']}`",
            f"- Scope: {v1372['scope']}",
            f"- Rationale: {v1372['rationale']}",
            "",
            "### Candidate Order",
            "",
            "\n".join(f"- {item}" for item in v1372["candidate_order"]),
            "",
            "### Hard Stops",
            "",
            "\n".join(f"- {item}" for item in v1372["hard_stops"]),
            "",
            "## Safety",
            "",
            "- V1371 is host-only and executes no device command.",
            "- No debugfs write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`,",
            "  Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external",
            "  ping, flash, boot image write, or partition write occurred.",
            "",
            "## Next",
            "",
            manifest["next_step"],
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = classify()
    manifest["command"] = args.command
    manifest["host"] = collect_host_metadata()
    out_dir = repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_summary(manifest))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(out_dir)}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
