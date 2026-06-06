#!/usr/bin/env python3
"""V1985 Android RIL/QMI producer capture, fast-poll retry.

This is the corrected one-shot producer measurement requested after the
2026-06-04 methods ledger: a rollbackable Android handoff that observes only
the internal-modem producer side with strace, unfiltered dmesg/logcat, and
QRTR nameservice lookup/readback.  It fixes the V1970 miss where fractional
`sleep 0.020` fell back to one-second polling on Android shell, so strace
attached after `wlan_pd` UP.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import android_ril_qmi_producer_capture_handoff_v1970 as base
import android_ril_qmi_producer_decode_v1971 as decoder
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


CYCLE = "V1985"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1985-android-ril-qmi-producer-fastpoll-handoff")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1985_ANDROID_RIL_QMI_PRODUCER_FASTPOLL_2026-06-04.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1985-android-ril-qmi-producer-fastpoll.txt")
MODULE_NAME = "a90_v1985_ril_qmi_fastpoll"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1985-ril-qmi-fastpoll"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v1985_ril_qmi_fastpoll"

ORIGINAL_POST_FS_DATA_SCRIPT = base.post_fs_data_script
ORIGINAL_ANALYZE = base.analyze_pulled_evidence
ORIGINAL_EVIDENCE_BASE = base.evidence_base

WLAN0_TIME_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\].*\bwlan0\b", re.IGNORECASE)
WLANMDSP_RE = re.compile(r"wlanmdsp(?:\.mbn)?", re.IGNORECASE)
ATTACH_EVENT_RE = re.compile(r"A90_V(?:1970|1985)_EVENT uptime=([0-9.]+) attached label=(\S+)")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def display_path(value: str) -> str:
    path = Path(value)
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return value


def patch_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"post-fs-data patch anchor not found: {old[:120]!r}")
    return text.replace(old, new, 1)


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1985 RIL QMI producer fast-poll observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only RIL/CNSS/PM QMI producer fast-poll capture. Remove after capture.",
            "",
        ]
    )


def post_fs_data_script(samples: int, delay_us: int) -> str:
    text = ORIGINAL_POST_FS_DATA_SCRIPT(samples, delay_us)
    text = text.replace("A90_V1970", "A90_V1985")
    text = text.replace("A90_V1521_STATUS", "A90_V1521_STATUS")
    text = text.replace("a90-v1970-ril-qmi-producer", "a90-v1985-ril-qmi-fastpoll")
    text = text.replace("a90_v1970_ril_qmi", "a90_v1985_ril_qmi_fastpoll")
    text = patch_once(
        text,
        "FAST_DELAY_SEC=0.020\n",
        f"FAST_DELAY_SEC=0.020\nFAST_DELAY_US=20000\nDELAY_US={delay_us}\n",
    )
    text = patch_once(
        text,
        "policy_allow_pid() {\n",
        """sleep_observer_delay() {
  if command -v usleep >/dev/null 2>&1; then
    usleep "$DELAY_US" 2>/dev/null || sleep 1
  else
    sleep "$DELAY_SEC" 2>/dev/null || sleep 1
  fi
}

sleep_fast_poll() {
  if command -v usleep >/dev/null 2>&1; then
    usleep "$FAST_DELAY_US" 2>/dev/null || sleep 1
  else
    sleep "$FAST_DELAY_SEC" 2>/dev/null || sleep 1
  fi
}

policy_allow_pid() {
""",
    )
    text = patch_once(
        text,
        """  if all_required_attached; then
    sleep "$DELAY_SEC" 2>/dev/null || sleep 1
  else
    sleep "$FAST_DELAY_SEC" 2>/dev/null || sleep 1
  fi
""",
        """  if all_required_attached; then
    sleep_observer_delay
  else
    sleep_fast_poll
  fi
""",
    )
    return text


def evidence_base(store: EvidenceStore) -> Path:
    root = base.v1521.pulled_evidence_dir(store)
    candidate = root / "a90-v1985-ril-qmi-fastpoll"
    return candidate if candidate.is_dir() else ORIGINAL_EVIDENCE_BASE(store)


def parse_attach_times(events: str) -> dict[str, float]:
    attach_times: dict[str, float] = {}
    for line in events.splitlines():
        match = ATTACH_EVENT_RE.search(line)
        if match:
            attach_times[match.group(2)] = float(match.group(1))
    return attach_times


def first_time(text: str, pattern: re.Pattern[str]) -> float | None:
    for line in text.splitlines():
        match = pattern.search(line)
        if not match:
            continue
        if "ts" in match.groupdict():
            return float(match.group("ts"))
        prefix = re.match(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]", line.strip())
        if prefix:
            return float(prefix.group(1))
    return None


def count_before(text: str, pattern: re.Pattern[str], before_time: float | None) -> int:
    count = 0
    for line in text.splitlines():
        prefix = re.match(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]", line.strip())
        line_time = float(prefix.group(1)) if prefix else None
        if before_time is not None and line_time is not None and line_time >= before_time:
            continue
        if pattern.search(line):
            count += 1
    return count


def summarize_qmi_decode(evidence_dir: Path, wlan_pd_time: float | None, attach_times: dict[str, float]) -> dict[str, Any]:
    qrtr = decoder.parse_qrtr_services(evidence_dir)
    messages = decoder.parse_straces(evidence_dir, qrtr["port_to_service"])
    summary = decoder.summarize_messages(messages)
    rild = [message for message in messages if message.process == "rild"]
    rild_dms = sorted({f"0x{message.msg_id:04x}" for message in rild if message.service == 2 and message.msg_id is not None})
    rild_nas = sorted({f"0x{message.msg_id:04x}" for message in rild if message.service == 3 and message.msg_id is not None})
    rild_wds = sorted({f"0x{message.msg_id:04x}" for message in rild if message.service == 1 and message.msg_id is not None})
    preup = [
        message
        for message in rild
        if wlan_pd_time is not None
        and attach_times.get("rild") is not None
        and attach_times["rild"] <= wlan_pd_time
        and message.service in {1, 2, 3}
    ]
    return {
        "decoded_message_count": len(messages),
        "decoded_rild_message_count": len(rild),
        "rild_dms_msg_ids": rild_dms,
        "rild_nas_msg_ids": rild_nas,
        "rild_wds_msg_ids": rild_wds,
        "rild_dms_nas_present": bool(rild_dms and rild_nas),
        "rild_wds_present": bool(rild_wds),
        "rild_attached_before_wlanpd": bool(
            wlan_pd_time is not None and attach_times.get("rild") is not None and attach_times["rild"] <= wlan_pd_time
        ),
        "producer_window_decoded_rild_lead_count": len(preup),
        "service_counts": summary.get("service_counts") or {},
        "message_counts": summary.get("message_counts") or {},
    }


def analyze_pulled_evidence(store: EvidenceStore) -> dict[str, Any]:
    analysis = ORIGINAL_ANALYZE(store)
    evidence_dir = base.evidence_base(store)
    dmesg_full = base.read_file(evidence_dir / "dmesg-full-final.txt", limit=20_000_000)
    dmesg_live = base.read_file(evidence_dir / "dmesg-live.txt", limit=4_000_000)
    logcat_dump = base.read_file(evidence_dir / "logcat-dump-final.txt", limit=20_000_000)
    events = base.read_file(evidence_dir / "events.log", limit=2_000_000)
    combined_dmesg = "\n".join(part for part in (dmesg_full, dmesg_live) if part)
    wlan_pd_time = first_time(combined_dmesg, base.WLAN_PD_UP_RE)
    wlan0_time = first_time(combined_dmesg, WLAN0_TIME_RE)
    pcie_mhi_before_wlan0 = count_before(combined_dmesg, base.PCIE_MHI_RE, wlan0_time)
    attach_times = analysis.get("attach_times") or {}
    analysis["v1985_gate"] = {
        "wlan_pd_up_time": wlan_pd_time,
        "wlan0_time": wlan0_time,
        "pcie_mhi_before_wlan0": pcie_mhi_before_wlan0,
        "degraded_257s_like": wlan0_time is not None and wlan0_time > 120.0,
        "wlanmdsp_logcat_lines": sum(1 for line in logcat_dump.splitlines() if WLANMDSP_RE.search(line)),
        "required_strace_attached_before_wlanpd": all(
            wlan_pd_time is not None
            and attach_times.get(label) is not None
            and attach_times[label] <= wlan_pd_time
            for label in ("rild", "cnss_daemon", "pm_service")
        ),
    }
    analysis["sample_count"] = events.count("A90_V1985_EVENT") or analysis.get("sample_count")
    try:
        analysis["v1985_qmi_decode"] = summarize_qmi_decode(evidence_dir, wlan_pd_time, attach_times)
    except Exception as exc:  # noqa: BLE001 - decoder failures should classify as evidence, not crash rollback reporting.
        analysis["v1985_qmi_decode"] = {"decode_error": repr(exc)}
    return analysis


def classify_result(
    base_decision: str,
    base_pass: bool,
    analysis: dict[str, Any],
    selftest_ok: bool,
) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return (
            "v1985-rollback-selftest-failed",
            False,
            "native rollback did not prove selftest fail=0",
            "rollback-selftest-failed",
        )
    if not base_pass:
        return (
            f"v1985-base-handoff-failed-{base_decision}",
            False,
            "underlying Android handoff did not complete cleanly",
            "base-handoff-failed",
        )
    gate = analysis.get("v1985_gate") or {}
    if gate.get("degraded_257s_like") or int(gate.get("pcie_mhi_before_wlan0") or 0) > 0:
        return (
            "v1985-reject-degraded-or-pre-wlan0-pcie-mhi",
            False,
            "capture rejected because it was degraded or included pre-wlan0 PCIe/MHI contamination",
            "reject-degraded-or-pre-wlan0-pcie-mhi",
        )
    if gate.get("wlan_pd_up_time") is None or gate.get("wlan0_time") is None:
        return (
            "v1985-normal-android-stateup-incomplete",
            False,
            "capture did not anchor both normal wlan_pd UP and wlan0",
            "normal-stateup-incomplete",
        )
    if not gate.get("required_strace_attached_before_wlanpd"):
        return (
            "v1985-strace-attached-after-wlanpd-up",
            False,
            "normal Android state-up completed, but one or more required straces attached after wlan_pd UP",
            "producer-window-missed",
        )
    strace = analysis.get("strace") or {}
    if not all((strace.get(label) or {}).get("present") for label in ("rild", "cnss_daemon", "pm_service")):
        return (
            "v1985-daemon-strace-incomplete",
            False,
            "one or more rild/cnss-daemon/pm-service strace files are absent",
            "daemon-strace-incomplete",
        )
    targeted = ((analysis.get("qrtr") or {}).get("targeted_service_events") or {})
    if not all(int(targeted.get(label) or 0) > 0 for label in ("wds", "dms", "nas")):
        return (
            "v1985-qrtr-dms-nas-wds-incomplete",
            False,
            "QRTR nameservice enumeration did not show all WDS/DMS/NAS targets",
            "qrtr-dms-nas-wds-incomplete",
        )
    decode = analysis.get("v1985_qmi_decode") or {}
    if decode.get("decode_error"):
        return (
            "v1985-offline-qmi-decode-failed",
            False,
            f"strace captured but offline QMI decode failed: {decode.get('decode_error')}",
            "offline-qmi-decode-failed",
        )
    if not decode.get("rild_dms_nas_present"):
        return (
            "v1985-ril-dms-nas-not-decoded",
            False,
            "producer-window strace captured, but offline decode did not show both RIL DMS and NAS traffic",
            "ril-dms-nas-not-decoded",
        )
    return (
        "v1985-ril-qmi-producer-fastpoll-captured-rollback-pass",
        True,
        "normal Android producer window captured with pre-wlan_pd rild/cnss-daemon/pm-service strace, WDS/DMS/NAS QRTR enumeration, offline RIL DMS/NAS decode, and native rollback selftest fail=0",
        "ril-qmi-producer-fastpoll-captured",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    gate = analysis.get("v1985_gate") or {}
    dmesg = analysis.get("dmesg") or {}
    strace = analysis.get("strace") or {}
    qrtr = analysis.get("qrtr") or {}
    decode = analysis.get("v1985_qmi_decode") or {}
    attach_times = analysis.get("attach_times") or {}
    strace_stats = {
        label: {
            key: value
            for key, value in (strace.get(label) or {}).items()
            if key in {"present", "lines", "send_lines", "recv_lines", "qipcrtr_lines"}
        }
        for label in ("rild", "cnss_daemon", "pm_service")
    }
    return "\n".join(
        [
            "# V1985 Android RIL/QMI Producer Fast-poll Handoff",
            "",
            "## Summary",
            "",
            f"- Cycle: `{CYCLE}`",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{display_path(manifest['out_dir'])}`",
            f"- Native rollback selftest fail=0: `{manifest['rollback_selftest_fail0']}`",
            f"- Base handoff: `{manifest['base_decision']}` / `{manifest['base_pass']}`",
            "",
            "## Producer Window",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["wlan_pd UP", gate.get("wlan_pd_up_time")],
                    ["wlan0", gate.get("wlan0_time")],
                    ["attach times", json.dumps(attach_times, sort_keys=True)],
                    ["required strace before wlan_pd", gate.get("required_strace_attached_before_wlanpd")],
                    ["pre-wlan0 PCIe/MHI", gate.get("pcie_mhi_before_wlan0")],
                    ["degraded 257s-like", gate.get("degraded_257s_like")],
                    ["wlanmdsp logcat lines", gate.get("wlanmdsp_logcat_lines")],
                    ["base normal window", dmesg.get("normal_android_window")],
                    ["base producer-window strace", dmesg.get("producer_window_strace")],
                ],
            ),
            "",
            "## Strace And QRTR",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["strace rild", json.dumps(strace_stats.get("rild") or {}, sort_keys=True)],
                    ["strace cnss-daemon", json.dumps(strace_stats.get("cnss_daemon") or {}, sort_keys=True)],
                    ["strace pm-service", json.dumps(strace_stats.get("pm_service") or {}, sort_keys=True)],
                    ["QRTR targeted events", json.dumps(qrtr.get("targeted_service_events") or {}, sort_keys=True)],
                    ["QRTR file count", qrtr.get("file_count")],
                ],
            ),
            "",
            "## Offline QMI Decode",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["decoded messages", decode.get("decoded_message_count")],
                    ["decoded RIL messages", decode.get("decoded_rild_message_count")],
                    ["RIL DMS msg IDs", json.dumps(decode.get("rild_dms_msg_ids") or [], sort_keys=True)],
                    ["RIL NAS msg IDs", json.dumps(decode.get("rild_nas_msg_ids") or [], sort_keys=True)],
                    ["RIL WDS msg IDs", json.dumps(decode.get("rild_wds_msg_ids") or [], sort_keys=True)],
                    ["RIL DMS+NAS present", decode.get("rild_dms_nas_present")],
                    ["producer-window decoded lead count", decode.get("producer_window_decoded_rild_lead_count")],
                    ["decode error", decode.get("decode_error")],
                ],
            ),
            "",
            "## Scope",
            "",
            "- Internal-modem producer measurement only; no external SDX50M/eSoC/PCIe/GDSC path is touched.",
            "- The only live additions are strace on `rild`, `cnss-daemon`, `pm-service`, unfiltered dmesg/logcat capture, and QRTR nameservice lookup/readback.",
            "- The V1970 polling bug is fixed by using `usleep 20000` before falling back to shell `sleep`.",
            "",
            "## Safety",
            "",
            "Rollbackable Android-handoff to native v724 only. No QMI payload replay, Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, sda29 remount-write, or partition write beyond the declared boot-image handoff/rollback.",
            "",
            "## Steps",
            "",
            markdown_table(
                ["step", "status", "rc", "duration", "file"],
                [
                    [
                        item["name"],
                        "skip" if item["skipped"] else ("ok" if item["ok"] else "fail"),
                        item["rc"],
                        f"{item['duration_sec']:.3f}s",
                        item["file"],
                    ]
                    for item in manifest["steps"]
                ],
            ),
            "",
        ]
    )


def configure_v1985() -> None:
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.LATEST_POINTER = LATEST_POINTER
    base.MODULE_NAME = MODULE_NAME
    base.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    base.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    base.REMOTE_STAGE_PREFIX = REMOTE_STAGE_PREFIX
    base.module_prop = module_prop
    base.post_fs_data_script = post_fs_data_script
    base.evidence_base = evidence_base
    base.parse_attach_times = parse_attach_times
    base.analyze_pulled_evidence = analyze_pulled_evidence


def main() -> int:
    configure_v1985()
    base.configure_v1521_engine()
    args = base.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    steps, context, base_decision, base_pass = base.v1521.execute_plan(args, store, execute=execute)
    selftest_ok = base.rollback_selftest_ok(store, steps) if execute else False
    if execute:
        analysis = context.get("analysis") or {}
        decision, pass_ok, reason, label = classify_result(base_decision, base_pass, analysis, selftest_ok)
    else:
        label = "plan-ready" if args.command == "plan" else "dryrun-ready"
        decision = (
            "v1985-android-ril-qmi-producer-fastpoll-plan-ready"
            if args.command == "plan"
            else "v1985-android-ril-qmi-producer-fastpoll-dryrun-ready"
        )
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android live capture"

    manifest = {
        "cycle": CYCLE,
        "generated_at": now_iso(),
        "command": args.command,
        "base_decision": base_decision,
        "base_pass": base_pass,
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": reason,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "steps": [asdict(step) for step in steps],
        "rollback_selftest_fail0": selftest_ok,
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "strace_attach_executed": execute,
        "qrtr_nameservice_lookup_executed": execute,
        "qmi_payload_replay_executed": False,
        "tracefs_uprobe_control_executed": False,
        "tracefs_kprobe_control_executed": False,
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
        "sda29_remount_write_executed": False,
        "flash_executed": execute,
        "boot_image_write_executed": execute,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    leaks = base.v1521.check_forbidden_output(manifest, summary)
    manifest["forbidden_output_env_hits"] = leaks
    if leaks:
        manifest["decision"] = "v1985-forbidden-output-hit"
        manifest["label"] = "forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "forbidden environment-backed output string detected"
        summary = render_summary(manifest)

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"label:    {manifest['label']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
