#!/usr/bin/env python3
"""V1113 combined global-firmware holder + CNSS PM-connect live gate.

V1112 selected a combined gate: keep the V1061 global firmware mounts and a
global `/dev/subsys_modem` holder active, then replay the V1111 CNSS-first PM
observer.  This answers whether the later `pm-service` open of
`/dev/subsys_modem` still blocks once the lower global firmware/holder
precondition is already true.

This runner does not start Wi-Fi HAL, wificond, IWifi, qcwlanstate,
scan/connect, credentials, DHCP/routes, external ping, `/dev/subsys_esoc0`,
eSoC ioctl/control, partition writes, boot image writes, or flash operations.
Cleanup is a bounded reboot, matching the earlier global holder gates.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
import native_wifi_holder_lower_companion_v733 as holder
import native_wifi_pm_connect_path_capture_live_v1110 as v1110
import native_wifi_pm_connect_path_capture_live_v1111 as v1111
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1113-global-firmware-pm-connect-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1113-global-firmware-pm-connect-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "467ea2ef54a7b1ad95d95876ce8a8b5fe90bb4d8c9bfce6360211d6848c874a5"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v209"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1113"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1113/pm-connect-global-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1113/pm-connect-global-tracefs-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1113/pm-connect-global-output.txt"
DEFAULT_HOLD_SEC = 180
DEFAULT_QRTR_RX_TIMEOUT_SEC = 45.0
DEFAULT_QRTR_RX_POLL_SEC = 2.0
PROOF_PREFIX = "/tmp/a90-v1113-"

ORIGINAL_V1106_RUN_LIVE = v1106.run_live


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    return holder.safe_name(value)


def proof_id(args: argparse.Namespace) -> str:
    explicit = getattr(args, "proof_id", None)
    if explicit:
        return safe_name(str(explicit))
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def set_global_defaults(args: argparse.Namespace) -> None:
    if not hasattr(args, "timeout"):
        args.timeout = max(45.0, float(getattr(args, "tcp_timeout", 90.0)))
    if not hasattr(args, "expect_version"):
        args.expect_version = holder.DEFAULT_EXPECT_VERSION
    if not hasattr(args, "hold_sec"):
        args.hold_sec = DEFAULT_HOLD_SEC
    if not hasattr(args, "qrtr_rx_timeout_sec"):
        args.qrtr_rx_timeout_sec = DEFAULT_QRTR_RX_TIMEOUT_SEC
    if not hasattr(args, "qrtr_rx_poll_sec"):
        args.qrtr_rx_poll_sec = DEFAULT_QRTR_RX_POLL_SEC
    if not hasattr(args, "proof_id"):
        args.proof_id = None
    if not hasattr(args, "companion_runtime_sec"):
        args.companion_runtime_sec = holder.DEFAULT_COMPANION_RUNTIME_SEC


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    return holder.step_payload(steps, name)


def active_process_hits(ps_text: str) -> list[str]:
    patterns = (
        "a90-v1113-",
        "a90-v1061-",
        "a90-v731-",
        "a90-v733-",
        "pm-service",
        "pm-proxy",
        "peripheral",
        "cnss-daemon",
        "wificond",
        "android.hardware.wifi",
        "wpa_supplicant",
    )
    return [line.strip() for line in ps_text.splitlines() if any(pattern in line for pattern in patterns)]


def global_preflight_blockers(preflight: dict[str, Any], steps: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if not preflight.get("native_healthy"):
        blockers.append("native-not-healthy")
    if preflight.get("pre_mount_hits") and any(
        preflight["pre_mount_hits"].get(target) for target in mountv.PARTITION_TARGETS.values()
    ):
        blockers.append("firmware-target-already-mounted")
    if not {"apnhlos", "modem"}.issubset(set((preflight.get("partitions") or {}).keys())):
        blockers.append("firmware-partitions-missing")
    if preflight.get("vendor_rootfs_shim_required") and not preflight.get("vendor_rootfs_shim_allowed_target"):
        blockers.append("vendor-shim-not-allowed")
    if not holder.parse_dev(step_payload(steps, "global-subsys-modem-dev")):
        blockers.append("subsys-modem-dev-missing")
    if active_process_hits(step_payload(steps, "global-ps-before")):
        blockers.append("residual-target-process")
    return blockers


def capture_global_preflight(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    holder.run_step(args, store, steps, "global-hide-menu", ["hide"], 10.0)
    mount_args = argparse.Namespace(**vars(args))
    mount_args.command = "preflight"
    preflight_steps: list[dict[str, Any]] = []
    preflight = mountv.capture_preflight(mount_args, store, preflight_steps)
    for item in preflight_steps:
        item["name"] = "global-" + str(item.get("name") or "step")
    steps.extend(preflight_steps)
    holder.run_step(args, store, steps, "global-mountsystem-ro", ["mountsystem", "ro"], 30.0)
    holder.run_step(args, store, steps, "global-proc-mounts-before", ["cat", "/proc/mounts"], 20.0)
    holder.run_step(args, store, steps, "global-firmware-class-path", ["cat", holder.FIRMWARE_CLASS_PATH], 10.0)
    holder.run_step(args, store, steps, "global-subsys-modem-dev", ["cat", holder.SUBSYS_MODEM_DEV], 10.0)
    holder.run_step(args, store, steps, "global-mss-state-before", ["cat", holder.MSS_STATE], 10.0)
    holder.run_step(args, store, steps, "global-mdm3-state-before", ["cat", holder.MDM3_STATE], 10.0)
    holder.run_step(args, store, steps, "global-ps-before", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    return preflight


def start_global_holder(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    preflight: dict[str, Any],
    proof_base: str,
) -> dict[str, Any]:
    before = holder.run_step(args, store, steps, "global-dmesg-before", ["run", args.toybox, "dmesg"], 60.0, proof_base)
    mount_results: list[str] = []
    for name, command, timeout in mountv.build_mount_commands(preflight, proof_base):
        item = holder.run_step(args, store, steps, f"global-{name}", command, timeout, proof_base)
        mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
    holder.run_step(args, store, steps, "global-proc-mounts-mounted", ["cat", "/proc/mounts"], 20.0, proof_base)
    holder.run_step(args, store, steps, "global-firmware-class-path-mounted", ["cat", holder.FIRMWARE_CLASS_PATH], 10.0, proof_base)
    for path in holder.GLOBAL_MODEM_BLOB_PATHS + holder.WLAN_FIRMWARE_PATHS:
        holder.run_step(args, store, steps, f"global-stat-{safe_name(path)}", ["stat", path], 10.0, proof_base)

    dev = holder.parse_dev(step_payload(steps, "global-subsys-modem-dev"))
    if not dev:
        raise RuntimeError("subsys_modem dev missing after global preflight")
    node = f"{proof_base}/subsys_modem"
    status_file = f"{proof_base}/holder.status"
    pid_file = f"{proof_base}/holder.pid"
    script = holder.holder_script(args, node, status_file, pid_file, dev[0], dev[1])
    holder.write_capture(
        store,
        "global-holder-script-redacted",
        script.replace(node, "$PROOF/subsys_modem").replace(proof_base, "$PROOF"),
    )
    holder.run_step(args, store, steps, "global-start-modem-holder", ["run", args.busybox, "sh", "-c", script], 25.0, proof_base)
    holder.run_step(args, store, steps, "global-mss-state-after-holder", ["cat", holder.MSS_STATE], 10.0, proof_base)
    holder.run_step(args, store, steps, "global-mdm3-state-after-holder", ["cat", holder.MDM3_STATE], 10.0, proof_base)
    qrtr_wait = holder.wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""), proof_base)
    return {
        "proof_base": proof_base,
        "mount_results": mount_results,
        "qrtr_rx_wait": qrtr_wait,
    }


def global_summary(
    steps: list[dict[str, Any]],
    setup: dict[str, Any],
    reboot: dict[str, Any] | None,
    observer_executed: bool,
    observer_error: str,
) -> dict[str, Any]:
    mounted = mountv.parse_mounts(step_payload(steps, "global-proc-mounts-mounted"))
    qrtr_services = holder.qrtr_service_counts(step_payload(steps, "proc-net-qrtr-after-observer"))
    dmesg_delta = ""
    before = step_payload(steps, "global-dmesg-before")
    after = step_payload(steps, "global-dmesg-after-observer")
    if before and after:
        dmesg_delta = holder.dmesg_delta(before, after)
    markers = holder.marker_summary(dmesg_delta) if dmesg_delta else {}
    return {
        "proof_base": setup.get("proof_base", ""),
        "mount_results": setup.get("mount_results", []),
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": step_payload(steps, "global-firmware-class-path-mounted").strip(),
        "modem_blob_visible": {
            path: holder.path_exists(step_payload(steps, f"global-stat-{safe_name(path)}"))
            for path in holder.GLOBAL_MODEM_BLOB_PATHS
        },
        "wlan_firmware_visible": {
            path: holder.path_exists(step_payload(steps, f"global-stat-{safe_name(path)}"))
            for path in holder.WLAN_FIRMWARE_PATHS
        },
        "holder_opened": "v731.holder.status=opened" in step_payload(steps, "global-start-modem-holder"),
        "mss_before": step_payload(steps, "global-mss-state-before").strip(),
        "mss_after_holder": step_payload(steps, "global-mss-state-after-holder").strip(),
        "mss_after_observer": step_payload(steps, "global-mss-state-after-observer").strip(),
        "mdm3_before": step_payload(steps, "global-mdm3-state-before").strip(),
        "mdm3_after_holder": step_payload(steps, "global-mdm3-state-after-holder").strip(),
        "mdm3_after_observer": step_payload(steps, "global-mdm3-state-after-observer").strip(),
        "qrtr_rx_wait": setup.get("qrtr_rx_wait", {}),
        "qrtr_services_after_observer": qrtr_services,
        "markers": markers,
        "observer_executed": observer_executed,
        "observer_error": observer_error,
        "reboot_cleanup": reboot or {},
    }


def run_live_with_global_firmware(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    set_global_defaults(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    preflight = capture_global_preflight(args, store, steps)
    blockers = global_preflight_blockers(preflight, steps)
    analysis["global_preflight"] = preflight
    analysis["global_preflight_blockers"] = blockers
    if blockers:
        analysis["global_firmware"] = {"blockers": blockers, "observer_executed": False}
        analysis["tracefs_uprobe"] = {"result": "v1113-global-preflight-blocked"}
        return steps, analysis

    label = proof_id(args)
    proof_base = PROOF_PREFIX + label
    setup: dict[str, Any] = {}
    reboot: dict[str, Any] | None = None
    observer_executed = False
    observer_error = ""
    try:
        setup = start_global_holder(args, store, steps, preflight, proof_base)
        if (setup.get("qrtr_rx_wait") or {}).get("seen"):
            observer_executed = True
            holder.run_step(args, store, steps, "global-hide-before-observer", ["hide"], 10.0, proof_base)
            observer_steps, observer_analysis = ORIGINAL_V1106_RUN_LIVE(args, store)
            steps.extend(observer_steps)
            analysis.update(observer_analysis)
        else:
            analysis["tracefs_uprobe"] = {"result": "v1113-qrtr-rx-not-observed"}
        holder.run_step(args, store, steps, "global-mss-state-after-observer", ["cat", holder.MSS_STATE], 10.0, proof_base)
        holder.run_step(args, store, steps, "global-mdm3-state-after-observer", ["cat", holder.MDM3_STATE], 10.0, proof_base)
        holder.run_step(args, store, steps, "proc-net-qrtr-after-observer", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0, proof_base)
        holder.run_step(args, store, steps, "proc-net-dev-after-observer", ["cat", "/proc/net/dev"], 10.0, proof_base)
        holder.run_step(args, store, steps, "global-dmesg-after-observer", ["run", args.toybox, "dmesg"], 60.0, proof_base)
    except Exception as exc:  # noqa: BLE001 - evidence runner must preserve failure reason
        observer_error = repr(exc)
        analysis.setdefault("tracefs_uprobe", {"result": "v1113-observer-exception", "error": observer_error})
    finally:
        reboot = holder.reboot_and_wait(args, store)

    analysis["global_firmware"] = global_summary(steps, setup, reboot, observer_executed, observer_error)
    return steps, analysis


def patch_defaults() -> None:
    v1111.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1111.LATEST_POINTER = LATEST_POINTER
    v1111.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1111.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1111.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1111.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1111.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1111.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1111.patch_defaults()
    v1106.remote_sha_check = serial_remote_sha_check
    v1106.remote_marker_check = serial_remote_marker_check
    v1106.run_live = run_live_with_global_firmware


def serial_remote_sha_check(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    path: str,
    expected: str,
) -> dict[str, Any]:
    step = holder.run_step(args, store, steps, name, ["run", args.toybox, "sha256sum", path], 30.0)
    text = str(step.get("payload") or "")
    return {"file": step["file"], "ok": expected in text, "expected": expected, "transport": "cmdv1-serial"}


def serial_remote_marker_check(
    args: argparse.Namespace,
    store: EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    step = holder.run_step(args, store, steps, "execns-helper-usage", ["run", args.helper, "--help"], 30.0)
    text = str(step.get("payload") or "")
    return {
        "file": step["file"],
        "marker_ok": args.helper_marker in text,
        "mode_ok": v1106.base.DEFAULT_MODE in text,
        "start_cnss_flag_ok": "--pm-observer-start-cnss-after-provider" in text,
        "start_cnss_before_per_proxy_flag_ok": "--pm-observer-start-cnss-before-per-proxy" in text,
        "transport": "cmdv1-serial",
    }


def cnss_return_values(tracefs: dict[str, Any], label: str) -> list[str]:
    return v1110.cnss_return_values(tracefs, label)


def blocked_open_candidates(contract: dict[str, str]) -> list[dict[str, str]]:
    blocked: list[dict[str, str]] = []
    for item in v1110.path_candidates(contract):
        path = item.get("path_value", "")
        wchan = item.get("wchan", "")
        if path == "/dev/subsys_modem" and "__subsystem_get" in wchan:
            blocked.append(item)
    return blocked


def decide_v1113(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1113-global-firmware-pm-connect-plan-ready",
            True,
            "plan-only; no tracefs write, PM actor, CNSS actor, modem holder, reboot, or Wi-Fi action executed",
            "run V1113 with explicit tracefs/vendor/selinuxfs/PM/CNSS allow flags",
        )

    analysis = manifest.get("analysis") or {}
    global_fw = analysis.get("global_firmware") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    usage = analysis.get("execns_usage") or {}
    blockers = analysis.get("global_preflight_blockers") or []
    register_ret = cnss_return_values(tracefs, "pm_client_register_ret")
    connect_ret = cnss_return_values(tracefs, "pm_client_connect_ret")
    blocked_candidates = blocked_open_candidates(contract)
    candidates = v1110.path_candidates(contract)
    services = global_fw.get("qrtr_services_after_observer") or {}
    marker_counts = (global_fw.get("markers") or {}).get("counts") or {}

    if blockers:
        return ("v1113-global-preflight-blocked", False, f"blockers={blockers}", "clear global firmware preflight blockers")
    if tracefs.get("result") == "v1113-qrtr-rx-not-observed":
        return ("v1113-global-holder-qrtr-rx-missing", False, "global holder did not produce QRTR RX", "restore V1061 lower prerequisite before PM observer")
    if tracefs.get("result") == "v1113-observer-exception":
        return ("v1113-observer-exception", False, str(tracefs.get("error", "")), "inspect preserved observer exception and cleanup state")
    if not global_fw.get("observer_executed"):
        return ("v1113-observer-not-executed", False, f"global={global_fw}", "run only after global holder and QRTR RX are true")
    if not all((global_fw.get("mounted_hits") or {}).values()):
        return ("v1113-global-firmware-mount-missing", False, f"mounted_hits={global_fw.get('mounted_hits')}", "repair global firmware mounts")
    if not global_fw.get("holder_opened"):
        return ("v1113-global-modem-holder-missing", False, "global /dev/subsys_modem holder did not open", "repair holder precondition")
    if "ONLINE" not in {global_fw.get("mss_after_holder"), global_fw.get("mss_after_observer")}:
        return ("v1113-global-holder-mss-not-online", False, f"mss={global_fw}", "do not run PM observer until mss reaches ONLINE")
    if not (global_fw.get("qrtr_rx_wait") or {}).get("seen"):
        return ("v1113-global-holder-qrtr-rx-missing", False, f"qrtr={global_fw.get('qrtr_rx_wait')}", "restore V1061 QRTR RX behavior")
    cleanup = global_fw.get("reboot_cleanup") or {}
    if not (cleanup.get("version_seen") and cleanup.get("status_healthy")):
        return ("v1113-reboot-cleanup-unhealthy", False, f"cleanup={cleanup}", "verify native health before continuing")
    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1113-execns-helper-sha-mismatch", False, "remote execns helper is not v209", "redeploy helper v209")
    if not (
        usage.get("marker_ok")
        and usage.get("mode_ok")
        and usage.get("start_cnss_flag_ok")
        and usage.get("start_cnss_before_per_proxy_flag_ok")
    ):
        return ("v1113-execns-helper-usage-mismatch", False, f"usage={usage}", "redeploy or rebuild helper v209")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1113-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("forbidden_true"):
        return ("v1113-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if contract.get("per_proxy_start_executed") != "0" or contract.get("child.per_proxy.start_skipped") != "1":
        return ("v1113-pre-cnss-per-proxy-not-skipped", False, f"contract={contract}", "repair no-pre-CNSS per_proxy order")
    if "0x0" not in register_ret or "0x0" not in connect_ret:
        return (
            "v1113-global-holder-cnss-pm-connect-not-reproduced",
            True,
            f"global holder succeeded but CNSS PM connect returns were not captured: register_ret={register_ret} connect_ret={connect_ret}",
            "classify pm-service lifetime/readiness under global holder before widening the window",
        )
    if services.get("69") or marker_counts.get("wlfw") or marker_counts.get("wlan0"):
        return (
            "v1113-global-holder-pm-connect-wlfw-advance",
            True,
            "WLFW/service69/wlan0 appeared under combined global holder + CNSS PM-connect gate",
            "capture BDF/fw-ready/interface before any scan/connect",
        )
    if blocked_candidates:
        return (
            "v1113-global-holder-still-subsys-modem-blocked",
            True,
            f"blocked_candidates={blocked_candidates[:8]}",
            "classify why pm-service still blocks in __subsystem_get despite global firmware holder",
        )
    if candidates:
        return (
            "v1113-global-holder-pm-connect-path-changed",
            True,
            f"path_candidates={candidates[:8]}",
            "classify the new PM-connect path before Wi-Fi HAL",
        )
    return (
        "v1113-global-holder-pm-connect-path-not-observed",
        True,
        "CNSS PM connect reproduced but no tagged path candidate was captured",
        "increase sampling around the owner thread or classify whether open returned quickly",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    global_fw = analysis.get("global_firmware") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    counts = (global_fw.get("markers") or {}).get("counts") or {}
    rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    state_rows = [
        ["mounted_hits", json.dumps(global_fw.get("mounted_hits", {}), sort_keys=True)],
        ["holder_opened", global_fw.get("holder_opened", "")],
        ["mss", f"{global_fw.get('mss_before', '')}->{global_fw.get('mss_after_holder', '')}->{global_fw.get('mss_after_observer', '')}"],
        ["mdm3", f"{global_fw.get('mdm3_before', '')}->{global_fw.get('mdm3_after_holder', '')}->{global_fw.get('mdm3_after_observer', '')}"],
        ["qrtr_rx_seen", (global_fw.get("qrtr_rx_wait") or {}).get("seen", "")],
        ["qrtr_services", json.dumps(global_fw.get("qrtr_services_after_observer", {}), sort_keys=True)],
        ["reboot_cleanup", json.dumps(global_fw.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    return "\n".join([
        "# V1113 Global Firmware PM Connect Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{DEFAULT_EXECNS_HELPER_MARKER}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- global_modem_holder_opened: `{manifest['global_modem_holder_opened']}`",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- pm_actor_executed: `{manifest['pm_actor_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Global Holder State",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## PM Connect Path",
        "",
        "```json",
        json.dumps({
            "tracefs_result": tracefs.get("result", ""),
            "register_ret": cnss_return_values(tracefs, "pm_client_register_ret"),
            "connect_ret": cnss_return_values(tracefs, "pm_client_connect_ret"),
            "path_candidates": v1110.path_candidates(contract)[:16],
            "path_errors": v1110.path_errors(contract)[:16],
            "blocked_subsys_modem": blocked_open_candidates(contract)[:16],
            "marker_counts": counts,
        }, indent=2, sort_keys=True),
        "```",
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1106.parse_args()
    set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1113"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1113(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    global_fw = (manifest.get("analysis") or {}).get("global_firmware") or {}
    contract = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {}).get("pm_contract") or {}
    manifest["firmware_mounts_executed"] = bool(global_fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(global_fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(global_fw.get("reboot_cleanup"))
    manifest["cnss_daemon_start_executed"] = contract.get("cnss_daemon_start_executed") == "1"
    manifest["wifi_hal_start_executed"] = contract.get("wifi_hal_start_executed") == "1"
    manifest["scan_connect_executed"] = contract.get("scan_connect_linkup") == "1"
    manifest["external_ping_executed"] = contract.get("external_ping") == "1"
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"global_modem_holder_opened: {manifest['global_modem_holder_opened']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
