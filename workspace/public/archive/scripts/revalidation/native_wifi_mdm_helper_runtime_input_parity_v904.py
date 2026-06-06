#!/usr/bin/env python3
"""V904 host-only Android/native mdm_helper runtime-input parity classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Iterable

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v904-mdm-helper-runtime-input-parity")
LATEST_POINTER = Path("tmp/wifi/latest-v904-mdm-helper-runtime-input-parity.txt")
DEFAULT_V903_MANIFEST = Path("tmp/wifi/v903-mdm-helper-only-deep-capture-live/manifest.json")
DEFAULT_V853_MANIFEST = Path(
    "tmp/wifi/v853-android-esoc-actor-handoff/"
    "v853-android-esoc-actor-run/manifest.json"
)
DEFAULT_V896_MANIFEST = Path("tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v903-manifest", type=Path, default=DEFAULT_V903_MANIFEST)
    parser.add_argument("--v853-manifest", type=Path, default=DEFAULT_V853_MANIFEST)
    parser.add_argument("--v896-manifest", type=Path, default=DEFAULT_V896_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value.replace("\x00", "")
    elif isinstance(value, dict):
        for item in value.values():
            yield from flatten_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from flatten_strings(item)


def filtered_lines(strings: Iterable[str], pattern: str, limit: int = 80) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    seen: set[str] = set()
    for text in strings:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line in seen:
                continue
            if regex.search(line):
                seen.add(line)
                lines.append(line)
                if len(lines) >= limit:
                    return lines
    return lines


def parse_key_values(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.strip().split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            keys[key] = value.strip()
    return keys


def capture_block(text: str, marker: str) -> str:
    begin = re.escape(marker + "_BEGIN")
    end = re.escape(marker + "_END")
    match = re.search(begin + r"[^\n]*\n(?P<body>.*?)\n" + end, text, re.DOTALL)
    return match.group("body").strip() if match else ""


def parse_fd_targets(text: str, label: str) -> list[str]:
    prefix = re.escape(f"capture.{label}.fd_links.entry_")
    targets: list[str] = []
    for match in re.finditer(prefix + r"\d+\.target=(?P<target>[^\n]+)", text):
        targets.append(match.group("target").strip())
    return targets


def first_match(lines: list[str], pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        if regex.search(line):
            return line
    return ""


def extract_android(v853_manifest: dict[str, Any], v896_manifest: dict[str, Any]) -> dict[str, Any]:
    summary = v853_manifest.get("android_summary") or {}
    holder_lines = filtered_lines(
        summary.get("holder_lines") or [],
        r"mdm_helper|ks .*mhi_0305|/dev/esoc-0|pm-service|/dev/subsys_esoc0|/dev/subsys_modem",
        limit=60,
    )
    process_lines = filtered_lines(
        summary.get("process_lines") or [],
        r"mdm_helper|ks .*mhi_0305|cnss-daemon|pm-service|qrtr-ns|rmt_storage|tftp_server|irq/290-mdm",
        limit=80,
    )
    ueventd_lines = filtered_lines(
        summary.get("ueventd_lines") or [],
        r"/dev/esoc-0|/dev/subsys_\*|service vendor\.mdm_helper|service vendor\.per_mgr|service cnss-daemon|service vendor\.rmt_storage|service vendor\.tftp_server",
        limit=80,
    )
    selinux_lines = filtered_lines(
        summary.get("selinux_lines") or [],
        r"mdm_helper|/bin/ks|/dev/esoc|/dev/subsys_|pm-service|rmt_storage|tftp_server|cnss-daemon",
        limit=80,
    )
    service_lines = filtered_lines(
        list(flatten_strings(v853_manifest.get("captures") or [])) + summary.get("dmesg_lines", []),
        r"init\.svc\.(vendor\.mdm_helper|vendor\.per_mgr|cnss-daemon|rmt_storage|tftp_server|vendor\.qrtr-ns)=|on property:init\.svc\.vendor\.per_mgr=running|starting service 'vendor\.mdm_helper'",
        limit=80,
    )
    mdm_holder = first_match(holder_lines, r"FDHOLDER .*comm=mdm_helper")
    ks_holder = first_match(holder_lines, r"FDHOLDER .*comm=ks")
    mdm_proc = first_match(process_lines, r"\bmdm_helper\b")
    ks_proc = first_match(process_lines, r"\bks\b")
    context_match = re.search(r"attr=([^\s]+)", mdm_holder)
    return {
        "v853_decision": v853_manifest.get("decision", ""),
        "v853_pass": bool(v853_manifest.get("pass")),
        "v896_decision": v896_manifest.get("decision", ""),
        "v896_pass": bool(v896_manifest.get("pass")),
        "boot_completed": bool(summary.get("boot_completed")),
        "mdm_helper_holder_line": mdm_holder,
        "ks_holder_line": ks_holder,
        "mdm_helper_process_line": mdm_proc,
        "ks_process_line": ks_proc,
        "mdm_helper_context": context_match.group(1) if context_match else "",
        "holder_lines": holder_lines,
        "process_lines": process_lines,
        "ueventd_lines": ueventd_lines,
        "selinux_lines": selinux_lines,
        "service_lines": service_lines,
        "has_mdm_helper_esoc_fd": any("mdm_helper" in line for line in holder_lines) and any("/dev/esoc-0" in line for line in holder_lines),
        "has_ks_esoc_fd": any("comm=ks" in line or "cmd=/vendor/bin/ks" in line for line in holder_lines) and any("/dev/esoc-0" in line for line in holder_lines),
        "has_ks_mhi_pipe": any("/dev/mhi_0305_01.01.00_pipe_10" in line for line in process_lines + holder_lines),
        "has_per_mgr_subsys_esoc0_fd": any("/dev/subsys_esoc0" in line for line in holder_lines),
        "has_per_mgr_subsys_modem_fd": any("/dev/subsys_modem" in line for line in holder_lines),
        "has_mdm_helper_init_service": any("service vendor.mdm_helper" in line for line in ueventd_lines),
        "has_per_mgr_init_service": any("service vendor.per_mgr" in line for line in ueventd_lines),
        "has_per_mgr_running_trigger": any("init.svc.vendor.per_mgr=running" in line for line in service_lines),
        "has_mdm_helper_running_property": any("init.svc.vendor.mdm_helper=running" in line for line in service_lines),
        "has_esoc0_ueventd_rule": any("/dev/esoc-0" in line for line in ueventd_lines),
        "has_subsys_ueventd_rule": any("/dev/subsys_*" in line for line in ueventd_lines),
        "has_mdm_helper_selinux": any("vendor_mdm_helper_exec" in line for line in selinux_lines),
        "has_esoc_device_selinux": any("vendor_esoc_device" in line for line in selinux_lines),
        "has_subsys_device_selinux": any("vendor_ssr_device" in line for line in selinux_lines),
    }


def extract_native(v903_manifest_path: Path, v903_manifest: dict[str, Any]) -> dict[str, Any]:
    steps = v903_manifest.get("steps") or []
    helper_rel = ""
    for step in steps:
        if step.get("name") == "mdm-helper-only-capture":
            helper_rel = str(step.get("file") or "")
            break
    transcript = read_text(v903_manifest_path.parent / helper_rel) if helper_rel else ""
    keys = parse_key_values(transcript)
    contract = ((v903_manifest.get("analysis") or {}).get("helper") or {}).get("contract") or {}
    window_attr = capture_block(transcript, "A90_EXECNS_CNSS_PROC_mdm_helper_only_window_attr_current")
    final_attr = capture_block(transcript, "A90_EXECNS_CNSS_PROC_mdm_helper_only_final_attr_current")
    window_wchan = capture_block(transcript, "A90_EXECNS_CNSS_PROC_mdm_helper_only_window_wchan")
    final_wchan = capture_block(transcript, "A90_EXECNS_CNSS_PROC_mdm_helper_only_final_wchan")
    window_syscall = capture_block(transcript, "A90_EXECNS_CNSS_PROC_mdm_helper_only_window_syscall")
    final_syscall = capture_block(transcript, "A90_EXECNS_CNSS_PROC_mdm_helper_only_final_syscall")
    window_status = capture_block(transcript, "A90_EXECNS_CNSS_PROC_mdm_helper_only_window_status")
    final_status = capture_block(transcript, "A90_EXECNS_CNSS_PROC_mdm_helper_only_final_status")
    window_fd_targets = parse_fd_targets(transcript, "mdm_helper_only_window")
    final_fd_targets = parse_fd_targets(transcript, "mdm_helper_only_final")
    data_wifi_socket_exists = keys.get("context.data_vendor_wifi_sockets.exists", "")
    return {
        "v903_decision": v903_manifest.get("decision", ""),
        "v903_pass": bool(v903_manifest.get("pass")),
        "helper_transcript": str(v903_manifest_path.parent / helper_rel) if helper_rel else "",
        "mdm_helper_observable": contract.get("mdm_helper_observable") == "1",
        "all_postflight_safe": contract.get("all_postflight_safe") == "1",
        "result": contract.get("result", ""),
        "reason": contract.get("reason", ""),
        "attr_current_window": window_attr,
        "attr_current_final": final_attr,
        "wchan_window": window_wchan,
        "wchan_final": final_wchan,
        "syscall_window": window_syscall,
        "syscall_final": final_syscall,
        "status_window": window_status,
        "status_final": final_status,
        "fd_targets_window": window_fd_targets,
        "fd_targets_final": final_fd_targets,
        "data_vendor_wifi_sockets_exists": data_wifi_socket_exists,
        "fd_esoc0_count_window": int(contract.get("fd_esoc0_count.window") or 0),
        "fd_esoc0_count_final": int(contract.get("fd_esoc0_count.final") or 0),
        "fd_subsys_esoc0_count_window": int(contract.get("fd_subsys_esoc0_count.window") or 0),
        "fd_subsys_esoc0_count_final": int(contract.get("fd_subsys_esoc0_count.final") or 0),
        "fd_mhi_pipe_count_window": int(contract.get("fd_mhi_pipe_count.window") or 0),
        "fd_mhi_pipe_count_final": int(contract.get("fd_mhi_pipe_count.final") or 0),
        "ks_count_window": int(contract.get("ks_count.window") or 0),
        "mhi_pipe_cmdline_count_window": int(contract.get("mhi_pipe_cmdline_count.window") or 0),
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "service_manager_start_executed": contract.get("service_manager_start_executed") == "1",
        "wifi_hal_start_executed": contract.get("wifi_hal_start_executed") == "1",
        "scan_connect_linkup": contract.get("scan_connect_linkup") == "1",
        "credentials": contract.get("credentials") == "1",
        "external_ping": contract.get("external_ping") == "1",
    }


def classify(android: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
    android_contract = (
        android["v853_pass"]
        and android["has_mdm_helper_esoc_fd"]
        and android["has_ks_mhi_pipe"]
        and android["has_per_mgr_subsys_esoc0_fd"]
        and android["has_mdm_helper_init_service"]
        and android["has_per_mgr_running_trigger"]
        and android["has_mdm_helper_selinux"]
        and android["has_esoc0_ueventd_rule"]
    )
    native_negative = (
        native["v903_pass"]
        and native["mdm_helper_observable"]
        and native["result"] == "mdm-helper-no-esoc-fd"
        and native["fd_esoc0_count_window"] == 0
        and native["fd_esoc0_count_final"] == 0
        and native["fd_mhi_pipe_count_window"] == 0
        and native["fd_mhi_pipe_count_final"] == 0
        and native["ks_count_window"] == 0
        and not native["subsys_esoc0_open_attempted"]
    )
    deltas = {
        "selinux_context_delta": {
            "android": android["mdm_helper_context"],
            "native_window": native["attr_current_window"],
            "native_final": native["attr_current_final"],
            "mismatch": bool(android["mdm_helper_context"]) and native["attr_current_final"] != android["mdm_helper_context"],
        },
        "init_service_delta": {
            "android_has_vendor_mdm_helper_service": android["has_mdm_helper_init_service"],
            "android_has_per_mgr_running_trigger": android["has_per_mgr_running_trigger"],
            "native_service_manager_start_executed": native["service_manager_start_executed"],
        },
        "device_fd_delta": {
            "android_mdm_helper_esoc_fd": android["has_mdm_helper_esoc_fd"],
            "native_esoc_fd_window": native["fd_esoc0_count_window"],
            "native_esoc_fd_final": native["fd_esoc0_count_final"],
            "android_ks_mhi_pipe": android["has_ks_mhi_pipe"],
            "native_mhi_fd_window": native["fd_mhi_pipe_count_window"],
            "native_mhi_fd_final": native["fd_mhi_pipe_count_final"],
        },
        "peripheral_manager_delta": {
            "android_pm_service_subsys_esoc0_fd": android["has_per_mgr_subsys_esoc0_fd"],
            "android_pm_service_subsys_modem_fd": android["has_per_mgr_subsys_modem_fd"],
            "native_started_peripheral_manager": False,
        },
        "socket_surface_delta": {
            "native_data_vendor_wifi_sockets_exists": native["data_vendor_wifi_sockets_exists"],
            "native_final_fd_targets": native["fd_targets_final"],
        },
    }
    if android_contract and native_negative:
        return {
            "decision": "v904-mdm-helper-runtime-input-parity-classified",
            "pass": True,
            "reason": "Android mdm_helper runs as init-managed vendor_mdm_helper with per_mgr trigger and esoc/MHI fd surface; native V903 direct mdm_helper stays in kernel context with no esoc/ks/MHI surface",
            "next_step": "V905 should design a fail-closed runtime-input repair, prioritizing SELinux/init/per_mgr/property parity before another subsystem-open retry",
            "android_contract": android_contract,
            "native_negative": native_negative,
            "deltas": deltas,
        }
    return {
        "decision": "v904-mdm-helper-runtime-input-parity-incomplete",
        "pass": False,
        "reason": f"android_contract={android_contract} native_negative={native_negative}",
        "next_step": "repair missing V853/V903 evidence or run a focused recapture before live repair work",
        "android_contract": android_contract,
        "native_negative": native_negative,
        "deltas": deltas,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    delta_rows: list[list[Any]] = []
    for name, values in (manifest.get("classification") or {}).get("deltas", {}).items():
        delta_rows.append([name, json.dumps(values, ensure_ascii=False, sort_keys=True)])
    android = manifest.get("android") or {}
    native = manifest.get("native") or {}
    android_rows = [
        ["v853_decision", android.get("v853_decision")],
        ["v896_decision", android.get("v896_decision")],
        ["mdm_helper_context", android.get("mdm_helper_context")],
        ["has_mdm_helper_esoc_fd", android.get("has_mdm_helper_esoc_fd")],
        ["has_ks_mhi_pipe", android.get("has_ks_mhi_pipe")],
        ["has_per_mgr_running_trigger", android.get("has_per_mgr_running_trigger")],
        ["has_mdm_helper_init_service", android.get("has_mdm_helper_init_service")],
        ["has_mdm_helper_selinux", android.get("has_mdm_helper_selinux")],
    ]
    native_rows = [
        ["v903_decision", native.get("v903_decision")],
        ["result", native.get("result")],
        ["attr_current_final", native.get("attr_current_final")],
        ["wchan_final", native.get("wchan_final")],
        ["fd_targets_final", json.dumps(native.get("fd_targets_final"), ensure_ascii=False)],
        ["fd_esoc0_count_final", native.get("fd_esoc0_count_final")],
        ["fd_mhi_pipe_count_final", native.get("fd_mhi_pipe_count_final")],
        ["ks_count_window", native.get("ks_count_window")],
    ]
    return "\n".join([
        "# V904 mdm_helper Runtime Input Parity Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_contact: `{manifest['device_contact']}`",
        f"- actor_start_executed: `{manifest['actor_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Android Contract",
        "",
        markdown_table(["field", "value"], android_rows),
        "",
        "## Native V903 Contract",
        "",
        markdown_table(["field", "value"], native_rows),
        "",
        "## Deltas",
        "",
        markdown_table(["delta", "value"], delta_rows),
        "",
        "## Selected Android Lines",
        "",
        markdown_table(["kind", "line"], [["holder", line] for line in android.get("holder_lines", [])[:12]]),
        "",
        markdown_table(["kind", "line"], [["service", line] for line in android.get("service_lines", [])[:12]]),
        "",
        "## Interpretation",
        "",
        "- Android positive path is init-managed and SELinux-labelled as `vendor_mdm_helper`.",
        "- Android `pm-service` owns subsystem nodes before `mdm_helper`/`ks` image-link handling is visible.",
        "- Native V903 starts `mdm_helper` directly, remains in `kernel` context, and never reaches `/dev/esoc-0`, `ks`, or MHI.",
        "- The next repair should model the missing runtime inputs before retrying `/dev/subsys_esoc0`.",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v903_manifest = load_json(args.v903_manifest)
    v853_manifest = load_json(args.v853_manifest)
    v896_manifest = load_json(args.v896_manifest)
    android = extract_android(v853_manifest, v896_manifest)
    native = extract_native(args.v903_manifest, v903_manifest)
    classification = classify(android, native)
    manifest = {
        "generated_at": now_iso(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "v903_manifest": str(args.v903_manifest),
        "v853_manifest": str(args.v853_manifest),
        "v896_manifest": str(args.v896_manifest),
        "android": android,
        "native": native,
        "classification": classification,
        "device_contact": False,
        "android_boot_executed": False,
        "adb_command_executed": False,
        "live_esoc_ioctl_executed": False,
        "actor_start_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "boot_image_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_contact: {manifest['device_contact']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
