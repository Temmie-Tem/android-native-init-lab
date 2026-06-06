#!/usr/bin/env python3
"""V594 global firmware mount plus subsystem PIL retry proof.

This proof temporarily recreates Android's global read-only firmware mounts,
verifies the firmware_class path and modem blob visibility, then runs the
bounded V592 subsystem char-device hold-open proof while those global mounts
are active. It does not start daemons, Wi-Fi HAL, qcwlanstate, scan/connect,
DHCP, routing, credentials, or external ping.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
import native_wifi_subsys_hold_open_v592 as v592  # noqa: F401 - applies V592 base overrides
import native_wifi_companion_start_only_v527 as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v594-global-firmware-subsys-pil-proof")
base.PROOF_VERSION = "V594"
base.PROOF_SLUG = "v594-global-firmware-subsys-pil-proof"
base.LIVE_HELPER_STEP_NAME = "v594-helper-run"
base.APPROVAL_PHRASE = (
    "approve v594 global firmware mount subsystem PIL proof only; "
    "no daemon start, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_V592_PREFLIGHT_STEPS = base.preflight_steps
_V592_BUILD_CHECKS = base.build_checks
_V592_RUN_LIVE = base.run_live
_V592_CLASSIFY = base.classify
_V592_RENDER_SUMMARY = base.render_summary
_V592_BUILD_MANIFEST = base.build_manifest

FIRMWARE_CLASS_PATH = "/vendor/firmware_mnt/image"
GLOBAL_MODEM_BLOB_PATHS = (
    "/vendor/firmware_mnt/image/modem.b00",
    "/vendor/firmware-modem/image/modem.b00",
    "/firmware/image/modem.b00",
)
GLOBAL_FIRMWARE_PATHS = (
    "/vendor/firmware_mnt",
    "/vendor/firmware_mnt/image",
    "/vendor/firmware-modem",
    "/vendor/firmware-modem/image",
    "/firmware",
    "/firmware/image",
)
PIL_FAILURE_RE = re.compile(
    r"firmware state wait timeout|Failed to locate blob modem\.b|Failed to load the segment",
    re.IGNORECASE,
)
PIL_LOAD_RE = re.compile(r"subsys-pil-tz .*modem: loading|Changing subsys fw_name to modem", re.IGNORECASE)
ONLINE_RE = re.compile(r"\bONLINE\b")


def _toybox(args: base.argparse.Namespace) -> str:
    toybox = getattr(args, "toybox", "")
    if not toybox:
        setattr(args, "toybox", mountv.DEFAULT_TOYBOX)
    return getattr(args, "toybox")


def _proof_id() -> str:
    return "v594-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def _step_payload(item: dict[str, Any]) -> str:
    return str(item.get("payload") or "")


def _run_mount_step(args: base.argparse.Namespace,
                    store: base.EvidenceStore,
                    steps: list[dict[str, Any]],
                    name: str,
                    command: list[str],
                    timeout: float) -> dict[str, Any]:
    item = base.run_step(args, store, name, command, timeout)
    steps.append(item)
    return item


def _path_exists(text: str) -> bool:
    lowered = text.lower()
    return "no such file" not in lowered and "errno=2" not in lowered and "not found" not in lowered


def preflight_steps(args: base.argparse.Namespace, store: base.EvidenceStore) -> list[dict[str, Any]]:
    _toybox(args)
    steps = _V592_PREFLIGHT_STEPS(args, store)
    extra: list[dict[str, Any]] = []
    mount_preflight = mountv.capture_preflight(args, store, extra)
    steps.extend(extra)
    steps.extend([
        base.run_step(args, store, "firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0),
        base.run_step(args, store, "pre-proc-mounts-firmware", ["run", _toybox(args), "cat", "/proc/mounts"], 10.0),
    ])
    for path in GLOBAL_FIRMWARE_PATHS + GLOBAL_MODEM_BLOB_PATHS:
        steps.append(base.run_step(args, store, f"pre-stat-{base.safe_name(path)}", ["stat", path], 8.0))
    steps.append({
        "name": "v594-mount-preflight-summary",
        "command": "host-summarize V584 mount preflight",
        "rc": 0,
        "status": "ok",
        "duration": 0.0,
        "file": base.write_capture(store, "v594-mount-preflight-summary", base.json.dumps(mount_preflight, indent=2, sort_keys=True)),
        "payload": base.json.dumps(mount_preflight, indent=2, sort_keys=True),
    })
    return steps


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _V592_BUILD_CHECKS(args, steps, v490, v525)
    if args.command == "plan":
        return checks

    firmware_path = base.step_payload(steps, "firmware-class-path").strip()
    mount_summary_raw = base.step_payload(steps, "v594-mount-preflight-summary")
    try:
        mount_preflight = base.json.loads(mount_summary_raw) if mount_summary_raw else {}
    except base.json.JSONDecodeError:
        mount_preflight = {}
    parts = mount_preflight.get("partitions") or {}
    pre_hits = mount_preflight.get("pre_mount_hits") or {}
    already_mounted = [target for target in mountv.PARTITION_TARGETS.values() if pre_hits.get(target)]
    shim_required = bool(mount_preflight.get("vendor_rootfs_shim_required"))
    shim_allowed = bool(mount_preflight.get("vendor_rootfs_shim_allowed_target"))

    base.add_check(
        checks,
        "firmware-class-path-android-equivalent",
        "pass" if firmware_path == FIRMWARE_CLASS_PATH else "blocked",
        "blocker",
        f"path={firmware_path or 'missing'}",
        [firmware_path],
        "preserve Android-equivalent firmware_class path before PIL retry",
    )
    base.add_check(
        checks,
        "vfat-supported-for-global-firmware",
        "pass" if mount_preflight.get("vfat_supported") else "blocked",
        "blocker",
        f"vfat_supported={mount_preflight.get('vfat_supported')}",
        [],
        "kernel must support read-only vfat firmware mounts",
    )
    base.add_check(
        checks,
        "apnhlos-modem-partitions-resolved",
        "pass" if "apnhlos" in parts and "modem" in parts else "blocked",
        "blocker",
        f"apnhlos={parts.get('apnhlos')} modem={parts.get('modem')}",
        [],
        "resolve firmware partitions before V594 live proof",
    )
    base.add_check(
        checks,
        "global-firmware-targets-not-mounted",
        "pass" if not already_mounted else "blocked",
        "blocker",
        f"already_mounted={already_mounted}",
        sum((mount_preflight.get("pre_mount_lines") or {}).values(), []),
        "inspect existing mount state before temporary V594 mount",
    )
    base.add_check(
        checks,
        "vendor-rootfs-shim-safe-for-global-mount",
        "pass" if not shim_required or shim_allowed else "blocked",
        "blocker",
        f"required={shim_required} target={mount_preflight.get('vendor_symlink_target')} allowed={shim_allowed}",
        [],
        "only replace /vendor when it is the known native symlink",
    )
    return checks


def _summarize_global_firmware(steps: list[dict[str, Any]],
                               cleanup_results: list[str],
                               base_dir: str) -> dict[str, Any]:
    mounted_mounts = mountv.parse_mounts(base.step_payload(steps, "v594-mounted-proc-mounts"))
    post_mounts = mountv.parse_mounts(base.step_payload(steps, "v594-post-proc-mounts"))
    firmware_path = base.step_payload(steps, "v594-mounted-firmware-class-path").strip()
    stat_texts = {
        path: base.step_payload(steps, f"v594-mounted-stat-{base.safe_name(path)}")
        for path in GLOBAL_MODEM_BLOB_PATHS
    }
    return {
        "base": base_dir,
        "firmware_class_path": firmware_path,
        "firmware_class_path_ok": firmware_path == FIRMWARE_CLASS_PATH,
        "mounted_hits": {target: target in mounted_mounts for target in mountv.PARTITION_TARGETS.values()},
        "post_mount_hits": {target: target in post_mounts for target in mountv.PARTITION_TARGETS.values()},
        "modem_blob_visible": {path: _path_exists(text) for path, text in stat_texts.items()},
        "cleanup_results": cleanup_results,
    }


def _run_global_mount(args: base.argparse.Namespace,
                      store: base.EvidenceStore,
                      steps: list[dict[str, Any]]) -> tuple[dict[str, Any], str | None]:
    _toybox(args)
    preflight_steps_for_mount: list[dict[str, Any]] = []
    mount_preflight = mountv.capture_preflight(args, store, preflight_steps_for_mount)
    steps.extend(preflight_steps_for_mount)
    base_dir = mountv.PROOF_BASE_PREFIX.replace("v584", "v594") + _proof_id()
    vendor_symlink_target = mount_preflight.get("vendor_symlink_target")
    for name, command, timeout in mountv.build_mount_commands(mount_preflight, base_dir):
        _run_mount_step(args, store, steps, f"v594-{name}", command, timeout)
    _run_mount_step(args, store, steps, "v594-mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0)
    _run_mount_step(args, store, steps, "v594-mounted-firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0)
    for path in GLOBAL_FIRMWARE_PATHS + GLOBAL_MODEM_BLOB_PATHS:
        _run_mount_step(args, store, steps, f"v594-mounted-stat-{base.safe_name(path)}", ["stat", path], 10.0)
    return mount_preflight, vendor_symlink_target


def _cleanup_global_mount(args: base.argparse.Namespace,
                          store: base.EvidenceStore,
                          steps: list[dict[str, Any]],
                          base_dir: str,
                          vendor_symlink_target: str | None) -> list[str]:
    cleanup_results: list[str] = []
    for name, command, timeout in mountv.build_cleanup_commands(base_dir, vendor_symlink_target):
        item = _run_mount_step(args, store, steps, f"v594-{name}", command, timeout)
        cleanup_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
    _run_mount_step(args, store, steps, "v594-post-proc-mounts", ["cat", "/proc/mounts"], 20.0)
    _run_mount_step(args, store, steps, "v594-post-ls-vendor-links", ["run", _toybox(args), "ls", "-ld", "/vendor", "/mnt/system/vendor", "/system/vendor"], 20.0)
    _run_mount_step(args, store, steps, "v594-post-status", ["status"], 25.0)
    return cleanup_results


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    _toybox(args)
    mount_steps: list[dict[str, Any]] = []
    cleanup_results: list[str] = []
    global_summary: dict[str, Any] = {}
    base_dir = ""
    vendor_symlink_target: str | None = None
    live_result: dict[str, Any] | None = None
    try:
        mount_preflight, vendor_symlink_target = _run_global_mount(args, store, mount_steps)
        base_dir = mountv.PROOF_BASE_PREFIX.replace("v584", "v594") + _proof_id()
        for step in mount_steps:
            if str(step.get("name")) == "v594-mkdir-proof-base":
                command = step.get("command")
                if isinstance(command, list) and len(command) >= 2:
                    base_dir = str(command[1])
                break
        global_summary = _summarize_global_firmware(mount_steps, [], base_dir)
        live_result = _V592_RUN_LIVE(args, store)
        live_result["mount_preflight"] = mount_preflight
        live_result["global_firmware"] = global_summary
        live_result["global_mount_steps"] = mount_steps
        return live_result
    finally:
        if mount_steps:
            if not base_dir:
                for step in mount_steps:
                    command = step.get("command")
                    if isinstance(command, list) and len(command) >= 2 and command[0] == "mkdir":
                        base_dir = str(command[1])
                        break
            cleanup_results = _cleanup_global_mount(args, store, mount_steps, base_dir, vendor_symlink_target)
            global_summary = _summarize_global_firmware(mount_steps, cleanup_results, base_dir)
            if live_result is not None:
                live_result["global_firmware"] = global_summary
                live_result["global_mount_steps"] = mount_steps


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    if args.command in {"plan", "preflight"}:
        decision, pass_ok, reason, next_step, live_executed = _V592_CLASSIFY(args, checks, live_result, dmesg)
        return (
            decision.replace("v592-subsys", "v594-global-firmware-subsys").replace("V592", "V594"),
            pass_ok,
            reason.replace("V592", "V594"),
            next_step.replace("V592", "V594"),
            live_executed,
        )
    blocked = base.blockers(checks)
    if blocked:
        return (
            "v594-global-firmware-subsys-pil-blocked",
            False,
            "blocked before live run by " + ", ".join(blocked),
            "resolve blockers before global firmware PIL proof",
            False,
        )
    if not base.approved(args):
        return (
            "v594-global-firmware-subsys-pil-approval-required",
            True,
            "exact approval phrase required; no live command executed",
            "rerun with exact V594 approval",
            False,
        )
    if not live_result:
        return (
            "v594-global-firmware-subsys-pil-review-required",
            False,
            "missing live result",
            "inspect runner failure",
            True,
        )

    global_fw = live_result.get("global_firmware") or {}
    mounted_hits = global_fw.get("mounted_hits") or {}
    post_hits = global_fw.get("post_mount_hits") or {}
    modem_visible = global_fw.get("modem_blob_visible") or {}
    if not global_fw.get("firmware_class_path_ok"):
        return (
            "v594-firmware-class-path-mismatch",
            False,
            f"firmware_class path={global_fw.get('firmware_class_path')}",
            "restore Android-equivalent firmware_class path before PIL retry",
            True,
        )
    if not all(mounted_hits.get(target) for target in mountv.PARTITION_TARGETS.values()):
        return (
            "v594-global-firmware-mount-incomplete",
            False,
            f"mounted_hits={mounted_hits}",
            "fix global read-only firmware mounts before subsystem PIL retry",
            True,
        )
    if not any(modem_visible.values()):
        return (
            "v594-global-modem-blob-not-visible",
            False,
            f"modem_blob_visible={modem_visible}",
            "inspect firmware-modem mount contents and Android fstab path parity",
            True,
        )
    if any(post_hits.get(target) for target in mountv.PARTITION_TARGETS.values()):
        return (
            "v594-global-firmware-cleanup-review",
            False,
            f"post_mount_hits={post_hits}",
            "reboot or manually unmount temporary firmware mounts before continuing",
            True,
        )

    dmesg_delta = str(live_result.get("dmesg_delta") or "")
    pil_failure = bool(PIL_FAILURE_RE.search(dmesg_delta))
    pil_load = bool(PIL_LOAD_RE.search(dmesg_delta))
    if not live_result.get("all_postflight_safe"):
        return (
            "v594-global-firmware-subsys-cleanup-review",
            False,
            "temporary subsystem hold child was not proven cleaned",
            "inspect evidence and consider recovery reboot before further live tests",
            True,
        )

    readiness_markers = dmesg.get("readiness_markers") or []
    online_delta = any(
        ONLINE_RE.search(str(live_result.get(key) or ""))
        for key in ("mss_state_hold", "mdm3_state_hold", "mss_state_after", "mdm3_state_after")
    )
    if readiness_markers or online_delta or live_result.get("readiness_delta"):
        markers = ",".join(readiness_markers) if readiness_markers else "subsys-online-or-rpmsg-ipcrtr"
        return (
            "v594-global-firmware-subsys-readiness-delta",
            True,
            "global firmware mount plus subsystem open changed lower readiness surface: " + markers,
            "advance to bounded companion/CNSS retry; still no scan/connect until next gate",
            True,
        )
    if pil_failure:
        return (
            "v594-pil-load-still-fails-with-global-modem-visible",
            True,
            "PIL modem load still reports firmware/segment failures even with global firmware mounts and modem blob visibility",
            "compare Android ueventd firmware loading path and firmware fallback order before daemon/HAL retry",
            True,
        )
    if pil_load:
        return (
            "v594-pil-load-no-readiness-delta",
            True,
            "PIL modem load path was reached with global firmware mounts, but no QRTR/QMI/WLFW readiness marker appeared",
            "inspect dmesg delta for next missing modem readiness dependency",
            True,
        )
    return (
        "v594-global-firmware-subsys-no-pil-delta",
        True,
        "global firmware mounts were visible, but subsystem open did not produce a new PIL/readiness delta",
        "inspect subsystem state and Android trigger ordering before retrying companions",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _V592_RENDER_SUMMARY(manifest).replace("V592", "V594")
    live = manifest.get("live_result") or {}
    global_fw = live.get("global_firmware") or {}
    rows = [[key, value] for key, value in sorted(global_fw.items())]
    extra = "\n".join([
        "## V594 Global Firmware Mount",
        "",
        base.markdown_table(["key", "value"], rows) if rows else "- none",
        "",
        "- forbidden: daemon start, service-manager, Wi-Fi HAL, qcwlanstate, wificond, supplicant, hostapd, scan/connect/link-up, credentials, DHCP, routes, external ping",
        "",
    ])
    return text.replace("## V594 Subsystem Hold-Open\n\n", extra + "## V594 Subsystem Hold-Open\n\n")


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _V592_BUILD_MANIFEST(args, store)
    manifest["daemon_start_executed"] = False
    manifest["wifi_hal_start_executed"] = False
    manifest["wlan_driver_state_write_executed"] = False
    manifest["scan_connect_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["explicitly_not_approved"] = [
        "service-manager, hwservicemanager, vndservicemanager start",
        "CNSS, diag, Wi-Fi HAL, wificond, supplicant, or hostapd daemon start",
        "qcwlanstate or sysfs driver-state writes",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "boot image changes or partition writes",
    ]
    return manifest


base.preflight_steps = preflight_steps
base.build_checks = build_checks
base.run_live = run_live
base.classify = classify
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
