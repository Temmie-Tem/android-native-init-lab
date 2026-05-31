#!/usr/bin/env python3
"""V1310 host-only lower prerequisite classifier for native Wi-Fi bring-up."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any


OUT_DIR = Path("tmp/wifi/v1310-lower-prereq-classifier")
SUMMARY_PATH = OUT_DIR / "summary.md"
MANIFEST_PATH = OUT_DIR / "manifest.json"

INPUTS = {
    "v1244_android_power_surface": Path("tmp/wifi/v1244-android-power-surface-classifier/manifest.json"),
    "v1276_pmic_gpio9_polarity": Path("tmp/wifi/v1276-pmic-gpio9-polarity-classifier/manifest.json"),
    "v1291_static_gpio_parity": Path("tmp/wifi/v1291-static-gpio-parity-classifier/manifest.json"),
    "v1306_pmic_gdsc_branch": Path("tmp/wifi/v1306-ext-mdm-pmic-gdsc-branch-classifier/manifest.json"),
    "v1309_focused_transition": Path("tmp/wifi/v1309-pmic-gdsc-transition-sampler-live/manifest.json"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"manifest is not an object: {path}")
    return data


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def first(items: list[str]) -> str:
    return items[0] if items else ""


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def build_manifest() -> dict[str, Any]:
    loaded = {name: load_json(path) for name, path in INPUTS.items()}
    v1244 = loaded["v1244_android_power_surface"]
    v1276 = loaded["v1276_pmic_gpio9_polarity"]
    v1291 = loaded["v1291_static_gpio_parity"]
    v1306 = loaded["v1306_pmic_gdsc_branch"]
    v1309 = loaded["v1309_focused_transition"]

    v1276_analysis = v1276.get("analysis") or {}
    v1309_sampler = v1309.get("response_sampler") or {}
    v1309_pm = v1309.get("pm_service_trigger_observer") or {}

    focused_count = int_value(v1309_sampler.get("pmic_gdsc_focus_sample_count"), 0)
    powerup_seen = bool(v1309_sampler.get("powerup_subsys_esoc0_inferred_seen"))
    pm_service_trigger = bool(v1309_pm.get("pm_service_actor_esoc0_attempt")) or powerup_seen
    no_dynamic_response = (
        int_value(v1309_sampler.get("max_mdm_status_count_total"), -1) == 0
        and int_value(v1309_sampler.get("max_mhi_bus_count"), -1) == 0
        and not bool(v1309_sampler.get("mhi_pipe_seen"))
        and not bool(v1309_sampler.get("wlan0_seen"))
        and int_value(v1309_sampler.get("pmic_gdsc_focus_max_mhi_pipe_fd_count"), -1) == 0
        and int_value(v1309_sampler.get("pmic_gdsc_focus_max_ks_process_count"), -1) == 0
    )
    pcie_gdsc_zero = (
        any("0mV" in line for line in v1309_sampler.get("pmic_gdsc_focus_pcie1_gdsc_lines") or [])
        and any("0mV" in line for line in v1309_sampler.get("pmic_gdsc_focus_pcie0_gdsc_lines") or [])
    )
    pmic_shape_closed = bool(v1276_analysis.get("pmic_gpio9_matches_android_reference"))
    static_gpio_closed = str(v1291.get("decision")) == "v1291-static-gpio-parity-dynamic-power-gap"
    android_positive = (
        bool((v1244.get("android") or {}).get("pcie_rc1_report_present"))
        and bool(((v1244.get("android") or {}).get("timeline") or {}).get("wlan0", {}).get("present"))
    )
    v1306_consistent = str(v1306.get("decision")) == "v1306-pmic-gdsc-prereq-gap-classified"

    checks = [
        check("all-input-manifests-present", all(path.exists() for path in INPUTS.values()), ", ".join(str(path) for path in INPUTS.values())),
        check("android-positive-contrast-present", android_positive, "Android reference reaches PCIe RC1 and wlan0"),
        check("pmic-gpio9-static-shape-closed", pmic_shape_closed, f"V1276 pmic_gpio9_matches_android_reference={pmic_shape_closed}"),
        check("tlmm-static-shape-closed", static_gpio_closed, f"V1291 decision={v1291.get('decision')}"),
        check("v1306-branch-consistent", v1306_consistent, f"V1306 decision={v1306.get('decision')}"),
        check("v1309-focused-window-sufficient", focused_count >= 70, f"focused samples={focused_count}"),
        check("v1309-esoc-powerup-boundary-seen", pm_service_trigger, "powerup marker saw /dev/subsys_esoc0 and mdm_subsys_powerup"),
        check("v1309-no-dynamic-response", no_dynamic_response, "MDM status/MHI/MHI pipe/ks/wlan0 stayed absent"),
        check("v1309-pcie-gdsc-zero", pcie_gdsc_zero, "PCIe0/PCIe1 GDSCs stayed at 0mV"),
    ]
    passed = all(item["pass"] for item in checks)
    if passed:
        decision = "v1310-static-surfaces-closed-dynamic-gdsc-sequence-blocker"
        reason = (
            "V1309 reconfirms the pm-service /dev/subsys_esoc0 -> mdm_subsys_powerup boundary with no "
            "PCIe GDSC/MHI/ks/wlan0 progress, while V1276 and V1291 close PMIC GPIO9 and TLMM static shape "
            "as the shortest blockers"
        )
        next_step = (
            "V1311 should add a stdout-reduced full-window lower-sequence summary sampler or classify the "
            "exact safe GDSC/eSoC prerequisite before any PMIC/GPIO/eSoC mutation"
        )
    else:
        decision = "v1310-lower-prereq-input-gap"
        reason = "one or more prerequisite evidence checks failed"
        next_step = "repair missing or contradictory evidence before selecting the next live gate"

    return {
        "cycle": "v1310",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "input_decisions": {name: loaded[name].get("decision") for name in loaded},
        "checks": checks,
        "classification": {
            "closed_static_surfaces": [
                "PMIC GPIO9 out/high shape (V1276)",
                "TLMM GPIO135/GPIO142 static shape (V1291)",
            ],
            "active_blocker": "dynamic PCIe/GDSC/eSoC lower power sequencing after mdm_subsys_powerup",
            "blocked_surfaces": [
                "PCIe0/PCIe1 GDSC voltage",
                "GPIO142 MDM2AP response IRQ",
                "PCIe RC1 enumeration",
                "MHI bus and MHI pipe",
                "ks image transfer path",
                "WLFW/wlan0",
            ],
            "rejected_next_gates": [
                "blind PMIC GPIO9 write or hold",
                "userspace GPIO line request",
                "direct eSoC ioctl retry",
                "Wi-Fi HAL/scan/connect before lower response",
            ],
        },
        "evidence_summary": {
            "v1309_focus_samples": focused_count,
            "v1309_powerup_seen": powerup_seen,
            "v1309_first_path": first(v1309_sampler.get("powerup_first_path_values") or []),
            "v1309_first_wchan": first(v1309_sampler.get("powerup_first_wchans") or []),
            "v1309_pcie1_gdsc": first(v1309_sampler.get("pmic_gdsc_focus_pcie1_gdsc_lines") or []),
            "v1309_pcie0_gdsc": first(v1309_sampler.get("pmic_gdsc_focus_pcie0_gdsc_lines") or []),
            "v1309_pmic_soft_reset_pinmux": first(v1309_sampler.get("pmic_gdsc_focus_pmic_soft_reset_lines") or []),
            "v1276_pmic_gpio9_matches_android": pmic_shape_closed,
            "v1291_static_gpio_parity_closed": static_gpio_closed,
            "android_positive_pcie_and_wlan0": android_positive,
        },
        "safety": {
            "host_only": True,
            "device_command_executed": False,
            "pmic_write_executed": False,
            "gpio_line_request_executed": False,
            "direct_esoc_ioctl_executed": False,
            "wifi_hal_or_connect_executed": False,
            "credential_use_executed": False,
            "external_ping_executed": False,
            "flash_or_partition_write_executed": False,
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest["checks"]
    evidence = manifest["evidence_summary"]
    classification = manifest["classification"]
    return "\n".join([
        "# Native Init V1310 Lower Prerequisite Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Evidence Summary",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in evidence.items()]),
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass", "detail"], [[item["name"], item["pass"], item["detail"]] for item in checks]),
        "",
        "## Classification",
        "",
        f"- Active blocker: `{classification['active_blocker']}`",
        f"- Closed static surfaces: {', '.join(classification['closed_static_surfaces'])}",
        f"- Blocked surfaces: {', '.join(classification['blocked_surfaces'])}",
        f"- Rejected next gates: {', '.join(classification['rejected_next_gates'])}",
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in manifest["safety"].items()]),
        "",
    ])


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(render_summary(manifest), encoding="utf-8")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {OUT_DIR.resolve()}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
