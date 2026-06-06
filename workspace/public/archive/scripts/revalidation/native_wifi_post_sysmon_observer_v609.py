#!/usr/bin/env python3
"""V609 post-sysmon service-notifier observer proof.

This proof reuses the V598 modem-holder and firmware-mount path, but replaces
the companion command with a no-CNSS observer mode. The helper starts only
qrtr-ns, rmt_storage, tftp_server, and pd-mapper, then holds a bounded window
for QRTR/sysmon/service-notifier observation. It does not start cnss_diag,
cnss-daemon, service-manager, Wi-Fi HAL, qcwlanstate, scan/connect, DHCP,
routing, credentials, or external ping.
"""

from __future__ import annotations

from typing import Any

import native_wifi_modem_holder_wlfw_readback_v598 as v598


base = v598.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v609-post-sysmon-observer")
base.DEFAULT_HELPER_SHA256 = "a63758a4cd10a4d0b227e2b85516ecc65575cca30fe863d332b802fabae4f57e"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v103"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v609-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v609 post-sysmon observer only; "
    "no CNSS daemon, no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_orig_decide = base.decide
_orig_render_summary = base.render_summary


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = [
        "run", args.helper,
        "--system-root", "/mnt/system/system",
        "--vendor-block", "/dev/block/sda29",
        "--vendor-fstype", "ext4",
        "--mode", "wifi-companion-post-sysmon-observer-start-only",
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


def _readback_clean(live: dict[str, Any]) -> bool:
    readback = live.get("qrtr_readback") or {}
    return int(readback.get("qmi_attempted") or 0) == 0


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
            "v609-post-sysmon-observer-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v103, refresh current-boot V401/V490, then run V609 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return (
            "v609-preflight-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "resolve blockers before V609",
            False,
        )
    if args.command == "preflight":
        return (
            "v609-post-sysmon-observer-preflight-ready",
            True,
            "preflight ready; live run needs approval and uses reboot cleanup",
            "run V609 observer live proof",
            False,
        )

    decision, pass_ok, reason, next_step, live_executed = _orig_decide(args, checks, live)
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed
    if not pass_ok:
        return decision, pass_ok, reason, next_step, live_executed
    if not _readback_clean(live):
        return (
            "v609-qmi-guard-failed",
            False,
            "unexpected QMI payload attempt in observer mode",
            "stop and inspect helper before any further Wi-Fi live action",
            live_executed,
        )
    expected_order = "qrtr_ns,rmt_storage,tftp_server,pd_mapper"
    if _observer_order(live) != expected_order or _child_started(live) != 4:
        return (
            "v609-observer-contract-gap",
            False,
            f"unexpected order={_observer_order(live)} child_started={_child_started(live)}",
            "inspect helper mode contract before rerun",
            live_executed,
        )
    counts = ((live.get("markers") or {}).get("counts") or {})
    if not counts.get("qrtr_tx") or not counts.get("sysmon_qmi"):
        return (
            "v609-qrtr-sysmon-not-reached",
            True,
            "observer reached cleanup but did not reach both QRTR TX and modem sysmon-qmi",
            "inspect lower modem publication prerequisites",
            live_executed,
        )
    if counts.get("service_notifier"):
        return (
            "v609-service-notifier-pre-cnss-visible",
            True,
            "service-notifier appeared before any CNSS daemon was started",
            "run a follow-up that starts CNSS only after service-notifier is visible",
            live_executed,
        )
    return (
        "v609-service-notifier-pre-cnss-missing",
        True,
        "QRTR TX and modem sysmon-qmi appeared, but service-notifier did not appear in the no-CNSS observer window",
        "compare Android/native lower modem publication preconditions before another Wi-Fi userspace retry",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest).replace(
        "# V598 Modem Holder WLFW QRTR Readback Proof",
        "# V609 Post-Sysmon Observer Proof",
        1,
    )
    live = manifest.get("live") or {}
    return "\n".join([
        text,
        "",
        "## V609 Observer Contract",
        "",
        f"- expected_order: `qrtr_ns,rmt_storage,tftp_server,pd_mapper`",
        f"- observed_order: `{_observer_order(live)}`",
        f"- child_started: `{_child_started(live)}`",
        f"- cnss_diag_started: `False`",
        f"- cnss_daemon_started: `False`",
        f"- service_manager_started: `False`",
        f"- wifi_bringup_executed: `{manifest.get('wifi_bringup_executed')}`",
    ])


base.companion_command = companion_command
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
