#!/usr/bin/env python3
"""V1314 host-only dynamic GDSC/eSoC prerequisite classifier.

V1313 closed the stdout-cap ambiguity and proved a full lower-sequence window:
PM-service reaches ``/dev/subsys_esoc0`` and blocks in ``mdm_subsys_powerup``,
but no PCIe GDSC, MHI, ks, WLFW, or wlan0 transition appears.  This classifier
decides the next safe prerequisite gate without running a device command.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1314-dynamic-gdsc-esoc-prereq-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1314-dynamic-gdsc-esoc-prereq-classifier.txt")
DEFAULT_V1313_MANIFEST = Path("tmp/wifi/v1313-lower-sequence-summary-sampler-live/manifest.json")
DEFAULT_V1310_MANIFEST = Path("tmp/wifi/v1310-lower-prereq-classifier/manifest.json")
DEFAULT_V1292_MANIFEST = Path("tmp/wifi/v1292-dynamic-sequence-plan/manifest.json")
DEFAULT_V776_MANIFEST = Path("tmp/wifi/v776-tracepoint-inventory/manifest.json")
DEFAULT_MDM3_RESEARCH = Path("docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_ESOC_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
DEFAULT_TRACE_SOURCES = [
    workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'trace', 'events', 'regulator.h'),
    workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'trace', 'events', 'gpio.h'),
    workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'trace', 'events', 'irq.h'),
    workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'trace', 'events', 'clk.h'),
    workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'trace', 'events', 'power.h'),
    workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'trace', 'events', 'trace_msm_pil_event.h'),
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1313-manifest", type=Path, default=DEFAULT_V1313_MANIFEST)
    parser.add_argument("--v1310-manifest", type=Path, default=DEFAULT_V1310_MANIFEST)
    parser.add_argument("--v1292-manifest", type=Path, default=DEFAULT_V1292_MANIFEST)
    parser.add_argument("--v776-manifest", type=Path, default=DEFAULT_V776_MANIFEST)
    parser.add_argument("--mdm3-research", type=Path, default=DEFAULT_MDM3_RESEARCH)
    parser.add_argument("--esoc-research", type=Path, default=DEFAULT_ESOC_RESEARCH)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


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
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def source_line(text: str, token: str) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if token in line:
            return index
    return None


def trace_source_summary() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in DEFAULT_TRACE_SOURCES:
        text = read_text(path)
        result[str(path)] = {
            "exists": bool(text),
            "trace_event_count": text.count("TRACE_EVENT(") + text.count("DEFINE_EVENT("),
        }
    return result


def extract_v1313(v1313: dict[str, Any]) -> dict[str, Any]:
    sampler = v1313.get("response_sampler") or {}
    return {
        "decision": v1313.get("decision", ""),
        "pass": bool_value(v1313.get("pass")),
        "sample_count": int_value(sampler.get("lower_summary_sample_count"), 0),
        "summary_end": bool_value(sampler.get("lower_summary_end")),
        "stdout_truncated": bool_value(sampler.get("helper_stdout_truncated")),
        "powerup_seen": bool_value(sampler.get("lower_summary_powerup_seen")),
        "max_powerup_thread_count": int_value(sampler.get("lower_summary_max_powerup_thread_count"), -1),
        "max_mdm_status_count": int_value(sampler.get("lower_summary_max_mdm_status_count_total"), -1),
        "max_pci_dev_count": int_value(sampler.get("lower_summary_max_pci_dev_count"), -1),
        "max_mhi_bus_count": int_value(sampler.get("lower_summary_max_mhi_bus_count"), -1),
        "mhi_pipe_seen": bool_value(sampler.get("lower_summary_mhi_pipe_seen")),
        "max_mhi_pipe_fd_count": int_value(sampler.get("lower_summary_max_mhi_pipe_fd_count"), -1),
        "max_ks_process_count": int_value(sampler.get("lower_summary_max_ks_process_count"), -1),
        "wlan0_seen": bool_value(sampler.get("lower_summary_wlan0_seen")),
        "pcie1_gdsc_zero_seen": bool_value(sampler.get("lower_summary_pcie1_gdsc_zero_seen")),
        "pcie1_gdsc_nonzero_seen": bool_value(sampler.get("lower_summary_pcie1_gdsc_nonzero_seen")),
        "pcie1_gdsc_line": sampler.get("lower_summary_pcie1_gdsc_line", ""),
        "pcie0_gdsc_zero_seen": bool_value(sampler.get("lower_summary_pcie0_gdsc_zero_seen")),
        "pcie0_gdsc_nonzero_seen": bool_value(sampler.get("lower_summary_pcie0_gdsc_nonzero_seen")),
        "pcie0_gdsc_line": sampler.get("lower_summary_pcie0_gdsc_line", ""),
        "pmic_soft_reset_line": sampler.get("lower_summary_pmic_soft_reset_line", ""),
        "tlmm_gpio135_line": sampler.get("lower_summary_tlmm_gpio135_line", ""),
        "tlmm_gpio142_line": sampler.get("lower_summary_tlmm_gpio142_line", ""),
        "gpiochip_line_request_executed": int_value(sampler.get("lower_summary_gpiochip_line_request_executed"), -1),
        "pmic_write_executed": int_value(sampler.get("lower_summary_pmic_write_executed"), -1),
        "esoc_ioctl_executed": int_value(sampler.get("lower_summary_esoc_ioctl_executed"), -1),
    }


def extract_v776(v776: dict[str, Any]) -> dict[str, Any]:
    proof = ((v776.get("analysis") or {}).get("proof") or {})
    return {
        "decision": v776.get("decision", ""),
        "pass": bool_value(v776.get("pass")),
        "available_events_readable": bool_value(proof.get("available_events_readable")),
        "available_events_total": int_value(proof.get("available_events_total"), 0),
        "events_dir": bool_value(proof.get("events_dir")),
        "mounted_after": proof.get("mounted_after"),
        "bpf_attach_executed": bool_value(v776.get("bpf_attach_executed")),
        "ftrace_control_write_executed": bool_value(v776.get("ftrace_control_write_executed")),
    }


def extract_contract(mdm3_research: str, esoc_research: str) -> dict[str, Any]:
    return {
        "mdm_subsys_powerup_waits_req_eng": (
            "mdm_subsys_powerup()` waits only for `REG_REQ_ENG`" in esoc_research
            or "REQ_ENG" in esoc_research and "mdm_subsys_powerup" in esoc_research
        ),
        "kernel_esoc_power_on_after_req": "kernel-side `ESOC_PWR_ON`" in esoc_research,
        "first_power_on_deasserts_soft_reset": "mdm_toggle_soft_reset(mdm, false)" in mdm3_research,
        "first_power_on_asserts_ap2mdm": "GPIO 135 → HIGH" in mdm3_research,
        "mhi_hook_after_esoc_powerup": "mhi_arch_esoc_ops_power_on" in mdm3_research and "esoc powerup **이후에** 실행" in mdm3_research,
        "userspace_gpio_rejected": "userspace에서 직접 HIGH" in mdm3_research,
    }


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1313_raw = load_json(args.v1313_manifest)
    v1310 = load_json(args.v1310_manifest)
    v1292 = load_json(args.v1292_manifest)
    v776 = extract_v776(load_json(args.v776_manifest))
    v1313 = extract_v1313(v1313_raw)
    mdm3_research = read_text(args.mdm3_research)
    esoc_research = read_text(args.esoc_research)
    contract = extract_contract(mdm3_research, esoc_research)
    trace_sources = trace_source_summary()

    full_window_no_transition = (
        v1313["pass"]
        and v1313["decision"] == "v1313-lower-sequence-full-window-no-transition"
        and v1313["sample_count"] >= 81
        and v1313["summary_end"]
        and not v1313["stdout_truncated"]
        and v1313["powerup_seen"]
        and v1313["max_powerup_thread_count"] >= 1
        and v1313["max_mdm_status_count"] == 0
        and v1313["max_pci_dev_count"] == 0
        and v1313["max_mhi_bus_count"] == 0
        and not v1313["mhi_pipe_seen"]
        and v1313["max_mhi_pipe_fd_count"] == 0
        and v1313["max_ks_process_count"] == 0
        and not v1313["wlan0_seen"]
    )
    gdsc_static_zero = (
        v1313["pcie1_gdsc_zero_seen"]
        and not v1313["pcie1_gdsc_nonzero_seen"]
        and v1313["pcie0_gdsc_zero_seen"]
        and not v1313["pcie0_gdsc_nonzero_seen"]
    )
    lower_safety_clean = (
        v1313["gpiochip_line_request_executed"] == 0
        and v1313["pmic_write_executed"] == 0
        and v1313["esoc_ioctl_executed"] == 0
    )
    static_surfaces_closed = (
        bool_value(v1310.get("pass"))
        and v1310.get("decision") == "v1310-static-surfaces-closed-dynamic-gdsc-sequence-blocker"
    )
    trace_source_available = all(item["exists"] and item["trace_event_count"] > 0 for item in trace_sources.values())
    tracefs_read_feasible = (
        v776["pass"]
        and v776["available_events_readable"]
        and v776["events_dir"]
        and v776["available_events_total"] > 0
    )
    contract_ready = all(contract[key] for key in (
        "mdm_subsys_powerup_waits_req_eng",
        "kernel_esoc_power_on_after_req",
        "first_power_on_deasserts_soft_reset",
        "first_power_on_asserts_ap2mdm",
        "mhi_hook_after_esoc_powerup",
    ))
    prior_dense_selection = (
        bool_value(v1292.get("pass"))
        and v1292.get("decision") == "v1292-dense-dynamic-response-sampler-selected"
    )

    checks = [
        check("v1313-full-window-no-transition", full_window_no_transition, f"decision={v1313['decision']} samples={v1313['sample_count']} end={v1313['summary_end']} truncated={v1313['stdout_truncated']}"),
        check("v1313-pcie-gdsc-zero", gdsc_static_zero, f"pcie1={v1313['pcie1_gdsc_line']} pcie0={v1313['pcie0_gdsc_line']}"),
        check("v1313-lower-safety-clean", lower_safety_clean, f"gpio_req={v1313['gpiochip_line_request_executed']} pmic_write={v1313['pmic_write_executed']} esoc_ioctl={v1313['esoc_ioctl_executed']}"),
        check("static-surfaces-already-closed", static_surfaces_closed, f"V1310 decision={v1310.get('decision', '')}"),
        check("prior-dense-sampler-need-satisfied", prior_dense_selection, f"V1292 decision={v1292.get('decision', '')}"),
        check("provider-powerup-contract-present", contract_ready, json.dumps(contract, sort_keys=True)),
        check("trace-sources-present", trace_source_available, json.dumps(trace_sources, sort_keys=True)),
        check("tracefs-read-feasible", tracefs_read_feasible, f"V776 decision={v776['decision']} events={v776['available_events_total']} mounted_after={v776['mounted_after']}"),
    ]
    passed = all(item["pass"] for item in checks)

    if args.command == "plan":
        decision = "v1314-dynamic-prereq-classifier-plan-ready"
        passed = True
        reason = "plan-only; no evidence mutation or device command executed"
        next_step = "run V1314 host-only dynamic GDSC/eSoC prerequisite classifier"
    elif passed:
        decision = "v1314-provider-internal-first-power-on-trace-gate-selected"
        reason = (
            "V1313 proves the full lower window reaches mdm_subsys_powerup but no GDSC/PCI/MHI/ks/wlan0 transition. "
            "Static PMIC/TLMM shape and sampler cadence are closed, so the next safe prerequisite is not a PMIC/GPIO/GDSC/eSoC mutation; "
            "it is a provider-internal first-power-on trace gate that records regulator/gpio/irq/clk/PIL events during the existing bounded PM-service path."
        )
        next_step = (
            "V1315 should implement a targeted tracefs-event preflight for regulator/gpio/irq/clk/power/msm_pil_event availability and formats; "
            "V1316 can then run a bounded tracefs event collector around the same late per_proxy PM-service path without Wi-Fi HAL/connect or lower writes."
        )
    else:
        decision = "v1314-dynamic-prereq-input-gap"
        reason = "one or more evidence or source prerequisites is missing or contradictory"
        next_step = "repair the failed checks before choosing any lower mutation or trace gate"

    return {
        "cycle": "v1314",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v1313_manifest": str(repo_path(args.v1313_manifest)),
            "v1310_manifest": str(repo_path(args.v1310_manifest)),
            "v1292_manifest": str(repo_path(args.v1292_manifest)),
            "v776_manifest": str(repo_path(args.v776_manifest)),
            "mdm3_research": str(repo_path(args.mdm3_research)),
            "esoc_research": str(repo_path(args.esoc_research)),
        },
        "checks": checks,
        "analysis": {
            "v1313": v1313,
            "v776": v776,
            "contract": contract,
            "trace_sources": trace_sources,
            "selected_gate": "tracefs-static-event preflight, then bounded PM-service event capture",
            "accepted_prerequisite": "provider-internal first-power-on event visibility",
            "rejected_mutations": [
                "direct PMIC GPIO9 write or hold",
                "userspace TLMM GPIO135/GPIO142 line request or hold",
                "direct PCIe GDSC regulator write",
                "direct ESOC_CMD_EXE / eSoC ioctl retry",
                "Wi-Fi HAL/scan/connect before WLFW/wlan0 readiness",
            ],
            "target_event_groups": [
                "regulator:regulator_enable* / regulator_set_voltage*",
                "gpio:gpio_direction / gpio_value",
                "irq:irq_handler_entry / irq_handler_exit",
                "clk:clk_enable* / clk_prepare*",
                "power:power_domain_target / device_pm_callback_*",
                "msm_pil_event:pil_event / pil_notif / pil_func",
            ],
        },
        "device_commands_executed": False,
        "device_mutations": False,
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
    analysis = manifest["analysis"]
    v1313 = analysis["v1313"]
    return "\n".join([
        "# Native Init V1314 Dynamic GDSC/eSoC Prerequisite Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Evidence",
        "",
        markdown_table(["field", "value"], [
            ["V1313 decision", v1313["decision"]],
            ["summary samples/end/truncated", f"{v1313['sample_count']} / {v1313['summary_end']} / {v1313['stdout_truncated']}"],
            ["mdm_subsys_powerup threads", v1313["max_powerup_thread_count"]],
            ["MDM status / PCI / MHI max", f"{v1313['max_mdm_status_count']} / {v1313['max_pci_dev_count']} / {v1313['max_mhi_bus_count']}"],
            ["MHI pipe / ks / wlan0", f"{v1313['mhi_pipe_seen']} / {v1313['max_ks_process_count']} / {v1313['wlan0_seen']}"],
            ["PCIe1 GDSC", v1313["pcie1_gdsc_line"]],
            ["PCIe0 GDSC", v1313["pcie0_gdsc_line"]],
            ["PMIC soft-reset", v1313["pmic_soft_reset_line"]],
            ["TLMM GPIO135", v1313["tlmm_gpio135_line"]],
            ["TLMM GPIO142", v1313["tlmm_gpio142_line"]],
        ]),
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass", "detail"], [[item["name"], item["pass"], item["detail"]] for item in manifest["checks"]]),
        "",
        "## Classification",
        "",
        f"- Accepted prerequisite: `{analysis['accepted_prerequisite']}`",
        f"- Selected gate: `{analysis['selected_gate']}`",
        "- Rejected mutations:",
        *[f"  - `{item}`" for item in analysis["rejected_mutations"]],
        "- Target event groups:",
        *[f"  - `{item}`" for item in analysis["target_event_groups"]],
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], [[key, manifest[key]] for key in (
            "device_commands_executed",
            "device_mutations",
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
        )]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
