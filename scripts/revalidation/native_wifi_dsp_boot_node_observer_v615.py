#!/usr/bin/env python3
"""V615 native DSP boot-node lower-publication observer.

This proof writes only the Android-equivalent ADSP/CDSP/SLPI boot nodes, then
reuses the V609 no-CNSS companion observer. It does not write boot_wlan, start
CNSS, service-manager, Wi-Fi HAL, qcwlanstate, scan/connect, credentials, DHCP,
routes, or external ping.
"""

from __future__ import annotations

import datetime as dt
import re
import time
from typing import Any

import native_wifi_post_sysmon_observer_v609 as v609


base = v609.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v615-dsp-boot-node-observer")
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v615-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v615 dsp boot-node observer only; "
    "no boot_wlan, no CNSS daemon, no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_orig_capture_preflight = base.capture_preflight
_orig_build_checks = base.build_checks
_orig_render_summary = base.render_summary

BOOT_NODES = {
    "adsp": "/sys/kernel/boot_adsp/boot",
    "cdsp": "/sys/kernel/boot_cdsp/boot",
    "slpi": "/sys/kernel/boot_slpi/boot",
}

DSP_PATTERNS = {
    "adsp_pil": re.compile(r"subsys-pil.*lpass: adsp: loading", re.I),
    "cdsp_pil": re.compile(r"subsys-pil.*turing: cdsp: loading", re.I),
    "slpi_pil": re.compile(r"subsys-pil.*ssc: slpi: loading", re.I),
    "adsp_sysmon": re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.I),
    "cdsp_sysmon": re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I),
    "slpi_sysmon": re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.I),
    "service_notifier_180": re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I),
    "service_notifier_74": re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I),
}


def proof_id() -> str:
    return "v615-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def holder_script(args: base.argparse.Namespace, major: str, minor: str, label: str) -> str:
    node = f"/tmp/a90-v615-modem-holder-{label}"
    status = f"/tmp/a90-v615-modem-holder-{label}.status"
    pidfile = f"/tmp/a90-v615-modem-holder-{label}.pid"
    hold_sec = max(args.holder_sec, args.companion_runtime_sec + 45)
    return "\n".join([
        "set -u",
        f"node={base.shell_quote(node)}",
        f"status={base.shell_quote(status)}",
        f"pidfile={base.shell_quote(pidfile)}",
        f"{args.toybox} rm -f \"$node\" \"$status\" \"$pidfile\"",
        f"{args.toybox} mknod -m 600 \"$node\" c {major} {minor}",
        "(",
        "  exec 3<\"$node\"",
        "  echo opened > \"$status\"",
        f"  sleep {hold_sec}",
        ") &",
        "holder_pid=$!",
        "echo \"$holder_pid\" > \"$pidfile\"",
        "for i in 1 2 3 4 5 6 7 8 9 10; do",
        "  test -s \"$status\" && break",
        "  sleep 1",
        "done",
        "echo v615.modem-holder.node=$node",
        "echo v615.modem-holder.pid=$holder_pid",
        f"echo v615.modem-holder.status=$({args.toybox} cat \"$status\" 2>/dev/null || true)",
        f"{args.toybox} ps -A -o pid,stat,comm,args | {args.toybox} grep \"$holder_pid\" | {args.toybox} grep -v grep || true",
    ])


def boot_node_write_script(path: str) -> str:
    return "\n".join([
        "set -u",
        f"node={base.shell_quote(path)}",
        "echo 1 > \"$node\"",
        "echo v615.boot_node.write=$node",
    ])


def pattern_counts(text: str) -> dict[str, int]:
    return {name: len([line for line in text.splitlines() if pattern.search(line)]) for name, pattern in DSP_PATTERNS.items()}


def step_ok(steps: list[dict[str, Any]], name: str) -> bool:
    for step in steps:
        if step.get("name") == name:
            return bool(step.get("ok")) and step.get("status") == "ok"
    return False


def capture_preflight(args: base.argparse.Namespace,
                      store: base.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    mount_preflight = _orig_capture_preflight(args, store, steps)
    for name, path in BOOT_NODES.items():
        base.run_step(args, store, steps, f"stat-boot-{name}", ["run", args.toybox, "ls", "-l", path], 10.0)
    base.run_step(args, store, steps, "stat-boot-wlan", ["run", args.toybox, "ls", "-l", "/sys/kernel/boot_wlan/boot_wlan"], 10.0)
    return mount_preflight


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _orig_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    for name, path in BOOT_NODES.items():
        payload = base.step_payload(steps, f"stat-boot-{name}")
        base.add_check(
            checks,
            f"boot-{name}-node-visible",
            "pass" if path in payload and "--w" in payload else "blocked",
            "blocker",
            payload.strip() or "missing",
            [],
            f"{path} must be visible and write-only for V615",
        )
    wlan_payload = base.step_payload(steps, "stat-boot-wlan")
    base.add_check(
        checks,
        "boot-wlan-node-visible-but-forbidden",
        "pass" if "/sys/kernel/boot_wlan/boot_wlan" in wlan_payload else "warn",
        "warning",
        "V615 records boot_wlan visibility but must not write it",
        [],
        "do not write boot_wlan in V615",
    )
    return checks


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    label = proof_id()
    base_dir = base.mountv.PROOF_BASE_PREFIX.replace("v584", "v615") + label
    before = base.run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    for name, command, timeout in base.mountv.build_mount_commands(mount_preflight, base_dir):
        base.run_step(args, store, steps, f"v615-{name}", command, timeout)
    base.run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0)
    base.run_step(args, store, steps, "mounted-firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0)
    for path in base.GLOBAL_MODEM_BLOB_PATHS:
        base.run_step(args, store, steps, f"mounted-stat-{base.safe_name(path)}", ["stat", path], 10.0)

    for name, path in BOOT_NODES.items():
        script = boot_node_write_script(path)
        base.write_capture(store, f"boot-{name}-write-script-redacted", script)
        base.run_step(args, store, steps, f"write-boot-{name}", ["run", args.busybox, "sh", "-c", script], 10.0)
        time.sleep(0.5)
    base.run_step(args, store, steps, "dmesg-after-dsp-boot", ["run", args.toybox, "dmesg"], 60.0)
    base.run_step(args, store, steps, "rpmsg-after-dsp-boot", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0)

    dev = base.parse_dev(base.step_payload(steps, "subsys-modem-dev"))
    if not dev:
        raise RuntimeError("subsys_modem dev missing after preflight")
    script = holder_script(args, dev[0], dev[1], label)
    base.write_capture(store, "modem-holder-script-redacted", script)
    holder = base.run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", script], 20.0)
    base.run_step(args, store, steps, "mss-state-after-holder", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
    qrtr_wait = base.wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""))
    if qrtr_wait.get("seen"):
        companion_live = base.run_step(args, store, steps, "companion-start-only-with-dsp-boot", v609.companion_command(args), args.companion_runtime_sec + 60.0)
        companion_executed = True
    else:
        companion_live = base.skipped_step(store, steps, "companion-start-only-with-dsp-boot", "QRTR RX marker was not observed after DSP boot and modem holder")
        companion_executed = False

    base.run_step(args, store, steps, "mss-state-after-companion", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
    base.run_step(args, store, steps, "mdm3-state-after-companion", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"], 10.0)
    base.run_step(args, store, steps, "rpmsg-after-companion", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0)
    base.run_step(args, store, steps, "proc-net-qrtr-after-companion", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0)
    base.run_step(args, store, steps, "ps-before-reboot", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    after = base.run_step(args, store, steps, "dmesg-after-companion", ["run", args.toybox, "dmesg"], 60.0)
    delta = base.dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
    base.write_capture(store, "dmesg-delta", delta)
    reboot = base.reboot_and_wait(args, store)
    mounted = base.mountv.parse_mounts(base.step_payload(steps, "mounted-proc-mounts"))
    modem_blob_visible = {
        path: base.path_exists(base.step_payload(steps, f"mounted-stat-{base.safe_name(path)}"))
        for path in base.GLOBAL_MODEM_BLOB_PATHS
    }
    keys = base.companion.parse_keys(str(companion_live.get("payload") or ""))
    return {
        "base": base_dir,
        "boot_nodes_written": {name: step_ok(steps, f"write-boot-{name}") for name in BOOT_NODES},
        "holder_started": (
            "v615.modem-holder.status=opened" in str(holder.get("payload") or "")
            or qrtr_wait.get("seen") is True
            or base.step_payload(steps, "mss-state-after-holder").strip() == "ONLINE"
        ),
        "mounted_hits": {target: target in mounted for target in base.mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": base.step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": modem_blob_visible,
        "mss_after_holder": base.step_payload(steps, "mss-state-after-holder").strip(),
        "qrtr_rx_wait": qrtr_wait,
        "companion_executed": companion_executed,
        "mss_after_companion": base.step_payload(steps, "mss-state-after-companion").strip(),
        "mdm3_after_companion": base.step_payload(steps, "mdm3-state-after-companion").strip(),
        "rpmsg_after_dsp_boot": base.step_payload(steps, "rpmsg-after-dsp-boot"),
        "rpmsg_after_companion": base.step_payload(steps, "rpmsg-after-companion"),
        "proc_qrtr_after_companion": base.step_payload(steps, "proc-net-qrtr-after-companion"),
        "companion_keys": keys,
        "helper_result": keys.get("wifi_companion_start.result", ""),
        "all_observable": keys.get("wifi_companion_start.all_observable", "") == "1",
        "all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe", "") == "1",
        "markers": base.marker_summary(delta),
        "dsp_counts": pattern_counts(delta),
        "dmesg_delta": delta[-12000:],
        "reboot_cleanup": reboot,
    }


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v615-dsp-boot-node-observer-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current-boot V401/V490, then run V615 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v615-preflight-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V615", False
    if args.command == "preflight":
        return (
            "v615-dsp-boot-node-observer-preflight-ready",
            True,
            "preflight ready; live run needs approval and uses reboot cleanup",
            "run V615 live proof",
            False,
        )
    if not live:
        return "v615-review-required", False, "missing live result", "inspect runner failure", True
    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v615-cleanup-review", False, f"reboot_cleanup={reboot}", "verify native recovery before continuing", True
    counts = (live.get("markers") or {}).get("counts") or {}
    dsp = live.get("dsp_counts") or {}
    if counts.get("kernel_warning"):
        return "v615-unsafe-kernel-warning", False, "kernel WARNING appeared during DSP boot observer", "do not repeat; inspect dmesg", True
    if not all(live.get("boot_nodes_written", {}).values()):
        return "v615-boot-node-write-gap", False, f"boot_nodes_written={live.get('boot_nodes_written')}", "inspect boot node write transcripts", True
    dsp_pil_count = sum(int(dsp.get(name, 0) or 0) for name in ("adsp_pil", "cdsp_pil", "slpi_pil"))
    sibling_sysmon_count = sum(int(dsp.get(name, 0) or 0) for name in ("adsp_sysmon", "cdsp_sysmon", "slpi_sysmon"))
    service_notifier_count = sum(int(dsp.get(name, 0) or 0) for name in ("service_notifier_180", "service_notifier_74"))
    if service_notifier_count > 0:
        return (
            "v615-dsp-boot-publication-advanced",
            True,
            f"DSP PIL={dsp_pil_count}, sibling_sysmon={sibling_sysmon_count}, service_notifier={service_notifier_count}",
            "plan CNSS-only WLFW/BDF observer; still no HAL/scan/connect",
            True,
        )
    if sibling_sysmon_count > 0:
        return (
            "v615-dsp-boot-sibling-only",
            True,
            f"DSP PIL={dsp_pil_count}, sibling_sysmon={sibling_sysmon_count}, service_notifier=0",
            "classify remaining service-notifier gap before CNSS/HAL",
            True,
        )
    return (
        "v615-dsp-boot-no-publication-change",
        True,
        f"DSP PIL={dsp_pil_count}, sibling_sysmon=0, service_notifier=0",
        "do not retry HAL; inspect DSP boot node effect and Android init timing",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest).replace(
        "# V598 Modem Holder WLFW QRTR Readback Proof",
        "# V615 DSP Boot-Node Observer",
        1,
    ).replace(
        "# V609 Post-Sysmon Observer Proof",
        "# V615 DSP Boot-Node Observer",
        1,
    )
    live = manifest.get("live") or {}
    return "\n".join([
        text,
        "",
        "## V615 DSP Boot Contract",
        "",
        f"- boot_nodes_written: `{live.get('boot_nodes_written')}`",
        f"- dsp_counts: `{live.get('dsp_counts')}`",
        f"- holder_started: `{live.get('holder_started')}`",
        f"- mss_after_companion: `{live.get('mss_after_companion')}`",
        f"- mdm3_after_companion: `{live.get('mdm3_after_companion')}`",
        f"- cnss_diag_started: `False`",
        f"- cnss_daemon_started: `False`",
        f"- service_manager_started: `False`",
        f"- boot_wlan_written: `False`",
        f"- wifi_bringup_executed: `{manifest.get('wifi_bringup_executed')}`",
    ])


base.capture_preflight = capture_preflight
base.build_checks = build_checks
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
