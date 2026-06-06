#!/usr/bin/env python3
"""V1061 global-firmware PM full-contract live classifier.

V1055 ran the PM full-contract-with-modem-holder helper, but its modem
pre-holder lived inside the helper private root while the kernel PIL loader
still required global `/vendor/firmware_mnt/image` visibility.  V1059/V1060
proved that the global firmware mounts can be refreshed and that a global
`/dev/subsys_modem` holder restores QRTR TX/sysmon.

This runner combines those facts:

    global firmware mounts -> global subsys_modem holder -> QRTR RX
      -> helper v180 PM full-contract-with-modem-holder

It intentionally does not start Wi-Fi HAL, wificond, IWifi, qcwlanstate,
scan/connect, credentials, DHCP/routes, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
import native_wifi_holder_lower_companion_v733 as holder
import native_wifi_pm_full_contract_with_modem_holder_live_v1055 as v1055


DEFAULT_OUT_DIR = Path("tmp/wifi/v1061-global-firmware-pm-full-contract")
DEFAULT_V490_MANIFEST = Path("tmp/wifi/v1061-v490-policy-load/manifest.json")
DEFAULT_V1055_MANIFEST = Path("tmp/wifi/v1055-pm-full-contract-with-modem-holder-live/manifest.json")
DEFAULT_V1060_MANIFEST = Path("tmp/wifi/v1060-current-cnss-only-observer/manifest.json")
HELPER_SHA256_V180 = "f260583dc99cc65390ffb719ba0c2618cbbbc25a523f0b1e4fc0a07e93df9641"
HELPER_MARKER_V180 = "a90_android_execns_probe v180"
PROOF_PREFIX = "/tmp/a90-v1061-"
SERVICE_MANAGER_ORDER = "after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder"
SUBSYS_TRIGGER_GATE = "wlfw-precondition"
LATEST_POINTER = Path("tmp/wifi/latest-v1061-global-firmware-pm-full-contract.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=holder.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=holder.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=holder.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=holder.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=holder.DEFAULT_BUSYBOX_PATH)
    parser.add_argument("--helper", default=holder.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=HELPER_SHA256_V180)
    parser.add_argument("--helper-marker", default=HELPER_MARKER_V180)
    parser.add_argument("--expect-version", default=holder.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--property-root", default=v1055.v1032.DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--helper-timeout-sec", type=int, default=30)
    parser.add_argument("--toybox-timeout-sec", type=int, default=180)
    parser.add_argument("--hold-sec", type=int, default=holder.DEFAULT_HOLD_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=holder.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=holder.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--service-manager-order", choices=(SERVICE_MANAGER_ORDER,), default=SERVICE_MANAGER_ORDER)
    parser.add_argument("--subsys-trigger-gate", choices=(SUBSYS_TRIGGER_GATE,), default=SUBSYS_TRIGGER_GATE)
    parser.add_argument("--v490-manifest", type=Path, default=DEFAULT_V490_MANIFEST)
    parser.add_argument("--v1055-manifest", type=Path, default=DEFAULT_V1055_MANIFEST)
    parser.add_argument("--v1060-manifest", type=Path, default=DEFAULT_V1060_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def configure_holder() -> None:
    holder.PROOF_PREFIX = PROOF_PREFIX
    holder.helper_command = helper_command


def helper_command(args: argparse.Namespace) -> list[str]:
    return v1055.helper_command(args)


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return holder.safe_name(args.proof_id)
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def load_json(path: Path) -> dict[str, Any]:
    return holder.load_json_if_exists(path)


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    return holder.step_payload(steps, name)


def capture_preflight(
    args: argparse.Namespace,
    store: holder.EvidenceStore,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    holder.run_step(args, store, steps, "hide-menu", ["hide"], 10.0)
    mount_args = argparse.Namespace(**vars(args))
    mount_args.command = "preflight"
    preflight_steps: list[dict[str, Any]] = []
    preflight = mountv.capture_preflight(mount_args, store, preflight_steps)
    steps.extend(preflight_steps)
    holder.run_step(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], 30.0)
    holder.run_step(args, store, steps, "proc-mounts", ["cat", "/proc/mounts"], 20.0)
    holder.run_step(args, store, steps, "selinux-status", ["stat", "/sys/fs/selinux/status"], 10.0)
    holder.run_step(args, store, steps, "helper-sha", ["run", args.toybox, "sha256sum", args.helper], 15.0)
    holder.run_step(args, store, steps, "helper-usage", ["run", args.helper, "--help"], 25.0)
    holder.run_step(args, store, steps, "firmware-class-path", ["cat", holder.FIRMWARE_CLASS_PATH], 10.0)
    holder.run_step(args, store, steps, "subsys-modem-dev", ["cat", holder.SUBSYS_MODEM_DEV], 10.0)
    holder.run_step(args, store, steps, "mss-state-before", ["cat", holder.MSS_STATE], 10.0)
    holder.run_step(args, store, steps, "mss-crash-before", ["cat", holder.MSS_CRASH_COUNT], 10.0)
    holder.run_step(args, store, steps, "mdm3-state-before", ["cat", holder.MDM3_STATE], 10.0)
    holder.run_step(args, store, steps, "mdm3-crash-before", ["cat", holder.MDM3_CRASH_COUNT], 10.0)
    holder.run_step(args, store, steps, "ps-before", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    return preflight


def helper_ready(args: argparse.Namespace, steps: list[dict[str, Any]]) -> bool:
    sha = step_payload(steps, "helper-sha")
    usage = step_payload(steps, "helper-usage")
    return (
        args.helper_sha256 in sha
        and args.helper_marker in usage
        and "wifi-companion-mdm-helper-cnss-service-manager-matrix" in usage
        and "--allow-pm-full-contract-with-modem-holder" in usage
        and "--allow-mdm-helper-cnss-service-manager-matrix" in usage
        and SERVICE_MANAGER_ORDER in usage
    )


def preflight_blockers(
    args: argparse.Namespace,
    steps: list[dict[str, Any]],
    preflight: dict[str, Any],
    v490: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if args.expect_version not in step_payload(steps, "version"):
        blockers.append("unexpected-native-version")
    if "fail=0" not in step_payload(steps, "status") or "fail=0" not in step_payload(steps, "selftest"):
        blockers.append("native-not-healthy")
    if preflight.get("pre_mount_hits") and any(preflight["pre_mount_hits"].get(target) for target in mountv.PARTITION_TARGETS.values()):
        blockers.append("firmware-target-already-mounted")
    if not {"apnhlos", "modem"}.issubset(set((preflight.get("partitions") or {}).keys())):
        blockers.append("firmware-partitions-missing")
    if preflight.get("vendor_rootfs_shim_required") and not preflight.get("vendor_rootfs_shim_allowed_target"):
        blockers.append("vendor-shim-not-allowed")
    if "/sys/fs/selinux" not in step_payload(steps, "proc-mounts") or "No such file" in step_payload(steps, "selinux-status"):
        blockers.append("selinuxfs-not-mounted")
    if not helper_ready(args, steps):
        blockers.append("helper-v180-not-ready")
    if not holder.parse_dev(step_payload(steps, "subsys-modem-dev")):
        blockers.append("subsys-modem-dev-missing")
    if holder.active_process_hits(step_payload(steps, "ps-before")):
        blockers.append("residual-target-process")
    if v490.get("decision") != "v490-selinux-policy-load-proof-pass":
        blockers.append("v490-current-policy-load-missing")
    if not (4 <= args.helper_timeout_sec <= 30):
        blockers.append("helper-timeout-out-of-range")
    return blockers


def helper_surface(text: str) -> dict[str, Any]:
    return v1055.v1032.helper_surface(text)


def run_live(
    args: argparse.Namespace,
    store: holder.EvidenceStore,
    steps: list[dict[str, Any]],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    label = proof_id(args)
    proof_base = PROOF_PREFIX + label
    node = f"{proof_base}/subsys_modem"
    status_file = f"{proof_base}/holder.status"
    pid_file = f"{proof_base}/holder.pid"
    before = holder.run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    mount_results: list[str] = []
    helper_item: dict[str, Any] | None = None
    qrtr_wait: dict[str, Any] = {}
    try:
        for name, command, timeout in mountv.build_mount_commands(preflight, proof_base):
            item = holder.run_step(args, store, steps, f"v1061-{name}", command, timeout, proof_base)
            mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
        holder.run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0, proof_base)
        holder.run_step(args, store, steps, "mounted-firmware-class-path", ["cat", holder.FIRMWARE_CLASS_PATH], 10.0, proof_base)
        for path in holder.GLOBAL_MODEM_BLOB_PATHS + holder.WLAN_FIRMWARE_PATHS:
            holder.run_step(args, store, steps, f"mounted-stat-{holder.safe_name(path)}", ["stat", path], 10.0, proof_base)

        dev = holder.parse_dev(step_payload(steps, "subsys-modem-dev"))
        if not dev:
            raise RuntimeError("subsys_modem dev missing after preflight")
        script = holder.holder_script(args, node, status_file, pid_file, dev[0], dev[1])
        holder.write_capture(store, "holder-script-redacted", script.replace(node, "$PROOF/subsys_modem").replace(proof_base, "$PROOF"))
        holder.run_step(args, store, steps, "start-global-modem-holder", ["run", args.busybox, "sh", "-c", script], 25.0, proof_base)
        holder.run_step(args, store, steps, "mss-state-after-holder", ["cat", holder.MSS_STATE], 10.0, proof_base)
        holder.run_step(args, store, steps, "mss-crash-after-holder", ["cat", holder.MSS_CRASH_COUNT], 10.0, proof_base)
        holder.run_step(args, store, steps, "mdm3-state-after-holder", ["cat", holder.MDM3_STATE], 10.0, proof_base)
        holder.run_step(args, store, steps, "mdm3-crash-after-holder", ["cat", holder.MDM3_CRASH_COUNT], 10.0, proof_base)
        qrtr_wait = holder.wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""), proof_base)
        if qrtr_wait.get("seen"):
            helper_item = holder.run_step(args, store, steps, "pm-full-contract-with-global-firmware", helper_command(args), args.toybox_timeout_sec + 20.0, proof_base)
        else:
            helper_item = {
                "name": "pm-full-contract-with-global-firmware",
                "ok": True,
                "rc": 0,
                "status": "skipped",
                "command": " ".join(helper_command(args)),
                "duration_sec": 0,
                "payload": "skipped: QRTR RX marker was not observed\n",
                "file": holder.write_capture(store, "pm-full-contract-skipped", "skipped: QRTR RX marker was not observed\n"),
            }
            steps.append(helper_item)
        holder.run_step(args, store, steps, "mss-state-after-helper", ["cat", holder.MSS_STATE], 10.0, proof_base)
        holder.run_step(args, store, steps, "mdm3-state-after-helper", ["cat", holder.MDM3_STATE], 10.0, proof_base)
        holder.run_step(args, store, steps, "rpmsg-after-helper", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0, proof_base)
        holder.run_step(args, store, steps, "proc-net-qrtr-after-helper", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0, proof_base)
        holder.run_step(args, store, steps, "proc-net-dev-after-helper", ["cat", "/proc/net/dev"], 10.0, proof_base)
        holder.run_step(args, store, steps, "ps-before-reboot", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0, proof_base)
        after = holder.run_step(args, store, steps, "dmesg-after-helper", ["run", args.toybox, "dmesg"], 60.0, proof_base)
        delta = holder.dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
        holder.write_capture(store, "dmesg-delta", delta)
        markers = holder.marker_summary(delta)
    finally:
        reboot = holder.reboot_and_wait(args, store)

    mounted = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    helper_text = str((helper_item or {}).get("payload") or "")
    parsed_helper = helper_surface(helper_text)
    contract = parsed_helper.get("contract") or {}
    return {
        "base": proof_base,
        "mount_results": mount_results,
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": {
            path: holder.path_exists(step_payload(steps, f"mounted-stat-{holder.safe_name(path)}"))
            for path in holder.GLOBAL_MODEM_BLOB_PATHS
        },
        "wlan_firmware_visible": {
            path: holder.path_exists(step_payload(steps, f"mounted-stat-{holder.safe_name(path)}"))
            for path in holder.WLAN_FIRMWARE_PATHS
        },
        "holder_opened": "v731.holder.status=opened" in step_payload(steps, "start-global-modem-holder"),
        "mss_before": step_payload(steps, "mss-state-before").strip(),
        "mss_after_holder": step_payload(steps, "mss-state-after-holder").strip(),
        "mss_after_helper": step_payload(steps, "mss-state-after-helper").strip(),
        "mdm3_before": step_payload(steps, "mdm3-state-before").strip(),
        "mdm3_after_holder": step_payload(steps, "mdm3-state-after-holder").strip(),
        "mdm3_after_helper": step_payload(steps, "mdm3-state-after-helper").strip(),
        "qrtr_rx_wait": qrtr_wait,
        "helper_executed": bool(qrtr_wait.get("seen")),
        "helper_ok": bool((helper_item or {}).get("ok")),
        "helper_status": (helper_item or {}).get("status"),
        "helper_result": parsed_helper,
        "contract": contract,
        "qrtr_services_after_helper": holder.qrtr_service_counts(step_payload(steps, "proc-net-qrtr-after-helper")),
        "markers": markers if "markers" in locals() else {},
        "reboot_cleanup": reboot,
    }


def blocked_checks(checks: list[dict[str, Any]]) -> list[str]:
    return [check["name"] for check in checks if check["status"] == "blocked"]


def int_value(value: Any) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def build_checks(
    args: argparse.Namespace,
    blockers: list[str],
    v490: dict[str, Any],
    v1055: dict[str, Any],
    v1060: dict[str, Any],
    live: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{"name": "plan-only", "status": "pass", "detail": "no device command executed", "next_step": "refresh V401/V490 and run V1061"}]
    checks = [
        {"name": "preflight-blockers", "status": "pass" if not blockers else "blocked", "detail": {"blockers": blockers}, "next_step": "clear blockers before live gate"},
        {"name": "references", "status": "pass" if v490.get("decision") == "v490-selinux-policy-load-proof-pass" and v1055.get("decision") and v1060.get("decision") == "v735-current-cnss-only-sysmon-gap-classified" else "review", "detail": {"v490": v490.get("decision"), "v1055": v1055.get("decision"), "v1060": v1060.get("decision")}, "next_step": "refresh missing references before interpreting V1061"},
    ]
    if not live:
        return checks
    contract = live.get("contract") or {}
    helper = live.get("helper_result") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    forbidden = {
        "wifi_hal_start": contract.get("wifi_hal_start_executed"),
        "wificond": contract.get("wificond_start_executed"),
        "iwifi_start": contract.get("iwifi_start"),
        "qcwlanstate": contract.get("qcwlanstate_write"),
        "scan_connect": contract.get("scan_connect_linkup"),
        "credentials": contract.get("credentials"),
        "dhcp_routing": contract.get("dhcp_routing"),
        "external_ping": contract.get("external_ping"),
        "notify": contract.get("notify_attempted"),
        "boot_done": contract.get("boot_done_attempted"),
    }
    checks.extend([
        {"name": "firmware-mounted", "status": "pass" if all((live.get("mounted_hits") or {}).values()) and any((live.get("modem_blob_visible") or {}).values()) else "blocked", "detail": {"mounted_hits": live.get("mounted_hits"), "modem_blob_visible": live.get("modem_blob_visible")}, "next_step": "fix global firmware mount before PM retry"},
        {"name": "global-modem-holder", "status": "pass" if live.get("holder_opened") and "ONLINE" in {live.get("mss_after_holder"), live.get("mss_after_helper")} and (live.get("qrtr_rx_wait") or {}).get("seen") else "blocked", "detail": {"holder_opened": live.get("holder_opened"), "mss": [live.get("mss_before"), live.get("mss_after_holder"), live.get("mss_after_helper")], "mdm3": [live.get("mdm3_before"), live.get("mdm3_after_holder"), live.get("mdm3_after_helper")], "qrtr_rx": (live.get("qrtr_rx_wait") or {}).get("seen")}, "next_step": "do not run PM full contract without global holder"},
        {"name": "helper-contract", "status": "pass" if contract.get("begin") == "1" and contract.get("allowed") == "1" and contract.get("pm_full_contract_with_modem_holder_matrix") == "1" else "blocked", "detail": {"result": contract.get("result"), "order": contract.get("service_manager_order"), "matrix": contract.get("pm_full_contract_with_modem_holder_matrix"), "guard_blocked": contract.get("runtime_domain_guard_blocked")}, "next_step": "inspect helper transcript"},
        {"name": "forbidden-actions", "status": "pass" if not any(int_value(value) for value in forbidden.values()) and not helper.get("forbidden_true") else "blocked", "detail": forbidden, "next_step": "stop if helper crossed Wi-Fi bring-up boundary"},
        {"name": "pm-full-contract", "status": "pass" if contract.get("pm_full_contract_seen") == "1" else "finding", "detail": {"modem_pre_holder_confirmed": contract.get("modem_pre_holder_confirmed"), "pm_full_contract_seen": contract.get("pm_full_contract_seen"), "pm_proxy_helper_subsys_modem_fd_count": contract.get("pm_proxy_helper_subsys_modem_fd_count"), "per_mgr_subsys_modem_fd_count": contract.get("per_mgr_subsys_modem_fd_count"), "mdm_helper_esoc0_fd_seen": contract.get("mdm_helper_esoc0_fd_seen")}, "next_step": "if missing, classify remaining PM fd/input delta"},
        {"name": "publication-progression", "status": "pass" if counts.get("wlfw") or counts.get("mhi") or counts.get("wlan0") or (live.get("qrtr_services_after_helper") or {}).get("69") else "finding", "detail": {"markers": {key: counts.get(key, 0) for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "wlan_pd", "mhi", "qca6390", "wlfw", "bdf", "wlan0")}, "qrtr_services": live.get("qrtr_services_after_helper")}, "next_step": "if absent, blocker remains SDX50M/eSoC or PM publication below Wi-Fi HAL"},
        {"name": "kernel-warning-review", "status": "blocked" if counts.get("kernel_warning", 0) else "pass", "detail": {"kernel_warning": counts.get("kernel_warning", 0), "first": ((live.get("markers") or {}).get("first_lines") or {}).get("kernel_warning", "")}, "next_step": "do not widen or repeat this gate until the esoc0 reference-count warning path is classified"},
        {"name": "postflight-reboot-cleanup", "status": "pass" if (live.get("reboot_cleanup") or {}).get("version_seen") and (live.get("reboot_cleanup") or {}).get("status_healthy") else "blocked", "detail": live.get("reboot_cleanup"), "next_step": "verify native health before continuing"},
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v1061-global-firmware-pm-full-contract-plan-ready", True, "plan-only; no device command executed", "refresh V401/V490 and run live V1061"
    blocked = blocked_checks(checks)
    if blocked:
        return "v1061-global-firmware-pm-full-contract-blocked", False, "blocked by " + ", ".join(blocked), "clear blocker before retry"
    if not live:
        return "v1061-global-firmware-pm-full-contract-preflight-ready", True, "preflight ready", "run live V1061"
    contract = live.get("contract") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    services = live.get("qrtr_services_after_helper") or {}
    if counts.get("wlan0") or counts.get("wlfw") or services.get("69"):
        return "v1061-global-firmware-pm-full-contract-wlfw-advance", True, "WLFW/service69/wlan0 evidence appeared under PM full contract", "capture BDF/fw-ready/interface before scan/connect"
    if counts.get("mhi") or counts.get("qca6390"):
        return "v1061-global-firmware-pm-full-contract-mhi-advance", True, "MHI/QCA6390 evidence appeared but WLFW did not", "classify MHI-to-WLFW boundary"
    if contract.get("pm_full_contract_seen") == "1":
        return "v1061-global-firmware-pm-full-contract-seen-wlfw-missing", True, "PM fd contract appeared but WLFW/MHI/service69 remained absent", "focus next on SDX50M/eSoC publication trigger"
    if contract.get("modem_pre_holder_confirmed") == "1":
        return "v1061-global-firmware-modem-holder-confirmed-pm-contract-missing", True, "global firmware allowed helper modem pre-holder but PM fd contract stayed missing", "inspect PM actor fd timing before retry"
    return "v1061-global-firmware-modem-pre-holder-gap", True, "global firmware did not make helper modem pre-holder report success", "compare global holder vs helper private holder path"


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    contract = live.get("contract") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    check_rows = [[check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]] for check in manifest.get("checks", [])]
    state_rows = [
        ["mounted_hits", json.dumps(live.get("mounted_hits", {}), sort_keys=True)],
        ["modem_blob_visible", json.dumps(live.get("modem_blob_visible", {}), sort_keys=True)],
        ["holder_opened", live.get("holder_opened", "")],
        ["mss", f"{live.get('mss_before', '')}->{live.get('mss_after_holder', '')}->{live.get('mss_after_helper', '')}"],
        ["mdm3", f"{live.get('mdm3_before', '')}->{live.get('mdm3_after_holder', '')}->{live.get('mdm3_after_helper', '')}"],
        ["contract", json.dumps({key: contract.get(key) for key in ("result", "modem_pre_holder_confirmed", "pm_full_contract_seen", "pm_proxy_helper_subsys_modem_fd_count", "per_mgr_subsys_modem_fd_count", "mdm_helper_esoc0_fd_seen", "wlfw_precondition_observed", "subsys_esoc0_open_attempted")}, sort_keys=True)],
        ["qrtr_services", json.dumps(live.get("qrtr_services_after_helper", {}), sort_keys=True)],
        ["reboot_cleanup", json.dumps(live.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    marker_rows = [[name, str(counts.get(name, 0))] for name in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "wlan_pd", "mhi", "qca6390", "wlfw", "bdf", "wlan0", "kernel_warning")]
    return "\n".join([
        "# V1061 Global Firmware PM Full-Contract",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- global_modem_holder_opened: `{manifest['global_modem_holder_opened']}`",
        f"- pm_proxy_helper_start_executed: `{manifest['pm_proxy_helper_start_executed']}`",
        f"- pm_full_contract_seen: `{manifest['pm_full_contract_seen']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        holder.markdown_table(["name", "status", "detail", "next"], check_rows),
        "",
        "## State Summary",
        "",
        holder.markdown_table(["key", "value"], state_rows),
        "",
        "## Dmesg Marker Counts",
        "",
        holder.markdown_table(["marker", "count"], marker_rows),
    ])


def build_manifest(args: argparse.Namespace, store: holder.EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    v490 = load_json(args.v490_manifest)
    v1055_ref = load_json(args.v1055_manifest)
    v1060_ref = load_json(args.v1060_manifest)
    preflight: dict[str, Any] = {}
    live: dict[str, Any] | None = None
    blockers: list[str] = []
    if args.command == "run":
        preflight = capture_preflight(args, store, steps)
        blockers = preflight_blockers(args, steps, preflight, v490)
        if not blockers:
            live = run_live(args, store, steps, preflight)
    checks = build_checks(args, blockers, v490, v1055_ref, v1060_ref, live)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    contract = (live or {}).get("contract") or {}
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v1061",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": holder.collect_host_metadata(),
        "v490": {"decision": v490.get("decision"), "pass": v490.get("pass"), "path": str(holder.repo_path(args.v490_manifest))},
        "v1055": {"decision": v1055_ref.get("decision"), "pass": v1055_ref.get("pass"), "path": str(holder.repo_path(args.v1055_manifest))},
        "v1060": {"decision": v1060_ref.get("decision"), "pass": v1060_ref.get("pass"), "path": str(holder.repo_path(args.v1060_manifest))},
        "preflight": preflight,
        "steps": steps,
        "checks": checks,
        "live": live or {},
        "device_commands_executed": args.command == "run",
        "firmware_mounts_executed": bool(live),
        "global_modem_holder_opened": bool((live or {}).get("holder_opened")),
        "pm_proxy_helper_start_executed": contract.get("pm_proxy_helper_start_executed") == "1",
        "pm_proxy_start_executed": contract.get("pm_proxy_start_attempted") == "1" or contract.get("pm_proxy_started") == "1",
        "pm_full_contract_seen": contract.get("pm_full_contract_seen") == "1",
        "per_mgr_light_start_executed": contract.get("per_mgr_start_attempted") == "1",
        "mdm_helper_start_executed": contract.get("mdm_helper_start_attempted") == "1",
        "service_manager_start_executed": contract.get("service_manager_start_executed") == "1",
        "cnss_diag_start_executed": contract.get("cnss_diag_start_attempted") == "1" or contract.get("cnss_diag_started") == "1",
        "cnss_daemon_start_executed": contract.get("cnss_daemon_start_attempted") == "1" or contract.get("cnss_daemon_started") == "1",
        "wlfw_precondition_observed": contract.get("wlfw_precondition_observed") == "1",
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "live_esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "wificond_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "reboot_cleanup_executed": bool(live),
    }


def main() -> int:
    configure_holder()
    args = parse_args()
    store = holder.EvidenceStore(holder.repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    holder.write_private_text(holder.repo_path(LATEST_POINTER), str(store.run_dir.relative_to(holder.repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"global_modem_holder_opened: {manifest['global_modem_holder_opened']}")
    print(f"pm_proxy_helper_start_executed: {manifest['pm_proxy_helper_start_executed']}")
    print(f"pm_full_contract_seen: {manifest['pm_full_contract_seen']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
