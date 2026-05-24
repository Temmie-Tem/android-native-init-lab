#!/usr/bin/env python3
"""V797 bounded PIL trace payload capture.

V796 selected payload capture because V782 counted real
msm_pil_event:pil_notif events but did not capture event_name/code/fw_name.
This runner wraps the already-tested V750 lower-window boot_wlan transition
with tracefs enabled only for msm_pil_event:pil_notif, then disables tracing and
reboot-cleans.  It does not start service-manager, Wi-Fi HAL, scan/connect, use
credentials, DHCP/routes, external ping, raw esoc0, bind/unbind, modules, flash,
or custom kernels.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
import native_wifi_holder_lower_companion_v733 as base
import native_wifi_lower_window_boot_wlan_v750 as v750
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v797-pil-trace-payload")
LATEST_POINTER = Path("tmp/wifi/latest-v797-pil-trace-payload.txt")
DEFAULT_TRACEFS_TARGET = "/sys/kernel/tracing"
TRACE_EVENT_ENABLE = f"{DEFAULT_TRACEFS_TARGET}/events/msm_pil_event/pil_notif/enable"
TRACE_EVENT_FORMAT = f"{DEFAULT_TRACEFS_TARGET}/events/msm_pil_event/pil_notif/format"
TRACE_EVENT_ID = f"{DEFAULT_TRACEFS_TARGET}/events/msm_pil_event/pil_notif/id"
TRACE_FILE = f"{DEFAULT_TRACEFS_TARGET}/trace"
TRACING_ON = f"{DEFAULT_TRACEFS_TARGET}/tracing_on"
PROOF_PREFIX = "/tmp/a90-v797-"

FORBIDDEN_TERMS = v750.FORBIDDEN_TERMS + (
    "trace_marker",
    "set_ftrace_filter",
    "set_graph_function",
    "function_graph",
    "function ",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v750.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v750.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v750.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=v750.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=v750.DEFAULT_BUSYBOX)
    parser.add_argument("--helper", default=v750.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=v750.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=v750.DEFAULT_HELPER_MARKER)
    parser.add_argument("--wlanbootctl", default=v750.DEFAULT_WLANBOOTCTL)
    parser.add_argument("--wlanbootctl-sha256", default=v750.DEFAULT_WLANBOOTCTL_SHA256)
    parser.add_argument("--wlanbootctl-marker", default=v750.DEFAULT_WLANBOOTCTL_MARKER)
    parser.add_argument("--expect-version", default=v750.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=v750.DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=v750.DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--boot-observe-sec", type=int, default=v750.DEFAULT_BOOT_OBSERVE_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=base.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=base.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=v750.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=v750.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v490-manifest", type=Path, default=v750.DEFAULT_V490_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("--allow-tracefs-mount", action="store_true")
    parser.add_argument("--allow-trace-control-write", action="store_true")
    parser.add_argument("--allow-lower-window-boot-wlan", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return v750.safe_name(value)


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return safe_name(args.proof_id)
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    return base.step_payload(steps, name)


def tracefs_mounted(text: str) -> bool:
    return re.search(rf"\s{re.escape(DEFAULT_TRACEFS_TARGET)}\s+tracefs\s", text) is not None


def shell_cmd(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def validate_device_command(args: argparse.Namespace,
                            command: list[str],
                            proof_base: str | None = None,
                            allow_trace_mount: bool = False,
                            allow_trace_write: bool = False) -> None:
    joined = " ".join(command)
    lowered = joined.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in lowered:
            raise RuntimeError(f"forbidden V797 command term {term!r}: {joined}")
    if command == ["run", args.busybox, "mount", "-t", "tracefs", "tracefs", DEFAULT_TRACEFS_TARGET]:
        if not allow_trace_mount:
            raise RuntimeError("tracefs mount requires explicit V797 allow flag")
        return
    if command == ["run", args.busybox, "umount", DEFAULT_TRACEFS_TARGET]:
        if not allow_trace_mount:
            raise RuntimeError("tracefs umount requires explicit V797 allow flag")
        return
    if command[:2] == ["run", args.busybox] and len(command) >= 4 and command[2] == "sh":
        script = command[-1]
        if DEFAULT_TRACEFS_TARGET in script or TRACE_EVENT_ENABLE in script or TRACE_FILE in script or TRACING_ON in script:
            if not allow_trace_write:
                raise RuntimeError("trace control writes require explicit V797 allow flag")
            allowed_fragments = (
                TRACE_EVENT_ENABLE,
                TRACE_EVENT_FORMAT,
                TRACE_EVENT_ID,
                TRACE_FILE,
                TRACING_ON,
                "pil_notif",
                "v797.trace",
            )
            if any(fragment in script for fragment in allowed_fragments):
                return
        if proof_base and proof_base in script:
            return
    try:
        v750.validate_device_command(args, command, proof_base)
    except RuntimeError as exc:
        raise RuntimeError(f"unexpected V797 command: {joined}") from exc


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             proof_base: str | None = None,
             allow_trace_mount: bool = False,
             allow_trace_write: bool = False) -> dict[str, Any]:
    validate_device_command(args, command, proof_base, allow_trace_mount, allow_trace_write)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    steps.append(item)
    return item


def trace_setup_script(args: argparse.Namespace) -> str:
    return (
        f"BB={args.busybox}; T={DEFAULT_TRACEFS_TARGET}; E={TRACE_EVENT_ENABLE}; "
        "printf 'v797.trace_setup.begin=1\\n'; "
        "[ -r \"" + TRACE_EVENT_ID + "\" ] && printf 'v797.tracepoint_id=' && $BB cat \"" + TRACE_EVENT_ID + "\" || printf 'v797.tracepoint_id=missing\\n'; "
        "printf '--- pil_notif_format_begin ---\\n'; $BB cat \"" + TRACE_EVENT_FORMAT + "\" 2>&1 || true; printf '--- pil_notif_format_end ---\\n'; "
        "printf 0 > \"" + TRACING_ON + "\"; "
        "printf 0 > \"$E\"; "
        ": > \"" + TRACE_FILE + "\"; "
        "printf 1 > \"$E\"; "
        "printf 1 > \"" + TRACING_ON + "\"; "
        "printf 'v797.trace_setup.done=1\\n'; "
        "printf 'v797.trace_event_enable='; $BB cat \"$E\" 2>&1 || true; "
        "printf 'v797.tracing_on='; $BB cat \"" + TRACING_ON + "\" 2>&1 || true"
    )


def trace_collect_script(args: argparse.Namespace) -> str:
    return (
        f"BB={args.busybox}; E={TRACE_EVENT_ENABLE}; "
        "printf 0 > \"" + TRACING_ON + "\" 2>/dev/null || true; "
        "printf 0 > \"$E\" 2>/dev/null || true; "
        "printf 'v797.trace_collect.begin=1\\n'; "
        "printf 'v797.trace_event_enable='; $BB cat \"$E\" 2>&1 || true; "
        "printf 'v797.tracing_on='; $BB cat \"" + TRACING_ON + "\" 2>&1 || true; "
        "printf '--- pil_trace_begin ---\\n'; "
        "$BB cat \"" + TRACE_FILE + "\" 2>&1 | $BB head -n 500; "
        "printf '--- pil_trace_end ---\\n'; "
        ": > \"" + TRACE_FILE + "\" 2>/dev/null || true; "
        "printf 'v797.trace_collect.done=1\\n'"
    )


def trace_cleanup_script(args: argparse.Namespace) -> str:
    return (
        f"BB={args.busybox}; E={TRACE_EVENT_ENABLE}; "
        "printf 0 > \"" + TRACING_ON + "\" 2>/dev/null || true; "
        "printf 0 > \"$E\" 2>/dev/null || true; "
        ": > \"" + TRACE_FILE + "\" 2>/dev/null || true; "
        "printf 'v797.trace_cleanup.done=1\\n'; "
        "printf 'v797.trace_event_enable='; $BB cat \"$E\" 2>&1 || true; "
        "printf 'v797.tracing_on='; $BB cat \"" + TRACING_ON + "\" 2>&1 || true"
    )


def parse_trace_payload(text: str) -> dict[str, Any]:
    in_trace = False
    lines: list[str] = []
    events: list[dict[str, str]] = []
    for raw in text.splitlines():
        if raw.strip() == "--- pil_trace_begin ---":
            in_trace = True
            continue
        if raw.strip() == "--- pil_trace_end ---":
            in_trace = False
            continue
        if not in_trace:
            continue
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
        if "pil_notif" not in line and "msm_pil_event" not in line:
            continue
        event: dict[str, str] = {"line": line}
        for field in ("event_name", "fw_name", "code"):
            match = re.search(rf"\b{field}[=:]\s*([^,\s]+)", line)
            if match:
                event[field] = match.group(1).strip()
        fw_match = re.search(r"\bfw[=:]\s*([^,\s]+)", line)
        if fw_match and "fw_name" not in event:
            event["fw_name"] = fw_match.group(1).strip()
        events.append(event)
    return {
        "line_count": len(lines),
        "event_count": len(events),
        "events": events[:120],
        "event_names": sorted({event.get("event_name", "") for event in events if event.get("event_name")}),
        "fw_names": sorted({event.get("fw_name", "") for event in events if event.get("fw_name")}),
        "codes": sorted({event.get("code", "") for event in events if event.get("code")}),
    }


def capture_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    preflight = v750.capture_preflight(args, store, steps)
    run_step(args, store, steps, "proc-mounts-before-tracefs", ["cat", "/proc/mounts"], 15.0)
    return preflight


def run_live(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             preflight: dict[str, Any]) -> dict[str, Any]:
    label = proof_id(args)
    proof_base = PROOF_PREFIX + label
    node = f"{proof_base}/subsys_modem"
    status_file = f"{proof_base}/holder.status"
    pid_file = f"{proof_base}/holder.pid"
    mounted_before = tracefs_mounted(step_payload(steps, "proc-mounts-before-tracefs"))
    trace_collected = False
    trace_payload: dict[str, Any] = {}
    before = run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    helper_item: dict[str, Any] | None = None
    boot_item: dict[str, Any] | None = None
    qrtr_wait: dict[str, Any] = {}
    reboot: dict[str, Any] = {}
    try:
        if not mounted_before:
            run_step(args, store, steps, "tracefs-mount", ["run", args.busybox, "mount", "-t", "tracefs", "tracefs", DEFAULT_TRACEFS_TARGET], 20.0, proof_base, allow_trace_mount=True)
        run_step(args, store, steps, "trace-setup", shell_cmd(args, trace_setup_script(args)), 25.0, proof_base, allow_trace_write=True)
        for name, command, timeout in mountv.build_mount_commands(preflight, proof_base):
            run_step(args, store, steps, f"v797-{name}", command, timeout, proof_base)
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0, proof_base)
        run_step(args, store, steps, "mounted-firmware-class-path", ["cat", base.FIRMWARE_CLASS_PATH], 10.0, proof_base)
        for path in base.GLOBAL_MODEM_BLOB_PATHS + base.WLAN_FIRMWARE_PATHS:
            run_step(args, store, steps, f"mounted-stat-{safe_name(path)}", ["stat", path], 10.0, proof_base)

        dev = base.parse_dev(step_payload(steps, "subsys-modem-dev"))
        if not dev:
            raise RuntimeError("subsys_modem dev missing after preflight")
        holder = base.holder_script(args, node, status_file, pid_file, dev[0], dev[1])
        write_capture(store, "holder-script-redacted", holder.replace(node, "$PROOF/subsys_modem").replace(proof_base, "$PROOF"))
        run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", holder], 25.0, proof_base)
        run_step(args, store, steps, "mss-state-after-holder", ["cat", base.MSS_STATE], 10.0, proof_base)
        run_step(args, store, steps, "mdm3-state-after-holder", ["cat", base.MDM3_STATE], 10.0, proof_base)
        qrtr_wait = base.wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""), proof_base)
        if qrtr_wait.get("seen"):
            helper_item = run_step(args, store, steps, "lower-companion-start-only", v750.helper_command(args), args.companion_runtime_sec + 75.0, proof_base)
        run_step(args, store, steps, "wlanbootctl-status-before-boot", ["run", args.wlanbootctl, "status"], 25.0, proof_base)
        boot_item = run_step(args, store, steps, "boot-wlan-observe", ["run", args.wlanbootctl, "boot-observe", str(args.boot_observe_sec)], args.boot_observe_sec + 35.0, proof_base)
        run_step(args, store, steps, "wlanbootctl-status-after-boot", ["run", args.wlanbootctl, "status"], 25.0, proof_base)
        run_step(args, store, steps, "mss-state-after-boot", ["cat", base.MSS_STATE], 10.0, proof_base)
        run_step(args, store, steps, "mdm3-state-after-boot", ["cat", base.MDM3_STATE], 10.0, proof_base)
        for path in v750.POST_BOOT_PATHS:
            v750.read_path_capture(args, store, steps, path, proof_base)
        trace_item = run_step(args, store, steps, "trace-stop-collect", shell_cmd(args, trace_collect_script(args)), 40.0, proof_base, allow_trace_write=True)
        trace_collected = True
        trace_payload = parse_trace_payload(str(trace_item.get("payload") or ""))
        if not mounted_before:
            run_step(args, store, steps, "tracefs-umount", ["run", args.busybox, "umount", DEFAULT_TRACEFS_TARGET], 20.0, proof_base, allow_trace_mount=True)
        run_step(args, store, steps, "proc-mounts-after-tracefs", ["cat", "/proc/mounts"], 15.0, proof_base)
        after = run_step(args, store, steps, "dmesg-after-boot", ["run", args.toybox, "dmesg"], 60.0, proof_base)
        delta = base.dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
        write_capture(store, "dmesg-delta", delta)
        markers = v750.extended_marker_summary(delta)
    finally:
        if not trace_collected:
            try:
                run_step(args, store, steps, "trace-cleanup-final", shell_cmd(args, trace_cleanup_script(args)), 20.0, proof_base, allow_trace_write=True)
            except Exception as exc:  # noqa: BLE001 - evidence cleanup path
                write_capture(store, "trace-cleanup-final-error", str(exc))
        reboot = base.reboot_and_wait(args, store)

    mounted = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    helper = v750.helper_surface(str((helper_item or {}).get("payload") or ""))
    status_after = step_payload(steps, "wlanbootctl-status-after-boot")
    proc_net_dev = step_payload(steps, "post-boot-cat-proc-net-dev")
    sys_class_net = step_payload(steps, "post-boot-ls-sys-class-net")
    ieee80211 = step_payload(steps, "post-boot-ls-sys-class-ieee80211")
    return {
        "base": proof_base,
        "mounted_before_tracefs": mounted_before,
        "mounted_after_tracefs": tracefs_mounted(step_payload(steps, "proc-mounts-after-tracefs")),
        "trace_payload": trace_payload,
        "trace_collected": trace_collected,
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "holder_opened": "v731.holder.status=opened" in step_payload(steps, "start-modem-holder"),
        "mss_before": step_payload(steps, "mss-state-before").strip(),
        "mss_after_holder": step_payload(steps, "mss-state-after-holder").strip(),
        "mss_after_boot": step_payload(steps, "mss-state-after-boot").strip(),
        "mdm3_before": step_payload(steps, "mdm3-state-before").strip(),
        "mdm3_after_holder": step_payload(steps, "mdm3-state-after-holder").strip(),
        "mdm3_after_boot": step_payload(steps, "mdm3-state-after-boot").strip(),
        "qrtr_rx_wait": qrtr_wait,
        "companion_executed": bool(qrtr_wait.get("seen")),
        "helper_result": helper,
        "boot_wlan_write_executed": bool(boot_item),
        "boot_wlan_ok": bool((boot_item or {}).get("ok")),
        "qcwlanstate_after": "wlanboot.status.qcwlanstate.value=ON" in status_after,
        "wlan0_after": "wlan0" in proc_net_dev or "wlan0" in sys_class_net,
        "wiphy_after": "phy" in ieee80211 or "wlan" in ieee80211.lower(),
        "qrtr_services_after_boot": base.qrtr_service_counts(step_payload(steps, "post-boot-cat-proc-net-qrtr")),
        "markers": markers if "markers" in locals() else {},
        "reboot_cleanup": reboot,
    }


def required_flags(args: argparse.Namespace) -> list[str]:
    flags = {
        "--allow-tracefs-mount": args.allow_tracefs_mount,
        "--allow-trace-control-write": args.allow_trace_control_write,
        "--allow-lower-window-boot-wlan": args.allow_lower_window_boot_wlan,
        "--assume-yes": args.assume_yes,
    }
    return [flag for flag, enabled in flags.items() if not enabled]


def build_checks(args: argparse.Namespace,
                 steps: list[dict[str, Any]],
                 preflight: dict[str, Any],
                 v731: dict[str, Any],
                 v732: dict[str, Any],
                 v490: dict[str, Any],
                 live: dict[str, Any] | None,
                 blockers: list[str]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        return [Check("plan-only", "pass", "info", "no device command executed", "run preflight/live with explicit V797 flags")]
    inherited = v750.preflight_blockers(args, steps, preflight, v731, v732, v490)
    inherited = [item for item in inherited if item != "live-boot-wlan-not-approved"]
    checks.append(Check("preflight", "pass" if not inherited else "blocked", "blocker", ",".join(inherited), "clear inherited V750 lower-window blockers"))
    missing = required_flags(args) if args.command == "run" else []
    checks.append(Check("explicit-flags", "pass" if not missing else "blocked", "blocker", ",".join(missing), "pass all explicit V797 allow flags"))
    if not live:
        return checks
    helper = live.get("helper_result") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    trace_payload = live.get("trace_payload") or {}
    reboot = live.get("reboot_cleanup") or {}
    checks.extend([
        Check("trace-payload", "pass" if trace_payload.get("event_count", 0) > 0 else "blocked", "blocker", json.dumps({key: trace_payload.get(key) for key in ("event_count", "event_names", "fw_names", "codes")}, sort_keys=True), "inspect tracefs setup if no pil_notif payload was captured"),
        Check("lower-transition", "pass" if live.get("holder_opened") and (live.get("qrtr_rx_wait") or {}).get("seen") and helper.get("order") == v750.EXPECTED_ORDER and live.get("boot_wlan_write_executed") else "blocked", "blocker", json.dumps({"holder": live.get("holder_opened"), "qrtr_rx": (live.get("qrtr_rx_wait") or {}).get("seen"), "order": helper.get("order"), "boot_wlan": live.get("boot_wlan_write_executed")}, sort_keys=True), "do not interpret trace without lower transition"),
        Check("wifi-still-gated", "pass" if not live.get("wlan0_after") and not live.get("wiphy_after") and not (live.get("qrtr_services_after_boot") or {}).get("69", 0) else "advanced", "info", json.dumps({"service69": (live.get("qrtr_services_after_boot") or {}).get("69", 0), "wlan0": live.get("wlan0_after"), "wiphy": live.get("wiphy_after"), "wlfw": counts.get("wlfw", 0), "bdf": counts.get("bdf", 0)}, sort_keys=True), "if advanced, stop before credentials and capture interface state"),
        Check("forbidden-actions", "pass", "blocker", "no service-manager/HAL/scan/connect/DHCP/external ping/raw esoc0/custom kernel path generated", "preserve V797 boundary"),
        Check("cleanup-health", "pass" if not live.get("mounted_after_tracefs") and reboot.get("version_seen") and reboot.get("status_healthy") else "blocked", "blocker", json.dumps({"tracefs_after": live.get("mounted_after_tracefs"), "reboot": reboot}, sort_keys=True), "recover v724 health before continuing"),
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[Check], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v797-pil-trace-payload-plan-ready", True, "plan-only; no device command executed", "run V797 preflight/live"
    blocked = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blocked:
        return "v797-pil-trace-payload-blocked", False, "blocked by " + ", ".join(blocked), "fix trace/lower-window blockers before retry"
    if not live:
        return "v797-pil-trace-payload-preflight-ready", True, "preflight ready", "run with explicit V797 flags"
    trace_payload = live.get("trace_payload") or {}
    return "v797-pil-notif-payload-captured", True, f"captured {trace_payload.get('event_count', 0)} pil_notif events with payload fields", "classify native PIL event sequence against Android before another trigger retry"


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    trace_payload = live.get("trace_payload") or {}
    return "\n".join([
        "# V797 PIL Trace Payload Capture",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Trace Payload",
        "",
        markdown_table(["signal", "value"], [
            ["event_count", trace_payload.get("event_count")],
            ["event_names", ", ".join(trace_payload.get("event_names") or [])],
            ["fw_names", ", ".join(trace_payload.get("fw_names") or [])],
            ["codes", ", ".join(trace_payload.get("codes") or [])],
            ["mss", f"{live.get('mss_before')} -> {live.get('mss_after_holder')} -> {live.get('mss_after_boot')}"],
            ["mdm3", f"{live.get('mdm3_before')} -> {live.get('mdm3_after_holder')} -> {live.get('mdm3_after_boot')}"],
            ["service69/wlan0/wiphy", f"{(live.get('qrtr_services_after_boot') or {}).get('69', 0)} / {live.get('wlan0_after')} / {live.get('wiphy_after')}"],
        ]),
        "",
        "## Sample Events",
        "",
        "```text",
        "\n".join((event.get("line", "") for event in (trace_payload.get("events") or [])[:20])),
        "```",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [[check["name"], check["status"], check["severity"], check["detail"], check["next_step"]] for check in manifest["checks"]]),
        "",
        "## Safety",
        "",
        "- Tracefs was enabled only for `msm_pil_event:pil_notif` and then disabled.",
        "- No service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, raw `esoc0`, bind/unbind, module load/unload, boot image write, partition write, or custom kernel flash.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    live: dict[str, Any] | None = None
    v731 = base.load_json_if_exists(args.v731_manifest)
    v732 = base.load_json_if_exists(args.v732_manifest)
    v490 = base.load_json_if_exists(args.v490_manifest)
    preflight: dict[str, Any] = {}
    blockers: list[str] = []
    if args.command in {"preflight", "run"}:
        preflight = capture_preflight(args, store, steps)
        blockers = v750.preflight_blockers(args, steps, preflight, v731, v732, v490)
        blockers = [item for item in blockers if item != "live-boot-wlan-not-approved"]
    if args.command == "run" and not blockers and not required_flags(args):
        live = run_live(args, store, steps, preflight)
    checks = build_checks(args, steps, preflight, v731, v732, v490, live, blockers)
    decision, passed, reason, next_step = decide(args, checks, live)
    manifest = {
        "cycle": "v797",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "preflight": preflight,
        "live": live or {},
        "checks": [asdict(check) for check in checks],
        "steps": [{key: value for key, value in step.items() if key != "payload"} for step in steps],
        "device_commands_executed": args.command in {"preflight", "run"},
        "device_mutations": args.command == "run" and bool(live),
        "trace_control_write_executed": args.command == "run" and bool(live),
        "lower_companion_start_executed": bool((live or {}).get("companion_executed")),
        "boot_wlan_executed": bool((live or {}).get("boot_wlan_write_executed")),
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "esoc0_access_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    print(f"trace_control_write_executed: {manifest['trace_control_write_executed']}")
    print(f"boot_wlan_executed: {manifest['boot_wlan_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
