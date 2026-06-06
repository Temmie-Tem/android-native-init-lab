#!/usr/bin/env python3
"""V1112 classifier for the /dev/subsys_modem open precondition after CNSS PM connect.

This collector is intentionally read-only on device.  It does not open
/dev/subsys_modem or /dev/subsys_esoc0; it only reads sysfs, mounts, and dmesg,
then reconciles that live surface with V1111 and V1061 evidence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1112-subsys-modem-precondition-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1112-subsys-modem-precondition-classifier.txt")
DEFAULT_V1111 = Path("tmp/wifi/v1111-pm-connect-path-capture-live/manifest.json")
DEFAULT_V1061 = Path("tmp/wifi/v1061-global-firmware-pm-full-contract/manifest.json")
DEFAULT_V1045_REPORT = Path("docs/reports/NATIVE_INIT_V1045_PM_PIL_PREREQUISITE_DELTA_2026-05-26.md")
DEFAULT_V1061_REPORT = Path("docs/reports/NATIVE_INIT_V1061_GLOBAL_FIRMWARE_PM_FULL_CONTRACT_2026-05-27.md")
DEFAULT_BUSYBOX = "/cache/bin/busybox"

EXPECTED_V1111_DECISION = "v1111-pm-connect-syscall-path-captured"
EXPECTED_V1061_DECISION = "v1061-global-firmware-modem-holder-confirmed-pm-contract-missing"

SURFACE_COMMAND = r'''BB=/cache/bin/busybox
printf 'firmware_class_path='
$BB cat /sys/module/firmware_class/parameters/path 2>/dev/null || true
for p in /vendor /vendor/firmware_mnt /vendor/firmware_mnt/image /vendor/firmware_mnt/image/modem.b00 /vendor/firmware-modem /vendor/firmware-modem/image /mnt/vendor /mnt/vendor/firmware_mnt /mnt/vendor/firmware_mnt/image /mnt/vendor/firmware_mnt/image/modem.b00 /mnt/vendor/firmware-modem /mnt/vendor/firmware-modem/image /mnt/vendor/firmware-modem/image/modem.b00 /firmware /firmware/image /firmware/image/modem.b00; do
  if [ -e "$p" ]; then
    if [ -r "$p" ]; then readable=1; else readable=0; fi
    printf 'path:%s exists=1 readable=%s type=' "$p" "$readable"
    if [ -d "$p" ]; then echo dir; else echo file; fi
  else
    printf 'path:%s exists=0 readable=0 type=missing\n' "$p"
  fi
done
echo 'mounts.begin'
$BB cat /proc/mounts | $BB grep -Ei 'firmware|vendor|system|sda29|apnhlos|modem' || true
echo 'mounts.end'
echo 'class_subsys.begin'
for d in /sys/class/subsys/*; do
  [ -e "$d" ] || continue
  b=${d##*/}
  dev=""; [ -r "$d/dev" ] && dev=$($BB cat "$d/dev" 2>/dev/null || true)
  printf 'class_subsys:%s dev=%s\n' "$b" "$dev"
done
echo 'class_subsys.end'
echo 'msm_subsys.begin'
for d in /sys/bus/msm_subsys/devices/*; do
  [ -e "$d" ] || continue
  b=${d##*/}
  name=""; state=""; restart=""; fw=""
  [ -r "$d/name" ] && name=$($BB cat "$d/name" 2>/dev/null || true)
  [ -r "$d/state" ] && state=$($BB cat "$d/state" 2>/dev/null || true)
  [ -r "$d/restart_level" ] && restart=$($BB cat "$d/restart_level" 2>/dev/null || true)
  [ -r "$d/firmware_name" ] && fw=$($BB cat "$d/firmware_name" 2>/dev/null || true)
  printf 'msm_subsys:%s name=%s state=%s restart=%s firmware=%s\n' "$b" "$name" "$state" "$restart" "$fw"
done
echo 'msm_subsys.end'
'''

DMESG_COMMAND = r'''BB=/cache/bin/busybox
$BB dmesg 2>/dev/null | $BB grep -Ei 'subsys|subsystem|modem|mss|mdm3|esoc|firmware|pil|pm-service|pm_proxy|cnss|icnss|wlfw|qrtr|sysmon|service-notifier|wlan_pd' | $BB tail -n 300 || true
'''


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path, limit: int = 4_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def trace_contract(manifest: dict[str, Any]) -> dict[str, str]:
    tracefs = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {})
    contract = tracefs.get("pm_contract") or {}
    return {str(key): str(value) for key, value in contract.items()}


def syscall_path_candidates(contract: dict[str, str]) -> list[dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    prefix = "syscall_probe."
    for key, value in contract.items():
        if not key.startswith(prefix):
            continue
        parts = key.split(".")
        if len(parts) < 4 or not parts[2].startswith("entry_"):
            continue
        entry_key = ".".join(parts[:3])
        field = ".".join(parts[3:])
        entries.setdefault(entry_key, {"entry_key": entry_key})[field] = value
    candidates = []
    for entry in sorted(entries.values(), key=lambda item: item.get("entry_key", "")):
        if entry.get("path.valid") == "1":
            candidates.append({
                "entry_key": entry.get("entry_key", ""),
                "tid": entry.get("tid", ""),
                "comm": entry.get("comm", ""),
                "wchan": entry.get("wchan", ""),
                "name": entry.get("name", ""),
                "path_value": entry.get("path.value", ""),
            })
    return candidates


def cnss_returns(manifest: dict[str, Any], label: str) -> list[str]:
    tracefs = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {})
    values: list[str] = []
    for comm, labels in (tracefs.get("return_values_by_comm") or {}).items():
        if "cnss" in str(comm):
            values.extend([str(item) for item in (labels or {}).get(label, [])])
    return values


def parse_surface(text: str) -> dict[str, Any]:
    paths: dict[str, dict[str, str]] = {}
    mounts: list[str] = []
    class_subsys: dict[str, dict[str, str]] = {}
    msm_subsys: dict[str, dict[str, str]] = {}
    firmware_class_path = ""
    section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "mounts.begin":
            section = "mounts"
            continue
        if line == "mounts.end":
            section = ""
            continue
        if line.endswith(".begin") or line.endswith(".end"):
            section = line[:-6] if line.endswith(".begin") else ""
            continue
        if line.startswith("firmware_class_path="):
            firmware_class_path = line.split("=", 1)[1]
            continue
        if line.startswith("path:"):
            path_part, rest = line[5:].split(" ", 1)
            attrs: dict[str, str] = {}
            for item in rest.split():
                if "=" in item:
                    key, value = item.split("=", 1)
                    attrs[key] = value
            paths[path_part] = attrs
            continue
        if line.startswith("class_subsys:"):
            name_part, rest = line.split(" ", 1)
            attrs = {"raw": line}
            for item in rest.split():
                if "=" in item:
                    key, value = item.split("=", 1)
                    attrs[key] = value
            class_subsys[name_part.split(":", 1)[1]] = attrs
            continue
        if line.startswith("msm_subsys:"):
            name_part, rest = line.split(" ", 1)
            attrs = {"raw": line}
            for item in rest.split():
                if "=" in item:
                    key, value = item.split("=", 1)
                    attrs[key] = value
            msm_subsys[name_part.split(":", 1)[1]] = attrs
            continue
        if section == "mounts":
            mounts.append(line)
    by_name = {attrs.get("name", ""): {"node": node, **attrs} for node, attrs in msm_subsys.items() if attrs.get("name")}
    return {
        "firmware_class_path": firmware_class_path,
        "paths": paths,
        "mounts": mounts,
        "class_subsys": class_subsys,
        "msm_subsys": msm_subsys,
        "msm_subsys_by_name": by_name,
        "global_firmware_path_visible": paths.get("/vendor/firmware_mnt/image", {}).get("exists") == "1",
        "global_modem_blob_visible": paths.get("/vendor/firmware_mnt/image/modem.b00", {}).get("readable") == "1",
        "mnt_vendor_mounted": any("/mnt/vendor" in line for line in mounts),
        "vendor_firmware_mnt_mounted_global": any("/vendor/firmware_mnt" in line for line in mounts),
        "subsys_modem_dev": class_subsys.get("subsys_modem", {}).get("dev", ""),
        "modem_state": by_name.get("modem", {}).get("state", ""),
        "esoc0_state": by_name.get("esoc0", {}).get("state", ""),
    }


def dmesg_counts(text: str) -> dict[str, int]:
    patterns = {
        "subsystem_get_modem": r"__subsystem_get.*modem|subsys.*modem",
        "request_firmware": r"request_firmware|firmware",
        "pil": r"\bpil\b|pil_|pil-",
        "cnss": r"cnss|icnss",
        "wlfw": r"wlfw",
        "qrtr": r"qrtr",
        "sysmon": r"sysmon",
        "warning": r"WARNING:|Reference count mismatch",
    }
    return {name: len(re.findall(pattern, text, re.IGNORECASE)) for name, pattern in patterns.items()}


def build_inputs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "v1111_manifest": str(repo_path(args.v1111_manifest)),
        "v1111_manifest_sha256": sha256(args.v1111_manifest),
        "v1061_manifest": str(repo_path(args.v1061_manifest)),
        "v1061_manifest_sha256": sha256(args.v1061_manifest),
        "v1045_report": str(repo_path(args.v1045_report)),
        "v1045_report_sha256": sha256(args.v1045_report),
        "v1061_report": str(repo_path(args.v1061_report)),
        "v1061_report_sha256": sha256(args.v1061_report),
    }


def run_device_read_only(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps = []
    captures = [
        ("bootstatus", ["bootstatus"], 12.0),
        ("firmware-subsys-surface", ["run", args.busybox, "ash", "-c", SURFACE_COMMAND], 20.0),
        ("dmesg-focus", ["run", args.busybox, "ash", "-c", DMESG_COMMAND], 25.0),
        ("selftest", ["selftest"], 12.0),
    ]
    payloads: dict[str, str] = {}
    for name, command, timeout in captures:
        capture = run_capture(args, name, command, timeout=timeout)
        steps.append(capture_to_manifest(capture))
        text = strip_cmdv1_text(capture.text) if capture.text else capture.error
        payloads[name] = text
        store.write_text(f"device/{name}.txt", text)
    surface = parse_surface(payloads.get("firmware-subsys-surface", ""))
    return steps, {
        "surface": surface,
        "dmesg_counts": dmesg_counts(payloads.get("dmesg-focus", "")),
    }


def classify(args: argparse.Namespace, live: dict[str, Any]) -> dict[str, Any]:
    v1111 = load_json(args.v1111_manifest)
    v1061 = load_json(args.v1061_manifest)
    v1045_report = read_text(args.v1045_report)
    v1061_report = read_text(args.v1061_report)
    contract = trace_contract(v1111)
    candidates = syscall_path_candidates(contract)
    target_paths = {item.get("path_value", "") for item in candidates}
    surface = live.get("surface") or {}

    v1111_connect_ok = "0x0" in cnss_returns(v1111, "pm_client_connect_ret")
    v1111_open_path_ok = "/dev/subsys_modem" in target_paths
    v1111_no_pre_holder = (
        contract.get("per_proxy_start_executed") == "0"
        and contract.get("child.per_proxy.start_skipped") == "1"
        and contract.get("after_cnss_daemon.per_mgr_subsys_modem_count") == "0"
    )
    v1061_holder_ok = bool(v1061.get("global_modem_holder_opened")) and bool(v1061.get("firmware_mounts_executed"))
    v1061_mss_online = ((v1061.get("live") or {}).get("mss_after_holder") == "ONLINE")
    v1061_pm_gap = v1061.get("decision") == EXPECTED_V1061_DECISION
    v1045_first_opener_model = all(
        token in v1045_report
        for token in (
            "subsys modem\nrefcount at 0",
            "__subsystem_get()",
            "subsys_start()",
            "count≥1",
        )
    )
    current_global_fw_absent = (
        surface.get("firmware_class_path") == "/vendor/firmware_mnt/image"
        and not surface.get("global_firmware_path_visible")
        and not surface.get("global_modem_blob_visible")
    )
    current_modem_offlining = surface.get("modem_state") == "OFFLINING"
    checks = {
        "v1111_input_present": bool(v1111),
        "v1111_decision_expected": v1111.get("decision") == EXPECTED_V1111_DECISION,
        "v1111_cnss_pm_connect_ok": v1111_connect_ok,
        "v1111_path_is_subsys_modem": v1111_open_path_ok,
        "v1111_no_preexisting_subsys_modem_fd": v1111_no_pre_holder,
        "v1061_input_present": bool(v1061),
        "v1061_global_firmware_holder_opened": v1061_holder_ok,
        "v1061_holder_made_mss_online": v1061_mss_online,
        "v1061_pm_gap_without_cnss_trigger": v1061_pm_gap,
        "v1045_first_opener_model_present": v1045_first_opener_model,
        "live_current_global_firmware_absent": current_global_fw_absent if args.command == "run" else True,
        "live_current_modem_offlining": current_modem_offlining if args.command == "run" else True,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    if args.command == "plan":
        decision = "v1112-subsys-modem-precondition-classifier-plan-ready"
        passed = True
        reason = "plan-only; no device command, actor start, subsystem open, Wi-Fi HAL, scan/connect, or external ping executed"
        next_step = "run V1112 read-only classifier, then plan V1113 combined global-firmware holder plus CNSS PM-connect gate"
    elif not blockers:
        decision = "v1112-select-global-firmware-holder-before-cnss-pm-connect"
        passed = True
        reason = (
            "V1111 proves CNSS PM connect makes pm-service open /dev/subsys_modem with no existing fd; "
            "live surface shows the current global firmware_class path is not mounted and modem is OFFLINING; "
            "V1061 proves global firmware mount plus modem holder opens and brings mss ONLINE but lacked the CNSS PM trigger"
        )
        next_step = (
            "V1113 source/build: add pm-service-observer order that installs global firmware mounts and a modem holder "
            "before service-manager/pm-service/CNSS PM connect, while still forbidding esoc0, Wi-Fi HAL, scan/connect, DHCP, credentials, and external ping"
        )
    else:
        decision = "v1112-subsys-modem-precondition-incomplete"
        passed = False
        reason = "missing checks: " + ", ".join(blockers)
        next_step = "repair missing predecessor evidence or recapture read-only live surface before another PM/CNSS live gate"

    return {
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "v1111_summary": {
            "decision": v1111.get("decision", ""),
            "path_candidates": candidates,
            "cnss_pm_client_register_ret": cnss_returns(v1111, "pm_client_register_ret"),
            "cnss_pm_client_connect_ret": cnss_returns(v1111, "pm_client_connect_ret"),
            "per_proxy_start_executed": contract.get("per_proxy_start_executed", ""),
            "per_proxy_start_skipped": contract.get("child.per_proxy.start_skipped", ""),
            "per_mgr_subsys_modem_count": contract.get("after_cnss_daemon.per_mgr_subsys_modem_count", ""),
            "mss_state": contract.get("post_provider_surface.after_cnss_daemon.mss_state", ""),
            "mdm3_state": contract.get("post_provider_surface.after_cnss_daemon.mdm3_state", ""),
        },
        "v1061_summary": {
            "decision": v1061.get("decision", ""),
            "firmware_mounts_executed": v1061.get("firmware_mounts_executed"),
            "global_modem_holder_opened": v1061.get("global_modem_holder_opened"),
            "mss_after_holder": ((v1061.get("live") or {}).get("mss_after_holder")),
            "mss_after_helper": ((v1061.get("live") or {}).get("mss_after_helper")),
            "mdm3_after_helper": ((v1061.get("live") or {}).get("mdm3_after_helper")),
            "pm_full_contract_seen": v1061.get("pm_full_contract_seen"),
            "wlfw_precondition_observed": v1061.get("wlfw_precondition_observed"),
        },
        "selected_route": {
            "next_version": "V1113",
            "intent": "combine V1061 global firmware/modem holder prerequisite with V1108/V1111 CNSS PM-connect trigger",
            "allow": [
                "read-only global firmware mounts used only to satisfy firmware_class.path",
                "bounded /dev/subsys_modem holder only; no /dev/subsys_esoc0 open",
                "service-manager trio and pm-service observer surface",
                "cnss-daemon start-only only until PM connect/path result is captured",
            ],
            "forbid": [
                "/dev/subsys_esoc0 open or eSoC ioctl/control path",
                "Wi-Fi HAL, wificond, IWifi.start, qcwlanstate write",
                "scan/connect/link-up, credential use, DHCP/routes, external ping",
                "firmware mutation, partition write, boot image write, reboot unless cleanup gate explicitly requires it",
            ],
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[name, "PASS" if ok else "FAIL"] for name, ok in manifest["checks"].items()]
    surface = (manifest.get("live") or {}).get("surface") or {}
    route = manifest.get("selected_route") or {}
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("status")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1112 Subsys Modem Precondition Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "result"], rows),
        "",
        "## Live Surface",
        "",
        "```json",
        json.dumps({
            "firmware_class_path": surface.get("firmware_class_path"),
            "global_firmware_path_visible": surface.get("global_firmware_path_visible"),
            "global_modem_blob_visible": surface.get("global_modem_blob_visible"),
            "mnt_vendor_mounted": surface.get("mnt_vendor_mounted"),
            "vendor_firmware_mnt_mounted_global": surface.get("vendor_firmware_mnt_mounted_global"),
            "subsys_modem_dev": surface.get("subsys_modem_dev"),
            "modem_state": surface.get("modem_state"),
            "esoc0_state": surface.get("esoc0_state"),
        }, indent=2, sort_keys=True),
        "```",
        "",
        "## V1111 Summary",
        "",
        "```json",
        json.dumps(manifest.get("v1111_summary") or {}, indent=2, sort_keys=True),
        "```",
        "",
        "## V1061 Summary",
        "",
        "```json",
        json.dumps(manifest.get("v1061_summary") or {}, indent=2, sort_keys=True),
        "```",
        "",
        "## Selected Route",
        "",
        f"- next_version: `{route.get('next_version', '')}`",
        f"- intent: {route.get('intent', '')}",
        "",
        "### Allow",
        "",
        *[f"- {item}" for item in route.get("allow", [])],
        "",
        "### Forbid",
        "",
        *[f"- {item}" for item in route.get("forbid", [])],
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "status"], step_rows),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1111-manifest", type=Path, default=DEFAULT_V1111)
    parser.add_argument("--v1061-manifest", type=Path, default=DEFAULT_V1061)
    parser.add_argument("--v1045-report", type=Path, default=DEFAULT_V1045_REPORT)
    parser.add_argument("--v1061-report", type=Path, default=DEFAULT_V1061_REPORT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    steps: list[dict[str, Any]] = []
    live: dict[str, Any] = {}
    device_commands_executed = False
    if args.command == "run":
        steps, live = run_device_read_only(args, store)
        device_commands_executed = True
    classification = classify(args, live)
    manifest: dict[str, Any] = {
        "cycle": "v1112",
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": build_inputs(args),
        "steps": steps,
        "live": live,
        "device_commands_executed": device_commands_executed,
        "device_mutations": False,
        "tracefs_write_executed": False,
        "bpf_attach_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "subsys_modem_open_attempted": False,
        "subsys_esoc0_open_attempted": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"subsys_modem_open_attempted: {manifest['subsys_modem_open_attempted']}")
    print(f"subsys_esoc0_open_attempted: {manifest['subsys_esoc0_open_attempted']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
