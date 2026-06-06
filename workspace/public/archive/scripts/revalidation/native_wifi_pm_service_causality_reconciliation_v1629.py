#!/usr/bin/env python3
"""V1629 host-only causality reconciliation for the pm-service OFFLINE track."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1629-pm-service-causality-reconciliation")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1629_PM_SERVICE_CAUSALITY_RECONCILIATION_2026-06-02.md")
LATEST_POINTER = Path("tmp/wifi/latest-v1629-pm-service-causality-reconciliation.txt")

V1496_MANIFEST = Path("tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/manifest.json")
V1497_REPORT = Path("docs/reports/NATIVE_INIT_V1497_AUTO_READINESS_RC1_FAILURE_CLASSIFIER_2026-06-01.md")
V1498_MANIFEST = Path("tmp/wifi/v1498-msm-pcie-test11-static-analysis/manifest.json")
V1523_MANIFEST = Path("tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier/manifest.json")
V1524_MANIFEST = Path("tmp/wifi/v1524-endpoint-trigger-attribution-classifier/manifest.json")
V1552_MANIFEST = Path("tmp/wifi/v1552-rc1-endpoint-response-tracefs-live/manifest.json")
V1556_REPORT = Path("docs/reports/NATIVE_INIT_V1556_V1555_VS_V1552_ENDPOINT_SIGNAL_COMPARATOR_2026-06-02.md")
V1559_REPORT = Path("docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md")
V1628_MANIFEST = Path("tmp/wifi/v1628-pm-service-shutdown-list-classifier/manifest.json")
OOB_HANDOFF_REPORT = Path("docs/reports/ESOC_PMSERVICE_CAUSALITY_HANDOFF_2026-06-02.md")
NEXT_PLAN = Path("docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md")


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path, limit: int = 8 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def status(pass_value: bool) -> str:
    return "pass" if pass_value else "manual-review"


def analyze() -> dict[str, Any]:
    v1496 = read_json(V1496_MANIFEST)
    v1496_progress = v1496.get("wifi_progress") if isinstance(v1496.get("wifi_progress"), dict) else {}
    v1498 = read_json(V1498_MANIFEST)
    v1523 = read_json(V1523_MANIFEST)
    v1524 = read_json(V1524_MANIFEST)
    v1552 = read_json(V1552_MANIFEST)
    v1628 = read_json(V1628_MANIFEST)
    v1628_current = v1628.get("current") if isinstance(v1628.get("current"), dict) else {}
    v1628_checks = v1628.get("checks") if isinstance(v1628.get("checks"), dict) else {}
    oob_text = read_text(OOB_HANDOFF_REPORT)
    v1556_text = read_text(V1556_REPORT)
    v1559_text = read_text(V1559_REPORT)

    current = {
        "v1496_decision": v1496.get("decision", ""),
        "v1496_final_decision": v1496_progress.get("final_decision", ""),
        "v1496_provider_trigger": bool_value(v1496_progress.get("provider_trigger")),
        "v1496_rc1_progress": bool_value(v1496_progress.get("rc1_progress")),
        "v1496_rc1_l0": bool_value(v1496_progress.get("rc1_l0")),
        "v1496_rc1_link_failed": bool_value(v1496_progress.get("rc1_link_failed")),
        "v1496_mhi_progress": bool_value(v1496_progress.get("mhi_progress")),
        "v1496_wlfw_progress": bool_value(v1496_progress.get("wlfw_progress")),
        "v1496_wlan0_present": bool_value(v1496_progress.get("wlan0_present")),
        "v1498_decision": v1498.get("decision", ""),
        "v1523_decision": v1523.get("decision", ""),
        "v1524_decision": v1524.get("decision", ""),
        "v1552_decision": v1552.get("decision", ""),
        "v1628_decision": v1628.get("decision", ""),
        "v1628_surface_still_offlining": bool_value(v1628_checks.get("surface_still_offlining")),
        "v1628_shutdown_critical_list_allowed": bool_value(v1628_checks.get("shutdown_critical_list_allowed")),
        "v1628_pm_service_exits_before_ipc_or_pm_fd": bool_value(v1628_checks.get("pm_service_still_exits_before_ipc_or_pm_fd")),
        "v1628_subsys9_state": v1628_current.get("subsys9_state", ""),
        "v1628_helper_result": v1628_current.get("helper_result", ""),
    }
    checks = {
        "v1496_rc1_failure_fixed_point": current["v1496_final_decision"] == "rc1-ltssm-link-failed-no-l0"
        and current["v1496_provider_trigger"]
        and current["v1496_rc1_progress"]
        and current["v1496_rc1_link_failed"]
        and not current["v1496_rc1_l0"]
        and not current["v1496_mhi_progress"]
        and not current["v1496_wlfw_progress"]
        and not current["v1496_wlan0_present"],
        "test11_path_already_classified": bool_value(v1498.get("pass"))
        and bool_value(v1523.get("pass"))
        and "test11" in current["v1523_decision"].lower()
        and "readiness-gap" in current["v1523_decision"],
        "endpoint_silent_after_ap_side_power": bool_value(v1552.get("pass"))
        and "endpoint-silent-no-l0" in current["v1552_decision"],
        "pm_service_offline_track_is_effect": bool_value(v1628.get("pass"))
        and current["v1628_surface_still_offlining"]
        and current["v1628_shutdown_critical_list_allowed"]
        and current["v1628_pm_service_exits_before_ipc_or_pm_fd"]
        and current["v1628_subsys9_state"] == "OFFLINING",
        "fake_online_explicitly_rejected": "STOP before V1630 fake-ONLINE" in oob_text
        and "No fake-ONLINE/system-info spoof" in oob_text
        and "do NOT fake ONLINE" in oob_text,
        "gpio142_mdm2ap_redirect_present": "GPIO142/MDM2AP" in oob_text
        and "no MDM2AP/GPIO142 response" in oob_text
        and "Keep everything read-only / source-build until the GPIO142 cause is classified" in oob_text,
        "android_pre_endpoint_order_reference_present": "GPIO142" in v1559_text
        and "Android" in v1559_text,
        "native_endpoint_signal_comparator_present": "GPIO142" in v1556_text
        and ("no L0" in v1556_text or "no-l0" in v1556_text),
    }
    pass_ok = all(checks.values())
    return {
        "cycle": "V1629",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1496_manifest": rel(V1496_MANIFEST),
            "v1497_report": rel(V1497_REPORT),
            "v1498_manifest": rel(V1498_MANIFEST),
            "v1523_manifest": rel(V1523_MANIFEST),
            "v1524_manifest": rel(V1524_MANIFEST),
            "v1552_manifest": rel(V1552_MANIFEST),
            "v1556_report": rel(V1556_REPORT),
            "v1559_report": rel(V1559_REPORT),
            "v1628_manifest": rel(V1628_MANIFEST),
            "oob_handoff_report": rel(OOB_HANDOFF_REPORT),
            "next_plan": rel(NEXT_PLAN),
        },
        "decision": "v1629-pm-service-causality-reconciled-lower-sdx50m-gate"
        if pass_ok else "v1629-pm-service-causality-reconciliation-manual-review",
        "pass": pass_ok,
        "current": current,
        "checks": checks,
        "next_gate": {
            "cycle": "V1630",
            "type": "host-only lower-layer classifier/design",
            "focus": "Android-good vs native AP2MDM/PM8150L-PON/MDM2AP/RC1 first-response parity",
            "reject": "fake ONLINE system-info, pm-service property chasing, blind TEST:11 retry",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    current = result["current"]
    checks = result["checks"]
    inputs = result["inputs"]
    next_gate = result["next_gate"]
    fixed_rows = [
        ["V1496", "RC1/LTSSM", current["v1496_final_decision"]],
        ["V1498", "TEST:11 source contract", current["v1498_decision"]],
        ["V1523", "TEST:11 vs normal path", current["v1523_decision"]],
        ["V1524", "trigger attribution", current["v1524_decision"]],
        ["V1552", "endpoint response", current["v1552_decision"]],
        ["V1628", "pm-service shutdown-list", current["v1628_decision"]],
    ]
    return "\n".join([
        "# Native Init V1629 pm-service Causality Reconciliation",
        "",
        "## Summary",
        "",
        "- Cycle: `V1629`",
        "- Type: host-only causality classifier over existing Wi-Fi bring-up evidence",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'MANUAL-REVIEW'}",
        "- Reason: the pm-service OFFLINE/exit path is an effect of real `subsys9=esoc0=OFFLINING`, not the lower Wi-Fi blocker; the next gate must return to SDX50M/MDM2AP response parity.",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "path"], [[key, value] for key, value in inputs.items()]),
        "",
        "## Checks",
        "",
        markdown_table(["check", "status"], [[key, status(value)] for key, value in checks.items()]),
        "",
        "## Fixed Points",
        "",
        markdown_table(["cycle", "topic", "decision"], fixed_rows),
        "",
        "## Current Boundary",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in current.items()]),
        "",
        "## Interpretation",
        "",
        "V1496/V1497 already fixed the low-level failure as `rc1-ltssm-link-failed-no-l0`: the provider path triggers, corrected RC1 enumerate reaches PHY/LTSSM progress, and the link fails before L0.  MHI, WLFW, BDF, FW-ready, `wlan0`, scan/connect, DHCP/routes, and external ping remain downstream.",
        "",
        "V1498 and V1523 close the idea that debugfs TEST:11 is missing the core AP-side PCIe enable operation.  TEST:11 reaches the common enumerate/enable path; V1552 then proves AP-side GDSC/refclk/pipe/PERST activity can occur while the endpoint remains silent, with no WAKE/MDM-status/errfatal IRQ and no L0.",
        "",
        "V1621-V1628 repaired property-root and shutdown-critical-list handling, but `pm-service` still exits on the OFFLINE system-info path.  The out-of-band handoff corrects the causality: `subsys9=OFFLINING` is true because SDX50M did not power up.  Faking ONLINE would only advance an upper layer on false state and then hit the already-proven `/dev/subsys_esoc0`/`mdm_subsys_powerup`/MDM2AP block.",
        "",
        "Therefore the pm-service property/system-info track is closed for now.  The actionable question is what Android-good does between AP2MDM/PM8150L-PON assertion and GPIO142/MDM2AP response that native still lacks, or whether native's asserted sequence is electrically ineffective.",
        "",
        "## Next Gate",
        "",
        f"- Recommended cycle: `{next_gate['cycle']}`",
        f"- Type: {next_gate['type']}",
        f"- Focus: {next_gate['focus']}",
        f"- Reject: {next_gate['reject']}",
        "- Output should be an Android-good vs native-fail timeline table for AP2MDM, PM8150L GPIO9/PON, MDM2AP GPIO142/IRQ, RC1 PHY/LTSSM/L0, MHI, WLFW/BDF/FW-ready, and `wlan0`.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, platform bind/unbind, or fake ONLINE/system-info bind.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = analyze()
    store.write_json("manifest.json", result)
    write_private_text(args.report_path, render_report(result))
    write_private_text(LATEST_POINTER, f"{rel(args.out_dir / 'manifest.json')}\n")
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "out_dir": str(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
