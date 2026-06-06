#!/usr/bin/env python3
"""V644 clean-DSP CNSS/WLFW readback replay.

This proof reuses the V598-class lower path under the V641 clean-DSP state:

    subsys_modem holder
      -> qrtr-ns, rmt_storage, tftp_server, pd-mapper, cnss_diag, cnss-daemon
      -> WLFW QRTR nameservice readback for service 69 instances 0/1

It does not write ADSP/CDSP/SLPI boot nodes, open esoc0, write boot_wlan or
qcwlanstate, start service-manager, start Wi-Fi HAL, scan/connect, use
credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

import native_wifi_modem_holder_wlfw_readback_v598 as v598


base = v598.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v644-clean-dsp-cnss-wlfw-readback")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "f811c18d1a9af92f5ca9fadcfd4dbd94593318240744a0c86d0419280bbea019"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v104"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v644-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v644 clean-DSP CNSS WLFW readback only; "
    "no DSP boot-node write, no service-manager, no Wi-Fi HAL start, "
    "no scan/connect/link-up and no external ping"
)

V641_PROOF_LOG = "/cache/native-init-sibling-fwssctl-v641.log"
EXPECTED_ORDER = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon"
REQUIRED_RPMSG = ("adsp.IPCRTR", "cdsp.IPCRTR", "dsps.IPCRTR")
V644_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("wlan_pd_ack_180", re.compile(r"service-notifier: send_ind_ack:.*msm/modem/wlan_pd.*instance 180", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("wlfw_start", re.compile(r"\bWLFW\b|wlfw", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|pm_qos_add_request|Reference count mismatch|subsystem_put", re.I)),
)

_orig_capture_preflight = base.capture_preflight
_orig_build_checks = base.build_checks
_orig_run_live = base.run_live
_orig_decide = base.decide
_orig_render_summary = base.render_summary


def proof_id() -> str:
    return "v644-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def capture_preflight(args: base.argparse.Namespace,
                      store: base.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    mount_preflight = _orig_capture_preflight(args, store, steps)
    base.run_step(args, store, steps, "v641-proof-log", ["run", args.toybox, "cat", V641_PROOF_LOG], 20.0)
    base.run_step(args, store, steps, "v641-timeline", ["timeline"], 20.0)
    base.run_step(args, store, steps, "rpmsg-current", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0)
    return mount_preflight


def _v641_clean_dsp_ready(steps: list[dict[str, Any]]) -> tuple[bool, str]:
    proof_log = base.step_payload(steps, "v641-proof-log")
    timeline = base.step_payload(steps, "v641-timeline")
    rpmsg = base.step_payload(steps, "rpmsg-current")
    log_clean = "complete failures=0 timeouts=0" in proof_log or "complete failures=0 timeouts=0" in timeline
    node_clean = all(f"{name} write rc=0" in proof_log for name in ("adsp", "cdsp", "slpi"))
    rpmsg_clean = all(name in rpmsg for name in REQUIRED_RPMSG)
    detail = (
        f"log_clean={log_clean} node_clean={node_clean} "
        f"rpmsg_clean={rpmsg_clean} required_rpmsg={','.join(REQUIRED_RPMSG)}"
    )
    return log_clean and node_clean and rpmsg_clean, detail


def _rename_check(check: base.Check) -> base.Check:
    name = "helper-v104-ready" if check.name == "helper-v100-ready" else check.name
    return base.Check(
        name,
        check.status,
        check.severity,
        check.detail.replace("V596", "V644").replace("V598", "V644").replace("helper v100", "helper v104"),
        check.evidence,
        check.next_step.replace("V596", "V644").replace("V598", "V644").replace("helper v100", "helper v104"),
    )


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = [_rename_check(check) for check in _orig_build_checks(args, steps, mount_preflight, v490, v525)]
    if args.command == "plan":
        return checks
    v641_ready, v641_detail = _v641_clean_dsp_ready(steps)
    base.add_check(
        checks,
        "v641-clean-dsp-state",
        "pass" if v641_ready else "blocked",
        "blocker",
        v641_detail,
        [V641_PROOF_LOG],
        "arm V641 one-shot proof and reboot before V644",
    )
    base.add_check(
        checks,
        "direct-dsp-boot-node-retry-blocked",
        "pass",
        "info",
        "V644 reuses V641 clean-DSP state and never writes ADSP/CDSP/SLPI boot nodes",
        [],
        "keep direct DSP boot-node writes blocked",
    )
    return checks


def v644_counts(text: str) -> dict[str, int]:
    return {
        name: len([line for line in text.splitlines() if pattern.search(line)])
        for name, pattern in V644_PATTERNS
    }


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    result = _orig_run_live(args, store, steps, mount_preflight)
    result["v644_counts"] = v644_counts(str(result.get("dmesg_delta") or ""))
    return result


def _observer_order(live: dict[str, Any]) -> str:
    keys = live.get("companion_keys") or {}
    return str(keys.get("wifi_companion_start.order") or "")


def _child_started(live: dict[str, Any]) -> int:
    keys = live.get("companion_keys") or {}
    try:
        return int(keys.get("wifi_companion_start.child_started") or 0)
    except ValueError:
        return 0


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v644-clean-dsp-cnss-wlfw-readback-plan-ready",
            True,
            "plan-only; no device command executed",
            "arm V641 clean-DSP state, refresh V401/V490, then run V644 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v644-preflight-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V644", False
    if args.command == "preflight":
        return (
            "v644-clean-dsp-cnss-wlfw-readback-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V644 live proof",
            False,
        )
    decision, pass_ok, reason, next_step, live_executed = _orig_decide(args, checks, live)
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed
    counts = live.get("v644_counts") or {}
    if not pass_ok and counts.get("kernel_warning", 0):
        if counts.get("service_notifier_74") or counts.get("service_notifier_180"):
            return (
                "v644-service-notifier-advanced-with-kernel-warning",
                False,
                f"service_notifier_180={counts.get('service_notifier_180', 0)} service_notifier_74={counts.get('service_notifier_74', 0)} kernel_warning={counts.get('kernel_warning', 0)}",
                "do not repeat live; classify post-service74 warning before HAL/qcwlanstate",
                live_executed,
            )
        return (
            "v644-kernel-warning",
            False,
            f"kernel_warning={counts.get('kernel_warning', 0)}",
            "do not repeat live; inspect dmesg",
            live_executed,
        )
    if not pass_ok:
        return decision, pass_ok, reason, next_step, live_executed
    if _observer_order(live) != EXPECTED_ORDER or _child_started(live) != 6:
        return (
            "v644-observer-contract-gap",
            False,
            f"unexpected order={_observer_order(live)} child_started={_child_started(live)}",
            "inspect helper v104 wifi-companion-start-only contract",
            live_executed,
        )
    readback = live.get("qrtr_readback") or {}
    if int(readback.get("qmi_attempted") or 0):
        return "v644-wlfw-readback-qmi-guard-failed", False, "unexpected QMI payload attempt", "stop and inspect helper", live_executed
    if counts.get("kernel_warning", 0):
        return "v644-kernel-warning", False, f"kernel_warning={counts.get('kernel_warning')}", "do not repeat; inspect dmesg", live_executed
    if counts.get("service_notifier_74") or counts.get("wlan_pd") or counts.get("qmi_server_connected") or counts.get("wlfw_start"):
        return (
            "v644-post-180-advanced",
            True,
            f"counts={counts} readback_events={readback.get('service_events')}",
            "plan bounded CNSS/HAL readiness gate; keep scan/connect blocked until wlan0 or FW-ready",
            live_executed,
        )
    if counts.get("service_notifier_180"):
        return (
            "v644-service180-only-clean-dsp",
            True,
            f"service_notifier_180={counts.get('service_notifier_180')} readback_end_of_list={readback.get('end_of_list')} mdm3={live.get('mdm3_after_companion')}",
            "classify clean-DSP service74/WLAN-PD publisher gap before HAL/qcwlanstate",
            live_executed,
        )
    return (
        "v644-cnss-no-service180-regression",
        True,
        f"service_notifier_180=0 counts={counts}",
        "compare helper v104/v100 and clean-DSP timing before retry",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest).replace(
        "# V598 Modem Holder WLFW QRTR Readback Proof",
        "# V644 Clean-DSP CNSS/WLFW Readback Proof",
        1,
    ).replace(
        "# V596 Modem Holder Companion Proof",
        "# V644 Clean-DSP CNSS/WLFW Readback Proof",
        1,
    )
    live = manifest.get("live") or {}
    return "\n".join([
        text,
        "",
        "## V644 Contract",
        "",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{_observer_order(live)}`",
        f"- child_started: `{_child_started(live)}`",
        f"- direct_dsp_boot_node_write: `False`",
        f"- service_manager_started: `False`",
        f"- wifi_hal_started: `{manifest.get('wifi_hal_start_executed')}`",
        f"- wifi_bringup_executed: `{manifest.get('wifi_bringup_executed')}`",
        "",
        "## V644 Marker Counts",
        "",
        base.markdown_table(
            ["marker", "count"],
            [[key, str(value)] for key, value in sorted((live.get("v644_counts") or {}).items())],
        ) if live.get("v644_counts") else "- none",
    ])


base.proof_id = proof_id
base.capture_preflight = capture_preflight
base.build_checks = build_checks
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
