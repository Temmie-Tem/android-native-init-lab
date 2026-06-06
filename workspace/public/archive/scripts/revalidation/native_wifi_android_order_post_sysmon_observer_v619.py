#!/usr/bin/env python3
"""V619 Android-order post-sysmon service-notifier observer proof.

This proof reuses the V615 DSP boot-node and modem-holder path, but changes the
no-CNSS companion order to match Android's lower companion sequence:

    qrtr-ns -> pd-mapper -> rmt_storage -> tftp_server

It does not start CNSS, service-manager, Wi-Fi HAL, wificond, supplicant,
hostapd, qcwlanstate, scan/connect, DHCP, routing, credentials, or external
ping.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import native_wifi_dsp_boot_node_observer_v615 as v615


base = v615.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v619-android-order-post-sysmon-observer")
base.DEFAULT_HELPER_SHA256 = "f811c18d1a9af92f5ca9fadcfd4dbd94593318240744a0c86d0419280bbea019"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v104"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v619-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v619 android-order post-sysmon observer only; "
    "no CNSS daemon, no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)


def proof_id() -> str:
    return "v619-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


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


def _observer_order(live: dict[str, Any]) -> str:
    keys = live.get("companion_keys") or {}
    return str(keys.get("wifi_companion_start.order") or "")


def _child_started(live: dict[str, Any]) -> int:
    keys = live.get("companion_keys") or {}
    try:
        return int(keys.get("wifi_companion_start.child_started") or 0)
    except ValueError:
        return 0


def _readback_clean(live: dict[str, Any]) -> bool:
    readback = live.get("qrtr_readback") or {}
    return int(readback.get("qmi_attempted") or 0) == 0


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = v615.build_checks(args, steps, mount_preflight, v490, v525)
    renamed: list[base.Check] = []
    for check in checks:
        name = "helper-v104-ready" if check.name == "helper-v100-ready" else check.name
        detail = check.detail.replace("V596", "V619").replace("V615", "V619")
        next_step = (
            check.next_step
            .replace("V596", "V619")
            .replace("V615", "V619")
            .replace("helper v100", "helper v104")
        )
        renamed.append(base.Check(
            name,
            check.status,
            check.severity,
            detail,
            check.evidence,
            next_step,
        ))
    return renamed


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v619-android-order-post-sysmon-observer-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v104, refresh current-boot V401/V490, then run V619 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v619-preflight-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V619", False
    if args.command == "preflight":
        return (
            "v619-android-order-post-sysmon-observer-preflight-ready",
            True,
            "preflight ready; live run needs approval and uses reboot cleanup",
            "run V619 live proof",
            False,
        )
    if not live:
        return "v619-review-required", False, "missing live result", "inspect runner failure", True
    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v619-cleanup-review", False, f"reboot_cleanup={reboot}", "verify native recovery before continuing", True
    if not _readback_clean(live):
        return "v619-qmi-guard-failed", False, "unexpected QMI payload attempt in observer mode", "stop and inspect helper", True
    expected_order = "qrtr_ns,pd_mapper,rmt_storage,tftp_server"
    if _observer_order(live) != expected_order or _child_started(live) != 4:
        return (
            "v619-observer-contract-gap",
            False,
            f"unexpected order={_observer_order(live)} child_started={_child_started(live)}",
            "inspect helper v104 mode contract before rerun",
            True,
        )

    counts = (live.get("markers") or {}).get("counts") or {}
    dsp = live.get("dsp_counts") or {}
    if counts.get("kernel_warning"):
        return "v619-unsafe-kernel-warning", False, "kernel WARNING appeared during Android-order observer", "do not repeat; inspect dmesg", True
    if not all(live.get("boot_nodes_written", {}).values()):
        return "v619-boot-node-write-gap", False, f"boot_nodes_written={live.get('boot_nodes_written')}", "inspect boot node write transcripts", True

    dsp_pil_count = sum(int(dsp.get(name, 0) or 0) for name in ("adsp_pil", "cdsp_pil", "slpi_pil"))
    sibling_sysmon_count = sum(int(dsp.get(name, 0) or 0) for name in ("adsp_sysmon", "cdsp_sysmon", "slpi_sysmon"))
    service_notifier_count = sum(int(dsp.get(name, 0) or 0) for name in ("service_notifier_180", "service_notifier_74"))
    if service_notifier_count > 0:
        return (
            "v619-android-order-service-notifier-advanced",
            True,
            f"DSP PIL={dsp_pil_count}, sibling_sysmon={sibling_sysmon_count}, service_notifier={service_notifier_count}",
            "plan CNSS-only WLFW/BDF observer; still no HAL/scan/connect",
            True,
        )
    if sibling_sysmon_count > 0:
        return (
            "v619-android-order-sibling-only",
            True,
            f"DSP PIL={dsp_pil_count}, sibling_sysmon={sibling_sysmon_count}, service_notifier=0",
            "classify remaining QMI service registration dependency before CNSS/HAL",
            True,
        )
    return (
        "v619-android-order-no-publication-change",
        True,
        f"DSP PIL={dsp_pil_count}, sibling_sysmon=0, service_notifier=0",
        "do not retry HAL; inspect lower QMI publication prerequisites",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = v615.render_summary(manifest).replace(
        "# V615 DSP Boot-Node Observer",
        "# V619 Android-Order Post-Sysmon Observer",
        1,
    ).replace(
        "## V609 Observer Contract",
        "## Base Observer Contract",
    ).replace(
        "- expected_order: `qrtr_ns,rmt_storage,tftp_server,pd_mapper`",
        "- expected_order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server`",
    )
    live = manifest.get("live") or {}
    return "\n".join([
        text,
        "",
        "## V619 Android-Order Contract",
        "",
        f"- expected_order: `qrtr_ns,pd_mapper,rmt_storage,tftp_server`",
        f"- observed_order: `{_observer_order(live)}`",
        f"- child_started: `{_child_started(live)}`",
        f"- cnss_diag_started: `False`",
        f"- cnss_daemon_started: `False`",
        f"- service_manager_started: `False`",
        f"- wifi_hal_started: `False`",
        f"- wifi_bringup_executed: `{manifest.get('wifi_bringup_executed')}`",
    ])


v615.proof_id = proof_id
v615.v609.companion_command = companion_command
base.capture_preflight = v615.capture_preflight
base.build_checks = build_checks
base.run_live = v615.run_live
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
