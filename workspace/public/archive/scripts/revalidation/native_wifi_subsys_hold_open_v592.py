#!/usr/bin/env python3
"""V592 bounded native subsystem char-device hold-open proof.

This proof creates temporary subsystem char-device nodes inside the helper's
private Android-like namespace, opens them from a chrooted child, holds the
file descriptors briefly, and observes whether modem/esoc state or rpmsg/QMI
readiness changes. It does not start service-manager, CNSS daemons, Wi-Fi HAL,
scan/connect/link-up, DHCP, routes, credentials, or external ping.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_start_only_v527 as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v592-subsys-hold-open-proof")
base.DEFAULT_HELPER_SHA256 = "916b5c68a3357c79604db4532b457e30fcb9a70c99aaabb6f95519af138abd29"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v100"
base.HELPER_MODE = "subsys-hold-open-proof"
base.PROOF_VERSION = "V592"
base.PROOF_SLUG = "v592-subsys-hold-open-proof"
base.LIVE_HELPER_STEP_NAME = "v592-helper-run"
base.APPROVAL_PHRASE = (
    "approve v592 subsystem char-device hold-open proof only; "
    "no daemon start, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_BASE_PREFLIGHT_STEPS = base.preflight_steps
_BASE_RUN_LIVE = base.run_live
_BASE_RENDER_SUMMARY = base.render_summary
_BASE_BUILD_MANIFEST = base.build_manifest

SUBSYS_DEV_RE = re.compile(r"^\s*[0-9]+:[0-9]+\s*$")
FOCUS_PREFIXES = (
    "wifi_companion_start.subsys_hold.",
    "wifi_companion_start.surface_subsys_",
    "wifi_companion_start.result",
    "wifi_companion_start.reason",
    "wifi_companion_start.all_postflight_safe",
    "wifi_companion_start.all_observable",
)


def _online(value: str) -> bool:
    return value.strip().upper() == "ONLINE"


def _truthy(value: str) -> bool:
    return value.strip() in {"1", "true", "True", "yes"}


def _key(live_result: dict[str, Any], key: str) -> str:
    return str((live_result.get("keys") or {}).get(key, ""))


def _focus_rows(keys: dict[str, str]) -> list[list[str]]:
    rows = []
    for key in sorted(keys):
        if key.startswith(FOCUS_PREFIXES):
            rows.append([key, keys[key]])
    return rows


def preflight_steps(args: base.argparse.Namespace, store: base.EvidenceStore) -> list[dict[str, Any]]:
    steps = _BASE_PREFLIGHT_STEPS(args, store)
    steps.extend([
        base.run_step(args, store, "mountsystem-ro", ["mountsystem", "ro"], 30.0),
        base.run_step(args, store, "system-root-stat", ["stat", "/mnt/system/system"], 10.0),
        base.run_step(args, store, "subsys-modem-dev", ["cat", "/sys/class/subsys/subsys_modem/dev"], 10.0),
        base.run_step(args, store, "subsys-esoc0-dev", ["cat", "/sys/class/subsys/subsys_esoc0/dev"], 10.0),
        base.run_step(args, store, "mss-subsys-state", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0),
        base.run_step(args, store, "mdm3-subsys-state", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"], 10.0),
        base.run_step(args, store, "rpmsg-devices", ["run", "/cache/bin/toybox", "ls", "/sys/bus/rpmsg/devices"], 10.0),
    ])
    return steps


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = [
        "run", args.helper,
        "--system-root", "/mnt/system/system",
        "--vendor-block", "/dev/block/sda29",
        "--vendor-fstype", "ext4",
        "--mode", base.HELPER_MODE,
        "--null-device-mode", "dev-null",
        "--vndk-apex-alias-mode", "v30-to-system-ext-v30",
        "--linkerconfig-mode", "minimal-vendor",
        "--timeout-sec", str(args.max_runtime_sec),
    ]
    if base.approved(args):
        command.append("--allow-wifi-companion-start-only")
    return command


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    del v490, v525
    checks: list[base.Check] = []
    if args.command == "plan":
        base.add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight")
        return checks

    version = base.step_payload(steps, "version")
    status = base.step_payload(steps, "status")
    selftest = base.step_payload(steps, "selftest")
    helper_sha = base.step_payload(steps, "sha-helper")
    helper_usage = base.step_payload(steps, "helper-usage")
    ps = base.step_payload(steps, "ps")
    netdev = base.step_payload(steps, "proc-net-dev")
    system_root = base.step_payload(steps, "system-root-stat")
    modem_dev = base.step_payload(steps, "subsys-modem-dev").strip()
    esoc_dev = base.step_payload(steps, "subsys-esoc0-dev").strip()
    mss_state = base.step_payload(steps, "mss-subsys-state").strip()
    mdm3_state = base.step_payload(steps, "mdm3-subsys-state").strip()
    rpmsg_devices = base.step_payload(steps, "rpmsg-devices")
    process_hits = [line.strip() for line in ps.splitlines() if base.PROCESS_RE.search(line)]
    helper_hits = [line.strip() for line in ps.splitlines() if "a90_android_execns_probe" in line]
    wifi_hits = [line.strip() for line in netdev.splitlines() if base.WIFI_RE.search(line)]
    helper_ready = (
        args.helper_sha256 in helper_sha
        and args.helper_marker in helper_usage
        and base.HELPER_MODE in helper_usage
    )

    base.add_check(
        checks,
        "native-clean",
        "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked",
        "blocker",
        f"expect_version={args.expect_version}",
        [line for line in version.splitlines() if "A90 Linux init" in line][:2],
        "restore native baseline before V592",
    )
    base.add_check(
        checks,
        "helper-v100-ready",
        "pass" if helper_ready else "blocked",
        "blocker",
        f"sha_match={args.helper_sha256 in helper_sha} marker={args.helper_marker in helper_usage} mode={base.HELPER_MODE in helper_usage}",
        [args.helper_sha256, args.helper_marker, base.HELPER_MODE],
        "deploy helper v100 before V592",
    )
    base.add_check(
        checks,
        "system-root-mounted",
        "pass" if "mode=0755" in system_root or "/mnt/system/system" in system_root else "blocked",
        "blocker",
        "helper namespace requires /mnt/system/system from read-only mountsystem",
        [line for line in system_root.splitlines() if line.strip()][:4],
        "run mountsystem ro before V592",
    )
    base.add_check(
        checks,
        "subsys-cdev-surface",
        "pass" if SUBSYS_DEV_RE.match(modem_dev) and SUBSYS_DEV_RE.match(esoc_dev) else "blocked",
        "blocker",
        f"subsys_modem={modem_dev or 'missing'} subsys_esoc0={esoc_dev or 'missing'}",
        [modem_dev, esoc_dev],
        "do not run V592 until both subsystem cdev majors are visible",
    )
    base.add_check(
        checks,
        "subsys-state-gap-present",
        "pass" if mss_state.upper() in {"OFFLINE", "OFFLINING"} or mdm3_state.upper() in {"OFFLINE", "OFFLINING"} else "warn",
        "warning",
        f"mss={mss_state or 'missing'} mdm3={mdm3_state or 'missing'} rpmsg_has_ipcrtr={'IPCRTR' in rpmsg_devices}",
        [mss_state, mdm3_state],
        "if already ONLINE/IPCRTR-present, move to companion/HAL retry instead of V592",
    )
    base.add_check(
        checks,
        "no-active-execns-helper",
        "pass" if not helper_hits else "blocked",
        "blocker",
        f"helper_count={len(helper_hits)}",
        helper_hits[:8],
        "reboot native init before rerunning V592 if a prior helper is stuck",
    )
    base.add_check(
        checks,
        "no-active-target-processes",
        "pass" if not process_hits else "blocked",
        "blocker",
        f"process_count={len(process_hits)}",
        process_hits[:8],
        "cleanup residual companion/Wi-Fi processes before V592",
    )
    base.add_check(
        checks,
        "no-wifi-link-surface",
        "pass" if not wifi_hits else "blocked",
        "blocker",
        f"wifi_hits={len(wifi_hits)}",
        wifi_hits[:8],
        "if wlan0 already exists, move to scan-only instead of V592",
    )
    return checks


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _BASE_RUN_LIVE(args, store)
    keys = result.get("keys") or {}
    result["focus_keys"] = _focus_rows(keys)
    result["mss_state_before"] = keys.get("wifi_companion_start.subsys_hold.before.mss_state", "")
    result["mdm3_state_before"] = keys.get("wifi_companion_start.subsys_hold.before.mdm3_state", "")
    result["mss_state_hold"] = keys.get("wifi_companion_start.subsys_hold.hold.mss_state", "")
    result["mdm3_state_hold"] = keys.get("wifi_companion_start.subsys_hold.hold.mdm3_state", "")
    result["mss_state_after"] = keys.get("wifi_companion_start.subsys_hold.after.mss_state", "")
    result["mdm3_state_after"] = keys.get("wifi_companion_start.subsys_hold.after.mdm3_state", "")
    result["subsys_any_open"] = keys.get("wifi_companion_start.subsys_hold.any_open") == "1"
    result["rpmsg_ipcrtr_hold"] = keys.get("wifi_companion_start.subsys_hold.hold.rpmsg_ipcrtr_present") == "1"
    result["rpmsg_ipcrtr_after"] = keys.get("wifi_companion_start.subsys_hold.after.rpmsg_ipcrtr_present") == "1"
    result["readiness_delta"] = (
        _online(result["mss_state_hold"])
        or _online(result["mdm3_state_hold"])
        or _online(result["mss_state_after"])
        or _online(result["mdm3_state_after"])
        or result["rpmsg_ipcrtr_hold"]
        or result["rpmsg_ipcrtr_after"]
    )
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v592-subsys-hold-open-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v100, run preflight, then bounded V592 live proof",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return (
            "v592-subsys-hold-open-blocked",
            False,
            "blocked before live run by " + ", ".join(blocked),
            "resolve blockers before V592",
            False,
        )
    if args.command == "preflight":
        return (
            "v592-subsys-hold-open-preflight-ready",
            True,
            "read-only preflight ready; live run still needs exact approval",
            "run approved V592 subsystem hold-open proof",
            False,
        )
    if not base.approved(args):
        return (
            "v592-subsys-hold-open-approval-required",
            True,
            "exact approval phrase required; no live command executed",
            "rerun with exact V592 approval",
            False,
        )
    if not live_result:
        return ("v592-subsys-hold-open-review-required", False, "missing live result", "inspect runner failure", True)
    if not live_result.get("all_postflight_safe"):
        return (
            "v592-subsys-hold-open-cleanup-review",
            False,
            "temporary subsystem hold child was not proven cleaned",
            "inspect evidence and consider recovery reboot",
            True,
        )

    keys = live_result.get("keys") or {}
    helper_result = live_result.get("helper_result")
    readiness_markers = dmesg.get("readiness_markers") or []
    if readiness_markers or live_result.get("readiness_delta"):
        markers = ",".join(readiness_markers) if readiness_markers else "subsys-online-or-rpmsg-ipcrtr"
        return (
            "v592-subsys-hold-readiness-delta",
            True,
            "temporary subsystem cdev hold-open changed lower readiness surface: " + markers,
            "advance to bounded companion/CNSS retry; still no scan/connect until next gate",
            True,
        )
    if helper_result == "subsys-hold-open-failed" or not _truthy(str(keys.get("wifi_companion_start.subsys_hold.any_open", "0"))):
        return (
            "v592-subsys-cdev-open-blocked",
            False,
            "temporary subsystem cdev nodes were created but neither open succeeded",
            "inspect modem/esoc open errno and consider Android init trigger delta before daemon retry",
            True,
        )
    if helper_result == "subsys-hold-window-pass":
        return (
            "v592-subsys-hold-no-readiness-delta",
            True,
            "subsystem cdevs opened and cleaned, but modem/esoc stayed non-online and no QRTR/QMI/WLFW marker appeared",
            "compare Android init subsystem triggers beyond cdev open before qcwlanstate/HAL retry",
            True,
        )
    return (
        "v592-subsys-hold-open-review-required",
        False,
        f"helper_result={helper_result}",
        "inspect V592 helper transcript",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _BASE_RENDER_SUMMARY(manifest)
    live = manifest.get("live_result") or {}
    focus_rows = live.get("focus_keys") or []
    extra = "\n".join([
        "## V592 Subsystem Hold-Open",
        "",
        base.markdown_table(["key", "value"], focus_rows[:160]) if focus_rows else "- none",
        "",
        "- forbidden: daemon start, service-manager, Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect/link-up, credentials, DHCP, routes, external ping",
        "",
    ])
    return text.replace("## Evidence\n\n", extra + "## Evidence\n\n")


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _BASE_BUILD_MANIFEST(args, store)
    manifest["daemon_start_executed"] = False
    manifest["wifi_hal_start_executed"] = False
    manifest["scan_connect_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["explicitly_not_approved"] = [
        "service-manager, hwservicemanager, vndservicemanager start",
        "CNSS, diag, Wi-Fi HAL, wificond, supplicant, or hostapd daemon start",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "sysfs state writes, rfkill writes, driver bind/unbind, boot image changes",
    ]
    return manifest


base.preflight_steps = preflight_steps
base.helper_command = helper_command
base.build_checks = build_checks
base.run_live = run_live
base.classify = classify
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
