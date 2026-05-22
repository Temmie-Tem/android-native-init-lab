#!/usr/bin/env python3
"""V613 native mdm3/esoc targeted lower-publication observer.

This proof reuses the V609 global firmware + subsys_modem holder path and adds
only a bounded no-close `subsys_esoc0` holder before the lower companion
observer window. It uses reboot cleanup. It does not start CNSS, service-manager,
Wi-Fi HAL, qcwlanstate, scan/connect, DHCP, routing, credentials, or external
ping.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

import native_wifi_post_sysmon_observer_v609 as v609


base = v609.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v613-mdm3-esoc-targeted-observer")
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v613-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v613 mdm3 esoc targeted observer only; "
    "no CNSS daemon, no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_orig_capture_preflight = base.capture_preflight
_orig_build_checks = base.build_checks
_orig_render_summary = base.render_summary

SIBLING_PATTERNS = {
    "sysmon_slpi": re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.I),
    "sysmon_cdsp": re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I),
    "sysmon_adsp": re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.I),
    "sysmon_esoc0": re.compile(r"sysmon-qmi:.*esoc0's SSCTL service", re.I),
    "service_notifier_180": re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I),
    "service_notifier_74": re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I),
}


def proof_id() -> str:
    return "v613-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def holder_script(args: base.argparse.Namespace, major: str, minor: str, label: str, name: str) -> str:
    node = f"/tmp/a90-v613-{name}-{label}"
    status = f"/tmp/a90-v613-{name}-{label}.status"
    pidfile = f"/tmp/a90-v613-{name}-{label}.pid"
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
        f"echo v613.{name}.node=$node",
        f"echo v613.{name}.pid=$holder_pid",
        f"echo v613.{name}.status=$({args.toybox} cat \"$status\" 2>/dev/null || true)",
        f"{args.toybox} ps -A -o pid,stat,comm,args | {args.toybox} grep \"$holder_pid\" | {args.toybox} grep -v grep || true",
    ])


def sibling_counts(text: str) -> dict[str, int]:
    return {name: len([line for line in text.splitlines() if pattern.search(line)]) for name, pattern in SIBLING_PATTERNS.items()}


def capture_preflight(args: base.argparse.Namespace,
                      store: base.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    mount_preflight = _orig_capture_preflight(args, store, steps)
    base.run_step(args, store, steps, "subsys-esoc0-dev", ["cat", "/sys/class/subsys/subsys_esoc0/dev"], 10.0)
    base.run_step(args, store, steps, "mdm3-name", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/name"], 10.0)
    return mount_preflight


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _orig_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    esoc_dev = base.parse_dev(base.step_payload(steps, "subsys-esoc0-dev"))
    mdm3_name = base.step_payload(steps, "mdm3-name").strip()
    base.add_check(
        checks,
        "subsys-esoc0-cdev-visible",
        "pass" if esoc_dev and mdm3_name == "esoc0" else "blocked",
        "blocker",
        f"dev={esoc_dev} mdm3_name={mdm3_name or 'missing'}",
        [],
        "subsys_esoc0 char dev must be visible for V613",
    )
    return checks


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    label = proof_id()
    base_dir = base.mountv.PROOF_BASE_PREFIX.replace("v584", "v613") + label
    before = base.run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    for name, command, timeout in base.mountv.build_mount_commands(mount_preflight, base_dir):
        base.run_step(args, store, steps, f"v613-{name}", command, timeout)
    base.run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0)
    base.run_step(args, store, steps, "mounted-firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0)
    for path in base.GLOBAL_MODEM_BLOB_PATHS:
        base.run_step(args, store, steps, f"mounted-stat-{base.safe_name(path)}", ["stat", path], 10.0)

    modem_dev = base.parse_dev(base.step_payload(steps, "subsys-modem-dev"))
    esoc_dev = base.parse_dev(base.step_payload(steps, "subsys-esoc0-dev"))
    if not modem_dev or not esoc_dev:
        raise RuntimeError(f"missing subsystem dev modem={modem_dev} esoc={esoc_dev}")

    modem_script = holder_script(args, modem_dev[0], modem_dev[1], label, "modem-holder")
    esoc_script = holder_script(args, esoc_dev[0], esoc_dev[1], label, "esoc-holder")
    base.write_capture(store, "modem-holder-script-redacted", modem_script)
    base.write_capture(store, "esoc-holder-script-redacted", esoc_script)
    modem_holder = base.run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", modem_script], 20.0)
    base.run_step(args, store, steps, "mss-state-after-modem-holder", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
    qrtr_wait = base.wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""))
    esoc_holder = base.run_step(args, store, steps, "start-esoc-holder", ["run", args.busybox, "sh", "-c", esoc_script], 20.0)
    base.run_step(args, store, steps, "mdm3-state-after-esoc-holder", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"], 10.0)
    base.run_step(args, store, steps, "rpmsg-after-esoc-holder", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0)

    if qrtr_wait.get("seen"):
        companion_live = base.run_step(args, store, steps, "companion-start-only-with-esoc-holder", v609.companion_command(args), args.companion_runtime_sec + 60.0)
        companion_executed = True
    else:
        companion_live = base.skipped_step(store, steps, "companion-start-only-with-esoc-holder", "QRTR RX marker was not observed after subsys_modem holder open")
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
        "modem_holder_started": "v613.modem-holder.status=opened" in str(modem_holder.get("payload") or "") or qrtr_wait.get("seen") is True,
        "esoc_holder_started": "v613.esoc-holder.status=opened" in str(esoc_holder.get("payload") or ""),
        "mounted_hits": {target: target in mounted for target in base.mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": base.step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": modem_blob_visible,
        "mss_after_modem_holder": base.step_payload(steps, "mss-state-after-modem-holder").strip(),
        "mdm3_after_esoc_holder": base.step_payload(steps, "mdm3-state-after-esoc-holder").strip(),
        "qrtr_rx_wait": qrtr_wait,
        "companion_executed": companion_executed,
        "mss_after_companion": base.step_payload(steps, "mss-state-after-companion").strip(),
        "mdm3_after_companion": base.step_payload(steps, "mdm3-state-after-companion").strip(),
        "rpmsg_after_companion": base.step_payload(steps, "rpmsg-after-companion"),
        "proc_qrtr_after_companion": base.step_payload(steps, "proc-net-qrtr-after-companion"),
        "companion_keys": keys,
        "helper_result": keys.get("wifi_companion_start.result", ""),
        "all_observable": keys.get("wifi_companion_start.all_observable", "") == "1",
        "all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe", "") == "1",
        "markers": base.marker_summary(delta),
        "sibling_counts": sibling_counts(delta),
        "dmesg_delta": delta[-12000:],
        "reboot_cleanup": reboot,
    }


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v613-mdm3-esoc-targeted-observer-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current-boot V401/V490, then run V613 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v613-preflight-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V613", False
    if args.command == "preflight":
        return (
            "v613-mdm3-esoc-targeted-observer-preflight-ready",
            True,
            "preflight ready; live run needs approval and uses reboot cleanup",
            "run V613 live proof",
            False,
        )
    if not live:
        return "v613-review-required", False, "missing live result", "inspect runner failure", True
    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v613-cleanup-review", False, f"reboot_cleanup={reboot}", "verify native recovery before continuing", True
    counts = (live.get("markers") or {}).get("counts") or {}
    sibling = live.get("sibling_counts") or {}
    if counts.get("kernel_warning"):
        return "v613-esoc-holder-unsafe", False, "kernel WARNING/reference mismatch appeared during live window", "do not repeat; inspect esoc holder safety", True
    if not live.get("esoc_holder_started"):
        return "v613-esoc-holder-not-opened", False, "esoc holder did not report opened", "inspect esoc holder transcript", True
    if live.get("mdm3_after_esoc_holder") == "ONLINE" or any(sibling.get(k, 0) for k in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp", "sysmon_esoc0")) or counts.get("service_notifier"):
        return (
            "v613-mdm3-esoc-publication-advanced",
            True,
            f"mdm3={live.get('mdm3_after_companion')} sibling={sibling} service_notifier={counts.get('service_notifier', 0)}",
            "use the advanced lower publication boundary for a follow-up CNSS-only gate; still no HAL/scan/connect",
            True,
        )
    if live.get("mdm3_after_esoc_holder") == "ONLINE":
        return (
            "v613-mdm3-online-service-notifier-missing",
            True,
            "mdm3 reached ONLINE but service-notifier stayed missing",
            "compare sibling sysmon and service-notifier surfaces before CNSS/HAL",
            True,
        )
    return (
        "v613-no-lower-publication-change",
        True,
        f"esoc holder opened but mdm3={live.get('mdm3_after_companion')} and no sibling/service-notifier markers appeared",
        "avoid HAL retry; inspect esoc holder timing and Android init triggers",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest).replace(
        "# V598 Modem Holder WLFW QRTR Readback Proof",
        "# V613 MDM3/ESOC Targeted Observer",
        1,
    )
    live = manifest.get("live") or {}
    return "\n".join([
        text,
        "",
        "## V613 ESOC Contract",
        "",
        f"- modem_holder_started: `{live.get('modem_holder_started')}`",
        f"- esoc_holder_started: `{live.get('esoc_holder_started')}`",
        f"- mdm3_after_esoc_holder: `{live.get('mdm3_after_esoc_holder')}`",
        f"- mdm3_after_companion: `{live.get('mdm3_after_companion')}`",
        f"- sibling_counts: `{live.get('sibling_counts')}`",
        f"- cnss_diag_started: `False`",
        f"- cnss_daemon_started: `False`",
        f"- service_manager_started: `False`",
        f"- wifi_bringup_executed: `{manifest.get('wifi_bringup_executed')}`",
    ])


base.capture_preflight = capture_preflight
base.build_checks = build_checks
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
