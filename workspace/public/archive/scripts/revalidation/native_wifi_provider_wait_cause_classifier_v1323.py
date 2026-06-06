#!/usr/bin/env python3
"""V1323 host-only provider wait-cause classifier.

V1322 classified SDX50M response inputs and placed the blocker around the
proprietary provider wait path.  V1323 reconciles OSRC-visible subsystem
restart code with retained live reports to decide whether the current blocker
is `wait_for_err_ready()` or the board-specific ext-mdm provider power-up body.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1323-provider-wait-cause-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1323-provider-wait-cause-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1323_PROVIDER_WAIT_CAUSE_CLASSIFIER_2026-05-31.md")
DEFAULT_V1322 = Path("tmp/wifi/v1322-sdx50m-response-input-classifier/manifest.json")
DEFAULT_V1318 = Path("tmp/wifi/v1318-critical-lower-trace-collector-live/manifest.json")
DEFAULT_V1319 = Path("tmp/wifi/v1319-gpio135-response-gap-classifier/manifest.json")
DEFAULT_V849_REPORT = Path("docs/reports/NATIVE_INIT_V849_SUBSYS_ESOC0_WAIT_STATE_SAMPLER_2026-05-25.md")
DEFAULT_V850_REPORT = Path("docs/reports/NATIVE_INIT_V850_EXT_MDM_POWERUP_SURFACE_CLASSIFIER_2026-05-25.md")
DEFAULT_V918_REPORT = Path("docs/reports/NATIVE_INIT_V918_MDM_HELPER_SUBSYS_TRIGGER_WAIT_LIVE_2026-05-26.md")
DEFAULT_V963_REPORT = Path("docs/reports/NATIVE_INIT_V963_POST_PROVIDER_TRIGGER_LIVE_2026-05-26.md")
DEFAULT_MDM3_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_PM_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_SSR_SOURCE = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'drivers', 'soc', 'qcom', 'subsystem_restart.c')
DEFAULT_ESOC_CLIENT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'linux', 'esoc_client.h')
DEFAULT_ESOC_CTRL = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'uapi', 'linux', 'esoc_ctrl.h')

FORBIDDEN_FLAGS = (
    "device_commands_executed",
    "device_mutations",
    "pm_actor_executed",
    "mdm_helper_executed",
    "tracefs_write_executed",
    "live_esoc_ioctl_executed",
    "live_esoc_notify_executed",
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
)

INPUT_FORBIDDEN_FLAGS = (
    "live_esoc_ioctl_executed",
    "live_esoc_notify_executed",
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
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


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


def contains(text: str, needle: str) -> bool:
    return needle in text


def all_input_forbidden_clear(manifest: dict[str, Any]) -> bool:
    return all(not bool_value(manifest.get(flag)) for flag in INPUT_FORBIDDEN_FLAGS)


def summarize_v1322(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_input_forbidden_clear(manifest),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_v1318(manifest: dict[str, Any]) -> dict[str, Any]:
    cls = manifest.get("critical_line_classification") or {}
    response = manifest.get("response_sampler") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_input_forbidden_clear(manifest),
        "critical_line_count": int_value(cls.get("critical_line_count")),
        "gpio1270_line_count": int_value(cls.get("gpio1270_line_count")),
        "gpio135_high_count": int_value(cls.get("gpio135_high_count")),
        "gpio142_line_count": int_value(cls.get("gpio142_line_count")),
        "post_gpio135_sample_span_sec": float_value(cls.get("post_gpio135_sample_span_sec")),
        "mhi_pipe_seen": bool_value(response.get("mhi_pipe_seen")),
        "wlan0_seen": bool_value(response.get("wlan0_seen")),
    }


def summarize_v1319(manifest: dict[str, Any]) -> dict[str, Any]:
    native = manifest.get("native_v1318") or {}
    android = manifest.get("android_reference") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool_value(manifest.get("pass")),
        "forbidden_clear": all_input_forbidden_clear(manifest),
        "native_gpio135_high_count": int_value(native.get("gpio135_high_count")),
        "native_gpio142_line_count": int_value(native.get("gpio142_line_count")),
        "native_mhi_pipe_seen": bool_value(native.get("mhi_pipe_seen")),
        "native_wlan0_seen": bool_value(native.get("wlan0_seen")),
        "android_gpio142_irq_count": int_value(android.get("v1239_gpio142_irq_count")),
        "android_pcie_rc1_lines": int_value(android.get("v1239_pcie_rc1_lines")),
        "android_wlan0_present": bool_value(android.get("v1239_wlan0_present")),
    }


def summarize_texts(args: argparse.Namespace) -> dict[str, Any]:
    v849 = read_text(args.v849_report)
    v850 = read_text(args.v850_report)
    v918 = read_text(args.v918_report)
    v963 = read_text(args.v963_report)
    mdm3 = read_text(args.mdm3_research)
    pm = read_text(args.pm_research)
    ssr = read_text(args.ssr_source)
    esoc_client = read_text(args.esoc_client)
    esoc_ctrl = read_text(args.esoc_ctrl)
    return {
        "v849_report_present": bool(v849),
        "v849_wchan_mdm_subsys_powerup": contains(v849, "Holder `wchan` | `mdm_subsys_powerup`") or contains(v849, "holder wchan  : mdm_subsys_powerup"),
        "v849_wait_for_err_ready_absent": contains(v849, "`wait_for_err_ready` marker | absent") or contains(v849, "not reaching\n`wait_for_err_ready()`"),
        "v849_stack_subsys_open": contains(v849, "mdm_subsys_powerup -> __subsystem_get -> subsys_device_open"),
        "v850_wait_for_err_ready_not_reached": contains(v850, "`wait_for_err_ready` | not reached") or contains(v850, "before\n`wait_for_err_ready`"),
        "v850_provider_source_absent": contains(v850, "Provider source | absent") or contains(v850, "proprietary ext-mdm provider"),
        "v918_soft_reset_stack": contains(v918, "sdx50m_toggle_soft_reset -> mdm4x_do_first_power_on -> mdm_cmd_exe -> mdm_subsys_powerup"),
        "v918_mdm3_offlining": contains(v918, "`mdm3` remained `OFFLINING`"),
        "v963_soft_reset_stack": contains(v963, "`sdx50m_toggle_soft_reset`") and contains(v963, "`mdm4x_do_first_power_on`"),
        "mdm3_gpio135_mapping": contains(mdm3, "GPIO 135") and contains(mdm3, "AP2MDM"),
        "mdm3_gpio142_mapping": contains(mdm3, "GPIO 142") and contains(mdm3, "MDM2AP"),
        "mdm3_wait_for_err_ready_immediate": contains(mdm3, "wait_for_err_ready()`는 **즉시 0을 리턴") or contains(mdm3, "wait_for_err_ready()`)는 **즉시 0"),
        "mdm3_provider_source_missing": contains(mdm3, "OSRC에 없는 proprietary") or contains(mdm3, "proprietary 심볼"),
        "pm_subsys_path": contains(pm, "subsys_device_open()") and contains(pm, "mdm_subsys_powerup()"),
        "pm_mdm2ap_online_contract": contains(pm, "MDM2AP_STATUS GPIO 142") and contains(pm, "mdm3 ONLINE"),
        "ssr_source_present": bool(ssr),
        "ssr_has_wait_for_err_ready": contains(ssr, "static int wait_for_err_ready"),
        "ssr_powerup_calls_desc_powerup_before_wait": contains(ssr, "ret = subsys->desc->powerup(subsys->desc);") and contains(ssr, "pil_ipc(\"[%s]: before wait_for_err_ready"),
        "ssr_has_wait_marker": contains(ssr, "before wait_for_err_ready"),
        "ssr_defines_mdm_subsys_powerup": contains(ssr, "mdm_subsys_powerup("),
        "esoc_client_has_mhi_hook": contains(esoc_client, "ESOC_MHI_HOOK"),
        "esoc_ctrl_has_req_notify": contains(esoc_ctrl, "ESOC_WAIT_FOR_REQ") and contains(esoc_ctrl, "ESOC_NOTIFY") and contains(esoc_ctrl, "ESOC_IMG_XFER_DONE"),
    }


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1322 = summarize_v1322(load_json(args.v1322_manifest))
    v1318 = summarize_v1318(load_json(args.v1318_manifest))
    v1319 = summarize_v1319(load_json(args.v1319_manifest))
    texts = summarize_texts(args)

    v1322_ready = (
        v1322["pass"]
        and v1322["decision"] == "v1322-response-inputs-classified-next-provider-wait-cause"
        and v1322["forbidden_clear"]
    )
    source_places_wait_after_powerup = (
        texts["ssr_source_present"]
        and texts["ssr_has_wait_for_err_ready"]
        and texts["ssr_powerup_calls_desc_powerup_before_wait"]
        and texts["ssr_has_wait_marker"]
        and not texts["ssr_defines_mdm_subsys_powerup"]
    )
    live_block_is_before_wait_for_err_ready = (
        texts["v849_wchan_mdm_subsys_powerup"]
        and texts["v849_wait_for_err_ready_absent"]
        and texts["v849_stack_subsys_open"]
        and texts["v850_wait_for_err_ready_not_reached"]
    )
    provider_stack_classified = (
        texts["v918_soft_reset_stack"]
        and texts["v963_soft_reset_stack"]
        and texts["v850_provider_source_absent"]
        and texts["mdm3_provider_source_missing"]
    )
    gpio_contract_classified = (
        texts["mdm3_gpio135_mapping"]
        and texts["mdm3_gpio142_mapping"]
        and texts["pm_subsys_path"]
        and texts["pm_mdm2ap_online_contract"]
    )
    native_response_absent = (
        v1318["pass"]
        and v1319["pass"]
        and v1318["gpio1270_line_count"] > 0
        and v1318["gpio135_high_count"] >= 1
        and v1318["gpio142_line_count"] == 0
        and v1318["post_gpio135_sample_span_sec"] >= 10.0
        and v1319["native_gpio142_line_count"] == 0
        and not v1319["native_mhi_pipe_seen"]
        and not v1319["native_wlan0_seen"]
    )
    android_positive_delta = (
        v1319["android_gpio142_irq_count"] > 0
        and v1319["android_pcie_rc1_lines"] > 0
        and v1319["android_wlan0_present"]
    )
    esoc_contract_visible = texts["esoc_client_has_mhi_hook"] and texts["esoc_ctrl_has_req_notify"]
    guardrails_clear = v1322["forbidden_clear"] and v1318["forbidden_clear"] and v1319["forbidden_clear"]

    checks = [
        check("v1322-provider-branch-ready", v1322_ready, f"decision={v1322['decision']}"),
        check("ssr-wait-after-provider-powerup", source_places_wait_after_powerup, f"wait_for_err_ready={texts['ssr_has_wait_for_err_ready']} marker={texts['ssr_has_wait_marker']} provider_defined_in_ssr={texts['ssr_defines_mdm_subsys_powerup']}"),
        check("live-block-before-wait-for-err-ready", live_block_is_before_wait_for_err_ready, f"v849_wchan={texts['v849_wchan_mdm_subsys_powerup']} wait_marker_absent={texts['v849_wait_for_err_ready_absent']} v850_not_reached={texts['v850_wait_for_err_ready_not_reached']}"),
        check("provider-stack-is-proprietary-soft-reset", provider_stack_classified, f"v918_stack={texts['v918_soft_reset_stack']} v963_stack={texts['v963_soft_reset_stack']} source_absent={texts['v850_provider_source_absent']}"),
        check("gpio135-gpio142-contract-mapped", gpio_contract_classified, f"gpio135={texts['mdm3_gpio135_mapping']} gpio142={texts['mdm3_gpio142_mapping']} pm_path={texts['pm_subsys_path']}"),
        check("native-post-gpio135-response-absent", native_response_absent, f"gpio1270={v1318['gpio1270_line_count']} gpio135={v1318['gpio135_high_count']} gpio142={v1318['gpio142_line_count']} span={v1318['post_gpio135_sample_span_sec']}"),
        check("android-positive-delta-present", android_positive_delta, f"android_gpio142={v1319['android_gpio142_irq_count']} pcie_rc1={v1319['android_pcie_rc1_lines']} wlan0={v1319['android_wlan0_present']}"),
        check("esoc-contract-visible", esoc_contract_visible, f"mhi_hook={texts['esoc_client_has_mhi_hook']} req_notify={texts['esoc_ctrl_has_req_notify']}"),
        check("guardrails-clear", guardrails_clear, "host-only classifier; reconciled inputs have no Wi-Fi HAL/connect/credentials/network/flash/partition/PMIC/GPIO/direct-eSoC mutation"),
    ]

    passed = all(row["pass"] for row in checks)
    if passed:
        decision = "v1323-provider-wait-cause-is-proprietary-powerup-response"
        reason = (
            "wait_for_err_ready is not the current blocker; source places it after provider powerup, "
            "while V849/V918/V963 place the live block inside the proprietary ext-mdm soft-reset/powerup path "
            "after GPIO1270/GPIO135 activity and before GPIO142/PCIe/MHI/WLFW response"
        )
        next_step = (
            "V1324 should classify Android-vs-native provider response deltas around GPIO142/errfatal/soft-reset/PCIe timing "
            "using host/source evidence first; only then design a bounded read-only or reboot-bounded live sampler. "
            "Do not issue direct PMIC/GPIO/GDSC/eSoC writes, repeat image-link, or start Wi-Fi HAL/connect."
        )
    else:
        decision = "v1323-provider-wait-cause-evidence-incomplete"
        reason = "provider wait-cause inputs are missing or inconsistent"
        next_step = "refresh the failed report/source/evidence input before another live gate"

    return {
        "cycle": "v1323",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1322_manifest": str(repo_path(args.v1322_manifest)),
            "v1318_manifest": str(repo_path(args.v1318_manifest)),
            "v1319_manifest": str(repo_path(args.v1319_manifest)),
            "v849_report": str(repo_path(args.v849_report)),
            "v850_report": str(repo_path(args.v850_report)),
            "v918_report": str(repo_path(args.v918_report)),
            "v963_report": str(repo_path(args.v963_report)),
            "mdm3_research": str(repo_path(args.mdm3_research)),
            "pm_research": str(repo_path(args.pm_research)),
            "ssr_source": str(repo_path(args.ssr_source)),
            "esoc_client": str(repo_path(args.esoc_client)),
            "esoc_ctrl": str(repo_path(args.esoc_ctrl)),
        },
        "v1322": v1322,
        "v1318": v1318,
        "v1319": v1319,
        "text_evidence": texts,
        "checks": checks,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "pm_actor_executed": False,
        "mdm_helper_executed": False,
        "tracefs_write_executed": False,
        "live_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
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
    rows = [[row["name"], row["pass"], row["detail"]] for row in manifest["checks"]]
    safety_rows = [[key, manifest.get(key)] for key in FORBIDDEN_FLAGS]
    v1318 = manifest["v1318"]
    v1319 = manifest["v1319"]
    texts = manifest["text_evidence"]
    return "\n".join([
        "# V1323 Provider Wait-cause Classifier",
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
        markdown_table(["check", "pass", "detail"], rows),
        "",
        "## Wait-cause Model",
        "",
        markdown_table(["layer", "evidence", "classification"], [
            ["SSR source", f"wait_for_err_ready={texts['ssr_has_wait_for_err_ready']} provider_defined_in_ssr={texts['ssr_defines_mdm_subsys_powerup']}", "provider powerup precedes public wait"],
            ["Live wait", f"V849 mdm_subsys_powerup={texts['v849_wchan_mdm_subsys_powerup']} V918 soft-reset stack={texts['v918_soft_reset_stack']}", "inside proprietary ext-mdm path"],
            ["Native response", f"GPIO1270={v1318['gpio1270_line_count']} GPIO135={v1318['gpio135_high_count']} GPIO142={v1318['gpio142_line_count']}", "AP side toggles, MDM2AP silent"],
            ["Android positive", f"GPIO142={v1319['android_gpio142_irq_count']} PCIe RC1={v1319['android_pcie_rc1_lines']} wlan0={v1319['android_wlan0_present']}", "hardware can answer under Android"],
        ]),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# Native Init V1323 Provider Wait-cause Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1323`",
        "- Type: host-only provider wait-cause classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1323-provider-wait-cause-classifier/manifest.json`",
        "  - `tmp/wifi/v1323-provider-wait-cause-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_provider_wait_cause_classifier_v1323.py`",
        "",
        "V1323 reconciles the public Samsung OSRC subsystem restart code with",
        "retained live evidence. The public SSR path calls the board provider",
        "`powerup()` before `wait_for_err_ready()`, and the staged OSRC tree does",
        "not contain the proprietary `mdm_subsys_powerup` implementation. V849,",
        "V918, and V963 place the live native block inside that provider path, with",
        "stacks including `sdx50m_toggle_soft_reset`, `mdm4x_do_first_power_on`,",
        "`mdm_cmd_exe`, and `mdm_subsys_powerup`. V1318/V1319 show that native",
        "reaches PMIC soft-reset/GPIO1270 and AP2MDM/GPIO135 activity, but never",
        "gets MDM2AP/GPIO142, PCIe RC1/MHI, WLFW/BDF, or `wlan0`. Android-positive",
        "reference evidence still has those downstream responses.",
        "",
        "## Decision",
        "",
        "The current blocker is not public `wait_for_err_ready()` and not the",
        "previous image-link/PM actor delivery gate. It is the proprietary ext-mdm",
        "provider response path after SDX50M soft-reset/AP2MDM activity and before",
        "GPIO142/PCIe/MHI/WLFW response. V1324 should classify Android-vs-native",
        "provider response deltas around GPIO142, errfatal, soft-reset, and PCIe",
        "timing from host/source evidence first. Only a bounded read-only or",
        "reboot-bounded live sampler is justified after that classification.",
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, PM actor start, `mdm_helper` start,",
        "tracefs write, live eSoC ioctl/notify, PMIC write, GPIO line request, direct",
        "GDSC/eSoC write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes,",
        "external ping, flash, boot image write, or partition write occurred.",
        "",
    ])


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print(f"gpio135_high: {manifest['v1318']['gpio135_high_count']}")
    print(f"gpio142_native_lines: {manifest['v1318']['gpio142_line_count']}")
    print(f"android_gpio142_irq: {manifest['v1319']['android_gpio142_irq_count']}")
    print(f"evidence: {manifest.get('_run_dir')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1322-manifest", type=Path, default=DEFAULT_V1322)
    parser.add_argument("--v1318-manifest", type=Path, default=DEFAULT_V1318)
    parser.add_argument("--v1319-manifest", type=Path, default=DEFAULT_V1319)
    parser.add_argument("--v849-report", type=Path, default=DEFAULT_V849_REPORT)
    parser.add_argument("--v850-report", type=Path, default=DEFAULT_V850_REPORT)
    parser.add_argument("--v918-report", type=Path, default=DEFAULT_V918_REPORT)
    parser.add_argument("--v963-report", type=Path, default=DEFAULT_V963_REPORT)
    parser.add_argument("--mdm3-research", type=Path, default=DEFAULT_MDM3_RESEARCH)
    parser.add_argument("--pm-research", type=Path, default=DEFAULT_PM_RESEARCH)
    parser.add_argument("--ssr-source", type=Path, default=DEFAULT_SSR_SOURCE)
    parser.add_argument("--esoc-client", type=Path, default=DEFAULT_ESOC_CLIENT)
    parser.add_argument("--esoc-ctrl", type=Path, default=DEFAULT_ESOC_CTRL)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    if args.command == "plan":
        manifest["decision"] = "v1323-provider-wait-cause-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; no device command or live action executed"
        manifest["next_step"] = "run V1323 host-only classifier against existing provider/source evidence"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
