#!/usr/bin/env python3
"""V642 clean-DSP lower companion observer proof.

This proof assumes the V641 boot-window proof already brought ADSP/CDSP/SLPI
through the clean firmware-backed path. It verifies that state read-only, then
reuses the V596 firmware-mount plus `subsys_modem` holder path with the V619
Android-order no-CNSS companion mode:

    qrtr-ns -> pd-mapper -> rmt_storage -> tftp_server

It does not write ADSP/CDSP/SLPI boot nodes, write boot_wlan/qcwlanstate, start
CNSS, start service-manager, start Wi-Fi HAL, scan/connect, use credentials,
run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import native_wifi_modem_holder_companion_v596 as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v642-clean-dsp-lower-companion")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "f811c18d1a9af92f5ca9fadcfd4dbd94593318240744a0c86d0419280bbea019"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v104"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v642-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v642 clean-DSP lower companion observer only; "
    "no DSP boot-node write, no CNSS daemon, no service-manager, no Wi-Fi HAL start, "
    "no scan/connect/link-up and no external ping"
)

V641_PROOF_LOG = "/cache/native-init-sibling-fwssctl-v641.log"
EXPECTED_ORDER = "qrtr_ns,pd_mapper,rmt_storage,tftp_server"
REQUIRED_RPMSG = ("adsp.IPCRTR", "cdsp.IPCRTR", "dsps.IPCRTR")

_orig_capture_preflight = base.capture_preflight
_orig_build_checks = base.build_checks
_orig_render_summary = base.render_summary


def proof_id() -> str:
    return "v642-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = [
        "run", args.helper,
        "--system-root", "/mnt/system/system",
        "--vendor-block", "/dev/block/sda29",
        "--vendor-fstype", "ext4",
        "--mode", "wifi-companion-android-order-post-sysmon-observer-start-only",
        "--null-device-mode", "dev-null",
        "--vndk-apex-alias-mode", "v30-to-system-ext-v30",
        "--linkerconfig-mode", "minimal-vendor",
        "--android-selinux-context-mode", "service-defaults",
        "--timeout-sec", str(args.companion_runtime_sec),
        "--allow-wifi-companion-start-only",
    ]
    if base.approved(args):
        command.append("--allow-qrtr-ns-readback")
    return command


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
        check.detail.replace("V596", "V642").replace("helper v100", "helper v104"),
        check.evidence,
        check.next_step.replace("V596", "V642").replace("helper v100", "helper v104"),
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
        "rerun V641 armed proof or restore a clean-DSP v641 boot before V642",
    )
    base.add_check(
        checks,
        "direct-dsp-boot-node-retry-blocked",
        "pass",
        "info",
        "V642 uses existing V641 clean-DSP state and never writes ADSP/CDSP/SLPI boot nodes",
        [],
        "keep direct DSP boot-node writes blocked unless a later plan explicitly reopens them",
    )
    return checks


def _observer_order(live: dict[str, Any]) -> str:
    keys = live.get("companion_keys") or {}
    return str(keys.get("wifi_companion_start.order") or "")


def _child_started(live: dict[str, Any]) -> int:
    keys = live.get("companion_keys") or {}
    try:
        return int(keys.get("wifi_companion_start.child_started") or 0)
    except ValueError:
        return 0


def _qmi_attempted(live: dict[str, Any]) -> int:
    keys = live.get("companion_keys") or {}
    total = 0
    for key, value in keys.items():
        if not str(key).endswith(".qmi_attempted"):
            continue
        try:
            total += int(str(value), 0)
        except ValueError:
            total += 1
    return total


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v642-clean-dsp-lower-companion-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current-boot V490, deploy helper v104 if needed, then run V642 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v642-preflight-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V642", False
    if args.command == "preflight":
        return (
            "v642-clean-dsp-lower-companion-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V642 live observer",
            False,
        )
    if not base.approved(args):
        return (
            "v642-clean-dsp-lower-companion-approval-required",
            True,
            "exact approval phrase required; no live command executed",
            "rerun with exact V642 approval",
            False,
        )
    if not live:
        return "v642-review-required", False, "missing live result", "inspect runner failure", True

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v642-cleanup-review", False, f"reboot_cleanup={reboot}", "verify native recovery before continuing", True
    counts = (live.get("markers") or {}).get("counts") or {}
    if counts.get("kernel_warning", 0):
        return "v642-kernel-warning", False, "kernel WARNING appeared during lower companion observer", "do not repeat; inspect dmesg", True
    if not live.get("holder_started"):
        return "v642-modem-holder-not-started", False, "subsys_modem holder did not report opened", "inspect holder transcript", True
    qrtr_wait = live.get("qrtr_rx_wait") or {}
    if not qrtr_wait.get("seen"):
        return "v642-qrtr-rx-missing", False, "QRTR RX was not observed; companion was not started", "inspect modem PIL and current DSP state", True
    if not live.get("companion_executed"):
        return "v642-companion-skipped", False, "companion was skipped by readiness gate", "inspect QRTR wait evidence", True
    if not live.get("all_postflight_safe"):
        return "v642-companion-cleanup-review", False, f"helper_result={live.get('helper_result')}", "inspect helper transcript before retry", True
    if _observer_order(live) != EXPECTED_ORDER or _child_started(live) != 4:
        return (
            "v642-observer-contract-gap",
            False,
            f"unexpected order={_observer_order(live)} child_started={_child_started(live)}",
            "inspect helper v104 mode contract before rerun",
            True,
        )
    qmi_attempted = _qmi_attempted(live)
    if qmi_attempted:
        return "v642-qmi-guard-failed", False, f"unexpected qmi_attempted={qmi_attempted}", "stop and inspect helper", True

    if counts.get("service_notifier"):
        return (
            "v642-service-notifier-advanced",
            True,
            f"service_notifier={counts.get('service_notifier')} advance={live.get('markers', {}).get('advance_markers')}",
            "plan bounded CNSS/WLFW observer; still block HAL/scan/connect until WLAN-PD/WLFW exists",
            True,
        )
    if counts.get("qrtr_tx") or counts.get("sysmon_qmi"):
        return (
            "v642-lower-modem-readiness-only",
            True,
            f"advance={live.get('markers', {}).get('advance_markers')} service_notifier=0",
            "compare V642 against V641/V619 and choose next lower publication trigger",
            True,
        )
    return (
        "v642-qrtr-rx-only",
        True,
        "QRTR RX was observed but no QRTR TX/sysmon/service-notifier marker advanced",
        "inspect modem holder timing and companion stdout before retry",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest).replace(
        "# V596 Modem Holder Companion Proof",
        "# V642 Clean-DSP Lower Companion Observer",
        1,
    )
    live = manifest.get("live") or {}
    return "\n".join([
        text,
        "",
        "## V642 Contract",
        "",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{_observer_order(live)}`",
        f"- child_started: `{_child_started(live)}`",
        f"- qmi_attempted: `{_qmi_attempted(live)}`",
        f"- direct_dsp_boot_node_write: `False`",
        f"- cnss_diag_started: `False`",
        f"- cnss_daemon_started: `False`",
        f"- service_manager_started: `False`",
        f"- wifi_hal_started: `{manifest.get('wifi_hal_start_executed')}`",
        f"- wifi_bringup_executed: `{manifest.get('wifi_bringup_executed')}`",
    ])


base.proof_id = proof_id
base.companion_command = companion_command
base.capture_preflight = capture_preflight
base.build_checks = build_checks
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
