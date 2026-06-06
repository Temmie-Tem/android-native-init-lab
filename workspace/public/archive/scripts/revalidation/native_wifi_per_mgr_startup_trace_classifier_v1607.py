#!/usr/bin/env python3
"""V1607 host-only classifier for the V1606 per_mgr startup trace.

V1606 ran the V1604 rollbackable test boot and proved that the PPH modem-fd
gate is closed, but /vendor/bin/pm-service exits cleanly in roughly one sample
window before opening /dev/subsys_modem, /dev/subsys_esoc0, binder nodes, or
service-manager sockets.  This classifier reads that evidence and selects the
next source-only gate.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1607-per-mgr-startup-trace-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1607_PER_MGR_STARTUP_TRACE_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1607-per-mgr-startup-trace-classifier.txt")

V1606_DIR = Path("tmp/wifi/v1606-per-mgr-startup-trace-handoff")
V1606_MANIFEST = V1606_DIR / "manifest.json"
V1606_HELPER = V1606_DIR / "test-v1393-helper-result.stdout.txt"
V1606_DMESG = V1606_DIR / "test-v1393-dmesg.stdout.txt"
V1606_SUMMARY = V1606_DIR / "summary.md"
V1606_REPORT = Path("docs/reports/NATIVE_INIT_V1606_PER_MGR_STARTUP_TRACE_HANDOFF_2026-06-02.md")
HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")

KV_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.:-]+)=(?P<value>.*)$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path, limit: int = 24 * 1024 * 1024) -> str:
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


def parse_kv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KV_RE.match(raw_line.strip())
        if match:
            values[match.group("key")] = match.group("value").strip()
    return values


def int_value(value: Any, default: int = -1) -> int:
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "pass"}


def count_lines(text: str, *needles: str) -> int:
    return sum(1 for line in text.splitlines() if all(needle in line for needle in needles))


def sample_fields(kv: dict[str, str], sample: int) -> dict[str, Any]:
    prefix = f"android_wifi_service_window.per_mgr_startup_trace.sample.{sample:02d}."
    return {
        "elapsed_ms": int_value(kv.get(prefix + "elapsed_ms")),
        "alive": int_value(kv.get(prefix + "alive")),
        "child_done": int_value(kv.get(prefix + "child_done")),
        "state": kv.get(prefix + "state", ""),
        "comm": kv.get(prefix + "comm", ""),
        "cmdline_seen": int_value(kv.get(prefix + "cmdline_seen")),
        "cmdline": kv.get(prefix + "cmdline", ""),
        "cwd_seen": int_value(kv.get(prefix + "cwd_seen")),
        "cwd": kv.get(prefix + "cwd", ""),
        "wchan_seen": int_value(kv.get(prefix + "wchan_seen")),
        "wchan": kv.get(prefix + "wchan", ""),
        "fd_subsys_modem": int_value(kv.get(prefix + "fd_subsys_modem")),
        "fd_subsys_esoc0": int_value(kv.get(prefix + "fd_subsys_esoc0")),
        "fd_vndbinder": int_value(kv.get(prefix + "fd_vndbinder")),
        "fd_hwbinder": int_value(kv.get(prefix + "fd_hwbinder")),
        "fd_binder": int_value(kv.get(prefix + "fd_binder")),
        "fd_socket": int_value(kv.get(prefix + "fd_socket")),
        "fd_dev_socket": int_value(kv.get(prefix + "fd_dev_socket")),
    }


def analyze() -> dict[str, Any]:
    manifest = read_json(V1606_MANIFEST)
    progress = manifest.get("wifi_progress") if isinstance(manifest.get("wifi_progress"), dict) else {}
    helper_text = read_text(V1606_HELPER)
    helper = parse_kv(helper_text)
    dmesg = read_text(V1606_DMESG)
    source = read_text(HELPER_SOURCE)

    samples = [sample_fields(helper, idx) for idx in range(0, 3)]
    current = {
        "v1606_decision": manifest.get("decision", ""),
        "v1606_pass": truthy(manifest.get("pass")),
        "handoff_pass": truthy(manifest.get("handoff_pass")),
        "rollback_ok": truthy((manifest.get("rollback") or {}).get("ok")),
        "progress_decision": progress.get("final_decision"),
        "provider_trigger": truthy(progress.get("provider_trigger")),
        "modem_trigger": truthy(progress.get("modem_trigger")),
        "rc1_progress": truthy(progress.get("rc1_progress")),
        "mhi_progress": truthy(progress.get("mhi_progress")),
        "wlfw_progress": truthy(progress.get("wlfw_progress")),
        "wlan0_present": truthy(progress.get("wlan0_present")),
        "mode": helper.get("android_wifi_service_window.mode", ""),
        "pph_gate_seen": int_value(helper.get("android_wifi_service_window.pph_modem_fd_gate_seen")),
        "pph_gate_first_seen_ms": int_value(
            helper.get("android_wifi_service_window.pph_modem_fd_gate_first_seen_ms")
        ),
        "pph_gate_final_count": int_value(helper.get("android_wifi_service_window.pph_modem_fd_gate_final_count")),
        "pm_proxy_helper_subsys_modem_fd_count": int_value(
            helper.get("android_wifi_service_window.pm_proxy_helper_subsys_modem_fd_count")
        ),
        "trace_enabled": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace")),
        "trace_sample_count": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.sample_count")
        ),
        "trace_alive_seen": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.alive_seen")),
        "trace_first_alive_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.first_alive_ms")
        ),
        "trace_last_alive_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.last_alive_ms")
        ),
        "trace_first_gone_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.first_gone_ms")
        ),
        "trace_first_child_done_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.first_child_done_ms")
        ),
        "trace_exit_code": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.exit_code")),
        "trace_signal": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.signal")),
        "trace_cmdline_seen": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.cmdline_seen")
        ),
        "trace_cwd_seen": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.cwd_seen")),
        "trace_wchan_seen": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.wchan_seen")),
        "trace_max_subsys_modem_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_modem_fd")
        ),
        "trace_max_subsys_esoc0_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_esoc0_fd")
        ),
        "trace_max_vndbinder_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_vndbinder_fd")
        ),
        "trace_max_hwbinder_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_hwbinder_fd")
        ),
        "trace_max_binder_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_binder_fd")
        ),
        "trace_max_socket_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_socket_fd")
        ),
        "trace_max_dev_socket_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_dev_socket_fd")
        ),
        "per_mgr_child_exit_code": int_value(helper.get("android_wifi_service_window.child.per_mgr.exit_code")),
        "pm_proxy_child_exit_code": int_value(helper.get("android_wifi_service_window.child.pm_proxy.exit_code")),
        "pm_full_contract_seen": int_value(helper.get("android_wifi_service_window.pm_full_contract_seen")),
        "subsys_esoc0_open_attempted": int_value(
            helper.get("android_wifi_service_window.subsys_esoc0_open_attempted")
        ),
        "final_result": helper.get("android_wifi_service_window.result", ""),
        "final_reason": helper.get("android_wifi_service_window.reason", ""),
        "sample_00": samples[0],
        "sample_01": samples[1],
        "sample_02": samples[2],
        "property_shim_request_count": int_value(
            helper.get("wifi_hal_composite_start.property_service_shim.request_count")
        ),
        "property_shim_sdx50m_offline": (
            helper.get("wifi_hal_composite_start.property_service_shim.request.2.name") == "vendor.peripheral.SDX50M.state"
            and helper.get("wifi_hal_composite_start.property_service_shim.request.2.value") == "OFFLINE"
        ),
        "property_shim_modem_offline": (
            helper.get("wifi_hal_composite_start.property_service_shim.request.3.name") == "vendor.peripheral.modem.state"
            and helper.get("wifi_hal_composite_start.property_service_shim.request.3.value") == "OFFLINE"
        ),
        "pm_service_vndservice_literal_seen": "vendor.qcom.PeripheralManager" in helper_text,
        "dmesg_pm_service_esoc0": count_lines(dmesg, "pm-service", "__subsystem_get: esoc0"),
        "dmesg_mdm_subsys_powerup": count_lines(dmesg, "mdm_subsys_powerup"),
        "dmesg_rc1": count_lines(dmesg, "PCIe RC1") + count_lines(dmesg, "LTSSM"),
        "helper_source_has_v298": "a90_android_execns_probe v298" in source,
        "helper_source_has_startup_trace": "per_mgr_startup_trace.sample_count" in source,
    }
    checks = {
        "v1606_handoff_and_rollback_ok": current["handoff_pass"] and current["rollback_ok"],
        "startup_trace_enabled_and_sampled": current["trace_enabled"] == 1 and current["trace_sample_count"] >= 3,
        "per_mgr_alive_only_briefly": current["trace_alive_seen"] == 1
        and current["trace_last_alive_ms"] <= 25
        and current["trace_first_child_done_ms"] <= 25
        and current["trace_first_gone_ms"] <= 45,
        "per_mgr_exited_cleanly": current["trace_exit_code"] == 0 and current["trace_signal"] == 0,
        "per_mgr_opened_no_contract_fds": current["trace_max_subsys_modem_fd"] == 0
        and current["trace_max_subsys_esoc0_fd"] == 0
        and current["trace_max_vndbinder_fd"] == 0
        and current["trace_max_hwbinder_fd"] == 0
        and current["trace_max_binder_fd"] == 0
        and current["trace_max_socket_fd"] == 0
        and current["trace_max_dev_socket_fd"] == 0,
        "pph_gate_still_closed": current["pph_gate_seen"] == 1
        and current["pm_proxy_helper_subsys_modem_fd_count"] >= 1,
        "downstream_remains_absent": not current["provider_trigger"]
        and not current["rc1_progress"]
        and not current["mhi_progress"]
        and not current["wlfw_progress"]
        and not current["wlan0_present"],
        "source_supports_trace": current["helper_source_has_v298"] and current["helper_source_has_startup_trace"],
    }
    pass_result = all(checks.values())
    decision = (
        "v1607-per-mgr-exits-before-any-contract-fd"
        if pass_result
        else "v1607-per-mgr-startup-trace-incomplete-review"
    )
    reason = (
        "V1606 proves pm-service runs only briefly, exits 0 around 21ms, and never opens /dev/subsys_modem, /dev/subsys_esoc0, binder nodes, sockets, or /dev/socket; the next gate should classify the pm-service pre-main/startup exit cause rather than retry lower eSoC/RC1"
        if pass_result
        else "V1606 evidence does not fully prove the pm-service clean pre-contract exit boundary"
    )
    next_gate = {
        "recommended_cycle": "V1608",
        "type": "source/build-only pm-service early-exit cause tracer",
        "focus": "instrument pm-service startup before it exits, preferably with bounded ptrace/exit or uprobe/openat/exit tracing around only /vendor/bin/pm-service",
        "success_markers": [
            "captures the syscall or library branch that leads to exit(0)",
            "records whether pm-service checks properties, init/service state, vndservicemanager, binder nodes, or peripheral state before exit",
            "does not ptrace mdm_helper or any long-running eSoC path",
            "preserves the PPH gate and startup trace guardrails",
            "still avoids Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, global PCI rescan, and platform bind/unbind",
        ],
    }
    return {
        "decision": decision,
        "pass": pass_result,
        "reason": reason,
        "checks": checks,
        "v1606": current,
        "next_gate": next_gate,
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    current = analysis["v1606"]
    next_gate = analysis["next_gate"]
    return "\n".join([
        "# Native Init V1607 per_mgr Startup Trace Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1607`",
        "- Type: host-only classifier over V1606 live evidence",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Inputs",
        "",
        markdown_table(
            ["input", "path"],
            [
                ["v1606_manifest", rel(V1606_MANIFEST)],
                ["v1606_helper_result", rel(V1606_HELPER)],
                ["v1606_dmesg", rel(V1606_DMESG)],
                ["v1606_summary", rel(V1606_SUMMARY)],
                ["v1606_report", rel(V1606_REPORT)],
                ["helper_source", rel(HELPER_SOURCE)],
            ],
        ),
        "",
        "## Derived Checks",
        "",
        markdown_table(["check", "value"], [[key, value] for key, value in analysis["checks"].items()]),
        "",
        "## Startup Trace Summary",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["mode", current["mode"]],
                ["pph_gate_seen", current["pph_gate_seen"]],
                ["pph_gate_first_seen_ms", current["pph_gate_first_seen_ms"]],
                ["pm_proxy_helper_subsys_modem_fd_count", current["pm_proxy_helper_subsys_modem_fd_count"]],
                ["sample_count", current["trace_sample_count"]],
                ["alive_seen", current["trace_alive_seen"]],
                ["first_alive_ms", current["trace_first_alive_ms"]],
                ["last_alive_ms", current["trace_last_alive_ms"]],
                ["first_child_done_ms", current["trace_first_child_done_ms"]],
                ["first_gone_ms", current["trace_first_gone_ms"]],
                ["exit_code", current["trace_exit_code"]],
                ["signal", current["trace_signal"]],
                ["max_subsys_modem_fd", current["trace_max_subsys_modem_fd"]],
                ["max_subsys_esoc0_fd", current["trace_max_subsys_esoc0_fd"]],
                ["max_vndbinder_fd", current["trace_max_vndbinder_fd"]],
                ["max_hwbinder_fd", current["trace_max_hwbinder_fd"]],
                ["max_binder_fd", current["trace_max_binder_fd"]],
                ["max_socket_fd", current["trace_max_socket_fd"]],
                ["max_dev_socket_fd", current["trace_max_dev_socket_fd"]],
            ],
        ),
        "",
        "## First Samples",
        "",
        markdown_table(
            ["sample", "elapsed", "alive", "done", "state", "cmdline", "cwd", "wchan", "fds"],
            [
                [
                    "00",
                    current["sample_00"]["elapsed_ms"],
                    current["sample_00"]["alive"],
                    current["sample_00"]["child_done"],
                    current["sample_00"]["state"],
                    current["sample_00"]["cmdline"],
                    current["sample_00"]["cwd"],
                    current["sample_00"]["wchan"],
                    f"modem={current['sample_00']['fd_subsys_modem']} esoc0={current['sample_00']['fd_subsys_esoc0']} vndbinder={current['sample_00']['fd_vndbinder']}",
                ],
                [
                    "01",
                    current["sample_01"]["elapsed_ms"],
                    current["sample_01"]["alive"],
                    current["sample_01"]["child_done"],
                    current["sample_01"]["state"],
                    current["sample_01"]["cmdline"],
                    current["sample_01"]["cwd"],
                    current["sample_01"]["wchan"],
                    f"modem={current['sample_01']['fd_subsys_modem']} esoc0={current['sample_01']['fd_subsys_esoc0']} vndbinder={current['sample_01']['fd_vndbinder']}",
                ],
                [
                    "02",
                    current["sample_02"]["elapsed_ms"],
                    current["sample_02"]["alive"],
                    current["sample_02"]["child_done"],
                    current["sample_02"]["state"],
                    current["sample_02"]["cmdline"],
                    current["sample_02"]["cwd"],
                    current["sample_02"]["wchan"],
                    f"modem={current['sample_02']['fd_subsys_modem']} esoc0={current['sample_02']['fd_subsys_esoc0']} vndbinder={current['sample_02']['fd_vndbinder']}",
                ],
            ],
        ),
        "",
        "## Interpretation",
        "",
        "`pm-service` is not failing after it talks to the PM provider contract.  It exits before any observed contract fd is opened: no `/dev/subsys_modem`, `/dev/subsys_esoc0`, binder node, socket, or `/dev/socket` fd is seen.  The first sample sees `/vendor/bin/pm-service` with cwd under the private root and `wait_on_page_bit_killable`; the next sample is already a zombie and the child is reaped by ~21ms.",
        "",
        "Therefore the active blocker is a pre-contract startup/branch exit inside `pm-service`, not the lower SDX50M/eSoC/RC1 path.  Lower RC1/MHI/WLFW work should remain parked until this process stays alive long enough to register or open the expected PM surfaces.",
        "",
        "## Next Gate",
        "",
        f"- Recommended cycle: `{next_gate['recommended_cycle']}`",
        f"- Type: {next_gate['type']}",
        f"- Focus: {next_gate['focus']}",
        "",
        "### Success Markers",
        "",
        *[f"- {item}" for item in next_gate["success_markers"]],
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = analyze()
    manifest = {
        "cycle": "V1607",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "host": collect_host_metadata(),
        "input_paths": {
            "v1606_manifest": rel(V1606_MANIFEST),
            "v1606_helper_result": rel(V1606_HELPER),
            "v1606_dmesg": rel(V1606_DMESG),
            "v1606_summary": rel(V1606_SUMMARY),
            "v1606_report": rel(V1606_REPORT),
            "helper_source": rel(HELPER_SOURCE),
        },
        "analysis": analysis,
        "out_dir": rel(store.run_dir),
        "device_commands_executed": False,
        "device_mutations": False,
    }
    store.write_json("manifest.json", manifest)
    report = render_report(manifest)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    write_private_text(repo_path(LATEST_POINTER), rel(store.run_dir) + "\n")
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
