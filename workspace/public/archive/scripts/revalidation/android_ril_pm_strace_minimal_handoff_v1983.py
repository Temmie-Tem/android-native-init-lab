#!/usr/bin/env python3
"""V1983 clean-baseline Android RIL/PM QRTR strace handoff.

This runner keeps the V1753 minimal Android-good firmware-request observer as
the behavioral baseline, then adds only early AF_QIPCRTR strace attachment for
`rild` and `pm-service`.  It deliberately leaves tracefs uprobes/kprobes and
the QRTR lookup matrix disabled until the clean baseline is preserved.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import android_wlan_pd_firmware_request_handoff_v1753 as v1753
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


CYCLE = "V1983"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1983-v1753-plus-ril-pm-strace-minimal")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1983_V1753_PLUS_RIL_PM_STRACE_MINIMAL_2026-06-04.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1983-v1753-plus-ril-pm-strace-minimal.txt")
MODULE_NAME = "a90_v1983_ril_pm_strace_min"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1983-ril-pm-strace-min"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v1983_ril_pm_strace_min"

ORIGINAL_ANALYZE = v1753.analyze_pulled_evidence
ORIGINAL_EVIDENCE_BASE = v1753.evidence_base
ORIGINAL_POST_FS_DATA_SCRIPT = v1753.post_fs_data_script

CONTAMINATION_RE = re.compile(
    r"__subsystem_get.*esoc0|PCIe RC1 link initialized|mhi .*enabling device|\bMHI\b|"
    r"pcie_initialized|mhi_enable|esoc0.*boot.*fail|boot_failed",
    re.IGNORECASE,
)
TS_RE = re.compile(r"\[\s*([0-9]+\.[0-9]+)\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def display_path(value: str) -> str:
    path = Path(value)
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return value


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1983 clean RIL PM strace observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only V1753 baseline plus rild/pm-service QRTR strace observer.",
            "",
        ]
    )


def post_fs_data_script(samples: int, delay_us: int) -> str:
    text = ORIGINAL_POST_FS_DATA_SCRIPT(samples, delay_us)
    text = text.replace("A90_V1753", "A90_V1983")
    text = text.replace("firmware_request_observer", "firmware_request_plus_ril_pm_strace_observer")
    attach_qrtr = r'''
attach_qrtr_once() {
  label="$1"
  pattern="$2"
  out="$OUT/$label.strace.txt"
  marker="$OUT/$label.attached"
  [ -e "$marker" ] && return 0
  pid="$(find_pid_by_cmd "$pattern" 2>/dev/null | head -n 1)"
  [ -n "$pid" ] || return 0
  snapshot_proc "$label" "$pid"
  if [ -x "$STRACE" ]; then
    "$STRACE" -f -tt -s 9999 -xx -e trace=sendmsg,recvmsg,sendto,recvfrom -p "$pid" -o "$out" >> "$OUT/strace-launch.log" 2>&1 &
    spid=$!
    echo "$label $pid $spid" >> "$PIDS"
    echo "attached label=$label pid=$pid strace_pid=$spid mode=qrtr-only" > "$marker"
  else
    echo "missing strace binary $STRACE" >> "$OUT/strace-launch.log"
    echo "missing" > "$marker"
  fi
}

'''
    text = text.replace("finish_strace() {", attach_qrtr + "finish_strace() {", 1)
    text = text.replace(
        "    attach_once cnss_daemon cnss-daemon\n",
        "    attach_once cnss_daemon cnss-daemon\n"
        "    attach_qrtr_once rild /vendor/bin/hw/rild\n"
        "    attach_qrtr_once pm_service /vendor/bin/pm-service\n",
        1,
    )
    text = text.replace(
        "    printf 'cnss_trace_lines='\n    grep -Ec '.' \"$OUT/cnss_daemon.strace.txt\" 2>/dev/null || echo 0\n",
        "    printf 'cnss_trace_lines='\n    grep -Ec '.' \"$OUT/cnss_daemon.strace.txt\" 2>/dev/null || echo 0\n"
        "    printf 'rild_trace_lines='\n    grep -Ec '.' \"$OUT/rild.strace.txt\" 2>/dev/null || echo 0\n"
        "    printf 'pm_service_trace_lines='\n    grep -Ec '.' \"$OUT/pm_service.strace.txt\" 2>/dev/null || echo 0\n",
        1,
    )
    return text


def _line_time(line: str) -> float | None:
    match = TS_RE.search(line)
    return float(match.group(1)) if match else None


def _count_before(lines: list[str], pattern: re.Pattern[str], before_time: float | None) -> int:
    count = 0
    for line in lines:
        line_time = _line_time(line)
        if before_time is not None and line_time is not None and line_time >= before_time:
            continue
        if pattern.search(line):
            count += 1
    return count


def _first_time(lines: list[str], pattern: str) -> float | None:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        if regex.search(line):
            return _line_time(line)
    return None


def evidence_base(store: EvidenceStore) -> Path:
    root = v1753.v1521.pulled_evidence_dir(store)
    candidate = root / "a90-v1983-ril-pm-strace-min"
    return candidate if candidate.is_dir() else ORIGINAL_EVIDENCE_BASE(store)


def summarize_strace_file(path: Path) -> dict[str, Any]:
    text = v1753.read_file(path, limit=12_000_000)
    lines = [line for line in text.splitlines() if line.strip()]
    return {
        "present": bool(text),
        "lines": len(lines),
        "sendto": sum("sendto(" in line for line in lines),
        "recvfrom": sum("recvfrom(" in line for line in lines),
        "sendmsg": sum("sendmsg(" in line for line in lines),
        "recvmsg": sum("recvmsg(" in line for line in lines),
        "hex_escaped_lines": sum("\\x" in line for line in lines),
        "sockaddr_qrtr_lines": sum(
            "AF_QIPCRTR" in line or "sq_node" in line or "sq_port" in line for line in lines
        ),
        "first_payload_line": next((line[:500] for line in lines if "\\x" in line), ""),
    }


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    analysis = ORIGINAL_ANALYZE(store)
    root = v1753.evidence_base(store)
    pulled_root = v1753.v1521.pulled_evidence_dir(store)
    dmesg_text = v1753.read_file(root / "dmesg-filtered.txt") + "\n" + v1753.read_file(
        pulled_root / "host-dmesg-filtered.txt"
    )
    logcat_text = v1753.read_file(root / "logcat-filtered.txt")
    dmesg_lines = dmesg_text.splitlines()
    combined_lines = (dmesg_text + "\n" + logcat_text).splitlines()
    wlan0_time = _first_time(combined_lines, r"\bwlan0\b")
    wlan_pd_time = _first_time(combined_lines, r"wlan_pd.*state indication|root_service_service_ind_cb.*wlan_pd")
    analysis["v1983_clean_gate"] = {
        "wlan_pd_time": wlan_pd_time,
        "wlan0_time": wlan0_time,
        "pcie_mhi_esoc_before_wlan0": _count_before(dmesg_lines, CONTAMINATION_RE, wlan0_time),
        "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
        "wlanmdsp_logcat_lines": sum("wlanmdsp" in line.lower() for line in logcat_text.splitlines()),
    }
    analysis["v1983_daemon_strace"] = {
        "rild": summarize_strace_file(root / "rild.strace.txt"),
        "pm_service": summarize_strace_file(root / "pm_service.strace.txt"),
        "cnss_daemon": summarize_strace_file(root / "cnss_daemon.strace.txt"),
    }
    return analysis


def classify_android(base_decision: str, base_pass: bool, context: dict[str, Any]) -> tuple[str, bool, str]:
    analysis = context.get("analysis") or {}
    files = analysis.get("files_present") or {}
    daemon_strace = analysis.get("v1983_daemon_strace") or {}
    evidence_pulled = bool(files.get("request_summary") or files.get("done") or (daemon_strace.get("rild") or {}).get("present"))
    if not base_pass and not (
        base_decision == "v1521-handoff-sampler-files-missing-rollback-pass" and evidence_pulled
    ):
        return (
            f"v1983-base-handoff-failed-{base_decision}",
            False,
            "underlying rollbackable Android handoff did not complete",
        )
    clean_gate = analysis.get("v1983_clean_gate") or {}
    if clean_gate.get("degraded_257s_like") or int(clean_gate.get("pcie_mhi_esoc_before_wlan0") or 0) > 0:
        return (
            "v1983-minimal-ril-pm-strace-rejected-pcie-mhi-contaminated",
            False,
            "minimal RIL/PM strace capture was rejected because pre-wlan0 external RC1/MHI/eSoC contamination appeared",
        )
    if str(analysis.get("requested_wlanmdsp")) != "1" and str(analysis.get("requested_pd_image")) != "1":
        return (
            "v1983-minimal-ril-pm-strace-no-wlanmdsp-request",
            False,
            "capture stayed clean but did not preserve Android-good wlanmdsp request evidence",
        )
    missing = [
        name
        for name in ("rild", "pm_service")
        if not (daemon_strace.get(name) or {}).get("present")
        or int((daemon_strace.get(name) or {}).get("hex_escaped_lines") or 0) <= 0
    ]
    if missing:
        return (
            "v1983-minimal-ril-pm-strace-incomplete",
            False,
            f"capture stayed clean but required QRTR strace payloads were missing for {','.join(missing)}",
        )
    return (
        "v1983-clean-ril-pm-strace-wlanmdsp-rollback-pass",
        True,
        "clean Android-good baseline preserved while rild and pm-service AF_QIPCRTR payload strace was captured",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    clean_gate = analysis.get("v1983_clean_gate") or {}
    daemon_strace = analysis.get("v1983_daemon_strace") or {}
    request_summary = analysis.get("request_summary") or {}
    return "\n".join(
        [
            "# Native Init V1983 V1753 Plus RIL PM Strace Minimal",
            "",
            "## Summary",
            "",
            f"- Cycle: `{CYCLE}`",
            f"- Decision: `{manifest['decision']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{display_path(manifest['out_dir'])}`",
            f"- Base handoff: `{manifest['base_decision']}` / `{manifest['base_pass']}`",
            "",
            "## Clean Baseline Gate",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["wlan_pd", clean_gate.get("wlan_pd_time")],
                    ["wlan0", clean_gate.get("wlan0_time")],
                    ["pre-wlan0 external RC1/MHI/eSoC", clean_gate.get("pcie_mhi_esoc_before_wlan0")],
                    ["degraded 257s-like", clean_gate.get("degraded_257s_like")],
                    ["requested_wlanmdsp", analysis.get("requested_wlanmdsp")],
                    ["requested_pd_image", analysis.get("requested_pd_image")],
                    ["wlanmdsp logcat lines", clean_gate.get("wlanmdsp_logcat_lines")],
                    ["request_summary", json.dumps(request_summary, sort_keys=True)],
                ],
            ),
            "",
            "## Daemon Strace",
            "",
            markdown_table(
                ["daemon", "lines", "sendto", "recvfrom", "sendmsg", "recvmsg", "hex payload"],
                [
                    [
                        name,
                        (daemon_strace.get(name) or {}).get("lines"),
                        (daemon_strace.get(name) or {}).get("sendto"),
                        (daemon_strace.get(name) or {}).get("recvfrom"),
                        (daemon_strace.get(name) or {}).get("sendmsg"),
                        (daemon_strace.get(name) or {}).get("recvmsg"),
                        (daemon_strace.get(name) or {}).get("hex_escaped_lines"),
                    ]
                    for name in ("rild", "pm_service", "cnss_daemon")
                ],
            ),
            "",
            "## Scope",
            "",
            "- Built directly on the clean V1753 firmware-request baseline.",
            "- Adds only early `rild` and `pm-service` AF_QIPCRTR strace; tracefs uprobes/kprobes and QRTR lookup matrix remain disabled.",
            "- The result is producer observability only, not native Wi-Fi bring-up.",
            "",
            "## Safety",
            "",
            "Rollbackable Android-handoff to native v724 only. No QMI payload replay, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or partition write beyond declared boot-image handoff/rollback.",
            "",
        ]
    )


def configure_v1983() -> None:
    v1753.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1753.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    v1753.LATEST_POINTER = LATEST_POINTER
    v1753.MODULE_NAME = MODULE_NAME
    v1753.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    v1753.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    v1753.REMOTE_STAGE_PREFIX = REMOTE_STAGE_PREFIX
    v1753.module_prop = module_prop
    v1753.post_fs_data_script = post_fs_data_script
    v1753.evidence_base = evidence_base
    v1753.analyze_pulled_evidence = analyze_pulled_evidence


def main() -> int:
    configure_v1983()
    v1753.configure_v1521_engine()
    args = v1753.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, base_pass = v1753.v1521.execute_plan(args, store, execute=execute)
    if execute:
        decision, pass_ok, reason = classify_android(base_decision, base_pass, context)
    else:
        decision = (
            "v1983-minimal-ril-pm-strace-plan-ready"
            if args.command == "plan"
            else "v1983-minimal-ril-pm-strace-dryrun-ready"
        )
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
    manifest = {
        "cycle": CYCLE,
        "generated_at": now_iso(),
        "command": args.command,
        "base_decision": base_decision,
        "base_pass": base_pass,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "strace_attach_executed": execute,
        "tracefs_uprobe_control_executed": False,
        "tracefs_kprobe_control_executed": False,
        "qrtr_nameservice_lookup_executed": False,
        "qmi_payload_replay_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "pmic_gpio_gdsc_regulator_write_executed": False,
        "forced_rc1_case_write_executed": False,
        "subsys_esoc0_open_executed": False,
        "fake_online_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": execute,
        "boot_image_write_executed": execute,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
