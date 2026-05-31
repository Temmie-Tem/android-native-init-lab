#!/usr/bin/env python3
"""V1292 host/source plan for the dynamic PCIe/GDSC/eSoC sequence gap.

V1291 closed static TLMM GPIO135/GPIO142 and PMIC9 shape as the shortest
blocker. This classifier decides the next implementation gate from current
evidence and source: the existing V1290 sampler is correct but 1s-granularity,
while Android-positive PCIe RC1 appears within the first sub-second window after
`/dev/subsys_esoc0`.

No device command is executed here.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1292-dynamic-sequence-plan")
LATEST_POINTER = Path("tmp/wifi/latest-v1292-dynamic-sequence-plan.txt")
DEFAULT_V1291_MANIFEST = Path("tmp/wifi/v1291-static-gpio-parity-classifier/manifest.json")
DEFAULT_V1290_MANIFEST = Path("tmp/wifi/v1290-tlmm-pcie-sampler-live/manifest.json")
DEFAULT_V1244_MANIFEST = Path("tmp/wifi/v1244-android-power-surface-classifier/manifest.json")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_MHI_SOURCE = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/bus/mhi/controllers/mhi_arch_qcom.c")
DEFAULT_TRACE_SOURCES = [
    Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/trace/events/regulator.h"),
    Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/trace/events/gpio.h"),
    Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/trace/events/irq.h"),
    Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/trace/events/clk.h"),
    Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/trace/events/power.h"),
    Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/trace/events/trace_msm_pil_event.h"),
]
DEFAULT_V776_MANIFEST = Path("tmp/wifi/v776-tracepoint-inventory/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1291-manifest", type=Path, default=DEFAULT_V1291_MANIFEST)
    parser.add_argument("--v1290-manifest", type=Path, default=DEFAULT_V1290_MANIFEST)
    parser.add_argument("--v1244-manifest", type=Path, default=DEFAULT_V1244_MANIFEST)
    parser.add_argument("--v776-manifest", type=Path, default=DEFAULT_V776_MANIFEST)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("--mhi-source", type=Path, default=DEFAULT_MHI_SOURCE)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def first_seconds_value(text: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)s\b", text)
    if match:
        return float(match.group(1))
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    return float(match.group(1)) if match else None


def nested(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def source_line(text: str, pattern: str) -> int | None:
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def parse_native(v1290: dict[str, Any]) -> dict[str, Any]:
    sampler = v1290.get("response_sampler") or {}
    pm = v1290.get("pm_service_trigger_observer") or {}
    samples = sampler.get("samples") or []
    return {
        "decision": v1290.get("decision", ""),
        "pass": bool_value(v1290.get("pass")),
        "pm_service_actor_esoc0_attempt": bool_value(pm.get("pm_service_actor_esoc0_attempt")),
        "sample_count": int_value(sampler.get("sample_count"), len(samples)),
        "sample_interval_ms": int_value(sampler.get("sample_interval_ms"), -1),
        "max_mdm_status_count_total": int_value(sampler.get("max_mdm_status_count_total")),
        "max_pci_dev_count": int_value(sampler.get("max_pci_dev_count")),
        "max_mhi_bus_count": int_value(sampler.get("max_mhi_bus_count")),
        "mhi_pipe_seen": bool_value(sampler.get("mhi_pipe_seen")),
        "wlan0_seen": bool_value(sampler.get("wlan0_seen")),
        "max_kmsg_pcie_count": int_value(sampler.get("max_kmsg_pcie_count")),
        "max_kmsg_mhi_count": int_value(sampler.get("max_kmsg_mhi_count")),
        "max_kmsg_wlfw_count": int_value(sampler.get("max_kmsg_wlfw_count")),
        "max_kmsg_sdx50m_count": int_value(sampler.get("max_kmsg_sdx50m_count")),
        "pcie1_gdsc_seen": bool_value(sampler.get("pcie1_gdsc_seen")),
        "pcie0_gdsc_seen": bool_value(sampler.get("pcie0_gdsc_seen")),
        "kmsg_sources": sampler.get("kmsg_sources") or [],
        "max_kmsg_filtered_count": int_value(sampler.get("max_kmsg_filtered_count")),
        "safety": {
            key: bool_value(v1290.get(key))
            for key in (
                "wifi_hal_start_executed",
                "scan_connect_executed",
                "credential_use_executed",
                "dhcp_route_executed",
                "external_ping_executed",
                "wifi_bringup_executed",
                "flash_executed",
                "partition_write_executed",
            )
        },
    }


def parse_android(v1244: dict[str, Any]) -> dict[str, Any]:
    android = v1244.get("android") or {}
    timeline = android.get("timeline") or {}
    subsys_time = nested(timeline, "subsys_esoc0_get", "time")
    pcie_time = first_seconds_value(str(android.get("pcie_rc1_report_line", "")))
    return {
        "decision": v1244.get("decision", ""),
        "pass": bool_value(v1244.get("pass")),
        "subsys_esoc0_time": subsys_time,
        "pcie_rc1_time": pcie_time,
        "pcie_delta_ms": int(round((pcie_time - float(subsys_time)) * 1000.0)) if pcie_time is not None and subsys_time is not None else None,
        "wlan_pd_present": bool_value(nested(timeline, "wlan_pd", "present")),
        "icnss_qmi_present": bool_value(nested(timeline, "icnss_qmi", "present")),
        "fw_ready_present": bool_value(nested(timeline, "fw_ready", "present")),
        "wlan0_present": bool_value(nested(timeline, "wlan0", "present")),
        "pcie_rc1_report_line": android.get("pcie_rc1_report_line", ""),
    }


def parse_source(args: argparse.Namespace) -> dict[str, Any]:
    helper = read_text(args.helper_source)
    mhi = read_text(args.mhi_source)
    trace_sources: dict[str, dict[str, Any]] = {}
    for path in DEFAULT_TRACE_SOURCES:
        text = read_text(path)
        trace_sources[str(path)] = {
            "exists": bool(text),
            "trace_event_count": text.count("TRACE_EVENT(") + text.count("DEFINE_EVENT("),
        }
    return {
        "helper_source": str(repo_path(args.helper_source)),
        "helper_source_present": bool(helper),
        "helper_version_line": source_line(helper, r"#define EXECNS_VERSION"),
        "helper_v270": "a90_android_execns_probe v270" in helper,
        "response_sampler_flag_line": source_line(helper, r"pm_observer_late_per_proxy_response_sampler"),
        "response_sampler_1s_literal_line": source_line(helper, r"response_sampler\.sample_interval_ms=1000"),
        "late_per_proxy_poll_interval_line": source_line(helper, r"late_per_proxy_poll_interval_ms\s*=\s*1000"),
        "late_per_proxy_poll_max_line": source_line(helper, r"late_per_proxy_poll_max\s*=\s*12"),
        "append_response_sample_line": source_line(helper, r"static int append_pm_esoc_response_sample"),
        "mhi_source": str(repo_path(args.mhi_source)),
        "mhi_source_present": bool(mhi),
        "mhi_esoc_power_on_line": source_line(mhi, r"mhi_arch_esoc_ops_power_on"),
        "mhi_pcie_resume_line": source_line(mhi, r"msm_pcie_pm_control\(MSM_PCIE_RESUME"),
        "mhi_pci_probe_line": source_line(mhi, r"mhi_pci_probe"),
        "mhi_esoc_hook_register_line": source_line(mhi, r"esoc_register_client_hook"),
        "trace_sources": trace_sources,
    }


def parse_v776(v776: dict[str, Any]) -> dict[str, Any]:
    proof = nested(v776, "analysis", "proof", default={})
    return {
        "decision": v776.get("decision", ""),
        "pass": bool_value(v776.get("pass")),
        "available_events_readable": bool_value(proof.get("available_events_readable")),
        "events_dir": bool_value(proof.get("events_dir")),
        "available_events_total": int_value(proof.get("available_events_total")),
        "mounted_after": proof.get("mounted_after"),
        "bpf_attach_executed": bool_value(v776.get("bpf_attach_executed")),
        "ftrace_control_write_executed": bool_value(v776.get("ftrace_control_write_executed")),
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1291_manifest = load_json(args.v1291_manifest)
    v1290 = parse_native(load_json(args.v1290_manifest))
    v1244 = parse_android(load_json(args.v1244_manifest))
    source = parse_source(args)
    v776 = parse_v776(load_json(args.v776_manifest))

    dynamic_gap_active = (
        v1290["pass"]
        and v1290["pm_service_actor_esoc0_attempt"]
        and v1290["max_mdm_status_count_total"] == 0
        and v1290["max_pci_dev_count"] == 0
        and v1290["max_mhi_bus_count"] == 0
        and not v1290["mhi_pipe_seen"]
        and not v1290["wlan0_seen"]
    )
    android_positive = (
        v1244["pass"]
        and v1244["wlan_pd_present"]
        and v1244["icnss_qmi_present"]
        and v1244["fw_ready_present"]
        and v1244["wlan0_present"]
        and v1244["pcie_delta_ms"] is not None
    )
    sampler_too_coarse_for_android_delta = (
        v1290["sample_interval_ms"] >= 1000
        and v1244["pcie_delta_ms"] is not None
        and v1244["pcie_delta_ms"] < v1290["sample_interval_ms"]
    )
    source_supports_dense_reuse = all(source.get(key) for key in (
        "helper_source_present",
        "response_sampler_1s_literal_line",
        "late_per_proxy_poll_interval_line",
        "append_response_sample_line",
    ))
    source_supports_mhi_pcie_model = all(source.get(key) for key in (
        "mhi_source_present",
        "mhi_esoc_power_on_line",
        "mhi_pcie_resume_line",
        "mhi_pci_probe_line",
        "mhi_esoc_hook_register_line",
    ))
    trace_source_available = all(item["exists"] and item["trace_event_count"] > 0 for item in source["trace_sources"].values())
    tracefs_feasible = (
        v776["pass"]
        and v776["available_events_readable"]
        and v776["events_dir"]
        and v776["available_events_total"] > 0
    )
    safety_clean = not any(v1290["safety"].values())
    v1291_closed_static = (
        bool_value(v1291_manifest.get("pass"))
        and v1291_manifest.get("decision") == "v1291-static-gpio-parity-dynamic-power-gap"
    )

    checks = [
        {
            "name": "v1291-static-shape-closed",
            "status": "pass" if v1291_closed_static else "blocked",
            "detail": f"decision={v1291_manifest.get('decision', '')}",
        },
        {
            "name": "v1290-dynamic-gap-active",
            "status": "pass" if dynamic_gap_active else "blocked",
            "detail": f"pm_esoc0={v1290['pm_service_actor_esoc0_attempt']} gpio142={v1290['max_mdm_status_count_total']} pci={v1290['max_pci_dev_count']} mhi={v1290['max_mhi_bus_count']} pipe={v1290['mhi_pipe_seen']} wlan0={v1290['wlan0_seen']}",
        },
        {
            "name": "android-positive-subsecond-reference",
            "status": "pass" if android_positive and sampler_too_coarse_for_android_delta else "blocked",
            "detail": f"pcie_delta_ms={v1244['pcie_delta_ms']} native_sample_interval_ms={v1290['sample_interval_ms']} line={v1244['pcie_rc1_report_line']}",
        },
        {
            "name": "helper-dense-sampler-reuse-possible",
            "status": "pass" if source_supports_dense_reuse else "blocked",
            "detail": f"append_sample_line={source['append_response_sample_line']} interval_line={source['late_per_proxy_poll_interval_line']} literal_line={source['response_sampler_1s_literal_line']}",
        },
        {
            "name": "mhi-esoc-pcie-source-model-present",
            "status": "pass" if source_supports_mhi_pcie_model else "blocked",
            "detail": f"power_on={source['mhi_esoc_power_on_line']} pcie_resume={source['mhi_pcie_resume_line']} mhi_probe={source['mhi_pci_probe_line']} hook={source['mhi_esoc_hook_register_line']}",
        },
        {
            "name": "tracepoint-fallback-source-present",
            "status": "pass" if trace_source_available and tracefs_feasible else "blocked",
            "detail": f"tracefs_events={v776['available_events_total']} trace_sources={source['trace_sources']}",
        },
        {
            "name": "safety-clean",
            "status": "pass" if safety_clean else "blocked",
            "detail": f"safety={v1290['safety']}",
        },
    ]
    pass_ok = all(check["status"] == "pass" for check in checks)
    decision = "v1292-dense-dynamic-response-sampler-selected" if pass_ok else "v1292-input-incomplete"
    reason = (
        "Static GPIO/PMIC shape is closed, but the current V1290 response sampler runs at 1000ms while Android-positive PCIe RC1 appears inside a sub-second window after subsys_esoc0. The next lowest-risk movement is a source/build-only dense sampler that reuses the existing no-write response sample function at 50ms cadence before considering PMIC/GPIO/eSoC mutations."
        if pass_ok else
        "one or more current evidence/source prerequisites are missing or contradictory"
    )
    next_step = (
        "V1293 should build helper v271 with an opt-in dense late-per_proxy response sampler: 50ms interval, 40 samples, no PMIC write, no GPIO request/hold, no direct eSoC ioctl, no Wi-Fi HAL/scan/connect"
        if pass_ok else
        "refresh V1290/V1291/V1244 evidence or source paths before implementing the dense sampler"
    )

    return {
        "cycle": "v1292",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1291_manifest": str(repo_path(args.v1291_manifest)),
            "v1290_manifest": str(repo_path(args.v1290_manifest)),
            "v1244_manifest": str(repo_path(args.v1244_manifest)),
            "v776_manifest": str(repo_path(args.v776_manifest)),
            "helper_source": str(repo_path(args.helper_source)),
            "mhi_source": str(repo_path(args.mhi_source)),
        },
        "v1290": v1290,
        "v1244": v1244,
        "source": source,
        "v776": v776,
        "dynamic_gap_active": dynamic_gap_active,
        "android_positive": android_positive,
        "sampler_too_coarse_for_android_delta": sampler_too_coarse_for_android_delta,
        "source_supports_dense_reuse": source_supports_dense_reuse,
        "source_supports_mhi_pcie_model": source_supports_mhi_pcie_model,
        "trace_source_available": trace_source_available,
        "tracefs_feasible": tracefs_feasible,
        "checks": checks,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
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
    v1290 = manifest["v1290"]
    v1244 = manifest["v1244"]
    source = manifest["source"]
    return "\n".join([
        "# V1292 Dynamic PCIe/GDSC/eSoC Sequence Plan",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail"], [[c["name"], c["status"], c["detail"]] for c in manifest["checks"]]),
        "",
        "## Timing Model",
        "",
        markdown_table(["field", "value"], [
            ["Android subsys_esoc0_get_s", v1244["subsys_esoc0_time"]],
            ["Android PCIe RC1_s", v1244["pcie_rc1_time"]],
            ["Android PCIe delta_ms", v1244["pcie_delta_ms"]],
            ["V1290 sample_interval_ms", v1290["sample_interval_ms"]],
            ["sampler_too_coarse_for_android_delta", manifest["sampler_too_coarse_for_android_delta"]],
        ]),
        "",
        "## Source Model",
        "",
        markdown_table(["field", "value"], [
            ["helper version v270", source["helper_v270"]],
            ["append_pm_esoc_response_sample", source["append_response_sample_line"]],
            ["current late_per_proxy interval line", source["late_per_proxy_poll_interval_line"]],
            ["current response sampler literal", source["response_sampler_1s_literal_line"]],
            ["mhi_arch_esoc_ops_power_on", source["mhi_esoc_power_on_line"]],
            ["msm_pcie_pm_control resume", source["mhi_pcie_resume_line"]],
            ["mhi_pci_probe", source["mhi_pci_probe_line"]],
            ["esoc_register_client_hook", source["mhi_esoc_hook_register_line"]],
        ]),
        "",
        "## Safety",
        "",
        "- host/source classifier; no device command or mutation executed",
        "- selected next build is observability-only and must remain opt-in",
        "- no PMIC write, userspace GPIO line request/hold, direct eSoC ioctl, new daemon/HAL expansion, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = analyze(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
