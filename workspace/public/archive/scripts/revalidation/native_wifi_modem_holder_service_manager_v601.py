#!/usr/bin/env python3
"""V601 modem-holder companion replay with service-manager binder surface.

This proof reuses V598's global firmware mounts, `subsys_modem` holder, QRTR RX
gate, companion stack, and WLFW QRTR nameservice readback. It changes only the
bounded companion mode to include `servicemanager`, `hwservicemanager`, and
`vndservicemanager` with Android-captured copy-real linkerconfig.

It does not start Wi-Fi HAL, write qcwlanstate, scan, connect, use credentials,
run DHCP, change routing, or ping externally.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_modem_holder_wlfw_readback_v598 as v598


base = v598.base

base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v601-modem-holder-service-manager")
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v601-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v601 modem holder service-manager binder proof only; "
    "no Wi-Fi HAL start, no qcwlanstate, no scan/connect/link-up and no external ping"
)

REAL_LD_CONFIG = "/cache/bin/a90_real_ld.config.txt"
REAL_APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
MAX_CMDV1_COMMAND_ARGS = 30

_v598_capture_preflight = base.capture_preflight
_v598_build_checks = base.build_checks
_v598_companion_command = base.companion_command
_v598_run_live = base.run_live
_v598_decide = base.decide
_v598_render_summary = base.render_summary
_v596_build_manifest = base.build_manifest


def _count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, re.IGNORECASE))


def _remove_option_with_value(command: list[str], option: str) -> None:
    while True:
        try:
            index = command.index(option)
        except ValueError:
            return
        del command[index:index + 2]


def _set_option(command: list[str], option: str, value: str) -> None:
    try:
        index = command.index(option)
    except ValueError:
        command.extend([option, value])
    else:
        command[index + 1] = value


def _helper_text(live: dict[str, Any] | None) -> str:
    if not live:
        return ""
    return str(live.get("helper_stdout_stderr") or "")


def capture_preflight(args: base.argparse.Namespace,
                      store: base.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    mount_preflight = _v598_capture_preflight(args, store, steps)
    if args.command != "plan":
        base.run_step(args, store, steps, "stat-real-ld-config", ["stat", REAL_LD_CONFIG], 10.0)
        base.run_step(args, store, steps, "stat-real-apex-libraries", ["stat", REAL_APEX_LIBRARIES], 10.0)
    return mount_preflight


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _v598_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    ld_text = base.step_payload(steps, "stat-real-ld-config")
    apex_text = base.step_payload(steps, "stat-real-apex-libraries")
    base.add_check(
        checks,
        "helper-v100-service-manager-ready",
        "pass"
        if (
            "wifi-companion-vnd-service-manager-start-only" in usage
            and "--allow-service-manager-start-only" in usage
            and "--allow-qrtr-ns-readback" in usage
        )
        else "blocked",
        "blocker",
        "helper must expose vnd service-manager companion and QRTR readback gates",
        [
            line
            for line in usage.splitlines()
            if "wifi-companion-vnd-service-manager-start-only" in line
            or "--allow-service-manager-start-only" in line
            or "--allow-qrtr-ns-readback" in line
        ][:6],
        "deploy helper v100 or newer before V601",
    )
    base.add_check(
        checks,
        "real-linkerconfig-present",
        "pass" if "size=134256" in ld_text else "blocked",
        "blocker",
        f"path={REAL_LD_CONFIG}",
        [line for line in ld_text.splitlines() if "size=" in line or REAL_LD_CONFIG in line][:4],
        "restore Android-captured ld.config.txt before V601",
    )
    base.add_check(
        checks,
        "real-apex-libraries-present",
        "pass" if "size=366" in apex_text else "blocked",
        "blocker",
        f"path={REAL_APEX_LIBRARIES}",
        [line for line in apex_text.splitlines() if "size=" in line or REAL_APEX_LIBRARIES in line][:4],
        "restore Android-captured apex.libraries.config.txt before V601",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = _v598_companion_command(args)
    _set_option(command, "--mode", "wifi-companion-vnd-service-manager-start-only")
    _set_option(command, "--linkerconfig-mode", "copy-real")
    _remove_option_with_value(command, "--linkerconfig-source")
    _remove_option_with_value(command, "--apex-libraries-source")
    command.extend([
        "--linkerconfig-source", REAL_LD_CONFIG,
        "--apex-libraries-source", REAL_APEX_LIBRARIES,
    ])
    if base.approved(args):
        command.append("--allow-service-manager-start-only")
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(f"V601 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def _service_manager_summary(keys: dict[str, str], helper_text: str) -> dict[str, Any]:
    children = ("servicemanager", "hwservicemanager", "vndservicemanager")
    return {
        "with_service_manager": keys.get("wifi_companion_start.with_service_manager", ""),
        "with_vnd_service_manager": keys.get("wifi_companion_start.with_vnd_service_manager", ""),
        "service_manager": keys.get("wifi_companion_start.service_manager", ""),
        "linkerconfig_mode": "copy-real" if "linkerconfig_mode=copy-real" in helper_text else "",
        "children": {
            name: {
                "observable": keys.get(f"wifi_companion_start.child.{name}.observable", ""),
                "exited": keys.get(f"wifi_companion_start.child.{name}.exited", ""),
                "exit_code": keys.get(f"wifi_companion_start.child.{name}.exit_code", ""),
                "signal": keys.get(f"wifi_companion_start.child.{name}.signal", ""),
                "postflight_safe": keys.get(f"wifi_companion_start.child.{name}.postflight_safe", ""),
            }
            for name in children
        },
    }


def _v601_counts(dmesg_delta: str, helper_text: str, readback: dict[str, Any]) -> dict[str, int]:
    return {
        "service_notifier_74": _count(r"service-notifier.*\b74\b", dmesg_delta),
        "service_notifier_180": _count(r"service-notifier.*\b180\b", dmesg_delta),
        "wlan_pd": _count(r"wlan[_-]pd|msm/modem/wlan_pd", dmesg_delta),
        "wlfw_start": _count(r"wlfw_start", dmesg_delta),
        "wlfw_thread": _count(r"wlfw.*thread", dmesg_delta),
        "qmi_server_connected": _count(r"icnss_qmi: QMI Server Connected", dmesg_delta),
        "bdf": _count(r"BDF file|bdwlan\.bin|regdb\.bin", dmesg_delta),
        "wlan_fw_ready": _count(r"WLAN FW is ready", dmesg_delta),
        "wlan0": _count(r"\bwlan0\b", dmesg_delta),
        "binder_transaction_failed": _count(r"binder: .*transaction failed|binder transaction failed", dmesg_delta),
        "binder_ioctl_unsupported": _count(r"BINDER_ENABLE_ONEWAY_SPAM_DETECTION|oneway spam|binder: .*ioctl .* returned -22", dmesg_delta),
        "cnss_daemon_binder_mentions": _count(r"cnss-daemon.*binder|binder.*cnss-daemon", dmesg_delta),
        "linker_symbol_gap": _count(r"cannot locate symbol|CANNOT LINK EXECUTABLE", helper_text),
        "perfd_client_failed": _count(r"Failed to become a perfd client", helper_text + "\n" + dmesg_delta),
        "wl_fw_qrtr_service_events": int(readback.get("service_events") or 0),
    }


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    result = _v598_run_live(args, store, steps, mount_preflight)
    helper_text = base.step_payload(steps, "companion-start-only-with-holder")
    keys = result.get("companion_keys") or {}
    readback = result.get("qrtr_readback") or {}
    result["helper_stdout_stderr"] = helper_text
    result["service_manager"] = _service_manager_summary(keys, helper_text)
    result["v601_counts"] = _v601_counts(str(result.get("dmesg_delta") or ""), helper_text, readback)
    return result


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v601-service-manager-binder-proof-plan-ready",
            True,
            "plan-only; no device command executed",
            "restore current-boot V490 and copy-real linkerconfig, then run V601 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return (
            "v601-service-manager-binder-proof-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "resolve V601 blockers before live run",
            False,
        )
    if args.command == "preflight":
        return (
            "v601-service-manager-binder-proof-preflight-ready",
            True,
            "preflight ready; live run uses modem holder, service-manager, copy-real linkerconfig, and reboot cleanup",
            "run V601 live proof",
            False,
        )
    if not base.approved(args):
        return (
            "v601-service-manager-binder-proof-approval-required",
            True,
            "exact approval phrase required; no live command executed",
            "rerun with exact V601 approval",
            False,
        )
    decision, pass_ok, reason, next_step, live_executed = _v598_decide(args, checks, live)
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed
    if not pass_ok:
        return decision, pass_ok, reason, next_step, live_executed

    counts = live.get("v601_counts") or {}
    service_manager = live.get("service_manager") or {}
    if service_manager.get("with_service_manager") != "1" or service_manager.get("with_vnd_service_manager") != "1":
        return (
            "v601-service-manager-not-executed",
            False,
            f"service_manager={service_manager}",
            "inspect helper mode and approval propagation before retry",
            live_executed,
        )
    if int(counts.get("linker_symbol_gap") or 0):
        return (
            "v601-service-manager-linker-gap",
            True,
            "service-manager companion reached copy-real mode but linker symbol gap remains",
            "inspect helper stdout/stderr and Android linker namespace delta before retry",
            live_executed,
        )
    if int(counts.get("binder_transaction_failed") or 0) > 0:
        return (
            "v601-service-manager-binder-gap-persists",
            True,
            f"binder transaction failures persisted; counts={counts}",
            "inspect service-manager socket/property surface before another CNSS retry",
            live_executed,
        )
    if int(counts.get("service_notifier_74") or 0) > 0 or int(counts.get("wlan_pd") or 0) > 0:
        return (
            "v601-service-manager-qmi-registration-advance",
            True,
            f"post-sysmon WLAN registration advanced; counts={counts}",
            "advance to bounded qcwlanstate/HAL retry only after confirming no residue",
            live_executed,
        )
    if int(counts.get("wl_fw_qrtr_service_events") or 0) > 0 or int(counts.get("wlfw_start") or 0) > 0:
        return (
            "v601-service-manager-wlfw-advance",
            True,
            f"WLFW registration advanced; counts={counts}",
            "advance to bounded qcwlanstate/HAL retry; still block scan/connect until wlan0 or FW-ready appears",
            live_executed,
        )
    return (
        "v601-service-manager-binder-cleared-wlfw-missing",
        True,
        f"service-manager binder gap cleared but WLFW/service-notifier 74 remains absent; counts={counts}",
        "classify missing service registry/sysmon sibling or WLAN-PD trigger before qcwlanstate/HAL retry",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v598_render_summary(manifest).replace(
        "# V598 Modem Holder WLFW QRTR Readback Proof",
        "# V601 Modem Holder Service-Manager Binder Proof",
        1,
    )
    live = manifest.get("live") or {}
    service_manager = live.get("service_manager") or {}
    children = service_manager.get("children") or {}
    child_rows = [
        [
            name,
            values.get("observable", ""),
            values.get("exited", ""),
            values.get("exit_code", ""),
            values.get("signal", ""),
            values.get("postflight_safe", ""),
        ]
        for name, values in sorted(children.items())
    ]
    counts = live.get("v601_counts") or {}
    count_rows = [[key, str(value)] for key, value in sorted(counts.items())]
    return "\n".join([
        text,
        "",
        "## V601 Service-Manager Surface",
        "",
        f"- with_service_manager: `{service_manager.get('with_service_manager', '')}`",
        f"- with_vnd_service_manager: `{service_manager.get('with_vnd_service_manager', '')}`",
        f"- service_manager: `{service_manager.get('service_manager', '')}`",
        f"- linkerconfig_mode: `{service_manager.get('linkerconfig_mode', '')}`",
        "",
        base.markdown_table(
            ["child", "observable", "exited", "exit_code", "signal", "postflight_safe"],
            child_rows,
        ) if child_rows else "- none",
        "",
        "## V601 Counts",
        "",
        base.markdown_table(["name", "count"], count_rows) if count_rows else "- none",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v596_build_manifest(args, store)
    live = manifest.get("live") or {}
    service_manager = live.get("service_manager") or {}
    service_manager_executed = (
        bool(live.get("companion_executed"))
        and service_manager.get("with_service_manager") == "1"
        and service_manager.get("with_vnd_service_manager") == "1"
    )
    manifest["service_manager_start_executed"] = service_manager_executed
    manifest["copy_real_linkerconfig_executed"] = bool(live) and service_manager.get("linkerconfig_mode") == "copy-real"
    manifest["explicitly_approved"] = [
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, cnss-daemon start-only inside bounded private namespace",
        "WLFW QRTR nameservice readback without QMI payload",
        "reboot cleanup boundary after live proof",
    ] if args.command == "run" and base.approved(args) else []
    manifest["explicitly_not_approved"] = [
        "Wi-Fi HAL, wificond, supplicant, or hostapd start",
        "qcwlanstate or sysfs driver-state writes",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "boot image changes or partition writes",
    ]
    return manifest


base.capture_preflight = capture_preflight
base.build_checks = build_checks
base.companion_command = companion_command
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
