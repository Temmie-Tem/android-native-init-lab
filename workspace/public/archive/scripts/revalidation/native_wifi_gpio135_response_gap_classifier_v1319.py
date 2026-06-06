#!/usr/bin/env python3
"""V1319 host-only GPIO135-to-GPIO142/PCIe response gap classifier.

V1318 changed the boundary: native no longer lacks AP2MDM GPIO135 assertion.
The bounded late per_proxy path now shows eSoC PIL notification, PMIC soft-reset
GPIO1270 toggles, and GPIO135 high, but no GPIO142/PCIe/MHI/WLFW response.
V1319 compares that evidence with Android-positive references and decides the
next non-mutating gate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1319-gpio135-response-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1319-gpio135-response-gap-classifier.txt")
DEFAULT_V1318_MANIFEST = Path("tmp/wifi/v1318-critical-lower-trace-collector-live/manifest.json")
DEFAULT_V1239_MANIFEST = Path("tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json")
DEFAULT_V1244_MANIFEST = Path("tmp/wifi/v1244-android-power-surface-classifier/manifest.json")
DEFAULT_V1304_MANIFEST = Path("tmp/wifi/v1304-ap2mdm-mdm2ap-response-classifier/manifest.json")
DEFAULT_V896_MANIFEST = Path("tmp/wifi/v896-android-mdm-helper-image-contract-validate/manifest.json")
DEFAULT_V968_MANIFEST = Path("tmp/wifi/v968-android-dmesg-esoc-gpio-timing/manifest.json")
DEFAULT_MDM3_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_ESOC_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1319_GPIO135_RESPONSE_GAP_CLASSIFIER_2026-05-31.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1318-manifest", type=Path, default=DEFAULT_V1318_MANIFEST)
    parser.add_argument("--v1239-manifest", type=Path, default=DEFAULT_V1239_MANIFEST)
    parser.add_argument("--v1244-manifest", type=Path, default=DEFAULT_V1244_MANIFEST)
    parser.add_argument("--v1304-manifest", type=Path, default=DEFAULT_V1304_MANIFEST)
    parser.add_argument("--v896-manifest", type=Path, default=DEFAULT_V896_MANIFEST)
    parser.add_argument("--v968-manifest", type=Path, default=DEFAULT_V968_MANIFEST)
    parser.add_argument("--mdm3-research", type=Path, default=DEFAULT_MDM3_RESEARCH)
    parser.add_argument("--esoc-research", type=Path, default=DEFAULT_ESOC_RESEARCH)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    real_path = repo_path(path)
    if not real_path.exists():
        return {}
    try:
        value = json.loads(real_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def read_text(path: Path) -> str:
    real_path = repo_path(path)
    return real_path.read_text(encoding="utf-8", errors="replace") if real_path.exists() else ""


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def float_value(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return fallback


def tracefs(v1318: dict[str, Any]) -> dict[str, Any]:
    return (v1318.get("analysis") or {}).get("tracefs_uprobe") or {}


def lower_static(v1318: dict[str, Any]) -> dict[str, Any]:
    return tracefs(v1318).get("lower_static_events") or {}


def summarize_v1318(v1318: dict[str, Any]) -> dict[str, Any]:
    classification = v1318.get("critical_line_classification") or {}
    response = v1318.get("response_sampler") or {}
    boundary = v1318.get("post_esoc_boundary") or {}
    mdm_helper = v1318.get("mdm_helper_ks_mhi_parity") or {}
    return {
        "decision": v1318.get("decision", ""),
        "pass": bool_value(v1318.get("pass")),
        "pm_service_esoc0_reach_basis": v1318.get("pm_service_esoc0_reach_basis", ""),
        "critical_count": int_value(lower_static(v1318).get("critical_count")),
        "line_count": int_value(classification.get("line_count")),
        "target_keyword_line_count": int_value(classification.get("target_keyword_line_count")),
        "target_gpio_line_count": int_value(classification.get("target_gpio_line_count")),
        "esoc_pil_notif_count": int_value(classification.get("esoc_pil_notif_count")),
        "gpio1270_line_count": int_value(classification.get("gpio1270_line_count")),
        "gpio135_line_count": int_value(classification.get("gpio135_line_count")),
        "gpio142_line_count": int_value(classification.get("gpio142_line_count")),
        "gpio135_high_count": int_value(classification.get("gpio135_high_count")),
        "post_gpio135_sample_span_sec": float_value(classification.get("post_gpio135_sample_span_sec")),
        "max_mdm_status_count_total": int_value(response.get("max_mdm_status_count_total")),
        "max_pci_dev_count": int_value(response.get("max_pci_dev_count")),
        "max_mhi_bus_count": int_value(response.get("max_mhi_bus_count")),
        "max_kmsg_pcie_count": int_value(response.get("max_kmsg_pcie_count")),
        "max_kmsg_mhi_count": int_value(response.get("max_kmsg_mhi_count")),
        "max_kmsg_wlfw_count": int_value(response.get("max_kmsg_wlfw_count")),
        "max_kmsg_gdsc_count": int_value(response.get("max_kmsg_gdsc_count")),
        "mhi_pipe_seen": bool_value(response.get("mhi_pipe_seen")),
        "wlan0_seen": bool_value(response.get("wlan0_seen")) or bool_value(boundary.get("wlan0_seen")),
        "service69_seen": bool_value(boundary.get("service69_seen")),
        "mdm3_states": boundary.get("mdm3_state_transitions") or [],
        "max_dmesg_wlfw_count": int_value(boundary.get("max_dmesg_wlfw_count")),
        "ks_count_window": int_value(mdm_helper.get("ks_count_window")),
        "mdm_helper_esoc_present": bool_value(mdm_helper.get("mdm_helper_esoc_present")),
        "pm_service_subsys_esoc0_attempt": bool_value(mdm_helper.get("pm_service_subsys_esoc0_attempt")),
        "target_samples": (
            list(classification.get("target_keyword_samples") or [])
            + list(classification.get("target_gpio_samples") or [])
        ),
    }


def summarize_android(v1239: dict[str, Any], v1244: dict[str, Any], v896: dict[str, Any], v968: dict[str, Any]) -> dict[str, Any]:
    android1239 = v1239.get("android") or {}
    android1244 = v1244.get("android") or {}
    class896 = v896.get("classification") or {}
    v852 = v896.get("v852") or {}
    class968 = v968.get("classification") or {}
    timing968 = class968.get("timeline") or class968.get("timing") or {}
    return {
        "v1239_pass": bool_value(v1239.get("pass")),
        "v1244_pass": bool_value(v1244.get("pass")),
        "v896_pass": bool_value(v896.get("pass")),
        "v1239_gpio142_irq_count": int_value(android1239.get("gpio142_irq_count")),
        "v1239_pcie_rc1_lines": int_value(android1239.get("pcie_rc1_lines")),
        "v1239_pcie_l0_lines": int_value(android1239.get("pcie_l0_lines")),
        "v1239_sysmon_esoc0_lines": int_value(android1239.get("sysmon_esoc0_lines")),
        "v1239_wlan0_present": bool_value(android1239.get("wlan0_present")),
        "v1239_wlfw_present": bool_value(android1239.get("wlfw_present")),
        "v1239_bdf_present": bool_value(android1239.get("bdf_present")),
        "v1244_android_pcie_delta": "PCIe RC1" in json.dumps(android1244, sort_keys=True) or bool_value(v1244.get("pass")),
        "v896_mdm3_online": (v852.get("mdm3_state") == "ONLINE") or bool_value(class896.get("android_mdm3_online")),
        "v896_ks_mhi_pipe": bool_value((v896.get("v853_actor_flags") or {}).get("has_ks_mhi_pipe")),
        "v968_has_gpio_request_timing": "GPIO135 request" in json.dumps(class968, sort_keys=True) or bool_value(v968.get("host_only")),
        "v968_subsys_esoc0_time": timing968.get("subsys_esoc0_get") or timing968.get("/dev/subsys_esoc0"),
    }


def summarize_references(mdm3_text: str, esoc_text: str, v1304: dict[str, Any]) -> dict[str, Any]:
    return {
        "v1304_pass": bool_value(v1304.get("pass")),
        "v1304_prior_decision": v1304.get("decision", ""),
        "dts_gpio135_ap2mdm": "GPIO 135" in mdm3_text and "AP → MDM" in mdm3_text,
        "dts_gpio142_mdm2ap": "GPIO 142" in mdm3_text and "MDM → AP" in mdm3_text,
        "dts_gpio1270_soft_reset": "PMIC pm8150l GPIO 9" in mdm3_text,
        "powerup_deasserts_soft_reset": "mdm_toggle_soft_reset(mdm, false)" in mdm3_text,
        "powerup_asserts_gpio135": "gpio_direction_output(MDM_GPIO(mdm, AP2MDM_STATUS), 1)" in mdm3_text,
        "gpio142_async_irq_contract": "GPIO 142" in mdm3_text and "IRQ" in mdm3_text,
        "req_eng_contract": "REQ_ENG" in esoc_text and "mdm_subsys_powerup" in esoc_text,
    }


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1318 = summarize_v1318(load_json(args.v1318_manifest))
    android = summarize_android(
        load_json(args.v1239_manifest),
        load_json(args.v1244_manifest),
        load_json(args.v896_manifest),
        load_json(args.v968_manifest),
    )
    references = summarize_references(
        read_text(args.mdm3_research),
        read_text(args.esoc_research),
        load_json(args.v1304_manifest),
    )

    native_powerup_sequence_seen = (
        v1318["pass"]
        and v1318["decision"] == "v1318-target-critical-lines-captured"
        and v1318["esoc_pil_notif_count"] >= 2
        and v1318["gpio1270_line_count"] >= 2
        and v1318["gpio135_high_count"] >= 1
    )
    native_response_absent = (
        v1318["gpio142_line_count"] == 0
        and v1318["post_gpio135_sample_span_sec"] >= 10.0
        and v1318["max_mdm_status_count_total"] == 0
        and v1318["max_pci_dev_count"] == 0
        and v1318["max_mhi_bus_count"] == 0
        and not v1318["mhi_pipe_seen"]
        and not v1318["service69_seen"]
        and not v1318["wlan0_seen"]
    )
    android_positive_response = (
        android["v1239_pass"]
        and android["v896_pass"]
        and android["v1239_gpio142_irq_count"] > 0
        and android["v1239_pcie_rc1_lines"] > 0
        and android["v1239_wlan0_present"]
        and android["v1239_wlfw_present"]
    )
    source_contract_matches = (
        references["dts_gpio135_ap2mdm"]
        and references["dts_gpio142_mdm2ap"]
        and references["dts_gpio1270_soft_reset"]
        and references["powerup_deasserts_soft_reset"]
        and references["powerup_asserts_gpio135"]
        and references["gpio142_async_irq_contract"]
    )
    prior_assertion_gap_superseded = references["v1304_pass"] and v1318["gpio135_high_count"] >= 1
    ks_mhi_absence_correlates = v1318["ks_count_window"] == 0 and not v1318["mhi_pipe_seen"] and android["v896_ks_mhi_pipe"]

    checks = [
        check(
            "native-powerup-sequence-visible",
            native_powerup_sequence_seen,
            f"esoc_pil={v1318['esoc_pil_notif_count']} gpio1270={v1318['gpio1270_line_count']} gpio135_high={v1318['gpio135_high_count']}",
        ),
        check(
            "native-response-absent-after-gpio135",
            native_response_absent,
            f"gpio142={v1318['gpio142_line_count']} post_gpio135_span={v1318['post_gpio135_sample_span_sec']} pci={v1318['max_pci_dev_count']} mhi={v1318['max_mhi_bus_count']} wlan0={v1318['wlan0_seen']}",
        ),
        check(
            "android-positive-response-reference",
            android_positive_response,
            f"gpio142_irq={android['v1239_gpio142_irq_count']} pcie_rc1={android['v1239_pcie_rc1_lines']} wlfw={android['v1239_wlfw_present']} wlan0={android['v1239_wlan0_present']}",
        ),
        check(
            "source-contract-matches-observed-sequence",
            source_contract_matches,
            json.dumps({key: references[key] for key in sorted(references) if key != "v1304_prior_decision"}, sort_keys=True),
        ),
        check(
            "prior-ap2mdm-assertion-gap-superseded",
            prior_assertion_gap_superseded,
            f"V1304={references['v1304_prior_decision']} V1318_gpio135_high={v1318['gpio135_high_count']}",
        ),
        check(
            "ks-mhi-response-contract-still-absent-native",
            ks_mhi_absence_correlates,
            f"native_ks={v1318['ks_count_window']} native_mhi_pipe={v1318['mhi_pipe_seen']} android_ks_mhi={android['v896_ks_mhi_pipe']}",
        ),
    ]

    passed = all(item["pass"] for item in checks)
    if passed:
        decision = "v1319-gpio135-asserted-mdm2ap-pcie-response-absent"
        reason = (
            "native reaches eSoC PIL notify, soft-reset GPIO1270 toggle, and GPIO135 high, "
            "but receives no GPIO142/PCIe/MHI/WLFW response while Android-positive evidence does"
        )
        next_step = (
            "classify the Android mdm_helper/ks/MHI image-transfer response contract as the likely "
            "post-GPIO135 prerequisite before any lower GPIO/PMIC mutation"
        )
    else:
        decision = "v1319-input-evidence-incomplete"
        reason = "one or more V1318 native or Android-positive response checks failed"
        next_step = "refresh the failed evidence source before selecting another live gate"

    return {
        "cycle": "v1319",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1318_manifest": str(repo_path(args.v1318_manifest)),
            "v1239_manifest": str(repo_path(args.v1239_manifest)),
            "v1244_manifest": str(repo_path(args.v1244_manifest)),
            "v1304_manifest": str(repo_path(args.v1304_manifest)),
            "v896_manifest": str(repo_path(args.v896_manifest)),
            "v968_manifest": str(repo_path(args.v968_manifest)),
            "mdm3_research": str(repo_path(args.mdm3_research)),
            "esoc_research": str(repo_path(args.esoc_research)),
        },
        "native_v1318": v1318,
        "android_reference": android,
        "references": references,
        "checks": checks,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "tracefs_write_executed": False,
        "pm_service_trigger_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    native = manifest["native_v1318"]
    android = manifest["android_reference"]
    target_rows = [
        [
            item.get("event", ""),
            item.get("gpio", ""),
            item.get("line", ""),
        ]
        for item in native["target_samples"][:12]
    ]
    safety_rows = [[key, manifest.get(key)] for key in (
        "device_commands_executed",
        "tracefs_write_executed",
        "pm_service_trigger_executed",
        "pmic_write_executed",
        "gpio_line_request_executed",
        "direct_esoc_ioctl_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
        "wifi_bringup_executed",
        "flash_executed",
        "partition_write_executed",
    )]
    return "\n".join([
        "# V1319 GPIO135 Response Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass", "detail"], [[c["name"], c["pass"], c["detail"]] for c in manifest["checks"]]),
        "",
        "## Native V1318",
        "",
        markdown_table(["field", "value"], [
            ["decision", native["decision"]],
            ["eSoC PIL notif count", native["esoc_pil_notif_count"]],
            ["GPIO1270 / GPIO135 / GPIO142 lines", f"{native['gpio1270_line_count']} / {native['gpio135_line_count']} / {native['gpio142_line_count']}"],
            ["GPIO135 high count", native["gpio135_high_count"]],
            ["post GPIO135 sample span sec", native["post_gpio135_sample_span_sec"]],
            ["PCI / MHI / MHI pipe / wlan0", f"{native['max_pci_dev_count']} / {native['max_mhi_bus_count']} / {native['mhi_pipe_seen']} / {native['wlan0_seen']}"],
            ["ks count window", native["ks_count_window"]],
            ["mdm3 states", json.dumps(native["mdm3_states"], sort_keys=True)],
        ]),
        "",
        "## Android Positive Reference",
        "",
        markdown_table(["field", "value"], [
            ["GPIO142 IRQ count", android["v1239_gpio142_irq_count"]],
            ["PCIe RC1 / L0 lines", f"{android['v1239_pcie_rc1_lines']} / {android['v1239_pcie_l0_lines']}"],
            ["sysmon esoc0 lines", android["v1239_sysmon_esoc0_lines"]],
            ["WLFW / BDF / wlan0", f"{android['v1239_wlfw_present']} / {android['v1239_bdf_present']} / {android['v1239_wlan0_present']}"],
            ["Android ks MHI pipe", android["v896_ks_mhi_pipe"]],
        ]),
        "",
        "## Native Target Samples",
        "",
        markdown_table(["event", "gpio", "line"], target_rows),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    native = manifest["native_v1318"]
    android = manifest["android_reference"]
    return "\n".join([
        "# Native Init V1319 GPIO135 Response Gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1319`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1319-gpio135-response-gap-classifier/manifest.json`",
        "  - `tmp/wifi/v1319-gpio135-response-gap-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_gpio135_response_gap_classifier_v1319.py`",
        "",
        "V1319 updates the lower blocker with V1318 evidence. Native now reaches",
        "the expected eSoC power sequence through PMIC soft-reset GPIO `1270` and",
        "AP2MDM GPIO `135` high. The remaining gap is the absent response: no GPIO",
        "`142`, PCIe, MHI, WLFW/service69, or `wlan0` appears.",
        "",
        "## Result",
        "",
        markdown_table(["field", "native V1318", "Android-positive reference"], [
            ["GPIO135/AP2MDM", f"high count {native['gpio135_high_count']}", "required by ext-sdx50m contract"],
            ["GPIO142/MDM2AP", f"lines {native['gpio142_line_count']}", f"IRQ count {android['v1239_gpio142_irq_count']}"],
            ["PCIe RC1", f"PCI dev count {native['max_pci_dev_count']}", f"RC1 lines {android['v1239_pcie_rc1_lines']}"],
            ["MHI / ks", f"ks {native['ks_count_window']}, MHI pipe {native['mhi_pipe_seen']}", f"Android ks MHI pipe {android['v896_ks_mhi_pipe']}"],
            ["Wi-Fi lower publication", f"service69 {native['service69_seen']}, wlan0 {native['wlan0_seen']}", f"WLFW {android['v1239_wlfw_present']}, wlan0 {android['v1239_wlan0_present']}"],
        ]),
        "",
        "## Interpretation",
        "",
        "V1304's earlier AP2MDM assertion/visibility gap is superseded. V1318 shows",
        "GPIO135 assertion directly in tracefs. The next blocker is post-assertion",
        "SDX50M response: Android gets GPIO142/PCIe/MHI/WLFW, native does not.",
        "",
        "The strongest non-mutating next unit is to classify the Android",
        "`mdm_helper`/`ks`/MHI image-transfer contract as the likely missing",
        "post-GPIO135 prerequisite before any direct GPIO, PMIC, GDSC, or eSoC",
        "mutation is considered.",
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, tracefs write, PM-service trigger,",
        "PMIC write, userspace GPIO line request/hold, direct eSoC ioctl, direct GDSC",
        "write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external",
        "ping, flash, boot image write, or partition write occurred.",
        "",
    ])


def print_result(manifest: dict[str, Any]) -> None:
    native = manifest["native_v1318"]
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print(f"gpio135_high_count:     {native['gpio135_high_count']}")
    print(f"gpio142_line_count:     {native['gpio142_line_count']}")
    print(f"post_gpio135_span_sec:  {native['post_gpio135_sample_span_sec']}")
    print(f"native_ks_count_window: {native['ks_count_window']}")
    print(f"evidence: {manifest.get('_run_dir')}")


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    if args.command == "plan":
        manifest["decision"] = "v1319-gpio135-response-gap-classifier-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; no device command or live action executed"
        manifest["next_step"] = "run V1319 host-only classifier against existing V1318 and Android-positive evidence"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
