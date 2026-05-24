#!/usr/bin/env python3
"""V808 bounded live gate: keep provider-first companion alive across boot_wlan."""

from __future__ import annotations

import argparse
import binascii
import datetime as dt
import json
import re
import shlex
from pathlib import Path
from typing import Any

import native_wifi_cnss_then_boot_wlan_v752 as v752
import native_wifi_firmware_mount_parity_v584 as mountv
import native_wifi_provider_first_boot_wlan_observe_v802 as v802
import native_wifi_same_helper_replay_v673 as v673
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v808-overlap-companion-boot-wlan")
DEFAULT_V807_MANIFEST = Path("tmp/wifi/v807-pre-wlfw-overlap-classifier/manifest.json")
PROOF_PREFIX = "/tmp/a90-v808-"
SCRIPT_WORK_PREFIX = "/mnt/sdext/a90/tmp"

ALLOWED_LIVE_ACTIONS = (
    "V641 one-shot clean-DSP reboot",
    "V401 SELinuxfs mount surface",
    "V490 Android SELinux policy-load proof",
    "firmware ro mounts and subsys_modem holder",
    "helper v124 provider-first companion in background",
    "bounded boot_wlan observe while helper is still running",
    "read-only dmesg/WLFW/ICNSS/WLAN output capture",
    "runner-owned reboot cleanup",
)
FORBIDDEN_ACTIONS = (
    "custom kernel flash or boot image write",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "qcwlanstate direct write",
    "esoc0 open or hold",
    "bind/unbind, driver_override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v752.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v752.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=v752.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=v752.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=v752.DEFAULT_BUSYBOX)
    parser.add_argument("--helper", default=v752.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=v752.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=v752.DEFAULT_HELPER_MARKER)
    parser.add_argument("--wlanbootctl", default=v752.DEFAULT_WLANBOOTCTL)
    parser.add_argument("--wlanbootctl-sha256", default=v752.DEFAULT_WLANBOOTCTL_SHA256)
    parser.add_argument("--wlanbootctl-marker", default=v752.DEFAULT_WLANBOOTCTL_MARKER)
    parser.add_argument("--expect-version", default=v752.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=v752.DEFAULT_HOLD_SEC)
    parser.add_argument("--cnss-runtime-sec", type=int, default=75)
    parser.add_argument("--companion-runtime-sec", type=int, default=None)
    parser.add_argument("--boot-observe-sec", type=int, default=30)
    parser.add_argument("--boot-delay-sec", type=int, default=18)
    parser.add_argument("--wait-sec", type=float, default=75.0)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=v752.lower.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=v752.lower.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=v752.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=v752.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v490-manifest", type=Path, default=v752.DEFAULT_V490_MANIFEST)
    parser.add_argument("--v751-manifest", type=Path, default=v752.DEFAULT_V751_MANIFEST)
    parser.add_argument("--v807-manifest", type=Path, default=DEFAULT_V807_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return v752.safe_name(args.proof_id)
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{v752.safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    return v752.step_payload(steps, name)


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             proof_base: str | None = None) -> dict[str, Any]:
    item = v752.run_step(args, store, steps, name, command, timeout=timeout, proof_base=proof_base)
    return item


def run_overlap_step(args: argparse.Namespace,
                     store: EvidenceStore,
                     steps: list[dict[str, Any]],
                     name: str,
                     script: str,
                     timeout: float,
                     proof_base: str,
                     script_path: str) -> dict[str, Any]:
    if any(term in script for term in ("wpa_supplicant", "hostapd", "svc wifi", "cmd wifi", "ip route", " ping ", "driver_override")):
        raise RuntimeError("forbidden V808 overlap script term")
    if "boot-observe" not in script or args.helper not in script:
        raise RuntimeError("V808 overlap script must contain helper and boot-observe")
    command = ["run", args.busybox, "sh", script_path]
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    item["proof_base"] = proof_base
    steps.append(item)
    return item


def v807_ready(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v807_manifest)
    return {
        "manifest": str(repo_path(args.v807_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "ready": manifest.get("decision") == "v807-overlapped-companion-boot-wlan-gate-selected" and bool(manifest.get("pass")),
    }


def shell_join(argv: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def uuencode_text(name: str, text: str) -> str:
    data = text.encode("utf-8")
    lines = [f"begin 700 {name}\n"]
    for offset in range(0, len(data), 45):
        lines.append(binascii.b2a_uu(data[offset:offset + 45]).decode("ascii"))
    lines.append("`\nend\n")
    return "".join(lines)


def run_direct_step(args: argparse.Namespace,
                    store: EvidenceStore,
                    steps: list[dict[str, Any]],
                    name: str,
                    command: list[str],
                    timeout: float | None = None,
                    proof_base: str | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    item["proof_base"] = proof_base
    steps.append(item)
    return item


def upload_text_script(args: argparse.Namespace,
                       store: EvidenceStore,
                       steps: list[dict[str, Any]],
                       proof_base: str,
                       name: str,
                       script: str) -> str:
    script_base = f"{SCRIPT_WORK_PREFIX}/{v752.safe_name(Path(proof_base).name)}"
    staging = f"{script_base}/{name}.uue"
    target = f"{script_base}/{name}.sh"
    encoded = uuencode_text(f"{name}.sh", script)
    run_direct_step(args, store, steps, f"mkdir-{name}-script-dir", ["run", args.toybox, "mkdir", "-p", script_base], 20.0, proof_base)
    run_direct_step(args, store, steps, f"rm-{name}-script", ["run", args.toybox, "rm", "-f", staging, target], 20.0, proof_base)
    chunks = 0
    for offset in range(0, len(encoded), 700):
        chunk = encoded[offset:offset + 700]
        item = run_direct_step(args, store, steps, f"append-{name}-script-{chunks:03d}", ["appendfile", staging, chunk], 20.0, proof_base)
        if not item.get("ok"):
            raise RuntimeError(f"failed to append V808 script chunk {chunks}")
        chunks += 1
    decode = run_direct_step(args, store, steps, f"decode-{name}-script", ["run", args.toybox, "uudecode", "-o", target, staging], 60.0, proof_base)
    chmod = run_direct_step(args, store, steps, f"chmod-{name}-script", ["run", args.toybox, "chmod", "700", target], 20.0, proof_base)
    if not decode.get("ok") or not chmod.get("ok"):
        raise RuntimeError("failed to decode/chmod V808 overlap script")
    return target


def overlap_script(args: argparse.Namespace, proof_base: str) -> str:
    helper_timeout = max(1, min(30, args.cnss_runtime_sec))
    helper_args_namespace = argparse.Namespace(**vars(args))
    helper_args_namespace.cnss_runtime_sec = helper_timeout
    helper_args = v802.helper_command(helper_args_namespace)
    helper_cmd = shell_join(helper_args[1:] if helper_args[:1] == ["run"] else helper_args)
    boot_sec = max(10, min(60, args.boot_observe_sec))
    delay = max(5, min(45, args.boot_delay_sec))
    observe_sec = max(boot_sec + delay + 8, args.cnss_runtime_sec + 8)
    return "\n".join([
        "set +e",
        f"BB={shlex.quote(args.busybox)}",
        f"BASE={shlex.quote(proof_base)}",
        "$BB mkdir -p \"$BASE\"",
        "HELPER_LOG=\"$BASE/helper.log\"",
        "BOOT_LOG=\"$BASE/boot.log\"",
        "OBS_LOG=\"$BASE/observer.log\"",
        "DMESG_BEFORE=\"$BASE/dmesg.before\"",
        "DMESG_AFTER=\"$BASE/dmesg.after\"",
        "$BB dmesg > \"$DMESG_BEFORE\" 2>&1",
        "echo v808.overlap.begin=1",
        "echo v808.scan_connect_linkup=0",
        "echo v808.credentials=0",
        "echo v808.dhcp_routing=0",
        "echo v808.external_ping=0",
        f"echo v808.helper.timeout_sec={helper_timeout}",
        f"({helper_cmd}; echo v808.helper.inner_rc=$?) > \"$HELPER_LOG\" 2>&1 &",
        "HPID=$!",
        "echo v808.helper.pid=$HPID",
        "GATE_SEEN=0",
        "GATE_WAIT=0",
        f"while [ \"$GATE_WAIT\" -lt {delay} ]; do",
        "  if $BB grep -q '^wifi_companion_start\\.service74_gate\\.open=1' \"$HELPER_LOG\" 2>/dev/null; then",
        "    GATE_SEEN=1",
        "    break",
        "  fi",
        "  if ! kill -0 \"$HPID\" 2>/dev/null; then",
        "    break",
        "  fi",
        "  $BB sleep 1",
        "  GATE_WAIT=$((GATE_WAIT+1))",
        "done",
        "echo v808.helper.gate_seen=$GATE_SEEN",
        "echo v808.helper.gate_wait_sec=$GATE_WAIT",
        "(",
        "  i=0",
        f"  while [ \"$i\" -lt {observe_sec} ]; do",
        "    echo V808_OBS_SAMPLE=$i",
        "    $BB dmesg | $BB grep -iE \"service-notifier|wlfw|QMI Server|WLAN FW|wlan: Loading|wlan: driver loaded|BDF|bdwlan|regdb|wlan0|Modules not initialized\" | $BB tail -80",
        "    $BB sleep 1",
        "    i=$((i+1))",
        "  done",
        ") > \"$OBS_LOG\" 2>&1 &",
        "OPID=$!",
        "if kill -0 \"$HPID\" 2>/dev/null; then echo v808.helper.alive_before_boot=1; else echo v808.helper.alive_before_boot=0; fi",
        "echo v808.boot.begin=1",
        f"{shlex.quote(args.wlanbootctl)} boot-observe {boot_sec} > \"$BOOT_LOG\" 2>&1",
        "BRC=$?",
        "echo v808.boot.rc=$BRC",
        "if kill -0 \"$HPID\" 2>/dev/null; then echo v808.helper.alive_after_boot=1; else echo v808.helper.alive_after_boot=0; fi",
        "wait \"$HPID\"",
        "HRC=$?",
        "echo v808.helper.rc=$HRC",
        "wait \"$OPID\" 2>/dev/null",
        "$BB dmesg > \"$DMESG_AFTER\" 2>&1",
        "echo v808.helper.raw_tail.begin=1",
        "$BB tail -260 \"$HELPER_LOG\" 2>&1",
        "echo v808.helper.raw_tail.end=1",
        "echo v808.helper.filtered.begin=1",
        "$BB grep -E '^(A90_EXECNS_BEGIN|helper_status|setup_error|mode=|wifi_companion_start\\.|wifi_vndservice_query\\.)' \"$HELPER_LOG\" 2>&1",
        "echo v808.helper.filtered.end=1",
        "echo v808.boot.filtered.begin=1",
        "$BB tail -220 \"$BOOT_LOG\" 2>&1",
        "echo v808.boot.filtered.end=1",
        "echo v808.observer.filtered.begin=1",
        "$BB tail -260 \"$OBS_LOG\" 2>&1",
        "echo v808.observer.filtered.end=1",
        "echo v808.dmesg.focus.begin=1",
        "$BB grep -iE 'service-notifier|wlfw|QMI Server|WLAN FW|wlan: Loading|wlan: driver loaded|BDF|bdwlan|regdb|wlan0|Modules not initialized' \"$DMESG_AFTER\" | $BB tail -220",
        "echo v808.dmesg.focus.end=1",
        "echo v808.overlap.end=1",
        "exit 0",
    ])


def collect_live(args: argparse.Namespace, store: EvidenceStore, prep: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    proof = PROOF_PREFIX + proof_id(args)
    before = run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    preflight = v752.capture_preflight(args, store, steps)
    mount_results: list[str] = []
    try:
        for name, command, timeout in mountv.build_mount_commands(preflight, proof):
            item = run_step(args, store, steps, f"v808-{name}", command, timeout, proof)
            mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0, proof)
        run_step(args, store, steps, "mounted-firmware-class-path", ["cat", v752.lower.FIRMWARE_CLASS_PATH], 10.0, proof)
        dev = v752.lower.parse_dev(step_payload(steps, "subsys-modem-dev"))
        if not dev:
            raise RuntimeError("subsys_modem dev missing after preflight")
        holder = v752.lower.holder_script(args, f"{proof}/subsys_modem", f"{proof}/holder.status", f"{proof}/holder.pid", dev[0], dev[1])
        write_capture(store, "holder-script-redacted", holder.replace(proof, "$PROOF"))
        run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", holder], 25.0, proof)
        qrtr_wait = v752.lower.wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""), proof)
        if not qrtr_wait.get("seen"):
            overlap_item = {
                "name": "overlap-helper-boot-wlan",
                "ok": True,
                "rc": 0,
                "status": "skipped",
                "payload": "skipped: QRTR RX marker was not observed\n",
                "file": write_capture(store, "overlap-helper-boot-wlan-skipped", "skipped: QRTR RX marker was not observed\n"),
            }
            steps.append(overlap_item)
        else:
            script = overlap_script(args, proof)
            write_capture(store, "overlap-script-redacted", script.replace(proof, "$PROOF"))
            script_path = upload_text_script(args, store, steps, proof, "overlap", script)
            overlap_item = run_overlap_step(
                args,
                store,
                steps,
                "overlap-helper-boot-wlan",
                script,
                max(140.0, args.cnss_runtime_sec + args.boot_delay_sec + args.boot_observe_sec + 45.0),
                proof,
                script_path,
            )
        after = run_step(args, store, steps, "dmesg-after-overlap", ["run", args.toybox, "dmesg"], 60.0, proof)
        delta = v752.lower.dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
        write_capture(store, "dmesg-delta", delta)
        markers = v752.marker_summary(delta)
    finally:
        reboot = v752.lower.reboot_and_wait(args, store)
    payload = str((overlap_item or {}).get("payload") or "")
    helper_text = "\n".join(
        line for line in payload.splitlines()
        if line.startswith(("A90_EXECNS_BEGIN", "helper_status", "setup_error", "mode=", "wifi_companion_start.", "wifi_vndservice_query."))
    )
    helper = v802.parse_helper_payload(helper_text)
    boot_ok = "v808.boot.rc=0" in payload
    helper_gate_seen = "v808.helper.gate_seen=1" in payload
    helper_alive_before = "v808.helper.alive_before_boot=1" in payload
    helper_alive_after = "v808.helper.alive_after_boot=1" in payload
    service69_seen = bool(re.search(r"\b(service\s+69|WLFW|wlfw_new_server|QMI Server Connected|WLAN FW is ready)\b", payload, re.I))
    return steps, {
        "base": proof,
        "prep": prep,
        "preflight": preflight,
        "mount_results": mount_results,
        "qrtr_rx_wait": qrtr_wait if "qrtr_wait" in locals() else {},
        "overlap_status": (overlap_item or {}).get("status"),
        "overlap_ok": bool((overlap_item or {}).get("ok")),
        "overlap_file": (overlap_item or {}).get("file"),
        "boot_ok": boot_ok,
        "helper_gate_seen": helper_gate_seen,
        "helper_alive_before_boot": helper_alive_before,
        "helper_alive_after_boot": helper_alive_after,
        "helper_result": helper,
        "markers": markers if "markers" in locals() else {},
        "service69_or_wlfw_seen_in_overlap": service69_seen,
        "reboot_cleanup": reboot,
    }


def build_checks(command: str, v807: dict[str, Any], prep: dict[str, Any] | None, live: dict[str, Any] | None) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command executed",
            "next_step": "run V808 bounded overlap live gate",
        }]
    helper = (live or {}).get("helper_result") or {}
    counts = (((live or {}).get("markers") or {}).get("counts") or {})
    reboot = (live or {}).get("reboot_cleanup") or {}
    forbidden = {
        key: helper.get(key)
        for key in ("wifi_hal", "wificond", "scan_connect_linkup", "external_ping", "qmi_attempted")
    }
    return [
        {
            "name": "v807-route-ready",
            "status": "pass" if v807.get("ready") else "blocked",
            "detail": v807,
            "next_step": "complete V807 before overlap live gate",
        },
        {
            "name": "current-boot-prep-ready",
            "status": "pass" if prep and prep.get("ready") else "blocked",
            "detail": prep or {},
            "next_step": "restore V641/V401/V490 prep",
        },
        {
            "name": "overlap-executed",
            "status": "pass" if live and live.get("overlap_ok") and live.get("boot_ok") and live.get("helper_alive_before_boot") else "blocked",
            "detail": {
                "overlap_status": (live or {}).get("overlap_status"),
                "boot_ok": (live or {}).get("boot_ok"),
                "helper_gate_seen": (live or {}).get("helper_gate_seen"),
                "helper_alive_before_boot": (live or {}).get("helper_alive_before_boot"),
                "helper_alive_after_boot": (live or {}).get("helper_alive_after_boot"),
                "qrtr_rx_wait": (live or {}).get("qrtr_rx_wait"),
            },
            "next_step": "fix overlap shell timing if helper was not alive during boot",
        },
        {
            "name": "provider-first-contract",
            "status": "pass" if helper.get("service74_gate", {}).get("open") == "1" and helper.get("provider_query_exact") and helper.get("cnss_retry_started") else "blocked",
            "detail": {
                "mode": helper.get("mode"),
                "service74_gate": helper.get("service74_gate"),
                "provider_query_exact": helper.get("provider_query_exact"),
                "cnss_retry_started": helper.get("cnss_retry_started"),
                "all_postflight_safe": helper.get("all_postflight_safe"),
            },
            "next_step": "inspect helper filtered output",
        },
        {
            "name": "forbidden-actions",
            "status": "pass" if all(int_value(value) == 0 for value in forbidden.values()) else "blocked",
            "detail": forbidden,
            "next_step": "stop if overlap crossed HAL/connect/network boundary",
        },
        {
            "name": "wlfw-or-netdev-progression",
            "status": "pass" if (live or {}).get("service69_or_wlfw_seen_in_overlap") or any(int_value(counts.get(name)) for name in ("wlfw", "icnss_qmi_connected", "fw_ready", "bdf", "wiphy", "wlan0", "wlan_driver_loaded")) else "finding",
            "detail": {"service69_or_wlfw_seen_in_overlap": (live or {}).get("service69_or_wlfw_seen_in_overlap"), "markers": counts},
            "next_step": "if absent, classify deeper pre-WLFW publication blocker under true overlap",
        },
        {
            "name": "postflight-reboot-cleanup",
            "status": "pass" if reboot.get("version_seen") and reboot.get("status_healthy") else "blocked",
            "detail": reboot,
            "next_step": "manually verify native if cleanup did not prove health",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v808-overlap-companion-boot-wlan-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V808 bounded overlap live gate",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return "v808-overlap-companion-boot-wlan-blocked", False, "blocked by " + ", ".join(blocked), "clear overlap live blocker"
    counts = (((live or {}).get("markers") or {}).get("counts") or {})
    if any(int_value(counts.get(name)) for name in ("wlan0", "wiphy")):
        return (
            "v808-overlap-netdev-appeared",
            True,
            "overlapped provider-first companion and boot_wlan produced netdev surface before HAL/connect",
            "plan link-readiness and scan-only gate before credential use",
        )
    if (live or {}).get("service69_or_wlfw_seen_in_overlap") or any(int_value(counts.get(name)) for name in ("wlfw", "icnss_qmi_connected", "fw_ready", "bdf", "wlan_driver_loaded")):
        return (
            "v808-overlap-wlfw-or-driver-advanced",
            True,
            "overlap advanced WLFW/ICNSS/HDD markers without crossing HAL/connect boundary",
            "classify ICNSS-QMI/FW_READY/BDF/netdev gap",
        )
    return (
        "v808-overlap-service69-still-absent",
        True,
        "helper was alive during boot_wlan and provider-first context was present, but WLFW/service69/FW_READY/BDF/netdev remained absent",
        "classify deeper pre-WLFW publication prerequisites under true overlap",
    )


def build_manifest(args: argparse.Namespace, v807: dict[str, Any], prep: dict[str, Any] | None, live: dict[str, Any] | None) -> dict[str, Any]:
    checks = build_checks(args.command, v807, prep, live)
    decision, pass_ok, reason, next_step = decide(args.command, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v808",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "allowed_live_actions": ALLOWED_LIVE_ACTIONS,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "v807": v807,
        "prep_v808": prep or {},
        "live": live or {},
        "checks": checks,
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "provider_first_context_executed": bool(live and (live.get("helper_result") or {}).get("provider_query_exact")),
        "boot_wlan_write_executed": bool(live and live.get("boot_ok")),
        "service_manager_start_executed": bool(live),
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    helper = live.get("helper_result") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    rows = [
        ["helper_alive_before_boot", str(live.get("helper_alive_before_boot"))],
        ["helper_alive_after_boot", str(live.get("helper_alive_after_boot"))],
        ["helper_gate_seen", str(live.get("helper_gate_seen"))],
        ["boot_ok", str(live.get("boot_ok"))],
        ["service69_or_wlfw_seen_in_overlap", str(live.get("service69_or_wlfw_seen_in_overlap"))],
        ["helper_contract", json.dumps({key: helper.get(key) for key in ("mode", "service74_gate", "provider_query_exact", "cnss_retry_started", "all_postflight_safe", "wifi_hal", "wificond", "scan_connect_linkup", "external_ping")}, sort_keys=True)],
        ["markers", json.dumps(counts, sort_keys=True)],
        ["reboot_cleanup", json.dumps(live.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V808 Overlap Companion Boot WLAN Live Gate",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- provider_first_context_executed: `{manifest['provider_first_context_executed']}`",
        f"- boot_wlan_write_executed: `{manifest['boot_wlan_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Signals",
        "",
        markdown_table(["signal", "value"], rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v807 = {
        "manifest": str(repo_path(args.v807_manifest)),
        "decision": load_json(args.v807_manifest).get("decision", ""),
        "pass": bool(load_json(args.v807_manifest).get("pass")),
        "ready": load_json(args.v807_manifest).get("decision") == "v807-overlapped-companion-boot-wlan-gate-selected"
        and bool(load_json(args.v807_manifest).get("pass")),
    }
    prep: dict[str, Any] | None = None
    live: dict[str, Any] | None = None
    if args.command == "run":
        arm_root = store.run_dir / "arm-v808-overlap"
        prep = v673.prep_current_boot(args, store, "v808", arm_root)
        if prep.get("ready") and v807.get("ready"):
            steps, live = collect_live(args, store, prep)
            store.write_json("steps.json", {"steps": steps})
    manifest = build_manifest(args, v807, prep, live)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"provider_first_context_executed: {manifest['provider_first_context_executed']}")
    print(f"boot_wlan_write_executed: {manifest['boot_wlan_write_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
