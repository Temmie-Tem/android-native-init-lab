#!/usr/bin/env python3
"""V820 host-only QRTR namespace/service-locator visibility classifier.

V819 captured registration catalogue evidence, but the remaining ambiguity is
whether the blocker is QRTR procfs visibility/namespace plumbing or actual
service publication absence.  This classifier parses the V819 helper output and
catalogue manifest without contacting the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v820-qrtr-namespace-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v820-qrtr-namespace-classifier.txt")
DEFAULT_V819_MANIFEST = Path("tmp/wifi/v819-mdm3-esoc-registration-catalogue/manifest.json")
DEFAULT_HELPER_OUTPUT = Path("tmp/wifi/v819-mdm3-esoc-registration-catalogue/native/lower-companion-start-only.txt")

FORBIDDEN_ACTIONS = (
    "device command",
    "custom kernel flash, boot image write, or partition write",
    "reboot or bootloader handoff",
    "service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "qcwlanstate on/off, esoc0 open, bind/unbind, driver override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v819-manifest", type=Path, default=DEFAULT_V819_MANIFEST)
    parser.add_argument("--helper-output", type=Path, default=DEFAULT_HELPER_OUTPUT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def safe_read(path: Path, limit: int = 16 * 1024 * 1024) -> tuple[str, dict[str, Any]]:
    resolved = resolve(path)
    info: dict[str, Any] = {"path": str(resolved), "exists": resolved.exists()}
    if not resolved.exists() or not resolved.is_file():
        return "", info
    data = resolved.read_bytes()[:limit]
    size = resolved.stat().st_size
    info.update({"is_file": True, "size": size, "bytes_read": len(data), "truncated": size > len(data)})
    return data.decode("utf-8", errors="replace"), info


def load_json(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    if not text:
        return {"file": info, "data": {}}
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"file": info, "data": {}, "error": str(exc)}
    return {"file": info, "data": loaded if isinstance(loaded, dict) else {}}


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def parse_key_values(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    key_re = re.compile(r"^([A-Za-z0-9_.:-]+)=(.*)$")
    for line in text.splitlines():
        match = key_re.match(line.strip())
        if not match:
            continue
        keys[match.group(1)] = match.group(2)
    return keys


def key_int(keys: dict[str, str], key: str) -> int:
    return int_value(keys.get(key))


def key_bool(keys: dict[str, str], key: str) -> bool:
    return key_int(keys, key) != 0


def socket_counts(keys: dict[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    prefix = "capture.wifi_hal_composite_"
    suffix = ".fd_links.socket_count"
    for key, value in keys.items():
        if key.startswith(prefix) and key.endswith(suffix):
            child = key[len(prefix):-len(suffix)]
            counts[child] = int_value(value)
    return counts


def qipcrtr_protocol(keys: dict[str, str]) -> dict[str, Any]:
    phases = ("net_before", "net_after_spawn", "net_window", "net_after_cleanup")
    rows: dict[str, dict[str, Any]] = {}
    for phase in phases:
        base = f"wifi_companion_start.{phase}"
        rows[phase] = {
            "present": key_bool(keys, f"{base}.qipcrtr_present"),
            "sockets": key_int(keys, f"{base}.qipcrtr_sockets"),
            "size": key_int(keys, f"{base}.qipcrtr_size"),
            "line": keys.get(f"{base}.qipcrtr_line", ""),
        }
    return {
        "phases": rows,
        "present_all": all(item["present"] for item in rows.values()),
        "socket_count_all_zero": all(item["sockets"] == 0 for item in rows.values()),
    }


def procfs_visibility(keys: dict[str, str], helper_text: str) -> dict[str, Any]:
    begin_count = helper_text.count("_proc_net_qrtr_BEGIN") + helper_text.count("_net_qrtr_BEGIN")
    open_errors = helper_text.count("path=/proc/net/qrtr") + helper_text.count("name=net/qrtr")
    missing_errors = helper_text.count("open-error=No such file or directory")
    return {
        "global_window_captured": key_bool(keys, "wifi_companion_start.net_window.qrtr_captured"),
        "surface_window_proc_qrtr_captured": key_bool(keys, "wifi_companion_start.surface_window.proc_qrtr_captured"),
        "proc_qrtr_begin_markers": begin_count,
        "proc_qrtr_path_mentions": open_errors,
        "open_error_no_such_file": missing_errors,
        "proc_qrtr_end_zero": helper_text.count("_proc_net_qrtr_END bytes=0") + helper_text.count("_net_qrtr_END bytes=0"),
    }


def qrtr_readback(keys: dict[str, str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index in (0, 1):
        prefix = f"wifi_companion_qrtr_readback.case_{index}"
        rows.append({
            "case": index,
            "service": key_int(keys, f"{prefix}.service"),
            "instance": keys.get(f"{prefix}.instance", ""),
            "socket_rc": key_int(keys, f"{prefix}.socket.rc"),
            "socket_family": key_int(keys, f"{prefix}.socket_name.family"),
            "socket_node": key_int(keys, f"{prefix}.socket_name.node"),
            "socket_port": key_int(keys, f"{prefix}.socket_name.port"),
            "new_lookup_rc": key_int(keys, f"{prefix}.new_lookup_send.rc"),
            "del_lookup_rc": key_int(keys, f"{prefix}.del_lookup_send.rc"),
            "events": key_int(keys, f"{prefix}.readback.events"),
            "service_events": key_int(keys, f"{prefix}.readback.service_events"),
            "end_of_list": key_int(keys, f"{prefix}.readback.end_of_list"),
            "timeout": key_int(keys, f"{prefix}.readback.timeout"),
            "empty_events": key_int(keys, f"{prefix}.readback.empty_events"),
            "qmi_attempted": key_int(keys, f"{prefix}.qmi_attempted"),
        })
    return {
        "allowed": key_int(keys, "wifi_companion_qrtr_readback.allowed"),
        "matrix": keys.get("wifi_companion_qrtr_readback.matrix", ""),
        "result": keys.get("wifi_companion_qrtr_readback.result", ""),
        "send_attempted": key_int(keys, "wifi_companion_qrtr_readback.send_attempted"),
        "qmi_payload": key_int(keys, "wifi_companion_qrtr_readback.qmi_payload"),
        "qmi_attempted_total": sum(row["qmi_attempted"] for row in rows),
        "service_events_total": sum(row["service_events"] for row in rows),
        "timeouts_total": sum(row["timeout"] for row in rows),
        "end_of_list_total": sum(row["end_of_list"] for row in rows),
        "socket_ok_all": all(row["socket_rc"] == 0 and row["socket_family"] == 42 for row in rows),
        "lookup_send_ok_all": all(row["new_lookup_rc"] == 0 and row["del_lookup_rc"] == 0 for row in rows),
        "rows": rows,
    }


def service_locator_visibility(v819: dict[str, Any], helper_text: str) -> dict[str, Any]:
    catalogue = as_dict(v819.get("catalogue"))
    after = as_dict(catalogue.get("after-companion"))
    counts = as_dict(after.get("counts"))
    return {
        "catalogue_after_companion": counts,
        "dmesg_service_locator_refs": int_value(counts.get("service_locator_refs")),
        "dmesg_service_notifier_refs": int_value(counts.get("service_notifier_refs")),
        "debug_service_missing": bool(counts.get("service_debug_missing")),
        "wlan_pd_refs": int_value(counts.get("wlan_pd_refs")),
        "wlfw_refs": int_value(counts.get("wlfw_refs")),
        "helper_service_notifier_captured": key_from_text_int(helper_text, "wifi_companion_start.surface_window.service_notifier_captured"),
    }


def key_from_text_int(text: str, key: str) -> int:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.M)
    return int_value(match.group(1) if match else None)


def child_process_summary(keys: dict[str, str]) -> dict[str, Any]:
    children = ("qrtr_ns", "rmt_storage", "tftp_server", "pd_mapper", "cnss_diag", "cnss_daemon")
    sockets = socket_counts(keys)
    rows: dict[str, Any] = {}
    for child in children:
        base = f"wifi_companion_start.child.{child}"
        rows[child] = {
            "observable": key_int(keys, f"{base}.observable"),
            "postflight_safe": key_int(keys, f"{base}.postflight_safe"),
            "start_order": key_int(keys, f"{base}.start_order"),
            "fd_socket_count": sockets.get(child, 0),
            "exec_target": keys.get(f"wifi_hal_composite_child.{child}.exec_target", ""),
            "selinux_exec": keys.get(f"wifi_hal_composite_child.{child}.selinux_exec.target_context", ""),
        }
    return {
        "child_started": key_int(keys, "wifi_companion_start.child_started"),
        "all_observable": key_int(keys, "wifi_companion_start.all_observable"),
        "all_postflight_safe": key_int(keys, "wifi_companion_start.all_postflight_safe"),
        "rows": rows,
    }


def copy_evidence(store: EvidenceStore, helper_text: str) -> None:
    snippets: list[str] = []
    patterns = (
        "qipcrtr",
        "proc_net_qrtr",
        "net_qrtr",
        "wifi_companion_qrtr_readback",
        "fd_links.socket_count",
        "service_locator",
        "service_notifier",
    )
    for line in helper_text.splitlines():
        lower = line.lower()
        if any(pattern in lower for pattern in patterns):
            snippets.append(line)
    store.write_text("helper-qrtr-service-snippets.txt", "\n".join(snippets) + "\n")


def build_analysis(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v819_loaded = load_json(args.v819_manifest)
    v819 = v819_loaded["data"]
    helper_text, helper_file = safe_read(args.helper_output)
    keys = parse_key_values(helper_text)
    if helper_text:
        copy_evidence(store, helper_text)
    return {
        "v819": {
            "file": v819_loaded["file"],
            "decision": v819.get("decision", ""),
            "pass": bool(v819.get("pass")),
            "reason": v819.get("reason", ""),
            "next_step": v819.get("next_step", ""),
        },
        "helper_file": helper_file,
        "helper_key_count": len(keys),
        "child_processes": child_process_summary(keys),
        "qipcrtr_protocol": qipcrtr_protocol(keys),
        "procfs_visibility": procfs_visibility(keys, helper_text),
        "qrtr_readback": qrtr_readback(keys),
        "service_locator_visibility": service_locator_visibility(v819, helper_text),
        "helper_guardrails": {
            "service_manager": key_int(keys, "wifi_companion_start.service_manager"),
            "wifi_hal": key_int(keys, "wifi_companion_start.wifi_hal"),
            "wificond": key_int(keys, "wifi_companion_start.wificond"),
            "scan_connect_linkup": key_int(keys, "wifi_companion_start.scan_connect_linkup"),
            "external_ping": key_int(keys, "wifi_companion_start.external_ping"),
            "qcwlanstate_write": key_int(keys, "wifi_companion_start.qcwlanstate_write"),
            "qmi_payload": key_int(keys, "wifi_companion_start.qmi_payload"),
        },
    }


def build_checks(command: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only classifier plan; no device command executed",
            "next_step": "run V820 host-only classifier",
        }]

    child = analysis["child_processes"]
    qipcrtr = analysis["qipcrtr_protocol"]
    procfs = analysis["procfs_visibility"]
    readback = analysis["qrtr_readback"]
    service_locator = analysis["service_locator_visibility"]
    guardrails = analysis["helper_guardrails"]
    guardrail_ok = all(int_value(value) == 0 for value in guardrails.values())
    children_ok = (
        child["child_started"] == 6
        and child["all_observable"] == 1
        and child["all_postflight_safe"] == 1
        and child["rows"]["qrtr_ns"]["fd_socket_count"] > 0
    )
    qrtr_socket_working = (
        readback["allowed"] == 1
        and readback["send_attempted"] == 1
        and readback["socket_ok_all"]
        and readback["lookup_send_ok_all"]
        and readback["qmi_attempted_total"] == 0
        and readback["timeouts_total"] == 0
    )
    service_empty = readback["service_events_total"] == 0 and readback["end_of_list_total"] > 0
    procfs_absent = procfs["proc_qrtr_path_mentions"] > 0 and procfs["open_error_no_such_file"] > 0
    return [
        {
            "name": "v819-route-ready",
            "status": "pass" if analysis["v819"]["pass"] and analysis["v819"]["decision"] == "v819-mdm3-esoc-registration-catalogue-captured" else "blocked",
            "detail": analysis["v819"],
            "next_step": "restore V819 evidence before V820 classification",
        },
        {
            "name": "host-only-boundary",
            "status": "pass",
            "detail": "no device command, reboot, flash, HAL, scan/connect, credential use, route, or ping",
            "next_step": "preserve V820 as a classifier only",
        },
        {
            "name": "helper-children-observable",
            "status": "pass" if children_ok else "blocked",
            "detail": child,
            "next_step": "refresh helper run if child observability is missing",
        },
        {
            "name": "guardrails-preserved",
            "status": "pass" if guardrail_ok else "blocked",
            "detail": guardrails,
            "next_step": "discard route if any forbidden helper action appeared",
        },
        {
            "name": "qipcrtr-protocol-no-sockets",
            "status": "pass" if qipcrtr["present_all"] and qipcrtr["socket_count_all_zero"] else "review",
            "detail": qipcrtr,
            "next_step": "treat protocol presence as necessary but not sufficient for publication",
        },
        {
            "name": "qrtr-procfs-absent",
            "status": "pass" if procfs_absent else "review",
            "detail": procfs,
            "next_step": "do not rely on /proc/net/qrtr as the primary live signal",
        },
        {
            "name": "af-qrtr-readback-working",
            "status": "pass" if qrtr_socket_working else "blocked",
            "detail": readback,
            "next_step": "if AF_QIPCRTR readback fails, fix QRTR socket path before service matrix",
        },
        {
            "name": "service69-publication-empty",
            "status": "pass" if service_empty else "finding",
            "detail": readback,
            "next_step": "expand the in-helper readback matrix beyond WLFW service69",
        },
        {
            "name": "service-locator-visible-only-in-dmesg",
            "status": "pass" if service_locator["dmesg_service_locator_refs"] > 0 and service_locator["debug_service_missing"] else "review",
            "detail": service_locator,
            "next_step": "V821 should query QRTR nameservice matrix directly instead of debugfs",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v820-qrtr-namespace-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only QRTR namespace classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v820-qrtr-namespace-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "restore required V819/helper evidence before selecting the next live gate",
        )
    readback = analysis["qrtr_readback"]
    if readback["service_events_total"] == 0:
        return (
            "v820-procfs-absent-af-qrtr-readback-working",
            True,
            "QIPCRTR protocol and helper AF_QIPCRTR readback work, but /proc/net/qrtr/debugfs visibility is absent and WLFW service69 publication is empty",
            "V821 should run an in-helper QRTR nameservice matrix for service-locator/service-notifier/WLFW candidates without QMI payload, HAL, scan/connect, credentials, DHCP, or external ping",
        )
    return (
        "v820-qrtr-service-publication-visible",
        True,
        "helper QRTR readback saw service events; route next gate to classify the published services",
        "V821 should classify observed service events before any HAL/connect step",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = build_analysis(args, store)
    checks = build_checks(args.command, analysis)
    decision, pass_ok, reason, next_step = decide(args.command, checks, analysis)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v820",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "analysis": analysis,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "reboot_executed": False,
        "esoc0_open_executed": False,
        "module_load_unload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    analysis = manifest["analysis"]
    signal_rows = [
        ["child_processes", json.dumps(analysis["child_processes"], ensure_ascii=False, sort_keys=True)],
        ["qipcrtr_protocol", json.dumps(analysis["qipcrtr_protocol"], ensure_ascii=False, sort_keys=True)],
        ["procfs_visibility", json.dumps(analysis["procfs_visibility"], ensure_ascii=False, sort_keys=True)],
        ["qrtr_readback", json.dumps(analysis["qrtr_readback"], ensure_ascii=False, sort_keys=True)],
        ["service_locator_visibility", json.dumps(analysis["service_locator_visibility"], ensure_ascii=False, sort_keys=True)],
    ]
    return "\n".join([
        "# V820 QRTR Namespace Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Signals",
        "",
        markdown_table(["signal", "value"], signal_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
